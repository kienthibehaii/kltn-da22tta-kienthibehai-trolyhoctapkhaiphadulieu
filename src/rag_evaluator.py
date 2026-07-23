# rag_evaluator.py - Module đánh giá hệ thống RAG
import time
import json
from typing import List, Dict, Tuple
from datetime import datetime
import re
from difflib import SequenceMatcher

class RAGEvaluator:
    """
    Đánh giá hệ thống RAG với các metrics:
    - Accuracy
    - Precision / Recall
    - Response time
    - Relevance score
    """
    
    def __init__(self):
        self.results = []
        self.test_set = []
    
    def load_test_set(self, test_set: List[Dict]):
        """
        Load test set
        
        Format:
        [
            {
                "question": "Clustering là gì?",
                "ground_truth": "Clustering là kỹ thuật phân nhóm...",
                "keywords": ["clustering", "phân nhóm", "unsupervised"],
                "category": "clustering"
            }
        ]
        """
        self.test_set = test_set
        print(f"✅ Đã load {len(test_set)} câu hỏi test")
    
    def evaluate(self, qa_chain, retriever, use_rerank=True) -> Dict:
        """
        Đánh giá hệ thống RAG
        
        Args:
            qa_chain: QA chain
            retriever: Document retriever
            use_rerank: Sử dụng reranking hay không
        
        Returns:
            Dict chứa kết quả đánh giá
        """
        print("\n" + "=" * 80)
        print("BẮT ĐẦU ĐÁNH GIÁ HỆ THỐNG RAG")
        print("=" * 80)
        
        self.results = []
        
        for i, test_case in enumerate(self.test_set, 1):
            print(f"\n📝 Test {i}/{len(self.test_set)}: {test_case['question'][:50]}...")
            
            result = self._evaluate_single(
                test_case, 
                qa_chain, 
                retriever, 
                use_rerank
            )
            
            self.results.append(result)
            
            # Hiển thị kết quả ngắn gọn
            print(f"   ✅ Accuracy: {result['accuracy']:.2f}")
            print(f"   ⏱️  Time: {result['response_time']:.2f}s")
        
        # Tính metrics tổng
        summary = self._calculate_summary()
        
        return summary
    
    def _evaluate_single(self, test_case: Dict, qa_chain, retriever, use_rerank: bool) -> Dict:
        """
        Đánh giá một câu hỏi
        """
        question = test_case['question']
        ground_truth = test_case['ground_truth']
        keywords = test_case.get('keywords', [])
        category = test_case.get('category', 'general')
        
        # Đo thời gian
        start_time = time.time()
        
        try:
            # Gọi hệ thống RAG
            from rag import ask_question
            answer, sources, citations = ask_question(
                qa_chain, 
                retriever, 
                question,
                conversation_context="",
                use_rerank=use_rerank
            )
            
            response_time = time.time() - start_time
            success = True
            
        except Exception as e:
            print(f"   ❌ Lỗi: {e}")
            answer = ""
            sources = []
            citations = []
            response_time = time.time() - start_time
            success = False
        
        # Tính metrics
        accuracy = self._calculate_accuracy(answer, ground_truth)
        precision, recall, f1 = self._calculate_precision_recall(answer, keywords)
        relevance = self._calculate_relevance(answer, ground_truth)
        keyword_coverage = self._calculate_keyword_coverage(answer, keywords)
        
        result = {
            'question': question,
            'ground_truth': ground_truth,
            'answer': answer,
            'category': category,
            'success': success,
            'response_time': response_time,
            'accuracy': accuracy,
            'precision': precision,
            'recall': recall,
            'f1_score': f1,
            'relevance': relevance,
            'keyword_coverage': keyword_coverage,
            'num_sources': len(sources),
            'num_citations': len(citations)
        }
        
        return result
    
    def _calculate_accuracy(self, answer: str, ground_truth: str) -> float:
        """
        Tính accuracy dựa trên similarity
        """
        if not answer or not ground_truth:
            return 0.0
        
        # Sử dụng SequenceMatcher để tính similarity
        similarity = SequenceMatcher(None, answer.lower(), ground_truth.lower()).ratio()
        
        return similarity
    
    def _calculate_precision_recall(self, answer: str, keywords: List[str]) -> Tuple[float, float, float]:
        """
        Tính Precision, Recall, F1 dựa trên keywords
        
        Precision: Tỷ lệ keywords trong answer có trong ground truth keywords
        Recall: Tỷ lệ ground truth keywords xuất hiện trong answer
        """
        if not keywords or not answer:
            return 0.0, 0.0, 0.0
        
        answer_lower = answer.lower()
        
        # Tìm keywords xuất hiện trong answer
        found_keywords = [kw for kw in keywords if kw.lower() in answer_lower]
        
        # Recall: Tỷ lệ keywords được tìm thấy
        recall = len(found_keywords) / len(keywords) if keywords else 0.0
        
        # Precision: Giả sử tất cả keywords tìm thấy đều đúng
        precision = recall  # Đơn giản hóa
        
        # F1 score
        if precision + recall > 0:
            f1 = 2 * (precision * recall) / (precision + recall)
        else:
            f1 = 0.0
        
        return precision, recall, f1
    
    def _calculate_relevance(self, answer: str, ground_truth: str) -> float:
        """
        Tính độ liên quan dựa trên overlap của từ
        """
        if not answer or not ground_truth:
            return 0.0
        
        # Tokenize
        answer_words = set(re.findall(r'\w+', answer.lower()))
        truth_words = set(re.findall(r'\w+', ground_truth.lower()))
        
        # Tính Jaccard similarity
        if not answer_words or not truth_words:
            return 0.0
        
        intersection = answer_words & truth_words
        union = answer_words | truth_words
        
        relevance = len(intersection) / len(union)
        
        return relevance
    
    def _calculate_keyword_coverage(self, answer: str, keywords: List[str]) -> float:
        """
        Tính tỷ lệ keywords được cover
        """
        if not keywords or not answer:
            return 0.0
        
        answer_lower = answer.lower()
        found = sum(1 for kw in keywords if kw.lower() in answer_lower)
        
        return found / len(keywords)
    
    def _calculate_summary(self) -> Dict:
        """
        Tính metrics tổng
        """
        if not self.results:
            return {}
        
        # Lọc kết quả thành công
        successful_results = [r for r in self.results if r['success']]
        
        if not successful_results:
            return {
                'total_tests': len(self.results),
                'successful_tests': 0,
                'failed_tests': len(self.results),
                'success_rate': 0.0
            }
        
        # Tính trung bình
        avg_accuracy = sum(r['accuracy'] for r in successful_results) / len(successful_results)
        avg_precision = sum(r['precision'] for r in successful_results) / len(successful_results)
        avg_recall = sum(r['recall'] for r in successful_results) / len(successful_results)
        avg_f1 = sum(r['f1_score'] for r in successful_results) / len(successful_results)
        avg_relevance = sum(r['relevance'] for r in successful_results) / len(successful_results)
        avg_response_time = sum(r['response_time'] for r in successful_results) / len(successful_results)
        avg_keyword_coverage = sum(r['keyword_coverage'] for r in successful_results) / len(successful_results)
        
        # Tính theo category
        categories = {}
        for result in successful_results:
            cat = result['category']
            if cat not in categories:
                categories[cat] = []
            categories[cat].append(result)
        
        category_stats = {}
        for cat, results in categories.items():
            category_stats[cat] = {
                'count': len(results),
                'avg_accuracy': sum(r['accuracy'] for r in results) / len(results),
                'avg_f1': sum(r['f1_score'] for r in results) / len(results)
            }
        
        summary = {
            'total_tests': len(self.results),
            'successful_tests': len(successful_results),
            'failed_tests': len(self.results) - len(successful_results),
            'success_rate': len(successful_results) / len(self.results),
            'avg_accuracy': avg_accuracy,
            'avg_precision': avg_precision,
            'avg_recall': avg_recall,
            'avg_f1_score': avg_f1,
            'avg_relevance': avg_relevance,
            'avg_response_time': avg_response_time,
            'avg_keyword_coverage': avg_keyword_coverage,
            'category_stats': category_stats
        }
        
        return summary
    
    def generate_report(self, summary: Dict, output_file: str = None) -> str:
        """
        Tạo báo cáo đánh giá
        """
        report = []
        report.append("=" * 80)
        report.append("BÁO CÁO ĐÁNH GIÁ HỆ THỐNG RAG")
        report.append("=" * 80)
        report.append(f"Thời gian: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        report.append("")
        
        # Tổng quan
        report.append("📊 TỔNG QUAN")
        report.append("-" * 80)
        report.append(f"Tổng số test: {summary['total_tests']}")
        report.append(f"Thành công: {summary['successful_tests']}")
        report.append(f"Thất bại: {summary['failed_tests']}")
        report.append(f"Tỷ lệ thành công: {summary['success_rate']*100:.1f}%")
        report.append("")
        
        # Metrics chính
        report.append("📈 METRICS CHÍNH")
        report.append("-" * 80)
        report.append(f"Accuracy:          {summary['avg_accuracy']*100:.2f}%")
        report.append(f"Precision:         {summary['avg_precision']*100:.2f}%")
        report.append(f"Recall:            {summary['avg_recall']*100:.2f}%")
        report.append(f"F1 Score:          {summary['avg_f1_score']*100:.2f}%")
        report.append(f"Relevance:         {summary['avg_relevance']*100:.2f}%")
        report.append(f"Keyword Coverage:  {summary['avg_keyword_coverage']*100:.2f}%")
        report.append(f"Avg Response Time: {summary['avg_response_time']:.2f}s")
        report.append("")
        
        # Theo category
        if summary.get('category_stats'):
            report.append("📂 THEO CATEGORY")
            report.append("-" * 80)
            for cat, stats in summary['category_stats'].items():
                report.append(f"{cat}:")
                report.append(f"  - Số test: {stats['count']}")
                report.append(f"  - Accuracy: {stats['avg_accuracy']*100:.2f}%")
                report.append(f"  - F1 Score: {stats['avg_f1']*100:.2f}%")
            report.append("")
        
        # Chi tiết từng test
        report.append("📝 CHI TIẾT TỪNG TEST")
        report.append("-" * 80)
        for i, result in enumerate(self.results, 1):
            status = "✅" if result['success'] else "❌"
            report.append(f"\n{status} Test {i}: {result['question'][:60]}...")
            report.append(f"   Category: {result['category']}")
            report.append(f"   Accuracy: {result['accuracy']*100:.1f}%")
            report.append(f"   F1 Score: {result['f1_score']*100:.1f}%")
            report.append(f"   Time: {result['response_time']:.2f}s")
            if not result['success']:
                report.append(f"   ⚠️  Test thất bại")
        
        report.append("")
        
        # Nhận xét tự động
        report.append("💡 NHẬN XÉT TỰ ĐỘNG")
        report.append("-" * 80)
        comments = self._generate_comments(summary)
        for comment in comments:
            report.append(f"• {comment}")
        
        report.append("")
        report.append("=" * 80)
        
        report_text = "\n".join(report)
        
        # Lưu file nếu có
        if output_file:
            with open(output_file, 'w', encoding='utf-8') as f:
                f.write(report_text)
            print(f"\n✅ Đã lưu báo cáo vào {output_file}")
        
        return report_text
    
    def _generate_comments(self, summary: Dict) -> List[str]:
        """
        Tạo nhận xét tự động
        """
        comments = []
        
        # Success rate
        if summary['success_rate'] >= 0.95:
            comments.append("Hệ thống hoạt động rất ổn định (success rate >= 95%)")
        elif summary['success_rate'] >= 0.8:
            comments.append("Hệ thống hoạt động tốt (success rate >= 80%)")
        else:
            comments.append("⚠️ Hệ thống cần cải thiện độ ổn định (success rate < 80%)")
        
        # Accuracy
        if summary['avg_accuracy'] >= 0.8:
            comments.append("Độ chính xác cao (accuracy >= 80%)")
        elif summary['avg_accuracy'] >= 0.6:
            comments.append("Độ chính xác trung bình (accuracy 60-80%)")
        else:
            comments.append("⚠️ Độ chính xác thấp, cần cải thiện (accuracy < 60%)")
        
        # F1 Score
        if summary['avg_f1_score'] >= 0.7:
            comments.append("F1 score tốt (>= 70%), cân bằng precision và recall")
        elif summary['avg_f1_score'] >= 0.5:
            comments.append("F1 score trung bình (50-70%)")
        else:
            comments.append("⚠️ F1 score thấp (< 50%), cần cải thiện precision/recall")
        
        # Response time
        if summary['avg_response_time'] <= 2.0:
            comments.append("Thời gian phản hồi nhanh (<= 2s)")
        elif summary['avg_response_time'] <= 5.0:
            comments.append("Thời gian phản hồi chấp nhận được (2-5s)")
        else:
            comments.append("⚠️ Thời gian phản hồi chậm (> 5s), cần tối ưu")
        
        # Keyword coverage
        if summary['avg_keyword_coverage'] >= 0.8:
            comments.append("Coverage keywords tốt (>= 80%)")
        elif summary['avg_keyword_coverage'] >= 0.6:
            comments.append("Coverage keywords trung bình (60-80%)")
        else:
            comments.append("⚠️ Coverage keywords thấp (< 60%), câu trả lời thiếu thông tin")
        
        # Recommendations
        comments.append("")
        comments.append("Khuyến nghị:")
        
        if summary['avg_accuracy'] < 0.7:
            comments.append("  - Cải thiện chất lượng documents và chunking")
        
        if summary['avg_f1_score'] < 0.6:
            comments.append("  - Tối ưu retrieval và reranking")
        
        if summary['avg_response_time'] > 3.0:
            comments.append("  - Tối ưu tốc độ (cache, batch processing)")
        
        if summary['avg_keyword_coverage'] < 0.7:
            comments.append("  - Cải thiện prompt để LLM trả lời đầy đủ hơn")
        
        return comments
    
    def export_to_json(self, output_file: str):
        """
        Export kết quả ra JSON
        """
        data = {
            'timestamp': datetime.now().isoformat(),
            'summary': self._calculate_summary(),
            'results': self.results
        }
        
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        
        print(f"✅ Đã export kết quả ra {output_file}")

def create_default_test_set() -> List[Dict]:
    """
    Tạo test set mặc định về Data Mining
    """
    test_set = [
        {
            "question": "Clustering là gì?",
            "ground_truth": "Clustering là kỹ thuật phân nhóm dữ liệu không giám sát, nhóm các đối tượng tương tự vào cùng một cụm.",
            "keywords": ["clustering", "phân nhóm", "unsupervised", "cụm"],
            "category": "clustering"
        },
        {
            "question": "K-means algorithm hoạt động như thế nào?",
            "ground_truth": "K-means phân cụm dữ liệu bằng cách chọn k centroids, gán điểm vào cụm gần nhất, cập nhật centroids, lặp lại cho đến hội tụ.",
            "keywords": ["k-means", "centroid", "phân cụm", "lặp lại", "hội tụ"],
            "category": "clustering"
        },
        {
            "question": "Classification là gì?",
            "ground_truth": "Classification là kỹ thuật học có giám sát để dự đoán nhãn lớp của dữ liệu mới dựa trên dữ liệu huấn luyện.",
            "keywords": ["classification", "supervised", "dự đoán", "nhãn", "huấn luyện"],
            "category": "classification"
        },
        {
            "question": "Decision tree hoạt động như thế nào?",
            "ground_truth": "Decision tree tạo cây quyết định bằng cách chia dữ liệu theo các thuộc tính, chọn thuộc tính tốt nhất dựa trên information gain.",
            "keywords": ["decision tree", "cây quyết định", "chia", "information gain"],
            "category": "classification"
        },
        {
            "question": "Association rules là gì?",
            "ground_truth": "Association rules tìm mối quan hệ thú vị giữa các items trong database, thường dùng trong market basket analysis.",
            "keywords": ["association rules", "mối quan hệ", "items", "market basket"],
            "category": "association"
        },
        {
            "question": "Apriori algorithm là gì?",
            "ground_truth": "Apriori là thuật toán tìm frequent itemsets và association rules, sử dụng nguyên lý apriori để giảm không gian tìm kiếm.",
            "keywords": ["apriori", "frequent itemsets", "association rules"],
            "category": "association"
        },
        {
            "question": "Sự khác biệt giữa supervised và unsupervised learning?",
            "ground_truth": "Supervised learning cần dữ liệu có nhãn để huấn luyện, unsupervised learning không cần nhãn và tự tìm cấu trúc trong dữ liệu.",
            "keywords": ["supervised", "unsupervised", "nhãn", "huấn luyện"],
            "category": "general"
        },
        {
            "question": "Data preprocessing là gì?",
            "ground_truth": "Data preprocessing là quá trình làm sạch, chuẩn hóa và biến đổi dữ liệu thô thành dạng phù hợp cho data mining.",
            "keywords": ["preprocessing", "làm sạch", "chuẩn hóa", "biến đổi"],
            "category": "preprocessing"
        }
    ]
    
    return test_set
