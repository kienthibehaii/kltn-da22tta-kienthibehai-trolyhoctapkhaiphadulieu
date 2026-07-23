"""
analytics.py
────────────
Tracking user feedback và metrics để evaluate quality
"""

import json
from pathlib import Path
from datetime import datetime
from typing import Dict, List

class AnalyticsTracker:
    """Track user interactions, feedback, metrics"""

    def __init__(self, log_file: str = "analytics/interactions.jsonl"):
        self.log_file = Path(log_file)
        self.log_file.parent.mkdir(exist_ok=True)

    def log_interaction(self,
                       query: str,
                       answer: str,
                       mode: str,
                       chapter: str,
                       sources: List[str],
                       response_time: float):
        """Log a Q&A interaction"""
        record = {
            "timestamp": datetime.now().isoformat(),
            "query": query,
            "answer": answer[:500],  # First 500 chars
            "mode": mode,
            "chapter": chapter,
            "sources": sources,
            "response_time": response_time,
            "feedback": None  # User will rate later
        }
        with open(self.log_file, "a") as f:
            f.write(json.dumps(record, ensure_ascii=False) + "\n")

    def log_feedback(self,
                     query: str,
                     rating: int,  # 1-5 stars
                     comment: str = ""):
        """Log user feedback (thumbs up/down or rating)"""
        record = {
            "timestamp": datetime.now().isoformat(),
            "query": query,
            "rating": rating,
            "comment": comment,
            "type": "feedback"
        }
        with open(self.log_file, "a") as f:
            f.write(json.dumps(record, ensure_ascii=False) + "\n")

    def get_statistics(self) -> Dict:
        """Get usage statistics"""
        if not self.log_file.exists():
            return {}

        total = 0
        by_mode = {}
        by_chapter = {}
        avg_response_time = 0
        avg_rating = 0
        ratings = []

        with open(self.log_file) as f:
            for line in f:
                record = json.loads(line)
                total += 1

                if "mode" in record:
                    by_mode[record["mode"]] = by_mode.get(record["mode"], 0) + 1
                    by_chapter[record["chapter"]] = by_chapter.get(record["chapter"], 0) + 1
                    avg_response_time += record.get("response_time", 0)

                if "rating" in record and record["rating"]:
                    ratings.append(record["rating"])

        return {
            "total_interactions": total,
            "by_mode": by_mode,
            "by_chapter": by_chapter,
            "avg_response_time": avg_response_time / total if total > 0 else 0,
            "avg_rating": sum(ratings) / len(ratings) if ratings else 0,
            "total_ratings": len(ratings)
        }


# Helper function
def get_tracker() -> AnalyticsTracker:
    """Get analytics tracker instance"""
    return AnalyticsTracker()
