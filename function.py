import asyncio
import logging
from pathlib import Path

import aiohttp
from aiogram import Bot, types
from aiogram.types import FSInputFile
from pydub import AudioSegment

from base import get_or_create_user_data
from bot_manager import get_bot
from openai_manager import get_async_openai_client


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

    # Идём с конца к началу
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

    # Возвращаем в прямом порядке
    return list(reversed(pruned_messages))


async def process_voice_message(bot: Bot, message: types.Message, user_id: int):
    """
    Скачивает голосовое сообщение, конвертирует его в mp3 и отправляет на распознавание через OpenAI.
    Возвращает текст транскрипции.
    """
    ogg_path = None
    mp3_path = None

    try:
        file_id = message.voice.file_id
        file_info = await bot.get_file(file_id)

        # Создаем директорию 'voice', если она не существует
        voice_dir = Path(__file__).parent / "voice"
        try:
            voice_dir.mkdir(exist_ok=True)
        except OSError as e:
            logging.error(f"Не удалось создать директорию voice: {e}")
            raise RuntimeError(f"Ошибка создания директории для голосовых файлов: {e}")

        ogg_path = voice_dir / f"voice_{user_id}.ogg"
        mp3_path = voice_dir / f"voice_{user_id}.mp3"

        # Скачиваем файл в формате OGG
        try:
            await bot.download_file(file_info.file_path, ogg_path)
        except Exception as e:
            logging.error(f"Ошибка скачивания голосового файла: {e}")
            raise RuntimeError(f"Не удалось скачать голосовое сообщение: {e}")

        # Конвертируем из OGG в MP3 (задаём опционально битрейт)
        try:
            await asyncio.to_thread(
                lambda: AudioSegment.from_ogg(ogg_path).export(
                    mp3_path, format="mp3", bitrate="192k"
                )
            )
        except Exception as e:
            logging.error(f"Ошибка конвертации аудио: {e}")
            raise RuntimeError(f"Не удалось конвертировать голосовое сообщение: {e}")

        # Проверяем, что mp3-файл создан и имеет ненулевой размер
        if not mp3_path.exists() or mp3_path.stat().st_size == 0:
            raise RuntimeError(
                "Конвертация файла завершилась неудачно, mp3-файл не создан."
            )

        # Используем асинхронный клиент для Whisper API
        client_async = get_async_openai_client()

        # Читаем файл асинхронно
        try:
            audio_data = await asyncio.to_thread(lambda: mp3_path.read_bytes())
        except Exception as e:
            logging.error(f"Ошибка чтения mp3 файла: {e}")
            raise RuntimeError(f"Не удалось прочитать конвертированный файл: {e}")

        # Создаем file-like объект для OpenAI API
        from io import BytesIO

        audio_file = BytesIO(audio_data)
        audio_file.name = mp3_path.name

        try:
            transcription = await client_async.audio.transcriptions.create(
                model="whisper-1", file=audio_file
            )
        except Exception as e:
            logging.error(f"Ошибка распознавания речи через OpenAI: {e}")
            raise RuntimeError(f"Не удалось распознать речь: {e}")

        return transcription.text

    except Exception as e:
        # Очищаем временные файлы в случае ошибки
        await _cleanup_voice_files(ogg_path, mp3_path)
        raise
    finally:
        # Очищаем временные файлы после успешной обработки
        await _cleanup_voice_files(ogg_path, mp3_path)


async def _cleanup_voice_files(*file_paths):
    """
    Асинхронно удаляет временные голосовые файлы.
    """
    for file_path in file_paths:
        if file_path and file_path.exists():
            try:
                await asyncio.to_thread(file_path.unlink)
                logging.debug(f"Удален временный файл: {file_path}")
            except Exception as e:
                logging.warning(f"Не удалось удалить временный файл {file_path}: {e}")


def chunk_text(text: str, chunk_size: int = 500) -> list[str]:
    """
    Делит строку `text` на список кусочков по длине не более `chunk_size`.
    """
    return [text[i : i + chunk_size] for i in range(0, len(text), chunk_size)]


async def text_to_speech(unic_id: int, text_message: str):
    """
    Генерирует голосовые сообщения, разделяя текст на части по 1000 символов.
    Для каждой части вызывается TTS через OpenAI API.
    """
    try:
        bot = get_bot()  # Получаем bot из менеджера
        client_async = get_async_openai_client()
    except Exception as e:
        logging.error(f"Ошибка инициализации для TTS: {e}")
        return []

    parts = chunk_text(text_message, 1000)
    results = []
    failed_parts = []

    # Проверяем и создаем директорию voice
    voice_dir = Path(__file__).parent / "voice"
    try:
        voice_dir.mkdir(exist_ok=True)
    except OSError as e:
        logging.error(f"Не удалось создать директорию voice для TTS: {e}")
        try:
            await bot.send_message(
                unic_id,
                "⚠️ Ошибка создания директории для аудиофайлов. Голосовой ответ недоступен.",
            )
        except Exception:
            pass
        return []

    for index, chunk in enumerate(parts, start=1):
        speech_file_path = None
        try:
            speech_file_path = voice_dir / f"speech_{unic_id}_{index}.mp3"

            # Используем асинхронный клиент для TTS API
            try:
                response_voice = await client_async.audio.speech.create(
                    model="tts-1",
                    voice="nova",
                    input=chunk,
                )
            except Exception as e:
                logging.error(f"Ошибка вызова OpenAI TTS API для части {index}: {e}")
                failed_parts.append(index)
                continue

            # Записываем аудио файл асинхронно
            try:
                await asyncio.to_thread(
                    lambda: speech_file_path.write_bytes(response_voice.content)
                )
            except Exception as e:
                logging.error(f"Ошибка записи аудиофайла части {index}: {e}")
                failed_parts.append(index)
                continue

            # Проверяем, что файл создан
            if not speech_file_path.exists() or speech_file_path.stat().st_size == 0:
                logging.error(f"Файл части {index} не создан или пустой")
                failed_parts.append(index)
                continue

            # Отправляем пользователю аудиофайл
            try:
                audio = FSInputFile(speech_file_path)
                msg = await bot.send_audio(
                    unic_id,
                    audio,
                    title=f"Аудио вариант ответа (часть {index})",
                )
                results.append(msg)
            except Exception as e:
                logging.error(f"Ошибка отправки аудиофайла части {index}: {e}")
                failed_parts.append(index)

        except Exception as e:
            logging.error(f"Общая ошибка при обработке части {index}: {e}")
            failed_parts.append(index)
        finally:
            # Удаляем временный файл
            if speech_file_path and speech_file_path.exists():
                try:
                    await asyncio.to_thread(speech_file_path.unlink)
                    return None
                except Exception as e:
                    logging.warning(
                        f"Не удалось удалить временный TTS файл {speech_file_path}: {e}"
                    )
                    return None

    # Уведомляем о неудачных частях, если они есть
    if failed_parts and len(failed_parts) < len(parts):
        try:
            await bot.send_message(
                unic_id,
                f"⚠️ Не удалось озвучить части: {', '.join(map(str, failed_parts))}",
            )
        except Exception:
            pass

    return results


async def download_image(bot_instance, file_id: str) -> bytes:
    """Скачивает файл из Telegram и возвращает bytes"""
    try:
        try:
            file = await bot_instance.get_file(file_id)
        except Exception as e:
            logging.error(f"Ошибка получения информации о файле {file_id}: {e}")
            raise ValueError(f"Не удалось получить информацию о файле: {e}")

        if not file.file_path:
            logging.error(f"Пустой file_path для файла {file_id}")
            raise ValueError("Файл недоступен для скачивания")

        # Формируем URL для скачивания
        url = f"https://api.telegram.org/file/bot{bot_instance.token}/{file.file_path}"

        # Добавляем таймауты для предотвращения зависания
        timeout = aiohttp.ClientTimeout(total=30, connect=10)

        # Скачиваем содержимое
        try:
            async with aiohttp.ClientSession(timeout=timeout) as session:
                async with session.get(url) as response:
                    if response.status != 200:
                        logging.error(
                            f"HTTP ошибка при скачивании файла: {response.status}"
                        )
                        raise ValueError(
                            f"Ошибка HTTP {response.status} при скачивании файла"
                        )

                    content_length = response.headers.get("content-length")
                    if (
                        content_length and int(content_length) > 20 * 1024 * 1024
                    ):  # 20MB лимит
                        logging.error(f"Файл слишком большой: {content_length} байт")
                        raise ValueError("Файл слишком большой для обработки")

                    data = await response.read()

                    if len(data) == 0:
                        logging.error("Скачан пустой файл")
                        raise ValueError("Скачанный файл пуст")

                    return data

        except asyncio.TimeoutError:
            logging.error(f"Таймаут при скачивании файла {file_id}")
            raise ValueError("Превышено время ожидания при скачивании файла")
        except aiohttp.ClientError as e:
            logging.error(f"Ошибка сети при скачивании файла {file_id}: {e}")
            raise ValueError(f"Ошибка сети: {e}")

    except ValueError:
        # Пробрасываем наши ValueError без изменений
        raise
    except Exception as e:
        logging.error(f"Неожиданная ошибка при скачивании файла {file_id}: {e}")
        raise ValueError(f"Неожиданная ошибка при скачивании файла: {e}")
