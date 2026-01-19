import os
from contextlib import asynccontextmanager
from fastapi import FastAPI, Request
from aiogram import Bot, Dispatcher, types
from aiogram.types import ReplyKeyboardMarkup, KeyboardButton, Update
from aiogram.filters import CommandStart
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.fsm.state import StatesGroup, State
from aiogram.fsm.context import FSMContext
import uvicorn
from table_income import get_average_income
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton

BOT_TOKEN = os.environ["BOT_TOKEN"]
WEBHOOK_URL = os.environ["WEBHOOK_URL"]

bot = Bot(token=BOT_TOKEN)
dp = Dispatcher(storage=MemoryStorage())

DELIVERY_TITLES = {
    "foot": "🧍 Пешком",
    "bike": "🚲 Вело",
    "car": "🚗 Авто",
}

DAILY_PAYOUT_CITIZENSHIPS = {
    "Россия",
    "Беларусь",
    "Казахстан",
    "Армения",
    "Кыргызстан",
}

# FSM
class Form(StatesGroup):
    waiting_for_first_question = State()
    waiting_for_age_question = State()
    waiting_for_city = State()
    waiting_for_citizenship = State()  
    waiting_for_delivery_type = State()

# Клавиатура "Хорошо, поехали"
next_keyboard = ReplyKeyboardMarkup(
    keyboard=[[KeyboardButton(text="Хорошо, поехали✅")]],
    resize_keyboard=True
)

# Клавиатура "Да / Нет"
yes_no_keyboard = ReplyKeyboardMarkup(
    keyboard=[
        [KeyboardButton(text="Да✅"), KeyboardButton(text="Нет❌")]
    ],
    resize_keyboard=True
)

#Клавиатура "Показать весь список городов"
city_keyboard = ReplyKeyboardMarkup(
    keyboard=[[KeyboardButton(text="Показать весь список городов📋")]],
    resize_keyboard=True
)

#Инлайн кнопки с гражданством
citizenship_keyboard = InlineKeyboardMarkup(
    inline_keyboard=[
        [InlineKeyboardButton(text="🇷🇺 Россия", callback_data="citizenship_ru")],
        [InlineKeyboardButton(text="🇧🇾 Беларусь", callback_data="citizenship_by")],
        [InlineKeyboardButton(text="🇰🇿 Казахстан", callback_data="citizenship_kz")],
        [InlineKeyboardButton(text="🇦🇲 Армения", callback_data="citizenship_am")],
        [InlineKeyboardButton(text="🇰🇬 Кыргызстан", callback_data="citizenship_kg")],
        [InlineKeyboardButton(text="Другое", callback_data="citizenship_other")]
    ]
)

#Инлайн кнопки с типом доставки
delivery_type_keyboard = InlineKeyboardMarkup(
    inline_keyboard=[
        [InlineKeyboardButton(text="🧍 Пешком", callback_data="delivery_walk")],
        [InlineKeyboardButton(text="🚲 Вело", callback_data="delivery_bike")],
        [InlineKeyboardButton(text="🚗 Авто", callback_data="delivery_car")],
    ]
)

@dp.message(CommandStart())
async def cmd_start(message: types.Message, state: FSMContext):
    await message.answer(
        "Чтобы показать условия и доход — задам несколько коротких вопросов 👌",
        reply_markup=next_keyboard
    )
    await state.set_state(Form.waiting_for_first_question)

@dp.message(Form.waiting_for_first_question)
async def first_question(message: types.Message, state: FSMContext):
    if message.text == "Хорошо, поехали✅":
        await message.answer(
            "Вам есть 18 лет?",
            reply_markup=yes_no_keyboard
        )
        await state.set_state(Form.waiting_for_age_question)

@dp.message(Form.waiting_for_age_question)
async def age_question(message: types.Message, state: FSMContext):
    if message.text == "Да✅":
        await message.answer(
            "В каком городе вы планируете выполнять доставки?\n\n"
            "Напишите город или откройте список 👇",
            reply_markup=city_keyboard
        )
        await state.set_state(Form.waiting_for_city)

    elif message.text == "Нет❌":
        await message.answer(
            "Если вам есть 16 лет, то можно откликнуться на вакансию по ссылке:\n"
            "https://example.com",
            reply_markup=types.ReplyKeyboardRemove()
        )
        await state.clear()

@dp.message(Form.waiting_for_city)
async def city_question(message: types.Message, state: FSMContext):
    user_city = message.text.strip()
    user_city_lower = user_city.lower()

    records = get_average_income()

    matched_records = [
        r for r in records
        if r["city"].lower() == user_city_lower
    ]

    # 1. Город найден
    if matched_records:
        await state.update_data(city=user_city)

        await message.answer(
            "Какое у вас гражданство?",
            reply_markup=citizenship_keyboard
        )
        await state.set_state(Form.waiting_for_citizenship)
        return       

    # 2. Пользователь нажал кнопку «Показать весь список городов📋»
    if user_city == "Показать весь список городов📋":
        cities = sorted({r["city"] for r in records})
        response_text = (
            "📍 Доступные города:\n\n"
            + ", ".join(cities)
            + "\n\n✍️ Скопируйте нужный город и отправьте его сообщением"
        )
        await message.answer(response_text, reply_markup=types.ReplyKeyboardRemove())
        return

    # 3. Город не найден
    response_text = (
        f"Я не смог найти город «{user_city}».\n\n"
        "Попробуйте написать ещё раз или откройте список городов 👇"
    )
    reply_markup = ReplyKeyboardMarkup(
        keyboard=[[KeyboardButton(text="Показать весь список городов📋")]],
        resize_keyboard=True
    )

    await message.answer(response_text, reply_markup=reply_markup)
    
@asynccontextmanager
async def lifespan(app: FastAPI):
    await bot.set_webhook(f"{WEBHOOK_URL}/{BOT_TOKEN}")
    yield
    await bot.delete_webhook()

app = FastAPI(lifespan=lifespan)

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

    await state.update_data(citizenship=citizenship)
    # убрать инлайн-кнопки у предыдущего сообщения
    await callback.message.edit_reply_markup(reply_markup=None)
    await callback.message.answer(
        "Остался последний вопрос — и покажу доход\nКакой формат доставки вам подходит?",
        reply_markup=delivery_type_keyboard
    )

    await state.set_state(Form.waiting_for_delivery_type)
    await callback.answer()

@dp.callback_query(Form.waiting_for_delivery_type)
async def delivery_type_chosen(callback: types.CallbackQuery, state: FSMContext):
    delivery_map = {
        "delivery_walk": "foot",
        "delivery_bike": "bike",
        "delivery_car": "car",
    }

    delivery_type = delivery_map.get(callback.data)

    if not delivery_type:
        await callback.answer()
        return

    data = await state.get_data()
    user_city = data.get("city")
    citizenship = data.get("citizenship")
    if citizenship in DAILY_PAYOUT_CITIZENSHIPS:
        payout_text = "Выплаты: ежедневные"
        legal_text = "Оформление через партнёра сервиса - самозанятость"
    else:
        payout_text = "Выплаты: еженедельные"
        legal_text = "Оформление по договору через партнёра сервиса"    
    records = get_average_income()

    matched_records = [
    r for r in records
    if r["city"].lower() == user_city.lower()
    and r["delivery"] == delivery_type
    ]

    if not matched_records:
        await callback.message.answer(
            "К сожалению, по выбранному формату нет данных 😔"
        )
        await state.clear()
        return

    r = matched_records[0]

    response_text = (
    f"📍 Доход курьера в городе: {user_city}\n"
    f"📍 Формат: {DELIVERY_TITLES[delivery_type]}\n\n"
    f"💰 Доход:\n"
    f"Средний в день — {r['day']} ₽\n"
    f"Средний в месяц — {r['month_avg']} ₽\n"
    f"Максимум в месяц — {r['month_max']} ₽\n\n"
    f"{payout_text}\n"
    f"{legal_text}\n"
)
    await callback.message.edit_reply_markup(reply_markup=None)  # убираем кнопки
    await callback.message.answer(
        response_text,
        reply_markup=types.ReplyKeyboardRemove()
    )

    await callback.answer()
    await state.clear()

@app.post(f"/{BOT_TOKEN}")
async def telegram_webhook(req: Request):
    update = Update.model_validate(await req.json())
    await dp.feed_update(bot, update)
    return {"ok": True}

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=80)
