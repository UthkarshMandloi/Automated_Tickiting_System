# **Automated Event Ticketing System**

This Python-based solution provides an end-to-end automation for event ticketing and attendance management, leveraging Google Workspace services. It streamlines the process from attendee registration to personalized ticket delivery and automated attendance marking.

## **✨ Features**

* **Google Sheets Integration:** Reads attendee registration data directly from a specified Google Sheet.  
* **Dynamic Ticket Generation:** Creates personalized e-tickets (PNG images) for each attendee.  
* **Automated QR Code Generation:** Embeds unique QR codes on tickets, linking to an automated attendance system.  
* **Google Drive Archiving:** Automatically uploads generated QR codes and tickets to designated Google Drive folders.  
* **Personalized Email Delivery:** Sends e-tickets to attendees via email with a customizable message.  
* **Automated Attendance Tracking:** QR codes trigger a Google Apps Script Web App for seamless, no-click attendance submission to a Google Form.  
* **Continuous Monitoring:** Runs as a long-running script, polling the Google Sheet for new registrations at set intervals.  
* **Smart Template Detection:** Automatically detects optimal placement (Y-coordinates, font size, QR size) for names and QR codes on a provided ticket template using OCR, ensuring consistent and professional-looking tickets without manual pixel adjustments.  
* **Status Tracking:** Updates registration statuses (e.g., "Generating...", "Generated", "Sent", "Failed") directly in the Google Sheet.  
* **Secure Configuration:** Keeps sensitive information (like API keys and app passwords) out of version control.

## **🚀 How It Works**

1. **Registration:** Attendees register via a Google Form linked to a Google Sheet (your main registration sheet).  
2. **Monitoring:** The Python script continuously monitors this Google Sheet for new entries.  
3. **Ticket Processing:** For each new, unprocessed entry:  
   * It generates a unique URL that, when accessed, triggers a Google Apps Script Web App.  
   * A QR code is created from this unique URL.  
   * The attendee's name and the QR code are overlaid onto a blank ticket template (using coordinates automatically detected during setup).  
   * The generated QR image and personalized ticket image are uploaded to Google Drive.  
   * The ticket is attached to a personalized email and sent to the attendee.  
   * The status in the Google Sheet is updated accordingly.  
4. **Attendance:** When an attendee scans their ticket's QR code at the event, the Apps Script Web App is invoked, which then programmatically submits their attendance to a separate Google Form (linked to your attendance sheet) without requiring any manual clicks.  
5. **Custom Confirmation:** After submission (either via QR scan or direct form fill), a custom HTML confirmation page is displayed instead of the default Google Forms page.

## **📂 Project Structure**

The project directory is organized as follows:

Automated\_Tickiting\_System/  
├── venv/                       \# Python virtual environment (ignored by Git)  
├── credentials.json            \# Google API OAuth Client ID/Secret (ignored by Git)  
├── token.json                  \# Google API access/refresh token (ignored by Git)  
├── config.py                   \# Your actual configuration file with sensitive data (ignored by Git)  
├── config\_example.py           \# Template for config.py (committed to Git)  
├── main\_app.py                 \# Main application logic and continuous monitoring  
├── google\_auth.py              \# Handles Google API authentication  
├── ticket\_template\_empty.png   \# Blank ticket design template (committed to Git)  
├── ticket\_template\_with\_tags.png \# Template with "{name}" and "{QR}" tags for auto-detection (committed to Git)  
├── email\_message.txt           \# Customizable email body template (committed to Git)  
├── requirements.txt            \# Python dependencies list (committed to Git)  
├── LICENSE                     \# Project license (MIT License) (committed to Git)  
└── README.md                   \# This README file

## **📋 Prerequisites**

Before you begin, ensure you have the following:

* **Python 3.8+:** [Download & Install Python](https://www.python.org/downloads/)  
* **Git:** [Download & Install Git](https://git-scm.com/downloads)  
* **A Google Account:** With access to Google Sheets, Google Drive, and Google Forms.  
* **Google Cloud Project:** Configured for API access.  
* **Tesseract OCR Engine:** A system-level installation is required for automated template detection.

### **Tesseract OCR Installation**

* **Windows:**  
  1. Download the installer from [Tesseract-OCR GitHub Wiki](https://tesseract-ocr.github.io/tessdoc/Downloads.html).  
  2. Run the installer. **Crucially, check "Add Tesseract to your system PATH" during installation.**  
  3. Restart your computer or open a new terminal/PowerShell window after installation.  
* **macOS (using Homebrew):**  
  1. Open Terminal.  
  2. brew install tesseract  
* **Linux (Debian/Ubuntu):**  
  1. Open Terminal.  
  2. sudo apt update  
  3. sudo apt install tesseract-ocr libtesseract-dev

## **⚙️ Setup & Installation**

Follow these steps to get your system up and running:

### **1\. Clone the Repository**

git clone https://github.com/UthkarshMandloi/Automated\_Tickiting\_System.git  
cd Automated\_Tickiting\_System

### **2\. Set Up Python Virtual Environment**

It's highly recommended to use a virtual environment to manage project dependencies.

python \-m venv venv  
\# On Windows:  
.\\venv\\Scripts\\activate  
\# On macOS/Linux:  
source venv/bin/activate

### **3\. Install Python Dependencies**

Install all required Python libraries within your active virtual environment.

pip install \-r requirements.txt  
\# If requirements.txt is missing or outdated, use:  
\# pip install google-api-python-client google-auth-oauthlib google-auth-httplib2 Pillow qrcode pytesseract

### **4\. Google Cloud Project Configuration**

You need to set up your Google Cloud Project to allow your Python script to interact with Google APIs.

* Go to [Google Cloud Console](https://console.cloud.google.com/) and log in with your Google Account.  
* **Create a New Project** (e.g., "Event Ticketing Automation") or select an existing one.

#### **a. Enable APIs**

* Navigate to **"APIs & Services" \> "Enabled APIs & Services"**.  
* Click **"+ ENABLE APIS AND SERVICES"**.  
* Search for and enable:  
  * Google Sheets API  
  * Google Drive API

#### **b. Configure OAuth Consent Screen**

This defines what users see when authorizing your app. For personal use, keep it in "Testing" mode.

* Navigate to **"APIs & Services" \> "OAuth consent screen"**.  
* **User type:** Select **"External"** and click "CREATE".  
* **App information:**  
  * **App name:** Provide a descriptive name (e.g., "Event Ticket Generator").  
  * **User support email:** Your email address.  
  * **Developer contact information:** Your email address.  
* **Scopes:**  
  * Click **"ADD OR REMOVE SCOPES"**.  
  * Search for and add the following scopes:  
    * .../auth/spreadsheets (for Google Sheets API)  
    * .../auth/drive (for Google Drive API \- broad access needed for uploads)  
  * Click "UPDATE" or "ADD TO YOUR APP".  
  * **Justification:** For the .../auth/drive scope (which is "restricted"), provide a brief justification like: "This desktop application automates event ticketing. The Drive scope is required to save generated QR codes and personalized e-tickets (PNG files) into specific Google Drive folders designated by the user. A more limited scope is insufficient as the application needs to create new files in user-specified locations."  
  * For "Demo video", you can use a placeholder like https://www.youtube.com/watch?v=dQw4w9WgXcQ for testing if required.  
* **Test users:** Under the "Test users" section, click **"+ Add users"** and add your Google Account email address.  
* **Publishing status:** Ensure it remains **"Testing"**. Do NOT click "Publish App" or "Prepare for Verification" unless you intend to go through Google's full app verification process for public use.

#### **c. Create OAuth Client ID**

This generates the credentials.json file your script uses for authentication.

* Navigate to **"APIs & Services" \> "Credentials"**.  
* Click **"+ CREATE CREDENTIALS" \> "OAuth client ID"**.  
* **Application type:** Select **"Desktop app"**.  
* **Name:** Give it a descriptive name (e.g., "Desktop Client for Ticketing").  
* Click "CREATE".  
* A dialog will appear with your Client ID and Client Secret. Click **"DOWNLOAD JSON"**.  
* Rename the downloaded file to credentials.json and place it in the root of your Automated\_Tickiting\_System project directory.  
  (Note: This file is ignored by Git for security reasons and should never be committed to your repository.)

### **5\. Generate a Gmail App Password**

This is required for your script to send emails via Gmail's SMTP server.

* Go to your Google Account Security settings: [https://myaccount.google.com/security](https://myaccount.google.com/security)  
* Under "How you sign in to Google," select **"App passwords"**. (If you don't see this option, you might need to enable 2-Step Verification first).  
* Follow the instructions to generate a new app password. Select "Mail" for the app and "Other" or "Windows Computer" for the device.  
* A 16-character code will be generated. Copy this code. This is your SENDER\_APP\_PASSWORD.  
  (Note: This password is a secret and should never be committed to your repository.)

### **6\. Google Forms Setup**

You'll need two Google Forms: one for registration (linked to your main sheet) and one for attendance.

#### **a. Main Registration Google Sheet**

* Ensure your main registration Google Form is linked to a Google Sheet.  
* Verify the exact column headers in this sheet for:  
  * Name (Attendee's full name)  
  * Email (Attendee's email for ticket delivery)  
  * Ticket Status (Manually add this empty column)  
  * Email Status (Manually add this empty column)  
  * Timestamp (Usually the first column, automatically added by Google Forms)

#### **b. Attendance Google Form & Apps Script Web App**

This form will be used for attendance marking, triggered by QR code scans.

1. **Create a new Google Form** for attendance (e.g., "Event Attendance Form").  
2. Add two "Short answer" questions to this form:  
   * One with the exact title: Name (or Attendee Name \- ensure it matches NAME\_QUESTION\_TITLE in Code.gs).  
   * One with the exact title: Status (or Present \- ensure it matches STATUS\_QUESTION\_TITLE in Code.gs).  
3. **Get the Form ID:** Open this attendance Google Form. The ID is the long string in the URL: https://docs.google.com/forms/d/e/YOUR\_ATTENDANCE\_FORM\_ID\_HERE/viewform. Copy YOUR\_ATTENDANCE\_FORM\_ID\_HERE.  
4. **Create Google Apps Script:**  
   * While in your attendance Google Form, click **"Extensions" \> "Apps Script"**.  
   * In the Code.gs file, **replace its entire content** with the code provided in Code.gs (see below in this README).  
   * **Update the configuration variables** at the top of Code.gs:  
     * ATTENDANCE\_FORM\_ID: Paste the ID you just copied.  
     * NAME\_QUESTION\_TITLE: Ensure it exactly matches your form's Name question title.  
     * STATUS\_QUESTION\_TITLE: Ensure it exactly matches your form's Status question title.  
   * **Save the script.**  
5. **Deploy Apps Script as Web App:**  
   * In the Apps Script editor, click **"Deploy" \> "New deployment"**.  
   * Click the **"Select type"** (gear icon) and choose **"Web app"**.  
   * **Description:** "Attendance Automation Web App".  
   * **Execute as:** Select **"Me (your\_google\_account@gmail.com)"**.  
   * **Who has access:** Select **"Anyone"**.  
   * Click **"Deploy"**.  
   * **Authorize access** if prompted (choose your Google account, click "Advanced" if needed, then "Go to \[Project Name\] (unsafe)" and "Allow").  
   * After deployment, copy the **"Web app URL"**. This is your PREFILLED\_FORM\_BASE\_LINK. It will look like https://script.google.com/macros/s/AKfycb.../exec.  
6. **Configure Google Form Presentation:**  
   * Open your Attendance Google Form.  
   * Go to **"Settings" \> "Presentation"**.  
   * For "Confirmation message", select **"Redirect to URL"**.  
   * **Paste your Web app URL** (e.g., https://script.google.com/macros/s/AKfycb.../exec) into the URL field. (Do NOT include ?name=... parameters here).  
   * **Toggle OFF** the option **"Show link to submit another response"**.

### **7\. Prepare Template Images**

You need two image files for ticket generation:

* **ticket\_template\_with\_tags.png**: Your base ticket design **with the literal text {name} and {QR} clearly printed** on it where you want the dynamic content to appear. Use a simple, high-contrast font for these tags. Place this file in your project root.  
* **ticket\_template\_empty.png**: The **exact same design as ticket\_template\_with\_tags.png, but with the areas where {name} and {QR} were completely blank** (no text, just background). Place this file in your project root.

### **8\. Create Email Message Template**

* Create a text file named email\_message.txt in your project root.  
* Write your custom email body. You can use {name} as a placeholder for the attendee's name.  
  **Example email\_message.txt content:**  
  Dear {name},

  Thank you for registering for Tech Unleash 3.0\!

  Your personalized e-ticket is attached to this email. Please present it at the event for entry.

  We look forward to seeing you there\!

  Best regards,  
  The Tech Unleash Team

### **9\. Configure config.py**

* In your project root, you will find config\_example.py.  
* **Make a copy of config\_example.py and rename it to config.py**.  
* **Open config.py** and fill in all the YOUR\_...\_HERE placeholders with the information you gathered in the previous steps:  
  * MAIN\_SHEET\_LINK  
  * MAIN\_SHEET\_NAME  
  * TICKETS\_FOLDER\_ID (Create a folder in Drive, copy its ID from the URL)  
  * QR\_CODES\_FOLDER\_ID (Create a folder in Drive, copy its ID from the URL)  
  * PREFILLED\_FORM\_BASE\_LINK (The Apps Script Web App URL with ?name={name\_param}\&status={status\_param})  
  * SENDER\_EMAIL  
  * SENDER\_APP\_PASSWORD (The 16-character App Password you generated)  
  * TESSERACT\_CMD\_PATH (Set this to the full path of tesseract.exe if it's not in your system PATH, e.g., r'C:\\Program Files\\Tesseract-OCR\\tesseract.exe')  
* **Ensure SHOULD\_DETECT\_COORDINATES\_ON\_STARTUP \= True** for the first run to enable auto-detection of image coordinates. The script will automatically set this to False after successful detection.

## **▶️ Usage**

1. **Activate your virtual environment:**  
   \# On Windows:  
   .\\venv\\Scripts\\activate  
   \# On macOS/Linux:  
   source venv/bin/activate

2. **Run the main application script:**  
   python main\_app.py

The script will:

* On the first run (or if SHOULD\_DETECT\_COORDINATES\_ON\_STARTUP is True):  
  * Attempt to detect {name} and {QR} positions on ticket\_template\_with\_tags.png using Tesseract OCR.  
  * Automatically update config.py with the detected coordinates and set SHOULD\_DETECT\_COORDINATES\_ON\_STARTUP \= False.  
* Initialize Google API services ( Sheets & Drive). The first time, it will open a browser for you to authorize access.  
* Start continuously monitoring your Google Sheet for new registrations.  
* For each new entry, it will generate a ticket, upload assets, send an email, and update statuses in the sheet.

To stop the script, press Ctrl+C in the terminal window.

## **⚠️ Troubleshooting**

* **AttributeError: module 'config' has no attribute '...'**: Ensure you have copied config\_example.py to config.py and filled in all required values. Also, verify that the column names in config.py exactly match your Google Sheet headers (case-sensitive).  
* **pytesseract.pytesseract.TesseractNotFoundError**: Tesseract OCR engine is not found.  
  * Verify Tesseract is installed on your system (see Prerequisites).  
  * Ensure tesseract.exe (Windows) or tesseract (macOS/Linux) is in your system's PATH.  
  * Alternatively, set the full path to tesseract.exe in config.TESSERACT\_CMD\_PATH.  
* **Detection Warning: '{QR}' tag not found...**: Tesseract couldn't read the tag from your image.  
  * Open ticket\_template\_with\_tags.png in an image editor.  
  * Ensure the text is **EXACTLY {QR}** (case-sensitive).  
  * Make it **large, clear, and high-contrast** (e.g., black text on white background).  
  * Ensure no other elements obscure it.  
* **HttpError 403: Insufficient Permission (for Drive uploads)**: Your authenticated Google account lacks permission for the target Drive folders.  
  * Ensure the Google account used for authentication (the one linked to token.json) has **"Editor" access** to both TICKETS\_FOLDER\_ID and QR\_CODES\_FOLDER\_ID in Google Drive.  
  * Delete token.json and re-run python google\_auth.py to force a fresh authorization, ensuring you grant all requested permissions in the browser.  
* **Error: Missing required parameters. (from Apps Script Web App)**: The Apps Script is not receiving name or status via the URL.  
  * Verify PREFILLED\_FORM\_BASE\_LINK in config.py is the correct Apps Script Web App URL and ends with ?name={name\_param}\&status={status\_param}.  
  * Check Apps Script "Executions" logs (console.log(e.parameter)) to see what it actually receives.  
* **Emails not sending**:  
  * Ensure SENDER\_EMAIL and SENDER\_APP\_PASSWORD in config.py are correct.  
  * Verify you are using an **App Password** for SENDER\_APP\_PASSWORD, not your regular Gmail password.  
  * Check your Gmail account's security settings for any blocked sign-in attempts.

## **🤝 Contributing**

Contributions are welcome\! If you have suggestions for improvements or find bugs, please open an issue or submit a pull request.

## **📄 License**

This project is open-source and available under the [MIT License](https://opensource.org/licenses/MIT). *(You can create a LICENSE file in your repo with the MIT license text)*