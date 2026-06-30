from aiogram.types import (
    ReplyKeyboardMarkup, KeyboardButton,
    InlineKeyboardButton, InlineKeyboardMarkup
)

main_keyboard = ReplyKeyboardMarkup(
    keyboard=[
        [KeyboardButton(text="Bet kirgizuu📖")],
        [KeyboardButton(text="Zhalpy📈"), KeyboardButton(text="Meniki👤")],
        [KeyboardButton(text="Gruppaga qoshuluu 👥")]
    ],
    resize_keyboard=True,
    input_field_placeholder="Emne qylaly..."
)

def build_books_keyboard(books) -> InlineKeyboardMarkup:
    buttons = []
    for book in books:
        buttons.append([InlineKeyboardButton(
            text=book['title'],
            callback_data=f"book:{book['book_id']}"
        )])
    buttons.append([InlineKeyboardButton(
        text="Zhaŋy kitep ➕",
        callback_data="add_new_book"
    )])
    return InlineKeyboardMarkup(inline_keyboard=buttons)