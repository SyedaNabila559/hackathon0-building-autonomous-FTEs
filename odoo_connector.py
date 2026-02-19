"""
Odoo ERP Connector
==================
Handles all communication with Odoo ERP for business data, invoices,
contacts, and workflow logging.

Replaces Neon PostgreSQL database operations with Odoo API calls.
"""

import os
import json
import xmlrpc.client
from datetime import datetime
from typing import Optional, Dict, Any, List
from dotenv import load_dotenv

load_dotenv()


class OdooConnector:
    """
    Connector for Odoo ERP operations.
    Handles authentication and CRUD operations via XML-RPC.
    """

    def __init__(self):
        self.url = os.getenv("ODOO_URL", "https://aiagent21.odoo.com")
        self.db = os.getenv("ODOO_DB", "aiagent21")
        self.username = os.getenv("ODOO_USERNAME")
        self.password = os.getenv("ODOO_PASSWORD")
        self.uid = None
        self._common = None
        self._models = None

    def _get_common(self):
        """Get common endpoint for authentication."""
        if self._common is None:
            self._common = xmlrpc.client.ServerProxy(f"{self.url}/xmlrpc/2/common")
        return self._common

    def _get_models(self):
        """Get models endpoint for CRUD operations."""
        if self._models is None:
            self._models = xmlrpc.client.ServerProxy(f"{self.url}/xmlrpc/2/object")
        return self._models

    def authenticate(self) -> bool:
        """
        Authenticate with Odoo and store the user ID.

        Returns:
            bool: True if authentication successful
        """
        if not all([self.url, self.db, self.username, self.password]):
            print("Error: Odoo credentials not fully configured in .env")
            return False

        try:
            common = self._get_common()
            self.uid = common.authenticate(self.db, self.username, self.password, {})
            if self.uid:
                print(f"Successfully authenticated with Odoo as UID: {self.uid}")
                return True
            else:
                print("Authentication failed: Invalid credentials")
                return False
        except Exception as e:
            print(f"Odoo authentication error: {e}")
            return False

    def _ensure_authenticated(self) -> bool:
        """Ensure we have a valid authentication."""
        if self.uid is None:
            return self.authenticate()
        return True

    def execute(self, model: str, method: str, *args, **kwargs) -> Any:
        """
        Execute an Odoo model method.

        Args:
            model: Odoo model name (e.g., 'res.partner', 'account.move')
            method: Method to call (e.g., 'search', 'read', 'create')
            *args: Positional arguments for the method
            **kwargs: Keyword arguments for the method

        Returns:
            Result from Odoo API
        """
        if not self._ensure_authenticated():
            return None

        try:
            models = self._get_models()
            return models.execute_kw(
                self.db, self.uid, self.password,
                model, method, list(args), kwargs
            )
        except Exception as e:
            print(f"Odoo API error ({model}.{method}): {e}")
            return None

    # =========================================================================
    # Contact Operations (res.partner)
    # =========================================================================

    def get_contacts(self, domain: List = None, fields: List[str] = None, limit: int = 100) -> List[Dict]:
        """
        Fetch contacts from Odoo.

        Args:
            domain: Odoo search domain (e.g., [['is_company', '=', True]])
            fields: Fields to retrieve
            limit: Maximum number of records

        Returns:
            List of contact dictionaries
        """
        domain = domain or []
        fields = fields or ['name', 'email', 'phone', 'is_company', 'street', 'city', 'country_id']

        ids = self.execute('res.partner', 'search', domain, limit=limit)
        if ids:
            return self.execute('res.partner', 'read', ids, fields=fields) or []
        return []

    def create_contact(self, name: str, email: str = None, phone: str = None,
                       is_company: bool = False, **kwargs) -> Optional[int]:
        """
        Create a new contact in Odoo.

        Returns:
            Contact ID if successful
        """
        vals = {
            'name': name,
            'email': email,
            'phone': phone,
            'is_company': is_company,
            **kwargs
        }
        # Remove None values
        vals = {k: v for k, v in vals.items() if v is not None}

        return self.execute('res.partner', 'create', vals)

    def search_contacts(self, search_term: str, limit: int = 10) -> List[Dict]:
        """Search contacts by name or email."""
        domain = [
            '|',
            ['name', 'ilike', search_term],
            ['email', 'ilike', search_term]
        ]
        return self.get_contacts(domain=domain, limit=limit)

    # =========================================================================
    # Invoice Operations (account.move)
    # =========================================================================

    def get_invoices(self, domain: List = None, fields: List[str] = None, limit: int = 100) -> List[Dict]:
        """
        Fetch invoices from Odoo.

        Args:
            domain: Odoo search domain
            fields: Fields to retrieve
            limit: Maximum number of records

        Returns:
            List of invoice dictionaries
        """
        domain = domain or [['move_type', 'in', ['out_invoice', 'out_refund']]]
        fields = fields or [
            'name', 'partner_id', 'invoice_date', 'amount_total',
            'amount_residual', 'state', 'payment_state'
        ]

        ids = self.execute('account.move', 'search', domain, limit=limit)
        if ids:
            return self.execute('account.move', 'read', ids, fields=fields) or []
        return []

    def get_unpaid_invoices(self, limit: int = 50) -> List[Dict]:
        """Get all unpaid invoices."""
        domain = [
            ['move_type', 'in', ['out_invoice']],
            ['payment_state', 'in', ['not_paid', 'partial']]
        ]
        return self.get_invoices(domain=domain, limit=limit)

    # =========================================================================
    # Product Operations (product.product)
    # =========================================================================

    def get_products(self, domain: List = None, fields: List[str] = None, limit: int = 100) -> List[Dict]:
        """Fetch products from Odoo."""
        domain = domain or []
        fields = fields or ['name', 'default_code', 'list_price', 'qty_available', 'type']

        ids = self.execute('product.product', 'search', domain, limit=limit)
        if ids:
            return self.execute('product.product', 'read', ids, fields=fields) or []
        return []

    # =========================================================================
    # Sale Order Operations (sale.order)
    # =========================================================================

    def get_sales_orders(self, domain: List = None, fields: List[str] = None, limit: int = 100) -> List[Dict]:
        """Fetch sales orders from Odoo."""
        domain = domain or []
        fields = fields or ['name', 'partner_id', 'date_order', 'amount_total', 'state']

        ids = self.execute('sale.order', 'search', domain, limit=limit)
        if ids:
            return self.execute('sale.order', 'read', ids, fields=fields) or []
        return []

    # =========================================================================
    # Custom Model for AI Tasks (if available) or Note Operations
    # =========================================================================

    def _ensure_ai_tasks_model(self) -> bool:
        """
        Check if x_ai_tasks custom model exists, if not use mail.activity or note.note.
        For simplicity, we'll use a workaround with notes or activities.
        """
        # Try to check if custom model exists
        try:
            result = self.execute('ir.model', 'search', [['model', '=', 'x_ai_tasks']])
            return bool(result)
        except Exception:
            return False

    def create_ai_task(self, source: str, sender: str, content: str,
                       status: str = 'inbox') -> Optional[int]:
        """
        Create an AI task record in Odoo.
        Uses note.note model as a fallback for storing tasks.
        """
        vals = {
            'name': f"[{source}] Task from {sender}",
            'memo': f"""Source: {source}
Sender: {sender}
Status: {status}
Created: {datetime.now().isoformat()}

Content:
{content}""",
        }

        # Try to create in note.note (available in many Odoo instances)
        result = self.execute('note.note', 'create', vals)
        if result:
            print(f"Created AI task in Odoo note: {result}")
            return result
        return None

    def get_ai_tasks(self, status: str = None, limit: int = 50) -> List[Dict]:
        """
        Get AI tasks from Odoo notes.
        """
        domain = []
        if status:
            domain.append(['memo', 'ilike', f'Status: {status}'])

        ids = self.execute('note.note', 'search', domain, limit=limit)
        if ids:
            return self.execute('note.note', 'read', ids, fields=['name', 'memo', 'create_date']) or []
        return []

    def update_ai_task(self, task_id: int, status: str = None, ai_draft: str = None) -> bool:
        """Update an AI task in Odoo."""
        # Read current memo
        tasks = self.execute('note.note', 'read', [task_id], fields=['memo'])
        if not tasks:
            return False

        memo = tasks[0].get('memo', '')

        # Update status in memo
        if status:
            import re
            memo = re.sub(r'Status: \w+', f'Status: {status}', memo)

        # Add AI draft
        if ai_draft:
            memo += f"\n\n--- AI Draft ---\n{ai_draft}"

        vals = {'memo': memo}
        result = self.execute('note.note', 'write', [task_id], vals)
        return bool(result)


class OdooDBLogger:
    """
    Replacement for NeonDBLogger - logs workflow events to Odoo.
    Uses Odoo's mail.activity or custom logging model.
    """

    def __init__(self):
        self.odoo = OdooConnector()
        self._authenticated = False

    def _ensure_connection(self) -> bool:
        """Ensure Odoo connection is established."""
        if not self._authenticated:
            self._authenticated = self.odoo.authenticate()
        return self._authenticated

    def log_event(
        self,
        event_type: str,
        file_name: str = None,
        status: str = None,
        platform: str = None,
        post_content: str = None,
        linkedin_post_id: str = None,
        error_message: str = None,
        metadata: dict = None
    ):
        """
        Log an event to Odoo.

        Uses note.note model to store workflow logs.
        """
        if not self._ensure_connection():
            print("Warning: Could not connect to Odoo - event not logged")
            return

        try:
            memo = f"""Event Type: {event_type}
File: {file_name or 'N/A'}
Status: {status or 'N/A'}
Platform: {platform or 'N/A'}
Timestamp: {datetime.now().isoformat()}
"""
            if linkedin_post_id:
                memo += f"LinkedIn Post ID: {linkedin_post_id}\n"
            if error_message:
                memo += f"Error: {error_message}\n"
            if post_content:
                memo += f"\n--- Content ---\n{post_content[:2000]}\n"
            if metadata:
                memo += f"\n--- Metadata ---\n{json.dumps(metadata, indent=2)}\n"

            vals = {
                'name': f"[{event_type.upper()}] {file_name or platform or 'Workflow Event'}",
                'memo': memo,
            }

            result = self.odoo.execute('note.note', 'create', vals)
            if result:
                print(f"Logged to Odoo: {event_type} - {file_name}")
            else:
                print(f"Warning: Failed to log event to Odoo")

        except Exception as e:
            print(f"Error logging to Odoo: {e}")

    def close(self):
        """Close connection (no-op for XML-RPC, kept for compatibility)."""
        pass


class OdooTaskProcessor:
    """
    Replacement for the action_processor's database operations.
    Handles AI task processing through Odoo.
    """

    def __init__(self):
        self.odoo = OdooConnector()
        self._authenticated = False

    def _ensure_connection(self) -> bool:
        """Ensure Odoo connection is established."""
        if not self._authenticated:
            self._authenticated = self.odoo.authenticate()
        return self._authenticated

    def get_pending_tasks(self) -> List[Dict]:
        """Get tasks with 'inbox' status."""
        if not self._ensure_connection():
            return []
        return self.odoo.get_ai_tasks(status='inbox')

    def create_task(self, source: str, sender: str, content: str) -> Optional[int]:
        """Create a new task."""
        if not self._ensure_connection():
            return None
        return self.odoo.create_ai_task(source, sender, content)

    def update_task_with_draft(self, task_id: int, draft: str) -> bool:
        """Update task with AI-generated draft."""
        if not self._ensure_connection():
            return False
        return self.odoo.update_ai_task(task_id, status='pending_approval', ai_draft=draft)


# Convenience function for quick access
def get_odoo_connector() -> OdooConnector:
    """Get a configured Odoo connector instance."""
    connector = OdooConnector()
    connector.authenticate()
    return connector


if __name__ == "__main__":
    # Test the connection
    print("Testing Odoo connection...")
    connector = OdooConnector()

    if connector.authenticate():
        print("\n--- Testing Contact Retrieval ---")
        contacts = connector.get_contacts(limit=5)
        for contact in contacts:
            print(f"  - {contact.get('name')} ({contact.get('email', 'No email')})")

        print("\n--- Testing Invoice Retrieval ---")
        invoices = connector.get_invoices(limit=5)
        for inv in invoices:
            print(f"  - {inv.get('name')}: {inv.get('amount_total')} ({inv.get('state')})")

        print("\n--- Testing Logger ---")
        logger = OdooDBLogger()
        logger.log_event(
            event_type="test",
            file_name="test_file.md",
            status="testing",
            platform="test",
            metadata={"test": True}
        )
        print("Test event logged successfully!")
    else:
        print("Failed to authenticate with Odoo")
