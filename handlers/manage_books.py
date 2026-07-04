from aiogram import F, Router
from aiogram.types import CallbackQuery, Message
from aiogram.fsm.context import FSMContext

from services.states import ReadingTracker
from database.db import DatabaseManager
from keyboard import (
    build_manage_books_menu_keyboard,
    build_manage_books_list_keyboard,
)

router = Router()


def _pressed_button_text(callback: CallbackQuery) -> str:
    """Grabs the label of the button just pressed, so confirmations can
    mention the book title without an extra DB round-trip."""
    if callback.message.reply_markup:
        for row in callback.message.reply_markup.inline_keyboard:
            for button in row:
                if button.callback_data == callback.data:
                    return button.text
    return ""


@router.message(F.text == "Kitepterimdi bashqaruu📚")
async def open_manage_books_menu(message: Message):
    await message.answer(
        "Kitepteriŋizdi kanday bashqarabyz?",
        reply_markup=build_manage_books_menu_keyboard()
    )


@router.callback_query(F.data == "manage_back")
async def back_to_manage_menu(callback: CallbackQuery):
    await callback.message.edit_text(
        "Kitepteriŋizdi emne kylaly?",
        reply_markup=build_manage_books_menu_keyboard()
    )
    await callback.answer()


@router.callback_query(F.data == "manage_delete")
async def choose_book_to_delete(callback: CallbackQuery, database: DatabaseManager):
    books = await database.user_books.get(callback.from_user.id)
    if not books:
        await callback.answer("Sizde öchürö turgan kitep zhoq☢️", show_alert=True)
        return
    await callback.message.edit_text(
        "Qaisy kitepti öchürösüz?",
        reply_markup=build_manage_books_list_keyboard(books, action="delete")
    )
    await callback.answer()


@router.callback_query(F.data == "manage_finish")
async def choose_book_to_finish(callback: CallbackQuery, database: DatabaseManager):
    books = await database.user_books.get(callback.from_user.id)
    if not books:
        await callback.answer("Sizde bütürö turgan kitep zhoq☢️", show_alert=True)
        return
    await callback.message.edit_text(
        "Qaisy kitepti bütürdüŋüz?",
        reply_markup=build_manage_books_list_keyboard(books, action="finish")
    )
    await callback.answer()


@router.callback_query(F.data == "manage_add")
async def prompt_new_book(callback: CallbackQuery, state: FSMContext):
    await callback.message.edit_text("Zhaŋy kiteptin atyn zhazyŋyz:", reply_markup=None)
    await state.set_state(ReadingTracker.add_book)
    await callback.answer()


@router.callback_query(F.data.startswith("delete_book:"))
async def delete_book(callback: CallbackQuery, database: DatabaseManager):
    book_id = int(callback.data.split(":")[1])
    title = _pressed_button_text(callback)
    await database.user_books.delete(callback.from_user.id, book_id)
    await callback.message.edit_text(
        f"✅ '{title}' kitep tizmeŋizden öchürüldü.", reply_markup=None
    )
    await callback.answer()


@router.callback_query(F.data.startswith("finish_book:"))
async def finish_book(callback: CallbackQuery, database: DatabaseManager):
    book_id = int(callback.data.split(":")[1])
    title = _pressed_button_text(callback)
    await database.user_books.finished(callback.from_user.id, book_id)
    await callback.message.edit_text(
        f"✅ '{title}' kitebi bütkön dep belgilendi!", reply_markup=None
    )
    await callback.answer()