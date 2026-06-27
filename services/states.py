from aiogram.fsm.state import State, StatesGroup

class ReadingTracker(StatesGroup):
    user_name = State()
    choose_book = State()
    add_book = State()
    log_page = State()