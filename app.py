import os
import sys
import json
import logging
from datetime import datetime

from aiohttp import web
from aiogram import Bot, Dispatcher, Router, F
from aiogram.types import Message, Update, ReplyKeyboardMarkup, KeyboardButton, CallbackQuery
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.filters import CommandStart, Command

# ====== CONFIG ======
logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
log = logging.getLogger("gtclub-bot:diag")

BOT_TOKEN = os.getenv("TELEGRAM_TOKEN") or os.getenv("BOT_TOKEN")
if not BOT_TOKEN:
    raise RuntimeError("BOT_TOKEN/TELEGRAM_TOKEN is not set")

WEBHOOK_BASE = (os.getenv("WEBHOOK_BASE") or "").rstrip("/")
WEBHOOK_PATH = "/webhook"
WEBHOOK_URL = f"{WEBHOOK_BASE}{WEBHOOK_PATH}" if WEBHOOK_BASE else None

HOST = "0.0.0.0"
PORT = int(os.getenv("PORT", 8080))

bot = Bot(token=BOT_TOKEN, parse_mode="HTML")
dp = Dispatcher(storage=MemoryStorage())
router = Router()
dp.include_router(router)

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
        }
    if lg == "en":
        return {
            "welcome": "👋 Welcome to <b>GTClub File Service</b>! 🚗⚡\nChoose an option below:",
            "order": "📂 Place order",
            "info": "ℹ️ Info",
            "support": "💬 Support",
        }
    return {
        "welcome": "👋 Добро пожаловать в <b>GTClub File Service</b>! 🚗⚡\nВыберите опцию ниже:",
        "order": "📂 Сделать заказ",
        "info": "ℹ️ Информация",
        "support": "💬 Поддержка",
    }

def main_kb(lg: str) -> ReplyKeyboardMarkup:
    t = labels(lg)
    return ReplyKeyboardMarkup(
        keyboard=[[KeyboardButton(text=t["order"])],
                  [KeyboardButton(text=t["info"]), KeyboardButton(text=t["support"])]],
        resize_keyboard=True
    )

@router.message(CommandStart())
async def on_start(message: Message):
    lg = lang_key(getattr(message.from_user, "language_code", ""))
    t = labels(lg)
    log.info("START from %s (%s) chat=%s", message.from_user.id, lg, message.chat.id)
    await message.answer(t["welcome"], reply_markup=main_kb(lg))

@router.message(Command("kbtest"))
async def on_kbtest(message: Message):
    lg = lang_key(getattr(message.from_user, "language_code", ""))
    t = labels(lg)
    kb = main_kb(lg)
    log.info("KBTEST to %s chat=%s", message.from_user.id, message.chat.id)
    await message.answer("Inline keyboard test below:", reply_markup=kb)

@router.message()
async def on_any_text(message: Message):
    lg = lang_key(getattr(message.from_user, "language_code", ""))
    t = labels(lg)
    txt = (message.text or "").strip()
    log.info("TEXT '%s' from %s chat=%s", txt, message.from_user.id, message.chat.id)
    await message.answer(t["welcome"], reply_markup=main_kb(lg))

# ==== WEBHOOK ====
async def handle_webhook(request: web.Request):
    body = await request.text()
    try:
        data = json.loads(body)
    except Exception:
        log.error("Non-JSON body: %s", body[:200])
        return web.Response(status=400, text="bad json")

    log.info("UPDATE RAW: %s", body[:500])
    update = Update(**data)
    await dp.feed_update(bot, update)
    return web.Response(text="ok")

async def healthcheck(request: web.Request):
    return web.Response(text="ok")

async def diag(request: web.Request):
    import aiohttp
    info = {
        "time": datetime.utcnow().isoformat() + "Z",
        "python": sys.version.split()[0],
        "aiogram": "3.x",
        "aiohttp": aiohttp.__version__,
        "AIOHTTP_NO_EXTENSIONS": os.getenv("AIOHTTP_NO_EXTENSIONS"),
        "WEBHOOK_URL": WEBHOOK_URL,
    }
    return web.json_response(info)

async def set_webhook_handler(request: web.Request):
    if not WEBHOOK_URL:
        return web.Response(status=400, text="WEBHOOK_BASE is not set")
    await bot.set_webhook(WEBHOOK_URL, drop_pending_updates=True)
    log.info("Webhook set to %s", WEBHOOK_URL)
    return web.Response(text=f"Webhook set to {WEBHOOK_URL}")

async def on_startup(app: web.Application):
    try:
        import aiohttp
        log.info("Startup: python=%s aiogram=3.x aiohttp=%s AIOHTTP_NO_EXTENSIONS=%s",
                 sys.version.split()[0], aiohttp.__version__, os.getenv("AIOHTTP_NO_EXTENSIONS"))
    except Exception:
        pass
    if WEBHOOK_URL:
        await bot.set_webhook(WEBHOOK_URL, drop_pending_updates=True)
        log.info("Webhook set to %s", WEBHOOK_URL)
    else:
        log.warning("WEBHOOK_BASE not set; call /setwebhook later.")

async def on_shutdown(app: web.Application):
    try:
        await bot.delete_webhook()
    except Exception as e:
        log.warning("delete_webhook failed: %s", e)
    await bot.session.close()

def create_app():
    app = web.Application()
    app.router.add_post(WEBHOOK_PATH, handle_webhook)
    app.router.add_get("/healthz", healthcheck)
    app.router.add_get("/diag", diag)
    app.router.add_get("/setwebhook", set_webhook_handler)
    app.on_startup.append(on_startup)
    app.on_shutdown.append(on_shutdown)
    return app

if __name__ == "__main__":
    web.run_app(create_app(), host="0.0.0.0", port=PORT)
