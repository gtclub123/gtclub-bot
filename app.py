import os
import sys
import json
import logging

from aiohttp import web

# Global (lazy) bot/dispatcher/router holders
_bot = None
_dp = None
_router = None
_startup_error = None

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
log = logging.getLogger("gtclub-bot")

# ====== Config ======
BOT_TOKEN = os.getenv("TELEGRAM_TOKEN") or os.getenv("BOT_TOKEN")
WEBHOOK_BASE = (os.getenv("WEBHOOK_BASE") or "").rstrip("/")
WEBHOOK_PATH = "/webhook"
WEBHOOK_URL = f"{WEBHOOK_BASE}{WEBHOOK_PATH}" if WEBHOOK_BASE else None

HOST = "0.0.0.0"
PORT = int(os.getenv("PORT", 8080))

def _labels(lg: str):
    if lg == "uk":
        return {
            "welcome": "👋 Ласкаво просимо до <b>GTClub File Service</b>! 🚗⚡\nОберіть опцію нижче:",
            "order": "📂 Зробити замовлення",
            "info": "ℹ️ Інформація",
            "support": "💬 Підтримка",
            "order_text": "Надішліть файл прошивки як документ та додайте вимоги/нотатки.",
            "info_text": "Чіптюнінг-файли: Stage 1–3, DPF/EGR/AdBlue OFF та інші послуги.",
            "support_text": "Контакт: gtclub.com.ua@gmail.com",
        }
    if lg == "en":
        return {
            "welcome": "👋 Welcome to <b>GTClub File Service</b>! 🚗⚡\nChoose an option below:",
            "order": "📂 Place order",
            "info": "ℹ️ Info",
            "support": "💬 Support",
            "order_text": "Please send your ECU file as a document and add requirements/notes.",
            "info_text": "Chiptuning files: Stage 1–3, DPF/EGR/AdBlue OFF and more.",
            "support_text": "Contact: gtclub.com.ua@gmail.com",
        }
    return {
        "welcome": "👋 Добро пожаловать в <b>GTClub File Service</b>! 🚗⚡\nВыберите опцию ниже:",
        "order": "📂 Сделать заказ",
        "info": "ℹ️ Информация",
        "support": "💬 Поддержка",
        "order_text": "Отправьте файл прошивки как документ и добавьте требования/пожелания.",
        "info_text": "Чип-тюнинг файлы: Stage 1–3, DPF/EGR/AdBlue OFF и др.",
        "support_text": "Связь: gtclub.com.ua@gmail.com",
    }

# ====== Handlers (defined after lazy init) ======
def install_handlers(router):
    from aiogram.types import Message, Update, ReplyKeyboardMarkup, KeyboardButton
    from aiogram.filters import CommandStart, Command

    def lang_key(code: str) -> str:
        c = (code or "").lower()
        if c.startswith("uk"):
            return "uk"
        if c.startswith("en"):
            return "en"
        return "ru"

    def main_kb(lg: str) -> ReplyKeyboardMarkup:
        t = _labels(lg)
        return ReplyKeyboardMarkup(
            keyboard=[[KeyboardButton(text=t["order"])],
                      [KeyboardButton(text=t["info"]), KeyboardButton(text=t["support"])]],
            resize_keyboard=True
        )

    @router.message(CommandStart())
    async def cmd_start(message: Message):
        lg = lang_key(getattr(message.from_user, "language_code", ""))
        t = _labels(lg)
        await message.answer(t["welcome"], reply_markup=main_kb(lg))

    @router.message(Command("help"))
    async def cmd_help(message: Message):
        lg = lang_key(getattr(message.from_user, "language_code", ""))
        t = _labels(lg)
        await message.answer(t["welcome"], reply_markup=main_kb(lg))

    @router.message()
    async def on_text(message: Message):
        lg = lang_key(getattr(message.from_user, "language_code", ""))
        t = _labels(lg)
        txt = (message.text or "").strip()
        if txt == t["order"]:
            await message.answer(t["order_text"])
        elif txt == t["info"]:
            await message.answer(t["info_text"])
        elif txt == t["support"]:
            await message.answer(t["support_text"])
        else:
            await message.answer(t["welcome"], reply_markup=main_kb(lg))

# ====== Webhook endpoints ======
async def handle_webhook(request: web.Request):
    global _dp, _bot
    if _startup_error:
        return web.Response(status=503, text=f"bot not ready: { _startup_error }")
    data = await request.json()
    from aiogram.types import Update
    update = Update(**data)
    await _dp.feed_update(_bot, update)
    return web.Response(text="ok")

async def healthcheck(request: web.Request):
    status = "ok" if _startup_error is None else f"degraded: { _startup_error }"
    return web.Response(text=status)

async def diag(request: web.Request):
    try:
        import aiohttp
        aiohttp_version = aiohttp.__version__
    except Exception:
        aiohttp_version = "unknown"
    info = {
        "python": sys.version.split()[0],
        "aiogram": "3.x (lazy)",
        "aiohttp": aiohttp_version,
        "AIOHTTP_NO_EXTENSIONS": os.getenv("AIOHTTP_NO_EXTENSIONS"),
        "WEBHOOK_URL": WEBHOOK_URL,
        "has_token": bool(BOT_TOKEN),
        "startup_error": str(_startup_error) if _startup_error else None,
    }
    return web.json_response(info)

async def set_webhook_handler(request: web.Request):
    global _bot
    if _startup_error:
        return web.Response(status=503, text=f"bot not ready: { _startup_error }")
    if not WEBHOOK_URL:
        return web.Response(status=400, text="WEBHOOK_BASE is not set")
    await _bot.set_webhook(WEBHOOK_URL, drop_pending_updates=True)
    log.info("Webhook set to %s", WEBHOOK_URL)
    return web.Response(text=f"Webhook set to {WEBHOOK_URL}")

# ====== Lifecycle ======
async def on_startup(app: web.Application):
    global _bot, _dp, _router, _startup_error
    try:
        if not BOT_TOKEN:
            raise RuntimeError("Missing TELEGRAM_TOKEN/BOT_TOKEN")

        from aiogram import Bot, Dispatcher, Router
        from aiogram.fsm.storage.memory import MemoryStorage
        from aiogram.client.default import DefaultBotProperties

        _bot = Bot(token=BOT_TOKEN, default=DefaultBotProperties(parse_mode="HTML"))
        _dp = Dispatcher(storage=MemoryStorage())
        _router = Router()
        _dp.include_router(_router)
        install_handlers(_router)

        if WEBHOOK_URL:
            await _bot.set_webhook(WEBHOOK_URL, drop_pending_updates=True)
            log.info("Webhook set to %s", WEBHOOK_URL)
        else:
            log.warning("WEBHOOK_BASE not set; open /setwebhook after setting it.")
    except Exception as e:
        _startup_error = e
        log.exception("Startup error: %s", e)

async def on_shutdown(app: web.Application):
    global _bot
    if _bot:
        try:
            await _bot.delete_webhook()
        except Exception as e:
            log.warning("delete_webhook failed: %s", e)
        await _bot.session.close()

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
    web.run_app(create_app(), host=HOST, port=PORT)
