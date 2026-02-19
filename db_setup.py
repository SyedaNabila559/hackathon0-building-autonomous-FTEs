"""
Odoo ERP Setup Script
=====================
Verifies connection to Odoo ERP and ensures required data structures exist.

Replaces the previous Neon PostgreSQL setup.
"""

import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Odoo Configuration
ODOO_URL = os.getenv("ODOO_URL", "https://aiagent21.odoo.com")
ODOO_DB = os.getenv("ODOO_DB", "aiagent21")
ODOO_USERNAME = os.getenv("ODOO_USERNAME")
ODOO_PASSWORD = os.getenv("ODOO_PASSWORD")


def setup_odoo():
    """
    Verify Odoo connection and ensure required models are accessible.
    """
    if not all([ODOO_URL, ODOO_DB, ODOO_USERNAME, ODOO_PASSWORD]):
        print("Error: Odoo credentials not fully configured in .env")
        print("Required variables: ODOO_URL, ODOO_DB, ODOO_USERNAME, ODOO_PASSWORD")
        return False

    print(f"Connecting to Odoo ERP at {ODOO_URL}...")

    try:
        from odoo_connector import OdooConnector

        connector = OdooConnector()

        # Test authentication
        if not connector.authenticate():
            print("Failed to authenticate with Odoo")
            return False

        print("Successfully authenticated with Odoo!")

        # Test access to common models
        print("\nVerifying access to Odoo models...")

        # Test contacts (res.partner)
        contacts = connector.get_contacts(limit=1)
        print(f"  - res.partner (Contacts): OK")

        # Test invoices (account.move) - may not be available in all instances
        try:
            invoices = connector.get_invoices(limit=1)
            print(f"  - account.move (Invoices): OK")
        except Exception:
            print(f"  - account.move (Invoices): Not available (may require accounting module)")

        # Test products (product.product)
        try:
            products = connector.get_products(limit=1)
            print(f"  - product.product (Products): OK")
        except Exception:
            print(f"  - product.product (Products): Not available")

        # Test notes (note.note) - used for AI task logging
        try:
            notes = connector.execute('note.note', 'search', [], limit=1)
            print(f"  - note.note (Notes/Tasks): OK")
        except Exception:
            print(f"  - note.note (Notes): Not available (may require Notes module)")

        print("\n" + "=" * 50)
        print("Odoo ERP setup complete!")
        print("=" * 50)
        print(f"\nInstance: {ODOO_URL}")
        print(f"Database: {ODOO_DB}")
        print(f"User: {ODOO_USERNAME}")

        return True

    except ImportError:
        print("Error: odoo_connector module not found.")
        print("Make sure odoo_connector.py is in the same directory.")
        return False
    except Exception as e:
        print(f"Error setting up Odoo connection: {e}")
        return False


def test_workflow_logging():
    """Test the workflow logging functionality."""
    print("\nTesting workflow logging...")

    try:
        from odoo_connector import OdooDBLogger

        logger = OdooDBLogger()
        logger.log_event(
            event_type="setup_test",
            file_name="db_setup.py",
            status="success",
            platform="system",
            metadata={"action": "setup_verification"}
        )
        print("Workflow logging test: OK")
        logger.close()
        return True
    except Exception as e:
        print(f"Workflow logging test failed: {e}")
        return False


if __name__ == "__main__":
    success = setup_odoo()
    if success:
        test_workflow_logging()
