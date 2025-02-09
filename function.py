import asyncio
import configparser
import logging
from pathlib import Path

import aiohttp
from aiogram import Bot, types
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
from openai import OpenAI
from pydub import AudioSegment

from base import get_or_create_user_data

config = configparser.ConfigParser()
config.read(Path(__file__).parent / "config.ini")

TOKEN = config.get("Telegram", "token")
bot = Bot(token=TOKEN, default=DefaultBotProperties(parse_mode=ParseMode.HTML))

openai_api_key = config.get("OpenAI", "api_key")
client = OpenAI(api_key=openai_api_key)


async def info_menu_func(user_id):
    user_data = await get_or_create_user_data(user_id)

    info_voice_answer = "Включен" if user_data["voice_answer"] else "Выключен"
    info_system_message = "Задана" if user_data["system_message"] else "Отсутствует"

    info_menu = (
        f"<i>Сообщений:</i> <b>{user_data['count_messages']}</b>\n"
        f"<i>Модель:</i> <b>{user_data['model_message_info']}</b>\n"
        f"<i>Аудио:</i> <b>{info_voice_answer}</b>\n"
        f"<i>Роль:</i> <b>{info_system_message}</b>\n"
        f"<i>Картинка</i>\n"
        f"<i>Качество:</i> <b>{user_data['pic_grade']}</b>\n"
        f"<i>Размер:</i> <b>{user_data['pic_size']}</b>"
    )
    return info_menu


async def prune_messages(messages, max_chars):
    """
    Обрезает историю сообщений по символам, начиная с конца.
    """
    pruned_messages = []
    total_chars = 0

    for message in reversed(messages):
        content_length = len(message["content"])
        remaining_chars = max_chars - total_chars
        if remaining_chars <= 0:
            break

        if content_length > remaining_chars:
            pruned_content = message["content"][:remaining_chars]
            pruned_messages.append({"role": message["role"], "content": pruned_content})
            break

        pruned_messages.append(message)
        total_chars += content_length

    return list(reversed(pruned_messages))


async def process_voice_message(bot: Bot, message: types.Message, user_id: int):
    """
    Скачивает голосовое сообщение, конвертирует его в mp3 и отправляет на распознавание через OpenAI.
    Возвращает текст транскрипции.
    """
    file_id = message.voice.file_id
    file_info = await bot.get_file(file_id)

    voice_dir = Path(__file__).parent / "voice"
    voice_dir.mkdir(exist_ok=True)

    ogg_path = voice_dir / f"voice_{user_id}.ogg"
    mp3_path = voice_dir / f"voice_{user_id}.mp3"

    await bot.download_file(file_info.file_path, ogg_path)

    await asyncio.to_thread(
        lambda: AudioSegment.from_ogg(ogg_path).export(
            mp3_path, format="mp3", bitrate="192k"
        )
    )

    if not mp3_path.exists() or mp3_path.stat().st_size == 0:
        raise RuntimeError(
            "Конвертация файла завершилась неудачно, mp3-файл не создан."
        )

    def call_whisper():
        with open(mp3_path, "rb") as audio_file:
            return client.audio.transcriptions.create(
                model="whisper-1", file=audio_file
            )

    transcription = await asyncio.to_thread(call_whisper)

    return transcription.text


def chunk_text(text: str, chunk_size: int = 500) -> list[str]:
    """
    Делит строку `text` на список кусочков по длине не более `chunk_size`.
    """
    return [text[i : i + chunk_size] for i in range(0, len(text), chunk_size)]


def write_streaming_response(streaming_resp, file_path: Path, chunk_size: int = 1024):
    """
    Синхронная функция, которая записывает потоковый ответ в файл.
    Ожидается, что streaming_resp имеет метод iter_bytes(), возвращающий данные порциями.
    """
    with open(file_path, "wb") as f:
        for chunk in streaming_resp.iter_bytes(chunk_size=chunk_size):
            f.write(chunk)


async def text_to_speech(unic_id: int, text_message: str):
    """
    Генерирует голосовые сообщения, разделяя текст на части по 500 символов.
    Для каждой части вызывается TTS через OpenAI API.
    """
    from aiogram.types import FSInputFile

    parts = chunk_text(text_message, 500)
    results = []

    for index, chunk in enumerate(parts, start=1):
        try:
            speech_file_path = (
                Path(__file__).parent / f"voice/speech_{unic_id}_{index}.mp3"
            )

            response_voice = await asyncio.to_thread(
                lambda: client.audio.speech.create(
                    model="tts-1",
                    voice="nova",
                    input=chunk,
                )
            )

            streaming_response = response_voice

            await asyncio.to_thread(
                lambda: write_streaming_response(
                    streaming_response, speech_file_path, 1024
                )
            )

            audio = FSInputFile(speech_file_path)
            msg = await bot.send_audio(
                unic_id,
                audio,
                title=f"Аудио вариант ответа (часть {index})",
            )
            results.append(msg)

        except Exception as e:
            await bot.send_message(
                unic_id,
                f"Ошибка при озвучке части {index}: {e}",
            )
    return results


async def download_image(bot: Bot, file_id: str) -> bytes:
    """Скачивает файл из Telegram и возвращает bytes"""
    try:
        file = await bot.get_file(file_id)

        url = f"https://api.telegram.org/file/bot{bot.token}/{file.file_path}"

        async with aiohttp.ClientSession() as session:
            async with session.get(url) as response:
                response.raise_for_status()
                return await response.read()

    except aiohttp.ClientError as e:
        logging.error(f"Ошибка сети: {str(e)}")
        raise ValueError("Не удалось загрузить изображение из Telegram")
    except Exception as e:
        logging.error(f"Общая ошибка: {str(e)}")
        raise ValueError("Ошибка при загрузке файла")
