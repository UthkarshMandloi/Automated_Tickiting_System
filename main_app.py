# -----------------------------------------------------------------------------
# Event Ticketing Automation System
#
# This script automates the entire event ticketing process:
# 1. Reads attendee data from a Google Sheet.
# 2. Generates a unique pre-filled Google Form link for each attendee.
# 3. Creates a QR code from this link.
# 4. Personalizes a ticket image with the attendee's name and the QR code.
# 5. Uploads the generated files to specific Google Drive folders.
# 6. Sends the personalized ticket via email to the attendee.
# 7. Updates the Google Sheet with the processing status ("Generated", "Sent", "Failed").
# It runs in a continuous loop to process new entries as they appear.
#
# -----------------------------------------------------------------------------

# =============================================================================
#  Part 1: Imports
# =============================================================================
import os
import time
import qrcode
import smtplib
import importlib
from urllib.parse import quote_plus
from PIL import Image, ImageDraw, ImageFont

# Google API client and errors
from googleapiclient.errors import HttpError
from googleapiclient.http import MediaFileUpload

# Email components
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.mime.image import MIMEImage

# Custom modules (ensure these files are in the same directory)
import config
from google_auth import authenticate_google_api

# Optional: Tesseract for OCR-based placeholder detection
try:
    import pytesseract
    if config.TESSERACT_CMD_PATH:
        pytesseract.pytesseract.tesseract_cmd = config.TESSERACT_CMD_PATH
except ImportError:
    pytesseract = None
    print("⚠️ Warning: pytesseract library not found. Automated placeholder detection will be disabled.")


# =============================================================================
#  Part 2: Main Application Code
# =============================================================================

# --- Global Application State & Constants ---
PROCESSED_ENTRIES = set()
COLUMN_INDICES = {}
APPLICATION_SCOPES = ['https://www.googleapis.com/auth/spreadsheets', 'https://www.googleapis.com/auth/drive']

###
# --- Utility Functions ---
###

def get_spreadsheet_id_from_url(url: str) -> str:
    """Extracts the Google Spreadsheet ID from its URL."""
    try:
        return url.split('/d/')[1].split('/')[0]
    except IndexError:
        raise ValueError(f"Invalid Google Sheet URL: '{url}'. Could not extract Spreadsheet ID.")

def get_sheet_data(sheets_service, spreadsheet_id: str, data_range: str) -> tuple[list, list]:
    """Fetches data from a Google Sheet, separating the header from data rows."""
    try:
        result = sheets_service.spreadsheets().values().get(spreadsheetId=spreadsheet_id, range=data_range).execute()
        values = result.get('values', [])
        if not values:
            return [], []
        return values[0], values[1:] # headers, data
    except HttpError as error:
        print(f"❌ An error occurred while fetching sheet data: {error}")
        return [], []

def update_sheet_cell(sheets_service, spreadsheet_id: str, sheet_name: str, row_index: int, col_index: int, value: str):
    """Updates a single cell in the Google Sheet."""
    range_name = f"{sheet_name}!{chr(ord('A') + col_index)}{row_index + 2}"
    body = {'values': [[value]]}
    try:
        sheets_service.spreadsheets().values().update(spreadsheetId=spreadsheet_id, range=range_name, valueInputOption='RAW', body=body).execute()
        print(f"✅ Sheet updated: Cell '{range_name}' set to '{value}'")
    except HttpError as error:
        print(f"❌ Error updating cell {range_name}: {error}")

def upload_file_to_drive(drive_service, file_path: str, folder_id: str, file_name: str) -> str | None:
    """Uploads a file to a specified Google Drive folder."""
    file_metadata = {'name': file_name, 'parents': [folder_id]}
    media = MediaFileUpload(file_path, mimetype='image/png')
    try:
        file = drive_service.files().create(body=file_metadata, media_body=media, fields='id').execute()
        print(f"✅ Uploaded '{file_name}' to Drive. File ID: {file.get('id')}")
        return file.get('id')
    except HttpError as error:
        print(f"❌ Error uploading '{file_name}' to Drive: {error}")
        return None

def generate_qr_code(data: str, file_path: str, size: int) -> bool:
    """Generates and saves a QR code image."""
    try:
        qr = qrcode.QRCode(version=1, error_correction=qrcode.constants.ERROR_CORRECT_L, box_size=10, border=4)
        qr.add_data(data)
        qr.make(fit=True)
        img = qr.make_image(fill_color="black", back_color="white").resize((size, size), Image.Resampling.LANCZOS)
        img.save(file_path)
        print(f"✅ QR code generated: {file_path}")
        return True
    except Exception as e:
        print(f"❌ Error generating QR code: {e}")
        return False

def create_ticket_image(output_path: str, name: str, qr_code_path: str) -> bool:
    """Creates a personalized ticket by overlaying a name and QR code onto a template."""
    try:
        base_img = Image.open(config.TICKET_TEMPLATE_EMPTY_PATH).convert("RGBA")
        draw = ImageDraw.Draw(base_img)

        # Load font
        try:
            font = ImageFont.truetype(config.FONT_PATH, config.DETECTED_FONT_SIZE)
        except IOError:
            print(f"⚠️ Warning: Font '{config.FONT_PATH}' not found. Using default font.")
            font = ImageFont.load_default()

        # Position and draw name (centered horizontally)
        text_bbox = draw.textbbox((0, 0), name, font=font)
        text_width = text_bbox[2] - text_bbox[0]
        text_x = (base_img.width - text_width) / 2
        text_y = config.DETECTED_NAME_TEXT_Y_POS
        
        # Adjust the bounding box to the final calculated position
        final_bbox = (text_x, text_y, text_x + text_width, text_y + (text_bbox[3] - text_bbox[1]))

        draw.text((text_x, text_y), name, font=font, fill=config.TEXT_COLOR)
        draw.rectangle(final_bbox, outline="red", width=3) # <<< ADD THIS LINE FOR DEBUGGING

        # Position and paste QR code (centered horizontally)
        qr_img = Image.open(qr_code_path).convert("RGBA")
        qr_x = (base_img.width - qr_img.width) / 2
        base_img.paste(qr_img, (int(qr_x), int(config.DETECTED_QR_CODE_Y_POS)), qr_img)

        base_img.save(output_path)
        print(f"✅ Personalized ticket created: {output_path}")
        return True
    except Exception as e:
        print(f"❌ Error creating ticket image: {e}")
        return False

def send_ticket_email(recipient_email: str, recipient_name: str, ticket_file_path: str) -> bool:
    """Sends an email with the generated ticket attached."""
    try:
        with open(config.EMAIL_MESSAGE_PATH, 'r', encoding='utf-8') as f:
            message_template = f.read()

        email_body = message_template.replace('{name}', recipient_name)
        msg = MIMEMultipart()
        msg['From'] = config.SENDER_EMAIL
        msg['To'] = recipient_email
        msg['Subject'] = "Your Event E-Ticket is Here!"
        msg.attach(MIMEText(email_body, 'plain'))

        with open(ticket_file_path, 'rb') as fp:
            img = MIMEImage(fp.read(), _subtype="png")
            img.add_header('Content-Disposition', 'attachment', filename=os.path.basename(ticket_file_path))
            msg.attach(img)

        with smtplib.SMTP_SSL('smtp.gmail.com', 465) as smtp:
            smtp.login(config.SENDER_EMAIL, config.SENDER_APP_PASSWORD)
            smtp.send_message(msg)
        print(f"✅ Email with ticket successfully sent to {recipient_email}.")
        return True
    except Exception as e:
        print(f"❌ Error sending email to {recipient_email}: {e}")
        return False

def get_value_safe(row: list, col_idx: int) -> str:
    """Safely retrieves a value from a list (sheet row)."""
    return row[col_idx] if col_idx < len(row) else ''

###
# --- Main Execution Logic ---
###
if __name__ == '__main__':
    print("--- 🚀 Event Ticketing Automation System ---")

    # On startup, reload config in case it was modified by OCR
    importlib.reload(config)

    print("\n--- Initializing Google API services ---")
    sheets_service = authenticate_google_api('sheets', 'v4', APPLICATION_SCOPES)
    drive_service = authenticate_google_api('drive', 'v3', APPLICATION_SCOPES)

    if not sheets_service or not drive_service:
        print("❌ CRITICAL: Could not authenticate with Google APIs. Check credentials.json.")
        exit(1)
    print("✅ Google API services initialized successfully.")

    try:
        spreadsheet_id = get_spreadsheet_id_from_url(config.MAIN_SHEET_LINK)
    except ValueError as e:
        print(f"❌ CRITICAL: {e}. Correct MAIN_SHEET_LINK in config.py.")
        exit(1)

    print(f"\n--- 🔄 Starting continuous monitoring of '{config.MAIN_SHEET_NAME}' ---")
    print(f"Polling every {config.POLLING_INTERVAL_SECONDS} seconds. Press Ctrl+C to stop.")

    # Main Polling Loop
    while True:
        try:
            print(f"\n[{time.strftime('%Y-%m-%d %H:%M:%S')}] Checking for new data...")
            headers, sheet_data = get_sheet_data(sheets_service, spreadsheet_id, config.DATA_RANGE_INITIAL)

            if not headers:
                time.sleep(config.POLLING_INTERVAL_SECONDS)
                continue

            # Dynamically map column names to indices
            for col_name in [config.COL_NAME, config.COL_EMAIL, config.COL_TICKET_STATUS, config.COL_EMAIL_STATUS]:
                if col_name not in headers:
                    print(f"❌ CRITICAL: Column '{col_name}' not found in sheet. Exiting.")
                    exit(1)
                COLUMN_INDICES[col_name] = headers.index(col_name)

            if not sheet_data:
                print("No data rows found. Waiting for new entries...")
                time.sleep(config.POLLING_INTERVAL_SECONDS)
                continue

            # Process each row
            for i, row in enumerate(sheet_data):
                name = get_value_safe(row, COLUMN_INDICES[config.COL_NAME]).strip()
                email = get_value_safe(row, COLUMN_INDICES[config.COL_EMAIL]).strip()
                ticket_status = get_value_safe(row, COLUMN_INDICES[config.COL_TICKET_STATUS]).strip()

                if not name or not email:
                    continue # Skip empty or malformed rows

                # A unique ID for the entry to avoid re-processing in the same run
                row_unique_id = f"{get_value_safe(row, 0).strip()}-{email}"

                if ticket_status == "Sent" or row_unique_id in PROCESSED_ENTRIES:
                    continue # Skip already processed entries

                print(f"\n✨ Processing new entry: Name='{name}', Email='{email}'")
                PROCESSED_ENTRIES.add(row_unique_id)
                os.makedirs("temp", exist_ok=True) # Ensure temp folder exists

                # 1. Update status to 'Generating...'
                update_sheet_cell(sheets_service, spreadsheet_id, config.MAIN_SHEET_NAME, i, COLUMN_INDICES[config.COL_TICKET_STATUS], "Generating...")

                # 2. Generate pre-filled link & QR code
                prefilled_link = config.PREFILLED_FORM_BASE_LINK.format(name_param=quote_plus(name), status_param="Attended")
                qr_filename = f"{name.replace(' ', '_')}_QR.png"
                qr_path = os.path.join("temp", qr_filename)
                if not generate_qr_code(prefilled_link, qr_path, config.DETECTED_QR_CODE_TARGET_SIZE):
                    update_sheet_cell(sheets_service, spreadsheet_id, config.MAIN_SHEET_NAME, i, COLUMN_INDICES[config.COL_TICKET_STATUS], "Failed (QR)")
                    continue

                # 3. Create Ticket Image
                ticket_filename = f"{name.replace(' ', '_')}_Ticket.png"
                ticket_path = os.path.join("temp", ticket_filename)
                if not create_ticket_image(ticket_path, name, qr_path):
                    update_sheet_cell(sheets_service, spreadsheet_id, config.MAIN_SHEET_NAME, i, COLUMN_INDICES[config.COL_TICKET_STATUS], "Failed (Image)")
                    continue

                # 4. Upload files to Drive
                upload_file_to_drive(drive_service, qr_path, config.QR_CODES_FOLDER_ID, qr_filename)
                upload_file_to_drive(drive_service, ticket_path, config.TICKETS_FOLDER_ID, ticket_filename)
                update_sheet_cell(sheets_service, spreadsheet_id, config.MAIN_SHEET_NAME, i, COLUMN_INDICES[config.COL_TICKET_STATUS], "Generated")
                update_sheet_cell(sheets_service, spreadsheet_id, config.MAIN_SHEET_NAME, i, COLUMN_INDICES[config.COL_EMAIL_STATUS], "Sending...")

                # 5. Send Email
                if send_ticket_email(email, name, ticket_path):
                    update_sheet_cell(sheets_service, spreadsheet_id, config.MAIN_SHEET_NAME, i, COLUMN_INDICES[config.COL_TICKET_STATUS], "Sent")
                    update_sheet_cell(sheets_service, spreadsheet_id, config.MAIN_SHEET_NAME, i, COLUMN_INDICES[config.COL_EMAIL_STATUS], "Sent")
                else:
                    update_sheet_cell(sheets_service, spreadsheet_id, config.MAIN_SHEET_NAME, i, COLUMN_INDICES[config.COL_EMAIL_STATUS], "Failed (Email)")

                # 6. Clean up temp files
                os.remove(qr_path)
                os.remove(ticket_path)
                print(f"✅ Cleaned up temp files for {name}.")


            time.sleep(config.POLLING_INTERVAL_SECONDS)

        except KeyboardInterrupt:
            print("\n🛑 Monitoring stopped by user. Exiting gracefully.")
            break
        except Exception as e:
            print(f"\n❌ An unexpected error occurred in the main loop: {e}")
            print("Restarting monitoring after a short delay...")
            time.sleep(config.POLLING_INTERVAL_SECONDS * 2)

# =============================================================================
#  Part 3: Test Code
# =============================================================================

def test_single_ticket_generation():
    """
    A standalone function to test only the image generation logic.
    It uses local files and does not require any API connections.
    This is useful for quickly verifying the template, font, and positioning.
    
    To run this test:
    1. Uncomment the lines at the very bottom of this script.
    2. Make sure you have 'template.png', 'qr.png', and 'Poppins-Bold.ttf' in your directory.
    3. Run the script: python your_script_name.py
    """
    print("\n--- 🧪 Running Standalone Image Generation Test ---")

    try:
        # --- Configuration (Local for this test) ---
        template_path = "template.png"
        qr_code_path = "qr.png"
        font_path = "Poppins-Bold.ttf"
        output_path = "test_final_output.png"
        
        name = "Uthkarsh Mandloi"
        font_size = 60
        text_position = (850, 750)  # (x, y) - Manually set for the test
        qr_size = 350
        qr_position = (785, 950) # (x, y) - Manually set for the test

        # --- Test Logic ---
        print(f"Loading template: {template_path}")
        template = Image.open(template_path).convert("RGBA")

        print(f"Loading and resizing QR code: {qr_code_path}")
        qr_code = Image.open(qr_code_path).convert("RGBA")
        qr_code = qr_code.resize((qr_size, qr_size))

        print("Pasting QR code onto template...")
        template.paste(qr_code, qr_position, qr_code)

        print("Drawing text on image...")
        draw = ImageDraw.Draw(template)
        font = ImageFont.truetype(font_path, font_size)
        draw.text(text_position, name, font=font, fill=(0, 0, 0, 255)) # Black text

        print(f"Saving final image to: {output_path}")
        template.save(output_path)

        print(f"✅✅✅ Test successful! Image generated and saved as '{output_path}'.")

    except FileNotFoundError as e:
        print(f"❌ TEST FAILED: File not found - {e}. Make sure the required files are in the directory.")
    except Exception as e:
        print(f"❌ TEST FAILED: An unexpected error occurred: {e}")


# --- To run the standalone test, uncomment the two lines below ---
# if __name__ == '__main__':
#     test_single_ticket_generation()