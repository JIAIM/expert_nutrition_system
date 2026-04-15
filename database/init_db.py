import os
from dotenv import load_dotenv
import psycopg2

load_dotenv(dotenv_path=os.path.join(os.path.dirname(__file__), '..', '.env'))

def init_database():
    try:
        conn = psycopg2.connect(
            host=os.getenv("DB_HOST"),
            port=os.getenv("DB_PORT"),
            user=os.getenv("DB_USER"),
            password=os.getenv("DB_PASSWORD"),
            dbname=os.getenv("DB_NAME")
        )
        cursor = conn.cursor()

        cursor.execute("DROP TABLE IF EXISTS recipe_ingredients, recipes, ingredients, users CASCADE;")

        create_tables_query = """
        CREATE TABLE users (
            user_id SERIAL PRIMARY KEY,
            tg_id BIGINT UNIQUE NOT NULL,
            gender VARCHAR(20),
            age INTEGER,
            weight FLOAT,
            height FLOAT,
            activity_level FLOAT,
            goal VARCHAR(20),
            target_calories INTEGER,
            target_proteins FLOAT,
            target_fats FLOAT,
            target_carbs FLOAT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );

        CREATE TABLE ingredients (
            ingredient_id SERIAL PRIMARY KEY,
            name VARCHAR(100) NOT NULL,
            calories_100g FLOAT NOT NULL,
            proteins_100g FLOAT DEFAULT 0,
            fats_100g FLOAT DEFAULT 0,
            carbs_100g FLOAT DEFAULT 0,
            category VARCHAR(50)
        );

        CREATE TABLE recipes (
            recipe_id SERIAL PRIMARY KEY,
            title VARCHAR(200) NOT NULL,
            description TEXT,
            instructions TEXT,
            total_calories_base INTEGER,
            is_snack BOOLEAN DEFAULT FALSE
        );

        CREATE TABLE recipe_ingredients (
            recipe_id INTEGER REFERENCES recipes(recipe_id) ON DELETE CASCADE,
            ingredient_id INTEGER REFERENCES ingredients(ingredient_id),
            weight_grams FLOAT NOT NULL,
            is_optional BOOLEAN DEFAULT FALSE,
            PRIMARY KEY (recipe_id, ingredient_id)
        );
        """
        cursor.execute(create_tables_query)

        seed_data_query = """
        -- Додаємо інгредієнти
        INSERT INTO ingredients (name, calories_100g, proteins_100g, fats_100g, carbs_100g, category) VALUES
        ('Яйця', 155, 13, 11, 1.1, 'Тваринні продукти'),
        ('Молоко 2.5%', 54, 2.9, 2.5, 4.8, 'Молочне'),
        ('Куряче філе', 110, 23, 1.2, 0, 'М''ясо'),
        ('Гречка', 343, 13, 3.4, 71.5, 'Крупи'),
        ('Помідор', 18, 0.9, 0.2, 3.9, 'Овочі');

        -- Додаємо рецепт
        INSERT INTO recipes (title, instructions, total_calories_base) VALUES
        ('Омлет класичний', '1. Збити яйця з молоком. 2. Вилити на розігріту сковорідку. 3. Смажити до готовності.', 350);

        -- Зв'язуємо рецепт з інгредієнтами (Омлет = Яйця + Молоко)
        -- Припускаємо, що Яйця мають ID 1, а Молоко ID 2
        INSERT INTO recipe_ingredients (recipe_id, ingredient_id, weight_grams) VALUES
        (1, 1, 150),  -- 3 яйця
        (1, 2, 50);   -- 50 мл молока
        """
        cursor.execute(seed_data_query)

        conn.commit()
        cursor.close()
        conn.close()
        print("Базу даних успішно ініціалізовано та заповнено тестовими даними!")

    except Exception as e:
        print(f"Помилка при ініціалізації бази даних: {e}")

if __name__ == "__main__":
    init_database()