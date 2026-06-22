import asyncio
import logging
import os
from aiogram import Bot, Dispatcher
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
from aiogram.fsm.storage.memory import MemoryStorage
from dotenv import load_dotenv

# استيراد الراوترات (تأكد أن مساراتها صحيحة في مجلدك)
from handlers.start import start_router
from handlers.private import private_router
from handlers.group import group_router

# تحميل التوكن من ملف .env
load_dotenv()
BOT_TOKEN = os.getenv("BOT_TOKEN")

def setup_logging() -> None:
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
    )

def setup_dispatcher() -> Dispatcher:
    dp = Dispatcher(storage=MemoryStorage())
    dp.include_routers(private_router, group_router, start_router)
    return dp

async def main() -> None:
    if not BOT_TOKEN:
        raise ValueError("خطأ: لم يتم العثور على BOT_TOKEN في ملف .env")
        
    setup_logging()

    bot = Bot(
        token=BOT_TOKEN,
        default=DefaultBotProperties(parse_mode=ParseMode.HTML),
    )

    dp = setup_dispatcher()

    try:
        logging.info("البوت يعمل الآن...")
        await dp.start_polling(bot)
    finally:
        await bot.session.close()
        logging.info("تم إيقاف البوت.")

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("تم إيقاف البوت يدوياً.")
