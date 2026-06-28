from aiogram import F
from aiogram import Router
from aiogram.filters import CommandStart
from aiogram.types import Message, LinkPreviewOptions, CallbackQuery
from aiogram.fsm.context import FSMContext
from services.states import ReadingTracker
from database.db import DatabaseManager
from keyboard import main_keyboard, build_books_keyboard

router = Router()

@router.message(CommandStart())
async def cmd_start(message: Message, state: FSMContext, database: DatabaseManager):
    presence = await database.users.get(message.from_user.id)
    if presence == None:
        await message.answer("Arybanyz, zhash okurman👋\n\n\nAtynyz kim?\n(atynyzdy Name Surname tartibinde berseniz zhakshy bolmok,\n\n misaly Bekmyrza Alyshbeav zhe Bekmyrza Samarbek uulu degendei)")
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
        await message.answer(f"Hosh keldiniz, {name}🤍\n", reply_markup=main_keyboard)
        await state.clear()
    else:
        await message.answer("Suranych atynyzdy talaptagydai kirgiziniz☢️")
    

@router.message(F.text == "Bet kirgizuu📖")
async def trigger_log_page(message: Message, state: FSMContext, database: DatabaseManager):
    books = await database.user_books.get(message.from_user.id)
    if not books:
        await message.answer("Kaisy kitepti okudunuz? Atyn zhazynyz:")
        await state.set_state(ReadingTracker.add_book)
    else:
        keyboard = build_books_keyboard(books)
        await message.answer("Kaisy kitepti okudunuz?", reply_markup=keyboard)
        await state.set_state(ReadingTracker.choose_book)

@router.callback_query(ReadingTracker.choose_book)
async def process_book_choice(callback: CallbackQuery, state: FSMContext, database: DatabaseManager):
    if callback.data == "add_new_book":
        await callback.message.answer("Zhany kiteptin atyn zhazynyz:")
        await state.set_state(ReadingTracker.add_book)
    else:
        book_id = int(callback.data.split(":")[1])  # "book:42" → 42
        await state.update_data(book_id=book_id)
        await callback.message.answer("Kancha bet okudunuzbu?")
        await state.set_state(ReadingTracker.log_page)
    await callback.answer()  # clears the loading spinner on the button

@router.message(ReadingTracker.add_book)
async def process_new_book(message: Message, state: FSMContext, database: DatabaseManager):
    title = message.text.strip()
    book_id = await database.books.add(title)
    await database.user_books.add(message.from_user.id, book_id)
    await state.update_data(book_id=book_id)
    await message.answer(f"'{title}' kitebi tizmenizge koshuldu!\nKancha bet okudunuz?")
    await state.set_state(ReadingTracker.log_page)

@router.message(ReadingTracker.log_page)
async def process_page(message: Message, state: FSMContext, database: DatabaseManager):
    if message.text.isdigit() and int(message.text) > 0:
        pages = int(message.text)
        data = await state.get_data()
        book_id = data['book_id']
        await database.logs.add(message.from_user.id, book_id, pages)
        await message.answer(f"Zharait, {pages} bet bugungo koshup koidum👌")
        await state.clear()
    else:
        await message.answer("Suranych durus bet sanyn zhazynyz☢️")

@router.message(F.text == "Meniki👤")
async def show_progress(message: Message, database: DatabaseManager):
    records = await database.logs.get(message.from_user.id)
    if not records:
        await message.answer("Siz ali bet kirgize eleksiz⛔")
        return
    response_text = "**Sizdin okuu taryhchanyz🕜:**\n\n"
    total_pages = 0
    for row in records:
        date_str = row['log_date'].strftime("%Y-%m-%d")
        total_pages += row['pages_read']
        response_text += f"`{date_str}` | {row['title']}: **{row['pages_read']}** бет\n"
    response_text += f"\n**➡️Zhalpy:** {total_pages} bet"
    await message.answer(response_text, parse_mode="Markdown")

@router.message(F.text == "Zhalpy📈")
async def hyperlink(message: Message):
    sheet_url = "https://docs.google.com/spreadsheets/d/1jpV8B5rMd5FfNqMmrfxxShMfaZvLd1aDG-HdGIEtzoM/edit?usp=sharing"
    response_text = f"📊 [TimeClub]({sheet_url})"
    
    await message.answer(
        response_text, 
        parse_mode="Markdown", 
        link_preview_options=LinkPreviewOptions(is_disabled=True)
    )