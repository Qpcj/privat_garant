from telegram import InlineKeyboardButton, InlineKeyboardMarkup

def get_payment_retry_keyboard(language):
    from messages import MESSAGES
    messages = MESSAGES[language]
    
    keyboard = [
        [InlineKeyboardButton("🔄 Повторить попытку", callback_data="retry_payment")],
        [InlineKeyboardButton(messages['support'], callback_data="support")]
    ]
    return InlineKeyboardMarkup(keyboard)

def get_buyer_deal_keyboard(language):
    from messages import MESSAGES
    messages = MESSAGES[language]
    
    keyboard = [
        [InlineKeyboardButton(messages['confirm_payment'], callback_data="confirm_payment")],
        [InlineKeyboardButton(messages['contact_support'], callback_data="contact_support")]
    ]
    return InlineKeyboardMarkup(keyboard)

def get_language_keyboard():
    keyboard = [
        [InlineKeyboardButton("🇷🇺 Русский", callback_data="lang_ru")],
        [InlineKeyboardButton("🇬🇧 English", callback_data="lang_en")]
    ]
    return InlineKeyboardMarkup(keyboard)

def get_welcome_inline_keyboard(language):
    from messages import MESSAGES
    messages = MESSAGES[language]
    
    keyboard = [
        [
            InlineKeyboardButton(messages['create_deal'], callback_data="create_deal"),
            InlineKeyboardButton(messages['profile'], callback_data="profile")
        ],
        [
            InlineKeyboardButton(messages['requisites'], callback_data="requisites"),
            InlineKeyboardButton(messages['support'], callback_data="support")
        ],
        [InlineKeyboardButton(messages['language'], callback_data="change_language")]
    ]
    return InlineKeyboardMarkup(keyboard)

# Реквизиты - главное меню
def get_requisites_main_keyboard(language):
    keyboard = [
        [InlineKeyboardButton("➕ Добавить реквизиты", callback_data="add_requisites")],
        [InlineKeyboardButton("👀 Посмотреть реквизиты", callback_data="view_requisites")],
        [InlineKeyboardButton("⬅️ Назад", callback_data="back_main")]
    ]
    return InlineKeyboardMarkup(keyboard)

# Добавление реквизитов
def get_requisites_add_type_keyboard(language):
    keyboard = [
        [InlineKeyboardButton("💳 Банковская карта", callback_data="add_bank_card")],
        [InlineKeyboardButton("💎 TON кошелёк", callback_data="add_ton_wallet")],
        [InlineKeyboardButton("⬅️ Назад", callback_data="back_requisites")]
    ]
    return InlineKeyboardMarkup(keyboard)

# Просмотр реквизитов  
def get_requisites_view_type_keyboard(language):
    keyboard = [
        [InlineKeyboardButton("💳 Банковские карты", callback_data="view_bank_cards")],
        [InlineKeyboardButton("💎 TON кошелёк", callback_data="view_ton_wallet")],
        [InlineKeyboardButton("⬅️ Назад", callback_data="back_requisites")]
    ]
    return InlineKeyboardMarkup(keyboard)

# Выбор валюты для карты

def get_card_currency_keyboard(language):
    """
    Клавиатура выбора валюты для банковской карты.
    Показывает варианты: 🇷🇺 RUB, 🇪🇺 EUR, 🇺🇿 UZS, 🇰🇿 KZT, 🇰🇬 KGS, 🇮🇩 IDR, 🇺🇦 UAH, 🇧🇾 BYN
    Callback data сохраняет код валюты в верхнем регистре, например: card_currency_RUB
    """
    keyboard = [
        [InlineKeyboardButton("🇷🇺 RUB", callback_data="card_currency_RUB")],
        [InlineKeyboardButton("🇪🇺 EUR", callback_data="card_currency_EUR")],
        [InlineKeyboardButton("🇺🇿 UZS", callback_data="card_currency_UZS")],
        [InlineKeyboardButton("🇰🇿 KZT", callback_data="card_currency_KZT")],
        [InlineKeyboardButton("🇰🇬 KGS", callback_data="card_currency_KGS")],
        [InlineKeyboardButton("🇮🇩 IDR", callback_data="card_currency_IDR")],
        [InlineKeyboardButton("🇺🇦 UAH", callback_data="card_currency_UAH")],
        [InlineKeyboardButton("🇧🇾 BYN", callback_data="card_currency_BYN")],
        [InlineKeyboardButton("⬅️ Назад", callback_data="back_requisites_add")]
    ]
    return InlineKeyboardMarkup(keyboard)

def get_back_to_requisites_keyboard(language):
    keyboard = [
        [InlineKeyboardButton("⬅️ Назад в реквизиты", callback_data="back_requisites")]
    ]
    return InlineKeyboardMarkup(keyboard)

def get_deal_type_keyboard(language):
    from messages import MESSAGES
    messages = MESSAGES[language]
    
    keyboard = [
        [InlineKeyboardButton(messages['gifts'], callback_data="deal_gifts")],
        [InlineKeyboardButton(messages['usertag'], callback_data="deal_usertag")],
        [InlineKeyboardButton(messages['channel'], callback_data="deal_channel")],
        [InlineKeyboardButton(messages['back'], callback_data="back_main")]
    ]
    return InlineKeyboardMarkup(keyboard)

def get_currency_keyboard(language):
    from messages import MESSAGES
    messages = MESSAGES[language]
    
    keyboard = [
        [InlineKeyboardButton("💳 На карту", callback_data="currency_card")],
        [InlineKeyboardButton("⭐ Stars", callback_data="currency_stars")],
        [InlineKeyboardButton("💎 Ton", callback_data="currency_ton")],
        [InlineKeyboardButton(messages['back'], callback_data="back_deal_type")]
    ]
    return InlineKeyboardMarkup(keyboard)

def get_fiat_currency_keyboard(language):
    from messages import MESSAGES
    messages = MESSAGES[language]
    
    keyboard = [
        [InlineKeyboardButton("RUB 🇷🇺", callback_data="fiat_RUB")],
        [InlineKeyboardButton("EUR 🇪🇺", callback_data="fiat_EUR")],
        [InlineKeyboardButton("UZS 🇺🇿", callback_data="fiat_UZS")],
        [InlineKeyboardButton("KZT 🇰🇿", callback_data="fiat_KZT")],
        [InlineKeyboardButton("KGS 🇰🇬", callback_data="fiat_KGS")],
        [InlineKeyboardButton("IDR 🇮🇩", callback_data="fiat_IDR")],
        [InlineKeyboardButton("UAH 🇺🇦", callback_data="fiat_UAH")],
        [InlineKeyboardButton("BYN 🇧🇾", callback_data="fiat_BYN")],
        [InlineKeyboardButton(messages['back'], callback_data="back_currency")]
    ]
    return InlineKeyboardMarkup(keyboard)

def get_warning_keyboard(language):
    from messages import MESSAGES
    messages = MESSAGES[language]
    
    keyboard = [
        [InlineKeyboardButton(messages['i_read'], callback_data="warning_read")],
        [InlineKeyboardButton(messages['back'], callback_data="back_fiat")]
    ]
    return InlineKeyboardMarkup(keyboard)

def get_deal_confirmation_keyboard(language):
    from messages import MESSAGES
    messages = MESSAGES[language]
    
    keyboard = [
        [InlineKeyboardButton(messages['create_deal'], callback_data="confirm_deal")],
        [InlineKeyboardButton(messages['cancel'], callback_data="cancel_deal")]
    ]
    return InlineKeyboardMarkup(keyboard)

def get_deal_management_keyboard(language):
    from messages import MESSAGES
    messages = MESSAGES[language]
    
    keyboard = [
        [InlineKeyboardButton(messages['share_deal'], callback_data="share_deal")],
        [
            InlineKeyboardButton(messages['exit_deal'], callback_data="exit_deal"),
            InlineKeyboardButton(messages['my_deals'], callback_data="my_deals")
        ]
    ]
    return InlineKeyboardMarkup(keyboard)

def get_buyer_payment_keyboard(language):
    from messages import MESSAGES
    messages = MESSAGES[language]
    
    keyboard = [
        [InlineKeyboardButton(messages['confirm_payment'], callback_data="confirm_payment")],
        [InlineKeyboardButton(messages['contact_support'], callback_data="contact_support")]
    ]
    return InlineKeyboardMarkup(keyboard)

def get_seller_gift_sent_keyboard(language):
    from messages import MESSAGES
    messages = MESSAGES[language]
    
    keyboard = [
        [InlineKeyboardButton(messages['gift_sent'], callback_data="gift_sent")],
        [InlineKeyboardButton(messages['contact_support'], callback_data="contact_support")]
    ]
    return InlineKeyboardMarkup(keyboard)

