import os
import pickle
import base64
from googleapiclient.discovery import build
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request
from email.mime.text import MIMEText

# If modifying these SCOPES, delete the file token.pickle.
SCOPES = ['https://www.googleapis.com/auth/gmail.send']

def get_service():
    creds = None
    # The file token.pickle stores the user's access and refresh tokens, and is
    # created automatically when the authorization flow completes for the first
    # time.
    if os.path.exists('token.pickle'):
        with open('token.pickle', 'rb') as token:
            creds = pickle.load(token)

    # If there are no (valid) credentials available, let the user log in.
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            flow = InstalledAppFlow.from_client_secrets_file(
                'credentials.json', SCOPES)
            creds = flow.run_local_server(port=0, open_browser=False)

        # Save the credentials for the next run
        with open('token.pickle', 'wb') as token:
            pickle.dump(creds, token)

    service = build('gmail', 'v1', credentials=creds)
    return service

def create_message(sender, to, subject, message_text):
    message = MIMEText(message_text)
    message['to'] = to
    message['from'] = sender
    message['subject'] = subject
    raw_message = base64.urlsafe_b64encode(message.as_string().encode("utf-8"))
    return {
        'raw': raw_message.decode("utf-8")
    }

def send_message(service, user_id, message):
    try:
        message = service.users().messages().send(userId=user_id, body=message).execute()
        print('Message Id: %s' % message['id'])
        return message
    except Exception as e:
        print('An error occurred: %s' % e)
        return None

def main():
    service = get_service()

    # You can update the sender if known, otherwise "me" works for the authenticated user
    sender = "me"
    to = "ak3723808@gmail.com"
    subject = "Digital FTE Test Email"
    content = "Hello! This is a test email from your Digital FTE to verify that I can send messages."

    print(f"Sending email to {to}...")
    message = create_message(sender, to, subject, content)
    send_message(service, sender, message)
    print("Email sent successfully.")

if __name__ == '__main__':
    main()
