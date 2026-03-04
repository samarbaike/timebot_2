from aiogram import F
from aiogram import Router
from aiogram.filters import CommandStart
from aiogram.types import Message, LinkPreviewOptions
from aiogram.fsm.context import FSMContext
from services.states import ReadingTracker
from database.db import DatabaseManager
from keyboard import main_keyboard
router = Router()

@router.message(CommandStart())
async def cmd_start(message: Message, state: FSMContext, database: DatabaseManager):
    presence = await database.users.get(message.from_user.id)
    if presence == None:
        await message.answer("Hello, before we proceed we need register you.\nWhat is your name?\n(give you name in Name Surname format, i.e. Samar Kanybek uulu or Samar Kanybekov)")
        await state.set_state(ReadingTracker.user_name)
    else:
        await message.answer("Welcome back", reply_markup=main_keyboard)

@router.message(ReadingTracker.user_name)
async def process_name(message: Message, state: FSMContext, database: DatabaseManager):
    provision = message.text.split()
    if len(provision)==2 or len(provision)==3:
        name = provision[0]
        surname = " ".join(provision[1:])
        await database.users.add(message.from_user.id, name, surname)
        await message.answer(f"Welcome, {name}\n", reply_markup=main_keyboard)
        await state.clear()
    else:
        await message.answer("Please insert name & surnmame as shown in the format")
    

@router.message(F.text == "Бет киргизүү📖")
async def trigger_log_page(message: Message, state: FSMContext):
    await message.answer("How pages have you read?")
    await state.set_state(ReadingTracker.log_page)

@router.message(ReadingTracker.log_page)
async def process_page(message: Message, state: FSMContext, database: DatabaseManager):
    if message.text.isdigit() and int(message.text)>=0:
        pages = int(message.text)
        await message.answer(f"Done, {pages} added for today")
        await database.logs.add(message.from_user.id, pages)
        await state.clear()

    else:
        await message.answer("Please insert proper number of pages")

@router.message(F.text == "Меники👤")
async def show_progress(message: Message, database: DatabaseManager):
    records = await database.logs.get(message.from_user.id)

    if not records:
        await message.answer("Сиз али бет киргизбептирсиз")
        return
    
    response_text = "**Сиздин окуу тарыхыңыз:**\n\n"
    total_pages = 0
    
    for row in records:
        date_str = row['log_date'].strftime("%Y-%m-%d")
        pages = row['pages_read']
        total_pages+=pages

        response_text+=f"{date_str}: {pages} бет\n"

    response_text+=f"\n **Жалпы:** {total_pages} бет"

    await message.answer(response_text, parse_mode="Markdown")

@router.message(F.text == "Жалпы📈")
async def hyperlink(message: Message):
    sheet_url = "https://docs.google.com/spreadsheets/d/14bOLSsLN2cQGG_YpGhfGaleeLSJt5YhXu3LzM6Exqv8/edit?usp=sharing"
    response_text = f"📊 [Жалпы абал]({sheet_url})"
    
    await message.answer(
        response_text, 
        parse_mode="Markdown", 
        link_preview_options=LinkPreviewOptions(is_disabled=True)
    )