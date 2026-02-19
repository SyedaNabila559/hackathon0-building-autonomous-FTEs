import os
import requests
import time
from datetime import datetime
from pathlib import Path
from dotenv import load_dotenv
from twilio.rest import Client

load_dotenv()

# Configuration
HF_API_KEY = os.getenv('HUGGINGFACE_API_KEY')
HF_MODEL_ID = "stabilityai/stable-diffusion-xl-base-1.0"
VAULT_DIR = Path("D:/zerohakathon/Vault_Template")
NEEDS_ACTION_DIR = VAULT_DIR / "Needs_Action"
IMAGES_DIR = Path("D:/zerohakathon/generated_images")

# Twilio Credentials
TWILIO_SID = os.getenv('TWILIO_ACCOUNT_SID')
TWILIO_TOKEN = os.getenv('TWILIO_AUTH_TOKEN')
FROM_WHATSAPP = f"whatsapp:{os.getenv('TWILIO_WHATSAPP_NUMBER')}"
CEO_PHONE = f"whatsapp:{os.getenv('CEO_PHONE_NUMBER')}"
twilio_client = Client(TWILIO_SID, TWILIO_TOKEN)

# Ensure directories exist
IMAGES_DIR.mkdir(parents=True, exist_ok=True)
NEEDS_ACTION_DIR.mkdir(parents=True, exist_ok=True)

def generate_image(prompt: str, filename: str) -> dict:
    print(f"🎨 Model ID: {HF_MODEL_ID}")
    print(f"🚀 Prompt: {prompt[:60]}...")
    
    # FIX: Updated to the new Router Endpoint to avoid Error 410
    endpoint = f"https://router.huggingface.co/hf-inference/models/{HF_MODEL_ID}"
    headers = {"Authorization": f"Bearer {HF_API_KEY}"}
    
    for i in range(3):
        try:
            # Added use_cache: False to ensure we get a new image every time
            response = requests.post(
                endpoint, 
                headers=headers, 
                json={"inputs": prompt, "options": {"wait_for_model": True, "use_cache": False}}, 
                timeout=120
            )
            
            if response.status_code == 200:
                image_path = IMAGES_DIR / filename
                with open(image_path, 'wb') as f:
                    f.write(response.content)
                return {"success": True, "path": str(image_path), "filename": filename}
            
            elif response.status_code in [503, 429]:
                print(f"⏳ Model is busy or loading... Waiting 30s (Attempt {i+1}/3)")
                time.sleep(30)
            else:
                print(f"❌ Error {response.status_code}: {response.text}")
                break
        except Exception as e:
            print(f"⚠️ Network Error: {e}")
            
    return {"success": False, "error": "Hugging Face failed after retries"}

def create_markdown_draft(img_res, topic_text, md_filename):
    """Obsidian ke liye .md file create karna"""
    timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    img_path_str = img_res.get('path', 'pending').replace('\\', '/')
    
    content = f'''---
created: {timestamp}
status: pending_approval
image_url: "{img_path_str}"
image_status: {"generated" if img_res.get('success') else "failed"}
approved: false
---

# LinkedIn Post: My Autonomous AI Employee

## Post Content

---

{topic_text}

---

## Image Details
**Status:** {"✅ Generated" if img_res.get('success') else "❌ Failed"}
**Local Path:** {img_path_str}

## Approval Workflow
1. Review the content.
2. Move this file to `/Vault_Template/Approved/` to publish.
'''
    file_path = NEEDS_ACTION_DIR / md_filename
    with open(file_path, "w", encoding="utf-8") as f:
        f.write(content)
    return md_filename

def send_approval_email(img_res, md_filename, topic_text):
    try:
        import smtplib
        from email.mime.multipart import MIMEMultipart
        from email.mime.text import MIMEText
        from email.mime.base import MIMEBase
        from email import encoders

        GMAIL_USER = os.getenv('GMAIL_USER')
        GMAIL_PASS = os.getenv('GMAIL_PASS')
        CEO_EMAIL = os.getenv('CEO_EMAIL', GMAIL_USER)  # Default to self if not set

        msg = MIMEMultipart()
        msg['From'] = GMAIL_USER
        msg['To'] = CEO_EMAIL
        msg['Subject'] = f"LinkedIn Post Approval: {md_filename}"

        body = f"""
        Ma'am, new LinkedIn post draft ready for approval!

        Topic: {topic_text}

        Image: {img_res.get('path', 'No image')}

        File: Vault_Template/Needs_Action/{md_filename}

        Action: Review and move to Approved/ to publish.

        Image attached.
        """
        msg.attach(MIMEText(body, 'plain'))

        # Attach image if generated
        if img_res.get('success') and img_res.get('path'):
            with open(img_res['path'], "rb") as attachment:
                part = MIMEBase('application', 'octet-stream')
                part.set_payload(attachment.read())

            encoders.encode_base64(part)
            part.add_header(
                'Content-Disposition',
                f'attachment; filename= {img_res["filename"]}'
            )
            msg.attach(part)

        server = smtplib.SMTP('smtp.gmail.com', 587)
        server.starttls()
        server.login(GMAIL_USER, GMAIL_PASS)
        text = msg.as_string()
        server.sendmail(GMAIL_USER, CEO_EMAIL, text)
        server.quit()

        print("✅ Approval email sent!")
    except Exception as e:
        print(f"❌ Email send error: {e}")

def notify_whatsapp_draft_ready(file_name, img_status):
    try:
        msg = (
            f"🗞️ *New Draft Ready!*\n\n"
            f"Ma'am, LinkedIn post draft kar di gayi hai.\n"
            f"🖼️ *Image:* {img_status}\n"
            f"📂 *File:* {file_name}\n\n"
            f"Please review in *Obsidian* and move to *Approved* folder.\\nApproval email also sent."
        )
        twilio_client.messages.create(body=msg, from_=FROM_WHATSAPP, to=CEO_PHONE)
        print("✅ WhatsApp notification sent!")
    except Exception as e:
        print(f"❌ Twilio Error: {e}")

if __name__ == "__main__":
    # Topic
    my_topic = 'Data Science is the backbone of our AI Employee! 📊 From predictive analytics in Odoo to automated insights, we are turning raw data into strategic decisions.'
    
    # Prompt
    professional_prompt = (
        "Professional 3D data visualization scene: holographic dashboards showing predictive analytics, "
        "Odoo charts, AI insights graphs, data streams transforming into strategic decisions, "
        "neon blue and purple tones, futuristic office background, high-resolution, cinematic lighting, 8k."
    )
    
    img_filename = f"linkedin_post_{int(time.time())}.png"
    img_res = generate_image(professional_prompt, img_filename)
    
    timestamp_str = datetime.now().strftime('%Y%m%d_%H%M%S')
    md_name = f"Post_{timestamp_str}.md"
    
    md_name = create_markdown_draft(img_res, my_topic, md_name)

    send_approval_email(img_res, md_name, my_topic)

    img_text = "Generated Successfully" if img_res['success'] else "Failed"
    notify_whatsapp_draft_ready(md_name, img_text)