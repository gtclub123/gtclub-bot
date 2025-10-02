
import asyncio
import json
import os
from aiogram import Bot, Dispatcher, types
from aiogram.types import ReplyKeyboardMarkup, KeyboardButton

from dotenv import load_dotenv
load_dotenv()

TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")
if not TELEGRAM_TOKEN:
    raise RuntimeError("Set TELEGRAM_TOKEN in .env")

bot = Bot(token=TELEGRAM_TOKEN, parse_mode="HTML")
dp = Dispatcher()

# Load flow
with open("flow.json", "r", encoding="utf-8") as f:
    FLOW = json.load(f)
FLOW_STATES = FLOW["flow"]

USER_STATE = {}

def get_user(chat_id):
    if chat_id not in USER_STATE:
        USER_STATE[chat_id] = {"state": "start", "data": {}}
    return USER_STATE[chat_id]

def build_keyboard(layout):
    rows = []
    for row in layout:
        buttons = [KeyboardButton(text=item["text"]) for item in row]
        rows.append(buttons)
    return ReplyKeyboardMarkup(keyboard=rows, resize_keyboard=True, one_time_keyboard=False)

async def send_state(chat_id, key):
    st = FLOW_STATES[key]
    kb = build_keyboard(st["keyboard"]) if "keyboard" in st else None
    await bot.send_message(chat_id, st.get("message",""), reply_markup=kb)

@dp.message()
async def handle_msg(message: types.Message):
    chat_id = message.chat.id
    text = message.text or ""

    if text == "/start":
        USER_STATE.pop(chat_id, None)
        get_user(chat_id)
        await send_state(chat_id, "start")
        return

    user = get_user(chat_id)
    state = FLOW_STATES.get(user["state"], FLOW_STATES["start"])

    # Very simplified: just follow buttons, no validators
    goto = None
    for row in state.get("keyboard", []):
        for item in row:
            if item["text"] == text:
                goto = item.get("goto")
                break
        if goto:
            break

    if goto:
        user["state"] = goto
        await send_state(chat_id, goto)
        return

    await message.answer("Не понял. Нажмите кнопку или /start")

async def main():
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
