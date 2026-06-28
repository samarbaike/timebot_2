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
    text = query.query.strip()

    # Show format hint if input is incomplete
    if not text or text.count(',') < 2:
        hint = InlineQueryResultArticle(
            id="hint",
            title="Формат кандай?",
            description="Ат Фамилия, Китеп, Бет саны",
            input_message_content=InputTextMessageContent(
                message_text="Мисалы: Самарбек Бекиев, Dune, 45"
            )
        )
        await query.answer([hint], cache_time=0)
        return

    parts = [p.strip() for p in text.split(',', 2)]
    full_name, book_title, pages_str = parts

    # Validate page count
    if not pages_str.isdigit() or int(pages_str) <= 0:
        await query.answer([InlineQueryResultArticle(
            id="err", title="❌ Бет саны туура эмес",
            description="Оң бүтүн сан болушу керек",
            input_message_content=InputTextMessageContent(message_text="❌ Бет саны туура эмес")
        )], cache_time=0)
        return

    pages = int(pages_str)

    # Validate name has two parts
    name_parts = full_name.split(None, 1)
    if len(name_parts) < 2:
        await query.answer([InlineQueryResultArticle(
            id="err", title="❌ Ат жана фамилия жазыңыз",
            description="Мисалы: Самарбек Бекиев",
            input_message_content=InputTextMessageContent(message_text="❌ Ат жана фамилия жазыңыз")
        )], cache_time=0)
        return

    user_name, user_surname = name_parts[0], name_parts[1]
    user = await database.users.get_by_name(user_name, user_surname)

    if not user:
        result = InlineQueryResultArticle(
            id="not_found",
            title=f"❌ {full_name} табылган жок",
            description="Колдонуучу катталган эмес. Алгач /start жазсын.",
            input_message_content=InputTextMessageContent(
                message_text=f"❌ {full_name} катталган эмес"
            )
        )
    else:
        result = InlineQueryResultArticle(
            id=str(uuid.uuid4()),  # unique id so Telegram doesn't cache it
            title=f"✅ {full_name}",
            description=f"«{book_title}» — {pages} бет",
            input_message_content=InputTextMessageContent(
                message_text=f"📖 {full_name}: «{book_title}» — {pages} бет бүгүн окуду"
            )
        )

    await query.answer([result], cache_time=0)


@router.chosen_inline_result()
async def handle_chosen_result(chosen: ChosenInlineResult, database: DatabaseManager):
    # Re-parse the same query text — this is intentional, not duplication.
    # inline_query only previews; this handler is the one that actually writes.
    parts = [p.strip() for p in chosen.query.split(',', 2)]
    if len(parts) < 3:
        return

    full_name, book_title, pages_str = parts
    if not pages_str.isdigit() or int(pages_str) <= 0:
        return

    name_parts = full_name.split(None, 1)
    if len(name_parts) < 2:
        return

    user_name, user_surname = name_parts[0], name_parts[1]
    user = await database.users.get_by_name(user_name, user_surname)
    if not user:
        return

    telegram_id = user['telegram_id']
    book_id = await database.books.add(book_title)
    await database.user_books.add(telegram_id, book_id)
    await database.logs.add(telegram_id, book_id, int(pages_str))