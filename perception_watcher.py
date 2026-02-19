import os
import time
import shutil
import datetime
from watchdog.observers.polling import PollingObserver as Observer
from watchdog.events import FileSystemEventHandler

# Configuration
VAULT_DIR = "AI_Employee_Vault"
INBOX_DIR = os.path.join(VAULT_DIR, "Inbox")
NEEDS_ACTION_DIR = os.path.join(VAULT_DIR, "Needs_Action")
DASHBOARD_FILE = os.path.join(VAULT_DIR, "Dashboard.md")

DRY_RUN = os.environ.get("DRY_RUN", "false").lower() == "true"

class InboxHandler(FileSystemEventHandler):
    def on_created(self, event):
        if event.is_directory:
            return
        self.process_file_move(event.src_path)

    def process_file_move(self, source_path):
        filename = os.path.basename(source_path)
        if not filename.endswith(".md"):
            return

        print(f"Detected file: {filename}")

        dest_path = os.path.join(NEEDS_ACTION_DIR, filename)

        # Check if source exists (handle race conditions or stale events)
        if not os.path.exists(source_path):
            return

        if DRY_RUN:
            print(f"[DRY_RUN] Would move '{source_path}' to '{dest_path}'")
            print(f"[DRY_RUN] Would append log to '{DASHBOARD_FILE}'")
        else:
            try:
                # Move the file
                # Waiting briefly to ensure file handle is released if just created
                time.sleep(0.5)
                shutil.move(source_path, dest_path)
                print(f"Moved '{filename}' to Needs_Action")

                # Update Dashboard
                self.update_dashboard(filename)

            except Exception as e:
                print(f"Error processing file {filename}: {e}")

    def update_dashboard(self, filename):
        today = datetime.date.today().strftime("%Y-%m-%d")
        task_name = f"Process {filename}"
        entry = f"| {today} | {task_name} | Moved to Needs_Action | Pending |\n"

        try:
            with open(DASHBOARD_FILE, "a") as f:
                f.write(entry)
            print(f"Updated Dashboard with entry for {filename}")
        except Exception as e:
            print(f"Error updating dashboard: {e}")

def main():
    # Ensure directories exist
    if not os.path.exists(INBOX_DIR):
        print(f"Error: Inbox directory '{INBOX_DIR}' not found.")
        return
    if not os.path.exists(NEEDS_ACTION_DIR):
        os.makedirs(NEEDS_ACTION_DIR, exist_ok=True)

    event_handler = InboxHandler()
    observer = Observer()
    observer.schedule(event_handler, INBOX_DIR, recursive=False)

    print(f"Starting perception_watcher.py...")
    print(f"Monitoring {INBOX_DIR}")
    print(f"DRY_RUN mode: {DRY_RUN}")

    # Process existing files in Inbox
    print("Scanning for existing files in Inbox...")
    for filename in os.listdir(INBOX_DIR):
        if filename.endswith(".md"):
            filepath = os.path.join(INBOX_DIR, filename)
            # Create a mock event object to reuse logic
            # Use type('obj', (object,), {'src_path': filepath, 'is_directory': False}) if needed,
            # but simpler to refactor logic. Let's make a helper method.
            event_handler.process_file_move(filepath)

    observer.start()
    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        observer.stop()
    observer.join()

if __name__ == "__main__":
    main()
