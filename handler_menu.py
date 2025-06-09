import logging
from datetime import datetime

import pytz
from aiogram import Router, F, types, flags
from aiogram.filters.state import StateFilter
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import StatesGroup, State
from aiogram.types import CallbackQuery
from aiogram.types import Message
from aiogram.utils.formatting import Text

from base import get_or_create_user_data, save_user_data
from bot_manager import get_bot
from buttons import (
    keyboard_pic,
    keyboard,
    keyboard_model,
    keyboard_context,
    keyboard_voice,
    keyboard_value_work,
)
from decorators import owner_only, owner_only_with_user_id_display
from function import (
    process_voice_message,
    info_menu_func,
)
from handler_work import reset_thread
from middlewares import ThrottlingMiddleware
from text import start_message, system_message_text, help_message, null_message

# Установка часового пояса
timezone = pytz.timezone("Europe/Moscow")


# Функция для получения текущего времени
def get_current_datetime():
    current_datetime = datetime.now(timezone)
    return current_datetime.strftime("%d.%m.%Y %H:%M:%S")


# Инициализация маршрутизатора
router = Router()

router.message.middleware(ThrottlingMiddleware(spin=1.5))


# Создаем класс для машины состояний
class ChangeValueState(StatesGroup):
    waiting_for_new_value = State()


@router.message(F.text == "/start")
@flags.throttling_key("spin")
@owner_only_with_user_id_display
async def command_start_handler(message: Message, state: FSMContext):
    user_id = message.from_user.id

    if state is not None:
        await state.clear()

    # Получение или создание объектов пользовательских данных
    await get_or_create_user_data(user_id)

    await message.answer(start_message)
    return


@router.message(F.text == "/null")
@flags.throttling_key("spin")
@owner_only
async def command_null_handler(message: Message, state: FSMContext):
    user_id = message.from_user.id

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

    # Очистка thread_id всех ассистентов
    reset_results = {}
    for assistant_number in range(1, 4):
        reset_results[assistant_number] = await reset_thread(
            user_data, user_id, assistant_number
        )

    # Логирование результатов сброса
    for assistant_number, success in reset_results.items():
        if not success:
            logging.warning(
                f"Не удалось сбросить thread для ассистента {assistant_number}"
            )

    user_data["current_assistant"] = 1

    # Очистка ID ассистентов
    user_data["assistant_id_1"] = ""
    user_data["assistant_id_2"] = ""
    user_data["assistant_id_3"] = ""

    # Сохранение обновленных данных в базу данных
    await save_user_data(user_id)

    await message.answer(null_message)
    return


@router.message(F.text == "/menu")
@flags.throttling_key("spin")
@owner_only
async def process_key_button(message: Message, state: FSMContext):
    user_id = message.from_user.id

    if state is not None:
        await state.clear()

    info_menu = await info_menu_func(user_id)

    await message.answer(text=f"{info_menu}", reply_markup=keyboard)

    return


@router.callback_query(F.data == "model_choice")
@owner_only
async def process_callback_model_choice(
    callback_query: CallbackQuery, state: FSMContext
):
    user_id = callback_query.from_user.id

    if state is not None:
        await state.clear()

    # Получение или создание объектов пользовательских данных
    user_data = await get_or_create_user_data(user_id)

    await callback_query.message.edit_text(
        text=f"<i>Модель:</i> {user_data['model_message_info']} ",
        reply_markup=keyboard_model,
    )

    await callback_query.answer()
    return


@router.callback_query(F.data == "gpt_4o_mini")
async def process_callback_menu_1(callback_query: CallbackQuery):
    model_config = {
        "model": "gpt-4o-mini",
        "model_message_info": "4o mini",
        "model_message_chat": "4o mini:\n\n",
        "max_out": 240000,
    }
    await handle_model_selection(callback_query, model_config)


@router.callback_query(F.data == "gpt_4_o")
async def process_callback_menu_2(callback_query: CallbackQuery):
    model_config = {
        "model": "gpt-4o",
        "model_message_info": "4o",
        "model_message_chat": "4o:\n\n",
        "max_out": 240000,
    }
    await handle_model_selection(callback_query, model_config)


@router.callback_query(F.data == "gpt_o1_mini")
async def process_callback_menu_3(callback_query: CallbackQuery):
    model_config = {
        "model": "o1-mini",
        "model_message_info": "o1 mini",
        "model_message_chat": "o1 mini:\n\n",
        "max_out": 240000,
    }
    await handle_model_selection(callback_query, model_config)


@router.callback_query(F.data == "gpt_o1_preview")
async def process_callback_menu_4(callback_query: CallbackQuery):
    model_config = {
        "model": "o1-preview",
        "model_message_info": "o1 preview",
        "model_message_chat": "o1 preview:\n\n",
        "max_out": 240000,
    }
    await handle_model_selection(callback_query, model_config)


@router.callback_query(F.data == "o3-mini")
async def process_callback_menu_5(callback_query: CallbackQuery):
    model_config = {
        "model": "o3-mini",
        "model_message_info": "o3 mini",
        "model_message_chat": "o3 mini:\n\n",
        "max_out": 240000,
    }
    await handle_model_selection(callback_query, model_config)


@router.callback_query(F.data == "dall_e_3")
async def process_callback_menu_6(callback_query: CallbackQuery):
    model_config = {
        "model": "dall-e-3",
        "model_message_info": "DALL·E 3",
        "model_message_chat": "DALL·E 3:\n\n",
    }
    await handle_model_selection(callback_query, model_config)


@router.callback_query(F.data == "o1-pro")
async def process_callback_o1_pro(callback_query: CallbackQuery):
    model_config = {
        "model": "o1-pro",
        "model_message_info": "o1 pro",
        "model_message_chat": "o1 pro:\n\n",
        "max_out": 240000,
    }
    await handle_model_selection(callback_query, model_config)


@router.callback_query(F.data == "gpt-4o-search-preview")
async def process_callback_gpt_4o_search_preview(callback_query: CallbackQuery):
    model_config = {
        "model": "gpt-4o-search-preview",
        "model_message_info": "Web 4o",
        "model_message_chat": "Web 4o:\n\n",
        "max_out": 5900,
    }
    await handle_model_selection(callback_query, model_config)


@router.callback_query(F.data == "assistant_1")
async def process_callback_assistant_1(callback_query: CallbackQuery):
    model_config = {
        "model": "assistant",
        "model_message_info": "ASSISTANT 1",
        "model_message_chat": "ASSISTANT 1:\n\n",
        "assistant_number": 1,
    }
    await handle_model_selection(callback_query, model_config)


@router.callback_query(F.data == "assistant_2")
async def process_callback_assistant_2(callback_query: CallbackQuery):
    model_config = {
        "model": "assistant",
        "model_message_info": "ASSISTANT 2",
        "model_message_chat": "ASSISTANT 2:\n\n",
        "assistant_number": 2,
    }
    await handle_model_selection(callback_query, model_config)


@router.callback_query(F.data == "assistant_3")
async def process_callback_assistant_3(callback_query: CallbackQuery):
    model_config = {
        "model": "assistant",
        "model_message_info": "ASSISTANT 3",
        "model_message_chat": "ASSISTANT 3:\n\n",
        "assistant_number": 3,
    }
    await handle_model_selection(callback_query, model_config)


@router.callback_query(F.data == "pic_setup")
@owner_only
async def process_callback_menu_pic_setup(
    callback_query: CallbackQuery, state: FSMContext
):
    user_id = callback_query.from_user.id

    if state is not None:
        await state.clear()

    # Получение или создание объектов пользовательских данных
    user_data = await get_or_create_user_data(user_id)

    await callback_query.message.edit_text(
        text=f"{user_data['pic_grade']} : {user_data['pic_size']} ",
        reply_markup=keyboard_pic,
    )

    await callback_query.answer()
    return


async def handle_pic_setting_selection(
    callback_query: CallbackQuery, setting_type: str, new_value: str
):
    """
    Универсальная функция для обработки настроек изображения
    """
    user_id = callback_query.from_user.id
    user_data = await get_or_create_user_data(user_id)

    # Проверяем, не установлено ли уже это значение
    if user_data[setting_type] == new_value:
        await callback_query.answer()
        return

    user_data[setting_type] = new_value
    await save_user_data(user_id)

    await callback_query.message.edit_text(
        text=f"{user_data['pic_grade']} : {user_data['pic_size']} ",
        reply_markup=keyboard_pic,
    )

    await callback_query.answer()


@router.callback_query(F.data == "set_sd")
@owner_only
async def process_callback_set_sd(callback_query: CallbackQuery):
    await handle_pic_setting_selection(callback_query, "pic_grade", "standard")


@router.callback_query(F.data == "set_hd")
@owner_only
async def process_callback_set_hd(callback_query: CallbackQuery):
    await handle_pic_setting_selection(callback_query, "pic_grade", "hd")


@router.callback_query(F.data == "set_1024x1024")
@owner_only
async def process_callback_set_1024x1024(callback_query: CallbackQuery):
    await handle_pic_setting_selection(callback_query, "pic_size", "1024x1024")


@router.callback_query(F.data == "set_1024x1792")
@owner_only
async def process_callback_set_1024x1792(callback_query: CallbackQuery):
    await handle_pic_setting_selection(callback_query, "pic_size", "1024x1792")


@router.callback_query(F.data == "set_1792x1024")
@owner_only
async def process_callback_set_1792x1024(callback_query: CallbackQuery):
    await handle_pic_setting_selection(callback_query, "pic_size", "1792x1024")


@router.callback_query(F.data == "context_work")
@owner_only
async def process_callback_context_work(
    callback_query: CallbackQuery, state: FSMContext
):
    user_id = callback_query.from_user.id

    if state is not None:
        await state.clear()

    # Получение или создание объектов пользовательских данных
    user_data = await get_or_create_user_data(user_id)

    await callback_query.message.edit_text(
        text=f"<i>Сообщений:</i> {user_data['count_messages']} ",
        reply_markup=keyboard_context,
    )

    await callback_query.answer()
    return


@router.callback_query(F.data == "context")
@owner_only
async def process_callback_context(callback_query: CallbackQuery):
    user_id = callback_query.from_user.id

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
    max_length = 4000  # Обновляем до согласованного лимита
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
    bot = get_bot()
    content_kwargs = Text(content)
    await bot.send_message(
        user_id,
        **content_kwargs.as_kwargs(),
        disable_web_page_preview=True,
    )


async def send_menu(user_id):
    bot = get_bot()
    await bot.send_message(
        user_id,
        text=f"Действия с контекстом",
        reply_markup=keyboard_context,
    )


@router.callback_query(F.data == "clear")
@owner_only
async def process_callback_clear(callback_query: CallbackQuery):
    user_id = callback_query.from_user.id

    if callback_query.message.text == "Контекст очищен":
        await callback_query.answer()
        return

    # Получение или создание объектов пользовательских данных
    user_data = await get_or_create_user_data(user_id)

    # Очищаем сообщения
    user_data["messages"] = []
    user_data["count_messages"] = 0

    # Определяем текущий ассистент и сбрасываем его thread_id
    current_assistant = user_data.get("current_assistant", 1)
    reset_success = await reset_thread(user_data, user_id, current_assistant)

    if not reset_success:
        logging.warning(
            f"Не удалось сбросить thread для ассистента {current_assistant}"
        )
        # Даже при ошибке сброса треда продолжаем, так как сообщения уже очищены

    await callback_query.message.edit_text(
        text="Контекст очищен", reply_markup=keyboard_context
    )

    return


@router.callback_query(F.data == "voice_answer_work")
@owner_only
async def process_callback_voice_answer_work(
    callback_query: CallbackQuery, state: FSMContext
):
    user_id = callback_query.from_user.id

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


async def handle_voice_answer_setting(callback_query: CallbackQuery, new_value: bool):
    """
    Универсальная функция для обработки настроек голосового ответа
    """
    user_id = callback_query.from_user.id
    user_data = await get_or_create_user_data(user_id)

    if user_data["voice_answer"] == new_value:
        await callback_query.answer()
        return

    user_data["voice_answer"] = new_value
    await save_user_data(user_id)

    info_voice_answer = "Включен" if user_data["voice_answer"] else "Выключен"

    await callback_query.message.edit_text(
        text=f"<i>Аудио:</i> {info_voice_answer}",
        reply_markup=keyboard_voice,
    )

    await callback_query.answer()


@router.callback_query(F.data == "voice_answer_add")
@owner_only
async def process_callback_voice_answer_add(callback_query: CallbackQuery):
    await handle_voice_answer_setting(callback_query, True)


@router.callback_query(F.data == "voice_answer_del")
@owner_only
async def process_callback_voice_answer_del(callback_query: CallbackQuery):
    await handle_voice_answer_setting(callback_query, False)


@router.callback_query(F.data == "back_menu")
@owner_only
async def process_callback_menu_back(callback_query: CallbackQuery, state: FSMContext):
    user_id = callback_query.from_user.id

    if state is not None:
        await state.clear()

    info_menu = await info_menu_func(user_id)

    await callback_query.message.edit_text(text=f"{info_menu}", reply_markup=keyboard)
    return


@router.callback_query(F.data == "info")
@owner_only
async def process_callback_info(callback_query: CallbackQuery, state: FSMContext):
    user_id = callback_query.from_user.id

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
        f"<i>Время:</i> <b>{get_current_datetime()}</b>\n"
        f"<i>User ID:</i> <b>{user_id}</b>\n"
        f"<i>Модель:</i> <b>{user_data['model_message_info']}</b>\n"
        f"<i>Картинка</i>\n"
        f"<i>Качество:</i> <b>{user_data['pic_grade']}</b>\n"
        f"<i>Размер:</i> <b>{user_data['pic_size']}</b>\n"
        f"<i>Сообщения:</i> <b>{user_data['count_messages']}</b>\n"
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
@owner_only
async def help_handler(message: Message, state: FSMContext):
    user_id = message.from_user.id

    if state is not None:
        await state.clear()

    # Получение или создание объектов пользовательских данных
    await get_or_create_user_data(user_id)

    await message.answer(help_message)
    return


@router.callback_query(F.data == "system_value_work")
@owner_only
async def process_callback_system_value_work(
    callback_query: CallbackQuery, state: FSMContext
):
    user_id = callback_query.from_user.id

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


@router.callback_query(F.data == "change_value")
@owner_only
async def process_callback_change_value(
    callback_query: types.CallbackQuery, state: FSMContext
):
    user_id = callback_query.from_user.id

    await state.set_state(ChangeValueState.waiting_for_new_value)

    await callback_query.message.edit_text(
        text=system_message_text,
        reply_markup=None,
    )

    await callback_query.answer()
    return


@router.callback_query(F.data == "delete_value")
@owner_only
async def process_callback_delete_value(
    callback_query: CallbackQuery, state: FSMContext
):
    user_id = callback_query.from_user.id

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
@owner_only
async def process_new_value(message: types.Message, state: FSMContext):
    user_id = message.from_user.id

    sys_message = ""  # Значение по умолчанию

    if message.voice:
        bot = get_bot()
        sys_message = await process_voice_message(bot, message, user_id)
    elif message.text:
        # Если сообщение содержит текст
        sys_message = message.text
    else:
        # Если нет ни голоса, ни текста, возвращаемся без изменений
        await message.answer("⚠️ Не удалось получить текст сообщения")
        return

    # Ваш метод получения или создания данных пользователя
    user_data = await get_or_create_user_data(user_id)

    user_data["system_message"] = sys_message

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


async def handle_model_selection(callback_query: CallbackQuery, model_config: dict):
    """
    Универсальная функция для обработки выбора модели
    model_config должен содержать: model, model_message_info, model_message_chat, max_out (опционально)
    """
    user_id = callback_query.from_user.id
    user_data = await get_or_create_user_data(user_id)

    # Проверяем, не выбрана ли уже эта модель
    current_model = user_data["model"]
    if current_model == model_config["model"]:
        # Для ассистентов проверяем также текущий номер ассистента
        if current_model == "assistant":
            current_assistant = user_data.get("current_assistant", 1)
            selected_assistant = model_config.get("assistant_number", 1)
            if current_assistant == selected_assistant:
                await callback_query.answer()
                return
        else:
            await callback_query.answer()
            return

    # Обновляем данные пользователя
    user_data["model"] = model_config["model"]
    user_data["model_message_info"] = model_config["model_message_info"]
    user_data["model_message_chat"] = model_config["model_message_chat"]

    # Устанавливаем max_out если указан
    if "max_out" in model_config:
        user_data["max_out"] = model_config["max_out"]

    # Специальная обработка для ассистентов
    if model_config["model"] == "assistant":
        assistant_number = model_config.get("assistant_number", 1)
        user_data["current_assistant"] = assistant_number

        # Загрузка assistant_id из конфигурации, если он не установлен
        assistant_id_key = f"assistant_id_{assistant_number}"
        if not user_data.get(assistant_id_key):
            from config_manager import get_openai_assistant_id

            user_data[assistant_id_key] = get_openai_assistant_id(assistant_number)

    # Сохранение данных
    await save_user_data(user_id)

    # Обновление сообщения
    await callback_query.message.edit_text(
        text=f"<i>Модель:</i> {user_data['model_message_info']} ",
        reply_markup=keyboard_model,
    )

    await callback_query.answer()


@router.callback_query(F.data == "gpt_4_1")
@owner_only
async def process_callback_gpt_4_1(callback_query: CallbackQuery, state: FSMContext):
    model_config = {
        "model": "gpt-4.1-2025-04-14",
        "model_message_info": "4.1",
        "model_message_chat": "4.1:\n\n",
        "max_out": 750000,  # ~1M токенов контекста
    }
    await handle_model_selection(callback_query, model_config)


# Остальные хендлеры
# register_handlers будет вызван в main.py после инициализации bot'а
