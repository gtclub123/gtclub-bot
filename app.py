import os
import logging
from aiohttp import web
from aiogram import Bot, Dispatcher, types
from aiogram.utils.executor import set_webhook

API_TOKEN = os.getenv("TELEGRAM_TOKEN")
WEBHOOK_BASE = os.getenv("WEBHOOK_BASE")
WEBHOOK_PATH = "/webhook"
WEBHOOK_URL = f"{WEBHOOK_BASE}{WEBHOOK_PATH}"

HOST = "0.0.0.0"
PORT = int(os.getenv("PORT", "8080"))

logging.basicConfig(level=logging.INFO)

bot = Bot(token=API_TOKEN, parse_mode="HTML")
dp = Dispatcher(bot)

def lang_key(user: types.User) -> str:
    lc = (user.language_code or "").lower()
    if lc.startswith("uk"):
        return "uk"
    if lc.startswith("en"):
        return "en"
    return "ru"

TEXTS = {
    "ru": {
        "welcome": "👋 Добро пожаловать в <b>GTClub File Service</b>!\n⚡ Профессиональные чип-тюнинг файлы (Stage 1–3, DPF/EGR/AdBlue OFF и др.).\n📂 Отправьте файл прошивки и получите готовое решение в кратчайшие сроки.",
        "menu": "Выберите действие:",
        "btn_upload": "📤 Отправить файл",
        "btn_services": "🧰 Услуги",
        "btn_support": "👨‍💻 Поддержка",
        "how_upload": "Пришлите <b>файл прошивки</b> как документ (не фото). Укажите:\n• Блок/ПО (ECU, SW)\n• Услуги (Stage, DPF/EGR/AdBlue OFF и т.д.)\n• Пожелания/заметки",
        "services": "🧰 <b>Услуги</b>:\n• Stage 1–3 (индивидуальные калибровки)\n• DPF/FAP OFF, EGR OFF, AdBlue/SCR OFF\n• Vmax OFF, Pop&Bang, Decat, O2/Lambda OFF\n• Иммо OFF, DTC off (по списку)\n• Проверка и правки ваших файлов",
        "support": "👨‍💻 <b>Поддержка</b>:\n• Telegram: @gtclub\n• Email: gtclub.com.ua@gmail.com",
        "got_file": "✅ Файл получен. Наш инженер возьмёт в работу и свяжется с вами в личных сообщениях.",
        "not_doc": "Пожалуйста, отправьте файл как <b>документ</b> (скрепка)."
    },
    "uk": {
        "welcome": "👋 Ласкаво просимо до <b>GTClub File Service</b>!\n⚡ Професійні чіп-тюнінг файли (Stage 1–3, DPF/EGR/AdBlue OFF та ін.).\n📂 Надішліть файл прошивки та отримайте готове рішення у найкоротші терміни.",
        "menu": "Оберіть дію:",
        "btn_upload": "📤 Надіслати файл",
        "btn_services": "🧰 Послуги",
        "btn_support": "👨‍💻 Підтримка",
        "how_upload": "Надішліть <b>файл прошивки</b> як документ (не фото). Вкажіть:\n• Блок/ПО (ECU, SW)\n• Послуги (Stage, DPF/EGR/AdBlue OFF тощо)\n• Побажання/нотатки",
        "services": "🧰 <b>Послуги</b>:\n• Stage 1–3 (індивідуальні калібрування)\n• DPF/FAP OFF, EGR OFF, AdBlue/SCR OFF\n• Vmax OFF, Pop&Bang, Decat, O2/Lambda OFF\n• Immo OFF, DTC off (за списком)\n• Перевірка та правки ваших файлів",
        "support": "👨‍💻 <b>Підтримка</b>:\n• Telegram: @gtclub\n• Email: gtclub.com.ua@gmail.com",
        "got_file": "✅ Файл отримано. Інженер розпочне роботу та зв'яжеться з вами у приватних повідомленнях.",
        "not_doc": "Будь ласка, надішліть файл як <b>документ</b> (скріпка)."
    },
    "en": {
        "welcome": "👋 Welcome to <b>GTClub File Service</b>!\n⚡ Professional chiptuning files (Stage 1–3, DPF/EGR/AdBlue OFF and more).\n📂 Upload your ECU file and get a ready-to-use solution in no time.",
        "menu": "Choose an option:",
        "btn_upload": "📤 Upload file",
        "btn_services": "🧰 Services",
        "btn_support": "👨‍💻 Support",
        "how_upload": "Please send the <b>original ECU file</b> as a document (not a photo). Include:\n• ECU/SW info\n• Required services (Stage, DPF/EGR/AdBlue OFF, etc.)\n• Notes / requests",
        "services": "🧰 <b>Services</b>:\n• Stage 1–3 (custom calibrations)\n• DPF/FAP OFF, EGR OFF, AdBlue/SCR OFF\n• Vmax OFF, Pop&Bang, Decat, O2/Lambda OFF\n• Immo OFF, DTC off (per list)\n• File review & corrections",
        "support": "👨‍💻 <b>Support</b>:\n• Telegram: @gtclub\n• Email: gtclub.com.ua@gmail.com",
        "got_file": "✅ File received. Our engineer will start and contact you in DM.",
        "not_doc": "Please upload the file as a <b>document</b> (paperclip)."
    }
}

from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton, ReplyKeyboardMarkup, KeyboardButton

def menu_kb(lang: str) -> InlineKeyboardMarkup:
    t = TEXTS[lang]
    kb = InlineKeyboardMarkup(row_width=2)
    kb.add(
        InlineKeyboardButton(t["btn_upload"], callback_data="upload"),
        InlineKeyboardButton(t["btn_services"], callback_data="services"),
    )
    kb.add(InlineKeyboardButton(t["btn_support"], callback_data="support"))
    return kb

def reply_upload_kb(lang: str) -> ReplyKeyboardMarkup:
    t = TEXTS[lang]
    kb = ReplyKeyboardMarkup(resize_keyboard=True, selective=True)
    kb.add(KeyboardButton(t["btn_upload"]))
    return kb

@dp.message_handler(commands=["start", "help"])
async def cmd_start(message: types.Message):
    lg = lang_key(message.from_user)
    t = TEXTS[lg]
    await message.answer(t["welcome"])
    await message.answer(t["menu"], reply_markup=menu_kb(lg))

@dp.callback_query_handler(lambda c: c.data in {"upload", "services", "support"})
async def on_menu_click(call: types.CallbackQuery):
    lg = lang_key(call.from_user)
    t = TEXTS[lg]
    if call.data == "upload":
        await call.message.answer(t["how_upload"], reply_markup=reply_upload_kb(lg))
    elif call.data == "services":
        await call.message.answer(t["services"])
    elif call.data == "support":
        await call.message.answer(t["support"])
    await call.answer()

@dp.message_handler(lambda m: m.text in (
    TEXTS["ru"]["btn_upload"], TEXTS["uk"]["btn_upload"], TEXTS["en"]["btn_upload"]
))
async def on_upload_button_text(message: types.Message):
    lg = lang_key(message.from_user)
    t = TEXTS[lg]
    await message.answer(t["how_upload"])

@dp.message_handler(content_types=types.ContentTypes.DOCUMENT)
async def on_document(message: types.Message):
    lg = lang_key(message.from_user)
    t = TEXTS[lg]
    await message.reply(t["got_file"])

@dp.message_handler(content_types=types.ContentTypes.PHOTO)
async def on_photo(message: types.Message):
    lg = lang_key(message.from_user)
    t = TEXTS[lg]
    await message.reply(t["not_doc"])

@dp.message_handler(content_types=types.ContentTypes.TEXT)
async def on_text(message: types.Message):
    lg = lang_key(message.from_user)
    t = TEXTS[lg]
    await message.answer(t["menu"], reply_markup=menu_kb(lg))

async def on_startup(app: web.Application):
    logging.info("Setting webhook: %s", WEBHOOK_URL)
    await set_webhook(dp, WEBHOOK_URL)

async def on_shutdown(app: web.Application):
    logging.info("Deleting webhook")
    await bot.delete_webhook()

async def handle_webhook(request: web.Request):
    data = await request.json()
    update = types.Update.to_object(data)
    await dp.process_update(update)
    return web.Response(text="ok")

async def healthcheck(request: web.Request):
    return web.Response(text="ok")

def create_app():
    if not API_TOKEN:
        raise RuntimeError("TELEGRAM_TOKEN env var is not set")
    if not WEBHOOK_BASE or not WEBHOOK_BASE.startswith("http"):
        raise RuntimeError("WEBHOOK_BASE env var must be like https://your-app.onrender.com")
    app = web.Application()
    app.router.add_post(WEBHOOK_PATH, handle_webhook)
    app.router.add_get("/healthz", healthcheck)
    app.on_startup.append(on_startup)
    app.on_shutdown.append(on_shutdown)
    return app

if __name__ == "__main__":
    web.run_app(create_app(), host=HOST, port=PORT)
