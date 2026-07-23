import sys
import json
import requests

def test_quiz():
    url = "http://localhost:8000/api/quiz"
    payload = {
        "session_id": "test_session",
        "topic": "dbscan",
        "num_questions": 5
    }
    try:
        res = requests.post(url, json=payload)
        data = res.json()
        
        print("Status Code:", res.status_code)
        if "data" in data and "questions" in data["data"]:
            questions = data["data"]["questions"]
            print(f"Generated {len(questions)} questions.")
            for i, q in enumerate(questions):
                print(f"Q{i+1}: {q.get('question')}")
        else:
            print("Response:", json.dumps(data, indent=2, ensure_ascii=False))
            
    except Exception as e:
        print("Error:", e)

if __name__ == "__main__":
    test_quiz()
