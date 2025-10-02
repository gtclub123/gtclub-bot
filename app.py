import os
import json
import re
from typing import Dict, Any, List

from fastapi import FastAPI, Request, HTTPException
from fastapi.responses import JSONResponse, PlainTextResponse

from dotenv import load_dotenv

# ===================== ENV FIRST =====================
load_dotenv()  # локально подтягивает .env; на Render берётся из Settings → Environment

TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")
ADMIN_CHAT_ID = os.getenv("ADMIN_CHAT_ID")
WEBHOOK_BASE = os.getenv("WEBHOOK_BASE")               # можно оставить пустым на Render
RENDER_EXTERNAL_URL = os.getenv("RENDER_EXTERNAL_URL") # Render подставляет автоматически
PORT = int(os.getenv("PORT", "8000"))

if not TELEGRAM_TOKEN:
    raise RuntimeError("Missing TELEGRAM_TOKEN env var")

WEBHOOK_BASE = WEBHOOK_BASE or RENDER_EXTERNAL_URL
WEBHOOK_PATH = f"/webhook/{TELEGRAM_TOKEN}"
WEBHOOK_URL = (WEBHOOK_BASE + WEBHOOK_PATH) if WEBHOOK_BASE else None

# ===================== AIOGRAM 3.7+ =====================
from aiogram import Bot, Dispatcher, types
from aiogram.client.default import DefaultBotProperties
from aiogram.types import Update, ReplyKeyboardMarkup, KeyboardButton

bot = Bot(token=TELEGRAM_TOKEN, default=DefaultBotPrope_
