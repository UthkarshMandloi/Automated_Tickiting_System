# =============================================================================
# Automated Placeholder Detection & Configuration Utility
#
# This script uses OCR to:
# 1. Find the exact location of '{name}' and '{QR}' tags in a template image.
# 2. Calculate the optimal Y-positions, font size, and QR code size.
# 3. Automatically update the 'config.py' file with these new values.
# 4. Sets 'SHOULD_DETECT_COORDINATES_ON_STARTUP' to False in 'config.py'.
#
# Run this script once to set up your ticket layout automatically.
# =============================================================================

import os
from PIL import Image
import config  # Import config to read paths and write back new values

try:
    import pytesseract
except ImportError:
    print("❌ CRITICAL: 'pytesseract' library not found.")
    print("Please install it by running: pip install pytesseract")
    exit(1)

def detect_and_update_config():
    """
    Detects placeholders using OCR and programmatically updates the config.py file.
    """
    print(f"🔎 Scanning '{config.TICKET_TEMPLATE_WITH_TAGS_PATH}' for placeholders...")

    # --- Step 1: Validate paths and Tesseract installation ---
    if not os.path.exists(config.TICKET_TEMPLATE_WITH_TAGS_PATH):
        print(f"❌ ERROR: Template image not found at '{config.TICKET_TEMPLATE_WITH_TAGS_PATH}'.")
        return False

    if config.TESSERACT_CMD_PATH:
        pytesseract.pytesseract.tesseract_cmd = config.TESSERACT_CMD_PATH

    try:
        # Test Tesseract by getting its version string
        pytesseract.get_tesseract_version()
    except pytesseract.TesseractNotFoundError:
        print("\n❌ ERROR: Tesseract OCR engine not found.")
        print("Please ensure Tesseract is installed and the path in 'config.py' is correct.")
        return False

    # --- Step 2: Perform OCR to find placeholders ---
    try:
        img = Image.open(config.TICKET_TEMPLATE_WITH_TAGS_PATH)
        data = pytesseract.image_to_data(img, output_type=pytesseract.Output.DICT)

        name_coords = None
        qr_coords = None

        for i in range(len(data['text'])):
            # We look for an exact, case-sensitive match for better accuracy
            text = data['text'][i].strip()
            if text == "{name}":
                x, y, w, h = data['left'][i], data['top'][i], data['width'][i], data['height'][i]
                name_coords = {'y': y, 'height': h}
                print(f"✅ Detected '{{name}}' at Y-position: {y}, Height: {h}")
            elif text == "{QR}":
                x, y, w, h = data['left'][i], data['top'][i], data['width'][i], data['height'][i]
                qr_coords = {'y': y, 'width': w}
                print(f"✅ Detected '{{QR}}' at Y-position: {y}, Width: {w}")

        if not name_coords or not qr_coords:
            print("\n❌ ERROR: Failed to detect both '{name}' and '{QR}' placeholders.")
            print("   - Ensure they are present and clearly visible in the image.")
            print("   - The text must be exactly '{name}' and '{QR}' (case-sensitive).")
            return False

        # --- Step 3: Calculate new configuration values ---
        new_name_y = name_coords['y']
        new_font_size = int(name_coords['height'] * 1.0) # Scale font size based on tag height
        new_qr_y = qr_coords['y']
        new_qr_size = int(qr_coords['width'] * 1.1) # Scale QR size slightly larger than tag width

        print("\n✨ Calculated new settings:")
        print(f"   - Name Y-Position: {new_name_y}")
        print(f"   - Font Size: {new_font_size}")
        print(f"   - QR Y-Position: {new_qr_y}")
        print(f"   - QR Size: {new_qr_size}")

    except Exception as e:
        print(f"An unexpected error occurred during image processing: {e}")
        return False

    # --- Step 4: Read config.py and update it programmatically ---
    try:
        with open('config.py', 'r') as f:
            config_lines = f.readlines()

        new_config_lines = []
        for line in config_lines:
            if line.strip().startswith('DETECTED_NAME_TEXT_Y_POS'):
                new_config_lines.append(f"DETECTED_NAME_TEXT_Y_POS = {new_name_y}\n")
            elif line.strip().startswith('DETECTED_FONT_SIZE'):
                new_config_lines.append(f"DETECTED_FONT_SIZE = {new_font_size}\n")
            elif line.strip().startswith('DETECTED_QR_CODE_Y_POS'):
                new_config_lines.append(f"DETECTED_QR_CODE_Y_POS = {new_qr_y}\n")
            elif line.strip().startswith('DETECTED_QR_CODE_TARGET_SIZE'):
                new_config_lines.append(f"DETECTED_QR_CODE_TARGET_SIZE = {new_qr_size}\n")
            elif line.strip().startswith('SHOULD_DETECT_COORDINATES_ON_STARTUP'):
                # Set the flag to False to prevent re-detection on every run
                new_config_lines.append("SHOULD_DETECT_COORDINATES_ON_STARTUP = False\n")
            else:
                new_config_lines.append(line)

        with open('config.py', 'w') as f:
            f.writelines(new_config_lines)

        print("\n✅✅✅ Success! Your 'config.py' file has been automatically updated.")
        return True

    except Exception as e:
        print(f"\n❌ ERROR: Failed to write the new settings to 'config.py': {e}")
        return False


if __name__ == '__main__':
    print("--- 🚀 Starting Automated Placeholder Detection & Config Update ---")
    detect_and_update_config()
    print("\n--- Script Finished ---")