"""
Filesystem Watcher for Obsidian Vault Integration

Monitors a designated folder for new CSV, PDF, and DOC files.
Creates Markdown summaries in Vault_Template/Needs_Action/ for Obsidian visibility.

Usage:
    python filesystem_watcher.py [--watch-dir PATH] [--vault-dir PATH]

Requirements:
    pip install watchdog python-docx PyPDF2
"""

import os
import sys
import time
import logging
import argparse
import hashlib
from datetime import datetime
from pathlib import Path
from typing import Optional

from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler, FileCreatedEvent

# Optional imports for file content extraction
try:
    import PyPDF2
    PDF_SUPPORT = True
except ImportError:
    PDF_SUPPORT = False

try:
    from docx import Document
    DOCX_SUPPORT = True
except ImportError:
    DOCX_SUPPORT = False

try:
    import csv
    CSV_SUPPORT = True
except ImportError:
    CSV_SUPPORT = False


# Configuration
DEFAULT_WATCH_DIR = Path.home() / "Downloads"
DEFAULT_VAULT_DIR = Path("D:/zerohakathon/Vault_Template/Needs_Action")
SUPPORTED_EXTENSIONS = {'.csv', '.pdf', '.doc', '.docx'}
LOG_DIR = Path("D:/zerohakathon/Vault_Template/Logs")

# Setup logging
def setup_logging() -> logging.Logger:
    """Configure logging for long-running operations."""
    LOG_DIR.mkdir(parents=True, exist_ok=True)

    logger = logging.getLogger("filesystem_watcher")
    logger.setLevel(logging.DEBUG)

    # File handler - detailed logs
    log_file = LOG_DIR / f"filesystem_watcher_{datetime.now().strftime('%Y-%m-%d')}.log"
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
    console_formatter = logging.Formatter('%(asctime)s | %(levelname)s | %(message)s')
    console_handler.setFormatter(console_formatter)

    logger.addHandler(file_handler)
    logger.addHandler(console_handler)

    return logger


logger = setup_logging()


class FileContentExtractor:
    """Extract content summaries from supported file types."""

    @staticmethod
    def extract_pdf_summary(file_path: Path, max_chars: int = 500) -> str:
        """Extract text from first page of PDF."""
        if not PDF_SUPPORT:
            return "*PDF content extraction not available. Install PyPDF2.*"

        try:
            with open(file_path, 'rb') as f:
                reader = PyPDF2.PdfReader(f)
                if len(reader.pages) > 0:
                    text = reader.pages[0].extract_text()
                    if text:
                        return text[:max_chars].strip() + ("..." if len(text) > max_chars else "")
                return "*No extractable text found in PDF.*"
        except Exception as e:
            logger.error(f"PDF extraction error for {file_path}: {e}")
            return f"*Error extracting PDF content: {e}*"

    @staticmethod
    def extract_docx_summary(file_path: Path, max_chars: int = 500) -> str:
        """Extract text from DOCX file."""
        if not DOCX_SUPPORT:
            return "*DOCX content extraction not available. Install python-docx.*"

        try:
            doc = Document(file_path)
            text = "\n".join([para.text for para in doc.paragraphs[:10]])
            if text:
                return text[:max_chars].strip() + ("..." if len(text) > max_chars else "")
            return "*No text content found in document.*"
        except Exception as e:
            logger.error(f"DOCX extraction error for {file_path}: {e}")
            return f"*Error extracting DOCX content: {e}*"

    @staticmethod
    def extract_csv_summary(file_path: Path, max_rows: int = 5) -> str:
        """Extract header and first few rows from CSV."""
        try:
            with open(file_path, 'r', encoding='utf-8', errors='replace') as f:
                reader = csv.reader(f)
                rows = []
                for i, row in enumerate(reader):
                    if i >= max_rows + 1:  # +1 for header
                        break
                    rows.append(row)

                if not rows:
                    return "*Empty CSV file.*"

                # Format as markdown table
                header = rows[0]
                md_table = "| " + " | ".join(header) + " |\n"
                md_table += "| " + " | ".join(["---"] * len(header)) + " |\n"

                for row in rows[1:]:
                    # Pad row if needed
                    padded = row + [""] * (len(header) - len(row))
                    md_table += "| " + " | ".join(padded[:len(header)]) + " |\n"

                return md_table
        except Exception as e:
            logger.error(f"CSV extraction error for {file_path}: {e}")
            return f"*Error extracting CSV content: {e}*"

    @classmethod
    def extract(cls, file_path: Path) -> str:
        """Extract content summary based on file type."""
        suffix = file_path.suffix.lower()

        if suffix == '.pdf':
            return cls.extract_pdf_summary(file_path)
        elif suffix == '.docx':
            return cls.extract_docx_summary(file_path)
        elif suffix == '.doc':
            return "*Legacy .doc format - please convert to .docx for content extraction.*"
        elif suffix == '.csv':
            return cls.extract_csv_summary(file_path)
        else:
            return "*Unsupported file type for content extraction.*"


class VaultFileHandler(FileSystemEventHandler):
    """Handle file system events and create Obsidian markdown summaries."""

    def __init__(self, vault_dir: Path):
        self.vault_dir = vault_dir
        self.vault_dir.mkdir(parents=True, exist_ok=True)
        self.processed_files: set = set()
        logger.info(f"Vault handler initialized. Output: {vault_dir}")

    def _generate_file_id(self, file_path: Path) -> str:
        """Generate unique ID for file based on name and size."""
        stat = file_path.stat()
        unique_str = f"{file_path.name}_{stat.st_size}_{stat.st_mtime}"
        return hashlib.md5(unique_str.encode()).hexdigest()[:8]

    def _is_file_ready(self, file_path: Path, wait_time: float = 1.0) -> bool:
        """Check if file is fully written (not still being copied)."""
        try:
            initial_size = file_path.stat().st_size
            time.sleep(wait_time)
            final_size = file_path.stat().st_size
            return initial_size == final_size and final_size > 0
        except (OSError, FileNotFoundError):
            return False

    def _create_markdown_summary(self, file_path: Path) -> Optional[Path]:
        """Create a markdown summary file in the vault."""
        try:
            stat = file_path.stat()
            file_id = self._generate_file_id(file_path)
            timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            date_slug = datetime.now().strftime('%Y%m%d_%H%M%S')

            # Extract content preview
            content_preview = FileContentExtractor.extract(file_path)

            # Determine file type label
            type_labels = {
                '.csv': 'Spreadsheet',
                '.pdf': 'PDF Document',
                '.doc': 'Word Document',
                '.docx': 'Word Document'
            }
            file_type = type_labels.get(file_path.suffix.lower(), 'Document')

            # Create markdown content
            md_content = f"""---
created: {timestamp}
source: filesystem_watcher
file_type: {file_path.suffix.lower()}
priority: medium
status: pending
original_path: "{file_path.as_posix()}"
file_size: {stat.st_size}
---

# New File: {file_path.name}

## Metadata

| Property | Value |
|----------|-------|
| **Type** | {file_type} |
| **Size** | {stat.st_size:,} bytes |
| **Location** | `{file_path.parent}` |
| **Detected** | {timestamp} |

## Content Preview

{content_preview}

## Actions Required

- [ ] Review file content
- [ ] Categorize and tag appropriately
- [ ] Process or archive as needed

## Notes

*File detected by filesystem watcher. Review and process accordingly.*

---
*Auto-generated by filesystem_watcher.py*
"""

            # Save to vault
            safe_name = "".join(c if c.isalnum() or c in '._- ' else '_' for c in file_path.stem)
            md_filename = f"{date_slug}_{safe_name}_{file_id}.md"
            md_path = self.vault_dir / md_filename

            with open(md_path, 'w', encoding='utf-8') as f:
                f.write(md_content)

            logger.info(f"Created summary: {md_filename}")
            return md_path

        except Exception as e:
            logger.error(f"Error creating markdown summary for {file_path}: {e}")
            return None

    def on_created(self, event):
        """Handle new file creation events."""
        if event.is_directory:
            return

        file_path = Path(event.src_path)

        # Check if supported file type
        if file_path.suffix.lower() not in SUPPORTED_EXTENSIONS:
            logger.debug(f"Ignoring unsupported file type: {file_path.suffix}")
            return

        # Skip temporary files
        if file_path.name.startswith('.') or file_path.name.startswith('~'):
            logger.debug(f"Ignoring temporary file: {file_path.name}")
            return

        logger.info(f"New file detected: {file_path.name}")

        # Wait for file to be fully written
        if not self._is_file_ready(file_path):
            logger.warning(f"File not ready or empty: {file_path.name}")
            return

        # Check for duplicates
        file_id = self._generate_file_id(file_path)
        if file_id in self.processed_files:
            logger.debug(f"File already processed: {file_path.name}")
            return

        # Create markdown summary
        md_path = self._create_markdown_summary(file_path)
        if md_path:
            self.processed_files.add(file_id)
            logger.info(f"Successfully processed: {file_path.name} -> {md_path.name}")


def run_watcher(watch_dir: Path, vault_dir: Path):
    """Run the filesystem watcher."""
    logger.info("=" * 60)
    logger.info("Filesystem Watcher Starting")
    logger.info("=" * 60)
    logger.info(f"Watching: {watch_dir}")
    logger.info(f"Output to: {vault_dir}")
    logger.info(f"Supported types: {', '.join(SUPPORTED_EXTENSIONS)}")
    logger.info(f"PDF support: {PDF_SUPPORT}")
    logger.info(f"DOCX support: {DOCX_SUPPORT}")
    logger.info("=" * 60)

    if not watch_dir.exists():
        logger.error(f"Watch directory does not exist: {watch_dir}")
        sys.exit(1)

    event_handler = VaultFileHandler(vault_dir)
    observer = Observer()
    observer.schedule(event_handler, str(watch_dir), recursive=False)
    observer.start()

    logger.info("Watcher started. Press Ctrl+C to stop.")

    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        logger.info("Shutdown requested...")
        observer.stop()
    except Exception as e:
        logger.error(f"Unexpected error: {e}")
        observer.stop()

    observer.join()
    logger.info("Filesystem watcher stopped.")


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description="Monitor folder for new files and create Obsidian summaries"
    )
    parser.add_argument(
        "--watch-dir",
        type=Path,
        default=DEFAULT_WATCH_DIR,
        help=f"Directory to monitor (default: {DEFAULT_WATCH_DIR})"
    )
    parser.add_argument(
        "--vault-dir",
        type=Path,
        default=DEFAULT_VAULT_DIR,
        help=f"Vault Needs_Action directory (default: {DEFAULT_VAULT_DIR})"
    )

    args = parser.parse_args()
    run_watcher(args.watch_dir, args.vault_dir)


if __name__ == "__main__":
    main()
