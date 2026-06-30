from aiogram import F
from aiogram import Router
from aiogram.filters import CommandStart
from aiogram.types import Message, LinkPreviewOptions, CallbackQuery
from aiogram.fsm.context import FSMContext
from services.states import ReadingTracker
from database.db import DatabaseManager
from keyboard import main_keyboard, build_books_keyboard
from aiogram.enums import ChatType
import re

def contains_emoji(text: str) -> bool:
    emoji_pattern = re.compile(
        "["
        "\U0001F600-\U0001F64F"  # emoticons
        "\U0001F300-\U0001F5FF"  # symbols & pictographs
        "\U0001F680-\U0001F6FF"  # transport & map
        "\U0001F700-\U0001F77F"  # alchemical
        "\U0001F780-\U0001F7FF"
        "\U0001F800-\U0001F8FF"
        "\U0001F900-\U0001F9FF"  # supplemental symbols
        "\U0001FA00-\U0001FAFF"
        "\U00002700-\U000027BF"  # dingbats
        "\U00002600-\U000026FF"
        "]+",
        flags=re.UNICODE
    )
    return bool(emoji_pattern.search(text))

router = Router()

@router.message(CommandStart(), F.chat.type == ChatType.PRIVATE)
async def cmd_start(message: Message, state: FSMContext, database: DatabaseManager):
    presence = await database.users.get_full(message.from_user.id)
    if presence == None:
        await message.answer("Arybaŋyz, zhash oqurman👋\n\n\nAtynyz kim?\n(atyŋyzdy Name Surname tartibinde latyn tamgalary menen berseŋiz sonun bolot,\n\n misaly Bekmyrza Alyshbeav zhe Bekmyrza Samarbek uulu degendei)")
        await state.set_state(ReadingTracker.user_name)
    else:
        await message.answer(f"{presence['user_name']}, sizdi kaira körgönü qubanychtamyn 🫰", reply_markup=main_keyboard)

@router.message(ReadingTracker.user_name)
async def process_name(message: Message, state: FSMContext, database: DatabaseManager):
    provision = message.text.split()
    if len(provision)==2 or len(provision)==3:
        name = provision[0]
        surname = " ".join(provision[1:])
        await database.users.add(message.from_user.id, name, surname)
        await message.answer(f"Qosh keldiŋiz, {name}🤍\n", reply_markup=main_keyboard)
        await state.clear()
    else:
        await message.answer("Suranych atyŋyzdy talaptagydai kirgiziŋiz☢️")
    

@router.message(F.text == "Bet kirgizüü📖")
async def trigger_log_page(message: Message, state: FSMContext, database: DatabaseManager):
    books = await database.user_books.get(message.from_user.id)
    if not books:
        await message.answer("Qaisy kitepti oqudunuz? Atyn zhazyŋyz:")
        await state.set_state(ReadingTracker.add_book)
    else:
        keyboard = build_books_keyboard(books)
        await message.answer("Qaisy kitepti oquduŋuz?", reply_markup=keyboard)
        await state.set_state(ReadingTracker.choose_book)

@router.callback_query(ReadingTracker.choose_book)
async def process_book_choice(callback: CallbackQuery, state: FSMContext, database: DatabaseManager):
    if callback.data == "add_new_book":
        await callback.message.answer("Zhaŋy kiteptin atyn zhazyŋyz:")
        await state.set_state(ReadingTracker.add_book)
    else:
        book_id = int(callback.data.split(":")[1])  # "book:42" → 42
        await state.update_data(book_id=book_id)
        await callback.message.answer("Qancha bet oquduŋuz?")
        await state.set_state(ReadingTracker.log_page)
    await callback.answer()  # clears the loading spinner on the button

@router.message(ReadingTracker.add_book)
async def process_new_book(message: Message, state: FSMContext, database: DatabaseManager):
    title = message.text.strip()

    if contains_emoji(title):
        await message.answer(
            "❌ Kitep aty tuura emes.\n\n"
            "📚 Taza atyn jazyŋyz (misaly: Atomic Habits)"
        )
        return  # stay in same state

    if not title:
        await message.answer("❌ Kitap aty tuura emes. Qayra jazyŋyz.")
        return

    book_id = await database.books.add(title)
    await database.user_books.add(message.from_user.id, book_id)

    await state.update_data(book_id=book_id)
    await message.answer(
        f"📖 '{title}' kitep tizmeŋizge qoshuldu!\n\n"
        "Qancha bet oquduŋuz?"
    )
    await state.set_state(ReadingTracker.log_page)

@router.message(ReadingTracker.log_page)
async def process_page(message: Message, state: FSMContext, database: DatabaseManager):
    if message.text.isdigit() and int(message.text) > 0 and int(message.text) < 1000:
        pages = int(message.text)
        data = await state.get_data()
        book_id = data['book_id']
        await database.logs.add(message.from_user.id, book_id, pages)
        await message.answer(f"Zharait, {pages} bet bügüngö koshup koidum👌")
        await state.clear()
    else:
        await message.answer("Suranych durus bir bet sanyn zhazyŋyz☢️")

@router.message(F.text == "Meniki👤")
async def show_progress(message: Message, database: DatabaseManager):
    records = await database.logs.get(message.from_user.id)
    if not records:
        await message.answer("Siz ali bet kirgize eleksiz⛔")
        return
    response_text = "**Sizdin oquu taryhchaŋyz🕜:**\n\n"
    total_pages = 0
    for row in records:
        date_str = row['log_date'].strftime("%Y-%m-%d")
        total_pages += row['pages_read']
        response_text += f"`{date_str}` | {row['title']}: **{row['pages_read']}** bet\n"
    response_text += f"\n**➡️Zhalpy:** {total_pages} bet"
    await message.answer(response_text, parse_mode="Markdown")

@router.message(F.text == "Zhalpy📈")
async def hyperlink(message: Message):
    sheet_url = "https://docs.google.com/spreadsheets/d/1jpV8B5rMd5FfNqMmrfxxShMfaZvLd1aDG-HdGIEtzoM/edit?usp=sharing"
    response_text = f"Klubtun zhalpy zhyiyntyq shiltemesi: \n📊[TimeClub]({sheet_url})"
    
    await message.answer(
        response_text, 
        parse_mode="Markdown", 
        link_preview_options=LinkPreviewOptions(is_disabled=True)
    )

@router.message(F.text == "Gruppaga qoshuluu 👥")
async def hyperlink(message: Message):
    sheet_url = "https://t.me/+mYguvPw7CopiODEy"
    response_text = f"Gruppaga qoshuluu shiltemesi: \n👥[oQush]({sheet_url})"
    
    await message.answer(
        response_text, 
        parse_mode="Markdown", 
        link_preview_options=LinkPreviewOptions(is_disabled=True)
    )