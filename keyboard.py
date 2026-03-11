from aiogram.types import ReplyKeyboardMarkup, KeyboardButton

main_keyboard = ReplyKeyboardMarkup(
    keyboard=[
        [KeyboardButton(text="Bet kirgizuu📖")],
        [KeyboardButton(text="Zhalpy📈"), KeyboardButton(text="Meniki👤")]
    ],
    resize_keyboard=True,
    input_field_placeholder="Emne kylaly..."
)
