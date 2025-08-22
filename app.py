import os
import sys
import json
import logging

from aiohttp import web
from aiogram import Bot, Dispatcher, Router
from aiogram.types import Message, Update, ReplyKeyboardMarkup, KeyboardButton
from aiogram.filters import CommandStart, Command
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.client.default import DefaultBotProperties

# ====== CONFIG ======
logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
log = logging.getLogger("gtclub-bot")

BOT_TOKEN = os.getenv("TELEGRAM_TOKEN") or os.getenv("BOT_TOKEN")
if not BOT_TOKEN:
    raise RuntimeError("BOT_TOKEN/TELEGRAM_TOKEN is not set")

WEBHOOK_BASE = (os.getenv("WEBHOOK_BASE") or "").rstrip("/")
WEBHOOK_PATH = "/webhook"
WEBHOOK_URL = f"{WEBHOOK_BASE}{WEBHOOK_PATH}" if WEBHOOK_BASE else None

HOST = "0.0.0.0"
PORT = int(os.getenv("PORT", 8080))

# ====== BOT CORE (aiogram >= 3.7) ======
bot = Bot(token=BOT_TOKEN, default=DefaultBotProperties(parse_mode="HTML"))
dp = Dispatcher(storage=MemoryStorage())
router = Router()
dp.include_router(router)

# ====== I18N ======
def lang_key(code: str) -> str:
    c = (code or "").lower()
    if c.startswith("uk"):
        return "uk"
    if c.startswith("en"):
        return "en"
    return "ru"

def labels(lg: str):
    if lg == "uk":
        return {
            "welcome": "👋 Ласкаво просимо до <b>GTClub File Service</b>! 🚗⚡\nОберіть опцію нижче:",
            "order": "📂 Зробити замовлення",
            "info": "ℹ️ Інформація",
            "support": "💬 Підтримка",
            "order_text": "Надішліть файл прошивки як документ та додайте вимоги/нотатки.",
            "info_text": "Чіптюнінг-файли: Stage 1–3, DPF/EGR/AdBlue OFF та інші послуги.",
