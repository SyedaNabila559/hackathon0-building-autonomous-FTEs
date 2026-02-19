"""
Action Processor - Odoo ERP Version
====================================
Processes AI tasks stored in Odoo ERP.

Replaces the previous Neon PostgreSQL version.
"""

import os
import time
from dotenv import load_dotenv
from openai import OpenAI

# Load environment variables
load_dotenv()

# Configuration
POLL_INTERVAL = 30  # seconds

# Initialize OpenAI Client
api_key = os.getenv("OPENAI_API_KEY")
client = OpenAI(api_key=api_key) if api_key else None


def generate_draft(content):
    """Generate AI draft using OpenAI."""
    if not client:
        print("Error: OpenAI API key is missing. Skipping AI generation.")
        return None

    try:
        response = client.chat.completions.create(
            model="gpt-4o",
            messages=[
                {"role": "system", "content": """You are a world-class Executive Assistant. Your goal is to take messy, informal WhatsApp messages and turn them into high-quality professional drafts.

If the user asks for an email, write a clear, concise, and polite email draft.

Always provide a Subject Line.

Use a tone that is helpful but professional.

If the request is a task (like 'remind me to buy milk'), format it as a clean To-Do item. Output should be in Markdown format."""},
                {"role": "user", "content": content}
            ]
        )
        return response.choices[0].message.content
    except Exception as e:
        print(f"Error generating draft with OpenAI: {e}")
        return None


def process_tasks():
    """Process pending tasks from Odoo ERP."""
    try:
        from odoo_connector import OdooTaskProcessor

        processor = OdooTaskProcessor()
        tasks = processor.get_pending_tasks()

        if tasks:
            print(f"Found {len(tasks)} tasks pending action.")
            for task in tasks:
                task_id = task.get('id')
                memo = task.get('memo', '')

                # Extract content from memo
                content_start = memo.find('Content:')
                if content_start != -1:
                    content = memo[content_start + 8:].strip()
                else:
                    content = memo

                print(f"Processing task ID: {task_id}")

                draft_content = generate_draft(content)

                if draft_content:
                    # Update task with draft and new status
                    success = processor.update_task_with_draft(task_id, draft_content)
                    if success:
                        print(f"Task {task_id} processed and moved to pending_approval.")
                    else:
                        print(f"Failed to update task {task_id} in Odoo.")
                else:
                    print(f"Failed to generate draft for task ID: {task_id}")
        else:
            print("No pending tasks found.")

    except ImportError:
        print("Error: odoo_connector module not found.")
        print("Make sure odoo_connector.py is in the same directory.")
    except Exception as e:
        print(f"Error processing tasks: {e}")


def main():
    print(f"Starting action_processor.py (Odoo ERP Version)...")
    print(f"Poll Interval: {POLL_INTERVAL} seconds")
    print(f"Odoo Instance: {os.getenv('ODOO_URL', 'https://aiagent21.odoo.com')}")

    if not client:
        print("WARNING: OpenAI API Key not found. AI features will fail.")

    # Verify Odoo connection on startup
    try:
        from odoo_connector import OdooConnector
        connector = OdooConnector()
        if connector.authenticate():
            print("Successfully connected to Odoo ERP!")
        else:
            print("WARNING: Could not authenticate with Odoo. Check credentials.")
    except Exception as e:
        print(f"WARNING: Odoo connection test failed: {e}")

    try:
        while True:
            process_tasks()
            time.sleep(POLL_INTERVAL)

    except KeyboardInterrupt:
        print("Stopping action_processor.py...")


if __name__ == "__main__":
    main()
