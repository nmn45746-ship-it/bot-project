import asyncio
import logging
import os
from aiogram import Bot, Dispatcher
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
from aiogram.fsm.storage.memory import MemoryStorage
from handlers import private
from handlers import group
from handlers import start
from handlers.start import start_router
from handlers.private import private_router
from handlers.group import group_router
# from bot.handlers.game_actions import game_actions_router


def setup_logging() -> None:
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
    )


# def get_token() -> str:
#     token = os.getenv("BOT_TOKEN")
#     if not token:
#         raise ValueError("BOT_TOKEN environment variable topilmadi")
#     return token


def setup_dispatcher() -> Dispatcher:
    dp = Dispatcher(storage=MemoryStorage())
    dp.include_router(private_router)
    dp.include_router(group_router)
    dp.include_router(start_router)
    # dp.include_router(game_actions_router)

    return dp


async def main() -> None:
    setup_logging()

    bot = Bot(
        token='8760199614:AAFIhoiT5tV3kJmbzcE6bBjKw_-ZzQn61-8',
        default=DefaultBotProperties(parse_mode=ParseMode.HTML),
    )

    dp = setup_dispatcher()

    try:
        logging.info("Bot ishga tushmoqda...")
        await dp.start_polling(bot)
    finally:
        await bot.session.close()
        logging.info("Bot to'xtadi.")


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("Bot manual to'xtatildi.")
