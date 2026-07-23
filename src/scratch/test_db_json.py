import os
import json
from pymongo import MongoClient
from dotenv import load_dotenv

load_dotenv()

mongo_uri = os.getenv("MONGODB_URI")
result = {"mongo_uri": mongo_uri, "databases": {}}

try:
    client = MongoClient(mongo_uri, serverSelectionTimeoutMS=5000)
    dbs = client.list_database_names()
    result["databases_list"] = dbs
    
    for db_name in ['chatbot_db', 'rag_system']:
        if db_name in dbs:
            db = client[db_name]
            result["databases"][db_name] = {}
            for col_name in db.list_collection_names():
                col = db[col_name]
                count = col.count_documents({})
                result["databases"][db_name][col_name] = {
                    "count": count,
                    "samples": []
                }
                # fetch last 5 items
                for doc in col.find().sort([("_id", -1)]).limit(5):
                    # convert ObjectId to string
                    doc_copy = {}
                    for k, v in doc.items():
                        if k == "_id":
                            doc_copy[k] = str(v)
                        elif hasattr(v, 'isoformat'):
                            doc_copy[k] = v.isoformat()
                        else:
                            doc_copy[k] = v
                    result["databases"][db_name][col_name]["samples"].append(doc_copy)
except Exception as e:
    result["error"] = str(e)

with open("scratch/db_info.json", "w", encoding="utf-8") as f:
    json.dump(result, f, ensure_ascii=False, indent=2)

print("DB check complete. Output written to scratch/db_info.json")
