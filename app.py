import os
import json
import re
import logging
from typing import Dict, Any, List

from fastapi import FastAPI, Request, HTTPException
from fastapi.responses import PlainTextResponse
from dotenv import load_dotenv

# ---------- ENV & LOGGING ----------
load_dotenv()
logging.basicConfig(level=logging.INFO)
log = logging.getLogger("gtclub-bot")

TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")
ADMIN_CHAT_ID = os.getenv("ADMIN_CHAT_ID")
WEBHOOK_BASE = os.getenv("WEBHOOK_BASE")
RENDER_EXTERNAL_URL = os.getenv("RENDER_EXTERNAL_URL")  # Render подставляет автоматически
DEBUG = os.getenv("DEBUG", "0") == "1"  # DEBUG=1 в окружении включает подробные логи/пинг

if not TELEGRAM_TOKEN:
    raise RuntimeError("Missing TELEGRAM_TOKEN env var")

WEBHOOK_BASE = WEBHOOK_BASE or RENDER_EXTERNAL_URL
# Гард от мусора в WEBHOOK_BASE (бывает на Render)
if WEBHOOK_BASE and not WEBHOOK_BASE.startswith("http"):
    WEBHOOK_BASE = None

WEBHOOK_PATH = f"/webhook/{TELEGRAM_TOKEN}"
WEBHOOK_URL = (WEBHOOK_BASE + WEBHOOK_PATH) if WEBHOOK_BASE else None

# ---------- AIOGRAM 3.7+ ----------
from aiogram import Bot, Dispatcher, types
from aiogram.client.default import DefaultBotProperties
from aiogram.types import Update, ReplyKeyboardMarkup, KeyboardButton

bot = Bot(token=TELEGRAM_TOKEN, default=DefaultBotProperties(parse_mode="HTML"))
dp = Dispatcher()

# ---------- FLOW ----------
with open(os.path.join(os.path.dirname(__file__), "flow.json"), "r", encoding="utf-8") as f:
    FLOW: Dict[str, Any] = json.load(f)

FLOW_STATES = FLOW["flow"]
AUTOMATIONS = FLOW.get("automations", {})

# ---------- STATE ----------
USER_STATE: Dict[int, Dict[str, Any]] = {}

def get_user(chat_id: int) -> Dict[str, Any]:
    if chat_id not in USER_STATE:
        USER_STATE[chat_id] = {"state": "start", "data": {}, "consent": True, "dnd": False}
    return USER_STATE[chat_id]

def save_field(data: Dict[str, Any], field_path: str, value: Any):
    keys = field_path.split("._
