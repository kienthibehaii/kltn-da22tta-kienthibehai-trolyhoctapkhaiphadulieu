# quiz_system.py - Hệ thống Quiz tương tác với đánh giá và giải thích
import os
import json
import re
from dotenv import load_dotenv
from langchain_google_genai import ChatGoogleGenerativeAI
from llm_router import get_llm
from auth.api_routes import auth_manager

load_dotenv()

OPTION_KEYS = ["A", "B", "C", "D"]

def strip_option_label(value):
    if not isinstance(value, str):
        return value
    return re.sub(r"^\s*(?:\*\*)?\s*([A-Da-d])\s*[\.\):：-]\s*(?:\*\*)?\s*", "", value).strip()

def normalize_answer_key(correct_answer, options):
    if correct_answer is None:
        return ""

    answer_text = str(correct_answer).strip()
    if answer_text.upper() in OPTION_KEYS:
        return answer_text.upper()

    key_match = re.match(r"^(?:\*\*)?\s*([A-Da-d])\s*(?:[\.\):：-]|\*\*)", answer_text)
    if key_match:
        return key_match.group(1).upper()

    normalized_answer = strip_option_label(answer_text).strip().lower()
    if isinstance(options, dict):
        for key, value in options.items():
            if str(key).upper() in OPTION_KEYS and strip_option_label(str(value)).strip().lower() == normalized_answer:
                return str(key).upper()

    return answer_text.upper()

def normalize_multiple_choice_question(question):
    normalized = dict(question)
    options = normalized.get("options")

    if isinstance(options, dict):
        normalized_options = {}
        for key in OPTION_KEYS:
            if key in options:
                normalized_options[key] = strip_option_label(options[key])
        for key, value in options.items():
            key_upper = str(key).upper()
            if key_upper in OPTION_KEYS and key_upper not in normalized_options:
                normalized_options[key_upper] = strip_option_label(value)
        normalized["options"] = normalized_options

    normalized["correct_answer"] = normalize_answer_key(normalized.get("correct_answer", ""), options or normalized.get("options", {}))
    normalized["type"] = normalized.get("type") or "multiple_choice"
    normalized["difficulty"] = normalized.get("difficulty") or "medium"
    return normalized

def load_static_quiz(topic, num_questions):
    """
    Đọc câu hỏi từ MongoDB (nếu có) hoặc fallback về data/question_bank.json.
    """
    questions = []
    topic_clean = topic.lower() if topic else "apriori"
    
    if auth_manager.use_mongo:
        try:
            # Query MongoDB bằng biểu thức chính quy (không phân biệt hoa thường)
            cursor = auth_manager.db.questions.find({"topic": {"$regex": f"^{topic_clean}$", "$options": "i"}}, {"_id": 0})
            questions = list(cursor)
        except Exception as e:
            print(f"⚠️ Lỗi query MongoDB questions: {e}")
            
    # Fallback to local JSON nếu không có MongoDB hoặc query bị lỗi/không có dữ liệu
    if not questions:
        bank_path = os.path.join("data", "question_bank.json")
        if os.path.exists(bank_path):
            try:
                with open(bank_path, "r", encoding="utf-8") as f:
                    bank_data = json.load(f)
                all_q = bank_data.get("questions", [])
                questions = [q for q in all_q if q.get("topic", "").lower() == topic_clean]
            except Exception as e:
                print(f"⚠️ Lỗi đọc data/question_bank.json: {e}")
                
    if not questions:
        return None
        
    # Trộn ngẫu nhiên và chọn số lượng câu hỏi
    import random
    random.shuffle(questions)
    selected_q = [normalize_multiple_choice_question(q) for q in questions[:num_questions]]
    
    print(f"✅ Đã tải {len(selected_q)} câu hỏi từ Ngân hàng (MongoDB/JSON) cho chủ đề '{topic}'")
    return {
        "questions": selected_q,
        "sources": []
    }

def generate_interactive_quiz(retriever, topic="", num_questions=5, language="Vietnamese", metadata_filter=None):
    """
    Tạo quiz tương tác với câu hỏi trắc nghiệm dựa trên đề cương và slide bài giảng/giáo trình
    """
    # 0. Ưu tiên đọc từ Ngân hàng câu hỏi tĩnh trước!
    static_quiz = load_static_quiz(topic, num_questions)
    if static_quiz and len(static_quiz["questions"]) >= num_questions:
        print(f"✅ Đủ {num_questions} câu tĩnh, không cần gọi LLM.")
        return static_quiz
    else:
        print(f"⚠️ Ngân hàng tĩnh chỉ có {len(static_quiz['questions']) if static_quiz else 0} câu (yêu cầu {num_questions}). Đang gọi LLM tạo thêm...")

    topic_clean = topic.lower() if topic else "apriori"

    # 1. Xây dựng Pre-filtering theo Giai đoạn 2 của Đề cương đặc tả
    pre_filter = {}
    if topic_clean == "ly_thuyet_25":
        pre_filter = {
            "$and": [
                {"doc_type": "theory"},
                {"lesson": {"$in": ["bai_1", "bai_2", "bai_3"]}}
            ]
        }
    elif topic_clean == "bai_tap_lon_25":
        pre_filter = {
            "$and": [
                {"doc_type": "theory"},
                {"lesson": {"$in": ["bai_2", "bai_3", "bai_4", "bai_5"]}}
            ]
        }
    elif topic_clean == "cuoi_ky_50":
        pre_filter = {
            "$and": [
                {"doc_type": "theory"},
                {"lesson": {"$in": ["bai_1", "bai_2", "bai_3", "bai_4", "bai_5"]}}
            ]
        }
    elif topic_clean == "code_thuc_hanh" or "code" in topic_clean:
        pre_filter = {
            "doc_type": "code"
        }
    elif topic_clean in ["apriori", "fp_growth"]:
        pre_filter = {
            "$and": [
                {"doc_type": "theory"},
                {"lesson": "bai_3"}
            ]
        }
    elif topic_clean in ["kmeans", "dbscan"]:
        pre_filter = {
            "$and": [
                {"doc_type": "theory"},
                {"lesson": "bai_5"}
            ]
        }
    else:
        pre_filter = {
            "doc_type": "theory"
        }

    # Gộp bộ lọc bảo mật người dùng (nếu có) và làm phẳng điều kiện cho ChromaDB
    if metadata_filter:
        conditions = [metadata_filter]
        if "$and" in pre_filter:
            conditions.extend(pre_filter["$and"])
        else:
            conditions.append(pre_filter)
        final_filter = {"$and": conditions}
        
        syllabus_filter = {
            "$and": [
                metadata_filter,
                {"doc_type": "syllabus"}
            ]
        }
    else:
        final_filter = pre_filter
        syllabus_filter = {"doc_type": "syllabus"}

    # 2. Định tuyến câu truy vấn
    if topic_clean == "ly_thuyet_25":
        content_query = "giới thiệu tiền xử lý dữ liệu luật kết hợp lý thuyết"
    elif topic_clean == "bai_tap_lon_25":
        content_query = "tiền xử lý dữ liệu luật kết hợp phân lớp phân cụm thực hành"
    elif topic_clean == "cuoi_ky_50":
        content_query = "lý thuyết khai phá dữ liệu phân lớp phân cụm luật kết hợp"
    elif topic_clean == "code_thuc_hanh" or "code" in topic_clean:
        content_query = "mã nguồn thuật toán python kNN Naive Bayes Decision Tree KMeans Apriori"
    else:
        topic_map = {
            "apriori": ("Apriori", "luật kết hợp association rules Apriori"),
            "fp_growth": ("FP-Growth", "tập phổ biến frequent patterns FP-Growth FP-Tree"),
            "kmeans": ("K-Means", "phân cụm clustering K-Means k-trung bình"),
            "dbscan": ("DBSCAN", "phân cụm mật độ density-based clustering DBSCAN")
        }
        topic_en, topic_vi = topic_map.get(topic_clean, (topic_clean, topic_clean))
        content_query = f"thuật toán lý thuyết {topic_en} {topic_vi}"

    syllabus_query = "đề cương học phần chuẩn đầu ra hình thức đánh giá trắc nghiệm"

    # 3. Thực hiện truy xuất từ cơ sở dữ liệu Vector DB
    try:
        raw_syllabus_docs = retriever.invoke(syllabus_query, filter=syllabus_filter)
    except Exception as e:
        print(f"⚠️ Lỗi truy xuất syllabus: {e}")
        raw_syllabus_docs = []

    try:
        raw_content_docs = retriever.invoke(content_query, filter=final_filter)
    except Exception as e:
        print(f"⚠️ Lỗi truy xuất content: {e}")
        raw_content_docs = []

    # Giới hạn số lượng tài liệu để giữ ngữ cảnh sạch
    syllabus_docs = raw_syllabus_docs[:2]
    content_docs = raw_content_docs[:4]

    # Dự phòng nếu danh sách trống
    if not syllabus_docs and raw_syllabus_docs:
        syllabus_docs = raw_syllabus_docs[:2]
    if not content_docs and raw_content_docs:
        content_docs = raw_content_docs[:4]

    # Định dạng ngữ cảnh trích xuất
    context_parts_syllabus = []
    context_parts_content = []
    sources = []

    for i, doc in enumerate(syllabus_docs, 1):
        filename = doc.metadata.get('source_file', 'Unknown').split('/')[-1]
        context_parts_syllabus.append(f"Syllabus Doc {i} ({filename}):\n{doc.page_content[:800]}")
        sources.append({
            'filename': filename,
            'page': doc.metadata.get('page', 'N/A'),
            'content': doc.page_content[:800]
        })

    for i, doc in enumerate(content_docs, 1):
        filename = doc.metadata.get('source_file', 'Unknown').split('/')[-1]
        context_parts_content.append(f"Content Doc {i} ({filename}):\n{doc.page_content[:1000]}")
        sources.append({
            'filename': filename,
            'page': doc.metadata.get('page', 'N/A'),
            'content': doc.page_content[:800]
        })

    syllabus_str = "\n\n".join(context_parts_syllabus)
    content_str = "\n\n".join(context_parts_content)

    # 4. Thiết lập System Prompt & Bảng thuật ngữ chuẩn hóa (Giai đoạn 3, Prompt 1)
    prompt = f"""Bạn là một Giảng viên môn Khai phá dữ liệu. Dựa VÀO CHÍNH XÁC các tài liệu được truy xuất dưới đây, hãy tạo {num_questions} câu hỏi trắc nghiệm.

[BẢNG THUẬT NGỮ CHUẨN]: 
Classification=Phân lớp; Clustering=Gom cụm; KDD=Khám phá tri thức; DM=Khai thác dữ liệu; Ensemble=Tập hợp mô hình; kNN=k láng giềng gần nhất; Naive Bayes=Bayes thơ ngây; Overfitting=Học vẹt/Quá khớp; Regression=Hồi quy; Support=Độ hỗ trợ; Confidence=Độ tin cậy; Lift=Độ nâng.

[YÊU CẦU NGHIÊM NGẶT]:
1. CHỈ dùng kiến thức trong tài liệu được cung cấp. KHÔNG dùng kiến thức mạng.
2. Nội dung chỉ xoay quanh lý thuyết, tuyệt đối bỏ qua các tham số code Python.
3. Mỗi câu hỏi có 4 đáp án A, B, C, D (chỉ 1 đáp án đúng). Các đáp án nhiễu phải có thật trong tài liệu để gây lú.
4. Đầu ra bắt buộc phải theo định dạng JSON.

[Tài liệu Đề cương học phần (Syllabus)]:
{syllabus_str}

[Tài liệu bài giảng & giáo trình (Course Content)]:
{content_str}

Hãy trả về định dạng JSON chính xác theo Schema sau:
{{
  "exam_questions": [
    {{
      "id": 1,
      "topic": "Chương/Bài tương ứng",
      "question": "Câu hỏi trắc nghiệm tiếng Việt?",
      "options": {{
        "A": "Đáp án A",
        "B": "Đáp án B",
        "C": "Đáp án C",
        "D": "Đáp án D"
      }},
      "correct_answer": "A",
      "explanation": "Giải thích chi tiết lý do đáp án đúng dựa theo tài liệu..."
    }}
  ]
}}

LƯU Ý: Chỉ trả về duy nhất chuỗi JSON hợp lệ, không thêm bất kỳ văn bản giải thích nào khác ngoài JSON."""

    from reliability.api_key_manager import api_key_manager
    keys_pool_size = len(api_key_manager.keys)
    attempts_limit = max(keys_pool_size, 3)
    response_text = None

    for attempt in range(attempts_limit):
        key_info = api_key_manager.get_available_key()
        if not key_info:
            print("⚠️ Không có API key khả dụng để tạo interactive quiz!")
            break

        current_key = key_info.key
        try:
            llm = get_llm(task_type="quiz_generation", require_json=True)
            response = llm.invoke(prompt)
            response_text = response.content if hasattr(response, 'content') else str(response)
            api_key_manager.record_key_success(current_key)
            break
        except Exception as e:
            error_msg = str(e)
            is_quota = any(kw in error_msg for kw in ["RESOURCE_EXHAUSTED", "429", "503", "UNAVAILABLE"])
            api_key_manager.record_key_failure(current_key, is_quota_error=is_quota)
            print(f"⚠️ Lỗi tạo interactive quiz với key {key_info.name} (lượt {attempt+1}/{attempts_limit}): {error_msg[:150]}")

    if not response_text:
        return create_fallback_quiz(content_docs, num_questions, topic)

    try:
        # Loại bỏ markdown code blocks nếu có
        if "```json" in response_text:
            response_text = response_text.split("```json")[1].split("```")[0].strip()
        elif "```" in response_text:
            response_text = response_text.split("```")[1].split("```")[0].strip()

        quiz_data = json.loads(response_text)
        
        # Ánh xạ trường exam_questions thành questions để tương thích ngược với Frontend
        if "exam_questions" in quiz_data:
            quiz_data["questions"] = quiz_data["exam_questions"]
        elif "questions" not in quiz_data:
            quiz_data["questions"] = []
        quiz_data["questions"] = [normalize_multiple_choice_question(q) for q in quiz_data["questions"]]
            
        # Thêm sources vào quiz data
        quiz_data['sources'] = sources
        return quiz_data

    except json.JSONDecodeError as e:
        print(f"⚠️ JSON parsing error: {e}")
        print(f"Response: {response_text[:500]}")
        return create_fallback_quiz(content_docs, num_questions, topic)

def create_fallback_quiz(docs, num_questions=5, topic="apriori"):
    """
    Tạo quiz trắc nghiệm từ offline knowledge base khi Gemini API thất bại
    """
    from rag import OFFLINE_QUIZ_KNOWLEDGE
    
    topic_clean = topic.lower() if topic else "apriori"
    if "apriori" in topic_clean:
        topic_key = "apriori"
    elif "fp" in topic_clean:
        topic_key = "frequent_pattern"
    elif "kmeans" in topic_clean or "k-means" in topic_clean:
        topic_key = "phan_cum"
    elif "dbscan" in topic_clean:
        topic_key = "phan_cum"
    elif "de_cuong" in topic_clean:
        topic_key = "de_cuong"
    else:
        topic_key = "data_mining"
        
    kb = OFFLINE_QUIZ_KNOWLEDGE.get(topic_key, OFFLINE_QUIZ_KNOWLEDGE["data_mining"])
    questions_list = kb["questions"][:num_questions]
    
    formatted_questions = []
    sources = []
    
    for q in questions_list:
        fq = {
            "id": q["id"],
            "type": "multiple_choice",
            "difficulty": "medium",
            "question": q["question"],
            "options": q["options"],
            "correct_answer": q["correct_answer"],
            "explanation": q["explanation"],
            "source_reference": f"Offline: {kb.get('title', 'Khai phá dữ liệu')}"
        }
        formatted_questions.append(fq)
        
    for i, doc in enumerate(docs[:3], 1):
        sources.append({
            'filename': doc.metadata.get('source', 'Unknown').split('/')[-1],
            'page': doc.metadata.get('page', 'N/A'),
            'content': doc.page_content[:800]
        })
        
    return {
        "questions": formatted_questions,
        "sources": sources
    }

def evaluate_answer(question_data, user_answer):
    """
    Đánh giá câu trả lời của người dùng
    """
    question_data = normalize_multiple_choice_question(question_data)
    question_type = question_data.get('type', 'multiple_choice')
    
    if question_type == 'multiple_choice':
        return evaluate_multiple_choice(question_data, user_answer)
    else:
        return evaluate_short_answer(question_data, user_answer)

def evaluate_multiple_choice(question_data, user_answer):
    """
    Đánh giá câu trả lời trắc nghiệm
    """
    question_data = normalize_multiple_choice_question(question_data)
    correct_answer = question_data.get('correct_answer', '')
    is_correct = str(user_answer).strip().upper() == str(correct_answer).strip().upper()
    
    result = {
        'is_correct': is_correct,
        'user_answer': user_answer.upper(),
        'correct_answer': correct_answer,
        'score': 1.0 if is_correct else 0.0,
        'feedback': '',
        'explanation': question_data.get('explanation', ''),
        'source_reference': question_data.get('source_reference', '')
    }
    
    if is_correct:
        result['feedback'] = "✅ Chính xác! Bạn đã chọn đúng đáp án."
    else:
        result['feedback'] = f"❌ Chưa chính xác. Đáp án đúng là {correct_answer}."
    
    return result

def evaluate_short_answer(question_data, user_answer):
    """
    Đánh giá câu trả lời tự luận bằng Gemini API
    """
    prompt = f"""Evaluate the following short answer question response.

Question: {question_data['question']}

Correct Answer: {question_data['correct_answer']}

Key Concepts: {', '.join(question_data.get('keywords', []))}

User's Answer: {user_answer}

Evaluate the user's answer and provide:
1. Score (0.0 to 1.0): How accurate is the answer?
2. Feedback: Brief feedback in Vietnamese
3. Is it correct? (yes/no)

Consider:
- Does the answer contain key concepts?
- Is the meaning correct even if wording differs?
- Is it complete?

Output format (JSON):
{{
  "score": 0.8,
  "is_correct": true,
  "feedback": "Câu trả lời của bạn đúng về cơ bản...",
  "missing_points": ["điểm còn thiếu 1", "điểm còn thiếu 2"]
}}

Return ONLY valid JSON."""

    try:
        from reliability.api_key_manager import api_key_manager
        keys_pool_size = len(api_key_manager.keys)
        attempts_limit = max(keys_pool_size, 3)
        response_text = None
        
        for attempt in range(attempts_limit):
            key_info = api_key_manager.get_available_key()
            if not key_info:
                print("⚠️ Không có API key khả dụng để đánh giá câu trả lời tự luận!")
                break
                
            current_key = key_info.key
            try:
                # Hybrid Router
                llm = get_llm(task_type="quiz_evaluation", require_json=True)
                response = llm.invoke(prompt)
                response_text = response.content if hasattr(response, 'content') else str(response)
                
                # Record success
                api_key_manager.record_key_success(current_key)
                break
            except Exception as e:
                error_msg = str(e)
                is_quota = any(kw in error_msg for kw in ["RESOURCE_EXHAUSTED", "429", "503", "UNAVAILABLE"])
                api_key_manager.record_key_failure(current_key, is_quota_error=is_quota)
                print(f"⚠️ Lỗi đánh giá tự luận với key {key_info.name} (lượt {attempt+1}/{attempts_limit}): {error_msg[:150]}")
                
        if not response_text:
            raise Exception("Không thể gọi API để đánh giá câu trả lời")
            
        # Parse JSON
        if "```json" in response_text:
            response_text = response_text.split("```json")[1].split("```")[0].strip()
        elif "```" in response_text:
            response_text = response_text.split("```")[1].split("```")[0].strip()
        
        eval_result = json.loads(response_text)
        
        # Thêm thông tin bổ sung
        eval_result['user_answer'] = user_answer
        eval_result['correct_answer'] = question_data['correct_answer']
        eval_result['explanation'] = question_data.get('explanation', '')
        eval_result['source_reference'] = question_data.get('source_reference', '')
        
        return eval_result
        
    except Exception as e:
        print(f"⚠️ Error evaluating answer: {e}")
        # Fallback: đánh giá đơn giản bằng keyword matching
        return evaluate_by_keywords(question_data, user_answer)

def evaluate_by_keywords(question_data, user_answer):
    """
    Đánh giá đơn giản bằng cách kiểm tra keywords
    """
    keywords = question_data.get('keywords', [])
    user_answer_lower = user_answer.lower()
    
    if not keywords:
        # Không có keywords, cho điểm trung bình
        return {
            'is_correct': True,
            'score': 0.5,
            'user_answer': user_answer,
            'correct_answer': question_data['correct_answer'],
            'feedback': "⚠️ Không thể đánh giá tự động. Vui lòng tự kiểm tra với đáp án mẫu.",
            'explanation': question_data.get('explanation', ''),
            'source_reference': question_data.get('source_reference', ''),
            'missing_points': []
        }
    
    # Đếm số keywords xuất hiện
    matched_keywords = sum(1 for kw in keywords if kw.lower() in user_answer_lower)
    score = matched_keywords / len(keywords)
    
    is_correct = score >= 0.6  # 60% keywords trở lên là đúng
    
    missing = [kw for kw in keywords if kw.lower() not in user_answer_lower]
    
    if is_correct:
        feedback = f"✅ Câu trả lời đúng! Bạn đã đề cập {matched_keywords}/{len(keywords)} khái niệm chính."
    else:
        feedback = f"⚠️ Câu trả lời chưa đầy đủ. Bạn đã đề cập {matched_keywords}/{len(keywords)} khái niệm chính."
    
    return {
        'is_correct': is_correct,
        'score': score,
        'user_answer': user_answer,
        'correct_answer': question_data['correct_answer'],
        'feedback': feedback,
        'explanation': question_data.get('explanation', ''),
        'source_reference': question_data.get('source_reference', ''),
        'missing_points': missing
    }

def calculate_quiz_score(results, total_questions=None):
    """
    Tính điểm tổng của quiz
    """
    if not results:
        return 0.0
    
    total_score = sum(r['score'] for r in results)
    max_score = total_questions or len(results)
    
    percentage = (total_score / max_score) * 100
    
    return {
        'total_score': total_score,
        'max_score': max_score,
        'percentage': percentage,
        'grade': get_grade(percentage)
    }

def get_grade(percentage):
    """
    Chuyển điểm phần trăm thành xếp loại
    """
    if percentage >= 90:
        return "Xuất sắc 🌟"
    elif percentage >= 80:
        return "Giỏi 🎉"
    elif percentage >= 70:
        return "Khá 👍"
    elif percentage >= 60:
        return "Trung bình 📚"
    else:
        return "Cần cố gắng thêm 💪"
