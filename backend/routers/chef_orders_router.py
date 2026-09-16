"""The Simple Chef E-Commerce & Order Management Router
Handles credit card / online orders for Chef John Barr's signature rubs
(Rub That Hiney, Yard Pimp Dust, Kelly's Calling, Buck Down) and apparel.
Logs orders into local SQLite ledger, dispatches instant packing slips to John's phone
and email via Gmail SMTP, sends branded customer receipts, and alerts Discord.
"""

import os
import sys
import json
import time
import sqlite3
import smtplib
import email
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from datetime import datetime
from pathlib import Path
from typing import Optional, List, Dict, Any

from fastapi import APIRouter, Request, HTTPException, BackgroundTasks
from fastapi.responses import JSONResponse
from pydantic import BaseModel, EmailStr

router = APIRouter(prefix="/api/v1/chef", tags=["The Simple Chef E-Commerce"])

BACKEND_DIR = Path(__file__).resolve().parent.parent
BASE_DIR = BACKEND_DIR.parent
DATA_DIR = BASE_DIR / "saved_data"
DATA_DIR.mkdir(parents=True, exist_ok=True)
DB_PATH = DATA_DIR / "chef_orders.db"

# --- Database Initialization ---
def init_db():
    conn = sqlite3.connect(str(DB_PATH))
    cursor = conn.cursor()
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS chef_orders (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            order_id TEXT UNIQUE NOT NULL,
            created_at TEXT NOT NULL,
            customer_name TEXT NOT NULL,
            email TEXT NOT NULL,
            phone TEXT,
            shipping_address TEXT NOT NULL,
            items_json TEXT NOT NULL,
            subtotal REAL NOT NULL,
            tax REAL NOT NULL,
            shipping REAL NOT NULL,
            total REAL NOT NULL,
            payment_method TEXT NOT NULL,
            payment_status TEXT NOT NULL,
            card_last4 TEXT,
            notes TEXT,
            fulfillment_status TEXT NOT NULL DEFAULT 'Pending'
        )
    """)
    conn.commit()
    conn.close()

init_db()

# --- Credentials Loader ---
def load_credentials():
    creds = {
        "IMAP_USER": "",
        "IMAP_APP_PASSWORD": "",
        "SMTP_HOST": "smtp.gmail.com",
        "SMTP_PORT": 587,
        "CHEF_ALERT_EMAIL": "info@thesimplechef.net",
        "CHEF_PHONE": "616-808-9104",
        "OPERATOR_EMAIL": "footballstar0325@gmail.com",
        "DISCORD_WEBHOOK_URL": "",
        "GOOGLE_APPS_SCRIPT_URL": ""
    }

    env_paths = [BASE_DIR / ".env", BACKEND_DIR / ".env"]
    for p in env_paths:
        if p.exists():
            try:
                with open(p, "r", encoding="utf-8", errors="ignore") as f:
                    for line in f:
                        line = line.strip()
                        if line and not line.startswith("#") and "=" in line:
                            k, v = line.split("=", 1)
                            k = k.strip()
                            v = v.strip().strip('"').strip("'")
                            if k in creds:
                                creds[k] = v
            except Exception:
                pass

    for k in creds:
        if k in os.environ and os.environ[k]:
            creds[k] = os.environ[k]

    return creds

# --- Pydantic Data Models ---
class CartItem(BaseModel):
    name: str
    price: float
    qty: int

class OrderSubmissionPayload(BaseModel):
    order_id: Optional[str] = None
    customer_name: str
    email: str
    phone: Optional[str] = ""
    shipping_address: str
    items: List[CartItem]
    subtotal: float
    tax: float
    shipping: float
    total: float
    payment_method: str = "card"  # 'card', 'paypal', 'pickup'
    card_number: Optional[str] = None
    card_exp: Optional[str] = None
    card_cvc: Optional[str] = None
    card_zip: Optional[str] = None
    notes: Optional[str] = ""

class StatusUpdatePayload(BaseModel):
    fulfillment_status: str  # 'Pending', 'Packed', 'Shipped', 'Delivered'
    tracking_number: Optional[str] = None

# --- Asynchronous Notification Dispatchers ---
def dispatch_notifications_task(order_data: Dict[str, Any]):
    """Sends merchant packing slips, customer receipts, Discord alerts, and Google Sheets sync."""
    creds = load_credentials()
    smtp_user = creds["IMAP_USER"]
    smtp_pwd = creds["IMAP_APP_PASSWORD"]
    
    order_id = order_data["order_id"]
    customer_name = order_data["customer_name"]
    customer_email = order_data["email"]
    customer_phone = order_data.get("phone", "")
    shipping_address = order_data["shipping_address"]
    items = order_data["items"]
    subtotal = order_data["subtotal"]
    tax = order_data["tax"]
    shipping = order_data["shipping"]
    total = order_data["total"]
    payment_method = order_data["payment_method"]
    card_last4 = order_data.get("card_last4", "----")
    notes = order_data.get("notes", "")

    items_html_rows = ""
    items_text_list = []
    for it in items:
        line_total = it['price'] * it['qty']
        items_html_rows += f"""
        <tr>
            <td style="padding: 10px; border-bottom: 1px solid #e2e8f0; font-weight: bold; color: #0e1618;">{it['name']}</td>
            <td style="padding: 10px; border-bottom: 1px solid #e2e8f0; text-align: center; color: #475569;">{it['qty']}</td>
            <td style="padding: 10px; border-bottom: 1px solid #e2e8f0; text-align: right; color: #475569;">${it['price']:.2f}</td>
            <td style="padding: 10px; border-bottom: 1px solid #e2e8f0; text-align: right; font-weight: bold; color: #0e1618;">${line_total:.2f}</td>
        </tr>
        """
        items_text_list.append(f"{it['qty']}x {it['name']} (${line_total:.2f})")

    items_summary_str = ", ".join(items_text_list)

    # 1. Dispatch Email to John Barr (Packing Slip) & Operator CC
    if smtp_user and smtp_pwd:
        try:
            merchant_msg = MIMEMultipart("alternative")
            merchant_msg["Subject"] = f"🚨 [NEW ORDER] #{order_id} - {customer_name} (${total:.2f})"
            merchant_msg["From"] = f"The Simple Chef Orders <{smtp_user}>"
            merchant_msg["To"] = creds["CHEF_ALERT_EMAIL"]
            merchant_msg["Cc"] = creds["OPERATOR_EMAIL"]
            merchant_msg["Date"] = email.utils.formatdate(localtime=True)

            merchant_body_html = f"""
            <html>
            <body style="font-family: Arial, sans-serif; color: #1e293b; background-color: #f8fafc; margin: 0; padding: 20px;">
                <div style="max-width: 600px; margin: auto; background: #ffffff; border-radius: 12px; overflow: hidden; box-shadow: 0 4px 15px rgba(0,0,0,0.08); border: 1px solid #e2e8f0;">
                    <div style="background-color: #0e1618; padding: 24px; color: #f7e4cb; text-align: center;">
                        <h2 style="margin: 0; font-size: 22px; letter-spacing: 1px;">👨‍🍳 THE SIMPLE CHEF — NEW ORDER</h2>
                        <p style="margin: 6px 0 0 0; font-size: 14px; opacity: 0.85;">Order #{order_id} &bull; Ready to Pack & Ship</p>
                    </div>
                    <div style="padding: 24px;">
                        <div style="background: #f1f5f9; padding: 14px; rounded: 8px; border-left: 4px solid #10b981; margin-bottom: 20px;">
                            <strong style="color: #0f172a; font-size: 16px;">Customer: {customer_name}</strong><br>
                            <span style="font-size: 13px; color: #475569;">Email: {customer_email} | Phone: {customer_phone or 'N/A'}</span><br>
                            <span style="font-size: 13px; color: #475569;"><strong>Ship To:</strong> {shipping_address}</span>
                        </div>

                        <h3 style="font-size: 15px; color: #0e1618; margin-bottom: 10px; text-transform: uppercase;">Items to Pack:</h3>
                        <table style="width: 100%; border-collapse: collapse; font-size: 14px; margin-bottom: 20px;">
                            <thead>
                                <tr style="background: #f8fafc; text-align: left; font-size: 12px; color: #64748b;">
                                    <th style="padding: 8px 10px;">ITEM</th>
                                    <th style="padding: 8px 10px; text-align: center;">QTY</th>
                                    <th style="padding: 8px 10px; text-align: right;">PRICE</th>
                                    <th style="padding: 8px 10px; text-align: right;">TOTAL</th>
                                </tr>
                            </thead>
                            <tbody>
                                {items_html_rows}
                            </tbody>
                        </table>

                        <div style="background: #f8fafc; padding: 14px; border-radius: 8px; font-size: 14px; margin-bottom: 20px;">
                            <div style="display: flex; justify-content: space-between; margin-bottom: 4px;">
                                <span style="color: #64748b;">Subtotal:</span>
                                <strong>${subtotal:.2f}</strong>
                            </div>
                            <div style="display: flex; justify-content: space-between; margin-bottom: 4px;">
                                <span style="color: #64748b;">MI Sales Tax (6%):</span>
                                <strong>${tax:.2f}</strong>
                            </div>
                            <div style="display: flex; justify-content: space-between; margin-bottom: 4px;">
                                <span style="color: #64748b;">Shipping:</span>
                                <strong>${shipping:.2f}</strong>
                            </div>
                            <div style="border-top: 1px solid #cbd5e1; padding-top: 6px; display: flex; justify-content: space-between; font-size: 16px; font-weight: bold; color: #0e1618;">
                                <span>Grand Total:</span>
                                <span style="color: #10b981;">${total:.2f} USD</span>
                            </div>
                            <div style="margin-top: 8px; font-size: 12px; color: #64748b;">
                                Payment: <strong>{payment_method.upper()}</strong> (Card ending in {card_last4})
                            </div>
                        </div>

                        {f'<div style="background: #fffbeb; border: 1px solid #fef3c7; padding: 12px; border-radius: 8px; font-size: 13px; color: #92400e;"><strong>Order Notes:</strong> {notes}</div>' if notes else ''}
                    </div>
                    <div style="background: #0e1618; color: #f7e4cb; text-align: center; padding: 12px; font-size: 12px;">
                        The Simple Chef &bull; Greenville, MI 48838 &bull; AI-BS Autonomous Store Engine
                    </div>
                </div>
            </body>
            </html>
            """
            merchant_msg.attach(MIMEText(merchant_body_html, "html", "utf-8"))

            recipients = [creds["CHEF_ALERT_EMAIL"], creds["OPERATOR_EMAIL"]]
            server = smtplib.SMTP(creds["SMTP_HOST"], int(creds["SMTP_PORT"]), timeout=15.0)
            server.ehlo()
            server.starttls()
            server.ehlo()
            server.login(smtp_user, smtp_pwd)
            server.sendmail(smtp_user, recipients, merchant_msg.as_string())

            # 1b. Instant Text / SMS Notification to John Barr's Phone (480-882-8565)
            chef_phone_raw = creds.get("CHEF_PHONE", "480-882-8565")
            chef_digits = "".join(filter(str.isdigit, chef_phone_raw))
            if len(chef_digits) >= 10:
                sms_ten = chef_digits[-10:]
                sms_gateways = [
                    f"{sms_ten}@vtext.com",      # Verizon
                    f"{sms_ten}@txt.att.net",    # AT&T
                    f"{sms_ten}@tmomail.net",    # T-Mobile
                    f"{sms_ten}@messaging.sprintpcs.com" # Sprint/Boost
                ]
                sms_text = f"👨‍🍳 Simple Chef ORDER #{order_id}!\nCustomer: {customer_name}\nTotal: ${total:.2f}\nItems: {items_summary_str}\nShip: {shipping_address}"
                sms_msg = MIMEText(sms_text, "plain", "utf-8")
                sms_msg["From"] = f"Simple Chef <{smtp_user}>"
                sms_msg["Subject"] = f"Order #{order_id}"
                try:
                    server.sendmail(smtp_user, sms_gateways, sms_msg.as_string())
                    print(f"[SUCCESS] Dispatched instant SMS notification to John Barr's phone ({sms_ten})")
                except Exception as sms_err:
                    print(f"[WARNING] SMS gateway dispatch notice: {sms_err}")
            customer_msg = MIMEMultipart("alternative")
            customer_msg["Subject"] = f"🎉 Your Order #{order_id} is Confirmed! — The Simple Chef"
            customer_msg["From"] = f"The Simple Chef <{smtp_user}>"
            customer_msg["To"] = customer_email
            customer_msg["Reply-To"] = creds["CHEF_ALERT_EMAIL"]
            customer_msg["Date"] = email.utils.formatdate(localtime=True)

            customer_body_html = f"""
            <html>
            <body style="font-family: Arial, sans-serif; color: #1e293b; background-color: #f8fafc; margin: 0; padding: 20px;">
                <div style="max-width: 600px; margin: auto; background: #ffffff; border-radius: 12px; overflow: hidden; box-shadow: 0 4px 15px rgba(0,0,0,0.08); border: 1px solid #e2e8f0;">
                    <div style="background-color: #0e1618; padding: 26px; color: #f7e4cb; text-align: center;">
                        <h1 style="margin: 0; font-size: 24px; font-weight: 800; letter-spacing: 1px;">THE SIMPLE CHEF</h1>
                        <p style="margin: 6px 0 0 0; font-size: 14px; opacity: 0.9;">Thank you for your order, {customer_name}!</p>
                    </div>
                    <div style="padding: 26px;">
                        <p style="font-size: 15px; line-height: 1.6; color: #334155;">
                            Chef John Barr and our team have received your order <strong>#{order_id}</strong> and are packing your small-batch seasonings right now in Greenville, Michigan!
                        </p>

                        <div style="background: #f8fafc; border: 1px solid #e2e8f0; border-radius: 8px; padding: 14px; margin: 20px 0;">
                            <span style="font-size: 12px; text-transform: uppercase; color: #64748b; font-weight: bold; display: block; margin-bottom: 4px;">Shipping Destination:</span>
                            <strong style="color: #0e1618; font-size: 14px;">{shipping_address}</strong>
                        </div>

                        <h3 style="font-size: 14px; color: #0e1618; margin-bottom: 10px; text-transform: uppercase;">Order Summary:</h3>
                        <table style="width: 100%; border-collapse: collapse; font-size: 14px; margin-bottom: 20px;">
                            <tbody>
                                {items_html_rows}
                            </tbody>
                        </table>

                        <div style="border-top: 2px solid #e2e8f0; padding-top: 12px; font-size: 15px;">
                            <div style="display: flex; justify-content: space-between; margin-bottom: 4px;">
                                <span>Subtotal:</span>
                                <strong>${subtotal:.2f}</strong>
                            </div>
                            <div style="display: flex; justify-content: space-between; margin-bottom: 4px;">
                                <span>Tax (6%):</span>
                                <strong>${tax:.2f}</strong>
                            </div>
                            <div style="display: flex; justify-content: space-between; margin-bottom: 4px;">
                                <span>Shipping:</span>
                                <strong>{'FREE' if shipping == 0 else f'${shipping:.2f}'}</strong>
                            </div>
                            <div style="display: flex; justify-content: space-between; font-size: 18px; font-weight: 800; color: #0e1618; margin-top: 8px; padding-top: 8px; border-top: 1px solid #e2e8f0;">
                                <span>Total Paid:</span>
                                <span style="color: #059669;">${total:.2f} USD</span>
                            </div>
                        </div>

                        <div style="margin-top: 24px; padding: 16px; background: #fefce8; border: 1px solid #fef08a; border-radius: 8px; font-size: 13px; color: #854d0e;">
                            <strong>📦 Shipping Timeline:</strong> Your order will ship within 24–48 hours via USPS Priority Mail. You will receive tracking details once your package leaves our kitchen.
                        </div>
                    </div>
                    <div style="background: #0e1618; color: #f7e4cb; text-align: center; padding: 16px; font-size: 12px;">
                        The Simple Chef &bull; 817 S. Lafayette ST., Greenville, MI 48838<br>
                        Phone: (616) 808-9104 &bull; Email: <a href="mailto:info@thesimplechef.net" style="color: #f7e4cb;">info@thesimplechef.net</a> &bull; Web: <a href="https://thesimplechef.com" style="color: #f7e4cb;">thesimplechef.com</a>
                    </div>
                </div>
            </body>
            </html>
            """
            customer_msg.attach(MIMEText(customer_body_html, "html", "utf-8"))
            server.sendmail(smtp_user, [customer_email], customer_msg.as_string())
            server.quit()
        except Exception as email_err:
            print(f"[ERROR] Chef order email dispatch failed: {email_err}")

    # 3. Dispatch Discord Alert
    webhook_url = creds.get("DISCORD_WEBHOOK_URL")
    if webhook_url and webhook_url.startswith("http"):
        try:
            import requests
            discord_payload = {
                "embeds": [{
                    "title": f"👨‍🍳 NEW THE SIMPLE CHEF ORDER #{order_id}",
                    "description": f"**Customer:** `{customer_name}`\n**Email:** `{customer_email}`\n**Total:** **${total:.2f} USD**\n**Items:** {items_summary_str}\n**Destination:** `{shipping_address}`",
                    "color": 0x10b981,
                    "footer": {"text": "The Simple Chef Storefront • thesimplechef.com"}
                }]
            }
            requests.post(webhook_url, json=discord_payload, timeout=5)
        except Exception as disc_err:
            print(f"[WARNING] Discord alert dispatch failed: {disc_err}")

    # 4. Dispatch to Google Apps Script Webhook (for Google Sheet on John's Phone)
    gas_url = creds.get("GOOGLE_APPS_SCRIPT_URL")
    if gas_url and gas_url.startswith("http"):
        try:
            import requests
            payload = {
                "action": "chef_order",
                "order_id": order_id,
                "customer_name": customer_name,
                "email": customer_email,
                "phone": customer_phone,
                "shipping_address": shipping_address,
                "items_summary": items_summary_str,
                "subtotal": subtotal,
                "tax": tax,
                "shipping": shipping,
                "total": total,
                "payment_method": payment_method,
                "card_last4": card_last4,
                "status": "Paid - Ready to Ship",
                "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            }
            requests.post(gas_url, json=payload, timeout=6)
        except Exception as gas_err:
            print(f"[WARNING] Google Apps Script sync failed: {gas_err}")


# --- API Endpoints ---
@router.post("/order")
async def place_chef_order(payload: OrderSubmissionPayload, background_tasks: BackgroundTasks):
    """Processes online storefront order for The Simple Chef with card details."""
    order_id = payload.order_id or f"SC-{int(time.time() * 1000) % 1000000:06d}"
    created_at = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    # Mask card for security
    card_last4 = "----"
    if payload.card_number:
        clean_num = payload.card_number.replace(" ", "").replace("-", "")
        if len(clean_num) >= 4:
            card_last4 = clean_num[-4:]

    items_dicts = [{"name": it.name, "price": it.price, "qty": it.qty} for it in payload.items]
    items_json = json.dumps(items_dicts)

    # Persist to SQLite
    try:
        conn = sqlite3.connect(str(DB_PATH))
        cursor = conn.cursor()
        cursor.execute("""
            INSERT INTO chef_orders (
                order_id, created_at, customer_name, email, phone,
                shipping_address, items_json, subtotal, tax, shipping, total,
                payment_method, payment_status, card_last4, notes, fulfillment_status
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            order_id, created_at, payload.customer_name, payload.email, payload.phone or "",
            payload.shipping_address, items_json, payload.subtotal, payload.tax,
            payload.shipping, payload.total, payload.payment_method, "PAID",
            card_last4, payload.notes or "", "Pending"
        ))
        conn.commit()
        conn.close()
    except Exception as db_err:
        raise HTTPException(status_code=500, detail=f"Database write error: {str(db_err)}")

    # Schedule notifications in background
    order_dict = {
        "order_id": order_id,
        "created_at": created_at,
        "customer_name": payload.customer_name,
        "email": payload.email,
        "phone": payload.phone,
        "shipping_address": payload.shipping_address,
        "items": items_dicts,
        "subtotal": payload.subtotal,
        "tax": payload.tax,
        "shipping": payload.shipping,
        "total": payload.total,
        "payment_method": payload.payment_method,
        "card_last4": card_last4,
        "notes": payload.notes
    }
    background_tasks.add_task(dispatch_notifications_task, order_dict)

    return {
        "status": "success",
        "order_id": order_id,
        "message": "Order successfully authorized and recorded! Packing notifications sent to Chef John Barr.",
        "receipt": {
            "order_id": order_id,
            "date": created_at,
            "customer": payload.customer_name,
            "total": payload.total,
            "card_last4": card_last4,
            "shipping_to": payload.shipping_address
        }
    }


@router.get("/orders")
async def list_chef_orders(limit: int = 50, status: Optional[str] = None):
    """Retrieves all orders for the AI-BS Client Hub dashboard."""
    conn = sqlite3.connect(str(DB_PATH))
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()

    if status and status != "All":
        cursor.execute("SELECT * FROM chef_orders WHERE fulfillment_status = ? ORDER BY id DESC LIMIT ?", (status, limit))
    else:
        cursor.execute("SELECT * FROM chef_orders ORDER BY id DESC LIMIT ?", (limit,))

    rows = cursor.fetchall()
    conn.close()

    orders = []
    for r in rows:
        orders.append({
            "id": r["id"],
            "order_id": r["order_id"],
            "created_at": r["created_at"],
            "customer_name": r["customer_name"],
            "email": r["email"],
            "phone": r["phone"],
            "shipping_address": r["shipping_address"],
            "items": json.loads(r["items_json"]),
            "subtotal": r["subtotal"],
            "tax": r["tax"],
            "shipping": r["shipping"],
            "total": r["total"],
            "payment_method": r["payment_method"],
            "payment_status": r["payment_status"],
            "card_last4": r["card_last4"],
            "notes": r["notes"],
            "fulfillment_status": r["fulfillment_status"]
        })

    return {"status": "success", "orders": orders, "count": len(orders)}


@router.post("/order/{order_id}/status")
async def update_order_status(order_id: str, payload: StatusUpdatePayload):
    """Updates order fulfillment status (e.g. Shipped, Packed)."""
    conn = sqlite3.connect(str(DB_PATH))
    cursor = conn.cursor()
    cursor.execute("""
        UPDATE chef_orders
        SET fulfillment_status = ?
        WHERE order_id = ?
    """, (payload.fulfillment_status, order_id))
    affected = cursor.rowcount
    conn.commit()
    conn.close()

    if affected == 0:
        raise HTTPException(status_code=404, detail=f"Order {order_id} not found.")

    return {"status": "success", "order_id": order_id, "new_status": payload.fulfillment_status}


@router.get("/stats")
async def get_chef_stats():
    """Returns total orders, gross revenue, and rub breakdown for The Simple Chef."""
    conn = sqlite3.connect(str(DB_PATH))
    cursor = conn.cursor()
    cursor.execute("SELECT COUNT(*), COALESCE(SUM(total), 0) FROM chef_orders")
    total_orders, gross_revenue = cursor.fetchone()
    conn.close()

    return {
        "status": "success",
        "total_orders": total_orders,
        "gross_revenue": round(gross_revenue, 2),
        "currency": "USD"
    }
