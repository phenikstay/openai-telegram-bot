import asyncio
import base64
import configparser
import logging
from datetime import datetime
from pathlib import Path

import pytz
from aiogram import Router, F, Bot, types, flags
from aiogram.client.default import DefaultBotProperties
from aiogram.client.session import aiohttp
from aiogram.enums import ParseMode
from aiogram.filters.state import StateFilter
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import StatesGroup, State
from aiogram.types import CallbackQuery
from aiogram.types import Message, FSInputFile
from aiogram.utils.formatting import Text, Bold
from openai import OpenAI

from base import get_or_create_user_data, save_user_data
from buttons import (
    keyboard_model,
    keyboard_context,
    keyboard_voice,
    keyboard_value_work,
)
from buttons import keyboard_pic, keyboard
from function import info_menu_func
from function import prune_messages, process_voice_message
from middlewares import ThrottlingMiddleware
from text import start_message, help_message, system_message_text

# Установка часового пояса, например, часовой пояс Москвы (UTC+3)
timezone = pytz.timezone("Europe/Moscow")

# Получение текущей даты и времени
current_datetime = datetime.now(timezone)

# Форматирование даты и времени
formatted_datetime = current_datetime.strftime("%d.%m.%Y %H:%M:%S")

# Чтение параметров из config.ini
config = configparser.ConfigParser()

config.read(Path(__file__).parent / "config.ini")

TOKEN = config.get("Telegram", "token")

bot = Bot(token=TOKEN, default=DefaultBotProperties(parse_mode=ParseMode.HTML))

# Параметры для OpenAI
openai_api_key = config.get("OpenAI", "api_key")

# Использование параметров для инициализации OpenAI
client = OpenAI(api_key=openai_api_key)

# Чтение списка ID из файла
OWNER_ID = {int(owner_id) for owner_id in config.get("Telegram", "owner_id").split(",")}

# Инициализация маршрутизатора
router = Router()

router.message.middleware(ThrottlingMiddleware(spin=1.5))

last_message_id = {}


# Создаем класс для машины состояний
class ChangeValueState(StatesGroup):
    waiting_for_new_value = State()


@router.message(F.text == "/start")
@flags.throttling_key("spin")
async def command_start_handler(message: Message, state: FSMContext):
    user_id = message.from_user.id

    if user_id not in OWNER_ID:
        await message.answer(
            f"<i>Извините, у вас нет доступа к этому боту.\n"
            f"Ваш User ID:</i> <b>{user_id}</b>"
        )
        return

    if state is not None:
        await state.clear()

    # Получение или создание объектов пользовательских данных
    user_data = await get_or_create_user_data(user_id)

    user_data.model = "gpt-4o-mini"
    user_data.model_message_info = "GPT-4o mini"
    user_data.model_message_chat = "GPT-4o mini:\n\n"
    user_data.messages = []
    user_data.count_messages = 0
    user_data.max_out = 128000
    user_data.voice_answer = False
    user_data.system_message = ""
    user_data.pic_grade = "standard"
    user_data.pic_size = "1024x1024"

    # Сохранение обновленных данных в базу данных
    await save_user_data(user_id)

    await message.answer(start_message)
    return


@router.message(F.text == "/menu")
@flags.throttling_key("spin")
async def process_key_button(message: Message, state: FSMContext):
    user_id = message.from_user.id

    if user_id not in OWNER_ID:
        await message.answer("Извините, у вас нет доступа к этому боту.")
        return

    if state is not None:
        await state.clear()

    info_menu = await info_menu_func(user_id)

    await message.answer(text=f"{info_menu}", reply_markup=keyboard)
    return


@router.callback_query(F.data == "model_choice")
async def process_callback_model_choice(
        callback_query: CallbackQuery, state: FSMContext
):
    user_id = callback_query.from_user.id

    if user_id not in OWNER_ID:
        await callback_query.answer("Извините, у вас нет доступа к этому боту.")
        return

    if state is not None:
        await state.clear()

    # Получение или создание объектов пользовательских данных
    user_data = await get_or_create_user_data(user_id)

    await callback_query.message.edit_text(
        text=f"<i>Модель:</i> {user_data.model_message_info} ",
        reply_markup=keyboard_model,
    )

    await callback_query.answer()
    return


@router.callback_query(F.data == "gpt_4o_mini")
async def process_callback_menu_1(callback_query: CallbackQuery):
    user_id = callback_query.from_user.id

    if user_id not in OWNER_ID:
        await callback_query.answer("Извините, у вас нет доступа к этому боту.")
        return

    # Получение или создание объектов пользовательских данных
    user_data = await get_or_create_user_data(user_id)

    if user_data.model == "gpt-4o-mini":
        await callback_query.answer()
        return

    user_data.model = "gpt-4o-mini"
    user_data.max_out = 128000
    user_data.model_message_info = "GPT-4o mini"
    user_data.model_message_chat = "GPT-4o mini:\n\n"

    # Сохранение обновленных данных в базу данных
    await save_user_data(user_id)

    await callback_query.message.edit_text(
        text=f"<i>Модель:</i> {user_data.model_message_info} ",
        reply_markup=keyboard_model,
    )

    await callback_query.answer()
    return


@router.callback_query(F.data == "gpt_4_o")
async def process_callback_menu_2(callback_query: CallbackQuery):
    user_id = callback_query.from_user.id

    if user_id not in OWNER_ID:
        await callback_query.answer("Извините, у вас нет доступа к этому боту.")
        return

    # Получение или создание объектов пользовательских данных
    user_data = await get_or_create_user_data(user_id)

    if user_data.model == "gpt-4o":
        await callback_query.answer()
        return

    user_data.model = "gpt-4o"
    user_data.max_out = 128000
    user_data.model_message_info = "GPT-4o"
    user_data.model_message_chat = "GPT-4o:\n\n"

    # Сохранение обновленных данных в базу данных
    await save_user_data(user_id)

    await callback_query.message.edit_text(
        text=f"<i>Модель:</i> {user_data.model_message_info} ",
        reply_markup=keyboard_model,
    )

    await callback_query.answer()
    return


@router.callback_query(F.data == "dall_e_3")
async def process_callback_menu_3(callback_query: CallbackQuery):
    user_id = callback_query.from_user.id

    if user_id not in OWNER_ID:
        await callback_query.answer("Извините, у вас нет доступа к этому боту.")
        return

    # Получение или создание объектов пользовательских данных
    user_data = await get_or_create_user_data(user_id)

    if user_data.model == "dall-e-3":
        await callback_query.answer()
        return

    user_data.model = "dall-e-3"
    user_data.model_message_info = "DALL·E 3 HD"
    user_data.model_message_chat = "DALL·E 3 HD:\n\n"

    # Сохранение обновленных данных в базу данных
    await save_user_data(user_id)

    await callback_query.message.edit_text(
        text=f"<i>Модель:</i> {user_data.model_message_info} ",
        reply_markup=keyboard_model,
    )

    await callback_query.answer()
    return


@router.callback_query(F.data == "pic_setup")
async def process_callback_menu_pic_setup(
        callback_query: CallbackQuery, state: FSMContext
):
    user_id = callback_query.from_user.id

    if user_id not in OWNER_ID:
        await callback_query.answer("Извините, у вас нет доступа к этому боту.")
        return

    if state is not None:
        await state.clear()

    # Получение или создание объектов пользовательских данных
    user_data = await get_or_create_user_data(user_id)

    await callback_query.message.edit_text(
        text=f"{user_data.pic_grade} : {user_data.pic_size} ",
        reply_markup=keyboard_pic,
    )

    await callback_query.answer()
    return


@router.callback_query(F.data == "set_sd")
async def process_callback_set_sd(callback_query: CallbackQuery):
    user_id = callback_query.from_user.id

    if user_id not in OWNER_ID:
        await callback_query.answer("Извините, у вас нет доступа к этому боту.")
        return

    # Получение или создание объектов пользовательских данных
    user_data = await get_or_create_user_data(user_id)

    if user_data.pic_grade == "standard":
        await callback_query.answer()
        return

    user_data.pic_grade = "standard"

    # Сохранение обновленных данных в базу данных
    await save_user_data(user_id)

    await callback_query.message.edit_text(
        text=f"{user_data.pic_grade} : {user_data.pic_size} ",
        reply_markup=keyboard_pic,
    )

    await callback_query.answer()
    return


@router.callback_query(F.data == "set_hd")
async def process_callback_set_hd(callback_query: CallbackQuery):
    user_id = callback_query.from_user.id

    if user_id not in OWNER_ID:
        await callback_query.answer("Извините, у вас нет доступа к этому боту.")
        return

    # Получение или создание объектов пользовательских данных
    user_data = await get_or_create_user_data(user_id)

    if user_data.pic_grade == "hd":
        await callback_query.answer()
        return

    user_data.pic_grade = "hd"

    # Сохранение обновленных данных в базу данных
    await save_user_data(user_id)

    await callback_query.message.edit_text(
        text=f"{user_data.pic_grade} : {user_data.pic_size} ",
        reply_markup=keyboard_pic,
    )

    await callback_query.answer()
    return


@router.callback_query(F.data == "set_1024x1024")
async def process_callback_set_1024x1024(callback_query: CallbackQuery):
    user_id = callback_query.from_user.id

    if user_id not in OWNER_ID:
        await callback_query.answer("Извините, у вас нет доступа к этому боту.")
        return

    # Получение или создание объектов пользовательских данных
    user_data = await get_or_create_user_data(user_id)

    if user_data.pic_size == "1024x1024":
        await callback_query.answer()
        return

    user_data.pic_size = "1024x1024"

    # Сохранение обновленных данных в базу данных
    await save_user_data(user_id)

    await callback_query.message.edit_text(
        text=f"{user_data.pic_grade} : {user_data.pic_size} ",
        reply_markup=keyboard_pic,
    )

    await callback_query.answer()
    return


@router.callback_query(F.data == "set_1024x1792")
async def process_callback_set_1024x1792(callback_query: CallbackQuery):
    user_id = callback_query.from_user.id

    if user_id not in OWNER_ID:
        await callback_query.answer("Извините, у вас нет доступа к этому боту.")
        return

    # Получение или создание объектов пользовательских данных
    user_data = await get_or_create_user_data(user_id)

    if user_data.pic_size == "1024x1792":
        await callback_query.answer()
        return

    user_data.pic_size = "1024x1792"

    # Сохранение обновленных данных в базу данных
    await save_user_data(user_id)

    await callback_query.message.edit_text(
        text=f"{user_data.pic_grade} : {user_data.pic_size} ",
        reply_markup=keyboard_pic,
    )

    await callback_query.answer()
    return


@router.callback_query(F.data == "set_1792x1024")
async def process_callback_set_1792x1024(callback_query: CallbackQuery):
    user_id = callback_query.from_user.id

    if user_id not in OWNER_ID:
        await callback_query.answer("Извините, у вас нет доступа к этому боту.")
        return

    # Получение или создание объектов пользовательских данных
    user_data = await get_or_create_user_data(user_id)

    if user_data.pic_size == "1792x1024":
        await callback_query.answer()
        return

    user_data.pic_size = "1792x1024"

    # Сохранение обновленных данных в базу данных
    await save_user_data(user_id)

    await callback_query.message.edit_text(
        text=f"{user_data.pic_grade} : {user_data.pic_size} ",
        reply_markup=keyboard_pic,
    )

    await callback_query.answer()
    return


@router.callback_query(F.data == "context_work")
async def process_callback_context_work(
        callback_query: CallbackQuery, state: FSMContext
):
    user_id = callback_query.from_user.id

    if user_id not in OWNER_ID:
        await callback_query.answer("Извините, у вас нет доступа к этому боту.")
        return

    if state is not None:
        await state.clear()

    # Получение или создание объектов пользовательских данных
    user_data = await get_or_create_user_data(user_id)

    await callback_query.message.edit_text(
        text=f"<i>Сообщений:</i> {user_data.count_messages} ",
        reply_markup=keyboard_context,
    )

    await callback_query.answer()
    return


@router.callback_query(F.data == "context")
async def process_callback_context(callback_query: CallbackQuery):
    user_id = callback_query.from_user.id

    if user_id not in OWNER_ID:
        await callback_query.answer("Извините, у вас нет доступа к этому боту.")
        return

    user_data = await get_or_create_user_data(user_id)
    history = await generate_history(user_data.messages)

    if callback_query.message.text == "Контекст пуст":
        await callback_query.answer()
        return

    if not history:
        await callback_query.message.edit_text(
            text="Контекст пуст", reply_markup=keyboard_context
        )
        await callback_query.answer()
        return

    await send_history(callback_query.from_user.id, history)
    await callback_query.message.edit_text(text="Контекст:", reply_markup=None)
    await callback_query.answer()


async def generate_history(messages):
    return "\n\n".join(f"{msg['role']}:\n{msg['content']}" for msg in messages)


async def send_history(user_id, history):
    max_length = 4096
    # Разбиваем историю на строки
    lines = history.split("\n")
    chunks = []
    current_chunk = []

    current_length = 0
    for line in lines:
        # Добавляем длину строки и символ новой строки
        line_length = len(line) + 1

        # Проверяем превышение длины текущего чанка
        if current_length + line_length > max_length:
            # Добавляем текущий чанк в список чанков
            chunks.append("\n".join(current_chunk))
            # Начинаем новый чанк
            current_chunk = [line]
            current_length = line_length
        else:
            # Добавляем строку в текущий чанк и увеличиваем длину
            current_chunk.append(line)
            current_length += line_length

    # Добавляем последний чанк, если он не пуст
    if current_chunk:
        chunks.append("\n".join(current_chunk))

    # Отправляем все чанки
    for chunk in chunks:
        await send_message(user_id, chunk)


async def send_message(user_id, content):
    content_kwargs = Text(content)
    await bot.send_message(
        user_id,
        **content_kwargs.as_kwargs(),
        disable_web_page_preview=True,
    )


@router.callback_query(F.data == "clear")
async def process_callback_clear(callback_query: CallbackQuery):
    user_id = callback_query.from_user.id

    if user_id not in OWNER_ID:
        await callback_query.answer("Извините, у вас нет доступа к этому боту.")
        return

    # Получение или создание объектов пользовательских данных
    user_data = await get_or_create_user_data(user_id)

    user_data.messages = []
    user_data.count_messages = 0

    # Сохранение обновленных данных в базу данных
    await save_user_data(user_id)

    if callback_query.message.text == "Контекст очищен":
        await callback_query.answer()
        return

    await callback_query.message.edit_text(
        text="Контекст очищен", reply_markup=keyboard_context
    )

    await callback_query.answer()
    return


@router.callback_query(F.data == "voice_answer_work")
async def process_callback_voice_answer_work(
        callback_query: CallbackQuery, state: FSMContext
):
    user_id = callback_query.from_user.id

    if user_id not in OWNER_ID:
        await callback_query.answer("Извините, у вас нет доступа к этому боту.")
        return

    if state is not None:
        await state.clear()

    # Получение или создание объектов пользовательских данных
    user_data = await get_or_create_user_data(user_id)

    info_voice_answer = "Включен" if user_data.voice_answer else "Выключен"

    await callback_query.message.edit_text(
        text=f"<i>Аудио:</i> {info_voice_answer}",
        reply_markup=keyboard_voice,
    )

    await callback_query.answer()
    return


@router.callback_query(F.data == "voice_answer_add")
async def process_callback_voice_answer_add(callback_query: CallbackQuery):
    user_id = callback_query.from_user.id

    if user_id not in OWNER_ID:
        await callback_query.answer("Извините, у вас нет доступа к этому боту.")
        return

    # Получение или создание объектов пользовательских данных
    user_data = await get_or_create_user_data(user_id)

    if user_data.voice_answer:
        await callback_query.answer()
        return

    user_data.voice_answer = True

    # Сохранение обновленных данных в базу данных
    await save_user_data(user_id)

    info_voice_answer = "Включен" if user_data.voice_answer else "Выключен"

    await callback_query.message.edit_text(
        text=f"<i>Аудио:</i> {info_voice_answer}", reply_markup=keyboard_voice
    )

    await callback_query.answer()
    return


@router.callback_query(F.data == "voice_answer_del")
async def process_callback_voice_answer_del(callback_query: CallbackQuery):
    user_id = callback_query.from_user.id

    if user_id not in OWNER_ID:
        await callback_query.answer("Извините, у вас нет доступа к этому боту.")
        return

    # Получение или создание объектов пользовательских данных
    user_data = await get_or_create_user_data(user_id)

    if not user_data.voice_answer:
        await callback_query.answer()
        return

    user_data.voice_answer = False

    # Сохранение обновленных данных в базу данных
    await save_user_data(user_id)

    info_voice_answer = "Включен" if user_data.voice_answer else "Выключен"

    await callback_query.message.edit_text(
        text=f"<i>Аудио:</i> {info_voice_answer}",
        reply_markup=keyboard_voice,
    )

    await callback_query.answer()
    return


@router.callback_query(F.data == "system_value_work")
async def process_callback_voice_answer_work(
        callback_query: CallbackQuery, state: FSMContext
):
    user_id = callback_query.from_user.id

    if user_id not in OWNER_ID:
        await callback_query.answer("Извините, у вас нет доступа к этому боту.")
        return

    if state is not None:
        await state.clear()

    # Получение или создание объектов пользовательских данных
    user_data = await get_or_create_user_data(user_id)

    info_system_message = (
        "Отсутствует" if not user_data.system_message else user_data.system_message
    )

    await callback_query.message.edit_text(
        text=f"<i>Роль:</i> {info_system_message}",
        reply_markup=keyboard_value_work,
    )

    await callback_query.answer()
    return


# Обработчик нажатия на кнопку
@router.callback_query(F.data == "change_value")
async def process_callback_change_value(
        callback_query: types.CallbackQuery, state: FSMContext
):
    user_id = callback_query.from_user.id

    if user_id not in OWNER_ID:
        await callback_query.answer("Извините, у вас нет доступа к этому боту.")
        return

    await state.set_state(ChangeValueState.waiting_for_new_value)

    await callback_query.message.edit_text(
        text=system_message_text,
        reply_markup=None,
    )

    await callback_query.answer()
    return


@router.callback_query(F.data == "delete_value")
async def process_callback_delete_value(callback_query: CallbackQuery):
    user_id = callback_query.from_user.id

    if user_id not in OWNER_ID:
        await callback_query.answer("Извините, у вас нет доступа к этому боту.")
        return

    # Получение или создание объектов пользовательских данных
    user_data = await get_or_create_user_data(user_id)

    if not user_data.system_message:
        await callback_query.answer()
        return

    user_data.system_message = ""

    # Сохранение обновленных данных в базу данных
    await save_user_data(user_id)

    info_system_message = "Задана" if user_data.system_message else "Отсутствует"

    await callback_query.message.edit_text(
        text=f"<i>Роль:</i> {info_system_message}",
        reply_markup=keyboard_value_work,
    )

    await callback_query.answer()
    return


# Обработчик ввода нового значения
@router.message(StateFilter(ChangeValueState.waiting_for_new_value))
async def process_new_value(message: types.Message, state: FSMContext):
    user_id = message.from_user.id

    if user_id not in OWNER_ID:
        await message.answer("Извините, у вас нет доступа к этому боту.")
        return

    global sys_massage

    if message.voice:
        sys_massage = await process_voice_message(bot, message, user_id)

    elif message.text:
        # Если сообщение содержит текст
        sys_massage = message.text

    # Ваш метод получения или создания данных пользователя
    user_data = await get_or_create_user_data(user_id)

    user_data.system_message = sys_massage

    # Сохранение обновленных данных в базу данных
    await save_user_data(user_id)

    await state.clear()

    await message.answer(
        f"<b>Системная роль изменена на:</b> <i>{user_data.system_message}</i>"
    )
    return


@router.callback_query(F.data == "back_menu")
async def process_callback_menu_back(callback_query: CallbackQuery):
    user_id = callback_query.from_user.id

    if user_id not in OWNER_ID:
        await callback_query.answer("Извините, у вас нет доступа к этому боту.")
        return

    info_menu = await info_menu_func(user_id)

    await callback_query.message.edit_text(
        text=f"{info_menu}", reply_markup=keyboard
    )
    return


@router.callback_query(F.data == "info")
async def process_callback_info(callback_query: CallbackQuery, state: FSMContext):
    user_id = callback_query.from_user.id

    if user_id not in OWNER_ID:
        await callback_query.answer("Извините, у вас нет доступа к этому боту.")
        return

    if state is not None:
        await state.clear()

    # Получение или создание объектов пользовательских данных
    user_data = await get_or_create_user_data(user_id)

    info_voice_answer = "Включен" if user_data.voice_answer else "Выключен"

    info_system_message = (
        "Отсутствует" if not user_data.system_message else user_data.system_message
    )

    info_messages = (
        f"<i>Старт:</i> <b>{formatted_datetime}</b>\n"
        f"<i>User ID:</i> <b>{user_id}</b>\n"
        f"<i>Модель:</i> <b>{user_data.model_message_info}</b>\n"
        f"<i>Картинка</i>\n"
        f"<i>Качество:</i> <b>{user_data.pic_grade}</b>\n"
        f"<i>Размер:</i> <b>{user_data.pic_size}</b>\n"
        f"<i>Сообщения:</i> <b>{user_data.count_messages}</b>\n"
        f"<i>Аудио:</i> <b>{info_voice_answer}</b>\n"
        f"<i>Роль:</i> <b>{info_system_message}</b>"
    )

    await callback_query.message.edit_text(
        text=info_messages,
        reply_markup=None,
    )

    await callback_query.answer()
    return


@router.message(F.text == "/help")
@flags.throttling_key("spin")
async def help_handler(message: Message, state: FSMContext):
    user_id = message.from_user.id

    if user_id not in OWNER_ID:
        await message.answer("Извините, у вас нет доступа к этому боту.")
        return

    if state is not None:
        await state.clear()

    # Получение или создание объектов пользовательских данных
    await get_or_create_user_data(user_id)

    await message.answer(help_message)
    return


@router.message(F.content_type.in_({"text", "voice"}))
async def chatgpt_text_handler(message: Message):
    user_id = message.from_user.id
    chat_id = message.chat.id

    if user_id not in OWNER_ID:
        await message.answer("Извините, у вас нет доступа к этому боту.")
        return

    # Получение или создание объектов пользовательских данных
    user_data = await get_or_create_user_data(user_id)

    promt = ""

    # Временное сообщение
    response = await message.answer(f"⏳ Подождите, Ваш запрос обрабатывается!")
    last_message_id = response.message_id

    if message.voice:
        promt = await process_voice_message(bot, message, user_id)

    elif message.text:
        # Если сообщение содержит текст
        promt = message.text

    if user_data.model == "gpt-4o-mini" or user_data.model == "gpt-4o":

        # Добавляем сообщение пользователя в историю чата
        user_data.messages.append({"role": "user", "content": promt})

        # Применяем функцию обрезки
        pruned_messages = await prune_messages(
            user_data.messages, max_chars=user_data.max_out
        )

        try:
            # Добавляем роль system временно, без сохранения в контексте
            system_message = {
                "role": "system",
                "content": user_data.system_message,
            }
            pruned_messages.insert(0, system_message)

            # Use asyncio.to_thread for OpenAI API call
            chat_completion = await asyncio.to_thread(
                lambda: client.chat.completions.create(
                    model=user_data.model, messages=pruned_messages
                )
            )

            # Бот печатает...
            await message.bot.send_chat_action(chat_id, action="typing")

            # Получаем ответ модели
            response_message = chat_completion.choices[0].message.content

            # Добавляем ответ модели в историю чата
            user_data.messages.append(
                {"role": "assistant", "content": response_message}
            )

            # Счетчик сообщений пользователя
            user_data.count_messages += 1

            # Сохранение обновленных данных в базу данных
            await save_user_data(user_id)

            # Удаление временного сообщения
            await message.bot.delete_message(chat_id, last_message_id)

            # Функция отправки kwargs
            async def send_message_kwargs(
                    model_massage_kwargs, response_message_kwargs
            ):
                content_kwargs = Text(
                    Bold(model_massage_kwargs), response_message_kwargs
                )
                await message.reply(
                    **content_kwargs.as_kwargs(), disable_web_page_preview=True
                )

            async def send_message_kwargs_long(
                    model_message_kwargs, response_message_kwargs
            ):
                content = f"{model_message_kwargs}\n{response_message_kwargs}"  # Соединяем две части сообщения
                messages = content.split("\n")  # Разделяем сообщение по \n
                chunk = ""
                chunks = []

                for line in messages:
                    if len(chunk) + len(line) + 1 > 4096:  # +1 для символа новой строки
                        chunks.append(chunk)
                        chunk = line
                    else:
                        if chunk:
                            chunk += line + "\n"
                        else:
                            chunk = line

                # Не забываем добавить последний кусок
                if chunk:
                    chunks.append(chunk)

                for chunk in chunks:
                    content_kwargs = Text(chunk)
                    await message.answer(
                        **content_kwargs.as_kwargs(),
                        disable_web_page_preview=True,
                    )

            # Функция отправки md
            async def send_message_md(model_massage_md, response_md):
                final_message = f"*{model_massage_md}*{response_md}"
                await message.reply(
                    final_message,
                    parse_mode=ParseMode.MARKDOWN,
                    disable_web_page_preview=True,
                )

            async def send_message_md_long(model_massage_md, response_md):
                final_message = f"*{model_massage_md}*\n{response_md}"

                lines = final_message.split("\n")
                chunks = []
                current_chunk = ""

                for line in lines:
                    # Если добавление ещё одной линии превысит лимит, добавляем текущий chunk и начинаем новый
                    if len(current_chunk) + len(line) + 1 > 4096:  # +1 для \n
                        chunks.append(current_chunk)
                        current_chunk = line
                    else:
                        if current_chunk:
                            current_chunk += line + "\n"
                        else:
                            current_chunk = line

                # Не забываем добавить последний chunk
                if current_chunk:
                    chunks.append(current_chunk)

                # Теперь отправляем все chunks как отдельные сообщения
                for chunk in chunks:
                    await message.answer(
                        chunk,
                        parse_mode=ParseMode.MARKDOWN,
                        disable_web_page_preview=True,
                    )

            async def text_to_speech(unic_id, text_message):
                """Генерирует голосовое сообщение из текста с использованием OpenAI API."""
                speech_file_path = Path(__file__).parent / f"voice/speech_{unic_id}.mp3"

                response_voice = await asyncio.to_thread(
                    lambda: client.audio.speech.create(
                        model="tts-1",
                        voice="nova",
                        input=text_message,
                    )
                )

                await asyncio.to_thread(
                    lambda: response_voice.stream_to_file(speech_file_path)
                )
                audio = FSInputFile(speech_file_path)

                return await bot.send_audio(
                    unic_id, audio, title="Аудио вариант ответа"
                )

            # Отправляем ответ модели пользователю
            try:
                if "```" in response_message:
                    if len(response_message) > 4096:
                        await send_message_md_long(
                            user_data.model_message_chat, response_message
                        )
                        if user_data.voice_answer:
                            await text_to_speech(message.chat.id, response_message)
                        return

                    await send_message_md(
                        user_data.model_message_chat, response_message
                    )
                    if user_data.voice_answer:
                        await text_to_speech(message.chat.id, response_message)
                    return

                else:
                    if len(response_message) > 4096:
                        await send_message_kwargs_long(
                            user_data.model_message_chat, response_message
                        )
                        if user_data.voice_answer:
                            await text_to_speech(message.chat.id, response_message)
                        return

                    await send_message_kwargs(
                        user_data.model_message_chat, response_message
                    )
                    if user_data.voice_answer:
                        await text_to_speech(message.chat.id, response_message)
                    return

            except Exception as e:
                logging.exception(e)
                if len(response_message) > 4096:
                    await send_message_kwargs_long(
                        user_data.model_message_chat, response_message
                    )
                    if user_data.voice_answer:
                        await text_to_speech(message.chat.id, response_message)
                    return

                await send_message_kwargs(
                    user_data.model_message_chat, response_message
                )
                if user_data.voice_answer:
                    await text_to_speech(message.chat.id, response_message)
                return

        except Exception as e:
            logging.exception(e)
            await message.reply(f"Произошла ошибка: {e}")
            return

    elif user_data.model == "dall-e-3":

        try:
            # Use asyncio.to_thread for OpenAI API call
            response = await asyncio.to_thread(
                lambda: client.images.generate(
                    prompt=promt,
                    n=1,
                    size=user_data.pic_size,
                    model="dall-e-3",
                    quality=user_data.pic_grade,
                )
            )

        except Exception as e:
            logging.exception(e)
            await message.reply(f"Произошла ошибка: {e}")
            return

        # Бот печатает...
        await message.bot.send_chat_action(chat_id, action="upload_photo")

        # Счетчик сообщений пользователя
        user_data.count_messages += 1

        # Сохранение обновленных данных в базу данных
        await save_user_data(user_id)

        # Удаление временного сообщения
        await message.bot.delete_message(chat_id, last_message_id)

        await message.bot.send_photo(
            message.chat.id,
            response.data[0].url,
            reply_to_message_id=message.message_id,
        )
        return


@router.message(F.photo)
async def chatgpt_photo_vision_handler(message: types.Message, state: FSMContext):
    user_id = message.from_user.id
    chat_id = message.chat.id

    if user_id not in OWNER_ID:
        await message.answer("Извините, у вас нет доступа к этому боту.")
        return

    if state is not None:
        await state.clear()

    try:
        user_data = await get_or_create_user_data(user_id)
        temp_message = await message.answer("⏳ Подождите, Ваш запрос обрабатывается!")

        text = message.caption or "Что на картинке?"
        photo = message.photo[-1]
        file_info = await message.bot.get_file(photo.file_id)
        file_url = f"https://api.telegram.org/file/bot{bot.token}/{file_info.file_path}"

        base64_image = await download_and_encode_image(file_url)

        ai_response = await process_image_with_gpt(text, base64_image)

        await update_user_data(user_data, user_id)
        await message.bot.delete_message(chat_id, temp_message.message_id)
        await message.answer(ai_response)

    except Exception as e:
        logging.exception(e)
        await message.reply(f"Произошла ошибка: {e}")


async def download_and_encode_image(url):
    async with aiohttp.ClientSession() as session:
        async with session.get(url) as resp:
            if resp.status == 200:
                image_content = await resp.read()
                base64_image = base64.b64encode(image_content).decode("utf-8")
                return f"data:image/jpeg;base64,{base64_image}"
    raise ValueError("Failed to download image")


async def process_image_with_gpt(text, base64_image):
    messages = [
        {
            "role": "user",
            "content": [
                {"type": "text", "text": text},
                {"type": "image_url", "image_url": {"url": base64_image}},
            ],
        }
    ]
    chat_completion = await asyncio.to_thread(
        lambda: client.chat.completions.create(
            model="gpt-4o", messages=messages, max_tokens=4000
        )
    )
    return chat_completion.choices[0].message.content


async def update_user_data(user_data, user_id):
    user_data.count_messages += 1
    await save_user_data(user_id)
