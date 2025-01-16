import asyncio
import base64
import logging

from aiogram import F, Bot, types
from aiogram.client.session import aiohttp
from aiogram.enums import ParseMode
from aiogram.fsm.context import FSMContext
from aiogram.types import Message
from aiogram.utils.formatting import Text, Bold

from base import get_or_create_user_data, save_user_data
from function import (
    prune_messages,
    process_voice_message,
    text_to_speech,
)


def register_handlers(router, bot: Bot, client, OWNER_ID):
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

        if (
            user_data["model"] == "gpt-4o-mini"
            or user_data["model"] == "gpt-4o"
            or user_data["model"] == "o1-mini"
            or user_data["model"] == "o1-preview"
        ):

            # Добавляем сообщение пользователя в историю чата
            user_data["messages"].append({"role": "user", "content": promt})

            # Применяем функцию обрезки
            pruned_messages = await prune_messages(
                user_data["messages"], max_chars=user_data["max_out"]
            )

            try:
                # Добавляем роль system временно, без сохранения в контексте
                system_message = {
                    "role": "system",
                    "content": user_data["system_message"],
                }

                if (
                    user_data["model"] == "gpt-4o-mini"
                    or user_data["model"] == "gpt-4o"
                ):
                    pruned_messages.insert(0, system_message)

                # Use asyncio.to_thread for OpenAI API call
                chat_completion = await asyncio.to_thread(
                    lambda: client.chat.completions.create(
                        model=user_data["model"], messages=pruned_messages
                    )
                )

                # Бот печатает...
                await message.bot.send_chat_action(chat_id, action="typing")

                # Получаем ответ модели
                response_message = chat_completion.choices[0].message.content

                # Добавляем ответ модели в историю чата
                user_data["messages"].append(
                    {"role": "assistant", "content": response_message}
                )

                # Счетчик сообщений пользователя
                user_data["count_messages"] += 1

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
                        if (
                            len(chunk) + len(line) + 1 > 4096
                        ):  # +1 для символа новой строки
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

                # Отправляем ответ модели пользователю
                try:
                    if "```" in response_message:
                        if len(response_message) > 4096:
                            await send_message_md_long(
                                user_data["model_message_chat"], response_message
                            )
                            if user_data["voice_answer"]:
                                await text_to_speech(message.chat.id, response_message)
                            return

                        await send_message_md(
                            user_data["model_message_chat"], response_message
                        )
                        if user_data["voice_answer"]:
                            await text_to_speech(message.chat.id, response_message)
                        return

                    else:
                        if len(response_message) > 4096:
                            await send_message_kwargs_long(
                                user_data["model_message_chat"], response_message
                            )
                            if user_data["voice_answer"]:
                                await text_to_speech(message.chat.id, response_message)
                            return

                        await send_message_kwargs(
                            user_data["model_message_chat"], response_message
                        )
                        if user_data["voice_answer"]:
                            await text_to_speech(message.chat.id, response_message)
                        return

                except Exception as e:
                    logging.exception(e)
                    if len(response_message) > 4096:
                        await send_message_kwargs_long(
                            user_data["model_message_chat"], response_message
                        )
                        if user_data["voice_answer"]:
                            await text_to_speech(message.chat.id, response_message)
                        return

                    await send_message_kwargs(
                        user_data["model_message_chat"], response_message
                    )
                    if user_data["voice_answer"]:
                        await text_to_speech(message.chat.id, response_message)
                    return

            except Exception as e:
                logging.exception(e)
                await message.reply(f"Произошла ошибка: {e}")
                return

        elif user_data["model"] == "dall-e-3":

            try:
                # Use asyncio.to_thread for OpenAI API call
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

            # Бот печатает...
            await message.bot.send_chat_action(chat_id, action="upload_photo")

            # Счетчик сообщений пользователя
            user_data["count_messages"] += 1

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

            # Добавляем ответ модели в историю чата
            user_data["messages"].append({"role": "assistant", "content": ai_response})

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
        user_data["count_messages"] += 1
        await save_user_data(user_id)
