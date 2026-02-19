import os
import re
import requests
from pathlib import Path
from dotenv import load_dotenv
from twilio.rest import Client 

load_dotenv()

# Config
ACCESS_TOKEN = os.getenv("LINKEDIN_ACCESS_TOKEN")
PERSON_ID = os.getenv("LINKEDIN_PERSON_ID")
VAULT_BASE = Path("D:/zerohakathon/Vault_Template")
APPROVED_DIR = VAULT_BASE / "Approved"
DONE_DIR = VAULT_BASE / "Done"

# Twilio Config
TWILIO_SID = os.getenv('TWILIO_ACCOUNT_SID')
TWILIO_TOKEN = os.getenv('TWILIO_AUTH_TOKEN')
FROM_WHATSAPP = f"whatsapp:{os.getenv('TWILIO_WHATSAPP_NUMBER')}"
CEO_PHONE = f"whatsapp:{os.getenv('CEO_PHONE_NUMBER')}"
twilio_client = Client(TWILIO_SID, TWILIO_TOKEN)

def send_whatsapp_status(message):
    try:
        twilio_client.messages.create(body=message, from_=FROM_WHATSAPP, to=CEO_PHONE)
        print("📲 WhatsApp notification sent!")
    except Exception as e:
        print(f"⚠️ WhatsApp Notify Error: {e}")

def publish_to_linkedin(text, image_path=None):
    headers = {
        "Authorization": f"Bearer {ACCESS_TOKEN}",
        "X-Restli-Protocol-Version": "2.0.0"
    }
    author = f"urn:li:person:{PERSON_ID}"

    asset_id = None
    if image_path and os.path.exists(image_path):
        try:
            print(f"Uploading image: {image_path}")
            reg_url = "https://api.linkedin.com/v2/assets?action=registerUpload"
            reg_payload = {
                "registerUploadRequest": {
                    "recipes": ["urn:li:digitalmediaRecipe:feedshare-image"],
                    "owner": author,
                    "serviceRelationships": [{"relationshipType": "OWNER", "identifier": "urn:li:userGeneratedContent"}]
                }
            }
            reg_res = requests.post(reg_url, headers=headers, json=reg_payload).json()
            upload_url = reg_res['value']['uploadMechanism']['com.linkedin.digitalmedia.uploading.MediaUploadHttpRequest']['uploadUrl']
            asset_id = reg_res['value']['asset']

            with open(image_path, 'rb') as f:
                requests.put(upload_url, data=f, headers={"Authorization": f"Bearer {ACCESS_TOKEN}"})
            print("Image uploaded successfully!")
        except Exception as e:
            print(f"⚠️ Image Upload Error: {e}")
            asset_id = None

    post_url = "https://api.linkedin.com/v2/ugcPosts"
    post_data = {
        "author": author,
        "lifecycleState": "PUBLISHED",
        "specificContent": {
            "com.linkedin.ugc.ShareContent": {
                "shareCommentary": {"text": text},
                "shareMediaCategory": "IMAGE" if asset_id else "NONE",
            }
        },
        "visibility": {"com.linkedin.ugc.MemberNetworkVisibility": "PUBLIC"}
    }
    
    if asset_id:
        post_data["specificContent"]["com.linkedin.ugc.ShareContent"]["media"] = [
            {"status": "READY", "media": asset_id, "title": {"text": "AI Generated Visual"}}
        ]

    response = requests.post(post_url, headers=headers, json=post_data)
    return response.status_code in [200, 201], response.text

def process_queue():
    for md_file in APPROVED_DIR.glob("*.md"):
        print(f"🚀 Processing: {md_file.name}")
        content = md_file.read_text(encoding="utf-8")
        
        # 1. Image extract karna
        img_match = re.search(r'image_url:\s*"(.*?)"', content)
        image_path = img_match.group(1) if img_match else None
        
        try:
            # 2. Robust Content Extraction logic
            if "## Post Content" in content:
                # Text ko headings ke darmiyan se ya end tak uthao
                post_body = content.split("## Post Content")[1].split("## Image Details")[0]
                # Agar section khali hai (jesa pichli baar line 15 par tha), to heading ke baad ka sab uthao
                if not post_body.strip():
                    post_body = content.split("## Post Content")[1]
            else:
                # Agar heading nahi mili to frontmatter ke baad ka saara text
                post_body = content.split("---")[-1]

            # Cleanup: Extra characters aur lines hatana
            post_body = re.sub(r'---', '', post_body).strip()
            post_body = post_body[:2990]

            if not post_body:
                print(f"⚠️ Warning: No content found in {md_file.name}. Skipping.")
                continue

            # 3. Publish
            success, msg = publish_to_linkedin(post_body, image_path)
            
            if success:
                print(f"✅ Posted successfully!")
                # Post live hone ka WhatsApp confirm
                alert_msg = f"🚀 *LinkedIn Update:* Your post '{md_file.name}' is now LIVE with content and image!"
                send_whatsapp_status(alert_msg)
                
                DONE_DIR.mkdir(parents=True, exist_ok=True)
                md_file.rename(DONE_DIR / md_file.name)
            else:
                print(f"❌ LinkedIn Error: {msg}")
                send_whatsapp_status(f"❌ *LinkedIn Error:* Failed to post {md_file.name}")
        except Exception as e:
            print(f"❌ Processing Error: {e}")

if __name__ == "__main__":
    process_queue()