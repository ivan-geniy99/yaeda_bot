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
from table_income import average_income_ya_eda
import re

BOT_TOKEN = os.environ["BOT_TOKEN"]
WEBHOOK_URL = os.environ["WEBHOOK_URL"]

bot = Bot(token=BOT_TOKEN)
dp = Dispatcher(storage=MemoryStorage())

# FSM
class Form(StatesGroup):
    waiting_for_first_question = State()
    waiting_for_age_question = State()
    waiting_for_city = State()

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
            "Вопрос 2\n\nВ каком городе желаете работать?",
            reply_markup=types.ReplyKeyboardRemove()
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

    # Приведение к регистру для поиска (если нужно)
    user_city_lower = user_city.lower()

    # Ищем совпадения в кэше
    matched_records = [
        record for record in average_income_ya_eda
        if re.fullmatch(user_city_lower, record["city"].lower())
    ]

    if matched_records:
        # Если есть совпадения, выводим информацию
        response_lines = [f"{r['delivery']}: среднее {r['month_avg']}, макс {r['month_max']}" for r in matched_records]
        response_text = f"Город: {user_city}\nНайдено {len(matched_records)} вариантов доставки:\n" + "\n".join(response_lines)
    else:
        # Если город не найден в кэше
        response_text = f"Город {user_city} не найден в нашей базе доходов."

    await message.answer(
        response_text,
        reply_markup=types.ReplyKeyboardRemove()
    )
    await state.clear()

@asynccontextmanager
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
