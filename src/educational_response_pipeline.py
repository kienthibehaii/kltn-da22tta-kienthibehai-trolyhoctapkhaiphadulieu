"""
Educational Response Pipeline - Generate 8-part pedagogical responses
Phase 2.2 - Component 5
"""

from typing import Dict, List, Optional
from dataclasses import dataclass
from teaching_strategy_selector import SelectedStrategy


@dataclass
class EightPartResponse:
    """8-part educational response structure"""
    quick_summary: str
    conceptual_explanation: str
    real_world_example: str
    implementation: str
    common_mistakes: str
    learning_path: str
    practice_hint: str
    mastery_check: str
    
    def to_markdown(self) -> str:
        """Convert to markdown format for display"""
        return f"""
## 📚 Câu Trả Lời Giáo Dục

### 1️⃣ Tóm Tắt Nhanh
{self.quick_summary}

### 2️⃣ Giải Thích Khái Niệm
{self.conceptual_explanation}

### 3️⃣ Ví Dụ Thực Tế
{self.real_world_example}

### 4️⃣ Cách Áp Dụng
{self.implementation}

### 5️⃣ Những Lỗi Phổ Biến
{self.common_mistakes}

### 6️⃣ Con Đường Học Tập
{self.learning_path}

### 7️⃣ Gợi Ý Thực Hành
{self.practice_hint}

### 8️⃣ Kiểm Tra Thành Thạo
{self.mastery_check}
"""
    
    def to_dict(self) -> Dict:
        """Convert to dictionary"""
        return {
            "quick_summary": self.quick_summary,
            "conceptual_explanation": self.conceptual_explanation,
            "real_world_example": self.real_world_example,
            "implementation": self.implementation,
            "common_mistakes": self.common_mistakes,
            "learning_path": self.learning_path,
            "practice_hint": self.practice_hint,
            "mastery_check": self.mastery_check
        }


class EducationalResponsePipeline:
    """Generate 8-part educational responses using teaching strategies"""
    
    def __init__(self, llm_client=None):
        """
        Initialize response pipeline
        
        Args:
            llm_client: LLM client (Google Gemini, OpenAI, etc.)
                       If None, uses templated responses
        """
        self.llm_client = llm_client
    
    def generate_response(
        self,
        base_response: str,
        strategy: SelectedStrategy,
        learning_pace: str,
        topic: str
    ) -> EightPartResponse:
        """
        Generate 8-part response using pedagogical strategy
        
        Args:
            base_response: Base LLM response to structure
            strategy: Selected teaching strategy with parameters
            learning_pace: Student's learning pace (slow/medium/fast)
            topic: Topic being discussed
            
        Returns:
            EightPartResponse: Structured 8-part response
        """
        
        # Generate each of 8 parts using strategy and LLM
        quick_summary = self._generate_quick_summary(
            base_response, topic, learning_pace
        )
        
        conceptual = self._generate_conceptual(
            base_response, strategy, topic
        )
        
        example = self._generate_example(
            base_response, strategy, learning_pace, topic
        )
        
        implementation = self._generate_implementation(
            base_response, strategy, topic
        )
        
        mistakes = self._generate_mistakes(base_response, topic)
        
        learning_path = self._generate_learning_path(
            topic, learning_pace
        )
        
        practice = self._generate_practice_hint(
            topic, strategy, learning_pace
        )
        
        check = self._generate_mastery_check(topic)
        
        return EightPartResponse(
            quick_summary=quick_summary,
            conceptual_explanation=conceptual,
            real_world_example=example,
            implementation=implementation,
            common_mistakes=mistakes,
            learning_path=learning_path,
            practice_hint=practice,
            mastery_check=check
        )
    
    def _generate_quick_summary(
        self,
        response: str,
        topic: str,
        learning_pace: str
    ) -> str:
        """Generate 1-2 sentence quick summary"""
        
        if not self.llm_client:
            # Fallback: use first 1-2 sentences from response
            sentences = response.split('.')
            summary = '. '.join(sentences[:2])
            return summary.strip() + '.' if summary else f"Giải thích ngắn về {topic}."
        
        # With LLM: Generate proper summary
        prompt = f"""
Tóm tắt lại đoạn text sau BẰNG 1-2 câu ngắn gọn, rõ ràng, dễ hiểu.

Text: {response}

Tóm tắt (1-2 câu):"""
        
        summary = self.llm_client.generate(prompt)
        return summary
    
    def _generate_conceptual(
        self,
        response: str,
        strategy: SelectedStrategy,
        topic: str
    ) -> str:
        """Generate conceptual explanation based on teaching strategy"""
        
        if not self.llm_client:
            # Fallback: return first part of response
            return response[:300] + "..." if len(response) > 300 else response
        
        # Different prompts based on selected strategy
        if strategy.strategy_name == "analogy-first":
            prompt = f"""
Giải thích {topic} bằng PHÉP SO SÁNH (analogy) với các khái niệm quen thuộc.

{response}

Giải thích dùng phép so sánh:"""
        
        elif strategy.strategy_name == "mathematical":
            prompt = f"""
Giải thích {topic} bằng công thức toán học và ký hiệu chính xác.

{response}

Giải thích toán học:"""
        
        elif strategy.strategy_name == "visual":
            prompt = f"""
Giải thích {topic} bằng cách mô tả hình ảnh hoặc sơ đồ.

{response}

Giải thích hình ảnh:"""
        
        else:  # Default: conceptual
            prompt = f"""
Giải thích rõ ràng khái niệm cốt lõi của {topic}.

{response}

Khái niệm cốt lõi:"""
        
        return self.llm_client.generate(prompt)
    
    def _generate_example(
        self,
        response: str,
        strategy: SelectedStrategy,
        learning_pace: str,
        topic: str
    ) -> str:
        """Generate practical real-world examples"""
        
        if not self.llm_client:
            return f"Ví dụ về {topic}: Trong thực tế, {topic} được áp dụng khi..."
        
        # Determine number of examples based on pace
        if learning_pace == "fast":
            count = 1
        elif learning_pace == "slow":
            count = 3
        else:
            count = 2
        
        prompt = f"""
Cung cấp {count} ví dụ thực tế (tiếp đất) cho {topic}.

{response}

Ví dụ thực tế:"""
        
        return self.llm_client.generate(prompt)
    
    def _generate_implementation(
        self,
        response: str,
        strategy: SelectedStrategy,
        topic: str
    ) -> str:
        """Generate implementation/how-to section"""
        
        if not self.llm_client:
            return f"Cách áp dụng {topic}: Bước 1... Bước 2... Bước 3..."
        
        if strategy.strategy_name == "step-by-step":
            prompt = f"""
Hướng dẫn chi tiết từng bước để áp dụng/triển khai {topic}.

{response}

Các bước cụ thể:
1. ...
2. ...
3. ..."""
        else:
            prompt = f"""
Cách áp dụng/triển khai {topic} trong thực tế.

{response}

Cách áp dụng:"""
        
        return self.llm_client.generate(prompt)
    
    def _generate_mistakes(
        self,
        response: str,
        topic: str
    ) -> str:
        """Generate common mistakes section"""
        
        if not self.llm_client:
            return f"Lỗi phổ biến: Hiểu sai khái niệm của {topic}"
        
        prompt = f"""
Liệt kê 3 lỗi phổ biến mà học sinh thường mắc khi học {topic}.

{response}

Lỗi phổ biến:
1. ...
2. ...
3. ..."""
        
        return self.llm_client.generate(prompt)
    
    def _generate_learning_path(
        self,
        topic: str,
        learning_pace: str
    ) -> str:
        """Generate next learning steps in the learning path"""
        
        if not self.llm_client:
            return f"Bước tiếp theo: Tìm hiểu các chủ đề liên quan đến {topic}"
        
        prompt = f"""
Đề xuất con đường học tập tiếp theo (những chủ đề liên quan) sau khi nắm được {topic}.

Con đường học tập tiếp theo:"""
        
        return self.llm_client.generate(prompt)
    
    def _generate_practice_hint(
        self,
        topic: str,
        strategy: SelectedStrategy,
        learning_pace: str
    ) -> str:
        """Generate practice suggestion for reinforcement"""
        
        if not self.llm_client:
            return f"Gợi ý thực hành: Giải quyết bài toán thực tế liên quan {topic}"
        
        prompt = f"""
Gợi ý một bài tập thực hành cụ thể để học sinh rèn luyện {topic}.

Bài tập thực hành:"""
        
        return self.llm_client.generate(prompt)
    
    def _generate_mastery_check(self, topic: str) -> str:
        """Generate self-check question for mastery verification"""
        
        if not self.llm_client:
            return f"❓ Bạn có thể giải thích {topic} bằng riêng mình không?"
        
        prompt = f"""
Tạo 1 câu hỏi (có thể tự kiểm tra) để học sinh xác định xem họ đã nắm {topic} chưa.

Câu hỏi kiểm tra thành thạo:"""
        
        return self.llm_client.generate(prompt)
    
    def demo_response_generation(self):
        """Demo response generation with sample data"""
        
        print("\n" + "="*70)
        print("📝 EDUCATIONAL RESPONSE PIPELINE DEMO")
        print("="*70)
        
        from teaching_strategy_selector import (
            TeachingStrategySelector,
            StrategyContext
        )
        
        # Create sample context
        selector = TeachingStrategySelector()
        context = StrategyContext(
            student_id="STU001",
            query="Decision Tree hoạt động như thế nào?",
            chapter_id="CH4",
            learning_pace="medium",
            preferred_strategy="example-first",
            knowledge_gaps=[],
            current_mastery=0.7,
            topic_difficulty="medium"
        )
        
        # Select strategy
        strategy = selector.select_strategy(context)
        
        print(f"\n🎯 Student: {context.student_id}")
        print(f"   Selected Strategy: {strategy.strategy_name}")
        print(f"   Learning Pace: {context.learning_pace}")
        
        # Generate response (without LLM client, uses templates)
        base_response = """
        Decision Tree là một thuật toán học máy phổ biến dùng để phân loại dữ liệu.
        Nó hoạt động bằng cách tạo ra một cây quyết định với các nhánh biểu diễn
        các quyết định tại mỗi nút. Quá trình xây dựng cây sử dụng các tiêu chí
        chia tách như Information Gain hoặc Gini Index.
        """
        
        response = self.generate_response(
            base_response,
            strategy,
            context.learning_pace,
            "Decision Tree"
        )
        
        print(f"\n✅ 8-Part Response Generated!")
        print(response.to_markdown())


# Usage:
if __name__ == "__main__":
    pipeline = EducationalResponsePipeline(llm_client=None)
    pipeline.demo_response_generation()
    print("\n✅ Component 5: Educational Response Pipeline - Ready!")
