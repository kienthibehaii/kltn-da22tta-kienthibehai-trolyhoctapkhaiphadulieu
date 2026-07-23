# intelligent_assistant/agentic_rag.py
"""
Agentic RAG System with multiple specialized agents:
- Planner Agent: Orchestrates workflow
- Retrieval Agent: Finds relevant documents
- Summarization Agent: Generates answers
- Evaluation Agent: Assesses quality
"""

import asyncio
from typing import Dict, List, Optional, Any
from dataclasses import dataclass
from enum import Enum
import logging

from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_core.documents import Document

logger = logging.getLogger(__name__)


class AgentRole(Enum):
    """Agent roles"""
    PLANNER = "planner"
    RETRIEVAL = "retrieval"
    SUMMARIZATION = "summarization"
    EVALUATION = "evaluation"


@dataclass
class AgentTask:
    """Task for an agent"""
    task_id: str
    role: AgentRole
    input_data: Dict
    dependencies: List[str]  # Task IDs this depends on
    status: str = "pending"  # pending, running, completed, failed
    output: Optional[Dict] = None
    error: Optional[str] = None


@dataclass
class Plan:
    """Execution plan"""
    plan_id: str
    query: str
    strategy: str  # simple, complex, multi-step
    tasks: List[AgentTask]
    metadata: Dict


class PlannerAgent:
    """Plans the execution workflow"""
    
    def __init__(self, llm):
        self.llm = llm
    
    async def create_plan(
        self,
        query: str,
        query_analysis: Any,
        context: Optional[Dict] = None
    ) -> Plan:
        """
        Create execution plan based on query analysis
        
        Returns:
            Plan with tasks
        """
        logger.info(f"Creating plan for query: {query}")
        
        # Determine strategy
        strategy = self._determine_strategy(query_analysis)
        
        # Create tasks based on strategy
        tasks = []
        
        if strategy == "simple":
            # Simple: Retrieve → Summarize → Evaluate
            tasks = [
                AgentTask(
                    task_id="retrieve_1",
                    role=AgentRole.RETRIEVAL,
                    input_data={"query": query, "k": 10},
                    dependencies=[]
                ),
                AgentTask(
                    task_id="summarize_1",
                    role=AgentRole.SUMMARIZATION,
                    input_data={"query": query},
                    dependencies=["retrieve_1"]
                ),
                AgentTask(
                    task_id="evaluate_1",
                    role=AgentRole.EVALUATION,
                    input_data={},
                    dependencies=["summarize_1"]
                )
            ]
        
        elif strategy == "complex":
            # Complex: Multiple retrievals + synthesis
            tasks = [
                AgentTask(
                    task_id="retrieve_broad",
                    role=AgentRole.RETRIEVAL,
                    input_data={"query": query, "k": 20, "mode": "broad"},
                    dependencies=[]
                ),
                AgentTask(
                    task_id="retrieve_specific",
                    role=AgentRole.RETRIEVAL,
                    input_data={"query": query, "k": 10, "mode": "specific"},
                    dependencies=[]
                ),
                AgentTask(
                    task_id="synthesize",
                    role=AgentRole.SUMMARIZATION,
                    input_data={"query": query, "mode": "synthesis"},
                    dependencies=["retrieve_broad", "retrieve_specific"]
                ),
                AgentTask(
                    task_id="evaluate_final",
                    role=AgentRole.EVALUATION,
                    input_data={},
                    dependencies=["synthesize"]
                )
            ]
        
        elif strategy == "multi-step":
            # Multi-step: Break down complex query
            sub_queries = await self._decompose_query(query)
            
            for i, sub_query in enumerate(sub_queries):
                tasks.extend([
                    AgentTask(
                        task_id=f"retrieve_{i}",
                        role=AgentRole.RETRIEVAL,
                        input_data={"query": sub_query, "k": 10},
                        dependencies=[]
                    ),
                    AgentTask(
                        task_id=f"summarize_{i}",
                        role=AgentRole.SUMMARIZATION,
                        input_data={"query": sub_query},
                        dependencies=[f"retrieve_{i}"]
                    )
                ])
            
            # Final synthesis
            tasks.append(
                AgentTask(
                    task_id="final_synthesis",
                    role=AgentRole.SUMMARIZATION,
                    input_data={"query": query, "mode": "final"},
                    dependencies=[f"summarize_{i}" for i in range(len(sub_queries))]
                )
            )
            
            tasks.append(
                AgentTask(
                    task_id="evaluate_final",
                    role=AgentRole.EVALUATION,
                    input_data={},
                    dependencies=["final_synthesis"]
                )
            )
        
        plan = Plan(
            plan_id=f"plan_{hash(query)}",
            query=query,
            strategy=strategy,
            tasks=tasks,
            metadata={
                "query_type": query_analysis.query_type.value,
                "difficulty": query_analysis.difficulty,
                "estimated_time": len(tasks) * 2  # seconds
            }
        )
        
        logger.info(f"Created {strategy} plan with {len(tasks)} tasks")
        return plan
    
    def _determine_strategy(self, query_analysis: Any) -> str:
        """Determine execution strategy"""
        # Simple for factual questions
        if query_analysis.query_type.value == "factual" and query_analysis.difficulty < 0.5:
            return "simple"
        
        # Complex for conceptual or comparative
        if query_analysis.query_type.value in ["conceptual", "comparative"]:
            return "complex"
        
        # Multi-step for procedural or high difficulty
        if query_analysis.query_type.value == "procedural" or query_analysis.difficulty > 0.7:
            return "multi-step"
        
        return "simple"
    
    async def _decompose_query(self, query: str) -> List[str]:
        """Decompose complex query into sub-queries"""
        prompt = f"""Break down this complex question into 2-3 simpler sub-questions.

Question: {query}

Sub-questions (one per line):"""
        
        try:
            response = await self.llm.ainvoke(prompt)
            sub_queries = [
                line.strip().lstrip("123456789.-) ")
                for line in response.content.split("\n")
                if line.strip()
            ][:3]
            
            return sub_queries if sub_queries else [query]
        except:
            return [query]


class RetrievalAgent:
    """Retrieves relevant documents"""
    
    def __init__(self, retriever):
        self.retriever = retriever
    
    async def retrieve(
        self,
        query: str,
        k: int = 10,
        mode: str = "standard",
        filters: Optional[Dict] = None
    ) -> List[Document]:
        """
        Retrieve documents
        
        Args:
            query: Search query
            k: Number of documents
            mode: broad, specific, or standard
            filters: Metadata filters
        """
        logger.info(f"Retrieving documents: mode={mode}, k={k}")
        
        # Adjust k based on mode
        if mode == "broad":
            k = int(k * 1.5)
        elif mode == "specific":
            k = int(k * 0.7)
        
        # Retrieve
        try:
            if hasattr(self.retriever, 'ainvoke'):
                docs = await self.retriever.ainvoke(query, k=k)
            else:
                docs = self.retriever.invoke(query, k=k)
            
            # Apply filters if provided
            if filters:
                docs = self._apply_filters(docs, filters)
            
            logger.info(f"Retrieved {len(docs)} documents")
            return docs
        
        except Exception as e:
            logger.error(f"Retrieval failed: {e}")
            return []
    
    def _apply_filters(self, docs: List[Document], filters: Dict) -> List[Document]:
        """Apply metadata filters"""
        filtered = []
        for doc in docs:
            match = True
            for key, value in filters.items():
                if key not in doc.metadata or doc.metadata[key] != value:
                    match = False
                    break
            if match:
                filtered.append(doc)
        return filtered


class SummarizationAgent:
    """Generates answers from documents"""
    
    def __init__(self, llm):
        self.llm = llm
    
    async def summarize(
        self,
        query: str,
        documents: List[Document],
        mode: str = "standard",
        previous_summaries: Optional[List[str]] = None
    ) -> Dict:
        """
        Generate answer from documents
        
        Returns:
            {
                "answer": str,
                "reasoning": List[str],
                "sources": List[int],
                "confidence": float
            }
        """
        logger.info(f"Generating answer: mode={mode}")
        
        if mode == "synthesis":
            return await self._synthesize_multiple(query, documents)
        elif mode == "final":
            return await self._final_synthesis(query, previous_summaries)
        else:
            return await self._standard_summary(query, documents)
    
    async def _standard_summary(self, query: str, documents: List[Document]) -> Dict:
        """Standard summarization"""
        # Create context
        context = "\n\n".join([
            f"[{i+1}] {doc.page_content[:500]}"
            for i, doc in enumerate(documents[:5])
        ])
        
        prompt = f"""Answer the question based on the provided documents. Include step-by-step reasoning.

Documents:
{context}

Question: {query}

Answer with reasoning:"""
        
        try:
            response = await self.llm.ainvoke(prompt)
            answer = response.content
            
            # Extract reasoning steps (simplified)
            reasoning = self._extract_reasoning(answer)
            
            return {
                "answer": answer,
                "reasoning": reasoning,
                "sources": list(range(min(5, len(documents)))),
                "confidence": 0.85
            }
        except Exception as e:
            logger.error(f"Summarization failed: {e}")
            return {
                "answer": "Unable to generate answer.",
                "reasoning": [],
                "sources": [],
                "confidence": 0.0
            }
    
    async def _synthesize_multiple(self, query: str, documents: List[Document]) -> Dict:
        """Synthesize from multiple retrievals"""
        # Group documents by relevance
        high_rel = documents[:10]
        context = documents[10:20] if len(documents) > 10 else []
        
        prompt = f"""Synthesize a comprehensive answer from multiple sources.

Primary sources:
{self._format_docs(high_rel)}

Additional context:
{self._format_docs(context)}

Question: {query}

Comprehensive answer:"""
        
        response = await self.llm.ainvoke(prompt)
        
        return {
            "answer": response.content,
            "reasoning": self._extract_reasoning(response.content),
            "sources": list(range(len(documents))),
            "confidence": 0.88
        }
    
    async def _final_synthesis(self, query: str, previous_summaries: List[str]) -> Dict:
        """Final synthesis from sub-answers"""
        summaries_text = "\n\n".join([
            f"Part {i+1}: {summary}"
            for i, summary in enumerate(previous_summaries)
        ])
        
        prompt = f"""Synthesize a final comprehensive answer from these partial answers.

Question: {query}

Partial answers:
{summaries_text}

Final comprehensive answer:"""
        
        response = await self.llm.ainvoke(prompt)
        
        return {
            "answer": response.content,
            "reasoning": self._extract_reasoning(response.content),
            "sources": [],
            "confidence": 0.90
        }
    
    def _format_docs(self, docs: List[Document]) -> str:
        """Format documents for prompt"""
        return "\n\n".join([
            f"[{i+1}] {doc.page_content[:300]}"
            for i, doc in enumerate(docs)
        ])
    
    def _extract_reasoning(self, text: str) -> List[str]:
        """Extract reasoning steps from answer"""
        # Simple extraction (can be improved with NLP)
        steps = []
        for line in text.split("\n"):
            if any(marker in line.lower() for marker in ["first", "second", "then", "finally", "because"]):
                steps.append(line.strip())
        return steps[:5]


class EvaluationAgent:
    """Evaluates answer quality"""
    
    def __init__(self, llm):
        self.llm = llm
    
    async def evaluate(
        self,
        query: str,
        answer: str,
        documents: List[Document],
        reasoning: List[str]
    ) -> Dict:
        """
        Evaluate answer quality
        
        Returns:
            {
                "overall_score": float,
                "relevance": float,
                "completeness": float,
                "accuracy": float,
                "educational_value": float,
                "feedback": str
            }
        """
        logger.info("Evaluating answer quality")
        
        # Calculate scores
        relevance = await self._evaluate_relevance(query, answer)
        completeness = self._evaluate_completeness(answer, reasoning)
        accuracy = await self._evaluate_accuracy(answer, documents)
        educational_value = self._evaluate_educational_value(answer, reasoning)
        
        overall_score = (
            relevance * 0.3 +
            completeness * 0.25 +
            accuracy * 0.3 +
            educational_value * 0.15
        )
        
        # Generate feedback
        feedback = self._generate_feedback(
            relevance, completeness, accuracy, educational_value
        )
        
        return {
            "overall_score": overall_score,
            "relevance": relevance,
            "completeness": completeness,
            "accuracy": accuracy,
            "educational_value": educational_value,
            "feedback": feedback
        }
    
    async def _evaluate_relevance(self, query: str, answer: str) -> float:
        """Evaluate if answer addresses the query"""
        # Simple keyword overlap (can use LLM for better evaluation)
        query_words = set(query.lower().split())
        answer_words = set(answer.lower().split())
        overlap = len(query_words & answer_words) / len(query_words)
        return min(1.0, overlap * 2)
    
    def _evaluate_completeness(self, answer: str, reasoning: List[str]) -> float:
        """Evaluate answer completeness"""
        score = 0.5  # Base score
        
        # Has reasoning
        if reasoning:
            score += 0.2
        
        # Sufficient length
        if len(answer.split()) > 50:
            score += 0.2
        
        # Has examples
        if "example" in answer.lower() or "ví dụ" in answer.lower():
            score += 0.1
        
        return min(1.0, score)
    
    async def _evaluate_accuracy(self, answer: str, documents: List[Document]) -> float:
        """Evaluate accuracy against sources"""
        # Check if answer content appears in documents
        answer_lower = answer.lower()
        doc_texts = " ".join([doc.page_content.lower() for doc in documents[:5]])
        
        # Simple overlap check
        answer_sentences = answer_lower.split(".")
        grounded_count = sum(
            1 for sent in answer_sentences
            if any(word in doc_texts for word in sent.split() if len(word) > 4)
        )
        
        return min(1.0, grounded_count / max(1, len(answer_sentences)))
    
    def _evaluate_educational_value(self, answer: str, reasoning: List[str]) -> float:
        """Evaluate educational value"""
        score = 0.5
        
        # Has step-by-step reasoning
        if len(reasoning) >= 2:
            score += 0.2
        
        # Uses educational language
        educational_markers = ["because", "therefore", "this means", "for example"]
        if any(marker in answer.lower() for marker in educational_markers):
            score += 0.2
        
        # Appropriate length
        if 100 < len(answer.split()) < 500:
            score += 0.1
        
        return min(1.0, score)
    
    def _generate_feedback(self, relevance, completeness, accuracy, educational_value) -> str:
        """Generate feedback message"""
        feedback_parts = []
        
        if relevance < 0.7:
            feedback_parts.append("Answer could be more relevant to the question.")
        if completeness < 0.7:
            feedback_parts.append("Answer could be more complete with examples.")
        if accuracy < 0.7:
            feedback_parts.append("Answer should be better grounded in sources.")
        if educational_value < 0.7:
            feedback_parts.append("Answer could have better educational structure.")
        
        if not feedback_parts:
            return "Excellent answer quality!"
        
        return " ".join(feedback_parts)


class AgenticRAG:
    """Orchestrates agentic RAG system"""
    
    def __init__(self, llm, retriever):
        self.planner = PlannerAgent(llm)
        self.retrieval_agent = RetrievalAgent(retriever)
        self.summarization_agent = SummarizationAgent(llm)
        self.evaluation_agent = EvaluationAgent(llm)
    
    async def execute(
        self,
        query: str,
        query_analysis: Any,
        context: Optional[Dict] = None
    ) -> Dict:
        """
        Execute agentic RAG pipeline
        
        Returns:
            Complete result with answer, evaluation, and metadata
        """
        logger.info(f"Executing agentic RAG for: {query}")
        
        # 1. Create plan
        plan = await self.planner.create_plan(query, query_analysis, context)
        
        # 2. Execute tasks
        results = await self._execute_plan(plan)
        
        # 3. Extract final answer and evaluation
        final_answer = results.get("answer", {})
        evaluation = results.get("evaluation", {})
        
        return {
            "query": query,
            "answer": final_answer.get("answer", ""),
            "reasoning": final_answer.get("reasoning", []),
            "sources": final_answer.get("sources", []),
            "confidence": final_answer.get("confidence", 0.0),
            "evaluation": evaluation,
            "plan": {
                "strategy": plan.strategy,
                "tasks_executed": len(plan.tasks)
            },
            "metadata": plan.metadata
        }
    
    async def _execute_plan(self, plan: Plan) -> Dict:
        """Execute plan tasks"""
        task_results = {}
        
        # Execute tasks in dependency order
        while any(task.status == "pending" for task in plan.tasks):
            for task in plan.tasks:
                if task.status != "pending":
                    continue
                
                # Check if dependencies are met
                if all(task_results.get(dep) for dep in task.dependencies):
                    task.status = "running"
                    
                    try:
                        # Execute task
                        result = await self._execute_task(task, task_results)
                        task.output = result
                        task.status = "completed"
                        task_results[task.task_id] = result
                    except Exception as e:
                        task.status = "failed"
                        task.error = str(e)
                        logger.error(f"Task {task.task_id} failed: {e}")
        
        # Return final results
        return {
            "answer": task_results.get("summarize_1") or task_results.get("final_synthesis"),
            "evaluation": task_results.get("evaluate_1") or task_results.get("evaluate_final"),
            "all_results": task_results
        }
    
    async def _execute_task(self, task: AgentTask, previous_results: Dict) -> Any:
        """Execute a single task"""
        if task.role == AgentRole.RETRIEVAL:
            return await self.retrieval_agent.retrieve(**task.input_data)
        
        elif task.role == AgentRole.SUMMARIZATION:
            # Get documents from dependencies
            docs = []
            for dep_id in task.dependencies:
                if dep_id in previous_results:
                    result = previous_results[dep_id]
                    if isinstance(result, list):
                        docs.extend(result)
            
            return await self.summarization_agent.summarize(
                task.input_data["query"],
                docs,
                mode=task.input_data.get("mode", "standard")
            )
        
        elif task.role == AgentRole.EVALUATION:
            # Get answer from dependencies
            answer_data = previous_results.get(task.dependencies[0], {})
            
            return await self.evaluation_agent.evaluate(
                query="",  # Would need to pass through
                answer=answer_data.get("answer", ""),
                documents=[],
                reasoning=answer_data.get("reasoning", [])
            )
        
        return None
