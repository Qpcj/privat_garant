# Создайте файл update_db.py
import sqlite3

def update_database():
    conn = sqlite3.connect("guarantee_bot.db")
    cursor = conn.cursor()
    
    # Добавляем недостающие колонки
    try:
        cursor.execute('ALTER TABLE deals ADD COLUMN total_amount REAL')
        print("✅ Добавлена колонка total_amount")
    except:
        print("⚠️ Колонка total_amount уже существует")
    
    try:
        cursor.execute('ALTER TABLE deals ADD COLUMN payment_address TEXT')
        print("✅ Добавлена колонка payment_address")
    except:
        print("⚠️ Колонка payment_address уже существует")
    
    try:
        cursor.execute('ALTER TABLE deals ADD COLUMN ton_amount REAL')
        print("✅ Добавлена колонка ton_amount")
    except:
        print("⚠️ Колонка ton_amount уже существует")
    
    try:
        cursor.execute('ALTER TABLE deals ADD COLUMN usdt_amount REAL')
        print("✅ Добавлена колонка usdt_amount")
    except:
        print("⚠️ Колонка usdt_amount уже существует")
    
    conn.commit()
    conn.close()
    print("✅ База данных обновлена!")

if __name__ == '__main__':
    update_database()
