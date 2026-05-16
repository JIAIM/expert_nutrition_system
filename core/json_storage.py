import json
import os

# Визначаємо шлях до папки з даними у колі проєкту
DATA_DIR = os.path.join(os.path.dirname(__file__), '..', 'data')
FILE_PATH = os.path.join(DATA_DIR, 'user_fridges.json')


def save_fridge_to_json(tg_id: int, ingredient_ids: list):
    """Зберігає масив ID інгредієнтів користувача у JSON-файл"""
    os.makedirs(DATA_DIR, exist_ok=True)

    data = {}
    if os.path.exists(FILE_PATH):
        with open(FILE_PATH, 'r', encoding='utf-8') as f:
            try:
                data = json.load(f)
            except json.JSONDecodeError:
                data = {}

    # Записуємо або оновлюємо дані для конкретного телеграм ID
    data[str(tg_id)] = ingredient_ids

    with open(FILE_PATH, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=4)


def load_fridge_from_json(tg_id: int) -> list:
    """Завантажує масив ID інгредієнтів користувача з JSON-файлу"""
    if not os.path.exists(FILE_PATH):
        return []

    with open(FILE_PATH, 'r', encoding='utf-8') as f:
        try:
            data = json.load(f)
            return data.get(str(tg_id), [])
        except json.JSONDecodeError:
            return []