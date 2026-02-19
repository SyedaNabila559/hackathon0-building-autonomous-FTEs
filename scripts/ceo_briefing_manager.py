import os
import glob
import subprocess
from datetime import datetime, timedelta

"""CEO Briefing Manager script."""

# Absolute paths
ROOT_PATH = r'D:\zerohakathon'
VAULT_PATH = os.path.join(ROOT_PATH, 'Vault_Template')
DONE_PATH = os.path.join(VAULT_PATH, 'Done')
REPORTS_PATH = os.path.join(VAULT_PATH, 'Reports', 'Weekly_Briefings')

# Ensure directories exist
os.makedirs(REPORTS_PATH, exist_ok=True)

def get_recent_done_files(days=7):
    """Get .md files from Done folder modified in last N days."""
    cutoff = datetime.now() - timedelta(days=days)
    recent = []
    for file_path in glob.glob(os.path.join(DONE_PATH, '*.md')):
        mtime = datetime.fromtimestamp(os.path.getmtime(file_path))
        if mtime > cutoff:
            recent.append(file_path)
    return recent

def find_bank_csv(vault_path):
    """Search for bank_transactions.csv in vault recursively."""
    for root, dirs, files in os.walk(vault_path):
        if 'bank_transactions.csv' in files:
            return os.path.join(root, 'bank_transactions.csv')
    return None

def summarize_file(file_path, max_chars=300):
    """Summarize file content to max chars."""
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
            if len(content) > max_chars:
                lines = content.split('\n')[:5]
                summary = '\n'.join(lines) + '\n...'
            else:
                summary = content
            return summary
    except Exception as e:
        return f"Error reading {os.path.basename(file_path)}: {str(e)}"

def generate_briefing(recent_files, bank_file):
    """Generate briefing content."""
    today_str = datetime.now().strftime('%Y-%m-%d')
    content = f'# CEO Weekly Briefing - {today_str}\n\n'
    content += f'**Generated:** {today_str}\n\n'

    content += '## Recent Completed Tasks (Last 7 Days)\n\n'
    if recent_files:
        for file_path in sorted(recent_files, key=os.path.getmtime, reverse=True):
            summary = summarize_file(file_path)
            basename = os.path.basename(file_path)
            content += f'### {basename}\n'
            content += f'{summary}\n\n'
    else:
        content += '*No recent completed tasks.*\n\n'

    if bank_file:
        content += '## Bank Transactions\n\n'
        try:
            with open(bank_file, 'r', encoding='utf-8') as f:
                csv_content = f.read()
                content += '```csv\n' + csv_content + '\n```\n\n'
        except Exception as e:
            content += f'Error reading bank file: {str(e)}\n\n'
    else:
        content += '*No bank_transactions.csv found.*\n\n'

    return content, today_str

# Main execution
print('Starting CEO Briefing Manager...')

recent_files = get_recent_done_files()
bank_file = find_bank_csv(VAULT_PATH)

# If no bank file, attempt to fetch Odoo data via generator
if not bank_file:
    print('No bank_transactions.csv found. Running ceo_briefing_generator.py to fetch Odoo data...')
    generator_path = os.path.join(ROOT_PATH, 'ceo_briefing_generator.py')
    try:
        result = subprocess.run(['python', generator_path], cwd=ROOT_PATH, capture_output=True, text=True, timeout=60)
        if result.returncode == 0:
            print('Generator executed successfully.')
            # Re-check for bank file after generator
            bank_file = find_bank_csv(VAULT_PATH)
        else:
            print(f'Generator failed: {result.stderr}')
    except subprocess.TimeoutExpired:
        print('Generator timed out.')
    except FileNotFoundError:
        print('ceo_briefing_generator.py not found.')

content, today_str = generate_briefing(recent_files, bank_file)

briefing_file = os.path.join(REPORTS_PATH, f'{today_str}_CEO_Briefing.md')

try:
    with open(briefing_file, 'w', encoding='utf-8') as f:
        f.write(content)
    print(f'CEO Briefing generated successfully: {briefing_file}')
except Exception as e:
    print(f'Error writing briefing: {str(e)}')

"""
Windows Task Scheduler command to run every Sunday at 11:59 PM:
schtasks /create /tn "CEO Weekly Briefing" /tr "python D:\\zerohakathon\\scripts\\ceo_briefing_manager.py" /sc weekly /d SUN /st 23:59 /f
"""