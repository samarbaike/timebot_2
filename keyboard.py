from aiogram.types import (
    ReplyKeyboardMarkup, KeyboardButton,
    InlineKeyboardButton, InlineKeyboardMarkup
)

main_keyboard = ReplyKeyboardMarkup(
    keyboard=[
        [KeyboardButton(text="Bet kirgizüü📖")],
        [KeyboardButton(text="Kitepterimdi bashqaruu📚")],
        [KeyboardButton(text="Zhalpy📈"), KeyboardButton(text="Meniki👤")],   # NEW
        [KeyboardButton(text="Gruppaga qoshuluu 👥")]
    ],
    resize_keyboard=True,
    input_field_placeholder="Emne qylaly..."
)


def build_books_keyboard(books) -> InlineKeyboardMarkup:
    """Book picker used ONLY for logging pages read.
    No 'add new book' entry here anymore — that lives under
    'Kitepterimdi bashqaruu📚' -> 'Zhaŋy kitep qoshuu'."""
    buttons = []
    for book in books:
        buttons.append([InlineKeyboardButton(
            text=book['title'],
            callback_data=f"book:{book['book_id']}"
        )])
    return InlineKeyboardMarkup(inline_keyboard=buttons)


def build_manage_books_menu_keyboard() -> InlineKeyboardMarkup:
    """Top-level menu shown after pressing 'Kitepterimdi bashqaruu📚'."""
    buttons = [
        [InlineKeyboardButton(text="🗑 Kitep öchürüü", callback_data="manage_delete")],
        [InlineKeyboardButton(text="✅ Kitepti bütürüü", callback_data="manage_finish")],
        [InlineKeyboardButton(text="➕ Zhaŋy kitep qoshuu", callback_data="manage_add")],
    ]
    return InlineKeyboardMarkup(inline_keyboard=buttons)


def build_manage_books_list_keyboard(books, action: str) -> InlineKeyboardMarkup:
    """
    Book picker shared by the delete and finish flows.
    `action` becomes the callback prefix, e.g. action="delete" -> "delete_book:<id>".
    Always ends with a Back button that returns to the 3-option menu.
    """
    buttons = []
    for book in books:
        buttons.append([InlineKeyboardButton(
            text=book['title'],
            callback_data=f"{action}_book:{book['book_id']}"
        )])
    buttons.append([InlineKeyboardButton(text="⬅️ Artqa", callback_data="manage_back")])
    return InlineKeyboardMarkup(inline_keyboard=buttons)