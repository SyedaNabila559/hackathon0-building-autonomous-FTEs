import os
import time
import random
import datetime

# Configuration
VAULT_DIR = "AI_Employee_Vault"
INBOX_DIR = os.path.join(VAULT_DIR, "Inbox")
POLL_INTERVAL = 60  # seconds

# Ensure inbox exists
os.makedirs(INBOX_DIR, exist_ok=True)

SCENARIOS = [
    {
        "type": "WhatsApp",
        "sender": "Client",
        "content": "I need the pricing for the new software."
    },
    {
        "type": "Email",
        "sender": "Manager",
        "content": "Please draft a summary of the latest AI trends."
    },
    {
        "type": "Slack",
        "sender": "Dev Team",
        "content": "The API documentation needs to be updated for the new endpoints."
    },
    {
        "type": "Email",
        "sender": "HR",
        "content": "Reminder: Complete the quarterly survey by Friday."
    },
    {
        "type": "WhatsApp",
        "sender": "Client B",
        "content": "Can we reschedule our meeting to next Tuesday?"
    }
]

def create_message():
    scenario = random.choice(SCENARIOS)
    timestamp = datetime.datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
    filename = f"Message_{timestamp}.md"
    filepath = os.path.join(INBOX_DIR, filename)

    content = f"""# Incoming Message

**Type:** {scenario['type']}
**Sender:** {scenario['sender']}
**Received:** {datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")}

## Content
{scenario['content']}
"""

    with open(filepath, 'w') as f:
        f.write(content)

    print(f"[{datetime.datetime.now().strftime('%H:%M:%S')}] Received new message: {filename}")

def main():
    print("Starting communication_hub.py...")
    print(f"Monitoring for simulated messages every {POLL_INTERVAL} seconds.")

    try:
        while True:
            create_message()
            time.sleep(POLL_INTERVAL)

    except KeyboardInterrupt:
        print("Stopping communication_hub.py...")

if __name__ == "__main__":
    main()
