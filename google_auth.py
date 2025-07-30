# This script handles authentication with Google APIs (Sheets and Drive).
# It uses OAuth 2.0 to securely obtain and refresh access tokens,
# storing them in 'token.json' to avoid re-authentication on every run.

import os.path
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError # Import HttpError for consistent error handling

import config # Import configuration for general settings like sheet link for test

def get_spreadsheet_id_from_url(url):
    """
    (Helper function copied from main_app.py for local test use in google_auth.py)
    Extracts the Google Spreadsheet ID from its URL.
    Args:
        url (str): The full URL of the Google Sheet.
    Returns:
        str: The extracted Spreadsheet ID.
    Raises:
        ValueError: If the URL format is invalid.
    """
    try:
        return url.split('/d/')[1].split('/')[0]
    except IndexError:
        raise ValueError(f"Invalid Google Sheet URL: '{url}'. Could not extract Spreadsheet ID.")


def authenticate_google_api(api_name, api_version, scopes, token_filename='token.json', credentials_filename='credentials.json'):
    """
    Authenticates with Google API using OAuth 2.0 and returns an API service object.
    It manages token storage in 'token.json'.

    Args:
        api_name (str): The name of the API (e.g., 'sheets', 'drive').
        api_version (str): The version of the API (e.g., 'v4', 'v3').
        scopes (list): A list of required OAuth scopes for the API.
        token_filename (str): The name of the file to store the user's access token.
        credentials_filename (str): The name of the JSON file downloaded from Google Cloud Console.

    Returns:
        googleapiclient.discovery.Resource: An authenticated API service object.
    """
    creds = None
    # Load credentials from token.json if it exists and is valid/not expired.
    if os.path.exists(token_filename):
        creds = Credentials.from_authorized_user_file(token_filename, scopes)

    # If no valid credentials, or they are expired and cannot be refreshed,
    # initiate the OAuth flow to prompt user for authorization.
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request()) # Attempt to refresh the token using refresh_token
        else:
            # Start the OAuth flow; this will open a browser window for user login/authorization.
            flow = InstalledAppFlow.from_client_secrets_file(
                credentials_filename, scopes)
            creds = flow.run_local_server(port=0) # port=0 picks a random available port
        
        # Save the new/refreshed credentials to token.json for future runs.
        with open(token_filename, 'w') as token:
            token.write(creds.to_json())

    # Build and return the authenticated API service object.
    service = build(api_name, api_version, credentials=creds)
    return service

if __name__ == '__main__':
    # This block is for directly testing the authentication setup.
    # It will authenticate for both Sheets and Drive and run basic tests.
    
    # Define API scopes directly in google_auth.py as they are constant permissions.
    SHEETS_SCOPE = 'https://www.googleapis.com/auth/spreadsheets'
    DRIVE_SCOPE = 'https://www.googleapis.com/auth/drive' # The broad Drive scope
    
    # Combine all scopes needed for the application for a single authorization.
    COMBINED_SCOPES_FOR_TEST = [SHEETS_SCOPE, DRIVE_SCOPE] # Changed to a list directly

    print("Authenticating for Google Sheets and Drive APIs with combined scopes...")
    try:
        # Authenticate using the combined scopes. The token.json will contain permissions for both.
        creds_for_all_services = None
        token_filename = 'token.json'
        credentials_filename = 'credentials.json'

        # This part of the code is duplicated from authenticate_google_api for explicit
        # control within __main__ for initial setup/testing.
        if os.path.exists(token_filename):
            creds_for_all_services = Credentials.from_authorized_user_file(token_filename, COMBINED_SCOPES_FOR_TEST)

        if not creds_for_all_services or not creds_for_all_services.valid:
            if creds_for_all_services and creds_for_all_services.expired and creds_for_all_services.refresh_token:
                creds_for_all_services.refresh(Request())
            else:
                flow = InstalledAppFlow.from_client_secrets_file(
                    credentials_filename, COMBINED_SCOPES_FOR_TEST)
                creds_for_all_services = flow.run_local_server(port=0)
            
            with open(token_filename, 'w') as token:
                token.write(creds_for_all_services.to_json())

        # Build service objects using the unified credentials
        sheets_service = build('sheets', 'v4', credentials=creds_for_all_services)
        drive_service = build('drive', 'v3', credentials=creds_for_all_services)
        
        print("Google Sheets and Drive APIs authenticated successfully with combined scopes.")

        # --- Test the services immediately after authentication ---
        print("\nTesting Sheets Service:")
        try:
            # Test Sheets access by trying to read a small range from your configured sheet
            # Uses config.MAIN_SHEET_LINK and config.MAIN_SHEET_NAME for the test
            sheets_test_result = sheets_service.spreadsheets().values().get(
                spreadsheetId=get_spreadsheet_id_from_url(config.MAIN_SHEET_LINK), 
                range=f"{config.MAIN_SHEET_NAME}!A1:E5"
            ).execute()
            print("Sheets service test successful. Data sample:", sheets_test_result.get('values', []))
        except HttpError as e:
            print(f"Sheets service test failed: {e}. Please ensure Sheets API is enabled and you have access.")
        except ValueError as e:
            print(f"Sheets service test setup error: {e}. Check MAIN_SHEET_LINK in config.py.")


        print("\nTesting Drive Service (listing files):")
        try:
            # Test Drive access by trying to list some files from your Drive
            drive_test_results = drive_service.files().list(
                pageSize=5, fields="nextPageToken, files(id, name)").execute()
            items = drive_test_results.get('files', [])
            if items:
                print("Drive service test successful. First 5 files:")
                for item in items:
                    print(f"  - {item['name']} ({item['id']})")
            else:
                print("Drive service test successful. No files found in root (or none returned by pageSize).")
        except HttpError as e:
            print(f"Drive service test failed: {e}. Please ensure Drive API is enabled and you have access.")

    except Exception as e:
        print(f"Authentication process failed: {e}")
        print("Please ensure you have 'credentials.json' in your project directory and ALL required APIs are enabled in Google Cloud Console.")