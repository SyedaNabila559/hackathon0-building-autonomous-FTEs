"""
Send approval email for LinkedIn post.
"""

import smtplib
import os
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from dotenv import load_dotenv

load_dotenv()

GMAIL_USER = os.getenv('GMAIL_USER')
GMAIL_PASS = os.getenv('GMAIL_PASS')

if not GMAIL_USER or not GMAIL_PASS:
    print('ERROR: Gmail credentials not found')
    exit(1)

# Create message
msg = MIMEMultipart('alternative')
msg['Subject'] = 'APPROVAL REQUIRED: LinkedIn Post - AI Employee'
msg['From'] = GMAIL_USER
msg['To'] = GMAIL_USER  # Sending to yourself

# Email body
text_content = """
APPROVAL REQUIRED: LinkedIn Post - AI Employee
================================================

Hello,

Your AI Executive Assistant has drafted a LinkedIn post that requires your approval before publication.

POST SUMMARY
------------
Topic: Building a Digital FTE (Full-Time Employee) with Claude Code & Odoo

Key Points:
- How the AI agent monitors WhatsApp and Gmail for incoming tasks
- Automated processing and prioritization of messages
- Odoo ERP integration for contacts, invoices, and records
- Human-in-the-Loop safety (approvals for payments >$100, new contacts, contracts)
- Weekly CEO Briefings with revenue summaries and recommendations

Target Audience: Business owners, tech leaders, automation enthusiasts
Tone: Professional thought leadership
Hashtags: #AIAutomation #DigitalTransformation #ClaudeAI #Odoo #FutureOfWork

IMAGE NOTE
----------
The HuggingFace API requires upgraded permissions to generate images.
Please manually add an image before approval. Suggested: "Futuristic AI Robot working on a business dashboard"

TO APPROVE
----------
1. Review the full draft at: D:/zerohakathon/Vault_Template/Needs_Action/post_ai_employee.md
2. Make any desired edits
3. Add an image (optional but recommended)
4. Move the file to: D:/zerohakathon/Vault_Template/Approved/
5. Update the frontmatter with:
   - approved: true
   - approved_by: [Your Name]
   - approved_date: 2026-01-28

The linkedin_publisher.py script will automatically detect the approved file and publish to LinkedIn.

---
This is an automated message from your AI Executive Assistant.
Human oversight is required for all publications.
"""

html_content = """
<html>
<body style="font-family: Arial, sans-serif; max-width: 600px; margin: 0 auto;">
<div style="background: #f0f4f8; padding: 20px; border-radius: 8px;">
<h1 style="color: #1a365d; border-bottom: 2px solid #3182ce; padding-bottom: 10px;">
APPROVAL REQUIRED: LinkedIn Post
</h1>

<p>Hello,</p>

<p>Your <strong>AI Executive Assistant</strong> has drafted a LinkedIn post that requires your approval before publication.</p>

<div style="background: white; padding: 15px; border-radius: 8px; margin: 20px 0; border-left: 4px solid #3182ce;">
<h2 style="color: #2d3748; margin-top: 0;">Post Summary</h2>
<p><strong>Topic:</strong> Building a Digital FTE (Full-Time Employee) with Claude Code & Odoo</p>

<h3 style="color: #4a5568;">Key Points:</h3>
<ul>
<li>AI agent monitors WhatsApp and Gmail for incoming tasks</li>
<li>Automated processing and prioritization of messages</li>
<li>Odoo ERP integration for contacts, invoices, and records</li>
<li>Human-in-the-Loop safety (approvals for payments &gt;$100, new contacts)</li>
<li>Weekly CEO Briefings with revenue summaries</li>
</ul>
</div>

<div style="background: #fef3c7; padding: 15px; border-radius: 8px; margin: 20px 0;">
<h3 style="color: #92400e; margin-top: 0;">Image Note</h3>
<p>The HuggingFace API requires upgraded permissions. Please manually add an image before approval.</p>
<p><em>Suggested: "Futuristic AI Robot working on a business dashboard"</em></p>
</div>

<div style="background: #c6f6d5; padding: 15px; border-radius: 8px; margin: 20px 0;">
<h3 style="color: #276749; margin-top: 0;">To Approve</h3>
<ol>
<li>Review the full draft in the Needs_Action folder</li>
<li>Make any desired edits</li>
<li>Add an image (recommended)</li>
<li>Move the file to the <strong>Approved</strong> folder</li>
<li>Update frontmatter: <code>approved: true</code></li>
</ol>
</div>

<p style="color: #718096; font-size: 12px; margin-top: 30px; border-top: 1px solid #e2e8f0; padding-top: 15px;">
This is an automated message from your AI Executive Assistant.<br>
Human oversight is required for all publications.
</p>
</div>
</body>
</html>
"""

msg.attach(MIMEText(text_content, 'plain'))
msg.attach(MIMEText(html_content, 'html'))

# Send email
try:
    server = smtplib.SMTP_SSL('smtp.gmail.com', 465)
    server.login(GMAIL_USER, GMAIL_PASS)
    server.sendmail(GMAIL_USER, GMAIL_USER, msg.as_string())
    server.quit()
    print('SUCCESS: Approval email sent to', GMAIL_USER)
except Exception as e:
    print(f'ERROR: Failed to send email - {e}')
