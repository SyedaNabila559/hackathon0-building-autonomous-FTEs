from flask import Flask, request
from twilio.rest import Client
import os
import xmlrpc.client
from dotenv import load_dotenv

# .env file load karein
load_dotenv()
app = Flask(__name__)

# Credentials uthayein
TWILIO_SID = os.getenv('TWILIO_ACCOUNT_SID')
TWILIO_TOKEN = os.getenv('TWILIO_AUTH_TOKEN')
FROM_WHATSAPP = f"whatsapp:{os.getenv('TWILIO_WHATSAPP_NUMBER')}"
CEO_PHONE = f"whatsapp:{os.getenv('CEO_PHONE_NUMBER')}"

# Odoo Connection Details
ODOO_URL = os.getenv('ODOO_URL')
ODOO_DB = os.getenv('ODOO_DB')
ODOO_USERNAME = os.getenv('ODOO_USERNAME')
ODOO_PASSWORD = os.getenv('ODOO_PASSWORD')

client = Client(TWILIO_SID, TWILIO_TOKEN)

# --- LOGIC 1: Odoo se Real Data nikaal kar Report bhejna ---
def send_ai_report():
    try:
        common = xmlrpc.client.ServerProxy(f'{ODOO_URL}/xmlrpc/2/common')
        uid = common.authenticate(ODOO_DB, ODOO_USERNAME, ODOO_PASSWORD, {})
        
        if uid:
            models = xmlrpc.client.ServerProxy(f'{ODOO_URL}/xmlrpc/2/object')
            
            # 1. Posted Invoices search karein
            invoice_ids = models.execute_kw(ODOO_DB, uid, ODOO_PASSWORD,
                'account.move', 'search', [[['move_type', '=', 'out_invoice'], ['state', '=', 'posted']]])
            
            if invoice_ids:
                # 2. Data Read karein (Fix: invoice_ids ko list mein wrap kiya hai)
                invoices = models.execute_kw(ODOO_DB, uid, ODOO_PASSWORD,
                    'account.move', 'read', [invoice_ids], {'fields': ['amount_total']})
                
                total = sum(inv.get('amount_total', 0) for inv in invoices)
                report_text = f"CEO Sahab! Odoo Live Revenue: Rs. {total:,.2f}"
            else:
                report_text = "CEO Sahab! Odoo mein filhaal koi posted invoices nahi hain."
        else:
            report_text = "Odoo Authentication failed! Please check credentials."

        # WhatsApp Message bhejna
        message = client.messages.create(body=report_text, from_=FROM_WHATSAPP, to=CEO_PHONE)
        print(f"✅ Report Sent to CEO! SID: {message.sid} | Revenue: {total if 'total' in locals() else 0}")
        
    except Exception as e:
        print(f"❌ Odoo Report Error: {e}")

# --- LOGIC 2: WhatsApp Message ko Odoo CRM mein save karna ---
def save_to_odoo(sender, content):
    try:
        common = xmlrpc.client.ServerProxy(f'{ODOO_URL}/xmlrpc/2/common')
        uid = common.authenticate(ODOO_DB, ODOO_USERNAME, ODOO_PASSWORD, {})
        
        if uid:
            models = xmlrpc.client.ServerProxy(f'{ODOO_URL}/xmlrpc/2/object')
            # WhatsApp message ko Odoo CRM Lead mein create karna
            lead_id = models.execute_kw(ODOO_DB, uid, ODOO_PASSWORD, 'crm.lead', 'create', [{
                'name': f"WhatsApp Task: {content[:30]}...",
                'description': f"From: {sender}\nMessage: {content}",
                'contact_name': sender
            }])
            print(f"✅ Message saved in Odoo CRM! Lead ID: {lead_id}")
    except Exception as e:
        print(f"❌ Odoo CRM Save Error: {e}")

@app.route("/whatsapp", methods=['POST'])
def whatsapp_webhook():
    message_body = request.form.get('Body')
    sender_number = request.form.get('From')

    if message_body:
        print(f"📩 Received: {message_body} from {sender_number}")
        
        # Agar 'report' keyword ho to report bhejein
        if "report" in message_body.lower():
            send_ai_report()
        else:
            # Warna Odoo CRM mein save karein
            save_to_odoo(sender_number, message_body)
            
        return "OK", 200
    
    return "No Data", 400

if __name__ == "__main__":
    print("🚀 AI Agent is live! Listening for WhatsApp & Connecting to Odoo...")
    app.run(port=5000, debug=True)