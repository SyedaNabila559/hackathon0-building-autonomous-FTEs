import imaplib
import email
from email.header import decode_header
import os
import time
import psycopg2
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Configuration
GMAIL_USER = os.getenv("GMAIL_USER")
GMAIL_PASS = os.getenv("GMAIL_PASS")
DATABASE_URL = os.getenv("DATABASE_URL")
POLL_INTERVAL = 10  # seconds

def clean_subject(subject):
    return "".join(c for c in subject if c.isalnum() or c in (' ', '_', '-')).strip()

def process_email(msg):
    # Decode subject
    subject, encoding = decode_header(msg["Subject"])[0]
    if isinstance(subject, bytes):
        subject = subject.decode(encoding if encoding else "utf-8")

    sender = msg.get("From")

    # Get email body
    body = ""
    if msg.is_multipart():
        for part in msg.walk():
            content_type = part.get_content_type()
            content_disposition = str(part.get("Content-Disposition"))

            if "attachment" not in content_disposition:
                if content_type == "text/plain":
                    try:
                        body = part.get_payload(decode=True).decode()
                    except:
                        pass
    else:
        try:
            body = msg.get_payload(decode=True).decode()
        except:
            pass

    # Combine subject and body for the db content
    full_content = f"Subject: {subject}\n\n{body}"

    try:
        conn = psycopg2.connect(DATABASE_URL)
        cur = conn.cursor()

        insert_query = """
        INSERT INTO ai_tasks (source, sender, content, status)
        VALUES (%s, %s, %s, 'inbox')
        """

        cur.execute(insert_query, ('gmail', sender, full_content))
        conn.commit()

        cur.close()
        conn.close()

        print("LIVE: New Email Captured and saved to database!")
        return True

    except Exception as e:
        print(f"Error saving to database: {e}")
        return False

def main():
    if not GMAIL_USER or not GMAIL_PASS:
        print("Error: GMAIL_USER or GMAIL_PASS not found in .env file.")
        return

    if not DATABASE_URL:
        print("Error: DATABASE_URL not found in .env file.")
        return

    print("Starting gmail_connector.py...")
    print(f"Monitoring Gmail Inbox for {GMAIL_USER} every {POLL_INTERVAL} seconds...")

    try:
        while True:
            try:
                # Connect to Gmail
                mail = imaplib.IMAP4_SSL("imap.gmail.com")
                mail.login(GMAIL_USER, GMAIL_PASS)

                # Select Inbox
                mail.select("inbox")

                # Search for unseen emails
                status, messages = mail.search(None, 'UNSEEN')

                if status == "OK":
                    email_ids = messages[0].split()

                    if email_ids:
                        for email_id in email_ids:
                            # Fetch the email
                            status, msg_data = mail.fetch(email_id, "(RFC822)")

                            for response_part in msg_data:
                                if isinstance(response_part, tuple):
                                    msg = email.message_from_bytes(response_part[1])
                                    process_email(msg)

                            # Mark as seen (happens automatically with fetch but being explicit is good)
                            # mail.store(email_id, '+FLAGS', '\\Seen')

                mail.close()
                mail.logout()

            except Exception as e:
                print(f"Error checking email: {e}")

            time.sleep(POLL_INTERVAL)

    except KeyboardInterrupt:
        print("Stopping gmail_connector.py...")

if __name__ == "__main__":
    main()
