from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup

BUTTONS_ALL = [
    ("GPT-4o mini", "gpt_4o_mini"),
    ("GPT-4o", "gpt_4_o"),
    ("DALL·E 3", "dall_e_3"),
    ("Параметры картинки", "pic_setup"),
    ("Показать контекст диалога", "context"),
    ("Очистить контекст", "clear"),
    ("Включить аудио ответ", "voice_answer_add"),
    ("Выключить аудио ответ", "voice_answer_del"),
    ("Назначить системную роль", "change_value"),
    ("Убрать системную роль", "delete_value"),
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
