import configparser
from datetime import datetime
from pathlib import Path

import pytz
from aiogram import Router, F, Bot, types, flags
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
from aiogram.filters.state import StateFilter
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import StatesGroup, State
from aiogram.types import CallbackQuery
from aiogram.types import Message
from aiogram.utils.formatting import Text
from openai import OpenAI

from base import get_or_create_user_data, save_user_data
from buttons import (
    keyboard_pic,
    keyboard,
    keyboard_model,
    keyboard_context,
    keyboard_voice,
    keyboard_value_work,
)
from function import (
    process_voice_message,
    info_menu_func,
)
from handler_work import register_handlers
from middlewares import ThrottlingMiddleware
from text import start_message, system_message_text, help_message

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

    user_data["model"] = "gpt-4o-mini"
    user_data["model_message_info"] = "4o mini"
    user_data["model_message_chat"] = "4o mini:\n\n"
    user_data["messages"] = []
    user_data["count_messages"] = 0
    user_data["max_out"] = 240000
    user_data["voice_answer"] = False
    user_data["system_message"] = ""
    user_data["pic_grade"] = "standard"
    user_data["pic_size"] = "1024x1024"

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
        text=f"<i>Модель:</i> {user_data["model_message_info"]} ",
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

    if user_data["model"] == "gpt-4o-mini":
        await callback_query.answer()
        return

    user_data["model"] = "gpt-4o-mini"
    user_data["max_out"] = 240000
    user_data["model_message_info"] = "4o mini"
    user_data["model_message_chat"] = "4o mini:\n\n"

    # Сохранение обновленных данных в базу данных
    await save_user_data(user_id)

    await callback_query.message.edit_text(
        text=f"<i>Модель:</i> {user_data["model_message_info"]} ",
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

    if user_data["model"] == "gpt-4o":
        await callback_query.answer()
        return

    user_data["model"] = "gpt-4o"
    user_data["max_out"] = 240000
    user_data["model_message_info"] = "4o"
    user_data["model_message_chat"] = "4o:\n\n"

    # Сохранение обновленных данных в базу данных
    await save_user_data(user_id)

    await callback_query.message.edit_text(
        text=f"<i>Модель:</i> {user_data["model_message_info"]} ",
        reply_markup=keyboard_model,
    )

    await callback_query.answer()
    return


@router.callback_query(F.data == "gpt_o1_mini")
async def process_callback_menu_1(callback_query: CallbackQuery):
    user_id = callback_query.from_user.id

    if user_id not in OWNER_ID:
        await callback_query.answer("Извините, у вас нет доступа к этому боту.")
        return

    # Получение или создание объектов пользовательских данных
    user_data = await get_or_create_user_data(user_id)

    if user_data["model"] == "o1-mini":
        await callback_query.answer()
        return

    user_data["model"] = "o1-mini"
    user_data["max_out"] = 240000
    user_data["model_message_info"] = "o1 mini"
    user_data["model_message_chat"] = "o1 mini:\n\n"

    # Сохранение обновленных данных в базу данных
    await save_user_data(user_id)

    await callback_query.message.edit_text(
        text=f"<i>Модель:</i> {user_data["model_message_info"]} ",
        reply_markup=keyboard_model,
    )

    await callback_query.answer()
    return


@router.callback_query(F.data == "gpt_o1_preview")
async def process_callback_menu_2(callback_query: CallbackQuery):
    user_id = callback_query.from_user.id

    if user_id not in OWNER_ID:
        await callback_query.answer("Извините, у вас нет доступа к этому боту.")
        return

    # Получение или создание объектов пользовательских данных
    user_data = await get_or_create_user_data(user_id)

    if user_data["model"] == "o1-preview":
        await callback_query.answer()
        return

    user_data["model"] = "o1-preview"
    user_data["max_out"] = 240000
    user_data["model_message_info"] = "o1"
    user_data["model_message_chat"] = "o1:\n\n"

    # Сохранение обновленных данных в базу данных
    await save_user_data(user_id)

    await callback_query.message.edit_text(
        text=f"<i>Модель:</i> {user_data["model_message_info"]} ",
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

    if user_data["model"] == "dall-e-3":
        await callback_query.answer()
        return

    user_data["model"] = "dall-e-3"
    user_data["model_message_info"] = "DALL·E 3"
    user_data["model_message_chat"] = "DALL·E 3:\n\n"

    # Сохранение обновленных данных в базу данных
    await save_user_data(user_id)

    await callback_query.message.edit_text(
        text=f"<i>Модель:</i> {user_data["model_message_info"]} ",
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
        text=f"{user_data["pic_grade"]} : {user_data["pic_size"]} ",
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

    if user_data["pic_grade"] == "standard":
        await callback_query.answer()
        return

    user_data["pic_grade"] = "standard"

    # Сохранение обновленных данных в базу данных
    await save_user_data(user_id)

    await callback_query.message.edit_text(
        text=f"{user_data["pic_grade"]} : {user_data["pic_size"]} ",
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

    if user_data["pic_grade"] == "hd":
        await callback_query.answer()
        return

    user_data["pic_grade"] = "hd"

    # Сохранение обновленных данных в базу данных
    await save_user_data(user_id)

    await callback_query.message.edit_text(
        text=f"{user_data["pic_grade"]} : {user_data["pic_size"]} ",
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

    if user_data["pic_size"] == "1024x1024":
        await callback_query.answer()
        return

    user_data["pic_size"] = "1024x1024"

    # Сохранение обновленных данных в базу данных
    await save_user_data(user_id)

    await callback_query.message.edit_text(
        text=f"{user_data["pic_grade"]} : {user_data["pic_size"]} ",
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

    if user_data["pic_size"] == "1024x1792":
        await callback_query.answer()
        return

    user_data["pic_size"] = "1024x1792"

    # Сохранение обновленных данных в базу данных
    await save_user_data(user_id)

    await callback_query.message.edit_text(
        text=f"{user_data["pic_grade"]} : {user_data["pic_size"]} ",
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

    if user_data["pic_size"] == "1792x1024":
        await callback_query.answer()
        return

    user_data["pic_size"] = "1792x1024"

    # Сохранение обновленных данных в базу данных
    await save_user_data(user_id)

    await callback_query.message.edit_text(
        text=f"{user_data["pic_grade"]} : {user_data["pic_size"]} ",
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
        text=f"<i>Сообщений:</i> {user_data["count_messages"]} ",
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
    history = await generate_history(user_data["messages"])

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

    await send_menu(user_id)


async def send_message(user_id, content):
    content_kwargs = Text(content)
    await bot.send_message(
        user_id,
        **content_kwargs.as_kwargs(),
        disable_web_page_preview=True,
    )


async def send_menu(user_id):
    await bot.send_message(
        user_id,
        text=f"Действия с контекстом",
        reply_markup=keyboard_context,
    )


@router.callback_query(F.data == "clear")
async def process_callback_clear(callback_query: CallbackQuery):
    user_id = callback_query.from_user.id

    if user_id not in OWNER_ID:
        await callback_query.answer("Извините, у вас нет доступа к этому боту.")
        return

    # Получение или создание объектов пользовательских данных
    user_data = await get_or_create_user_data(user_id)

    user_data["messages"] = []
    user_data["count_messages"] = 0

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

    info_voice_answer = "Включен" if user_data["voice_answer"] else "Выключен"

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

    if user_data["voice_answer"]:
        await callback_query.answer()
        return

    user_data["voice_answer"] = True

    # Сохранение обновленных данных в базу данных
    await save_user_data(user_id)

    info_voice_answer = "Включен" if user_data["voice_answer"] else "Выключен"

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

    if not user_data["voice_answer"]:
        await callback_query.answer()
        return

    user_data["voice_answer"] = False

    # Сохранение обновленных данных в базу данных
    await save_user_data(user_id)

    info_voice_answer = "Включен" if user_data["voice_answer"] else "Выключен"

    await callback_query.message.edit_text(
        text=f"<i>Аудио:</i> {info_voice_answer}",
        reply_markup=keyboard_voice,
    )

    await callback_query.answer()
    return


@router.callback_query(F.data == "back_menu")
async def process_callback_menu_back(callback_query: CallbackQuery, state: FSMContext):
    user_id = callback_query.from_user.id

    if user_id not in OWNER_ID:
        await callback_query.answer("Извините, у вас нет доступа к этому боту.")
        return

    if state is not None:
        await state.clear()

    info_menu = await info_menu_func(user_id)

    await callback_query.message.edit_text(text=f"{info_menu}", reply_markup=keyboard)
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

    info_voice_answer = "Включен" if user_data["voice_answer"] else "Выключен"

    info_system_message = (
        "Отсутствует"
        if not user_data["system_message"]
        else user_data["system_message"]
    )

    info_messages = (
        f"<i>Старт:</i> <b>{formatted_datetime}</b>\n"
        f"<i>User ID:</i> <b>{user_id}</b>\n"
        f"<i>Модель:</i> <b>{user_data["model_message_info"]}</b>\n"
        f"<i>Картинка</i>\n"
        f"<i>Качество:</i> <b>{user_data["pic_grade"]}</b>\n"
        f"<i>Размер:</i> <b>{user_data["pic_size"]}</b>\n"
        f"<i>Сообщения:</i> <b>{user_data["count_messages"]}</b>\n"
        f"<i>Аудио ответ:</i> <b>{info_voice_answer}</b>\n"
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
        "Отсутствует"
        if not user_data["system_message"]
        else user_data["system_message"]
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
async def process_callback_delete_value(
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

    if not user_data["system_message"]:
        await callback_query.answer()
        return

    user_data["system_message"] = ""

    # Сохранение обновленных данных в базу данных
    await save_user_data(user_id)

    info_system_message = (
        "Отсутствует"
        if not user_data["system_message"]
        else user_data["system_message"]
    )

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

    user_data["system_message"] = sys_massage

    # Сохранение обновленных данных в базу данных
    await save_user_data(user_id)

    await state.clear()

    info_system_message = (
        "Отсутствует"
        if not user_data["system_message"]
        else user_data["system_message"]
    )

    await message.answer(
        text=f"<i>Роль:</i> {info_system_message}",
        reply_markup=keyboard_value_work,
    )
    return


# Остальные хендлеры
register_handlers(router, bot, client, OWNER_ID)
