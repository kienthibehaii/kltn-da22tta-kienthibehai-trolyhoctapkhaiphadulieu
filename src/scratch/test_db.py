import os
from pymongo import MongoClient
from dotenv import load_dotenv

load_dotenv()

mongo_uri = os.getenv("MONGODB_URI")
print("MONGODB_URI:", mongo_uri)

try:
    client = MongoClient(mongo_uri, serverSelectionTimeoutMS=5000)
    print("Databases:", client.list_database_names())
    
    # Check chatbot_db
    if 'chatbot_db' in client.list_database_names():
        db = client['chatbot_db']
        print("chatbot_db collections:", db.list_collection_names())
        for col_name in db.list_collection_names():
            col = db[col_name]
            print(f"  Collection '{col_name}' count:", col.count_documents({}))
            print(f"  Sample from '{col_name}':")
            for doc in col.find().limit(2):
                doc_str = str(doc)
                print("    ", doc_str[:200])
                
    # Check rag_system
    if 'rag_system' in client.list_database_names():
        db = client['rag_system']
        print("rag_system collections:", db.list_collection_names())
        for col_name in db.list_collection_names():
            col = db[col_name]
            print(f"  Collection '{col_name}' count:", col.count_documents({}))
            print(f"  Sample from '{col_name}':")
            for doc in col.find().limit(2):
                doc_str = str(doc)
                print("    ", doc_str[:200])
                
except Exception as e:
    print("Error:", e)
