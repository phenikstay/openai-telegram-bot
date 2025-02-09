from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup

BUTTONS_ALL = [
    ("Выбор модели/режима", "model_choice"),
    ("Настройки изображения", "pic_setup"),
    ("Действия с контекстом", "context_work"),
    ("Голосовые ответы", "voice_answer_work"),
    ("Системная роль", "system_value_work"),
    ("Информация", "info"),
]

inline_buttons = [
    InlineKeyboardButton(text=text, callback_data=data) for text, data in BUTTONS_ALL
]

keyboard = InlineKeyboardMarkup(inline_keyboard=[[button] for button in inline_buttons])

pic_buttons = [
    ("SD", "set_sd"),
    ("HD", "set_hd"),
    ("1024x1024", "set_1024x1024"),
    ("1024x1792", "set_1024x1792"),
    ("1792x1024", "set_1792x1024"),
    ("Назад в меню", "back_menu"),
]

inline_buttons_pic = [
    InlineKeyboardButton(text=text, callback_data=data) for text, data in pic_buttons
]

keyboard_pic = InlineKeyboardMarkup(
    inline_keyboard=[[button] for button in inline_buttons_pic]
)

BUTTONS_MODEL = [
    ("4o mini", "gpt_4o_mini"),
    ("4o", "gpt_4_o"),
    ("o1 mini", "gpt_o1_mini"),
    ("o1 preview", "gpt_o1_preview"),
    ("o3 mini", "o3-mini"),
    ("DALL·E 3", "dall_e_3"),
    ("ASSISTANT", "assistant"),
    ("Назад в меню", "back_menu"),
]

inline_buttons_model = [
    InlineKeyboardButton(text=text, callback_data=data) for text, data in BUTTONS_MODEL
]

keyboard_model = InlineKeyboardMarkup(
    inline_keyboard=[[button] for button in inline_buttons_model]
)

BUTTONS_CONTEXT = [
    ("Показать контекст", "context"),
    ("Очистить контекст", "clear"),
    ("Назад в меню", "back_menu"),
]

inline_buttons_context = [
    InlineKeyboardButton(text=text, callback_data=data)
    for text, data in BUTTONS_CONTEXT
]

keyboard_context = InlineKeyboardMarkup(
    inline_keyboard=[[button] for button in inline_buttons_context]
)

BUTTONS_VOICE = [
    ("Включить аудио ответ", "voice_answer_add"),
    ("Выключить аудио ответ", "voice_answer_del"),
    ("Назад в меню", "back_menu"),
]

inline_buttons_voice = [
    InlineKeyboardButton(text=text, callback_data=data) for text, data in BUTTONS_VOICE
]

keyboard_voice = InlineKeyboardMarkup(
    inline_keyboard=[[button] for button in inline_buttons_voice]
)

BUTTONS_VALUE_WORK = [
    ("Назначить системную роль", "change_value"),
    ("Убрать системную роль", "delete_value"),
    ("Назад в меню", "back_menu"),
]

inline_buttons_value_work = [
    InlineKeyboardButton(text=text, callback_data=data)
    for text, data in BUTTONS_VALUE_WORK
]

keyboard_value_work = InlineKeyboardMarkup(
    inline_keyboard=[[button] for button in inline_buttons_value_work]
)
