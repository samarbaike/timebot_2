from aiogram import Router
from aiogram.filters import CommandStart
from aiogram.types import Message
from aiogram.fsm.context import FSMContext
from services.states import ReadingTracker
from database.db import DatabaseManager

router = Router()

@router.message(CommandStart())
async def cmd_start(message: Message, state: FSMContext):
    await message.answer("Ассаламу алейкум, тууган атынды айт да?")

    await state.set_state(ReadingTracker.user_name)

@router.message(ReadingTracker.user_name)
async def process_name(message: Message, state: FSMContext):
    # 1. Capture the text the user sent
    provided_name = message.text
    # 2. Acknowledge the input
    await state.update_data(name=provided_name)
    await message.answer(f"Жарайт, {provided_name}! Канча бет окудун родной?")
    
    # 3. Shift the user to the next state
    await state.set_state(ReadingTracker.log_page)

@router.message(ReadingTracker.log_page)
async def process_pages(message: Message, state: FSMContext,database: DatabaseManager):
    if message.text.isdigit():
        pages = int(message.text)
        dict_name = await state.get_data()
        name = dict_name["name"]

        await message.answer(f"Azamatsyn {name}, {pages} бетти бүгүнгө кошуп койдум!")
        await database.add_log(message.from_user.id, name, pages)
        await state.clear()
    else:
        await message.answer("Родной жакшыраак сан киргизчи, 45 дегендей.")