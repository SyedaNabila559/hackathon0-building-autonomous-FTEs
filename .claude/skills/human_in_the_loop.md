# Skill: Human-in-the-Loop Approval Pattern

> Safety-first workflow pattern ensuring no critical actions execute without explicit human approval.

---

## Core Principle

```
DRAFT → REVIEW → APPROVE → EXECUTE
         ↑
      Human Gate
```

**No file in `/Approved/` with `approved: true` = No execution**

---

## Folder Structure

```
Vault_Template/
├── Needs_Action/      # Inbox - new tasks land here
├── In_Progress/       # Agent working on tasks
├── Pending_Approval/  # Drafts awaiting human review
├── Approved/          # Human-approved, ready to execute
├── Done/              # Completed tasks
└── Logs/              # Activity audit trail
```

---

## Approval File Format

```markdown
---
created: 2026-01-28
action_type: email | payment | linkedin_post | deletion | contract
amount: $150.00  # if financial
recipient: vendor@example.com
approved: false  # HUMAN changes to true
approved_by:     # HUMAN fills in
approved_date:   # HUMAN fills in
---

# Approval Request: [Title]

## Action Details
[What will be done when approved]

## Draft Content
[The actual content/message/action]

## Justification
[Why this action is needed]

## Risk Assessment
[Any concerns or notes]
```

---

## Actions Requiring Approval

| Action | Condition | Required Fields |
|--------|-----------|-----------------|
| Payment | > $100 | `amount`, `recipient` |
| Email to NEW contact | Always | `recipient`, `is_new_contact: true` |
| Data deletion | Always | `delete_target`, `backup_confirmed` |
| Contract/Commitment | Always | `contract_details`, `legal_review` |
| LinkedIn post | Always | `post_content` |
| Odoo record creation | If financial | `model`, `values` |

---

## Agent Workflow

### Step 1: Create Draft (Agent)

```python
def create_approval_request(action_type, content, metadata):
    """Agent creates approval file in Pending_Approval."""
    file_path = PENDING_APPROVAL_DIR / f"Request_{action_type}_{timestamp}.md"

    frontmatter = {
        'created': datetime.now().isoformat(),
        'action_type': action_type,
        'approved': False,  # Always start False
        **metadata
    }

    # Write file with draft content
    write_approval_file(file_path, frontmatter, content)

    # Log the request
    log_action("approval_requested", file_path.name)

    return file_path
```

### Step 2: Human Review (Human)

Human opens file in Obsidian/IDE:
1. Reviews the draft content
2. Makes edits if needed
3. **Moves file** from `Pending_Approval/` to `Approved/`
4. **Adds approval fields**:
   ```yaml
   approved: true
   approved_by: John Smith
   approved_date: 2026-01-28
   ```

### Step 3: Execute Approved (Agent)

```python
def process_approved_files():
    """Agent checks Approved folder and executes."""
    for file_path in APPROVED_DIR.glob("*.md"):
        frontmatter = parse_frontmatter(file_path)

        # CRITICAL SAFETY CHECK
        if frontmatter.get('approved') != True:
            continue  # Skip - not approved

        if not frontmatter.get('approved_by'):
            continue  # Skip - no approver name

        # Safe to execute
        execute_action(frontmatter, file_path)

        # Move to Done
        move_to_done(file_path)

        # Log completion
        log_action("action_executed", file_path.name)
```

---

## Safety Checks (Must Pass All)

```python
def is_safe_to_execute(file_path: Path, frontmatter: dict) -> bool:
    """All checks must pass before execution."""

    # Check 1: File must be in Approved folder
    if file_path.parent.name != "Approved":
        return False

    # Check 2: approved must be explicitly True
    if frontmatter.get('approved') is not True:
        return False

    # Check 3: approver must be identified
    if not frontmatter.get('approved_by'):
        return False

    # Check 4: For payments > $100, verify amount is approved
    if frontmatter.get('action_type') == 'payment':
        amount = parse_amount(frontmatter.get('amount', '$0'))
        if amount > 100 and not frontmatter.get('payment_approved'):
            return False

    # Check 5: For new contacts, verify contact approval
    if frontmatter.get('is_new_contact') == True:
        if not frontmatter.get('new_contact_approved'):
            return False

    return True
```

---

## Autonomous Actions (No Approval)

These actions can execute without human gate:

- Reading files and data
- Generating drafts (not sending)
- Creating plans in `In_Progress/`
- Logging activities
- Moving files between folders (except to Approved)
- Responding to existing contacts with routine info
- Payments ≤ $100 to pre-approved vendors
- Odoo read operations
- Report generation

---

## Logging Requirements

Every action must be logged:

```python
# Activity log entry
f"{timestamp} | {action} | {file} | {result} | {approver}"

# Daily log entry
f"| {time} | {action} | {approver} | {result} |"
```

---

## Emergency Stop

If something goes wrong:

1. **Remove all files from `/Approved/`**
2. Agent will stop executing new actions
3. Review logs in `/Logs/` for audit
4. Fix issues before restoring files

---

## Quick Reference

```
SAFE (Auto):        READ, DRAFT, PLAN, LOG, ORGANIZE
NEEDS APPROVAL:     SEND, PAY, DELETE, COMMIT, PUBLISH

Check: /Approved/ + approved: true + approved_by: [name]
```

---

*This pattern ensures human oversight for all critical business actions.*
