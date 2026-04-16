def generate_expert_explanation(goal: str, calories: int, missing_ingredients: list, matched_names: list) -> str:
    explanation = "💡 **Експертний аналіз:**\n"
    goal_lower = goal.lower()

    # ================= 1. ЕНЕРГІЯ ТА ЦІЛЬ =================
    explanation += f"⚡️ **Енергія ({calories} ккал):** "
    if goal_lower == 'схуднення':
        if calories <= 350:
            explanation += "Ідеальний розмір порції для дефіциту. Дасть енергію, не перевантажуючи шлунок.\n"
        else:
            explanation += "Досить ситна страва. Краще запланувати її на сніданок або обід, щоб організм встиг витратити ці калорії.\n"
    elif goal_lower in ['набір', 'набір маси']:
        if calories >= 450:
            explanation += "Відмінний калораж для анаболізму! Забезпечить необхідний профіцит для росту маси.\n"
        else:
            explanation += "Трохи замало калорій для повноцінного прийому їжі на масонаборі. Додайте жменю горіхів, олію або подвійте порцію.\n"
    else:
        explanation += "Оптимальна калорійність для підтримки стабільної ваги та здорового метаболізму.\n"

    # ================= 2. МАКРО ТА МІКРОНУТРІЄНТИ =================
    # Словники-маркери корисних речовин
    protein_markers = ["кур", "яловичин", "свинин", "риба", "лосось", "тунець", "яйц", "сир", "креветк", "фарш",
                       "печінк", "сочевиц", "індичк"]
    fiber_markers = ["помідор", "огірок", "капуст", "броколі", "гречк", "вівсян", "яблук", "моркв", "шпинат", "авокадо",
                     "буряк", "булгур", "сочевиц"]
    omega3_markers = ["лосось", "оселедець", "тунець", "авокадо", "волоський горіх", "оливков", "мигдаль", "сало"]
    vitamin_markers = ["помідор", "перець", "лимон", "апельсин", "броколі", "ківі", "полуниц", "шпинат", "моркв",
                       "яблук"]
    calcium_markers = ["сир", "молоко", "кефір", "йогурт", "сметан", "вершк", "пармезан", "моцарелла"]

    # Перевіряємо, що з цього є у вибраних інгредієнтах (ігноруючи регістр)
    has_protein = any(
        any(p in str(m).lower() for p in protein_markers) for m in matched_names) if matched_names else False
    has_fiber = any(any(f in str(m).lower() for f in fiber_markers) for m in matched_names) if matched_names else False
    has_omega3 = any(
        any(o in str(m).lower() for o in omega3_markers) for m in matched_names) if matched_names else False
    has_vitamins = any(
        any(v in str(m).lower() for v in vitamin_markers) for m in matched_names) if matched_names else False
    has_calcium = any(
        any(c in str(m).lower() for c in calcium_markers) for m in matched_names) if matched_names else False

    benefits = []
    if has_protein:
        benefits.append("💪 **Білок:** захист та відновлення м'язових тканин.")
    if has_fiber:
        benefits.append("🌾 **Клітковина:** плавне вивільнення енергії та користь для мікробіома.")
    if has_omega3:
        benefits.append("🐟 **Корисні жири:** підтримка серця, судин та гормональної системи.")
    if has_vitamins:
        benefits.append("🍋 **Вітаміни:** зміцнення імунітету та антиоксидантний ефект.")
    if has_calcium:
        benefits.append("🥛 **Кальцій:** міцність кісток, зубів та нервової системи.")

    if benefits:
        explanation += "🧬 **Нутрієнтний профіль:**\n" + "\n".join(benefits)
    else:
        explanation += "🧬 **Нутрієнтний профіль:** Базове джерело енергії (переважно прості вуглеводи/жири)."

    # ================= 3. АНАЛІЗ НЕСТАЧІ =================
    if missing_ingredients:
        missed_str = ", ".join(missing_ingredients)
        explanation += f"\n\n🛒 *Порада:* Щоб страва вийшла ідеальною, вам бракує: {missed_str}."
    else:
        explanation += "\n\n✨ *Клас!* У вас є абсолютно всі інгредієнти."

    return explanation
