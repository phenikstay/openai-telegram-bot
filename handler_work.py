import base64
import logging
import re

from aiogram import F, Bot, types, flags
from aiogram.client.session import aiohttp
from aiogram.enums import ParseMode
from aiogram.exceptions import TelegramBadRequest
from aiogram.fsm.context import FSMContext
from aiogram.types import Message
from openai import NotFoundError

from base import get_or_create_user_data, save_user_data
from config_manager import get_openai_assistant_id
from decorators import owner_only
from function import (
    prune_messages,
    process_voice_message,
    text_to_speech,
    download_image,
)
from openai_manager import get_async_openai_client


def register_handlers(router, bot: Bot):
    @router.message(F.content_type.in_({"text", "voice", "document"}))
    @flags.throttling_key("spin")
    @owner_only
    async def chatgpt_text_handler(message: Message):
        user_id = message.from_user.id
        chat_id = message.chat.id

        # Получение или создание объектов пользовательских данных
        user_data = await get_or_create_user_data(user_id)

        # ---------- ПРОВЕРКА РЕЖИМА АССИСТЕНТА ----------
        if user_data["model"] == "assistant":
            # Если включён режим ассистента (Threads)
            await handle_assistant_message(message, user_data, bot)
            return
        # -------------------------------------

        prompt = ""

        # Временное сообщение
        response = await message.answer("⏳ Подождите, Ваш запрос обрабатывается!")
        last_message_id = response.message_id

        if message.voice:
            prompt = await process_voice_message(bot, message, user_id)
        elif message.text:
            prompt = message.text

        if user_data["model"] in [
            "gpt-4o-mini",
            "gpt-4o",
            "gpt-4.1-2025-04-14",
            "o1-mini",
            "o1-preview",
            "o3-mini",
            "o1-pro",
            "gpt-4o-search-preview",
        ]:
            # Добавляем сообщение пользователя в историю чата
            user_data["messages"].append({"role": "user", "content": prompt})

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
                if user_data["model"] in [
                    "gpt-4o-mini",
                    "gpt-4o",
                    "gpt-4.1-2025-04-14",
                ]:
                    pruned_messages.insert(0, system_message)

                # Формируем параметры для запроса
                params = {
                    "model": user_data["model"],
                    "messages": pruned_messages,
                }
                if user_data["model"] == "o3-mini":
                    params["reasoning_effort"] = "high"

                if user_data["model"] == "gpt-4o-search-preview":
                    params["web_search_options"] = {
                        "search_context_size": "medium",
                    }

                # Используем асинхронный клиент для вызова API OpenAI
                client_async = get_async_openai_client()
                chat_completion = await client_async.chat.completions.create(**params)

                # Бот печатает...
                await message.bot.send_chat_action(chat_id, action="typing")

                # Получаем ответ модели
                response_message = chat_completion.choices[0].message.content

                # Добавляем ответ модели в историю чата
                user_data["messages"].append(
                    {"role": "assistant", "content": response_message}
                )
                user_data["count_messages"] += 1

                # Сохраняем обновленные данные
                await save_user_data(user_id)

                # Удаляем временное сообщение
                await message.bot.delete_message(chat_id, last_message_id)

                # Отправляем ответ через send_safe_message
                await send_safe_message(message, response_message, user_data)
                return

            except Exception as e:
                logging.exception(e)
                await message.reply(
                    f"Произошла ошибка: {e}", disable_web_page_preview=True
                )
                return

        elif user_data["model"] == "dall-e-3":
            try:
                # Используем асинхронный клиент для вызова API OpenAI
                client_async = get_async_openai_client()
                response = await client_async.images.generate(
                    prompt=prompt,
                    n=1,
                    size=user_data["pic_size"],
                    model="dall-e-3",
                    quality=user_data["pic_grade"],
                )
            except Exception as e:
                logging.exception(e)
                await message.reply(
                    f"Произошла ошибка: {e}", disable_web_page_preview=True
                )
                return

            # Бот печатает...
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
    @owner_only
    async def chatgpt_photo_vision_handler(message: types.Message, state: FSMContext):
        user_id = message.from_user.id
        chat_id = message.chat.id

        if state is not None:
            await state.clear()

        user_data = await get_or_create_user_data(user_id)

        if user_data["model"] == "assistant":
            # Получаем bot из параметра функции register_handlers
            await handle_assistant_message(message, user_data, bot)
            return

        try:
            temp_message = await message.answer(
                "⏳ Подождите, Ваш запрос обрабатывается!"
            )
            text = message.caption or "Что на картинке?"
            photo = message.photo[-1]
            file_info = await message.bot.get_file(photo.file_id)
            file_url = f"https://api.telegram.org/file/bot{message.bot.token}/{file_info.file_path}"

            base64_image = await download_and_encode_image(file_url)
            ai_response = await process_image_with_gpt(text, base64_image)

            user_data["messages"].append({"role": "assistant", "content": ai_response})
            user_data["count_messages"] += 1
            await save_user_data(user_id)

            await message.bot.delete_message(chat_id, temp_message.message_id)
            await send_safe_message(message, ai_response, user_data)

        except Exception as e:
            logging.exception(e)
            await message.reply(f"Произошла ошибка: {e}", disable_web_page_preview=True)

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
        client_async = get_async_openai_client()
        chat_completion = await client_async.chat.completions.create(
            model="gpt-4o", messages=messages, max_tokens=4000
        )
        return chat_completion.choices[0].message.content


async def handle_assistant_message(message: Message, user_data: dict, bot: Bot):
    user_id = message.from_user.id
    chat_id = message.chat.id

    MAX_RETRIES = 3
    attempts = 0

    while attempts <= MAX_RETRIES:
        try:
            # Обработка входящих данных
            user_text = message.caption or message.text or ""
            image_file_ids = []
            document_attachments = []

            # Получаем номер текущего ассистента сразу, чтобы он был доступен всем обработчикам
            current_assistant = user_data.get("current_assistant", 1)

            # Обработка голосовых сообщений
            if message.voice:
                try:
                    user_text = await process_voice_message(bot, message, user_id)
                except Exception as e:
                    logging.error(f"Ошибка обработки голоса: {str(e)}")
                    await message.answer("⚠️ Ошибка распознавания голоса")
                    return

            # Обработка изображений
            if message.photo:
                try:
                    photo = message.photo[-1]
                    image_data = await download_image(bot, photo.file_id)

                    # Загружаем изображение для vision - purpose="vision"
                    client_async = get_async_openai_client()
                    file = await client_async.files.create(
                        file=("image.jpg", image_data, "image/jpeg"), purpose="vision"
                    )
                    image_file_ids.append(file.id)

                except Exception as e:
                    logging.error(f"Ошибка загрузки изображения из фото: {str(e)}")
                    await message.answer("⚠️ Не удалось обработать изображение")
                    return

            # Обработка документов-изображений
            if message.document and message.document.mime_type.startswith("image/"):
                try:
                    file_info = await bot.get_file(message.document.file_id)
                    downloaded_file = await bot.download_file(file_info.file_path)
                    file_data = downloaded_file.read()

                    # Определяем mime-тип для правильного создания файла
                    image_mime = message.document.mime_type
                    extension = image_mime.split("/")[1]

                    # Загружаем изображение-документ для vision - purpose="vision"
                    client_async = get_async_openai_client()
                    file = await client_async.files.create(
                        file=(f"image.{extension}", file_data, image_mime),
                        purpose="vision",
                    )
                    image_file_ids.append(file.id)

                except Exception as e:
                    logging.error(f"Ошибка загрузки изображения из документа: {str(e)}")
                    await message.answer("⚠️ Не удалось обработать изображение-документ")
                    return

            # Обработка документов (не изображений)
            if message.document and not message.document.mime_type.startswith("image/"):
                try:
                    file_info = await bot.get_file(message.document.file_id)
                    downloaded_file = await bot.download_file(file_info.file_path)
                    file_data = downloaded_file.read()

                    # Загружаем файл с purpose="assistants", что делает его доступным для всех тредов
                    client_async = get_async_openai_client()
                    uploaded_file = await client_async.files.create(
                        file=(
                            message.document.file_name,
                            file_data,
                            message.document.mime_type,
                        ),
                        purpose="assistants",
                    )

                    # Файлы с purpose="assistants" автоматически становятся доступными в тредах
                    logging.info(
                        f"Файл {uploaded_file.id} загружен для использования в тредах"
                    )

                    # Добавляем в attachments для текущего сообщения с указанием tools
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

            # Выбор thread_id в зависимости от текущего ассистента
            thread_id_key = get_thread_id_key(current_assistant)
            thread_id = user_data.get(thread_id_key)

            if not thread_id:
                try:
                    thread_id = await create_new_thread(
                        user_data, user_id, current_assistant
                    )
                    if not thread_id:
                        await message.answer(
                            "⚠️ Ошибка создания нового треда. Попробуйте позже."
                        )
                        return
                except Exception as e:
                    logging.error(f"Непредвиденная ошибка при создании треда: {str(e)}")
                    await message.answer(
                        "⚠️ Ошибка создания нового треда. Попробуйте позже."
                    )
                    return

            # Формирование контента сообщения
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

            client_async = get_async_openai_client()
            await client_async.beta.threads.messages.create(
                thread_id=thread_id,
                role="user",
                content=content,
                attachments=document_attachments,
            )

            logging.info(
                f"Сообщение создано в thread {thread_id} с {len(image_file_ids)} изображениями и {len(document_attachments)} документами"
            )

            await bot.send_chat_action(chat_id, action="typing")

            assistant_id = get_assistant_id(user_data, current_assistant)
            logging.info(f"Запуск ассистента {assistant_id} для пользователя {user_id}")

            client_async = get_async_openai_client()
            run = await client_async.beta.threads.runs.create_and_poll(
                thread_id=thread_id, assistant_id=assistant_id, timeout=60
            )

            if run.status != "completed":
                error_msg = f"Run завершился со статусом: {run.status}"
                if run.last_error:
                    error_msg += f" ({run.last_error.code}: {run.last_error.message})"
                logging.error(f"Ошибка выполнения ассистента: {error_msg}")
                raise Exception(error_msg)

            logging.info(f"Run завершен успешно: {run.id}, получаем сообщения")

            messages = await client_async.beta.threads.messages.list(
                thread_id=thread_id, limit=1, run_id=run.id
            )

            if not messages.data:
                raise Exception("Пустой ответ от ассистента")

            assistant_message = messages.data[0]
            text_response = []
            response_files = []
            response_images = []

            logging.info(f"Получено сообщение от ассистента: {assistant_message.id}")
            logging.info(
                f"Количество блоков контента: {len(assistant_message.content)}"
            )

            for content_block in assistant_message.content:
                if content_block.type == "text":
                    cleaned_text = content_block.text.value
                    annotations = content_block.text.annotations

                    logging.info(f"Текстовый блок с {len(annotations)} аннотациями")

                    for idx, ann in enumerate(annotations):
                        if hasattr(ann, "file_path"):
                            file_id = ann.file_path.file_id
                            response_files.append(file_id)
                            logging.info(f"Обнаружен файл в аннотации: {file_id}")
                            cleaned_text = cleaned_text.replace(
                                ann.text, f" [Файл {idx + 1}]"
                            )

                    text_response.append(cleaned_text.strip())

                elif content_block.type == "image_file":
                    image_id = content_block.image_file.file_id
                    logging.info(f"Обнаружено изображение в ответе: {image_id}")
                    response_images.append(image_id)
                else:
                    logging.warning(
                        f"Неизвестный тип блока контента: {content_block.type}"
                    )

            if text_response:
                full_text = "\n".join(text_response)
                user_data["messages"].append(
                    {"role": "assistant", "content": full_text}
                )
                user_data["count_messages"] += 1
                await save_user_data(user_id)

                await send_safe_message(message, full_text, user_data)
            else:
                logging.warning("Получен ответ без текста")

            logging.info(f"Найдено {len(response_files)} файлов для отправки")
            for file_id in response_files:
                file_sent = await send_file_to_user(
                    bot, file_id, message, chat_id, is_image=False
                )
                if not file_sent:
                    logging.warning(f"Не удалось отправить файл {file_id}")

            logging.info(f"Найдено {len(response_images)} изображений для отправки")
            for file_id in response_images:
                image_sent = await send_file_to_user(
                    bot, file_id, message, chat_id, is_image=True
                )
                if not image_sent:
                    logging.warning(f"Не удалось отправить изображение {file_id}")

            break

        except NotFoundError:
            logging.warning("Тред не найден, создаём новый тред и повторяем попытку.")
            current_assistant = user_data.get("current_assistant", 1)

            # Сбрасываем текущий thread_id и создаем новый
            await reset_thread(user_data, user_id, current_assistant)

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
                current_assistant = user_data.get("current_assistant", 1)

                # Сбрасываем текущий thread_id
                await reset_thread(user_data, user_id, current_assistant)

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


def get_thread_id_key(assistant_number):
    """Возвращает ключ для thread_id в зависимости от номера ассистента"""
    if assistant_number == 1:
        return "assistant_thread_id"
    else:
        return f"assistant_thread_id_{assistant_number}"


async def reset_thread(user_data, user_id, current_assistant):
    """
    Сбрасывает thread_id для указанного ассистента в данных пользователя
    и асинхронно сохраняет изменения в базу данных
    """
    try:
        thread_id_key = get_thread_id_key(current_assistant)
        old_thread_id = user_data.get(thread_id_key, "")

        # Сбрасываем thread_id
        user_data[thread_id_key] = ""

        # Сохраняем данные пользователя
        await save_user_data(user_id)

        logging.info(
            f"Успешно сброшен thread_id для ассистента {current_assistant}: {old_thread_id}"
        )
        return True
    except Exception as e:
        logging.error(
            f"Ошибка при сбросе thread_id для ассистента {current_assistant}: {str(e)}"
        )
        return False


def get_assistant_id(user_data, assistant_number):
    """
    Возвращает assistant_id в зависимости от номера ассистента.
    Если id не задан в user_data, берет его из конфигурации
    """
    # Получаем ключ для хранения ID ассистента
    key = f"assistant_id_{assistant_number}"

    # Если в user_data есть ID для данного ассистента, используем его
    if user_data.get(key) and user_data[key].strip():
        return user_data[key]

    # Иначе берем ID из конфигурации
    return get_openai_assistant_id(assistant_number)


async def send_safe_message(message: Message, text: str, user_data: dict) -> None:
    """Отправка сообщений с удалением маркеров заголовков, конструкций вида 【...】
    и сохранением кода."""
    try:
        # Шаг 1: Извлечение блоков кода
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

        # Шаг 2: Разбивка на части ≤ 4000 символов (более безопасный лимит для Telegram)
        max_chunk_size = 4000
        chunks = []
        current_chunk = []
        current_length = 0

        # Разбиваем текст на строки
        lines = formatted_text.split("\n")

        for line in lines:
            # Если строка слишком длинная, разбиваем её на подстроки
            if len(line) > max_chunk_size:
                # Сначала добавляем текущий chunk, если он не пустой
                if current_chunk:
                    chunks.append("\n".join(current_chunk))
                    current_chunk = []
                    current_length = 0

                # Разбиваем длинную строку на части по max_chunk_size символов
                # Стараемся делить по пробелам, когда возможно
                start = 0
                while start < len(line):
                    # Если оставшаяся часть строки помещается в chunk
                    if len(line) - start <= max_chunk_size:
                        part = line[start:]
                        chunks.append(part)
                        start = len(line)
                    else:
                        # Ищем последний пробел в диапазоне
                        end = start + max_chunk_size
                        split_pos = line.rfind(" ", start, end)

                        # Если пробел не найден, просто разрезаем по размеру
                        if split_pos == -1 or split_pos <= start:
                            part = line[start:end]
                            start = end
                        else:
                            part = line[start:split_pos]
                            start = split_pos + 1  # +1 чтобы пропустить пробел

                        chunks.append(part)
            else:
                # Обычная обработка для строк нормальной длины
                line_length = len(line) + 1  # +1 для символа новой строки
                if current_length + line_length > max_chunk_size:
                    chunks.append("\n".join(current_chunk))
                    current_chunk = [line]
                    current_length = line_length
                else:
                    current_chunk.append(line)
                    current_length += line_length

        # Добавляем последний chunk, если он есть
        if current_chunk:
            chunks.append("\n".join(current_chunk))

        # Шаг 3: Восстановление блоков кода
        final_chunks = []
        for chunk in chunks:
            restored_chunk = chunk
            for idx, code in enumerate(code_blocks):
                restored_chunk = restored_chunk.replace(f"%%CODE_BLOCK_{idx}%%", code)
            final_chunks.append(restored_chunk)

        # Функция для конвертации Markdown в HTML
        def markdown_to_html(text):
            # Обработка блоков кода (многострочных)
            code_blocks_html = []
            parts = re.split(r"(```[\s\S]*?```)", text)

            result_parts = []
            for i, part in enumerate(parts):
                if i % 2 == 1:  # Это блок кода
                    # Извлекаем язык программирования, если указан
                    lang_match = re.match(r"```(\w*)\n([\s\S]*?)```", part)
                    if lang_match:
                        lang, code_content = lang_match.groups()
                        if lang:
                            html_code = f'<pre><code class="language-{lang}">{code_content}</code></pre>'
                        else:
                            html_code = f"<pre>{code_content}</pre>"
                    else:
                        # Если формат не соответствует ожидаемому, сохраняем как простой блок кода
                        code_content = part.strip("`").strip()
                        html_code = f"<pre>{code_content}</pre>"

                    code_blocks_html.append(html_code)
                    result_parts.append(
                        f"%%HTML_CODE_BLOCK_{len(code_blocks_html) - 1}%%"
                    )
                else:
                    # Обработка строчных элементов
                    # Заменяем разметку жирного текста
                    processed_part = re.sub(r"\*(.*?)\*", r"<b>\1</b>", part)
                    # Заменяем разметку курсива
                    processed_part = re.sub(r"_(.*?)_", r"<i>\1</i>", processed_part)
                    # Заменяем разметку инлайн-кода
                    processed_part = re.sub(
                        r"`(.*?)`", r"<code>\1</code>", processed_part
                    )
                    # Заменяем ссылки [text](url)
                    processed_part = re.sub(
                        r"\[(.*?)\]\((.*?)\)", r'<a href="\2">\1</a>', processed_part
                    )

                    result_parts.append(processed_part)

            # Собираем результат и восстанавливаем блоки кода
            result = "".join(result_parts)
            for idx, code in enumerate(code_blocks_html):
                result = result.replace(f"%%HTML_CODE_BLOCK_{idx}%%", code)

            return result

        # Шаг 4: Отправка сообщений с безопасной обработкой разметки
        for i, chunk in enumerate(final_chunks):
            try:
                if i == 0:
                    # Безопасно отправляем первое сообщение с префиксом модели
                    msg_text = f"**{user_data['model_message_chat']}**{chunk}"
                    try:
                        # Сначала пробуем отправить с MARKDOWN - без экранирования
                        await message.reply(
                            msg_text,
                            parse_mode=ParseMode.MARKDOWN,
                            disable_web_page_preview=True,
                        )
                    except TelegramBadRequest as e:
                        # Если ошибка в разметке, попробуем с HTML
                        if "can't parse entities" in str(e):
                            try:
                                # Конвертируем разметку Markdown в HTML
                                html_text = markdown_to_html(msg_text)

                                await message.reply(
                                    html_text,
                                    parse_mode=ParseMode.HTML,
                                    disable_web_page_preview=True,
                                )
                            except TelegramBadRequest as html_error:
                                # Если и HTML не сработал, логируем ошибку и отправляем без форматирования
                                logging.error(
                                    f"HTML-разметка не сработала: {str(html_error)}"
                                )
                                await message.reply(
                                    msg_text[:4000],
                                    parse_mode=None,
                                    disable_web_page_preview=True,
                                )
                        else:
                            # Если другая ошибка
                            await message.reply(
                                msg_text[:4000],
                                parse_mode=None,
                                disable_web_page_preview=True,
                            )
                else:
                    # Последующие сообщения
                    try:
                        # Также пробуем с MARKDOWN сначала
                        await message.answer(
                            chunk,
                            parse_mode=ParseMode.MARKDOWN,
                            disable_web_page_preview=True,
                        )
                    except TelegramBadRequest as e:
                        # Если ошибка в разметке, пробуем HTML
                        if "can't parse entities" in str(e):
                            try:
                                # Конвертируем разметку Markdown в HTML
                                html_chunk = markdown_to_html(chunk)

                                await message.answer(
                                    html_chunk,
                                    parse_mode=ParseMode.HTML,
                                    disable_web_page_preview=True,
                                )
                            except TelegramBadRequest as html_error:
                                # Если и HTML не сработал, логируем ошибку и отправляем без форматирования
                                logging.error(
                                    f"HTML-разметка не сработала: {str(html_error)}"
                                )
                                await message.answer(
                                    chunk[:4000],
                                    parse_mode=None,
                                    disable_web_page_preview=True,
                                )
                        else:
                            # Если другая ошибка
                            await message.answer(
                                chunk[:4000],
                                parse_mode=None,
                                disable_web_page_preview=True,
                            )
            except Exception as e:
                # Отправляем сообщение без разметки как последнее средство
                logging.error(f"Ошибка при отправке сообщения: {str(e)}")
                await message.answer(chunk[:4000], disable_web_page_preview=True)

        # Голосовой ответ
        if user_data.get("voice_answer"):
            await text_to_speech(message.chat.id, text)

    except Exception as e:
        logging.error(f"Ошибка в send_safe_message: {str(e)}")
        # В случае полного сбоя, отправляем текст без обработки, сократив до безопасной длины
        try:
            await message.answer(text[:4000], disable_web_page_preview=True)
        except Exception as err:
            logging.error(f"Критическая ошибка при отправке сообщения: {str(err)}")


async def create_new_thread(user_data, user_id, current_assistant):
    """
    Создает новый тред для указанного ассистента
    и сохраняет его ID в данных пользователя
    """
    try:
        # Создаем новый тред
        thread_id_key = get_thread_id_key(current_assistant)
        client_async = get_async_openai_client()
        new_thread = await client_async.beta.threads.create()

        # Сохраняем ID нового треда
        user_data[thread_id_key] = new_thread.id

        # Сохраняем обновленные данные
        await save_user_data(user_id)

        logging.info(
            f"Создан новый тред {new_thread.id} для ассистента {current_assistant}"
        )
        return new_thread.id
    except Exception as e:
        logging.error(
            f"Ошибка при создании нового треда для ассистента {current_assistant}: {str(e)}"
        )
        return None


async def send_file_to_user(bot, file_id, message, chat_id, is_image=False):
    """
    Асинхронно отправляет файл пользователю с корректной обработкой ошибок

    В OpenAI API файлы обрабатываются следующим образом:
    1. Файлы с purpose="assistants" доступны во всех тредах без явной привязки к ассистенту
    2. Файлы с purpose="vision" используются только для обработки изображений
    3. При добавлении файла в сообщение треда, он указывается в параметре attachments
       с обязательным параметром tools для указания способа обработки
    """
    try:
        logging.info(
            f"Загрузка содержимого {'изображения' if is_image else 'файла'}: {file_id}"
        )

        # Получение содержимого файла от OpenAI
        try:
            client_async = get_async_openai_client()
            file_content = await client_async.files.content(file_id)
            file_data = file_content.read()
        except Exception as e:
            logging.error(f"Ошибка получения файла {file_id} от OpenAI: {e}")
            return False

        # Проверка размера файла
        if len(file_data) == 0:
            logging.error(f"Файл {file_id} пуст")
            return False

        # Telegram лимиты: 50MB для документов, 10MB для фото
        max_size = 10 * 1024 * 1024 if is_image else 50 * 1024 * 1024
        if len(file_data) > max_size:
            logging.error(f"Файл {file_id} слишком большой: {len(file_data)} байт")
            try:
                await bot.send_message(
                    chat_id=chat_id,
                    text=f"⚠️ Файл слишком большой для отправки через Telegram ({len(file_data) // 1024 // 1024} МБ)",
                    reply_to_message_id=message.message_id,
                    disable_web_page_preview=True,
                )
            except Exception:
                pass
            return False

        if is_image:
            try:
                logging.info(f"Отправка изображения пользователю")
                await bot.send_photo(
                    chat_id=chat_id,
                    photo=types.BufferedInputFile(
                        file_data, filename=f"response_image_{file_id}.png"
                    ),
                    reply_to_message_id=message.message_id,
                )
            except Exception as e:
                logging.error(f"Ошибка отправки изображения: {e}")
                return False
        else:
            try:
                # Получаем информацию о файле для имени
                file_info = await client_async.files.retrieve(file_id)
                filename = (
                    file_info.filename
                    if hasattr(file_info, "filename") and file_info.filename
                    else f"file_{file_id}"
                )

                logging.info(f"Отправка файла пользователю: {filename}")
                await bot.send_document(
                    chat_id=chat_id,
                    document=types.BufferedInputFile(file_data, filename=filename),
                    reply_to_message_id=message.message_id,
                )
            except Exception as e:
                logging.error(f"Ошибка отправки документа: {e}")
                return False

        return True

    except Exception as e:
        logging.error(
            f"Неожиданная ошибка при отправке {'изображения' if is_image else 'файла'} {file_id}: {str(e)}"
        )
        return False
