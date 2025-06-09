# openai-telegram-bot - Advanced Telegram Bot with OpenAI Integration

An advanced Telegram bot that integrates with OpenAI API to provide multiple AI model access, voice processing, image generation, document handling, and assistant capabilities. Built with Python using aiogram framework and SQLite database.

## 🚀 Features

### Multi-Model Support
- **GPT Models**: 4o mini, 4o, 4.1, o1-mini, o1-preview, o3-mini, o1-pro
- **Web Search**: gpt-4o-search-preview with web context
- **Image Generation**: DALL-E 3 with customizable quality and size
- **OpenAI Assistants**: Support for up to 3 custom assistants with thread management

### Advanced Capabilities
- **Voice Processing**: Speech-to-text (Whisper) and text-to-speech
- **Image Analysis**: Vision API for image understanding and description
- **Document Processing**: Support for various file formats through assistants
- **Context Management**: Intelligent message history with pruning
- **Multi-User Support**: Owner-based access control with multiple owners
- **Caching System**: LRU cache for optimized database performance

### User Interface
- **Interactive Menus**: Comprehensive inline keyboard navigation
- **System Roles**: Custom AI personality settings
- **Voice Responses**: Toggle audio output on/off
- **Context Control**: View and clear conversation history
- **Real-time Information**: User statistics and configuration display

## 📋 Prerequisites

Before installing, ensure you have:

- Python 3.8 or higher
- A Telegram Bot Token (from [@BotFather](https://t.me/botfather))
- OpenAI API Key with access to desired models
- FFmpeg (for audio processing)

## 🛠 Installation

### 1. Clone the Repository
```bash
git clone https://github.com/phenikstay/openai-telegram-bot.git
cd openai-telegram-bot
```

### 2. Create Virtual Environment
```bash
python -m venv .venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate
```

### 3. Install Dependencies
```bash
pip install -r requirements.txt
```

### 4. Install FFmpeg
- **Ubuntu/Debian**: `sudo apt update && sudo apt install ffmpeg`
- **macOS**: `brew install ffmpeg`
- **Windows**: Download from [FFmpeg official site](https://ffmpeg.org/download.html)

### 5. Configuration Setup

Create a `config.ini` file in the project root:

```ini
[Telegram]
token = YOUR_TELEGRAM_BOT_TOKEN
owner_id = YOUR_USER_ID,ADDITIONAL_USER_ID  # Comma-separated for multiple owners

[OpenAI]
api_key = YOUR_OPENAI_API_KEY
assistant_id = ASSISTANT_1_ID  # Optional
assistant_id_2 = ASSISTANT_2_ID  # Optional
assistant_id_3 = ASSISTANT_3_ID  # Optional
```

### 6. Get Your User ID
1. Start the bot using `/start` command
2. The bot will display your User ID in the response
3. Add your User ID to the `owner_id` field in `config.ini`

## 🚀 Running the Bot

### Development Mode
```bash
python main.py
```

### Production Mode (with systemd)

1. Create service file:
```bash
sudo nano /etc/systemd/system/openai-telegram-bot.service
```

2. Add configuration:
```ini
[Unit]
Description=openai-telegram-bot Telegram Bot
After=network.target

[Service]
Type=simple
User=phenikstay
WorkingDirectory=/path/to/openai-telegram-bot
Environment=PATH=/path/to/openai-telegram-bot/.venv/bin
ExecStart=/path/to/openai-telegram-bot/.venv/bin/python main.py
Restart=always
RestartSec=3

[Install]
WantedBy=multi-user.target
```

3. Enable and start:
```bash
sudo systemctl enable openai-telegram-bot.service
sudo systemctl start openai-telegram-bot.service
sudo systemctl status openai-telegram-bot.service
```

### Using Docker (Optional)

Create `Dockerfile`:
```dockerfile
FROM python:3.11-slim

RUN apt-get update && apt-get install -y ffmpeg && rm -rf /var/lib/apt/lists/*

WORKDIR /app
COPY requirements.txt .
RUN pip install -r requirements.txt

COPY . .

CMD ["python", "main.py"]
```

Build and run:
```bash
docker build -t openai-telegram-bot .
docker run -d --name openai-telegram-bot-bot -v $(pwd)/config.ini:/app/config.ini openai-telegram-bot
```

## 📖 Usage Guide

### Bot Commands
- `/start` - Initialize the bot and get your User ID
- `/menu` - Open the main menu with all options
- `/help` - Display detailed help information
- `/null` - Reset all settings to factory defaults

### Main Menu Options

#### 1. Model Selection
Choose from available AI models:
- **4o mini**: Fast, cost-effective model
- **4o**: Balanced performance and capabilities
- **4.1**: Enhanced reasoning capabilities
- **o1 models**: Advanced reasoning models
- **o3 mini**: Latest reasoning model
- **DALL-E 3**: Image generation
- **Web 4o**: Web search capabilities
- **Assistants 1-3**: Custom OpenAI assistants

#### 2. Image Settings
Configure DALL-E 3 generation:
- **Quality**: Standard or HD
- **Sizes**: 1024x1024, 1024x1792, 1792x1024

#### 3. Context Management
- **View Context**: Display conversation history
- **Clear Context**: Reset conversation memory

#### 4. Voice Features
- **Enable/Disable Voice Responses**: Toggle TTS output
- **Voice Input**: Send voice messages for speech-to-text

#### 5. System Role
- **Set Custom Role**: Define AI personality/behavior
- **Remove Role**: Reset to default behavior

### Advanced Features

#### Assistant Mode
When using assistant models, the bot:
- Maintains separate conversation threads for each assistant
- Supports file uploads and analysis
- Handles images with vision capabilities
- Processes documents with file search

#### Message Types Supported
- **Text**: Standard text conversations
- **Voice**: Speech-to-text processing
- **Images**: Vision analysis and description
- **Documents**: File processing through assistants

## 🏗 Architecture

### Project Structure
```
openai-telegram-bot/
├── main.py              # Application entry point
├── config_manager.py    # Configuration management
├── bot_manager.py       # Bot instance management
├── openai_manager.py    # OpenAI client management
├── handler_menu.py      # Menu and command handlers
├── handler_work.py      # Message processing handlers
├── base.py             # Database operations and caching
├── classes.py          # SQLAlchemy models
├── function.py         # Utility functions
├── buttons.py          # Inline keyboard definitions
├── decorators.py       # Access control decorators
├── middlewares.py      # Request throttling middleware
├── text.py            # Static text messages
├── requirements.txt   # Python dependencies
└── voice/            # Temporary audio files directory
```

### Database Schema
The bot uses SQLite with the following user data structure:
- User preferences and settings
- Conversation history and context
- Assistant thread IDs
- Voice and image preferences
- Usage statistics

### Key Components

#### 1. Multi-Model Handler
Supports different OpenAI models with appropriate parameter handling:
- Context length management per model
- Model-specific features (reasoning effort, web search)
- Automatic message pruning for context limits

#### 2. Caching System
- LRU cache with 1000 user limit
- Automatic cache management
- Optimized database operations

#### 3. Voice Processing
- Whisper API for speech recognition
- TTS with chunked output for long responses
- Automatic audio format conversion

#### 4. Assistant Integration
- Thread-based conversations
- File attachment support
- Vision and document processing
- Automatic thread recovery

## 🛡 Security Features

- **Owner-only Access**: Bot restricted to configured users
- **Input Validation**: Secure handling of user inputs
- **Error Handling**: Comprehensive error management
- **Rate Limiting**: Throttling middleware to prevent abuse
- **Safe File Handling**: Secure temporary file management

## 🔧 Configuration Options

### Model Parameters
Each model can be configured with:
- Maximum output tokens
- Context window size
- Special parameters (reasoning effort, web search)

### Cache Settings
- Maximum cache size (default: 1000 users)
- TTL for throttling (default: 1.5 seconds)

### Audio Settings
- Voice model: Nova (TTS)
- Audio quality: 192k bitrate
- Chunk size: 1000 characters per audio file

## 📊 Monitoring and Logging

The bot includes comprehensive logging:
- Error tracking and exception handling
- User activity monitoring
- Performance metrics
- Database operation logs

## 🔄 Updates and Maintenance

### Regular Updates
- Monitor OpenAI API changes
- Update model availability
- Security patches

### Database Maintenance
- Automatic schema updates
- Cache optimization
- Storage cleanup

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Test thoroughly
5. Submit a pull request

## 📜 License

This project is licensed under the MIT License - see the LICENSE file for details.

## 🆘 Support

For issues and questions:
1. Check the logs for error messages
2. Verify configuration settings
3. Ensure all dependencies are installed
4. Check OpenAI API quota and permissions

## 🔮 Roadmap

- [ ] Multi-language support
- [ ] Plugin system for custom features
- [ ] Advanced analytics dashboard
- [ ] Integration with more AI providers
- [ ] Enhanced file processing capabilities 