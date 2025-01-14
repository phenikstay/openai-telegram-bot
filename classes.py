import json
from pathlib import Path
from typing import Optional

from sqlalchemy import String, Boolean, Integer, Text
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker
from sqlalchemy.orm import declarative_base, mapped_column, Mapped

# Указываем путь к файлу базы
db_file = Path(__file__).parent / "database.sqlite"
DB_URI = f"sqlite+aiosqlite:///{db_file}"

# Создаём движок
engine = create_async_engine(
    DB_URI,
    echo=False,  # Можно поставить True для отладки
)

# Создаём фабрику сессий
SessionLocal = async_sessionmaker(
    engine,
    expire_on_commit=False,
)

# Базовый класс моделей
Base = declarative_base()


class UserDataModel(Base):
    """
    SQLAlchemy-модель для хранения пользовательских данных.
    Таблица 'users_data'.
    """

    __tablename__ = "users_data"

    user_id: Mapped[str] = mapped_column(String, primary_key=True)
    model: Mapped[str] = mapped_column(String, default="gpt-4o-mini")
    model_message_info: Mapped[str] = mapped_column(String, default="4o mini")
    model_message_chat: Mapped[str] = mapped_column(String, default="4o mini:\n\n")
    messages: Mapped[Optional[str]] = mapped_column(Text, default="[]")
    count_messages: Mapped[int] = mapped_column(Integer, default=0)
    max_out: Mapped[int] = mapped_column(Integer, default=240000)
    voice_answer: Mapped[bool] = mapped_column(Boolean, default=False)
    system_message: Mapped[str] = mapped_column(Text, default="")
    pic_grade: Mapped[str] = mapped_column(String, default="standard")
    pic_size: Mapped[str] = mapped_column(String, default="1024x1024")

    def to_dict(self) -> dict:
        """
        Преобразует SQLAlchemy-объект в словарь для удобной передачи в код.
        """
        return {
            "user_id": self.user_id,
            "model": self.model,
            "model_message_info": self.model_message_info,
            "model_message_chat": self.model_message_chat,
            "messages": json.loads(self.messages) if self.messages else [],
            "count_messages": self.count_messages,
            "max_out": self.max_out,
            "voice_answer": self.voice_answer,
            "system_message": self.system_message,
            "pic_grade": self.pic_grade,
            "pic_size": self.pic_size,
        }


async def init_async_db() -> None:
    """
    Создаём таблицы на лету (без Alembic).
    Если используете Alembic, таблицы будут создаваться миграциями.
    """
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
