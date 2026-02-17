from aiogram.fsm.state import State, StatesGroup

class ReadingTracker(StatesGroup):
    user_name = State()
    log_page = State()