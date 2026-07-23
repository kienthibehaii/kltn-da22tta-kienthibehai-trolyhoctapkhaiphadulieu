"""
multi_turn_support.py
─────────────────────
Thêm hỗ trợ multi-turn conversations
Giữ context từ câu hỏi trước để trả lời "nó là gì?" hiểu được context
"""

def build_context_aware_prompt(chat_history, current_question, retrieved_docs):
    """
    Xây dựng prompt aware về context từ hội thoại trước

    Args:
        chat_history: list of {"role": "user"/"assistant", "content": ...}
        current_question: câu hỏi hiện tại
        retrieved_docs: list of Document objects

    Returns:
        str: prompt với context đầy đủ
    """

    # Extract previous Q&A for context
    previous_qa = ""
    if len(chat_history) >= 2:
        # Lấy 2 lượt hội thoại gần nhất
        recent = chat_history[-4:-1] if len(chat_history) >= 4 else chat_history[-2:]
        for msg in recent:
            role = "User" if msg.get("role") == "user" else "Assistant"
            previous_qa += f"{role}: {msg.get('content', '')[:200]}\n"

    # Build context
    context = "TÀI LIỆU THAM KHẢO:\n"
    for i, doc in enumerate(retrieved_docs, 1):
        source = doc.metadata.get('source_name', 'Unknown')
        context += f"\n[{i}] {source}:\n{doc.page_content}\n"

    # Build final prompt
    prompt = f"""Based on the following context and conversation history:

CONVERSATION HISTORY:
{previous_qa if previous_qa else "(This is the first question)"}

CURRENT QUESTION: {current_question}

REFERENCE MATERIALS:
{context}

Please provide a clear answer in Vietnamese, maintaining consistency with any previous answers."""

    return prompt


def format_chat_history_for_llm(chat_history):
    """Format chat history for LLM consumption"""
    formatted = []
    for msg in chat_history:
        formatted.append({
            "role": msg.get("role", "user"),
            "content": msg.get("content", "")
        })
    return formatted
