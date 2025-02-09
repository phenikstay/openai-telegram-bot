import asyncio
import base64
import configparser
import logging
import re
from pathlib import Path
from typing import Optional

from aiogram import F, Bot, types, flags
from aiogram.client.session import aiohttp
from aiogram.enums import ParseMode
from aiogram.exceptions import TelegramBadRequest
from aiogram.fsm.context import FSMContext
from aiogram.types import Message
from openai import AsyncOpenAI, NotFoundError

from base import get_or_create_user_data, save_user_data
from function import (
    prune_messages,
    process_voice_message,
    text_to_speech,
    download_image,
)

config = configparser.ConfigParser()
config.read(Path(__file__).parent / "config.ini")
OPENAI_ASSISTANT_ID = config.get("OpenAI", "assistant_id", fallback="")
OPENAI_API_KEY = config.get("OpenAI", "api_key")

client_async = AsyncOpenAI(api_key=OPENAI_API_KEY)


def register_handlers(router, bot: Bot, client, OWNER_ID):
    @router.message(F.content_type.in_({"text", "voice", "document"}))
    @flags.throttling_key("spin")
    async def chatgpt_text_handler(message: Message):
        user_id = message.from_user.id
        chat_id = message.chat.id

        if user_id not in OWNER_ID:
            await message.answer("Извините, у вас нет доступа к этому боту.")
            return

        user_data = await get_or_create_user_data(user_id)

        if user_data["model"] == "assistant":
            await handle_assistant_message(message, user_data, bot, OWNER_ID)
            return

        promt = ""

        response = await message.answer("⏳ Подождите, Ваш запрос обрабатывается!")
        last_message_id = response.message_id

        if message.voice:
            promt = await process_voice_message(bot, message, user_id)
        elif message.text:
            promt = message.text

        if user_data["model"] in [
            "gpt-4o-mini",
            "gpt-4o",
            "o1-mini",
            "o1-preview",
            "o3-mini",
        ]:
            user_data["messages"].append({"role": "user", "content": promt})

            pruned_messages = await prune_messages(
                user_data["messages"], max_chars=user_data["max_out"]
            )

            try:
                system_message = {
                    "role": "system",
                    "content": user_data["system_message"],
                }
                if user_data["model"] in ["gpt-4o-mini", "gpt-4o"]:
                    pruned_messages.insert(0, system_message)

                params = {
                    "model": user_data["model"],
                    "messages": pruned_messages,
                }
                if user_data["model"] == "o3-mini":
                    params["reasoning_effort"] = "high"

                chat_completion = await asyncio.to_thread(
                    lambda: client.chat.completions.create(**params)
                )

                await message.bot.send_chat_action(chat_id, action="typing")

                response_message = chat_completion.choices[0].message.content

                user_data["messages"].append(
                    {"role": "assistant", "content": response_message}
                )
                user_data["count_messages"] += 1

                await save_user_data(user_id)

                await message.bot.delete_message(chat_id, last_message_id)

                await send_safe_message(message, response_message, user_data)
                return

            except Exception as e:
                logging.exception(e)
                await message.reply(f"Произошла ошибка: {e}")
                return

        elif user_data["model"] == "dall-e-3":
            try:
                response = await asyncio.to_thread(
                    lambda: client.images.generate(
                        prompt=promt,
                        n=1,
                        size=user_data["pic_size"],
                        model="dall-e-3",
                        quality=user_data["pic_grade"],
                    )
                )
            except Exception as e:
                logging.exception(e)
                await message.reply(f"Произошла ошибка: {e}")
                return

            await message.bot.send_chat_action(chat_id, action="upload_photo")

            user_data["count_messages"] += 1
            await save_user_data(user_id)
            await message.bot.delete_message(chat_id, last_message_id)

            await message.bot.send_photo(
                chat_id,
                response.data[0].url,
                reply_to_message_id=message.message_id,
            )
            return

    @router.message(F.photo)
    @flags.throttling_key("spin")
    async def chatgpt_photo_vision_handler(message: types.Message, state: FSMContext):
        user_id = message.from_user.id
        chat_id = message.chat.id

        if user_id not in OWNER_ID:
            await message.answer("Извините, у вас нет доступа к этому боту.")
            return

        if state is not None:
            await state.clear()

        user_data = await get_or_create_user_data(user_id)

        if user_data["model"] == "assistant":
            await handle_assistant_message(message, user_data, bot, OWNER_ID)
            return

        try:
            temp_message = await message.answer(
                "⏳ Подождите, Ваш запрос обрабатывается!"
            )
            text = message.caption or "Что на картинке?"
            photo = message.photo[-1]
            file_info = await message.bot.get_file(photo.file_id)
            file_url = (
                f"https://api.telegram.org/file/bot{bot.token}/{file_info.file_path}"
            )

            base64_image = await download_and_encode_image(file_url)
            ai_response = await process_image_with_gpt(text, base64_image)

            user_data["messages"].append({"role": "assistant", "content": ai_response})
            user_data["count_messages"] += 1
            await save_user_data(user_id)

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


async def handle_assistant_message(
    message: Message, user_data: dict, bot: Bot, OWNER_ID
):
    user_id = message.from_user.id
    chat_id = message.chat.id

    if user_id not in OWNER_ID:
        await message.answer("Извините, у вас нет доступа к этому боту.")
        return

    MAX_RETRIES = 3
    attempts = 0

    while attempts <= MAX_RETRIES:
        try:
            user_text = message.caption or message.text or ""
            image_file_ids = []
            document_attachments = []

            if message.voice:
                try:
                    user_text = await process_voice_message(bot, message, user_id)
                except Exception as e:
                    logging.error(f"Ошибка обработки голоса: {str(e)}")
                    await message.answer("⚠️ Ошибка распознавания голоса")
                    return

            if message.photo:
                try:
                    photo = message.photo[-1]
                    image_data = await download_image(bot, photo.file_id)

                    file = await client_async.files.create(
                        file=("image.jpg", image_data, "image/jpeg"), purpose="vision"
                    )
                    image_file_ids.append(file.id)

                except Exception as e:
                    logging.error(f"Ошибка загрузки изображения: {str(e)}")
                    await message.answer("⚠️ Не удалось обработать изображение")
                    return

            if message.document and not message.document.mime_type.startswith("image/"):
                try:
                    file_info = await bot.get_file(message.document.file_id)
                    downloaded_file = await bot.download_file(file_info.file_path)
                    file_data = downloaded_file.read()

                    uploaded_file = await client_async.files.create(
                        file=(
                            message.document.file_name,
                            file_data,
                            message.document.mime_type,
                        ),
                        purpose="assistants",
                    )

                    document_attachments.append(
                        {
                            "file_id": uploaded_file.id,
                            "tools": [{"type": "file_search"}],
                        }
                    )

                except Exception as e:
                    logging.error(f"Ошибка загрузки документа: {str(e)}")
                    await message.answer("⚠️ Не удалось обработать документ")
                    return

            thread_id = user_data.get("assistant_thread_id")
            if not thread_id:
                try:
                    new_thread = await client_async.beta.threads.create()
                    thread_id = new_thread.id
                    user_data["assistant_thread_id"] = thread_id
                    await save_user_data(user_id)
                except Exception as e:
                    logging.error(f"Ошибка создания нового треда: {str(e)}")
                    await message.answer(
                        "⚠️ Ошибка создания нового треда. Попробуйте позже."
                    )
                    return

            content = []
            if user_text:
                user_data["messages"].append({"role": "user", "content": user_text})
                content.append({"type": "text", "text": user_text})

            for file_id in image_file_ids:
                content.append(
                    {"type": "image_file", "image_file": {"file_id": file_id}}
                )

            if not content:
                fallback_text = " "
                user_data["messages"].append({"role": "user", "content": fallback_text})
                content.append({"type": "text", "text": fallback_text})

            await client_async.beta.threads.messages.create(
                thread_id=thread_id,
                role="user",
                content=content,
                attachments=document_attachments,
            )

            await bot.send_chat_action(chat_id, action="typing")

            run = await client_async.beta.threads.runs.create_and_poll(
                thread_id=thread_id, assistant_id=OPENAI_ASSISTANT_ID, timeout=60
            )

            if run.status != "completed":
                error_msg = f"Run завершился со статусом: {run.status}"
                if run.last_error:
                    error_msg += f" ({run.last_error.code}: {run.last_error.message})"
                raise Exception(error_msg)

            messages = await client_async.beta.threads.messages.list(
                thread_id=thread_id, limit=1, run_id=run.id
            )

            if not messages.data:
                raise Exception("Пустой ответ от ассистента")

            assistant_message = messages.data[0]
            text_response = []
            response_files = []
            response_images = []

            for content_block in assistant_message.content:
                if content_block.type == "text":
                    cleaned_text = content_block.text.value
                    annotations = content_block.text.annotations

                    for idx, ann in enumerate(annotations):
                        if hasattr(ann, "file_path"):
                            file_id = ann.file_path.file_id
                            response_files.append(file_id)
                            cleaned_text = cleaned_text.replace(
                                ann.text, f" [Файл {idx + 1}]"
                            )

                    text_response.append(cleaned_text.strip())

                elif content_block.type == "image_file":
                    response_images.append(content_block.image_file.file_id)

            if text_response:
                full_text = "\n".join(text_response)
                user_data["messages"].append(
                    {"role": "assistant", "content": full_text}
                )
                user_data["count_messages"] += 1
                await save_user_data(user_id)

                await send_safe_message(message, full_text, user_data)

            for file_id in response_files:
                try:
                    file_content = await client_async.files.content(file_id)
                    file_data = file_content.read()
                    file_info = await client_async.files.retrieve(file_id)

                    await bot.send_document(
                        chat_id=chat_id,
                        document=types.BufferedInputFile(
                            file_data, filename=file_info.filename
                        ),
                        reply_to_message_id=message.message_id,
                    )
                except Exception as e:
                    logging.error(f"Ошибка отправки файла: {str(e)}")

            for file_id in response_images:
                try:
                    file_content = await client_async.files.content(file_id)
                    image_data = file_content.read()
                    await bot.send_photo(
                        chat_id=chat_id,
                        photo=types.BufferedInputFile(
                            image_data, filename=f"response_image_{file_id}.png"
                        ),
                        reply_to_message_id=message.message_id,
                    )
                except Exception as e:
                    logging.error(f"Ошибка отправки изображения: {str(e)}")

            break

        except NotFoundError:
            logging.warning("Тред не найден, создаём новый тред и повторяем попытку.")
            user_data["assistant_thread_id"] = None
            await save_user_data(user_id)
            attempts += 1
            if attempts > MAX_RETRIES:
                logging.error("Максимальное количество попыток достигнуто.")
                await message.answer(
                    "⚠️ Не удалось создать новый тред. Попробуйте позже."
                )
                break

        except Exception as e:
            if "Can't add messages to thread" in str(e):
                logging.warning(
                    "Невозможно добавить сообщение в тред. Создаём новый тред."
                )
                user_data["assistant_thread_id"] = None
                await save_user_data(user_id)
                attempts += 1
                if attempts > MAX_RETRIES:
                    logging.error("Максимальное количество попыток достигнуто.")
                    await message.answer(
                        "⚠️ Не удалось добавить сообщение в тред. Попробуйте позже."
                    )
                    break
            else:
                logging.exception("Assistant error:")
                await message.answer(f"⚠️ Ошибка: {str(e)}")
                break


async def safe_delete(message: Optional[Message]) -> None:
    """Безопасное удаление сообщения с обработкой ошибок"""
    if message:
        try:
            await message.delete()
        except TelegramBadRequest as e:
            if "message to delete not found" not in str(e):
                logging.warning(f"Ошибка при удалении сообщения: {str(e)}")
        except Exception as e:
            logging.error(f"Неизвестная ошибка при удалении: {str(e)}")


async def send_safe_message(message: Message, text: str, user_data: dict) -> None:
    """Отправка сообщений с удалением маркеров заголовков, конструкций вида 【...】
    и сохранением кода."""
    try:
        code_blocks = []
        parts = re.split(r"(```[\s\S]*?```)", text)

        processed_parts = []
        for i, part in enumerate(parts):
            if i % 2 == 1:
                code_blocks.append(part)
                processed_parts.append(f"%%CODE_BLOCK_{len(code_blocks) - 1}%%")
            else:
                cleaned_part = re.sub(r"#{2,4}\s+", "", part)
                cleaned_part = re.sub(r"【[^】]*】", "", cleaned_part)
                processed_parts.append(cleaned_part)

        formatted_text = "".join(processed_parts)

        chunks = []
        current_chunk = []
        current_length = 0

        for line in formatted_text.split("\n"):
            line_length = len(line) + 1
            if current_length + line_length > 4096:
                chunks.append("\n".join(current_chunk))
                current_chunk = [line]
                current_length = line_length
            else:
                current_chunk.append(line)
                current_length += line_length

        if current_chunk:
            chunks.append("\n".join(current_chunk))

        final_chunks = []
        for chunk in chunks:
            restored_chunk = chunk
            for idx, code in enumerate(code_blocks):
                restored_chunk = restored_chunk.replace(f"%%CODE_BLOCK_{idx}%%", code)
            final_chunks.append(restored_chunk)

        for i, chunk in enumerate(final_chunks):
            try:
                if i == 0:
                    await message.reply(
                        f"*{user_data['model_message_chat']}*{chunk}",
                        parse_mode=ParseMode.MARKDOWN,
                    )
                else:
                    await message.answer(chunk, parse_mode=ParseMode.MARKDOWN)
            except Exception as e:
                safe_chunk = chunk.replace("`", "'")
                await message.answer(safe_chunk)

        if user_data.get("voice_answer"):
            await text_to_speech(message.chat.id, text)

    except Exception as e:
        logging.error(f"Ошибка: {str(e)}")
        await message.answer(text[:4096])
