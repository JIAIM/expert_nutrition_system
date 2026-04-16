from aiogram import Router, F
from aiogram.types import Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.fsm.context import FSMContext
from database.connection import get_db_connection
from database.queries import get_categories, get_ingredients_by_category, get_smart_recipes
from core.inference import generate_expert_explanation

router = Router()


@router.message(F.text == "Що в холодильнику?")
async def start_inventory(message: Message, state: FSMContext):
    await state.update_data(selected_ingredients=[])
    await show_categories(message)


async def show_categories(event):
    conn = get_db_connection()
    if not conn:
        return
    cats = get_categories(conn)
    conn.close()

    kb = []
    # Розбиваємо категорії по 2 в ряд для краси
    for i in range(0, len(cats), 2):
        row = [InlineKeyboardButton(text=f"📁 {cats[i]}", callback_data=f"cat:{cats[i]}")]
        if i + 1 < len(cats):
            row.append(InlineKeyboardButton(text=f"📁 {cats[i + 1]}", callback_data=f"cat:{cats[i + 1]}"))
        kb.append(row)

    kb.append([InlineKeyboardButton(text="🔍 ПІДІБРАТИ СТРАВУ", callback_data="search_recipes")])
    markup = InlineKeyboardMarkup(inline_keyboard=kb)
    text = "Оберіть категорію та додайте продукти, які у вас є:"

    if isinstance(event, CallbackQuery):
        await event.message.edit_text(text, reply_markup=markup)
    else:
        await event.answer(text, reply_markup=markup)


@router.callback_query(F.data.startswith("cat:"))
async def show_products(call: CallbackQuery):
    category = call.data.split(":")[1]

    conn = get_db_connection()
    products = get_ingredients_by_category(conn, category)
    conn.close()

    kb = []
    for prod in products:
        cb_data = f"add:{prod['ingredient_id']}"
        kb.append([InlineKeyboardButton(text=f"➕ {prod['name']}", callback_data=cb_data)])

    kb.append([InlineKeyboardButton(text="◀️ Назад", callback_data="back_cat")])

    await call.message.edit_text(
        f"Категорія: **{category}**\nДодайте продукти:",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=kb),
        parse_mode="Markdown"
    )
    await call.answer()


@router.callback_query(F.data.startswith("add:"))
async def add_product(call: CallbackQuery, state: FSMContext):
    prod_id = int(call.data.split(":")[1])

    data = await state.get_data()
    selected = data.get("selected_ingredients", [])

    if prod_id not in selected:
        selected.append(prod_id)
        await state.update_data(selected_ingredients=selected)
        await call.answer("✅ Додано в кошик!", show_alert=False)
    else:
        await call.answer("⚠️ Вже є у списку!", show_alert=False)


@router.callback_query(F.data == "back_cat")
async def back_to_cats(call: CallbackQuery):
    await show_categories(call)


@router.callback_query(F.data == "search_recipes")
async def search_recipes(call: CallbackQuery, state: FSMContext):
    data = await state.get_data()
    selected = data.get("selected_ingredients", [])

    if not selected:
        await call.answer("❌ Ви не обрали жодного продукту!", show_alert=True)
        return

    conn = get_db_connection()
    # Викликаємо наш новий розумний пошук
    recipes, user_goal = get_smart_recipes(conn, selected, call.from_user.id)
    conn.close()

    if recipes:
        response = "🎉 **Ось що я підібрав для вас:**\n\n"
        for recipe in recipes:
            response += f"🍳 **{recipe['title']}** (~{recipe['total_calories_base']} ккал)\n"
            response += f"📖 Як готувати: {recipe['instructions']}\n"

            # Генеруємо експертний висновок
            explanation = generate_expert_explanation(
                goal=user_goal,
                calories=recipe['total_calories_base'],
                missing_ingredients=recipe['missing_ingredients']
            )
            response += f"{explanation}\n\n"
            response += "➖➖➖➖➖➖➖➖➖➖\n"

        await call.message.edit_text(response, parse_mode="Markdown")
    else:
        await call.message.edit_text(
            "😔 Навіть з частковим збігом я нічого не знайшов. Додайте ще кілька базових продуктів (яйця, борошно, м'ясо).")

    await call.answer()