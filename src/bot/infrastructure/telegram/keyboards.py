from telegram import (
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    KeyboardButton,
    ReplyKeyboardMarkup,
)


def phone_keyboard() -> ReplyKeyboardMarkup:
    button = KeyboardButton("Compartir mi teléfono", request_contact=True)
    return ReplyKeyboardMarkup(
        [[button]], resize_keyboard=True, one_time_keyboard=True
    )


def consent_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        [
            [
                InlineKeyboardButton("Acepto", callback_data="consent:si"),
                InlineKeyboardButton("No acepto", callback_data="consent:no"),
            ]
        ]
    )
