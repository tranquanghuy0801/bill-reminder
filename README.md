# Bill Reminder

## Description

This is a simple bill reminder app that allows users to fetch their utility bills from their email and add create reminders for them in their phone so that they never miss a bill payment again.

## Architecture

![Architecture of the application](images/aws_architecture.png)

# Installation

1. Create a secret in AWS Secrets Manager and the following keys into the secret:

```
OPENAI_API_KEY=***
IFTTT_WEBHOOK_KEY=***
GMAIL_USERNAME=***
GMAIL_APP_PASSWORD=***
```

2. Create .env file at the root of the project and add the following keys:

```
ACCOUNT_ID=***
REGION_NAME=***
BUCKET_NAME=***
SECRET_NAME=<secret name created above>
```

3. Deploy the application using the following command:

```bash
serverless deploy
```

4. Destroy all the resources created by the application using the following command:

```bash
serverless remove
```
