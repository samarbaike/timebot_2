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
        await message.answer("Arybanyz, zhash okurman👋\n\n\nAtynyz kim?\n(atynyzdy Name Surname tartibinde berseniz zhakshy bolmok,\n\n misaly Bekmyrze Alyshbeav zhe Bekmyrza Samarbek uulu degendei)")
        await state.set_state(ReadingTracker.user_name)
    else:
        await message.answer("Kosh kelipsiz", reply_markup=main_keyboard)

@router.message(ReadingTracker.user_name)
async def process_name(message: Message, state: FSMContext, database: DatabaseManager):
    provision = message.text.split()
    if len(provision)==2 or len(provision)==3:
        name = provision[0]
        surname = " ".join(provision[1:])
        await database.users.add(message.from_user.id, name, surname)
        await message.answer(f"Kosh keldiniz, {name}🤍\n", reply_markup=main_keyboard)
        await state.clear()
    else:
        await message.answer("Surancyh atynyzdy talaptagydai kirgiziniz☢️")
    

@router.message(F.text == "Bet kirgizuu📖")
async def trigger_log_page(message: Message, state: FSMContext):
    await message.answer("Kancha bet okudunuz?")
    await state.set_state(ReadingTracker.log_page)

@router.message(ReadingTracker.log_page)
async def process_page(message: Message, state: FSMContext, database: DatabaseManager):
    if message.text.isdigit() and int(message.text)>0:
        pages = int(message.text)
        await message.answer(f"Zharait, {pages} bet bugungo koshup koidum👌")
        await database.logs.add(message.from_user.id, pages)
        await state.clear()

    else:
        await message.answer("Suranych durus bir bet sanyn kirgiziniz☢️")

@router.message(F.text == "Meniki👤")
async def show_progress(message: Message, database: DatabaseManager):
    records = await database.logs.get(message.from_user.id)

    if not records:
        await message.answer("Siz ali bet kirgize eleksiz⛔")
        return
    
    response_text = "**Sizdin oku taryhynyz🕜:**\n\n"
    total_pages = 0
    
    for row in records:
        date_str = row['log_date'].strftime("%Y-%m-%d")
        pages = row['pages_read']
        total_pages+=pages

        response_text+=f"{date_str}: {pages} bet\n"

    response_text+=f"\n **➡️Zhalpy:** {total_pages} bet"

    await message.answer(response_text, parse_mode="Markdown")

@router.message(F.text == "Zhalpy📈")
async def hyperlink(message: Message):
    sheet_url = "https://docs.google.com/spreadsheets/d/14bOLSsLN2cQGG_YpGhfGaleeLSJt5YhXu3LzM6Exqv8/edit?usp=sharing"
    response_text = f"📊 [TimeClub]({sheet_url})"
    
    await message.answer(
        response_text, 
        parse_mode="Markdown", 
        link_preview_options=LinkPreviewOptions(is_disabled=True)
    )