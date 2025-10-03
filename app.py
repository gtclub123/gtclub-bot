import os
import json
import re
import logging
from typing import Dict, Any, List

from fastapi import FastAPI, Request, HTTPException
from fastapi.responses import PlainTextResponse
from dotenv import load_dotenv

# -------------------- ENV & LOGGING --------------------
load_dotenv()
logging.basicConfig(level=logging.INFO)
log = logging.getLogger("gtclub-bot")

TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")
ADMIN_CHAT_ID = os.getenv("ADMIN_CHAT_ID")
WEBHOOK_BASE = os.getenv("WEBHOOK_BASE")
RENDER_EXTERNAL_URL = os.getenv("RENDER_EXTERNAL_URL")
DEBUG = os.getenv("DEBUG", "0") == "1"

if not TELEGRAM_TOKEN:
    raise RuntimeError("Missing TELEGRAM_TOKEN env var")

WEBHOOK_BASE = WEBHOOK_BASE or RENDER_EXTERNAL_URL
if WEBHOOK_BASE and not WEBHOOK_BASE.startswith("http"):
    WEBHOOK_BASE = None

WEBHOOK_PATH = f"/webhook/{TELEGRAM_TOKEN}"
WEBHOOK_URL = (WEBHOOK_BASE + WEBHOOK_PATH) if WEBHOOK_BASE else None

# -------------------- AIOGRAM 3.7+ --------------------
from aiogram import Bot, Dispatcher, types
from aiogram.client.default import DefaultBotProperties
from aiogram.types import Update, ReplyKeyboardMarkup, KeyboardButton

bot = Bot(token=TELEGRAM_TOKEN, default=DefaultBotProperties(parse_mode="HTML"))
dp = Dispatcher()

# -------------------- FLOW --------------------
with open(os.path.join(os.path.dirname(__file__), "flow.json"), "r", encoding="utf-8") as f:
    FLOW: Dict[str, Any] = json.load(f)

FLOW_STATES = FLOW["flow"]
AUTOMATIONS = FLOW.get("automations", {})

# -------------------- STATE --------------------
USER_STATE: Dict[int, Dict[str, Any]] = {}

def get_user(chat_id: int) -> Dict[str, Any]:
    if chat_id not in USER_STATE:
        USER_STATE[chat_id] = {"state": "start", "data": {}, "consent": True, "dnd": False}
    return USER_STATE[chat_id]

def save_field(data: Dict[str, Any], field_path: str, value: Any):
    keys = field_path.split(".")
    cur = data
    for k in keys[:-1]:
        if k not in cur or not isinstance(cur[k], dict):
            cur[k] = {}
        cur = cur[k]
    cur[keys[-1]] = value

def build_keyboard(layout: List[List[Dict[str, Any]]]) -> ReplyKeyboardMarkup:
    rows = []
    for row in layout:
        buttons = [KeyboardButton(text=item["text"]) for item in row]
        rows.append(buttons)
    return ReplyKeyboardMarkup(keyboard=rows, resize_keyboard=True, one_time_keyboard=False)

async def send_state(chat_id: int, state_key: str):
    user = get_user(chat_id)
    user["state"] = state_key
    state = FLOW_STATES[state_key]
    message = state.get("message", "")

    kb = build_keyboard(state["keyboard"]) if "keyboard" in state else None
    await bot.send_message(chat_id, message, reply_markup=kb)

    for d in state.get("deliver", []):
        if d.get("type") == "document" and d.get("url"):
            try:
                await bot.send_document(chat_id, d["url"], caption=d.get("title"))
            except Exception as e:
                log.warning("deliver error: %r", e)
                await bot.send_message(chat_id, f"Не удалось отправить документ: {d.get('title','file')}")

    if state.get("notify_admin") and ADMIN_CHAT_ID:
        try:
            await bot.send_message(
                int(ADMIN_CHAT_ID),
                f"Notify: user {chat_id} → <b>{state_key}</b>\nData: {json.dumps(user['data'], ensure_ascii=False)}"
            )
        except Exception as e:
            log.warning("notify admin error: %r", e)

# -------------------- FASTAPI --------------------
app = FastAPI()

@app.api_route("/", methods=["GET", "HEAD"], response_class=PlainTextResponse)
async def root():
    return "OK"

@app.post("/webhook/{token}", response_class=PlainTextResponse)
async def telegram_webhook(token: str, request: Request):
    if token != TELEGRAM_TOKEN:
        raise HTTPException(403, "Invalid token")

    # Если базовый URL не знаем — вычислим и выставим вебхук
    global WEBHOOK_URL, WEBHOOK_BASE
    if not WEBHOOK_BASE:
        host = request.headers.get("Host")
        proto = "https" if request.headers.get("X-Forwarded-Proto", "http") == "https" else "http"
        if host:
            WEBHOOK_BASE = f"{proto}://{host}"
            WEBHOOK_URL = WEBHOOK_BASE + WEBHOOK_PATH
            try:
                # allowed_updates=None → принять все типы, вдруг появятся callback_query и т.п.
                await bot.set_webhook(WEBHOOK_URL, drop_pending_updates=True, allowed_updates=None)
                log.info("Webhook set to: %s", WEBHOOK_URL)
            except Exception as e:
                log.error("Webhook set error: %r", e)

    data = await request.json()
    if DEBUG:
        log.info("UPDATE RAW: %s", data)

    update: Update = Update.model_validate(data)
    # КОРРЕКТНАЯ передача апдейта в диспетчер
    await dp.feed_update(bot, update)

    return "OK"

# -------------------- HANDLERS --------------------
@dp.message()
async def handle_message(message: types.Message):
    try:
        chat_id = message.chat.id
        text = (message.text or "").strip()

        # команды
        if text in ("/start", "⬅️ В начало"):
            USER_STATE.pop(chat_id, None)
            get_user(chat_id)
            await bot.send_message(chat_id, "Добро пожаловать в GTClub File Service!")
            await send_state(chat_id, "start")
            return

        # отписка/согласие
        if text.lower() in [s.lower() for s in AUTOMATIONS.get("unsubscribe_keywords", [])]:
            u = get_user(chat_id); u["dnd"] = True
            await bot.send_message(chat_id, "Вы отписались. Чтобы подписаться снова — напишите «Согласен».")
            return
        if text.lower() in [s.lower() for s in AUTOMATIONS.get("consent_keywords", [])]:
            u = get_user(chat_id); u["dnd"] = False; u["consent"] = True
            await bot.send_message(chat_id, "Спасибо, отмечено ✅")
            return

        user = get_user(chat_id)
        state_key = user.get("state", "start")
        state = FLOW_STATES.get(state_key, FLOW_STATES["start"])

        # быстрые команды из любого состояния
        if text == "/price": await send_state(chat_id, "price"); return
        if text == "/order": await send_state(chat_id, "order_intro"); return
        if text == "/help":  await send_state(chat_id, "help"); return

        # ожидаем ввод?
        expect = state.get("expect")
        if expect:
            if expect["type"] in ("file_or_text", "text_or_file") and message.document:
                file_info = {
                    "file_id": message.document.file_id,
                    "file_name": message.document.file_name,
                    "mime": message.document.mime_type,
                    "size": message.document.file_size
                }
                save_field(user["data"], expect["field"], file_info)
            else:
                value = text
                valid = True
                for v in expect.get("validators", []):
                    t = v.get("type")
                    pattern = v.get("value", "")
                    if t == "minlen" and len(value) < int(v.get("value", 0)):
                        valid = False
                    if t == "regex" and pattern and not re.match(pattern, value):
                        valid = False
                    if t == "regex_any" and pattern and not re.search(pattern, value):
                        valid = False
                if not value and expect.get("required"):
                    await bot.send_message(chat_id, "Это поле обязательно. Введите значение."); return
                if not valid:
                    await bot.send_message(chat_id, "Значение не прошло проверку. Попробуйте снова."); return
                save_field(user["data"], expect["field"], value)

            next_state = state.get("next", "menu_main")
            await send_state(chat_id, next_state)
            return

        # кнопки
        goto = None
        for row in state.get("keyboard", []):
            for item in row:
                if item["text"] == text:
                    if "set" in item:
                        for k, v in item["set"].items():
                            save_field(user["data"], k, v)
                    if "toggle" in item:
                        for k, v in item["toggle"].items():
                            arr = user["data"].get(k, [])
                            arr = [x for x in arr if x != v] if v in arr else arr + [v]
                            user["data"][k] = arr
                    goto = item.get("goto")
                    break
            if goto:
                break

        if goto:
            await send_state(chat_id, goto); return

        # fallback
        await bot.send_message(chat_id, "Не понял команду. Выберите кнопку или используйте /help.")
        await send_state(chat_id, state_key)

    except Exception as e:
        log.error("HANDLE_MESSAGE ERROR: %r", e, exc_info=True)

# -------------------- LIFECYCLE --------------------
@app.on_event("startup")
async def on_startup():
    if WEBHOOK_URL:
        try:
            await bot.set_webhook(WEBHOOK_URL, drop_pending_updates=True, allowed_updates=None)
            log.info("Webhook set to: %s", WEBHOOK_URL)
        except Exception as e:
            log.error("Failed to set webhook: %r", e)
    else:
        log.info("WEBHOOK_URL unknown. Will try to set on first request.")

@app.on_event("shutdown")
async def on_shutdown():
    try:
        await bot.delete_webhook(drop_pending_updates=False)
    except Exception:
        pass
