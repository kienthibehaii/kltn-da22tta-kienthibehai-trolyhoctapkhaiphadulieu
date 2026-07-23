"""
Analytics Dashboard - Student and system analytics
Phase 2.3 - Component 9
"""

from typing import Dict, List, Optional
from dataclasses import dataclass
from datetime import datetime


@dataclass
class StudentMetrics:
    """Student learning metrics"""
    student_id: str
    overall_mastery: float  # 0-1
    total_interactions: int
    quiz_success_rate: float  # 0-1
    average_response_quality: float  # 0-1
    learning_pace: str  # slow/medium/fast
    current_focus: str  # current chapter
    weak_areas: List[str]
    strong_areas: List[str]
    time_on_platform: int  # hours
    last_active: datetime
    
    def to_dict(self):
        """Convert to dictionary"""
        return {
            "student_id": self.student_id,
            "overall_mastery": self.overall_mastery,
            "total_interactions": self.total_interactions,
            "quiz_success_rate": self.quiz_success_rate,
            "average_response_quality": self.average_response_quality,
            "learning_pace": self.learning_pace,
            "current_focus": self.current_focus,
            "weak_areas": self.weak_areas,
            "strong_areas": self.strong_areas,
            "time_on_platform": self.time_on_platform,
            "last_active": self.last_active.isoformat()
        }


@dataclass
class SystemMetrics:
    """System performance metrics"""
    total_students: int
    average_mastery: float
    total_interactions: int
    system_uptime: float  # percentage
    average_response_time: float  # ms
    cache_hit_rate: float  # percentage
    total_quizzes_generated: int
    total_recommendations: int
    
    def to_dict(self):
        """Convert to dictionary"""
        return {
            "total_students": self.total_students,
            "average_mastery": self.average_mastery,
            "total_interactions": self.total_interactions,
            "system_uptime": self.system_uptime,
            "average_response_time": self.average_response_time,
            "cache_hit_rate": self.cache_hit_rate,
            "total_quizzes_generated": self.total_quizzes_generated,
            "total_recommendations": self.total_recommendations
        }


class AnalyticsDashboard:
    """Analytics dashboard for tracking performance"""
    
    def __init__(self):
        """Initialize dashboard"""
        self.student_data = {}
        self.system_metrics = None
    
    def calculate_student_analytics(
        self,
        student_id: str,
        mastery_levels: Dict[str, float],
        interactions: List[Dict],
        quiz_responses: List[Dict]
    ) -> StudentMetrics:
        """Calculate comprehensive student analytics"""
        
        # Overall mastery
        overall_mastery = (
            sum(mastery_levels.values()) / len(mastery_levels)
            if mastery_levels else 0.0
        )
        
        # Quiz success rate
        if quiz_responses:
            correct = sum(1 for q in quiz_responses if q.get("is_correct", False))
            quiz_success_rate = correct / len(quiz_responses)
        else:
            quiz_success_rate = 0.0
        
        # Average response quality
        if interactions:
            avg_quality = sum(
                i.get("quality", 0.5) for i in interactions
            ) / len(interactions)
        else:
            avg_quality = 0.5
        
        # Identify weak and strong areas
        weak_areas = [
            ch for ch, m in mastery_levels.items() if m < 0.6
        ]
        strong_areas = [
            ch for ch, m in mastery_levels.items() if m > 0.85
        ]
        
        # Calculate time on platform
        time_hours = sum(i.get("duration", 0) for i in interactions) // 60
        
        metrics = StudentMetrics(
            student_id=student_id,
            overall_mastery=overall_mastery,
            total_interactions=len(interactions),
            quiz_success_rate=quiz_success_rate,
            average_response_quality=avg_quality,
            learning_pace="medium",  # Would be calculated
            current_focus="CH2",  # Would come from student profile
            weak_areas=weak_areas,
            strong_areas=strong_areas,
            time_on_platform=time_hours,
            last_active=datetime.now()
        )
        
        self.student_data[student_id] = metrics
        return metrics
    
    def get_student_progress_chart_data(
        self,
        student_id: str,
        num_weeks: int = 4
    ) -> Dict:
        """Get student progress data for chart"""
        
        # Generate sample data (in real app, retrieve from database)
        weeks = []
        mastery_values = []
        
        for week in range(num_weeks):
            weeks.append(f"Week {week + 1}")
            mastery_values.append(0.5 + (week * 0.1))  # Simulated progression
        
        return {
            "labels": weeks,
            "mastery": mastery_values,
            "type": "line",
            "title": f"Mastery Progress - {student_id}"
        }
    
    def get_topic_heatmap_data(
        self,
        mastery_levels: Dict[str, float]
    ) -> Dict:
        """Get heatmap data (difficulty vs mastery)"""
        
        heatmap_data = []
        
        for chapter, mastery in mastery_levels.items():
            heatmap_data.append({
                "chapter": chapter,
                "mastery": mastery,
                "difficulty": 0.5,  # Would calculate from content
                "color_intensity": mastery  # Green when high
            })
        
        return {"data": heatmap_data}
    
    def get_strategy_effectiveness(
        self,
        strategy_usage: Dict[str, int],
        strategy_success: Dict[str, int]
    ) -> Dict:
        """Get teaching strategy effectiveness"""
        
        effectiveness = {}
        
        for strategy, count in strategy_usage.items():
            success_count = strategy_success.get(strategy, 0)
            if count > 0:
                effectiveness[strategy] = success_count / count
            else:
                effectiveness[strategy] = 0.0
        
        return effectiveness
    
    def calculate_system_health(
        self,
        all_students: List[Dict],
        response_times: List[float],
        uptime_hours: float,
        total_hours: float = 720  # 30 days
    ) -> SystemMetrics:
        """Calculate overall system health metrics"""
        
        # Average mastery across all students
        all_mastery = []
        for student in all_students:
            mastery = student.get("mastery_levels", {})
            if mastery:
                avg = sum(mastery.values()) / len(mastery)
                all_mastery.append(avg)
        
        avg_system_mastery = (
            sum(all_mastery) / len(all_mastery) if all_mastery else 0.0
        )
        
        # Average response time
        avg_response_time = (
            sum(response_times) / len(response_times)
            if response_times else 0.0
        )
        
        # Uptime percentage
        uptime_percentage = (uptime_hours / total_hours) * 100
        
        metrics = SystemMetrics(
            total_students=len(all_students),
            average_mastery=avg_system_mastery,
            total_interactions=sum(
                len(s.get("interactions", [])) for s in all_students
            ),
            system_uptime=uptime_percentage,
            average_response_time=avg_response_time,
            cache_hit_rate=85.0,  # Would calculate from cache logs
            total_quizzes_generated=150,  # Would track
            total_recommendations=500  # Would track
        )
        
        self.system_metrics = metrics
        return metrics
    
    def get_learning_analytics_summary(
        self,
        student_id: str
    ) -> Dict:
        """Get comprehensive learning analytics for a student"""
        
        if student_id not in self.student_data:
            return {"error": "Student not found"}
        
        metrics = self.student_data[student_id]
        
        return {
            "student_id": student_id,
            "metrics": metrics.to_dict(),
            "progress_chart": self.get_student_progress_chart_data(student_id),
            "summary": {
                "mastery_level": "Intermediate" if metrics.overall_mastery > 0.6 else "Beginner",
                "next_focus": metrics.weak_areas[0] if metrics.weak_areas else "Advanced topics",
                "learning_efficiency": metrics.average_response_quality,
                "engagement": "High" if metrics.total_interactions > 50 else "Medium" if metrics.total_interactions > 20 else "Low"
            }
        }
    
    def demo_analytics(self):
        """Demo analytics dashboard"""
        
        print("\n" + "="*70)
        print("📊 ANALYTICS DASHBOARD DEMO")
        print("="*70)
        
        # Sample student metrics
        mastery = {"CH1": 0.9, "CH2": 0.8, "CH3": 0.5, "CH4": 0.3}
        interactions = [
            {"quality": 0.9, "duration": 2700},
            {"quality": 0.85, "duration": 3600},
            {"quality": 0.8, "duration": 3000},
        ]
        quiz_responses = [
            {"is_correct": True},
            {"is_correct": True},
            {"is_correct": False},
            {"is_correct": True},
        ]
        
        metrics = self.calculate_student_analytics(
            "STU001", mastery, interactions, quiz_responses
        )
        
        print(f"\n👤 Student Metrics (STU001):")
        print(f"   📈 Overall Mastery: {metrics.overall_mastery*100:.1f}%")
        print(f"   📊 Total Interactions: {metrics.total_interactions}")
        print(f"   ✅ Quiz Success Rate: {metrics.quiz_success_rate*100:.1f}%")
        print(f"   ⭐ Response Quality: {metrics.average_response_quality*100:.1f}%")
        print(f"   ⏱️  Time on Platform: {metrics.time_on_platform} hours")
        
        if metrics.weak_areas:
            print(f"   ⚠️  Weak Areas: {', '.join(metrics.weak_areas)}")
        if metrics.strong_areas:
            print(f"   ✨ Strong Areas: {', '.join(metrics.strong_areas)}")
        
        # System metrics
        all_students = [
            {"mastery_levels": mastery, "interactions": interactions},
            {"mastery_levels": {"CH1": 0.7, "CH2": 0.6}, "interactions": []},
        ]
        response_times = [45.2, 52.1, 48.9, 51.5, 49.2]
        
        system_metrics = self.calculate_system_health(
            all_students, response_times, 729
        )
        
        print(f"\n🖥️  System Metrics:")
        print(f"   👥 Total Students: {system_metrics.total_students}")
        print(f"   📈 Average Mastery: {system_metrics.average_mastery*100:.1f}%")
        print(f"   📊 Total Interactions: {system_metrics.total_interactions}")
        print(f"   ⚡ Avg Response Time: {system_metrics.average_response_time:.1f}ms")
        print(f"   ⬆️  System Uptime: {system_metrics.system_uptime:.1f}%")
        print(f"   💾 Cache Hit Rate: {system_metrics.cache_hit_rate:.1f}%")
        print(f"   📝 Quizzes Generated: {system_metrics.total_quizzes_generated}")
        print(f"   💡 Recommendations: {system_metrics.total_recommendations}")
        
        # Get learning summary
        summary = self.get_learning_analytics_summary("STU001")
        print(f"\n📋 Learning Analytics Summary:")
        if "summary" in summary:
            s = summary["summary"]
            print(f"   Level: {s['mastery_level']}")
            print(f"   Next Focus: {s['next_focus']}")
            print(f"   Efficiency: {s['learning_efficiency']*100:.1f}%")
            print(f"   Engagement: {s['engagement']}")


if __name__ == "__main__":
    dashboard = AnalyticsDashboard()
    dashboard.demo_analytics()
    print("\n✅ Component 9: Analytics Dashboard - Ready!")
