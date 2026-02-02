import os
from fastapi import FastAPI, Request
from aiogram import Bot, Dispatcher, types
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton, Update
from aiogram.filters import CommandStart
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.fsm.state import StatesGroup, State
from aiogram.fsm.context import FSMContext
from aiogram.exceptions import TelegramBadRequest
import uvicorn
from table_leads import save_lead
from table_income import get_average_income


BOT_TOKEN = os.environ["BOT_TOKEN"]
WEBHOOK_URL = os.environ["WEBHOOK_URL"]

bot = Bot(token=BOT_TOKEN)
dp = Dispatcher(storage=MemoryStorage())

# ===============================
# КОНСТАНТЫ
# ===============================

DELIVERY_TITLES = {
    "foot": "🧍 Пешком",
    "bike": "🚲 Вело",
    "car": "🚗 Авто",
}
DOCUMENTS_BY_CITIZENSHIP = {
    "Россия": "Паспорт, ИНН, медкнижка (если есть)",
    "Беларусь": "Паспорт, ИНН, СНИЛС (если есть), дактилоскопия (если есть)",
    "Казахстан": "Паспорт, миграционная карта, ИНН, СНИЛС (если есть), дактилоскопия (если есть)",
    "Армения": "Паспорт, миграционная карта, ИНН, СНИЛС (если есть), дактилоскопия (если есть)",
    "Кыргызстан": "Паспорт, миграционная карта, ИНН, СНИЛС (если есть), дактилоскопия (если есть)",
    "Другое": "Паспорт, миграционная карта, ИНН (если есть), патент/ВНЖ/РВП (по региону), СНИЛС/дактилоскопия (если есть)"
}

DAILY_PAYOUT_CITIZENSHIPS = {
    "Россия", "Беларусь", "Казахстан", "Армения", "Кыргызстан"
}

CITIZENSHIP_TYPE_MAP = {
    "Россия": "rf",
    "Беларусь": "eaes",
    "Казахстан": "eaes",
    "Армения": "eaes",
    "Кыргызстан": "eaes",
    "Другое": "not_rf",
}

TOP_CITIES = [
    "Москва", "Санкт-Петербург", "Екатеринбург", "Новосибирск",
    "Казань", "Нижний Новгород"
]

bonus_cities = [
    "Ростов-на-Дону",
    "Батайск",
    "Пятигорск",
    "Майкоп",
    "Сочи",
    "Москва",
    "Красногорск",
    "Тула",
    "Воронеж",
    "Мурманск",
    "Пушкин",
    "Ханты-Мансийск",
    "Красноярск",
    "Елабуга",
    "Тобольск"
]
# ===============================
# FSM
# ===============================

class Form(StatesGroup):
    waiting_for_start = State()
    waiting_for_age = State()
    waiting_for_underage = State()
    waiting_for_citizenship = State()
    waiting_for_city = State()
    waiting_for_delivery = State()

# ===============================
# ВСПОМОГАТЕЛЬНЫЕ ФУНКЦИИ
# ===============================
async def safe_edit(message, text, **kwargs):
    try:
        await message.edit_text(text, **kwargs)
    except TelegramBadRequest as e:
        if "message is not modified" in str(e):
            pass
        else:
            raise

async def safe_edit_markup(message, reply_markup):
    try:
        await message.edit_reply_markup(reply_markup=reply_markup)
    except TelegramBadRequest as e:
        if "message is not modified" in str(e):
            pass
        else:
            raise

def filter_cities_by_citizenship(records, citizenship_type):
    cities = set()
    for r in records:
        if citizenship_type == "rf":
            cities.add(r["city"])
        elif citizenship_type == "eaes" and r["eaes"] == "TRUE":
            cities.add(r["city"])
        elif citizenship_type == "not_rf" and r["not_rf"] == "TRUE":
            cities.add(r["city"])
    return sorted(cities)

def income_keyboard():
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(
                text="📝 Откликнуться",
                callback_data="send_lead"
            )],
            [
                InlineKeyboardButton(
                    text="🎁 Бонусы для курьеров",
                    callback_data="income_bonus"
                ),
                InlineKeyboardButton(
                    text="❓ Частые вопросы",
                    callback_data="income_faq"
                )
            ],
            [
                InlineKeyboardButton(
                    text="🔄 Рассчитать ещё раз",
                    callback_data="income_recalc"
                )
            ]
        ]
    )


def sort_cities(top, all_cities):
    top_part = [c for c in top if c in all_cities]
    rest = sorted(c for c in all_cities if c not in top_part)
    return top_part + rest

def back_to_age_keyboard():
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="⬅ Назад", callback_data="back_to_age")]
        ]
    )

def cities_keyboard(cities, page=0, per_page=10):
    start = page * per_page
    end = start + per_page

    keyboard = []

    for city in cities[start:end]:
        keyboard.append([
            InlineKeyboardButton(text=city, callback_data=f"city_{city}")
        ])

    nav = []
    if page > 0:
        nav.append(
            InlineKeyboardButton(text="⬅ Назад", callback_data=f"cities_page_{page-1}")
        )
    if end < len(cities):
        nav.append(
            InlineKeyboardButton(text="➡ Далее", callback_data=f"cities_page_{page+1}")
        )

    if nav:
        keyboard.append(nav)

    keyboard.append([
        InlineKeyboardButton(text="❌ Нет моего города", callback_data="no_city")
    ])

    return InlineKeyboardMarkup(inline_keyboard=keyboard)


def citizenship_keyboard():
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="🇷🇺 Россия", callback_data="citizenship_ru")],
            [InlineKeyboardButton(text="🇧🇾 Беларусь", callback_data="citizenship_by")],
            [InlineKeyboardButton(text="🇰🇿 Казахстан", callback_data="citizenship_kz")],
            [InlineKeyboardButton(text="🇦🇲 Армения", callback_data="citizenship_am")],
            [InlineKeyboardButton(text="🇰🇬 Кыргызстан", callback_data="citizenship_kg")],
            [InlineKeyboardButton(text="Другое", callback_data="citizenship_other")],
        ]
    )


def delivery_keyboard():
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="🧍 Пешком", callback_data="delivery_foot")],
            [InlineKeyboardButton(text="🚲 Вело", callback_data="delivery_bike")],
            [InlineKeyboardButton(text="🚗 Авто", callback_data="delivery_car")],
        ]
    )


# ===============================
# START
# ===============================

@dp.message(CommandStart())
async def start(message: types.Message, state: FSMContext):
    await message.answer(
            "Узнайте, какие возможности есть для курьеров в вашем городе — всего 3 быстрых вопроса",
            reply_markup=InlineKeyboardMarkup(
                inline_keyboard=[
                    [InlineKeyboardButton(text="Хочу узнать✅", callback_data="start_next")]
                ]
            )
        )
    await state.set_state(Form.waiting_for_start)


@dp.callback_query(Form.waiting_for_start, lambda c: c.data == "start_next")
async def age_question(callback: types.CallbackQuery, state: FSMContext):
    await safe_edit(
    callback.message,
        "Вам есть 18 лет?",
        reply_markup=InlineKeyboardMarkup(
            inline_keyboard=[
                [
                    InlineKeyboardButton(text="Да✅", callback_data="age_yes"),
                    InlineKeyboardButton(text="Нет❌", callback_data="age_no")
                ]
            ]
        )
    )
    await state.set_state(Form.waiting_for_age)
    await callback.answer()


@dp.callback_query(Form.waiting_for_age, lambda c: c.data in ("age_yes", "age_no"))
async def age_answer(callback: types.CallbackQuery, state: FSMContext):
    if callback.data == "age_no":
        await safe_edit(
    callback.message,
            "Если тебе есть 16 лет, ты можешь работать курьером в некоторых городах:\n"
            "<b>Нижний Новгород, Самара, Ростов-на-Дону, Челябинск, Тверь, Сургут, Тюмень, Астрахань, Владивосток, Томск, Иваново, Сочи, Ставрополь, Ижевск, Калуга, Липецк, Барнаул, Сергиев Посад, Нижнекамск, Красноярск, Воронеж, Екатеринбург, Казань, Новороссийск, Тула, Набережные Челны, Ульяновск, Москва+МО, Санкт-Петербург+ЛО</b>\n\n"
            "Для оформления потребуется <b>свидетельство о рождении</b> и <b>согласие родителей</b>.\n\n",
            parse_mode="HTML",
            reply_markup=back_to_age_keyboard()
        )
        await state.set_state(Form.waiting_for_underage)
        await callback.answer()
        return

    await safe_edit(
    callback.message,
        "Выберите ваше гражданство",
        reply_markup=citizenship_keyboard()
    )
    await state.set_state(Form.waiting_for_citizenship)
    await callback.answer()

@dp.callback_query(Form.waiting_for_underage, lambda c: c.data == "back_to_age")
async def back_to_age(callback: types.CallbackQuery, state: FSMContext):
    await safe_edit(
    callback.message,
        "Вам есть 18 лет?",
        reply_markup=InlineKeyboardMarkup(
            inline_keyboard=[
                [
                    InlineKeyboardButton(text="Да✅", callback_data="age_yes"),
                    InlineKeyboardButton(text="Нет❌", callback_data="age_no")
                ]
            ]
        )
    )

    await state.set_state(Form.waiting_for_age)
    await callback.answer()



# ===============================
# ГРАЖДАНСТВО → ГОРОДА
# ===============================

@dp.callback_query(Form.waiting_for_citizenship)
async def citizenship_chosen(callback: types.CallbackQuery, state: FSMContext):
    citizenship_map = {
        "citizenship_ru": "Россия",
        "citizenship_by": "Беларусь",
        "citizenship_kz": "Казахстан",
        "citizenship_am": "Армения",
        "citizenship_kg": "Кыргызстан",
        "citizenship_other": "Другое",
    }

    citizenship = citizenship_map.get(callback.data)
    if not citizenship:
        await callback.answer()
        return

    citizenship_type = CITIZENSHIP_TYPE_MAP[citizenship]
    records = get_average_income()

    cities = filter_cities_by_citizenship(records, citizenship_type)
    cities = sort_cities(TOP_CITIES, cities)

    await state.update_data(
        citizenship=citizenship,
        citizenship_type=citizenship_type,
        cities=cities
    )

    await safe_edit(
    callback.message,
        "В каком городе вы планируете выполнять доставки?\nВыберите:",
        reply_markup=cities_keyboard(cities, page=0)
    )

    await state.set_state(Form.waiting_for_city)
    await callback.answer()


@dp.callback_query(Form.waiting_for_city, lambda c: c.data.startswith("cities_page_"))
async def cities_pagination(callback: types.CallbackQuery, state: FSMContext):
    if await state.get_state() != Form.waiting_for_city:
        await callback.answer()
        return
    page = int(callback.data.split("_")[-1])
    data = await state.get_data()
    cities = data.get("cities")
    if not cities:
        await callback.answer("Сценарий устарел. Нажмите /start", show_alert=True)
        return
    await safe_edit_markup(callback.message, cities_keyboard(cities, page)
    )
    await callback.answer()


@dp.callback_query(Form.waiting_for_city, lambda c: c.data.startswith("city_"))
async def city_chosen(callback: types.CallbackQuery, state: FSMContext):
    if await state.get_state() != Form.waiting_for_city:
        await callback.answer()
        return
    city = callback.data.replace("city_", "")
    await state.update_data(city=city)

    await safe_edit(
    callback.message,
        "Остался последний вопрос — и покажу доход\n"
        "Какой формат доставки вам подходит?",
        reply_markup=delivery_keyboard()
    )

    await state.set_state(Form.waiting_for_delivery)
    await callback.answer()


@dp.callback_query(Form.waiting_for_city, lambda c: c.data == "no_city")
async def no_city(callback: types.CallbackQuery, state: FSMContext):
    await safe_edit(
    callback.message,
        "К сожалению, в вашем городе пока нет найма 😔"
    )
    await state.clear()
    await callback.answer()

@dp.callback_query(Form.waiting_for_delivery, lambda c: c.data == "send_lead")
async def send_lead(callback: types.CallbackQuery, state: FSMContext):
    data = await state.get_data()

    if data.get("lead_sent"):
        await callback.answer()
        return

    if "city" not in data:
        await callback.answer("Сначала рассчитайте доход", show_alert=True)
        return
    user = callback.from_user

    await state.update_data(lead_sent=True)
    user = callback.from_user
    save_lead({
        **data,
        "user_id": user.id,
        "username": user.username
    })

    await safe_edit(
    callback.message,
        "Двигаемся дальше 😊\n\n"
        "➡️ Следующий шаг — короткая анкета и мини-обучение по работе с заказами.\n"
        "Ничего сложного, обычно занимает 15 минут.\n"
        "Готовы? Тогда начнём здесь 👇\nhttps://reg.eda.yandex.ru/?advertisement_campaign=forms_for_agents&user_invite_code=4fd8c46d41724e86a4448b0367951ddb&utm_content=blank",
        parse_mode="HTML"
    )

    await state.clear()
    await callback.answer()


# ===============================
# ДОХОД И КНОПКИ
# ===============================

# 🔹 Заменяем оба старых коллбэка delivery_chosen и income_buttons этим
@dp.callback_query(Form.waiting_for_delivery, lambda c: c.data.startswith("delivery_") or c.data in ["income_bonus", "income_faq", "income_recalc"])
async def income_flow(callback: types.CallbackQuery, state: FSMContext):
    if await state.get_state() != Form.waiting_for_delivery:
        await callback.answer()
        return
    data = await state.get_data()
    if not data or "city" not in data or "citizenship" not in data:
        await callback.answer("Сценарий устарел. Нажмите /start", show_alert=True)
        return
    # Если выбрали формат доставки
    if callback.data.startswith("delivery_"):
        delivery_map = {
            "delivery_foot": "foot",
            "delivery_bike": "bike",
            "delivery_car": "car",
        }
        delivery = delivery_map.get(callback.data)
        if not delivery:
            await callback.answer()
            return

        city = data["city"]
        citizenship = data["citizenship"]

        records = get_average_income()
        rec = next((r for r in records if r["city"] == city and r["delivery"] == delivery), None)

        if not rec:
            await callback.answer("Нет данных по выбранному формату", show_alert=True)
            await state.clear()
            return
        payout = "Выплаты: ежедневные" if citizenship in DAILY_PAYOUT_CITIZENSHIPS else "Выплаты: еженедельно"
        legal = "Оформление через партнёра сервиса — самозанятость" if citizenship in DAILY_PAYOUT_CITIZENSHIPS else "Оформление по договору через партнёра сервиса"

        # 🔹 Форматируем числа с пробелами
        day_income = f"{int(rec['day']):,}".replace(",", " ")
        month_avg_income = f"{int(rec['month_avg']):,}".replace(",", " ")
        month_max_income = f"{int(rec['month_max']):,}".replace(",", " ")

        # 🔹 СОХРАНЯЕМ В FSM (ВОТ ЭТО ДОБАВЛЯЕМ 👇)
        await state.update_data(
            delivery=DELIVERY_TITLES[delivery],
            day_income=day_income,
            month_avg=month_avg_income,
            month_max=month_max_income
        )

        doc_text = DOCUMENTS_BY_CITIZENSHIP.get(citizenship)
        text = (
            f"📍 Город: {city}\n\n"
            f"💵 Доход курьера ({DELIVERY_TITLES[delivery]}, средний):\n"
            f"• В день: {day_income} ₽\n"
            f"• В месяц: {month_avg_income} ₽\n"
            f"• Максимум в месяц: {month_max_income} ₽\n\n"
            f"{payout}\n"
            f"{legal}\n\n"
            f"📝 <b>Документы для оформления:</b>\n"
            f"{doc_text}"
        )

        # 🔹 Показываем доход с клавиатурой бонусов/FAQ/расчёта
        await safe_edit(
    callback.message,
            text,
            parse_mode="HTML",
            reply_markup=income_keyboard()
        )
        await state.set_state(Form.waiting_for_delivery)
        await callback.answer()
        return

    # Если нажали кнопки после расчёта
    if callback.data == "income_bonus":
        await safe_edit(
    callback.message,
            "🎁 <b>Бонусы для курьеров</b>\n\n"
            "• Яндекс Байк за 1 ₽\n"
            "• Комбо-обед за 95 ₽\n"
            "• Скидка 20% в Яндекс Лавке\n"
            "• Яндекс Плюс в подарок\n"
            "• 100% чаевых ваши\n"
            "• Промокод на Еду 300 ₽\n"
            "• Скидка 10% в Ленте\n"
            "• Бери Заряд бесплатно\n"
            "• Юридическая поддержка",
            parse_mode="HTML",
            reply_markup=income_keyboard()
        )
    elif callback.data == "income_faq":
        await safe_edit(
    callback.message,
            "❓ <b>Частые вопросы</b>\n\n"
            "• 🏫 <b>Нет опыта?</b>\n"
            "Не переживайте, обучение предоставляется. Освоиться быстро!\n\n"
            "• ⏰ <b>Какой график?</b>\n"
            "Свободный режим: сами выбираете удобные слоты. Сами выбираете в какой день работать. Слот - это смена на несколько часов. Можно отработать один слот или несколько сразу.\n\n"
            "• 💪 <b>Физически тяжело?</b>\n"
            "Лёгкие доставки, выбираете заказы по силам.\n\n"
            "• 📍 <b>Сложно ориентироваться?</b>\n"
            "Есть удобное навигационное приложение.\n\n"
            "• 🚶‍♂️ <b>Нет транспорта?</b>\n"
            "Можно пешком, на вело или общественном транспорте.\n\n"
            "• 🛡️ <b>Безопасно?</b>\n"
            "Страхование и поддержка на маршруте гарантируют безопасность.\n\n",
            parse_mode="HTML",
            reply_markup=income_keyboard()
        )
    elif callback.data == "income_recalc":
        await state.update_data(
            delivery=None,
            day_income=None,
            month_avg=None,
            month_max=None
        )
        await safe_edit(
    callback.message,
            "Какой формат доставки вам подходит?",
            reply_markup=delivery_keyboard()
        )
        await state.set_state(Form.waiting_for_delivery)

    await callback.answer()


# ===============================
# WEBHOOK
# ===============================

async def lifespan(app: FastAPI):
    await bot.set_webhook(f"{WEBHOOK_URL}/{BOT_TOKEN}")
    yield
    await bot.delete_webhook()

app = FastAPI(lifespan=lifespan)

@app.post(f"/{BOT_TOKEN}")
async def telegram_webhook(req: Request):
    update = Update.model_validate(await req.json())
    await dp.feed_update(bot, update)
    return {"ok": True}


if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=80)
