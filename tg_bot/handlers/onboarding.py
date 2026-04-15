from aiogram import Router
from aiogram.types import Message, ReplyKeyboardMarkup, KeyboardButton
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from tg_bot.states import Onboarding
from core.calculator import calculate_daily_targets
from database.connections import get_db_connection
from database.queries import upsert_user

router = Router()


def make_kb(items):
    return ReplyKeyboardMarkup(
        keyboard=[[KeyboardButton(text=item)] for item in items],
        resize_keyboard=True
    )


@router.message(Command("start"))
async def cmd_start(message: Message, state: FSMContext):
    await message.answer(
        "Привіт! Я експертна система харчування. Вкажіть вашу стать:",
        reply_markup=make_kb(["Чоловік", "Жінка"])
    )
    await state.set_state(Onboarding.gender)


@router.message(Onboarding.gender)
async def process_gender(message: Message, state: FSMContext):
    await state.update_data(gender=message.text)
    await message.answer("Введіть ваш вік (у роках):")
    await state.set_state(Onboarding.age)


@router.message(Onboarding.age)
async def process_age(message: Message, state: FSMContext):
    try:
        await state.update_data(age=int(message.text))
        await message.answer("Введіть вашу вагу (в кг):")
        await state.set_state(Onboarding.weight)
    except ValueError:
        await message.answer("Будь ласка, введіть число.")


@router.message(Onboarding.weight)
async def process_weight(message: Message, state: FSMContext):
    try:
        await state.update_data(weight=float(message.text))
        await message.answer("Введіть ваш зріст (у см):")
        await state.set_state(Onboarding.height)
    except ValueError:
        await message.answer("Будь ласка, введіть число.")


@router.message(Onboarding.height)
async def process_height(message: Message, state: FSMContext):
    try:
        await state.update_data(height=float(message.text))
        await message.answer(
            "Оберіть рівень активності:",
            reply_markup=make_kb(["1.2 (Сидячий)", "1.375 (Легка)", "1.55 (Середня)", "1.725 (Висока)"])
        )
        await state.set_state(Onboarding.activity)
    except ValueError:
        await message.answer("Будь ласка, введіть число.")


@router.message(Onboarding.activity)
async def process_activity(message: Message, state: FSMContext):
    activity_val = float(message.text.split()[0])
    await state.update_data(activity=activity_val)
    await message.answer(
        "Яка ваша мета?",
        reply_markup=make_kb(["Схуднення", "Підтримка", "Набір маси"])
    )
    await state.set_state(Onboarding.goal)


@router.message(Onboarding.goal)
async def process_goal(message: Message, state: FSMContext):
    data = await state.get_data()
    gender = data['gender']
    age = data['age']
    weight = data['weight']
    height = data['height']
    activity = data['activity']
    goal = message.text

    targets = calculate_daily_targets(gender, weight, height, age, activity, goal)

    conn = get_db_connection()
    if conn:
        upsert_user(
            conn, message.from_user.id, gender, age, weight, height, activity, goal, targets
        )
        conn.close()

    await message.answer(
        f"Анкету збережено!\nВаша добова норма: {targets['calories']} ккал.\n"
        f"Б: {targets['proteins']}г, Ж: {targets['fats']}г, В: {targets['carbs']}г.",
        reply_markup=make_kb(["Що в холодильнику?"])
    )
    await state.clear()