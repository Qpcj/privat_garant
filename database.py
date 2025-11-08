import sqlite3
import json
from datetime import datetime
import random
import string

class Database:
    def __init__(self, db_name="guarantee_bot.db"):
        self.db_name = db_name
        self.init_db()

    def get_connection(self):
        connection = sqlite3.connect(self.db_name)
        return connection

    def init_db(self):
        connection = self.get_connection()
        cursor = connection.cursor()
        
        # Пользователи
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS users (
                user_id INTEGER PRIMARY KEY,
                username TEXT,
                first_name TEXT,
                language TEXT DEFAULT 'ru',
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        # Администраторы
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS admins (
                user_id INTEGER PRIMARY KEY,
                username TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        # Реквизиты - TON кошельки
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS requisites (
                user_id INTEGER PRIMARY KEY,
                ton_wallet TEXT DEFAULT 'UQAeQikkaB6Zz0hWF2IVjsMwK8Ldvtv4jYHPJ3KJDpzoWS1M',
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (user_id) REFERENCES users (user_id)
            )
        ''')
        
        # Банковские карты
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS bank_cards (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER,
                card_number TEXT,
                currency TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (user_id) REFERENCES users (user_id)
            )
        ''')
        
        # Сделки
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS deals (
                deal_id TEXT PRIMARY KEY,
                seller_id INTEGER,
                buyer_id INTEGER,
                deal_type TEXT,
                gift_links TEXT,
                currency TEXT,
                fiat_currency TEXT,
                amount REAL,
                total_amount REAL,
                status TEXT DEFAULT 'created',
                buyer_link TEXT,
                payment_address TEXT,
                ton_amount REAL,
                usdt_amount REAL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (seller_id) REFERENCES users (user_id),
                FOREIGN KEY (buyer_id) REFERENCES users (user_id)
            )
        ''')
        
        connection.commit()
        connection.close()
        print("✅ База данных инициализирована")

    def add_user(self, user_id, username, first_name):
        connection = self.get_connection()
        cursor = connection.cursor()
        
        cursor.execute('''
            INSERT OR IGNORE INTO users (user_id, username, first_name) 
            VALUES (?, ?, ?)
        ''', (user_id, username, first_name))
        
        cursor.execute('''
            INSERT OR IGNORE INTO requisites (user_id) 
            VALUES (?)
        ''', (user_id,))
        
        connection.commit()
        connection.close()

    def get_user(self, user_id):
        connection = self.get_connection()
        cursor = connection.cursor()
        cursor.execute('SELECT * FROM users WHERE user_id = ?', (user_id,))
        result = cursor.fetchone()
        connection.close()
        return result

    def get_user_language(self, user_id):
        connection = self.get_connection()
        cursor = connection.cursor()
        cursor.execute('SELECT language FROM users WHERE user_id = ?', (user_id,))
        result = cursor.fetchone()
        connection.close()
        if result:
            return result[0]
        else:
            return 'ru'

    def update_user_language(self, user_id, language):
        connection = self.get_connection()
        cursor = connection.cursor()
        cursor.execute('UPDATE users SET language = ? WHERE user_id = ?', (language, user_id))
        connection.commit()
        connection.close()

    def add_admin(self, user_id, username):
        connection = self.get_connection()
        cursor = connection.cursor()
        try:
            cursor.execute('INSERT OR REPLACE INTO admins (user_id, username) VALUES (?, ?)', (user_id, username))
            connection.commit()
            return True  # ✅ ВОЗВРАЩАЕМ True ПРИ УСПЕХЕ
        except Exception as e:
            print(f"❌ Ошибка добавления админа: {e}")
            return False
        finally:
            connection.close()

    def is_admin(self, user_id):
        connection = self.get_connection()
        cursor = connection.cursor()
        cursor.execute('SELECT * FROM admins WHERE user_id = ?', (user_id,))
        result = cursor.fetchone()
        connection.close()
        return result is not None

    # Методы для TON кошельков
    def get_user_requisites(self, user_id):
        connection = self.get_connection()
        cursor = connection.cursor()
        cursor.execute('SELECT ton_wallet FROM requisites WHERE user_id = ?', (user_id,))
        result = cursor.fetchone()
        connection.close()
        if result:
            return result[0]
        else:
            return 'UQAeQikkaB6Zz0hWF2IVjsMwK8Ldvtv4jYHPJ3KJDpzoWS1M'

    def update_user_requisites(self, user_id, ton_wallet):
        connection = self.get_connection()
        cursor = connection.cursor()
        try:
            cursor.execute('''
                INSERT OR REPLACE INTO requisites (user_id, ton_wallet, updated_at)
                VALUES (?, ?, CURRENT_TIMESTAMP)
            ''', (user_id, ton_wallet))
            connection.commit()
            return True
        except Exception as e:
            print(f"❌ Ошибка обновления реквизитов: {e}")
            return False
        finally:
            connection.close()

    def has_custom_ton_wallet(self, user_id):
        default_wallet = 'UQAeQikkaB6Zz0hWF2IVjsMwK8Ldvtv4jYHPJ3KJDpzoWS1M'
        current_wallet = self.get_user_requisites(user_id)
        return current_wallet != default_wallet

    # Методы для банковских карт
    def add_bank_card(self, user_id, card_number, currency):
        connection = self.get_connection()
        cursor = connection.cursor()
        try:
            cursor.execute('''
                INSERT INTO bank_cards (user_id, card_number, currency)
                VALUES (?, ?, ?)
            ''', (user_id, card_number, currency))
            connection.commit()
            return True
        except Exception as e:
            print(f"❌ Ошибка добавления карты: {e}")
            return False
        finally:
            connection.close()

    def get_user_bank_cards(self, user_id):
        connection = self.get_connection()
        cursor = connection.cursor()
        cursor.execute('SELECT * FROM bank_cards WHERE user_id = ? ORDER BY created_at DESC', (user_id,))
        results = cursor.fetchall()
        connection.close()
        
        cards = []
        for result in results:
            cards.append({
                'id': result[0],
                'user_id': result[1],
                'card_number': result[2],
                'currency': result[3],
                'created_at': result[4]
            })
        return cards

    def has_bank_cards(self, user_id):
        cards = self.get_user_bank_cards(user_id)
        return len(cards) > 0

    def create_deal(self, deal_data):
        connection = self.get_connection()
        cursor = connection.cursor()
        
        try:
            deal_id = self.generate_deal_id()
            buyer_link = f"https://t.me/TreasureSaveBot?start=deal_{deal_id}"
            
            amount = deal_data['amount']
            total_amount = amount * (1 + deal_data.get('fee_percent', 3) / 100)
            
            payment_address = self.get_user_requisites(deal_data['seller_id'])
            ton_amount = round(total_amount * deal_data.get('ton_rate', 0.053), 4)
            usdt_amount = round(total_amount / deal_data.get('usdt_rate', 24.3), 2)
            
            gift_links_json = json.dumps(deal_data['gift_links'])
            
            cursor.execute('''
                INSERT INTO deals 
                (deal_id, seller_id, deal_type, gift_links, currency, fiat_currency, 
                 amount, total_amount, buyer_link, payment_address, ton_amount, usdt_amount)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                deal_id, 
                deal_data['seller_id'],
                deal_data['deal_type'],
                gift_links_json,
                deal_data['currency'],
                deal_data['fiat_currency'],
                amount,
                total_amount,
                buyer_link,
                payment_address,
                ton_amount,
                usdt_amount
            ))
            
            connection.commit()
            return deal_id, buyer_link
        except Exception as e:
            print(f"❌ Ошибка создания сделки: {e}")
            return None, None
        finally:
            connection.close()

    def get_deal(self, deal_id):
        connection = self.get_connection()
        cursor = connection.cursor()
        cursor.execute('SELECT * FROM deals WHERE deal_id = ?', (deal_id,))
        columns = [description[0] for description in cursor.description]
        result = cursor.fetchone()
        connection.close()
        
        if result:
            deal_dict = dict(zip(columns, result))
            if 'gift_links' in deal_dict and deal_dict['gift_links']:
                try:
                    deal_dict['gift_links'] = json.loads(deal_dict['gift_links'])
                except:
                    deal_dict['gift_links'] = [deal_dict['gift_links']]
            return deal_dict
        return None

    def update_deal_buyer(self, deal_id, buyer_id):
        connection = self.get_connection()
        cursor = connection.cursor()
        try:
            cursor.execute('UPDATE deals SET buyer_id = ? WHERE deal_id = ?', (buyer_id, deal_id))
            connection.commit()
            return True
        except Exception as e:
            print(f"❌ Ошибка обновления покупателя: {e}")
            return False
        finally:
            connection.close()

    def update_deal_status(self, deal_id, status):
        connection = self.get_connection()
        cursor = connection.cursor()
        try:
            cursor.execute('UPDATE deals SET status = ? WHERE deal_id = ?', (status, deal_id))
            connection.commit()
            return True
        except Exception as e:
            print(f"❌ Ошибка обновления статуса: {e}")
            return False
        finally:
            connection.close()

    def get_user_deals(self, user_id):
        connection = self.get_connection()
        cursor = connection.cursor()
        cursor.execute('SELECT * FROM deals WHERE seller_id = ? OR buyer_id = ? ORDER BY created_at DESC', (user_id, user_id))
        columns = [description[0] for description in cursor.description]
        results = cursor.fetchall()
        connection.close()
        
        deals = []
        for result in results:
            deal_dict = dict(zip(columns, result))
            if 'gift_links' in deal_dict and deal_dict['gift_links']:
                try:
                    deal_dict['gift_links'] = json.loads(deal_dict['gift_links'])
                except:
                    deal_dict['gift_links'] = [deal_dict['gift_links']]
            deals.append(deal_dict)
        return deals

    def get_all_waiting_payment_deals(self):
        connection = self.get_connection()
        cursor = connection.cursor()
        cursor.execute('SELECT * FROM deals WHERE status = "waiting_payment" ORDER BY created_at ASC')
        columns = [description[0] for description in cursor.description]
        results = cursor.fetchall()
        connection.close()
        
        deals = []
        for result in results:
            deal_dict = dict(zip(columns, result))
            if 'gift_links' in deal_dict and deal_dict['gift_links']:
                try:
                    deal_dict['gift_links'] = json.loads(deal_dict['gift_links'])
                except:
                    deal_dict['gift_links'] = [deal_dict['gift_links']]
            deals.append(deal_dict)
        return deals

    def get_waiting_payment_deals_for_buyer(self, buyer_id):
        """Найти сделки покупателя со статусом waiting_payment"""
        connection = self.get_connection()
        cursor = connection.cursor()
        cursor.execute('''
            SELECT * FROM deals 
            WHERE buyer_id = ? AND status = 'waiting_payment' 
            ORDER BY created_at DESC
        ''', (buyer_id,))
        columns = [description[0] for description in cursor.description]
        results = cursor.fetchall()
        connection.close()
        
        deals = []
        for result in results:
            deal_dict = dict(zip(columns, result))
            if 'gift_links' in deal_dict and deal_dict['gift_links']:
                try:
                    deal_dict['gift_links'] = json.loads(deal_dict['gift_links'])
                except:
                    deal_dict['gift_links'] = [deal_dict['gift_links']]
            deals.append(deal_dict)
        return deals

    def get_seller_stats(self, seller_id):
        connection = self.get_connection()
        cursor = connection.cursor()
        cursor.execute('SELECT COUNT(*) FROM deals WHERE seller_id = ? AND status = "completed"', (seller_id,))
        result = cursor.fetchone()
        connection.close()
        if result:
            return result[0]
        else:
            return 0

    def generate_deal_id(self):
        characters = string.ascii_uppercase + string.digits
        deal_id = ''.join(random.choices(characters, k=8))
        return deal_id

    def debug_deal_status(self, deal_id):
        """Для отладки - посмотреть статус сделки"""
        connection = self.get_connection()
        cursor = connection.cursor()
        cursor.execute('SELECT deal_id, status, buyer_id, seller_id FROM deals WHERE deal_id = ?', (deal_id,))
        result = cursor.fetchone()
        connection.close()
        return result

    def drop_and_recreate_tables(self):
        connection = self.get_connection()
        cursor = connection.cursor()
        
        cursor.execute('DROP TABLE IF EXISTS deals')
        cursor.execute('DROP TABLE IF EXISTS bank_cards')
        cursor.execute('DROP TABLE IF EXISTS requisites')
        cursor.execute('DROP TABLE IF EXISTS admins')
        cursor.execute('DROP TABLE IF EXISTS users')
        
        connection.commit()
        connection.close()
        
        self.init_db()
        print("✅ Таблицы пересозданы")
