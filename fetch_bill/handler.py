import imaplib
import email
import boto3
import json
from botocore.exceptions import NoCredentialsError
from common.helpers import get_secret, BUCKET_NAME, REGION_NAME


def send_event_to_eventbridge(object_key: str):
    # Create an EventBridge client
    client = boto3.client("events", region_name=REGION_NAME)

    # Define your event
    event = {
        "EventBusName": "start-process-bill",
        "Source": "my.bill.query",
        "DetailType": "TriggerProcessBill",
        "Detail": json.dumps({"file_key": object_key}),
    }

    # Put the event
    response = client.put_events(Entries=[event])

    return response


def upload_to_s3(file_name, bucket, object_name=None):
    """
    Upload a file to an S3 bucket and return the object key

    :param file_name: File to upload
    :param bucket: Bucket to upload to
    :param object_name: S3 object name. If not specified, file_name is used
    :return: Object key if file was uploaded, else None
    """

    # If S3 object_name was not specified, use file_name
    if object_name is None:
        object_name = file_name

    # Upload the file
    s3_client = boto3.client("s3")
    try:
        s3_client.upload_file(file_name, bucket, object_name)
        return object_name
    except NoCredentialsError:
        print("Credentials not available")
        return None


def fetch_emails(username, password):
    print("Fetching emails...")

    # Connect to the email server
    mail = imaplib.IMAP4_SSL("imap.gmail.com")
    mail.login(username, password)
    mail.select("inbox")

    # Search for emails from a specific sender
    sender_email = "customerservice@silverasset.com.au"
    _, data = mail.search(None, f'(FROM "{sender_email}")')

    # Fetch and parse the emails
    last_email_id = data[0].split()[-1]
    _, msg_data = mail.fetch(last_email_id, "(RFC822)")

    for response_part in msg_data:
        if not isinstance(response_part, tuple):
            continue

        msg = email.message_from_bytes(response_part[1])

        if not msg["Subject"].startswith("Important Notice: Your Silver Asset invoice"):
            continue

        for part in msg.walk():
            # Check if the content type is a PDF
            if part.get_content_type() == "application/pdf":
                print("Found PDF file")
                # Extract PDF file name and content
                pdf_filename = part.get_filename()
                pdf_content = part.get_payload(decode=True)

                # Save the PDF to a file
                with open(f"/tmp/{pdf_filename}", "wb") as pdf_file:
                    pdf_file.write(pdf_content)
                print(f"Downloaded: /tmp/{pdf_filename}")

                # Upload the PDF to S3
                object_key = upload_to_s3(f"/tmp/{pdf_filename}", BUCKET_NAME, pdf_filename)
                if object_key:
                    print(f"Uploaded: {object_key}")
                    send_event_to_eventbridge(object_key)
                    print(f"Sent event to EventBridge: {object_key}")
                else:
                    print(f"Error uploading: {object_key}")

    # Close the connection
    mail.close()
    mail.logout()

    print("Closing connection...")


def main(event, context):
    try:
        credentials = get_secret()

        # Email credentials
        username = credentials["GMAIL_USERNAME"]
        password = credentials["GMAIL_APP_PASSWORD"]
        print(f"Username: {username}")
        print(f"Password: {password}")
        fetch_emails(username, password)

        return {"statusCode": 200, "body": "Emails fetched successfully"}
    except Exception as e:
        print(e)
        return {"statusCode": 500, "body": "Error fetching emails"}
