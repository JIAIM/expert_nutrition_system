def generate_expert_explanation(goal: str, calories: int, missing_ingredients: list, matched_names: list) -> str:
    explanation = "💡 **Експертний аналіз:**\n"
    goal_lower = goal.lower()

    # 1. Аналіз калорійності під мету
    explanation += f"🔹 **Енергія ({calories} ккал):** "
    if goal_lower == 'схуднення':
        if calories <= 350:
            explanation += "Ідеально для дефіциту калорій. Забезпечить ситість без переїдання.\n"
        else:
            explanation += "Ситна порція. Рекомендую їсти це в першій половині дня (сніданок/обід), щоб ефективно спалити калорії.\n"
    elif goal_lower in ['набір', 'набір маси']:
        if calories >= 450:
            explanation += "Те, що треба для профіциту! Дасть потужний заряд для росту м'язової маси.\n"
        else:
            explanation += "Порція замала для набору. Раджу додати додатковий білок (наприклад, сир або горіхи) чи збільшити грамівки.\n"
    else:
        explanation += "Оптимально для підтримки вашої поточної форми та здорового обміну речовин.\n"

    # 2. Аналіз нутрієнтів
    protein_markers = ["Кур", "Яловичина", "Свинина", "Риба", "Лосось", "Тунець", "Яйця", "Сир", "Креветки", "Фарш", "Печінка", "Сочевиця"]
    fiber_markers = ["Помідор", "Огірок", "Капуста", "Броколі", "Гречка", "Вівсян", "Яблуко", "Морква", "Шпинат", "Авокадо", "Буряк"]

    has_protein = any(any(p.lower() in str(m).lower() for p in protein_markers) for m in matched_names) if matched_names else False
    has_fiber = any(any(f.lower() in str(m).lower() for f in fiber_markers) for m in matched_names) if matched_names else False

    explanation += "🔹 **Користь:** "
    if has_protein and has_fiber:
        explanation += "Ідеальний баланс! Білок захистить м'язи, а клітковина дасть довгу ситість і користь для травлення."
    elif has_protein:
        explanation += "Багате джерело протеїну, що критично важливо для відновлення м'язів та пружності шкіри."
    elif has_fiber:
        explanation += "Тут багато складних вуглеводів та клітковини. Це дасть тривалу енергію без стрибків цукру."
    else:
        explanation += "Швидке джерело енергії для вашого організму."

    # 3. Аналіз нестачі
    if missing_ingredients:
        missed_str = ", ".join(missing_ingredients)
        explanation += f"\n\n🛒 *Для ідеалу не вистачає:* {missed_str}."
    else:
        explanation += "\n\n✨ *Супер! У вас є всі інгредієнти для цього рецепта.*"

    return explanation