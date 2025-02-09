import asyncio
import configparser
import logging
import sys
from pathlib import Path

from aiogram import Bot, Dispatcher, types
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
from aiogram.fsm.storage.memory import MemoryStorage

from classes import init_async_db
from handler_menu import router

config = configparser.ConfigParser()
config.read(Path(__file__).parent / "config.ini")

TOKEN = config.get("Telegram", "token")


async def set_commands(bot: Bot):
    commands = {
        types.BotCommandScopeAllPrivateChats(): [
            types.BotCommand(command="/start", description="📌 старт"),
            types.BotCommand(command="/menu", description="⚙️ меню"),
            types.BotCommand(command="/help", description="🧰 помощь!"),
            types.BotCommand(command="/null", description="🛠 заводские настройки"),
        ],
        types.BotCommandScopeAllGroupChats(): [],
    }

    for scope, command_list in commands.items():
        await bot.set_my_commands(commands=command_list, scope=scope)


async def start_bot():
    bot = Bot(token=TOKEN, default=DefaultBotProperties(parse_mode=ParseMode.HTML))
    dp = Dispatcher(storage=MemoryStorage())
    dp.include_router(router)
    await bot.delete_webhook(drop_pending_updates=True)
    return bot, dp


async def main():
    bot = None
    try:
        await init_async_db()
        bot, dp = await start_bot()
        await set_commands(bot)
        await dp.start_polling(bot, allowed_updates=dp.resolve_used_update_types())
    except Exception as e:
        logging.exception(f"An error occurred: {e}")
    finally:
        if bot is not None:
            await bot.session.close()


if __name__ == "__main__":
    logging.basicConfig(level=logging.ERROR, stream=sys.stdout)
    asyncio.run(main())
