"""
Enrich vector DB chunks with course metadata
PHASE 2.1 - Day 2 Implementation
"""

import json
from typing import Dict, List, Any, Optional


class MetadataEnricher:
    """Enrich chunks with educational metadata"""
    
    def __init__(self, course_graph_path: str = "course_knowledge_graph.json"):
        """
        Initialize enricher with course knowledge graph
        
        Args:
            course_graph_path: Path to course_knowledge_graph.json
        """
        self.course_graph = self._load_course_graph(course_graph_path)
        self.course_graph_path = course_graph_path
    
    def _load_course_graph(self, filepath: str) -> Dict:
        """Load course knowledge graph from JSON"""
        try:
            with open(filepath, 'r', encoding='utf-8') as f:
                return json.load(f)
        except FileNotFoundError:
            print(f"⚠️  {filepath} not found. Running in demo mode.")
            return {}
    
    def enrich_chunk_metadata(
        self, 
        chunk_text: str,
        source: str = "",
        page: int = 0,
        chapter_id: str = "CH1",
        topic_id: str = ""
    ) -> Dict[str, Any]:
        """
        Enrich a single chunk with educational metadata
        
        Args:
            chunk_text: Text content of the chunk
            source: Source document
            page: Page number
            chapter_id: Chapter identifier
            topic_id: Topic identifier
            
        Returns:
            Dict: Enhanced metadata for the chunk
        """
        
        # Find chapter info
        chapter_info = self._get_chapter_info(chapter_id)
        
        # Determine difficulty
        difficulty = self._assess_difficulty(chunk_text, chapter_info)
        
        # Assess importance
        importance = self._calculate_importance(chapter_id, chunk_text)
        
        # Determine linked learning outcomes
        linked_los = chapter_info.get("learning_outcomes", [])
        
        # Determine teaching strategy
        strategy = self._select_teaching_strategy(chunk_text, difficulty)
        
        # Get prerequisites
        prerequisites = self._get_prerequisites(chapter_id)
        
        metadata = {
            "chapter": chapter_id,
            "chapter_title": chapter_info.get("title", ""),
            "topic": topic_id,
            "source": source,
            "page": page,
            "learning_outcomes": linked_los,
            "bloom_level": self._estimate_bloom_level(chunk_text),
            "difficulty_level": difficulty,
            "assessment_type": chapter_info.get("assessment_types", ["quiz"])[0] if chapter_info.get("assessment_types") else "quiz",
            "importance_score": importance,
            "teaching_strategy": strategy,
            "prerequisites": prerequisites,
            "keywords": self._extract_keywords(chunk_text),
            "created_at": "2026-05-26"
        }
        
        return metadata
    
    def _get_chapter_info(self, chapter_id: str) -> Dict:
        """Get chapter information from knowledge graph"""
        chapters = self.course_graph.get("chapters", [])
        for chapter in chapters:
            if chapter.get("id") == chapter_id:
                return chapter
        
        # Return default if not found
        return {
            "title": f"Chapter {chapter_id}",
            "learning_outcomes": [],
            "assessment_types": ["quiz"],
            "importance": 0.5
        }
    
    def _assess_difficulty(self, text: str, chapter_info: Dict) -> str:
        """
        Assess text difficulty (easy/medium/hard)
        
        Heuristic: 
        - < 100 chars = easy
        - 100-500 chars = medium
        - > 500 chars = hard
        """
        if len(text) < 100:
            return "easy"
        if len(text) > 500:
            return "hard"
        return "medium"
    
    def _calculate_importance(self, chapter_id: str, text: str) -> float:
        """
        Calculate importance score (0-1)
        
        Based on:
        - Chapter importance from knowledge graph
        - Presence of key concepts in text
        """
        chapter = self._get_chapter_info(chapter_id)
        base_importance = chapter.get("importance", 0.5)
        
        # Boost if text mentions key concepts
        keywords = ["algorithm", "concept", "definition", "theorem", "property"]
        text_lower = text.lower()
        boost = sum(0.1 for kw in keywords if kw in text_lower)
        
        return min(1.0, base_importance + boost)
    
    def _select_teaching_strategy(self, text: str, difficulty: str) -> str:
        """
        Select teaching strategy based on difficulty
        
        Returns one of: analogy-first, example-first, conceptual, 
                        mathematical, step-by-step, visual
        """
        strategies = {
            "easy": ["example-first", "visual"],
            "medium": ["conceptual", "step-by-step"],
            "hard": ["mathematical", "step-by-step"]
        }
        return strategies.get(difficulty, ["conceptual"])[0]
    
    def _estimate_bloom_level(self, text: str) -> str:
        """
        Estimate Bloom's taxonomy level
        
        Returns: knowledge, comprehension, application, analysis, synthesis, evaluation
        """
        text_lower = text.lower()
        
        if any(w in text_lower for w in ["define", "explain", "understand", "remember"]):
            return "comprehension"
        if any(w in text_lower for w in ["apply", "implement", "use", "solve"]):
            return "application"
        if any(w in text_lower for w in ["analyze", "compare", "evaluate", "examine", "distinguish"]):
            return "analysis"
        if any(w in text_lower for w in ["create", "design", "combine", "organize"]):
            return "synthesis"
        
        return "knowledge"
    
    def _get_prerequisites(self, chapter_id: str) -> List[str]:
        """Get prerequisite chapters (all chapters before this one)"""
        try:
            chapter_num = int(chapter_id.replace("CH", ""))
            prerequisites = [f"CH{i}" for i in range(1, chapter_num)]
            return prerequisites
        except:
            return []
    
    def _extract_keywords(self, text: str, num_keywords: int = 5) -> List[str]:
        """Extract keywords from text"""
        # Simple keyword extraction: split and take first words
        words = text.split()[:num_keywords]
        return [w.lower().strip(',.!?;:') for w in words if len(w) > 4]
    
    def enrich_all_chunks(self, chunks: List[Dict], collection_name: str = "educational_docs") -> List[Dict]:
        """
        Enrich all chunks with metadata
        
        Args:
            chunks: List of chunk dictionaries with 'text', 'source', 'page', 'chapter', 'topic'
            collection_name: Collection name (for reference)
            
        Returns:
            List[Dict]: Chunks with enriched metadata
        """
        
        enriched_chunks = []
        for i, chunk in enumerate(chunks):
            # Extract metadata
            text = chunk.get("text", "")
            source = chunk.get("source", "")
            page = chunk.get("page", 0)
            chapter_id = chunk.get("chapter", "CH1")
            topic_id = chunk.get("topic", "")
            
            # Enrich
            enriched_metadata = self.enrich_chunk_metadata(
                text, source, page, chapter_id, topic_id
            )
            
            # Create enriched chunk
            enriched_chunk = chunk.copy()
            enriched_chunk["metadata"] = enriched_metadata
            
            enriched_chunks.append(enriched_chunk)
        
        print(f"✅ Enriched {len(enriched_chunks)} chunks")
        return enriched_chunks
    
    def demo_enrich(self):
        """Demo enrichment with sample chunks"""
        sample_chunks = [
            {
                "text": "Decision Tree is a machine learning algorithm used for classification",
                "source": "textbook.pdf",
                "page": 42,
                "chapter": "CH4",
                "topic": "decision_trees"
            },
            {
                "text": "To implement a decision tree, we use recursive splitting based on information gain",
                "source": "textbook.pdf",
                "page": 43,
                "chapter": "CH4",
                "topic": "decision_trees"
            }
        ]
        
        enriched = self.enrich_all_chunks(sample_chunks)
        
        print("\n📋 Demo Enriched Chunks:")
        for i, chunk in enumerate(enriched, 1):
            print(f"\nChunk {i}:")
            print(f"  Text: {chunk['text'][:60]}...")
            print(f"  Chapter: {chunk['metadata']['chapter']}")
            print(f"  Difficulty: {chunk['metadata']['difficulty_level']}")
            print(f"  Bloom Level: {chunk['metadata']['bloom_level']}")
            print(f"  Strategy: {chunk['metadata']['teaching_strategy']}")
            print(f"  Importance: {chunk['metadata']['importance_score']}")
        
        return enriched


# Usage:
if __name__ == "__main__":
    print("🔄 Phase 2.1 Task 2: Metadata Enrichment")
    print("=" * 50)
    
    # Create enricher
    enricher = MetadataEnricher()
    
    # Run demo
    enricher.demo_enrich()
    
    print("\n✅ Phase 2.1 Task 2 Complete!")
