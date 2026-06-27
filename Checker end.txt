#!/usr/bin/env python
# -*- coding: utf-8 -*-
import logging
import os
import http
import re
import random
import asyncio
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple

from telegram import (
    Update,
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    InputMediaPhoto,
    BotCommand
)
from telegram.ext import (
    Application,
    CommandHandler,
    ContextTypes,
    CallbackQueryHandler,
    MessageHandler,
    filters,
    )

# --- إعدادات البوت الأساسية ---
TOKEN = "8627020385:AAEQ2YkmQKZiS74tfie3Hy-ricFyMa5CqCw"
DEVELOPER_ID = 8011795436  # استبدل برقمك الخاص
ADMIN_IDS = [DEVELOPER_ID, 8011795436]  # أرقام المشرفين الإضافيين
REQUIRED_CHANNEL = "https://t.me/ankabot6"  # قناة الاشتراك الإجباري
SUPPORT_LINK = "https://t.me/ankabot6"
SUPPORT_NAME = "عنكبوت 🕷"
WEBSITE_LINK = "https://example.com"
BOT_NAME = "CHECKER CC1"
WELCOME_IMAGE = "https://files.catbox.moe/smvjl7.jpg"
PAYMENT_METHODS = {
    "USDT": "ERC20 Address: 0x3d0e9b0A74A2779b5b306068305832633A1db126",
    "BTC": "BTC Address: bc1q98syzh0s5p7sf3hmgk5latvly56wd3y8efvnkx",
    "ETH": "ETH Address: 0x3d0e9b0A74A2779b5b306068305832633A1db126",
    "BNB": "BNB Address: 0x3d0e9b0A74A2779b5b306068305832633A1db126"
}

# تمكين التسجيل
logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# --- نماذج البيانات ---
class User:
    def __init__(self, user_id: int):
        self.user_id = user_id
        self.is_admin = user_id in ADMIN_IDS or user_id == DEVELOPER_ID
        self.subscription_type = "free"  # free, basic, premium
        self.subscription_expiry = None
        self.join_date = datetime.now()
        self.usage_count = 0
        self.last_check = None

class Card:
    def __init__(self, number: str, expiry: str, cvv: str):
        self.number = number
        self.expiry = expiry
        self.cvv = cvv
        self.checked = False
        self.live = False
        self.response = None
        self.check_date = datetime.now()
        self.gateway = None

# --- قاعدة بيانات ---
class Database:
    def __init__(self):
        self.users: Dict[int, User] = {}
        self.cards: Dict[str, Card] = {}
        self.settings = {
            "title": "CHECKER CC1",
            "stripe_key": "sk_live_xxxxxxxxxxxxxx",
            "welcome_message": "مرحباً بك في أقوى بوت فحص البطاقات",
            "max_free_checks": 3,
            "subscription_prices": {
                "basic": {"price": 10, "duration": 30},
                "premium": {"price": 25, "duration": 90}
            },
            "course_prices": {
                "hacking": 50,
                "bot_development": 40,
                "carding": 60
            }
        }
        # تحميل المستخدمين الموجودين بالفعل كمسؤولين
        for admin_id in ADMIN_IDS:
            self.users[admin_id] = User(admin_id)
            self.users[admin_id].subscription_type = "premium"

    async def get_user(self, user_id: int) -> Optional[User]:
        return self.users.get(user_id)

    async def add_user(self, user_id: int) -> User:
        if user_id not in self.users:
            self.users[user_id] = User(user_id)
        return self.users[user_id]

    async def update_user(self, user_id: int, **kwargs):
        user = await self.get_user(user_id)
        if user:
            for key, value in kwargs.items():
                setattr(user, key, value)

    async def add_card(self, card: Card):
        self.cards[card.number] = card

    async def get_card(self, number: str) -> Optional[Card]:
        return self.cards.get(number)

db = Database()

# --- أدوات مساعدة ---
async def is_admin(user_id: int) -> bool:
    user = await db.get_user(user_id)
    return user and (user.is_admin or user_id == DEVELOPER_ID)

async def is_subscribed(user_id: int, required_level: str = "basic") -> bool:
    user = await db.get_user(user_id)
    if not user:
        return False
    
    if user.is_admin:
        return True
    
    if user.subscription_type == "premium":
        return True
    elif user.subscription_type == "basic" and required_level == "basic":
        return True
    
    return False

async def check_channel_membership(user_id: int, context: ContextTypes.DEFAULT_TYPE) -> bool:
    try:
        member = await context.bot.get_chat_member(REQUIRED_CHANNEL, user_id)
        return member.status in ['member', 'administrator', 'creator']
    except Exception as e:
        logger.error(f"Error checking channel membership: {e}")
        return False

async def extract_cc_info(text: str) -> Optional[Dict]:
    patterns = [
        r'(\d{16})\|(\d{2})\|(\d{2,4})\|(\d{3,4})',
        r'(\d{16})\s+(\d{2})\s+(\d{2,4})\s+(\d{3,4})',
        r'(\d{4}\s?\d{4}\s?\d{4}\s?\d{4})\s+(\d{2})\/?(\d{2,4})\s+(\d{3,4})'
    ]
    
    for pattern in patterns:
        match = re.search(pattern, text)
        if match:
            expiry_year = match.group(3)
            if len(expiry_year) == 2:
                expiry_year = '20' + expiry_year
            
            return {
                "number": match.group(1).replace(" ", ""),
                "expiry": f"{match.group(2)}/{expiry_year}",
                "cvv": match.group(4)
            }
    return None

async def check_cc_with_stripe(card_number: str, expiry: str, cvv: str) -> Dict:
    headers = {
        "Authorization": f"Bearer {db.settings['stripe_key']}",
        "Content-Type": "application/x-www-form-urlencoded",
    }
    
    try:
        exp_month, exp_year = expiry.split("/")
        if len(exp_year) == 2:
            exp_year = '20' + exp_year
    except:
        return {
            "valid": False,
            "status": "Invalid",
            "response": "400",
            "message": "صيغة تاريخ انتهاء الصلاحية غير صحيحة"
        }
    
    payload = {
        "card[number]": card_number,
        "card[exp_month]": exp_month,
        "card[exp_year]": exp_year,
        "card[cvc]": cvv
    }
    
    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.post(
                "https://api.stripe.com/v1/tokens",
                data=payload,
                headers=headers
            )
            
            result = response.json()
            if response.status_code == 200:
                return {
                    "valid": True,
                    "status": "Approved",
                    "response": "200",
                    "brand": result.get("card", {}).get("brand", "Unknown"),
                    "country": result.get("card", {}).get("country", "Unknown"),
                    "funding": result.get("card", {}).get("funding", "Unknown"),
                    "message": "تم الفحص بنجاح"
                }
            else:
                error_msg = result.get("error", {}).get("message", "Unknown error")
                return {
                    "valid": False,
                    "status": "Declined",
                    "response": str(response.status_code),
                    "message": error_msg
                }
    except httpx.TimeoutException:
        return {
            "valid": False,
            "status": "Error",
            "response": "408",
            "message": "انتهت مهلة الاتصال بالخادم"
        }
    except Exception as e:
        return {
            "valid": False,
            "status": "Error",
            "response": "500",
            "message": f"خطأ في الاتصال: {str(e)}"
        }

async def generate_virtual_card(card_type: str = "visa", amount: int = 1) -> List[Dict]:
    cards = []
    for _ in range(amount):
        if card_type.lower() == "visa":
            prefix = "4" + str(random.randint(0, 9))
            length = 16
        elif card_type.lower() == "mastercard":
            prefix = str(random.choice(["51", "52", "53", "54", "55"]))
            length = 16
        elif card_type.lower() == "amex":
            prefix = str(random.choice(["34", "37"]))
            length = 15
        else:
            prefix = "4"
            length = 16
            
        number = prefix + ''.join([str(random.randint(0, 9)) for _ in range(length - len(prefix) - 1)])
        number += luhn_checksum(number)
        
        card = {
            "number": number,
            "expiry": f"{random.randint(1, 12):02d}/{random.randint(23, 28)}",
            "cvv": f"{random.randint(100, 999)}",
            "type": card_type.upper(),
            "balance": random.randint(10, 1000)
        }
        cards.append(card)
    return cards

def luhn_checksum(partial_number: str) -> str:
    digits = [int(d) for d in partial_number]
    for i in range(len(digits)-1, -1, -2):
        digits[i] *= 2
        if digits[i] > 9:
            digits[i] = digits[i] // 10 + digits[i] % 10
    total = sum(digits)
    return str((10 - (total % 10)) % 10)

def create_check_gateways_keyboard() -> InlineKeyboardMarkup:
    keyboard = [
        [InlineKeyboardButton("Stripe CC Checker", callback_data='stripe_check')],
        [InlineKeyboardButton("Live Checker", callback_data='live_check')],
        [InlineKeyboardButton("OTP Checker", callback_data='otp_check')],
        [InlineKeyboardButton("🔙 الرجوع", callback_data='main_menu')]
    ]
    return InlineKeyboardMarkup(keyboard)

def create_main_menu_keyboard() -> InlineKeyboardMarkup:
    keyboard = [
        [InlineKeyboardButton("🔍 فحص البطاقات", callback_data='check_gateways')],
        [InlineKeyboardButton("🎫 توليد فيز", callback_data='gen_vcc')],
        [InlineKeyboardButton("💳 الاشتراكات", callback_data='subscriptions')],
        [InlineKeyboardButton("📚 الكورسات", callback_data='courses')],
        [InlineKeyboardButton("📞 الدعم الفني", url=SUPPORT_LINK)],
        [InlineKeyboardButton("🌐 الموقع الرسمي", url=WEBSITE_LINK)]
    ]
    return InlineKeyboardMarkup(keyboard)

def create_subscriptions_keyboard() -> InlineKeyboardMarkup:
    keyboard = [
        [InlineKeyboardButton("🟢 Basic - 10$ / شهر", callback_data='sub_basic')],
        [InlineKeyboardButton("🔴 Premium - 25$ / 3 شهور", callback_data='sub_premium')],
        [InlineKeyboardButton("🔙 الرجوع", callback_data='main_menu')]
    ]
    return InlineKeyboardMarkup(keyboard)

def create_courses_keyboard() -> InlineKeyboardMarkup:
    keyboard = [
        [InlineKeyboardButton("📌 صنع تشيكرات - 50$", callback_data='course_hacking')],
        [InlineKeyboardButton("🤖 تطوير بوتات - 40$", callback_data='course_bot')],
        [InlineKeyboardButton("💻 اختراق أجهزة - 60$", callback_data='course_carding')],
        [InlineKeyboardButton("🔙 الرجوع", callback_data='main_menu')]
    ]
    return InlineKeyboardMarkup(keyboard)

def create_admin_keyboard() -> InlineKeyboardMarkup:
    keyboard = [
        [InlineKeyboardButton("📊 إحصائيات البوت", callback_data='bot_stats')],
        [InlineKeyboardButton("🛠 إعدادات البوت", callback_data='bot_settings')],
        [InlineKeyboardButton("👥 إدارة المستخدمين", callback_data='manage_users')],
        [InlineKeyboardButton("🔙 القائمة الرئيسية", callback_data='main_menu')]
    ]
    return InlineKeyboardMarkup(keyboard)

# --- معالجات الأوامر ---
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    await db.add_user(user.id)
    
    # التحقق من الاشتراك في القناة
    if not await check_channel_membership(user.id, context):
        await context.bot.send_message(
            chat_id=update.effective_chat.id,
            text=f"⛔ يرجى الانضمام إلى قناتنا أولاً: @{REQUIRED_CHANNEL}",
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("الانضمام للقناة", url=f"https://t.me/{REQUIRED_CHANNEL[1:]}")],
                [InlineKeyboardButton("✅ لقد انضممت", callback_data='check_membership')]
            ])
        )
        return
    
    welcome_text = f"""
*بِسْمِ اللَّهِ الرَّحْمَنِ الرَّحِيمِ*
وَإِنْ يَمْسَسْكَ اللَّهُ بِضُرٍّ فَلَا كَاشِفَ لَهُ إِلَّا هُوَ

✨ *مرحباً بك في {BOT_NAME}* ✨
🎯 *المميزات:*

- فحص بطاقات Stripe CC
- توليد فيز مجاني
- فحص OTP متقدم
- أدوات تطوير احترافية

📌 *حقوق المطور:* [{SUPPORT_NAME}]({SUPPORT_LINK})
    """
    
    try:
        await context.bot.send_photo(
            chat_id=update.effective_chat.id,
            photo=WELCOME_IMAGE,
            caption=welcome_text,
            reply_markup=create_main_menu_keyboard(),
            parse_mode="Markdown"
        )
    except Exception as e:
        logger.error(f"Failed to send welcome image: {e}")
        await context.bot.send_message(
            chat_id=update.effective_chat.id,
            text=welcome_text,
            reply_markup=create_main_menu_keyboard(),
            parse_mode="Markdown"
        )

async def handle_cc_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    user = await db.get_user(user_id)
    
    if not user:
        await update.message.reply_text("⛔ يرجى البدء باستخدام الأمر /start أولاً.")
        return
    
    if not await is_subscribed(user_id):
        await update.message.reply_text(
            "⛔ هذه الميزة متاحة للمشتركين فقط.\n\nيرجى الاشتراك أولاً.",
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("💳 الاشتراكات", callback_data='subscriptions')]
            ])
        )
        return
    
    if not context.args:
        await update.message.reply_text("📌 أرسل رقم البطاقة بالصيغة التالية:\n\n1234567890123456|12|25|123")
        return
    
    cc_info = await extract_cc_info(" ".join(context.args))
    if not cc_info:
        await update.message.reply_text("❌ صيغة البطاقة غير صحيحة. مثال: 1234567890123456|12|25|123")
        return
    
    processing_msg = await update.message.reply_text("⏳ جاري فحص البطاقة، يرجى الانتظار...")
    
    result = await check_cc_with_stripe(
        cc_info["number"],
        cc_info["expiry"],
        cc_info["cvv"]
    )
    
    card = Card(cc_info["number"], cc_info["expiry"], cc_info["cvv"])
    card.checked = True
    card.live = result["valid"]
    card.response = result
    card.gateway = "stripe"
    await db.add_card(card)
    
    await db.update_user(user_id, usage_count=user.usage_count + 1, last_check=datetime.now())
    
    response_text = f"""
💳 *نتيجة فحص البطاقة* (Stripe):
━━━━━━━━━━━━━━
🔢 *الرقم*: `{cc_info['number']}`
📅 *الصلاحية*: `{cc_info['expiry']}`
🔐 *CVV*: `{cc_info['cvv']}`
━━━━━━━━━━━━━━
✅ *الحالة*: `{result['status']}`
🏦 *النوع*: `{result.get('brand', 'غير معروف')}`
🌍 *البلد*: `{result.get('country', 'غير معروف')}`
💳 *نوع التمويل*: `{result.get('funding', 'غير معروف')}`
📝 *الرسالة*: `{result['message']}`
━━━━━━━━━━━━━━
📌 *حقوق المطور*: [{SUPPORT_NAME}]({SUPPORT_LINK})
    """
    
    try:
        await context.bot.delete_message(
            chat_id=update.effective_chat.id,
            message_id=processing_msg.message_id
        )
    except:
        pass
    
    await update.message.reply_text(
        response_text,
        parse_mode="Markdown",
        reply_markup=InlineKeyboardMarkup([
            [InlineKeyboardButton("🔙 القائمة الرئيسية", callback_data='main_menu')]
        ])
    )

async def handle_check_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    user = await db.get_user(user_id)
    
    if not user:
        await update.message.reply_text("⛔ يرجى البدء باستخدام الأمر /start أولاً.")
        return
    
    if not await is_subscribed(user_id, "premium"):
        await update.message.reply_text(
            "⛔ هذه الميزة متاحة للمشتركين في الباقة المميزة فقط.",
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("💳 ترقية الاشتراك", callback_data='subscriptions')]
            ])
        )
        return
    
    if not context.args:
        await update.message.reply_text("📌 أرسل رقم البطاقة للفحص: /chk 1234567890123456")
        return
    
    card_number = context.args[0].strip()
    processing_msg = await update.message.reply_text("⏳ جاري فحص البطاقة (Live Check)، يرجى الانتظار...")
    
    # محاكاة فحص Live (في الواقع يجب استبدالها بوظيفة الفحص الحقيقية)
    await asyncio.sleep(3)
    is_live = random.choice([True, False])
    response_code = random.choice(["200", "201", "400", "401", "402", "403"])
    
    card = Card(card_number, "??/??", "???")
    card.checked = True
    card.live = is_live
    card.response = {"status": "Approved" if is_live else "Declined", "code": response_code}
    card.gateway = "live"
    await db.add_card(card)
    
    await db.update_user(user_id, usage_count=user.usage_count + 1, last_check=datetime.now())
    
    response_text = f"""
🔍 *نتيجة الفحص المباشر*:
━━━━━━━━━━━━━━
🔢 *الرقم*: `{card_number}`
✅ *الحالة*: `{"Live ✅" if is_live else "Dead ❌"}`
📊 *الاستجابة*: `{response_code}`
🔄 *بوابة الفحص*: `Live Check`
━━━━━━━━━━━━━━
📌 *حقوق المطور*: [{SUPPORT_NAME}]({SUPPORT_LINK})
    """
    
    try:
        await context.bot.delete_message(
            chat_id=update.effective_chat.id,
            message_id=processing_msg.message_id
        )
    except:
        pass
    
    await update.message.reply_text(
        response_text,
        parse_mode="Markdown",
        reply_markup=InlineKeyboardMarkup([
            [InlineKeyboardButton("🔙 القائمة الرئيسية", callback_data='main_menu')]
        ])
    )

async def handle_gen_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    user = await db.get_user(user_id)
    
    if not user:
        await update.message.reply_text("⛔ يرجى البدء باستخدام الأمر /start أولاً.")
        return
    
    if len(context.args) < 1:
        await update.message.reply_text("📌 اختر نوع البطاقة:\n/gen visa\n/gen mastercard\n/gen amex\n\nيمكنك إضافة الكمية بعد النوع:\n/gen visa 3")
        return
    
    card_type = context.args[0].lower()
    amount = 1
    
    if len(context.args) > 1:
        try:
            amount = int(context.args[1])
            if amount > 5:
                amount = 5
        except ValueError:
            await update.message.reply_text("❌ الكمية يجب أن تكون رقماً صحيحاً")
            return
    
    if card_type not in ["visa", "mastercard", "amex"]:
        await update.message.reply_text("❌ نوع البطاقة غير مدعوم. الاختيارات: visa, mastercard, amex")
        return
    
    processing_msg = await update.message.reply_text(f"⏳ جاري توليد {amount} بطاقة من نوع {card_type}...")
    
    cards = await generate_virtual_card(card_type, amount)
    
    response_text = f"""
✨ *تم توليد {len(cards)} بطاقة من نوع {card_type.upper()}*:
━━━━━━━━━━━━━━
"""
    
    for i, card in enumerate(cards, 1):
        response_text += f"""
💳 *البطاقة #{i}*:
🔢 *الرقم*: `{card['number']}`
📅 *الصلاحية*: `{card['expiry']}`
🔐 *CVV*: `{card['cvv']}`
💰 *الرصيد*: `${card['balance']}`
🏦 *النوع*: `{card['type']}`
━━━━━━━━━━━━━━
"""
    
    response_text += f"""
📌 *ملاحظة*: هذه بطاقات افتراضية للاختبار فقط
📌 *حقوق المطور*: [{SUPPORT_NAME}]({SUPPORT_LINK})
"""
    
    try:
        await context.bot.delete_message(
            chat_id=update.effective_chat.id,
            message_id=processing_msg.message_id
        )
    except:
        pass
    
    await update.message.reply_text(
        response_text,
        parse_mode="Markdown",
        reply_markup=InlineKeyboardMarkup([
            [InlineKeyboardButton("🔙 القائمة الرئيسية", callback_data='main_menu')]
        ])
    )

async def handle_otp_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    user = await db.get_user(user_id)
    
    if not user:
        await update.message.reply_text("⛔ يرجى البدء باستخدام الأمر /start أولاً.")
        return
    
    if not await is_subscribed(user_id, "premium"):
        await update.message.reply_text(
            "⛔ هذه الميزة متاحة للمشتركين في الباقة المميزة فقط.",
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("💳 ترقية الاشتراك", callback_data='subscriptions')]
            ])
        )
        return
    
    if not context.args:
        await update.message.reply_text("📌 أرسل كود OTP للفحص: /otp 123456")
        return
    
    otp_code = context.args[0]
    processing_msg = await update.message.reply_text("⏳ جاري فحص كود OTP، يرجى الانتظار...")
    
    # محاكاة فحص OTP (في الواقع يجب استبدالها بوظيفة الفحص الحقيقية)
    await asyncio.sleep(3)
    is_valid = random.choice([True, False])
    
    response_text = f"""
🔢 *نتيجة فحص OTP*:
━━━━━━━━━━━━━━
📝 *الكود المرسل*: `{otp_code}`
✅ *الحالة*: `{"صحيح ✅" if is_valid else "غير صحيح ❌"}`
🔄 *نوع الفحص*: `SMS OTP`
━━━━━━━━━━━━━━
📌 *حقوق المطور*: [{SUPPORT_NAME}]({SUPPORT_LINK})
    """
    
    try:
        await context.bot.delete_message(
            chat_id=update.effective_chat.id,
            message_id=processing_msg.message_id
        )
    except:
        pass
    
    await update.message.reply_text(
        response_text,
        parse_mode="Markdown",
        reply_markup=InlineKeyboardMarkup([
            [InlineKeyboardButton("🔙 القائمة الرئيسية", callback_data='main_menu')]
        ])
    )

# --- معالجات الاستدعاء ---
async def handle_callback_query(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    user_id = query.from_user.id
    user = await db.get_user(user_id)
    
    if not user:
        await query.edit_message_text("⛔ يرجى البدء باستخدام الأمر /start أولاً.")
        return
    
    if query.data == 'main_menu':
        await query.edit_message_text(
            text=f"✨ *مرحباً بك في {BOT_NAME}* ✨\n\nاختر من القائمة أدناه:",
            reply_markup=create_main_menu_keyboard(),
            parse_mode="Markdown"
        )
    
    elif query.data == 'check_gateways':
        if not await check_channel_membership(user_id, context):
            await query.edit_message_text(
                text=f"⛔ يرجى الانضمام إلى قناتنا أولاً: @{REQUIRED_CHANNEL}",
                reply_markup=InlineKeyboardMarkup([
                    [InlineKeyboardButton("الانضمام للقناة", url=f"https://t.me/{REQUIRED_CHANNEL[1:]}")],
                    [InlineKeyboardButton("✅ لقد انضممت", callback_data='check_membership')]
                ])
            )
            return
        
        await query.edit_message_text(
            text="🔍 *اختر بوابة الفحص المناسبة*:",
            reply_markup=create_check_gateways_keyboard(),
            parse_mode="Markdown"
        )
    
    elif query.data == 'stripe_check':
        if not await is_subscribed(user_id):
            await query.edit_message_text(
                text="⛔ هذه الميزة متاحة للمشتركين فقط.\n\nيرجى الاشتراك أولاً.",
                reply_markup=InlineKeyboardMarkup([
                    [InlineKeyboardButton("💳 الاشتراكات", callback_data='subscriptions')],
                    [InlineKeyboardButton("🔙 القائمة الرئيسية", callback_data='main_menu')]
                ])
            )
            return
        
        await query.edit_message_text(
            text="💳 *فحص Stripe CC*\n\nأرسل رقم البطاقة بالصيغة التالية:\n\n`1234567890123456|12|25|123`",
            parse_mode="Markdown",
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("🔙 الرجوع", callback_data='check_gateways')]
            ])
        )
    
    elif query.data == 'live_check':
        if not await is_subscribed(user_id, "premium"):
            await query.edit_message_text(
                text="⛔ هذه الميزة متاحة للمشتركين في الباقة المميزة فقط.",
                reply_markup=InlineKeyboardMarkup([
                    [InlineKeyboardButton("💳 ترقية الاشتراك", callback_data='subscriptions')],
                    [InlineKeyboardButton("🔙 القائمة الرئيسية", callback_data='main_menu')]
                ])
            )
            return
        
        await query.edit_message_text(
            text="🔍 *فحص Live*\n\nأرسل رقم البطاقة للفحص المباشر:\n\n`1234567890123456`",
            parse_mode="Markdown",
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("🔙 الرجوع", callback_data='check_gateways')]
            ])
        )
    
    elif query.data == 'otp_check':
        if not await is_subscribed(user_id, "premium"):
            await query.edit_message_text(
                text="⛔ هذه الميزة متاحة للمشتركين في الباقة المميزة فقط.",
                reply_markup=InlineKeyboardMarkup([
                    [InlineKeyboardButton("💳 ترقية الاشتراك", callback_data='subscriptions')],
                    [InlineKeyboardButton("🔙 القائمة الرئيسية", callback_data='main_menu')]
                ])
            )
            return
        
        await query.edit_message_text(
            text="🔢 *فحص OTP*\n\nأرسل كود OTP للفحص:\n\n`123456`",
            parse_mode="Markdown",
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("🔙 الرجوع", callback_data='check_gateways')]
            ])
        )
    
    elif query.data == 'gen_vcc':
        await query.edit_message_text(
            text="🎫 *توليد بطاقات افتراضية*\n\nاختر نوع البطاقة:",
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("VISA", callback_data='gen_visa'),
                 InlineKeyboardButton("MasterCard", callback_data='gen_master')],
                [InlineKeyboardButton("AMEX", callback_data='gen_amex')],
                [InlineKeyboardButton("🔙 القائمة الرئيسية", callback_data='main_menu')]
            ]),
            parse_mode="Markdown"
        )
    
    elif query.data.startswith('gen_'):
        card_type = query.data[4:]
        cards = await generate_virtual_card(card_type, 1)
        card = cards[0]
        
        response_text = f"""
✨ *تم توليد بطاقة {card_type.upper()}*:
━━━━━━━━━━━━━━
🔢 *الرقم*: `{card['number']}`
📅 *الصلاحية*: `{card['expiry']}`
🔐 *CVV*: `{card['cvv']}`
💰 *الرصيد*: `${card['balance']}`
🏦 *النوع*: `{card['type']}`
━━━━━━━━━━━━━━
📌 *ملاحظة*: هذه بطاقة افتراضية للاختبار فقط
"""
        
        await query.edit_message_text(
            text=response_text,
            parse_mode="Markdown",
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("🔄 توليد أخرى", callback_data=query.data)],
                [InlineKeyboardButton("🔙 القائمة الرئيسية", callback_data='main_menu')]
            ])
        )
    
    elif query.data == 'subscriptions':
        await query.edit_message_text(
            text="💳 *باقات الاشتراك المتاحة*:\n\n"
                 "🟢 *Basic* - 10$ / شهر\n"
                 "- فحص حتى 50 بطاقة يومياً\n"
                 "- وصول لبوابة Stripe CC\n\n"
                 "🔴 *Premium* - 25$ / 3 شهور\n"
                 "- فحص غير محدود للبطاقات\n"
                 "- وصول لجميع البوابات\n"
                 "- دعم فني مميز\n\n"
                 "📌 اختر الباقة المناسبة لك:",
            reply_markup=create_subscriptions_keyboard(),
            parse_mode="Markdown"
        )
    
    elif query.data.startswith('sub_'):
        sub_type = query.data[4:]
        price_info = db.settings['subscription_prices'].get(sub_type, {})
        
        if not price_info:
            await query.answer("⛔ هذه الباقة غير متاحة حالياً")
            return
        
        payment_text = f"""
💳 *تفاصيل الاشتراك* ({sub_type.capitalize()})
━━━━━━━━━━━━━━
💰 *السعر*: {price_info['price']}$
⏳ *المدة*: {price_info['duration']} يوم
━━━━━━━━━━━━━━
📌 *طرق الدفع المتاحة*:
"""
        for method, address in PAYMENT_METHODS.items():
            payment_text += f"\n🔹 *{method}*: `{address}`\n"
        
        payment_text += f"""
━━━━━━━━━━━━━━
📌 بعد التحويل، أرسل إيصال الدفع إلى @{SUPPORT_LINK.split('/')[-1]}
"""
        
        await query.edit_message_text(
            text=payment_text,
            parse_mode="Markdown",
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("📞 التواصل مع الدعم", url=SUPPORT_LINK)],
                [InlineKeyboardButton("🔙 الرجوع", callback_data='courses')]
            ])
        )
    
    elif query.data == 'courses':
        await query.edit_message_text(
            text="📚 *الكورسات التعليمية المتاحة*:\n\n"
                 "📌 *صنع تشيكرات* - 50$\n"
                 "- تعلم صنع تشيكرات احترافية\n"
                 "- شروحات متقدمة للفحص\n\n"
                 "🤖 *تطوير بوتات* - 40$\n"
                 "- تعلم برمجة بوتات تلجرام\n"
                 "- شروحات متكاملة للبايثون\n\n"
                 "💻 *اختراق أجهزة* - 60$\n"
                 "- تعلم اختراق الأجهزة\n"
                 "- أدوات وتقنيات متقدمة\n\n"
                 "📌 اختر الكورس المناسب لك:",
            reply_markup=create_courses_keyboard(),
            parse_mode="Markdown"
        )
    
    elif query.data == 'check_membership':
        if await check_channel_membership(user_id, context):
            await start(update, context)
        else:
            await query.answer("⛔ لم تنضم بعد إلى القناة المطلوبة!", show_alert=True)
    
    elif query.data == 'admin_menu':
        if not await is_admin(user_id):
            await query.answer("⛔ ليس لديك صلاحية الوصول لهذه القائمة!", show_alert=True)
            return
        
        await query.edit_message_text(
            text="⚙️ *لوحة التحكم الإدارية*",
            reply_markup=create_admin_keyboard(),
            parse_mode="Markdown"
        )
    
    elif query.data == 'bot_stats':
        if not await is_admin(user_id):
            await query.answer("⛔ ليس لديك صلاحية الوصول لهذه القائمة!", show_alert=True)
            return
        
        total_users = len(db.users)
        active_users = len([u for u in db.users.values() if u.last_check and (datetime.now() - u.last_check).days < 7])
        total_checks = sum(u.usage_count for u in db.users.values())
        live_cards = len([c for c in db.cards.values() if c.live])
        
        stats_text = f"""
📊 *إحصائيات البوت*:
━━━━━━━━━━━━━━
👥 *إجمالي المستخدمين*: {total_users}
🚀 *المستخدمين النشطين*: {active_users}
🔍 *إجمالي الفحوصات*: {total_checks}
💳 *البطاقات الناجحة*: {live_cards}
━━━━━━━━━━━━━━
📅 *تاريخ التشغيل*: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
"""
        
        await query.edit_message_text(
            text=stats_text,
            parse_mode="Markdown",
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("🔄 تحديث", callback_data='bot_stats')],
                [InlineKeyboardButton("🔙 القائمة الإدارية", callback_data='admin_menu')]
            ])
        )
    
    elif query.data == 'manage_users':
        if not await is_admin(user_id):
            await query.answer("⛔ ليس لديك صلاحية الوصول لهذه القائمة!", show_alert=True)
            return
        
        await query.edit_message_text(
            text="👥 *إدارة المستخدمين*\n\nأرسل معرف المستخدم للبحث عنه:",
            parse_mode="Markdown",
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("🔙 القائمة الإدارية", callback_data='admin_menu')]
            ])
        )

# --- معالجات الرسائل ---
async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    message_text = update.message.text
    
    if not message_text:
        return
    
    # إذا كان المستخدم مشرفاً ويتفاعل مع لوحة التحكم
    if await is_admin(user_id):
        if message_text.isdigit():
            user = await db.get_user(int(message_text))
            if user:
                user_info = f"""
👤 *معلومات المستخدم*:
━━━━━━━━━━━━━━
🆔 *المعرف*: `{user.user_id}`
📅 *تاريخ الانضمام*: `{user.join_date.strftime('%Y-%m-%d %H:%M:%S')}`
💎 *نوع الاشتراك*: `{user.subscription_type}`
🔢 *عدد الفحوصات*: `{user.usage_count}"""
                
                if user.subscription_expiry:
                    user_info += f"\n⏳ *انتهاء الاشتراك*: `{user.subscription_expiry.strftime('%Y-%m-%d %H:%M:%S')}`"
                
                user_info += f"\n━━━━━━━━━━━━━━\n📌 *حقوق المطور*: [{SUPPORT_NAME}]({SUPPORT_LINK})"
                
                await update.message.reply_text(
                    text=user_info,
                    parse_mode="Markdown",
                    reply_markup=InlineKeyboardMarkup([
                        [
                            InlineKeyboardButton("🔨 حظر", callback_data=f'ban_{user.user_id}'),
                            InlineKeyboardButton("💎 ترقية", callback_data=f'upgrade_{user.user_id}')
                        ],
                        [InlineKeyboardButton("🔙 القائمة الإدارية", callback_data='admin_menu')]
                    ])
                )
                return
    
    # معالجة رسائل فحص البطاقات
    cc_info = await extract_cc_info(message_text)
    if cc_info:
        await handle_cc_command(update, context)
        return
    
    await update.message.reply_text(
        "❌ لم أفهم طلبك. يرجى استخدام الأوامر أو القوائم المتاحة.",
        reply_markup=create_main_menu_keyboard()
    )

# --- وظائف إدارية ---
async def broadcast_message(context: ContextTypes.DEFAULT_TYPE):
    if not context.args or len(context.args) < 2:
        return "⛔ صيغة الأمر غير صحيحة. استخدم: /broadcast [الرسالة]"
    
    message = " ".join(context.args[1:])
    success = 0
    failed = 0
    
    for user_id in db.users:
        try:
            await context.bot.send_message(
                chat_id=user_id,
                text=message
            )
            success += 1
        except Exception as e:
            logger.error(f"Failed to send broadcast to {user_id}: {e}")
            failed += 1
    
    return f"📢 تم إرسال الإذاعة بنجاح إلى {success} مستخدم. فشل الإرسال لـ {failed} مستخدم."

# --- إعداد البوت وتشغيله ---
def main() -> None:
    application = Application.builder().token(TOKEN).build()
    
    # إضافة معالجات الأوامر
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("cc", handle_cc_command))
    application.add_handler(CommandHandler("chk", handle_check_command))
    application.add_handler(CommandHandler("gen", handle_gen_command))
    application.add_handler(CommandHandler("otp", handle_otp_command))
    application.add_handler(CommandHandler("admin", lambda u, c: handle_callback_query(u, c, 'admin_menu')))
    
    # إضافة معالجات الاستدعاء
    application.add_handler(CallbackQueryHandler(handle_callback_query))
    
    # إضافة معالجات الرسائل
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    
    # تشغيل البوت
    web: python bot.py

if __name__ == "__main__":
    main()
        
