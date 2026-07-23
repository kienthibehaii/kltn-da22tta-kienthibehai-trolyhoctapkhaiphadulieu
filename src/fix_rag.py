import sys

with open('rag.py', 'r', encoding='utf-8') as f:
    content = f.read()

idx = content.find('def generate_structured_summary')
if idx != -1:
    content = content[:idx]

new_content = """def generate_structured_summary(retriever, topic, metadata_filter=None):
    from langchain_google_genai import ChatGoogleGenerativeAI
    from reliability.api_key_manager import api_key_manager
    import time
    
    if hasattr(retriever, 'invoke'):
        docs = retriever.invoke(topic, k=10, filter=metadata_filter)
    else:
        docs = retriever.get_relevant_documents(topic, filter=metadata_filter)[:10]
    
    context = "\\n\\n".join([f"Tài liệu {i+1}:\\n{doc.page_content}" for i, doc in enumerate(docs)])
    prompt = f\"\"\"Dựa trên các đoạn tài liệu sau, tóm tắt có cấu trúc về [{topic}].
Trình bày theo các mục: Định nghĩa cốt lõi, Thuật toán chính, Ví dụ minh họa.
Giữ nguyên ký hiệu toán học. Trả lời bằng tiếng Việt.

Tài liệu: {context}\"\"\"

    attempts_limit = 5
    for attempt in range(attempts_limit):
        current_key = api_key_manager.get_available_key()
        if not current_key:
            return "Lỗi kỹ thuật: Hết quota API.", docs, []
        try:
            llm = ChatGoogleGenerativeAI(model="gemini-2.5-flash", google_api_key=current_key, temperature=0.2, timeout=30)
            response = llm.invoke(prompt)
            answer_text = getattr(response, "content", str(response))
            if hasattr(answer_text, "text"): answer_text = answer_text.text
            api_key_manager.record_key_success(current_key)
            return answer_text, docs, []
        except Exception as e:
            api_key_manager.record_key_failure(current_key, is_quota_error=any(kw in str(e) for kw in ["RESOURCE_EXHAUSTED", "429"]))
            time.sleep(1)
            
    return "Lỗi kỹ thuật: Không thể sinh tóm tắt vào lúc này.", docs, []

def generate_flashcards(retriever, topic, n=5, metadata_filter=None):
    from langchain_google_genai import ChatGoogleGenerativeAI
    from reliability.api_key_manager import api_key_manager
    import time
    import json
    import re
    
    if hasattr(retriever, 'invoke'):
        docs = retriever.invoke(topic, k=5, filter=metadata_filter)
    else:
        docs = retriever.get_relevant_documents(topic, filter=metadata_filter)[:5]
        
    context = "\\n\\n".join([doc.page_content[:400] for doc in docs])
    prompt = f\"\"\"Từ nội dung sau, sinh {n} flashcard dạng JSON:
[
  {{"front": "câu hỏi", "back": "đáp án ngắn gọn", "category": "Định nghĩa / Thuật toán / Công thức"}}
]
Tập trung vào định nghĩa, công thức, và so sánh thuật toán.
Chỉ trả về JSON, không có text khác. (Mảng JSON thuần túy, không dùng code block)

Nội dung: {context}\"\"\"

    attempts_limit = 5
    for attempt in range(attempts_limit):
        current_key = api_key_manager.get_available_key()
        if not current_key:
            return []
        try:
            llm = ChatGoogleGenerativeAI(model="gemini-2.5-flash", google_api_key=current_key, temperature=0.3, timeout=30)
            response = llm.invoke(prompt)
            text = getattr(response, "content", str(response))
            if hasattr(text, "text"): text = text.text
            api_key_manager.record_key_success(current_key)
            
            json_str = text.strip()
            if json_str.startswith("```json"): json_str = json_str[7:]
            if json_str.startswith("```"): json_str = json_str[3:]
            if json_str.endswith("```"): json_str = json_str[:-3]
            match = re.search(r'\\[\\s*\\{.*\\}\\s*\\]', json_str, re.DOTALL)
            if match: json_str = match.group(0)
            return json.loads(json_str)
        except Exception as e:
            api_key_manager.record_key_failure(current_key, is_quota_error=any(kw in str(e) for kw in ["RESOURCE_EXHAUSTED", "429"]))
            time.sleep(1)
            
    return []
"""

with open('rag.py', 'w', encoding='utf-8') as f:
    f.write(content + new_content)
