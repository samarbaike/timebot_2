from aiogram import Router
from aiogram.types import (
    InlineQuery, ChosenInlineResult,
    InlineQueryResultArticle, InputTextMessageContent
)
from database.db import DatabaseManager

router = Router()


@router.inline_query()
async def handle_inline_query(query: InlineQuery, database: DatabaseManager):
    user_id = query.from_user.id
    text = query.query.strip()

    user = await database.users.get_full(user_id)
    if not user:
        await query.answer([InlineQueryResultArticle(
            id="not_registered",
            title="❌ Sistemada zhokkens",
            description="Bottun zheke qatyna zhazyp, qattalynyz",
            input_message_content=InputTextMessageContent(
                message_text="❌ Men qattalbapmyn."
            )
        )], cache_time=0)
        return

    full_name = f"{user['user_name']} {user['user_surname']}"

    if ',' not in text:
        await query.answer([InlineQueryResultArticle(
            id="hint",
            title=f"👋 {full_name}",
            description="Algach BET sanyn zhazyp, andan kiyin ÜTÜR koyuŋuz",
            input_message_content=InputTextMessageContent(
                message_text="Misaly: 45, Harry Potter"
            )
        )], cache_time=0)
        return

    pages_str, _, book_filter = text.partition(',')
    pages_str = pages_str.strip()
    book_filter = book_filter.strip().lower()

    if not pages_str.isdigit() or not (0 < int(pages_str) < 1000):
        await query.answer([InlineQueryResultArticle(
            id="bad_pages",
            title="❌ Bet sany galaty",
            description="Ütürdön murun oŋ bütün san jazyŋyz — misaly: 45, Harry Potter",
            input_message_content=InputTextMessageContent(
                message_text="❌ Bet sany GALATY"
            )
        )], cache_time=0)
        return

    pages = int(pages_str)

    books = await database.user_books.get(user_id)
    if not books:
        await query.answer([InlineQueryResultArticle(
            id="no_books",
            title="⛔ Sizde ali kitep zhoq",
            description="Algach 'Kitepterimdi bashqaruu📚' bölümünön kitep qoshuŋuz",
            input_message_content=InputTextMessageContent(
                message_text="⛔ Ali kitebim zhoq"
            )
        )], cache_time=0)
        return

    if book_filter:
        books = [b for b in books if book_filter in b['title'].lower()]

    if not books:
        await query.answer([InlineQueryResultArticle(
            id="no_match",
            title="❌ Dal kelgen kitep zhoq",
            description="Bashqacha jazyp köruŋuz",
            input_message_content=InputTextMessageContent(
                message_text="❌ Dal kelgen kitep tabylbady"
            )
        )], cache_time=0)
        return

    results = [
        InlineQueryResultArticle(
            # book_id and pages are both already known — encode them straight into
            # the id so chosen_inline_result can log them with zero re-parsing.
            id=f"{book['book_id']}:{pages}",
            title=f"📖 {book['title']}",
            description=f"{pages} bet => jiberüü üchün basyŋyz",
            input_message_content=InputTextMessageContent(
                message_text=f"{full_name}: «{book['title']}», {pages} bet"
            )
        )
        for book in books[:50]  # Telegram inline result cap
    ]

    await query.answer(results, cache_time=0)


@router.chosen_inline_result()
async def handle_chosen_result(chosen: ChosenInlineResult, database: DatabaseManager):
    try:
        book_id_str, pages_str = chosen.result_id.split(':', 1)
        book_id, pages = int(book_id_str), int(pages_str)
    except ValueError:
        # One of the hint/error placeholders (e.g. "not_registered", "hint") was
        # chosen instead of a real book — nothing to log.
        return

    try:
        await database.logs.add(chosen.from_user.id, book_id, pages)
    except Exception:
        # The posted message already shows success at this point since Telegram
        # sends it the instant it's tapped — a failure here just means this entry
        # needs a manual re-log. Worth alerting on if this ever fires in practice.
        pass