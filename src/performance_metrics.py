# performance_metrics.py - Performance Monitoring and System Metrics
"""
Công cụ theo dõi hiệu suất hệ thống RAG

Metrics được theo dõi:
1. Response Time: Thời gian phản hồi cho mỗi câu hỏi
2. Cache Hit Rate: Tỷ lệ cache hit cho embedding và BM25
3. Retrieval Quality: Precision, Recall, MRR, NDCG
4. Generation Quality: BLEU, ROUGE, BERTScore
5. System Load: CPU, Memory usage
6. API Usage: Số lượng API calls, tokens used
7. Citation Accuracy: Chính xác của trích dẫn
"""

import time
import json
import os
from datetime import datetime
from typing import Dict, List, Tuple, Optional
from collections import defaultdict
import logging

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('rag_performance.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)


class PerformanceMetrics:
    """
    Theo dõi toàn bộ metrics hiệu suất của hệ thống RAG
    """
    
    def __init__(self, persist_file="metrics.json"):
        """
        Khởi tạo Performance Metrics
        
        Args:
            persist_file: File để lưu metrics
        """
        self.persist_file = persist_file
        self.metrics = {
            'response_times': [],
            'cache_hits': 0,
            'cache_misses': 0,
            'retrieval_metrics': [],
            'generation_metrics': [],
            'citation_metrics': [],
            'api_calls': 0,
            'total_tokens': 0,
            'errors': 0,
            'sessions': defaultdict(dict)
        }
        self.current_session_id = None
        self.session_start_time = None
        self.load_metrics()
    
    def load_metrics(self):
        """Load metrics từ file nếu tồn tại"""
        if os.path.exists(self.persist_file):
            try:
                with open(self.persist_file, 'r') as f:
                    loaded = json.load(f)
                    # Merge với default metrics
                    self.metrics.update(loaded)
                    logger.info(f"✅ Đã load metrics từ {self.persist_file}")
            except Exception as e:
                logger.warning(f"⚠️ Không thể load metrics: {e}")
    
    def save_metrics(self):
        """Lưu metrics vào file"""
        try:
            # Convert defaultdict to dict
            metrics_to_save = self.metrics.copy()
            metrics_to_save['sessions'] = dict(metrics_to_save['sessions'])
            
            with open(self.persist_file, 'w') as f:
                json.dump(metrics_to_save, f, indent=2, default=str)
            logger.debug(f"💾 Đã lưu metrics vào {self.persist_file}")
        except Exception as e:
            logger.error(f"❌ Lỗi khi lưu metrics: {e}")
    
    # ============== Session Management ==============
    
    def start_session(self, session_id: str):
        """Bắt đầu phiên làm việc mới"""
        self.current_session_id = session_id
        self.session_start_time = time.time()
        self.metrics['sessions'][session_id] = {
            'start_time': datetime.now().isoformat(),
            'queries': 0,
            'response_times': [],
            'errors': 0
        }
        logger.info(f"🔄 Bắt đầu session: {session_id}")
    
    def end_session(self, session_id: str):
        """Kết thúc phiên làm việc"""
        if session_id in self.metrics['sessions']:
            session = self.metrics['sessions'][session_id]
            session['end_time'] = datetime.now().isoformat()
            duration = time.time() - self.session_start_time if self.session_start_time else 0
            session['duration_seconds'] = duration
            
            logger.info(f"✅ Kết thúc session: {session_id}, duration: {duration:.2f}s")
        
        self.save_metrics()
    
    # ============== Response Time Tracking ==============
    
    def record_response_time(self, response_time: float, session_id: Optional[str] = None):
        """Ghi nhận thời gian phản hồi"""
        session = session_id or self.current_session_id
        
        self.metrics['response_times'].append({
            'timestamp': datetime.now().isoformat(),
            'response_time': response_time,
            'session_id': session
        })
        
        if session and session in self.metrics['sessions']:
            self.metrics['sessions'][session]['response_times'].append(response_time)
        
        logger.debug(f"⏱️  Response time: {response_time:.2f}s")
    
    def get_avg_response_time(self, session_id: Optional[str] = None) -> float:
        """Lấy thời gian phản hồi trung bình"""
        if session_id and session_id in self.metrics['sessions']:
            times = self.metrics['sessions'][session_id]['response_times']
            return sum(times) / len(times) if times else 0
        
        times = [m['response_time'] for m in self.metrics['response_times']]
        return sum(times) / len(times) if times else 0
    
    # ============== Cache Metrics ==============
    
    def record_cache_hit(self, cache_type: str = "embedding"):
        """Ghi nhận cache hit"""
        self.metrics['cache_hits'] += 1
        logger.debug(f"✅ Cache hit ({cache_type})")
    
    def record_cache_miss(self, cache_type: str = "embedding"):
        """Ghi nhận cache miss"""
        self.metrics['cache_misses'] += 1
        logger.debug(f"❌ Cache miss ({cache_type})")
    
    def get_cache_hit_rate(self) -> float:
        """Lấy tỷ lệ cache hit"""
        total = self.metrics['cache_hits'] + self.metrics['cache_misses']
        if total == 0:
            return 0.0
        return self.metrics['cache_hits'] / total
    
    # ============== Retrieval Metrics ==============
    
    def record_retrieval_metrics(self, 
                                metrics: Dict[str, float],
                                query: str,
                                session_id: Optional[str] = None):
        """
        Ghi nhận metrics retrieval
        
        Args:
            metrics: Dict chứa precision, recall, mrr, ndcg
            query: Câu query
            session_id: ID của session
        """
        session = session_id or self.current_session_id
        
        metric_record = {
            'timestamp': datetime.now().isoformat(),
            'query': query,
            'session_id': session,
            **metrics
        }
        
        self.metrics['retrieval_metrics'].append(metric_record)
        logger.debug(f"📊 Retrieval metrics recorded: {metrics}")
    
    def get_retrieval_stats(self) -> Dict[str, float]:
        """Lấy thống kê retrieval"""
        if not self.metrics['retrieval_metrics']:
            return {}
        
        metrics_list = self.metrics['retrieval_metrics']
        
        stats = {}
        for key in ['precision', 'recall', 'mrr', 'ndcg', 'hit_rate']:
            values = [m.get(key, 0) for m in metrics_list if key in m]
            if values:
                stats[f'{key}_avg'] = sum(values) / len(values)
                stats[f'{key}_min'] = min(values)
                stats[f'{key}_max'] = max(values)
        
        return stats
    
    # ============== Generation Metrics ==============
    
    def record_generation_metrics(self,
                                 metrics: Dict[str, float],
                                 question: str,
                                 session_id: Optional[str] = None):
        """
        Ghi nhận metrics generation
        
        Args:
            metrics: Dict chứa bleu, rouge, bertscore
            question: Câu hỏi
            session_id: ID của session
        """
        session = session_id or self.current_session_id
        
        metric_record = {
            'timestamp': datetime.now().isoformat(),
            'question': question,
            'session_id': session,
            **metrics
        }
        
        self.metrics['generation_metrics'].append(metric_record)
        logger.debug(f"🎯 Generation metrics recorded: {metrics}")
    
    def get_generation_stats(self) -> Dict[str, float]:
        """Lấy thống kê generation"""
        if not self.metrics['generation_metrics']:
            return {}
        
        metrics_list = self.metrics['generation_metrics']
        
        stats = {}
        for key in ['bleu', 'rouge1', 'rouge2', 'rougeL', 'bertscore']:
            values = [m.get(key, 0) for m in metrics_list if key in m]
            if values:
                stats[f'{key}_avg'] = sum(values) / len(values)
                stats[f'{key}_min'] = min(values)
                stats[f'{key}_max'] = max(values)
        
        return stats
    
    # ============== Citation Metrics ==============
    
    def record_citation_metrics(self,
                               accuracy: float,
                               completeness: float,
                               relevance: float,
                               session_id: Optional[str] = None):
        """
        Ghi nhận metrics của citations
        
        Args:
            accuracy: Chính xác của citation (0-1)
            completeness: Đầy đủ của citations (0-1)
            relevance: Độ liên quan của citations (0-1)
            session_id: ID của session
        """
        session = session_id or self.current_session_id
        
        metric_record = {
            'timestamp': datetime.now().isoformat(),
            'accuracy': accuracy,
            'completeness': completeness,
            'relevance': relevance,
            'session_id': session
        }
        
        self.metrics['citation_metrics'].append(metric_record)
        logger.debug(f"📚 Citation metrics recorded: accuracy={accuracy:.2f}, completeness={completeness:.2f}")
    
    def get_citation_stats(self) -> Dict[str, float]:
        """Lấy thống kê citations"""
        if not self.metrics['citation_metrics']:
            return {}
        
        metrics_list = self.metrics['citation_metrics']
        
        stats = {}
        for key in ['accuracy', 'completeness', 'relevance']:
            values = [m[key] for m in metrics_list if key in m]
            if values:
                stats[f'{key}_avg'] = sum(values) / len(values)
                stats[f'{key}_min'] = min(values)
                stats[f'{key}_max'] = max(values)
        
        return stats
    
    # ============== API Usage Tracking ==============
    
    def record_api_call(self, tokens_used: int = 0):
        """Ghi nhận API call"""
        self.metrics['api_calls'] += 1
        self.metrics['total_tokens'] += tokens_used
        logger.debug(f"🔗 API call recorded, tokens: {tokens_used}")
    
    def get_api_stats(self) -> Dict[str, int]:
        """Lấy thống kê API usage"""
        return {
            'total_api_calls': self.metrics['api_calls'],
            'total_tokens': self.metrics['total_tokens'],
            'avg_tokens_per_call': self.metrics['total_tokens'] / self.metrics['api_calls'] 
                                  if self.metrics['api_calls'] > 0 else 0
        }
    
    # ============== Error Tracking ==============
    
    def record_error(self, error_msg: str, error_type: str = "general"):
        """Ghi nhận lỗi"""
        self.metrics['errors'] += 1
        
        session = self.current_session_id
        if session and session in self.metrics['sessions']:
            self.metrics['sessions'][session]['errors'] += 1
        
        logger.error(f"❌ Error ({error_type}): {error_msg}")
    
    # ============== System Summary ==============
    
    def get_system_summary(self) -> Dict:
        """Lấy tóm tắt toàn hệ thống"""
        return {
            'response_time': {
                'average': self.get_avg_response_time(),
                'total_queries': len(self.metrics['response_times'])
            },
            'cache': {
                'hit_rate': self.get_cache_hit_rate(),
                'total_hits': self.metrics['cache_hits'],
                'total_misses': self.metrics['cache_misses']
            },
            'retrieval': self.get_retrieval_stats(),
            'generation': self.get_generation_stats(),
            'citations': self.get_citation_stats(),
            'api_usage': self.get_api_stats(),
            'total_errors': self.metrics['errors'],
            'total_sessions': len(self.metrics['sessions'])
        }
    
    def print_summary(self):
        """In tóm tắt metrics"""
        summary = self.get_system_summary()
        
        print("\n" + "="*60)
        print("📊 PERFORMANCE METRICS SUMMARY")
        print("="*60)
        
        print(f"\n⏱️  Response Time:")
        print(f"   Average: {summary['response_time']['average']:.2f}s")
        print(f"   Total queries: {summary['response_time']['total_queries']}")
        
        print(f"\n💾 Cache Performance:")
        print(f"   Hit rate: {summary['cache']['hit_rate']*100:.1f}%")
        print(f"   Total hits: {summary['cache']['total_hits']}")
        
        if summary['retrieval']:
            print(f"\n🔍 Retrieval Metrics:")
            for key, value in summary['retrieval'].items():
                print(f"   {key}: {value:.3f}")
        
        if summary['generation']:
            print(f"\n🎯 Generation Metrics:")
            for key, value in summary['generation'].items():
                print(f"   {key}: {value:.3f}")
        
        if summary['citations']:
            print(f"\n📚 Citation Metrics:")
            for key, value in summary['citations'].items():
                print(f"   {key}: {value:.3f}")
        
        print(f"\n🔗 API Usage:")
        for key, value in summary['api_usage'].items():
            print(f"   {key}: {value}")
        
        print(f"\n❌ Errors: {summary['total_errors']}")
        print(f"🎯 Total Sessions: {summary['total_sessions']}")
        print("="*60 + "\n")


# Singleton instance
_metrics_instance = None

def get_metrics_tracker() -> PerformanceMetrics:
    """Lấy global metrics tracker instance"""
    global _metrics_instance
    if _metrics_instance is None:
        _metrics_instance = PerformanceMetrics()
    return _metrics_instance


if __name__ == "__main__":
    # Test metrics tracking
    metrics = get_metrics_tracker()
    
    # Start session
    metrics.start_session("test_session_001")
    
    # Simulate some operations
    metrics.record_cache_hit()
    metrics.record_response_time(2.5)
    metrics.record_api_call(tokens_used=150)
    
    metrics.record_retrieval_metrics({
        'precision': 0.85,
        'recall': 0.90,
        'mrr': 0.88,
        'ndcg': 0.92
    }, query="test query")
    
    metrics.record_citation_metrics(
        accuracy=0.95,
        completeness=0.88,
        relevance=0.92
    )
    
    # End session
    metrics.end_session("test_session_001")
    
    # Print summary
    metrics.print_summary()
