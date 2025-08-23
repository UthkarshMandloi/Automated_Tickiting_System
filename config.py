# =============================================================================
# Event Ticketing System - Configuration File
#
# This file loads all settings from the .env file and centralizes them
# for the rest of the application.
# =============================================================================
import os
from dotenv import load_dotenv

# Load variables from the .env file into the environment
load_dotenv()

# --- Google Services Configuration ---
GOOGLE_SA_JSON = os.getenv("GOOGLE_SERVICE_ACCOUNT_JSON")

# --- 1. Google Services Configuration ---
MAIN_SHEET_LINK = os.getenv("MAIN_SHEET_LINK")
MAIN_SHEET_NAME = os.getenv("MAIN_SHEET_NAME", "Form_Responses_1")
DATA_RANGE_INITIAL = f"{MAIN_SHEET_NAME}!A:Z"
TICKETS_FOLDER_ID = os.getenv("TICKETS_FOLDER_ID")
QR_CODES_FOLDER_ID = os.getenv("QR_CODES_FOLDER_ID")

# --- 2. Email Configuration ---
SENDER_EMAIL = os.getenv("SENDER_EMAIL")
SENDER_APP_PASSWORD = os.getenv("SENDER_APP_PASSWORD")

# --- 3. File Paths & Assets ---
TICKET_TEMPLATE_EMPTY_PATH = os.getenv("TICKET_TEMPLATE_EMPTY_PATH")
EMAIL_MESSAGE_PATH = os.getenv("EMAIL_MESSAGE_PATH")
FONT_PATH = os.getenv("FONT_PATH")
TESSERACT_CMD_PATH = os.getenv("TESSERACT_CMD_PATH") # Optional

# --- 4. Automation & Sheet Mapping ---
POLLING_INTERVAL_SECONDS = int(os.getenv("POLLING_INTERVAL_SECONDS", 30))
COL_NAME = os.getenv("COL_NAME", "Name")
COL_EMAIL = os.getenv("COL_EMAIL", "Email")
COL_TICKET_STATUS = os.getenv("COL_TICKET_STATUS", "Ticket Status")
COL_EMAIL_STATUS = os.getenv("COL_EMAIL_STATUS", "Email Status")

# Add this line to your config.py
TEXT_COLOR = (17, 17, 17) # This corresponds to the color #111111

# In your config.py or Render Environment Variables
FONT_PATH = "https://drive.google.com/file/d/1nbAEoAi7vaGJf4nkx6gjaxwKplzKWFhd/view?usp=sharing"
DETECTED_FONT_SIZE = 55
DETECTED_QR_CODE_TARGET_SIZE = 300

# In your config.py or Render Environment Variables
DETECTED_NAME_TEXT_X_POS = 51  # The X-coordinate for the name
DETECTED_NAME_TEXT_Y_POS = 887 # The Y-coordinate for the name
DETECTED_QR_CODE_X_POS = 184   # The X-coordinate for the QR code
DETECTED_QR_CODE_Y_POS = 394   # The Y-coordinate for the QR code

# --- 6. MongoDB Configuration ---
MONGO_URI = os.getenv("MONGO_URI")
MONGO_DB_NAME = os.getenv("MONGO_DB_NAME")
MONGO_COLLECTION_NAME = os.getenv("MONGO_COLLECTION_NAME")
