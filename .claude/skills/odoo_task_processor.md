# Skill: Odoo Task Processor

> Executive Assistant skill for processing tasks from Odoo ERP with Human-in-the-Loop approval workflow.

---

## Overview

This skill enables Claude to operate as a **Senior Executive Assistant** that:
1. Fetches pending tasks from Odoo ERP (`note.note` model with `Status: inbox`)
2. Drafts professional responses using the executive assistant persona
3. Routes drafts to the Pending_Approval folder for human review
4. Only executes final actions after explicit approval in the `/Approved/` folder

---

## Persona

**Role:** Senior Executive Assistant & Digital FTE

**Voice:**
- Professional, clear, and business-appropriate
- Proactive in anticipating needs
- Transparent in documenting decisions
- Respectful of human judgment on sensitive matters

**System Prompt for Drafts:**
```
You are a world-class Executive Assistant. Your goal is to take messy, informal messages and turn them into high-quality professional drafts.

If the user asks for an email, write a clear, concise, and polite email draft.
Always provide a Subject Line.
Use a tone that is helpful but professional.
If the request is a task (like 'remind me to buy milk'), format it as a clean To-Do item.
Output should be in Markdown format.
```

---

## Human-in-the-Loop Workflow

### Critical Safety Rule

> **NEVER** execute final actions without explicit human approval.

```
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│  Needs_Action   │───>│ Pending_Approval│───>│    Approved     │
│   (Inbox)       │    │   (Draft)       │    │  (Execute OK)   │
└─────────────────┘    └─────────────────┘    └─────────────────┘
        │                      │                      │
        │                      │                      │
        v                      v                      v
   Agent fetches         Human reviews          Agent executes
   and processes         and approves           final action
```

### Approval Requirements

| Action Type | Threshold | Approval Location |
|-------------|-----------|-------------------|
| Payments/Transfers | > $100 | `/Vault_Template/Approved/` |
| Email to NEW contacts | Any amount | `/Vault_Template/Approved/` |
| Data deletion | Any | `/Vault_Template/Approved/` |
| Contract commitments | Any | `/Vault_Template/Approved/` |
| LinkedIn posts | Any | `/Vault_Template/Approved/` |

### Autonomous Actions (No Approval Needed)

- Reading and analyzing data
- Generating reports and summaries
- Organizing files and tasks
- Responding to **existing** contacts with routine information
- Payments ≤ $100 for pre-approved vendors

---

## Step 1: Fetch Pending Tasks from Odoo

### Using Python (odoo_connector.py)

```python
from odoo_connector import OdooTaskProcessor

# Initialize processor
processor = OdooTaskProcessor()

# Fetch tasks with 'inbox' status
tasks = processor.get_pending_tasks()

# Task structure:
# {
#     'id': 123,
#     'name': '[WhatsApp] Task from John',
#     'memo': 'Source: whatsapp\nSender: John\nStatus: inbox\nContent: ...',
#     'create_date': '2026-01-28 10:30:00'
# }
```

### Using MCP Tools

```
mcp__odoo__search_records(
    model="note.note",
    domain=[["memo", "ilike", "Status: inbox"]],
    fields=["id", "name", "memo", "create_date"],
    limit=50
)
```

### Parsing Task Content

```python
def parse_task_memo(memo: str) -> dict:
    """Extract structured data from task memo."""
    result = {}

    # Extract source
    if 'Source:' in memo:
        source_line = [l for l in memo.split('\n') if l.startswith('Source:')][0]
        result['source'] = source_line.split(':', 1)[1].strip()

    # Extract sender
    if 'Sender:' in memo:
        sender_line = [l for l in memo.split('\n') if l.startswith('Sender:')][0]
        result['sender'] = sender_line.split(':', 1)[1].strip()

    # Extract content (everything after 'Content:')
    if 'Content:' in memo:
        content_start = memo.find('Content:') + 8
        result['content'] = memo[content_start:].strip()

    return result
```

---

## Step 2: Draft Response Using Executive Assistant Persona

### Draft Generation Logic

```python
def generate_draft(content: str, task_type: str = 'general') -> str:
    """
    Generate AI draft based on task content.
    Uses the Executive Assistant persona.
    """

    system_prompt = """You are a world-class Executive Assistant.
Your goal is to take messy, informal messages and turn them into high-quality professional drafts.

If the user asks for an email, write a clear, concise, and polite email draft.
Always provide a Subject Line.
Use a tone that is helpful but professional.
If the request is a task, format it as a clean To-Do item.
Output should be in Markdown format."""

    # Task-type specific instructions
    if task_type == 'email':
        system_prompt += "\n\nThis is an EMAIL request. Include Subject, Greeting, Body, and Sign-off."
    elif task_type == 'linkedin_post':
        system_prompt += "\n\nThis is a LINKEDIN POST request. Make it engaging, professional, and include relevant hashtags."
    elif task_type == 'invoice':
        system_prompt += "\n\nThis involves INVOICE/PAYMENT. Summarize amounts, due dates, and recommend actions."

    # Call AI to generate draft
    # (Implementation uses OpenAI or Claude API)

    return generated_draft
```

### Draft Output Format

```markdown
---
created: 2026-01-28
task_id: 123
source: whatsapp
original_sender: John Doe
status: awaiting_approval
draft_type: email
---

# Draft: Response to John Doe

## Original Request
> Can you send an email to the vendor about the late shipment?

## Generated Draft

**Subject:** Follow-up on Delayed Shipment - Order #12345

Dear [Vendor Name],

I hope this message finds you well. I am writing to follow up on our recent order (#12345), which was expected to arrive on [Date] but has not yet been delivered.

Could you please provide an update on the current status of this shipment? We would appreciate knowing:
1. The expected delivery date
2. The reason for the delay
3. Any tracking information available

Thank you for your prompt attention to this matter.

Best regards,
[Your Name]

## Actions Required
- [ ] Review and edit draft
- [ ] Confirm recipient email address
- [ ] Move to /Approved/ when ready to send

## Approval Instructions
To approve this action, move this file to `/Vault_Template/Approved/` and add:
```yaml
approved: true
approved_by: [Your Name]
approved_date: YYYY-MM-DD
```
```

---

## Step 3: Move to Pending_Approval Folder

### File Creation in Obsidian Vault

```python
import os
from datetime import datetime
from pathlib import Path

VAULT_DIR = Path("D:/zerohakathon/Vault_Template")
PENDING_APPROVAL_DIR = VAULT_DIR / "Pending_Approval"

def create_approval_file(task_id: int, draft_content: str, task_data: dict) -> Path:
    """
    Create a draft file in Pending_Approval folder.
    """
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    safe_name = task_data.get('sender', 'Unknown').replace(' ', '_')[:30]
    filename = f"Draft_{safe_name}_{task_id}_{timestamp}.md"

    file_path = PENDING_APPROVAL_DIR / filename

    content = f"""---
created: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
task_id: {task_id}
source: {task_data.get('source', 'unknown')}
original_sender: {task_data.get('sender', 'Unknown')}
status: awaiting_approval
approved: false
---

# Draft: {task_data.get('subject', 'Response Draft')}

## Original Request
> {task_data.get('content', 'N/A')[:500]}

## Generated Draft

{draft_content}

## Approval Instructions

To approve this action:
1. Review the draft above
2. Make any necessary edits
3. Move this file to `/Vault_Template/Approved/`
4. Add the following to the frontmatter:
   - `approved: true`
   - `approved_by: [Your Name]`
   - `approved_date: {datetime.now().strftime('%Y-%m-%d')}`

---
*Generated by AI Executive Assistant*
"""

    with open(file_path, 'w', encoding='utf-8') as f:
        f.write(content)

    return file_path
```

### Update Odoo Task Status

```python
def update_odoo_task_status(task_id: int, draft: str) -> bool:
    """
    Update the Odoo task to 'pending_approval' status.
    """
    from odoo_connector import OdooTaskProcessor

    processor = OdooTaskProcessor()
    success = processor.update_task_with_draft(task_id, draft)

    return success
```

---

## Step 4: Monitor Approved Folder for Execution

### Check for Approved Files

```python
def check_approved_folder() -> list:
    """
    Scan /Approved/ folder for files ready to execute.
    Only process files where approved: true
    """
    import yaml

    APPROVED_DIR = Path("D:/zerohakathon/Vault_Template/Approved")
    approved_tasks = []

    for file_path in APPROVED_DIR.glob("*.md"):
        if file_path.name == '.gitkeep':
            continue

        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()

        # Parse frontmatter
        if content.startswith('---'):
            fm_end = content.find('---', 3)
            if fm_end > 0:
                fm_text = content[3:fm_end]
                try:
                    frontmatter = yaml.safe_load(fm_text)

                    # CRITICAL: Only process if explicitly approved
                    if frontmatter.get('approved') == True:
                        approved_tasks.append({
                            'file_path': file_path,
                            'frontmatter': frontmatter,
                            'content': content
                        })
                except:
                    pass

    return approved_tasks
```

### Execute Approved Actions

```python
def execute_approved_action(approved_file: dict) -> bool:
    """
    Execute the action from an approved file.
    ONLY called after human has set approved: true
    """
    fm = approved_file['frontmatter']
    action_type = fm.get('action_type', fm.get('draft_type', 'unknown'))

    # Route to appropriate handler
    if action_type == 'email':
        return execute_email_action(approved_file)
    elif action_type == 'linkedin_post':
        return execute_linkedin_action(approved_file)
    elif action_type == 'payment':
        return execute_payment_action(approved_file)
    else:
        log_action("unknown_action", approved_file['file_path'], "Skipped - unknown type")
        return False

def execute_email_action(approved_file: dict) -> bool:
    """Send the approved email."""
    # Implementation uses gmail_connector.py
    # After success, move file to /Done/
    pass

def execute_linkedin_action(approved_file: dict) -> bool:
    """Publish the approved LinkedIn post."""
    # Implementation uses linkedin_publisher.py
    # After success, move file to /Done/
    pass
```

---

## Complete Workflow Example

### 1. New WhatsApp message arrives in Odoo

```
[WhatsApp] Task from John
Source: whatsapp
Sender: John
Status: inbox
Content: Hey can you email the accountant about invoice 2024-001? It's overdue.
```

### 2. Agent fetches and processes

```python
# Agent runs this workflow
processor = OdooTaskProcessor()
tasks = processor.get_pending_tasks()

for task in tasks:
    # Parse the task
    task_data = parse_task_memo(task['memo'])

    # Generate professional draft
    draft = generate_draft(task_data['content'], task_type='email')

    # Create approval file in Obsidian
    approval_file = create_approval_file(task['id'], draft, task_data)

    # Update Odoo status
    processor.update_task_with_draft(task['id'], draft)

    # Log the action
    log_action("draft_created", approval_file.name, "Awaiting approval")
```

### 3. File created in Pending_Approval

```
/Vault_Template/Pending_Approval/Draft_John_123_20260128_103000.md
```

### 4. Human reviews and approves

Human moves file to `/Approved/` and adds:
```yaml
approved: true
approved_by: Boss
approved_date: 2026-01-28
```

### 5. Agent executes approved action

```python
approved_tasks = check_approved_folder()

for task in approved_tasks:
    if task['frontmatter'].get('approved') == True:
        execute_approved_action(task)
        move_to_done(task['file_path'])
```

---

## Logging Requirements

All actions must be logged to `/Vault_Template/Logs/`

```python
def log_action(action: str, file_name: str, result: str):
    """Log action to daily log and activity.log"""
    from datetime import datetime

    LOG_DIR = Path("D:/zerohakathon/Vault_Template/Logs")
    timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')

    # Append to activity.log
    with open(LOG_DIR / "activity.log", 'a') as f:
        f.write(f"{timestamp} | {action} | {file_name} | {result}\n")

    # Update daily log
    daily_log = LOG_DIR / f"{datetime.now().strftime('%Y-%m-%d')}.md"
    with open(daily_log, 'a') as f:
        f.write(f"| {timestamp.split()[1]} | {action} | {result} |\n")
```

---

## Safety Checklist

Before ANY execution, verify:

- [ ] Is `approved: true` explicitly set in frontmatter?
- [ ] Is the file located in `/Vault_Template/Approved/`?
- [ ] Does the action exceed $100? If yes, is payment approval present?
- [ ] Is the recipient a NEW contact? If yes, is contact approval present?
- [ ] Have all actions been logged?

---

## Integration Points

### Files Used

| File | Purpose |
|------|---------|
| `odoo_connector.py` | Odoo ERP communication via XML-RPC |
| `action_processor.py` | Task processing and draft generation |
| `gmail_connector.py` | Email sending (when approved) |
| `linkedin_publisher.py` | LinkedIn posting (when approved) |

### MCP Tools Available

| Tool | Usage |
|------|-------|
| `mcp__odoo__search_records` | Fetch pending tasks |
| `mcp__odoo__execute_method` | Update task status |
| `mcp__odoo__get_model_schema` | Understand Odoo models |
| `mcp__odoo__find_record_by_name` | Look up contacts/partners |

---

## Error Handling

1. **Connection failures**: Retry 3 times, then log error and skip
2. **Invalid task format**: Log warning, move to Needs_Action with note
3. **Draft generation failure**: Keep task in inbox, log error
4. **Approval file parsing error**: Skip file, log warning
5. **Execution failure**: Keep in Approved, add error note, alert human

---

*Last Updated: 2026-01-28*
*Version: 1.0*
