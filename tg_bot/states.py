from aiogram.fsm.state import State, StatesGroup

class Onboarding(StatesGroup):
    gender = State()
    age = State()
    weight = State()
    height = State()
    activity = State()
    goal = State()