import os
from fastapi import FastAPI, Request
from aiogram import Bot, Dispatcher, types
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton, Update
from aiogram.filters import CommandStart
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.fsm.state import StatesGroup, State
from aiogram.fsm.context import FSMContext
import uvicorn

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
                text="📝 Оставить заявку",
                url="https://example.com/apply"  # ссылка-рыба
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
        "Узнайте, какие возможности есть для курьеров в вашем городе — всего 3 быстрых вопроса 👌",
        reply_markup=InlineKeyboardMarkup(
            inline_keyboard=[
                [InlineKeyboardButton(text="Хочу узнать✅", callback_data="start_next")]
            ]
        )
    )
    await state.set_state(Form.waiting_for_start)


@dp.callback_query(lambda c: c.data == "start_next")
async def age_question(callback: types.CallbackQuery, state: FSMContext):
    await callback.message.edit_text(
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


@dp.callback_query(lambda c: c.data in ("age_yes", "age_no"))
async def age_answer(callback: types.CallbackQuery, state: FSMContext):
    if callback.data == "age_no":
        await callback.message.edit_text(
            "Если вам есть 16 лет, можно откликнуться по ссылке:\nhttps://example.com",
            reply_markup=back_to_age_keyboard()
        )
        await state.set_state(Form.waiting_for_underage)
        await callback.answer()
        return

    await callback.message.edit_text(
        "Выберите ваше гражданство",
        reply_markup=citizenship_keyboard()
    )
    await state.set_state(Form.waiting_for_citizenship)
    await callback.answer()

@dp.callback_query(Form.waiting_for_underage, lambda c: c.data == "back_to_age")
async def back_to_age(callback: types.CallbackQuery, state: FSMContext):
    await callback.message.edit_text(
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

    await callback.message.edit_text(
        "В каком городе вы планируете выполнять доставки?\nВыберите:",
        reply_markup=cities_keyboard(cities, page=0)
    )

    await state.set_state(Form.waiting_for_city)
    await callback.answer()


@dp.callback_query(lambda c: c.data.startswith("cities_page_"))
async def cities_pagination(callback: types.CallbackQuery, state: FSMContext):
    page = int(callback.data.split("_")[-1])
    data = await state.get_data()
    cities = data["cities"]

    await callback.message.edit_reply_markup(
        reply_markup=cities_keyboard(cities, page)
    )
    await callback.answer()


@dp.callback_query(lambda c: c.data.startswith("city_"), Form.waiting_for_city)
async def city_chosen(callback: types.CallbackQuery, state: FSMContext):
    city = callback.data.replace("city_", "")
    await state.update_data(city=city)

    await callback.message.edit_text(
        "Остался последний вопрос — и покажу доход\n"
        "Какой формат доставки вам подходит?",
        reply_markup=delivery_keyboard()
    )

    await state.set_state(Form.waiting_for_delivery)
    await callback.answer()


@dp.callback_query(lambda c: c.data == "no_city")
async def no_city(callback: types.CallbackQuery, state: FSMContext):
    await callback.message.edit_text(
        "К сожалению, в вашем городе пока нет найма 😔"
    )
    await state.clear()
    await callback.answer()

# ===============================
# ДОХОД И КНОПКИ
# ===============================

# 🔹 Заменяем оба старых коллбэка delivery_chosen и income_buttons этим
@dp.callback_query(lambda c: c.data.startswith("delivery_") or c.data in ["income_bonus", "income_faq", "income_recalc"])
async def income_flow(callback: types.CallbackQuery, state: FSMContext):
    data = await state.get_data()

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
            await callback.message.answer("Нет данных по выбранному формату 😔")
            await state.clear()
            return

        payout = "Выплаты: ежедневные" if citizenship in DAILY_PAYOUT_CITIZENSHIPS else "Выплаты: еженедельно"
        legal = "Оформление через партнёра сервиса — самозанятость" if citizenship in DAILY_PAYOUT_CITIZENSHIPS else "Оформление по договору через партнёра сервиса"

        # 🔹 Форматируем числа с пробелами
        day_income = f"{int(rec['day']):,}".replace(",", " ")
        month_avg_income = f"{int(rec['month_avg']):,}".replace(",", " ")
        month_max_income = f"{int(rec['month_max']):,}".replace(",", " ")

        # 🔹 Цепляющая фраза про бонус, только если город в списке
        bonus_text = ""
        if city in bonus_cities:
            bonus_text = "🎁 Новым курьерам в этом городе: 10 000 ₽ сверху за первые 35 заказов!\n\n"
        text = (
            f"📍 Город: {city}\n"
            f"📦 Формат: {DELIVERY_TITLES[delivery]}\n\n"
            f"{bonus_text}"  # 🔹 вставляем бонус
            f"💵 Доход курьера:\n"
            f"• В день: {day_income} ₽\n"
            f"• В месяц: {month_avg_income} ₽\n"
            f"• Макс/мес: {month_max_income} ₽\n\n"
            f"{payout}\n"
            f"{legal}"
        )

        # 🔹 Показываем доход с клавиатурой бонусов/FAQ/расчёта
        await callback.message.edit_text(
            text,
            reply_markup=income_keyboard()
        )
        await state.set_state(Form.waiting_for_delivery)
        await callback.answer()
        return

    # Если нажали кнопки после расчёта
    if callback.data == "income_bonus":
        await callback.message.edit_text(
            "🎁 Бонусы для курьеров\n\nБонус 10 000 ₽ за первые 35 заказов\nв течение 10 дней сверх основного дохода.",
            reply_markup=income_keyboard()
        )
    elif callback.data == "income_faq":
        await callback.message.edit_text(
            "❓ Частые вопросы\n\n1. Как часто выплаты?\n— ежедневно или еженедельно\n2. Можно ли совмещать?\n— да, график свободный\n3. Нужен ли опыт?\n— нет, обучаем",
            reply_markup=income_keyboard()
        )
    elif callback.data == "income_recalc":
        await callback.message.edit_text(
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
