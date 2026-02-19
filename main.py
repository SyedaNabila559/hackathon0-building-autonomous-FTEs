"""
AI Employee - Autonomous Entry Point (HITL Edition)
====================================================

Human-in-the-Loop Workflow:
1. AI generates drafts -> vault/Inbox/
2. Human reviews, edits, and moves approved items to vault/Approved/
3. This script monitors vault/Approved/ and posts to LinkedIn
4. After posting, files move to vault/Done/
5. All actions logged to Odoo ERP (aiagent21.odoo.com)

Ralph Wiggum Loop:
    # PowerShell
    while ($true) { claude --print "Run AI employee cycle"; Start-Sleep 60 }

    # Bash
    while true; do claude --print "Run AI employee cycle"; sleep 60; done
"""

import sys
import os
sys.path.append('/usr/local/lib/python3.9/site-packages')
sys.path.append('/home/opc/.local/lib/python3.9/site-packages')

import time
import json
import shutil
import argparse
import logging
import urllib.request
import urllib.error
from pathlib import Path
from datetime import datetime
from typing import Callable

# Project root - all paths relative to this
PROJECT_ROOT = Path(".")
sys.path.insert(0, str(PROJECT_ROOT))

from dotenv import load_dotenv
load_dotenv(PROJECT_ROOT / ".env")

# Configure logging
LOG_DIR = PROJECT_ROOT / "logs"
LOG_DIR.mkdir(exist_ok=True)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[
        logging.FileHandler(LOG_DIR / "ai_employee.log"),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

# Import skills
from skills import social_manager, email_manager

# Import Odoo connector for database operations
from odoo_connector import OdooDBLogger


# =============================================================================
# LinkedIn API Integration
# =============================================================================

class LinkedInPoster:
    """Handles posting to LinkedIn via API."""

    def __init__(self):
        self.access_token = os.getenv("LINKEDIN_ACCESS_TOKEN")
        self.api_base = "https://api.linkedin.com/v2"

    def _get_user_urn(self) -> str:
        """Get the authenticated user's URN."""
        if not self.access_token:
            raise ValueError("LINKEDIN_ACCESS_TOKEN not set in .env")

        url = f"{self.api_base}/userinfo"
        headers = {
            "Authorization": f"Bearer {self.access_token}",
        }

        request = urllib.request.Request(url, headers=headers)

        try:
            with urllib.request.urlopen(request) as response:
                data = json.loads(response.read().decode())
                return f"urn:li:person:{data['sub']}"
        except urllib.error.HTTPError as e:
            error_body = e.read().decode()
            raise Exception(f"Failed to get user info: {e.code} - {error_body}")

    def post(self, content: str) -> dict:
        """
        Post content to LinkedIn.

        Args:
            content: The text content to post

        Returns:
            dict with success status and post ID or error
        """
        if not self.access_token:
            return {
                "success": False,
                "error": "LINKEDIN_ACCESS_TOKEN not set in .env"
            }

        try:
            # Get user URN
            author_urn = self._get_user_urn()
            logger.info(f"Posting as: {author_urn}")

            # Create post
            url = f"{self.api_base}/ugcPosts"
            headers = {
                "Authorization": f"Bearer {self.access_token}",
                "Content-Type": "application/json",
                "X-Restli-Protocol-Version": "2.0.0",
            }

            payload = {
                "author": author_urn,
                "lifecycleState": "PUBLISHED",
                "specificContent": {
                    "com.linkedin.ugc.ShareContent": {
                        "shareCommentary": {
                            "text": content
                        },
                        "shareMediaCategory": "NONE"
                    }
                },
                "visibility": {
                    "com.linkedin.ugc.MemberNetworkVisibility": "PUBLIC"
                }
            }

            data = json.dumps(payload).encode()
            request = urllib.request.Request(url, data=data, headers=headers, method="POST")

            with urllib.request.urlopen(request) as response:
                result = json.loads(response.read().decode())
                post_id = result.get("id", "unknown")
                logger.info(f"Successfully posted to LinkedIn: {post_id}")
                return {
                    "success": True,
                    "post_id": post_id,
                    "error": None
                }

        except urllib.error.HTTPError as e:
            error_body = e.read().decode()
            logger.error(f"LinkedIn API error: {e.code} - {error_body}")
            return {
                "success": False,
                "error": f"HTTP {e.code}: {error_body}",
                "post_id": None
            }
        except Exception as e:
            logger.error(f"Error posting to LinkedIn: {e}")
            return {
                "success": False,
                "error": str(e),
                "post_id": None
            }


# =============================================================================
# AI Employee Orchestrator
# =============================================================================

class AIEmployee:
    """
    The AI Employee orchestrator with HITL workflow.
    Monitors vault/Approved/ and handles posting.
    """

    def __init__(self):
        self.project_root = PROJECT_ROOT
        self.vault_dir = PROJECT_ROOT / "vault"
        self.inbox_dir = self.vault_dir / "Inbox"
        self.approved_dir = self.vault_dir / "Approved"
        self.done_dir = self.vault_dir / "Done"
        self.needs_action_dir = self.vault_dir / "Needs_Action"

        self.skills_registry: dict[str, Callable] = {}
        self.db_logger = OdooDBLogger()  # Using Odoo ERP for logging
        self.linkedin = LinkedInPoster()

        self._register_skills()
        self._ensure_directories()

    def _ensure_directories(self):
        """Create required directories if they don't exist."""
        for dir_path in [
            self.vault_dir,
            self.inbox_dir,
            self.approved_dir,
            self.done_dir,
            self.needs_action_dir
        ]:
            dir_path.mkdir(parents=True, exist_ok=True)

    def _register_skills(self):
        """Register available skills."""
        self.skills_registry = {
            "social": social_manager.run_skill,
            "email": email_manager.run_skill,
        }
        logger.info(f"Registered skills: {list(self.skills_registry.keys())}")

    def run_skill(self, skill_name: str, action: str = None, **kwargs) -> dict:
        """Execute a registered skill."""
        if skill_name not in self.skills_registry:
            return {
                "success": False,
                "error": f"Unknown skill: {skill_name}. Available: {list(self.skills_registry.keys())}"
            }

        logger.info(f"Running skill: {skill_name} (action: {action})")

        try:
            skill_func = self.skills_registry[skill_name]
            if action:
                result = skill_func(action=action, **kwargs)
            else:
                result = skill_func(**kwargs)

            if result.get("success"):
                logger.info(f"Skill {skill_name} completed successfully")
                # Log draft creation to DB
                if action == "draft" and result.get("file_path"):
                    self.db_logger.log_event(
                        event_type="draft_created",
                        file_name=Path(result["file_path"]).name,
                        status="pending_review",
                        platform="linkedin",
                        post_content=result.get("content"),
                        metadata={"topic": kwargs.get("topic"), "tone": kwargs.get("tone")}
                    )
            else:
                logger.warning(f"Skill {skill_name} failed: {result.get('error')}")

            return result

        except Exception as e:
            logger.error(f"Error running skill {skill_name}: {e}")
            return {"success": False, "error": str(e)}

    def process_approved_posts(self) -> dict:
        """
        Monitor vault/Approved/ and post approved content to LinkedIn.

        Returns:
            dict with processing results
        """
        results = {
            "processed": 0,
            "posted": 0,
            "errors": []
        }

        if not self.approved_dir.exists():
            return results

        # Find LinkedIn drafts in Approved folder
        for file_path in self.approved_dir.glob("LinkedIn_*.md"):
            results["processed"] += 1
            file_name = file_path.name

            logger.info(f"Processing approved post: {file_name}")

            # Log approval event
            self.db_logger.log_event(
                event_type="approved",
                file_name=file_name,
                status="posting",
                platform="linkedin"
            )

            try:
                # Extract post content from markdown file
                post_content = social_manager.extract_post_content(file_path)

                if not post_content:
                    error_msg = "Could not extract post content from file"
                    logger.error(f"{file_name}: {error_msg}")
                    results["errors"].append(f"{file_name}: {error_msg}")
                    self.db_logger.log_event(
                        event_type="error",
                        file_name=file_name,
                        status="failed",
                        platform="linkedin",
                        error_message=error_msg
                    )
                    continue

                # Post to LinkedIn
                post_result = self.linkedin.post(post_content)

                if post_result["success"]:
                    results["posted"] += 1
                    logger.info(f"Successfully posted: {file_name}")

                    # Log successful post
                    self.db_logger.log_event(
                        event_type="posted",
                        file_name=file_name,
                        status="completed",
                        platform="linkedin",
                        post_content=post_content,
                        linkedin_post_id=post_result.get("post_id"),
                        metadata={"posted_at": datetime.now().isoformat()}
                    )

                    # Move to Done folder
                    done_path = self.done_dir / file_name
                    shutil.move(str(file_path), str(done_path))
                    logger.info(f"Moved to Done: {file_name}")

                    # Update the file with posted status
                    self._update_file_status(done_path, post_result.get("post_id"))

                else:
                    error_msg = post_result.get("error", "Unknown error")
                    logger.error(f"Failed to post {file_name}: {error_msg}")
                    results["errors"].append(f"{file_name}: {error_msg}")

                    self.db_logger.log_event(
                        event_type="error",
                        file_name=file_name,
                        status="failed",
                        platform="linkedin",
                        post_content=post_content,
                        error_message=error_msg
                    )

            except Exception as e:
                error_msg = str(e)
                logger.error(f"Error processing {file_name}: {error_msg}")
                results["errors"].append(f"{file_name}: {error_msg}")

                self.db_logger.log_event(
                    event_type="error",
                    file_name=file_name,
                    status="failed",
                    platform="linkedin",
                    error_message=error_msg
                )

        return results

    def _update_file_status(self, file_path: Path, post_id: str):
        """Update the markdown file with posted status."""
        try:
            content = file_path.read_text(encoding="utf-8")

            # Update status line
            content = content.replace(
                "**Status:** Pending Human Review",
                f"**Status:** POSTED to LinkedIn"
            )

            # Add posting info
            posted_info = f"""

---

## Posted Successfully

**Posted At:** {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}
**LinkedIn Post ID:** {post_id}
"""
            content += posted_info

            file_path.write_text(content, encoding="utf-8")

        except Exception as e:
            logger.error(f"Error updating file status: {e}")

    def check_pending_tasks(self) -> list:
        """Check vault/Needs_Action for pending tasks."""
        tasks = []
        if self.needs_action_dir.exists():
            for f in self.needs_action_dir.glob("*.md"):
                tasks.append({
                    "file": str(f),
                    "name": f.stem,
                    "created": datetime.fromtimestamp(f.stat().st_ctime)
                })
        return sorted(tasks, key=lambda x: x["created"])

    def run_cycle(self) -> dict:
        """
        Run one cycle of the AI Employee.

        Returns:
            Summary of what was done
        """
        cycle_start = datetime.now()
        logger.info("=" * 50)
        logger.info(f"Starting AI Employee cycle at {cycle_start}")

        results = {
            "cycle_time": str(cycle_start),
            "tasks_found": 0,
            "approved_processed": 0,
            "linkedin_posted": 0,
            "skills_run": [],
            "errors": []
        }

        # 1. Process approved posts (HITL - main workflow)
        logger.info("Checking vault/Approved/ for human-approved posts...")
        approved_results = self.process_approved_posts()
        results["approved_processed"] = approved_results["processed"]
        results["linkedin_posted"] = approved_results["posted"]
        results["errors"].extend(approved_results["errors"])

        if approved_results["posted"] > 0:
            logger.info(f"Posted {approved_results['posted']} approved post(s) to LinkedIn")

        # 2. Check for pending tasks in Needs_Action
        pending = self.check_pending_tasks()
        results["tasks_found"] = len(pending)

        if pending:
            logger.info(f"Found {len(pending)} pending tasks in Needs_Action:")
            for task in pending:
                logger.info(f"  - {task['name']}")

        # 3. Check inbox status
        inbox_count = len(list(self.inbox_dir.glob("*.md")))
        if inbox_count > 0:
            logger.info(f"Inbox has {inbox_count} draft(s) awaiting review")

        # 4. Run email check
        logger.info("Checking for urgent emails...")
        email_result = self.run_skill("email", action="check", max_results=5)
        results["skills_run"].append({
            "skill": "email",
            "success": email_result.get("success", False),
            "details": email_result.get("message") or f"Found {email_result.get('count', 0)} emails"
        })

        if not email_result.get("success"):
            results["errors"].append(f"Email check: {email_result.get('error')}")

        logger.info(f"Cycle completed in {(datetime.now() - cycle_start).seconds}s")
        logger.info("=" * 50)

        return results

    def run_loop(self, interval: int = 60, max_cycles: int = None):
        """Run the AI Employee in a continuous loop (Ralph Wiggum Loop)."""
        logger.info(f"Starting Ralph Wiggum Loop (interval: {interval}s)")
        logger.info("Press Ctrl+C to stop")

        cycle_count = 0

        try:
            while max_cycles is None or cycle_count < max_cycles:
                cycle_count += 1
                logger.info(f"\n{'='*60}")
                logger.info(f"CYCLE {cycle_count}")
                logger.info(f"{'='*60}\n")

                self.run_cycle()

                if max_cycles is None or cycle_count < max_cycles:
                    logger.info(f"Sleeping for {interval} seconds...")
                    time.sleep(interval)

        except KeyboardInterrupt:
            logger.info("\nStopping AI Employee (user interrupt)")

        finally:
            self.db_logger.close()

        logger.info(f"Completed {cycle_count} cycles")

    def cleanup(self):
        """Clean up resources."""
        self.db_logger.close()


def main():
    parser = argparse.ArgumentParser(
        description="AI Employee - Autonomous Task Runner with HITL",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
HITL Workflow:
  1. Draft posts are created in vault/Inbox/
  2. Human reviews and moves approved posts to vault/Approved/
  3. This script posts approved content to LinkedIn
  4. Posted files are moved to vault/Done/
  5. All actions are logged to Neon PostgreSQL

Examples:
  # Run a single cycle
  python main.py

  # Run in continuous loop (checks every 60 seconds)
  python main.py --loop --interval 60

  # Create a LinkedIn draft (saved to Inbox for review)
  python main.py --skill social --action draft --topic "AI productivity"

  # Check for urgent emails
  python main.py --skill email --action check

Ralph Wiggum Loop (continuous):
  # PowerShell
  while ($true) { python main.py; Start-Sleep 60 }

  # Bash
  while true; do python main.py; sleep 60; done
        """
    )

    parser.add_argument("--loop", action="store_true", help="Run in continuous loop mode")
    parser.add_argument("--interval", type=int, default=60, help="Seconds between cycles (default: 60)")
    parser.add_argument("--max-cycles", type=int, default=None, help="Maximum cycles (default: infinite)")
    parser.add_argument("--skill", type=str, choices=["social", "email"], help="Run a specific skill")
    parser.add_argument("--action", type=str, help="Action for the skill")
    parser.add_argument("--topic", type=str, help="Topic for social skill")
    parser.add_argument("--tone", type=str, default="professional", help="Tone for social skill")

    args = parser.parse_args()

    employee = AIEmployee()

    try:
        # Run specific skill if requested
        if args.skill:
            kwargs = {}
            if args.topic:
                kwargs["topic"] = args.topic
            if args.tone:
                kwargs["tone"] = args.tone

            result = employee.run_skill(args.skill, action=args.action, **kwargs)
            print(f"\nResult: {json.dumps(result, indent=2)}")
            return

        # Run in loop mode or single cycle
        if args.loop:
            employee.run_loop(interval=args.interval, max_cycles=args.max_cycles)
        else:
            result = employee.run_cycle()
            print(f"\nCycle Summary:")
            print(f"  Approved posts processed: {result['approved_processed']}")
            print(f"  Posted to LinkedIn: {result['linkedin_posted']}")
            print(f"  Pending tasks: {result['tasks_found']}")
            if result['errors']:
                print(f"  Errors: {result['errors']}")

    finally:
        employee.cleanup()


if __name__ == "__main__":
    main()
