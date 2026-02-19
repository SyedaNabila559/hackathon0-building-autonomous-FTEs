"""
Ralph-Loop Agent - Background automation loop for task processing.

This agent:
1. Monitors /Needs_Action for new tasks from watchers
2. Uses Claude API to draft Plans and LinkedIn Posts in /Pending_Approval
3. Triggers linkedin_publisher.py when files are moved to /Approved
4. Moves completed tasks to /Done
5. Logs every step to activity.log
"""

import os
import re
import sys
import json
import time
import shutil
import subprocess
import traceback
from pathlib import Path
from datetime import datetime

# =============================================================================
# ROBUST ENVIRONMENT LOADING
# =============================================================================

def load_env_with_validation(env_path: str = None) -> dict:
    """
    Load .env file with robust error handling.
    Returns dict of loaded variables and logs any parsing errors.
    """
    if env_path is None:
        env_path = Path(__file__).parent / ".env"
    else:
        env_path = Path(env_path)

    loaded_vars = {}
    errors = []

    if not env_path.exists():
        return {"loaded": {}, "errors": [f".env file not found at {env_path}"]}

    try:
        with open(env_path, "r", encoding="utf-8") as f:
            lines = f.readlines()

        for line_num, line in enumerate(lines, start=1):
            line = line.strip()

            # Skip empty lines and comments
            if not line or line.startswith("#"):
                continue

            # Parse key=value
            if "=" in line:
                try:
                    key, value = line.split("=", 1)
                    key = key.strip()
                    value = value.strip()

                    # Remove quotes if present
                    if (value.startswith('"') and value.endswith('"')) or \
                       (value.startswith("'") and value.endswith("'")):
                        value = value[1:-1]

                    os.environ[key] = value
                    loaded_vars[key] = value

                except Exception as e:
                    errors.append(f"Line {line_num}: Failed to parse '{line[:50]}...' - {str(e)}")
            else:
                errors.append(f"Line {line_num}: Invalid format (no '=' found): '{line[:50]}...'")

    except Exception as e:
        errors.append(f"Failed to read .env file: {str(e)}")

    return {"loaded": loaded_vars, "errors": errors}


# Load environment with validation
ENV_RESULT = load_env_with_validation()

# =============================================================================
# DIRECTORY CONFIGURATION - Aligned with Obsidian Vault Structure
# =============================================================================

VAULT_BASE = Path("D:/zerohakathon/Vault_Template")
NEEDS_ACTION_DIR = VAULT_BASE / "Needs_Action"
IN_PROGRESS_DIR = VAULT_BASE / "In_Progress"
PENDING_APPROVAL_DIR = VAULT_BASE / "Pending_Approval"  # Claude's drafts go here
APPROVED_DIR = VAULT_BASE / "Approved"                   # Final execution trigger
DONE_DIR = VAULT_BASE / "Done"
LOGS_DIR = VAULT_BASE / "Logs"
LOG_FILE = LOGS_DIR / "activity.log"

# All required directories
ALL_VAULT_DIRS = [
    NEEDS_ACTION_DIR,
    IN_PROGRESS_DIR,
    PENDING_APPROVAL_DIR,
    APPROVED_DIR,
    DONE_DIR,
    LOGS_DIR
]

# Ensure all directories exist
for dir_path in ALL_VAULT_DIRS:
    dir_path.mkdir(parents=True, exist_ok=True)

# =============================================================================
# LOGGING
# =============================================================================

def log_activity(message: str, level: str = "INFO"):
    """Log activity to the activity log file with timestamp."""
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    log_entry = f"[{timestamp}] [{level}] [RALPH-LOOP] {message}\n"

    try:
        LOG_FILE.parent.mkdir(parents=True, exist_ok=True)
        with open(LOG_FILE, "a", encoding="utf-8") as f:
            f.write(log_entry)
    except Exception as e:
        print(f"[ERROR] Failed to write to log: {e}")

    # Also print to console
    print(f"[{level}] {message}")


# Log any .env parsing errors
if ENV_RESULT["errors"]:
    for error in ENV_RESULT["errors"]:
        log_activity(f".env parsing error: {error}", "ERROR")

# =============================================================================
# ENVIRONMENT VARIABLES - Using standard names
# =============================================================================

# Gmail credentials (standard names)
GMAIL_CLIENT_ID = os.getenv("GMAIL_CLIENT_ID")
GMAIL_CLIENT_SECRET = os.getenv("GMAIL_CLIENT_SECRET")
GMAIL_USER = os.getenv("GMAIL_USER")

# LinkedIn credentials
LINKEDIN_ACCESS_TOKEN = os.getenv("LINKEDIN_ACCESS_TOKEN")
LINKEDIN_PAGE_ID = os.getenv("LINKEDIN_PAGE_ID")

# Anthropic API - try multiple possible key names
ANTHROPIC_API_KEY = os.getenv("ANTHROPIC_API_KEY")

# =============================================================================
# CLAUDE CLIENT INITIALIZATION
# =============================================================================

claude_client = None

try:
    import anthropic

    if ANTHROPIC_API_KEY:
        claude_client = anthropic.Anthropic(api_key=ANTHROPIC_API_KEY)
        log_activity("Claude client initialized with ANTHROPIC_API_KEY")
    else:
        # Try default initialization (uses ANTHROPIC_API_KEY env var automatically)
        claude_client = anthropic.Anthropic()
        log_activity("Claude client initialized with default settings")

except ImportError:
    log_activity("anthropic package not installed - Claude features disabled", "WARNING")
except Exception as e:
    log_activity(f"Could not initialize Anthropic client: {e}", "WARNING")

# =============================================================================
# WATCHDOG IMPORTS
# =============================================================================

try:
    from watchdog.observers import Observer
    from watchdog.events import FileSystemEventHandler
    WATCHDOG_AVAILABLE = True
except ImportError:
    WATCHDOG_AVAILABLE = False
    log_activity("watchdog package not installed - file watching disabled", "ERROR")

# =============================================================================
# TASK PROCESSING FUNCTIONS
# =============================================================================

def parse_task_file(file_path: Path) -> dict:
    """Parse a task markdown file and extract metadata and content."""
    content = file_path.read_text(encoding="utf-8")

    task = {
        "filename": file_path.name,
        "filepath": str(file_path),
        "raw_content": content,
        "frontmatter": {},
        "title": "",
        "description": "",
        "actions": []
    }

    # Extract frontmatter
    frontmatter_match = re.match(r'^---\s*\n(.*?)\n---\s*\n', content, re.DOTALL)
    body = content

    if frontmatter_match:
        frontmatter_text = frontmatter_match.group(1)
        body = content[frontmatter_match.end():]

        # Parse frontmatter key-value pairs
        for line in frontmatter_text.split('\n'):
            if ':' in line:
                key, value = line.split(':', 1)
                task["frontmatter"][key.strip()] = value.strip()

    # Extract title
    title_match = re.search(r'^#\s+(.+)$', body, re.MULTILINE)
    if title_match:
        task["title"] = title_match.group(1).strip()

    # Extract description section
    desc_match = re.search(r'##\s+Description\s*\n(.*?)(?=\n##|\Z)', body, re.DOTALL)
    if desc_match:
        task["description"] = desc_match.group(1).strip()

    # Extract actions/checklist items
    action_matches = re.findall(r'- \[([ x])\] (.+)', body)
    task["actions"] = [{"done": check == 'x', "text": text} for check, text in action_matches]

    return task


def generate_plan_with_claude(task: dict) -> str:
    """Use Claude to generate a plan for the task."""
    if not claude_client:
        log_activity("Claude client not available, generating basic plan", "WARNING")
        return generate_basic_plan(task)

    prompt = f"""You are an executive assistant creating a plan for a task.

Task Title: {task['title']}
Task Description: {task['description']}
Raw Content:
{task['raw_content']}

Create a clear, actionable plan in markdown format with:
1. Objective (1-2 sentences)
2. Steps to accomplish (numbered list)
3. Resources needed
4. Success criteria

Keep it concise and professional."""

    try:
        message = claude_client.messages.create(
            model="claude-sonnet-4-20250514",
            max_tokens=1024,
            messages=[
                {"role": "user", "content": prompt}
            ]
        )
        return message.content[0].text
    except Exception as e:
        log_activity(f"Claude API error: {e}", "ERROR")
        return generate_basic_plan(task)


def generate_linkedin_post_with_claude(task: dict) -> str:
    """Use Claude to draft a LinkedIn post for the task."""
    if not claude_client:
        log_activity("Claude client not available, generating basic post", "WARNING")
        return generate_basic_linkedin_post(task)

    prompt = f"""You are a social media manager creating a LinkedIn post.

Task/Topic: {task['title']}
Context: {task['description']}
Full Content:
{task['raw_content']}

Create an engaging LinkedIn post that:
1. Has a strong hook in the first line
2. Is professional but conversational
3. Includes relevant hashtags (3-5)
4. Is optimized for engagement
5. Is under 3000 characters

Output ONLY the post text, ready to publish."""

    try:
        message = claude_client.messages.create(
            model="claude-sonnet-4-20250514",
            max_tokens=1024,
            messages=[
                {"role": "user", "content": prompt}
            ]
        )
        return message.content[0].text
    except Exception as e:
        log_activity(f"Claude API error: {e}", "ERROR")
        return generate_basic_linkedin_post(task)


def generate_basic_plan(task: dict) -> str:
    """Generate a basic plan without Claude."""
    return f"""# Plan: {task['title']}

## Objective
Process and complete the task: {task['title']}

## Steps
1. Review task requirements
2. Draft LinkedIn content
3. Submit for approval
4. Publish upon approval

## Resources Needed
- LinkedIn Publisher script
- Approval from human operator

## Success Criteria
- Post published to LinkedIn
- Task moved to Done folder
"""


def generate_basic_linkedin_post(task: dict) -> str:
    """Generate a basic LinkedIn post without Claude."""
    return f"""{task['title']}

{task['description'] or 'Check out our latest update!'}

#business #update #news
"""


def process_new_task(task_file: Path):
    """Process a new task from Needs_Action directory."""
    log_activity(f"Processing new task: {task_file.name}")

    try:
        # Parse the task
        task = parse_task_file(task_file)
        log_activity(f"Parsed task: {task['title']}")

        # Generate plan
        log_activity("Generating plan with Claude...")
        plan_content = generate_plan_with_claude(task)

        # Save plan to In_Progress
        plan_filename = f"Plan_{task_file.stem}.md"
        plan_path = IN_PROGRESS_DIR / plan_filename
        with open(plan_path, "w", encoding="utf-8") as f:
            f.write(f"""---
created: {datetime.now().strftime('%Y-%m-%d')}
source_task: {task_file.name}
status: planning
---

{plan_content}
""")
        log_activity(f"Plan saved to In_Progress: {plan_filename}")

        # Generate LinkedIn post draft
        log_activity("Generating LinkedIn post draft with Claude...")
        post_content = generate_linkedin_post_with_claude(task)

        # Save LinkedIn post to Pending_Approval (NOT In_Progress)
        post_filename = f"LinkedIn_{task_file.stem}.md"
        post_path = PENDING_APPROVAL_DIR / post_filename
        with open(post_path, "w", encoding="utf-8") as f:
            f.write(f"""---
created: {datetime.now().strftime('%Y-%m-%d')}
source_task: {task_file.name}
status: pending_approval
type: linkedin_post
approved: false
---

# LinkedIn Post: {task['title']}

{post_content}
""")
        log_activity(f"LinkedIn post draft saved to Pending_Approval: {post_filename}")

        # Move original task to In_Progress (to track it's being worked on)
        in_progress_task = IN_PROGRESS_DIR / task_file.name
        shutil.move(str(task_file), str(in_progress_task))
        log_activity(f"Moved original task to In_Progress: {task_file.name}")

        log_activity(f"Task processing complete. Move '{post_filename}' to /Approved to publish.")

    except Exception as e:
        log_activity(f"Error processing task {task_file.name}: {str(e)}", "ERROR")
        log_activity(f"Traceback: {traceback.format_exc()}", "ERROR")


def trigger_linkedin_publisher(approved_file: Path):
    """Trigger the LinkedIn publisher for an approved file."""
    log_activity(f"Triggering LinkedIn publisher for: {approved_file.name}")

    try:
        # Run the linkedin_publisher.py script
        result = subprocess.run(
            [sys.executable, "D:/zerohakathon/linkedin_publisher.py"],
            capture_output=True,
            text=True,
            cwd="D:/zerohakathon",
            timeout=60
        )

        if result.returncode == 0:
            log_activity(f"LinkedIn publisher completed successfully")
            if result.stdout:
                log_activity(f"Publisher output: {result.stdout[:500]}")
        else:
            log_activity(f"LinkedIn publisher failed with code {result.returncode}", "ERROR")
            if result.stderr:
                log_activity(f"Publisher error: {result.stderr[:500]}", "ERROR")

    except subprocess.TimeoutExpired:
        log_activity("LinkedIn publisher timed out after 60 seconds", "ERROR")
    except Exception as e:
        log_activity(f"Error running LinkedIn publisher: {str(e)}", "ERROR")


# =============================================================================
# FILE SYSTEM HANDLERS
# =============================================================================

if WATCHDOG_AVAILABLE:
    class NeedsActionHandler(FileSystemEventHandler):
        """Handler for new files in Needs_Action directory."""

        def on_created(self, event):
            if event.is_directory:
                return

            file_path = Path(event.src_path)
            if file_path.suffix == '.md' and file_path.name != '.gitkeep':
                log_activity(f"New task detected in Needs_Action: {file_path.name}")
                # Small delay to ensure file is fully written
                time.sleep(1)
                process_new_task(file_path)


    class ApprovedHandler(FileSystemEventHandler):
        """Handler for files moved to Approved directory."""

        def on_created(self, event):
            if event.is_directory:
                return

            file_path = Path(event.src_path)
            if file_path.suffix == '.md' and file_path.name != '.gitkeep':
                log_activity(f"Approved file detected: {file_path.name}")
                # Small delay to ensure file is fully written/moved
                time.sleep(1)
                trigger_linkedin_publisher(file_path)


def scan_existing_tasks():
    """Scan for existing tasks that need processing."""
    log_activity("Scanning for existing tasks in Needs_Action...")

    for task_file in NEEDS_ACTION_DIR.glob("*.md"):
        if task_file.name != '.gitkeep':
            log_activity(f"Found existing task: {task_file.name}")
            process_new_task(task_file)


def run_agent_loop():
    """Main agent loop that monitors directories."""
    log_activity("=" * 60)
    log_activity("RALPH-LOOP AGENT STARTING")
    log_activity("=" * 60)
    log_activity(f"Monitoring directories:")
    log_activity(f"  - Needs_Action: {NEEDS_ACTION_DIR}")
    log_activity(f"  - In_Progress: {IN_PROGRESS_DIR}")
    log_activity(f"  - Pending_Approval: {PENDING_APPROVAL_DIR}")
    log_activity(f"  - Approved: {APPROVED_DIR}")
    log_activity(f"  - Done: {DONE_DIR}")
    log_activity("=" * 60)

    # Log environment status
    log_activity(f"Environment loaded: {len(ENV_RESULT['loaded'])} variables")
    log_activity(f"Claude client: {'Available' if claude_client else 'Not available'}")
    log_activity(f"LinkedIn token: {'Set' if LINKEDIN_ACCESS_TOKEN else 'Not set'}")

    if not WATCHDOG_AVAILABLE:
        log_activity("FATAL: watchdog not available, cannot start file monitoring", "ERROR")
        return

    # Process any existing tasks first
    scan_existing_tasks()

    # Set up file system watchers
    needs_action_handler = NeedsActionHandler()
    approved_handler = ApprovedHandler()

    observer = Observer()
    observer.schedule(needs_action_handler, str(NEEDS_ACTION_DIR), recursive=False)
    observer.schedule(approved_handler, str(APPROVED_DIR), recursive=False)

    observer.start()
    log_activity("File system watchers started successfully")
    log_activity("Agent is now running. Press Ctrl+C to stop.")

    try:
        while True:
            time.sleep(5)  # Check every 5 seconds
    except KeyboardInterrupt:
        log_activity("Received shutdown signal (Ctrl+C)")
        observer.stop()

    observer.join()
    log_activity("RALPH-LOOP AGENT STOPPED")


# =============================================================================
# MAIN ENTRY POINT
# =============================================================================

if __name__ == "__main__":
    print("=" * 60)
    print("RALPH-LOOP AGENT")
    print("=" * 60)
    print(f"Vault Base: {VAULT_BASE}")
    print(f"Log File: {LOG_FILE}")
    print(f"Python: {sys.executable}")
    print("Press Ctrl+C to stop")
    print("=" * 60)

    run_agent_loop()
