import sys
from config import *
from backend_api import get_qa_system
from rag import ask_question

qa = get_qa_system()
print("Initialized QA System")
try:
    ans, docs, conf = ask_question(
        chain=qa["qa_chain"],
        retriever=qa["retriever"],
        question="Hãy cho tôi xem đoạn code Python để vẽ biểu đồ Tọa độ Song song (Parallel Coordinates) cho tập dữ liệu Iris. Hàm nào của thư viện pandas được sử dụng để vẽ biểu đồ này?",
        conversation_context=""
    )
    print("ANSWER:")
    print(ans)
except Exception as e:
    print("ERROR:", e)
