import xmlrpc.client

# Odoo Details from your screenshots
url = "https://aiagent21.odoo.com"
db = "aiagent21"
username = "03312436713aa@gmail.com" # Updated from your screenshot
password = "e056c7e15c3faf26b8eb30dbcca77f407ba1b306" # Your API Key

print("Connecting to Odoo...")
try:
    common = xmlrpc.client.ServerProxy(f'{url}/xmlrpc/2/common')
    uid = common.authenticate(db, username, password, {})

    if not uid:
        print("❌ Login Failed! Username ya Key mein ab bhi koi masla hai.")
        exit()

    print(f"✅ Connected successfully! User ID: {uid}")
    models = xmlrpc.client.ServerProxy(f'{url}/xmlrpc/2/object')

    # Function to create and post
    def create_invoice(name, amount, type):
        inv_id = models.execute_kw(db, uid, password, 'account.move', 'create', [{
            'partner_id': 1, # Default partner
            'move_type': type,
            'invoice_date': '2026-01-29',
            'line_ids': [(0, 0, {'name': 'Test Item', 'price_unit': amount, 'quantity': 1})]
        }])
        models.execute_kw(db, uid, password, 'account.move', 'action_post', [inv_id])
        return inv_id

    # Creating Data
    create_invoice("Customer Sale 1", 2750, 'out_invoice')
    create_invoice("Customer Sale 2", 2750, 'out_invoice')
    create_invoice("Vendor Bill", 1200, 'in_invoice')

    print("\n[SUCCESS] 2 Invoices ($5,500) and 1 Bill ($1,200) created!")
    print("Now run: python D:\\zerohakathon\\ceo_briefing_generator.py")

except Exception as e:
    print(f"❌ Error: {str(e)}")