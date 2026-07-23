import os
import sys
from pymongo import MongoClient
from dotenv import load_dotenv

load_dotenv()

def make_admin(email: str):
    mongo_uri = os.getenv("MONGODB_URI")
    if not mongo_uri:
        print("Lỗi: MONGODB_URI chưa được cấu hình trong file .env!")
        sys.exit(1)

    try:
        client = MongoClient(mongo_uri)
        db = client.get_database("rag_system")
        users_collection = db.users
        
        user = users_collection.find_one({"email": email})
        if not user:
            print(f"Không tìm thấy người dùng nào với email: {email}")
            sys.exit(1)
            
        result = users_collection.update_one(
            {"email": email},
            {"$set": {"role": "admin"}}
        )
        
        if result.modified_count > 0:
            print(f"✅ Thành công! Đã cấp quyền admin cho tài khoản: {email}")
        else:
            print(f"Tài khoản {email} đã là admin từ trước.")
            
    except Exception as e:
        print(f"Lỗi kết nối MongoDB: {e}")

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Hướng dẫn sử dụng: python make_admin.py <email_cua_ban>")
        print("Ví dụ: python make_admin.py admin@example.com")
        sys.exit(1)
        
    email_to_promote = sys.argv[1]
    make_admin(email_to_promote)
