import os
import sys
import logging
from typing import Dict, List, Any
from aiohttp import web

# ================= Logging =================
logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
log = logging.getLogger("gtclub-bot")

# ================= Config =================
BOT_TOKEN = os.getenv("TELEGRAM_TOKEN") or os.getenv("BOT_TOKEN")
WEBHOOK_BASE = (os.getenv("WEBHOOK_BASE") or "").rstrip("/")
WEBHOOK_PATH = "/webhook"
WEBHOOK_URL = f"{WEBHOOK_BASE}{WEBHOOK_PATH}" if WEBHOOK_BASE else None
ADMIN_CHAT_ID = os.getenv("ADMIN_CHAT_ID")  # опционально
HOST = "0.0.0.0"
PORT = int(os.getenv("PORT", 8080))

# ================= Globals =================
_bot = None
_dp = None
_router = None
_startup_error = None

# ================= Справочники =================
BRANDS = ["BMW", "VAG", "Mercedes", "Ford", "Toyota"]
MODELS: Dict[str, List[str]] = {
    "BMW": ["F10", "F30", "G20"],
    "VAG": ["Golf 7", "A3 8V", "A4 B9"],
    "Mercedes": ["W205", "W213"],
    "Ford": ["Focus 3", "Mondeo 5"],
    "Toyota": ["Camry V70", "RAV4 XA50"],
}
YEARS: Dict[str, List[str]] = {
    "F10": ["2010","2011","2012","2013","2014","2015","2016"],
    "F30": ["2012","2013","2014","2015","2016","2017","2018"],
    "G20": ["2019","2020","2021","2022","2023"],
    "Golf 7": ["2013","2014","2015","2016","2017","2018"],
    "A3 8V": ["2013","2014","2015","2016","2017","2018"],
    "A4 B9": ["2016","2017","2018","2019","2020"],
    "W205": ["2014","2015","2016","2017","2018"],
    "W213": ["2016","2017","2018","2019","2020"],
    "Focus 3": ["2011","2012","2013","2014","2015","2016","2017","2018"],
    "Mondeo 5": ["2014","2015","2016","2017","2018","2019"],
    "Camry V70": ["2018","2019","2020","2021","2022"],
    "RAV4 XA50": ["2019","2020","2021","2022"],
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
OPTIONS = [
    "Stage 1", "Stage 2", "Stage 3",
    "DPF/FAP OFF", "EGR OFF", "AdBlue/SCR OFF",
    "Vmax OFF", "Pop&Bang", "O2/Lambda OFF", "DTC off"
]

# ================= I18N =================
def _lang(code: str) -> str:
    c = (code or "").lower()
    if c.startswith("uk"): return "uk"
    if c.startswith("en"): return "en"
    return "ru"

TEXTS = {
    "ru": {
        "welcome": "👋 Добро пожаловать в <b>GTClub File Service</b>!\nНажмите «Начать заказ», чтобы оформить заявку.",
        "start_order": "📝 Начать заказ",
        "order": "📂 Сделать заказ",
        "info": "ℹ️ Информация",
        "support": "💬 Поддержка",
        "info_text": "Доступные услуги: Stage 1–3, DPF/EGR/AdBlue OFF, Vmax OFF, Pop&Bang и др.",
        "support_text": "Email: gtclub.com.ua@gmail.com",
        "choose_brand": "Выберите марку авто:",
        "choose_model": "Выберите модель:",
        "choose_year": "Выберите год выпуска:",
        "choose_engine": "Выберите двигатель:",
        "choose_options": "Выберите опции (можно несколько):",
        "done": "✅ Готово",
        "cancel": "❌ Отменить",
        "upload_file": "📂 Пришлите файл прошивки как <b>документ</b> (скрепка). Можно добавить комментарий текстом.",
        "bad_file": "Пожалуйста, отправьте файл именно как <b>документ</b> (не фото).",
        "summary": "Проверьте данные и подтвердите заявку:",
        "confirm": "✅ Подтвердить",
        "cancelled": "❌ Заказ отменен.",
        "thanks": "✅ Заявка отправлена. Инженер свяжется с вами.",
        "menu": "Главное меню:",
        "menu_btn": "Меню"
    },
    "uk": {
        "welcome": "👋 Ласкаво просимо до <b>GTClub File Service</b>!\nНатисніть «Почати замовлення», щоб оформити заявку.",
        "start_order": "📝 Почати замовлення",
        "order": "📂 Зробити замовлення",
        "info": "ℹ️ Інформація",
        "support": "💬 Підтримка",
        "info_text": "Доступні послуги: Stage 1–3, DPF/EGR/AdBlue OFF, Vmax OFF, Pop&Bang тощо.",
        "support_text": "Email: gtclub.com.ua@gmail.com",
        "choose_brand": "Оберіть марку авто:",
        "choose_model": "Оберіть модель:",
        "choose_year": "Оберіть рік випуску:",
        "choose_engine": "Оберіть двигун:",
        "choose_options": "Оберіть опції (можна декілька):",
        "done": "✅ Готово",
        "cancel": "❌ Скасувати",
        "upload_file": "📂 Надішліть файл прошивки як <b>документ</b> (скріпка). Можна додати коментар текстом.",
        "bad_file": "Будь ласка, надішліть файл саме як <b>документ</b> (не фото).",
        "summary": "Перевірте дані та підтвердіть заявку:",
        "confirm": "✅ Підтвердити",
        "cancelled": "❌ Замовлення скасовано.",
        "thanks": "✅ Заявку надіслано. Інженер зв'яжеться з вами.",
        "menu": "Головне меню:",
        "menu_btn": "Меню"
    },
    "en": {
        "welcome": "👋 Welcome to <b>GTClub File Service</b>!\nTap “Start order” to create a request.",
        "start_order": "📝 Start order",
        "order": "📂 Place order",
        "info": "ℹ️ Info",
        "support": "💬 Support",
        "info_text": "Services: Stage 1–3, DPF/EGR/AdBlue OFF, Vmax OFF, Pop&Bang and more.",
        "support_text": "Email: gtclub.com.ua@gmail.com",
        "choose_brand": "Choose car brand:",
        "choose_model": "Choose model:",
        "choose_year": "Choose model year:",
        "choose_engine": "Choose engine:",
        "choose_options": "Choose options (you can select multiple):",
        "done": "✅ Done",
        "cancel": "❌ Cancel",
        "upload_file": "📂 Please send the ECU file as a <b>document</b> (paperclip). You may add comments as text.",
        "bad_file": "Please upload the file as a <b>document</b> (not a photo).",
        "summary": "Review the details and confirm:",
        "confirm": "✅ Confirm",
        "cancelled": "❌ Order cancelled.",
        "thanks": "✅ Request sent. Our engineer will contact you.",
        "menu": "Main menu:",
        "menu_btn": "Menu"
    }
}
def tr(lg: str, key: str) -> str:
    return TEXTS[lg].get(key, key)

# ================= Handlers =================
def install_handlers(router):
    from aiogram import F
    from aiogram.types import (
        Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton,
        ReplyKeyboardMarkup, KeyboardButton
    )
    from aiogram.filters import CommandStart, Command
    from aiogram.fsm.state import StatesGroup, State
    from aiogram.fsm.context import FSMContext

    # Keyboards
    def main_kb(lg: str) -> ReplyKeyboardMarkup:
        return ReplyKeyboardMarkup(
            keyboard=[[KeyboardButton(text=tr(lg, "order"))],
                      [KeyboardButton(text=tr(lg, "info")), KeyboardButton(text=tr(lg, "support"))]],
            resize_keyboard=True
        )

    def ikb_start(lg: str) -> InlineKeyboardMarkup:
        return InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text=tr(lg, "start_order"), callback_data="start_order")]
        ])

    def ikb_brands() -> InlineKeyboardMarkup:
        return InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text=b, callback_data=f"brand:{b}")] for b in BRANDS
        ])

    def ikb_models(brand: str) -> InlineKeyboardMarkup:
        items = MODELS.get(brand, [])
        return InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text=m, callback_data=f"model:{m}")] for m in items
        ])

    def ikb_years(model: str) -> InlineKeyboardMarkup:
        items = YEARS.get(model, [])
        return InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text=y, callback_data=f"year:{y}")] for y in items
        ])

    def ikb_engines(model: str) -> InlineKeyboardMarkup:
        items = ENGINES.get(model, [])
        return InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text=e, callback_data=f"engine:{e}")] for e in items
        ])

    def ikb_options_kb(lg: str, chosen: List[str]) -> InlineKeyboardMarkup:
        rows = []
        for opt in OPTIONS:
            mark = "✅ " if opt in chosen else ""
            rows.append([InlineKeyboardButton(text=f"{mark}{opt}", callback_data=f"opt:{opt}")])
        rows.append([InlineKeyboardButton(text=tr(lg, "done"), callback_data="opt_done")])
        rows.append([InlineKeyboardButton(text=tr(lg, "cancel"), callback_data="cancel")])
        return InlineKeyboardMarkup(inline_keyboard=rows)

    def ikb_confirm(lg: str) -> InlineKeyboardMarkup:
        return InlineKeyboardMarkup(inline_keyboard=[[
            InlineKeyboardButton(text=tr(lg, "confirm"), callback_data="confirm"),
            InlineKeyboardButton(text=tr(lg, "cancel"), callback_data="cancel")
        ]])

    # FSM
    class Order(StatesGroup):
        BRAND = State()
        MODEL = State()
        YEAR = State()
        ENGINE = State()
        OPTIONS = State()
        FILE = State()
        CONFIRM = State()

    # Helpers
    def user_lang(obj) -> str:
        code = ""
        if hasattr(obj, "from_user") and obj.from_user:
            code = getattr(obj.from_user, "language_code", "") or ""
        elif hasattr(obj, "message") and obj.message and obj.message.from_user:
            code = getattr(obj.message.from_user, "language_code", "") or ""
        return _lang(code)

    def summary(lg: str, data: Dict[str, Any]) -> str:
        lines = [
            f"<b>Brand:</b> {data.get('brand') or '—'}",
            f"<b>Model:</b> {data.get('model') or '—'}",
            f"<b>Year:</b> {data.get('year') or '—'}",
            f"<b>Engine:</b> {data.get('engine') or '—'}",
            f"<b>Options:</b> {', '.join(data.get('options', [])) or '—'}",
        ]
        doc = data.get("file")
        if doc:
            lines.append(f"<b>File:</b> {getattr(doc, 'file_name', 'document')}")
        comment = data.get("comment")
        if comment:
            lines.append(f"<b>Comment:</b> {comment}")
        return tr(lg, "summary") + "\n\n" + "\n".join(lines)

    async def notify_admin(data: Dict[str, Any], msg: Message):
        if not ADMIN_CHAT_ID:
            return
        try:
            uid = int(ADMIN_CHAT_ID)
            await msg.bot.send_message(uid, "🔔 <b>New file-service request</b>\n" + summary("en", data))
            if data.get("file"):
                await msg.bot.send_document(uid, data["file"].file_id, caption="Client file")
            await msg.bot.send_message(uid, f"Client: @{msg.from_user.username or msg.from_user.id}")
        except Exception as e:
            logging.warning("notify_admin failed: %s", e)

    # Service ping
    @router.message(Command("ping"))
    async def ping_cmd(message: Message, state: FSMContext):
        await message.answer("pong")

    # Commands
    @router.message(CommandStart())
    async def cmd_start(message: Message, state: FSMContext):
        lg = user_lang(message)
        await state.clear()
        await message.answer(tr(lg, "welcome"), reply_markup=main_kb(lg))
        await message.answer(tr(lg, "menu"), reply_markup=ikb_start(lg))

    @router.message(Command("cancel"))
    async def cmd_cancel(message: Message, state: FSMContext):
        lg = user_lang(message)
        await state.clear()
        await message.answer(tr(lg, "cancelled"), reply_markup=main_kb(lg))

    # Reply-меню
    @router.message()
    async def on_text(message: Message, state: FSMContext):
        lg = user_lang(message)
        txt = (message.text or "").strip()
        if txt == tr(lg, "order"):
            await state.set_state(Order.BRAND)
            await state.update_data(options=[], comment=None, file=None)
            await message.answer(tr(lg, "choose_brand"), reply_markup=ikb_brands())
        elif txt == tr(lg, "info"):
            await message.answer(TEXTS[lg]["info_text"])
        elif txt == tr(lg, "support"):
            await message.answer(TEXTS[lg]["support_text"])

    # Inline flow
    @router.callback_query(F.data == "start_order")
    async def cb_start_order(cb: CallbackQuery, state: FSMContext):
        lg = user_lang(cb)
        await state.set_state(Order.BRAND)
        await state.update_data(options=[], comment=None, file=None)
        await cb.message.edit_text(tr(lg, "choose_brand"), reply_markup=ikb_brands())
        await cb.answer()

    @router.callback_query(F.data.startswith("brand:"))
    async def cb_brand(cb: CallbackQuery, state: FSMContext):
        lg = user_lang(cb)
        brand = cb.data.split(":", 1)[1]
        await state.update_data(brand=brand, model=None, year=None, engine=None)
        await state.set_state(Order.MODEL)
        await cb.message.edit_text(tr(lg, "choose_model"), reply_markup=ikb_models(brand))
        await cb.answer()

    @router.callback_query(F.data.startswith("model:"))
    async def cb_model(cb: CallbackQuery, state: FSMContext):
        lg = user_lang(cb)
        model = cb.data.split(":", 1)[1]
        await state.update_data(model=model, year=None, engine=None)
        await state.set_state(Order.YEAR)
        await cb.message.edit_text(tr(lg, "choose_year"), reply_markup=ikb_years(model))
        await cb.answer()

    @router.callback_query(F.data.startswith("year:"))
    async def cb_year(cb: CallbackQuery, state: FSMContext):
        lg = user_lang(cb)
        year = cb.data.split(":", 1)[1]
        await state.update_data(year=year, engine=None)
        await state.set_state(Order.ENGINE)
        data = await state.get_data()
        await cb.message.edit_text(tr(lg, "choose_engine"), reply_markup=ikb_engines(data.get("model")))
        await cb.answer()

    @router.callback_query(F.data.startswith("engine:"))
    async def cb_engine(cb: CallbackQuery, state: FSMContext):
        lg = user_lang(cb)
        engine = cb.data.split(":", 1)[1]
        await state.update_data(engine=engine)
        await state.set_state(Order.OPTIONS)
        data = await state.get_data()
        await cb.message.edit_text(tr(lg, "choose_options"), reply_markup=ikb_options_kb(lg, data.get("options", [])))
        await cb.answer()

    @router.callback_query(F.data.startswith("opt:"))
    async def cb_opt_toggle(cb: CallbackQuery, state: FSMContext):
        lg = user_lang(cb)
        opt = cb.data.split(":", 1)[1]
        data = await state.get_data()
        chosen = set(data.get("options", []))
        if opt in chosen: chosen.remove(opt)
        else: chosen.add(opt)
        chosen_list = sorted(list(chosen))
        await state.update_data(options=chosen_list)
        await cb.message.edit_reply_markup(reply_markup=ikb_options_kb(lg, chosen_list))
        await cb.answer()

    @router.callback_query(F.data == "opt_done")
    async def cb_opt_done(cb: CallbackQuery, state: FSMContext):
        lg = user_lang(cb)
        await state.set_state(Order.FILE)
        await cb.message.edit_text(tr(lg, "upload_file"))
        await cb.answer()

    @router.message(Order.FILE, F.document)
    async def on_document(message: Message, state: FSMContext):
        lg = user_lang(message)
        await state.update_data(file=message.document)
        await state.set_state(Order.CONFIRM)
        data = await state.get_data()
        await message.answer(summary(lg, data), reply_markup=ikb_confirm(lg))

    @router.message(Order.FILE)
    async def on_comment_or_wrongfile(message: Message, state: FSMContext):
        lg = user_lang(message)
        if message.text:
            await state.update_data(comment=message.text.strip())
            data = await state.get_data()
            await message.answer(summary(lg, data), reply_markup=ikb_confirm(lg))
        else:
            await message.answer(tr(lg, "bad_file"))

    @router.callback_query(F.data == "confirm")
    async def cb_confirm(cb: CallbackQuery, state: FSMContext):
        lg = user_lang(cb)
        data = await state.get_data()
        await notify_admin(data, cb.message)
        await state.clear()
        await cb.message.edit_text(tr(lg, "thanks"))
        await cb.answer()

# ================= HTTP Handlers =================
async def handle_webhook(request: web.Request):
    """Приём апдейтов от Telegram + подробные логи."""
    global _dp, _bot, _startup_error
    if _startup_error:
        logging.error("Webhook hit while startup_error: %s", _startup_error)
        return web.Response(status=503, text=f"bot not ready: { _startup_error }")
    try:
        body = await request.text()
        logging.info("Webhook RAW body: %s", body[:2000])
        from aiogram.types import Update
        update = Update.model_validate_json(body)
        await _dp.feed_update(_bot, update)
        return web.Response(text="ok")
    except Exception as e:
        logging.exception("Webhook handler failed: %s", e)
        return web.Response(status=200, text="ok")  # 200, чтобы TG не ретраил

async def root(request: web.Request):
    return web.Response(text="gtclub-bot ok")

async def healthcheck(request: web.Request):
    return web.Response(text="ok" if _startup_error is None else f"degraded: { _startup_error }")

async def diag(request: web.Request):
    try:
        import aiohttp
        aiohttp_version = aiohttp.__version__
    except Exception:
        aiohttp_version = "unknown"
    info = {
        "python": sys.version.split()[0],
        "WEBHOOK_URL": WEBHOOK_URL,
        "has_token": bool(BOT_TOKEN),
        "startup_error": str(_startup_error) if _startup_error else None,
        "aiohttp": aiohttp_version,
        "admin_chat_id": ADMIN_CHAT_ID,
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

# ---- Диагностика: TG ping, webhook info, локальная симуляция /start ----
async def tg_ping(request: web.Request):
    global _bot
    chat_id = request.query.get("chat_id") or os.getenv("ADMIN_CHAT_ID")
    if not chat_id:
        return web.Response(status=400, text="pass ?chat_id=<id> or set ADMIN_CHAT_ID")
    try:
        await _bot.send_message(int(chat_id), "🔧 ping from server (outbound OK)")
        return web.Response(text=f"sent to {chat_id}")
    except Exception as e:
        logging.exception("tg_ping failed: %s", e)
        return web.Response(status=500, text=f"send failed: {e}")

async def tg_webhook_info(request: web.Request):
    global _bot
    try:
        info = await _bot.get_webhook_info()
        data = {
            "url": info.url,
            "has_custom_certificate": info.has_custom_certificate,
            "pending_update_count": info.pending_update_count,
            "ip_address": getattr(info, "ip_address", None),
            "last_error_message": getattr(info, "last_error_message", None),
            "last_error_date": getattr(info, "last_error_date", None),
            "max_connections": getattr(info, "max_connections", None),
        }
        return web.json_response(data)
    except Exception as e:
        logging.exception("tg_webhook_info failed: %s", e)
        return web.Response(status=500, text=str(e))

async def test_update(request: web.Request):
    """Локальная симуляция апдейта /start на ADMIN_CHAT_ID."""
    global _dp, _bot
    from aiogram.types import Update
    cid = int(os.getenv("ADMIN_CHAT_ID", "0"))
    if not cid:
        return web.Response(status=400, text="Set ADMIN_CHAT_ID to use /test-update")
    body = {
        "update_id": 999999,
        "message": {
            "message_id": 1,
            "date": 0,
            "chat": {"id": cid, "type": "private"},
            "text": "/start",
            "from": {"id": cid, "is_bot": False, "language_code": "ru"}
        }
    }
    try:
        update = Update.model_validate(body)
        await _dp.feed_update(_bot, update)
        return web.Response(text=f"fed /start to chat {cid}")
    except Exception as e:
        logging.exception("test_update failed: %s", e)
        return web.Response(status=500, text=str(e))

# ================= Lifecycle =================
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
    app.router.add_get("/", root)
    app.router.add_get("/healthz", healthcheck)
    app.router.add_get("/diag", diag)
    app.router.add_get("/setwebhook", set_webhook_handler)
    app.router.add_get("/tg/ping", tg_ping)
    app.router.add_get("/tg/webhookinfo", tg_webhook_info)
    app.router.add_get("/test-update", test_update)
    app.router.add_post(WEBHOOK_PATH, handle_webhook)
    app.on_startup.append(on_startup)
    app.on_shutdown.append(on_shutdown)
    return app

if __name__ == "__main__":
    web.run_app(create_app(), host=HOST, port=PORT)
