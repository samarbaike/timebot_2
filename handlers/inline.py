import uuid
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
                message_text="❌ Men qattalbapmyn. Botqo zhazuum kerek."
            )
        )], cache_time=0)
        return

    full_name = f"{user['user_name']} {user['user_surname']}"

    if not text or ',' not in text:
        await query.answer([InlineQueryResultArticle(
            id="hint",
            title=f"👋 {full_name}",
            description="Kitep aty, bet sany",
            input_message_content=InputTextMessageContent(
                message_text=f"Misaly: Harry Potter, 45"
            )
        )], cache_time=0)
        return

    parts = [p.strip() for p in text.split(',', 1)]
    book_title = parts[0]
    pages_str = parts[1] if len(parts) > 1 else ""

    if not pages_str.isdigit() or int(pages_str) <= 0:
        await query.answer([InlineQueryResultArticle(
            id="err",
            title="❌ Bet sany galaty",
            description="Oŋ bütün san bolush kerek — misaly: Harry Potter, 45",
            input_message_content=InputTextMessageContent(
                message_text="❌ Bet sany galaty"
            )
        )], cache_time=0)
        return

    await query.answer([InlineQueryResultArticle(
        id=str(uuid.uuid4()),
        title=f"✅ {full_name}",
        description=f"«{book_title}» — {int(pages_str)} bet",
        input_message_content=InputTextMessageContent(
            message_text=f"📖 {full_name}: «{book_title}» — {int(pages_str)} bet"
        )
    )], cache_time=0)


@router.chosen_inline_result()
async def handle_chosen_result(chosen: ChosenInlineResult, database: DatabaseManager):
    telegram_id = chosen.from_user.id  # identity from Telegram, not typed text

    parts = [p.strip() for p in chosen.query.split(',', 1)]
    if len(parts) < 2:
        return

    book_title, pages_str = parts
    if not pages_str.isdigit() or int(pages_str) <= 0:
        return

    book_id = await database.books.add(book_title)
    await database.user_books.add(telegram_id, book_id)
    await database.logs.add(telegram_id, book_id, int(pages_str))