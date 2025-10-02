
# GTClub Telegram Bot (Webhook on Render, aiogram v3)

Готовый шаблон: FastAPI + aiogram v3 + JSON-флоу. Можно запускать локально (polling) и в прод (webhook).

## 0) Что внутри
- `app.py` — FastAPI-вебхук + движок бота, читает `flow.json`
- `dev_polling.py` — локальный запуск в режиме `polling`
- `flow.json` — сценарий диалогов (состояния, тексты, кнопки, переходы)
- `requirements.txt` — зависимости
- `render.yaml` — конфигурация Render
- `.env.example` — пример переменных окружения

---

## 1) Создай бота в BotFather
1. В Telegram открой `@BotFather`
2. Команда `/newbot` → задай имя и юзернейм бота
3. Скопируй `TOKEN`

---

## 2) Локальный запуск (для проверки)
```bash
python -m venv .venv
source .venv/bin/activate  # Windows: .venv\Scripts\activate
pip install -r requirements.txt

cp .env.example .env
# Открой .env и вставь TELEGRAM_TOKEN и (желательно) ADMIN_CHAT_ID

python dev_polling.py
```
Открой чат с ботом → напиши `/start`

> Режим polling не требует вебхука и HTTPS. Удобен для проверки логики.

---

## 3) Деплой на Render (вебхук)
Вариант А (через `render.yaml`):
1. Залей код в GitHub-репозиторий
2. На https://render.com → `New +` → `Blueprint` → выбери свой репозиторий
3. Render распознает `render.yaml` и предложит создать Web Service
4. В Variables добавь:
   - `TELEGRAM_TOKEN` (Secret)
   - `ADMIN_CHAT_ID` (необязательно)
   - `WEBHOOK_BASE` (необязательно — Render подставит `RENDER_EXTERNAL_URL`)
5. Нажми Deploy. Render запустит `uvicorn app:app --host 0.0.0.0 --port $PORT`

Вариант Б (вручную):
1. `New +` → `Web Service` → подключи репозиторий
2. Build Command: `pip install -r requirements.txt`
3. Start Command: `uvicorn app:app --host 0.0.0.0 --port $PORT`
4. Добавь переменные окружения, как в пункте выше
5. Deploy

После первого старта бэк сам выставит вебхук на `WEBHOOK_BASE + /webhook/TELEGRAM_TOKEN`.
Если `WEBHOOK_BASE` не задан, будет использован `RENDER_EXTERNAL_URL` (Render его подставляет).

---

## 4) Проверка работоспособности
- Зайди на URL сервиса (Render покажет ссылку). Должен открыться `/` с JSON-ответом:
  ```json
  { "status": "ok", "webhook_path": "/webhook/<TOKEN>", ... }
  ```
- Проверь вебхук у Telegram:
  - Открой в браузере:  
    `https://api.telegram.org/bot<TELEGRAM_TOKEN>/getWebhookInfo`
  - В `result.url` должна быть ссылка вашего сервиса с путём `/webhook/<TOKEN>`
- Напиши боту `/start` и проверь диалог.

> Если видишь `404: Not Found` при обращении к `/webhook/...` — проверь, что путь совпадает EXACTLY с `/webhook/<ваш_точный_TOKEN>`.

---

## 5) Частые ошибки и решения
- **404 на вебхуке**:  
  Убедись, что Telegram шлёт POST на `/webhook/<ваш токен>` (точное совпадение).  
  В Render `External URL` должен быть доступен из интернета (https).

- **Вебхук не выставился**:  
  Посмотри логи Render. Если `WEBHOOK_BASE` пуст, приложение попытается вычислить URL из заголовка `Host` первого запроса и выставить вебхук.  
  Лучше задать `WEBHOOK_BASE` вручную в переменных (например, `https://gtclub-bot.onrender.com`).

- **Бот не отвечает**:  
  Проверь `TELEGRAM_TOKEN`. Убедись, что вебхук в `getWebhookInfo` указывает на ваш активный URL.  
  На время отладки удали вебхук и запусти локально `dev_polling.py`:
  ```
  https://api.telegram.org/bot<token>/deleteWebhook?drop_pending_updates=true
  ```

- **Кнопки не работают**:  
  В этом шаблоне обычная клавиатура (ReplyKeyboard). Бот сопоставляет `message.text` с текстом кнопки.  
  Изменили текст в `flow.json` → перезапустите приложение.

- **Документы не отправляются**:  
  Проверьте валидность ссылок в `flow.json` в блоках `deliver`.

---

## 6) Как изменять сценарий
- Редактируй `flow.json`: тексты, кнопки (`text`), переходы (`goto`), сбор полей (`expect`), валидации.
- Текущая реализация поддерживает:
  - `message`, `keyboard` с `text`/`goto`
  - `expect` с `field`, `required`, простыми валидаторами (`minlen`, `regex`, `regex_any`)
  - `set`/`toggle` для записи в данные пользователя
  - `deliver` (документы по URL)
  - `notify_admin` (шлёт событие админу, если задан `ADMIN_CHAT_ID`)

> Для продакшена стоит вынести `USER_STATE` в Redis/БД, добавить обработку ошибок и логирование.

---

## 7) Команды для BotFather (опционально)
В BotFather → `/setcommands`:
```
start - Запуск бота
price - Прайс на услуги
order - Сделать заказ файла
help - Помощь и контакты
```

---

## 8) Сброс/перевыставление вебхука вручную
```
# удалить вебхук и все висящие апдейты
https://api.telegram.org/bot<token>/deleteWebhook?drop_pending_updates=true

# поставить вебхук заново (пример)
https://api.telegram.org/bot<token>/setWebhook?url=https://your-app.onrender.com/webhook/<token>
```

Удачи! Если понадобится — подключим CRM/Google Sheets, оплату и выдачу готовых файлов прямо из бота.
