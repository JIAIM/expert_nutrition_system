from aiogram import Router, F
from aiogram.types import Message, ReplyKeyboardMarkup, KeyboardButton
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from tg_bot.states import Onboarding
from core.calculator import calculate_daily_targets
from database.connection import get_db_connection
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
        "Привіт! Я експертна система харчування.\n"
        "💡 *Підказка: якщо захочете змінити свої дані в майбутньому, просто напишіть /reset*\n\n"
        "Вкажіть вашу стать:",
        reply_markup=make_kb(["Чоловік", "Жінка"]),
        parse_mode="Markdown"
    )
    await state.set_state(Onboarding.gender)


def get_main_menu():
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="🍳 Підібрати рецепт"), KeyboardButton(text="🛒 Мій холодильник")],
            [KeyboardButton(text="⚙️ Змінити параметри"), KeyboardButton(text="🎯 Змінити ціль")]
        ],
        resize_keyboard=True
    )


@router.message(Command("reset"))
async def cmd_reset(message: Message, state: FSMContext):
    await state.clear()
    await message.answer(
        "🔄 Ваші дані скинуто! Почнемо спочатку. Вкажіть вашу стать:",
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

        text = (
            "Оберіть ваш рівень фізичної активності:\n\n"
            "🛋 **1.2 (Сидячий)** - мінімум руху, робота за комп'ютером, відсутність тренувань.\n"
            "🚶‍♂️ **1.375 (Легка)** - легкі тренування 1-3 рази на тиждень або щоденні прогулянки.\n"
            "🏃‍♂️ **1.55 (Середня)** - тренування 3-5 разів на тиждень, активний спосіб життя.\n"
            "🏋️‍♂️ **1.725 (Висока)** - інтенсивні тренування 6-7 разів на тиждень або важка фізична робота."
        )

        await message.answer(
            text,
            reply_markup=make_kb(["1.2 (Сидячий)", "1.375 (Легка)", "1.55 (Середня)", "1.725 (Висока)"]),
            parse_mode="Markdown"
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

    expert_text = (
        f"✅ **Анкету збережено!**\n\n"
        f"Ваша базова потреба розрахована за науковою формулою Міффліна-Сан Жеора з урахуванням активності.\n"
        f"🔥 **Добова норма:** {targets['calories']} ккал.\n\n"
        f"📊 **Чому такий розподіл БЖУ (1г жиру = 9 ккал, 1г білка/вуглеводів = 4 ккал):**\n"
        f"🥩 **Білки ({targets['proteins']}г)**: 30% калорійності. Це будівельний матеріал для м'язів, імунітету та шкіри.\n"
        f"🥑 **Жири ({targets['fats']}г)**: 30% калорійності. Критично важливі для правильної роботи гормональної системи.\n"
        f"🌾 **Вуглеводи ({targets['carbs']}г)**: 40% калорійності. Ваше головне джерело енергії для роботи мозку та тіла.\n\n"
        f"Що будемо робити далі?"
    )

    await message.answer(expert_text, reply_markup=get_main_menu(), parse_mode="Markdown")
    await state.clear()


# Додаємо обробники для швидкої зміни параметрів.
@router.message(F.text == "⚙️ Змінити параметри")
async def btn_change_params(message: Message, state: FSMContext):
    await state.clear()
    await message.answer("Почнемо спочатку. Вкажіть вашу стать:", reply_markup=make_kb(["Чоловік", "Жінка"]))
    await state.set_state(Onboarding.gender)


@router.message(F.text == "🎯 Змінити ціль")
async def btn_change_goal(message: Message, state: FSMContext):
    await state.clear()
    await message.answer(
        "Щоб правильно перерахувати норму калорій під нову ціль, мені потрібно оновити ваші поточні параметри (адже ваша вага могла змінитись).\n\n"
        "Вкажіть вашу стать:",
        reply_markup=make_kb(["Чоловік", "Жінка"])
    )
    await state.set_state(Onboarding.gender)