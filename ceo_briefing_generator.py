#!/usr/bin/env python3
"""
CEO Briefing Generator
======================
Generates weekly Monday Morning Briefing from Odoo accounting data
and completed tasks in the Obsidian vault.

Gold Tier Deliverable - Autonomous Executive Intelligence

Usage:
    python ceo_briefing_generator.py [--output-dir PATH] [--weeks-back N]

Features:
    1. Audits Odoo accounting records (revenue, expenses, receivables)
    2. Analyzes completed tasks from Done folder
    3. Generates proactive suggestions for cost-cutting and bottlenecks
    4. Creates Monday_Morning_Briefing.md in Obsidian vault
"""

import os
import sys
import re
import json
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Any, Optional
from dotenv import load_dotenv

load_dotenv()

# Configuration
VAULT_DIR = Path(os.getenv("VAULT_PATH", "D:/zerohakathon")).resolve() / "Vault_Template"
DONE_DIR = VAULT_DIR / "Done"
LOGS_DIR = VAULT_DIR / "Logs"
REPORTS_DIR = VAULT_DIR / "Reports" / "Weekly_Briefings"
OUTPUT_DIR = VAULT_DIR


# =============================================================================
# Financial Data Collection from Odoo
# =============================================================================

def collect_financial_metrics(start_date: str, end_date: str) -> Dict[str, Any]:
    """
    Collect all financial metrics from Odoo for the reporting period.

    Args:
        start_date: YYYY-MM-DD format
        end_date: YYYY-MM-DD format

    Returns:
        Dictionary with all financial metrics
    """
    try:
        from odoo_connector import OdooConnector
    except ImportError:
        print("Warning: odoo_connector not found. Using mock data.")
        return _mock_financial_data()

    odoo = OdooConnector()
    if not odoo.authenticate():
        print("Warning: Failed to connect to Odoo. Using mock data.")
        return _mock_financial_data()

    metrics = {}

    try:
        # 1. Revenue from paid invoices
        # Note: Odoo domain is a flat list, not nested
        paid_invoice_ids = odoo.execute(
            'account.move', 'search',
            [
                ['move_type', '=', 'out_invoice'],
                ['payment_state', '=', 'paid'],
                ['invoice_date', '>=', start_date],
                ['invoice_date', '<=', end_date]
            ]
        ) or []

        paid_invoices = []
        if paid_invoice_ids:
            paid_invoices = odoo.execute(
                'account.move', 'read', paid_invoice_ids,
                fields=['name', 'partner_id', 'amount_total', 'invoice_date']
            ) or []

        metrics['revenue'] = {
            'total': sum(inv.get('amount_total', 0) for inv in paid_invoices),
            'invoice_count': len(paid_invoices),
            'invoices': paid_invoices
        }

        # 2. Outstanding receivables (unpaid invoices)
        unpaid_ids = odoo.execute(
            'account.move', 'search',
            [
                ['move_type', '=', 'out_invoice'],
                ['payment_state', 'in', ['not_paid', 'partial']],
                ['state', '=', 'posted']
            ]
        ) or []

        unpaid_invoices = []
        if unpaid_ids:
            unpaid_invoices = odoo.execute(
                'account.move', 'read', unpaid_ids,
                fields=['name', 'partner_id', 'amount_total', 'amount_residual',
                        'invoice_date', 'invoice_date_due']
            ) or []

        metrics['receivables'] = {
            'total_outstanding': sum(inv.get('amount_residual', 0) for inv in unpaid_invoices),
            'count': len(unpaid_invoices),
            'invoices': unpaid_invoices
        }

        # 3. Expenses (vendor bills paid)
        bill_ids = odoo.execute(
            'account.move', 'search',
            [
                ['move_type', '=', 'in_invoice'],
                ['payment_state', '=', 'paid'],
                ['invoice_date', '>=', start_date],
                ['invoice_date', '<=', end_date]
            ]
        ) or []

        paid_bills = []
        if bill_ids:
            paid_bills = odoo.execute(
                'account.move', 'read', bill_ids,
                fields=['name', 'partner_id', 'amount_total', 'invoice_date']
            ) or []

        metrics['expenses'] = {
            'total': sum(bill.get('amount_total', 0) for bill in paid_bills),
            'bill_count': len(paid_bills),
            'bills': paid_bills
        }

        # 4. Net profit
        metrics['net_profit'] = metrics['revenue']['total'] - metrics['expenses']['total']

        # 5. New customers this period
        customer_ids = odoo.execute(
            'res.partner', 'search',
            [
                ['customer_rank', '>', 0],
                ['create_date', '>=', start_date],
                ['create_date', '<=', end_date]
            ]
        ) or []

        new_customers = []
        if customer_ids:
            new_customers = odoo.execute(
                'res.partner', 'read', customer_ids,
                fields=['name', 'email', 'create_date']
            ) or []

        metrics['new_customers'] = {
            'count': len(new_customers),
            'customers': new_customers
        }

        # 6. Sales orders this period
        order_ids = odoo.execute(
            'sale.order', 'search',
            [
                ['date_order', '>=', start_date],
                ['date_order', '<=', end_date]
            ]
        ) or []

        sales_orders = []
        if order_ids:
            sales_orders = odoo.execute(
                'sale.order', 'read', order_ids,
                fields=['name', 'partner_id', 'amount_total', 'state', 'date_order']
            ) or []

        confirmed_orders = [o for o in sales_orders if o.get('state') in ['sale', 'done']]
        draft_orders = [o for o in sales_orders if o.get('state') == 'draft']

        metrics['sales_orders'] = {
            'total_value': sum(o.get('amount_total', 0) for o in confirmed_orders),
            'confirmed_count': len(confirmed_orders),
            'draft_count': len(draft_orders),
            'orders': sales_orders
        }

    except Exception as e:
        print(f"Error collecting Odoo metrics: {e}")
        return _mock_financial_data()

    return metrics


def _mock_financial_data() -> Dict[str, Any]:
    """Return mock financial data when Odoo is unavailable."""
    return {
        'revenue': {'total': 0, 'invoice_count': 0, 'invoices': []},
        'expenses': {'total': 0, 'bill_count': 0, 'bills': []},
        'receivables': {'total_outstanding': 0, 'count': 0, 'invoices': []},
        'net_profit': 0,
        'new_customers': {'count': 0, 'customers': []},
        'sales_orders': {'total_value': 0, 'confirmed_count': 0, 'draft_count': 0, 'orders': []}
    }


# =============================================================================
# Task Analysis from Done Folder
# =============================================================================

def analyze_completed_tasks(start_date: str, end_date: str) -> Dict[str, Any]:
    """
    Analyze tasks in the Done folder for the reporting period.
    """
    tasks = []

    if not DONE_DIR.exists():
        print(f"Warning: Done directory not found at {DONE_DIR}")
        return _empty_task_metrics()

    for file_path in DONE_DIR.glob("*.md"):
        if file_path.name == '.gitkeep':
            continue

        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()

            # Parse frontmatter
            frontmatter = _parse_frontmatter(content)

            # Get dates
            completed_date = frontmatter.get('completed', frontmatter.get('created', ''))

            # Filter by date range if we have a date
            if completed_date:
                task_date = completed_date[:10]  # Get YYYY-MM-DD portion
                if not (start_date <= task_date <= end_date):
                    continue

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

        except Exception as e:
            print(f"Warning: Error parsing {file_path.name}: {e}")
            continue

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


def _parse_frontmatter(content: str) -> Dict[str, str]:
    """Extract YAML-like frontmatter from markdown."""
    frontmatter = {}

    if content.startswith('---'):
        fm_end = content.find('---', 3)
        if fm_end > 0:
            fm_text = content[3:fm_end]
            for line in fm_text.strip().split('\n'):
                if ':' in line:
                    key, value = line.split(':', 1)
                    frontmatter[key.strip()] = value.strip().strip('"').strip("'")

    return frontmatter


def _empty_task_metrics() -> Dict[str, Any]:
    """Return empty task metrics."""
    return {
        'total_completed': 0,
        'by_source': {},
        'by_type': {},
        'by_priority': {},
        'tasks': []
    }


# =============================================================================
# Activity Log Analysis
# =============================================================================

def parse_activity_logs(start_date: str, end_date: str) -> Dict[str, Any]:
    """Parse activity logs for the period."""
    logs = {
        'total_actions': 0,
        'by_action': {},
        'errors': [],
        'approvals_requested': 0,
        'approvals_granted': 0
    }

    activity_log = LOGS_DIR / "activity.log"

    if activity_log.exists():
        try:
            with open(activity_log, 'r', encoding='utf-8') as f:
                for line in f:
                    parts = line.strip().split(' | ')
                    if len(parts) >= 2:
                        timestamp = parts[0][:10] if len(parts[0]) >= 10 else ''
                        if timestamp and start_date <= timestamp <= end_date:
                            logs['total_actions'] += 1
                            action = parts[1] if len(parts) > 1 else 'unknown'
                            logs['by_action'][action] = logs['by_action'].get(action, 0) + 1

                            if 'error' in line.lower():
                                logs['errors'].append(line.strip())

                            if 'approval_requested' in action.lower():
                                logs['approvals_requested'] += 1

                            if 'approved' in action.lower() or 'action_executed' in action.lower():
                                logs['approvals_granted'] += 1

        except Exception as e:
            print(f"Warning: Error reading activity log: {e}")

    return logs


# =============================================================================
# Bottleneck & Opportunity Analysis
# =============================================================================

def analyze_bottlenecks_and_savings(
    financial: Dict[str, Any],
    tasks: Dict[str, Any],
    logs: Dict[str, Any]
) -> Dict[str, List]:
    """
    AI-powered analysis to identify issues and opportunities.
    """
    insights = {
        'bottlenecks': [],
        'cost_cutting': [],
        'opportunities': [],
        'risks': []
    }

    today = datetime.now().strftime('%Y-%m-%d')

    # === BOTTLENECK DETECTION ===

    # 1. Aged receivables analysis
    receivables = financial.get('receivables', {})
    if receivables.get('invoices'):
        overdue = []
        for inv in receivables['invoices']:
            due_date = inv.get('invoice_date_due')
            if due_date and due_date < today:
                try:
                    days_overdue = (datetime.now() - datetime.strptime(due_date[:10], '%Y-%m-%d')).days
                    partner = inv.get('partner_id')
                    customer_name = partner[1] if isinstance(partner, (list, tuple)) and len(partner) > 1 else 'Unknown'
                    overdue.append({
                        'invoice': inv.get('name', 'N/A'),
                        'customer': customer_name,
                        'amount': inv.get('amount_residual', 0),
                        'days_overdue': days_overdue
                    })
                except (ValueError, TypeError):
                    continue

        if overdue:
            total_overdue = sum(o['amount'] for o in overdue)
            insights['bottlenecks'].append({
                'type': 'aged_receivables',
                'severity': 'high' if total_overdue > 10000 else 'medium',
                'description': f"{len(overdue)} overdue invoices totaling ${total_overdue:,.2f}",
                'recommendation': "Follow up on overdue accounts. Consider payment plans for large amounts.",
                'details': sorted(overdue, key=lambda x: x['amount'], reverse=True)[:5]
            })

    # 2. Task backlog analysis
    high_priority = tasks.get('by_priority', {}).get('high', 0)
    critical = tasks.get('by_priority', {}).get('critical', 0)

    if critical > 0:
        insights['bottlenecks'].append({
            'type': 'critical_backlog',
            'severity': 'high',
            'description': f"{critical} critical priority tasks processed (may indicate recurring issues)",
            'recommendation': "Review root causes of critical tasks. Implement preventive measures."
        })

    # 3. Error rate analysis
    total_actions = logs.get('total_actions', 0)
    error_count = len(logs.get('errors', []))
    if total_actions > 0 and error_count / total_actions > 0.1:
        insights['bottlenecks'].append({
            'type': 'high_error_rate',
            'severity': 'medium',
            'description': f"{error_count} errors out of {total_actions} actions ({error_count/total_actions*100:.1f}% error rate)",
            'recommendation': "Review error logs. Identify and fix recurring issues."
        })

    # === COST-CUTTING OPPORTUNITIES ===

    # 1. Expense ratio analysis
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
                'potential_savings': f"${expenses * 0.1:,.2f} (target: 10% reduction)"
            })
        elif expense_ratio > 0.5:
            insights['cost_cutting'].append({
                'type': 'expense_monitoring',
                'severity': 'low',
                'description': f"Expense ratio at {expense_ratio*100:.1f}% - within acceptable range",
                'recommendation': "Continue monitoring. Look for optimization opportunities."
            })

    # 2. Automation opportunities
    manual_tasks = tasks.get('by_source', {}).get('manual', 0)
    total_tasks = tasks.get('total_completed', 1) or 1

    if manual_tasks / total_tasks > 0.5:
        insights['cost_cutting'].append({
            'type': 'automation_opportunity',
            'severity': 'medium',
            'description': f"{manual_tasks}/{total_tasks} tasks ({manual_tasks/total_tasks*100:.0f}%) are manually created",
            'recommendation': "Increase automation. Connect more data sources to reduce manual entry.",
            'potential_savings': "Estimated 2-3 hours/week in manual task creation"
        })

    # 3. Quarterly subscription audit reminder
    if datetime.now().day <= 7:  # First week of month
        insights['cost_cutting'].append({
            'type': 'subscription_audit',
            'severity': 'low',
            'description': "Monthly reminder: Review recurring subscriptions and licenses",
            'recommendation': "Audit software subscriptions, unused licenses, and recurring charges."
        })

    # === GROWTH OPPORTUNITIES ===

    # 1. New customer trend
    new_customers = financial.get('new_customers', {}).get('count', 0)
    if new_customers > 0:
        insights['opportunities'].append({
            'type': 'customer_growth',
            'description': f"{new_customers} new customer(s) acquired this period",
            'recommendation': "Implement onboarding sequence. Request testimonials and referrals."
        })

    # 2. Draft orders (potential revenue)
    draft_orders = financial.get('sales_orders', {}).get('draft_count', 0)
    if draft_orders > 0:
        insights['opportunities'].append({
            'type': 'pending_orders',
            'description': f"{draft_orders} draft sales order(s) pending confirmation",
            'recommendation': "Follow up to convert drafts to confirmed orders."
        })

    # 3. High task completion rate
    if total_tasks > 20:
        insights['opportunities'].append({
            'type': 'productivity_win',
            'description': f"{total_tasks} tasks completed this period - strong productivity",
            'recommendation': "Document efficient workflows. Consider expanding automation."
        })

    # === RISK ALERTS ===

    # 1. Cash flow risk
    receivables_total = financial.get('receivables', {}).get('total_outstanding', 0)
    if revenue > 0 and receivables_total > revenue * 2:
        insights['risks'].append({
            'type': 'cash_flow',
            'severity': 'high',
            'description': f"Outstanding receivables (${receivables_total:,.2f}) exceed 2x weekly revenue",
            'recommendation': "Implement stricter payment terms. Consider invoice factoring."
        })

    # 2. Revenue decline warning
    if revenue == 0 and expenses > 0:
        insights['risks'].append({
            'type': 'no_revenue',
            'severity': 'high',
            'description': "No revenue recorded this period while expenses continue",
            'recommendation': "Urgent: Review sales pipeline. Activate lead generation."
        })

    return insights


# =============================================================================
# Briefing Document Generation
# =============================================================================

def generate_monday_briefing(
    financial: Dict[str, Any],
    tasks: Dict[str, Any],
    insights: Dict[str, List],
    logs: Dict[str, Any],
    period_start: str,
    period_end: str
) -> str:
    """Generate the Monday Morning Briefing markdown document."""

    today = datetime.now().strftime('%Y-%m-%d')
    generated_time = datetime.now().strftime('%Y-%m-%d %H:%M:%S')

    # Extract key metrics
    revenue = financial.get('revenue', {}).get('total', 0)
    expenses = financial.get('expenses', {}).get('total', 0)
    net_profit = financial.get('net_profit', 0)
    receivables = financial.get('receivables', {}).get('total_outstanding', 0)
    tasks_completed = tasks.get('total_completed', 0)
    new_customers = financial.get('new_customers', {}).get('count', 0)

    # Determine overall status
    risk_count = len([r for r in insights.get('risks', []) if r.get('severity') == 'high'])
    bottleneck_count = len([b for b in insights.get('bottlenecks', []) if b.get('severity') == 'high'])

    if net_profit > 0 and risk_count == 0 and bottleneck_count == 0:
        status_emoji = "🟢"
        status_text = "Healthy"
    elif net_profit >= 0 and risk_count == 0:
        status_emoji = "🟡"
        status_text = "Attention Needed"
    else:
        status_emoji = "🔴"
        status_text = "Action Required"

    # Build the briefing
    briefing = f"""---
generated: {generated_time}
period_start: {period_start}
period_end: {period_end}
type: ceo_briefing
status: {status_text.lower().replace(' ', '_')}
revenue: {revenue}
expenses: {expenses}
net_profit: {net_profit}
tasks_completed: {tasks_completed}
---

# Monday Morning Briefing

**Week of {period_start} to {period_end}**

**Overall Status:** {status_emoji} {status_text}

---

## Executive Summary

| Metric | This Week | Status |
|--------|-----------|--------|
| **Revenue** | ${revenue:,.2f} | {"📈" if revenue > 0 else "📉"} |
| **Expenses** | ${expenses:,.2f} | {"⚠️" if revenue > 0 and expenses > revenue * 0.7 else "✅"} |
| **Net Profit** | ${net_profit:,.2f} | {"✅" if net_profit > 0 else "🔴" if net_profit < 0 else "➖"} |
| **Outstanding AR** | ${receivables:,.2f} | {"⚠️" if revenue > 0 and receivables > revenue * 2 else "✅"} |
| **Tasks Completed** | {tasks_completed} | {"✅" if tasks_completed > 0 else "➖"} |
| **New Customers** | {new_customers} | {"📈" if new_customers > 0 else "➖"} |

---

## 1. Financial Performance

### Revenue Breakdown

| Source | Amount | Count |
|--------|--------|-------|
| Paid Invoices | ${revenue:,.2f} | {financial.get('revenue', {}).get('invoice_count', 0)} |
| Confirmed Sales Orders | ${financial.get('sales_orders', {}).get('total_value', 0):,.2f} | {financial.get('sales_orders', {}).get('confirmed_count', 0)} |

### Accounts Receivable

| Status | Amount | Count |
|--------|--------|-------|
| Outstanding | ${receivables:,.2f} | {financial.get('receivables', {}).get('count', 0)} |
| Draft Orders (Pipeline) | - | {financial.get('sales_orders', {}).get('draft_count', 0)} |

### Expenses

| Category | Amount | Count |
|----------|--------|-------|
| Vendor Bills Paid | ${expenses:,.2f} | {financial.get('expenses', {}).get('bill_count', 0)} |

**Profit Margin:** {(net_profit/revenue*100) if revenue > 0 else 0:.1f}%

---

## 2. Tasks Completed

**Total:** {tasks_completed} tasks processed this week

"""

    # Task breakdown by source
    if tasks.get('by_source'):
        briefing += "### By Source\n"
        for source, count in sorted(tasks['by_source'].items(), key=lambda x: x[1], reverse=True):
            briefing += f"- **{source.replace('_', ' ').title()}:** {count}\n"
        briefing += "\n"

    # Task breakdown by type
    if tasks.get('by_type'):
        briefing += "### By Type\n"
        for task_type, count in sorted(tasks['by_type'].items(), key=lambda x: x[1], reverse=True):
            briefing += f"- **{task_type.replace('_', ' ').title()}:** {count}\n"
        briefing += "\n"

    # Task breakdown by priority
    if tasks.get('by_priority'):
        briefing += "### By Priority\n"
        priority_order = ['critical', 'high', 'medium', 'low']
        priority_emojis = {'critical': '🔴', 'high': '🟠', 'medium': '🟡', 'low': '🟢'}
        for priority in priority_order:
            count = tasks['by_priority'].get(priority, 0)
            if count > 0:
                emoji = priority_emojis.get(priority, '')
                briefing += f"- {emoji} **{priority.title()}:** {count}\n"
        briefing += "\n"

    # Bottlenecks section
    briefing += """---

## 3. Bottlenecks Identified

"""

    if insights.get('bottlenecks'):
        for i, bottleneck in enumerate(insights['bottlenecks'], 1):
            severity_emoji = {'high': '🔴', 'medium': '🟡', 'low': '🟢'}.get(
                bottleneck.get('severity', 'medium'), '⚪')
            briefing += f"""### {i}. {bottleneck.get('type', 'Issue').replace('_', ' ').title()} {severity_emoji}

**Issue:** {bottleneck.get('description', 'N/A')}

**Recommendation:** {bottleneck.get('recommendation', 'N/A')}

"""
            # Add details if available (e.g., overdue invoices)
            if bottleneck.get('details'):
                briefing += "**Top Items:**\n"
                for detail in bottleneck['details'][:3]:
                    if 'invoice' in detail:
                        briefing += f"- {detail.get('invoice', 'N/A')}: ${detail.get('amount', 0):,.2f} ({detail.get('days_overdue', 0)} days overdue)\n"
                briefing += "\n"
    else:
        briefing += "✅ *No significant bottlenecks identified this week.*\n\n"

    # Cost-cutting section
    briefing += """---

## 4. Cost-Cutting Opportunities

"""

    if insights.get('cost_cutting'):
        for i, opportunity in enumerate(insights['cost_cutting'], 1):
            severity_emoji = {'high': '🔴', 'medium': '🟡', 'low': '🟢'}.get(
                opportunity.get('severity', 'low'), '⚪')
            briefing += f"""### {i}. {opportunity.get('type', 'Opportunity').replace('_', ' ').title()} {severity_emoji}

**Finding:** {opportunity.get('description', 'N/A')}

**Action:** {opportunity.get('recommendation', 'N/A')}

"""
            if opportunity.get('potential_savings'):
                briefing += f"**Potential Savings:** {opportunity['potential_savings']}\n\n"
    else:
        briefing += "✅ *Operations running efficiently. No immediate cost-cutting needs.*\n\n"

    # Opportunities section
    briefing += """---

## 5. Growth Opportunities

"""

    if insights.get('opportunities'):
        for opportunity in insights['opportunities']:
            briefing += f"""### {opportunity.get('type', '').replace('_', ' ').title()}

**Observation:** {opportunity.get('description', '')}

**Recommended Action:** {opportunity.get('recommendation', '')}

"""
    else:
        briefing += "*No specific growth opportunities flagged this week.*\n\n"

    # Risk alerts section
    briefing += """---

## 6. Risk Alerts

"""

    if insights.get('risks'):
        for risk in insights['risks']:
            severity_emoji = {'high': '🔴', 'medium': '🟡', 'low': '🟢'}.get(
                risk.get('severity', 'medium'), '⚪')
            briefing += f"""### {severity_emoji} {risk.get('type', 'Risk').replace('_', ' ').title()}

**Alert:** {risk.get('description', 'N/A')}

**Mitigation:** {risk.get('recommendation', 'N/A')}

"""
    else:
        briefing += "✅ *No critical risks identified this week.*\n\n"

    # Action items section
    briefing += """---

## 7. Recommended Action Items

"""

    action_items = []

    # High priority items from insights
    for bottleneck in insights.get('bottlenecks', []):
        if bottleneck.get('severity') in ['high', 'critical']:
            action_items.append(f"🔴 Address: {bottleneck.get('description', '')[:80]}")

    for risk in insights.get('risks', []):
        action_items.append(f"⚠️ Mitigate: {risk.get('description', '')[:80]}")

    for opportunity in insights.get('opportunities', []):
        action_items.append(f"📈 Pursue: {opportunity.get('description', '')[:80]}")

    # Add cost-cutting with high/medium severity
    for saving in insights.get('cost_cutting', []):
        if saving.get('severity') in ['high', 'medium']:
            action_items.append(f"💰 Review: {saving.get('description', '')[:80]}")

    if action_items:
        for item in action_items[:10]:
            briefing += f"- [ ] {item}\n"
    else:
        briefing += "- [ ] Review this briefing and acknowledge\n"
        briefing += "- [ ] Plan priorities for the week\n"
        briefing += "- [ ] Follow up on any pending approvals\n"

    # New customers appendix
    briefing += f"""

---

## Appendix A: New Customers

"""

    customers = financial.get('new_customers', {}).get('customers', [])
    if customers:
        briefing += "| Name | Email | Added |\n|------|-------|-------|\n"
        for customer in customers[:10]:
            name = customer.get('name', 'N/A')
            email = customer.get('email', 'N/A') or 'N/A'
            created = customer.get('create_date', 'N/A')
            if created and len(created) >= 10:
                created = created[:10]
            briefing += f"| {name} | {email} | {created} |\n"
    else:
        briefing += "*No new customers this period.*\n"

    # Agent activity summary
    briefing += f"""

---

## Appendix B: Agent Activity

| Metric | Count |
|--------|-------|
| Total Actions | {logs.get('total_actions', 0)} |
| Approvals Requested | {logs.get('approvals_requested', 0)} |
| Approvals Granted | {logs.get('approvals_granted', 0)} |
| Errors Logged | {len(logs.get('errors', []))} |

"""

    # Footer
    briefing += f"""
---

*Generated automatically by CEO Briefing Skill*
*Report Date: {today}*
*Data Period: {period_start} to {period_end}*
*Next Briefing: {(datetime.now() + timedelta(days=7)).strftime('%Y-%m-%d')}*
"""

    return briefing


# =============================================================================
# Main Execution
# =============================================================================

def get_week_dates(weeks_back: int = 0) -> tuple:
    """Get start and end dates for the reporting week."""
    today = datetime.now()

    # Find last Monday (or this Monday if today is Monday)
    days_since_monday = today.weekday()
    if days_since_monday == 0 and today.hour < 6:
        # If it's Monday before 6 AM, report on previous week
        days_since_monday = 7

    last_monday = today - timedelta(days=days_since_monday + (7 * weeks_back))
    last_sunday = last_monday + timedelta(days=6)

    return (
        last_monday.strftime('%Y-%m-%d'),
        last_sunday.strftime('%Y-%m-%d')
    )


def main(output_dir: Path = None, weeks_back: int = 0) -> Optional[Path]:
    """Generate the Monday Morning Briefing."""

    output_dir = output_dir or OUTPUT_DIR

    # Ensure directories exist
    output_dir.mkdir(parents=True, exist_ok=True)
    REPORTS_DIR.mkdir(parents=True, exist_ok=True)

    period_start, period_end = get_week_dates(weeks_back)

    print("=" * 60)
    print("CEO Weekly Briefing Generator")
    print("=" * 60)
    print(f"Report Period: {period_start} to {period_end}")
    print(f"Output Directory: {output_dir}")
    print("=" * 60)

    # Step 1: Collect financial data
    print("\n[1/5] Collecting financial metrics from Odoo...")
    financial = collect_financial_metrics(period_start, period_end)
    print(f"      Revenue: ${financial.get('revenue', {}).get('total', 0):,.2f}")
    print(f"      Expenses: ${financial.get('expenses', {}).get('total', 0):,.2f}")

    # Step 2: Analyze completed tasks
    print("\n[2/5] Analyzing completed tasks...")
    tasks = analyze_completed_tasks(period_start, period_end)
    print(f"      Tasks completed: {tasks.get('total_completed', 0)}")

    # Step 3: Parse activity logs
    print("\n[3/5] Reviewing activity logs...")
    logs = parse_activity_logs(period_start, period_end)
    print(f"      Total actions: {logs.get('total_actions', 0)}")

    # Step 4: Generate insights
    print("\n[4/5] Generating insights and recommendations...")
    insights = analyze_bottlenecks_and_savings(financial, tasks, logs)
    print(f"      Bottlenecks: {len(insights.get('bottlenecks', []))}")
    print(f"      Cost-cutting opportunities: {len(insights.get('cost_cutting', []))}")
    print(f"      Risks: {len(insights.get('risks', []))}")

    # Step 5: Generate briefing document
    print("\n[5/5] Composing briefing document...")
    briefing = generate_monday_briefing(
        financial, tasks, insights, logs, period_start, period_end
    )

    # Save main briefing
    output_file = output_dir / "Monday_Morning_Briefing.md"
    with open(output_file, 'w', encoding='utf-8') as f:
        f.write(briefing)
    print(f"\n[OK] Briefing saved to: {output_file}")

    # Save dated archive copy
    archive_file = REPORTS_DIR / f"Briefing_{period_start}.md"
    with open(archive_file, 'w', encoding='utf-8') as f:
        f.write(briefing)
    print(f"[OK] Archive copy saved to: {archive_file}")

    # Log the generation
    try:
        activity_log = LOGS_DIR / "activity.log"
        with open(activity_log, 'a', encoding='utf-8') as f:
            timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            f.write(f"{timestamp} | ceo_briefing_generated | {output_file.name} | success\n")
    except Exception as e:
        print(f"Warning: Could not log activity: {e}")

    print("\n" + "=" * 60)
    print("Briefing generation complete!")
    print("=" * 60)

    return output_file


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(
        description="Generate CEO Weekly Briefing from Odoo and Vault data"
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=OUTPUT_DIR,
        help=f"Output directory (default: {OUTPUT_DIR})"
    )
    parser.add_argument(
        "--weeks-back",
        type=int,
        default=0,
        help="Generate report for N weeks ago (0=current week, 1=last week, etc.)"
    )
    parser.add_argument(
        "--test",
        action="store_true",
        help="Run in test mode with sample data"
    )

    args = parser.parse_args()

    try:
        result = main(args.output_dir, args.weeks_back)
        if result:
            print(f"\nOpen the briefing: {result}")
    except KeyboardInterrupt:
        print("\nBriefing generation cancelled.")
    except Exception as e:
        print(f"\nError generating briefing: {e}")
        sys.exit(1)
