import configparser
from pathlib import Path
from typing import List

import aiosqlite

from classes import UserData

# Словарь для хранения данных пользователей
users_data = {}

# Чтение параметров из config.ini
config = configparser.ConfigParser()
config.read(Path(__file__).parent / "config.ini")


DB_FILE = Path(__file__).parent / "users_data.db"


async def get_or_create_user_data(user_id: int) -> UserData:
    if user_id in users_data:
        return users_data[user_id]

    user_data = await UserData.load_from_db(user_id)
    if user_data is None:
        user_data = UserData(user_id)

    users_data[user_id] = user_data
    return user_data


async def save_user_data(user_id: int) -> None:
    user_data = users_data.get(user_id)
    if user_data:
        await user_data.save_to_db()


async def get_all_users() -> List[str]:
    async with aiosqlite.connect(DB_FILE) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute("SELECT user_id FROM UsersData") as cursor:
            return [str(row["user_id"]) for row in await cursor.fetchall()]
