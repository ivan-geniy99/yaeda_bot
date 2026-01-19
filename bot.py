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
import re
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton

BOT_TOKEN = os.environ["BOT_TOKEN"]
WEBHOOK_URL = os.environ["WEBHOOK_URL"]

bot = Bot(token=BOT_TOKEN)
dp = Dispatcher(storage=MemoryStorage())

# FSM
class Form(StatesGroup):
    waiting_for_first_question = State()
    waiting_for_age_question = State()
    waiting_for_city = State()
    waiting_for_citizenship = State()  # ← новое
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

@dp.message(CommandStart())
async def cmd_start(message: types.Message, state: FSMContext):
    await message.answer(
        "Чтобы показать условия — ответьте на 3 вопроса.",
        reply_markup=next_keyboard
    )
    await state.set_state(Form.waiting_for_first_question)

@dp.message(Form.waiting_for_first_question)
async def first_question(message: types.Message, state: FSMContext):
    if message.text == "Хорошо, поехали✅":
        await message.answer(
            "Вопрос 1\n\nВам есть 18 лет?",
            reply_markup=yes_no_keyboard
        )
        await state.set_state(Form.waiting_for_age_question)

@dp.message(Form.waiting_for_age_question)
async def age_question(message: types.Message, state: FSMContext):
    if message.text == "Да✅":
        await message.answer(
            "Вопрос 2\n\nВ каком городе желаете работать?\n\n"
            "Вы можете написать город вручную или открыть список 👇",
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
            "Вопрос 3 из 3\n\nКакое у вас гражданство?",
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
    }

    citizenship = citizenship_map.get(callback.data)

    if not citizenship:
        await callback.answer()
        return

    data = await state.get_data()
    user_city = data.get("city")

    records = get_average_income()

    matched_records = [
        r for r in records
        if r["city"].lower() == user_city.lower()
    ]

    response_lines = [
        f"{r['delivery']}: среднее {r['month_avg']}, макс {r['month_max']}"
        for r in matched_records
    ]

    response_text = (
        f"Город: {user_city}\n"
        f"Гражданство: {citizenship}\n\n"
        f"Найдено {len(matched_records)} вариантов доставки:\n"
        + "\n".join(response_lines)
    )

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
