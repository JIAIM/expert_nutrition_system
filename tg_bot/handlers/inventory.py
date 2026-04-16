from aiogram import Router, F
from aiogram.types import Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.fsm.context import FSMContext
from database.connection import get_db_connection
from database.queries import get_categories, get_ingredients_by_category, get_smart_recipes, get_ingredient_ids_by_names
from core.inference import generate_expert_explanation

router = Router()


# ================= MENU HANDLERS =================
@router.message(F.text == "🍳 Підібрати рецепт")
async def start_inventory(message: Message, state: FSMContext):
    # Не очищаємо холодильник, щоб продукти зберігалися між пошуками
    data = await state.get_data()
    if "selected_ingredients" not in data:
        await state.update_data(selected_ingredients=[])
    await show_categories(message)


@router.message(F.text == "🛒 Мій холодильник")
async def show_fridge(message: Message, state: FSMContext):
    data = await state.get_data()
    selected_ids = data.get("selected_ingredients", [])

    if not selected_ids:
        await message.answer(
            "Ваш холодильник порожній! 💨\nНатисніть '🍳 Підібрати рецепт', щоб додати продукти, або просто напишіть їх назви текстом (через кому).")
        return

    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT ingredient_id, name FROM ingredients WHERE ingredient_id = ANY(%s);", (selected_ids,))
    products = cursor.fetchall()
    conn.close()

    kb = []
    for prod in products:
        # Кнопка для видалення конкретного продукту
        kb.append(
            [InlineKeyboardButton(text=f"❌ Видалити: {prod['name']}", callback_data=f"del:{prod['ingredient_id']}")])

    kb.append([InlineKeyboardButton(text="🗑 Очистити все", callback_data="clear_fridge")])
    kb.append([InlineKeyboardButton(text="🔍 ПІДІБРАТИ СТРАВУ", callback_data="search_recipes")])

    await message.answer(
        "🧊 **Ваш поточний холодильник:**\n*(Також ви можете просто написати назву продукту в чат, щоб додати його)*",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=kb), parse_mode="Markdown")


# Ручне введення продуктів текстом
@router.message(F.text & ~F.text.startswith("/"))
async def manual_add_product(message: Message, state: FSMContext):
    # Ігноруємо кнопки системного меню
    if message.text in ["🍳 Підібрати рецепт", "🛒 Мій холодильник", "⚙️ Змінити параметри", "🎯 Змінити ціль",
                        "Схуднення", "Підтримка", "Набір маси"]:
        return

    product_names = [p.strip() for p in message.text.split(',')]
    conn = get_db_connection()
    found_ids = get_ingredient_ids_by_names(conn, product_names)
    conn.close()

    if not found_ids:
        await message.answer(
            "❌ Я не знайшов таких продуктів у базі. Перевірте орфографію або оберіть їх через меню категорій.")
        return

    data = await state.get_data()
    selected = data.get("selected_ingredients", [])

    added_count = 0
    for pid in found_ids:
        if pid not in selected:
            selected.append(pid)
            added_count += 1

    await state.update_data(selected_ingredients=selected)
    await message.answer(
        f"✅ Додано {added_count} нових продуктів до холодильника!\nЗайдіть у '🛒 Мій холодильник', щоб перевірити.")


# ================= FRIDGE MANAGEMENT =================
@router.callback_query(F.data.startswith("del:"))
async def delete_product(call: CallbackQuery, state: FSMContext):
    prod_id = int(call.data.split(":")[1])
    data = await state.get_data()
    selected = data.get("selected_ingredients", [])

    if prod_id in selected:
        selected.remove(prod_id)
        await state.update_data(selected_ingredients=selected)
        await call.answer("🗑 Продукт видалено!")
        # Оновлюємо вікно холодильника
        await show_fridge(call.message, state)
    else:
        await call.answer("Помилка")


@router.callback_query(F.data == "clear_fridge")
async def clear_fridge(call: CallbackQuery, state: FSMContext):
    await state.update_data(selected_ingredients=[])
    await call.message.edit_text("💨 Холодильник повністю очищено!")
    await call.answer()


# ================= CATEGORY LOGIC =================
async def show_categories(event):
    conn = get_db_connection()
    if not conn:
        return
    cats = get_categories(conn)
    conn.close()

    kb = []
    for i in range(0, len(cats), 2):
        row = [InlineKeyboardButton(text=f"📁 {cats[i]}", callback_data=f"cat:{cats[i]}")]
        if i + 1 < len(cats):
            row.append(InlineKeyboardButton(text=f"📁 {cats[i + 1]}", callback_data=f"cat:{cats[i + 1]}"))
        kb.append(row)

    kb.append([InlineKeyboardButton(text="🛒 ДО ХОЛОДИЛЬНИКА", callback_data="open_fridge")])
    markup = InlineKeyboardMarkup(inline_keyboard=kb)
    text = "Оберіть категорію та додайте продукти:"

    if isinstance(event, CallbackQuery):
        await event.message.edit_text(text, reply_markup=markup)
    else:
        await event.answer(text, reply_markup=markup)


@router.callback_query(F.data == "open_fridge")
async def open_fridge_cb(call: CallbackQuery, state: FSMContext):
    await show_fridge(call.message, state)
    await call.answer()


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
        f"Категорія: **{category}**",
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
        await call.answer("✅ Додано в холодильник!", show_alert=False)
    else:
        await call.answer("⚠️ Вже є у холодильнику!", show_alert=False)


@router.callback_query(F.data == "back_cat")
async def back_to_cats(call: CallbackQuery):
    await show_categories(call)


# ================= SEARCH RECIPES (INFERENCE ENGINE) =================
@router.callback_query(F.data == "search_recipes")
async def search_recipes(call: CallbackQuery, state: FSMContext):
    data = await state.get_data()
    selected = data.get("selected_ingredients", [])

    if not selected:
        await call.answer("❌ Холодильник порожній!", show_alert=True)
        return

    conn = get_db_connection()
    recipes, user_goal = get_smart_recipes(conn, selected, call.from_user.id)
    conn.close()

    if recipes:
        response = "🎉 **Ось що я підібрав для вас:**\n\n"
        for recipe in recipes:
            response += f"🍳 **{recipe['title']}** (~{recipe['total_calories_base']} ккал)\n"
            response += f"📖 Як готувати: {recipe['instructions']}\n"

            explanation = generate_expert_explanation(
                goal=user_goal,
                calories=recipe['total_calories_base'],
                missing_ingredients=recipe['missing_ingredients'],
                matched_names=recipe['matched_names']
            )
            response += f"{explanation}\n\n"
            response += "➖➖➖➖➖➖➖➖➖➖\n"

        await call.message.edit_text(response, parse_mode="Markdown")
    else:
        await call.message.edit_text(
            "😔 Навіть з частковим збігом я нічого не знайшов. Спробуйте додати ще кілька базових продуктів (яйця, крупи, м'ясо).")

    await call.answer()