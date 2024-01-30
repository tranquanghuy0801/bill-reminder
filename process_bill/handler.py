from llama_index import VectorStoreIndex, download_loader
import os
import boto3
import json
import re
import requests
from common.helpers import get_secret, BUCKET_NAME


def create_reminder_icloud(due_date, amount_due, webhook_key):
    if not due_date or not amount_due:
        print("No due date or amount due provided")
        return

    try:
        # Login credentials
        url = "https://maker.ifttt.com/trigger/create_reminder/with/key/{your_key}".format(
            your_key=webhook_key
        )

        # IFTTT Maker Webhooks payload
        payload = {"value1": amount_due, "value2": due_date}

        # Send POST request to IFTTT Maker Webhooks
        response = requests.post(url, data=payload)

        # Print response status code and content
        print("Response status code:", response.status_code)
        print("Response content:", response.content)
    except Exception as e:
        print("Couldn't create reminder:", e)


def create_query_engine(document_key):
    PDFReader = download_loader("PDFReader", custom_path="/tmp/llamahub_modules")
    loader = PDFReader()
    documents = loader.load_data(file=f"/tmp/{document_key}")
    index = VectorStoreIndex.from_documents(documents)
    return index.as_query_engine()


def main(event, context):
    print("Received event:", json.dumps(event))
    try:
        credentials = get_secret()
        os.environ["OPENAI_API_KEY"] = credentials["OPENAI_API_KEY"]

        # Specify the bucket name and file key
        file_key = event["detail"]["file_key"]

        # Fetch the file from S3
        s3_client = boto3.client("s3")
        s3_client.download_file(BUCKET_NAME, file_key, f"/tmp/{file_key}")

        # Process the PDF file as needed
        print("Start processing...")

        query_engine = create_query_engine(file_key)

        # Query the due amount of the bill
        response = query_engine.query("What is the due amount of the bill?")
        due_amount_regex = re.findall(r"\d+\.\d+", str(response))
        due_amount = due_amount_regex[0] if due_amount_regex else None
        print(due_amount)

        # Query the due date of the bill
        deadline = query_engine.query("When is the due date of the bill in DD/MM/YYYY?")
        # Regular expression pattern for dd/mm/yyyy format
        match = re.search(
            r"\b(?:0?[1-9]|[12][0-9]|3[01])/(?:0?[1-9]|1[0-2])/(?:19|20\d{2})\b", str(deadline)
        )
        due_date = match.group() if match else None
        print(due_date)

        print("PDF file processed successfully")

        # Create a reminder on iCloud
        webhook_key = credentials["IFTTT_WEBHOOK_KEY"]
        create_reminder_icloud(due_date, due_amount, webhook_key)

        return {"statusCode": 200, "body": json.dumps({"output": str(response)})}

    except Exception as e:
        print(e)
        return {"statusCode": 500, "body": "Error processing the PDF file"}
