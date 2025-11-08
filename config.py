import os
from dotenv import load_dotenv

load_dotenv()

# Проверяем существует ли .env файл
if not os.path.exists('.env'):
    print("❌ Файл .env не найден!")
    print("📝 Создайте файл .env с содержимым:")
    print("BOT_TOKEN=ваш_токен_от_botfather")
    exit(1)

BOT_TOKEN = os.getenv('BOT_TOKEN')

if not BOT_TOKEN:
    print("❌ Ошибка: BOT_TOKEN не найден!")
    print("📝 Проверьте что в файле .env есть строка:")
    print("BOT_TOKEN=ваш_токен_от_botfather")
    exit(1)

print("✅ Токен найден, бот запускается...")

ADMIN_IDS = [123456789]
DB_NAME = "guarantee_bot.db"
DEAL_PREFIX = "deal_"

# Настройки оплаты
TON_RATE = 0.053  # Курс TON к RUB
USDT_RATE = 24.3  # Курс USDT к RUB
FEE_PERCENT = 3   # Комиссия 3%
