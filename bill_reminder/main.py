import base64
import datetime
import email
import imaplib
import json
import os
import re

from dotenv import load_dotenv
from google.oauth2.service_account import Credentials
from googleapiclient.discovery import build
from llama_index.core import VectorStoreIndex, download_loader
from logger import logger


def create_query_engine(file_path: str):
    PDFReader = download_loader("PDFReader", custom_path="/tmp/llamahub_modules")
    loader = PDFReader()
    documents = loader.load_data(file=file_path)
    index = VectorStoreIndex.from_documents(documents)
    return index.as_query_engine()


def process_bill_document(file_path: str):
    query_engine = create_query_engine(file_path)

    # Query the due amount of the bill
    response = query_engine.query(
        "What is the due amount of the bill? If the text has word 'CR' in it, the due amount is 0"
    )
    due_amount_regex = re.findall(r"\d+\.\d+", str(response))
    due_amount = due_amount_regex[0] if due_amount_regex else None

    # Query the due date of the bill
    deadline = query_engine.query("When is the due date of the bill in DD/MM/YYYY?")
    # Regular expression pattern for dd/mm/yyyy format
    match = re.search(
        r"\b(?:0?[1-9]|[12][0-9]|3[01])/(?:0?[1-9]|1[0-2])/(?:19|20\d{2})\b",
        str(deadline),
    )
    due_date = match.group() if match else None

    return due_date, due_amount


def create_calendar_event(service_account_file, due_date, due_amount):
    # Load credentials from the service account file
    decoded_creds = base64.b64decode(service_account_file)
    json_creds = json.loads(decoded_creds.decode("utf-8"))
    creds = Credentials.from_service_account_info(
        json_creds, scopes=["https://www.googleapis.com/auth/calendar"]
    )

    # Build the service
    service = build("calendar", "v3", credentials=creds)

    # Convert due_date to a datetime object
    due_date_obj = datetime.datetime.strptime(due_date, "%d/%m/%Y")

    # Subtract one day from the due date
    event_start_date = due_date_obj - datetime.timedelta(days=1)

    event = {
        "summary": f"Pay utilities bill ${due_amount}",
        "description": f"Amount Due: ${due_amount}",
        "start": {
            "dateTime": event_start_date.isoformat(),
            "timeZone": "UTC",
        },
        "end": {
            "dateTime": (event_start_date + datetime.timedelta(hours=1)).isoformat(),
            "timeZone": "UTC",
        },
    }

    # Insert the event into the calendar
    event = service.events().insert(calendarId=GMAIL_USERNAME, body=event).execute()
    logger.info(f"Event created: {event.get('htmlLink')}")


def fetch_emails(username, password):
    logger.info("Fetching emails...")

    # Connect to the email server
    mail = imaplib.IMAP4_SSL("imap.gmail.com")
    mail.login(username, password)
    mail.select("inbox")

    # Search for emails from a specific sender
    sender_email = "customerservice@silverasset.com.au"
    _, data = mail.search(None, f'(FROM "{sender_email}")')

    # Fetch and parse the last 2 emails
    email_ids = data[0].split()[-2:]

    for email_id in email_ids:
        _, msg_data = mail.fetch(email_id, "(RFC822)")

        for response_part in msg_data:
            if not isinstance(response_part, tuple):
                continue

            msg = email.message_from_bytes(response_part[1])

            if not msg["Subject"].startswith("Important Notice: Your Silver Asset invoice"):
                continue

            for part in msg.walk():
                # Check if the content type is a PDF
                if part.get_content_type() == "application/pdf":
                    logger.info("Found PDF file")
                    # Extract PDF file name and content
                    pdf_filename = part.get_filename()
                    pdf_content = part.get_payload(decode=True)

                    # Create new folder and save the PDF to a file
                    if ENVIRONMENT == "production":
                        # Save the PDF to a file
                        file_path = f"/tmp/{pdf_filename}"
                        with open(file_path, "wb") as pdf_file:
                            pdf_file.write(pdf_content)
                        logger.info(f"Save the file to: {file_path}")
                    else:
                        os.makedirs("pdfs", exist_ok=True)
                        file_path = f"pdfs/{pdf_filename}"
                        with open(file_path, "wb") as pdf_file:
                            pdf_file.write(pdf_content)
                        logger.info(f"Save the file to: {file_path}")

                    due_date, due_amount = process_bill_document(file_path=file_path)

                    logger.info(f"Due date: {due_date} - Amount: ${due_amount}")

                    if due_amount and due_date:
                        create_calendar_event(
                            service_account_file=CREDENTIALS_JSON_FILE,
                            due_date=due_date,
                            due_amount=due_amount,
                        )

    # Close the connection
    mail.close()
    mail.logout()

    logger.info("Closing connection...")


def main():
    try:
        # Email credentials
        fetch_emails(GMAIL_USERNAME, GMAIL_APP_PASSWORD)
        logger.info("Finished fetching emails")
    except Exception as e:
        logger.error(f"Error fetching emails: {e}")
        exit(1)


if __name__ == "__main__":
    load_dotenv()

    try:
        GMAIL_USERNAME = os.environ["GMAIL_USERNAME"]
        GMAIL_APP_PASSWORD = os.environ["GMAIL_APP_PASSWORD"]
        ENVIRONMENT = os.environ["ENVIRONMENT"]
        CREDENTIALS_JSON_FILE = os.environ["CREDENTIALS_JSON_FILE"]
    except KeyError as e:
        logger.error(f"Missing environment variable: {e}")
        exit(1)

    main()
