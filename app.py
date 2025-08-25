def install_handlers(router):
    # --- импорты локально, как у тебя сделано ---
    from aiogram import F
    from aiogram.types import (
        Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton,
        ReplyKeyboardMarkup, KeyboardButton
    )
    from aiogram.filters import CommandStart, Command
    from aiogram.fsm.state import StatesGroup, State
    from aiogram.fsm.context import FSMContext

    # -------- язык и подписи --------
    def lang_key(code: str) -> str:
        c = (code or "").lower()
        if c.startswith("uk"):
            return "uk"
        if c.startswith("en"):
            return "en"
        return "ru"

    def labels(lg: str):
        # используем те же тексты, что и были в твоём файле
        return _labels(lg)

    # -------- справочники (пример) --------
    BRANDS = ["BMW", "VAG", "Mercedes", "Ford", "Toyota"]
    MODELS = {
        "BMW": ["F10", "F30", "G20"],
        "VAG": ["Golf 7", "A3 8V", "A4 B9"],
        "Mercedes": ["W205", "W213"],
        "Ford": ["Focus 3", "Mondeo 5"],
        "Toyota": ["Camry V70", "RAV4 XA50"],
    }
    YEARS = {
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
    ENGINES = {
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

    # -------- клавиатуры --------
    def main_kb(lg: str) -> ReplyKeyboardMarkup:
        t = labels(lg)
        return ReplyKeyboardMarkup(
            keyboard=[[KeyboardButton(text=t["order"])],
                      [KeyboardButton(text=t["info"]), KeyboardButton(text=t["support"])]],
            resize_keyboard=True
        )

    def ikb_brands() -> InlineKeyboardMarkup:
        return InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text=b, callback_data=f"brand:{b}")]
            for b in BRANDS
        ])

    def ikb_models(brand: str) -> InlineKeyboardMarkup:
        items = MODELS.get(brand, [])
        return InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text=m, callback_data=f"model:{m}")]
            for m in items
        ])

    def ikb_years(model: str) -> InlineKeyboardMarkup:
        items = YEARS.get(model, [])
        return InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text=y, callback_data=f"year:{y}")]
            for y in items
        ])

    def ikb_engines(model: str) -> InlineKeyboardMarkup:
        items = ENGINES.get(model, [])
        return InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text=e, callback_data=f"engine:{e}")]
            for e in items
        ])

    def ikb_options(lg: str, chosen: list) -> InlineKeyboardMarkup:
        t = labels(lg)
        rows = []
        for opt in OPTIONS:
            mark = "✅ " if opt in chosen else ""
            rows.append([InlineKeyboardButton(text=f"{mark}{opt}", callback_data=f"opt:{opt}")])
        rows.append([InlineKeyboardButton(text="✅ Готово" if lg=="ru" else "✅ Готово" if lg=="uk" else "✅ Done", callback_data="opt_done")])
        rows.append([InlineKeyboardButton(text="❌ Отменить" if lg=="ru" else "❌ Скасувати" if lg=="uk" else "❌ Cancel", callback_data="cancel")])
        return InlineKeyboardMarkup(inline_keyboard=rows)

    def ikb_confirm(lg: str) -> InlineKeyboardMarkup:
        ok = "✅ Подтвердить" if lg=="ru" else "✅ Підтвердити" if lg=="uk" else "✅ Confirm"
        cancel = "❌ Отменить" if lg=="ru" else "❌ Скасувати" if lg=="uk" else "❌ Cancel"
        return InlineKeyboardMarkup(inline_keyboard=[[
            InlineKeyboardButton(text=ok, callback_data="confirm"),
            InlineKeyboardButton(text=cancel, callback_data="cancel"),
        ]])

    # -------- FSM --------
    class Order(StatesGroup):
        BRAND = State()
        MODEL = State()
        YEAR = State()
        ENGINE = State()
        OPTIONS = State()
        FILE = State()
        CONFIRM = State()

    # -------- helpers --------
    def summary(lg: str, data: dict) -> str:
        lines = []
        lines.append(f"<b>Brand:</b> {data.get('brand') or '—'}")
        lines.append(f"<b>Model:</b> {data.get('model') or '—'}")
        lines.append(f"<b>Year:</b> {data.get('year') or '—'}")
        lines.append(f"<b>Engine:</b> {data.get('engine') or '—'}")
        lines.append(f"<b>Options:</b> {', '.join(data.get('options', [])) or '—'}")
        doc = data.get("file")
        if doc:
            lines.append(f"<b>File:</b> {getattr(doc, 'file_name', 'document')}")
        comment = data.get("comment")
        if comment:
            lines.append(f"<b>Comment:</b> {comment}")
        head = "Проверьте данные и подтвердите заявку:" if lg=="ru" else \
               "Перевірте дані та підтвердіть заявку:" if lg=="uk" else \
               "Review the details and confirm:"
        return head + "\n\n" + "\n".join(lines)

    async def notify_admin(data: dict, msg: Message):
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

    # -------- команды /start и /help --------
    @router.message(CommandStart())
    async def cmd_start(message: Message, state: FSMContext):
        lg = lang_key(getattr(message.from_user, "language_code", ""))  # ru/uk/en
        t = labels(lg)
        await state.clear()
        # приветствие + главное меню
        await message.answer(t["welcome"], reply_markup=main_kb(lg))
        # кнопка «начать заказ» отдельным сообщением (для удобства)
        kb = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text=("📝 Почати замовлення" if lg=="uk" else "📝 Начать заказ" if lg=="ru" else "📝 Start order"), callback_data="start_order")]
        ])
        await message.answer("Меню" if lg=="ru" else "Меню" if lg=="uk" else "Menu", reply_markup=kb)

    @router.message(Command("help"))
    async def cmd_help(message: Message, state: FSMContext):
        # повторяем поведение /start
        await cmd_start(message, state)

    # -------- reply-меню обработка --------
    @router.message()
    async def on_text(message: Message, state: FSMContext):
        lg = lang_key(getattr(message.from_user, "language_code", ""))
        t = labels(lg)
        txt = (message.text or "").strip()
        if txt == t["order"]:
            # запуск воронки
            await state.set_state(Order.BRAND)
            await state.update_data(options=[], comment=None, file=None)
            await message.answer("Оберіть марку авто:" if lg=="uk" else "Выберите марку авто:" if lg=="ru" else "Choose car brand:",
                                 reply_markup=ikb_brands())
        elif txt == t["info"]:
            await message.answer(t["info_text"])
        elif txt == t["support"]:
            await message.answer(t["support_text"])
        else:
            # не ломаем твой UX — отвечаем приветствием
            await message.answer(t["welcome"], reply_markup=main_kb(lg))

    # -------- шаги воронки --------
    @router.callback_query(F.data == "start_order")
    async def cb_start_order(cb: CallbackQuery, state: FSMContext):
        lg = lang_key(cb.from_user.language_code or "")
        await state.set_state(Order.BRAND)
        await state.update_data(options=[], comment=None, file=None)
        await cb.message.edit_text("Оберіть марку авто:" if lg=="uk" else "Выберите марку авто:" if lg=="ru" else "Choose car brand:",
                                   reply_markup=ikb_brands())
        await cb.answer()

    @router.callback_query(F.data.startswith("brand:"))
    async def cb_brand(cb: CallbackQuery, state: FSMContext):
        lg = lang_key(cb.from_user.language_code or "")
        brand = cb.data.split(":",1)[1]
        await state.update_data(brand=brand, model=None, year=None, engine=None)
        await state.set_state(Order.MODEL)
        await cb.message.edit_text("Оберіть модель:" if lg=="uk" else "Выберите модель:" if lg=="ru" else "Choose model:",
                                   reply_markup=ikb_models(brand))
        await cb.answer()

    @router.callback_query(F.data.startswith("model:"))
    async def cb_model(cb: CallbackQuery, state: FSMContext):
        lg = lang_key(cb.from_user.language_code or "")
        model = cb.data.split(":",1)[1]
        await state.update_data(model=model, year=None, engine=None)
        await state.set_state(Order.YEAR)
        await cb.message.edit_text("Оберіть рік випуску:" if lg=="uk" else "Выберите год выпуска:" if lg=="ru" else "Choose model year:",
                                   reply_markup=ikb_years(model))
        await cb.answer()

    @router.callback_query(F.data.startswith("year:"))
    async def cb_year(cb: CallbackQuery, state: FSMContext):
        lg = lang_key(cb.from_user.language_code or "")
        year = cb.data.split(":",1)[1]
        await state.update_data(year=year, engine=None)
        await state.set_state(Order.ENGINE)
        data = await state.get_data()
        await cb.message.edit_text("Оберіть двигун:" if lg=="uk" else "Выберите двигатель:" if lg=="ru" else "Choose engine:",
                                   reply_markup=ikb_engines(data.get("model")))
        await cb.answer()

    @router.callback_query(F.data.startswith("engine:"))
    async def cb_engine(cb: CallbackQuery, state: FSMContext):
        lg = lang_key(cb.from_user.language_code or "")
        engine = cb.data.split(":",1)[1]
        await state.update_data(engine=engine)
        await state.set_state(Order.OPTIONS)
        data = await state.get_data()
        await cb.message.edit_text("Оберіть опції (можна декілька):" if lg=="uk" else "Выберите опции (можно несколько):" if lg=="ru" else "Choose options (you can select multiple):",
                                   reply_markup=ikb_options(lg, data.get("options", [])))
        await cb.answer()

    @router.callback_query(F.data.startswith("opt:"))
    async def cb_opt_toggle(cb: CallbackQuery, state: FSMContext):
        lg = lang_key(cb.from_user.language_code or "")
        opt = cb.data.split(":",1)[1]
        data = await state.get_data()
        chosen = set(data.get("options", []))
        if opt in chosen: chosen.remove(opt)
        else: chosen.add(opt)
        chosen_list = sorted(list(chosen))
        await state.update_data(options=chosen_list)
        await cb.message.edit_reply_markup(reply_markup=ikb_options(lg, chosen_list))
        await cb.answer()

    @router.callback_query(F.data == "opt_done")
    async def cb_opt_done(cb: CallbackQuery, state: FSMContext):
        lg = lang_key(cb.from_user.language_code or "")
        await state.set_state(Order.FILE)
        await cb.message.edit_text("📂 Надішліть файл прошивки як документ (скріпка). Можна додати коментар текстом." if lg=="uk"
                                   else "📂 Пришлите файл прошивки как документ (скрепка). Можно добавить комментарий текстом." if lg=="ru"
                                   else "📂 Please send the ECU file as a document (paperclip). You may add comments as text.")
        await cb.answer()

    # ---- приём файла и/или комментария ----
    @router.message(Order.FILE, F.document)
    async def on_document(message: Message, state: FSMContext):
        lg = lang_key(getattr(message.from_user, "language_code", ""))
        await state.update_data(file=message.document)
        await state.set_state(Order.CONFIRM)
        data = await state.get_data()
        await message.answer(summary(lg, data), reply_markup=ikb_confirm(lg))

    @router.message(Order.FILE)
    async def on_comment_or_wrongfile(message: Message, state: FSMContext):
        lg = lang_key(getattr(message.from_user, "language_code", ""))
        if message.text:
            await state.update_data(comment=message.text.strip())
            data = await state.get_data()
            await message.answer(summary(lg, data), reply_markup=ikb_confirm(lg))
        else:
            await message.answer("Будь ласка, надішліть файл саме як документ (не фото)." if lg=="uk"
                                 else "Пожалуйста, отправьте файл именно как документ (не фото)." if lg=="ru"
                                 else "Please upload the file as a document (not a photo).")

    @router.callback_query(F.data == "confirm")
    async def cb_confirm(cb: CallbackQuery, state: FSMContext):
        lg = lang_key(cb.from_user.language_code or "")
        data = await state.get_data()
        # уведомим админа, если указан
        try:
            if ADMIN_CHAT_ID:
                uid = int(ADMIN_CHAT_ID)
                await cb.message.bot.send_message(uid, "🔔 <b>New file-service request</b>\n" + summary("en", data))
                if data.get("file"):
                    await cb.message.bot.send_document(uid, data["file"].file_id, caption="Client file")
                await cb.message.bot.send_message(uid, f"Client: @{cb.from_user.username or cb.from_user.id}")
        except Exception as e:
            logging.warning("notify_admin failed: %s", e)
        await state.clear()
        await cb.message.edit_text("✅ Заявка отправлена. Инженер свяжется с вами." if lg=="ru"
                                   else "✅ Заявку надіслано. Інженер зв'яжеться з вами." if lg=="uk"
                                   else "✅ Request sent. Our engineer will contact you.")
        await cb.answer()
