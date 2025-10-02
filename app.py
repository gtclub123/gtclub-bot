
import os
import json
import re
import asyncio
from typing import Dict, Any, Optional, List

from fastapi import FastAPI, Request, HTTPException
from fastapi.responses import JSONResponse, PlainTextResponse
from pydantic import BaseModel
from aiogram import Bot, Dispatcher, types
from aiogram.types import Update, ReplyKeyboardMarkup, KeyboardButton

from dotenv import load_dotenv

load_dotenv()

TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")
ADMIN_CHAT_ID = os.getenv("ADMIN_CHAT_ID")
WEBHOOK_BASE = os.getenv("WEBHOOK_BASE")  # e.g. https://gtclub-bot.onrender.com
RENDER_EXTERNAL_URL = os.getenv("RENDER_EXTERNAL_URL")  # Render injects this
PORT = int(os.getenv("PORT", "8000"))

if not TELEGRAM_TOKEN:
    raise RuntimeError("Missing TELEGRAM_TOKEN env var")

WEBHOOK_BASE = WEBHOOK_BASE or RENDER_EXTERNAL_URL
if not WEBHOOK_BASE:
    print("WARNING: WEBHOOK_BASE/RENDER_EXTERNAL_URL is not set. Webhook set on first request using Host header.")

WEBHOOK_PATH = f"/webhook/{TELEGRAM_TOKEN}"
WEBHOOK_URL = (WEBHOOK_BASE + WEBHOOK_PATH) if WEBHOOK_BASE else None

bot = Bot(token=TELEGRAM_TOKEN, parse_mode="HTML")
dp = Dispatcher()

# --- Load flow.json ---
with open(os.path.join(os.path.dirname(__file__), "flow.json"), "r", encoding="utf-8") as f:
    FLOW: Dict[str, Any] = json.load(f)

FLOW_STATES = FLOW["flow"]
AUTOMATIONS = FLOW.get("automations", {})
COMMANDS = {c["cmd"]: c["desc"] for c in FLOW.get("commands", [])}

# --- In-memory user storage (use Redis/DB in production) ---
USER_STATE: Dict[int, Dict[str, Any]] = {}  # chat_id -> {state:str, data:dict, consent:bool, dnd:bool}

def get_user(chat_id: int) -> Dict[str, Any]:
    if chat_id not in USER_STATE:
        USER_STATE[chat_id] = {"state": "start", "data": {}, "consent": True, "dnd": False}
    return USER_STATE[chat_id]

def save_field(data: Dict[str, Any], field_path: str, value: Any):
    # Support dotted paths e.g. "order.stage"
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
    return ReplyKeyboardMarkup(
        keyboard=rows,
        resize_keyboard=True,
        one_time_keyboard=False
    )

async def send_state(chat_id: int, state_key: str):
    user = get_user(chat_id)
    user["state"] = state_key
    state = FLOW_STATES[state_key]
    message = state.get("message", "")

    kb = None
    if "keyboard" in state:
        kb = build_keyboard(state["keyboard"])

    await bot.send_message(chat_id, message, reply_markup=kb)

    # Deliver documents if any
    for d in state.get("deliver", []):
        if d.get("type") == "document" and d.get("url"):
            try:
                await bot.send_document(chat_id, d["url"], caption=d.get("title", None))
            except Exception as e:
                await bot.send_message(chat_id, f"Не удалось отправить документ: {d.get('title','file')}")

    # Notify admin if requested
    if state.get("notify_admin") and ADMIN_CHAT_ID:
        try:
            await bot.send_message(int(ADMIN_CHAT_ID), f"Notify: user {chat_id} reached state <b>{state_key}</b>\nData: {json.dumps(user['data'], ensure_ascii=False)}")
        except:
            pass

class TelegramRoute(BaseModel):
    token: str

app = FastAPI()

@app.get("/", response_class=JSONResponse)
async def root():
    return {
        "status": "ok",
        "webhook_path": WEBHOOK_PATH,
        "webhook_url": WEBHOOK_URL,
        "commands": COMMANDS
    }

@app.post("/webhook/{token}")
async def telegram_webhook(token: str, request: Request):
    if token != TELEGRAM_TOKEN:
        raise HTTPException(403, "Invalid token")

    # If webhook base unknown (local dev), set on the fly
    global WEBHOOK_URL, WEBHOOK_BASE
    if not WEBHOOK_BASE:
        host = request.headers.get("Host")
        proto = "https" if request.headers.get("X-Forwarded-Proto", "http") == "https" else "http"
        if host:
            WEBHOOK_BASE = f"{proto}://{host}"
            WEBHOOK_URL = WEBHOOK_BASE + WEBHOOK_PATH
            try:
                await bot.set_webhook(WEBHOOK_URL, drop_pending_updates=True, allowed_updates=["message"])
            except Exception as e:
                print("Webhook set error:", e)

    try:
        data = await request.json()
    except Exception:
        raise HTTPException(400, "Invalid JSON")

    try:
        update = Update.model_validate(data)
    except Exception as e:
        raise HTTPException(400, f"Bad update: {e}")

    # Minimal dispatcher
    if update.message:
        await handle_message(update.message)
    return PlainTextResponse("OK")

@dp.message()
async def handle_message(message: types.Message):
    chat_id = message.chat.id
    text = message.text or ""

    # Unsubscribe
    unsub = [s.lower() for s in AUTOMATIONS.get("unsubscribe_keywords", [])]
    if text.lower() in unsub:
        u = get_user(chat_id)
        u["dnd"] = True
        await bot.send_message(chat_id, "Вы отписались. Чтобы подписаться снова — напишите «Согласен».")
        return

    # Consent
    consent_words = [s.lower() for s in AUTOMATIONS.get("consent_keywords", [])]
    if text.lower() in consent_words:
        u = get_user(chat_id)
        u["dnd"] = False
        u["consent"] = True
        await bot.send_message(chat_id, "Спасибо, отмечено ✅")
        return

    # Commands
    if text in ("/start", "⬅️ В начало"):
        USER_STATE.pop(chat_id, None)  # reset
        get_user(chat_id)  # create
        await bot.send_message(chat_id, "Добро пожаловать в GTClub File Service!")
        await send_state(chat_id, "start")
        return

    if text == "/price":
        await send_state(chat_id, "price")
        return

    if text == "/order":
        await send_state(chat_id, "order_intro")
        return

    if text == "/help":
        await send_state(chat_id, "help")
        return

    # FSM based on JSON
    user = get_user(chat_id)
    state_key = user.get("state", "start")
    state = FLOW_STATES.get(state_key, FLOW_STATES["start"])

    # If expecting value
    expect = state.get("expect")
    if expect:
        # Files allowed?
        if expect["type"] in ("file_or_text", "text_or_file") and message.document:
            file_info = {
                "file_id": message.document.file_id,
                "file_name": message.document.file_name,
                "mime": message.document.mime_type,
                "size": message.document.file_size
            }
            save_field(user["data"], expect["field"], file_info)
        else:
            value = text.strip()
            # validators
            valid = True
            for v in expect.get("validators", []):
                t = v.get("type")
                if t == "minlen" and len(value) < int(v.get("value", 0)):
                    valid = False
                if t == "regex":
                    if not re.match(v.get("value", ""), value):
                        valid = False
                if t == "regex_any":
                    if not re.search(v.get("value", ""), value):
                        valid = False
            if not value and expect.get("required"):
                await bot.send_message(chat_id, "Это поле обязательно. Введите значение.")
                return
            if not valid:
                await bot.send_message(chat_id, "Значение не прошло проверку. Попробуйте снова.")
                return
            save_field(user["data"], expect["field"], value)

        next_state = state.get("next", "menu_main")
        await send_state(chat_id, next_state)
        return

    # Otherwise, interpret buttons (by text)
    # search current state's keyboard for matching button
    goto = None
    chosen_button = None
    for row in state.get("keyboard", []):
        for item in row:
            if item["text"] == text:
                chosen_button = item
                goto = item.get("goto")
                # apply 'set' / 'toggle' if present
                if "set" in item:
                    for k, v in item["set"].items():
                        save_field(user["data"], k, v)
                if "toggle" in item:
                    for k, v in item["toggle"].items():
                        arr = user["data"].get(k, [])
                        if v in arr:
                            arr.remove(v)
                        else:
                            arr.append(v)
                        user["data"][k] = arr
                break
        if goto:
            break

    if goto:
        await send_state(chat_id, goto)
        return

    # default: if not recognized, re-show current state keyboard/message
    await bot.send_message(chat_id, "Не понял команду. Выберите кнопку или используйте /help.")
    await send_state(chat_id, state_key)

@app.on_event("startup")
async def on_startup():
    # Set webhook on startup if WEBHOOK_BASE known
    if WEBHOOK_URL:
        try:
            await bot.set_webhook(WEBHOOK_URL, drop_pending_updates=True, allowed_updates=["message"])
            print("Webhook set to:", WEBHOOK_URL)
        except Exception as e:
            print("Failed to set webhook:", e)
    else:
        print("WEBHOOK_URL unknown. Will try to set on first request.")

@app.on_event("shutdown")
async def on_shutdown():
    try:
        await bot.delete_webhook(drop_pending_updates=False)
    except:
        pass
