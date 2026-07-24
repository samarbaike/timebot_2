from aiogram import F
from aiogram import Router
from aiogram.filters import CommandStart
from aiogram.types import Message, LinkPreviewOptions
from aiogram.fsm.context import FSMContext
from services.states import ReadingTracker
from database.db import DatabaseManager
from keyboard import main_keyboard
from aiogram.enums import ChatType
from aiogram.exceptions import TelegramBadRequest
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


async def resolve_user_group(bot, database: DatabaseManager, user_id: int):
    """Checks every group the bot currently belongs to and returns the
    group_id the user is a member of, or None if they're in none of them.
    Relies on handlers/groups.py keeping the groups table in sync with
    which chats the bot is actually still a member of."""
    groups = await database.groups.get_all_active()
    for group in groups:
        try:
            member = await bot.get_chat_member(group['group_id'], user_id)
        except TelegramBadRequest:
            # User was never in this chat (most common case), or the bot
            # otherwise can't see membership — just try the next group.
            continue
        if member.status in ("member", "administrator", "creator", "restricted"):
            return group['group_id']
    return None


@router.message(CommandStart(), F.chat.type == ChatType.PRIVATE)
async def cmd_start(message: Message, state: FSMContext, database: DatabaseManager):
    presence = await database.users.get_full(message.from_user.id)

    if presence is None:
        group_id = await resolve_user_group(message.bot, database, message.from_user.id)
        if group_id is None:
            await message.answer(
                "❌ Kechiresiz, siz bottun eç bir gruppasynda tabylbadyŋyz.\n\n"
                "Bul bot tek gana klubdun gruppalaryna qatyshqan oqurmandar üchün.\n"
                "Aldy menen tiiştüü gruppaga qoshuluŋuz, andan kiyin qaira /start basyŋyz."
            )
            return
        await state.update_data(group_id=group_id)
        await message.answer("Arybaŋyz, zhash oqurman👋\n\n\nAtynyz kim?\n(atyŋyzdy Name Surname tartibinde latyn tamgalary menen berseŋiz sonun bolot,\n\n misaly Bekmyrza Alyshbeav zhe Bekmyrza Samarbek uulu degendei)")
        await state.set_state(ReadingTracker.user_name)
    else:
        # Legacy users who registered before group-matching existed won't
        # have a group_id yet — try to backfill it silently on this /start.
        if presence['group_id'] is None:
            group_id = await resolve_user_group(message.bot, database, message.from_user.id)
            if group_id is not None:
                await database.users.set_group(message.from_user.id, group_id)
        await message.answer(f"{presence['user_name']}, sizdi kaira körgönü qubanychtamyn 🫰", reply_markup=main_keyboard)

@router.message(ReadingTracker.user_name)
async def process_name(message: Message, state: FSMContext, database: DatabaseManager):
    provision = message.text.split()
    if len(provision)==2 or len(provision)==3:
        name = provision[0]
        surname = " ".join(provision[1:])
        data = await state.get_data()
        group_id = data.get('group_id')
        await database.users.add(message.from_user.id, name, surname, group_id)
        await message.answer(f"Qosh keldiŋiz, {name}🤍\n", reply_markup=main_keyboard)
        await state.clear()
    else:
        await message.answer("Suranych atyŋyzdy talaptagydai kirgiziŋiz☢️")
    

@router.message(ReadingTracker.add_book)
async def process_new_book(message: Message, state: FSMContext, database: DatabaseManager):
    title = message.text.strip()

    def contains_quotes(text: str) -> bool:
        quotes = ['"', "'", '«', '»', '“', '”', '‘', '’']
        return any(q in text for q in quotes)

    if contains_emoji(title) or contains_quotes(title):
        await message.answer(
            "❌ Kitep aty tuura emes.\n\n"
            "📚 Taza atyn jazyŋyz, tyrnakchsyz (misaly: Atomic Habits)"
        )
        return

    if not title:
        await message.answer("❌ Kitep aty tuura emes. Qayra jazyŋyz.")
        return

    book_id = await database.books.add(title)
    await database.user_books.add(message.from_user.id, book_id)

    await message.answer(
        f"📖 '{title}' kitebi tizmeŋizge qoshuldu!",
        reply_markup=main_keyboard
    )
    await state.clear()


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
async def hyperlink(message: Message, database: DatabaseManager):
    group = await database.groups.get_by_user(message.from_user.id)

    if group is None or not group['sheet_url']:
        await message.answer(
            "❌ Sizdin gruppaŋyzdyn ali google sheet'i ornotula elek.\n\n"
            "Gruppa adminine qayrylyŋyz — al /setsheet buirugun qoldonup ornotushu kk."
        )
        return

    sheet_url = group['sheet_url']
    response_text = f"Gruppaŋyzdyn zhyiyntyq shiltemesi: \n📊[zhalpy]({sheet_url})"

    await message.answer(
        response_text,
        parse_mode="Markdown",
        link_preview_options=LinkPreviewOptions(is_disabled=True)
    )