"""
Gmail Watcher for Obsidian Vault Integration

Scans for unread 'Important' emails and creates Markdown summaries
in Vault_Template/Needs_Action/ for Obsidian visibility.

Setup:
    1. Enable Gmail API in Google Cloud Console
    2. Create OAuth 2.0 credentials (Desktop app)
    3. Download credentials.json to this directory
    4. Run script - it will open browser for authentication

Usage:
    python gmail_watcher.py [--interval SECONDS] [--vault-dir PATH]

Requirements:
    pip install google-api-python-client google-auth-httplib2 google-auth-oauthlib
"""

import os
import sys
import time
import logging
import argparse
import hashlib
import pickle
import base64
import re
from datetime import datetime
from pathlib import Path
from typing import Optional, List, Dict, Any
from email.utils import parsedate_to_datetime

from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError


# Configuration
SCOPES = ['https://www.googleapis.com/auth/gmail.readonly']
DEFAULT_CHECK_INTERVAL = 300  # 5 minutes

BASE_DIR = Path(__file__).resolve().parent

DEFAULT_VAULT_DIR = BASE_DIR / "vault" / "Needs_Action"
LOG_DIR = BASE_DIR / "logs"
CREDENTIALS_FILE = BASE_DIR / "credentials.json"
TOKEN_FILE = BASE_DIR / "token.pickle"
PROCESSED_IDS_FILE = BASE_DIR / ".processed_email_ids"



def setup_logging() -> logging.Logger:
    """Configure logging for long-running operations."""
    LOG_DIR.mkdir(parents=True, exist_ok=True)

    logger = logging.getLogger("gmail_watcher")
    logger.setLevel(logging.DEBUG)

    # File handler
    log_file = LOG_DIR / f"gmail_watcher_{datetime.now().strftime('%Y-%m-%d')}.log"
    file_handler = logging.FileHandler(log_file, encoding='utf-8')
    file_handler.setLevel(logging.DEBUG)
    file_formatter = logging.Formatter(
        '%(asctime)s | %(levelname)-8s | %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )
    file_handler.setFormatter(file_formatter)

    # Console handler
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(logging.INFO)
    console_formatter = logging.Formatter('%(asctime)s | %(levelname)s | %(message)s')
    console_handler.setFormatter(console_formatter)

    logger.addHandler(file_handler)
    logger.addHandler(console_handler)

    return logger


logger = setup_logging()


class GmailAuthenticator:
    """Handle Gmail API authentication."""

    def __init__(self, credentials_file: Path, token_file: Path):
        self.credentials_file = credentials_file
        self.token_file = token_file
        self.creds: Optional[Credentials] = None

    def authenticate(self) -> Credentials:
        """Authenticate with Gmail API using OAuth2."""
        # Load existing token
        if self.token_file.exists():
            logger.debug("Loading existing token...")
            with open(self.token_file, 'rb') as f:
                self.creds = pickle.load(f)

        # Refresh or create new credentials
        if not self.creds or not self.creds.valid:
            if self.creds and self.creds.expired and self.creds.refresh_token:
                logger.info("Refreshing expired token...")
                try:
                    self.creds.refresh(Request())
                except Exception as e:
                    logger.warning(f"Token refresh failed: {e}")
                    self.creds = None

            if not self.creds:
                if not self.credentials_file.exists():
                    logger.error(f"Credentials file not found: {self.credentials_file}")
                    logger.error("Download OAuth credentials from Google Cloud Console")
                    raise FileNotFoundError(f"Missing {self.credentials_file}")

                logger.info("Starting OAuth flow - browser will open...")
                flow = InstalledAppFlow.from_client_secrets_file(
                    str(self.credentials_file), SCOPES
                )
                self.creds = flow.run_local_server(port=0)

            # Save token for future use
            with open(self.token_file, 'wb') as f:
                pickle.dump(self.creds, f)
            logger.info("Token saved successfully")

        return self.creds


class ProcessedEmailTracker:
    """Track which emails have already been processed."""

    def __init__(self, storage_file: Path):
        self.storage_file = storage_file
        self.processed_ids: set = self._load()

    def _load(self) -> set:
        """Load processed IDs from file."""
        if self.storage_file.exists():
            try:
                with open(self.storage_file, 'r') as f:
                    return set(line.strip() for line in f if line.strip())
            except Exception as e:
                logger.warning(f"Error loading processed IDs: {e}")
        return set()

    def _save(self):
        """Save processed IDs to file."""
        try:
            with open(self.storage_file, 'w') as f:
                f.write('\n'.join(self.processed_ids))
        except Exception as e:
            logger.error(f"Error saving processed IDs: {e}")

    def is_processed(self, email_id: str) -> bool:
        """Check if email has been processed."""
        return email_id in self.processed_ids

    def mark_processed(self, email_id: str):
        """Mark email as processed."""
        self.processed_ids.add(email_id)
        self._save()

    def cleanup_old(self, max_entries: int = 10000):
        """Keep only the most recent entries."""
        if len(self.processed_ids) > max_entries:
            # Convert to list, keep last max_entries
            id_list = list(self.processed_ids)
            self.processed_ids = set(id_list[-max_entries:])
            self._save()
            logger.info(f"Cleaned up processed IDs: kept {max_entries} entries")


class GmailWatcher:
    """Watch Gmail for unread important emails."""

    def __init__(self, vault_dir: Path, credentials_file: Path, token_file: Path):
        self.vault_dir = vault_dir
        self.vault_dir.mkdir(parents=True, exist_ok=True)

        self.authenticator = GmailAuthenticator(credentials_file, token_file)
        self.tracker = ProcessedEmailTracker(PROCESSED_IDS_FILE)
        self.service = None

    def connect(self):
        """Establish connection to Gmail API."""
        logger.info("Connecting to Gmail API...")
        creds = self.authenticator.authenticate()
        self.service = build('gmail', 'v1', credentials=creds)
        logger.info("Connected to Gmail API successfully")

    def _get_header(self, headers: List[Dict], name: str) -> str:
        """Extract header value by name."""
        for header in headers:
            if header.get('name', '').lower() == name.lower():
                return header.get('value', '')
        return ''

    def _clean_html(self, text: str) -> str:
        """Remove HTML tags from text."""
        clean = re.sub(r'<[^>]+>', '', text)
        clean = re.sub(r'\s+', ' ', clean)
        return clean.strip()

    def _get_email_body(self, payload: Dict) -> str:
        """Extract email body from payload."""
        body = ""

        if 'body' in payload and payload['body'].get('data'):
            body = base64.urlsafe_b64decode(payload['body']['data']).decode('utf-8', errors='replace')

        if 'parts' in payload:
            for part in payload['parts']:
                mime_type = part.get('mimeType', '')
                if mime_type == 'text/plain' and part.get('body', {}).get('data'):
                    body = base64.urlsafe_b64decode(part['body']['data']).decode('utf-8', errors='replace')
                    break
                elif mime_type == 'text/html' and part.get('body', {}).get('data') and not body:
                    html = base64.urlsafe_b64decode(part['body']['data']).decode('utf-8', errors='replace')
                    body = self._clean_html(html)

        return body[:1000] if body else ""  # Limit body length

    def _sanitize_filename(self, text: str, max_length: int = 50) -> str:
        """Create safe filename from text."""
        safe = re.sub(r'[<>:"/\\|?*]', '', text)
        safe = re.sub(r'\s+', '_', safe)
        return safe[:max_length]

    def _determine_priority(self, subject: str, sender: str, labels: List[str]) -> str:
        """Determine email priority based on content and labels."""
        subject_lower = subject.lower()

        # High priority indicators
        high_priority_keywords = ['urgent', 'asap', 'important', 'action required',
                                   'immediate', 'critical', 'deadline']
        if any(kw in subject_lower for kw in high_priority_keywords):
            return 'high'

        if 'IMPORTANT' in labels:
            return 'high'

        if 'STARRED' in labels:
            return 'high'

        return 'medium'

    def fetch_important_unread(self, max_results: int = 20) -> List[Dict[str, Any]]:
        """Fetch unread emails from Important category."""
        try:
            # Query for unread important emails
            query = 'is:unread is:important'

            results = self.service.users().messages().list(
                userId='me',
                q=query,
                maxResults=max_results
            ).execute()

            messages = results.get('messages', [])
            logger.info(f"Found {len(messages)} unread important emails")

            emails = []
            for msg in messages:
                if self.tracker.is_processed(msg['id']):
                    logger.debug(f"Skipping already processed email: {msg['id']}")
                    continue

                try:
                    # Fetch full message details
                    full_msg = self.service.users().messages().get(
                        userId='me',
                        id=msg['id'],
                        format='full'
                    ).execute()

                    headers = full_msg.get('payload', {}).get('headers', [])

                    email_data = {
                        'id': msg['id'],
                        'thread_id': full_msg.get('threadId', ''),
                        'subject': self._get_header(headers, 'Subject') or '(No Subject)',
                        'sender': self._get_header(headers, 'From'),
                        'date': self._get_header(headers, 'Date'),
                        'snippet': full_msg.get('snippet', ''),
                        'labels': full_msg.get('labelIds', []),
                        'body_preview': self._get_email_body(full_msg.get('payload', {}))
                    }

                    emails.append(email_data)
                    logger.debug(f"Fetched email: {email_data['subject'][:50]}")

                except HttpError as e:
                    logger.error(f"Error fetching message {msg['id']}: {e}")
                    continue

            return emails

        except HttpError as e:
            logger.error(f"Error fetching email list: {e}")
            return []

    def create_markdown_summary(self, email: Dict[str, Any]) -> Optional[Path]:
        """Create markdown summary for email in vault."""
        try:
            timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            date_slug = datetime.now().strftime('%Y%m%d_%H%M%S')

            # Parse email date
            email_date = email['date']
            try:
                parsed_date = parsedate_to_datetime(email_date)
                email_date_formatted = parsed_date.strftime('%Y-%m-%d %H:%M')
            except Exception:
                email_date_formatted = email_date

            # Extract sender name and email
            sender = email['sender']
            sender_match = re.match(r'(.+?)\s*<(.+?)>', sender)
            if sender_match:
                sender_name = sender_match.group(1).strip().strip('"')
                sender_email = sender_match.group(2)
            else:
                sender_name = sender
                sender_email = sender

            # Determine priority
            priority = self._determine_priority(
                email['subject'],
                sender,
                email['labels']
            )

            # Create markdown content
            md_content = f"""---
created: {timestamp}
source: gmail_watcher
type: email
priority: {priority}
status: pending
email_id: "{email['id']}"
thread_id: "{email['thread_id']}"
---

# Email: {email['subject']}

## Metadata

| Property | Value |
|----------|-------|
| **From** | {sender_name} |
| **Email** | `{sender_email}` |
| **Date** | {email_date_formatted} |
| **Priority** | {priority} |

## Snippet

> {email['snippet']}

## Preview

{email['body_preview'][:500] if email['body_preview'] else '*No preview available*'}

## Actions Required

- [ ] Read full email in Gmail
- [ ] Determine required response
- [ ] Process or archive

## Response Draft

*Draft your response here if needed:*

```
[Your response]
```

## Notes

*Add any notes or context here.*

---
*Auto-generated by gmail_watcher.py*
*Email ID: {email['id']}*
"""

            # Create filename
            safe_subject = self._sanitize_filename(email['subject'])
            short_id = hashlib.md5(email['id'].encode()).hexdigest()[:6]
            md_filename = f"{date_slug}_email_{safe_subject}_{short_id}.md"
            md_path = self.vault_dir / md_filename

            with open(md_path, 'w', encoding='utf-8') as f:
                f.write(md_content)

            # Mark as processed
            self.tracker.mark_processed(email['id'])

            logger.info(f"Created summary: {md_filename}")
            return md_path

        except Exception as e:
            logger.error(f"Error creating markdown for email {email['id']}: {e}")
            return None

    def check_emails(self) -> int:
        """Check for new emails and create summaries. Returns count of new emails."""
        emails = self.fetch_important_unread()

        created_count = 0
        for email in emails:
            if self.create_markdown_summary(email):
                created_count += 1

        return created_count

    def run(self, interval: int = DEFAULT_CHECK_INTERVAL):
        """Run the watcher in a loop."""
        logger.info("=" * 60)
        logger.info("Gmail Watcher Starting")
        logger.info("=" * 60)
        logger.info(f"Output to: {self.vault_dir}")
        logger.info(f"Check interval: {interval} seconds")
        logger.info("=" * 60)

        self.connect()

        logger.info("Starting email watch loop. Press Ctrl+C to stop.")

        try:
            while True:
                try:
                    logger.info("Checking for new important emails...")
                    count = self.check_emails()

                    if count > 0:
                        logger.info(f"Processed {count} new email(s)")
                    else:
                        logger.info("No new emails to process")

                    # Periodic cleanup
                    self.tracker.cleanup_old()

                except HttpError as e:
                    if e.resp.status == 401:
                        logger.warning("Auth token expired, reconnecting...")
                        self.connect()
                    else:
                        logger.error(f"API error: {e}")
                except Exception as e:
                    logger.error(f"Error during check: {e}")

                logger.debug(f"Sleeping for {interval} seconds...")
                time.sleep(interval)

        except KeyboardInterrupt:
            logger.info("Shutdown requested...")

        logger.info("Gmail watcher stopped.")


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description="Watch Gmail for important unread emails and create Obsidian summaries"
    )
    parser.add_argument(
        "--interval",
        type=int,
        default=DEFAULT_CHECK_INTERVAL,
        help=f"Check interval in seconds (default: {DEFAULT_CHECK_INTERVAL})"
    )
    parser.add_argument(
        "--vault-dir",
        type=Path,
        default=DEFAULT_VAULT_DIR,
        help=f"Vault Needs_Action directory (default: {DEFAULT_VAULT_DIR})"
    )
    parser.add_argument(
        "--credentials",
        type=Path,
        default=CREDENTIALS_FILE,
        help=f"Google OAuth credentials file (default: {CREDENTIALS_FILE})"
    )
    parser.add_argument(
        "--once",
        action="store_true",
        help="Run once and exit (don't loop)"
    )

    args = parser.parse_args()

    watcher = GmailWatcher(
        vault_dir=args.vault_dir,
        credentials_file=args.credentials,
        token_file=TOKEN_FILE
    )

    if args.once:
        watcher.connect()
        count = watcher.check_emails()
        logger.info(f"Single run complete. Processed {count} email(s).")
    else:
        watcher.run(interval=args.interval)


if __name__ == "__main__":
    main()
