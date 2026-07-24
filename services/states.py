from aiogram.fsm.state import State, StatesGroup

class ReadingTracker(StatesGroup):
    user_name = State()
    add_book = State()