import os
import sys
import logging
from typing import Dict, Any, List

from aiohttp import web
from aiogram import Bot, Dispatcher, Router, F
from aiogram.types import Message, Update, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton, Document
from aiogram.fsm.context import FSMContext
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.fsm.state import StatesGroup, State
from aiogram.filters import CommandStart, Command

# ================== CONFIG ==================
logging.basicConfig(level=logging.INFO)
log = logging.getLogger("gtclub-bot")

BOT_TOKEN = os.getenv("TELEGRAM_TOKEN") or os.getenv("BOT_TOKEN")
if not BOT_TOKEN:
    raise ValueError("BOT_TOKEN/TELEGRAM_TOKEN is not set")

WEBHOOK_BASE = (os.getenv("WEBHOOK_BASE") or "").rstrip("/")
WEBHOOK_PATH = "/webhook"
WEBHOOK_URL = f"{WEBHOOK_BASE}{WEBHOOK_PATH}" if WEBHOOK_BASE else None

ADMIN_CHAT_ID = os.getenv("ADMIN_CHAT_ID")  # "-100..." или "123..."
HOST = "0.0.0.0"
PORT = int(os.getenv("PORT", 8080))

# ================== BOT CORE ==================
bot = Bot(token=BOT_TOKEN, parse_mode="HTML")
dp = Dispatcher(storage=MemoryStorage())
router = Router()
dp.include_router(router)

# ================== DATA (примерные справочники) ==================
BRANDS = ["BMW", "VAG", "Mercedes", "Ford", "Toyota"]
MODELS: Dict[str, List[str]] = {
    "BMW": ["F10", "F30", "G20"],
    "VAG": ["Golf 7", "A3 8V", "A4 B9"],
    "Mercedes": ["W205", "W213"],
    "Ford": ["Focus 3", "Mondeo 5"],
    "Toyota": ["Camry V70", "RAV4 XA50"],
}
ENGINES: Dict[str, List[str]] = {
    "F10": ["2.0d N47", "3.0d N57"],
    "F30": ["2.0d B47", "2.0i N20"],
    "G20": ["2.0d B47", "3.0i B58"],
    "Golf 7": ["1.4 TSI", "2.0 TDI"],
    "A3 8V": ["1.8 TFSI", "2.0 TDI"],
    "A4 B9": ["2.0 TFSI", "2.0 TDI"],
    "W205": ["2.0t M274", "2.2d OM651"],
    "W213": ["2.0d OM654", "3.0d OM656"],
    "Focus 3": ["1.6 Ti", "2.0 TDCi"],
    "Mondeo 5": ["2.0 EcoBoost", "2.0 TDCi"],
    "Camry V70": ["2.5 A25A", "3.5 V6 2GR"],
    "RAV4 XA50": ["2.0 M20A", "2.5 A25A"],
}
SERVICES = [
    "Stage 1", "Stage 2", "Stage 3",
    "DPF/FAP OFF", "EGR OFF", "AdBlue/SCR OFF",
    "Vmax OFF", "Pop&Bang", "O2/Lambda OFF", "DTC off"
]

# ================== I18N TEXTS ==================
def lang_key(user_lang: str) -> str:
    lc = (user_lang or "").lower()
    if lc.startswith("uk"):
        return "uk"
    if lc.startswith("en"):
        return "en"
    return "ru"

T = {
    "ru": {
        "welcome": "👋 Добро пожаловать в <b>GTClub File Service</b>!\nНажмите «Начать заказ», чтобы оформить заявку.",
        "start_order": "📝 Начать заказ",
        "choose_brand": "Выберите марку авто:",
        "choose_model": "Выберите модель:",
        "choose_engine": "Выберите двигатель:",
        "choose_services": "Выберите услуги (можно несколько):",
        "done_services": "✅ Готово",
        "upload_file": "📂 Пришлите файл прошивки как <b>документ</b> (иконка скрепки).",
        "confirm": "Проверьте данные и подтвердите заявку:",
        "confirm_btn": "✅ Подтвердить",
        "cancel_btn": "❌ Отменить",
        "thank_you": "✅ Заявка отправлена. Инженер свяжется с вами.",
        "bad_file": "Пожалуйста, отправьте файл как <b>документ</b>.",
        "menu": "Главное меню:",
        "cancelled": "❌ Заказ отменен.",
        "help": "Команды:\n/start — меню\n/order — начать заказ\n/cancel — отменить",
        "order_btn": "🛒 Оформить заказ"
    },
    "uk": {
        "welcome": "👋 Ласкаво просимо до <b>GTClub File Service</b>!\nНатисніть «Почати замовлення», щоб оформити заявку.",
        "start_order": "📝 Почати замовлення",
        "choose_brand": "Оберіть марку авто:",
        "choose_model": "Оберіть модель:",
        "choose_engine": "Оберіть двигун:",
        "choose_services": "Оберіть послуги (можна кілька):",
        "done_services": "✅ Готово",
        "upload_file": "📂 Надішліть файл прошивки як <b>документ</b> (скріпка).",
        "confirm": "Перевірте дані та підтвердіть заявку:",
        "confirm_btn": "✅ Підтвердити",
        "cancel_btn": "❌ Скасувати",
        "thank_you": "✅ Заявку надіслано. Інженер зв'яжеться з вами.",
        "bad_file": "Будь ласка, надішліть файл як <b>документ</b>.",
        "menu": "Головне меню:",
        "cancelled": "❌ Замовлення скасовано.",
        "help": "Команди:\n/start — меню\n/order — почати замовлення\n/cancel — скасувати",
        "order_btn": "🛒 Оформити замовлення"
    },
    "en": {
        "welcome": "👋 Welcome to <b>GTClub File Service</b>!\nTap “Start order” to create a request.",
        "start_order": "📝 Start order",
        "choose_brand": "Choose car brand:",
        "choose_model": "Choose model:",
        "choose_engine": "Choose engine:",
        "choose_services": "Choose services (you can select multiple):",
        "done_services": "✅ Done",
        "upload_file": "📂 Please send the ECU file as a <b>document</b> (paperclip).",
        "confirm": "Review details and confirm the request:",
        "confirm_btn": "✅ Confirm",
        "cancel_btn": "❌ Cancel",
        "thank_you": "✅ Request sent. Our engineer will contact you.",
        "bad_file": "Please upload the file as a <b>document</b>.",
        "menu": "Main menu:",
        "cancelled": "❌ Order cancelled.",
        "help": "Commands:\n/start — menu\n/order — start order\n/cancel — cancel",
        "order_btn": "🛒 Place order"
    }
}

def tr(lang: str, key: str) -> str:
    return T[lang].get(key, key)

# ================== FSM ==================
class Order(StatesGroup):
    BRAND = State()
    MODEL = State()
    ENGINE = State()
    SERVICES = State()
    FILE = State()
    CONFIRM = State()

# ================== KEYBOARDS ==================
def ikb_brands(lang: str) -> InlineKeyboardMarkup:
    buttons = [[InlineKeyboardButton(text=b, callback_data=f"brand:{b}")] for b in BRANDS]
    return InlineKeyboardMarkup(inline_keyboard=buttons)

def ikb_models(lang: str, brand: str) -> InlineKeyboardMarkup:
    models = MODELS.get(brand, [])
    buttons = [[InlineKeyboardButton(text=m, callback_data=f"model:{m}")] for m in models]
    return InlineKeyboardMarkup(inline_keyboard=buttons or [[InlineKeyboardButton(text="—", callback_data="noop")]])

def ikb_engines(lang: str, model: str) -> InlineKeyboardMarkup:
    engines = ENGINES.get(model, [])
    buttons = [[InlineKeyboardButton(text=e, callback_data=f"engine:{e}")] for e in engines]
    return InlineKeyboardMarkup(inline_keyboard=buttons or [[InlineKeyboardButton(text="—", callback_data="noop")]])

def ikb_services(lang: str, chosen: List[str]) -> InlineKeyboardMarkup:
    rows = []
    for s in SERVICES:
        mark = "✅ " if s in chosen else ""
        rows.append([InlineKeyboardButton(text=f"{mark}{s}", callback_data=f"svc:{s}")])
    rows.append([InlineKeyboardButton(text=tr(lang, "done_services"), callback_data="svc_done")])
    rows.append([InlineKeyboardButton(text=tr(lang, "cancel_btn"), callback_data="cancel")])
    return InlineKeyboardMarkup(inline_keyboard=rows)

def ikb_start(lang: str) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[[
        InlineKeyboardButton(text=tr(lang, "start_order"), callback_data="start_order")
    ]])

def ikb_confirm(lang: str) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[[
        InlineKeyboardButton(text=tr(lang, "confirm_btn"), callback_data="confirm"),
        InlineKeyboardButton(text=tr(lang, "cancel_btn"), callback_data="cancel")
    ]])

# ================== HELPERS ==================
def user_lang(message: Message) -> str:
    return lang_key(getattr(message.from_user, "language_code", ""))

def format_summary(lang: str, data: Dict[str, Any]) -> str:
    lines = []
    lines.append(f"<b>Brand:</b> {data.get('brand')}")
    lines.append(f"<b>Model:</b> {data.get('model')}")
    lines.append(f"<b>Engine:</b> {data.get('engine')}")
    lines.append(f"<b>Services:</b> {', '.join(data.get('services', [])) or '—'}")
    doc = data.get("file")
    if doc:
        lines.append(f"<b>File:</b> {doc.file_name} ({doc.file_id})")
    return "\n".join(lines)

async def send_to_admin(data: Dict[str, Any], user: Message):
    if not ADMIN_CHAT_ID:
        return
    try:
        txt = "🔔 <b>New tuning request</b>\n" + format_summary("en", data)  # админский фид можно держать на EN
        await bot.send_message(int(ADMIN_CHAT_ID), txt)
        if data.get("file"):
            await bot.send_document(int(ADMIN_CHAT_ID), data["file"].file_id, caption="Client file")
        # контакт клиента
        await bot.send_message(int(ADMIN_CHAT_ID), f"Client: @{user.from_user.username or user.from_user.id}")
    except Exception as e:
        log.warning("Failed to notify admin: %s", e)

# ================== COMMANDS ==================
@router.message(CommandStart())
async def cmd_start(message: Message, state: FSMContext):
    lang = user_lang(message)
    await state.clear()
    await message.answer(tr(lang, "welcome"), reply_markup=ikb_start(lang))

@router.message(Command("help"))
async def cmd_help(message: Message):
    lang = user_lang(message)
    await message.answer(tr(lang, "help"))

@router.message(Command("order"))
async def cmd_order(message: Message, state: FSMContext):
    lang = user_lang(message)
    await state.set_state(Order.BRAND)
    await state.update_data(services=[])
    await message.answer(tr(lang, "choose_brand"), reply_markup=ikb_brands(lang))

@router.message(Command("cancel"))
async def cmd_cancel(message: Message, state: FSMContext):
    lang = user_lang(message)
    await state.clear()
    await message.answer(tr(lang, "cancelled"), reply_markup=ikb_start(lang))

# ================== CALLBACK FLOW ==================
@router.callback_query(F.data == "start_order")
async def cb_start_order(cb: CallbackQuery, state: FSMContext):
    lang = lang_key(cb.from_user.language_code or "")
    await state.set_state(Order.BRAND)
    await state.update_data(services=[])
    await cb.message.edit_text(tr(lang, "choose_brand"), reply_markup=ikb_brands(lang))
    await cb.answer()

@router.callback_query(F.data.startswith("brand:"))
async def cb_brand(cb: CallbackQuery, state: FSMContext):
    lang = lang_key(cb.from_user.language_code or "")
    brand = cb.data.split(":", 1)[1]
    await state.update_data(brand=brand, model=None, engine=None)
    await state.set_state(Order.MODEL)
    await cb.message.edit_text(tr(lang, "choose_model"), reply_markup=ikb_models(lang, brand))
    await cb.answer()

@router.callback_query(F.data.startswith("model:"))
async def cb_model(cb: CallbackQuery, state: FSMContext):
    lang = lang_key(cb.from_user.language_code or "")
    model = cb.data.split(":", 1)[1]
    await state.update_data(model=model, engine=None)
    await state.set_state(Order.ENGINE)
    await cb.message.edit_text(tr(lang, "choose_engine"), reply_markup=ikb_engines(lang, model))
    await cb.answer()

@router.callback_query(F.data.startswith("engine:"))
async def cb_engine(cb: CallbackQuery, state: FSMContext):
    lang = lang_key(cb.from_user.language_code or "")
    engine = cb.data.split(":", 1)[1]
    await state.update_data(engine=engine)
    await state.set_state(Order.SERVICES)
    data = await state.get_data()
    await cb.message.edit_text(tr(lang, "choose_services"), reply_markup=ikb_services(lang, data.get("services", [])))
    await cb.answer()

@router.callback_query(F.data.startswith("svc:"))
async def cb_service_toggle(cb: CallbackQuery, state: FSMContext):
    lang = lang_key(cb.from_user.language_code or "")
    svc = cb.data.split(":", 1)[1]
    data = await state.get_data()
    chosen = set(data.get("services", []))
    if svc in chosen:
        chosen.remove(svc)
    else:
        chosen.add(svc)
    await state.update_data(services=list(chosen))
    await cb.message.edit_reply_markup(reply_markup=ikb_services(lang, list(chosen)))
    await cb.answer()

@router.callback_query(F.data == "svc_done")
async def cb_services_done(cb: CallbackQuery, state: FSMContext):
    lang = lang_key(cb.from_user.language_code or "")
    await state.set_state(Order.FILE)
    await cb.message.edit_text(tr(lang, "upload_file"))
    await cb.answer()

@router.callback_query(F.data == "cancel")
async def cb_cancel(cb: CallbackQuery, state: FSMContext):
    lang = lang_key(cb.from_user.language_code or "")
    await state.clear()
    await cb.message.edit_text(tr(lang, "cancelled"))
    await cb.answer()

# ================== FILE HANDLER ==================
@router.message(Order.FILE, F.document)
async def got_document(message: Message, state: FSMContext):
    lang = user_lang(message)
    doc: Document = message.document
    await state.update_data(file=doc)
    await state.set_state(Order.CONFIRM)
    data = await state.get_data()
    summary = tr(lang, "confirm") + "\n\n" + format_summary(lang, data)
    await message.answer(summary, reply_markup=ikb_confirm(lang))

@router.message(Order.FILE)
async def warn_document(message: Message, state: FSMContext):
    lang = user_lang(message)
    await message.answer(tr(lang, "bad_file"))

# ================== CONFIRM ==================
@router.callback_query(Order.CONFIRM, F.data == "confirm")
async def cb_confirm(cb: CallbackQuery, state: FSMContext):
    lang = lang_key(cb.from_user.language_code or "")
    data = await state.get_data()
    # отправка админу
    await send_to_admin(data, cb.message)
    await state.clear()
    await cb.message.edit_text(tr(lang, "thank_you"))
    await cb.answer()

# ================== WEBHOOK ==================
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
