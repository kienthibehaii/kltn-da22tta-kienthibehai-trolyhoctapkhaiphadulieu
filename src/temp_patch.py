import os
import json

content = open('backend_api.py', encoding='utf-8').read()
if 'def get_library_topics' not in content:
    target = 'app = FastAPI('
    new_code = '''
@app.get("/api/questions/library")
async def get_library_topics():
    try:
        import json
        import os
        bank_path = os.path.join("data", "question_bank.json")
        if not os.path.exists(bank_path):
            return {"status": "success", "topics": []}
        
        with open(bank_path, "r", encoding="utf-8") as f:
            data = json.load(f)
            
        topics_count = {}
        for q in data.get("questions", []):
            topic = q.get("topic", "unknown")
            topics_count[topic] = topics_count.get(topic, 0) + 1
            
        topics_list = [{"topic": k, "questionCount": v} for k, v in topics_count.items()]
        return {"status": "success", "topics": topics_list}
    except Exception as e:
        return {"status": "error", "message": str(e)}

'''
    content = content.replace(target, new_code + target)
    with open('backend_api.py', 'w', encoding='utf-8') as f:
        f.write(content)
    print('Added successfully')
else:
    print('Already exists')
