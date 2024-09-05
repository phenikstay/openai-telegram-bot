# Telegram Bot Using OpenAI
This project is a Telegram bot written in Python using the aiogram 3 library. It uses the OpenAI API to generate texts and images, as well as to work with audio messages. The bot supports several OpenAI models, including GPT-4.0 Omni and DALL·E 3, and allows users to interact with it through text and voice messages.

## Installation and Setup
### Requirements
- Python 3.8 or higher

### Installing
1. Clone the repository:
   ```sh
   git clone https://github.com/phenikstay/openai-telegram-bot.git
   cd openai-telegram-bot
   ```
   
2. Create a directory for audio files:
   ```sh
   mkdir voice
   ```

3. Install the dependencies:
   ```sh
   pip install -r requirements.txt
   ```

### Configuration
1. Create a `config.ini` file in the root directory of the project and add the following lines:
   ```ini
   [OpenAI]
   api_key = your_api_key
   
   [Telegram]
   token = your_token
   owner_id = your_user_id
   ```
   - `api_key`: Your OpenAI API key.
   - `token`: Your Telegram bot token.
   - `owner_id`: Your User ID in Telegram, which will have access to the bot.

## Running the Bot
Run the bot with the following command:
```sh
python main.py
```

## Features
### Main Commands
- `/start`: Initializes the GPT-4.0 Mini model, disables voice response, clears the dialogue context, resets the message counter, removes the system role, and sets the image quality and size.
- `/menu`: Opens the settings menu.
- `/help`: Displays help and usage instructions for the bot.

### Settings Menu
- **Model Selection**:
  - GPT-4.0 Mini
  - GPT-4.0
  - DALL·E 3

- **Image Settings**:
  - Set quality (SD/HD)
  - Set size (1024x1024, 1024x1792, 1792x1024)

- **Context Actions**:
  - Show current context
  - Clear current context

- **Voice Responses**:
  - Enable voice response
  - Disable voice response

- **System Role**:
  - Assign system role
  - Remove system role

- **Information**:
  - Show bot status information

## Project Structure
- `main.py`: Main file to run the bot.
- `handler.py`: Handlers for various commands and messages.
- `classes.py`: Classes for database operations and user data management.
- `base.py`: Functions for database operations.
- `middlewares.py`: Middleware for rate limiting.
- `buttons.py`: Defines buttons and keyboards for user interaction.
- `function.py`: Functions for processing voice messages and trimming long messages.
- `text.py`: Text messages used by the bot.
- `config.ini`: Configuration file for storing tokens and API keys.
- `requirements.txt`: List of dependencies.

## Contribution and Support
If you find any bugs or have suggestions for improvement, feel free to create an issue or submit a pull request in this repository.

## License
This project is licensed under the MIT License.
