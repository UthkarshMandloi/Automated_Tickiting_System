# -----------------------------------------------------------------------------
# Event Ticketing Automation System (Server Ready)
#
# This script is now configured to run on a server using Google Service Account
# credentials for authentication, removing the need for browser-based login.
# It can download assets like templates and fonts directly from URLs.
# It also runs a simple web server for status checks and data retrieval.
# -----------------------------------------------------------------------------

# =============================================================================
#  Part 1: Imports
# =============================================================================
import os
import time
import uuid
import qrcode
import smtplib
import importlib
import json
import requests
import threading
import http.server
import socketserver
from urllib.parse import quote_plus, urlparse
from PIL import Image, ImageDraw, ImageFont

# Google API client and errors
from googleapiclient.errors import HttpError
from googleapiclient.http import MediaFileUpload
from google.oauth2.service_account import Credentials
from googleapiclient.discovery import build


# Email components
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.mime.image import MIMEImage

# Custom modules (ensure these files are in the same directory)
import config
from mongo_helper import MongoDBClient

# =============================================================================
#  Part 2: Main Application Code
# =============================================================================

# --- Global Application State & Constants ---
PROCESSED_ENTRIES = set()
COLUMN_INDICES = {}
ERROR_LOG = []
MAX_ERROR_LOG_SIZE = 100
mongo_client = MongoDBClient() # Initialize MongoDB client

def log_error(message):
    """Logs an error message to the console and a global list."""
    print(message)
    if len(ERROR_LOG) >= MAX_ERROR_LOG_SIZE:
        ERROR_LOG.pop(0) # Remove the oldest error
    ERROR_LOG.append(f"[{time.strftime('%Y-%m-%d %H:%M:%S')}] {message}")

###
# --- Web Server Components ---
###

class StatusHandler(http.server.SimpleHTTPRequestHandler):
    """A handler for multiple API endpoints for status and data retrieval."""
    def do_GET(self):
        if self.path == '/':
            self.send_status_response()
        elif self.path == '/errors':
            self.send_json_response(ERROR_LOG)
        elif self.path == '/attendees':
            self.send_attendees_response()
        elif self.path == '/unsent':
            self.send_unsent_response()
        else:
            self.send_error(404, "Not Found")

    def send_json_response(self, data):
        """Sends a JSON response."""
        self.send_response(200)
        self.send_header("Content-type", "application/json; charset=utf-8")
        self.end_headers()
        self.wfile.write(json.dumps(data, indent=2).encode('utf-8'))

    def send_status_response(self):
        """Sends a simple text status response."""
        self.send_response(200)
        self.send_header("Content-type", "text/plain; charset=utf-8")
        self.end_headers()
        status_message = f"✅ Event Ticketing System is running.\nLast check: {time.strftime('%Y-%m-%d %H:%M:%S')}"
        self.wfile.write(status_message.encode('utf-8'))

    def send_attendees_response(self):
        """Fetches and returns all attendees from MongoDB."""
        try:
            # CORRECTED: Use find_attendees_by_query with an empty dict to get all
            attendees = mongo_client.find_attendees_by_query({})
            sanitized_attendees = []
            for attendee in attendees:
                attendee['_id'] = str(attendee['_id']) # Convert ObjectId to string
                sanitized_attendees.append({
                    "name": attendee.get(config.COL_NAME),
                    "email": attendee.get(config.COL_EMAIL),
                    "attendee_id": attendee.get("attendee_id"),
                    "ticket_status": attendee.get(config.COL_TICKET_STATUS),
                    "email_status": attendee.get(config.COL_EMAIL_STATUS)
                })
            self.send_json_response(sanitized_attendees)
        except Exception as e:
            self.send_error(500, f"Error fetching attendees: {e}")
            log_error(f"API Error fetching attendees: {e}")

    def send_unsent_response(self):
        """Fetches and returns attendees with unsent emails."""
        try:
            unsent = mongo_client.find_attendees_by_query(
                {config.COL_EMAIL_STATUS: {"$ne": "Sent"}}
            )
            sanitized_unsent = []
            for attendee in unsent:
                attendee['_id'] = str(attendee['_id'])
                sanitized_unsent.append({
                    "name": attendee.get(config.COL_NAME),
                    "email": attendee.get(config.COL_EMAIL),
                    "attendee_id": attendee.get("attendee_id"),
                    "email_status": attendee.get(config.COL_EMAIL_STATUS)
                })
            self.send_json_response(sanitized_unsent)
        except Exception as e:
            self.send_error(500, f"Error fetching unsent list: {e}")
            log_error(f"API Error fetching unsent list: {e}")


def run_web_server(port=8000):
    """Runs a simple HTTP server in a separate thread."""
    with socketserver.TCPServer(("", port), StatusHandler) as httpd:
        print(f"🌐 Simple web server started at http://localhost:{port}")
        httpd.serve_forever()

###
# --- Utility Functions ---
###

def download_file(url, local_filename):
    """Downloads a file from a URL to a local path."""
    try:
        if "drive.google.com" in url:
            file_id = url.split('/d/')[1].split('/')[0]
            download_url = f'https://drive.google.com/uc?export=download&id={file_id}'
        else:
            download_url = url

        with requests.get(download_url, stream=True) as r:
            r.raise_for_status()
            with open(local_filename, 'wb') as f:
                for chunk in r.iter_content(chunk_size=8192):
                    f.write(chunk)
        print(f"✅ Successfully downloaded '{local_filename}' from URL.")
        return local_filename
    except Exception as e:
        log_error(f"❌ Error downloading file from {url}: {e}")
        return None


def get_spreadsheet_id_from_url(url: str) -> str:
    """Extracts the Google Spreadsheet ID from its URL."""
    try:
        return url.split('/d/')[1].split('/')[0]
    except IndexError:
        raise ValueError(f"Invalid Google Sheet URL: '{url}'. Could not extract Spreadsheet ID.")

def get_folder_id_from_url(url: str) -> str:
    """Extracts the Google Drive Folder ID from its URL."""
    try:
        parsed_url = urlparse(url)
        path = parsed_url.path
        if '/folders/' in path:
            return path.split('/folders/')[1].split('/')[0]
        elif len(url) > 20 and ' ' not in url and not url.startswith('http'):
             return url
        else:
            raise ValueError("URL does not contain '/folders/'.")
    except (IndexError, ValueError) as e:
        raise ValueError(f"Invalid Google Drive Folder URL: '{url}'. Could not extract Folder ID. {e}")


def get_sheet_data(sheets_service, spreadsheet_id: str, data_range: str) -> tuple[list, list]:
    """Fetches data from a Google Sheet, separating the header from data rows."""
    try:
        result = sheets_service.spreadsheets().values().get(spreadsheetId=spreadsheet_id, range=data_range).execute()
        values = result.get('values', [])
        if not values:
            return [], []
        return values[0], values[1:] # headers, data
    except HttpError as error:
        log_error(f"❌ An error occurred while fetching sheet data: {error}")
        return [], []

def update_sheet_cell(sheets_service, spreadsheet_id: str, sheet_name: str, row_index: int, col_index: int, value: str) -> bool:
    """Updates a single cell in the Google Sheet and returns True on success."""
    range_name = f"{sheet_name}!{chr(ord('A') + col_index)}{row_index + 2}"
    body = {'values': [[value]]}
    try:
        sheets_service.spreadsheets().values().update(spreadsheetId=spreadsheet_id, range=range_name, valueInputOption='RAW', body=body).execute()
        print(f"✅ Sheet updated: Cell '{range_name}' set to '{value}'")
        return True
    except HttpError as error:
        log_error(f"❌ Error updating cell {range_name}: {error}")
        return False

def upload_file_to_drive(drive_service, file_path: str, folder_id: str, file_name: str) -> str | None:
    """Uploads a file to a specified Google Drive folder."""
    file_metadata = {'name': file_name, 'parents': [folder_id]}
    media = MediaFileUpload(file_path, mimetype='image/png')
    try:
        file = drive_service.files().create(
            body=file_metadata,
            media_body=media,
            fields='id',
            supportsAllDrives=True
        ).execute()
        print(f"✅ Uploaded '{file_name}' to Drive. File ID: {file.get('id')}")
        return file.get('id')
    except HttpError as error:
        log_error(f"❌ Error uploading '{file_name}' to Drive: {error}")
        return None

def generate_qr_code(data: str, file_path: str, size: int, corner_radius: int) -> bool:
    """Generates and saves a QR code image with rounded corners."""
    try:
        qr = qrcode.QRCode(version=1, error_correction=qrcode.constants.ERROR_CORRECT_L, box_size=10, border=2)
        qr.add_data(data)
        qr.make(fit=True)
        img = qr.make_image(fill_color="black", back_color="white").convert("RGBA").resize((size, size), Image.Resampling.LANCZOS)

        mask = Image.new('L', (size, size), 0)
        draw = ImageDraw.Draw(mask)
        draw.rounded_rectangle((0, 0, size, size), radius=corner_radius, fill=255)

        img.putalpha(mask)
        
        img.save(file_path)
        print(f"✅ QR code with rounded corners generated: {file_path}")
        return True
    except Exception as e:
        log_error(f"❌ Error generating QR code: {e}")
        return False

def create_ticket_image(output_path: str, name: str, qr_code_path: str) -> bool:
    """Creates a personalized ticket by overlaying a name and QR code onto a template."""
    try:
        # --- Download assets using paths from config.py ---
        local_template_path = download_file(config.TICKET_TEMPLATE_EMPTY_PATH, "temp/template.png")
        local_font_path = download_file(config.FONT_PATH, "temp/Inter-Bold.ttf")
        
        if not local_template_path or not local_font_path:
            log_error("Critical error: Font or template download failed. Cannot create ticket.")
            return False

        base_img = Image.open(local_template_path).convert("RGBA")
        draw = ImageDraw.Draw(base_img)

        try:
            # Use font size from config
            font = ImageFont.truetype(local_font_path, config.DETECTED_FONT_SIZE)
        except IOError:
            print(f"⚠️ Warning: Font from URL '{config.FONT_PATH}' could not be loaded. Using default font.")
            font = ImageFont.load_default()

        # --- Position and draw the name with the new style ---
        text_bbox = draw.textbbox((0, 0), name, font=font)
        text_width = text_bbox[2] - text_bbox[0]
        
        # Center the text horizontally
        text_x = (base_img.width - text_width) / 2
        # Use Y position from config
        text_y = config.DETECTED_NAME_TEXT_Y_POS
        draw.text((text_x, text_y), name, font=font, fill=config.TEXT_COLOR)

        # --- Position and paste the QR code ---
        qr_img = Image.open(qr_code_path).convert("RGBA")
        
        # Center the QR code horizontally
        qr_x = (base_img.width - qr_img.width) / 2
        # Use Y position from config
        qr_y = config.DETECTED_QR_CODE_Y_POS
        
        base_img.paste(qr_img, (int(qr_x), int(qr_y)), qr_img)

        base_img.save(output_path)
        print(f"✅ Personalized ticket created: {output_path}")
        return True
    except Exception as e:
        log_error(f"❌ Error creating ticket image: {e}")
        return False

def send_ticket_email(recipient_email: str, recipient_name: str, ticket_file_path: str) -> bool:
    """Sends an email with the generated ticket attached."""
    try:
        local_email_path = download_file(config.EMAIL_MESSAGE_PATH, "temp/email_message.html")
        if not local_email_path:
            return False

        with open(local_email_path, 'r', encoding='utf-8') as f:
            message_template = f.read()

        email_body = message_template.replace('{name}', recipient_name)
        msg = MIMEMultipart()
        msg['From'] = config.SENDER_EMAIL
        msg['To'] = recipient_email
        msg['Subject'] = "Your Event E-Ticket is Here!"
        # CORRECTED: Send email as HTML
        msg.attach(MIMEText(email_body, 'html'))

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
        log_error(f"❌ Error sending email to {recipient_email}: {e}")
        return False

def get_value_safe(row: list, col_idx: int) -> str:
    """Safely retrieves a value from a list (sheet row)."""
    return row[col_idx] if col_idx < len(row) else ''

###
# --- Main Execution Logic ---
###
def main():
    """Main function to run the ticketing automation loop."""
    print("--- 🚀 Event Ticketing Automation System ---")

    importlib.reload(config)

    def build_google_service(service_name, version):
        """Builds a Google service client using the service account from config."""
        if not config.GOOGLE_SA_JSON:
            log_error(f"⚠️ {service_name.capitalize()} service not configured. Check GOOGLE_SERVICE_ACCOUNT_JSON in .env")
            return None
        try:
            cred_dict = json.loads(config.GOOGLE_SA_JSON)
            scopes = ['https://www.googleapis.com/auth/spreadsheets', 'https://www.googleapis.com/auth/drive']
            creds = Credentials.from_service_account_info(cred_dict, scopes=scopes)
            service = build(service_name, version, credentials=creds)
            print(f"✅ Google {service_name.capitalize()} service initialized.")
            return service
        except Exception as e:
            log_error(f"❌ Error initializing {service_name.capitalize()} service: {e}")
            return None

    print("\n--- Initializing Google API services ---")
    sheets_service = build_google_service('sheets', 'v4')
    drive_service = build_google_service('drive', 'v3')

    if not sheets_service or not drive_service:
        log_error("❌ CRITICAL: Could not authenticate with Google APIs. Check your service account credentials.")
        exit(1)

    try:
        spreadsheet_id = get_spreadsheet_id_from_url(config.MAIN_SHEET_LINK)
        tickets_folder_id = get_folder_id_from_url(config.TICKETS_FOLDER_ID)
        qr_codes_folder_id = get_folder_id_from_url(config.QR_CODES_FOLDER_ID)
    except ValueError as e:
        log_error(f"❌ CRITICAL: {e}. Check your links in the .env file.")
        exit(1)

    print(f"\n--- 🔄 Starting continuous monitoring of '{config.MAIN_SHEET_NAME}' ---")
    print(f"Polling every {config.POLLING_INTERVAL_SECONDS} seconds. Press Ctrl+C to stop.")

    while True:
        try:
            print(f"\n[{time.strftime('%Y-%m-%d %H:%M:%S')}] Checking for new data...")
            headers, sheet_data = get_sheet_data(sheets_service, spreadsheet_id, config.DATA_RANGE_INITIAL)

            if not headers:
                time.sleep(config.POLLING_INTERVAL_SECONDS)
                continue

            required_columns = [config.COL_NAME, config.COL_EMAIL, config.COL_TICKET_STATUS, config.COL_EMAIL_STATUS, "Attendee ID"]
            for col_name in required_columns:
                if col_name not in headers:
                    log_error(f"❌ CRITICAL: Column '{col_name}' not found in sheet. Exiting.")
                    exit(1)
                COLUMN_INDICES[col_name] = headers.index(col_name)

            if not sheet_data:
                print("No data rows found. Waiting for new entries...")
                time.sleep(config.POLLING_INTERVAL_SECONDS)
                continue

            for i, row in enumerate(sheet_data):
                name = get_value_safe(row, COLUMN_INDICES[config.COL_NAME]).strip()
                email = get_value_safe(row, COLUMN_INDICES[config.COL_EMAIL]).strip()
                ticket_status = get_value_safe(row, COLUMN_INDICES[config.COL_TICKET_STATUS]).strip()

                if not name or not email: continue
                row_unique_id = f"{name}-{email}"
                if ticket_status == "Sent" or row_unique_id in PROCESSED_ENTRIES: continue

                print(f"\n✨ Processing new entry: Name='{name}', Email='{email}'")
                PROCESSED_ENTRIES.add(row_unique_id)
                os.makedirs("temp", exist_ok=True)

                update_sheet_cell(sheets_service, spreadsheet_id, config.MAIN_SHEET_NAME, i, COLUMN_INDICES[config.COL_TICKET_STATUS], "Generating...")

                attendee_id = None
                existing_attendee = mongo_client.find_attendee_by_email_and_name(email, name)

                if existing_attendee:
                    print(f"↪️ Found existing attendee in DB for email: {email} and name: {name}")
                    attendee_id = existing_attendee.get("attendee_id")
                    sheet_attendee_id = get_value_safe(row, COLUMN_INDICES["Attendee ID"]).strip()
                    if sheet_attendee_id != attendee_id:
                        print(f"⚠️ Sheet has incorrect ID. Updating sheet with correct ID: {attendee_id}")
                        update_sheet_cell(sheets_service, spreadsheet_id, config.MAIN_SHEET_NAME, i, COLUMN_INDICES["Attendee ID"], attendee_id)
                else:
                    print(f"➕ No existing attendee found for {email} and {name}. Creating new entry.")
                    attendee_id = str(uuid.uuid4())
                    id_update_success = update_sheet_cell(sheets_service, spreadsheet_id, config.MAIN_SHEET_NAME, i, COLUMN_INDICES["Attendee ID"], attendee_id)
                    if id_update_success:
                        try:
                            full_attendee_data = {header: get_value_safe(row, idx) for idx, header in enumerate(headers)}
                            full_attendee_data['attendee_id'] = attendee_id
                            full_attendee_data[config.COL_TICKET_STATUS] = 'Issued'
                            full_attendee_data[config.COL_EMAIL_STATUS] = 'Pending'
                            mongo_client.insert_full_attendee(full_attendee_data)
                            print(f"✅ New attendee '{name}' inserted into MongoDB with ID: {attendee_id}")
                        except Exception as e:
                            log_error(f"❌ Error inserting new attendee '{name}' into MongoDB: {e}")
                            update_sheet_cell(sheets_service, spreadsheet_id, config.MAIN_SHEET_NAME, i, COLUMN_INDICES[config.COL_TICKET_STATUS], "Failed (DB)")
                            continue
                    else:
                        log_error(f"❌ Aborting processing for '{name}' due to sheet update failure.")
                        update_sheet_cell(sheets_service, spreadsheet_id, config.MAIN_SHEET_NAME, i, COLUMN_INDICES[config.COL_TICKET_STATUS], "Failed (Sheet)")
                        continue

                qr_filename = f"{name.replace(' ', '_')}_QR.png"
                qr_path = os.path.join("temp", qr_filename)
                
                # Use QR code size from config and set a corner radius
                if not generate_qr_code(attendee_id, qr_path, config.DETECTED_QR_CODE_TARGET_SIZE, 30):
                    update_sheet_cell(sheets_service, spreadsheet_id, config.MAIN_SHEET_NAME, i, COLUMN_INDICES[config.COL_TICKET_STATUS], "Failed (QR)")
                    continue

                ticket_filename = f"{name.replace(' ', '_')}_Ticket.png"
                ticket_path = os.path.join("temp", ticket_filename)
                if not create_ticket_image(ticket_path, name, qr_path):
                    update_sheet_cell(sheets_service, spreadsheet_id, config.MAIN_SHEET_NAME, i, COLUMN_INDICES[config.COL_TICKET_STATUS], "Failed (Image)")
                    continue

                upload_file_to_drive(drive_service, qr_path, qr_codes_folder_id, qr_filename)
                upload_file_to_drive(drive_service, ticket_path, tickets_folder_id, ticket_filename)

                update_sheet_cell(sheets_service, spreadsheet_id, config.MAIN_SHEET_NAME, i, COLUMN_INDICES[config.COL_TICKET_STATUS], "Generated")
                mongo_client.update_attendee_field(attendee_id, config.COL_TICKET_STATUS, "Generated")
                update_sheet_cell(sheets_service, spreadsheet_id, config.MAIN_SHEET_NAME, i, COLUMN_INDICES[config.COL_EMAIL_STATUS], "Sending...")
                mongo_client.update_attendee_field(attendee_id, config.COL_EMAIL_STATUS, "Sending...")

                if send_ticket_email(email, name, ticket_path):
                    update_sheet_cell(sheets_service, spreadsheet_id, config.MAIN_SHEET_NAME, i, COLUMN_INDICES[config.COL_TICKET_STATUS], "Sent")
                    update_sheet_cell(sheets_service, spreadsheet_id, config.MAIN_SHEET_NAME, i, COLUMN_INDICES[config.COL_EMAIL_STATUS], "Sent")
                    mongo_client.update_attendee_field(attendee_id, config.COL_TICKET_STATUS, "Sent")
                    mongo_client.update_attendee_field(attendee_id, config.COL_EMAIL_STATUS, "Sent")
                else:
                    update_sheet_cell(sheets_service, spreadsheet_id, config.MAIN_SHEET_NAME, i, COLUMN_INDICES[config.COL_EMAIL_STATUS], "Failed (Email)")
                    mongo_client.update_attendee_field(attendee_id, config.COL_EMAIL_STATUS, "Failed (Email)")

                os.remove(qr_path)
                os.remove(ticket_path)
                print(f"✅ Cleaned up temp files for {name}.")

            time.sleep(config.POLLING_INTERVAL_SECONDS)

        except KeyboardInterrupt:
            print("\n🛑 Monitoring stopped by user. Exiting gracefully.")
            break
        except Exception as e:
            log_error(f"\n❌ An unexpected error occurred in the main loop: {e}")
            print("Restarting monitoring after a short delay...")
            time.sleep(config.POLLING_INTERVAL_SECONDS * 2)

# =============================================================================
#  Part 4: Script Execution
# =============================================================================

if __name__ == '__main__':
    # Start the web server in a background thread
    server_thread = threading.Thread(target=run_web_server, daemon=True)
    server_thread.start()

    # Run the main application loop
    main()
