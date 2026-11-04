import os

from dotenv import load_dotenv

load_dotenv()

GROQ_API_KEY = os.getenv("GROQ_API_KEY")

TEXT_MODEL = "openai/gpt-oss-20b"

SYSTEM_PROMPT = (
    "Ты дружелюбный помощник внутри Telegram-бота. "
    "Отвечай понятно и коротко: максимум 5 предложений. "
    "Всегда отвечай на том же языке, на котором написал пользователь."
)

if not GROQ_API_KEY:
    raise ValueError("Не найден BOT_TOKEN или GROQ_API_KEY. Проверь файл .env!")
