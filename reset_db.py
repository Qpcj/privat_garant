from database import Database

def reset_database():
    db = Database("guarantee_bot.db")
    db.drop_and_recreate_tables()
    print("✅ База данных сброшена!")

if __name__ == '__main__':
    reset_database()
