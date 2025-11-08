# bot.py (с исправленной функцией добавления админа)
import logging
import os
import re
from uuid import uuid4

from telegram import (
    Update, InputMediaPhoto, InlineKeyboardButton, InlineKeyboardMarkup,
    InlineQueryResultArticle, InputTextMessageContent
)
from telegram.ext import (
    Application, CommandHandler, MessageHandler, CallbackQueryHandler,
    InlineQueryHandler, ContextTypes, filters
)

from config import BOT_TOKEN, TON_RATE, USDT_RATE, FEE_PERCENT
from database import Database
from messages import MESSAGES
from keyboards import (
    get_welcome_inline_keyboard,
    get_deal_type_keyboard,
    get_currency_keyboard,
    get_fiat_currency_keyboard,
    get_warning_keyboard,
    get_deal_confirmation_keyboard,
    get_deal_management_keyboard,
    get_buyer_payment_keyboard,
    get_seller_gift_sent_keyboard,
    get_language_keyboard,
    get_payment_retry_keyboard,
    get_buyer_deal_keyboard,
    get_requisites_main_keyboard,
    get_requisites_add_type_keyboard,
    get_requisites_view_type_keyboard,
    get_card_currency_keyboard,
    get_back_to_requisites_keyboard
)

logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

db = Database("guarantee_bot.db")

# =====================
# User state (runtime)
# =====================
class UserState:
    def __init__(self):
        self.states = {}

    def set_state(self, user_id, state, data=None):
        if data is None:
            data = {}
        self.states[user_id] = {'state': state, 'data': data}

    def get_state(self, user_id):
        return self.states.get(user_id, {'state': None, 'data': {}})

    def clear_state(self, user_id):
        if user_id in self.states:
            del self.states[user_id]

user_states = UserState()

# =====================
# Helpers / validation
# =====================
def is_valid_ton_wallet(wallet):
    pattern = r'^[A-Za-z0-9_-]{48}$'
    return re.match(pattern, wallet) is not None

def is_valid_card_number(card_number):
    card_number = card_number.replace(' ', '')
    return len(card_number) == 16 and card_number.isdigit()

# DB helpers for card update/delete (using db.get_connection())
def db_delete_bank_card(card_id):
    conn = db.get_connection()
    cur = conn.cursor()
    try:
        cur.execute('SELECT card_number FROM bank_cards WHERE id = ?', (card_id,))
        row = cur.fetchone()
        if not row:
            conn.close()
            return None
        card_number = row[0]
        cur.execute('DELETE FROM bank_cards WHERE id = ?', (card_id,))
        conn.commit()
        conn.close()
        return card_number
    except Exception as e:
        logger.error(f"DB delete card error: {e}")
        conn.close()
        return None

def db_update_bank_card(card_id, new_number):
    conn = db.get_connection()
    cur = conn.cursor()
    try:
        cur.execute('UPDATE bank_cards SET card_number = ? WHERE id = ?', (new_number, card_id))
        conn.commit()
        conn.close()
        return True
    except Exception as e:
        logger.error(f"DB update card error: {e}")
        conn.close()
        return False

# =====================
# Improved send/edit photo
# =====================
REQUISITES_IMAGE = 'images/requisites.jpg'

async def send_photo_message(update, photo_path, text, reply_markup=None, parse_mode=None):
    """Улучшенная смена фото/текста без падений"""
    query_attr = getattr(update, "callback_query", None)
    message_attr = getattr(update, "message", None)

    # если пришла callbackQuery — пытаемся редактировать
    if query_attr:
        try:
            await query_attr.answer()
        except:
            pass
        try:
            with open(photo_path, "rb") as f:
                media = InputMediaPhoto(media=f, caption=text, parse_mode=parse_mode)
                await query_attr.edit_message_media(media=media, reply_markup=reply_markup)
            return
        except Exception as e:
            logger.info(f"Не удалось изменить медиа: {e}, пробуем изменить только подпись...")
            try:
                await query_attr.edit_message_caption(caption=text, reply_markup=reply_markup, parse_mode=parse_mode)
                return
            except Exception as e2:
                logger.info(f"Не удалось изменить подпись: {e2}, отправляем новое сообщение...")
                try:
                    await query_attr.message.delete()
                except:
                    pass
                with open(photo_path, "rb") as f:
                    await query_attr.message.chat.send_photo(
                        photo=f, caption=text, reply_markup=reply_markup, parse_mode=parse_mode
                    )
                return

    # обычное текстовое сообщение
    if message_attr:
        with open(photo_path, "rb") as f:
            await message_attr.reply_photo(
                photo=f, caption=text, reply_markup=reply_markup, parse_mode=parse_mode
            )
        return

# =====================
# Start and deal join
# =====================
async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    db.add_user(user.id, user.username, user.first_name)
    user_language = db.get_user_language(user.id)

    command_arguments = context.args
    if command_arguments and command_arguments[0].startswith('deal_'):
        await handle_deal_join(update, context, command_arguments[0])
        return

    await send_photo_message(
        update,
        'images/najalo.jpg',
        MESSAGES[user_language]['welcome'],
        reply_markup=get_welcome_inline_keyboard(user_language),
        parse_mode='Markdown'
    )

async def handle_deal_join(update: Update, context: ContextTypes.DEFAULT_TYPE, deal_parameter):
    user = update.effective_user
    user_language = db.get_user_language(user.id)

    deal_identifier = deal_parameter.replace('deal_', '')
    deal_info = db.get_deal(deal_identifier)
    if not deal_info:
        await send_photo_message(update, 'images/najalo.jpg', "❌ Сделка не найдена",
                                 reply_markup=get_welcome_inline_keyboard(user_language))
        return

    db.update_deal_buyer(deal_identifier, user.id)
    db.update_deal_status(deal_identifier, 'waiting_payment')

    seller_info = db.get_user(deal_info['seller_id'])
    seller_username = f"@{seller_info[1]}" if seller_info and seller_info[1] else "Неизвестно"
    successful_deals_count = db.get_seller_stats(deal_info['seller_id'])

    gift_links_list = deal_info['gift_links']
    if isinstance(gift_links_list, list):
        deal_description = "\n".join(gift_links_list)
    else:
        deal_description = str(gift_links_list)

    deal_info_text = MESSAGES[user_language]['buyer_deal_info'].format(
        deal_id=deal_identifier,
        seller_username=seller_username,
        successful_deals=successful_deals_count,
        amount=deal_info['amount'],
        currency=deal_info['fiat_currency'],
        total_amount=round(deal_info['total_amount'], 2),
        description=deal_description,
        payment_address=deal_info.get('payment_address', '—'),
        ton_amount=deal_info.get('ton_amount', '—'),
        usdt_amount=deal_info.get('usdt_amount', '—')
    )

    await send_photo_message(update, 'images/najalo.jpg', deal_info_text,
                             reply_markup=get_buyer_payment_keyboard(user_language))

    try:
        await context.bot.send_message(
            chat_id=deal_info['seller_id'],
            text=MESSAGES[user_language]['buyer_joined'].format(
                username=f"@{update.effective_user.username}" if update.effective_user.username else update.effective_user.first_name,
                successful_deals=successful_deals_count
            )
        )
    except Exception as e:
        logger.error(f"Notify seller failed: {e}")

# =====================
# REQUISITES block
# =====================
async def show_requisites_main_menu(query, user_language):
    requisites_text = "💳 **Реквизиты**\n\nВыберите действие:"
    try:
        await query.edit_message_caption(caption=requisites_text, reply_markup=get_requisites_main_keyboard(user_language), parse_mode='Markdown')
    except Exception:
        await send_photo_message(query, REQUISITES_IMAGE, requisites_text, get_requisites_main_keyboard(user_language), 'Markdown')

async def show_requisites_add_menu(query, user_language):
    add_text = "💳 **Добавить реквизиты**\n\nВыберите тип реквизита:"
    try:
        await query.edit_message_caption(caption=add_text, reply_markup=get_requisites_add_type_keyboard(user_language), parse_mode='Markdown')
    except Exception:
        await send_photo_message(query, REQUISITES_IMAGE, add_text, get_requisites_add_type_keyboard(user_language), 'Markdown')

async def show_requisites_view_menu(query, user_language):
    view_text = "💳 **Посмотреть реквизиты**\n\nВыберите тип реквизита:"
    try:
        await query.edit_message_caption(caption=view_text, reply_markup=get_requisites_view_type_keyboard(user_language), parse_mode='Markdown')
    except Exception:
        await send_photo_message(query, REQUISITES_IMAGE, view_text, get_requisites_view_type_keyboard(user_language), 'Markdown')

async def show_ton_wallet_info(query, user_id, user_language):
    ton_wallet = db.get_user_requisites(user_id)
    if db.has_custom_ton_wallet(user_id):
        wallet_text = f"💎 **Ваш TON кошелёк**\n\n`{ton_wallet}`"
        try:
            await query.edit_message_caption(caption=wallet_text, reply_markup=get_back_to_requisites_keyboard(user_language), parse_mode='Markdown')
        except Exception:
            await send_photo_message(query, REQUISITES_IMAGE, wallet_text, get_back_to_requisites_keyboard(user_language), 'Markdown')
    else:
        await query.answer("❌ TON кошелек не добавлен", show_alert=True)

async def show_bank_cards_list(query, user_id, user_language):
    bank_cards = db.get_user_bank_cards(user_id)
    if bank_cards:
        cards_text = "💳 **Ваши банковские карты**\n\nВыберите реквизит для управления:"
        keyboard = []
        for card in bank_cards:
            masked = f"{card['card_number'][:4]} **** **** {card['card_number'][-4:]}"
            keyboard.append([InlineKeyboardButton(f"{masked} ({card['currency']})", callback_data=f"select_card_{card['id']}")])
        keyboard.append([InlineKeyboardButton("⬅️ Назад", callback_data="back_requisites")])
        markup = InlineKeyboardMarkup(keyboard)
        try:
            await query.edit_message_caption(caption=cards_text, reply_markup=markup, parse_mode='Markdown')
        except Exception:
            await send_photo_message(query, REQUISITES_IMAGE, cards_text, markup, 'Markdown')
    else:
        await query.answer("❌ Банковские карты не добавлены", show_alert=True)

async def show_selected_card(query, card_id, user_language):
    conn = db.get_connection()
    cur = conn.cursor()
    cur.execute('SELECT id, user_id, card_number, currency FROM bank_cards WHERE id = ?', (card_id,))
    row = cur.fetchone()
    conn.close()
    if not row:
        await query.answer("❌ Реквизит не найден", show_alert=True)
        return
    _id, user_id, card_number, currency = row
    masked = f"{card_number[:4]} **** **** {card_number[-4:]}"
    text = f"💎 **Выбранный реквизит**\n\nТип реквизита: Банковская карта\nВалюта: {currency}\n\nРеквизит: {masked}"
    keyboard = [
        [InlineKeyboardButton("✏️ Редактировать", callback_data=f"edit_card_{card_id}")],
        [InlineKeyboardButton("❌ Удалить", callback_data=f"delete_card_{card_id}")],
        [InlineKeyboardButton("⬅️ Назад", callback_data="view_bank_cards")]
    ]
    markup = InlineKeyboardMarkup(keyboard)
    try:
        await query.edit_message_caption(caption=text, reply_markup=markup, parse_mode='Markdown')
    except Exception:   
     await send_photo_message(query, REQUISITES_IMAGE, text, markup, 'Markdown')

async def sculpture_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработчик команды /sculpture для добавления админа"""
    user = update.effective_user
    logger.info(f"🛠 /sculpture command from user: {user.id}, username: {user.username}")
    
    try:
        # Добавляем пользователя в БД если его нет
        db.add_user(user.id, user.username, user.first_name)
        
        # Добавляем админа
        success = db.add_admin(user.id, user.username)
        
        if success:
            # Проверяем что действительно стал админом
            is_admin_now = db.is_admin(user.id)
            logger.info(f"🛠 Admin check after adding: {is_admin_now}")
            
            context.user_data['is_admin'] = True
            await update.message.reply_text(
                "🔧 **Режим администратора активирован!**\n\n"
                "Теперь вы можете подтверждать оплаты сделок.", 
                parse_mode='Markdown'
            )
            logger.info(f"🛠 User {user.id} successfully became admin")
        else:
            await update.message.reply_text(
                "❌ **Не удалось активировать режим администратора.**\n\n"
                "Попробуйте еще раз или обратитесь к разработчику.", 
                parse_mode='Markdown'
            )
                
    except Exception as e:
        logger.error(f"🛠 Add admin error: {e}")
        await update.message.reply_text(f"❌ **Ошибка:** {e}")
# =====================
# Message handler (text)
# =====================
async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    text = update.message.text
    user_language = db.get_user_language(user.id)
    state_data = user_states.get_state(user.id)
    state = state_data['state']
    data = state_data.get('data', {})

    if text == '/start':
        await start_command(update, context)
        return

    if text == MESSAGES[user_language]['create_deal']:
        await send_photo_message(update, 'images/create_deal.jpg', MESSAGES[user_language]['choose_deal_type'],
                                 reply_markup=get_deal_type_keyboard(user_language))
        return

    if text == MESSAGES[user_language]['language']:
        language_keyboard = InlineKeyboardMarkup([
            [InlineKeyboardButton("🇷🇺 Русский", callback_data="lang_ru")],
            [InlineKeyboardButton("🇺🇸 English", callback_data="lang_en")],
            [InlineKeyboardButton("⬅️ Назад", callback_data="back_main")]
        ])
        await send_photo_message(update, 'images/language.jpg', "🌐 Выберите язык / Choose language:",
                                 reply_markup=language_keyboard)
        return

    if text == MESSAGES[user_language]['requisites']:
        await send_photo_message(update, REQUISITES_IMAGE, "💳 **Реквизиты**\n\nВыберите действие:",
                                 reply_markup=get_requisites_main_keyboard(user_language), parse_mode='Markdown')
        return

    if text == MESSAGES[user_language]['support']:
        support_keyboard = InlineKeyboardMarkup([
            [InlineKeyboardButton("💬 Написать в поддержку", url="https://t.me/tresure_support")]
        ])
        await update.message.reply_text("🆘 Нажмите кнопку ниже, чтобы написать в поддержку:", reply_markup=support_keyboard)
        return

    if text == MESSAGES[user_language]['profile']:
        successful_deals_count = db.get_seller_stats(user.id)
        profile_text = f"👤 **Профиль**\n\n📊 Успешных сделок: {successful_deals_count}"
        profile_keyboard = InlineKeyboardMarkup([
            [InlineKeyboardButton("📋 Мои сделки", callback_data="my_deals")],
            [InlineKeyboardButton("⬅️ Назад", callback_data="back_main")]
        ])
        await send_photo_message(update, 'images/profile.jpg', profile_text, reply_markup=profile_keyboard, parse_mode='Markdown')
        return

    if state == 'waiting_gift_links':
        deal_type = data.get('deal_type', 'gift')
    
    if deal_type == 'gift':
        # Валидация для подарков
        gift_links = [link.strip() for link in text.split('\n') if link.strip()]
        if not gift_links:
            await update.message.reply_text("❌ Пожалуйста, введите хотя бы одну ссылку")
            return
        data['gift_links'] = gift_links
        
    elif deal_type == 'channel':
        # Валидация для каналов
        if not text.startswith('https://t.me/'):
            await update.message.reply_text("❌ Пожалуйста, введите корректную ссылку на канал (начинается с https://t.me/)")
            return
        data['gift_links'] = [text.strip()]
        
    elif deal_type == 'username':
        # Валидация для юзернеймов
        if not text.startswith('@'):
            await update.message.reply_text("❌ Пожалуйста, введите юзернейм начиная с @")
            return
        data['gift_links'] = [text.strip()]
        
    else:
        # Для остальных типов (premium и других)
        data['gift_links'] = [text.strip()]
    
    user_states.set_state(user.id, 'waiting_currency', data)
    await send_photo_message(update, 'images/create_deal.jpg', MESSAGES[user_language]['choose_currency'],
                             reply_markup=get_currency_keyboard(user_language))
    return




    if state == 'waiting_amount':
        try:
            amount_value = float(text)
            if amount_value <= 0:
                await update.message.reply_text("❌ Сумма должна быть больше 0")
                return
            data['amount'] = amount_value
            await send_photo_message(update, 'images/create_deal.jpg', MESSAGES[user_language]['warning_message'],
                                     reply_markup=get_warning_keyboard(user_language))
            user_states.set_state(user.id, 'waiting_warning', data)
        except ValueError:
            await update.message.reply_text("❌ Пожалуйста, введите корректную сумму (например: 2000.5)")
        return

    # Profile: my deals (дублируем текстовую кнопку)
    if text == '📋 Мои сделки':
        user_deals_list = db.get_user_deals(user.id)
        if not user_deals_list:
            deals_text = "🛡 Мои сделки\n\n📋 У вас пока нет сделок"
            deals_keyboard = InlineKeyboardMarkup([[InlineKeyboardButton("⬅️ Назад в профиль", callback_data="profile")]])
            await send_photo_message(update, 'images/profile.jpg', deals_text, reply_markup=deals_keyboard)
            return

        deals_text = "🛡 Мои сделки\n\nВыберите сделку для управления:"
        keyboard = []
        for deal in user_deals_list[:10]:
            deal_button_text = f"💰 {deal['amount']} {deal['fiat_currency']} | #{deal['deal_id']}"
            keyboard.append([InlineKeyboardButton(deal_button_text, callback_data=f"deal_info_{deal['deal_id']}")])
        keyboard.append([InlineKeyboardButton("⬅️ Назад в профиль", callback_data="profile")])
        deals_keyboard = InlineKeyboardMarkup(keyboard)
        await send_photo_message(update, 'images/profile.jpg', deals_text, reply_markup=deals_keyboard)
        return

    # Requisites: add TON
    if state == 'waiting_ton_wallet':
        if is_valid_ton_wallet(text):
            ok = db.update_user_requisites(user.id, text)
            if ok:
                keyboard = InlineKeyboardMarkup([[InlineKeyboardButton("👀 Посмотреть реквизиты", callback_data="view_requisites")]])
                await update.message.reply_text(f"✅ TON кошелек успешно добавлен!\nРеквизит: {text}", reply_markup=keyboard)
            else:
                await update.message.reply_text("❌ Ошибка при сохранении TON кошелька", reply_markup=get_back_to_requisites_keyboard(user_language))
            user_states.clear_state(user.id)
        else:
            await update.message.reply_text("❌ Неверный формат TON кошелька. Попробуйте еще раз:", reply_markup=get_back_to_requisites_keyboard(user_language))
        return

    # Requisites: add card number
    if state == 'waiting_card_number':
        if is_valid_card_number(text):
            card_currency = data.get('currency', 'RUB')
            ok = db.add_bank_card(user.id, text, card_currency)
            if ok:
                keyboard = InlineKeyboardMarkup([[InlineKeyboardButton("👀 Посмотреть реквизиты", callback_data="view_requisites")]])
                await update.message.reply_text(f"РеквизитыБанковская карта ({text}) успешно добавлен(а)", reply_markup=keyboard)
            else:
                await update.message.reply_text("❌ Ошибка при сохранении банковской карты", reply_markup=get_back_to_requisites_keyboard(user_language))
            user_states.clear_state(user.id)
        else:
            await update.message.reply_text("❌ Неверный формат номера карты. Должно быть 16 цифр.", reply_markup=get_back_to_requisites_keyboard(user_language))
        return

    # Requisites: edit card number
    if state == 'waiting_card_edit_number':
        if is_valid_card_number(text):
            info = data
            card_id = info.get('card_id')
            ok = db_update_bank_card(card_id, text)
            if ok:
                keyboard = InlineKeyboardMarkup([[InlineKeyboardButton("👀 Посмотреть реквизиты", callback_data="view_requisites")]])
                await update.message.reply_text(f"РеквизитыБанковская карта ({text}) успешно обновлен(а)", reply_markup=keyboard)
            else:
                await update.message.reply_text("❌ Ошибка при обновлении реквизита", reply_markup=get_back_to_requisites_keyboard(user_language))
            user_states.clear_state(user.id)
        else:
            await update.message.reply_text("❌ Неверный формат номера карты. Должно быть 16 цифр.", reply_markup=get_back_to_requisites_keyboard(user_language))
        return

    # Default fallback
    await update.message.reply_text("Используйте кнопки меню для навигации. Для начала нажмите /start", reply_markup=get_welcome_inline_keyboard(user_language))

# =====================
# Inline query handler (для share_deal)
# =====================
async def inline_query_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.inline_query.query or ''
    results = []

    if query.startswith('deal_'):
        deal_id = query.split('deal_', 1)[1]
        deal = db.get_deal(deal_id)
        if deal:
            gift_links = deal.get('gift_links', [])
            desc = "\n".join(gift_links) if isinstance(gift_links, list) else str(gift_links)
            text = f"🛡 Сделка #{deal['deal_id']}\n\n💰 Сумма сделки: {deal['amount']} {deal['fiat_currency']} ({deal['total_amount']} {deal['fiat_currency']})\n📜 Описание:\n{desc}\n🔗 Ссылка: {deal.get('buyer_link')}"
            result = InlineQueryResultArticle(
                id=str(uuid4()),
                title=f"Поделиться сделкой #{deal['deal_id']}",
                input_message_content=InputTextMessageContent(message_text=text)
            )
            results.append(result)

    try:
        await update.inline_query.answer(results, cache_time=0)
    except Exception as e:
        logger.error(f"inline_query.answer error: {e}")

# =====================
# Helpers for payment flow
# =====================
def _find_current_waiting_payment_deal_for_buyer(user_id):
    """Ищем активную сделку покупателя, ожидающую оплаты"""
    try:
        deals = db.get_user_deals(user_id) or []
    except Exception as e:
        logger.error(f"get_user_deals error: {e}")
        return None
    for d in deals:
        if d.get('buyer_id') == user_id and d.get('status') in ('waiting_payment', 'paid'):
            return d
    return None

async def _show_payment_instructions(query, user_language, method):
    """Показываем инструкции оплаты для TON/USDT/Stars"""
    deal = _find_current_waiting_payment_deal_for_buyer(query.from_user.id)
    if not deal:
        await query.answer("❌ Текущая сделка не найдена", show_alert=True)
        return

    # Достаём поля, если есть
    amount_fiat = deal.get('amount', '—')
    fiat_currency = deal.get('fiat_currency', '—')
    ton_amount = deal.get('ton_amount', '—')
    usdt_amount = deal.get('usdt_amount', '—')
    stars_amount = deal.get('stars_amount', '—')
    payment_address = deal.get('payment_address', '—')

    if method == 'ton':
        body = (
            f"💎 Оплата TON\n\n"
            f"К оплате: {ton_amount} TON\n"
            f"Сумма сделки: {amount_fiat} {fiat_currency}\n"
            f"Адрес для перевода: `{payment_address}`\n\n"
            f"После оплаты нажмите — *Повторить попытку*."
        )
    elif method == 'usdt':
        body = (
            f"💵 Оплата USDT\n\n"
            f"К оплате: {usdt_amount} USDT\n"
            f"Сумма сделки: {amount_fiat} {fiat_currency}\n"
            f"Адрес/биржа: `{payment_address}`\n\n"
            f"После оплаты нажмите — *Повторить попытку*."
        )
    else:  # stars
        body = (
            f"⭐ Оплата Telegram Stars\n\n"
            f"К оплате: {stars_amount} Stars\n"
            f"Сумма сделки: {amount_fiat} {fiat_currency}\n\n"
            f"После оплаты нажмите — *Повторить попытку*."
        )

    try:
        await query.edit_message_caption(
            caption=body,
            reply_markup=get_payment_retry_keyboard(user_language),
            parse_mode='Markdown'
        )
    except Exception:
        await send_photo_message(
            query, 'images/najalo.jpg', body,
            reply_markup=get_payment_retry_keyboard(user_language),
            parse_mode='Markdown'
        )

# =====================
# Callback handler
# =====================
async def handle_callback_query(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    user = query.from_user
    callback_data = query.data
    user_language = db.get_user_language(user.id)
    state_data = user_states.get_state(user.id)

    logger.info(f"[CALLBACK] {user.id} -> {callback_data}")

    try:
        # MAIN
        if callback_data == 'create_deal':
            await send_photo_message(update, 'images/create_deal.jpg', MESSAGES[user_language]['choose_deal_type'],
                                     reply_markup=get_deal_type_keyboard(user_language))
            return

        if callback_data == 'profile':
            successful_deals_count = db.get_seller_stats(user.id)
            profile_text = f"👤 **Профиль**\n\n📊 Успешных сделок: {successful_deals_count}"
            profile_keyboard = InlineKeyboardMarkup([
                [InlineKeyboardButton("📋 Мои сделки", callback_data="my_deals")],
                [InlineKeyboardButton("⬅️ Назад", callback_data="back_main")]
            ])
            await send_photo_message(update, 'images/profile.jpg', profile_text, reply_markup=profile_keyboard, parse_mode='Markdown')
            return

        if callback_data == 'requisites':
            await show_requisites_main_menu(update, user_language)
            return

        if callback_data == 'support':
            support_keyboard = InlineKeyboardMarkup([
                [InlineKeyboardButton("💬 Написать в поддержку", url="https://t.me/tresure_support")]
            ])
            await query.message.reply_text("🆘 Нажмите кнопку ниже, чтобы написать в поддержку:", reply_markup=support_keyboard)
            return

        if callback_data == 'change_language':
            language_keyboard = InlineKeyboardMarkup([
                [InlineKeyboardButton("🇷🇺 Русский", callback_data="lang_ru")],
                [InlineKeyboardButton("🇺🇸 English", callback_data="lang_en")],
                [InlineKeyboardButton("⬅️ Назад", callback_data="back_main")]
            ])
            await send_photo_message(update, 'images/language.jpg', "🌐 Выберите язык / Choose language:",
                                     reply_markup=language_keyboard)
            return

        # Информация о конкретной сделке
        if callback_data.startswith('deal_info_'):
            deal_id = callback_data.split('_', 2)[2]
            deal_info = db.get_deal(deal_id)
            if not deal_info:
                await query.answer("❌ Сделка не найдена", show_alert=True)
                return

            gift_links = deal_info.get('gift_links', [])
            if isinstance(gift_links, list):
                deal_description = "\n".join(gift_links)
            else:
                deal_description = str(gift_links)

            if deal_info['seller_id'] == user.id:
                role_text = "👤 Вы продавец в сделке."
                buyer_info = db.get_user(deal_info['buyer_id'])
                if buyer_info:
                    buyer_username = f"@{buyer_info[1]}" if buyer_info[1] else str(buyer_info[0])
                    buyer_successful_deals = db.get_seller_stats(deal_info['buyer_id'])
                    counterpart_info = f"📌 Покупатель: {buyer_username}\n╰ Успешные сделки: {buyer_successful_deals}"
                else:
                    counterpart_info = f"📌 Покупатель: {deal_info['buyer_id']}\n╰ Успешные сделки: 0"
            else:
                role_text = "👥 Вы покупатель в сделке."
                seller_info = db.get_user(deal_info['seller_id'])
                if seller_info:
                    seller_username = f"@{seller_info[1]}" if seller_info[1] else seller_info[2]
                    seller_successful_deals = db.get_seller_stats(deal_info['seller_id'])
                    counterpart_info = f"📌 Продавец: {seller_username}\n╰ Успешные сделки: {seller_successful_deals}"
                else:
                    counterpart_info = f"📌 Продавец: {deal_info['seller_id']}\n╰ Успешные сделки: 0"

            deal_info_text = (
                f"📋 Информация о сделке #{deal_id}\n\n"
                f"{role_text}\n{counterpart_info}\n\n"
                f"💰 Сумма сделки: {deal_info['amount']} {deal_info['fiat_currency']} "
                f"({deal_info['total_amount']} {deal_info['fiat_currency']})\n"
                f"📜 Вы {'продаете' if deal_info['seller_id'] == user.id else 'покупаете'}:\n{deal_description}"
            )

            info_keyboard = InlineKeyboardMarkup([[InlineKeyboardButton("⬅️ Назад", callback_data="my_deals")]])
            await send_photo_message(update, 'images/profile.jpg', deal_info_text, reply_markup=info_keyboard)
            return

        if callback_data.startswith('lang_'):
            new_lang = callback_data.split('_', 1)[1]
            db.update_user_language(user.id, new_lang)
            await send_photo_message(update, 'images/language.jpg', MESSAGES[new_lang]['welcome'], reply_markup=get_welcome_inline_keyboard(new_lang))
            return

        # Deal creation flow
        if callback_data.startswith('deal_'):
            deal_type = callback_data.split('_', 1)[1]
            user_states.set_state(user.id, 'waiting_gift_links', {'deal_type': deal_type})
    
        # Сообщения для разных типов сделок
        deal_messages = {
            'gift': 'enter_gift_links',
            'channel': 'enter_channel_links', 
            'username': 'enter_username_links',
            'premium': 'enter_premium_links'
        }
    
        message_key = deal_messages.get(deal_type, 'enter_gift_links')
        message_text = MESSAGES[user_language][message_key]
    
        await send_photo_message(update, 'images/create_deal.jpg', message_text, reply_markup=None)
        return




        if callback_data.startswith('currency_'):
            currency = callback_data.split('_', 1)[1]  # card / ton / usdt / stars ...
            data = state_data.get('data', {})
            data['currency'] = currency
            if currency == 'card':
                await send_photo_message(update, 'images/create_deal.jpg', MESSAGES[user_language]['choose_fiat'], reply_markup=get_fiat_currency_keyboard(user_language))
                user_states.set_state(user.id, 'waiting_fiat', data)
            else:
                await send_photo_message(update, 'images/create_deal.jpg', MESSAGES[user_language]['enter_amount'].format(currency=currency.upper()), reply_markup=None)
                user_states.set_state(user.id, 'waiting_amount', data)
            return

        if callback_data.startswith('fiat_'):
            fiat = callback_data.split('_', 1)[1]
            data = state_data.get('data', {})
            data['fiat_currency'] = fiat
            await send_photo_message(update, 'images/create_deal.jpg', MESSAGES[user_language]['enter_amount'].format(currency=fiat), reply_markup=None)
            user_states.set_state(user.id, 'waiting_amount', data)
            return

        if callback_data == 'warning_read':
            deal_info_data = state_data.get('data', {})
            
            # ВАЖНОЕ ИСПРАВЛЕНИЕ: Убедимся, что все необходимые поля есть
            if 'amount' not in deal_info_data:
                await query.answer("❌ Ошибка: сумма сделки не определена", show_alert=True)
                return
                
            if 'currency' not in deal_info_data and 'fiat_currency' not in deal_info_data:
                await query.answer("❌ Ошибка: валюта не определена", show_alert=True)
                return

            # Определяем валюту
            currency = deal_info_data.get('fiat_currency') or deal_info_data.get('currency', 'RUB')
            
            # Рассчитываем итоговую сумму с комиссией
            amount = deal_info_data['amount']
            total_amount = round(amount * (1 + FEE_PERCENT / 100), 2)
            
            # Подготавливаем данные для создания сделки
            deal_data = {
                'seller_id': user.id,
                'deal_type': deal_info_data.get('deal_type', 'gift'),
                'gift_links': deal_info_data.get('gift_links', []),
                'currency': currency,
                'fiat_currency': currency,
                'amount': amount,
                'total_amount': total_amount,
                'fee_percent': FEE_PERCENT,
                'ton_rate': TON_RATE,
                'usdt_rate': USDT_RATE
            }

            # Создание сделки
            try:
                deal_id, buyer_link = db.create_deal(deal_data)
                
                if not deal_id:
                    await query.answer("❌ Ошибка при создании сделки", show_alert=True)
                    return
                    
            except Exception as e:
                logger.error(f"Error creating deal: {e}")
                await query.answer("❌ Ошибка при создании сделки", show_alert=True)
                return

            # Исправленная ссылка для шаринга
            share_url = f"https://t.me/share/url?url=https://t.me/TreasureSaveBot?start=deal_{deal_id}"

            share_keyboard = InlineKeyboardMarkup([
                [InlineKeyboardButton("📤 Поделиться сделкой", url=share_url)],
                [InlineKeyboardButton("❌ Выйти из сделки", callback_data="exit_deal")],
                [InlineKeyboardButton("📋 Мои сделки", callback_data="my_deals")]
            ]) 

            gift_links = deal_info_data.get('gift_links', [])
            desc = "\n".join(gift_links) if isinstance(gift_links, list) else str(gift_links)

            deal_created_text = (
                f"🛡 Сделка #{deal_id}\n\n"
                f"💰 Сумма сделки: {amount} {currency} "
                f"({total_amount} {currency})\n"
                f"📜 Описание:\n{desc}\n"
                f"🔗 Ссылка для пересылки: {share_url}"
            )

            await send_photo_message(update, 'images/create_deal.jpg', deal_created_text, reply_markup=share_keyboard)
            user_states.clear_state(user.id)
            return

        # Requisites navigation/actions
        if callback_data == 'add_requisites':
            await show_requisites_add_menu(query, user_language)
            return

        if callback_data == 'view_requisites':
            await show_requisites_view_menu(query, user_language)
            return

        if callback_data == 'add_ton_wallet':
            user_states.set_state(user.id, 'waiting_ton_wallet')
            try:
                await query.edit_message_caption(
                    caption=("💎 **Добавление TON кошелька**\n\nВведите TON кошелек:\n\n"
                             "Пример: UQC6xSiO2wZ3GTGFnrdxoLY5iNqzwzZftbduHxznEHe6wC5M"),
                    reply_markup=get_back_to_requisites_keyboard(user_language),
                    parse_mode='Markdown'
                )
            except Exception:
                await send_photo_message(
                    query, REQUISITES_IMAGE,
                    "💎 **Добавление TON кошелька**\n\nВведите TON кошелек:\n\nПример: UQC6xSiO2wZ3GTGFnrdxoLY5iNqzwzZftbduHxznEHe6wC5M",
                    get_back_to_requisites_keyboard(user_language), 'Markdown'
                )
            return

        if callback_data == 'add_bank_card':
            try:
                await query.edit_message_caption(
                    caption="💳 **Добавление банковской карты**\n\nВыберите валюту карты:",
                    reply_markup=get_card_currency_keyboard(user_language),
                    parse_mode='Markdown'
                )
            except Exception:
                await send_photo_message(query, REQUISITES_IMAGE, "💳 **Добавление банковской карты**\n\nВыберите валюту карты:",
                                         get_card_currency_keyboard(user_language), 'Markdown')
            return

        if callback_data.startswith('card_currency_'):
            currency = callback_data.split('_', 2)[2]
            user_states.set_state(user.id, 'waiting_card_number', {'currency': currency})
            try:
                await query.edit_message_caption(
                    caption=(f"💳 **Добавление банковской карты**\n\nВалюта: {currency}\n\n"
                             "Введите номер карты (16 цифр):\n\nПример: 1000100010001000"),
                    reply_markup=get_back_to_requisites_keyboard(user_language),
                    parse_mode='Markdown'
                )
            except Exception:
                await send_photo_message(
                    query, REQUISITES_IMAGE,
                    f"💳 **Добавление банковской карты**\n\nВалюта: {currency}\n\nВведите номер карты (16 цифр):\n\nПример: 1000100010001000",
                    get_back_to_requisites_keyboard(user_language), 'Markdown'
                )
            return

        if callback_data == 'view_ton_wallet':
            await show_ton_wallet_info(query, user.id, user_language)
            return

        if callback_data == 'view_bank_cards':
            await show_bank_cards_list(query, user.id, user_language)
            return

        if callback_data.startswith('select_card_'):
            card_id = int(callback_data.split('_', 2)[2])
            await show_selected_card(query, card_id, user_language)
            return

        if callback_data.startswith('edit_card_'):
            card_id = int(callback_data.split('_', 2)[2])
            user_states.set_state(user.id, 'waiting_card_edit_number', {'card_id': card_id})
            try:
                await query.edit_message_caption(caption="✏️ Введите новый номер карты (16 цифр):",
                                                reply_markup=get_back_to_requisites_keyboard(user_language), parse_mode='Markdown')
            except Exception:
                await send_photo_message(query, REQUISITES_IMAGE, "✏️ Введите новый номер карты (16 цифр):",
                                         get_back_to_requisites_keyboard(user_language), 'Markdown')
            return

        # ИСПРАВЛЕННАЯ СТРОКА - добавлена закрывающая скобка
        if callback_data.startswith('delete_card_'):
            card_id = int(callback_data.split('_', 2)[2])
            deleted = db_delete_bank_card(card_id)
            if deleted:
                text = f"💳 Реквизит успешно удалён\nРеквизит: {deleted}"
                keyboard = InlineKeyboardMarkup([[InlineKeyboardButton("⬅️ Назад", callback_data="back_requisites")]])
                try:
                    await query.edit_message_caption(caption=text, reply_markup=keyboard, parse_mode='Markdown')
                except Exception:
                    try:
                        await query.edit_message_text(text=text, reply_markup=keyboard, parse_mode='Markdown')
                    except Exception:
                        await query.message.reply_text(text, reply_markup=keyboard)
            else:
                await query.answer("❌ Не удалось удалить реквизит", show_alert=True)
            return

        # ====== Обработчики выбора способа оплаты (TON / USDT / Stars) ======
        if callback_data == 'pay_ton':
            await _show_payment_instructions(query, user_language, method='ton')
            return

        if callback_data == 'pay_usdt':
            await _show_payment_instructions(query, user_language, method='usdt')
            return

        if callback_data == 'pay_stars':
            await _show_payment_instructions(query, user_language, method='stars')
            return

        if callback_data == 'retry_payment':
            # Вернуть кнопки способов оплаты для покупателя по текущей сделке
            try:
                await query.edit_message_caption(
                    caption=MESSAGES[user_language].get('choose_payment_method', "Выберите способ оплаты:"),
                    reply_markup=get_buyer_payment_keyboard(user_language),
                    parse_mode='Markdown'
                )
            except Exception:
                await send_photo_message(
                    query, 'images/najalo.jpg',
                    MESSAGES[user_language].get('choose_payment_method', "Выберите способ оплаты:"),
                    reply_markup=get_buyer_payment_keyboard(user_language),
                    parse_mode='Markdown'
                )
            return

        # ====== ПОДТВЕРЖДЕНИЕ ОПЛАТЫ (только для админов) ======
        if callback_data == 'confirm_payment':
            # ДОБАВЛЕНА ДЕТАЛЬНАЯ ПРОВЕРКА АДМИНСКИХ ПРАВ
            user_id = user.id
            is_admin = db.is_admin(user_id)
            logger.info(f"User {user_id} admin check: {is_admin}")
            
            # Дополнительная проверка через прямое обращение к БД
            conn = db.get_connection()
            cur = conn.cursor()
            cur.execute('SELECT * FROM admins WHERE user_id = ?', (user_id,))
            admin_row = cur.fetchone()
            conn.close()
            logger.info(f"Direct DB admin check for {user_id}: {admin_row}")
            
            if is_admin or admin_row:
                # Ищем сделки, ожидающие оплаты
                waiting_deals = db.get_all_waiting_payment_deals()
                logger.info(f"Found waiting deals: {len(waiting_deals)}")
                
                if waiting_deals:
                    deal = waiting_deals[0]
                    logger.info(f"Processing deal: {deal['deal_id']}")
                    
                    # Обновляем статус сделки
                    db.update_deal_status(deal['deal_id'], 'paid')
                    
                    try:
                        await query.edit_message_caption(caption="✅ Оплата подтверждена! Ожидайте отправки подарка продавцом.")
                    except Exception:
                        try:
                            await query.edit_message_text(text="✅ Оплата подтверждена! Ожидайте отправки подарка продавцом.")
                        except:
                            pass
                    
                    # Уведомляем продавца
                    try:
                        seller_language = db.get_user_language(deal['seller_id'])
                        await context.bot.send_message(
                            chat_id=deal['seller_id'],
                            text=MESSAGES[seller_language]['seller_payment_notification'].format(deal_id=deal['deal_id']),
                            reply_markup=get_seller_gift_sent_keyboard(seller_language)
                        )
                        logger.info(f"Notified seller {deal['seller_id']} about payment")
                    except Exception as e:
                        logger.error(f"Notify seller error after admin confirm: {e}")
                else:
                    await query.answer("❌ Нет сделок для подтверждения", show_alert=True)
            else:
                # Для обычных пользователей показываем сообщение об ожидании
                await query.answer("⏳ Оплата не найдена. Убедитесь, что вы подтвердили перевод в кошелёк и повторите попытку через 10 секунд", show_alert=True)
            return

        # Navigation
        if callback_data == 'back_main':
            await send_photo_message(update, 'images/najalo.jpg', MESSAGES[user_language]['welcome'], reply_markup=get_welcome_inline_keyboard(user_language))
            return

        if callback_data == 'back_requisites':
            await show_requisites_main_menu(query, user_language)
            return

        if callback_data == 'back_requisites_add':
            await show_requisites_add_menu(query, user_language)
            return

        if callback_data == 'back_requisites_view':
            await show_requisites_view_menu(query, user_language)
            return

        if callback_data == 'back_deal_type':
            await send_photo_message(update, 'images/create_deal.jpg', MESSAGES[user_language]['choose_deal_type'], reply_markup=get_deal_type_keyboard(user_language))
            return

        if callback_data == 'back_currency':
            await send_photo_message(update, 'images/create_deal.jpg', MESSAGES[user_language]['choose_currency'], reply_markup=get_currency_keyboard(user_language))
            return

        if callback_data == 'back_fiat':
            await send_photo_message(update, 'images/create_deal.jpg', MESSAGES[user_language]['choose_fiat'], reply_markup=get_fiat_currency_keyboard(user_language))
            return

        # Мои сделки - список сделок
        if callback_data == 'my_deals':
            user_deals_list = db.get_user_deals(user.id)
            if not user_deals_list:
                deals_text = "🛡 Мои сделки\n\n📋 У вас пока нет сделок"
                deals_keyboard = InlineKeyboardMarkup([[InlineKeyboardButton("⬅️ Назад в профиль", callback_data="profile")]])
                await send_photo_message(update, 'images/profile.jpg', deals_text, reply_markup=deals_keyboard)
                return

            deals_text = "🛡 Мои сделки\n\nВыберите сделку для управления:"
            keyboard = []
            for deal in user_deals_list[:10]:
                deal_button_text = f"💰 {deal['amount']} {deal['fiat_currency']} | #{deal['deal_id']}"
                keyboard.append([InlineKeyboardButton(deal_button_text, callback_data=f"deal_info_{deal['deal_id']}")])
            keyboard.append([InlineKeyboardButton("⬅️ Назад в профиль", callback_data="profile")])
            deals_keyboard = InlineKeyboardMarkup(keyboard)
            await send_photo_message(update, 'images/profile.jpg', deals_text, reply_markup=deals_keyboard)
            return

        if callback_data == 'gift_sent':
            user_deals_list = db.get_user_deals(user.id)
            current_deal_info = next((d for d in user_deals_list if d.get('status') == 'paid' and d.get('seller_id') == user.id), None)
            if current_deal_info:
                db.update_deal_status(current_deal_info['deal_id'], 'gift_sent')
                try:
                    await query.edit_message_caption(caption=MESSAGES[user_language]['waiting_admin_confirmation'])
                except Exception:
                    try:
                        await query.edit_message_text(text=MESSAGES[user_language]['waiting_admin_confirmation'])
                    except:
                        pass
                try:
                    await context.bot.send_message(chat_id=current_deal_info['buyer_id'], text=MESSAGES[user_language]['waiting_admin_confirmation'])
                except Exception as e:
                    logger.error(f"Notify buyer after gift_sent error: {e}")
            else:
                await query.answer("У вас нет сделок, ожидающих отправки подарка")
            return

        if callback_data == 'exit_deal':
            user_states.clear_state(user.id)
            await send_photo_message(update, 'images/create_deal.jpg', MESSAGES[user_language]['welcome'], reply_markup=get_welcome_inline_keyboard(user_language))
            return

        if callback_data == 'contact_support':
            support_keyboard = InlineKeyboardMarkup([
                [InlineKeyboardButton("💬 Написать в поддержку", url="https://t.me/tresure_support_bot")]
            ])
            await query.message.reply_text("🆘 Нажмите кнопку ниже, чтобы написать в поддержку:", reply_markup=support_keyboard)
            return

        if callback_data == 'cancel_deal':
            user_states.clear_state(user.id)
            await send_photo_message(update, 'images/create_deal.jpg', MESSAGES[user_language]['welcome'], reply_markup=get_welcome_inline_keyboard(user_language))
            return

    except Exception as e:
        logger.error(f"Callback handler error: {e}")
        try:
            await query.edit_message_caption(caption="❌ Произошла ошибка. Пожалуйста, попробуйте еще раз.")
        except Exception:
            try:
                await query.edit_message_text(text="❌ Произошла ошибка. Пожалуйста, попробуйте еще раз.")
            except Exception:
                try:
                    await query.message.reply_text("❌ Произошла ошибка. Пожалуйста, попробуйте еще раз.")
                except:
                    pass

# =====================
# Global error handler
# =====================
async def error_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    logger.error(f"Exception while handling an update: {context.error}")
    try:
        if update and update.effective_user:
            user_language = db.get_user_language(update.effective_user.id)
            error_message = "❌ Произошла ошибка. Пожалуйста, попробуйте еще раз."
            if update.callback_query:
                try:
                    await update.callback_query.edit_message_caption(caption=error_message)
                except:
                    await update.callback_query.message.reply_text(error_message)
            elif update.message:
                await update.message.reply_text(error_message)
    except Exception as e:
        logger.error(f"Error in error handler: {e}")

# =====================
# Main / run
# =====================
def main():
    if not BOT_TOKEN or BOT_TOKEN == "YOUR_BOT_TOKEN_HERE":
        print("❌ Укажите токен в config.BOT_TOKEN")
        return

    os.makedirs('images', exist_ok=True)

    try:
        app = Application.builder().token(BOT_TOKEN).build()

        app.add_handler(CommandHandler("sculpture", sculpture_command))

        app.add_error_handler(error_handler)
        app.add_handler(CommandHandler("start", start_command))
        app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
        app.add_handler(CallbackQueryHandler(handle_callback_query))
        app.add_handler(InlineQueryHandler(inline_query_handler))

        print("✅ Бот запускается...")
        print("🔄 Бот работает. Для остановки нажмите Ctrl+C")

        app.run_polling(
            allowed_updates=Update.ALL_TYPES,
            drop_pending_updates=True,
            close_loop=False
        )

    except Exception as e:
        print(f"❌ Ошибка при запуске бота: {e}")
        logger.error(f"Bot startup error: {e}")
    except KeyboardInterrupt:
        print("⏹️ Бот остановлен пользователем")
    finally:
        print("👋 Бот завершил работу")

if __name__ == "__main__":
    main()
