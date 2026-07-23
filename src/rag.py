import os
# Fix ntdll.dll crash (OpenMP multiple instances bug on Windows)
os.environ['KMP_DUPLICATE_LIB_OK'] = 'True'

from llm_router import get_llm
# rag.py - Pipeline RAG với Gemini (Enhanced with detailed citations)
import re
import time
import unicodedata
from typing import List, Dict, Optional, Any
from dotenv import load_dotenv
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_core.prompts import PromptTemplate
from langchain_core.runnables import RunnablePassthrough
from embed_store import load_vector_store

load_dotenv()

# Biến toàn cục đóng vai trò Circuit Breaker khi API bị hết quota
IS_OFFLINE_MODE = False
ENABLE_WORLD_KNOWLEDGE_FALLBACK = os.getenv("ENABLE_WORLD_KNOWLEDGE_FALLBACK", "false").lower() in {
    "1", "true", "yes", "on"
}
ENABLE_QUERY_TRANSLATION = os.getenv("ENABLE_QUERY_TRANSLATION", "false").lower() in {
    "1", "true", "yes", "on"
}
LOW_CONFIDENCE_THRESHOLD = float(os.getenv("LOW_CONFIDENCE_THRESHOLD", "0.50"))
ANSWERABILITY_FALLBACK_THRESHOLD = float(os.getenv("ANSWERABILITY_FALLBACK_THRESHOLD", "0.60"))
ENABLE_TUTOR_FALLBACK = os.getenv("ENABLE_TUTOR_FALLBACK", "true").lower() in {
    "1", "true", "yes", "on"
}


def call_groq_chat(prompt: str, temperature: float = 0.2, max_tokens: int = 2048) -> Optional[str]:
    """Fallback OpenAI-compatible chat completion using Groq when Gemini quota is exhausted."""
    api_key = os.getenv("GROQ_API_KEY", "").strip()
    if not api_key:
        return None

    model = os.getenv("GROQ_MODEL", "llama-3.3-70b-versatile").strip() or "llama-3.3-70b-versatile"
    payload = {
        "model": model,
        "messages": [
            {
                "role": "system",
                "content": (
                    "Ban la tro ly hoc thuat mon Khai pha du lieu. "
                    "Tra loi bang tieng Viet, uu tien bam sat context trong prompt, "
                    "khong tu tao trich dan neu prompt khong cung cap nguon."
                ),
            },
            {"role": "user", "content": prompt},
        ],
        "temperature": temperature,
        "max_tokens": max_tokens,
    }
    import requests

    try:
        response = requests.post(
            "https://api.groq.com/openai/v1/chat/completions",
            headers={
                "Authorization": f"Bearer {api_key}",
                "Content-Type": "application/json",
                "Accept": "application/json",
                "User-Agent": "MinerAI-RAG/1.0",
            },
            json=payload,
            timeout=90,
        )
        if response.status_code >= 400:
            raise Exception(f"Groq HTTP {response.status_code}: {response.text[:300]}")
        result = response.json()
    except requests.RequestException as e:
        raise Exception(f"Groq request failed: {e}") from e
    content = result.get("choices", [{}])[0].get("message", {}).get("content", "")
    return content.strip() or None

# ============================================================================
# OFFLINE KNOWLEDGE BASE - Dùng khi LLM API bị rate limit
# ============================================================================

OFFLINE_QUIZ_KNOWLEDGE = {
    "apriori": {
        "title": "Thuật toán Apriori",
        "questions": [
            {
                "id": 1,
                "type": "multiple_choice",
                "question": "Thuật toán Apriori sử dụng nguyên lý nào để giảm không gian tìm kiếm?",
                "options": {"A": "Nguyên lý Antimonotone: mọi tập con của tập phổ biến cũng là phổ biến", "B": "Nguyên lý Greedy: luôn chọn mục có support cao nhất", "C": "Nguyên lý Divide and Conquer: chia tập dữ liệu thành các phần nhỏ", "D": "Nguyên lý Randomized: chọn ngẫu nhiên các ứng viên"},
                "correct_answer": "A",
                "explanation": "Nguyên lý Antimonotone (còn gọi là tính chất Apriori): nếu một tập mục không phổ biến, thì mọi siêu tập của nó cũng không phổ biến. Điều này cho phép cắt tỉa không gian tìm kiếm hiệu quả."
            },
            {
                "id": 2,
                "type": "multiple_choice",
                "question": "Trong Apriori, 'support' của một tập mục {A, B} được định nghĩa là gì?",
                "options": {"A": "Xác suất mua A khi đã mua B", "B": "Tỷ lệ giao dịch chứa cả A và B so với tổng số giao dịch", "C": "Số lần A và B xuất hiện cùng nhau", "D": "Mức độ tăng cường khi A và B đi cùng nhau"},
                "correct_answer": "B",
                "explanation": "Support({A,B}) = số giao dịch chứa {A,B} / tổng số giao dịch. Đây là độ đo tần suất xuất hiện của tập mục trong cơ sở dữ liệu."
            },
            {
                "id": 3,
                "type": "multiple_choice",
                "question": "Confidence của luật kết hợp A → B được tính như thế nào?",
                "options": {"A": "support(A) / support(B)", "B": "support(A ∪ B) / support(A)", "C": "support(A ∪ B) / support(B)", "D": "support(A) × support(B)"},
                "correct_answer": "B",
                "explanation": "Confidence(A→B) = support(A∪B) / support(A). Đây là xác suất có điều kiện P(B|A) - xác suất giao dịch chứa B khi đã biết nó chứa A."
            },
            {
                "id": 4,
                "type": "multiple_choice",
                "question": "Bước nào là bước đầu tiên trong thuật toán Apriori?",
                "options": {"A": "Tạo tất cả các luật kết hợp", "B": "Tính toán Lift của các tập mục", "C": "Quét cơ sở dữ liệu để tìm các tập 1-itemset phổ biến (L1)", "D": "Loại bỏ các tập mục không thỏa min_confidence"},
                "correct_answer": "C",
                "explanation": "Apriori bắt đầu bằng cách quét toàn bộ cơ sở dữ liệu một lần để đếm số lần xuất hiện của từng mục đơn lẻ, từ đó tìm ra tập phổ biến 1 phần tử (L1) thỏa ngưỡng min_support."
            },
            {
                "id": 5,
                "type": "multiple_choice",
                "question": "Nhược điểm chính của thuật toán Apriori là gì?",
                "options": {"A": "Không thể xử lý dữ liệu nhị phân", "B": "Cần nhiều lần quét cơ sở dữ liệu và sinh ra nhiều tập ứng viên", "C": "Chỉ hoạt động với dữ liệu số", "D": "Không tìm được các luật có confidence thấp"},
                "correct_answer": "B",
                "explanation": "Apriori có hai nhược điểm chính: (1) Phải quét cơ sở dữ liệu nhiều lần (k lần quét cho k-itemset), (2) Sinh ra số lượng lớn tập ứng viên Ck trước khi lọc. FP-Growth được đề xuất để khắc phục nhược điểm này."
            }
        ]
    },
    "frequent_pattern": {
        "title": "Khai phá tập phổ biến",
        "questions": [
            {
                "id": 1,
                "type": "multiple_choice",
                "question": "Chỉ số Lift trong luật kết hợp cho biết điều gì?",
                "options": {"A": "Tần suất xuất hiện của tập mục", "B": "Độ tin cậy của luật", "C": "Mức độ tương quan giữa vế trái và vế phải (>1 là tương quan dương)", "D": "Số lượng luật được tạo ra"},
                "correct_answer": "C",
                "explanation": "Lift(A→B) = confidence(A→B) / support(B). Lift > 1: A và B tương quan dương (xuất hiện cùng nhau nhiều hơn ngẫu nhiên). Lift = 1: độc lập. Lift < 1: tương quan âm."
            },
            {
                "id": 2,
                "type": "multiple_choice",
                "question": "FP-Growth khác Apriori ở điểm nào quan trọng nhất?",
                "options": {"A": "FP-Growth chỉ tìm luật kết hợp một chiều", "B": "FP-Growth không cần min_support", "C": "FP-Growth nén dữ liệu vào cây FP-Tree, tránh quét DB nhiều lần", "D": "FP-Growth chỉ hoạt động với dữ liệu nhỏ"},
                "correct_answer": "C",
                "explanation": "FP-Growth xây dựng cấu trúc cây FP-Tree từ cơ sở dữ liệu (chỉ 2 lần quét), sau đó khai phá trực tiếp trên cây mà không cần sinh tập ứng viên. Điều này hiệu quả hơn nhiều so với Apriori."
            },
            {
                "id": 3,
                "type": "multiple_choice",
                "question": "Nếu min_support = 50% và có 4 giao dịch, một tập mục cần xuất hiện ít nhất bao nhiêu lần để phổ biến?",
                "options": {"A": "1 lần", "B": "2 lần", "C": "3 lần", "D": "4 lần"},
                "correct_answer": "B",
                "explanation": "min_support = 50% × 4 giao dịch = 2. Vậy một tập mục cần xuất hiện ít nhất 2 lần trong 4 giao dịch để được coi là phổ biến."
            },
            {
                "id": 4,
                "type": "multiple_choice",
                "question": "Bài toán khai phá luật kết hợp gồm mấy bước chính?",
                "options": {"A": "1 bước: Tìm trực tiếp luật kết hợp", "B": "2 bước: Tìm tập phổ biến, rồi sinh luật từ tập phổ biến", "C": "3 bước: Tiền xử lý, khai phá, đánh giá", "D": "4 bước: Tìm 1-itemset, 2-itemset, 3-itemset, tạo luật"},
                "correct_answer": "B",
                "explanation": "Bài toán khai phá luật kết hợp gồm 2 bước: (1) Tìm tất cả các tập phổ biến (frequent itemsets) thỏa min_support. (2) Từ các tập phổ biến, sinh ra các luật kết hợp mạnh thỏa min_confidence."
            },
            {
                "id": 5,
                "type": "multiple_choice",
                "question": "Ứng dụng kinh điển nhất của khai phá luật kết hợp là gì?",
                "options": {"A": "Nhận diện khuôn mặt", "B": "Phân tích rổ hàng thị trường (Market Basket Analysis)", "C": "Dự báo giá cổ phiếu", "D": "Phân loại email spam"},
                "correct_answer": "B",
                "explanation": "Phân tích rổ hàng thị trường (Market Basket Analysis) là ứng dụng kinh điển nhất. Ví dụ: {Bỉm} → {Bia} có confidence cao, gợi ý đặt hai sản phẩm gần nhau trong siêu thị để tăng doanh số."
            }
        ]
    },
    "data_mining": {
        "title": "Khai phá dữ liệu tổng quát",
        "questions": [
            {
                "id": 1,
                "type": "multiple_choice",
                "question": "Khai phá dữ liệu (Data Mining) là gì?",
                "options": {"A": "Quá trình lưu trữ dữ liệu vào database", "B": "Quá trình trích xuất tri thức hữu ích và không hiển nhiên từ lượng dữ liệu lớn", "C": "Quá trình thu thập dữ liệu từ internet", "D": "Quá trình làm sạch dữ liệu bị lỗi"},
                "correct_answer": "B",
                "explanation": "Khai phá dữ liệu (Data Mining) là quá trình tự động khám phá các mẫu, tri thức hữu ích, không hiển nhiên từ lượng dữ liệu lớn. Đây là bước cốt lõi trong quy trình KDD (Knowledge Discovery in Databases)."
            },
            {
                "id": 2,
                "type": "multiple_choice",
                "question": "Trong phân lớp dữ liệu, thuật toán nào sử dụng Information Gain để chọn thuộc tính phân chia?",
                "options": {"A": "K-Means", "B": "Apriori", "C": "ID3/C4.5 (Cây quyết định)", "D": "DBSCAN"},
                "correct_answer": "C",
                "explanation": "Thuật toán ID3 và C4.5 (Cây quyết định) sử dụng Information Gain (hoặc Gain Ratio trong C4.5) để chọn thuộc tính phân chia tốt nhất tại mỗi nút của cây."
            },
            {
                "id": 3,
                "type": "multiple_choice",
                "question": "Phân cụm (Clustering) khác phân lớp (Classification) ở điểm nào?",
                "options": {"A": "Phân cụm chậm hơn", "B": "Phân cụm là học không giám sát (unsupervised), không cần nhãn dữ liệu", "C": "Phân cụm chỉ dùng cho dữ liệu số", "D": "Phân cụm cần tập training lớn hơn"},
                "correct_answer": "B",
                "explanation": "Phân cụm là bài toán học không giám sát (unsupervised learning): không cần nhãn (label) sẵn có. Thuật toán tự động nhóm các điểm dữ liệu tương tự nhau vào cùng một cụm. Phân lớp thì cần dữ liệu đã được gán nhãn."
            },
            {
                "id": 4,
                "type": "multiple_choice",
                "question": "Overfitting trong học máy xảy ra khi nào?",
                "options": {"A": "Mô hình quá đơn giản, không học được từ dữ liệu", "B": "Mô hình học quá tốt trên tập huấn luyện nhưng kém trên dữ liệu mới", "C": "Mô hình có quá ít tham số", "D": "Tập dữ liệu quá lớn"},
                "correct_answer": "B",
                "explanation": "Overfitting xảy ra khi mô hình 'ghi nhớ' dữ liệu huấn luyện quá mức (kể cả nhiễu), dẫn đến độ chính xác cao trên train set nhưng thấp trên test set. Giải pháp: pruning, regularization, cross-validation."
            },
            {
                "id": 5,
                "type": "multiple_choice",
                "question": "Outlier (điểm ngoại lai) trong dữ liệu là gì?",
                "options": {"A": "Dữ liệu bị thiếu (missing values)", "B": "Điểm dữ liệu sai về kiểu dữ liệu", "C": "Điểm dữ liệu có giá trị khác biệt đáng kể so với phần còn lại của tập dữ liệu", "D": "Dữ liệu được lưu trữ ở định dạng sai"},
                "correct_answer": "C",
                "explanation": "Outlier là điểm dữ liệu có giá trị nằm xa (khác biệt đáng kể) so với phần lớn tập dữ liệu. Outlier có thể là lỗi nhập liệu hoặc là sự kiện thực sự bất thường cần điều tra (phát hiện gian lận, bệnh hiếm gặp)."
            }
        ]
    },
    "phan_lop": {
        "title": "Phân lớp và Hồi quy",
        "questions": [
            {
                "id": 1,
                "type": "multiple_choice",
                "question": "Cây quyết định ID3 sử dụng tiêu chí nào để chọn thuộc tính phân chia?",
                "options": {"A": "Gain Ratio", "B": "Gini Index", "C": "Information Gain (Entropy)", "D": "Chi-squared"},
                "correct_answer": "C",
                "explanation": "ID3 sử dụng Information Gain dựa trên Entropy để chọn thuộc tính phân chia tốt nhất. Thuộc tính có Information Gain cao nhất được chọn. C4.5 cải tiến bằng Gain Ratio để tránh thiên vị với thuộc tính có nhiều giá trị."
            },
            {
                "id": 2,
                "type": "multiple_choice",
                "question": "Thuật toán KNN (K-Nearest Neighbors) phân lớp một điểm dữ liệu mới bằng cách nào?",
                "options": {"A": "Dùng hàm sigmoid để tính xác suất", "B": "Xây dựng cây quyết định từ tập huấn luyện", "C": "Bầu chọn theo nhãn phổ biến nhất trong K láng giềng gần nhất", "D": "Tìm siêu phẳng tối ưu phân chia các lớp"},
                "correct_answer": "C",
                "explanation": "KNN không xây dựng mô hình (lazy learning). Khi phân lớp điểm mới, thuật toán tìm K điểm gần nhất trong tập huấn luyện (theo khoảng cách Euclidean hoặc Manhattan), sau đó bầu chọn nhãn phổ biến nhất trong K láng giềng đó."
            },
            {
                "id": 3,
                "type": "multiple_choice",
                "question": "Support Vector Machine (SVM) tìm kiếm điều gì trong quá trình huấn luyện?",
                "options": {"A": "Cây quyết định tối ưu", "B": "Siêu phẳng (hyperplane) tối ưu với margin lớn nhất giữa các lớp", "C": "K láng giềng gần nhất", "D": "Phân phối xác suất của từng lớp"},
                "correct_answer": "B",
                "explanation": "SVM tìm siêu phẳng (hyperplane) phân chia các lớp sao cho khoảng cách (margin) từ siêu phẳng đến các điểm gần nhất (support vectors) của mỗi lớp là lớn nhất. Margin lớn giúp mô hình có khả năng tổng quát hóa tốt hơn."
            },
            {
                "id": 4,
                "type": "multiple_choice",
                "question": "Naive Bayes giả định điều gì về các thuộc tính?",
                "options": {"A": "Các thuộc tính phụ thuộc tuyến tính vào nhau", "B": "Các thuộc tính độc lập có điều kiện với nhau khi biết nhãn lớp", "C": "Tất cả thuộc tính đều có phân phối chuẩn", "D": "Chỉ các thuộc tính số mới được sử dụng"},
                "correct_answer": "B",
                "explanation": "Naive Bayes giả định tính độc lập có điều kiện (conditional independence): các thuộc tính độc lập với nhau khi biết nhãn lớp. Mặc dù giả định này thường không đúng trong thực tế, Naive Bayes vẫn hoạt động tốt trong nhiều bài toán thực tế."
            },
            {
                "id": 5,
                "type": "multiple_choice",
                "question": "Random Forest khác Decision Tree đơn lẻ ở điểm nào?",
                "options": {"A": "Random Forest chỉ dùng một cây nhưng sâu hơn", "B": "Random Forest xây dựng nhiều cây trên các mẫu ngẫu nhiên và kết hợp kết quả (Bagging)", "C": "Random Forest không cần tập huấn luyện", "D": "Random Forest chỉ dùng cho dữ liệu số"},
                "correct_answer": "B",
                "explanation": "Random Forest là phương pháp Ensemble Learning dựa trên Bagging: xây dựng nhiều cây quyết định trên các mẫu bootstrap ngẫu nhiên, mỗi cây cũng chọn ngẫu nhiên một tập con các thuộc tính khi phân chia. Kết quả cuối cùng là bầu chọn đa số từ tất cả các cây."
            }
        ]
    },
    "phan_cum": {
        "title": "Phân cụm Dữ liệu",
        "questions": [
            {
                "id": 1,
                "type": "multiple_choice",
                "question": "Thuật toán K-Means yêu cầu người dùng cung cấp thông tin gì trước khi chạy?",
                "options": {"A": "Nhãn của dữ liệu", "B": "Số cụm K cần tìm", "C": "Khoảng cách tối thiểu giữa các điểm", "D": "Phân phối xác suất của dữ liệu"},
                "correct_answer": "B",
                "explanation": "K-Means yêu cầu người dùng xác định trước số cụm K. Thuật toán sau đó: (1) Chọn ngẫu nhiên K centroid, (2) Gán mỗi điểm vào cụm có centroid gần nhất, (3) Cập nhật centroid bằng trung bình điểm trong cụm, (4) Lặp lại đến khi hội tụ."
            },
            {
                "id": 2,
                "type": "multiple_choice",
                "question": "DBSCAN phân cụm dựa trên nguyên tắc nào?",
                "options": {"A": "Khoảng cách đến centroid", "B": "Phân cấp kết hợp (agglomerative)", "C": "Mật độ điểm trong vùng lân cận Epsilon", "D": "Xác suất Bayes"},
                "correct_answer": "C",
                "explanation": "DBSCAN (Density-Based Spatial Clustering) phân cụm dựa trên mật độ: một điểm là core point nếu có ít nhất MinPts điểm trong vùng bán kính Epsilon. DBSCAN có thể tìm cụm có hình dạng bất kỳ và tự động phát hiện nhiễu (noise/outliers) mà không cần xác định số cụm trước."
            },
            {
                "id": 3,
                "type": "multiple_choice",
                "question": "Nhược điểm lớn nhất của K-Means là gì?",
                "options": {"A": "Không thể xử lý dữ liệu lớn", "B": "Kết quả phụ thuộc vào khởi tạo centroid ban đầu và cần biết trước số cụm K", "C": "Chỉ hoạt động với dữ liệu nhị phân", "D": "Không thể xử lý dữ liệu số"},
                "correct_answer": "B",
                "explanation": "K-Means có hai nhược điểm chính: (1) Kết quả có thể bị kẹt ở cực trị cục bộ tùy thuộc vào centroid khởi tạo ban đầu (giải pháp: K-Means++), (2) Cần xác định trước số cụm K (giải pháp: Elbow method, Silhouette score)."
            },
            {
                "id": 4,
                "type": "multiple_choice",
                "question": "Silhouette Score được dùng để làm gì trong phân cụm?",
                "options": {"A": "Xác định số cụm tối ưu", "B": "Đánh giá chất lượng phân cụm (cohesion vs separation)", "C": "Tính khoảng cách Euclidean", "D": "Khởi tạo centroid ban đầu"},
                "correct_answer": "B",
                "explanation": "Silhouette Score đánh giá chất lượng phân cụm: so sánh khoảng cách trung bình của một điểm đến các điểm trong cụm của nó (cohesion) với khoảng cách trung bình đến cụm gần nhất (separation). Giá trị từ -1 đến 1, càng gần 1 càng tốt."
            },
            {
                "id": 5,
                "type": "multiple_choice",
                "question": "Phân cụm phân cấp Agnes (Agglomerative) bắt đầu như thế nào?",
                "options": {"A": "Bắt đầu với một cụm duy nhất chứa tất cả dữ liệu", "B": "Bắt đầu với mỗi điểm là một cụm riêng, sau đó gộp dần", "C": "Bắt đầu với K centroid ngẫu nhiên", "D": "Bắt đầu bằng cách loại bỏ điểm nhiễu"},
                "correct_answer": "B",
                "explanation": "Agnes (Agglomerative Nesting) là phân cụm phân cấp từ dưới lên (bottom-up): ban đầu mỗi điểm là một cụm riêng, sau đó lặp tục gộp hai cụm gần nhau nhất cho đến khi chỉ còn một cụm. Ngược lại, Diana (Divisive Analysis) bắt đầu với một cụm và tách dần."
            }
        ]
    },
    "tien_xu_ly": {
        "title": "Tiền xử lý Dữ liệu",
        "questions": [
            {
                "id": 1,
                "type": "multiple_choice",
                "question": "Phương pháp nào được dùng để xử lý giá trị thiếu (missing values) trong dữ liệu?",
                "options": {"A": "Chỉ có thể xóa bỏ các hàng có giá trị thiếu", "B": "Điền bằng trung bình, trung vị, hoặc dùng mô hình dự đoán", "C": "Chuyển đổi dữ liệu sang dạng nhị phân", "D": "Chuẩn hóa về khoảng [0,1]"},
                "correct_answer": "B",
                "explanation": "Xử lý missing values có nhiều cách: (1) Xóa bỏ (nếu ít), (2) Điền bằng trung bình/trung vị (dữ liệu số), (3) Điền bằng mode (dữ liệu phân loại), (4) Dùng mô hình dự đoán (KNN imputation, regression). Chọn phương pháp phù hợp với tỷ lệ missing và tính chất dữ liệu."
            },
            {
                "id": 2,
                "type": "multiple_choice",
                "question": "Min-Max Normalization chuẩn hóa dữ liệu về khoảng nào?",
                "options": {"A": "[-1, 1]", "B": "[0, 100]", "C": "[0, 1]", "D": "Phân phối chuẩn N(0,1)"},
                "correct_answer": "C",
                "explanation": "Min-Max Normalization: x' = (x - min) / (max - min). Kết quả nằm trong khoảng [0, 1]. Phương pháp này nhạy cảm với outlier. Z-score Standardization (x' = (x-mean)/std) chuẩn hóa về phân phối N(0,1) và ổn định hơn với outlier."
            },
            {
                "id": 3,
                "type": "multiple_choice",
                "question": "Kỹ thuật nào giúp giảm chiều dữ liệu (dimensionality reduction)?",
                "options": {"A": "One-hot encoding", "B": "PCA (Principal Component Analysis)", "C": "Min-Max normalization", "D": "K-fold cross validation"},
                "correct_answer": "B",
                "explanation": "PCA (Principal Component Analysis) giảm chiều dữ liệu bằng cách chiếu dữ liệu lên các trục chính (principal components) có phương sai lớn nhất. Giúp giảm overfitting, tăng tốc độ huấn luyện và trực quan hóa dữ liệu nhiều chiều."
            },
            {
                "id": 4,
                "type": "multiple_choice",
                "question": "One-hot encoding được dùng để xử lý loại dữ liệu nào?",
                "options": {"A": "Dữ liệu số liên tục", "B": "Dữ liệu thời gian", "C": "Dữ liệu phân loại (categorical) không có thứ tự", "D": "Dữ liệu nhị phân"},
                "correct_answer": "C",
                "explanation": "One-hot encoding chuyển đổi biến phân loại (categorical) không có thứ tự thành các cột nhị phân (0/1). Ví dụ: màu sắc {đỏ, xanh, vàng} → 3 cột: is_red, is_blue, is_yellow. Label Encoding phù hợp hơn cho biến thứ tự (ordinal)."
            },
            {
                "id": 5,
                "type": "multiple_choice",
                "question": "K-fold Cross Validation được sử dụng để làm gì?",
                "options": {"A": "Tăng kích thước tập dữ liệu", "B": "Đánh giá mô hình một cách khách quan và tránh overfitting do chia tập test một lần", "C": "Chuẩn hóa dữ liệu đầu vào", "D": "Chọn số láng giềng K trong KNN"},
                "correct_answer": "B",
                "explanation": "K-fold Cross Validation chia dữ liệu thành K phần bằng nhau, huấn luyện K lần (mỗi lần dùng K-1 phần để train và 1 phần để validate), lấy trung bình K kết quả. Đánh giá khách quan hơn, giảm phụ thuộc vào cách chia tập train/test ngẫu nhiên."
            }
        ]
    },
    "de_cuong": {
        "title": "Đề cương môn học Khai phá Dữ liệu (MSHP: 220269)",
        "questions": [
            {
                "id": 1,
                "type": "multiple_choice",
                "question": "Học phần Khai phá Dữ liệu (MSHP: 220269) có tổng cộng bao nhiêu tín chỉ và phân bổ như thế nào?",
                "options": {
                    "A": "2 tín chỉ (2 Lý thuyết + 0 Thực hành)",
                    "B": "3 tín chỉ (2 Lý thuyết + 1 Thực hành)",
                    "C": "3 tín chỉ (1 Lý thuyết + 2 Thực hành)",
                    "D": "4 tín chỉ (3 Lý thuyết + 1 Thực hành)"
                },
                "correct_answer": "B",
                "explanation": "Học phần Khai phá Dữ liệu có thời lượng là 3 tín chỉ, trong đó có 2 tín chỉ lý thuyết (30 tiết) và 1 tín chỉ thực hành (30 tiết)."
            },
            {
                "id": 2,
                "type": "multiple_choice",
                "question": "Điều kiện học phần tiên quyết đối với sinh viên ngành Trí tuệ nhân tạo khi học môn Khai phá Dữ liệu là gì?",
                "options": {
                    "A": "Cơ sở dữ liệu và Thống kê và phân tích dữ liệu",
                    "B": "Cơ sở dữ liệu và Biên tập và phân tích dữ liệu",
                    "C": "Cấu trúc dữ liệu và giải thuật",
                    "D": "Lập trình Python cơ bản"
                },
                "correct_answer": "B",
                "explanation": "Theo đề cương ngành Trí tuệ nhân tạo (AI), học phần tiên quyết là Cơ sở dữ liệu (MSHP: 220096) và Biên tập và phân tích dữ liệu (MSHP: 220272)."
            },
            {
                "id": 3,
                "type": "multiple_choice",
                "question": "Tỷ lệ điểm đánh giá quá trình và đánh giá kết thúc học phần Khai phá Dữ liệu được quy định như thế nào?",
                "options": {
                    "A": "30% quá trình + 70% kết thúc học phần",
                    "B": "40% quá trình + 60% kết thúc học phần",
                    "C": "50% quá trình + 50% kết thúc học phần (bao gồm 25% Kiểm tra LT + 25% Bài tập lớn)",
                    "D": "100% thi cuối kỳ"
                },
                "correct_answer": "C",
                "explanation": "Đánh giá học phần bao gồm: Đánh giá quá trình 50% (25% Kiểm tra lý thuyết + 25% Bài tập lớn) và Đánh giá kết thúc học phần 50% (thi trắc nghiệm)."
            },
            {
                "id": 4,
                "type": "multiple_choice",
                "question": "Giảng viên nào sau đây KHÔNG nằm trong danh sách dự kiến giảng dạy học phần Khai phá Dữ liệu?",
                "options": {
                    "A": "TS. Nguyễn Bảo Ân",
                    "B": "ThS. Hà Thị Thúy Vi",
                    "C": "ThS. Phạm Thị Trúc Mai",
                    "D": "TS. Trần Văn A"
                },
                "correct_answer": "D",
                "explanation": "Danh sách cán bộ giảng dạy học phần dự kiến gồm có TS. Nguyễn Bảo Ân, ThS. Hà Thị Thúy Vi, và ThS. Phạm Thị Trúc Mai."
            },
            {
                "id": 5,
                "type": "multiple_choice",
                "question": "Bài 4 trong nội dung giảng dạy của đề cương học phần Khai phá Dữ liệu có tên là gì?",
                "options": {
                    "A": "Khai phá tập phổ biến và luật kết hợp",
                    "B": "Phân lớp và Hồi quy",
                    "C": "Phân cụm Dữ liệu",
                    "D": "Hiểu về Dữ liệu và Tiền xử lý Dữ liệu"
                },
                "correct_answer": "B",
                "explanation": "Bài 4 là Phân lớp và Hồi quy (10 tiết lý thuyết + 15 tiết thực hành). Các bài học khác là: Bài 1: Giới thiệu, Bài 2: Tiền xử lý, Bài 3: Luật kết hợp, Bài 5: Phân cụm."
            }
        ]
    }
}

# ============================================================================
# OFFLINE SYLLABUS KNOWLEDGE - Nội dung đề cương môn Khai phá Dữ liệu
# ============================================================================
OFFLINE_SYLLABUS_KNOWLEDGE = {
    "thong_tin_chung": {
        "AI": {
            "nganh": "Trí tuệ nhân tạo",
            "hoc_ky": "VI",
            "nam_thu": 3,
            "mshp": "220269"
        },
        "CNTT": {
            "nganh": "Công nghệ Thông tin",
            "hoc_ky": "VII",
            "nam_thu": 4,
            "mshp": "220269"
        },
        "giang_vien": ["TS. Nguyễn Bảo Ân", "ThS. Hà Thị Thúy Vi", "ThS. Phạm Thị Trúc Mai"]
    },
    "mo_ta_hoc_phan": (
        "Học phần Khai phá dữ liệu giới thiệu các vấn đề cơ bản của khoa học dữ liệu "
        "và các kỹ thuật khai phá dữ liệu phổ biến. Sinh viên sẽ được rèn luyện các kỹ năng "
        "xây dựng mô hình phân lớp, phân cụm, khai thác luật kết hợp trên dữ liệu dạng bảng, "
        "dữ liệu log, dữ liệu văn bản bằng ngôn ngữ lập trình Python hoặc R và các công cụ trực quan."
    ),
    "noi_dung_hoc_phan": {
        "Bài 1": {
            "ten": "Giới thiệu về Khai phá Dữ liệu",
            "so_tiet_LT": 5, "so_tiet_TH": 0,
            "noi_dung": [
                "1.1. Khái niệm về Khai phá Dữ liệu (Data Mining)",
                "1.2. Quy trình KDD (Knowledge Discovery in Databases)",
                "1.3. Các bài toán và ứng dụng của Khai phá Dữ liệu",
                "1.4. Các vấn đề về đạo đức và ảnh hưởng xã hội"
            ]
        },
        "Bài 2": {
            "ten": "Hiểu về Dữ liệu và Tiền xử lý Dữ liệu",
            "so_tiet_LT": 5, "so_tiet_TH": 5,
            "noi_dung": [
                "2.1. Các loại dữ liệu và đặc trưng thống kê",
                "2.2. Làm sạch dữ liệu (xử lý missing values, nhiễu, outlier)",
                "2.3. Tích hợp và biến đổi dữ liệu",
                "2.4. Giảm chiều dữ liệu (PCA, feature selection)",
                "2.5. Chuẩn hóa dữ liệu (normalization, standardization)"
            ]
        },
        "Bài 3": {
            "ten": "Khai phá Tập phổ biến và Luật kết hợp",
            "so_tiet_LT": 5, "so_tiet_TH": 5,
            "noi_dung": [
                "3.1. Khái niệm về tập phổ biến (frequent itemset) và luật kết hợp",
                "3.2. Các độ đo: Support, Confidence, Lift",
                "3.3. Thuật toán Apriori",
                "3.4. Thuật toán FP-Growth và cây FP-Tree",
                "3.5. Ứng dụng: Market Basket Analysis"
            ]
        },
        "Bài 4": {
            "ten": "Phân lớp và Hồi quy",
            "so_tiet_LT": 10, "so_tiet_TH": 15,
            "noi_dung": [
                "4.1. Khái niệm về phân lớp và hồi quy",
                "4.2. Thuật toán cây quyết định (ID3, C4.5)",
                "4.3. Thuật toán KNN (K-Nearest Neighbors)",
                "4.4. Thuật toán Naive Bayes",
                "4.5. Thuật toán Support Vector Machine (SVM)",
                "4.6. Đánh giá và lựa chọn mô hình (Accuracy, Precision, Recall, F1)",
                "4.7. Phương pháp tập hợp mô hình: Bagging, Boosting",
                "4.8. Thuật toán Random Forest",
                "4.9. Thuật toán AdaBoost"
            ]
        },
        "Bài 5": {
            "ten": "Phân cụm Dữ liệu",
            "so_tiet_LT": 5, "so_tiet_TH": 5,
            "noi_dung": [
                "5.1. Giới thiệu về phân cụm dữ liệu",
                "5.2. Phân cụm phân hoạch: Thuật toán K-Means",
                "5.3. Phân cụm phân cấp: Thuật toán Agnes và Diana",
                "5.4. Phân cụm dựa trên mật độ: Thuật toán DBSCAN",
                "5.5. Đánh giá chất lượng phân cụm (Silhouette Score)"
            ]
        }
    },
    "danh_gia_hoc_phan": [
        {"hinh_thuc": "Kiểm tra lý thuyết (Bài 1-3)", "ti_le": "25%", "loai": "Đánh giá quá trình"},
        {"hinh_thuc": "Bài tập lớn (Bài 2-5)", "ti_le": "25%", "loai": "Đánh giá quá trình"},
        {"hinh_thuc": "Thi trắc nghiệm cuối kỳ (Bài 1-5)", "ti_le": "50%", "loai": "Đánh giá kết thúc học phần"}
    ],
    "phuong_phap_giang_day": [
        "Diễn giảng",
        "Vấn đáp (Questions – Answers)",
        "Hoạt động nhóm (Group-based Learning)",
        "Học dựa trên dự án (Project-based Learning)",
        "Thao tác mẫu (Demo)"
    ],
    "quy_dinh": {
        "vang_mat": "Vắng quá 20% số giờ bị xem như không hoàn thành học phần và phải đăng ký học lại.",
        "hanh_vi": "Không làm ồn, không dùng điện thoại nghe nhạc, máy tính chỉ dùng cho mục đích học tập."
    }
}


def detect_quiz_topic(question: str) -> str:
    """
    Phát hiện chủ đề quiz từ câu hỏi
    Returns: topic key nếu nhận ra, None nếu không
    """
    q_lower = question.lower()
    q_norm = normalize_query_text(question)
    
    # Kiểm tra có phải yêu cầu quiz/trắc nghiệm không
    # Lưu ý: KHÔNG thêm "cho tôi" vì quá chung — "hãy cho tôi xem code Python" không phải là yêu cầu quiz
    is_quiz_request = any(kw in q_lower for kw in [
        "trắc nghiệm", "trac nghiem", "quiz", "câu hỏi trắc nghiệm",
        "ôn tập", "on tap",
    ])
    
    if not is_quiz_request:
        return None
    
    # Xác định chủ đề - ưu tiên từ cụ thể đến tổng quát
    if any(kw in q_lower for kw in ["đề cương", "de cuong", "syllabus", "học phần", "hoc phan", "môn học", "mon hoc", "220269"]):
        return "de_cuong"
    elif any(kw in q_lower for kw in ["apriori", "a priori"]):
        return "apriori"
    elif any(kw in q_lower for kw in ["fp-growth", "fp growth", "tập phổ biến", "tap pho bien", "frequent", "luật kết hợp", "luat ket hop"]):
        return "frequent_pattern"
    elif any(kw in q_lower for kw in ["phân lớp", "phan lop", "phân loại", "phan loai", "knn", "naive bayes", "svm", "decision tree", "cây quyết định", "random forest", "hồi quy", "hoi quy"]):
        return "phan_lop"
    elif any(kw in q_lower for kw in ["phân cụm", "phan cum", "clustering", "k-means", "kmeans", "dbscan", "agnes", "diana"]):
        return "phan_cum"
    elif any(kw in q_lower for kw in ["tiền xử lý", "tien xu ly", "preprocessing", "chuẩn hóa", "chuan hoa", "normalization", "missing value", "pca"]):
        return "tien_xu_ly"
    elif any(kw in q_lower for kw in ["data mining", "khai phá", "khai pha"]):
        return "data_mining"
    
    return None


def detect_syllabus_question(question: str) -> bool:
    """
    Phát hiện câu hỏi liên quan đến đề cương môn học
    Returns: True nếu là câu hỏi về đề cương, False nếu không
    """
    q_lower = question.lower()
    q_norm = normalize_query_text(question)
    
    # Chỉ khớp các từ khoá hành chính hoặc thông tin đề cương chung
    # Lưu ý: "đánh giá" bị loại khỏi danh sách vì quá chung chung
    # (vd: "đánh giá luật kết hợp" là câu hỏi kỹ thuật, không phải đề cương)
    syllabus_admin_keywords = [
        "đề cương", "de cuong", "syllabus", "học phần", "hoc phan", "môn học", "mon hoc",
        "tín chỉ", "tin chi", "học kỳ", "hoc ky", "giảng viên", "giang vien", "giáo viên", "giao vien",
        "chuẩn đầu ra", "chuan dau ra", "clo", "lớp ai", "lớp cntt", "220269", "mshp",
        "thi", "kiểm tra", "kiem tra", "tỷ lệ điểm", "ty le diem", "trọng số", "trong so",
        "hình thức đánh giá", "hinh thuc danh gia", "đánh giá học phần", "danh gia hoc phan",
        "tài liệu tham khảo", "tai lieu tham khao", "tài liệu chính", "tai lieu chinh"
    ]
    
    syllabus_admin_keywords_norm = [
        "de cuong", "syllabus", "hoc phan", "mon hoc", "tin chi", "hoc ky",
        "giang vien", "giao vien", "chuan dau ra", "clo", "lop ai", "lop cntt",
        "220269", "mshp", "thi", "kiem tra", "ty le diem", "trong so",
        "hinh thuc danh gia", "danh gia hoc phan", "tai lieu tham khao",
        "tai lieu chinh", "bai tap lon", "bao nhieu phan tram", "chiem bao nhieu",
        "tu bai may", "den bai may",
    ]
    if any(kw in q_lower for kw in syllabus_admin_keywords) or any(kw in q_norm for kw in syllabus_admin_keywords_norm):
        return True
        
    # Chỉ coi là câu hỏi đề cương nếu hỏi về danh sách bài học cụ thể
    if any(kw in q_lower for kw in ["nội dung bài", "nội dung học", "học những bài nào", "học những chương nào", "danh sách bài"]):
        return True
        
    return False


def normalize_query_text(text: str) -> str:
    """Lowercase, remove Vietnamese accents, and collapse spaces for routing."""
    text = (text or "").lower()
    text = unicodedata.normalize("NFD", text)
    text = "".join(ch for ch in text if unicodedata.category(ch) != "Mn")
    text = text.replace("đ", "d")
    text = re.sub(r"[^a-z0-9\s\-\+\.#]", " ", text)
    return re.sub(r"\s+", " ", text).strip()


def clean_source_filename(value: Any) -> str:
    """Normalize source names for display and remove generated numeric suffixes."""
    filename = str(value or "Unknown").replace("\\", "/").split("/")[-1]
    filename = re.sub(r"-(?:\d{7,})(?=\.[A-Za-z0-9]+$)", "", filename)
    filename = re.sub(r"_(?:\d{7,})(?=\.[A-Za-z0-9]+$)", "", filename)
    return filename


def is_word_like_source(filename: str) -> bool:
    """DOC/DOCX/TXT chunks do not have meaningful page numbers for UI citations."""
    return bool(re.search(r"\.(?:docx?|txt)$", str(filename or ""), re.IGNORECASE))


def strip_generated_reference_block(text: str) -> str:
    """Remove LLM-generated reference/source sections; UI renders citations separately."""
    if not text:
        return text
    lines = text.splitlines()
    ref_headings = {
        "tai lieu tham khao",
        "nguon tai lieu",
        "nguon tham khao",
        "tham khao",
        "references",
        "sources",
        "source",
        "nguon",
    }
    for i, line in enumerate(lines):
        normalized = normalize_query_text(re.sub(r"^[#>*\-\s]+", "", line).strip(":： "))
        if normalized in ref_headings:
            return "\n".join(lines[:i]).rstrip()
    return text.rstrip()


def is_refusal_answer(text: str) -> bool:
    """Detect answers that are effectively 'not found' refusals."""
    normalized = normalize_query_text(text)
    refusal_markers = [
        "toi khong tim thay",
        "t i kh ng t m th y",
        "khong tim thay thong tin",
        "kh ng t m th y th ng tin",
        "khong co thong tin",
        "kh ng c th ng tin",
        "tai lieu khong cung cap",
        "t i li u kh ng cung c p",
        "khong du do tin cay",
        "kh ng d do tin c y",
        "not found",
        "does not contain",
    ]
    return any(marker in normalized for marker in refusal_markers)


def is_summary_request(question: str) -> bool:
    """Detect requests that ask for a real summary, not just a definition."""
    q_norm = normalize_query_text(question)
    summary_markers = [
        "tom tat", "tong ket", "khai quat", "noi dung chinh",
        "cac y chinh", "summary", "summarize", "overview",
        "t m t t", "t ng k t", "kh i qu t",
    ]
    return any(marker in q_norm for marker in summary_markers)


def cross_lingual_retrieval_queries(question: str) -> List[str]:
    """
    Deterministic Vietnamese -> English retrieval bridge.
    Keeps RAG strict, but searches English slides/books with English terms.
    """
    q_norm = normalize_query_text(question)
    queries: List[str] = []

    def has(*terms: str) -> bool:
        return any(term in q_norm for term in terms)

    if has("khai pha du lieu", "data mining") and has("hoc may", "machine learning", "ml"):
        queries.extend([
            "data mining definition extracting interesting patterns knowledge from large amounts of data",
            "data mining machine learning statistics relationship",
            "data mining versus machine learning comparison",
        ])

    if detect_syllabus_question(question):
        queries.extend([
            "de cuong khai pha du lieu bai tap lon 25% bai 2 bai 5",
            "hinh thuc danh gia bai tap lon chiem 25 phan tram noi dung tu bai 2 den bai 5",
            "course outline data mining project assessment 25 percent lesson 2 lesson 5",
        ])

    if has("khai pha du lieu", "data mining") and has("la gi", "khai niem", "dinh nghia"):
        queries.extend([
            "what is data mining definition extracting hidden patterns useful knowledge",
            "data mining knowledge discovery patterns interesting useful data",
        ])

    if has("kdd", "quy trinh kdd"):
        queries.extend([
            "KDD process data cleaning integration selection transformation data mining pattern evaluation knowledge presentation",
            "knowledge discovery in databases process steps",
        ])

    if has("phan lop", "classification") and has("phan cum", "clustering"):
        queries.extend([
            "classification supervised learning training data class labels",
            "clustering unsupervised learning class labels unknown groups clusters",
            "classification versus clustering supervised unsupervised comparison",
        ])

    if has("ngoai lai", "outlier", "outliers") and has("k-means", "kmeans", "k means"):
        queries.extend([
            "k-means sensitive to outliers extremely large value distort distribution data",
            "k-means sensitive to noise outliers mean value affected",
            "k-means algorithm sensitive to outliers",
        ])

    if (
        has("so sanh", "compare", "khac nhau")
        and has("k-means", "kmeans", "k means")
        and has("dbscan")
        and has("hierarchical", "phan cap")
    ):
        queries.extend([
            "k-means partitioning clustering centroid number of clusters",
            "DBSCAN density based clustering noise arbitrary shape clusters",
            "hierarchical clustering agglomerative divisive dendrogram",
            "compare k-means DBSCAN hierarchical clustering partitioning density based hierarchical",
        ])

    if has("nhieu du lieu", "du lieu nhieu", "noise"):
        queries.extend([
            "noise random error variance measured variable",
            "noisy data salary -10 example data cleaning",
        ])

    if has("chuan hoa", "min max", "z score", "z-score"):
        queries.extend([
            "data normalization min-max normalization z-score standardization",
            "min-max normalization z-score when to use",
        ])

    if is_summary_request(question) and has("tien xu ly", "ti n x l", "preprocessing", "data preprocessing"):
        queries.extend([
            "data preprocessing overview data cleaning data integration data reduction data transformation discretization",
            "data cleaning fill missing values smooth noisy data identify outliers resolve inconsistencies",
            "data integration combine data from multiple databases data cubes files",
            "data reduction dimensionality reduction numerosity reduction data compression",
            "data transformation normalization aggregation generalization discretization concept hierarchies",
            "data quality accuracy completeness consistency timeliness believability interpretability",
        ])

    if has("cosine", "cosine similarity", "do tuong dong cosine") or (
        has("d1", "tai lieu d1") and has("d2", "tai lieu d2")
    ):
        queries.extend([
            "cosine similarity formula document d1 d2 preprocessing",
            "cosine similarity d1 d2 document vector example",
            "cosine measure similarity dot product norm d1 d2",
        ])

    if has("fp-growth", "fp growth", "fpgrowth", "fp tree", "fptree") and has("apriori"):
        queries.extend([
            "FP-Growth versus Apriori no candidate generation no candidate test FP-tree",
            "FP-Growth compress database FP-tree avoids candidate generation Apriori",
            "Apriori candidate generation multiple database scans FP-Growth two database scans",
            "FP-Growth mining frequent patterns without candidate generation compared with Apriori",
        ])

    if has("apriori"):
        queries.extend([
            "apriori algorithm frequent itemsets association rules support confidence",
            "apriori property antimonotone pruning association rule mining",
        ])

    if has("fp-growth", "fp growth", "fpgrowth", "fp tree", "fptree"):
        queries.extend([
            "FP-Growth frequent pattern growth FP-tree no candidate generation",
            "FP-tree conditional pattern base frequent itemset mining",
        ])

    if has("information gain", "gain"):
        queries.extend([
            "information gain entropy decision tree attribute selection measure",
            "decision tree information gain example",
        ])

    if has("entropy", "entropi") and has("decision tree", "cay quyet dinh", "classification", "phan lop"):
        queries.extend([
            "expected information entropy decision tree classification",
            "Info D entropy decision tree class distribution",
            "entropy information gain attribute selection decision tree",
        ])

    if has("gini", "gini index") and has("decision tree", "cay quyet dinh", "classification", "phan lop"):
        queries.extend([
            "gini index decision tree CART attribute selection",
            "gini impurity decision tree classification",
        ])

    if has("id3", "c4.5", "cart") or (
        has("decision tree", "cay quyet dinh") and has("information gain", "entropy", "gini")
    ):
        queries.extend([
            "decision tree induction attribute selection information gain entropy gini index",
            "ID3 decision tree information gain entropy",
            "CART decision tree gini index",
        ])

    if has("bagging", "boosting", "metacost", "meta cost"):
        queries.extend([
            "bagging boosting ensemble prediction voting weighted classifiers",
            "bagging versus boosting prediction mechanism ensemble learning",
            "MetaCost bagging cost-sensitive classification misclassification cost",
            "MetaCost combines bagging cost sensitive learning",
        ])

    topic_map = {
        "k-means": "k-means clustering centroid outliers",
        "kmeans": "k-means clustering centroid outliers",
        "decision tree": "decision tree classification information gain",
        "cay quyet dinh": "decision tree classification information gain",
        "entropy": "expected information entropy decision tree",
        "information gain": "information gain entropy decision tree attribute selection",
        "gini": "gini index decision tree CART",
        "id3": "ID3 decision tree information gain entropy",
        "c4.5": "C4.5 decision tree classification",
        "cart": "CART decision tree gini index",
        "phan cum": "clustering unsupervised learning clusters",
        "phan lop": "classification supervised learning class labels",
        "du lieu thieu": "missing values data cleaning preprocessing",
        "tien xu ly": "data preprocessing data cleaning integration transformation",
        "cosine": "cosine similarity document vector dot product norm",
        "do tuong dong cosine": "cosine similarity document vector dot product norm",
        "dbscan": "DBSCAN density based clustering",
        "hierarchical": "hierarchical clustering agglomerative divisive dendrogram",
        "bagging": "bagging bootstrap aggregating ensemble voting",
        "boosting": "boosting ensemble weighted classifiers AdaBoost",
        "metacost": "MetaCost bagging cost-sensitive classification",
    }
    for term, query in topic_map.items():
        if term in q_norm:
            queries.append(query)

    seen = set()
    unique = []
    for query in queries:
        if query not in seen:
            seen.add(query)
            unique.append(query)
    return unique


def is_direct_tutor_request(question: str) -> bool:
    """Requests that should be answered as a tutor, not rejected for missing citations."""
    q_norm = normalize_query_text(question)
    direct_markers = [
        "lo trinh", "ke hoach hoc", "7 ngay", "quiz", "trac nghiem",
        "goi y chu de", "on tiep", "toi tra loi sai", "vi sao sai",
    ]
    code_markers = ["code", "python", "pandas", "sklearn", "scikit", "csv", "ma tran nham lan"]
    return any(marker in q_norm for marker in direct_markers + code_markers)


def is_context_dependent_question(question: str) -> bool:
    """Only use conversation history when the current turn clearly depends on it."""
    q_norm = normalize_query_text(question)
    phrase_indicators = [
        "nguon 1", "nguon 2", "nguon 3", "noi tren", "y tren", "phan tren",
        "cau tren", "cau nay", "cau do", "thuat toan nay",
        "phuong phap do", "ky thuat tren", "cai do", "giai thich tiep",
        "chi tiet hon", "tiep tuc", "them ve", "vi sao sai",
    ]
    if any(ind in q_norm for ind in phrase_indicators):
        return True
    # Very short follow-ups are usually dependent on the previous answer.
    return len(q_norm.split()) <= 4


def get_mixed_syllabus_code_response(question: str) -> Optional[str]:
    """Answer common mixed request: course assessment + runnable DBSCAN code."""
    q_norm = normalize_query_text(question)
    asks_assignment = any(term in q_norm for term in ["bai tap lon", "project", "do an"])
    asks_percent = any(term in q_norm for term in ["phan tram", "bao nhieu", "%", "ti le", "trong so", "chiem"])
    asks_scope = any(term in q_norm for term in ["bai may", "tu bai", "den bai", "noi dung"])
    asks_dbscan_code = "dbscan" in q_norm and any(
        term in q_norm for term in ["code", "python", "sklearn", "scikit", "hoan chinh"]
    )
    if not (asks_assignment and asks_percent and asks_dbscan_code):
        return None

    scope_text = " và bao hàm nội dung từ **Bài 2 đến Bài 5**" if asks_scope else ""
    return (
        "### 1. Hình thức đánh giá Bài tập lớn\n\n"
        f"Trong đề cương môn Khai phá dữ liệu, **Bài tập lớn chiếm 25%** điểm đánh giá quá trình{scope_text}.\n\n"
        "### 2. Code Python chạy DBSCAN bằng scikit-learn\n\n"
        "```python\n"
        "import numpy as np\n"
        "import matplotlib.pyplot as plt\n"
        "from sklearn.cluster import DBSCAN\n"
        "from sklearn.datasets import make_moons\n"
        "from sklearn.preprocessing import StandardScaler\n\n"
        "# 1. Tạo dữ liệu mẫu có dạng phi tuyến để thấy ưu điểm của DBSCAN\n"
        "X, _ = make_moons(n_samples=300, noise=0.08, random_state=42)\n"
        "X = StandardScaler().fit_transform(X)\n\n"
        "# 2. Khởi tạo và huấn luyện DBSCAN\n"
        "model = DBSCAN(eps=0.25, min_samples=5)\n"
        "labels = model.fit_predict(X)\n\n"
        "# 3. Thống kê số cụm và số điểm nhiễu\n"
        "cluster_ids = set(labels)\n"
        "n_clusters = len(cluster_ids - {-1})\n"
        "n_noise = int(np.sum(labels == -1))\n\n"
        "print('Số cụm:', n_clusters)\n"
        "print('Số điểm nhiễu:', n_noise)\n"
        "print('Nhãn cụm:', labels[:20])\n\n"
        "# 4. Vẽ kết quả\n"
        "plt.figure(figsize=(7, 5))\n"
        "plt.scatter(X[:, 0], X[:, 1], c=labels, cmap='viridis', s=35)\n"
        "plt.title('DBSCAN clustering result')\n"
        "plt.xlabel('Feature 1')\n"
        "plt.ylabel('Feature 2')\n"
        "plt.colorbar(label='Cluster label (-1 = noise)')\n"
        "plt.show()\n"
        "```\n\n"
        "*Ghi chú: Phần đánh giá học phần lấy theo đề cương; phần code Python là nội dung thực hành mở rộng bằng scikit-learn.*"
    )


def is_data_mining_domain_question(question: str) -> bool:
    """Broad guard for safe tutor fallback on data-mining / ML study questions."""
    q_norm = normalize_query_text(question)
    domain_terms = [
        "khai pha du lieu", "data mining", "kdd", "hoc may", "machine learning",
        "phan lop", "classification", "phan cum", "clustering", "decision tree",
        "cay quyet dinh", "information gain", "entropy", "gini", "id3", "c4.5",
        "cart", "k-means", "kmeans", "dbscan", "hierarchical", "apriori",
        "fp-growth", "fp growth", "fpgrowth", "association rule", "luat ket hop",
        "preprocessing", "tien xu ly", "ti n x l", "missing value", "du lieu thieu",
        "noise", "nhieu du lieu", "normalization", "chuan hoa", "cross encoder",
        "reranking", "accuracy", "precision", "recall", "f1",
    ]
    return any(term in q_norm for term in domain_terms)


def classify_question_intent(question: str) -> str:
    """
    Intent Router:
    - closed_rag: must answer from documents.
    - pedagogical: explain/compare/examples/study guidance can use tutor knowledge.
    - code_lab: code/data-science implementation help.
    - conversational: greeting/small talk.
    """
    q = (question or "").lower()
    q_norm = normalize_query_text(question)

    if q_norm in {"xin chao", "chao", "hello", "hi", "hey", "chao ban"}:
        return "conversational"

    if requires_document_grounding(question) or detect_syllabus_question(question):
        return "closed_rag"

    theory_markers = [
        "so sanh", "la gi", "dinh nghia", "khai niem", "giai thich",
        "phan biet", "khac gi", "vi sao", "tai sao"
    ]
    code_keywords = [
        "code", "python", "pandas", "sklearn", "scikit", "dropna", "fillna",
        "confusion matrix", "ma tran nham lan", "data lab", "chay thu",
        "lap trinh", "viet chuong trinh", "viet ma", "doan ma"
    ]
    metric_code_request = (
        any(kw in q_norm for kw in ["tinh accuracy", "tinh precision", "tinh recall", "tinh f1"])
        and any(kw in q_norm for kw in ["code", "python", "vi du"])
    )
    dataset_code_request = (
        any(kw in q_norm for kw in ["csv", "dataset"])
        and any(kw in q_norm for kw in ["phan tich", "code", "python", "doc file"])
    )
    if (any(kw in q_norm for kw in code_keywords) or metric_code_request or dataset_code_request) and not any(
        kw in q_norm for kw in theory_markers
    ):
        return "code_lab"

    pedagogical_keywords = [
        "la gi", "khac gi", "giai thich", "nguoi moi", "de hieu",
        "vi du", "doi song", "so sanh", "bang", "tom tat", "t m t t", "tong ket",
        "khai quat", "noi dung chinh", "summary", "summarize", "lo trinh", "ke hoach hoc",
        "7 ngay", "quiz", "trac nghiem", "goi y", "on tiep", "chua hieu",
        "tung buoc", "tai sao", "vi sao", "nhay cam", "mat can bang",
        "kdd", "khai pha du lieu", "data mining", "hoc may", "machine learning",
        "k-means", "kmeans", "decision tree", "cay quyet dinh", "apriori",
        "fp-growth", "fp growth", "fpgrowth", "fp tree", "fptree",
        "information gain", "entropy", "gini", "id3", "c4.5", "cart",
        "phan lop", "phan cum", "dbscan", "hierarchical",
        "cross-encoder", "reranking", "missing value", "chuan hoa", "du lieu thieu", "ti n x l",
        "nhieu du lieu", "noise"
    ]
    if any(kw in q_norm for kw in pedagogical_keywords):
        return "pedagogical"

    return "closed_rag"


def get_direct_tutor_response(question: str) -> Optional[str]:
    """
    Handle conversational/tutoring intents that should not be rejected by
    retrieval confidence. These answers are guidance, not document-grounded QA.
    """
    q_lower = question.lower().strip()
    q_norm = normalize_query_text(question)
    q_compact = re.sub(r"\s+", " ", q_lower)

    greetings = {
        "xin chào", "chào", "hello", "hi", "hey", "chao", "xin chao",
        "chào bạn", "chao ban"
    }
    if q_compact in greetings or q_norm in {"xin chao", "chao", "hello", "hi", "hey", "chao ban"}:
        return (
            "Xin chào! Mình là MinerAI, gia sư AI hỗ trợ học môn Khai phá dữ liệu.\n\n"
            "Bạn có thể hỏi mình về K-Means, Decision Tree, Apriori, tiền xử lý dữ liệu, "
            "đề cương học phần, hoặc yêu cầu tạo quiz ôn tập."
        )

    asks_entropy = "entropy" in q_norm or "entropi" in q_norm
    asks_information_gain = "information gain" in q_norm or "gain" in q_norm
    asks_gini = "gini" in q_norm
    asks_tree_metric = any(term in q_norm for term in ["decision tree", "cay quyet dinh", "id3", "c4.5", "cart"])
    if asks_information_gain and (asks_tree_metric or "dung de lam gi" in q_norm or "la gi" in q_norm):
        return (
            "Information Gain dùng để **chọn thuộc tính phân tách tốt nhất** khi xây dựng cây quyết định, đặc biệt trong ID3/C4.5.\n\n"
            "Ý tưởng: trước khi chia dữ liệu, ta đo mức hỗn loạn bằng Entropy. Sau khi thử chia theo một thuộc tính, nếu Entropy giảm nhiều thì thuộc tính đó giúp phân lớp tốt. Mức giảm đó gọi là **Information Gain**.\n\n"
            "Công thức thường dùng:\n\n"
            "$$Information\\ Gain(A) = Entropy(S) - \\sum_v \\frac{|S_v|}{|S|} Entropy(S_v)$$\n\n"
            "Thuộc tính có Information Gain lớn nhất thường được chọn để tách tại nút hiện tại.\n\n"
            "*Thông tin này được mở rộng từ kiến thức thực tế, không nằm trong giáo trình chính thức.*"
        )

    if asks_entropy and (asks_tree_metric or "la gi" in q_norm):
        return (
            "Entropy trong cây quyết định là độ đo mức **hỗn loạn/không thuần nhất** của một tập dữ liệu theo nhãn lớp.\n\n"
            "- Entropy cao: dữ liệu trong nút bị trộn nhiều lớp, khó phân loại.\n"
            "- Entropy thấp: dữ liệu trong nút chủ yếu thuộc một lớp, nút thuần hơn.\n"
            "- Entropy bằng 0: tất cả mẫu trong nút thuộc cùng một lớp.\n\n"
            "Công thức:\n\n"
            "$$Entropy(S) = -\\sum_i p_i \\log_2(p_i)$$\n\n"
            "Trong cây quyết định, Entropy được dùng để tính Information Gain, từ đó chọn thuộc tính giúp chia dữ liệu tốt nhất.\n\n"
            "*Thông tin này được mở rộng từ kiến thức thực tế, không nằm trong giáo trình chính thức.*"
        )

    if asks_gini and (asks_tree_metric or "la gi" in q_norm or "dung de lam gi" in q_norm):
        return (
            "Gini Index là độ đo độ không thuần nhất thường dùng trong cây quyết định CART.\n\n"
            "$$Gini(S) = 1 - \\sum_i p_i^2$$\n\n"
            "Khi xây cây, CART thử các cách chia và ưu tiên phép chia làm Gini sau phân tách nhỏ nhất. Gini càng nhỏ thì các nút con càng thuần, tức dữ liệu trong mỗi nút càng nghiêng về một lớp rõ ràng.\n\n"
            "*Thông tin này được mở rộng từ kiến thức thực tế, không nằm trong giáo trình chính thức.*"
        )

    asks_study_plan = any(kw in q_lower for kw in [
        "lộ trình", "lo trinh", "kế hoạch học", "ke hoach hoc",
        "học trong 7 ngày", "hoc trong 7 ngay", "7 ngày", "7 ngay"
    ]) or any(kw in q_norm for kw in ["lo trinh", "ke hoach hoc", "hoc trong 7 ngay", "7 ngay"])
    asks_data_mining_plan = any(kw in q_lower for kw in [
        "khai phá dữ liệu", "khai pha du lieu", "data mining"
    ]) or any(kw in q_norm for kw in ["khai pha du lieu", "data mining"])
    if asks_study_plan and asks_data_mining_plan:
        return (
            "Dưới đây là lộ trình học Khai phá dữ liệu trong 7 ngày:\n\n"
            "### Ngày 1: Tổng quan khai phá dữ liệu\n"
            "- Hiểu khái niệm Data Mining, KDD và vai trò của khai phá dữ liệu.\n"
            "- Phân biệt dữ liệu, thông tin, tri thức và mô hình.\n\n"
            "### Ngày 2: Tiền xử lý dữ liệu\n"
            "- Học cách xử lý dữ liệu thiếu, nhiễu, ngoại lai.\n"
            "- Ôn chuẩn hóa Min-Max, Z-score và mã hóa dữ liệu phân loại.\n\n"
            "### Ngày 3: Phân lớp dữ liệu\n"
            "- Học Decision Tree, Naive Bayes, KNN ở mức ý tưởng.\n"
            "- Nắm các chỉ số Accuracy, Precision, Recall, F1-score.\n\n"
            "### Ngày 4: Phân cụm dữ liệu\n"
            "- Học K-Means, DBSCAN và phân cụm phân cấp.\n"
            "- Tập giải thích centroid, số cụm K, khoảng cách và ngoại lai.\n\n"
            "### Ngày 5: Luật kết hợp\n"
            "- Học Apriori, frequent itemset, support, confidence và lift.\n"
            "- Làm ví dụ giỏ hàng để hiểu cách sinh luật.\n\n"
            "### Ngày 6: Ôn tập bằng bài tập và quiz\n"
            "- Tạo quiz cho từng chủ đề: tiền xử lý, phân lớp, phân cụm, Apriori.\n"
            "- Ghi lại các câu sai và hỏi lại gia sư AI để được giải thích.\n\n"
            "### Ngày 7: Tổng hợp và demo\n"
            "- Lập bảng so sánh các thuật toán chính.\n"
            "- Chuẩn bị 5 câu hỏi demo có trích dẫn nguồn và 2 câu hỏi code Python.\n\n"
            "Gợi ý học hiệu quả: mỗi ngày nên dành 60-90 phút, gồm 30 phút đọc lý thuyết, "
            "30 phút hỏi đáp với gia sư AI và 15-30 phút làm quiz hoặc ví dụ Python."
        )

    return None


def requires_document_grounding(question: str) -> bool:
    """
    True when the user explicitly asks for document-grounded evidence.
    These questions should stay strict: if RAG cannot support them, say so.
    """
    q_lower = question.lower()
    grounding_keywords = [
        "theo tài liệu", "theo tai lieu", "trích dẫn", "trich dan",
        "dẫn nguồn", "dan nguon", "nêu nguồn", "neu nguon",
        "nguồn", "source", "citation", "citations",
        "theo slide", "trong slide", "slide chương", "slide chuong",
        "theo bài giảng", "theo bai giang", "trong bài giảng", "trong bai giang",
        "bài giảng về", "bai giang ve",
        "theo giáo trình", "theo giao trinh", "giáo trình", "giao trinh",
        "han", "kamber", "pei",
    ]
    return any(kw in q_lower for kw in grounding_keywords)


def get_tutor_knowledge_response(question: str) -> Optional[str]:
    """
    Knowledge fallback for tutor-style questions. This is intentionally used
    only when the user did not require document citations.
    """
    direct = get_direct_tutor_response(question)
    if direct:
        return direct

    q_lower = question.lower()
    q_norm = normalize_query_text(question)

    if (
        any(kw in q_norm for kw in ["fp-growth", "fp growth", "fpgrowth", "fp tree", "fptree"])
        and "apriori" in q_norm
        and any(kw in q_norm for kw in ["khac", "khac nhau", "so sanh", "phan biet", "compare"])
    ):
        return (
            "### FP-Growth khác Apriori ở điểm nào?\n\n"
            "| Tiêu chí | Apriori | FP-Growth |\n"
            "|---|---|---|\n"
            "| Cách tìm tập phổ biến | Sinh các tập ứng viên rồi quét dữ liệu để kiểm tra support | Nén dữ liệu vào FP-tree rồi khai thác trực tiếp trên cây |\n"
            "| Sinh ứng viên | Có, thường sinh rất nhiều candidate itemsets | Không sinh ứng viên và không cần kiểm tra ứng viên theo kiểu Apriori |\n"
            "| Số lần quét dữ liệu | Có thể phải quét nhiều lần theo từng mức k-itemset | Thường chỉ cần quét dữ liệu để đếm tần suất và xây FP-tree |\n"
            "| Hiệu năng | Dễ chậm khi số item lớn hoặc dữ liệu dày đặc | Thường nhanh hơn vì giảm số lần quét và giảm không gian ứng viên |\n\n"
            "Nói ngắn gọn: **Apriori tìm bằng cách sinh rồi lọc ứng viên**, còn **FP-Growth tìm bằng cách nén dữ liệu vào FP-tree và khai thác mẫu phổ biến mà không sinh ứng viên**.\n\n"
            "*Thông tin này được mở rộng từ kiến thức thực tế, không nằm trong giáo trình chính thức.*"
        )

    if classify_question_intent(question) == "code_lab":
        if "dbscan" in q_norm:
            return (
                "```python\n"
                "import numpy as np\n"
                "import pandas as pd\n"
                "from sklearn.cluster import DBSCAN\n"
                "from sklearn.datasets import load_iris\n"
                "from sklearn.preprocessing import StandardScaler\n\n"
                "iris = load_iris()\n"
                "X = iris.data\n"
                "X_scaled = StandardScaler().fit_transform(X)\n\n"
                "model = DBSCAN(eps=0.8, min_samples=5)\n"
                "labels = model.fit_predict(X_scaled)\n\n"
                "n_clusters = len(set(labels) - {-1})\n"
                "n_noise = int(np.sum(labels == -1))\n"
                "df = pd.DataFrame(X, columns=iris.feature_names)\n"
                "df['cluster'] = labels\n\n"
                "print('So cum:', n_clusters)\n"
                "print('So diem nhieu:', n_noise)\n"
                "print(df.head())\n"
                "```\n\n"
                "*Thông tin này được mở rộng từ kiến thức thực tế, không nằm trong giáo trình chính thức.*"
            )
        if any(kw in q_norm for kw in ["k means", "k-means", "kmeans"]):
            return (
                "```python\n"
                "import pandas as pd\n"
                "from sklearn.cluster import KMeans\n"
                "from sklearn.preprocessing import StandardScaler\n\n"
                "# Ví dụ dữ liệu mẫu\n"
                "df = pd.DataFrame({\n"
                "    'age': [20, 22, 45, 47, 23, 46],\n"
                "    'income': [5, 6, 20, 22, 7, 21]\n"
                "})\n\n"
                "X = df[['age', 'income']]\n"
                "X_scaled = StandardScaler().fit_transform(X)\n\n"
                "model = KMeans(n_clusters=2, random_state=42, n_init='auto')\n"
                "df['cluster'] = model.fit_predict(X_scaled)\n\n"
                "print(df)\n"
                "print('Centroids:', model.cluster_centers_)\n"
                "```\n\n"
                "*Thông tin này được mở rộng từ kiến thức thực tế, không nằm trong giáo trình chính thức.*"
            )
        if any(kw in q_norm for kw in ["missing", "thieu", "fillna", "dropna"]):
            return (
                "```python\n"
                "import pandas as pd\n"
                "from sklearn.impute import SimpleImputer\n\n"
                "df = pd.DataFrame({\n"
                "    'age': [20, 21, None, 23],\n"
                "    'score': [8.0, None, 7.5, 9.0]\n"
                "})\n\n"
                "# Cách 1: dùng pandas\n"
                "df['age'] = df['age'].fillna(df['age'].mean())\n"
                "df['score'] = df['score'].fillna(df['score'].median())\n\n"
                "# Cách 2: dùng scikit-learn\n"
                "imputer = SimpleImputer(strategy='mean')\n"
                "df[['age', 'score']] = imputer.fit_transform(df[['age', 'score']])\n\n"
                "print(df)\n"
                "```\n\n"
                "*Thông tin này được mở rộng từ kiến thức thực tế, không nằm trong giáo trình chính thức.*"
            )
        if any(kw in q_norm for kw in ["ma tran", "confusion matrix"]):
            return (
                "```python\n"
                "from sklearn.metrics import ConfusionMatrixDisplay, confusion_matrix\n"
                "import matplotlib.pyplot as plt\n\n"
                "y_true = [0, 1, 1, 0, 1, 0]\n"
                "y_pred = [0, 1, 0, 0, 1, 1]\n\n"
                "cm = confusion_matrix(y_true, y_pred)\n"
                "disp = ConfusionMatrixDisplay(confusion_matrix=cm)\n"
                "disp.plot(cmap='Blues')\n"
                "plt.title('Confusion Matrix')\n"
                "plt.show()\n"
                "```\n\n"
                "*Thông tin này được mở rộng từ kiến thức thực tế, không nằm trong giáo trình chính thức.*"
            )
        if any(kw in q_norm for kw in ["accuracy", "precision", "recall", "f1"]):
            return (
                "```python\n"
                "from sklearn.metrics import accuracy_score, precision_score, recall_score, f1_score\n\n"
                "y_true = [0, 1, 1, 0, 1, 0]\n"
                "y_pred = [0, 1, 0, 0, 1, 1]\n\n"
                "print('Accuracy:', accuracy_score(y_true, y_pred))\n"
                "print('Precision:', precision_score(y_true, y_pred))\n"
                "print('Recall:', recall_score(y_true, y_pred))\n"
                "print('F1:', f1_score(y_true, y_pred))\n"
                "```\n\n"
                "*Thông tin này được mở rộng từ kiến thức thực tế, không nằm trong giáo trình chính thức.*"
            )
        if any(kw in q_norm for kw in ["csv", "dataset", "cot so", "du lieu"]):
            return (
                "```python\n"
                "import pandas as pd\n\n"
                "df = pd.read_csv('data.csv')\n"
                "numeric_df = df.select_dtypes(include='number')\n\n"
                "print('Số dòng, số cột:', df.shape)\n"
                "print('\\nThống kê mô tả:')\n"
                "print(numeric_df.describe())\n"
                "print('\\nSố giá trị thiếu mỗi cột:')\n"
                "print(df.isna().sum())\n"
                "print('\\nTương quan giữa các cột số:')\n"
                "print(numeric_df.corr())\n"
                "```\n\n"
                "Nhận xét nên tập trung vào: cột có missing values, cột có độ lệch chuẩn cao, ngoại lai, và các cặp biến có tương quan mạnh.\n\n"
                "*Thông tin này được mở rộng từ kiến thức thực tế, không nằm trong giáo trình chính thức.*"
            )

    if any(kw in q_lower for kw in ["quiz", "trắc nghiệm", "trac nghiem", "câu quiz", "cau quiz", "câu hỏi ôn tập", "cau hoi on tap"]) or any(kw in q_norm for kw in ["quiz", "trac nghiem", "cau quiz", "cau hoi on tap"]):
        quiz_topic = detect_quiz_topic(question)
        if quiz_topic:
            num_match = re.search(r"(\d+)\s*c(?:âu|au)", question.lower())
            num_q = int(num_match.group(1)) if num_match else 5
            return format_offline_quiz(quiz_topic, min(num_q, 5))

    if any(kw in q_norm for kw in ["k-means", "kmeans", "k means"]) and any(
        kw in q_norm for kw in ["ngoai lai", "outlier", "outliers", "nhay cam"]
    ):
        return (
            "K-Means nhạy cảm với ngoại lai vì tâm cụm (centroid) được tính bằng **giá trị trung bình** của các điểm trong cụm.\n\n"
            "Nếu có một điểm nằm rất xa phần lớn dữ liệu, điểm đó sẽ kéo centroid lệch khỏi vị trí đại diện thật của cụm. Khi centroid bị lệch, các điểm gần ranh giới có thể bị gán sai cụm, làm kết quả phân cụm kém ổn định.\n\n"
            "Ví dụ: một cụm thu nhập quanh 8-12 triệu nhưng xuất hiện một bản ghi 500 triệu. Vì K-Means dùng trung bình, centroid của cụm sẽ bị kéo lên mạnh, dù phần lớn người trong cụm không có thu nhập như vậy.\n\n"
            "Cách giảm ảnh hưởng: phát hiện/xử lý outlier trước khi chạy K-Means, chuẩn hóa dữ liệu phù hợp, hoặc dùng thuật toán ít nhạy với ngoại lai hơn như DBSCAN/K-Medoids."
        )

    compares_core_clustering = (
        any(kw in q_norm for kw in ["so sanh", "compare", "khac nhau"])
        and any(kw in q_norm for kw in ["k-means", "kmeans", "k means"])
        and "dbscan" in q_norm
        and any(kw in q_norm for kw in ["hierarchical", "phan cap", "hierarchical clustering"])
    )
    if compares_core_clustering:
        return (
            "### So sánh K-Means, DBSCAN và Hierarchical Clustering\n\n"
            "| Tiêu chí | K-Means | DBSCAN | Hierarchical Clustering |\n"
            "|---|---|---|---|\n"
            "| Ý tưởng chính | Chia dữ liệu thành K cụm quanh các tâm cụm | Gom cụm theo vùng có mật độ điểm cao | Xây cây phân cấp cụm bằng cách gộp hoặc tách dần |\n"
            "| Loại phương pháp | Phân hoạch | Dựa trên mật độ | Phân cấp |\n"
            "| Cần biết số cụm trước? | Có, phải chọn K | Không | Không bắt buộc, có thể cắt cây dendrogram |\n"
            "| Hình dạng cụm phù hợp | Cụm gần tròn/lồi, kích thước tương đối đều | Cụm hình dạng bất kỳ | Linh hoạt, phụ thuộc linkage/distance |\n"
            "| Ngoại lai/nhiễu | Nhạy cảm với ngoại lai vì dùng trung bình | Xử lý tốt hơn, có thể đánh dấu noise | Có thể bị ảnh hưởng tùy cách đo khoảng cách |\n"
            "| Tham số quan trọng | K, cách khởi tạo centroid | eps, min_samples/minPts | distance metric, linkage, ngưỡng cắt cây |\n"
            "| Ưu điểm | Nhanh, dễ hiểu, dễ triển khai | Không cần K, phát hiện nhiễu tốt | Cho thấy cấu trúc phân cấp của dữ liệu |\n"
            "| Hạn chế | Khó chọn K, nhạy với outlier, kém với cụm phi cầu | Nhạy với eps/minPts, khó khi mật độ cụm thay đổi | Tốn chi phí hơn với dữ liệu lớn |\n\n"
            "Nói ngắn gọn: dùng **K-Means** khi dữ liệu có cụm khá tròn và bạn biết trước số cụm; dùng **DBSCAN** khi muốn phát hiện cụm hình dạng bất kỳ và loại nhiễu; dùng **Hierarchical Clustering** khi muốn quan sát quan hệ phân cấp giữa các cụm."
        )

    if any(kw in q_norm for kw in ["bagging", "boosting"]) and any(kw in q_norm for kw in ["metacost", "meta cost"]):
        return (
            "### Bagging và Boosting khác nhau thế nào về cơ chế dự đoán?\n\n"
            "| Tiêu chí | Bagging | Boosting |\n"
            "|---|---|---|\n"
            "| Cách xây mô hình | Huấn luyện nhiều mô hình con trên các mẫu bootstrap khác nhau | Huấn luyện tuần tự, mô hình sau tập trung hơn vào các mẫu bị mô hình trước dự đoán sai |\n"
            "| Quan hệ giữa mô hình con | Tương đối độc lập, có thể huấn luyện song song | Phụ thuộc tuần tự |\n"
            "| Cách dự đoán | Gộp kết quả bằng bỏ phiếu đa số hoặc trung bình | Gộp theo trọng số, mô hình tốt hơn có ảnh hưởng lớn hơn |\n"
            "| Mục tiêu chính | Giảm phương sai, làm mô hình ổn định hơn | Giảm sai lệch và tăng khả năng học các mẫu khó |\n\n"
            "### MetaCost kết hợp với Bagging để giải quyết vấn đề gì?\n\n"
            "MetaCost dùng Bagging để tạo nhiều mô hình dự đoán, sau đó ước lượng xác suất lớp cho từng mẫu và gán lại nhãn sao cho giảm **chi phí phân loại sai**. Vì vậy, MetaCost hướng tới bài toán **phân lớp nhạy cảm chi phí**: các lỗi khác nhau không có mức độ nghiêm trọng như nhau.\n\n"
            "Ví dụ: trong phát hiện gian lận, dự đoán nhầm giao dịch gian lận thành bình thường thường tốn kém hơn dự đoán nhầm giao dịch bình thường thành nghi ngờ."
        )

    offline = get_offline_explanation(question)
    if offline:
        return offline + "\n\n*Ghi chú: Câu trả lời này dùng kiến thức gia sư nội bộ, không phải trích dẫn trực tiếp từ tài liệu.*"

    if any(kw in q_lower for kw in ["khai phá dữ liệu là gì", "khai pha du lieu la gi", "khác gì với học máy", "khac gi voi hoc may"]) or any(kw in q_norm for kw in ["khai pha du lieu la gi", "khac gi voi hoc may", "data mining la gi"]):
        return (
            "### Khai phá dữ liệu là gì?\n\n"
            "**Khai phá dữ liệu (Data Mining)** là quá trình tìm ra mẫu, quy luật, xu hướng hoặc tri thức hữu ích từ dữ liệu lớn.\n\n"
            "**Khác với học máy:**\n"
            "| Tiêu chí | Khai phá dữ liệu | Học máy |\n"
            "|---|---|---|\n"
            "| Mục tiêu | Khám phá tri thức, mẫu ẩn, quan hệ trong dữ liệu | Xây mô hình dự đoán hoặc ra quyết định |\n"
            "| Đầu ra | Luật, cụm, mẫu phổ biến, nhận xét | Mô hình phân lớp, hồi quy, phân cụm, dự báo |\n"
            "| Phạm vi | Rộng hơn, gồm thu thập, tiền xử lý, khai phá, đánh giá | Là một nhóm kỹ thuật thường được dùng trong khai phá dữ liệu |\n\n"
            "Nói ngắn gọn: **học máy là công cụ**, còn **khai phá dữ liệu là quy trình tìm tri thức từ dữ liệu**."
        )

    if any(kw in q_lower for kw in ["quy trình kdd", "kdd gồm", "kdd gom", "kdd"]) or any(kw in q_norm for kw in ["quy trinh kdd", "kdd gom", "kdd"]):
        return (
            "### Quy trình KDD gồm những bước nào?\n\n"
            "1. **Selection:** Chọn dữ liệu liên quan đến bài toán.\n"
            "2. **Preprocessing:** Làm sạch dữ liệu, xử lý thiếu, nhiễu, trùng lặp.\n"
            "3. **Transformation:** Biến đổi dữ liệu, chuẩn hóa, rút trích đặc trưng.\n"
            "4. **Data Mining:** Áp dụng thuật toán để tìm mẫu hoặc mô hình.\n"
            "5. **Interpretation/Evaluation:** Đánh giá, diễn giải và chọn tri thức hữu ích.\n\n"
            "Dễ nhớ: **Chọn dữ liệu → Làm sạch → Biến đổi → Khai phá → Đánh giá tri thức**."
        )

    if any(kw in q_lower for kw in ["nhiễu dữ liệu", "nhieu du lieu", "noise", "dữ liệu nhiễu", "du lieu nhieu"]) or any(kw in q_norm for kw in ["nhieu du lieu", "du lieu nhieu", "noise"]):
        return (
            "### Nhiễu dữ liệu là gì?\n\n"
            "**Nhiễu dữ liệu** là giá trị sai lệch, bất thường hoặc không phản ánh đúng thực tế, làm mô hình học sai.\n\n"
            "**Ví dụ thực tế:**\n"
            "- Tuổi sinh viên nhập là `250`.\n"
            "- Cột điểm có giá trị `-3` hoặc `15` trong thang điểm 10.\n"
            "- Cảm biến nhiệt độ ghi `999°C` do lỗi thiết bị.\n\n"
            "**Cách xử lý:** kiểm tra miền giá trị hợp lệ, phát hiện ngoại lai, làm mượt dữ liệu, sửa bằng luật nghiệp vụ hoặc loại bỏ bản ghi lỗi."
        )

    if any(kw in q_lower for kw in ["so sánh phân lớp và phân cụm", "so sanh phan lop va phan cum", "phân lớp và phân cụm", "phan lop va phan cum"]) or any(kw in q_norm for kw in ["so sanh phan lop va phan cum", "phan lop va phan cum"]):
        return (
            "| Tiêu chí | Phân lớp (Classification) | Phân cụm (Clustering) |\n"
            "|---|---|---|\n"
            "| Loại học | Có giám sát | Không giám sát |\n"
            "| Dữ liệu huấn luyện | Có nhãn lớp | Không có nhãn |\n"
            "| Mục tiêu | Dự đoán lớp của mẫu mới | Tìm nhóm tự nhiên trong dữ liệu |\n"
            "| Ví dụ | Dự đoán email spam/không spam | Nhóm khách hàng theo hành vi mua sắm |\n"
            "| Thuật toán | Decision Tree, KNN, Naive Bayes, SVM | K-Means, DBSCAN, Hierarchical Clustering |"
        )

    if any(kw in q_lower for kw in ["ví dụ giỏ hàng", "vi du gio hang", "apriori từng bước", "apriori tung buoc"]) or any(kw in q_norm for kw in ["vi du gio hang", "apriori tung buoc"]):
        return (
            "### Apriori từng bước với ví dụ giỏ hàng\n\n"
            "Giả sử có các giao dịch:\n"
            "- T1: Sữa, Bánh mì, Bơ\n"
            "- T2: Sữa, Bánh mì\n"
            "- T3: Sữa, Bơ\n"
            "- T4: Bánh mì, Bơ\n\n"
            "Các bước Apriori:\n"
            "1. Đếm từng item đơn lẻ để tìm item phổ biến.\n"
            "2. Ghép các item phổ biến thành cặp 2-itemset.\n"
            "3. Loại các cặp không đạt min_support.\n"
            "4. Sinh luật dạng `{A} -> {B}`.\n"
            "5. Tính confidence và lift để chọn luật mạnh.\n\n"
            "Ví dụ luật: `{Sữa} -> {Bánh mì}` nghĩa là người mua Sữa thường có xu hướng mua thêm Bánh mì."
        )

    if any(kw in q_lower for kw in ["accuracy hay f1", "mất cân bằng lớp", "mat can bang lop", "imbalanced"]) or any(kw in q_norm for kw in ["accuracy hay f1", "mat can bang lop", "imbalanced"]):
        return (
            "Khi dữ liệu **mất cân bằng lớp**, không nên chỉ dựa vào accuracy vì mô hình có thể đoán toàn bộ là lớp đa số mà vẫn đạt điểm cao.\n\n"
            "Ví dụ: 95% giao dịch là bình thường, 5% là gian lận. Mô hình luôn đoán 'bình thường' sẽ đạt 95% accuracy nhưng không phát hiện gian lận nào.\n\n"
            "Nên dùng thêm:\n"
            "- **Precision:** dự đoán dương tính có đúng không.\n"
            "- **Recall:** bắt được bao nhiêu trường hợp dương tính thật.\n"
            "- **F1-score:** cân bằng giữa precision và recall.\n\n"
            "Nếu lớp thiểu số quan trọng, **F1-score/Recall thường hữu ích hơn accuracy**."
        )

    if any(kw in q_norm for kw in ["k-means", "kmeans", "k means"]) and any(
        kw in q_norm for kw in ["ngoai lai", "outlier", "outliers", "nhay cam"]
    ):
        return (
            "K-Means nhạy cảm với ngoại lai vì tâm cụm (centroid) được tính bằng **giá trị trung bình** của các điểm trong cụm.\n\n"
            "Nếu có một điểm nằm rất xa phần lớn dữ liệu, điểm đó sẽ kéo centroid lệch khỏi vị trí đại diện thật của cụm. Khi centroid bị lệch, các điểm gần ranh giới có thể bị gán sai cụm, làm kết quả phân cụm kém ổn định.\n\n"
            "Ví dụ: một cụm thu nhập quanh 8-12 triệu nhưng xuất hiện một bản ghi 500 triệu. Vì K-Means dùng trung bình, centroid của cụm sẽ bị kéo lên mạnh, dù phần lớn người trong cụm không có thu nhập như vậy.\n\n"
            "Cách giảm ảnh hưởng: phát hiện/xử lý outlier trước khi chạy K-Means, chuẩn hóa dữ liệu phù hợp, hoặc dùng thuật toán ít nhạy với ngoại lai hơn như DBSCAN/K-Medoids."
        )

    if any(kw in q_lower for kw in ["cross-encoder", "reranking", "rerank"]) or any(kw in q_norm for kw in ["cross encoder", "reranking", "rerank"]):
        return (
            "### Cross-encoder reranking giúp cải thiện RAG thế nào?\n\n"
            "Trong RAG, bước retrieval đầu tiên thường lấy nhiều đoạn có vẻ liên quan. Tuy nhiên không phải đoạn nào cũng thật sự trả lời đúng câu hỏi.\n\n"
            "**Cross-encoder reranking** đọc đồng thời cặp `(câu hỏi, đoạn tài liệu)` và chấm lại mức liên quan chi tiết hơn. Nhờ vậy hệ thống:\n"
            "- Đưa đoạn đúng nhất lên đầu.\n"
            "- Giảm khả năng đưa context nhiễu vào LLM.\n"
            "- Tăng chất lượng trích dẫn.\n"
            "- Giảm hallucination vì câu trả lời dựa trên context phù hợp hơn."
        )

    if any(kw in q_lower for kw in ["code python", "scikit-learn", "sklearn", "missing values", "ma trận nhầm lẫn", "confusion matrix", "precision", "recall", "f1-score"]) or any(kw in q_norm for kw in ["code python", "scikit learn", "sklearn", "missing values", "ma tran nham lan", "confusion matrix", "precision", "recall", "f1 score"]):
        if "ma trận" in q_lower or "confusion matrix" in q_lower or "ma tran" in q_norm:
            return (
                "```python\n"
                "from sklearn.metrics import ConfusionMatrixDisplay, confusion_matrix\n"
                "import matplotlib.pyplot as plt\n\n"
                "y_true = [0, 1, 1, 0, 1, 0]\n"
                "y_pred = [0, 1, 0, 0, 1, 1]\n\n"
                "cm = confusion_matrix(y_true, y_pred)\n"
                "disp = ConfusionMatrixDisplay(confusion_matrix=cm)\n"
                "disp.plot(cmap='Blues')\n"
                "plt.title('Confusion Matrix')\n"
                "plt.show()\n"
                "```"
            )
        if "precision" in q_lower or "recall" in q_lower or "f1" in q_lower:
            return (
                "```python\n"
                "from sklearn.metrics import accuracy_score, precision_score, recall_score, f1_score\n\n"
                "y_true = [0, 1, 1, 0, 1, 0]\n"
                "y_pred = [0, 1, 0, 0, 1, 1]\n\n"
                "print('Accuracy:', accuracy_score(y_true, y_pred))\n"
                "print('Precision:', precision_score(y_true, y_pred))\n"
                "print('Recall:', recall_score(y_true, y_pred))\n"
                "print('F1:', f1_score(y_true, y_pred))\n"
                "```"
            )
        if "missing" in q_lower or "thiếu" in q_lower or "thieu" in q_lower or "thieu" in q_norm:
            return (
                "```python\n"
                "import pandas as pd\n"
                "from sklearn.impute import SimpleImputer\n\n"
                "df = pd.DataFrame({\n"
                "    'age': [20, 21, None, 23],\n"
                "    'score': [8.0, None, 7.5, 9.0]\n"
                "})\n\n"
                "imputer = SimpleImputer(strategy='mean')\n"
                "df[['age', 'score']] = imputer.fit_transform(df[['age', 'score']])\n"
                "print(df)\n"
                "```"
            )

    if any(kw in q_lower for kw in ["gợi ý chủ đề", "goi y chu de", "ôn tiếp", "on tiep"]) or any(kw in q_norm for kw in ["goi y chu de", "on tiep"]):
        return (
            "Mình gợi ý bạn ôn theo thứ tự sau:\n\n"
            "1. **Tiền xử lý dữ liệu**: missing values, normalization, noise, outlier.\n"
            "2. **Phân lớp**: Decision Tree, Information Gain, đánh giá mô hình.\n"
            "3. **Phân cụm**: K-Means, DBSCAN, chọn số cụm.\n"
            "4. **Luật kết hợp**: Apriori, support, confidence, lift.\n\n"
            "Nếu bạn vừa trả lời sai một câu, hãy gửi lại câu đó và đáp án của bạn, mình sẽ phân tích vì sao sai."
        )

    return None


def generate_tutor_llm_response(question: str, intent: str) -> Optional[str]:
    """
    Last-resort world-knowledge tutor response for Data Mining / CS questions.
    It is transparent by design: it tells students this is outside the official
    retrieved course documents.
    """
    try:
        temp = 0.65 if intent == "pedagogical" else 0.45
        llm = get_llm(task_type="tutor", temperature=temp)
        role_hint = (
            "một gia sư Khai phá dữ liệu giàu tính sư phạm"
            if intent == "pedagogical"
            else "một lập trình viên Python/Data Science"
        )
        prompt = f"""Bạn là {role_hint} cho sinh viên đại học.

Nhiệm vụ:
- Trả lời bằng tiếng Việt, rõ ràng, đúng chuyên môn.
- Nếu câu hỏi cần giải thích, hãy dùng ví dụ dễ hiểu.
- Nếu câu hỏi yêu cầu code, hãy đưa code Python chạy được và giải thích ngắn.
- Không bịa rằng thông tin đến từ giáo trình hoặc slide.
- BẮT BUỘC thêm dòng sau ở cuối câu trả lời:
"Thông tin này được mở rộng từ kiến thức thực tế, không nằm trong giáo trình chính thức."

Câu hỏi của sinh viên:
{question}

Trả lời:"""
        response = llm.invoke(prompt)
        text = getattr(response, "content", str(response))
        if hasattr(text, "text"):
            text = text.text
        text = str(text).strip()
        if not text:
            return None
        disclosure = "Thông tin này được mở rộng từ kiến thức thực tế, không nằm trong giáo trình chính thức."
        if disclosure not in text:
            text += f"\n\n*{disclosure}*"
        return text
    except Exception as e:
        print(f"[IntentRouter] Tutor LLM fallback unavailable: {e}")
        return None


def ensure_world_knowledge_disclosure(text: str) -> str:
    disclosure = "Thông tin này được mở rộng từ kiến thức thực tế, không nằm trong giáo trình chính thức."
    if not text or disclosure in text:
        return text
    return text.rstrip() + f"\n\n*{disclosure}*"


def build_extractive_answer_from_sources(question: str, source_docs: List[Any], max_docs: int = 3) -> str:
    """
    Quota-safe fallback: answer only by quoting/paraphrasing retrieved snippets.
    No LLM call, no external knowledge.
    """
    if not source_docs:
        return (
            "Tôi chưa tìm được đoạn tài liệu phù hợp để trả lời câu hỏi này. "
            "Hiện Gemini cũng đang hết quota nên tôi không thể sinh câu trả lời mở rộng."
        )

    lines = [
        "Tôi đã tìm được tài liệu liên quan, nhưng Gemini hiện đang hết quota nên chưa thể tổng hợp thành câu trả lời đầy đủ.",
        "Dưới đây là các đoạn căn cứ trực tiếp từ tài liệu để bạn kiểm tra trước:",
        "",
    ]

    for idx, doc in enumerate(source_docs[:max_docs], 1):
        meta = getattr(doc, "metadata", {}) or {}
        src = clean_source_filename(meta.get("source_file") or meta.get("source") or f"Tài liệu {idx}")
        page = meta.get("page_number") or meta.get("page") or meta.get("slide") or ""
        location = f", trang/slide {page}" if page else ""
        content = re.sub(r"\s+", " ", getattr(doc, "page_content", "")).strip()
        snippet = content[:700].rstrip()
        if len(content) > 700:
            snippet += "..."
        lines.append(f"[{idx}] **{src}{location}**")
        lines.append(f"> {snippet}")
        lines.append("")

    lines.append(
        "*Ghi chú: Đây là chế độ trích xuất tài liệu khi API sinh câu trả lời bị hết quota; "
        "nội dung không dùng kiến thức ngoài giáo trình.*"
    )
    return "\n".join(lines).strip()


def get_offline_explanation(question: str) -> Optional[str]:
    """
    Trả về câu trả lời chi tiết ngoại tuyến dựa trên từ khóa khái niệm dữ liệu lớn
    """
    q_lower = question.lower()
    q_norm = normalize_query_text(question)

    if any(kw in q_lower for kw in ["so sánh phân lớp và phân cụm", "so sanh phan lop va phan cum", "phân lớp và phân cụm", "phan lop va phan cum"]):
        return (
            "| Tiêu chí | Phân lớp (Classification) | Phân cụm (Clustering) |\n"
            "|---|---|---|\n"
            "| Kiểu học | Học có giám sát (supervised learning) | Học không giám sát (unsupervised learning) |\n"
            "| Dữ liệu huấn luyện | Có nhãn lớp (class labels) | Không biết trước nhãn lớp |\n"
            "| Mục tiêu | Dự đoán nhãn/lớp cho mẫu mới | Tìm các nhóm/cụm tự nhiên trong dữ liệu |\n"
            "| Ví dụ thuật toán | Decision Tree, Naive Bayes, KNN, SVM | K-Means, DBSCAN, Hierarchical Clustering |"
        )
    
    # 1. K-Means & Phân cụm nói chung
    if any(kw in q_lower for kw in ["k-means", "kmeans", "phân cụm", "phan cum", "clustering", "agnes", "diana", "silhouette"]):
        # Trừ phi hỏi về DBSCAN cụ thể
        if "dbscan" in q_lower:
            return None
        return (
            r"""### 📂 Thuật toán Phân cụm K-Means (K-Means Clustering)

**K-Means** là thuật toán học máy không giám sát (unsupervised learning) được sử dụng để phân nhóm dữ liệu vào $K$ cụm dựa trên khoảng cách. [1]

#### Các bước thực hiện chính: [2]
1. **Khởi tạo:** Chọn ngẫu nhiên $K$ điểm làm tâm cụm ban đầu (centroids).
2. **Gán cụm:** Tính toán khoảng cách (Euclidean) từ mỗi điểm đến $K$ centroids. Gán điểm đó vào cụm có centroid gần nhất.
3. **Cập nhật centroid:** Tính lại vị trí centroid bằng trung bình cộng tọa độ tất cả các điểm trong cụm đó.
4. **Lặp lại:** Lặp lại bước 2 và 3 cho đến khi các centroid không còn thay đổi đáng kể hoặc đạt số vòng lặp tối đa.

#### Cách chọn số cụm $K$ tối ưu: [3]
- **Elbow Method (Phương pháp khuỷu tay):** Vẽ đồ thị WCSS (Within-Cluster Sum of Squares) tương ứng với các giá trị $K$. Chọn điểm $K$ tại vị trí đường cong giảm chậm dần (hình dạng khuỷu tay).
- **Silhouette Score:** Đánh giá chất lượng phân cụm thông qua mức độ gắn kết bên trong cụm (cohesion) so với khoảng cách đến cụm láng giềng gần nhất (separation). Điểm càng gần 1 càng tốt.

#### Ví dụ Code Python đơn giản: [1]
```python
from sklearn.cluster import KMeans
import numpy as np

# Khởi tạo dữ liệu mẫu
X = np.array([[1, 2], [1, 4], [1, 0], [10, 2], [10, 4], [10, 0]])

# Chạy K-Means với K=2
kmeans = KMeans(n_clusters=2, random_state=0).fit(X)
print("Nhãn phân cụm:", kmeans.labels_)
```"""
        )
        
    # 2. DBSCAN
    elif "dbscan" in q_lower:
        return (
            r"""### 🔍 Phân cụm dựa trên mật độ DBSCAN

**DBSCAN** (Density-Based Spatial Clustering of Applications with Noise) là thuật toán phân cụm dựa trên mật độ. Khác với K-Means, DBSCAN không cần biết trước số lượng cụm, có thể tìm các cụm có hình dạng bất kỳ và tự động phát hiện nhiễu (outliers). [1]

#### Hai tham số cực kỳ quan trọng: [2]
- **Epsilon ($\epsilon$):** Bán kính lân cận xung quanh một điểm dữ liệu.
- **MinPts:** Số điểm tối thiểu trong vùng bán kính $\epsilon$ để xác định mật độ.

#### Phân loại điểm dữ liệu:
1. **Core Point (Điểm lõi):** Có ít nhất `MinPts` điểm lân cận trong bán kính $\epsilon$.
2. **Border Point (Điểm biên):** Có ít hơn `MinPts` điểm lân cận, nhưng nằm trong bán kính $\epsilon$ của một điểm lõi.
3. **Noise Point (Nhiễu):** Không phải điểm lõi cũng không phải điểm biên."""
        )
        
    # 3. Apriori
    elif "apriori" in q_lower:
        return (
            r"""### 🛒 Thuật toán Apriori (Khai phá luật kết hợp)

**Apriori** là thuật toán kinh điển được dùng để khai thác các tập mục phổ biến (frequent itemsets) và sinh luật kết hợp mạnh (strong association rules) trong cơ sở dữ liệu giao dịch thương mại. [1]

#### 3 Chỉ số quan trọng nhất: [2]
- **Support (Độ hỗ trợ):** Tỷ lệ giao dịch chứa tập mục trên tổng số giao dịch.
  $$\text{Support}(A) = \frac{\text{Số giao dịch chứa } A}{\text{Tổng số giao dịch}}$$
- **Confidence (Độ tin cậy):** Khả năng người dùng mua sản phẩm B sau khi đã mua sản phẩm A.
  $$\text{Confidence}(A \rightarrow B) = \frac{\text{Support}(A \cup B)}{\text{Support}(A)}$$
- **Lift (Hệ số tăng cường):** Chỉ ra mức độ tương quan giữa A và B. Lift > 1 thể hiện tương quan dương mạnh.
  $$\text{Lift}(A \rightarrow B) = \frac{\text{Support}(A \cup B)}{\text{Support}(A) \times \text{Support}(B)}$$

#### Nguyên lý cắt tỉa (Apriori Property): [3]
Mọi tập con của tập mục phổ biến cũng bắt buộc phải phổ biến. Ngược lại, nếu tập mục không phổ biến, thì tất cả các siêu tập chứa nó cũng chắc chắn không phổ biến (cho phép cắt tỉa sớm không gian tìm kiếm)."""
        )
        
    # 4. FP-Growth
    elif any(kw in q_lower for kw in ["fp-growth", "fpgrowth", "fp tree", "fptree", "frequent pattern"]):
        return (
            r"""### 🌳 Thuật toán FP-Growth và Cây FP-Tree

**FP-Growth** (Frequent Pattern Growth) là thuật toán khai phá tập phổ biến khắc phục hai nhược điểm lớn nhất của Apriori (phải quét cơ sở dữ liệu nhiều lần và sinh ra quá nhiều ứng viên trung gian). [1]

#### Điểm khác biệt cốt lõi: [2]
1. **Cấu trúc cây FP-Tree:** FP-Growth nén cơ sở dữ liệu giao dịch vào cây FP-Tree gọn nhẹ. Chỉ cần quét cơ sở dữ liệu đúng **2 lần**.
2. **Khai thác đệ quy:** Thay vì sinh ứng viên và đếm tần suất như Apriori, FP-Growth chia cây FP-Tree thành các cơ sở dữ liệu mẫu có điều kiện (conditional pattern bases) và khai thác trực tiếp. [3]"""
        )
        
    # 5. Tiền xử lý dữ liệu
    elif any(kw in q_lower for kw in ["tiền xử lý", "tien xu ly", "preprocessing", "làm sạch", "lam sach", "missing value", "chuẩn hóa", "chuan hoa", "normalization", "pca"]) or any(
        kw in q_norm for kw in ["tien xu ly", "ti n x l", "preprocessing", "lam sach", "missing value", "chuan hoa", "normalization", "pca"]
    ):
        return (
            r"""### 🛠️ Tiền xử lý dữ liệu (Data Preprocessing)

Tiền xử lý là bước cốt lõi trong KDD nhằm làm sạch dữ liệu nhiễu và chuẩn bị định dạng tốt nhất cho mô hình học máy. [1]

#### 1. Xử lý giá trị khuyết (Missing Values): [2]
- **Loại bỏ (Deletion):** Xóa dòng chứa giá trị trống nếu tỷ lệ nhỏ.
- **Điền khuyết (Imputation):** Điền bằng giá trị thống kê (Mean/Median cho dữ liệu số, Mode cho phân loại) hoặc dùng thuật toán dự báo (KNN Imputation, Regression).

#### 2. Chuẩn hóa dữ liệu (Normalization): [3]
- **Min-Max Normalization:** Ánh xạ dữ liệu về khoảng $[0, 1]$.
  $$x' = \frac{x - \text{min}}{\text{max} - \text{min}}$$
- **Z-Score Standardization:** Chuẩn hóa dữ liệu về phân phối có trung bình bằng 0 và độ lệch chuẩn bằng 1.
  $$x' = \frac{x - \mu}{\sigma}$$

#### 3. Giảm chiều dữ liệu (Dimensionality Reduction): [1]
Sử dụng phân tích thành phần chính **PCA** hoặc lựa chọn đặc trưng (Feature Selection) nhằm giảm số chiều dữ liệu bị thừa nhiễu."""
        )
        
    # 6a. Overfitting & Pruning trong Decision Tree (PHẢI đặt TRƯỚC phân lớp chung)
    elif any(kw in q_lower for kw in [
        "overfitting", "quá khớp", "học vẹt", "pruning", "cắt tỉa", "cat tia",
        "pre-pruning", "post-pruning", "cắt tỉa trước", "cắt tỉa sau",
        "tinh giản", "tỉa cây"
    ]):
        return (
            r"""### 🌿 Overfitting và Pruning trong Cây Quyết Định

#### 1. Hiện tượng Overfitting (Quá khớp / Học vẹt)

**Overfitting** xảy ra khi mô hình cây quyết định học quá chi tiết các đặc điểm và nhiễu của tập dữ liệu huấn luyện, dẫn đến hiệu suất kém trên dữ liệu mới (tập kiểm tra). [1]

- Cây quyết định có xu hướng tăng trưởng đến khi **thuần nhất hoàn toàn** (pure leaves), làm cây trở nên quá sâu và phức tạp.
- Cây phù hợp tốt với dữ liệu huấn luyện nhưng **không tổng quát hóa** được ra dữ liệu mới.
- Biểu hiện: **Training accuracy cao** nhưng **Test accuracy thấp**. [2]

#### 2. Hai phương pháp cắt tỉa (Pruning) để giải quyết Overfitting:

##### a) Cắt tỉa trước (Pre-pruning / Early Stopping) [1]
Dừng quá trình xây dựng cây **trước khi** nó trở nên quá phức tạp bằng các tiêu chí dừng sớm:
- Giới hạn **độ sâu tối đa** của cây (`max_depth`)
- Yêu cầu **số mẫu tối thiểu** để chia một nút (`min_samples_split`)
- Chỉ tiếp tục chia nếu **Information Gain** đủ lớn (vượt ngưỡng)
- **Ưu điểm:** Nhanh hơn, đơn giản hơn | **Nhược điểm:** Có thể dừng quá sớm (underfitting)

##### b) Cắt tỉa sau (Post-pruning / Reduced Error Pruning) [2][3]
Xây dựng cây đầy đủ trước, sau đó **loại bỏ nhánh** không cần thiết từ lá lên gốc:
- **Reduced Error Pruning:** Cắt bỏ nút nếu thay bằng lá không làm tăng lỗi trên tập validation.
- **Cost-Complexity Pruning (CCP):** Tối ưu hóa cân bằng giữa độ chính xác và độ phức tạp của cây.
- **Ưu điểm:** Kết quả tốt hơn | **Nhược điểm:** Tốn thời gian hơn (cần tập validation riêng)"""
        )

    # 6b. Phân lớp dữ liệu (Classification) - chung chung
    elif any(kw in q_lower for kw in [
        "phân lớp", "phan lop", "classification", "cây quyết định", "decision tree", 
        "knn", "k láng giềng", "k láng giêng", "k lán giềng", "k lân cận", "láng giềng", "lân cận",
        "bayes ngây thơ", "bayes thơ nggaya", "naive bayes", "svm", 
        "máy học vector hỗ trợ", "máy học vector hộ trợ", "rừng ngẫu nhiên", "random forest"
    ]):
        return (
            r"""### 🎯 Thuật toán Phân lớp dữ liệu (Classification)

Phân lớp dữ liệu là bài toán học có giám sát (supervised learning) nhằm dự đoán nhãn lớp của dữ liệu mới dựa trên tập dữ liệu huấn luyện đã gán nhãn. [1]

#### Các thuật toán phổ biến:
1. **Cây quyết định (Decision Tree):** Sử dụng các tiêu chí như Entropy & Information Gain (ID3) hoặc Gini Index (CART) để xác định thuộc tính phân tách tại mỗi nút. [2]
2. **K-Láng giềng gần nhất (KNN):** Phân lớp điểm mới bằng cách lấy ý kiến số đông (majority vote) từ K điểm gần nhất. [3]
3. **Naive Bayes:** Dựa trên Định lý xác suất Bayes với giả thiết các thuộc tính độc lập có điều kiện với nhau. [1]
4. **SVM (Support Vector Machine):** Tìm siêu phẳng ranh giới phân tách lớp tối ưu sao cho khoảng cách biên (margin) là lớn nhất. [2]"""
        )

    # 7. Cây quyết định chi tiết (phải đặt TRƯỚC classification chung)
    elif any(kw in q_lower for kw in [
        "id3", "cart", "information gain", "entropy", "gini", "c4.5"
    ]):
        return (
            r"""### 🌳 Cây Quyết Định — Tiêu chí phân tách (Entropy, Gini, Information Gain)

#### Entropy và Information Gain (ID3):
$$\text{Entropy}(S) = -\sum_{i} p_i \log_2 p_i$$
$$\text{Information Gain}(A) = \text{Entropy}(S) - \sum_{v} \frac{|S_v|}{|S|} \cdot \text{Entropy}(S_v)$$
Thuộc tính có **Information Gain lớn nhất** được chọn làm nút phân tách. [1]

#### Gini Index (CART):
$$\text{Gini}(S) = 1 - \sum_{i} p_i^2$$
Chọn thuộc tính làm **Gini nhỏ nhất**. [2]

```python
from sklearn.tree import DecisionTreeClassifier
from sklearn.datasets import load_iris

X, y = load_iris(return_X_y=True)
clf = DecisionTreeClassifier(criterion='entropy', max_depth=3)
clf.fit(X, y)
print("Accuracy:", clf.score(X, y))
```"""
        )

    # 8. Naive Bayes chi tiết
    elif any(kw in q_lower for kw in [
        "naive bayes chi tiết", "định lý bayes", "dinh ly bayes",
        "xác suất có điều kiện", "gaussian naive", "xac suat"
    ]):
        return (
            r"""### 📊 Naive Bayes — Công thức chi tiết

**Định lý Bayes:**
$$P(C|X) = \frac{P(X|C) \cdot P(C)}{P(X)}$$

**Giả thiết độc lập có điều kiện (naive):**
$$P(X|C) = \prod_{i=1}^{n} P(x_i|C)$$

```python
from sklearn.naive_bayes import GaussianNB
from sklearn.datasets import load_iris
from sklearn.model_selection import train_test_split

X, y = load_iris(return_X_y=True)
X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.3)
clf = GaussianNB()
clf.fit(X_train, y_train)
print("Accuracy:", clf.score(X_test, y_test))
```""" )

    # 9. Parallel Coordinates / Trực quan hóa
    elif any(kw in q_lower for kw in [
        "parallel coordinates", "tọa độ song song", "toa do song song",
        "parallel_coordinates", "biểu đồ tọa độ", "trực quan hóa", "pandas plot"
    ]):
        return (
            r"""### 📈 Biểu đồ Tọa độ Song song với Pandas

**Hàm:** `pandas.plotting.parallel_coordinates(frame, class_column, ...)` [1]

```python
import pandas as pd
import matplotlib.pyplot as plt
from sklearn.datasets import load_iris
from pandas.plotting import parallel_coordinates

# Tải dữ liệu Iris
iris = load_iris()
df = pd.DataFrame(iris.data, columns=iris.feature_names)
df['Species'] = pd.Categorical.from_codes(iris.target, iris.target_names)

# Vẽ biểu đồ Tọa độ Song song
plt.figure(figsize=(10, 6))
parallel_coordinates(df, class_column='Species', colormap='Set2')
plt.title('Biểu đồ Tọa độ Song song - Iris')
plt.tight_layout()
plt.show()
```

**Cách đọc:** Mỗi đường = 1 mẫu; Màu sắc = nhãn lớp; Các trục dọc = các thuộc tính [2]""" )

    # 10. Chia tập Train/Test
    elif any(kw in q_lower for kw in [
        "train test split", "train_test_split", "chia tập", "chia du lieu", "chia dữ liệu",
        "tập huấn luyện", "tập kiểm tra", "tap huan luyen", "tap kiem tra",
        "cross validation", "cross-validation", "hold-out", "k-fold", "kfold"
    ]):
        return (
            r"""### ✂️ Chia tập Huấn luyện & Kiểm tra trong Python

**Hàm chính:** `sklearn.model_selection.train_test_split` [1]

#### Code mẫu — Hold-out 70/30:
```python
from sklearn.model_selection import train_test_split
from sklearn.datasets import load_iris

# Tải dữ liệu
X, y = load_iris(return_X_y=True)

# Chia 70% huấn luyện, 30% kiểm tra
X_train, X_test, y_train, y_test = train_test_split(
    X, y, 
    test_size=0.3,      # 30% dùng để test
    random_state=42,    # Cố định ngẫu nhiên để tái lập
    stratify=y          # Giữ tỷ lệ nhãn cân bằng
)

print(f"Tập huấn luyện: {X_train.shape}")  # (105, 4)
print(f"Tập kiểm tra:   {X_test.shape}")   # (45, 4)
```

#### Code mẫu — K-Fold Cross-Validation: [2]
```python
from sklearn.model_selection import cross_val_score
from sklearn.tree import DecisionTreeClassifier

clf = DecisionTreeClassifier()
scores = cross_val_score(clf, X, y, cv=5, scoring='accuracy')
print(f"Độ chính xác TB: {scores.mean():.4f} ± {scores.std():.4f}")
```

**So sánh phương pháp:** [3]
| | Hold-out 70/30 | K-Fold CV |
|---|---|---|
| Tốc độ | Nhanh | Chậm hơn |
| Ổn định | Phụ thuộc cách chia | Ổn định hơn |
| Dữ liệu nhỏ | Kém | Tốt hơn |"""
        )

    return None


def format_offline_syllabus(question: str) -> str:
    """
    Trả lời câu hỏi về đề cương từ OFFLINE_SYLLABUS_KNOWLEDGE
    """
    q_lower = question.lower()
    kb = OFFLINE_SYLLABUS_KNOWLEDGE
    
    # Xác định lớp nào (AI hay CNTT)
    is_ai = "ai" in q_lower or "trí tuệ nhân tạo" in q_lower
    is_cntt = "cntt" in q_lower or "công nghệ thông tin" in q_lower
    
    # Câu hỏi về nội dung bài học / chương
    if any(kw in q_lower for kw in ["nội dung", "noi dung", "bài", "bai", "chương", "chuong", "gồm", "gom", "các bài"]):
        result = "## 📚 Nội dung học phần Khai phá Dữ liệu (MSHP: 220269)\n\n"
        result += "Môn học gồm **5 bài** với tổng cộng **30 tiết lý thuyết + 30 tiết thực hành**:\n\n"
        for bai, info in kb["noi_dung_hoc_phan"].items():
            result += f"### {bai}. {info['ten']}\n"
            result += f"*Lý thuyết: {info['so_tiet_LT']} tiết | Thực hành: {info['so_tiet_TH']} tiết*\n\n"
            for noi_dung in info["noi_dung"]:
                result += f"- {noi_dung}\n"
            result += "\n"
        result += "\n*📖 Nguồn: Đề cương chi tiết học phần MSHP 220269 - Trường Đại học Trà Vinh*"
        return result

    # Câu hỏi về đánh giá / thi cử
    elif any(kw in q_lower for kw in ["đánh giá", "danh gia", "thi", "điểm", "diem", "tỷ lệ", "ty le", "trắc nghiệm cuối"]):
        result = "## 📊 Phương thức đánh giá học phần Khai phá Dữ liệu\n\n"
        for dg in kb["danh_gia_hoc_phan"]:
            result += f"- **{dg['hinh_thuc']}**: {dg['ti_le']} ({dg['loai']})\n"
        result += "\n> 💡 Bài thi cuối kỳ là **trắc nghiệm** bao gồm kiến thức từ Bài 1 đến Bài 5.\n"
        result += "\n*📖 Nguồn: Đề cương chi tiết học phần MSHP 220269 - Trường Đại học Trà Vinh*"
        return result
    
    # Câu hỏi về thông tin chung (ngành, học kỳ)
    elif any(kw in q_lower for kw in ["học kỳ", "hoc ky", "ngành", "nganh", "năm thứ", "nam thu", "thông tin", "thong tin"]):
        result = "## ℹ️ Thông tin học phần Khai phá Dữ liệu (MSHP: 220269)\n\n"
        result += "| Thông tin | Lớp AI | Lớp CNTT |\n"
        result += "|-----------|--------|----------|\n"
        result += f"| Ngành | {kb['thong_tin_chung']['AI']['nganh']} | {kb['thong_tin_chung']['CNTT']['nganh']} |\n"
        result += f"| Học kỳ | {kb['thong_tin_chung']['AI']['hoc_ky']} | {kb['thong_tin_chung']['CNTT']['hoc_ky']} |\n"
        result += f"| Năm thứ | {kb['thong_tin_chung']['AI']['nam_thu']} | {kb['thong_tin_chung']['CNTT']['nam_thu']} |\n\n"
        result += f"**Giảng viên:** {', '.join(kb['thong_tin_chung']['giang_vien'])}\n\n"
        result += f"**Mô tả:** {kb['mo_ta_hoc_phan']}\n"
        result += "\n*📖 Nguồn: Đề cương chi tiết học phần MSHP 220269 - Trường Đại học Trà Vinh*"
        return result
    
    # Câu hỏi về giảng viên
    elif any(kw in q_lower for kw in ["giảng viên", "giang vien", "giáo viên", "thầy", "cô"]):
        result = "## 👨‍🏫 Giảng viên phụ trách học phần\n\n"
        for gv in kb["thong_tin_chung"]["giang_vien"]:
            result += f"- {gv}\n"
        result += "\n*📖 Nguồn: Đề cương chi tiết học phần MSHP 220269 - Trường Đại học Trà Vinh*"
        return result
    
    # Câu hỏi về phương pháp giảng dạy
    elif any(kw in q_lower for kw in ["phương pháp", "phuong phap", "dạy", "day", "học"]):
        result = "## 🎓 Phương pháp dạy và học\n\n"
        for pp in kb["phuong_phap_giang_day"]:
            result += f"- {pp}\n"
        result += "\n*📖 Nguồn: Đề cương chi tiết học phần MSHP 220269 - Trường Đại học Trà Vinh*"
        return result
    
    # Câu hỏi về bài cụ thể - tìm theo số bài
    for bai_key, info in kb["noi_dung_hoc_phan"].items():
        bai_num = bai_key.replace("Bài ", "")
        if f"bài {bai_num}" in q_lower or f"bai {bai_num}" in q_lower or info["ten"].lower() in q_lower:
            result = f"## 📖 {bai_key}: {info['ten']}\n\n"
            result += f"**Số tiết:** Lý thuyết: {info['so_tiet_LT']} tiết | Thực hành: {info['so_tiet_TH']} tiết\n\n"
            result += "**Nội dung:**\n"
            for noi_dung in info["noi_dung"]:
                result += f"- {noi_dung}\n"
            result += "\n*📖 Nguồn: Đề cương chi tiết học phần MSHP 220269 - Trường Đại học Trà Vinh*"
            return result
    
    # Mặc định: hiển thị tổng quan
    result = "## 📚 Đề cương Môn học Khai phá Dữ liệu (MSHP: 220269)\n\n"
    result += f"**Mô tả:** {kb['mo_ta_hoc_phan']}\n\n"
    result += "**5 Bài học chính:**\n"
    for bai, info in kb["noi_dung_hoc_phan"].items():
        result += f"- {bai}. {info['ten']} ({info['so_tiet_LT']}LT + {info['so_tiet_TH']}TH tiết)\n"
    result += "\n**Đánh giá:** 25% Kiểm tra + 25% Bài tập lớn + 50% Thi trắc nghiệm cuối kỳ\n"
    result += "\n*📖 Nguồn: Đề cương chi tiết học phần MSHP 220269 - Trường Đại học Trà Vinh*"
    return result

def format_offline_quiz(topic_key: str, num_questions: int = 5) -> str:
    """
    Tạo câu trả lời quiz từ offline knowledge base (không cần LLM)
    """
    if topic_key not in OFFLINE_QUIZ_KNOWLEDGE:
        topic_key = "data_mining"  # Fallback
    
    kb = OFFLINE_QUIZ_KNOWLEDGE[topic_key]
    questions = kb["questions"][:num_questions]
    title = kb["title"]
    
    result = f"## 📝 {num_questions} Câu hỏi Trắc nghiệm về {title}\n\n"
    result += "---\n\n"
    
    for q in questions:
        result += f"**Câu {q['id']}.** {q['question']}\n\n"
        if q["type"] == "multiple_choice" and "options" in q:
            for key, val in q["options"].items():
                result += f"- **{key}.** {val}\n"
        result += f"\n> **Đáp án:** {q['correct_answer']}\n"
        result += f"> **Giải thích:** {q['explanation']}\n\n"
        result += "---\n\n"
    
    result += "\n*💡 Lưu ý: Câu hỏi được tạo từ kho kiến thức nội bộ (offline mode).*"
    return result

# Hàm dịch sử dụng Gemini
def translate_text(text, target_language="Vietnamese", max_retries=2):
    """
    Dịch text sang ngôn ngữ đích sử dụng Gemini với retry logic và xoay vòng API key
    """
    import time
    global IS_OFFLINE_MODE
    
    # Auto-recover if there's any active API key again
    if IS_OFFLINE_MODE:
        from reliability.api_key_manager import api_key_manager
        if api_key_manager.get_available_key():
            IS_OFFLINE_MODE = False
            print("🔄 [Circuit Breaker] Phát hiện có API key hoạt động trở lại! Tự động chuyển về chế độ online.")
            
    if IS_OFFLINE_MODE:
        print("⚡ [Circuit Breaker] Đang ở chế độ offline, bỏ qua dịch thuật.")
        return text
        
    from reliability.api_key_manager import api_key_manager
    
    keys_pool_size = len(api_key_manager.keys)
    attempts_limit = max(1, keys_pool_size)
    
    for attempt in range(attempts_limit):
        key_info = api_key_manager.get_available_key()
        if not key_info:
            print("⚡ [Circuit Breaker] Không có API key khả dụng khi dịch thuật! Chuyển sang chế độ offline.")
            IS_OFFLINE_MODE = True
            return text
            
        current_key = key_info.key
        try:
            llm = get_llm(task_type="general")
            
            prompt = f"""Translate the following text to {target_language}. 
Only provide the translation, nothing else.

Text: {text}

Translation:"""
            
            response = llm.invoke(prompt)
            
            # Xử lý response - có thể là string hoặc list
            translated = extract_text_from_response(response)
            
            # Record success
            api_key_manager.record_key_success(current_key)
            print(f"✅ Dịch thành công với key {key_info.name}: {translated[:50]}...")
            return translated
        except Exception as e:
            error_msg = str(e)
            is_quota = any(kw in error_msg for kw in ["RESOURCE_EXHAUSTED", "429"])
            is_overloaded = any(kw in error_msg for kw in ["503", "UNAVAILABLE", "SERVICE_UNAVAILABLE"])
            if not is_overloaded:
                api_key_manager.record_key_failure(current_key, is_quota_error=is_quota)
            print(f"Loi dich thuat voi key {key_info.name} (luot {attempt + 1}/{attempts_limit}): {error_msg[:150]}")
            if is_quota:
                continue
            
    return text

def extract_text_from_response(response):
    """
    Trích xuất text từ response của LLM - xử lý nhiều format khác nhau
    """
    if response is None:
        return ""
    
    # Nếu là string, return luôn
    if isinstance(response, str):
        return response
    
    # Nếu có attribute 'content'
    if hasattr(response, 'content'):
        content = response.content
        
        # Content là list
        if isinstance(content, list):
            if len(content) > 0:
                # List of dicts with 'text' key
                if isinstance(content[0], dict) and 'text' in content[0]:
                    return content[0]['text']
                # List of strings
                elif isinstance(content[0], str):
                    return content[0]
                # Other types
                else:
                    return str(content[0])
            return ""
        
        # Content là dict
        elif isinstance(content, dict):
            if 'text' in content:
                return content['text']
            elif 'content' in content:
                return str(content['content'])
            else:
                return str(content)
        
        # Content là string
        elif isinstance(content, str):
            return content
        
        # Other types
        else:
            return str(content)
    
    # Nếu là dict
    if isinstance(response, dict):
        if 'text' in response:
            return response['text']
        elif 'content' in response:
            return extract_text_from_response(response['content'])
        elif 'answer' in response:
            return response['answer']
        else:
            return str(response)
    
    # Nếu là list
    if isinstance(response, list):
        if len(response) > 0:
            return extract_text_from_response(response[0])
        return ""
    
    # Fallback
    return str(response)

def detect_language(text):
    """
    Phát hiện ngôn ngữ của text
    """
    vietnamese_chars = set('àáảãạăằắẳẵặâầấẩẫậèéẻẽẹêềếểễệìíỉĩịòóỏõọôồốổỗộơờớởỡợùúủũụưừứửữựỳýỷỹỵđĐ')
    
    if any(char in vietnamese_chars for char in text):
        return "Vietnamese"
    return "English"

def expand_query_for_retrieval(query: str) -> str:
    """
    Chuẩn hóa và mở rộng truy vấn (Query Expansion & Correction) tiếng Việt.
    Giúp sửa các lỗi viết tắt, lỗi chính tả học tập phổ biến của sinh viên.
    """
    if not query:
        return query
        
    query_lower = query.lower().strip()
    
    # Bộ từ điển ánh xạ từ khóa viết tắt/sai chính tả sang thuật ngữ học thuật đầy đủ
    synonym_map = {
        # K-Nearest Neighbors
        "k láng giềng": "k-nearest neighbors knn k láng giềng phân lớp classification",
        "k láng giêng": "k-nearest neighbors knn k láng giềng phân lớp classification",
        "k lán giềng": "k-nearest neighbors knn k láng giềng phân lớp classification",
        "k lân cận": "k-nearest neighbors knn k láng giềng phân lớp classification",
        "knn": "k-nearest neighbors knn k láng giềng phân lớp classification",
        "k-nn": "k-nearest neighbors knn k láng giềng phân lớp classification",
        
        # Naive Bayes
        "bayes ngây thơ": "naive bayes bayes ngây thơ phân lớp classification classifier",
        "bayes thơ nggaya": "naive bayes bayes ngây thơ phân lớp classification classifier",
        "naive bayes": "naive bayes bayes ngây thơ phân lớp classification classifier",
        "naivebayes": "naive bayes bayes ngây thơ phân lớp classification classifier",
        
        # Random Forest
        "rừng ngẫu nhiên": "random forest rừng ngẫu nhiên ensemble learning phân lớp classification",
        "random forest": "random forest rừng ngẫu nhiên ensemble learning phân lớp classification",
        "rf": "random forest rừng ngẫu nhiên ensemble learning phân lớp classification",
        
        # SVM
        "máy học vector hỗ trợ": "support vector machine svm máy học vector hỗ trợ phân lớp classification",
        "máy học vector hộ trợ": "support vector machine svm máy học vector hỗ trợ phân lớp classification",
        "máy học vec tơ hỗ trợ": "support vector machine svm máy học vector hỗ trợ phân lớp classification",
        "svm": "support vector machine svm máy học vector hỗ trợ phân lớp classification",
        "support vector": "support vector machine svm máy học vector hỗ trợ classification",
        
        # K-Means
        "k-means": "k-means clustering gom cụm kmeans phân cụm phân nhóm unsupervised",
        "kmeans": "k-means clustering gom cụm kmeans phân cụm phân nhóm unsupervised",
        "k means": "k-means clustering gom cụm kmeans phân cụm phân nhóm unsupervised",
        "phân cụm kmeans": "k-means clustering gom cụm kmeans phân cụm phân nhóm unsupervised",
        "gom cụm kmeans": "k-means clustering gom cụm kmeans phân cụm phân nhóm unsupervised",
        
        # Decision Tree & Pruning
        "cây quyết định": "decision tree cây quyết định phân lớp classification",
        "cay quyet dinh": "decision tree cây quyết định phân lớp classification",
        "cắt tỉa": "pruning tree pruning cắt tỉa overfitting",
        "tỉa cây": "pruning tree pruning cắt tỉa overfitting",
        "cat tia": "pruning tree pruning cắt tỉa overfitting",
        "tia cay": "pruning tree pruning cắt tỉa overfitting",
        
        # DBSCAN
        "dbscan": "dbscan density-based clustering phân cụm dựa trên mật độ",
        "phân cụm mật độ": "dbscan density-based clustering phân cụm dựa trên mật độ",
        "gom cụm mật độ": "dbscan density-based clustering phân cụm dựa trên mật độ",
        
        # Apriori / Association Rules
        "apriori": "apriori association rule mining luật kết hợp tập mục phổ biến frequent itemset support confidence",
        "luật kết hợp": "apriori association rule mining luật kết hợp tập mục phổ biến frequent itemset support confidence lift",
"luật kết hợp": "apriori association rule mining luật kết hợp tập mục phổ biến frequent itemset support confidence lift",
        "độ hỗ trợ": "support độ hỗ trợ association rules",
        "do ho tro": "support độ hỗ trợ association rules",
        "độ tin cậy": "confidence độ tin cậy association rules",
        "do tin cay": "confidence độ tin cậy association rules",
        "tập mục phổ biến": "frequent itemsets tập mục phổ biến support confidence minimum support",
        "tap muc pho bien": "frequent itemsets tập mục phổ biến support confidence minimum support",
        
        # FP-Growth
        "fp-growth": "fp-growth frequent pattern tree cây fp-tree association rules",
        "fpgrowth": "fp-growth frequent pattern tree cây fp-tree association rules",
        "fp growth": "fp-growth frequent pattern tree cây fp-tree association rules",
        "cây fp": "fp-growth frequent pattern tree cây fp-tree association rules",
        "cay fp": "fp-growth frequent pattern tree cây fp-tree association rules",
        
        # AGNES / Hierarchical
        "agnes": "agnes hierarchical clustering phân cụm cấp bậc dendrogram",
        "phân cụm cấp bậc": "agnes hierarchical clustering phân cụm cấp bậc dendrogram",
        "gom cụm cấp bậc": "agnes hierarchical clustering phân cụm cấp bậc dendrogram",
        
        # Preprocessing
        "tiền xử lý": "data preprocessing tiền xử lý dữ liệu làm sạch dữ liệu cleaning normalization chuẩn hóa",
        "tien xu ly": "data preprocessing tiền xử lý dữ liệu làm sạch dữ liệu cleaning normalization chuẩn hóa",
        "chuẩn hóa": "data normalization chuẩn hóa dữ liệu min-max z-score scaling",
        "chuan hoa": "data normalization chuẩn hóa dữ liệu min-max z-score scaling",
        "dữ liệu thiếu": "missing values dữ liệu thiếu imputation điền khuyết dropna",
        "du lieu thieu": "missing values dữ liệu thiếu imputation điền khuyết dropna",
        "missing": "missing values dữ liệu thiếu imputation điền khuyết",
        # Overfitting / Underfitting
        "overfitting": "overfitting quá khớp cây quyết định decision tree pruning cắt tỉa pre-pruning post-pruning",
        "quá khớp": "overfitting quá khớp cây quyết định decision tree pruning",
        "học vẹt": "overfitting quá khớp cây quyết định decision tree pruning",
        "underfitting": "underfitting thiếu khớp bias variance tradeoff",
        "pruning": "pruning cắt tỉa cây decision tree overfitting pre-pruning post-pruning reduced error cost complexity",
        "cắt tỉa cây": "pruning cắt tỉa cây decision tree overfitting pre-pruning post-pruning",
        "pre-pruning": "pre-pruning cắt tỉa trước early stopping decision tree overfitting",
        "post-pruning": "post-pruning cắt tỉa sau reduced error pruning decision tree overfitting",
    }
    import re
    # Tìm kiếm khớp chính xác hoặc khớp một phần
    matched_expansions = []
    for key, value in synonym_map.items():
        # Dùng regex word boundary để tránh "rf" khớp với "overfitting"
        pattern = r'\b' + re.escape(key) + r'\b'
        if re.search(pattern, query_lower):
            matched_expansions.append(value)
            
    if matched_expansions:
        words = []
        for exp in matched_expansions:
            words.extend(exp.split())
        
        # Loại bỏ trùng lặp từ ngữ
        seen = set()
        unique_words = [w for w in words if not (w in seen or seen.add(w))]
        
        expanded_part = " ".join(unique_words)
        expanded_query = f"{query} {expanded_part}"
        print(f"🔄 [Query Expansion] Đã mở rộng truy vấn thành: '{expanded_query}'")
        return expanded_query
        
    return query


def extract_topic_from_context(conversation_context: str, current_question: str) -> str:
    """
    Trích xuất chủ đề từ lịch sử hội thoại MÀ KHÔNG cần gọi API (100% offline).
    Dùng làm fallback khi Standalone Query LLM bị Rate Limit.
    
    Logic:
    1. Lấy câu hỏi cuối của User (dòng bắt đầu bằng 'User:' hoặc 'Bạn:')
    2. Loại bỏ các từ đệm phổ biến (chi tiết hơn, giải thích, hãy, ...)
    3. Nếu câu hỏi cuối quá ngắn sau khi lọc, thử lấy từ câu hỏi trước đó
    4. Kết hợp với từ điển query expansion để mở rộng
    """
    import re
    
    # Danh sách từ đệm cần loại bỏ (filler words)
    FILLER_WORDS = [
        "chi tiết hơn", "chi tiết", "giải thích", "giải thích thêm", "giải thích chi tiết",
        "hãy", "thêm", "nữa", "tiếp tục", "tiếp", "và", "hoặc", "nó", "điều này",
        "phần trên", "vấn đề này", "cái này", "đó", "ý trên", "như trên",
        "more detail", "explain", "elaborate", "tell me more", "details",
    ]
    
    def clean_question(text: str) -> str:
        """Loại bỏ từ đệm và làm sạch câu hỏi."""
        text = text.strip()
        text_lower = text.lower()
        for filler in FILLER_WORDS:
            text_lower = text_lower.replace(filler, " ")
        # Xóa khoảng trắng thừa
        text_cleaned = re.sub(r'\s+', ' ', text_lower).strip()
        return text_cleaned
    
    # Bước 1: Phân tích lịch sử hội thoại
    lines = conversation_context.strip().split('\n')
    
    # Tìm tất cả các câu User hỏi từ lịch sử
    user_questions = []
    ai_answers = []
    
    for line in lines:
        line_stripped = line.strip()
        if line_stripped.lower().startswith(('user:', 'bạn:', 'human:')):
            # Lấy nội dung câu hỏi (sau dấu ":")
            q_text = re.sub(r'^(user|bạn|human):\s*', '', line_stripped, flags=re.IGNORECASE)
            user_questions.append(q_text)
        elif line_stripped.lower().startswith(('assistant:', 'ai:', 'trợ lý:')):
            a_text = re.sub(r'^(assistant|ai|trợ lý):\s*', '', line_stripped, flags=re.IGNORECASE)
            ai_answers.append(a_text)
    
    # Bước 2: Thử từng câu hỏi User (ưu tiên câu hỏi cuối cùng có nội dung thực sự)
    for q in reversed(user_questions):
        cleaned = clean_question(q)
        if len(cleaned.split()) >= 3:  # Câu hỏi có ít nhất 3 từ sau khi lọc
            print(f"📎 [Offline StandaloneQuery] Trích xuất từ câu hỏi lịch sử: '{cleaned}'")
            return cleaned
    
    # Bước 3: Nếu không tìm được từ câu hỏi, thử trích xuất từ câu trả lời AI trước
    # Lấy 50 từ đầu tiên của câu trả lời gần nhất và giữ các danh từ/thuật ngữ
    if ai_answers:
        last_answer = ai_answers[-1]
        # Lấy 60 ký tự đầu (thường chứa chủ đề chính)
        topic_snippet = last_answer[:200].strip()
        # Loại bỏ các ký tự đặc biệt, giữ chữ và số
        topic_snippet = re.sub(r'[\[\]\(\)\*\#\_\>]', ' ', topic_snippet)
        topic_snippet = re.sub(r'\s+', ' ', topic_snippet).strip()
        # Lấy 10 từ đầu tiên
        words = topic_snippet.split()[:12]
        snippet = " ".join(words)
        if snippet:
            print(f"📎 [Offline StandaloneQuery] Trích xuất từ câu trả lời AI: '{snippet}'")
            return snippet
    
    # Bước 4: Fallback cuối cùng — dùng câu hỏi hiện tại
    print(f"📎 [Offline StandaloneQuery] Không tìm được chủ đề, dùng câu hỏi hiện tại: '{current_question}'")
    return current_question

def create_qa_chain(vectordb, documents=None, use_llm=True, use_hybrid=True):
    """
    Tạo chain QA với Gemini API.
    
    Args:
        vectordb: Chroma vector database
        documents: Danh sách documents gốc (cho BM25)
        use_llm: Sử dụng LLM hay không
        use_hybrid: Sử dụng hybrid search hay chỉ vector search
    """
    from reliability.api_key_manager import api_key_manager
    _key_info = api_key_manager.get_available_key()
    _api_key = _key_info.key if _key_info else os.getenv("GEMINI_API_KEY") or os.getenv("GOOGLE_API_KEY")
    llm = get_llm(task_type="general")
    
    # Tạo retriever
    if use_hybrid and documents:
        from hybrid_retriever import HybridRetriever
        
        # Tự động lấy persist directory của vectordb làm thư mục chứa bm25 index
        persist_dir = "chroma_db"
        if hasattr(vectordb, "_persist_directory") and vectordb._persist_directory:
            persist_dir = vectordb._persist_directory
        bm25_index_path = os.path.join(persist_dir, "bm25_index.pkl")
        
        retriever = HybridRetriever(
            vectordb, 
            documents,
            vector_weight=0.7,  # FIX-P10: Vector 70% (semantic) > BM25 30% (keyword)
            bm25_weight=0.3,
            bm25_index_path=bm25_index_path
        )
        retriever.k = 5
    else:
        print("🔍 Sử dụng Vector Retriever")
        retriever = vectordb.as_retriever(
            search_type="similarity",
            search_kwargs={"k": 5}
        )
    
    template = """You are an AI assistant specialized in Data Mining education.

[BẢNG THUẬT NGỮ CHUẨN]: 
Classification=Phân lớp; Gom cụm/Gom nhóm=Clustering; Knowledge discovery in databases=KDD/Khám phá tri thức trong cơ sở dữ liệu; Data mining=DM/Khai thác dữ liệu; Ensemble-based method=Phương pháp tập hợp mô hình; Feature space=Không gian đặc trưng; Gini index=Chỉ số Gini; Hierarchical clustering=Gom cụm phân cấp; Hyperplane=Siêu phẳng; Impurity=Độ hỗn loạn; Information gain=Độ lợi thông tin; Information visualization=Hiển thị thông tin dữ liệu; Kernel=Hàm nhân; kNN=k nearest neighbors/k láng giềng gần nhất; Laplace estimator=Ước lượng Laplace; Machine learning=Máy học; MDS=Multidimensional scaling/Phương pháp giảm chiều MDS; Naive Bayes=Bayes thơ ngây; Overfitting=Học vẹt (quá khớp); Principal component analysis=PCA/Phân tích thành phần chính; Random forest=Rừng ngẫu nhiên; Regression=Hồi quy; Stress function=Hàm độ đo biến dạng; Supervised learning=Học có giám sát; SVM=Support vector machines/Máy vectơ hỗ trợ; Underfitting=Học không đủ (không khớp); Unsupervised learning=Học không giám sát.

[QUY TRÌNH SUY LUẬN BẮT BUỘC KHI GIẢI CÂU HỎI TRẮC NGHIỆM]:
Nếu câu hỏi của người dùng có dạng trắc nghiệm (chứa các lựa chọn A, B, C, D hoặc tương tự):
1. Trích dẫn đoạn lý thuyết trong tài liệu liên quan đến câu hỏi.
2. Phân tích từng đáp án A, B, C, D xem tại sao đúng/sai theo tài liệu.
3. Nếu tài liệu không chứa đủ thông tin để trả lời, HÃY TỪ CHỐI TRẢ LỜI (nói rõ: "Tôi không tìm thấy thông tin này trong tài liệu."), tuyệt đối không tự bịa đáp án.
4. Đưa ra kết luận đáp án cuối cùng.


Your task is to answer the user's question STRICTLY based on the retrieved
course context. The retrieval layer already translated Vietnamese questions to
English when needed, so you must use the retrieved context instead of your
internal knowledge.

CRITICAL RULES FOR PREVENTING HALLUCINATIONS:
1. You MUST ONLY use the information provided in the Retrieved Context. Do NOT use your internal knowledge.
2. If the context lists methods, steps, or items, you MUST list exactly what is in the context. Do NOT invent, hallucinate, or add any items that are not in the context.
3. If the context does not contain the answer, respond exactly with: "Tôi không tìm thấy thông tin này trong tài liệu." Do NOT guess.
4. Reply directly in Vietnamese. Use natural and academic Vietnamese suitable for university students.
5. NEVER use Chinese (e.g., 填补), Japanese, or any other language except Vietnamese (and English terms if they appear in the context). ALWAYS translate English technical terms into Vietnamese if possible (e.g., convergence -> hội tụ).
6. CRITICAL INLINE CITATIONS REQUIREMENT: When using facts or information from a Document [i], you MUST cite it inline within the text at the exact place of use using square brackets like [i] (e.g., [1], [2]). Do not write "Document [1]" or "Source [1]" or "Document 1" or "[Source 1]", just write "[1]". Do not group all citations at the end of the response; they must be embedded in the text.
7. BỐ CỤC GIẢI THÍCH THUẬT TOÁN: Khi được hỏi "Thuật toán X hoạt động như thế nào", BẠN BẮT BUỘC PHẢI CHIA CÂU TRẢ LỜI THÀNH 2 PHẦN RÕ RÀNG:
   - Phần 1: Cách mô hình được huấn luyện/xây dựng.
   - Phần 2: Cách mô hình đưa ra dự đoán cuối cùng.

User Question: {question}

Retrieved Context:
{context}

Answer (provide detailed, accurate response in Vietnamese):"""
   
    PROMPT = PromptTemplate(
        template=template,
        input_variables=["context", "question"]
    )
    
    def format_docs(docs):
        formatted = []
        for i, doc in enumerate(docs, 1):
            formatted.append(f"Document [{i}]:\n{doc.page_content}")
        return "\n\n".join(formatted)
    
    if llm is not None:
        # Kiểm tra nếu là HybridRetriever (không hỗ trợ pipe operator)
        if use_hybrid and documents:
            # Tạo custom chain cho HybridRetriever
            def hybrid_chain(question_data):
                if isinstance(question_data, dict):
                    question = question_data.get("question", str(question_data))
                else:
                    question = str(question_data)
                
                # Gọi retriever.invoke() trực tiếp
                docs = retriever.invoke(question, k=5)
                context = format_docs(docs)
                
                # Format prompt và gọi LLM
                formatted_prompt = PROMPT.format(context=context, question=question)
                response = llm.invoke(formatted_prompt)
                return response
            
            chain = hybrid_chain
        else:
            # Chain bình thường cho vector retriever
            chain = (
                {"context": (lambda x: x["question"]) | retriever | format_docs, "question": lambda x: x["question"]}
                | PROMPT
                | llm
            )
    else:
        def retrieval_only_chain(question):
            if hasattr(retriever, 'invoke'):
                docs = retriever.invoke(question)
            else:
                docs = retriever.get_relevant_documents(question)
            context = format_docs(docs)
            return f"Retrieved documents:\n\n{context}"
        chain = retrieval_only_chain
    
    return chain, retriever

def format_source_citation(doc, index, relevance_score=None):
    """
    Format một document thành citation với đầy đủ thông tin nguồn
    """
    metadata = doc.metadata
    source = metadata.get('source', 'Unknown')
    page = metadata.get('page', 'N/A')
    slide = metadata.get('slide', None)
    
    # Lấy tên file từ path và loại bỏ mã sinh tự động nếu có
    filename = clean_source_filename(source)
    if is_word_like_source(filename):
        page = ""
        slide = None
    
    # Lấy nội dung
    content = doc.page_content.strip()
    
    # Giới hạn độ dài nếu quá dài (giữ 800 ký tự để có context đầy đủ hơn)
    max_length = 800
    if len(content) > max_length:
        content = content[:max_length] + "..."
        
    # Tính toán relevance score nếu chưa có
    if relevance_score is None:
        relevance_score = metadata.get('relevance_score', None)
    if relevance_score is None:
        # Deterministic score between 0.85 and 0.95 dựa trên nội dung
        hash_val = sum(ord(c) for c in content[:200])
        relevance_score = 0.85 + (hash_val % 11) / 100.0
    
    # Format citation
    citation = {
        'index': index,
        'filename': filename,
        'page': page,
        'slide': slide,
        'content': content,
        'full_source': source,
        'relevance_score': relevance_score
    }
    
    return citation

def format_citations_display(citations):
    """
    Format danh sách citations thành text hiển thị đẹp
    """
    if not citations:
        return ""
    
    display_text = "\n\n---\n\n### 📚 Nguồn tài liệu tham khảo:\n\n"
    
    for citation in citations:
        idx = citation['index']
        filename = citation['filename']
        page = citation['page']
        slide = citation['slide']
        content = citation['content']
        
        # Tạo header cho citation
        if slide:
            header = f"**📄 Nguồn {idx}: {filename} - Slide {slide}**"
        elif page != 'N/A':
            header = f"**📄 Nguồn {idx}: {filename} - Trang {page}**"
        else:
            header = f"**📄 Nguồn {idx}: {filename}**"
        
        display_text += f"{header}\n\n"
        display_text += f"> {content}\n\n"
    
    return display_text

def deduplicate_docs(docs):
    """
    Deduplicate/merge documents that come from the same file and page/slide.
    """
    unique_docs = []
    seen = {}
    
    for doc in docs:
        metadata = doc.metadata
        source = metadata.get('source', 'Unknown')
        page = metadata.get('page', 'N/A')
        slide = metadata.get('slide', None)
        
        # Get filename
        if '/' in source or '\\' in source:
            filename = source.replace('\\', '/').split('/')[-1]
        else:
            filename = source
            
        # Normalize keys for accurate matching
        def get_norm(val):
            if val is None:
                return ""
            return str(val).strip().lower()
            
        key = (filename.lower(), get_norm(page), get_norm(slide))
        
        if key in seen:
            # Merge content
            existing_doc = seen[key]
            # Avoid repeating exact same content
            if doc.page_content.strip() not in existing_doc.page_content:
                existing_doc.page_content += "\n\n" + doc.page_content.strip()
            # Keep highest relevance score
            if 'relevance_score' in doc.metadata and 'relevance_score' in existing_doc.metadata:
                existing_doc.metadata['relevance_score'] = max(
                    doc.metadata['relevance_score'], 
                    existing_doc.metadata['relevance_score']
                )
        else:
            # Clone doc to avoid mutating original in vector db cache
            from langchain_core.documents import Document
            new_doc = Document(page_content=doc.page_content, metadata=doc.metadata.copy())
            seen[key] = new_doc
            unique_docs.append(new_doc)
            
    return unique_docs

def translate_to_english_for_retrieval(query_vi: str) -> str:
    """Sử dụng LLM để dịch câu hỏi tiếng Việt sang từ khóa tìm kiếm tiếng Anh"""
    from langchain_google_genai import ChatGoogleGenerativeAI
    from reliability.api_key_manager import api_key_manager
    
    key_info = api_key_manager.get_available_key()
    if not key_info:
        return query_vi
        
    try:
        llm_trans = get_llm(task_type="general")
        trans_prompt = f"""Bạn là một chuyên gia kỹ thuật dữ liệu. Dịch câu truy vấn tiếng Việt sau sang tiếng Anh, chú trọng giữ nguyên và dịch đúng các thuật ngữ kỹ thuật chuyên ngành Khai phá Dữ liệu (Data Mining). Trả về duy nhất câu tiếng Anh, không giải thích.
Câu hỏi tiếng Việt: {query_vi}
Tiếng Anh:"""
        resp = llm_trans.invoke(trans_prompt)
        text = getattr(resp, "content", str(resp))
        if hasattr(text, "text"): text = text.text
        translated = text.strip()
        print(f"✅ Translated Query: {translated}")
        return translated
    except Exception as e:
        print(f"⚠️ Lỗi dịch Query (fallback sang bản gốc): {e}")
        return query_vi

def analyze_and_route_query(question: str) -> dict:
    """
    Phân tích câu hỏi để tìm ý định (intent) và mở rộng đa ngôn ngữ (Multi-Query Expansion).
    """
    from llm_router import get_llm
    import json
    
    try:
        llm = get_llm("general", require_json=True, attempt=1) # Ép dùng Gemini cho nhanh
        prompt = f"""Bạn là bộ định tuyến truy vấn (Query Router) cho hệ thống AI môn Khai phá dữ liệu.
Nhiệm vụ 1: Dịch và mở rộng câu hỏi sang tiếng Anh để vét cạn tài liệu.
Nhiệm vụ 2: Phân loại ý định để thu hẹp phạm vi tìm kiếm.
Quy tắc mục tiêu (target_file_pattern):
- "chỉ khi câu hỏi yêu cầu code, viết mã, lập trình python, hoặc cài đặt thuật toán bằng python" -> "thuattoanpython.docx"
- "weka", "thực hành weka", "công cụ weka" -> "DM3.pdf"
- "đề cương học phần", "tín chỉ", "bài tập lớn", "quy chế", "quy định" -> "220269_ Khai pha du lieu"
- "lý thuyết", "khái niệm", "định nghĩa", "hoạt động thế nào", "các bước của thuật toán" hoặc chung chung -> Để mảng rỗng [] (không lọc file nào)

BẮT BUỘC TRẢ VỀ JSON HỢP LỆ THEO ĐÚNG ĐỊNH DẠNG SAU, KHÔNG CÓ MARKDOWN HAY CHỮ THỪA:
{{
  "expanded_queries": ["câu hỏi gốc tiếng việt", "translated english query", "core keywords"],
  "intent": "code | weka | syllabus | theory | general",
  "target_file_pattern": ["thuattoanpython.docx"]
}}

Câu hỏi của sinh viên: {question}"""
        response = llm.invoke(prompt)
        text = getattr(response, "content", str(response)).strip()
        if text.startswith('```json'): text = text[7:-3]
        elif text.startswith('```'): text = text[3:-3]
        return json.loads(text.strip())
    except Exception as e:
        print(f"⚠️ [Query Router] Bỏ qua do lỗi: {e}")
        return {"expanded_queries": [question], "target_file_pattern": []}

# Module-level VI→EN translation map (dùng chung cho fast routing & decomposition)
_VI_EN_MAP = {
    # ── Chủ đề chính Data Mining ───────────────────────────────────────────────
    "khai phá dữ liệu": "data mining knowledge discovery databases",
    "khai phá": "data mining knowledge discovery",
    "khai thác dữ liệu": "data mining knowledge discovery",
    "khám phá tri thức": "knowledge discovery databases KDD",
    "học máy": "machine learning",

    # ── Câu hỏi lý thuyết / định nghĩa ────────────────────────────────────────
    "định nghĩa": "definition define what is",
    "khái niệm": "concept definition",
    "là gì": "what is definition",
    "nêu": "describe explain list",
    "giải thích": "explain description",
    "trình bày": "describe explain",
    "phát biểu": "state formulation theorem definition",
    "tính chất": "property characteristic attribute",
    "liệt kê": "list enumerate",
    "so sánh": "compare comparison difference",
    "ưu điểm": "advantage benefit",
    "nhược điểm": "disadvantage limitation drawback",
    "đặc điểm": "characteristic feature property",
    "mục tiêu": "goal objective purpose",
    "vai trò": "role function purpose",
    "tầm quan trọng": "importance significance",
    "ứng dụng": "application use case real-world business",
    "ứng dụng thực tế": "real-world applications use cases business examples",
    "ví dụ": "example instance",
    "ví dụ thực tế": "real-world example business application",
    "kinh doanh": "business commerce marketing",
    "đời sống": "everyday life real-world society",
    "thực tiễn": "practice real-world application",
    "bước": "step process procedure",
    "quy trình": "process procedure workflow",
    "hoạt động": "work function operation",
    "hoạt động như thế nào": "how it works operation mechanism",
    "cách thức": "method approach way",
    "nguyên lý": "principle mechanism",
    "nguyên tắc": "principle rule",

    # ── Thuật toán phân cụm ────────────────────────────────────────────────────
    "phân cụm": "clustering grouping unsupervised",
    "gom cụm": "clustering grouping",
    "phân nhóm": "clustering grouping",

    # ── Thuật toán phân lớp ────────────────────────────────────────────────────
    "phân lớp": "classification supervised learning",
    "học có giám sát": "supervised learning classification",
    "học không giám sát": "unsupervised learning clustering",
    "học máy": "machine learning",
    "trí tuệ nhân tạo": "artificial intelligence AI",
    "cây quyết định": "decision tree ID3 C4.5",
    "hồi quy": "regression linear logistic",
    "học sâu": "deep learning neural network",
    "mạng nơ-ron": "neural network deep learning",
    "mạng neuron": "neural network deep learning",

    # ── Frequent Patterns ──────────────────────────────────────────────────────
    "tập phổ biến": "frequent itemset support threshold",
    "tập mục phổ biến": "frequent itemset support threshold",
    "luật kết hợp": "association rule mining confidence lift support",
    "độ hỗ trợ": "support frequency threshold",
    "độ tin cậy luật": "confidence association rule",
    "tăng cường": "lift measure association",

    # ── Tiền xử lý ─────────────────────────────────────────────────────────────
    "tiền xử lý": "preprocessing data cleaning normalization",
    "tiền xử lý dữ liệu": "data preprocessing cleaning normalization",
    "làm sạch dữ liệu": "data cleaning missing values handling",
    "chuẩn hóa": "normalization standardization min-max",
    "dữ liệu thiếu": "missing values imputation",
    "dữ liệu nhiễu": "noisy data outlier",
    "nhiễu dữ liệu": "noise random error variance measured variable noisy data",
    "nhiễu": "noise random error variance",
    "ngoại lai": "outlier anomaly",

    # ── Đánh giá mô hình ────────────────────────────────────────────────────────
    "đánh giá": "evaluation metric performance",
    "độ chính xác": "accuracy precision recall",
    "quá khớp": "overfitting generalization",
    "thiếu khớp": "underfitting bias",
    "rừng ngẫu nhiên": "random forest ensemble",
    "phân tán": "scatter distribution",
    "biểu đồ": "chart diagram visualization",
    "thống kê": "statistics statistical",
    "xác suất": "probability probabilistic",

    # ── Code / Lập trình ───────────────────────────────────────────────────────
    "code": "code implementation python programming",
    "viết code": "code implementation python programming",
    "mã": "code implementation python",
    "lập trình": "programming code implementation",
    "cài đặt": "implementation code algorithm",
    "cài đặt thuật toán": "algorithm implementation code python",

    # ── KDD Process ────────────────────────────────────────────────────────────
    "quy trình kdd": "KDD process knowledge discovery steps",
    "khám phá tri thức": "knowledge discovery databases KDD process",
    "kho dữ liệu": "data warehouse",
    "cơ sở dữ liệu": "database",
    "tích hợp dữ liệu": "data integration",
    "chuyển đổi dữ liệu": "data transformation",
}

def _fast_route_query(question: str) -> dict:
    """
    Fast keyword-based query routing (KHÔNG gọi LLM).
    Trả về cùng cấu trúc như analyze_and_route_query nhưng không tốn API call.
    Tiết kiệm ~10-15 giây cho mỗi câu hỏi đơn giản.
    
    Bao gồm bản dịch VI→EN đầy đủ cho câu hỏi lý thuyết/định nghĩa/ứng dụng
    để tìm kiếm trong các tài liệu giáo trình tiếng Anh.
    """
    q_lower = question.lower()
    q_norm = normalize_query_text(question)
    
    target_patterns = []
    intent = "general"
    
    # Keyword-based file routing
    if is_summary_request(question) and any(kw in q_norm for kw in ["tien xu ly", "ti n x l", "preprocessing", "data preprocessing"]):
        target_patterns = ["03preprocessing"]
        intent = "summary"
    elif any(kw in q_norm for kw in ["cosine", "do tuong dong cosine", "tien xu ly", "preprocessing"]) and any(
        kw in q_norm for kw in ["cosine", "similarity", "d1", "d2", "khoang cach"]
    ):
        target_patterns = ["03preprocessing"]
        intent = "theory"
    elif any(kw in q_norm for kw in ["fp-growth", "fp growth", "fpgrowth", "fp tree", "fptree"]) and "apriori" in q_norm:
        target_patterns = ["06fpbasic"]
        intent = "theory"
    elif any(kw in q_norm for kw in ["information gain", "entropy", "gini", "id3", "c4.5", "cart"]) and any(
        kw in q_norm for kw in ["decision tree", "cay quyet dinh", "phan lop", "classification", "dung de lam gi", "la gi"]
    ):
        target_patterns = ["08ClassBasic"]
        intent = "theory"
    elif any(kw in q_norm for kw in ["bagging", "boosting", "metacost", "meta cost"]):
        target_patterns = ["09classadvanced"]
        intent = "theory"
    elif detect_syllabus_question(question) and not any(
        kw in q_norm for kw in ["code", "python", "sklearn", "scikit", "viet ma", "doan code", "lap trinh"]
    ):
        target_patterns = ["220269"]
        intent = "syllabus"
    elif any(kw in q_lower for kw in ["code", "viết mã", "lập trình", "python",
                                      "cài đặt thuật toán", "implement", "cài đặt",
                                      "đoạn mã", "đoạn code", "viết chương trình"]):
        target_patterns = ["thuattoanpython.docx"]
        intent = "code"
    elif any(kw in q_lower for kw in ["weka", "thực hành weka", "công cụ weka"]):
        target_patterns = ["DM3.pdf"]
        intent = "weka"
    elif any(kw in q_lower for kw in ["đề cương", "tín chỉ", "bài tập lớn",
                                       "quy chế", "quy định", "môn học"]):
        target_patterns = ["220269"]
        intent = "syllabus"
    else:
        intent = "theory"
    
    # ── Bước 1: Dịch từng cụm từ VI→EN (word-level substitution) ───────────────
    vi_en_map = _VI_EN_MAP
    en_translation = question
    # Sắp xếp theo độ dài giảm dần để ưu tiên cụm từ dài nhất
    sorted_pairs = sorted(vi_en_map.items(), key=lambda x: len(x[0]), reverse=True)
    for vi, en in sorted_pairs:
        en_translation = en_translation.replace(vi, en)
    
    # ── Bước 2: Tạo query tiếng Anh thuần túy cho câu hỏi định nghĩa/ứng dụng/khái niệm ──
    # KHÔNG dùng bản dịch garbled (TV+EN hỗn hợp) vì BM25 không hiểu text hỗn hợp
    # Chỉ giữ: (1) query gốc tiếng Việt, (2) query thuần tiếng Anh có nghĩa
    extra_en_queries = []
    extra_en_queries.extend(cross_lingual_retrieval_queries(question))
    
    # Nhận diện chủ đề chính trong câu hỏi
    _TOPIC_TO_EN = {
        "khai phá dữ liệu": "data mining",
        "khai thác dữ liệu": "data mining",
        "data mining": "data mining",
        "học máy": "machine learning",
        "machine learning": "machine learning",
        "phân cụm": "clustering",
        "gom cụm": "clustering",
        "phân lớp": "classification",
        "học máy": "machine learning",
        "cây quyết định": "decision tree",
        "hồi quy": "regression",
        "tập phổ biến": "frequent itemset mining",
        "luật kết hợp": "association rule mining",
        "tiền xử lý": "data preprocessing",
        "dữ liệu nhiễu": "noise random error variance measured variable",
        "nhiễu dữ liệu": "noise random error variance measured variable",
        "nhiễu": "noise random error variance measured variable",
        "noise": "noise random error variance measured variable",
        "k-means": "k-means clustering",
        "kmeans": "k-means clustering",
        "dbscan": "dbscan density clustering",
        "apriori": "apriori algorithm frequent itemset",
        "fp-growth": "fp-growth frequent pattern tree",
        "naive bayes": "naive bayes classification",
        "svm": "support vector machine svm",
        "random forest": "random forest ensemble",
        "rừng ngẫu nhiên": "random forest ensemble",
        "knn": "k-nearest neighbors classification",
        "overfitting": "overfitting generalization",
        "quá khớp": "overfitting generalization",
        "quy trình kdd": "KDD knowledge discovery process",
        "kdd": "KDD knowledge discovery process",
        "agnes": "agnes hierarchical clustering",
        "phân cụm cấp bậc": "hierarchical clustering dendrogram",
        "mẫu phổ biến": "frequent pattern itemset mining",
        "frequent pattern": "frequent pattern mining",
        "frequent itemset": "frequent itemset mining",
        "độ hỗ trợ": "support measure confidence lift",
        "độ tin cậy": "confidence measure association rule",
        "support": "support measure frequent itemset",
        "confidence": "confidence measure association rule",
        "luật kết hợp": "association rule mining",
        "đánh giá luật kết hợp": "association rule evaluation support confidence",
        "apriori property": "apriori property downward closure pruning",
        "apriori pruning": "apriori pruning principle downward closure",
        "nguyên lý cắt tỉa": "apriori pruning property antimonotone",
        "tính chất apriori": "apriori property downward closure antimonotone",
        "c4.5": "C4.5 decision tree pruning pessimistic",
        "c4.5 pruning": "C4.5 pessimistic pruning overfitting avoidance",
        "id3": "ID3 decision tree information gain entropy",
        "cây quyết định": "decision tree ID3 C4.5 pruning",
        "overfitting": "overfitting pruning generalization decision tree",
        "quá khớp": "overfitting pruning generalization tree",
        "cắt tỉa": "pruning pessimistic postpruning C4.5",
        "holdout": "holdout method train test split validation",
        "cross-validation": "cross validation k-fold stratified evaluation",
        "train_test_split": "train_test_split sklearn holdout method",
        "laplace smoothing": "Laplace smoothing Laplacian correction zero probability",
        "làm nhẵn laplace": "Laplace smoothing Laplacian correction zero probability",
        "zero probability": "zero probability problem Laplace smoothing Naive Bayes",
        "xác suất bằng 0": "zero probability problem Laplace smoothing Naive Bayes",
        "hierarchical clustering": "hierarchical clustering agglomerative divisive dendrogram",
        "gom cụm phân cấp": "hierarchical clustering agglomerative divisive linkage",
        "phân cụm phân cấp": "hierarchical clustering agglomerative divisive",
    }
    
    detected_topic_en = None
    # Sắp xếp key dài trước để ưu tiên cụm từ dài hơn
    for vi_topic, en_topic in sorted(_TOPIC_TO_EN.items(), key=lambda x: len(x[0]), reverse=True):
        if vi_topic in q_lower:
            detected_topic_en = en_topic
            break
    
    is_definition_q = any(kw in q_lower for kw in [
        "định nghĩa", "khái niệm", "là gì", "nêu", "trình bày",
        "giải thích", "phát biểu", "tính chất", "describe", "define", "what is"
    ])
    is_application_q = any(kw in q_lower for kw in [
        "ứng dụng", "ví dụ thực tế", "kinh doanh", "đời sống", "thực tiễn",
        "liệt kê", "kể tên", "application", "use case", "example"
    ])
    is_comparison_q = any(kw in q_lower for kw in [
        "so sánh", "khác nhau", "khác gì", "ưu điểm", "nhược điểm",
        "compare", "difference", "advantage", "disadvantage"
    ])
    is_process_q = any(kw in q_lower for kw in [
        "quy trình", "các bước", "hoạt động", "cách", "nguyên lý",
        "how", "process", "steps", "algorithm"
    ])

    # Pair/multi-concept questions need explicit English retrieval queries.
    if any(kw in q_lower for kw in ["khai phá dữ liệu", "khai pha du lieu", "data mining"]) and any(
        kw in q_lower for kw in ["học máy", "hoc may", "machine learning"]
    ):
        extra_en_queries.extend([
            "data mining machine learning statistics relationship",
            "what is data mining definition patterns knowledge hidden useful data",
            "data mining versus machine learning comparison"
        ])

    if any(kw in q_lower for kw in ["phân lớp", "phan lop", "classification"]) and any(
        kw in q_lower for kw in ["phân cụm", "phan cum", "clustering"]
    ):
        extra_en_queries.extend([
            "classification supervised learning training data class labels",
            "clustering unsupervised learning class labels unknown clusters",
            "classification versus clustering supervised unsupervised comparison"
        ])

    if any(kw in q_lower for kw in ["nhiễu", "nhieu", "noise"]):
        extra_en_queries.extend([
            "noise random error variance measured variable",
            "noisy data salary -10 example data cleaning"
        ])
    
    if detected_topic_en:
        if is_definition_q and is_application_q:
            extra_en_queries.append(
                f"definition of {detected_topic_en} applications real-world examples business"
            )
        elif is_definition_q:
            extra_en_queries.append(
                f"what is {detected_topic_en} definition concept overview introduction"
            )
        elif is_application_q:
            extra_en_queries.append(
                f"{detected_topic_en} real-world applications examples business use cases"
            )
        elif is_comparison_q:
            extra_en_queries.append(
                f"{detected_topic_en} comparison advantages disadvantages"
            )
        elif is_process_q:
            extra_en_queries.append(
                f"how does {detected_topic_en} work steps algorithm process"
            )
        else:
            extra_en_queries.append(
                f"{detected_topic_en} overview explanation"
            )

    if ENABLE_QUERY_TRANSLATION and detect_language(question) == "Vietnamese":
        translated_query = translate_to_english_for_retrieval(question)
        if translated_query and translated_query.strip() and translated_query.strip() != question:
            extra_en_queries.append(translated_query.strip())
    
    # ── Bước 3: Chỉ dùng query gốc (TV) + query EN thuần túy ────────────────────────────────
    # KHÔNG thêm en_translation vì nó là text garbled (TV từ + EN từ hỗn hợp)
    expanded_queries = [question] + extra_en_queries
    
    # Loại bỏ trùng lặp
    seen = set()
    unique_queries = []
    for q in expanded_queries:
        if q not in seen:
            seen.add(q)
            unique_queries.append(q)
    
    print(f"⚡ [FastRoute] intent={intent} | {len(unique_queries)} queries generated")
    if extra_en_queries:
        print(f"   → EN query: {extra_en_queries[0]}")
    
    return {
        "expanded_queries": unique_queries,
        "intent": intent,
        "target_file_pattern": target_patterns
    }

def _decompose_question(question: str, depth: int = 0) -> list:
    """
    QUERY DECOMPOSER: Tách câu hỏi phức hợp thành các câu hỏi con (đệ quy).
    
    Chiến lược:
    1. Split theo dấu "?" → mỗi câu hỏi kết thúc bằng ?
    2. Mỗi phần còn lại chứa "và" nối 2 ý khác nhau → tách tiếp
    3. Split theo "đồng thời", "ngoài ra", "bên cạnh đó"
    4. Đệ quy tối đa 3 lần để tránh vòng lặp vô hạn
    
    Trả về: list các câu hỏi con (tối thiểu [question])
    """
    if depth > 3:
        return [question]
    
    results = []
    q = question.strip()
    
    # Pattern 1: Split by "?" (mỗi câu hỏi kết thúc bằng ?)
    qmarks = re.split(r'\?\s*(?=[A-ZĐÀÁẢÃẠÂẦẤẨẪẬÊỀẾỂỄỆÔỒỐỔỖỘƠỜỚỞỠỢƯỪỨỬỮỰĂẮẰẲẴẶ0-9\(\"\'])', q)
    if len(qmarks) >= 2:
        parts = [p.strip() + '?' for p in qmarks if len(p.strip()) > 10]
        # Đệ quy từng phần để tách tiếp pattern "và"
        for p in parts:
            sub = _decompose_question(p, depth + 1)
            results.extend(sub)
        if len(results) >= 2:
            print(f"🔀 [Decomposer] Tách thành {len(results)} sub-queries: {results}")
            return results
    
    # Pattern 2: Split by "và" khi nó nối 2 câu hỏi khác nhau
    # Pattern: "... nào và làm sao ...", "... gì và tại sao ..."
    and_patterns = [
        r'(.*?(?:nào|gì|không|bao nhiêu|ai|đâu))\s+và\s+(.*?(?:làm sao|tại sao|như thế nào|cách nào|bằng cách nào|làm thế nào))',
        r'(.*?(?:nào|gì|không|bao nhiêu))\s+và\s+(.*?(?:liệt kê|kể tên|nêu|trình bày))',
        r'(.*?(?:định nghĩa|khái niệm)\s+.*?)\s+và\s+(.*?(?:ví dụ|ứng dụng|so sánh|phân biệt|giải thích|ý nghĩa))',
    ]
    for pattern in and_patterns:
        m = re.match(pattern, q, re.IGNORECASE)
        if m:
            p1, p2 = m.group(1).strip(), 'Hãy ' + m.group(2).strip()
            sub1 = _decompose_question(p1, depth + 1)
            sub2 = _decompose_question(p2, depth + 1)
            results = sub1 + sub2
            if len(results) >= 2:
                print(f"🔀 [Decomposer] Tách 'và' thành {len(results)} sub-queries: {results}")
                return results
    
    # Pattern 3: Split by multi-question markers
    parts = re.split(
        r'(?:,?\s*(?:đồng thời|ngoài ra|bên cạnh đó|bên cạnh đấy|mặt khác|thêm vào đó)\s*,?\s*)',
        q, flags=re.IGNORECASE
    )
    if len(parts) >= 2:
        results = [p.strip() for p in parts if len(p.strip()) > 10]
        print(f"🔀 [Decomposer] Tách markers thành {len(results)} sub-queries: {results}")
        return results
    
    # Pattern 4: Split by ". Ngoài ra", ". Bên cạnh", ". Đồng thời"
    parts = re.split(
        r'\.\s*(?=(?:Ngoài ra|Bên cạnh|Đồng thời|Mặt khác|Thêm vào đó)\b)',
        q, flags=re.IGNORECASE
    )
    if len(parts) >= 2:
        results = [p.strip() for p in parts if len(p.strip()) > 10]
        print(f"🔀 [Decomposer] Tách câu thành {len(results)} sub-queries: {results}")
        return results
    
    return [question]


def ask_question(chain, retriever, question, conversation_context="", metadata_filter=None, use_rerank=True):
    """
    Gửi câu hỏi đến chain và nhận câu trả lời với trích dẫn nguồn chi tiết.
    
    Args:
        chain: QA chain
        retriever: Document retriever
        question: Câu hỏi của người dùng
        conversation_context: Context từ lịch sử hội thoại (tùy chọn)
        metadata_filter: Bộ lọc siêu dữ liệu (tùy chọn)
        use_rerank: Sử dụng reranking hay không
    """
    global IS_OFFLINE_MODE
    
    # Lưu lại câu hỏi gốc trước khi bị thay thế bởi standalone_query
    original_question = question
    
    # Phát hiện ngôn ngữ câu hỏi
    input_language = detect_language(question)

    intent = classify_question_intent(question)
    print(f"[IntentRouter] intent={intent} question={question[:120]}")

    if intent == "conversational":
        tutor_response = get_direct_tutor_response(question)
        if tutor_response:
            return tutor_response, [], []

    # Mixed syllabus + code requests must go through RAG decomposition first so
    # the syllabus part can cite the course outline and code can be retrieved
    # from the practical-code document before falling back to tutor generation.

    if ENABLE_TUTOR_FALLBACK and not requires_document_grounding(question) and is_direct_tutor_request(question):
        tutor_response = get_tutor_knowledge_response(question)
        if tutor_response:
            print("[IntentRouter] Direct tutor response served before strict RAG.")
            return ensure_world_knowledge_disclosure(tutor_response), [], []
    
    # ============================================================================
    # QUERY DECOMPOSITION: Tách câu hỏi ghép thành sub-queries
    # ============================================================================
    sub_questions = _decompose_question(question)

    if conversation_context and not is_context_dependent_question(question):
        print("[Context] Current question is self-contained; ignoring prior chat context.")
        conversation_context = ""
    
    # Nếu có context, dùng LLM để sinh câu hỏi độc lập (Standalone Query)
    if conversation_context:
        print("🔄 Bắt đầu sinh Standalone Query từ lịch sử hội thoại...")
        try:
            from langchain_google_genai import ChatGoogleGenerativeAI
            from reliability.api_key_manager import api_key_manager
            
            key_info = api_key_manager.get_available_key()
            if key_info:
                llm_sq = get_llm(task_type="general")
                sq_prompt = f"""Bạn là chuyên gia Khai phá Dữ liệu. Người dùng đang hỏi một câu hỏi tiếp nối.
Dựa vào Lịch sử trò chuyện và Câu hỏi mới nhất, hãy viết lại thành MỘT câu hỏi độc lập đầy đủ ý nghĩa.

QUY TẮC BẮT BUỘC:
1. GIẢI QUYẾT ĐẠI TỪ: Nếu câu hỏi dùng "nó", "thuật toán này", "phương pháp đó", "kỹ thuật trên", "cái đó"
   → XÁC ĐỊNH và THAY THẾ bằng tên thực thể cụ thể từ lịch sử hội thoại.
   Ví dụ: "cách hoạt động của nó" + lịch sử có "SVM" → "SVM (Support Vector Machine) hoạt động như thế nào?"
2. GIẢI QUYẾT CÂU NỐI TIẾP: Câu bắt đầu bằng "và ...", "thêm về ...", "chi tiết hơn ..."
   → ghép chủ đề chính từ lịch sử vào câu hỏi.
   Ví dụ: "và ứng dụng của nó?" + lịch sử có "Naive Bayes" → "Ứng dụng của Naive Bayes?"
3. DỊCH thuật ngữ chuyên ngành sang tiếng Anh (độ hỗ trợ → support, máy véc-tơ hỗ trợ → SVM).
4. KẾT QUẢ phải là câu query hoàn chỉnh, tìm được trong DB mà KHÔNG cần biết ngữ cảnh trước đó.
5. TUYỆT ĐỐI KHÔNG giữ đại từ chưa giải quyết ("nó", "này", "đó") trong kết quả cuối.

Lịch sử trò chuyện:
{conversation_context}

Câu hỏi mới nhất:
{question}

Câu truy vấn độc lập (viết bằng tiếng Việt + thuật ngữ Anh):"""
                sq_response = llm_sq.invoke(sq_prompt)
                sq_text = getattr(sq_response, "content", str(sq_response))
                if hasattr(sq_text, "text"): sq_text = sq_text.text
                question_with_context = sq_text.strip()
                print(f"✅ Standalone Query: {question_with_context}")
            else:
                print("⚠️ Không có API key cho Standalone Query. Fallback to raw question.")
                question_with_context = question
        except Exception as e:
            print(f"⚠️ Lỗi sinh Standalone Query (có thể do Rate Limit): {e}")
            # Thay vì báo lỗi hoặc dùng "chi tiết hơn" làm từ khóa tìm kiếm,
            # dùng thuật toán offline để trích xuất chủ đề từ lịch sử hội thoại.
            print("📎 Kích hoạt Offline Topic Extractor để tránh lấy sai tài liệu...")
            offline_query = extract_topic_from_context(conversation_context, question)
            if len(offline_query.split()) >= 2:
                question_with_context = offline_query
                print(f"✅ [Offline Fallback] Sẽ tìm kiếm với: '{question_with_context}'")
            else:
                # Nếu offline extractor cũng không tìm được chủ đề (câu hỏi quá ngắn và context rỗng)
                print("⚠️ Không thể xác định chủ đề. Báo lỗi rate limit cho user.")
                raise Exception("API_RATE_LIMIT_STANDALONE")
    else:
        question_with_context = question
        
    # ============================================================================
    # QUERY ROUTING — Fast path (no LLM) vs Full path (LLM)
    # ============================================================================
    # Kiểm tra xem câu hỏi có phải là câu hỏi tiếp nối (follow-up) không
    _followup_indicators = [
        "nó", "này", "đó", "thuật toán này", "phương pháp đó",
        "kỹ thuật trên", "cái đó", "thêm về", "chi tiết hơn",
        "tiếp tục", "ý trên", "phần trên"
    ]
    is_followup = any(kw in question_with_context.lower() for kw in _followup_indicators)
    
    if not conversation_context and not is_followup:
        # Câu hỏi đơn giản, trực tiếp → dùng fast routing (KHÔNG gọi LLM, tiết kiệm ~10-15s)
        print("⚡ Fast Query Routing (skip LLM call)...")
        routing_info = _fast_route_query(question_with_context)
    else:
        # Câu hỏi phức tạp hoặc follow-up → dùng LLM-based routing
        print("🧭 Bắt đầu Query Router (LLM)...")
        routing_info = analyze_and_route_query(question_with_context)
    
    target_patterns = routing_info.get("target_file_pattern", [])
    
    print(f"   → Intent: {routing_info.get('intent', 'general')}")
    print(f"   → Target Filters: {target_patterns}")
    
    # Update metadata_filter with routing logic
    # Compound question: không filter file để các sub-queries tìm trong tất cả files
    is_compound = len(sub_questions) > 1
    
    # Helper: resolve pattern → list file paths để dùng trong filter $in
    def _resolve_pattern_to_files(pattern, data_dir="data"):
        import os
        resolved = []
        if os.path.exists(data_dir):
            all_f = os.listdir(data_dir)
            for f in all_f:
                if pattern in f.lower():
                    resolved.append(f)
                    resolved.append(f"data/{f}")
                    resolved.append(f"data\\{f}")
                    resolved.append(os.path.abspath(os.path.join(data_dir, f)))
        return resolved if resolved else [pattern]
    
    if target_patterns and len(target_patterns) > 0 and not is_compound:
        resolved_files = []
        for pattern in target_patterns:
            resolved_files.extend(_resolve_pattern_to_files(pattern.lower().strip()))
        new_filter = {"source": {"$in": resolved_files}}
        if metadata_filter:
            allowed_in_filter = set()
            src_f = metadata_filter.get("source", {})
            if isinstance(src_f, dict) and "$in" in src_f:
                allowed_in_filter = set(src_f["$in"])
            if allowed_in_filter:
                merged = list(set(resolved_files) & allowed_in_filter)
                metadata_filter = {"source": {"$in": merged}} if merged else {"source": {"$in": resolved_files}}
            else:
                metadata_filter = {"$and": [metadata_filter, new_filter]}
        else:
            metadata_filter = new_filter
    
    # Lấy RETRIEVE_K từ config (mặc định 20)
    from config import USE_RERANKING as _USE_RERANKING
    try:
        from config import RETRIEVE_K as _RETRIEVE_K
    except ImportError:
        _RETRIEVE_K = 20
    RETRIEVE_K = _RETRIEVE_K

    # Khởi tạo danh sách documents chứa tất cả kết quả retrieve
    all_initial_docs = []

    # Hàm retrieve cho 1 query với filter riêng (dùng cho parallel execution)
    def _retrieve_single(query, filter_override=None):
        try:
            current_filter = filter_override if filter_override is not None else metadata_filter
            if hasattr(retriever, 'invoke'):
                return retriever.invoke(query, k=RETRIEVE_K, filter=current_filter)
            else:
                return retriever.get_relevant_documents(query, filter=current_filter)[:RETRIEVE_K]
        except Exception as e:
            print(f"Canh bao: Error retrieving for query '{query}': {e}")
            return []

    # Bước 1: Multi-Query Retrieval (PARALLEL — chạy song song các query)
    # Với compound question: mỗi sub-question chạy với filter riêng
    if len(sub_questions) > 1:
        print(f"🔀 Đang retrieve documents cho {len(sub_questions)} sub-queries (parallel)...")
        # Xây dựng danh sách (query, filter) cho từng sub-question
        query_filter_pairs = []
        for sq in sub_questions:
            sq_routing = _fast_route_query(sq)
            sq_intent = sq_routing.get("intent", "general")
            is_sq_syllabus = detect_syllabus_question(sq) or sq_intent == "syllabus"

            # Queries cho sub-question này (VI + EN expansions)
            sq_queries = [sq]
            for en_q in sq_routing.get("expanded_queries", []):
                if en_q != sq and en_q not in sq_queries:
                    sq_queries.append(en_q)

            # Filter riêng: syllabus sub-query CHỈ tìm trong syllabus file
            if is_sq_syllabus:
                sq_patterns = sq_routing.get("target_file_pattern", [])
                syllabus_files = []
                for pat in sq_patterns:
                    syllabus_files.extend(_resolve_pattern_to_files(pat.lower().strip()))
                if syllabus_files:
                    unique_files = list(set(syllabus_files))
                    # Merge với security filter: giao của 2 $in list — tránh $and ChromaDB bug
                    allowed_sources = set()
                    if metadata_filter and isinstance(metadata_filter, dict):
                        src_filter = metadata_filter.get("source", {})
                        if isinstance(src_filter, dict) and "$in" in src_filter:
                            allowed_sources = set(src_filter["$in"])
                    if allowed_sources:
                        merged = list(set(unique_files) & allowed_sources)
                        sq_filter = {"source": {"$in": merged}} if merged else {"source": {"$in": unique_files}}
                    else:
                        sq_filter = {"source": {"$in": unique_files}}
                else:
                    sq_filter = metadata_filter
            else:
                sq_filter = metadata_filter

            for q in sq_queries:
                query_filter_pairs.append((q, sq_filter))

        import concurrent.futures
        max_workers = min(len(query_filter_pairs), 4)
        with concurrent.futures.ThreadPoolExecutor(max_workers=max_workers) as executor:
            futures = [executor.submit(_retrieve_single, q, f) for q, f in query_filter_pairs]
            for future in concurrent.futures.as_completed(futures):
                all_initial_docs.extend(future.result())

        expanded_queries = [q for q, _ in query_filter_pairs]
    else:
        print("🔍 Đang retrieve documents (parallel)...")
        expanded_queries = routing_info.get("expanded_queries", [question_with_context])
        import concurrent.futures
        max_workers = min(len(expanded_queries), 4)
        with concurrent.futures.ThreadPoolExecutor(max_workers=max_workers) as executor:
            futures = [executor.submit(_retrieve_single, q) for q in expanded_queries]
            for future in concurrent.futures.as_completed(futures):
                all_initial_docs.extend(future.result())

    # Gộp và loại bỏ trùng lặp (giữ nguyên thứ tự ưu tiên)
    seen_content = set()
    initial_docs = []
    for doc in all_initial_docs:
        content_hash = doc.page_content.strip()
        if content_hash not in seen_content:
            seen_content.add(content_hash)
            initial_docs.append(doc)

    # Đặt biến search_query_en để truyền cho Reranker (nếu cần thiết)
    search_query_en = expanded_queries[-1] if len(expanded_queries) > 1 else expanded_queries[0]

    print(f"📊 Retrieved {len(initial_docs)} documents")
    
    # Bỏ qua tài liệu Đề cương chi tiết nếu người dùng không hỏi về đề cương
    # Compound question: giữ tất cả tài liệu vì có thể cần cả syllabus và bài giảng
    is_syllabus_q = detect_syllabus_question(original_question) or routing_info.get("intent") == "syllabus"
    if not is_syllabus_q and not is_compound:
        filtered_docs = []
        for doc in initial_docs:
            src = str(doc.metadata.get("source_file", doc.metadata.get("source", ""))).lower()
            if "đề cương" not in src and "de cuong" not in src and "220269" not in src:
                filtered_docs.append(doc)
        initial_docs = filtered_docs
        print(f"📊 Sau khi lọc Syllabus: {len(initial_docs)} documents")
    elif is_compound:
        # Compound question: kiểm tra từng sub-question — chỉ giữ syllabus docs
        # nếu sub-question đó thực sự hỏi về đề cương
        syllabus_sqs = []
        theory_sqs = []
        for sq in sub_questions:
            sq_syllabus = detect_syllabus_question(sq)
            sq_routing = _fast_route_query(sq)
            sq_intent = sq_routing.get("intent", "general")
            if sq_syllabus or sq_intent == "syllabus":
                syllabus_sqs.append(sq)
            else:
                theory_sqs.append(sq)
        # Nếu có cả 2 loại: lọc syllabus docs cho theory sub-queries
        if syllabus_sqs and theory_sqs:
            print(f"📊 Compound có cả syllabus ({len(syllabus_sqs)}) + theory ({len(theory_sqs)}), lọc riêng...")
            filtered_docs = []
            for doc in initial_docs:
                src = str(doc.metadata.get("source_file", doc.metadata.get("source", ""))).lower()
                if "đề cương" not in src and "de cuong" not in src and "220269" not in src:
                    filtered_docs.append(doc)
            # Giữ lại syllabus docs với số lượng giới hạn
            syllabus_docs = [d for d in initial_docs if d not in filtered_docs][:2]
            initial_docs = filtered_docs + syllabus_docs
            print(f"📊 Compound filter: {len(filtered_docs)} theory + {len(syllabus_docs)} syllabus = {len(initial_docs)}")
    
    # Bước 2: Rerank và chọn top 3
    # Bước 2: Rerank — dùng retrieval/reranker.py với BAAI/bge-reranker-v2-m3
    from config import USE_RERANKING
    if USE_RERANKING and use_rerank and len(initial_docs) > 3:
        from retrieval.reranker import create_reranker as _new_reranker
        reranker = _new_reranker(
            retrieval_weight=0.35,
            rerank_weight=0.65,
            top_k=6,
            threshold=0.35,
        )
        # Truyền rank-based retrieval scores
        n = len(initial_docs)
        retrieval_scores = [1.0 - (i / n) for i in range(n)]
        scored_docs_obj = reranker.rerank(
            search_query_en, initial_docs,
            retrieval_scores=retrieval_scores,
            verbose=True,
        )
        source_docs = [sd.document for sd in scored_docs_obj]
        for sd in scored_docs_obj:
            sd.document.metadata['relevance_score'] = sd.final_score
            sd.document.metadata['retrieval_score'] = sd.retrieval_score
            sd.document.metadata['rerank_score'] = sd.rerank_score
    else:
        print("Reranking disabled, using top 3 documents directly")
        source_docs = initial_docs[:3]
    
    source_docs = deduplicate_docs(source_docs)
    print(f"✅ Sử dụng {len(source_docs)} documents cho LLM sau khi gộp trùng lặp")
    
    from reliability.api_key_manager import api_key_manager
    global IS_OFFLINE_MODE

    # Auto-recover: reset IS_OFFLINE_MODE mỗi request mới
    # IS_OFFLINE_MODE KHÔNG nên persist giữa các request vì quota tự phục hồi
    IS_OFFLINE_MODE = False

    # Reset key health nếu cooldown đã hết
    from datetime import datetime
    now = datetime.now()
    for k in api_key_manager.keys:
        if not k.is_healthy and k.cooldown_until and now >= k.cooldown_until:
            k.is_healthy = True
            k.failures = 0
            k.cooldown_until = None
            print(f"Key {k.name} cooldown expired, restored to healthy.")
            
    keys_pool_size = len(api_key_manager.keys)
    attempts_limit = max(1, keys_pool_size)
    answer_text = None
    last_llm_prompt = None
    rate_limited = IS_OFFLINE_MODE
    # Model fallback list — thử lần lượt khi model bị overload
    _model_list = ["gemini-2.5-flash-lite", "gemini-2.5-flash", "gemini-flash-latest", "gemini-2.0-flash"]
    
    if IS_OFFLINE_MODE:
        print("⚡ [Circuit Breaker] Đang ở chế độ offline, bỏ qua gọi Gemini API.")
    
    for attempt in range(attempts_limit) if not IS_OFFLINE_MODE else []:
        key_info = api_key_manager.get_available_key()
        if not key_info:
            print("⚡ [Circuit Breaker] Không có API key khả dụng khi hỏi đáp! Kích hoạt chế độ offline fallback.")
            IS_OFFLINE_MODE = True
            rate_limited = True
            break
            
        current_key = key_info.key
        _model = _model_list[attempt % len(_model_list)]
        try:
            from langchain_google_genai import ChatGoogleGenerativeAI
            llm = get_llm(task_type="general", attempt=attempt, api_key=current_key)
            
            formatted_docs = []
            for idx, doc in enumerate(source_docs, 1):
                meta = doc.metadata
                src_file = clean_source_filename(meta.get("source_file", meta.get("source", "unknown")))
                section  = meta.get("section_title") or meta.get("section", "")
                page     = meta.get("page_number") or meta.get("page", "")
                loc = f"{src_file}"
                if section:
                    loc += f" — {section}"
                if page and not is_word_like_source(src_file):
                    loc += f" (trang/slide {page})"
                # Xóa [N] nằm trong nội dung tài liệu gốc (ví dụ footnote của sách)
                # để LLM không sao chép sang câu trả lời, thành 7 nguồn giả
                clean_content = re.sub(r'\[(\d+)\]', r'(\1)', doc.page_content)
                formatted_docs.append(
                    f"[{idx}] Nguồn: {loc}\n"
                    f"Nội dung:\n{clean_content}"
                )
            context = "\n\n---\n\n".join(formatted_docs)

            # Conversation history section for multi-turn context
            conv_history_section = ""
            if conversation_context:
                conv_history_section = f"""
════════════════════════════════════════════════════════════
LỊCH SỬ HỘI THOẠI (giữ mạch hội thoại liên tục)
════════════════════════════════════════════════════════════
{conversation_context}

Lưu ý: Câu hỏi hiện tại đã được viết lại thành câu độc lập: "{question_with_context}"
"""

            template = f"""Bạn là trợ lý học thuật chuyên về môn Khai phá Dữ liệu.

════════════════════════════════════════════════════════════
NGUYÊN TẮC DỰA TRÊN TÀI LIỆU (GROUNDING)
════════════════════════════════════════════════════════════
1. NGUỒN THÔNG TIN: Bạn BẮT BUỘC phải lấy các dữ kiện, khái niệm và phương pháp từ CONTEXT bên dưới. KHÔNG tự sáng tác thêm các phương pháp hoặc định nghĩa không có trong CONTEXT.
2. TỔNG HỢP & GIẢI THÍCH: Bạn ĐƯỢC PHÉP diễn đạt lại, dịch từ tiếng Anh sang tiếng Việt, tổng hợp và giải thích các thông tin trong CONTEXT một cách dễ hiểu (như một gia sư), miễn là không làm sai lệch ý nghĩa.
3. PHÂN TÍCH TÌNH HUỐNG: Nếu câu hỏi đưa ra một ví dụ hoặc tình huống (ví dụ: train 99% nhưng test 65%), hãy sử dụng các khái niệm trong CONTEXT (ví dụ: Overfitting) để giải thích tình huống đó.
4. CHỐNG GỘP KIẾN THỨC (ANTI-CONFLATION): Khi giải thích một thuật toán cụ thể (ví dụ: Random Forest), BẠN CHỈ ĐƯỢC PHÉP trích xuất phần nội dung nói chính xác về thuật toán đó. TUYỆT ĐỐI KHÔNG tự ý gộp các thuật toán khác nằm lân cận trong tài liệu (như Rotation Forest, Bagging, PCA) vào làm các bước của thuật toán đang hỏi, trừ khi tài liệu ghi rõ chúng là một phần cấu thành của thuật toán đó.
5. TỪ CHỐI AN TOÀN: NẾU VÀ CHỈ NẾU CONTEXT hoàn toàn không có bất kỳ thông tin nào liên quan đến chủ đề câu hỏi (độ phủ ngữ cảnh = 0), tuyệt đối không được hiển thị nội dung không liên quan mà hãy thông báo ngay: "Tôi không tìm thấy thông tin này trong tài liệu."
6. NGÔN NGỮ: BẮT BUỘC SỬ DỤNG TIẾNG VIỆT 100%. TUYỆT ĐỐI KHÔNG SỬ DỤNG TIẾNG TRUNG QUỐC (CHINESE) trong câu trả lời. Nếu có thuật ngữ tiếng Anh (ví dụ: convergence, decision tree), BẮT BUỘC phải dịch sang tiếng Việt (ví dụ: hội tụ, cây quyết định).
7. BỐ CỤC GIẢI THÍCH THUẬT TOÁN: Khi được hỏi "Thuật toán X hoạt động như thế nào", BẠN BẮT BUỘC PHẢI CHIA CÂU TRẢ LỜI THÀNH 2 PHẦN RÕ RÀNG:
   - Phần 1: Cách mô hình được huấn luyện/xây dựng.
   - Phần 2: Cách mô hình đưa ra dự đoán cuối cùng.
8. CHỐNG ẢO GIÁC TRÍCH DẪN & ƯU TIÊN NGUỒN: Nếu câu hỏi về kiến thức chuyên môn (ví dụ: định nghĩa, độ đo, thuật toán), hãy ưu tiên tìm kiếm câu trả lời trong các slide bài giảng (PowerPoint) và giáo trình có trong CONTEXT. TUYỆT ĐỐI KHÔNG lấy thông tin hoặc trích dẫn từ các tài liệu "Đề cương chi tiết" (Syllabus) để định nghĩa thuật toán hay lý thuyết chuyên môn, vì chúng chỉ liệt kê tên bài học.
9. CÂU HỎI NHIỀU PHẦN: Nếu câu hỏi có nhiều vế (ví dụ: vế 1 hỏi về đề cương, vế 2 hỏi về thuật toán), hãy TRẢ LỜI TỪNG VẾ MỘT CÁCH RIÊNG BIỆT, đánh số rõ ràng (1), (2),... và sử dụng nguồn phù hợp cho mỗi vế. KHÔNG gộp chung các nguồn không liên quan vào một câu trả lời.

════════════════════════════════════════════════════════════
QUY TẮC TRÍCH DẪN INLINE (BẮT BUỘC)
════════════════════════════════════════════════════════════
- BẠN BẮT BUỘC PHẢI CHÈN TRỰC TIẾP thẻ [1], [2], [3]... VÀO NGAY BÊN TRONG VĂN BẢN (INLINE) tại nơi bạn sử dụng thông tin.
- MỖI CÂU LÝ THUYẾT HOẶC GIẢI THÍCH MÀ BẠN VIẾT RA ĐỀU PHẢI KẾT THÚC BẰNG ÍT NHẤT MỘT TRÍCH DẪN.
- TUYỆT ĐỐI KHÔNG TẠO MỤC "Tài liệu tham khảo" HAY LIỆT KÊ NGUỒN Ở CUỐI CÂU TRẢ LỜI.
- TUYỆT ĐỐI KHÔNG VIẾT CÁC DÒNG "Nguồn:", "References:", "Tài liệu tham khảo:" ở cuối. Hệ thống giao diện sẽ tự hiển thị hộp nguồn riêng từ metadata.
- CÂU TRẢ LỜI CUỐI CÙNG CHỈ GỒM NỘI DUNG GIẢI THÍCH VÀ CÁC THẺ [N] INLINE.
- TUYỆT ĐỐI KHÔNG trích dẫn [N] cho các tài liệu "Đề cương chi tiết" nếu nó chỉ liệt kê tiêu đề thuật toán.

VÍ DỤ CÁCH TRẢ LỜI ĐÚNG (câu hỏi 2 vế):
"(1) Theo đề cương, môn học có các môn tiên quyết là X, Y, Z [1].
(2) Thuật toán Naive Bayes hoạt động dựa trên định lý Bayes [2]. Để khắc phục xác suất bằng 0, người ta dùng kỹ thuật làm nhẵn Laplace (Laplace smoothing) [3]."

{conv_history_section}
════════════════════════════════════════════════════════════
CONTEXT — TÀI LIỆU THAM KHẢO
════════════════════════════════════════════════════════════
{{context}}

════════════════════════════════════════════════════════════
CÂU HỎI
════════════════════════════════════════════════════════════
{{question}}

════════════════════════════════════════════════════════════
TRẢ LỜI (Tiếng Việt, từng vế riêng biệt nếu có nhiều vế, BẮT BUỘC chèn [N] inline):
════════════════════════════════════════════════════════════"""

            num_sources = len(source_docs)
            display_question = question_with_context
            if is_summary_request(question):
                template += """

YEU CAU RIENG CHO CAU HOI TOM TAT:
- KHONG duoc chi liet ke tieu de, agenda, muc luc hoac cac dau muc trong slide.
- PHAI doc noi dung chi tiet trong CONTEXT va viet tom tat giai thich y nghia cot loi cua tung phan.
- Voi chu de tien xu ly du lieu, neu co trong CONTEXT, hay tom tat ro: chat luong du lieu, lam sach du lieu, tich hop du lieu, giam du lieu, chuyen doi/chuan hoa/roi rac hoa du lieu.
- Moi y tom tat quan trong van phai co trich dan inline [N].
"""
            prompt = (
                template
                .replace("{num_sources}", str(num_sources))
                .replace("{context}", context)
                .replace("{question}", display_question)
            )
            last_llm_prompt = prompt
            
            # Sử dụng ThreadPoolExecutor để bắt buộc timeout
            import concurrent.futures
            with concurrent.futures.ThreadPoolExecutor(max_workers=1) as executor:
                future = executor.submit(llm.invoke, prompt)
                try:
                    response = future.result(timeout=60)
                except concurrent.futures.TimeoutError:
                    raise Exception("timeout: LLM bị treo (vượt quá 60s)")
                    
            answer_text = getattr(response, "content", str(response))
            if hasattr(answer_text, "text"): answer_text = answer_text.text
            
            # Record success
            api_key_manager.record_key_success(current_key)
            rate_limited = False
            break
        except Exception as e:
            error_msg = str(e)
            is_quota      = any(kw in error_msg for kw in ["RESOURCE_EXHAUSTED", "429"])
            is_overloaded = any(kw in error_msg for kw in ["503", "UNAVAILABLE", "SERVICE_UNAVAILABLE"])
            is_timeout    = any(kw in error_msg.lower() for kw in ["timeout", "timed out", "deadline"])
            is_network    = any(kw in error_msg.lower() for kw in ["connection", "network", "refused", "reset"])

            safe_err = error_msg[:150].encode('ascii', errors='replace').decode('ascii')
            print(f"[LLM] attempt={attempt+1} quota={is_quota} overload={is_overloaded} timeout={is_timeout}")
            print(f"[LLM] {safe_err}")

            if is_overloaded and not is_quota:
                import time as _time
                _time.sleep(2)
            elif is_timeout or is_network:
                print("[LLM] Network/Timeout error detected. Activating offline fallback immediately to save time.")
                rate_limited = True
                break
            elif is_quota:
                api_key_manager.record_key_failure(current_key, is_quota_error=True)
            else:
                api_key_manager.record_key_failure(current_key, is_quota_error=False)

            if attempt == attempts_limit - 1:
                print("[LLM] All attempts failed. Offline fallback for this request only.")
                rate_limited = True
                break
            
    if rate_limited and not answer_text and last_llm_prompt and os.getenv("GROQ_API_KEY", "").strip():
        try:
            print("[LLM] Gemini exhausted. Trying Groq fallback...")
            answer_text = call_groq_chat(last_llm_prompt, temperature=0.2, max_tokens=2048)
            if answer_text:
                rate_limited = False
                print("[LLM] Groq fallback succeeded.")
        except Exception as e:
            safe_err = str(e)[:180].encode("ascii", errors="replace").decode("ascii")
            print(f"[LLM] Groq fallback failed: {safe_err}")

    # Offline fallback khi bị rate limit
    if rate_limited and not answer_text:
        if detect_syllabus_question(question):
            print("📚 Phát hiện câu hỏi về đề cương, dùng OFFLINE_SYLLABUS_KNOWLEDGE...")
            answer_text = format_offline_syllabus(question)
        elif not ENABLE_WORLD_KNOWLEDGE_FALLBACK:
            answer_text = build_extractive_answer_from_sources(question, source_docs)
        else:
            print("Thong bao: Using offline knowledge base for response...")
            quiz_topic = detect_quiz_topic(question)
            if quiz_topic:
                num_match = re.search(r'(\d+)\s*câu', question.lower())
                num_q = int(num_match.group(1)) if num_match else 5
                num_q = min(num_q, 5)
                answer_text = format_offline_quiz(quiz_topic, num_q)
            else:
                offline_explanation = get_offline_explanation(question)
                if offline_explanation:
                    print("💡 Phát hiện từ khóa khái niệm học thuật, dùng offline explanation...")
                    answer_text = offline_explanation
                else:
                    answer_text = (
                        "⚠️ **Hệ thống đang tạm thời bị giới hạn quota API**.\n\n"
                        "Bạn có thể thử lại sau hoặc hỏi về nội dung đề cương học phần.\n\n"
                        "*Hệ thống đang hoạt động ở chế độ offline với kho kiến thức được lưu trữ sẵn.*"
                    )
            
    # FIX-P4: Chỉ dịch ngược nếu answer phát hiện là tiếng Anh thuần túy
    # (hiếm khi xảy ra với prompt tiếng Việt mới, tiết kiệm API call)
    if not rate_limited and answer_text:
        detected_lang = detect_language(answer_text[:300])
        if detected_lang == "English" and input_language == "Vietnamese":
            print("⚠️ LLM trả lời tiếng Anh, đang dịch về tiếng Việt...")
            answer_text = translate_text(answer_text, "Vietnamese")
            
    # citations s\u1ebd \u0111\u01b0\u1ee3c build sau khi dedup ho\u00e0n t\u1ea5t \u0111\u1ec3 index kh\u1edbp ch\u00ednh x\u00e1c v\u1edbi text
    citations = []  # placeholder, s\u1ebd populate sau
    _source_docs_raw = source_docs  # gi\u1eef tham chi\u1ebfu g\u1ed1c cho dedup

    # Citation verification + Confidence Score (local, no API)
    try:
        from verification.citation_verifier import verify_citations
        from verification.confidence_score import (
            compute_confidence, format_confidence_block,
            build_source_block, extract_used_citation_indices,
        )

        verif = verify_citations(answer_text or "", source_docs, citations)

        # Reranker scores từ metadata
        reranker_scores = [
            doc.metadata.get('rerank_score') or doc.metadata.get('relevance_score', 0.5)
            for doc in source_docs
        ]

        confidence = compute_confidence(
            source_docs=source_docs,
            citations=citations,
            citation_coverage=verif.citation_coverage,
            reranker_scores=reranker_scores,
            question=question,
            answer_text=answer_text,
        )

        if answer_text and source_docs:
            # Strip phần source block LLM tự sinh (tránh duplicate)
            # Dùng regex xóa các dòng tham khảo ở cuối văn bản một cách an toàn. 
            # Bắt buộc phải có chữ Nguồn/Tham khảo để tránh xóa nhầm nội dung chính.
            answer_stripped = re.sub(
                r'\n*\*?\*?(?:[\u2600-\u27BF\uD800-\uDBFF\uDC00-\uDFFF]+\s*)?(?:Nguồn tài liệu|Tài liệu tham khảo|Tham khảo|Nguồn|TÀI LIỆU THAM KHẢO|References)\s*\*?[:\s]*\[?1\]?.*$',
                '', answer_text, flags=re.DOTALL | re.IGNORECASE
            ).rstrip()
            answer_stripped = re.sub(
                r'\n+\s*(?:#{1,6}\s*)?(?:\*\*)?(?:Tài liệu tham khảo|Nguồn tài liệu|Nguồn tham khảo|Tham khảo|References|Sources)(?:\*\*)?\s*:?\s*\n(?:\s*(?:[-*]\s*)?\[\d+\].*(?:\n|$))*\s*$',
                '',
                answer_stripped,
                flags=re.IGNORECASE,
            ).rstrip()
            answer_stripped = strip_generated_reference_block(answer_stripped)

            # KIỂM TRA: Loại bỏ [N] nếu N > số nguồn thực tế (LLM tự bịa số)
            num_real_sources = len(source_docs)
            answer_stripped = re.sub(
                r'\[(\d+)\]',
                lambda m: f'[{m.group(1)}]' if int(m.group(1)) <= num_real_sources else '',
                answer_stripped
            )

            # FIX-2: Xoá metadata raw lộ ra ngoài (vd: "— Section 1 (trang/slide 1)", "— Page 373 (trang/slide 373)", "[67%]")
            answer_stripped = re.sub(
                r'\s*—\s*(?:Section|Section\s+\d+|Section\s+\d+\s*–\s*.*?|Page\s+\d+|page\s+\d+)(?:\s*\(trang/slide\s+\d+\))?',
                '', answer_stripped
            )
            answer_stripped = re.sub(
                r'\s*\[?\d*\.?\d+%\]?', '', answer_stripped
            )

            # ── AUTO-CITATION INSERTION ─────────────────────────────────────
            # Nếu answer không có [N] citations hoặc rất ít, tự động gán citation
            # bằng cách match từng câu với source documents
            existing_cites = set(int(m) for m in re.findall(r'\[(\d+)\]', answer_stripped) if 1 <= int(m) <= num_real_sources)
            auto_cite_threshold = max(1, num_real_sources // 2)
            if len(existing_cites) < auto_cite_threshold and num_real_sources > 0:
                sentences = re.split(r'(?<=[.!?])\s+(?=[A-ZÁÀẢÃẠĂẮẰẲẴẶÂẤẦẨẪẬĐÉÈẺẼẸÊẾỀỂỄỆÍÌỈĨỊÓÒỎÕỌÔỐỒỔỖỘƠỚỜỞỠỢÚÙỦŨỤƯỨỪỬỮỰÝỲỶỸỴ])', answer_stripped)
                new_answer_parts = []
                for sent in sentences:
                    sent = sent.strip()
                    if not sent or len(sent) < 20:
                        new_answer_parts.append(sent)
                        continue
                    has_citation = bool(re.search(r'\[(\d+)\]', sent))
                    if not has_citation:
                        # Token overlap matching
                        sent_lower = re.sub(r'[^\w\s]', ' ', sent.lower())
                        sent_tokens = set(w for w in sent_lower.split() if len(w) > 2)
                        best_idx, best_score = 0, 0.0
                        for didx, doc in enumerate(source_docs):
                            doc_text = doc.page_content.lower()
                            doc_tokens = set(w for w in re.sub(r'[^\w\s]', ' ', doc_text).split() if len(w) > 2)
                            if sent_tokens and doc_tokens:
                                overlap = len(sent_tokens & doc_tokens) / len(sent_tokens)
                                if overlap > best_score:
                                    best_score = overlap
                                    best_idx = didx + 1
                        if best_score >= 0.10 and best_idx > 0:
                            sent = f"{sent} [{best_idx}]"
                    new_answer_parts.append(sent)
                answer_stripped = " ".join(new_answer_parts)

            # Xây dựng khối danh sách nguồn tài liệu khớp chính xác với [N] được dùng
            used_indices = sorted(set(
                int(m) for m in re.findall(r'\[(\d+)\]', answer_stripped)
                if 1 <= int(m) <= num_real_sources
            ))
            if used_indices:
                seen_filenames = set()
                idx_remap: dict = {}
                display_entries = []

                for idx in used_indices:
                    doc_i = idx - 1
                    meta = source_docs[doc_i].metadata
                    src = clean_source_filename(meta.get("source_file") or meta.get("source", f"Tài liệu {idx}"))
                    is_word_like = is_word_like_source(src)
                    if src in seen_filenames:
                        existing_idx = next(
                            (ei for ei in used_indices
                             if ei < idx and (
                                 clean_source_filename(
                                     source_docs[ei-1].metadata.get("source_file") or
                                     source_docs[ei-1].metadata.get("source", "")
                                 ) == src
                             )),
                            None
                        )
                        if existing_idx:
                            idx_remap[idx] = idx_remap.get(existing_idx, existing_idx)
                        else:
                            idx_remap[idx] = None
                        continue
                    seen_filenames.add(src)
                    section = meta.get("section_title") or meta.get("section", "")
                    page    = meta.get("page_number") or meta.get("page", "")
                    label   = src
                    # Chỉ thêm section nếu không phải metadata raw (Section N, Page N, Slide N)
                    has_generic_meta = bool(re.match(r'^(?:section|page|slide|trang)\s*\d+', section, re.IGNORECASE))
                    if section and not has_generic_meta:
                        label += f" — {section}"
                    if page and not has_generic_meta and not is_word_like:
                        label += f" (trang/slide {page})"
                    display_entries.append((idx, label))
                    idx_remap[idx] = idx

                def apply_remap(m):
                    n = int(m.group(1))
                    mapped = idx_remap.get(n, n)
                    if mapped is None:
                        return ''
                    return f'[{mapped}]'

                answer_stripped = re.sub(r'\[(\d+)\]', apply_remap, answer_stripped)

                citations = []
                for (d_idx, d_label) in display_entries:
                    doc_i = d_idx - 1
                    doc_obj = _source_docs_raw[doc_i]
                    cit = format_source_citation(doc_obj, d_idx, relevance_score=None)
                    citations.append(cit)

            # Recompute verification after citation cleanup/auto-citation.
            # The first pass may see zero coverage because citations are added here.
            final_verif = verify_citations(answer_stripped, source_docs, citations)
            confidence = compute_confidence(
                source_docs=source_docs,
                citations=citations,
                citation_coverage=final_verif.citation_coverage,
                reranker_scores=reranker_scores,
                question=question,
                answer_text=answer_stripped,
            )

            # 2. Append confidence block
            conf_block = format_confidence_block(confidence)

            # 3. Check Confidence/Answerability Threshold.
            # Answerability catches cases where retrieval found a syllabus/title
            # chunk, but the chunk cannot actually answer the question.
            low_answerability = (
                confidence.answerability_score is not None
                and confidence.answerability_score < ANSWERABILITY_FALLBACK_THRESHOLD
            )
            low_confidence = confidence.score < LOW_CONFIDENCE_THRESHOLD
            refusal_answer = is_refusal_answer(answer_stripped)
            reject_for_low_confidence = low_confidence and (refusal_answer or not citations)
            reject_for_low_answerability = (
                low_answerability
                and not requires_document_grounding(question)
                and (
                    refusal_answer
                    or not citations
                    or confidence.score < 0.45
                    or (is_summary_request(question) and confidence.answerability_score < 0.50)
                )
            )
            if reject_for_low_confidence or reject_for_low_answerability:
                print(
                    f"[RAG] Rejecting/redirecting answer due to "
                    f"confidence={confidence.score}, answerability={confidence.answerability_score}, "
                    f"refusal={refusal_answer}, citations={len(citations)}"
                )
                tutor_fallback = None
                fallback_intent = classify_question_intent(question)
                can_use_tutor_fallback = (
                    ENABLE_TUTOR_FALLBACK
                    and not requires_document_grounding(question)
                    and (
                        fallback_intent in {"pedagogical", "code_lab", "conversational"}
                        or is_data_mining_domain_question(question)
                    )
                )
                if can_use_tutor_fallback:
                    tutor_fallback = get_tutor_knowledge_response(question)
                    if not tutor_fallback:
                        tutor_fallback = generate_tutor_llm_response(question, fallback_intent)

                if tutor_fallback:
                    tutor_fallback = ensure_world_knowledge_disclosure(tutor_fallback)
                    answer_text = (
                        tutor_fallback
                        + "\n\n---\n"
                        + f"*RAG không đủ tự tin để trích dẫn tài liệu cho câu hỏi này "
                        + f"({int(confidence.score*100)}%). Mình đã trả lời theo chế độ gia sư AI.*"
                    )
                    citations = []
                else:
                    answer_text = (
                        "Tôi không tìm thấy thông tin chuyên môn phù hợp hoặc không đủ độ tin cậy "
                        f"để trả lời chính xác câu hỏi này (Độ tin cậy: {int(confidence.score*100)}% - Thấp).\n\n"
                        "Vui lòng thử diễn đạt lại câu hỏi rõ ràng hơn hoặc hỏi về các chủ đề có trong tài liệu bài giảng.\n\n"
                        f"{conf_block}"
                    )
            else:
                answer_text = answer_stripped + "\n" + conf_block

    except Exception as e:
        print(f"[Verification/Confidence] Non-critical error: {e}")
        
    return answer_text, source_docs, citations

def generate_quiz(chain, retriever, topic="", num_questions=5):
    """
    Tạo câu hỏi ôn tập dựa trên tài liệu sử dụng Gemini API với offline fallback.
    """
    global IS_OFFLINE_MODE
    
    # Auto-recover if there's any active API key again
    if IS_OFFLINE_MODE:
        from reliability.api_key_manager import api_key_manager
        if api_key_manager.get_available_key():
            IS_OFFLINE_MODE = False
            print("🔄 [Circuit Breaker] Phát hiện có API key hoạt động trở lại! Tự động chuyển về chế độ online.")
            
    if IS_OFFLINE_MODE:
        print("⚡ [Circuit Breaker] Đang ở chế độ offline, dùng kho câu hỏi cục bộ.")
        rate_limited = True
        # Ghi đè để bỏ qua vòng lặp API
        prompt = ""
    else:
        rate_limited = False
    
    # Phát hiện ngôn ngữ chủ đề
    input_language = detect_language(topic) if topic else "Vietnamese"
    
    # Nếu chủ đề tiếng Việt, dịch sang tiếng Anh (chỉ khi API available)
    topic_en = topic if topic else "data mining concepts"
    
    # Tìm tài liệu liên quan
    try:
        docs = retriever.invoke(topic_en)
    except Exception:
        docs = []
    
    # Tạo prompt cho Gemini
    context = "\n\n".join([doc.page_content[:300] for doc in docs[:3]])
    
    prompt = f"""Based on the following documents about data mining, create {num_questions} multiple-choice quiz questions in Vietnamese.
Topic: {topic_en if topic_en else 'General data mining concepts'}

Documents:
{context}

For each question, provide:
- Question in Vietnamese
- 4 options (A, B, C, D) 
- Correct answer
- Brief explanation

Format each question clearly."""
    
    from reliability.api_key_manager import api_key_manager
    keys_pool_size = len(api_key_manager.keys)
    attempts_limit = max(1, keys_pool_size)
    rate_limited = False
    
    for attempt in range(attempts_limit) if not IS_OFFLINE_MODE else []:
        key_info = api_key_manager.get_available_key()
        if not key_info:
            print("⚡ [Circuit Breaker] Không có API key khả dụng khi sinh quiz! Kích hoạt chế độ offline.")
            IS_OFFLINE_MODE = True
            rate_limited = True
            break
            
        current_key = key_info.key
        try:
            llm = get_llm(task_type="general")
            response = llm.invoke(prompt)
            quiz_text = extract_text_from_response(response)
            # Record success
            api_key_manager.record_key_success(current_key)
            return f"## 📝 Câu hỏi ôn tập ({num_questions} câu)\n\n{quiz_text}"
        except Exception as e:
            error_msg = str(e)
            is_quota = any(kw in error_msg for kw in ["RESOURCE_EXHAUSTED", "429"])
            is_overloaded = any(kw in error_msg for kw in ["503", "UNAVAILABLE", "SERVICE_UNAVAILABLE"])
            api_key_manager.record_key_failure(current_key, is_quota_error=is_quota, is_overloaded=is_overloaded)
            print(f"Canh bao: Error generating quiz with key {key_info.name} (attempt {attempt+1}/{attempts_limit}): {error_msg[:100]}")
            if attempt == attempts_limit - 1:
                print("⚡ [Circuit Breaker] Đã thử hết các key khi sinh quiz! Kích hoạt chế độ offline.")
                IS_OFFLINE_MODE = True
                rate_limited = True
                break
    
    # Offline fallback - dùng knowledge base cứng-coded
    print("Thong bao: Using offline knowledge base for quiz generation...")
    if topic:
        # Xác định topic từ chủ đề
        topic_lower = topic.lower()
        if any(kw in topic_lower for kw in ["apriori", "a priori"]):
            topic_key = "apriori"
        elif any(kw in topic_lower for kw in ["fp", "frequent", "phổ biến", "kết hợp"]):
            topic_key = "frequent_pattern"
        else:
            topic_key = "data_mining"
    else:
        topic_key = "data_mining"
    
    return format_offline_quiz(topic_key, num_questions)

def generate_structured_summary(retriever, topic, metadata_filter=None):
    from langchain_google_genai import ChatGoogleGenerativeAI
    from reliability.api_key_manager import api_key_manager
    import time
    
    if hasattr(retriever, 'invoke'):
        docs = retriever.invoke(topic, k=10, filter=metadata_filter)
    else:
        docs = retriever.get_relevant_documents(topic, filter=metadata_filter)[:10]
    
    context = "\n\n".join([f"Tài liệu {i+1}:\n{doc.page_content}" for i, doc in enumerate(docs)])
    prompt = f"""Dựa trên các đoạn tài liệu sau, tóm tắt có cấu trúc về [{topic}].
Trình bày theo các mục: Định nghĩa cốt lõi, Thuật toán chính, Ví dụ minh họa.
Giữ nguyên ký hiệu toán học. Trả lời bằng tiếng Việt.

Tài liệu: {context}"""

    attempts_limit = max(1, len(api_key_manager.keys))
    for attempt in range(attempts_limit):
        current_key = api_key_manager.get_available_key()
        if not current_key:
            return "Lỗi kỹ thuật: Hết quota API.", docs, []
        try:
            llm = get_llm(task_type="general", api_key=current_key.key)
            response = llm.invoke(prompt)
            answer_text = getattr(response, "content", str(response))
            if hasattr(answer_text, "text"): answer_text = answer_text.text
            api_key_manager.record_key_success(current_key.key)
            return answer_text, docs, []
        except Exception as e:
            api_key_manager.record_key_failure(current_key.key, is_quota_error=any(kw in str(e) for kw in ["RESOURCE_EXHAUSTED", "429"]))
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
        
    context = "\n\n".join([doc.page_content[:400] for doc in docs])
    prompt = f"""Từ nội dung sau, sinh {n} flashcard dạng JSON:
[
  {{"front": "câu hỏi", "back": "đáp án ngắn gọn", "category": "Định nghĩa / Thuật toán / Công thức"}}
]
Tập trung vào định nghĩa, công thức, và so sánh thuật toán.
Chỉ trả về JSON, không có text khác. (Mảng JSON thuần túy, không dùng code block)

Nội dung: {context}"""

    attempts_limit = max(1, len(api_key_manager.keys))
    for attempt in range(attempts_limit):
        current_key = api_key_manager.get_available_key()
        if not current_key:
            return []
        try:
            llm = get_llm(task_type="general", api_key=current_key.key)
            response = llm.invoke(prompt)
            text = getattr(response, "content", str(response))
            if hasattr(text, "text"): text = text.text
            api_key_manager.record_key_success(current_key.key)
            
            json_str = text.strip()
            if json_str.startswith("```json"): json_str = json_str[7:]
            if json_str.startswith("```"): json_str = json_str[3:]
            if json_str.endswith("```"): json_str = json_str[:-3]
            match = re.search(r'\[\s*\{.*\}\s*\]', json_str, re.DOTALL)
            if match: json_str = match.group(0)
            return json.loads(json_str)
        except Exception as e:
            api_key_manager.record_key_failure(current_key.key, is_quota_error=any(kw in str(e) for kw in ["RESOURCE_EXHAUSTED", "429"]))
            time.sleep(1)
            
    return []
