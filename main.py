import asyncio
import smtplib
import os
import json
from datetime import datetime, timedelta
from email.message import EmailMessage
from pyrogram import Client, filters
from pyrogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from pyrogram.errors import MessageNotModified

# --- البيانات الحساسة (تُسحب من Railway Variables) ---
API_ID = int(os.environ.get("API_ID"))
API_HASH = os.environ.get("API_HASH")
BOT_TOKEN = os.environ.get("BOT_TOKEN")
ADMIN_ID = int(os.environ.get("ADMIN_ID"))

app = Client("LidoVaultBot", api_id=API_ID, api_hash=API_HASH, bot_token=BOT_TOKEN)

DB_FILE = "database.json"
active_tasks = {}

# --- إدارة قاعدة البيانات ---
def load_db():
    if os.path.exists(DB_FILE):
        try:
            with open(DB_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except: pass
    return {"users_auth": {}, "users_vault": {}}

db = load_db()

def save_db():
    with open(DB_FILE, "w", encoding="utf-8") as f:
        json.dump(db, f, ensure_ascii=False, indent=4)

def get_vault(user_id):
    uid = str(user_id)
    if uid not in db["users_vault"]:
        db["users_vault"][uid] = {
            "accs": [], "targets": [], "subject": "No Subject",
            "body": "No Content", "image": None, "sleep": 5, "count": 10,
            "waiting_for": None, "temp_id": None
        }
    return db["users_vault"][uid]

def is_subscribed(user_id):
    if user_id == ADMIN_ID: return True
    uid = str(user_id)
    if uid in db["users_auth"]:
        try:
            expiry = datetime.fromisoformat(db["users_auth"][uid])
            if datetime.now() < expiry: return True
        except: pass
    return False

# --- أوامر البوت الأساسية ---
@app.on_message(filters.command("start"))
async def start(client, message):
    if not is_subscribed(message.from_user.id):
        return await message.reply("⚠️ أنت غير مشترك. تواصل مع الإدمن.")
    await message.reply("🚀 أهلاً بك في بوت بروفيسور للرفع.")

# --- محرك الإرسال (الجزء الذي طلبته) ---
async def start_engine(message, vault, user_id):
    uid_str = str(user_id); active_tasks[uid_str] = True
    succ, fail = 0, 0
    status = await message.reply("🚀 بدأ الرفع...")

    for _ in range(vault["count"]):
        if not active_tasks.get(uid_str): break
        for acc in vault["accs"]:
            try:
                mail, pwd = acc.split(":", 1)
                for target in vault["targets"]:
                    if not active_tasks.get(uid_str): break
                    try:
                        msg = EmailMessage(); msg.set_content(vault["body"]); msg['Subject'] = vault["subject"]
                        msg['From'], msg['To'] = mail.strip(), target.strip()
                        with smtplib.SMTP_SSL('smtp.gmail.com', 465) as s:
                            s.login(mail.strip(), pwd.strip()); s.send_message(msg)
                        succ += 1
                    except: fail += 1
                    await asyncio.sleep(vault["sleep"])
            except: continue
    await status.edit_text(f"🏁 انتهى! \n✅ {succ} | ❌ {fail}")
    active_tasks.pop(uid_str, None)

app.run()
