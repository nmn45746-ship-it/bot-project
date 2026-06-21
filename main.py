import os
import sqlite3
import pandas as pd
import asyncio
import logging
from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.ext import (Application, CommandHandler, MessageHandler, 
                          CallbackQueryHandler, filters, ContextTypes)

# إعداد السجلات لمتابعة أي أخطاء في الـ Logs
logging.basicConfig(level=logging.INFO)

# قراءة التوكن من متغيرات البيئة في الاستضافة
TOKEN = os.getenv("BOT_TOKEN")
TEMP_FILE = "/tmp/dump.csv"
DB_FILE = "/tmp/cards.db"

def init_db():
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    cursor.execute('CREATE TABLE IF NOT EXISTS cards (country TEXT, data TEXT)')
    cursor.execute('CREATE INDEX IF NOT EXISTS idx_country ON cards(country)')
    conn.commit()
    conn.close()

def process_data_sync():
    """معالجة الملف في الخلفية"""
    conn = sqlite3.connect(DB_FILE)
    # مسح البيانات القديمة
    conn.execute('DELETE FROM cards')
    # قراءة الملف وإضافته لقاعدة البيانات
    df = pd.read_csv(TEMP_FILE)
    df.to_sql('cards', conn, if_exists='append', index=False)
    conn.commit()
    conn.close()

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("أهلاً بك! أرسل ملف الـ CSV للبدء.")

async def handle_document(update: Update, context: ContextTypes.DEFAULT_TYPE):
    msg = await update.message.reply_text("⏳ جارٍ التحميل...")
    
    file = await update.message.document.get_file()
    await file.download_to_drive(TEMP_FILE)
    
    await context.bot.edit_message_text(chat_id=update.message.chat_id, message_id=msg.message_id, text="⚙️ جارٍ المعالجة... يرجى الانتظار.")
    
    # تنفيذ المعالجة في الخلفية بدون تجميد البوت
    loop = asyncio.get_event_loop()
    await loop.run_in_executor(None, process_data_sync)
    
    # جلب الإحصائيات بعد المعالجة
    conn = sqlite3.connect(DB_FILE)
    stats = pd.read_sql_query('SELECT country, COUNT(*) as count FROM cards GROUP BY country', conn)
    conn.close()
    
    keyboard = [[InlineKeyboardButton(f"{r['country']} ({r['count']})", callback_data=r['country'])] for _, r in stats.iterrows()]
    await context.bot.edit_message_text(chat_id=update.message.chat_id, message_id=msg.message_id, text="✅ تمت المعالجة! اختر الدولة:", reply_markup=InlineKeyboardMarkup(keyboard))

async def button_click(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer("جاري التجهيز...")
    
    conn = sqlite3.connect(DB_FILE)
    result = pd.read_sql_query(f"SELECT * FROM cards WHERE country = '{query.data}'", conn)
    conn.close()
    
    output_file = f"/tmp/{query.data}.csv"
    result.to_csv(output_file, index=False)
    
    await query.message.reply_document(document=open(output_file, 'rb'))

def main():
    init_db()
    app = Application.builder().token(TOKEN).build()
    
    app.add_handler(CommandHandler("start", start))
    app.add_handler(MessageHandler(filters.Document.ALL, handle_document))
    app.add_handler(CallbackQueryHandler(button_click))
    
    print("البوت يعمل الآن...")
    app.run_polling()

if __name__ == "__main__":
    main()
