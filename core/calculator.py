from typing import Dict

def calculate_daily_targets(gender: str, weight: float, height: float, age: int, activity: float, goal: str) -> Dict[str, int]:
    if gender.lower() in ['чоловік', 'ч', 'male']:
        bmr = (10 * weight) + (6.25 * height) - (5 * age) + 5
    else:
        bmr = (10 * weight) + (6.25 * height) - (5 * age) - 161

    tdee = bmr * activity

    goal_lower = goal.lower()
    if goal_lower == 'схуднення':
        target_calories = tdee * 0.85
    elif goal_lower in ['набір', 'набір маси']:
        target_calories = tdee * 1.15
    else:
        target_calories = tdee

    proteins = (target_calories * 0.30) / 4
    fats = (target_calories * 0.30) / 9
    carbs = (target_calories * 0.40) / 4

    return {
        "calories": int(target_calories),
        "proteins": int(proteins),
        "fats": int(fats),
        "carbs": int(carbs)
    }

if __name__ == "__main__":
    result = calculate_daily_targets("чоловік", 80, 180, 25, 1.375, "набір")
    print(f"Тестовий розрахуок: {result}")