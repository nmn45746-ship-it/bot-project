import os
import logging
import sqlite3
import pandas as pd
from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.ext import (Application, CommandHandler, MessageHandler, 
                          CallbackQueryHandler, filters, ContextTypes)

# إعداد السجلات
logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)

# قراءة التوكن من إعدادات الاستضافة (أكثر أماناً)
TOKEN = os.getenv("BOT_TOKEN")

def init_db():
    conn = sqlite3.connect('cards.db')
    cursor = conn.cursor()
    cursor.execute('CREATE TABLE IF NOT EXISTS cards (country TEXT, data TEXT)')
    conn.commit()
    conn.close()

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("مرحباً! أرسل ملف الـ Dump الآن.")

async def handle_document(update: Update, context: ContextTypes.DEFAULT_TYPE):
    file = await update.message.document.get_file()
    file_path = "dump.csv"
    await file.download_to_drive(file_path)
    await update.message.reply_text("جاري المعالجة...")

    conn = sqlite3.connect('cards.db')
    conn.execute('DELETE FROM cards')
    
    df = pd.read_csv(file_path)
    df.to_sql('cards', conn, if_exists='append', index=False)
    
    stats = pd.read_sql_query('SELECT country, COUNT(*) as count FROM cards GROUP BY country', conn)
    conn.close()
    
    keyboard = [[InlineKeyboardButton(f"{r['country']} ({r['count']})", callback_data=r['country'])] for _, r in stats.iterrows()]
    await update.message.reply_text("اختر الدولة:", reply_markup=InlineKeyboardMarkup(keyboard))

async def button_click(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    conn = sqlite3.connect('cards.db')
    result = pd.read_sql_query(f"SELECT * FROM cards WHERE country = '{query.data}'", conn)
    conn.close()
    
    output_file = f"{query.data}.csv"
    result.to_csv(output_file, index=False)
    await query.message.reply_document(document=open(output_file, 'rb'))

if __name__ == "__main__":
    init_db()
    # استخدام Application.builder للتشغيل
    app = Application.builder().token(TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(MessageHandler(filters.Document.ALL, handle_document))
    app.add_handler(CallbackQueryHandler(button_click))
    print("البوت يعمل...")
    app.run_polling()
