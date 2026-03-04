from aiogram.types import ReplyKeyboardMarkup, KeyboardButton

main_keyboard = ReplyKeyboardMarkup(
    keyboard=[
        [KeyboardButton(text="Бет киргизүү📖")],
        [KeyboardButton(text="Progress📈"), KeyboardButton(text="Меники👤")]
    ],
    resize_keyboard=True,
    input_field_placeholder="Эмне кылалы..."
)
