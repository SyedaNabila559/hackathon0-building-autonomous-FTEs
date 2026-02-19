"""
Verify Setup Script - Validates the Ralph-Loop automation environment.

This script:
1. Prints a 'Directory Status' table (checks if all vault folders exist)
2. Validates that .env keys are loaded (prints first 4 chars only for security)
3. Tests if watchdog can see file events in the vault
"""

import os
import sys
import time
import tempfile
import threading
from pathlib import Path
from datetime import datetime

# =============================================================================
# DIRECTORY CONFIGURATION
# =============================================================================

VAULT_BASE = Path("D:/zerohakathon/Vault_Template")

REQUIRED_DIRS = {
    "Needs_Action": VAULT_BASE / "Needs_Action",
    "In_Progress": VAULT_BASE / "In_Progress",
    "Pending_Approval": VAULT_BASE / "Pending_Approval",
    "Approved": VAULT_BASE / "Approved",
    "Done": VAULT_BASE / "Done",
    "Logs": VAULT_BASE / "Logs",
}

# =============================================================================
# ENVIRONMENT LOADING
# =============================================================================

def load_env_manual(env_path: Path) -> dict:
    """Load .env file manually with line-by-line validation."""
    loaded = {}
    errors = []

    if not env_path.exists():
        return {"loaded": {}, "errors": [f".env not found at {env_path}"]}

    try:
        with open(env_path, "r", encoding="utf-8") as f:
            lines = f.readlines()

        for line_num, line in enumerate(lines, start=1):
            line = line.strip()

            if not line or line.startswith("#"):
                continue

            if "=" in line:
                try:
                    key, value = line.split("=", 1)
                    key = key.strip()
                    value = value.strip()

                    if (value.startswith('"') and value.endswith('"')) or \
                       (value.startswith("'") and value.endswith("'")):
                        value = value[1:-1]

                    os.environ[key] = value
                    loaded[key] = value

                except Exception as e:
                    errors.append(f"Line {line_num}: {str(e)}")
            else:
                errors.append(f"Line {line_num}: No '=' found in '{line[:30]}...'")

    except Exception as e:
        errors.append(f"Failed to read file: {str(e)}")

    return {"loaded": loaded, "errors": errors}


# =============================================================================
# HELPER FUNCTIONS
# =============================================================================

def mask_value(value: str, show_chars: int = 4) -> str:
    """Mask a value showing only first N characters."""
    if not value:
        return "NOT SET"
    if len(value) <= show_chars:
        return value
    return value[:show_chars] + "*" * (len(value) - show_chars)


def print_header(title: str):
    """Print a section header."""
    print("\n" + "=" * 60)
    print(f" {title}")
    print("=" * 60)


def print_status_row(name: str, status: str, details: str = ""):
    """Print a status row."""
    status_icon = "[OK]" if status == "OK" else "[!!]"
    print(f"  {status_icon} {name:<20} {details}")


# =============================================================================
# VALIDATION TESTS
# =============================================================================

def check_directories() -> dict:
    """Check if all required vault directories exist."""
    print_header("DIRECTORY STATUS")

    results = {}
    all_ok = True

    for name, path in REQUIRED_DIRS.items():
        exists = path.exists()
        is_dir = path.is_dir() if exists else False

        if exists and is_dir:
            results[name] = {"status": "OK", "path": str(path)}
            print_status_row(name, "OK", f"Exists at {path}")
        else:
            results[name] = {"status": "MISSING", "path": str(path)}
            print_status_row(name, "MISSING", f"Not found: {path}")
            all_ok = False

            # Attempt to create
            try:
                path.mkdir(parents=True, exist_ok=True)
                print(f"       -> Created directory: {path}")
                results[name]["status"] = "CREATED"
            except Exception as e:
                print(f"       -> Failed to create: {e}")

    print(f"\n  Summary: {sum(1 for r in results.values() if r['status'] in ['OK', 'CREATED'])}/{len(REQUIRED_DIRS)} directories ready")

    return results


def check_env_variables() -> dict:
    """Check if required environment variables are loaded."""
    print_header("ENVIRONMENT VARIABLES")

    env_path = Path("D:/zerohakathon/.env")
    env_result = load_env_manual(env_path)

    # Report errors
    if env_result["errors"]:
        print("\n  Parsing Errors:")
        for error in env_result["errors"]:
            print(f"    [!!] {error}")

    # Required variables
    required_vars = [
        "LINKEDIN_ACCESS_TOKEN",
        "LINKEDIN_PAGE_ID",
        "LINKEDIN_CLIENT_ID",
        "LINKEDIN_CLIENT_SECRET",
        "GMAIL_CLIENT_ID",
        "GMAIL_CLIENT_SECRET",
        "GMAIL_USER",
        "ANTHROPIC_API_KEY",
    ]

    # Optional but useful
    optional_vars = [
        "OPENAI_API_KEY",
        "HUGGINGFACE_API_KEY",
        "ODOO_URL",
        "TWILIO_ACCOUNT_SID",
    ]

    print("\n  Required Variables:")
    results = {}

    for var in required_vars:
        value = os.getenv(var)
        if value:
            masked = mask_value(value, 4)
            print_status_row(var, "OK", masked)
            results[var] = {"status": "OK", "masked": masked}
        else:
            print_status_row(var, "MISSING", "Not set in .env")
            results[var] = {"status": "MISSING"}

    print("\n  Optional Variables:")
    for var in optional_vars:
        value = os.getenv(var)
        if value:
            masked = mask_value(value, 4)
            print_status_row(var, "OK", masked)
            results[var] = {"status": "OK", "masked": masked}
        else:
            print_status_row(var, "NOT SET", "(optional)")
            results[var] = {"status": "NOT SET"}

    # Count stats
    required_ok = sum(1 for v in required_vars if os.getenv(v))
    print(f"\n  Summary: {required_ok}/{len(required_vars)} required variables set")

    return results


def test_watchdog() -> dict:
    """Test if watchdog can detect file events."""
    print_header("WATCHDOG FILE MONITORING TEST")

    result = {"status": "UNKNOWN", "details": ""}

    try:
        from watchdog.observers import Observer
        from watchdog.events import FileSystemEventHandler

        print("  [OK] watchdog package imported successfully")

        # Create a test handler
        events_detected = []

        class TestHandler(FileSystemEventHandler):
            def on_created(self, event):
                events_detected.append(("created", event.src_path))

            def on_deleted(self, event):
                events_detected.append(("deleted", event.src_path))

        # Set up observer on Needs_Action
        test_dir = REQUIRED_DIRS["Needs_Action"]
        test_dir.mkdir(parents=True, exist_ok=True)

        handler = TestHandler()
        observer = Observer()
        observer.schedule(handler, str(test_dir), recursive=False)
        observer.start()

        print(f"  [OK] Observer started on {test_dir}")

        # Create a test file
        test_file = test_dir / f"_watchdog_test_{int(time.time())}.tmp"
        print(f"  [..] Creating test file: {test_file.name}")

        test_file.write_text("watchdog test")
        time.sleep(1.5)  # Wait for event

        # Check if event was detected
        if any("created" in str(e) for e in events_detected):
            print("  [OK] File creation event detected!")
            result["status"] = "OK"
        else:
            print("  [!!] File creation event NOT detected")
            result["status"] = "PARTIAL"

        # Clean up
        if test_file.exists():
            test_file.unlink()
            time.sleep(0.5)

        observer.stop()
        observer.join()

        print("  [OK] Observer stopped cleanly")

        if result["status"] == "OK":
            result["details"] = "Watchdog is fully operational"
        else:
            result["details"] = "Watchdog started but events may be delayed"

    except ImportError:
        print("  [!!] watchdog package NOT installed")
        print("       Run: pip install watchdog")
        result["status"] = "FAILED"
        result["details"] = "watchdog not installed"

    except Exception as e:
        print(f"  [!!] Error testing watchdog: {e}")
        result["status"] = "ERROR"
        result["details"] = str(e)

    return result


def test_anthropic() -> dict:
    """Test if Anthropic client can be initialized."""
    print_header("CLAUDE API TEST")

    result = {"status": "UNKNOWN", "details": ""}

    try:
        import anthropic

        print("  [OK] anthropic package imported")

        api_key = os.getenv("ANTHROPIC_API_KEY")

        if api_key:
            client = anthropic.Anthropic(api_key=api_key)
            print("  [OK] Anthropic client initialized with API key")
            result["status"] = "OK"
            result["details"] = "Client ready with explicit API key"
        else:
            # Try default initialization
            try:
                client = anthropic.Anthropic()
                print("  [OK] Anthropic client initialized with default settings")
                result["status"] = "OK"
                result["details"] = "Client ready with default auth"
            except Exception as e:
                print(f"  [!!] Default initialization failed: {e}")
                result["status"] = "NO_KEY"
                result["details"] = "ANTHROPIC_API_KEY not set"

    except ImportError:
        print("  [!!] anthropic package NOT installed")
        print("       Run: pip install anthropic")
        result["status"] = "NOT_INSTALLED"
        result["details"] = "Package not installed"

    except Exception as e:
        print(f"  [!!] Error: {e}")
        result["status"] = "ERROR"
        result["details"] = str(e)

    return result


# =============================================================================
# MAIN
# =============================================================================

def main():
    print("\n" + "=" * 60)
    print("  RALPH-LOOP SETUP VERIFICATION")
    print("  " + datetime.now().strftime("%Y-%m-%d %H:%M:%S"))
    print("=" * 60)
    print(f"\n  Python: {sys.executable}")
    print(f"  Version: {sys.version.split()[0]}")
    print(f"  Vault: {VAULT_BASE}")

    results = {
        "directories": check_directories(),
        "env_vars": check_env_variables(),
        "watchdog": test_watchdog(),
        "anthropic": test_anthropic(),
    }

    # Final summary
    print_header("FINAL SUMMARY")

    dir_ok = all(r["status"] in ["OK", "CREATED"] for r in results["directories"].values())
    env_ok = os.getenv("LINKEDIN_ACCESS_TOKEN") and os.getenv("LINKEDIN_PAGE_ID")
    watchdog_ok = results["watchdog"]["status"] == "OK"
    claude_ok = results["anthropic"]["status"] == "OK"

    print(f"  Directories:     {'READY' if dir_ok else 'NEEDS ATTENTION'}")
    print(f"  Environment:     {'READY' if env_ok else 'NEEDS ATTENTION'}")
    print(f"  Watchdog:        {'READY' if watchdog_ok else 'NEEDS ATTENTION'}")
    print(f"  Claude API:      {'READY' if claude_ok else 'OPTIONAL - Basic mode available'}")

    all_ready = dir_ok and env_ok and watchdog_ok

    print("\n" + "-" * 60)
    if all_ready:
        print("  STATUS: READY FOR LIVE TESTING")
        print("\n  To start the agent, run:")
        print("    python D:/zerohakathon/agent_loop.py")
    else:
        print("  STATUS: SETUP INCOMPLETE")
        print("\n  Please resolve the issues above before starting.")

    print("=" * 60 + "\n")

    return 0 if all_ready else 1


if __name__ == "__main__":
    sys.exit(main())
