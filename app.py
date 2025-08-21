import os
import sys
import logging
from aiohttp import web
from aiogram import Bot, Dispatcher
from aiogram.types import Message, Update
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.filters import Command, CommandStart
from aiogram import Router

logging.basicConfig(level=logging.INFO)
log = logging.getLogger("gtclub-bot")

# ---- ENV & Config ----
BOT_TOKEN = os.getenv("TELEGRAM_TOKEN") or os.getenv("BOT_TOKEN")
if not BOT_TOKEN:
    raise ValueError("BOT_TOKEN/TELEGRAM_TOKEN is not set in environment variables")

WEBHOOK_BASE = (os.getenv("WEBHOOK_BASE") or "").rstrip("/")
WEBHOOK_PATH = "/webhook"
WEBHOOK_URL = f"{WEBHOOK_BASE}{WEBHOOK_PATH}" if WEBHOOK_BASE else None

HOST = "0.0.0.0"
PORT = int(os.getenv("PORT", 8080))

# ---- Aiogram v3 core ----
bot = Bot(token=BOT_TOKEN)
dp = Dispatcher(storage=MemoryStorage())
router = Router()

# ---- Handlers (v3 syntax) ----
@router.message(CommandStart())
@router.message(Command("help"))
async def start_cmd(message: Message):
    lang = (message.from_user.language_code or "").lower()
    if lang.startswith("uk"):
        text = "👋 Ласкаво просимо до GTClub File Service! 🚗⚡\nОберіть дію нижче:"
    elif lang.startswith("en"):
        text = "👋 Welcome to GTClub File Service! 🚗⚡\nChoose an option below:"
    else:
        text = "👋 Добро пожаловать в GTClub File Service! 🚗⚡\nВыберите действие ниже:"
    await message.answer(text)

dp.include_router(router)

# ---- Webhook plumbing ----
async def handle_webhook(request: web.Request):
    data = await request.json()
    update = Update(**data)
    await dp.feed_update(bot, update)
    return web.Response(text="ok")

async def healthcheck(request: web.Request):
    return web.Response(text="ok")

async def set_webhook_handler(request: web.Request):
    if not WEBHOOK_URL:
        return web.Response(status=400, text="WEBHOOK_BASE is not set")
    await bot.set_webhook(WEBHOOK_URL, drop_pending_updates=True)
    log.info("Webhook set to %s", WEBHOOK_URL)
    return web.Response(text=f"Webhook set to {WEBHOOK_URL}")

async def on_startup(app: web.Application):
    try:
        import aiohttp
        log.info("Python: %s | aiogram: 3.x | aiohttp: %s | AIOHTTP_NO_EXTENSIONS=%s",
                 sys.version.split()[0], aiohttp.__version__, os.getenv("AIOHTTP_NO_EXTENSIONS"))
    except Exception:
        pass

    if WEBHOOK_URL:
        await bot.set_webhook(WEBHOOK_URL, drop_pending_updates=True)
        log.info("Webhook set to %s", WEBHOOK_URL)
    else:
        log.warning("WEBHOOK_BASE not set; webhook not configured. Open /setwebhook after setting it.")

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
    app.router.add_get("/setwebhook", set_webhook_handler)  # optional helper
    app.on_startup.append(on_startup)
    app.on_shutdown.append(on_shutdown)
    return app

if __name__ == "__main__":
    web.run_app(create_app(), host=HOST, port=PORT)
