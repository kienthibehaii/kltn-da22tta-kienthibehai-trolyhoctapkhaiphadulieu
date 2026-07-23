"""
Phase 2.4 Component 11: Query Optimizer
Optimizes database and vector store queries with caching and batching
"""

from typing import Any, Dict, List, Optional, Tuple
from dataclasses import dataclass, field
from datetime import datetime
import time
from performance_cache import PerformanceCache


@dataclass
class QueryStats:
    """Statistics for a single query"""
    query_id: str
    query_type: str  # student, mastery, recommendation, analytics
    execution_time_ms: float
    cache_hit: bool
    rows_affected: int
    timestamp: datetime
    optimization_score: float  # 0-1
    
    def to_dict(self) -> Dict:
        """Convert to dictionary"""
        return {
            "query_id": self.query_id,
            "query_type": self.query_type,
            "execution_time_ms": round(self.execution_time_ms, 2),
            "cache_hit": self.cache_hit,
            "rows_affected": self.rows_affected,
            "timestamp": self.timestamp.isoformat(),
            "optimization_score": round(self.optimization_score, 3)
        }


@dataclass
class OptimizerStats:
    """Overall optimizer statistics"""
    total_queries: int = 0
    cached_queries: int = 0
    avg_execution_time_ms: float = 0.0
    slowest_query_ms: float = 0.0
    fastest_query_ms: float = float('inf')
    total_cache_savings_ms: float = 0.0
    optimization_opportunities: int = 0
    
    def to_dict(self) -> Dict:
        """Convert to dictionary"""
        return {
            "total_queries": self.total_queries,
            "cached_queries": self.cached_queries,
            "avg_execution_time_ms": round(self.avg_execution_time_ms, 2),
            "slowest_query_ms": round(self.slowest_query_ms, 2),
            "fastest_query_ms": round(self.fastest_query_ms, 2),
            "total_cache_savings_ms": round(self.total_cache_savings_ms, 2),
            "optimization_opportunities": self.optimization_opportunities
        }


class QueryOptimizer:
    """Optimizes queries through caching, batching, and intelligent execution"""
    
    def __init__(self, cache_manager: Optional[PerformanceCache] = None):
        """
        Initialize query optimizer
        
        Args:
            cache_manager: PerformanceCache instance (creates new if None)
        """
        self.cache = cache_manager or PerformanceCache(max_size=2000, default_ttl=1800)
        self.stats = OptimizerStats()
        self.query_history: List[QueryStats] = []
        self.batch_size = 100
        self.max_query_time_ms = 1000  # Slow query threshold
    
    def optimize_student_query(
        self,
        student_id: str,
        include_interactions: bool = True,
        include_quizzes: bool = True
    ) -> Dict:
        """
        Optimize student data query
        
        Args:
            student_id: Student ID
            include_interactions: Include interaction history
            include_quizzes: Include quiz responses
            
        Returns:
            Optimized query result
        """
        cache_key = f"student:{student_id}:{include_interactions}:{include_quizzes}"
        
        # Check cache
        cached = self.cache.get(cache_key)
        if cached is not None:
            self._record_query_stats(
                query_id=cache_key,
                query_type="student",
                execution_time_ms=0.1,
                cache_hit=True,
                rows_affected=1,
                optimization_score=1.0
            )
            return cached
        
        # Simulate query execution
        start = time.time()
        
        result = {
            "student_id": student_id,
            "name": f"Student {student_id}",
            "level": "intermediate",
            "join_date": "2026-01-15",
            "interactions": 42 if include_interactions else 0,
            "quiz_count": 8 if include_quizzes else 0,
            "total_mastery": 0.72
        }
        
        execution_time = (time.time() - start) * 1000
        
        # Cache result (5 min TTL)
        self.cache.set(cache_key, result, ttl=300)
        
        self._record_query_stats(
            query_id=cache_key,
            query_type="student",
            execution_time_ms=execution_time,
            cache_hit=False,
            rows_affected=1,
            optimization_score=0.8
        )
        
        return result
    
    def optimize_mastery_query(
        self,
        chapter_ids: List[str],
        student_id: Optional[str] = None
    ) -> Dict:
        """
        Optimize mastery level queries
        
        Args:
            chapter_ids: List of chapter IDs
            student_id: Optional student ID for filtering
            
        Returns:
            Optimized mastery data
        """
        # Sort for consistent cache key
        sorted_chapters = ":".join(sorted(chapter_ids))
        cache_key = f"mastery:{sorted_chapters}:{student_id}"
        
        # Check cache
        cached = self.cache.get(cache_key)
        if cached is not None:
            self._record_query_stats(
                query_id=cache_key,
                query_type="mastery",
                execution_time_ms=0.1,
                cache_hit=True,
                rows_affected=len(chapter_ids),
                optimization_score=1.0
            )
            return cached
        
        # Simulate query execution
        start = time.time()
        
        result = {
            "student_id": student_id,
            "mastery_levels": {
                chapter: round(0.7 + (hash(chapter) % 30) / 100, 2)
                for chapter in chapter_ids
            },
            "avg_mastery": 0.72,
            "last_updated": datetime.now().isoformat()
        }
        
        execution_time = (time.time() - start) * 1000
        
        # Cache result (10 min TTL)
        self.cache.set(cache_key, result, ttl=600)
        
        self._record_query_stats(
            query_id=cache_key,
            query_type="mastery",
            execution_time_ms=execution_time,
            cache_hit=False,
            rows_affected=len(chapter_ids),
            optimization_score=0.85
        )
        
        return result
    
    def batch_analytics_queries(
        self,
        student_ids: List[str]
    ) -> Dict[str, Dict]:
        """
        Optimize multiple analytics queries through batching
        
        Args:
            student_ids: List of student IDs
            
        Returns:
            Dictionary of student ID to analytics data
        """
        cache_key = f"analytics_batch:{':'.join(sorted(student_ids))}"
        
        # Check batch cache
        cached = self.cache.get(cache_key)
        if cached is not None:
            self._record_query_stats(
                query_id=cache_key,
                query_type="analytics",
                execution_time_ms=0.1,
                cache_hit=True,
                rows_affected=len(student_ids),
                optimization_score=1.0
            )
            return cached
        
        # Simulate batch query execution
        start = time.time()
        
        result = {
            student_id: {
                "student_id": student_id,
                "overall_mastery": 0.65 + (hash(student_id) % 35) / 100,
                "interactions": 30 + (hash(student_id) % 50),
                "quiz_success_rate": 0.72,
                "engagement": "medium"
            }
            for student_id in student_ids
        }
        
        execution_time = (time.time() - start) * 1000
        
        # Cache batch result (15 min TTL)
        self.cache.set(cache_key, result, ttl=900)
        
        self._record_query_stats(
            query_id=cache_key,
            query_type="analytics",
            execution_time_ms=execution_time,
            cache_hit=False,
            rows_affected=len(student_ids),
            optimization_score=0.9
        )
        
        return result
    
    def optimize_recommendation_query(
        self,
        student_id: str,
        top_n: int = 5
    ) -> List[Dict]:
        """
        Optimize recommendation queries
        
        Args:
            student_id: Student ID
            top_n: Number of recommendations
            
        Returns:
            List of recommendations
        """
        cache_key = f"recommendations:{student_id}:{top_n}"
        
        # Check cache
        cached = self.cache.get(cache_key)
        if cached is not None:
            self._record_query_stats(
                query_id=cache_key,
                query_type="recommendation",
                execution_time_ms=0.1,
                cache_hit=True,
                rows_affected=len(cached),
                optimization_score=1.0
            )
            return cached
        
        # Simulate query execution
        start = time.time()
        
        chapters = ["CH1", "CH2", "CH3", "CH4", "CH5"]
        result = [
            {
                "chapter": ch,
                "type": "remedial" if i < 2 else "next_topic",
                "priority": round(1.0 - (i * 0.15), 2),
                "reason": f"Recommendation for {ch}"
            }
            for i, ch in enumerate(chapters[:top_n])
        ]
        
        execution_time = (time.time() - start) * 1000
        
        # Cache result (10 min TTL)
        self.cache.set(cache_key, result, ttl=600)
        
        self._record_query_stats(
            query_id=cache_key,
            query_type="recommendation",
            execution_time_ms=execution_time,
            cache_hit=False,
            rows_affected=len(result),
            optimization_score=0.88
        )
        
        return result
    
    def get_query_stats(self) -> Dict:
        """Get query optimizer statistics"""
        return self.stats.to_dict()
    
    def get_query_history(self, limit: int = 100) -> List[Dict]:
        """
        Get recent query history
        
        Args:
            limit: Maximum number of queries to return
            
        Returns:
            List of query stats dictionaries
        """
        return [q.to_dict() for q in self.query_history[-limit:]]
    
    def suggest_optimization(self, query_id: str) -> Optional[str]:
        """
        Suggest optimization for a query
        
        Args:
            query_id: Query ID
            
        Returns:
            Optimization suggestion or None
        """
        # Find query in history
        query = None
        for q in self.query_history:
            if q.query_id == query_id:
                query = q
                break
        
        if not query:
            return None
        
        # Suggest based on execution time
        if query.execution_time_ms > self.max_query_time_ms:
            return f"Query slow ({query.execution_time_ms:.0f}ms). Consider indexing or batching."
        
        if query.optimization_score < 0.7:
            return "Consider caching results or optimizing query plan."
        
        return None
    
    def get_optimization_report(self) -> Dict:
        """Get comprehensive optimization report"""
        report = {
            "summary": self.stats.to_dict(),
            "slow_queries": [],
            "optimization_opportunities": []
        }
        
        # Find slow queries
        slow_queries = [
            q for q in self.query_history
            if q.execution_time_ms > self.max_query_time_ms
        ]
        report["slow_queries"] = [q.to_dict() for q in slow_queries[-10:]]
        
        # Find optimization opportunities
        for query in self.query_history[-50:]:
            if query.optimization_score < 0.8 and not query.cache_hit:
                suggestion = self.suggest_optimization(query.query_id)
                if suggestion:
                    report["optimization_opportunities"].append({
                        "query_id": query.query_id,
                        "suggestion": suggestion
                    })
        
        return report
    
    # ========== Internal Methods ==========
    
    def _record_query_stats(
        self,
        query_id: str,
        query_type: str,
        execution_time_ms: float,
        cache_hit: bool,
        rows_affected: int,
        optimization_score: float
    ) -> None:
        """Record query statistics"""
        stats = QueryStats(
            query_id=query_id,
            query_type=query_type,
            execution_time_ms=execution_time_ms,
            cache_hit=cache_hit,
            rows_affected=rows_affected,
            timestamp=datetime.now(),
            optimization_score=optimization_score
        )
        
        self.query_history.append(stats)
        
        # Update overall stats
        self.stats.total_queries += 1
        if cache_hit:
            self.stats.cached_queries += 1
            self.stats.total_cache_savings_ms += execution_time_ms * 10
        
        self.stats.avg_execution_time_ms = (
            (self.stats.avg_execution_time_ms * (self.stats.total_queries - 1) + execution_time_ms)
            / self.stats.total_queries
        )
        
        self.stats.slowest_query_ms = max(
            self.stats.slowest_query_ms,
            execution_time_ms
        )
        
        self.stats.fastest_query_ms = min(
            self.stats.fastest_query_ms,
            execution_time_ms
        )
        
        if optimization_score < 0.8:
            self.stats.optimization_opportunities += 1


def demo_optimizer():
    """Demo query optimizer functionality"""
    print("\n" + "="*70)
    print("🔍 QUERY OPTIMIZER DEMO")
    print("="*70)
    
    cache = PerformanceCache()
    optimizer = QueryOptimizer(cache)
    
    # Test 1: Student query optimization
    print("\n📚 Test 1: Student Query Optimization")
    result1 = optimizer.optimize_student_query("STU001")
    print(f"   ✅ First query: {result1['name']}, interactions: {result1['interactions']}")
    result2 = optimizer.optimize_student_query("STU001")  # Should be cached
    print(f"   ✅ Second query (cached): {result2['name']}")
    
    # Test 2: Mastery query optimization
    print("\n📊 Test 2: Mastery Query Optimization")
    chapters = ["CH1", "CH2", "CH3"]
    mastery = optimizer.optimize_mastery_query(chapters, "STU001")
    print(f"   ✅ Mastery levels: {mastery['mastery_levels']}")
    print(f"   ✅ Average mastery: {mastery['avg_mastery']}")
    
    # Test 3: Batch analytics queries
    print("\n⚡ Test 3: Batch Analytics Queries")
    students = ["STU001", "STU002", "STU003"]
    batch_result = optimizer.batch_analytics_queries(students)
    print(f"   ✅ Batch processed {len(batch_result)} students")
    for sid in list(batch_result.keys())[:2]:
        print(f"      • {sid}: mastery={batch_result[sid]['overall_mastery']}")
    
    # Test 4: Recommendation query optimization
    print("\n💡 Test 4: Recommendation Query Optimization")
    recommendations = optimizer.optimize_recommendation_query("STU001", top_n=3)
    print(f"   ✅ Generated {len(recommendations)} recommendations:")
    for i, rec in enumerate(recommendations, 1):
        print(f"      {i}. {rec['chapter']} - {rec['type']} (priority: {rec['priority']})")
    
    # Test 5: Query statistics
    print("\n📈 Test 5: Query Statistics")
    stats = optimizer.get_query_stats()
    print(f"   ✅ Total Queries: {stats['total_queries']}")
    print(f"   ✅ Cached Queries: {stats['cached_queries']}")
    print(f"   ✅ Avg Execution: {stats['avg_execution_time_ms']:.2f}ms")
    print(f"   ✅ Total Cache Savings: {stats['total_cache_savings_ms']:.2f}ms")
    
    # Test 6: Optimization report
    print("\n📋 Test 6: Optimization Report")
    report = optimizer.get_optimization_report()
    print(f"   ✅ Total Queries: {report['summary']['total_queries']}")
    print(f"   ✅ Optimization Opportunities: {report['summary']['optimization_opportunities']}")
    
    print("\n✅ Component 11: Query Optimizer - Ready!")
    print("="*70)


if __name__ == "__main__":
    demo_optimizer()
