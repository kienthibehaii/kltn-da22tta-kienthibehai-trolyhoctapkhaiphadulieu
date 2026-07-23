# metrics_tracker.py - Track performance metrics cho RAG system
import json
from datetime import datetime
from typing import Dict, Optional
import os


class MetricsTracker:
    """Track và log metrics cho RAG system"""
    
    def __init__(self, log_file="metrics.json"):
        self.log_file = log_file
        self.current_session = {
            'session_id': None,
            'start_time': None,
            'queries': []
        }
        
    def start_session(self, session_id: str):
        """Bắt đầu tracking session mới"""
        self.current_session = {
            'session_id': session_id,
            'start_time': datetime.now().isoformat(),
            'queries': []
        }

    # ── Alias methods để tương thích với app.py (Streamlit) ──────────────────
    def record_response_time(self, response_time: float, session_id: Optional[str] = None):
        """Alias: ghi nhận thời gian phản hồi (tương thích với app.py)"""
        self.track_query(
            query="",
            response_time=response_time,
            num_retrieved=0,
            num_sources=0,
            answer_length=0
        )

    def record_citation_metrics(self, accuracy: float, completeness: float,
                                relevance: float, session_id: Optional[str] = None):
        """Alias: ghi nhận citation metrics (tương thích với app.py)"""
        query_data = {
            'timestamp': datetime.now().isoformat(),
            'type': 'citation_metrics',
            'citation_accuracy': round(accuracy, 4),
            'citation_completeness': round(completeness, 4),
            'citation_relevance': round(relevance, 4),
            'session_id': session_id
        }
        self.current_session['queries'].append(query_data)

    def record_error(self, error_msg: str, context: Optional[str] = None):
        """Alias: ghi nhận lỗi (tương thích với app.py)"""
        self.track_query(
            query=context or "",
            response_time=0,
            num_retrieved=0,
            num_sources=0,
            answer_length=0,
            error=error_msg[:200]
        )

    def track_query(self, query: str, response_time: float,
                   num_retrieved: int, num_sources: int,
                   answer_length: int, error: str = None):
        """Track một query"""
        query_data = {
            'timestamp': datetime.now().isoformat(),
            'query': query[:100],
            'response_time': round(response_time, 2),
            'num_retrieved': num_retrieved,
            'num_sources': num_sources,
            'answer_length': answer_length,
            'error': error
        }
        self.current_session['queries'].append(query_data)
        
    def get_session_stats(self) -> Dict:
        """Lấy thống kê của session hiện tại"""
        if not self.current_session['queries']:
            return {}
        
        queries = self.current_session['queries']
        response_times = [q['response_time'] for q in queries if q['error'] is None]
        
        stats = {
            'total_queries': len(queries),
            'successful_queries': len(response_times),
            'failed_queries': len([q for q in queries if q['error'] is not None]),
            'avg_response_time': round(sum(response_times) / len(response_times), 2) if response_times else 0,
            'min_response_time': round(min(response_times), 2) if response_times else 0,
            'max_response_time': round(max(response_times), 2) if response_times else 0,
            'avg_sources': round(sum(q['num_sources'] for q in queries) / len(queries), 1),
            'avg_answer_length': round(sum(q['answer_length'] for q in queries) / len(queries), 0)
        }
        return stats
    
    def save_session(self):
        """Lưu session vào file"""
        if not self.current_session['queries']:
            return
        
        if os.path.exists(self.log_file):
            with open(self.log_file, 'r', encoding='utf-8') as f:
                try:
                    data = json.load(f)
                except:
                    data = {'sessions': []}
        else:
            data = {'sessions': []}
        
        data['sessions'].append(self.current_session)
        
        with open(self.log_file, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
        
        print(f"✅ Đã lưu metrics vào {self.log_file}")
    
    def get_all_stats(self) -> Dict:
        """Lấy thống kê tổng hợp từ tất cả sessions"""
        if not os.path.exists(self.log_file):
            return {}
        
        with open(self.log_file, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        all_queries = []
        for session in data['sessions']:
            all_queries.extend(session['queries'])
        
        if not all_queries:
            return {}
        
        response_times = [q['response_time'] for q in all_queries if q['error'] is None]
        
        stats = {
            'total_sessions': len(data['sessions']),
            'total_queries': len(all_queries),
            'successful_queries': len(response_times),
            'failed_queries': len([q for q in all_queries if q['error'] is not None]),
            'avg_response_time': round(sum(response_times) / len(response_times), 2) if response_times else 0,
            'min_response_time': round(min(response_times), 2) if response_times else 0,
            'max_response_time': round(max(response_times), 2) if response_times else 0,
            'success_rate': round(len(response_times) / len(all_queries) * 100, 1) if all_queries else 0
        }
        return stats


# Singleton instance
_metrics_tracker = None


def get_metrics_tracker():
    """Get singleton metrics tracker instance"""
    global _metrics_tracker
    if _metrics_tracker is None:
        _metrics_tracker = MetricsTracker()
    return _metrics_tracker
