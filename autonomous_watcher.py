"""
Autonomous Agent Watcher
========================
Monitors the Needs_Action folder and triggers Claude Code to process tasks autonomously.

When a new .md file (from WhatsApp, Gmail, or manual input) is dropped into Needs_Action,
this watcher:
1. Detects the new file
2. Reads and parses the task content
3. Triggers Claude Code via subprocess to reason through and execute the task
4. Logs all activity to the Vault logs

Usage:
    python autonomous_watcher.py [--watch-dir PATH] [--dry-run]

Requirements:
    pip install watchdog python-dotenv
"""

import os
import sys
import time
import json
import logging
import argparse
import subprocess
import hashlib
import re
from datetime import datetime
from pathlib import Path
from typing import Optional, Dict, Any, List
from dataclasses import dataclass
from enum import Enum

from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler, FileCreatedEvent, FileModifiedEvent
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# =============================================================================
# Configuration
# =============================================================================
BASE_DIR = Path("D:/zerohakathon")
VAULT_DIR = BASE_DIR / "Vault_Template"
NEEDS_ACTION_DIR = VAULT_DIR / "Needs_Action"
IN_PROGRESS_DIR = VAULT_DIR / "In_Progress"
PENDING_APPROVAL_DIR = VAULT_DIR / "Pending_Approval"
APPROVED_DIR = VAULT_DIR / "Approved"
DONE_DIR = VAULT_DIR / "Done"
LOG_DIR = VAULT_DIR / "Logs"

# Claude Code command (adjust based on your installation)
CLAUDE_CODE_CMD = os.getenv("CLAUDE_CODE_CMD", "claude")

# Debounce settings
FILE_STABILITY_WAIT = 1.5  # seconds to wait for file to be fully written
PROCESSING_COOLDOWN = 5.0  # seconds between processing same file

# Safety settings from CLAUDE.md
PAYMENT_THRESHOLD = 100  # dollars


class TaskType(Enum):
    """Types of tasks the agent can handle."""
    EMAIL = "email"
    LINKEDIN_POST = "linkedin_post"
    WHATSAPP = "whatsapp"
    INVOICE = "invoice"
    CONTACT = "contact"
    RESEARCH = "research"
    GENERAL = "general"


@dataclass
class TaskContext:
    """Parsed task information from markdown file."""
    file_path: Path
    title: str
    description: str
    task_type: TaskType
    priority: str
    status: str
    source: str
    created: str
    frontmatter: Dict[str, Any]
    actions: List[str]
    raw_content: str


# =============================================================================
# Logging Setup
# =============================================================================
def setup_logging() -> logging.Logger:
    """Configure logging for the autonomous watcher."""
    LOG_DIR.mkdir(parents=True, exist_ok=True)

    logger = logging.getLogger("autonomous_watcher")
    logger.setLevel(logging.DEBUG)

    # Prevent duplicate handlers
    if logger.handlers:
        return logger

    # File handler - detailed logs
    log_file = LOG_DIR / f"autonomous_watcher_{datetime.now().strftime('%Y-%m-%d')}.log"
    file_handler = logging.FileHandler(log_file, encoding='utf-8')
    file_handler.setLevel(logging.DEBUG)
    file_formatter = logging.Formatter(
        '%(asctime)s | %(levelname)-8s | %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )
    file_handler.setFormatter(file_formatter)

    # Console handler - info and above
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(logging.INFO)
    console_formatter = logging.Formatter(
        '%(asctime)s | %(levelname)s | %(message)s',
        datefmt='%H:%M:%S'
    )
    console_handler.setFormatter(console_formatter)

    logger.addHandler(file_handler)
    logger.addHandler(console_handler)

    return logger


logger = setup_logging()


# =============================================================================
# Task Parser
# =============================================================================
class TaskParser:
    """Parse markdown task files into structured TaskContext objects."""

    @staticmethod
    def parse_frontmatter(content: str) -> Dict[str, Any]:
        """Extract YAML frontmatter from markdown."""
        frontmatter = {}

        match = re.match(r'^---\s*\n(.*?)\n---\s*\n', content, re.DOTALL)
        if match:
            fm_text = match.group(1)
            for line in fm_text.strip().split('\n'):
                if ':' in line:
                    key, value = line.split(':', 1)
                    key = key.strip()
                    value = value.strip().strip('"').strip("'")
                    frontmatter[key] = value

        return frontmatter

    @staticmethod
    def extract_title(content: str) -> str:
        """Extract title from first H1 heading."""
        match = re.search(r'^#\s+(.+)$', content, re.MULTILINE)
        if match:
            return match.group(1).strip()
        return "Untitled Task"

    @staticmethod
    def extract_description(content: str) -> str:
        """Extract description section."""
        match = re.search(r'##\s*Description\s*\n+(.*?)(?=\n##|\Z)', content, re.DOTALL | re.IGNORECASE)
        if match:
            return match.group(1).strip()

        # Fallback: get content after title
        lines = content.split('\n')
        desc_lines = []
        in_desc = False
        for line in lines:
            if line.startswith('# ') and not in_desc:
                in_desc = True
                continue
            if line.startswith('## '):
                break
            if in_desc and line.strip():
                desc_lines.append(line.strip())

        return ' '.join(desc_lines[:5]) if desc_lines else ""

    @staticmethod
    def extract_actions(content: str) -> List[str]:
        """Extract action items (checkboxes)."""
        actions = []

        # Look for unchecked action items
        pattern = r'- \[ \]\s+(.+)'
        matches = re.findall(pattern, content)
        actions.extend(matches)

        return actions

    @staticmethod
    def determine_task_type(frontmatter: Dict, title: str, content: str) -> TaskType:
        """Determine the type of task based on content analysis."""
        # Check frontmatter type field
        if 'type' in frontmatter:
            type_map = {
                'email': TaskType.EMAIL,
                'linkedin_post': TaskType.LINKEDIN_POST,
                'whatsapp': TaskType.WHATSAPP,
                'invoice': TaskType.INVOICE,
                'contact': TaskType.CONTACT,
                'research': TaskType.RESEARCH,
            }
            fm_type = frontmatter['type'].lower()
            if fm_type in type_map:
                return type_map[fm_type]

        # Check source field
        source = frontmatter.get('source', '').lower()
        if 'gmail' in source or 'email' in source:
            return TaskType.EMAIL
        if 'whatsapp' in source:
            return TaskType.WHATSAPP

        # Content-based detection
        content_lower = content.lower()
        title_lower = title.lower()

        if 'linkedin' in content_lower or 'linkedin' in title_lower:
            return TaskType.LINKEDIN_POST
        if 'email' in title_lower or 'reply to' in content_lower:
            return TaskType.EMAIL
        if 'invoice' in content_lower or 'payment' in content_lower:
            return TaskType.INVOICE
        if 'contact' in title_lower or 'customer' in content_lower:
            return TaskType.CONTACT

        return TaskType.GENERAL

    @classmethod
    def parse(cls, file_path: Path) -> Optional[TaskContext]:
        """Parse a markdown file into a TaskContext."""
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()

            frontmatter = cls.parse_frontmatter(content)
            title = cls.extract_title(content)
            description = cls.extract_description(content)
            actions = cls.extract_actions(content)
            task_type = cls.determine_task_type(frontmatter, title, content)

            return TaskContext(
                file_path=file_path,
                title=title,
                description=description,
                task_type=task_type,
                priority=frontmatter.get('priority', 'medium'),
                status=frontmatter.get('status', 'pending'),
                source=frontmatter.get('source', 'unknown'),
                created=frontmatter.get('created', datetime.now().strftime('%Y-%m-%d')),
                frontmatter=frontmatter,
                actions=actions,
                raw_content=content
            )

        except Exception as e:
            logger.error(f"Error parsing task file {file_path}: {e}")
            return None


# =============================================================================
# Claude Code Executor
# =============================================================================
class ClaudeCodeExecutor:
    """Execute Claude Code commands to process tasks."""

    def __init__(self, dry_run: bool = False):
        self.dry_run = dry_run
        self.base_dir = BASE_DIR

    def _build_prompt(self, task: TaskContext) -> str:
        """Build the prompt for Claude Code based on task type."""

        # Base context about the task
        prompt = f"""You are processing a task from the Needs_Action folder.

TASK FILE: {task.file_path.name}
TASK TYPE: {task.task_type.value}
PRIORITY: {task.priority}
TITLE: {task.title}

DESCRIPTION:
{task.description}

PENDING ACTIONS:
{chr(10).join(f'- {action}' for action in task.actions) if task.actions else '- Process this task'}

FULL TASK CONTENT:
---
{task.raw_content}
---

INSTRUCTIONS:
1. Analyze this task and determine the appropriate actions
2. For tasks requiring approval (payments > $100, new contacts, etc.), create an approval file in /Vault_Template/Approved/
3. Use the odoo_connector.py module for any ERP operations
4. Log your actions to /Vault_Template/Logs/
5. Update the task file status as you progress
6. Move completed tasks to /Vault_Template/Done/

"""

        # Add type-specific instructions
        if task.task_type == TaskType.EMAIL:
            prompt += """
EMAIL-SPECIFIC INSTRUCTIONS:
- Draft a professional response
- Check if the sender is a known contact (use odoo_connector.py)
- If replying to a NEW contact, create approval request first
- Save draft in the task file for review
"""
        elif task.task_type == TaskType.LINKEDIN_POST:
            prompt += """
LINKEDIN POST INSTRUCTIONS:
- Generate a compelling LinkedIn post based on the context
- Create a plan file in /Vault_Template/In_Progress/
- Move to Pending_Approval when draft is ready
- Wait for approval file in /Approved/ before publishing
"""
        elif task.task_type == TaskType.INVOICE:
            prompt += """
INVOICE INSTRUCTIONS:
- Use odoo_connector.py to check invoice status
- For payment actions over $100, create approval request
- Update Odoo records as needed
"""
        elif task.task_type == TaskType.WHATSAPP:
            prompt += """
WHATSAPP TASK INSTRUCTIONS:
- Parse the informal message content
- Draft a professional response or action plan
- Check if this requires any Odoo operations
"""

        prompt += """
Execute the task now. Be thorough but efficient.
"""

        return prompt

    def execute(self, task: TaskContext) -> Dict[str, Any]:
        """Execute Claude Code to process a task."""
        result = {
            'success': False,
            'task_file': str(task.file_path),
            'task_type': task.task_type.value,
            'started_at': datetime.now().isoformat(),
            'completed_at': None,
            'output': None,
            'error': None
        }

        prompt = self._build_prompt(task)

        if self.dry_run:
            logger.info(f"[DRY RUN] Would execute Claude Code with prompt:")
            logger.info(f"  Task: {task.title}")
            logger.info(f"  Type: {task.task_type.value}")
            result['success'] = True
            result['output'] = "[DRY RUN] No execution performed"
            result['completed_at'] = datetime.now().isoformat()
            return result

        try:
            logger.info(f"Executing Claude Code for task: {task.title}")

            # Build the command
            cmd = [
                CLAUDE_CODE_CMD,
                "--print",  # Print output to stdout
                "--dangerously-skip-permissions",  # Auto-approve safe operations
                prompt
            ]

            # Execute Claude Code
            process = subprocess.run(
                cmd,
                cwd=str(self.base_dir),
                capture_output=True,
                text=True,
                timeout=300  # 5 minute timeout
            )

            result['output'] = process.stdout
            result['completed_at'] = datetime.now().isoformat()

            if process.returncode == 0:
                result['success'] = True
                logger.info(f"Claude Code completed successfully for: {task.title}")
            else:
                result['error'] = process.stderr
                logger.error(f"Claude Code returned error: {process.stderr}")

        except subprocess.TimeoutExpired:
            result['error'] = "Execution timed out after 5 minutes"
            logger.error(f"Timeout processing task: {task.title}")
        except FileNotFoundError:
            result['error'] = f"Claude Code command not found: {CLAUDE_CODE_CMD}"
            logger.error(f"Claude Code not found. Set CLAUDE_CODE_CMD environment variable.")
        except Exception as e:
            result['error'] = str(e)
            logger.error(f"Error executing Claude Code: {e}")

        return result


# =============================================================================
# Activity Logger
# =============================================================================
class ActivityLogger:
    """Log agent activity to the Vault logs."""

    def __init__(self):
        self.log_dir = LOG_DIR
        self.log_dir.mkdir(parents=True, exist_ok=True)
        self.activity_log_file = self.log_dir / "activity.log"

    def log_activity(self, action: str, details: Dict[str, Any]):
        """Log an activity entry."""
        timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')

        entry = {
            'timestamp': timestamp,
            'action': action,
            **details
        }

        # Append to activity log
        try:
            with open(self.activity_log_file, 'a', encoding='utf-8') as f:
                f.write(f"{timestamp} | {action} | {json.dumps(details)}\n")
        except Exception as e:
            logger.error(f"Error writing to activity log: {e}")

        # Also update daily log
        self._update_daily_log(timestamp, action, details)

    def _update_daily_log(self, timestamp: str, action: str, details: Dict[str, Any]):
        """Update the daily markdown log."""
        date_str = datetime.now().strftime('%Y-%m-%d')
        daily_log = self.log_dir / f"{date_str}.md"

        # Create daily log if it doesn't exist
        if not daily_log.exists():
            header = f"""# Agent Log: {date_str}

## Session Summary
- Tasks processed: 0
- Approvals requested: 0
- Actions completed: 0

## Activity Log
| Time | Action | Result |
|------|--------|--------|
"""
            with open(daily_log, 'w', encoding='utf-8') as f:
                f.write(header)

        # Append activity entry
        time_str = timestamp.split(' ')[1]
        result = details.get('result', details.get('status', 'completed'))
        entry = f"| {time_str} | {action} | {result} |\n"

        try:
            with open(daily_log, 'a', encoding='utf-8') as f:
                f.write(entry)
        except Exception as e:
            logger.error(f"Error updating daily log: {e}")


# =============================================================================
# Autonomous File Handler
# =============================================================================
class AutonomousFileHandler(FileSystemEventHandler):
    """Handle file events and trigger Claude Code processing."""

    def __init__(self, executor: ClaudeCodeExecutor, activity_logger: ActivityLogger):
        self.executor = executor
        self.activity_logger = activity_logger
        self.processing_lock = set()  # Track files being processed
        self.last_processed: Dict[str, float] = {}  # Debounce tracking
        self.parser = TaskParser()

    def _get_file_hash(self, file_path: Path) -> str:
        """Generate hash for file identification."""
        try:
            stat = file_path.stat()
            unique_str = f"{file_path.name}_{stat.st_size}"
            return hashlib.md5(unique_str.encode()).hexdigest()[:8]
        except Exception:
            return hashlib.md5(str(file_path).encode()).hexdigest()[:8]

    def _should_process(self, file_path: Path) -> bool:
        """Determine if file should be processed."""
        # Only process .md files
        if not file_path.suffix.lower() == '.md':
            return False

        # Skip hidden/temp files
        if file_path.name.startswith('.') or file_path.name.startswith('~'):
            return False

        # Skip .gitkeep
        if file_path.name == '.gitkeep':
            return False

        # Check cooldown
        file_key = str(file_path)
        now = time.time()
        if file_key in self.last_processed:
            if now - self.last_processed[file_key] < PROCESSING_COOLDOWN:
                logger.debug(f"Skipping {file_path.name} - in cooldown period")
                return False

        # Check if already being processed
        if file_key in self.processing_lock:
            logger.debug(f"Skipping {file_path.name} - already processing")
            return False

        return True

    def _is_file_ready(self, file_path: Path) -> bool:
        """Check if file is fully written."""
        try:
            initial_size = file_path.stat().st_size
            time.sleep(FILE_STABILITY_WAIT)

            if not file_path.exists():
                return False

            final_size = file_path.stat().st_size
            return initial_size == final_size and final_size > 0
        except Exception:
            return False

    def process_file(self, file_path: Path):
        """Process a task file with Claude Code."""
        file_key = str(file_path)

        # Add to processing lock
        self.processing_lock.add(file_key)

        try:
            logger.info(f"Processing task file: {file_path.name}")

            # Parse the task
            task = self.parser.parse(file_path)
            if not task:
                logger.warning(f"Could not parse task file: {file_path.name}")
                return

            # Log the start
            self.activity_logger.log_activity(
                "task_started",
                {
                    'file': file_path.name,
                    'type': task.task_type.value,
                    'priority': task.priority,
                    'title': task.title
                }
            )

            # Execute with Claude Code
            result = self.executor.execute(task)

            # Log the result
            self.activity_logger.log_activity(
                "task_completed" if result['success'] else "task_failed",
                {
                    'file': file_path.name,
                    'type': task.task_type.value,
                    'success': result['success'],
                    'error': result.get('error'),
                    'result': 'success' if result['success'] else 'failed'
                }
            )

            # Update last processed time
            self.last_processed[file_key] = time.time()

        except Exception as e:
            logger.error(f"Error processing {file_path.name}: {e}")
            self.activity_logger.log_activity(
                "task_error",
                {
                    'file': file_path.name,
                    'error': str(e),
                    'result': 'error'
                }
            )
        finally:
            # Remove from processing lock
            self.processing_lock.discard(file_key)

    def on_created(self, event):
        """Handle new file creation."""
        if event.is_directory:
            return

        file_path = Path(event.src_path)

        if not self._should_process(file_path):
            return

        logger.info(f"New file detected: {file_path.name}")

        # Wait for file to be fully written
        if not self._is_file_ready(file_path):
            logger.warning(f"File not ready: {file_path.name}")
            return

        # Process the file
        self.process_file(file_path)

    def on_modified(self, event):
        """Handle file modifications (sometimes new files trigger modify instead of create)."""
        if event.is_directory:
            return

        file_path = Path(event.src_path)

        # Only process if not recently processed (handles create/modify race)
        file_key = str(file_path)
        now = time.time()
        if file_key in self.last_processed:
            if now - self.last_processed[file_key] < PROCESSING_COOLDOWN:
                return

        if not self._should_process(file_path):
            return

        # Check if this looks like a new file (within last 10 seconds)
        try:
            stat = file_path.stat()
            if now - stat.st_ctime > 10:
                return  # Not a new file, skip
        except Exception:
            return

        logger.info(f"File modified (treating as new): {file_path.name}")

        if not self._is_file_ready(file_path):
            logger.warning(f"File not ready: {file_path.name}")
            return

        self.process_file(file_path)


# =============================================================================
# Main Watcher
# =============================================================================
class AutonomousWatcher:
    """Main watcher class that orchestrates the autonomous agent."""

    def __init__(self, watch_dir: Path, dry_run: bool = False):
        self.watch_dir = watch_dir
        self.dry_run = dry_run

        # Ensure directories exist
        for dir_path in [NEEDS_ACTION_DIR, IN_PROGRESS_DIR, PENDING_APPROVAL_DIR,
                         APPROVED_DIR, DONE_DIR, LOG_DIR]:
            dir_path.mkdir(parents=True, exist_ok=True)

        # Initialize components
        self.executor = ClaudeCodeExecutor(dry_run=dry_run)
        self.activity_logger = ActivityLogger()
        self.handler = AutonomousFileHandler(self.executor, self.activity_logger)
        self.observer = Observer()

    def process_existing_files(self):
        """Process any existing files in Needs_Action on startup."""
        logger.info("Scanning for existing tasks in Needs_Action...")

        existing_files = list(self.watch_dir.glob("*.md"))
        pending_files = [f for f in existing_files if f.name != '.gitkeep']

        if pending_files:
            logger.info(f"Found {len(pending_files)} existing task(s) to process")
            for file_path in pending_files:
                self.handler.process_file(file_path)
        else:
            logger.info("No existing tasks found")

    def run(self):
        """Run the autonomous watcher."""
        logger.info("=" * 70)
        logger.info("Autonomous Agent Watcher Starting")
        logger.info("=" * 70)
        logger.info(f"Watching: {self.watch_dir}")
        logger.info(f"Dry Run: {self.dry_run}")
        logger.info(f"Claude Code: {CLAUDE_CODE_CMD}")
        logger.info("=" * 70)

        if not self.watch_dir.exists():
            logger.error(f"Watch directory does not exist: {self.watch_dir}")
            sys.exit(1)

        # Log startup
        self.activity_logger.log_activity(
            "watcher_started",
            {
                'watch_dir': str(self.watch_dir),
                'dry_run': self.dry_run,
                'result': 'started'
            }
        )

        # Process existing files first
        self.process_existing_files()

        # Start watching
        self.observer.schedule(self.handler, str(self.watch_dir), recursive=False)
        self.observer.start()

        logger.info("Watcher started. Press Ctrl+C to stop.")
        logger.info("Waiting for new tasks in Needs_Action folder...")

        try:
            while True:
                time.sleep(1)
        except KeyboardInterrupt:
            logger.info("Shutdown requested...")
            self.activity_logger.log_activity(
                "watcher_stopped",
                {'result': 'shutdown'}
            )
            self.observer.stop()
        except Exception as e:
            logger.error(f"Unexpected error: {e}")
            self.observer.stop()

        self.observer.join()
        logger.info("Autonomous watcher stopped.")


# =============================================================================
# Entry Point
# =============================================================================
def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description="Autonomous Agent Watcher - Monitor Needs_Action and trigger Claude Code"
    )
    parser.add_argument(
        "--watch-dir",
        type=Path,
        default=NEEDS_ACTION_DIR,
        help=f"Directory to monitor (default: {NEEDS_ACTION_DIR})"
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Run in dry-run mode (no actual Claude Code execution)"
    )
    parser.add_argument(
        "--process-existing",
        action="store_true",
        default=True,
        help="Process existing files on startup (default: True)"
    )

    args = parser.parse_args()

    watcher = AutonomousWatcher(
        watch_dir=args.watch_dir,
        dry_run=args.dry_run
    )

    watcher.run()


if __name__ == "__main__":
    main()
