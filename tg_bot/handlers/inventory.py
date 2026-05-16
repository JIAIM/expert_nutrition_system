from aiogram import Router, F
from aiogram.types import Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.fsm.context import FSMContext
from database.connection import get_db_connection
from database.queries import get_categories, get_ingredients_by_category, get_smart_recipes, get_ingredient_ids_by_names
from core.inference import generate_expert_explanation
# Імпортуємо наш сервіс JSON
from core.json_storage import save_fridge_to_json, load_fridge_from_json

router = Router()


async def sync_fridge_state(tg_id: int, state: FSMContext) -> list:
    """Допоміжна функція для ініціалізації та синхронізації стану холодильника"""
    data = await state.get_data()
    selected = data.get("selected_ingredients")

    # Якщо в FSM (оперативній пам'яті) пусто, завантажуємо з JSON (файлу)
    if selected is None:
        selected = load_fridge_from_json(tg_id)
        await state.update_data(selected_ingredients=selected)
    return selected


# ================= MENU HANDLERS =================
@router.message(F.text == "🍳 Підібрати рецепт")
async def start_recipe_search_from_menu(message: Message, state: FSMContext):
    selected = await sync_fridge_state(message.from_user.id, state)

    if not selected:
        await message.answer("❌ Ваш холодильник порожній! Давайте спочатку додамо продукти.")
        await show_categories(message)
        return

    conn = get_db_connection()
    recipes, user_goal = get_smart_recipes(conn, selected, message.from_user.id)
    conn.close()

    if recipes:
        response = "🎉 **Ось що я підібрав для вас:**\n\n"
        for recipe in recipes:
            response += f"🍳 **{recipe['title']}** (~{recipe['total_calories_base']} ккал)\n"
            response += f"📖 Як готувати: {recipe['instructions']}\n"

            # Об'єднуємо всі інгредієнти для повноцінного експертного аналізу
            matched = recipe['matched_names'] if recipe['matched_names'] else []
            missing = recipe['missing_ingredients'] if recipe['missing_ingredients'] else []
            all_ingredients = matched + missing

            explanation = generate_expert_explanation(
                goal=user_goal,
                calories=recipe['total_calories_base'],
                missing_ingredients=missing,
                matched_names=all_ingredients
            )
            response += f"{explanation}\n\n"
            response += "➖➖➖➖➖➖➖➖➖➖\n"

        await message.answer(response, parse_mode="Markdown")
    else:
        await message.answer(
            "😔 Навіть з частковим збігом я нічого не знайшов. Спробуйте додати ще кілька базових продуктів (яйця, крупи, м'ясо)."
        )


@router.message(F.text == "🛒 Мій холодильник")
async def show_fridge(message: Message, state: FSMContext):
    selected_ids = await sync_fridge_state(message.from_user.id, state)

    if not selected_ids:
        await message.answer(
            "Ваш холодильник порожній! 💨\nНатисніть '📁 Відкрити каталог', щоб додати продукти, або просто напишіть їх назви текстом (через кому).",
            reply_markup=InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text="📁 Відкрити каталог", callback_data="open_categories")]
            ])
        )
        return

    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT ingredient_id, name FROM ingredients WHERE ingredient_id = ANY(%s);", (selected_ids,))
    products = cursor.fetchall()
    conn.close()

    kb = []
    for prod in products:
        kb.append(
            [InlineKeyboardButton(text=f"❌ Видалити: {prod['name']}", callback_data=f"del:{prod['ingredient_id']}")])

    kb.append([InlineKeyboardButton(text="📁 Додати з каталогу", callback_data="open_categories")])
    kb.append([InlineKeyboardButton(text="🗑 Очистити все", callback_data="clear_fridge")])
    kb.append([InlineKeyboardButton(text="🔍 ПІДІБРАТИ СТРАВУ", callback_data="search_recipes")])

    await message.answer(
        "🧊 **Ваш поточний холодильник:**\n*(Також ви можете просто напишіть назву продукту в чат, щоб додати його)*",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=kb), parse_mode="Markdown")


# Ручне введення продуктів текстом
@router.message(F.text & ~F.text.startswith("/"))
async def manual_add_product(message: Message, state: FSMContext):
    if message.text in ["🍳 Підібрати рецепт", "🛒 Мій холодильник", "⚙️ Змінити параметри", "🎯 Змінити ціль",
                        "Схуднення", "Підтримка", "Набір маси", "Чоловік", "Жінка"]:
        return

    product_names = [p.strip() for p in message.text.split(',')]
    conn = get_db_connection()
    found_ids = get_ingredient_ids_by_names(conn, product_names)
    conn.close()

    if not found_ids:
        await message.answer(
            "❌ Я не знайшов таких продуктів у базі. Перевірте орфографію або оберіть їх через меню категорій.")
        return

    selected = await sync_fridge_state(message.from_user.id, state)

    added_count = 0
    for pid in found_ids:
        if pid not in selected:
            selected.append(pid)
            added_count += 1

    await state.update_data(selected_ingredients=selected)
    save_fridge_to_json(message.from_user.id, selected)  # ЗБЕРІГАЄМО В JSON

    await message.answer(
        f"✅ Додано {added_count} нових продуктів до холодильника!\nЗайдіть у '🛒 Мій холодильник', щоб перевірити, або одразу тисніть '🍳 Підібрати рецепт'.")


# ================= FRIDGE MANAGEMENT =================
@router.callback_query(F.data.startswith("del:"))
async def delete_product(call: CallbackQuery, state: FSMContext):
    prod_id = int(call.data.split(":")[1])
    selected = await sync_fridge_state(call.from_user.id, state)

    if prod_id in selected:
        selected.remove(prod_id)
        await state.update_data(selected_ingredients=selected)
        save_fridge_to_json(call.from_user.id, selected)  # ЗБЕРІГАЄМО В JSON
        await call.answer("🗑 Продукт видалено!")
        await show_fridge(call.message, state)
    else:
        await call.answer("Помилка")


@router.callback_query(F.data == "clear_fridge")
async def clear_fridge(call: CallbackQuery, state: FSMContext):
    await state.update_data(selected_ingredients=[])
    save_fridge_to_json(call.from_user.id, [])  # ОЧИЩАЄМО В JSON
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


@router.callback_query(F.data == "open_categories")
async def open_categories_cb(call: CallbackQuery):
    await show_categories(call)
    await call.answer()


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
    selected = await sync_fridge_state(call.from_user.id, state)

    if prod_id not in selected:
        selected.append(prod_id)
        await state.update_data(selected_ingredients=selected)
        save_fridge_to_json(call.from_user.id, selected)  # ЗБЕРІГАЄМО В JSON
        await call.answer("✅ Додано в холодильник!", show_alert=False)
    else:
        await call.answer("⚠️ Вже є у холодильнику!", show_alert=False)


@router.callback_query(F.data == "back_cat")
async def back_to_cats(call: CallbackQuery):
    await show_categories(call)


# ================= SEARCH RECIPES (INLINE BUTTON) =================
@router.callback_query(F.data == "search_recipes")
async def search_recipes_inline(call: CallbackQuery, state: FSMContext):
    selected = await sync_fridge_state(call.from_user.id, state)

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

            matched = recipe['matched_names'] if recipe['matched_names'] else []
            missing = recipe['missing_ingredients'] if recipe['missing_ingredients'] else []
            all_ingredients = matched + missing

            explanation = generate_expert_explanation(
                goal=user_goal,
                calories=recipe['total_calories_base'],
                missing_ingredients=missing,
                matched_names=all_ingredients
            )
            response += f"{explanation}\n\n"
            response += "➖➖➖➖➖➖➖➖➖➖\n"

        await call.message.edit_text(response, parse_mode="Markdown")
    else:
        await call.message.edit_text(
            "😔 Навіть з частковим збігом я нічого не знайшов. Спробуйте додати ще кілька базових продуктів (яйця, крупи, м'ясо).")

    await call.answer()