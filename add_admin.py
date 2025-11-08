from database import Database

db = Database()
user_id = 6819155423  # твой ID
username = "@Crytoi_pro_igrok"  # замени на свой

# Добавляем админа
success = db.add_admin(user_id, username)
if success:
    print(f"✅ Пользователь {user_id} добавлен как админ")
    
    # Проверяем
    is_admin = db.is_admin(user_id)
    print(f"✅ Проверка: is_admin = {is_admin}")
else:
    print("❌ Ошибка добавления админа")
