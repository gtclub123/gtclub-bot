import os
import sys
import logging
from typing import Dict, List, Any
from aiohttp import web

# ===== Logging =====
logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
log = logging.getLogger("gtclub-bot")

# ===== Global state =====
_bot = None
_dp = None
_router = None
_startup_error = None

# ===== Config =====
BOT_TOKEN = os.getenv("TELEGRAM_TOKEN") or os.getenv("BOT_TOKEN")
WEBHOOK_BASE = (os.getenv("WEBHOOK_BASE") or "").rstrip("/")
WEBHOOK_PATH = "/webhook"
WEBHOOK_URL = f"{WEBHOOK_BASE}{WEBHOOK_PATH}" if WEBHOOK_BASE else None
ADMIN_CHAT_ID = os.getenv("ADMIN_CHAT_ID")  # optional: where to send orders
HOST = "0.0.0.0"
PORT = int(os.getenv("PORT", 8080))

# ===== Sample reference data =====
BRANDS = ["BMW", "VAG", "Mercedes"]
MODELS: Dict[str, List[str]] = {
    "BMW": ["F10", "F30"],
    "VAG": ["Golf 7", "A3 8V"],
    "Mercedes": ["W205", "W213"],
}
YEARS: Dict[str, List[str]] = {
    "F10": ["2010", "2011", "2012"],
    "F30": ["2012", "2013", "2014"],
    "Golf 7": ["2013", "2014"],
    "A3 8V": ["2013", "2014"],
    "W205": ["2014", "2015"],
    "W213": ["2016", "2017"],
}
ENGINES: Dict[str, List[str]] = {
    "F10": ["2.0d", "3.0d"],
    "F30": ["2.0i", "2.0d"],
    "Golf 7": ["1.4 TSI", "2.0 TDI"],
    "A3 8V": ["1.8 TFSI", "2.0 TDI"],
    "W205": ["2.0t", "2.2d"],
    "W213": ["2.0d", "3.0d"],
}
OPTIONS = [
    "Stage 1", "Stage 2", "Stage 3",
    "DPF OFF", "EGR OFF", "AdBlue OFF"
]

# ===== I18N =====
def lang_key(code: str) -> str:
    c = (code or "").lower()
    if c.startswith("uk"): return "uk"
    if c.startswith("en"): return "en"
    return "ru"

T = {
    "ru": {
        "welcome": "👋 Добро пожаловать в GTClub File Service!\nНажмите «Начать заказ».",
        "start_order": "📝 Начать заказ",
        "choose_brand": "Выберите марку авто:",
        "choose_model": "Выберите модель:",
        "choose_year": "Выберите год выпуска:",
        "choose_engine": "Выберите двигатель:",
        "choose_options": "Выберите опции:",
        "done": "✅ Готово",
        "cancel": "❌ Отменить",
        "upload_file": "📂 Пришлите файл прошивки как документ.",
        "bad_file": "Отправьте файл именно как документ (не фото).",
        "summary": "Проверьте данные и подтвердите заявку:",
        "confirm": "✅ Подтвердить",
        "cancelled": "❌ Заказ отменен.",
        "thanks": "✅ Заявка отправлена. Инженер свяжется с вами."
    },
    "uk": {
        "welcome": "👋 Ласкаво просимо до GTClub File Service!\nНатисніть «Почати замовлення».",
        "start_order": "📝 Почати замовлення",
        "choose_brand": "Оберіть марку авто:",
        "choose_model": "Оберіть модель:",
        "choose_year": "Оберіть рік випуску:",
        "choose_engine": "Оберіть двигун:",
        "choose_options": "Оберіть опції:",
        "done": "✅ Готово",
        "cancel": "❌ Скасувати",
        "upload_file": "📂 Надішліть файл прошивки як документ.",
        "bad_file": "Будь ласка, надішліть файл саме як документ (не фото).",
        "summary": "Перевірте дані та підтвердіть заявку:",
        "confirm": "✅ Підтвердити",
        "cancelled": "❌ Замовлення скасовано.",
        "thanks": "✅ Заявку надіслано. Інженер зв'яжеться з вами."
    },
    "en": {
        "welcome": "👋 Welcome to GTClub File Service!\nTap “Start order”.",
        "start_order": "📝 Start order",
        "choose_brand": "Choose car brand:",
        "choose_model": "Choose model:",
        "choose_year": "Choose model year:",
        "choose_engine": "Choose engine:",
        "choose_options": "Choose options:",
        "done": "✅ Done",
        "cancel": "❌ Cancel",
        "upload_file": "📂 Please send the ECU file as a document.",
        "bad_file": "Please upload the file as a document (not photo).",
        "summary": "Review and confirm:",
        "confirm": "✅ Confirm",
        "cancelled": "❌ Cancelled.",
        "thanks": "✅ Request sent. Engineer will contact you."
    }
}
def tr(lang, key): return T[lang].get(key, key)

# ===== Handlers =====
def install_handlers(router):
    from aiogram import F
    from aiogram.types import Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton, Document
    from aiogram.filters import CommandStart
    from aiogram.fsm.state import StatesGroup, State
    from aiogram.fsm.context import FSMContext

    class Order(StatesGroup):
        BRAND = State()
        MODEL = State()
        YEAR = State()
        ENGINE = State()
        OPTIONS = State()
        FILE = State()
        CONFIRM = State()

    def ikb(items, prefix): 
        return InlineKeyboardMarkup(
            inline_keyboard=[[InlineKeyboardButton(text=i, callback_data=f"{prefix}:{i}")] for i in items]
        )

    @router.message(CommandStart())
    async def cmd_start(message: Message, state: FSMContext):
        lg = lang_key(message.from_user.language_code or "")
        await state.clear()
        kb = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text=tr(lg, "start_order"), callback_data="start_order")]
        ])
        await message.answer(tr(lg, "welcome"), reply_markup=kb)

    @router.callback_query(F.data == "start_order")
    async def cb_start_order(cb, state: FSMContext):
        lg = lang_key(cb.from_user.language_code or "")
        await state.set_state(Order.BRAND)
        await cb.message.edit_text(tr(lg, "choose_brand"), reply_markup=ikb(BRANDS, "brand"))
        await cb.answer()

    @router.callback_query(F.data.startswith("brand:"))
    async def cb_brand(cb, state: FSMContext):
        brand = cb.data.split(":",1)[1]
        await state.update_data(brand=brand)
        lg = lang_key(cb.from_user.language_code or "")
        await state.set_state(Order.MODEL)
        await cb.message.edit_text(tr(lg, "choose_model"), reply_markup=ikb(MODELS[brand], "model"))
        await cb.answer()

    # аналогично для model -> year -> engine -> options -> file -> confirm...
    # (сократил ради примера, логику ты видел выше в полной версии)

# ===== Web endpoints =====
async def handle_webhook(request: web.Request):
    global _dp, _bot, _startup_error
    if _startup_error:
        return web.Response(status=503, text=f"bot not ready: { _startup_error }")
    from aiogram.types import Update
    data = await request.json()
    update = Update(**data)
    await _dp.feed_update(_bot, update)
    return web.Response(text="ok")

async def healthcheck(request: web.Request):
    return web.Response(text="ok" if _startup_error is None else f"degraded: { _startup_error }")

async def root(request: web.Request):
    return web.Response(text="gtclub-bot ok")

async def diag(request: web.Request):
    info = {
        "python": sys.version.split()[0],
        "WEBHOOK_URL": WEBHOOK_URL,
        "has_token": bool(BOT_TOKEN),
        "startup_error": str(_startup_error) if _startup_error else None,
    }
    return web.json_response(info)

async def set_webhook_handler(request: web.Request):
    global _bot, _startup_error
    if _startup_error:
        return web.Response(status=503, text=f"bot not ready: { _startup_error }")
    if not WEBHOOK_URL:
        return web.Response(status=400, text="WEBHOOK_BASE is not set")
    await _bot.set_webhook(WEBHOOK_URL, drop_pending_updates=True)
    log.info("Webhook set to %s", WEBHOOK_URL)
    return web.Response(text=f"Webhook set to {WEBHOOK_URL}")

# ===== Lifecycle =====
async def on_startup(app: web.Application):
    global _bot, _dp, _router, _startup_error
    try:
        if not BOT_TOKEN:
            raise RuntimeError("Missing TELEGRAM_TOKEN/BOT_TOKEN")
        from aiogram import Bot, Dispatcher, Router
        from aiogram.fsm.storage.memory import MemoryStorage
        from aiogram.client.default import DefaultBotProperties
