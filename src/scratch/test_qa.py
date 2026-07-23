import sys
import requests
import json

# Ensure stdout handles encoding properly
if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(errors='replace')

url = "http://127.0.0.1:8000/api/question"

questions = [
    "Đề cương chi tiết học phần Khai phá dữ liệu lớp AI có những chuẩn đầu ra (CLO) nào?",
    "Trình bày thuật toán phân cụm K-Means và cách chọn tâm cụm tối ưu?"
]

for idx, q in enumerate(questions, 1):
    print(f"\n=============================================================")
    print(f"CÂU HỎI {idx}: {q}")
    print(f"=============================================================\n")
    
    payload = {
        "question": q,
        "use_context": False
    }
    
    try:
        response = requests.post(url, json=payload, timeout=30)
        if response.status_code == 200:
            data = response.json()
            print("--- CÂU TRẢ LỜI CỦA AI ---")
            print(data.get("answer"))
            print("\n--- TRÍCH DẪN & NGUỒN (CITATIONS) ---")
            citations = data.get("citations", [])
            for c in citations:
                print(f"- File: {c.get('filename')}, Page: {c.get('page')}, Slide: {c.get('slide')}, Relevance Score: {c.get('relevance_score')}")
        else:
            print(f"Lỗi API: {response.status_code} - {response.text}")
    except Exception as e:
        print(f"Lỗi kết nối: {e}")
