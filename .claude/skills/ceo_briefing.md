# Skill: CEO Weekly Briefing

> Automated executive intelligence - generates Monday morning briefings with financial summaries, task metrics, and proactive business recommendations.

---

## Overview

This skill audits:
1. **Odoo Accounting Records** - Revenue, invoices, payments, aged receivables
2. **Completed Tasks** (`/Done/` folder) - Productivity metrics, task patterns
3. **Workflow Analysis** - Bottlenecks, inefficiencies, cost-cutting opportunities

**Output:** `Monday_Morning_Briefing.md` in the Obsidian vault

---

## Trigger Schedule

| Trigger | Timing | Location |
|---------|--------|----------|
| Weekly automated | Every Monday 6:00 AM | `/Vault_Template/` |
| Manual request | On-demand | `/Vault_Template/` |
| Month-end | Last day of month | `/Vault_Template/Reports/` |

---

## Data Sources

### 1. Odoo Accounting (via MCP or odoo_connector.py)

```python
# Models to query
ACCOUNTING_MODELS = {
    'account.move': 'Invoices and bills',
    'account.payment': 'Payments received/sent',
    'res.partner': 'Customer/vendor data',
    'sale.order': 'Sales orders',
    'purchase.order': 'Purchase orders',
}
```

### 2. Vault Done Folder

```
D:\zerohakathon\Vault_Template\Done\
├── *.md files (completed tasks)
└── Metadata: created date, source, type, priority
```

### 3. Activity Logs

```
D:\zerohakathon\Vault_Template\Logs\
├── activity.log
└── YYYY-MM-DD.md (daily logs)
```

---

## Briefing Generation Process

### Step 1: Collect Financial Data from Odoo

```python
def collect_financial_metrics(start_date: str, end_date: str) -> dict:
    """
    Collect all financial metrics from Odoo for the reporting period.

    Args:
        start_date: YYYY-MM-DD format (typically last Monday)
        end_date: YYYY-MM-DD format (typically this Sunday)

    Returns:
        Dictionary with all financial metrics
    """
    from odoo_connector import OdooConnector

    odoo = OdooConnector()
    if not odoo.authenticate():
        return {'error': 'Failed to connect to Odoo'}

    metrics = {}

    # 1. Revenue from paid invoices
    paid_invoices = odoo.execute(
        'account.move', 'search_read',
        [[
            ['move_type', '=', 'out_invoice'],
            ['payment_state', '=', 'paid'],
            ['invoice_date', '>=', start_date],
            ['invoice_date', '<=', end_date]
        ]],
        fields=['name', 'partner_id', 'amount_total', 'invoice_date']
    ) or []

    metrics['revenue'] = {
        'total': sum(inv['amount_total'] for inv in paid_invoices),
        'invoice_count': len(paid_invoices),
        'invoices': paid_invoices
    }

    # 2. Outstanding receivables (unpaid invoices)
    unpaid_invoices = odoo.execute(
        'account.move', 'search_read',
        [[
            ['move_type', '=', 'out_invoice'],
            ['payment_state', 'in', ['not_paid', 'partial']],
            ['state', '=', 'posted']
        ]],
        fields=['name', 'partner_id', 'amount_total', 'amount_residual',
                'invoice_date', 'invoice_date_due']
    ) or []

    metrics['receivables'] = {
        'total_outstanding': sum(inv['amount_residual'] for inv in unpaid_invoices),
        'count': len(unpaid_invoices),
        'invoices': unpaid_invoices
    }

    # 3. Expenses (vendor bills paid)
    paid_bills = odoo.execute(
        'account.move', 'search_read',
        [[
            ['move_type', '=', 'in_invoice'],
            ['payment_state', '=', 'paid'],
            ['invoice_date', '>=', start_date],
            ['invoice_date', '<=', end_date]
        ]],
        fields=['name', 'partner_id', 'amount_total', 'invoice_date']
    ) or []

    metrics['expenses'] = {
        'total': sum(bill['amount_total'] for bill in paid_bills),
        'bill_count': len(paid_bills),
        'bills': paid_bills
    }

    # 4. Net profit (simple calculation)
    metrics['net_profit'] = metrics['revenue']['total'] - metrics['expenses']['total']

    # 5. New customers this period
    new_customers = odoo.execute(
        'res.partner', 'search_read',
        [[
            ['customer_rank', '>', 0],
            ['create_date', '>=', start_date],
            ['create_date', '<=', end_date]
        ]],
        fields=['name', 'email', 'create_date']
    ) or []

    metrics['new_customers'] = {
        'count': len(new_customers),
        'customers': new_customers
    }

    # 6. Sales orders this period
    sales_orders = odoo.execute(
        'sale.order', 'search_read',
        [[
            ['date_order', '>=', start_date],
            ['date_order', '<=', end_date]
        ]],
        fields=['name', 'partner_id', 'amount_total', 'state', 'date_order']
    ) or []

    confirmed_orders = [o for o in sales_orders if o['state'] in ['sale', 'done']]

    metrics['sales_orders'] = {
        'total_value': sum(o['amount_total'] for o in confirmed_orders),
        'confirmed_count': len(confirmed_orders),
        'draft_count': len([o for o in sales_orders if o['state'] == 'draft']),
        'orders': sales_orders
    }

    return metrics
```

### Using MCP Tools (Alternative)

```
# Revenue this week
mcp__odoo__search_records(
    model="account.move",
    domain=[
        ["move_type", "=", "out_invoice"],
        ["payment_state", "=", "paid"],
        ["invoice_date", ">=", "2026-01-20"],
        ["invoice_date", "<=", "2026-01-26"]
    ],
    fields=["name", "partner_id", "amount_total", "invoice_date"]
)

# Aged receivables
mcp__odoo__search_records(
    model="account.move",
    domain=[
        ["move_type", "=", "out_invoice"],
        ["payment_state", "in", ["not_paid", "partial"]],
        ["state", "=", "posted"]
    ],
    fields=["name", "partner_id", "amount_residual", "invoice_date_due"]
)
```

---

### Step 2: Analyze Completed Tasks

```python
def analyze_completed_tasks(start_date: str, end_date: str) -> dict:
    """
    Analyze tasks in the Done folder for the reporting period.
    """
    from pathlib import Path
    from datetime import datetime
    import re

    DONE_DIR = Path("D:/zerohakathon/Vault_Template/Done")

    tasks = []

    for file_path in DONE_DIR.glob("*.md"):
        if file_path.name == '.gitkeep':
            continue

        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()

        # Parse frontmatter
        frontmatter = {}
        if content.startswith('---'):
            fm_end = content.find('---', 3)
            if fm_end > 0:
                fm_text = content[3:fm_end]
                for line in fm_text.strip().split('\n'):
                    if ':' in line:
                        key, value = line.split(':', 1)
                        frontmatter[key.strip()] = value.strip()

        # Check if task was completed in reporting period
        completed_date = frontmatter.get('completed', frontmatter.get('created', ''))

        # Extract title
        title_match = re.search(r'^#\s+(.+)$', content, re.MULTILINE)
        title = title_match.group(1) if title_match else file_path.stem

        tasks.append({
            'file': file_path.name,
            'title': title,
            'source': frontmatter.get('source', 'unknown'),
            'type': frontmatter.get('type', 'general'),
            'priority': frontmatter.get('priority', 'medium'),
            'created': frontmatter.get('created', ''),
            'completed': completed_date
        })

    # Categorize tasks
    by_source = {}
    by_type = {}
    by_priority = {}

    for task in tasks:
        source = task['source']
        by_source[source] = by_source.get(source, 0) + 1

        task_type = task['type']
        by_type[task_type] = by_type.get(task_type, 0) + 1

        priority = task['priority']
        by_priority[priority] = by_priority.get(priority, 0) + 1

    return {
        'total_completed': len(tasks),
        'by_source': by_source,
        'by_type': by_type,
        'by_priority': by_priority,
        'tasks': tasks
    }
```

---

### Step 3: Identify Bottlenecks & Cost-Cutting Opportunities

```python
def analyze_bottlenecks_and_savings(financial: dict, tasks: dict, logs: dict) -> dict:
    """
    AI-powered analysis to identify issues and opportunities.
    """
    insights = {
        'bottlenecks': [],
        'cost_cutting': [],
        'opportunities': [],
        'risks': []
    }

    # === BOTTLENECK DETECTION ===

    # 1. Aged receivables analysis
    if financial.get('receivables', {}).get('invoices'):
        overdue = []
        for inv in financial['receivables']['invoices']:
            due_date = inv.get('invoice_date_due')
            if due_date and due_date < datetime.now().strftime('%Y-%m-%d'):
                days_overdue = (datetime.now() - datetime.strptime(due_date, '%Y-%m-%d')).days
                overdue.append({
                    'invoice': inv['name'],
                    'customer': inv['partner_id'][1] if inv.get('partner_id') else 'Unknown',
                    'amount': inv['amount_residual'],
                    'days_overdue': days_overdue
                })

        if overdue:
            total_overdue = sum(o['amount'] for o in overdue)
            insights['bottlenecks'].append({
                'type': 'aged_receivables',
                'severity': 'high' if total_overdue > 10000 else 'medium',
                'description': f"{len(overdue)} overdue invoices totaling ${total_overdue:,.2f}",
                'recommendation': "Follow up on overdue accounts. Consider payment plans for large amounts.",
                'details': overdue[:5]  # Top 5
            })

    # 2. Task backlog analysis (if many high-priority tasks)
    high_priority = tasks.get('by_priority', {}).get('high', 0)
    critical = tasks.get('by_priority', {}).get('critical', 0)

    if critical > 0:
        insights['bottlenecks'].append({
            'type': 'critical_backlog',
            'severity': 'high',
            'description': f"{critical} critical tasks in queue",
            'recommendation': "Prioritize critical items. Consider delegating or automating."
        })

    # 3. Email response backlog
    email_tasks = tasks.get('by_type', {}).get('email', 0)
    if email_tasks > 20:
        insights['bottlenecks'].append({
            'type': 'email_overload',
            'severity': 'medium',
            'description': f"{email_tasks} email-related tasks processed",
            'recommendation': "Consider email templates or auto-responders for common queries."
        })

    # === COST-CUTTING OPPORTUNITIES ===

    # 1. Expense analysis
    expenses = financial.get('expenses', {}).get('total', 0)
    revenue = financial.get('revenue', {}).get('total', 0)

    if revenue > 0:
        expense_ratio = expenses / revenue
        if expense_ratio > 0.7:
            insights['cost_cutting'].append({
                'type': 'high_expense_ratio',
                'severity': 'high',
                'description': f"Expenses are {expense_ratio*100:.1f}% of revenue",
                'recommendation': "Review vendor contracts. Identify non-essential expenses.",
                'potential_savings': f"${expenses * 0.1:,.2f} (10% reduction target)"
            })

    # 2. Subscription audit suggestion
    insights['cost_cutting'].append({
        'type': 'subscription_audit',
        'severity': 'low',
        'description': "Quarterly subscription review recommended",
        'recommendation': "Audit software subscriptions, unused licenses, and recurring charges."
    })

    # 3. Automation opportunities
    manual_tasks = tasks.get('by_source', {}).get('manual', 0)
    total_tasks = tasks.get('total_completed', 1)

    if manual_tasks / total_tasks > 0.5:
        insights['cost_cutting'].append({
            'type': 'automation_opportunity',
            'severity': 'medium',
            'description': f"{manual_tasks}/{total_tasks} tasks are manually created",
            'recommendation': "Increase automation. Connect more data sources to reduce manual entry.",
            'potential_savings': "2-3 hours/week in manual task creation"
        })

    # === GROWTH OPPORTUNITIES ===

    # 1. New customer trend
    new_customers = financial.get('new_customers', {}).get('count', 0)
    if new_customers > 0:
        insights['opportunities'].append({
            'type': 'customer_growth',
            'description': f"{new_customers} new customers this period",
            'recommendation': "Follow up with onboarding. Request referrals from satisfied customers."
        })

    # 2. Draft orders (potential revenue)
    draft_orders = financial.get('sales_orders', {}).get('draft_count', 0)
    if draft_orders > 0:
        insights['opportunities'].append({
            'type': 'pending_orders',
            'description': f"{draft_orders} draft sales orders pending confirmation",
            'recommendation': "Follow up to convert drafts to confirmed orders."
        })

    # === RISK ALERTS ===

    # 1. Cash flow risk
    receivables = financial.get('receivables', {}).get('total_outstanding', 0)
    if receivables > revenue * 2:
        insights['risks'].append({
            'type': 'cash_flow',
            'severity': 'high',
            'description': f"Outstanding receivables (${receivables:,.2f}) exceed 2x weekly revenue",
            'recommendation': "Implement stricter payment terms. Consider factoring for immediate cash."
        })

    # 2. Customer concentration risk
    # (Would need more detailed customer revenue breakdown)

    return insights
```

---

### Step 4: Generate the Briefing Document

```python
def generate_monday_briefing(
    financial: dict,
    tasks: dict,
    insights: dict,
    period_start: str,
    period_end: str
) -> str:
    """
    Generate the Monday Morning Briefing markdown document.
    """
    from datetime import datetime

    today = datetime.now().strftime('%Y-%m-%d')

    # Calculate key metrics
    revenue = financial.get('revenue', {}).get('total', 0)
    expenses = financial.get('expenses', {}).get('total', 0)
    net_profit = financial.get('net_profit', 0)
    receivables = financial.get('receivables', {}).get('total_outstanding', 0)
    tasks_completed = tasks.get('total_completed', 0)

    # Determine overall status
    if net_profit > 0 and len(insights.get('risks', [])) == 0:
        status_emoji = "🟢"
        status_text = "Healthy"
    elif net_profit > 0:
        status_emoji = "🟡"
        status_text = "Attention Needed"
    else:
        status_emoji = "🔴"
        status_text = "Action Required"

    briefing = f"""---
generated: {today}
period_start: {period_start}
period_end: {period_end}
type: ceo_briefing
status: {status_text.lower().replace(' ', '_')}
---

# Monday Morning Briefing

**Week of {period_start} to {period_end}**

**Overall Status:** {status_emoji} {status_text}

---

## Executive Summary

| Metric | This Week | Status |
|--------|-----------|--------|
| **Revenue** | ${revenue:,.2f} | {"📈" if revenue > 0 else "📉"} |
| **Expenses** | ${expenses:,.2f} | {"⚠️" if expenses > revenue * 0.7 else "✅"} |
| **Net Profit** | ${net_profit:,.2f} | {"✅" if net_profit > 0 else "🔴"} |
| **Outstanding AR** | ${receivables:,.2f} | {"⚠️" if receivables > revenue * 2 else "✅"} |
| **Tasks Completed** | {tasks_completed} | ✅ |

---

## 1. Financial Performance

### Revenue Breakdown

| Source | Amount | Count |
|--------|--------|-------|
| Paid Invoices | ${revenue:,.2f} | {financial.get('revenue', {}).get('invoice_count', 0)} |
| New Sales Orders | ${financial.get('sales_orders', {}).get('total_value', 0):,.2f} | {financial.get('sales_orders', {}).get('confirmed_count', 0)} |

### Accounts Receivable

| Status | Amount | Count |
|--------|--------|-------|
| Outstanding | ${receivables:,.2f} | {financial.get('receivables', {}).get('count', 0)} |
| Draft Orders | - | {financial.get('sales_orders', {}).get('draft_count', 0)} |

### Expenses

| Category | Amount |
|----------|--------|
| Vendor Bills Paid | ${expenses:,.2f} |

**Profit Margin:** {(net_profit/revenue*100) if revenue > 0 else 0:.1f}%

---

## 2. Tasks Completed

**Total:** {tasks_completed} tasks processed this week

### By Source
"""

    # Add task breakdown by source
    for source, count in tasks.get('by_source', {}).items():
        briefing += f"- **{source.title()}:** {count}\n"

    briefing += "\n### By Type\n"
    for task_type, count in tasks.get('by_type', {}).items():
        briefing += f"- **{task_type.replace('_', ' ').title()}:** {count}\n"

    briefing += "\n### By Priority\n"
    priority_order = ['critical', 'high', 'medium', 'low']
    for priority in priority_order:
        count = tasks.get('by_priority', {}).get(priority, 0)
        if count > 0:
            emoji = {'critical': '🔴', 'high': '🟠', 'medium': '🟡', 'low': '🟢'}.get(priority, '')
            briefing += f"- {emoji} **{priority.title()}:** {count}\n"

    # Add insights sections
    briefing += """
---

## 3. Bottlenecks Identified

"""

    if insights.get('bottlenecks'):
        for i, bottleneck in enumerate(insights['bottlenecks'], 1):
            severity_emoji = {'high': '🔴', 'medium': '🟡', 'low': '🟢'}.get(bottleneck.get('severity', 'medium'), '⚪')
            briefing += f"""### {i}. {bottleneck.get('type', 'Issue').replace('_', ' ').title()} {severity_emoji}

**Issue:** {bottleneck.get('description', 'N/A')}

**Recommendation:** {bottleneck.get('recommendation', 'N/A')}

"""
    else:
        briefing += "*No significant bottlenecks identified this week.*\n\n"

    briefing += """---

## 4. Cost-Cutting Opportunities

"""

    if insights.get('cost_cutting'):
        for i, opportunity in enumerate(insights['cost_cutting'], 1):
            briefing += f"""### {i}. {opportunity.get('type', 'Opportunity').replace('_', ' ').title()}

**Finding:** {opportunity.get('description', 'N/A')}

**Action:** {opportunity.get('recommendation', 'N/A')}

"""
            if opportunity.get('potential_savings'):
                briefing += f"**Potential Savings:** {opportunity['potential_savings']}\n\n"
    else:
        briefing += "*No cost-cutting opportunities identified this week.*\n\n"

    briefing += """---

## 5. Growth Opportunities

"""

    if insights.get('opportunities'):
        for opportunity in insights['opportunities']:
            briefing += f"""- **{opportunity.get('type', '').replace('_', ' ').title()}:** {opportunity.get('description', '')}
  - *Action:* {opportunity.get('recommendation', '')}

"""
    else:
        briefing += "*No specific growth opportunities flagged this week.*\n\n"

    briefing += """---

## 6. Risk Alerts

"""

    if insights.get('risks'):
        for risk in insights['risks']:
            severity_emoji = {'high': '🔴', 'medium': '🟡', 'low': '🟢'}.get(risk.get('severity', 'medium'), '⚪')
            briefing += f"""### {severity_emoji} {risk.get('type', 'Risk').replace('_', ' ').title()}

**Alert:** {risk.get('description', 'N/A')}

**Mitigation:** {risk.get('recommendation', 'N/A')}

"""
    else:
        briefing += "✅ *No critical risks identified this week.*\n\n"

    briefing += f"""---

## Action Items for This Week

"""

    # Generate action items from insights
    action_items = []

    for bottleneck in insights.get('bottlenecks', []):
        if bottleneck.get('severity') in ['high', 'critical']:
            action_items.append(f"[ ] Address: {bottleneck.get('description', '')}")

    for risk in insights.get('risks', []):
        action_items.append(f"[ ] Mitigate: {risk.get('description', '')}")

    for opportunity in insights.get('opportunities', []):
        action_items.append(f"[ ] Pursue: {opportunity.get('description', '')}")

    if action_items:
        for item in action_items[:10]:  # Top 10 items
            briefing += f"- {item}\n"
    else:
        briefing += "- [ ] Review this briefing\n- [ ] Plan weekly priorities\n"

    briefing += f"""
---

## Appendix: New Customers

"""

    new_customers = financial.get('new_customers', {}).get('customers', [])
    if new_customers:
        briefing += "| Name | Email | Added |\n|------|-------|-------|\n"
        for customer in new_customers[:10]:
            briefing += f"| {customer.get('name', 'N/A')} | {customer.get('email', 'N/A')} | {customer.get('create_date', 'N/A')[:10]} |\n"
    else:
        briefing += "*No new customers this period.*\n"

    briefing += f"""
---

*Generated automatically by CEO Briefing Skill*
*Report Date: {today}*
*Data Period: {period_start} to {period_end}*
"""

    return briefing
```

---

## Complete Execution Script

```python
#!/usr/bin/env python3
"""
CEO Briefing Generator
======================
Generates weekly Monday Morning Briefing from Odoo and Vault data.

Usage:
    python ceo_briefing_generator.py [--output-dir PATH] [--weeks-back N]
"""

import os
import sys
from datetime import datetime, timedelta
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from odoo_connector import OdooConnector

# Configuration
VAULT_DIR = Path("D:/zerohakathon/Vault_Template")
DONE_DIR = VAULT_DIR / "Done"
LOGS_DIR = VAULT_DIR / "Logs"
OUTPUT_DIR = VAULT_DIR  # Briefing goes to vault root


def get_week_dates(weeks_back: int = 0) -> tuple:
    """Get start and end dates for the reporting week."""
    today = datetime.now()

    # Find last Monday
    days_since_monday = today.weekday()
    last_monday = today - timedelta(days=days_since_monday + (7 * weeks_back))
    last_sunday = last_monday + timedelta(days=6)

    return (
        last_monday.strftime('%Y-%m-%d'),
        last_sunday.strftime('%Y-%m-%d')
    )


def main(output_dir: Path = None, weeks_back: int = 0):
    """Generate the Monday Morning Briefing."""

    output_dir = output_dir or OUTPUT_DIR
    output_dir.mkdir(parents=True, exist_ok=True)

    period_start, period_end = get_week_dates(weeks_back)

    print(f"Generating CEO Briefing for {period_start} to {period_end}")

    # Step 1: Collect financial data
    print("Collecting financial metrics from Odoo...")
    financial = collect_financial_metrics(period_start, period_end)

    if 'error' in financial:
        print(f"Warning: {financial['error']}")
        financial = {
            'revenue': {'total': 0, 'invoice_count': 0},
            'expenses': {'total': 0},
            'receivables': {'total_outstanding': 0, 'count': 0},
            'net_profit': 0,
            'new_customers': {'count': 0, 'customers': []},
            'sales_orders': {'total_value': 0, 'confirmed_count': 0, 'draft_count': 0}
        }

    # Step 2: Analyze completed tasks
    print("Analyzing completed tasks...")
    tasks = analyze_completed_tasks(period_start, period_end)

    # Step 3: Parse activity logs
    print("Reviewing activity logs...")
    logs = parse_activity_logs(period_start, period_end)

    # Step 4: Generate insights
    print("Generating insights and recommendations...")
    insights = analyze_bottlenecks_and_savings(financial, tasks, logs)

    # Step 5: Generate briefing document
    print("Composing briefing document...")
    briefing = generate_monday_briefing(
        financial, tasks, insights, period_start, period_end
    )

    # Step 6: Save to file
    output_file = output_dir / "Monday_Morning_Briefing.md"

    with open(output_file, 'w', encoding='utf-8') as f:
        f.write(briefing)

    print(f"Briefing saved to: {output_file}")

    # Also save dated archive copy
    archive_dir = output_dir / "Reports" / "Weekly_Briefings"
    archive_dir.mkdir(parents=True, exist_ok=True)
    archive_file = archive_dir / f"Briefing_{period_start}.md"

    with open(archive_file, 'w', encoding='utf-8') as f:
        f.write(briefing)

    print(f"Archive copy saved to: {archive_file}")

    return output_file


def parse_activity_logs(start_date: str, end_date: str) -> dict:
    """Parse activity logs for the period."""
    logs = {
        'total_actions': 0,
        'by_action': {},
        'errors': []
    }

    activity_log = LOGS_DIR / "activity.log"

    if activity_log.exists():
        with open(activity_log, 'r', encoding='utf-8') as f:
            for line in f:
                parts = line.strip().split(' | ')
                if len(parts) >= 3:
                    timestamp = parts[0][:10]
                    if start_date <= timestamp <= end_date:
                        logs['total_actions'] += 1
                        action = parts[1] if len(parts) > 1 else 'unknown'
                        logs['by_action'][action] = logs['by_action'].get(action, 0) + 1

                        if 'error' in line.lower():
                            logs['errors'].append(line.strip())

    return logs


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Generate CEO Weekly Briefing")
    parser.add_argument("--output-dir", type=Path, default=OUTPUT_DIR)
    parser.add_argument("--weeks-back", type=int, default=0,
                        help="Generate for N weeks ago (0=current week)")

    args = parser.parse_args()
    main(args.output_dir, args.weeks_back)
```

---

## Scheduling (Windows Task Scheduler)

### Create Scheduled Task

```powershell
# Run every Monday at 6:00 AM
$action = New-ScheduledTaskAction -Execute "python" -Argument "D:\zerohakathon\ceo_briefing_generator.py"
$trigger = New-ScheduledTaskTrigger -Weekly -DaysOfWeek Monday -At 6:00AM
$principal = New-ScheduledTaskPrincipal -UserId "$env:USERNAME" -LogonType Interactive
$settings = New-ScheduledTaskSettingsSet -StartWhenAvailable

Register-ScheduledTask -TaskName "CEO Weekly Briefing" -Action $action -Trigger $trigger -Principal $principal -Settings $settings
```

### Alternative: Python Schedule

```python
import schedule
import time

def job():
    main()

# Run every Monday at 6:00 AM
schedule.every().monday.at("06:00").do(job)

while True:
    schedule.run_pending()
    time.sleep(60)
```

---

## Sample Output

```markdown
# Monday Morning Briefing

**Week of 2026-01-20 to 2026-01-26**

**Overall Status:** 🟢 Healthy

---

## Executive Summary

| Metric | This Week | Status |
|--------|-----------|--------|
| **Revenue** | $15,450.00 | 📈 |
| **Expenses** | $3,200.00 | ✅ |
| **Net Profit** | $12,250.00 | ✅ |
| **Outstanding AR** | $8,500.00 | ✅ |
| **Tasks Completed** | 47 | ✅ |

---

## 4. Cost-Cutting Opportunities

### 1. Automation Opportunity

**Finding:** 28/47 tasks are manually created

**Action:** Increase automation. Connect more data sources.

**Potential Savings:** 2-3 hours/week in manual task creation

...
```

---

## Integration with Autonomous Watcher

Add to `autonomous_watcher.py`:

```python
def check_briefing_schedule():
    """Check if it's time to generate the weekly briefing."""
    from datetime import datetime

    now = datetime.now()

    # Monday at 6 AM
    if now.weekday() == 0 and now.hour == 6 and now.minute < 5:
        from ceo_briefing_generator import main
        main()
```

---

*Last Updated: 2026-01-28*
*Version: 1.0*
