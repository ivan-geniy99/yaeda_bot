import os
from fastapi import FastAPI, Request
from aiogram import Bot, Dispatcher, types
from aiogram.types import Update, InlineKeyboardMarkup, InlineKeyboardButton
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

# FSM
class Form(StatesGroup):
    waiting_for_first_question = State()
    waiting_for_age_question = State()
    waiting_for_city = State()
    waiting_for_citizenship = State()
    waiting_for_delivery_type = State()

# ===============================
# INLINE КНОПКИ
# ===============================

# Инлайн кнопка "Хорошо, поехали"
next_inline_keyboard = InlineKeyboardMarkup(
    inline_keyboard=[[InlineKeyboardButton(text="Хорошо, поехали✅", callback_data="next_start")]]
)

# Инлайн кнопки "Да/Нет"
yes_no_inline_keyboard = InlineKeyboardMarkup(
    inline_keyboard=[[InlineKeyboardButton(text="Да✅", callback_data="age_yes"),
                      InlineKeyboardButton(text="Нет❌", callback_data="age_no")]]
)

# Инлайн кнопки "Показать весь список городов"
city_list_inline_keyboard = InlineKeyboardMarkup(
    inline_keyboard=[[InlineKeyboardButton(text="Показать весь список городов📋", callback_data="show_all_cities")]]
)

# Инлайн кнопки с гражданством
def citizenship_keyboard():
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="🇷🇺 Россия", callback_data="citizenship_ru")],
            [InlineKeyboardButton(text="🇧🇾 Беларусь", callback_data="citizenship_by")],
            [InlineKeyboardButton(text="🇰🇿 Казахстан", callback_data="citizenship_kz")],
            [InlineKeyboardButton(text="🇦🇲 Армения", callback_data="citizenship_am")],
            [InlineKeyboardButton(text="🇰🇬 Кыргызстан", callback_data="citizenship_kg")],
            [InlineKeyboardButton(text="Другое", callback_data="citizenship_other")],
            [InlineKeyboardButton(text="⬅ Назад", callback_data="back_to_city_question")]
        ]
    )

# Инлайн кнопки с типом доставки
def delivery_type_keyboard():
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="🧍 Пешком", callback_data="delivery_walk")],
            [InlineKeyboardButton(text="🚲 Вело", callback_data="delivery_bike")],
            [InlineKeyboardButton(text="🚗 Авто", callback_data="delivery_car")],
            [InlineKeyboardButton(text="⬅ Назад", callback_data="back_to_citizenship_question")]
        ]
    )

# ===============================
# START
# ===============================
@dp.message(CommandStart())
async def cmd_start(message: types.Message, state: FSMContext):
    sent_msg = await message.answer(
        "Чтобы показать условия и доход — задам несколько коротких вопросов 👌",
        reply_markup=next_inline_keyboard
    )
    # Сохраняем ID последнего сообщения
    await state.update_data(last_message_id=sent_msg.message_id)
    await state.set_state(Form.waiting_for_first_question)

# ===============================
# CALLBACK: "Хорошо, поехали"
# ===============================
@dp.callback_query(lambda c: c.data == "next_start")
async def start_next(callback: types.CallbackQuery, state: FSMContext):
    chat_id = callback.message.chat.id
    sent_msg = await bot.edit_message_text(
        chat_id=chat_id,
        message_id=callback.message.message_id,
        text="Вам есть 18 лет?",
        reply_markup=yes_no_inline_keyboard
    )
    await state.update_data(last_message_id=sent_msg.message_id)
    await state.set_state(Form.waiting_for_age_question)
    await callback.answer()

# ===============================
# CALLBACK: Возраст "Да/Нет"
# ===============================
@dp.callback_query(lambda c: c.data in ["age_yes", "age_no"])
async def age_answer(callback: types.CallbackQuery, state: FSMContext):
    chat_id = callback.message.chat.id
    if callback.data == "age_yes":
        sent_msg = await bot.edit_message_text(
            chat_id=chat_id,
            message_id=callback.message.message_id,
            text="В каком городе вы планируете выполнять доставки?\n\nНапишите город или откройте список 👇",
            reply_markup=InlineKeyboardMarkup(
                inline_keyboard=[[InlineKeyboardButton(text="⬅ Назад", callback_data="back_to_age_question")]]
            )
        )
        await state.set_state(Form.waiting_for_city)
    else:
        sent_msg = await bot.edit_message_text(
            chat_id=chat_id,
            message_id=callback.message.message_id,
            text="Если вам есть 16 лет, то можно откликнуться на вакансию по ссылке:\nhttps://example.com",
            reply_markup=InlineKeyboardMarkup(
                inline_keyboard=[[InlineKeyboardButton(text="⬅ Назад", callback_data="back_to_age_question")]]
            )
        )
        await state.set_state(Form.waiting_for_age_question)

    await state.update_data(last_message_id=sent_msg.message_id)
    await callback.answer()

# ===============================
# MESSAGE: Ввод города
# ===============================
@dp.message(Form.waiting_for_city)
async def city_question(message: types.Message, state: FSMContext):
    user_city = message.text.strip()
    user_city_lower = user_city.lower()
    records = get_average_income()
    matched_records = [r for r in records if r["city"].lower() == user_city_lower]

    # Город найден
    if matched_records:
        sent_msg = await message.answer(
            "Какое у вас гражданство?",
            reply_markup=citizenship_keyboard()
        )
        await state.update_data(city=user_city, last_message_id=sent_msg.message_id)
        await state.set_state(Form.waiting_for_citizenship)
        return

    # Показать весь список городов
    if user_city == "Показать весь список городов📋":
        cities = sorted({r["city"] for r in records})
        response_text = "📍 Доступные города:\n\n" + ", ".join(cities) + \
                        "\n\n✍️ Скопируйте нужный город и отправьте его сообщением"
        await message.answer(response_text, reply_markup=None)
        return

    # Город не найден
    response_text = f"Я не смог найти город «{user_city}».\n\nПопробуйте написать ещё раз или откройте список городов 👇"
    sent_msg = await message.answer(response_text, reply_markup=city_list_inline_keyboard)
    await state.update_data(last_message_id=sent_msg.message_id)

# ===============================
# CALLBACK: Гражданство
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

    await state.update_data(citizenship=citizenship)
    data = await state.get_data()
    user_city = data.get("city")
    last_message_id = data.get("last_message_id")
    citizenship_type = CITIZENSHIP_TYPE_MAP.get(citizenship)
    records = get_average_income()
    city_records = [r for r in records if r["city"].lower() == user_city.lower()]

    if not city_records:
        sent_msg = await bot.send_message(callback.message.chat.id, "К сожалению, по этому городу нет данных 😔")
        await state.clear()
        await callback.answer()
        return

    # Проверка найма
    if (citizenship_type == "eaes" and city_records[0].get("eaes") != "TRUE") or \
        (citizenship_type == "not_rf" and city_records[0].get("not_rf") != "TRUE"):
    
        # Отправляем отдельное сообщение о временном отсутствии найма
        sent_msg = await bot.send_message(
            chat_id=callback.message.chat.id,
            text="❌ В выбранном городе временно нет найма.\n\nПопробуйте выбрать другой город.",
            reply_markup=InlineKeyboardMarkup(
                inline_keyboard=[[InlineKeyboardButton(text="⬅ Назад", callback_data="back_to_citizenship_question")]]
            )
        )
    
        # Сохраняем message_id для кнопки «Назад»
        await state.update_data(last_message_id=sent_msg.message_id)
        # Состояние остаётся citizenship
        await state.set_state(Form.waiting_for_citizenship)
        await callback.answer()
        return

    # Найм возможен — формат доставки
    # Сначала убираем кнопки с предыдущего сообщения
    await bot.edit_message_reply_markup(
        chat_id=callback.message.chat.id,
        message_id=last_message_id,
        reply_markup=None
    )

    # Отправляем новый вопрос отдельным сообщением
    sent_msg = await bot.send_message(
        chat_id=callback.message.chat.id,
        text="Остался последний вопрос — и покажу доход\nКакой формат доставки вам подходит?",
        reply_markup=delivery_type_keyboard()
    )
    await state.update_data(last_message_id=sent_msg.message_id)
    await state.set_state(Form.waiting_for_delivery_type)
    await callback.answer()

# ===============================
# CALLBACK: Формат доставки
# ===============================
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
    records = get_average_income()
    city_records = [r for r in records if r["city"].lower() == user_city.lower()]

    if not city_records:
        await callback.message.answer("К сожалению, по этому городу нет данных 😔")
        await state.clear()
        return

    matched_records = [r for r in records if r["city"].lower() == user_city.lower() and r["delivery"] == delivery_type]
    if not matched_records:
        await callback.message.answer("К сожалению, по выбранному формату нет данных 😔")
        await state.clear()
        return

    r = matched_records[0]
    payout_text = "Выплаты: ежедневные" if citizenship in DAILY_PAYOUT_CITIZENSHIPS else "Выплаты: еженедельные"
    legal_text = "Оформление через партнёра сервиса — самозанятость" if citizenship in DAILY_PAYOUT_CITIZENSHIPS else "Оформление по договору через партнёра сервиса"

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

    await callback.message.edit_reply_markup(reply_markup=None)
    await callback.message.answer(response_text)
    await callback.answer()
    await state.clear()

# ===============================
# CALLBACK: Универсальный "Назад"
# ===============================
@dp.callback_query(lambda c: c.data in ["back_to_age_question", "back_to_city_question", "back_to_citizenship_question"])
async def universal_back(callback: types.CallbackQuery, state: FSMContext):
    data = await state.get_data()
    last_message_id = data.get("last_message_id")
    chat_id = callback.message.chat.id

    if callback.data == "back_to_age_question":
        sent_msg = await bot.edit_message_text(
            chat_id=chat_id,
            message_id=last_message_id,
            text="Вам есть 18 лет?",
            reply_markup=yes_no_inline_keyboard
        )
        await state.set_state(Form.waiting_for_age_question)

    elif callback.data == "back_to_city_question":
        sent_msg = await bot.edit_message_text(
            chat_id=chat_id,
            message_id=last_message_id,
            text="В каком городе вы планируете выполнять доставки?\n\nНапишите город или откройте список 👇",
            reply_markup=InlineKeyboardMarkup(
                inline_keyboard=[[InlineKeyboardButton(text="⬅ Назад", callback_data="back_to_age_question")]]
            )
        )
        await state.set_state(Form.waiting_for_city)

    elif callback.data == "back_to_citizenship_question":
        sent_msg = await bot.edit_message_text(
            chat_id=chat_id,
            message_id=last_message_id,
            text="Какое у вас гражданство?",
            reply_markup=citizenship_keyboard()
        )
        await state.set_state(Form.waiting_for_citizenship)

    await state.update_data(last_message_id=sent_msg.message_id)
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
