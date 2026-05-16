import json

def export_users_to_json_file(conn, output_path="data/users_profiles_backup.json"):
    """Експортує анкетні дані всіх користувачів з PostgreSQL у файл JSON"""
    cursor = conn.cursor()
    cursor.execute("""
        SELECT tg_id, gender, age, weight, height, activity_level, goal, 
               target_calories, target_proteins, target_fats, target_carbs 
        FROM users;
    """)
    rows = cursor.fetchall()
    cursor.close()

    backup_data = {}
    for row in rows:
        backup_data[str(row['tg_id'])] = {
            "gender": row['gender'],
            "age": row['age'],
            "weight": row['weight'],
            "height": row['height'],
            "activity_level": row['activity_level'],
            "goal": row['goal'],
            "targets": {
                "calories": row['target_calories'],
                "proteins": row['target_proteins'],
                "fats": row['target_fats'],
                "carbs": row['target_carbs']
            }
        }

    with open(output_path, 'w', encoding='utf-8') as f:
        json.dump(backup_data, f, ensure_ascii=False, indent=4)
    print(f" Надійна резервна копія БД створена за шляхом: {output_path}")

def upsert_user(conn, tg_id, gender, age, weight, height, activity, goal, targets):
    cursor = conn.cursor()
    query = """
        INSERT INTO users (tg_id, gender, age, weight, height, activity_level, goal, 
                           target_calories, target_proteins, target_fats, target_carbs)
        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
        ON CONFLICT (tg_id) DO UPDATE SET
            gender = EXCLUDED.gender,
            age = EXCLUDED.age,
            weight = EXCLUDED.weight,
            height = EXCLUDED.height,
            activity_level = EXCLUDED.activity_level,
            goal = EXCLUDED.goal,
            target_calories = EXCLUDED.target_calories,
            target_proteins = EXCLUDED.target_proteins,
            target_fats = EXCLUDED.target_fats,
            target_carbs = EXCLUDED.target_carbs;
    """
    cursor.execute(query, (
        tg_id, gender, age, weight, height, activity, goal,
        targets['calories'], targets['proteins'], targets['fats'], targets['carbs']
    ))
    conn.commit()
    cursor.close()


def get_categories(conn):
    """Витягує список унікальних категорій продуктів"""
    cursor = conn.cursor()
    cursor.execute("SELECT DISTINCT category FROM ingredients WHERE category IS NOT NULL;")
    categories = [row['category'] for row in cursor.fetchall()]
    cursor.close()
    return categories


def get_ingredients_by_category(conn, category):
    """Витягує продукти конкретної категорії"""
    cursor = conn.cursor()
    cursor.execute("SELECT ingredient_id, name FROM ingredients WHERE category = %s ORDER BY name;", (category,))
    items = cursor.fetchall()
    cursor.close()
    return items


def get_smart_recipes(conn, ingredient_ids, user_tg_id):
    cursor = conn.cursor()

    cursor.execute("SELECT goal FROM users WHERE tg_id = %s;", (user_tg_id,))
    user_data = cursor.fetchone()
    user_goal = user_data['goal'] if user_data else "Підтримка"

    query = """
        SELECT 
            r.recipe_id, 
            r.title, 
            r.total_calories_base, 
            r.instructions,
            COUNT(ri.ingredient_id) as total_ingredients,
            SUM(CASE WHEN ri.ingredient_id = ANY(%s) THEN 1 ELSE 0 END) as matched_ingredients,
            ARRAY_AGG(i.name) FILTER (WHERE NOT ri.ingredient_id = ANY(%s)) as missing_ingredients,
            ARRAY_AGG(i.name) FILTER (WHERE ri.ingredient_id = ANY(%s)) as matched_names
        FROM recipes r
        JOIN recipe_ingredients ri ON r.recipe_id = ri.recipe_id
        JOIN ingredients i ON ri.ingredient_id = i.ingredient_id
        GROUP BY r.recipe_id, r.title, r.total_calories_base, r.instructions
        HAVING SUM(CASE WHEN ri.ingredient_id = ANY(%s) THEN 1 ELSE 0 END)::float / COUNT(ri.ingredient_id) >= 0.5
        ORDER BY matched_ingredients DESC, total_calories_base ASC
        LIMIT 5;
    """
    cursor.execute(query, (ingredient_ids, ingredient_ids, ingredient_ids, ingredient_ids))
    recipes = cursor.fetchall()
    cursor.close()

    return recipes, user_goal


def get_ingredient_ids_by_names(conn, names):
    """Пошук ID інгредієнтів за їхніми текстовими назвами"""
    cursor = conn.cursor()
    # Створюємо рядок з %s для безпечного SQL-запиту
    format_strings = ','.join(['%s'] * len(names))
    query = f"SELECT ingredient_id FROM ingredients WHERE LOWER(name) IN ({format_strings});"

    # Переводимо все в нижній регістр і прибираємо зайві пробіли
    lower_names = [name.strip().lower() for name in names]
    cursor.execute(query, tuple(lower_names))

    results = cursor.fetchall()
    cursor.close()
    return [row['ingredient_id'] for row in results]

def get_user(conn, tg_id):
    """Отримує всі дані користувача за його Telegram ID"""
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM users WHERE tg_id = %s;", (tg_id,))
    user = cursor.fetchone()
    cursor.close()
    return user