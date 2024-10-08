# Telegram Бот с использованием OpenAI

Этот проект представляет собой Telegram-бота, написанного на Python с использованием библиотеки `aiogram`. Он взаимодействует с API OpenAI для генерации текстов и изображений, а также работы с голосовыми сообщениями. Бот поддерживает различные модели OpenAI, такие как GPT-4.0 Omni, o1 and DALL·E 3 и позволяет взаимодействовать через текстовые и голосовые сообщения.

## Установка и Настройка

### Требования
- Python 3.8 или выше

### Установка

1. **Клонируйте репозиторий:**
   ```bash
   git clone https://github.com/phenikstay/openai-telegram-bot.git
   cd openai-telegram-bot
   ```

2. **Создайте директорию для аудиофайлов:**
   ```bash
   mkdir voice
   ```

3. **Установите зависимости:**
   ```bash
   pip install -r requirements.txt
   ```

### Конфигурация

1. Создайте файл `config.ini` в корневом каталоге проекта и добавьте следующие строки:

   ```ini
   [OpenAI]
   api_key = your_api_key

   [Telegram]
   token = your_token
   owner_id = your_user_id
   ```

   - `api_key`: Ваш API-ключ OpenAI.
   - `token`: Токен вашего Telegram-бота.
   - `owner_id`: Ваш User ID в Telegram, который будет иметь доступ к боту.

### Запуск Бота

Запустите бота с помощью следующей команды:
```bash
python main.py
```

## Функции

### Основные Команды

- **/start**: Инициализирует модель GPT-4.0 Mini, отключает голосовой ответ, очищает контекст диалога, сбрасывает счетчик сообщений, убирает системную роль и устанавливает качество и размер изображения.
- **/menu**: Открывает меню настроек.
- **/help**: Отображает справку и инструкции по использованию бота.

### Меню Настроек

- **Выбор модели:**
  - GPT-4.0 Mini
  - GPT-4.0
  - o1 Mini
  - o1
  - DALL·E 3

- **Настройки изображения:**
  - Установить качество (SD/HD)
  - Установить размер (1024x1024, 1024x1792, 1792x1024)

- **Действия с контекстом:**
  - Показать текущий контекст
  - Очистить текущий контекст

- **Голосовые ответы:**
  - Включить голосовой ответ
  - Отключить голосовой ответ

- **Системная роль:**
  - Назначить системную роль
  - Убрать системную роль

- **Информация:**
  - Показать информацию о статусе бота

## Структура Проекта

- `main.py`: Главный файл для запуска бота.
- `handler.py`: Обработчики для различных команд и сообщений.
- `classes.py`: Классы для операций с базой данных и управления данными пользователя.
- `base.py`: Функции для операций с базой данных.
- `middlewares.py`: Middleware для ограничения скорости запросов.
- `buttons.py`: Определяет кнопки и клавиатуры для взаимодействия с пользователем.
- `function.py`: Функции для обработки голосовых сообщений и обрезки длинных сообщений.
- `text.py`: Текстовые сообщения, используемые ботом.
- `config.ini`: Конфигурационный файл для хранения токенов и API-ключей.
- `requirements.txt`: Список зависимостей.

## Вклад и Поддержка

Если вы обнаружили ошибки или у вас есть предложения по улучшению, не стесняйтесь создать issue или отправить pull request в этом репозитории.