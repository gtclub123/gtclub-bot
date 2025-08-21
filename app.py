import os
import sys
import logging

from aiohttp import web
from aiogram import Bot, Dispatcher, Router, F
from aiogram.types import Message, Update, ReplyKeyboardMarkup, KeyboardButton
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.filters import CommandStart, Command
from aiogram.client.default import DefaultBotProperties

# ================== CONFIG ==================
logging.basicConfig(level=logging.INFO)
log = logging.getLogger("gtclub-bot")

BOT_TOKEN = os.getenv("TELEGRAM_TOKEN") or os.getenv("BOT_TOKEN")
if not BOT_TOKEN:
    raise ValueError("BOT_TOKEN/TELEGRAM_TOKEN is not set")

WEBHOOK_BASE = (os.getenv("WEBHOOK_BASE") or "").rstrip("/")
WEBHOOK_PATH = "/webhook"
WEBHOOK_URL = f"{WEBHOOK_BASE}{WEBHOOK_PATH}" if WEBHOOK_BASE else None

HOST = "0.0.0.0"
PORT = int(os.getenv("PORT", 8080))

# ================== CORE ==================
bot = Bot(token=BOT_TOKEN, default=DefaultBotProperties(parse_mode="HTML"))
dp = Dispatcher(storage=MemoryStorage())
router = Router()
dp.include_router(router)

# ================== I18N ==================
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
            "info_text": "Надаємо чіптюнінг-файли: Stage 1–3, DPF/EGR/AdBlue OFF та інші послуги.",
            "order_text": "Надішліть файл прошивки як документ та додайте побажання.",
            "support_text": "Зв'язок: gtclub.com.ua@gmail.com",
        }
    if lg == "en":
        return {
            "welcome": "👋 Welcome to <b>GTClub File Service</b>! 🚗⚡\nChoose an option below:",
            "order": "📂 Place order",
            "info": "ℹ️ Info",
            "support": "💬 Support",
            "info_text": "We provide chiptuning files: Stage 1–3, DPF/EGR/AdBlue OFF and more.",
            "order_text": "Please send your ECU file as a document and add notes/requirements.",
            "support_text": "Contact: gtclub.com.ua@gmail.com",
        }
    return {
        "welcome": "👋 Добро пожаловать в <b>GTClub File Service</b>! 🚗⚡\nВыберите опцию ниже:",
        "order": "📂 Сделать заказ",
        "info": "ℹ️ Информация",
        "support": "💬 Поддержка",
        "info_text": "Предоставляем чиптюнинг-файлы: Stage 1–3, DPF/EGR/AdBlue OFF и др.",
        "order_text": "Отправьте файл прошивки как документ и добавьте пожелания.",
        "support_text": "Связь: gtclub.com.ua@gmail.com",
    }

def main_kb(lg: str) -> ReplyKeyboardMarkup:
    t = labels(lg)
    kb = ReplyKeyboardMarkup(
        keyboard=[[KeyboardButton(text=t["order"])],
                  [KeyboardButton(text=t["info"]), KeyboardButton(text=t["support"])]],
        resize_keyboard=True
    )
    return kb

# ================== HANDLERS ==================
@router.message(CommandStart())
async def cmd_start(message: Message):
    lg = lang_key(getattr(message.from_user, "language_code", ""))
    t = labels(lg)
    await message.answer(t["welcome"], reply_markup=main_kb(lg))

@router.message(Command("help"))
async def cmd_help(message: Message):
    lg = lang_key(getattr(message.from_user, "language_code", ""))
    t = labels(lg)
    await message.answer(t["welcome"], reply_markup=main_kb(lg))

@router.message()
async def catch_all(message: Message):
    lg = lang_key(getattr(message.from_user, "language_code", ""))
    t = labels(lg)
    txt = (message.text or "").strip()
    if txt == t["order"]:
        await message.answer(t["order_text"])
    elif txt == t["info"]:
        await message.answer(t["info_text"])
    elif txt == t["support"]:
        await message.answer(t["support_text"])
    else:
        await message.answer(t["welcome"], reply_markup=main_kb(lg))

# ================== WEBHOOK (AIOHTTP) ==================
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
        log.info("Startup: python=%s aiogram=3.x aiohttp=%s AIOHTTP_NO_EXTENSIONS=%s",
                 sys.version.split()[0], aiohttp.__version__, os.getenv("AIOHTTP_NO_EXTENSIONS"))
    except Exception:
        pass
    if WEBHOOK_URL:
        await bot.set_webhook(WEBHOOK_URL, drop_pending_updates=True)
        log.info("Webhook set to %s", WEBHOOK_URL)
    else:
        log.warning("WEBHOOK_BASE not set; open /setwebhook after setting it.")

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
    app.router.add_get("/setwebhook", set_webhook_handler)  # optional
    app.on_startup.append(on_startup)
    app.on_shutdown.append(on_shutdown)
    return app

if __name__ == "__main__":
    web.run_app(create_app(), host=HOST, port=PORT)
