# educational_engine/learning_context_manager.py
"""
Learning Context Manager

Tracks user learning state and personalizes responses:
- User learning profile (topics, level, progress)
- Learning patterns and preferences
- Weak areas and strengths
- Recommended difficulty level
- Personalization hints
"""

from typing import Dict, List, Optional
from datetime import datetime, timedelta
import json
from pymongo import MongoClient
import os
from dotenv import load_dotenv

load_dotenv()


class LearningContextManager:
    """
    Manages user learning context for personalization
    """

    def __init__(self):
        # MongoDB connection for user profiles
        mongo_uri = os.getenv("MONGODB_URI", "mongodb://localhost:27017")
        self.client = MongoClient(mongo_uri)
        self.db = self.client.get_database("rag_system")
        self.profiles_collection = self.db.user_learning_profiles
        self.interactions_collection = self.db.learning_interactions

        # Create indexes for performance
        self.profiles_collection.create_index("user_id", unique=True)
        self.interactions_collection.create_index("user_id")
        self.interactions_collection.create_index("timestamp")

    def build_user_profile(self, user_id: str) -> Dict:
        """
        Build or retrieve user learning profile

        Returns comprehensive user profile
        """

        # Try to get existing profile
        profile = self.profiles_collection.find_one({"user_id": user_id})

        if profile:
            profile['_id'] = str(profile['_id'])
            return profile

        # Create new profile
        new_profile = {
            'user_id': user_id,
            'created_at': datetime.utcnow(),
            'last_updated': datetime.utcnow(),
            'learning_level': 'intermediate',
            'topics_explored': [],
            'favorite_topics': [],
            'weak_areas': [],
            'strong_areas': [],
            'total_interactions': 0,
            'total_quiz_score': 0,
            'average_quiz_score': 0,
            'preferred_teaching_style': 'mixed',  # analogy, examples, steps
            'preferred_difficulty': 'intermediate',
            'last_30_days_topics': [],
            'learning_pattern': 'sporadic',  # sporadic, consistent, intensive, casual
            'engagement_level': 'medium',  # low, medium, high
            'metadata': {
                'questions_asked': 0,
                'quizzes_taken': 0,
                'average_response_time': 0,
                'learning_velocity': 'steady'  # fast, steady, slow
            }
        }

        self.profiles_collection.insert_one(new_profile)
        new_profile['_id'] = str(new_profile['_id'])
        return new_profile

    def track_interaction(
        self,
        user_id: str,
        question: str,
        question_type: str,
        concepts: List[str],
        difficulty_used: str,
        timestamp: str = None
    ) -> None:
        """
        Track user interaction for learning profile updates
        """

        if timestamp is None:
            timestamp = datetime.utcnow().isoformat()

        interaction = {
            'user_id': user_id,
            'question': question,
            'question_type': question_type,
            'concepts': concepts,
            'difficulty_used': difficulty_used,
            'timestamp': timestamp,
            'unix_timestamp': datetime.utcnow()
        }

        self.interactions_collection.insert_one(interaction)

        # Update user profile
        self._update_profile_from_interaction(user_id, question_type, concepts)

    def detect_learning_pattern(self, user_id: str, window_days: int = 30) -> Dict:
        """
        Detect user's learning pattern over time window

        Returns pattern analysis
        """

        cutoff_date = datetime.utcnow() - timedelta(days=window_days)

        interactions = list(
            self.interactions_collection.find({
                'user_id': user_id,
                'unix_timestamp': {'$gte': cutoff_date}
            })
        )

        if not interactions:
            return {
                'pattern': 'no_data',
                'frequency': 'none',
                'consistency': 'unknown',
                'intensity': 'none',
                'favorite_types': [],
                'total_interactions': 0
            }

        # Analyze patterns
        dates = [datetime.fromisoformat(i['timestamp']) for i in interactions]
        dates = sorted(dates)

        # Calculate frequency
        if len(dates) > 1:
            days_span = (dates[-1] - dates[0]).days
            frequency = len(dates) / max(1, days_span)
        else:
            frequency = 0

        # Determine pattern
        if frequency > 0.5:  # More than once per 2 days
            pattern = 'intensive'
        elif frequency > 0.1:  # At least once per 10 days
            pattern = 'consistent'
        else:
            pattern = 'sporadic'

        # Favorite question types
        type_counts = {}
        for interaction in interactions:
            qtype = interaction.get('question_type', 'unknown')
            type_counts[qtype] = type_counts.get(qtype, 0) + 1

        favorite_types = sorted(type_counts.items(), key=lambda x: x[1], reverse=True)

        return {
            'pattern': pattern,
            'frequency': frequency,
            'days_active': len(set((d.date() for d in dates))),
            'total_interactions': len(interactions),
            'favorite_types': [t[0] for t in favorite_types[:3]],
            'favorite_topics': self._get_favorite_topics(interactions),
            'window_days': window_days
        }

    def recommend_difficulty_level(self, user_id: str) -> str:
        """
        Recommend difficulty level based on user history and performance

        Returns: 'beginner' | 'intermediate' | 'advanced'
        """

        profile = self.build_user_profile(user_id)

        # Factors in recommendation
        stored_preference = profile.get('preferred_difficulty', 'intermediate')
        avg_quiz_score = profile.get('average_quiz_score', 0)
        learning_level = profile.get('learning_level', 'intermediate')

        # Quiz score based recommendation
        if avg_quiz_score > 0.85:
            score_recommendation = 'advanced'
        elif avg_quiz_score > 0.65:
            score_recommendation = 'intermediate'
        else:
            score_recommendation = 'beginner'

        # Combine recommendations
        if score_recommendation == 'advanced' and learning_level != 'beginner':
            return 'advanced'
        elif score_recommendation == 'beginner':
            return 'beginner'
        else:
            return 'intermediate'

    def identify_weak_areas(self, user_id: str, window_days: int = 90) -> List[str]:
        """
        Identify user's weak areas based on interaction history

        Topics where user has lower scores or struggles
        """

        profile = self.build_user_profile(user_id)
        weak_areas = profile.get('weak_areas', [])

        return weak_areas[:5]

    def identify_strong_areas(self, user_id: str) -> List[str]:
        """
        Identify user's strong areas

        Topics where user has high scores or mastery
        """

        profile = self.build_user_profile(user_id)
        strong_areas = profile.get('strong_areas', [])

        return strong_areas[:5]

    def personalize_response(
        self,
        response: Dict,
        user_profile: Dict
    ) -> Dict:
        """
        Personalize response based on user profile

        Adjusts difficulty, teaching style, examples based on history
        """

        personalized = response.copy()

        # Adjust difficulty based on user level
        user_level = user_profile.get('learning_level', 'intermediate')
        personalized['difficulty_level'] = user_level

        # Add personalization metadata
        personalized['personalization'] = {
            'based_on_user': True,
            'user_learning_level': user_level,
            'recommended_for_weak_areas': user_profile.get('weak_areas', [])[:2],
            'suggested_followup': self._suggest_followup(user_profile)
        }

        return personalized

    def _update_profile_from_interaction(
        self,
        user_id: str,
        question_type: str,
        concepts: List[str]
    ) -> None:
        """
        Update user profile based on new interaction
        """

        from bson import ObjectId

        try:
            profile = self.profiles_collection.find_one({"user_id": user_id})

            if not profile:
                return

            # Update metrics
            updates = {
                'last_updated': datetime.utcnow(),
                'metadata.questions_asked': profile.get('metadata', {}).get('questions_asked', 0) + 1
            }

            # Track topics
            current_topics = profile.get('topics_explored', [])
            for concept in concepts:
                if concept not in current_topics:
                    current_topics.append(concept)

            updates['topics_explored'] = current_topics

            # Track recent topics (last 30 days)
            last_30_topics = profile.get('last_30_days_topics', [])
            for concept in concepts:
                if concept not in last_30_topics:
                    last_30_topics.append(concept)

            updates['last_30_days_topics'] = last_30_topics[-20:]  # Keep last 20

            self.profiles_collection.update_one(
                {"user_id": user_id},
                {"$set": updates}
            )
        except Exception as e:
            print(f"⚠️ Profile update error: {e}")

    def _get_favorite_topics(self, interactions: List[Dict]) -> List[str]:
        """
        Extract favorite topics from interactions
        """

        topic_counts = {}
        for interaction in interactions:
            concepts = interaction.get('concepts', [])
            for concept in concepts:
                topic_counts[concept] = topic_counts.get(concept, 0) + 1

        # Sort by frequency
        favorite = sorted(topic_counts.items(), key=lambda x: x[1], reverse=True)
        return [t[0] for t in favorite[:5]]

    def _suggest_followup(self, user_profile: Dict) -> str:
        """
        Suggest follow-up topic based on user profile
        """

        weak_areas = user_profile.get('weak_areas', [])

        if weak_areas:
            return f"Consider reviewing {weak_areas[0]}"

        favorite_topics = user_profile.get('last_30_days_topics', [])
        if favorite_topics:
            return f"Deepen your knowledge of {favorite_topics[0]}"

        return "Explore related topics"

    def get_timestamp(self) -> str:
        """Get current timestamp in ISO format"""
        return datetime.utcnow().isoformat()

    def get_learning_summary(self, user_id: str) -> Dict:
        """
        Get comprehensive learning summary for user

        Used for dashboard/profile display
        """

        profile = self.build_user_profile(user_id)
        pattern = self.detect_learning_pattern(user_id)

        summary = {
            'user_id': user_id,
            'learning_level': profile.get('learning_level', 'intermediate'),
            'total_questions': profile.get('metadata', {}).get('questions_asked', 0),
            'topics_explored': len(profile.get('topics_explored', [])),
            'favorite_topics': profile.get('favorite_topics', [])[:3],
            'weak_areas': profile.get('weak_areas', [])[:3],
            'strong_areas': profile.get('strong_areas', [])[:3],
            'learning_pattern': pattern['pattern'],
            'engagement_level': profile.get('engagement_level', 'medium'),
            'quiz_performance': {
                'total_taken': profile.get('metadata', {}).get('quizzes_taken', 0),
                'average_score': profile.get('average_quiz_score', 0)
            },
            'recommendations': self._get_recommendations(profile, pattern)
        }

        return summary

    def _get_recommendations(self, profile: Dict, pattern: Dict) -> List[str]:
        """
        Generate recommendations for user
        """

        recommendations = []

        # Based on engagement
        if pattern['total_interactions'] < 5:
            recommendations.append("Keep learning! You're just getting started")

        # Based on weak areas
        weak_areas = profile.get('weak_areas', [])
        if weak_areas:
            recommendations.append(f"Focus on strengthening {weak_areas[0]}")

        # Based on learning pattern
        if pattern['pattern'] == 'sporadic':
            recommendations.append("Try to maintain consistent learning habits")

        return recommendations[:3]

    def track_confusion_signal(
        self,
        user_id: str,
        question_id: str,
        confusion_signals: Dict
    ) -> None:
        """
        Track confusion signals for future prediction

        Args:
            user_id: User ID
            question_id: Question ID
            confusion_signals: {
                're_asked_count': int,
                'asked_for_simpler': bool,
                'asked_for_example': bool,
                'time_spent': seconds,
                'follow_up_specificity': 'vague|focused|technical',
                'skipped': bool
            }
        """

        confusion_record = {
            'user_id': user_id,
            'question_id': question_id,
            'signals': confusion_signals,
            'timestamp': datetime.utcnow(),
            'confusion_score': self._calculate_confusion_score(confusion_signals)
        }

        # Store in database
        if not hasattr(self, 'confusion_collection'):
            self.confusion_collection = self.db.confusion_signals
            self.confusion_collection.create_index("user_id")

        self.confusion_collection.insert_one(confusion_record)

        # Update user profile weak areas if high confusion
        if confusion_record['confusion_score'] > 0.7:
            self._mark_concept_as_weak(user_id, question_id)

    def get_remedial_content_for_concept(
        self,
        user_id: str,
        concept: str
    ) -> Dict:
        """
        Get remedial content and prerequisites for struggling concept

        Returns:
            Dict with prerequisites, simpler related topics, suggested resources
        """

        # Get prerequisite map from LocalPedagogicalAnalyzer
        from .local_pedagogical_analyzer import LocalPedagogicalAnalyzer
        from .example_database import get_example, list_examples_for_concept
        from .analogy_database import get_analogy

        analyzer = LocalPedagogicalAnalyzer()

        # Get prerequisites
        prerequisites = analyzer.PREREQUISITE_MAP.get(concept.lower(), [])

        # Check which prerequisites user has NOT explored
        profile = self.build_user_profile(user_id)
        explored = [t.lower() for t in profile.get('topics_explored', [])]
        missing_prereqs = [p for p in prerequisites if p not in explored]

        # Get examples and analogies
        examples = list_examples_for_concept(concept)
        beginner_analogy = get_analogy(concept, 'beginner')

        return {
            'concept': concept,
            'missing_prerequisites': missing_prereqs,
            'suggested_learning_path': missing_prereqs + [concept],
            'remedial_analogy': beginner_analogy,
            'available_examples': examples,
            'recommendation': f"Master these first: {', '.join(missing_prereqs)}" if missing_prereqs else f"Ready to learn {concept}"
        }

    def calculate_mastery_level(
        self,
        user_id: str,
        concept: str
    ) -> str:
        """
        Calculate mastery level: novice|beginner|intermediate|proficient|expert

        Based on: attempts, time, confidence, application (not just quiz score)
        """

        profile = self.build_user_profile(user_id)

        # Get interaction history for this concept
        cutoff_date = datetime.utcnow() - timedelta(days=90)
        interactions = list(
            self.interactions_collection.find({
                'user_id': user_id,
                'concepts': concept,
                'unix_timestamp': {'$gte': cutoff_date}
            })
        )

        if not interactions:
            return 'novice'

        # Calculate mastery based on multiple factors
        num_interactions = len(interactions)
        in_strong_areas = concept in profile.get('strong_areas', [])
        in_weak_areas = concept in profile.get('weak_areas', [])

        # Mastery scale
        if in_weak_areas:
            return 'novice'
        elif num_interactions < 2:
            return 'beginner'
        elif num_interactions < 5 and not in_strong_areas:
            return 'intermediate'
        elif num_interactions >= 5 and not in_strong_areas:
            return 'proficient'
        elif in_strong_areas and num_interactions >= 3:
            return 'expert'

        return 'intermediate'

    def suggest_next_concept(
        self,
        user_id: str,
        limit: int = 3
    ) -> List[Dict]:
        """
        Suggest next concepts to learn based on:
        - mastery level
        - prerequisites
        - weak areas
        - interest (recent topics)

        Returns list of suggested concepts with reasoning
        """

        profile = self.build_user_profile(user_id)
        explored = set(t.lower() for t in profile.get('topics_explored', []))

        # Get prerequisites map
        from .local_pedagogical_analyzer import LocalPedagogicalAnalyzer
        analyzer = LocalPedagogicalAnalyzer()
        prereq_map = analyzer.PREREQUISITE_MAP

        suggestions = []

        # Strategy 1: Fill in missing prerequisites
        for concept, prerequisites in prereq_map.items():
            # If user has explored concept, suggest prerequisites they're missing
            if concept in explored:
                for prereq in prerequisites:
                    if prereq not in explored:
                        suggestions.append({
                            'concept': prereq,
                            'reason': f'Prerequisites for {concept}',
                            'priority': 'high'
                        })

        # Strategy 2: Natural next steps (concepts that build on what they know)
        for concept, prerequisites in prereq_map.items():
            if concept not in explored:
                # Check if they have prerequisites
                missing = [p for p in prerequisites if p not in explored]
                if len(missing) == 0 or len(missing) <= 1:  # Can learn with minor gaps
                    suggestions.append({
                        'concept': concept,
                        'reason': f'Natural next step after {profile.get("last_30_days_topics", ["general"])[0]}',
                        'priority': 'medium'
                    })

        # Strategy 3: Revisit weak areas
        for weak_area in profile.get('weak_areas', [])[:2]:
            if weak_area not in explored:
                suggestions.append({
                    'concept': weak_area,
                    'reason': 'Strengthen this weak area',
                    'priority': 'high'
                })

        # Deduplicate and rank
        seen = set()
        unique_suggestions = []
        for s in suggestions:
            if s['concept'] not in seen:
                seen.add(s['concept'])
                unique_suggestions.append(s)

        # Sort by priority
        priority_order = {'high': 0, 'medium': 1, 'low': 2}
        unique_suggestions.sort(key=lambda x: priority_order.get(x['priority'], 2))

        return unique_suggestions[:limit]

    def _calculate_confusion_score(self, signals: Dict) -> float:
        """Calculate confusion score from signals (0-1)"""
        score = 0.0

        if signals.get('asked_for_simpler'):
            score += 0.3
        if signals.get('asked_for_example'):
            score += 0.2
        if signals.get('re_asked_count', 0) > 0:
            score += min(0.3, signals['re_asked_count'] * 0.1)
        if signals.get('skipped'):
            score += 0.2

        # Time spent (more time = possible confusion)
        time_spent = signals.get('time_spent', 0)
        if time_spent > 300:  # More than 5 minutes
            score += 0.1

        # Follow-up specificity (vague = confused)
        if signals.get('follow_up_specificity') == 'vague':
            score += 0.15

        return min(1.0, score)

    def _mark_concept_as_weak(self, user_id: str, concept: str) -> None:
        """Mark a concept as weak area for user"""
        profile = self.profiles_collection.find_one({'user_id': user_id})
        if not profile:
            return

        weak_areas = profile.get('weak_areas', [])
        if concept not in weak_areas:
            weak_areas.append(concept)

        self.profiles_collection.update_one(
            {'user_id': user_id},
            {'$set': {'weak_areas': weak_areas[-10:]}}  # Keep last 10
        )
