# backend_api.py - FastAPI Backend cho RAG System
"""
Backend API riêng biệt theo yêu cầu đề cương
Cung cấp RESTful API để frontend có thể gọi

Tác giả: Kiên Thị Bé Hai
MSSV: 110122218
Trường: Đại học Trà Vinh
Năm: 2026
"""

import sys
import os

# Fix ntdll.dll crash (OpenMP multiple instances bug on Windows)
os.environ['KMP_DUPLICATE_LIB_OK'] = 'True'

if hasattr(sys.stdout, 'reconfigure'):
    try:
        sys.stdout.reconfigure(errors='replace')
    except Exception:
        pass

from fastapi import FastAPI, HTTPException, BackgroundTasks, Request, UploadFile, File, Depends, Header
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from auth.api_routes import get_current_user, auth_manager
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field
from typing import List, Dict, Optional, Any, AsyncGenerator
import uuid
import time
import json
import asyncio
import re
from datetime import datetime, timedelta
import os

# Import các module RAG
from embed_store import load_vector_store, load_documents
from rag import create_qa_chain, ask_question, generate_quiz
from quiz_system import generate_interactive_quiz, evaluate_answer, calculate_quiz_score, normalize_multiple_choice_question
from conversation_history import get_conversation_history
from metrics_tracker import get_metrics_tracker
from text_encoding import repair_mojibake_obj

# Import tính năng nâng cao
try:
    from compare_llm_rag import LLMRAGComparator
    from multi_document_qa import ask_question_multi_document
    ADVANCED_FEATURES = True
except ImportError:
    ADVANCED_FEATURES = False
    print("⚠️ Advanced features not available")

# Import authentication & chat history
from auth import auth_router
from auth.admin_routes import admin_router
from auth.user_routes import user_router
from auth.chat_history_manager import chat_history_manager

# ============================================================================
# FASTAPI APP INITIALIZATION
# ============================================================================

app = FastAPI(
    title="RAG System API",
    description="Backend API cho hệ thống Trợ lý Học tập Khai phá Dữ liệu",
    version="1.0.0"
)

@app.get("/api/questions/library")
async def get_library_topics():
    try:
        topics_count = {}
        if auth_manager.use_mongo:
            questions = list(auth_manager.db.questions.find({"created_by_user_id": {"$exists": False}}))
            for q in questions:
                topic = q.get("topic", "unknown")
                topics_count[topic] = topics_count.get(topic, 0) + 1

        # Always include the bundled JSON bank so syllabus-based seed exams show
        # up even when MongoDB is enabled but does not contain those topics yet.
        bank_path = os.path.join("data", "question_bank.json")
        if os.path.exists(bank_path):
            with open(bank_path, "r", encoding="utf-8") as f:
                data = json.load(f)
            for q in data.get("questions", []):
                topic = q.get("topic", "unknown")
                topics_count[topic] = topics_count.get(topic, 0) + 1
                    
        topics_list = [{"topic": k, "questionCount": v} for k, v in topics_count.items()]
        return {"status": "success", "topics": topics_list}
    except Exception as e:
        return {"status": "error", "message": str(e)}


# CORS middleware - Allow frontend to connect
_ALLOWED_ORIGINS = [
    "http://localhost:3000",
    "http://127.0.0.1:3000",
    "http://localhost:5173",
]
# Cho phép thêm origin từ env (để dễ deploy production)
_extra_origin = os.getenv("CORS_ORIGIN", "").strip()
if _extra_origin:
    _ALLOWED_ORIGINS.append(_extra_origin)

app.add_middleware(
    CORSMiddleware,
    allow_origins=_ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"],
    allow_headers=["Authorization", "Content-Type", "X-Requested-With"],
)

# Include authentication routes
app.include_router(auth_router, prefix="/api", tags=["Authentication & Chat History"])
app.include_router(admin_router)
app.include_router(user_router)

# ============================================================================
# GLOBAL VARIABLES
# ============================================================================
qa_chain = None
retriever = None
vectordb = None
documents = None
conv_history = None
metrics_tracker = None

# Loading status
loading_status = {
    "is_loading": True,
    "progress": 0,
    "message": "Starting...",
    "ready": False
}

# Session storage (trong production nên dùng Redis hoặc database)
sessions = {}

_LOCAL_FLASHCARD_SETS_PATH = os.path.join("data", "flashcard_sets_local.json")


def _load_local_flashcard_sets() -> Dict[str, List[Dict[str, Any]]]:
    if os.path.exists(_LOCAL_FLASHCARD_SETS_PATH):
        try:
            with open(_LOCAL_FLASHCARD_SETS_PATH, "r", encoding="utf-8") as f:
                data = json.load(f)
            return data if isinstance(data, dict) else {}
        except Exception:
            pass
    return {}


def _save_local_flashcard_sets(data: Dict[str, List[Dict[str, Any]]]) -> None:
    os.makedirs(os.path.dirname(_LOCAL_FLASHCARD_SETS_PATH), exist_ok=True)
    with open(_LOCAL_FLASHCARD_SETS_PATH, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2, default=str)


def _sanitize_flashcards(flashcards: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    sanitized = []
    for card in flashcards:
        sanitized.append({
            "front": str(card.get("front", "")).strip(),
            "back": str(card.get("back", "")).strip(),
            "category": str(card.get("category", "General")).strip() or "General",
        })
    return [card for card in sanitized if card["front"] and card["back"]]


def _save_flashcard_set_for_user(user_id: str, topic: str, flashcards: List[Dict[str, Any]]) -> Dict[str, Any]:
    now = datetime.utcnow()
    record = {
        "id": str(uuid.uuid4()),
        "user_id": user_id,
        "topic": topic.strip() or "Flashcards",
        "flashcards": _sanitize_flashcards(flashcards),
        "created_at": now,
        "updated_at": now,
    }

    if auth_manager.use_mongo:
        auth_manager.db.flashcard_sets.insert_one(record.copy())
    else:
        data = _load_local_flashcard_sets()
        serializable_record = {
            **record,
            "created_at": now.isoformat(),
            "updated_at": now.isoformat(),
        }
        data.setdefault(user_id, []).insert(0, serializable_record)
        data[user_id] = data[user_id][:50]
        _save_local_flashcard_sets(data)

    return {
        "id": record["id"],
        "topic": record["topic"],
        "count": len(record["flashcards"]),
        "created_at": now.isoformat(),
        "updated_at": now.isoformat(),
    }

# ============================================================================
# PYDANTIC MODELS
# ============================================================================
class QuestionRequest(BaseModel):
    question: str = Field(..., description="Câu hỏi của người dùng")
    session_id: Optional[str] = Field(None, description="ID phiên làm việc")
    use_context: bool = Field(True, description="Sử dụng context từ lịch sử")
    max_context_turns: int = Field(5, description="Số lượt hội thoại context")
    metadata_filter: Optional[Dict[str, Any]] = Field(None, description="Bộ lọc metadata cho tìm kiếm semantic")

class ChatMessagePart(BaseModel):
    text: str

class ChatMessageItem(BaseModel):
    role: str
    parts: List[ChatMessagePart]

class ChatRequest(BaseModel):
    thread_id: str
    messages: List[ChatMessageItem]
    metadata_filter: Optional[Dict[str, Any]] = None

class ChatResponse(BaseModel):
    text: str
    citations: List[Dict[str, Any]]


class QuestionResponse(BaseModel):
    answer: str
    sources: List[Dict[str, Any]]
    citations: List[Dict[str, Any]]
    session_id: str
    response_time: float

class SummaryRequest(BaseModel):
    topic: Optional[str] = Field(None, description="Chủ đề cần tóm tắt")
    session_id: Optional[str] = None
    metadata_filter: Optional[Dict[str, Any]] = None

class SummaryResponse(BaseModel):
    summary: str
    sources: List[Dict[str, Any]]
    citations: List[Dict[str, Any]]
    response_time: float

class FlashcardRequest(BaseModel):
    topic: str
    count: int = 5
    metadata_filter: Optional[Dict[str, Any]] = None

class FlashcardResponse(BaseModel):
    flashcards: List[Dict[str, Any]]
    saved_set: Optional[Dict[str, Any]] = None

class SavedFlashcardSetResponse(BaseModel):
    id: str
    topic: str
    count: int
    created_at: str
    updated_at: str

class QuizRequest(BaseModel):
    topic: Optional[str] = Field(None, description="Chủ đề quiz")
    num_questions: int = Field(5, ge=3, le=10, description="Số câu hỏi")
    session_id: Optional[str] = None

class QuizResponse(BaseModel):
    quiz_id: str
    questions: List[Dict[str, Any]]
    sources: List[Dict[str, Any]]
    total_questions: int

class QuizAnswerRequest(BaseModel):
    quiz_id: str
    question_index: int
    user_answer: str

class QuizAnswerResponse(BaseModel):
    is_correct: bool
    score: float
    feedback: str
    correct_answer: str
    explanation: Optional[str] = None
    source_reference: Optional[str] = None
    missing_points: Optional[List[str]] = None

class ComparisonRequest(BaseModel):
    question: str
    session_id: Optional[str] = None

class ComparisonResponse(BaseModel):
    llm_result: Dict[str, Any]
    rag_result: Dict[str, Any]
    comparison: Dict[str, Any]
    response_time: float

class MultiDocRequest(BaseModel):
    question: str
    use_synthesis: bool = Field(True, description="Tổng hợp từ nhiều tài liệu")
    session_id: Optional[str] = None

class MultiDocResponse(BaseModel):
    answer: str
    sources: List[Dict[str, Any]]
    citations: List[Dict[str, Any]]
    num_sources: int
    response_time: float

class SessionResponse(BaseModel):
    session_id: str
    message_count: int
    created_at: datetime

class HistoryResponse(BaseModel):
    messages: List[Dict[str, Any]]
    total_count: int

# ============================================================================
# STARTUP & SHUTDOWN
# ============================================================================
@app.on_event("startup")
async def startup_event():
    """Khởi tạo khi server start"""
    import asyncio
    
    # Start loading in background
    asyncio.create_task(load_rag_pipeline())
    
    print("✅ API Server ready! RAG pipeline loading in background...")
    print("📡 Frontend can connect now")
    print("⏳ RAG features will be available in ~30 seconds")

def _load_rag_pipeline_sync():
    """Blocking loader chạy trong thread pool (không block event loop)"""
    global qa_chain, retriever, vectordb, documents, conv_history, metrics_tracker, loading_status
    
    # Sử dụng chroma_db_new (đã rebuild với đầy đủ 5984 chunks bao gồm DM3.pdf)
    CHROMA_DIR = "chroma_db_new"
    
    try:
        loading_status["message"] = "Loading vector store..."
        loading_status["progress"] = 20
        print(f"📚 Loading vector store from '{CHROMA_DIR}'...")
        vectordb = load_vector_store(CHROMA_DIR)
        
        loading_status["message"] = "Loading documents..."
        loading_status["progress"] = 40
        print("📄 Loading documents...")
        documents = load_documents(CHROMA_DIR)
        
        loading_status["message"] = "Creating QA chain..."
        loading_status["progress"] = 60
        print("🔗 Creating QA chain...")
        qa_chain, retriever = create_qa_chain(vectordb, documents=documents, use_hybrid=True)
        
        loading_status["message"] = "Initializing services..."
        loading_status["progress"] = 80
        print("💬 Initializing conversation history...")
        conv_history = get_conversation_history(max_history=10)
        
        print("📊 Initializing metrics tracker...")
        metrics_tracker = get_metrics_tracker()
        
        loading_status["is_loading"] = False
        loading_status["progress"] = 100
        loading_status["message"] = "Ready!"
        loading_status["ready"] = True
        
        print("✅ RAG System fully ready!")
        
    except Exception as e:
        import traceback
        loading_status["is_loading"] = False
        loading_status["ready"] = False
        loading_status["message"] = f"Error: {str(e)}"
        print(f"❌ Error loading RAG pipeline: {e}")
        traceback.print_exc()

async def load_rag_pipeline():
    """Khởi động RAG pipeline trong thread pool để không block event loop"""
    import asyncio
    loop = asyncio.get_event_loop()
    await loop.run_in_executor(None, _load_rag_pipeline_sync)
    
    # Pre-warm LLM instance (tạo sẵn LLM để lần đầu hỏi không bị chờ)
    try:
        print("🔥 Pre-warming LLM instance...")
        from llm_router import get_llm
        get_llm(task_type="general")
        print("✅ LLM pre-warmed!")
    except Exception as e:
        print(f"⚠️ LLM pre-warm failed (non-critical): {e}")

@app.on_event("shutdown")
async def shutdown_event():
    """Cleanup khi server shutdown"""
    print("👋 Shutting down RAG System API...")

# ============================================================================
# HELPER FUNCTIONS
# ============================================================================
def get_or_create_session(session_id: Optional[str] = None) -> str:
    """Lấy hoặc tạo session mới"""
    if session_id:
        if session_id not in sessions:
            sessions[session_id] = {
                "created_at": datetime.now(),
                "messages": [],
                "quiz_data": None
            }
            if metrics_tracker:
                metrics_tracker.start_session(session_id)
        return session_id
    
    new_session_id = str(uuid.uuid4())
    sessions[new_session_id] = {
        "created_at": datetime.now(),
        "messages": [],
        "quiz_data": None
    }
    
    # Start metrics tracking
    if metrics_tracker:
        metrics_tracker.start_session(new_session_id)
    
    return new_session_id

def format_source_for_api(doc) -> Dict[str, Any]:
    """Format document thành dict cho API response"""
    def _clean_source_filename(value: Any) -> str:
        filename = str(value or "unknown").replace("\\", "/").split("/")[-1]
        filename = re.sub(r"-(?:\d{7,})(?=\.[A-Za-z0-9]+$)", "", filename)
        filename = re.sub(r"_(?:\d{7,})(?=\.[A-Za-z0-9]+$)", "", filename)
        return filename

    source = doc.metadata.get("source_file") or doc.metadata.get("source", "unknown")
    clean_source = _clean_source_filename(source)
    page = doc.metadata.get("page", "N/A")
    slide = doc.metadata.get("slide", None)
    if re.search(r"\.(?:docx?|txt)$", clean_source, re.IGNORECASE):
        page = ""
        slide = None
    return {
        "content": doc.page_content,
        "filename": clean_source,
        "source": clean_source,
        "page": page,
        "slide": slide,
        "metadata": {
            "source": clean_source,
            "page": page,
            "slide": slide,
        }
    }

# ============================================================================
# API ENDPOINTS
# ============================================================================

@app.get("/")
async def root():
    """Health check endpoint"""
    return {
        "status": "ok",
        "message": "RAG System API is running",
        "version": "1.0.0",
        "features": {
            "authentication": True,
            "chat_history": True,
            "rag_qa": True,
            "quiz": True,
            "comparison": ADVANCED_FEATURES,
            "multi_document": ADVANCED_FEATURES
        },
        "endpoints": {
            "auth": {
                "register": "/api/auth/register",
                "login": "/api/auth/login",
                "me": "/api/auth/me",
                "change_password": "/api/auth/change-password"
            },
            "chat": {
                "conversations": "/api/conversations",
                "messages": "/api/conversations/{id}/messages",
                "search": "/api/conversations/search"
            },
            "rag": {
                "qa": "/api/question",
                "summary": "/api/summary",
                "quiz": "/api/quiz",
                "comparison": "/api/compare",
                "multi_doc": "/api/multi-document"
            },
            "session": "/api/session",
            "history": "/api/history/{session_id}"
        }
    }

@app.get("/health")
async def health_check():
    """Kiểm tra trạng thái hệ thống"""
    return {
        "status": "healthy" if loading_status["ready"] else "loading",
        "qa_chain": qa_chain is not None,
        "retriever": retriever is not None,
        "vectordb": vectordb is not None,
        "documents_loaded": documents is not None and len(documents) > 0,
        "active_sessions": len(sessions),
        "timestamp": datetime.now().isoformat(),
        "loading": {
            "is_loading": loading_status["is_loading"],
            "progress": loading_status["progress"],
            "message": loading_status["message"],
            "ready": loading_status["ready"]
        }
    }

def get_allowed_filenames(user_id: str) -> list[str]:
    import os
    data_dir = os.path.join(os.path.dirname(__file__), "data")
    if not os.path.exists(data_dir):
        return []
    
    allowed = []
    user_prefix = f"{user_id}__"
    for filename in os.listdir(data_dir):
        if filename.startswith(user_prefix) or "__" not in filename:
            allowed.append(filename)
            # Thêm đường dẫn data/ để ChromaDB match chính xác metadata
            allowed.append(f"data\\{filename}")
            allowed.append(f"data/{filename}")
            
    # ChromaDB IN query requires non-empty list. Add a dummy if empty.
    if not allowed:
        allowed.append("_none_")
    return allowed

@app.post("/api/question", response_model=QuestionResponse)
async def ask_question_endpoint(request: QuestionRequest, current_user: dict = Depends(get_current_user)):
    """Endpoint hỏi đáp với RAG (non-streaming)"""
    if not loading_status["ready"]:
        # Chờ pipeline sẵn sàng tối đa 120 giây thay vì từ chối ngay
        waited = 0
        while not loading_status["ready"] and waited < 120:
            await asyncio.sleep(2)
            waited += 2
        if not loading_status["ready"]:
            raise HTTPException(
                status_code=503,
                detail=f"RAG pipeline is still loading: {loading_status['message']} ({loading_status['progress']}%)"
            )

    start_time = time.time()
    session_id = get_or_create_session(request.session_id)

    try:
        context = ""
        if request.use_context and conv_history:
            context = conv_history.get_context_for_llm(session_id, max_turns=request.max_context_turns)

        # Merge metadata_filter with security filter
        user_id = current_user.get("user_id", "default")
        allowed_files = get_allowed_filenames(user_id)
        security_filter = {"source": {"$in": allowed_files}}
        
        final_filter = security_filter
        if request.metadata_filter:
            final_filter = {"$and": [request.metadata_filter, security_filter]}

        answer, sources, citations = await asyncio.to_thread(
            ask_question, qa_chain, retriever, request.question, context, final_filter
        )

        # Log interaction for user profiling
        if user_id != "default":
            await asyncio.to_thread(
                auth_manager.log_interaction, user_id, request.question, sources, "chat"
            )

        if conv_history:
            conv_history.save_message(session_id, "user", request.question)
            conv_history.save_message(session_id, "assistant", answer, citations=citations)

        sessions[session_id]["messages"].extend([
            {"role": "user", "content": request.question},
            {"role": "assistant", "content": answer, "citations": citations}
        ])

        return QuestionResponse(
            answer=answer,
            sources=[format_source_for_api(doc) for doc in sources],
            citations=citations,
            session_id=session_id,
            response_time=time.time() - start_time,
        )
    except Exception as e:
        if str(e) == "API_RATE_LIMIT_STANDALONE":
            raise HTTPException(
                status_code=429,
                detail="⚠️ **Hệ thống đang quá tải API (Rate Limit của Google Gemini)**.\n\nCâu hỏi của bạn là một câu hỏi tiếp nối (cần ghép ngữ cảnh), nhưng do vượt quá giới hạn 15 yêu cầu/phút của bản miễn phí, hệ thống không thể phân tích ngữ cảnh được. Vui lòng chờ khoảng 1 phút rồi thử lại nhé!"
            )
@app.post("/api/chat", response_model=ChatResponse)
async def chat_endpoint(request: ChatRequest, current_user: dict = Depends(get_current_user)):
    """Bridge endpoint phục vụ cho MentorTab frontend"""
    if not loading_status["ready"]:
        waited = 0
        while not loading_status["ready"] and waited < 120:
            await asyncio.sleep(2)
            waited += 2
        if not loading_status["ready"]:
            raise HTTPException(
                status_code=503,
                detail=f"RAG pipeline is still loading: {loading_status['message']} ({loading_status['progress']}%)"
            )

    if not request.messages:
        raise HTTPException(status_code=400, detail="No messages provided")

    # Lấy câu hỏi cuối cùng
    last_message = request.messages[-1]
    if not last_message.parts or not last_message.parts[0].text:
        raise HTTPException(status_code=400, detail="Last message text is empty")
        
    question_text = last_message.parts[0].text
    session_id = get_or_create_session(request.thread_id)

    try:
        context = ""
        if conv_history:
            context = conv_history.get_context_for_llm(session_id, max_turns=5)

        # Merge metadata_filter với security filter
        user_id = current_user.get("user_id", "default")
        allowed_files = get_allowed_filenames(user_id)
        security_filter = {"source": {"$in": allowed_files}}
        
        final_filter = security_filter
        if request.metadata_filter:
            final_filter = {"$and": [request.metadata_filter, security_filter]}

        answer, sources, citations = await asyncio.to_thread(
            ask_question, qa_chain, retriever, question_text, context, final_filter
        )

        # Ghi log tương tác
        if user_id != "default":
            await asyncio.to_thread(
                auth_manager.log_interaction, user_id, question_text, sources, "chat"
            )
            try:
                from learning_tracker import get_tracker

                await asyncio.to_thread(
                    get_tracker().log_question,
                    user_id,
                    question_text,
                    answer,
                    [os.path.basename(getattr(doc, "metadata", {}).get("source", "")) for doc in sources if getattr(doc, "metadata", {}).get("source")]
                )
            except Exception as e:
                print(f"⚠️ Không thể lưu learning event cho chat: {e}")

        if conv_history:
            conv_history.save_message(session_id, "user", question_text)
            conv_history.save_message(session_id, "assistant", answer, citations=citations)

        sessions[session_id]["messages"].extend([
            {"role": "user", "content": question_text},
            {"role": "assistant", "content": answer, "citations": citations}
        ])

        return ChatResponse(
            text=answer,
            citations=citations
        )
    except Exception as e:
        if str(e) == "API_RATE_LIMIT_STANDALONE":
            raise HTTPException(
                status_code=429,
                detail="⚠️ **Hệ thống đang quá tải API (Rate Limit của Google Gemini)**.\n\nCâu hỏi của bạn là một câu hỏi tiếp nối (cần ghép ngữ cảnh), nhưng do vượt quá giới hạn 15 yêu cầu/phút của bản miễn phí, hệ thống không thể phân tích ngữ cảnh được. Vui lòng chờ khoảng 1 phút rồi thử lại nhé!"
            )
        raise HTTPException(status_code=500, detail=f"Error in chat endpoint: {str(e)}")


@app.post("/api/question/stream")
async def ask_question_stream(request: QuestionRequest, current_user: dict = Depends(get_current_user)):
    """
    Streaming endpoint — gửi câu trả lời từng đoạn (Server-Sent Events).
    Frontend đọc qua EventSource hoặc fetch + ReadableStream.
    Format mỗi dòng: data: <json>\n\n
    Events: token | citations | done | error
    """
    if not loading_status["ready"]:
        async def _err():
            msg = json.dumps({"event": "error", "detail": f"RAG loading: {loading_status['message']}"})
            yield f"data: {msg}\n\n"
        return StreamingResponse(_err(), media_type="text/event-stream")

    session_id = get_or_create_session(request.session_id)

    async def event_stream() -> AsyncGenerator[str, None]:
        try:
            context = ""
            if request.use_context and conv_history:
                context = conv_history.get_context_for_llm(session_id, max_turns=request.max_context_turns)

            # Merge metadata_filter with security filter
            user_id = current_user.get("user_id", "default")
            allowed_files = get_allowed_filenames(user_id)
            security_filter = {"source": {"$in": allowed_files}}
            
            final_filter = security_filter
            if request.metadata_filter:
                final_filter = {"$and": [request.metadata_filter, security_filter]}

            # Chạy ask_question trong thread để không block event loop
            answer, sources, citations = await asyncio.to_thread(
                ask_question, qa_chain, retriever, request.question, context, final_filter
            )

            # Stream câu trả lời theo từng đoạn ~80 ký tự
            chunk_size = 80
            for i in range(0, len(answer), chunk_size):
                chunk = answer[i:i + chunk_size]
                payload = json.dumps({"event": "token", "text": chunk}, ensure_ascii=False)
                yield f"data: {payload}\n\n"
                await asyncio.sleep(0.015)  # 15ms delay — mượt hơn với mắt người

            # Gửi citations sau khi stream xong
            citations_payload = json.dumps({"event": "citations", "citations": citations}, ensure_ascii=False)
            yield f"data: {citations_payload}\n\n"

            # Gửi done
            done_payload = json.dumps({"event": "done", "session_id": session_id})
            yield f"data: {done_payload}\n\n"

            # Lưu vào lịch sử
            if conv_history:
                conv_history.save_message(session_id, "user", request.question)
                conv_history.save_message(session_id, "assistant", answer, citations=citations)

        except Exception as e:
            if str(e) == "API_RATE_LIMIT_STANDALONE":
                answer_text = "⚠️ **Hệ thống đang quá tải API (Rate Limit của Google Gemini)**.\n\nCâu hỏi của bạn là một câu hỏi tiếp nối (cần ghép ngữ cảnh), nhưng do vượt quá giới hạn 15 yêu cầu/phút của bản miễn phí, hệ thống không thể phân tích ngữ cảnh được. Vui lòng chờ khoảng 1 phút rồi thử lại nhé!"
                for i in range(0, len(answer_text), 80):
                    chunk = answer_text[i:i + 80]
                    yield f"data: {json.dumps({'event': 'token', 'text': chunk}, ensure_ascii=False)}\n\n"
                    import asyncio
                    await asyncio.sleep(0.015)
                yield f"data: {json.dumps({'event': 'done', 'session_id': session_id})}\n\n"
                return
            err_payload = json.dumps({"event": "error", "detail": str(e)})
            yield f"data: {err_payload}\n\n"

    return StreamingResponse(
        event_stream(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "X-Accel-Buffering": "no",  # Tắt nginx buffering
        },
    )

@app.post("/api/summary", response_model=SummaryResponse)
async def create_summary(request: SummaryRequest, current_user: dict = Depends(get_current_user)):
    """
    Endpoint tạo tóm tắt có cấu trúc
    """
    start_time = time.time()
    
    try:
        from rag import generate_structured_summary
        import asyncio
        
        # Merge metadata_filter with security filter
        user_id = current_user.get("user_id", "default")
        allowed_files = get_allowed_filenames(user_id)
        security_filter = {"source": {"$in": allowed_files}}
        
        final_filter = security_filter
        if request.metadata_filter:
            final_filter = {"$and": [request.metadata_filter, security_filter]}

        # Get summary (run in thread pool to prevent blocking uvicorn event loop)
        summary, sources, citations = await asyncio.to_thread(
            generate_structured_summary, retriever, request.topic or "Tổng quan Khai phá dữ liệu", final_filter
        )
        
        response_time = time.time() - start_time
        if user_id != "default":
            try:
                from learning_tracker import get_tracker

                await asyncio.to_thread(
                    get_tracker().log_learning_event,
                    user_id,
                    "summary_generated",
                    request.topic or "Tổng quan Khai phá dữ liệu",
                    {
                        "source_count": len(sources),
                        "response_time": response_time,
                    },
                )
            except Exception as e:
                print(f"⚠️ Không thể lưu learning event cho summary: {e}")
        
        return SummaryResponse(
            summary=summary,
            sources=[format_source_for_api(doc) for doc in sources],
            citations=citations,
            response_time=response_time
        )
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error creating summary: {str(e)}")

@app.post("/api/flashcards", response_model=FlashcardResponse)
async def create_flashcards(request: FlashcardRequest, current_user: dict = Depends(get_current_user)):
    """
    Endpoint tạo flashcards tự động
    """
    try:
        from rag import generate_flashcards
        import asyncio
        
        # Merge metadata_filter with security filter
        user_id = current_user.get("user_id", "default")
        allowed_files = get_allowed_filenames(user_id)
        security_filter = {"source": {"$in": allowed_files}}
        
        final_filter = security_filter
        if request.metadata_filter:
            final_filter = {"$and": [request.metadata_filter, security_filter]}

        flashcards = await asyncio.to_thread(
            generate_flashcards, retriever, request.topic, request.count, final_filter
        )
        saved_set = None
        if user_id != "default":
            saved_set = await asyncio.to_thread(
                _save_flashcard_set_for_user,
                user_id,
                request.topic,
                flashcards,
            )
            try:
                from learning_tracker import get_tracker

                await asyncio.to_thread(
                    get_tracker().log_learning_event,
                    user_id,
                    "flashcards_generated",
                    request.topic,
                    {"count": len(flashcards)},
                )
            except Exception as e:
                print(f"⚠️ Không thể lưu learning event cho flashcards: {e}")
        
        return FlashcardResponse(flashcards=flashcards, saved_set=saved_set)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error creating flashcards: {str(e)}")

@app.get("/api/flashcards/saved", response_model=List[SavedFlashcardSetResponse])
async def list_saved_flashcards(current_user: dict = Depends(get_current_user)):
    user_id = current_user.get("user_id", "default")
    if user_id == "default":
        return []

    if auth_manager.use_mongo:
        rows = list(
            auth_manager.db.flashcard_sets.find(
                {"user_id": user_id},
                {"_id": 0, "id": 1, "topic": 1, "flashcards": 1, "created_at": 1, "updated_at": 1},
            ).sort("updated_at", -1).limit(50)
        )
    else:
        rows = _load_local_flashcard_sets().get(user_id, [])

    result = []
    for row in rows:
        created_at = row.get("created_at")
        updated_at = row.get("updated_at") or created_at
        result.append({
            "id": row.get("id", ""),
            "topic": row.get("topic", "Flashcards"),
            "count": len(row.get("flashcards", [])),
            "created_at": created_at.isoformat() if hasattr(created_at, "isoformat") else str(created_at or ""),
            "updated_at": updated_at.isoformat() if hasattr(updated_at, "isoformat") else str(updated_at or ""),
        })
    return result

@app.get("/api/flashcards/saved/{set_id}")
async def get_saved_flashcard_set(set_id: str, current_user: dict = Depends(get_current_user)):
    user_id = current_user.get("user_id", "default")
    if user_id == "default":
        raise HTTPException(status_code=401, detail="Not authenticated")

    if auth_manager.use_mongo:
        row = auth_manager.db.flashcard_sets.find_one({"id": set_id, "user_id": user_id}, {"_id": 0})
    else:
        row = next(
            (item for item in _load_local_flashcard_sets().get(user_id, []) if item.get("id") == set_id),
            None,
        )

    if not row:
        raise HTTPException(status_code=404, detail="Flashcard set not found")

    created_at = row.get("created_at")
    updated_at = row.get("updated_at") or created_at
    return {
        "id": row.get("id"),
        "topic": row.get("topic", "Flashcards"),
        "flashcards": row.get("flashcards", []),
        "created_at": created_at.isoformat() if hasattr(created_at, "isoformat") else str(created_at or ""),
        "updated_at": updated_at.isoformat() if hasattr(updated_at, "isoformat") else str(updated_at or ""),
    }

@app.delete("/api/flashcards/saved/{set_id}")
async def delete_saved_flashcard_set(set_id: str, current_user: dict = Depends(get_current_user)):
    user_id = current_user.get("user_id", "default")
    if user_id == "default":
        raise HTTPException(status_code=401, detail="Not authenticated")

    if auth_manager.use_mongo:
        result = auth_manager.db.flashcard_sets.delete_one({"id": set_id, "user_id": user_id})
        deleted = result.deleted_count > 0
    else:
        data = _load_local_flashcard_sets()
        original_len = len(data.get(user_id, []))
        data[user_id] = [item for item in data.get(user_id, []) if item.get("id") != set_id]
        deleted = len(data[user_id]) < original_len
        _save_local_flashcard_sets(data)

    if not deleted:
        raise HTTPException(status_code=404, detail="Flashcard set not found")
    return {"success": True}

@app.get("/api/quiz/topics")
async def get_quiz_topics():
    if not auth_manager.use_mongo:
        return {"success": True, "topics": [
            {"id": "apriori", "count": 10}, 
            {"id": "fp_growth", "count": 10}, 
            {"id": "kmeans", "count": 10}, 
            {"id": "dbscan", "count": 10}
        ]}
    
    try:
        pipeline = [
            {"$group": {"_id": "$topic", "count": {"$sum": 1}}}
        ]
        results = list(auth_manager.db.questions.aggregate(pipeline))
        topics = [{"id": r["_id"], "count": r["count"]} for r in results if r["_id"]]
        return {"success": True, "topics": topics}
    except Exception as e:
        logger.error(f"Error fetching topics: {str(e)}")
        return {"success": False, "topics": []}

@app.post("/api/quiz", response_model=QuizResponse)
async def create_quiz(request: QuizRequest, current_user: dict = Depends(get_current_user)):
    """
    Endpoint tạo quiz tương tác
    """
    session_id = get_or_create_session(request.session_id)
    
    try:
        import asyncio
        # Compute security filter for Quiz
        user_id = current_user.get("user_id", "default")
        allowed_files = get_allowed_filenames(user_id)
        security_filter = {"source": {"$in": allowed_files}}

        # Generate quiz (run in thread pool to prevent blocking uvicorn event loop)
        quiz_data = await asyncio.to_thread(
            generate_interactive_quiz,
            retriever, 
            request.topic, 
            request.num_questions,
            "Vietnamese",
            security_filter
        )
        
        # Log quiz creation interaction
        if user_id != "default":
            await asyncio.to_thread(
                auth_manager.log_interaction, user_id, request.topic, quiz_data.get("sources", []), "quiz_generated"
            )
        
        # Create quiz ID
        quiz_id = str(uuid.uuid4())
        
        # Save to session
        sessions[session_id]["quiz_data"] = {
            "quiz_id": quiz_id,
            "topic": request.topic,
            "data": quiz_data,
            "results": []
        }
        
        return QuizResponse(
            quiz_id=quiz_id,
            questions=quiz_data["questions"],
            sources=quiz_data.get("sources", []),
            total_questions=len(quiz_data["questions"])
        )
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error creating quiz: {str(e)}")

@app.post("/api/quiz/custom-practice", response_model=QuizResponse)
async def create_custom_practice_quiz(request: QuizRequest, current_user: dict = Depends(get_current_user)):
    """
    Endpoint tạo quiz TỪ NGÂN HÀNG CÁ NHÂN (Custom Practice)
    """
    session_id = get_or_create_session(request.session_id)
    
    try:
        user_id = current_user.get("user_id", current_user.get("email"))
        
        if not auth_manager.use_mongo:
            raise HTTPException(status_code=500, detail="Tính năng cần kết nối MongoDB")
            
        # Lọc câu hỏi cá nhân theo topic (hoặc toàn bộ nếu topic trống)
        query = {"created_by_user_id": user_id}
        if request.topic:
            # Match regex case insensitive
            query["topic"] = {"$regex": f"^{request.topic.lower()}$", "$options": "i"}
            
        questions = [
            repair_mojibake_obj(q)
            for q in auth_manager.db.questions.find(query, {"_id": 0})
        ]
        
        if not questions:
            raise HTTPException(status_code=404, detail="Không tìm thấy câu hỏi cá nhân phù hợp")
            
        def shuffle_question_options(question: dict) -> dict:
            question = normalize_multiple_choice_question(question)
            options = question.get("options")
            correct_answer = question.get("correct_answer")
            if not isinstance(options, dict) or not correct_answer:
                return question

            option_items = [(key, options[key]) for key in ["A", "B", "C", "D"] if key in options]
            if len(option_items) < 2:
                return question

            correct_text = options.get(correct_answer, correct_answer)
            shuffled_items = option_items[:]
            random.shuffle(shuffled_items)
            new_options = {}
            new_correct = correct_answer
            for idx, (_, text) in enumerate(shuffled_items):
                new_key = ["A", "B", "C", "D"][idx]
                new_options[new_key] = text
                if text == correct_text:
                    new_correct = new_key

            shuffled_question = dict(question)
            shuffled_question["options"] = new_options
            shuffled_question["correct_answer"] = new_correct
            return shuffled_question

        # Shuffle & limit
        import random
        random.shuffle(questions)
        selected_questions = [shuffle_question_options(q) for q in questions[:request.num_questions]]
        
        # Create quiz ID
        quiz_id = str(uuid.uuid4())
        
        # Build mock quiz_data
        quiz_data = {
            "questions": selected_questions,
            "sources": []
        }
        
        # Save to session
        sessions[session_id]["quiz_data"] = {
            "quiz_id": quiz_id,
            "topic": f"My Questions: {request.topic}",
            "data": quiz_data,
            "results": []
        }
        
        return QuizResponse(
            quiz_id=quiz_id,
            questions=quiz_data["questions"],
            sources=[],
            total_questions=len(quiz_data["questions"])
        )
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Lỗi tạo đề tự tạo: {str(e)}")

@app.post("/api/quiz/answer", response_model=QuizAnswerResponse)
async def submit_quiz_answer(request: QuizAnswerRequest):
    """
    Endpoint nộp câu trả lời quiz
    """
    try:
        # Find session with this quiz
        session_id = None
        for sid, session in sessions.items():
            if session.get("quiz_data") and session["quiz_data"]["quiz_id"] == request.quiz_id:
                session_id = sid
                break
        
        if not session_id:
            raise HTTPException(status_code=404, detail="Quiz not found")
        
        quiz_data = sessions[session_id]["quiz_data"]["data"]
        
        # Get question
        if request.question_index >= len(quiz_data["questions"]):
            raise HTTPException(status_code=400, detail="Invalid question index")
        
        question = quiz_data["questions"][request.question_index]
        
        # Evaluate answer
        result = evaluate_answer(question, request.user_answer)
        
        # Save result
        sessions[session_id]["quiz_data"]["results"].append(result)
        
        return QuizAnswerResponse(**result)
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error evaluating answer: {str(e)}")

@app.get("/api/quiz/{quiz_id}/results")
async def get_quiz_results(quiz_id: str, current_user: dict = Depends(get_current_user)):
    """
    Lấy kết quả tổng của quiz và lưu vào MongoDB
    """
    try:
        # Find session with this quiz
        session_id = None
        for sid, session in sessions.items():
            if session.get("quiz_data") and session["quiz_data"]["quiz_id"] == quiz_id:
                session_id = sid
                break
        
        if not session_id:
            raise HTTPException(status_code=404, detail="Quiz not found")
        
        results = sessions[session_id]["quiz_data"]["results"]
        total_questions = len(sessions[session_id]["quiz_data"]["data"]["questions"])
        
        if not results:
            raise HTTPException(status_code=400, detail="No answers submitted yet")
        
        # Calculate score
        score_data = calculate_quiz_score(results, total_questions)
        
        # Lưu vào MongoDB
        try:
            topic = sessions[session_id]["quiz_data"].get("topic", "general")
            user_id = current_user.get("user_id", "default")
            
            result_doc = {
                "user_id": user_id,
                "email": current_user.get("email"),
                "quiz_id": quiz_id,
                "topic": topic,
                "score": score_data,
                "total_questions": total_questions,
                "answered_questions": len(results),
                "created_at": datetime.utcnow()
            }
            
            if auth_manager.use_mongo and user_id != "default":
                # Tránh lưu trùng lặp nếu frontend gọi nhiều lần
                existing = auth_manager.db.quiz_results.find_one({"quiz_id": quiz_id})
                if not existing:
                    auth_manager.db.quiz_results.insert_one(result_doc)
                    
                    # Gọi tracker để cập nhật tiến độ (Cá nhân hoá)
                    try:
                        from learning_tracker import get_tracker
                        tracker = get_tracker()
                        questions = sessions[session_id]["quiz_data"]["data"]["questions"]
                        tracker.log_quiz_attempt(
                            user_id,
                            topic,
                            questions,
                            results,
                            score_data.get("percentage", 0),
                        )
                    except Exception as e:
                        print(f"⚠️ Không thể cập nhật tracker: {e}")
        except Exception as e:
            print(f"⚠️ Lỗi lưu quiz_results: {e}")
        
        return {
            "quiz_id": quiz_id,
            "results": results,
            "score": score_data,
            "total_questions": total_questions,
            "answered_questions": len(results)
        }
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error getting quiz results: {str(e)}")

@app.post("/api/compare", response_model=ComparisonResponse)
async def compare_llm_rag(request: ComparisonRequest):
    """
    Endpoint so sánh LLM vs RAG
    """
    if not ADVANCED_FEATURES:
        raise HTTPException(status_code=501, detail="Comparison feature not available")
    
    start_time = time.time()
    
    try:
        # Create comparator
        comparator = LLMRAGComparator()
        comparator.qa_chain = qa_chain
        comparator.retriever = retriever
        
        import asyncio
        # Run comparison (run in thread pool to prevent blocking uvicorn event loop)
        result = await asyncio.to_thread(comparator.compare, request.question)
        
        response_time = time.time() - start_time
        result["response_time"] = response_time
        
        return ComparisonResponse(**result)
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error comparing: {str(e)}")

@app.post("/api/multi-document", response_model=MultiDocResponse)
async def multi_document_qa(request: MultiDocRequest):
    """
    Endpoint Multi-Document QA
    """
    if not ADVANCED_FEATURES:
        raise HTTPException(status_code=501, detail="Multi-document feature not available")
    
    start_time = time.time()
    
    try:
        import asyncio
        # Ask question with multi-document synthesis (run in thread pool to prevent blocking uvicorn event loop)
        answer, sources, citations = await asyncio.to_thread(
            ask_question_multi_document,
            qa_chain,
            retriever,
            request.question,
            "",
            True,
            request.use_synthesis
        )
        
        response_time = time.time() - start_time
        
        return MultiDocResponse(
            answer=answer,
            sources=[format_source_for_api(doc) for doc in sources],
            citations=citations,
            num_sources=len(sources),
            response_time=response_time
        )
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error in multi-document QA: {str(e)}")

@app.post("/api/session", response_model=SessionResponse)
async def create_session():
    """
    Tạo session mới
    """
    session_id = get_or_create_session()
    
    return SessionResponse(
        session_id=session_id,
        message_count=0,
        created_at=sessions[session_id]["created_at"]
    )

@app.get("/api/session/{session_id}", response_model=SessionResponse)
async def get_session(session_id: str):
    """
    Lấy thông tin session
    """
    if session_id not in sessions:
        raise HTTPException(status_code=404, detail="Session not found")
    
    session = sessions[session_id]
    
    return SessionResponse(
        session_id=session_id,
        message_count=len(session["messages"]),
        created_at=session["created_at"]
    )

@app.delete("/api/session/{session_id}")
async def delete_session(session_id: str):
    """
    Xóa session
    """
    if session_id not in sessions:
        raise HTTPException(status_code=404, detail="Session not found")
    
    # Clear conversation history
    if conv_history:
        conv_history.clear_history(session_id)
    
    # Delete session
    del sessions[session_id]
    
    return {"message": "Session deleted successfully"}

@app.get("/api/history/{session_id}", response_model=HistoryResponse)
async def get_history(session_id: str, limit: int = 10):
    """
    Lấy lịch sử hội thoại
    """
    if not conv_history:
        raise HTTPException(status_code=501, detail="Conversation history not available")
    
    try:
        messages = conv_history.get_recent_messages(session_id, n=limit)
        
        return HistoryResponse(
            messages=messages,
            total_count=len(messages)
        )
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error getting history: {str(e)}")

@app.delete("/api/history/{session_id}")
async def clear_history(session_id: str):
    """
    Xóa lịch sử hội thoại
    """
    if not conv_history:
        raise HTTPException(status_code=501, detail="Conversation history not available")
    
    try:
        conv_history.clear_history(session_id)
        
        # Also clear from session
        if session_id in sessions:
            sessions[session_id]["messages"] = []
        
        return {"message": "History cleared successfully"}
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error clearing history: {str(e)}")

@app.post("/api/upload")
async def upload_document(
    file: UploadFile = File(...),
    current_user: dict = Depends(get_current_user)
):
    """
    Endpoint nhận file upload (PDF, PPTX, DOCX), trích xuất văn bản, chunking
    và cập nhật vector database (ChromaDB) theo thời gian thực.
    """
    if not loading_status["ready"]:
        raise HTTPException(status_code=503, detail="RAG pipeline is not ready yet")
        
    try:
        # Validate extension
        user_id = current_user.get("user_id", "default")
        original_filename = file.filename
        filename = f"{user_id}__{original_filename}"
        ext = os.path.splitext(original_filename)[1].lower()
        if ext not in [".pdf", ".pptx", ".docx", ".txt"]:
            raise HTTPException(status_code=400, detail="Only PDF, PPTX, DOCX, TXT allowed")
            
        # Create data dir
        os.makedirs("data", exist_ok=True)
        file_path = os.path.join("data", filename)
        
        # Save file
        import shutil
        with open(file_path, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)
            
        # Process file in thread
        import asyncio
        from loader import load_pdf, load_ppt, load_docx, clean_text, chunk_documents
        import pickle
        
        def process_new_file():
            global documents, vectordb
            
            docs = []
            if ext == ".pdf":
                docs = load_pdf(file_path)
            elif ext == ".pptx":
                docs = load_ppt(file_path)
            elif ext == ".docx":
                docs = load_docx(file_path)
            elif ext == ".txt":
                from langchain_core.documents import Document
                import hashlib
                from datetime import datetime
                from config import EMBEDDING_MODEL_NAME
                with open(file_path, "r", encoding="utf-8") as f:
                    content = f.read()
                now = datetime.utcnow().isoformat()
                chunk_id = hashlib.md5(f"{filename}:txt:{content[:80]}".encode()).hexdigest()[:16]
                docs = [Document(
                    page_content=content,
                    metadata={
                        "chunk_id": chunk_id,
                        "source_file": filename,
                        "source": file_path,
                        "page_number": 1,
                        "page": 1,
                        "section": "Full text",
                        "file_type": "txt",
                        "created_at": now,
                        "embedding_model": EMBEDDING_MODEL_NAME,
                    }
                )]
            
            if not docs:
                raise ValueError(
                    f"Không trích xuất được nội dung từ file {original_filename}. "
                    "File có thể là ảnh scan, rỗng hoặc định dạng không được hỗ trợ."
                )

            cleaned_docs = []
            for doc in docs:
                doc.page_content = clean_text(doc.page_content or "")
                if doc.page_content.strip():
                    cleaned_docs.append(doc)

            extracted_chars = sum(len(doc.page_content) for doc in cleaned_docs)
            print(
                f"📥 Upload extracted {len(cleaned_docs)} docs / "
                f"{extracted_chars} chars from {filename}"
            )
            if not cleaned_docs:
                raise ValueError(
                    f"File {original_filename} không có văn bản đọc được sau khi làm sạch. "
                    "Nếu đây là PDF scan/ảnh, cần OCR trước khi nạp vào RAG."
                )
                
            chunks = chunk_documents(cleaned_docs)
            if not chunks:
                raise ValueError(
                    f"File {original_filename} đã trích xuất được {extracted_chars} ký tự "
                    "nhưng không tạo được chunk nào. Vui lòng kiểm tra cấu trúc nội dung file."
                )
                
            # Add to vectordb
            if vectordb:
                vectordb.add_documents(chunks)
                vectordb.persist()
                print(f"✅ Added {len(chunks)} chunks to vector database.")
                
            # Update global documents and save pickle
            if documents is not None:
                documents.extend(chunks)
                CHROMA_DIR = "chroma_db_new"
                documents_path = os.path.join(CHROMA_DIR, "documents.pkl")
                try:
                    with open(documents_path, 'wb') as f:
                        pickle.dump(documents, f)
                    print(f"✅ Updated {documents_path} with new documents.")
                except Exception as e:
                    print(f"❌ Error saving documents.pkl: {e}")
                    
            return len(chunks)
            
        try:
            chunks_added = await asyncio.to_thread(process_new_file)
        except ValueError as e:
            try:
                if os.path.exists(file_path):
                    os.remove(file_path)
            except Exception as cleanup_error:
                print(f"⚠️ Could not remove failed upload {file_path}: {cleanup_error}")
            raise HTTPException(status_code=422, detail=str(e))

        if chunks_added <= 0:
            try:
                if os.path.exists(file_path):
                    os.remove(file_path)
            except Exception as cleanup_error:
                print(f"⚠️ Could not remove zero-chunk upload {file_path}: {cleanup_error}")
            raise HTTPException(
                status_code=422,
                detail=(
                    f"File {original_filename} đã tải lên nhưng không tạo được chunk nào. "
                    "Vui lòng kiểm tra file có văn bản đọc được hay không."
                ),
            )
        
        return {
            "success": True,
            "message": f"Successfully uploaded and processed {filename}",
            "chunks_added": chunks_added,
            "file_path": file_path
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

class DatasetAnalysisRequest(BaseModel):
    filename: str
    fileContent: str
    algorithm: str
    columnX: Optional[str] = None
    columnY: Optional[str] = None
    paramK: Optional[int] = 3
    paramEps: Optional[float] = 0.5
    paramMinSamples: Optional[int] = 5
    paramSupport: Optional[float] = 0.1
    paramConfidence: Optional[float] = 0.5
    paramMaxDepth: Optional[int] = 5

@app.post("/api/analyze-dataset")
async def analyze_dataset(
    request: DatasetAnalysisRequest,
    current_user: dict = Depends(get_current_user)
):
    import io
    import pandas as pd
    import numpy as np
    
    filename = request.filename
    content = request.fileContent
    algorithm = request.algorithm
    
    # 1. Đọc CSV và giới hạn kích thước tài nguyên
    try:
        df = pd.read_csv(io.StringIO(content))
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Lỗi đọc định dạng file CSV: {str(e)}")
        
    if df.empty:
        raise HTTPException(status_code=400, detail="Bộ dữ liệu tải lên bị trống.")
        
    MAX_ROWS = 20000
    if len(df) > MAX_ROWS:
        df = df.iloc[:MAX_ROWS]
        
    features = list(df.columns)
    instances = len(df)
    
    logs = [
        f"[HỆ THỐNG] Nạp thành công tệp: {filename}.",
        f"[HỆ THỐNG] Phát hiện {len(features)} thuộc tính và {instances} bản ghi dữ liệu."
    ]
    
    try:
        summary = ""
        metrics = {}
        visualization_data = {}
        
        # 2. XỬ LÝ THEO THUẬT TOÁN THỰC TẾ
        if algorithm == "K-Means":
            from sklearn.cluster import KMeans
            colX = request.columnX if request.columnX in df.columns else df.columns[0]
            colY = request.columnY if request.columnY in df.columns else (df.columns[1] if len(df.columns) > 1 else df.columns[0])
            
            logs.append(f"[THAM SỐ] Chọn trục X: '{colX}', trục Y: '{colY}', số cụm k: {request.paramK}")
            
            df_clean = df[[colX, colY]].dropna().copy()
            df_clean[colX] = pd.to_numeric(df_clean[colX], errors='coerce')
            df_clean[colY] = pd.to_numeric(df_clean[colY], errors='coerce')
            df_clean = df_clean.dropna()
            
            if df_clean.empty:
                raise ValueError(f"Không tìm thấy thuộc tính số hợp lệ trong hai cột '{colX}' và '{colY}' để chạy K-Means.")
                
            if len(df_clean) < 2:
                raise ValueError("K-Means cần ít nhất 2 bản ghi số hợp lệ để phân cụm.")

            requested_k = max(2, min(10, request.paramK or 3))
            k = min(requested_k, len(df_clean))
            if k != requested_k:
                logs.append(f"[THAM SỐ] Số cụm K được giảm từ {requested_k} xuống {k} vì chỉ có {len(df_clean)} bản ghi hợp lệ.")
            kmeans = KMeans(n_clusters=k, random_state=42, n_init='auto')
            kmeans.fit(df_clean)
            labels = kmeans.labels_
            centroids = kmeans.cluster_centers_
            
            # Scaler đưa về phạm vi 0-10 của SVG
            x_min, x_max = float(df_clean[colX].min()), float(df_clean[colX].max())
            y_min, y_max = float(df_clean[colY].min()), float(df_clean[colY].max())
            x_range = (x_max - x_min) if (x_max - x_min) > 0 else 1.0
            y_range = (y_max - y_min) if (y_max - y_min) > 0 else 1.0
            
            def scale_x(v): return round((float(v) - x_min) / x_range * 10, 2)
            def scale_y(v): return round((float(v) - y_min) / y_range * 10, 2)
            
            sample_df = df_clean.copy()
            sample_df['cluster'] = labels
            if len(sample_df) > 500:
                sample_df = sample_df.sample(500, random_state=42)
                
            chart_points = []
            for idx, row in sample_df.iterrows():
                chart_points.append({
                    "id": int(idx),
                    "x": scale_x(row[colX]),
                    "y": scale_y(row[colY]),
                    "group": f"Cụm {int(row['cluster'])}",
                    "isSupport": False
                })
                
            for c_idx, cen in enumerate(centroids):
                chart_points.append({
                    "id": f"centroid-{c_idx}",
                    "x": scale_x(cen[0]),
                    "y": scale_y(cen[1]),
                    "group": f"Tâm cụm {c_idx}",
                    "isSupport": True
                })
                
            metrics = {
                "Số cụm (k)": k,
                "Độ biến dạng (Inertia)": f"{kmeans.inertia_:.1f}",
                "Bản ghi hợp lệ": len(df_clean)
            }
            logs.append(f"[MÔ HÌNH] Huấn luyện K-Means hoàn tất sau {kmeans.n_iter_} vòng lặp.")
            
            summary = f"### Kết quả phân cụm K-Means thực tế\n\nThuật toán K-Means đã phân nhóm thành công **{len(df_clean)}** bản ghi thành **{k}** cụm dựa trên thuộc tính **{colX}** và **{colY}**:\n\n"
            for c in range(k):
                cnt = np.sum(labels == c)
                summary += f"- **Cụm {c}**: Chứa **{cnt}** điểm dữ liệu ({round(cnt/len(df_clean)*100, 1)}%)\n"
                
        elif algorithm == "DBSCAN":
            from sklearn.cluster import DBSCAN
            colX = request.columnX if request.columnX in df.columns else df.columns[0]
            colY = request.columnY if request.columnY in df.columns else (df.columns[1] if len(df.columns) > 1 else df.columns[0])
            
            logs.append(f"[THAM SỐ] Chọn trục X: '{colX}', trục Y: '{colY}', Eps: {request.paramEps}, Min Samples: {request.paramMinSamples}")
            
            df_clean = df[[colX, colY]].dropna().copy()
            df_clean[colX] = pd.to_numeric(df_clean[colX], errors='coerce')
            df_clean[colY] = pd.to_numeric(df_clean[colY], errors='coerce')
            df_clean = df_clean.dropna()
            
            if df_clean.empty:
                raise ValueError(f"Không tìm thấy thuộc tính số hợp lệ trong hai cột '{colX}' và '{colY}' để chạy DBSCAN.")
                
            eps = max(0.1, min(10.0, request.paramEps or 0.5))
            min_samples = max(1, min(20, request.paramMinSamples or 5))
            
            dbscan = DBSCAN(eps=eps, min_samples=min_samples)
            dbscan.fit(df_clean)
            labels = dbscan.labels_
            
            x_min, x_max = float(df_clean[colX].min()), float(df_clean[colX].max())
            y_min, y_max = float(df_clean[colY].min()), float(df_clean[colY].max())
            x_range = (x_max - x_min) if (x_max - x_min) > 0 else 1.0
            y_range = (y_max - y_min) if (y_max - y_min) > 0 else 1.0
            def scale_x(v): return round((float(v) - x_min) / x_range * 10, 2)
            def scale_y(v): return round((float(v) - y_min) / y_range * 10, 2)
            
            sample_df = df_clean.copy()
            sample_df['cluster'] = labels
            if len(sample_df) > 500:
                sample_df = sample_df.sample(500, random_state=42)
                
            chart_points = []
            for idx, row in sample_df.iterrows():
                cluster_label = int(row['cluster'])
                chart_points.append({
                    "id": int(idx),
                    "x": scale_x(row[colX]),
                    "y": scale_y(row[colY]),
                    "group": "Nhiễu" if cluster_label == -1 else f"Cụm {cluster_label}",
                    "isSupport": cluster_label == -1
                })
                
            n_clusters = len(set(labels)) - (1 if -1 in labels else 0)
            n_noise = list(labels).count(-1)
            
            metrics = {
                "Số cụm phát hiện": n_clusters,
                "Số điểm nhiễu": n_noise,
                "Bản ghi hợp lệ": len(df_clean)
            }
            logs.append(f"[MÔ HÌNH] Huấn luyện DBSCAN hoàn tất. Phát hiện {n_clusters} cụm mật độ và {n_noise} điểm nhiễu.")
            
            summary = f"### Kết quả phân cụm mật độ DBSCAN\n\nThuật toán DBSCAN với tham số $Eps = {eps}$, $MinSamples = {min_samples}$ đã kết thúc phân tích:\n\n"
            summary += f"- **Số cụm tìm thấy**: **{n_clusters}** cụm mật độ tuần hoàn.\n"
            summary += f"- **Số điểm nhiễu (outliers)**: **{n_noise}** điểm chiếm {round(n_noise/len(df_clean)*100, 1)}% tổng số bản ghi.\n"
            
        elif algorithm == "Apriori":
            from mlxtend.frequent_patterns import apriori, association_rules
            min_support = max(0.01, min(0.9, request.paramSupport or 0.1))
            min_confidence = max(0.1, min(0.99, request.paramConfidence or 0.5))
            
            logs.append(f"[THAM SỐ] Apriori: Min Support: {min_support}, Min Confidence: {min_confidence}")
            
            binary_df = pd.DataFrame()
            for col in df.columns:
                unique_vals = set(df[col].dropna().unique())
                if unique_vals.issubset({0, 1, 0.0, 1.0, True, False}):
                    binary_df[col] = df[col].fillna(0).astype(bool)
                elif df[col].dtype == object or isinstance(df[col].dtype, pd.CategoricalDtype):
                    dummies = pd.get_dummies(df[col], prefix=col)
                    for d_col in dummies.columns:
                        binary_df[d_col] = dummies[d_col].astype(bool)
                        
            if binary_df.empty:
                raise ValueError("Không tìm thấy thuộc tính nhị phân hoặc phân loại để chạy Apriori.")
                
            frequent_itemsets = apriori(binary_df, min_support=min_support, use_colnames=True)
            
            if len(frequent_itemsets) > 500:
                frequent_itemsets = frequent_itemsets.sort_values(by="support", ascending=False).iloc[:500]
                logs.append("[WARNING] Số lượng tập phổ biến vượt quá 500, hệ thống tự động giới hạn lấy top 500.")
                
            if frequent_itemsets.empty:
                metrics = {"Tập phổ biến": 0, "Luật khai phá": 0}
                summary = "### Khai phá Luật kết hợp Apriori\n\nKhông tìm thấy tập phổ biến nào đạt mức độ hỗ trợ tối thiểu đã thiết lập."
                chart_points = []
            else:
                rules = association_rules(frequent_itemsets, metric="confidence", min_threshold=min_confidence)
                rules_list = []
                
                if not rules.empty:
                    rules = rules.sort_values(by="lift", ascending=False)
                    for idx, row in rules.iterrows():
                        rules_list.append({
                            "itemA": ", ".join(list(row['antecedents'])),
                            "itemB": ", ".join(list(row['consequents'])),
                            "support": round(float(row['support']) * 100, 1),
                            "confidence": round(float(row['confidence']) * 100, 1),
                            "lift": round(float(row['lift']), 2)
                        })
                        if len(rules_list) >= 8:
                            break
                            
                metrics = {
                    "Tập phổ biến": len(frequent_itemsets),
                    "Luật tìm thấy": len(rules),
                    "Số cột nhị phân": len(binary_df.columns)
                }
                logs.append(f"[MÔ HÌNH] Chạy Apriori hoàn tất. Tìm ra {len(frequent_itemsets)} tập phổ biến và {len(rules)} luật kết hợp.")
                
                summary = f"### Luật kết hợp Apriori ({len(rules_list)} luật hàng đầu)\n\n"
                if rules_list:
                    for i, r in enumerate(rules_list):
                        summary += f"{i+1}. **{{{r['itemA']}}} &rArr; {{{r['itemB']}}}** (Support: {r['support']}%, Confidence: {r['confidence']}%, Lift: {r['lift']})\n"
                else:
                    summary += "Không tìm thấy luật kết hợp nào thỏa mãn độ tin cậy đã chọn."
                    
                chart_points = rules_list
                
        elif algorithm == "Decision Tree":
            from sklearn.tree import DecisionTreeClassifier
            
            y_col = request.columnY if request.columnY in df.columns else df.columns[-1]
            x_cols = [c for c in df.columns if c != y_col]
            
            logs.append(f"[THAM SỐ] Cây quyết định. Trực quan hóa biến mục tiêu: '{y_col}'")
            
            if not x_cols:
                raise ValueError("Cây quyết định cần ít nhất 1 thuộc tính đầu vào ngoài cột mục tiêu.")

            X_df = df[x_cols].copy()
            y_series = df[y_col].copy()
            
            for col in X_df.columns:
                if X_df[col].dtype == object or isinstance(X_df[col].dtype, pd.CategoricalDtype):
                    X_df[col] = pd.factorize(X_df[col])[0]
                X_df[col] = pd.to_numeric(X_df[col], errors='coerce')
                X_df[col] = X_df[col].fillna(X_df[col].median() if not X_df[col].empty else 0)
                
            y_encoded, y_classes = pd.factorize(y_series)
            if len(y_classes) == 0:
                raise ValueError("Cột mục tiêu bị trống hoặc không thể phân lớp.")
                
            max_depth = max(2, min(15, request.paramMaxDepth or 5))
            clf = DecisionTreeClassifier(max_depth=max_depth, random_state=42)
            clf.fit(X_df, y_encoded)
            
            tree_ = clf.tree_
            feature_names = list(X_df.columns)
            chart_points = []
            
            if tree_.node_count > 0:
                root_feature = feature_names[tree_.feature[0]] if tree_.feature[0] != -2 else "Lá quyết định"
                root_threshold = round(tree_.threshold[0], 2)
                root_samples = tree_.n_node_samples[0]
                chart_points.append({
                    "name": f"{root_feature} <= {root_threshold}" if tree_.feature[0] != -2 else f"Dự báo: {y_classes[np.argmax(tree_.value[0])]}",
                    "value": 100,
                    "label": "Gốc (Tất cả mẫu)"
                })
                
                left_child = tree_.children_left[0]
                right_child = tree_.children_right[0]
                
                if left_child != -1:
                    left_feature = feature_names[tree_.feature[left_child]] if tree_.feature[left_child] != -2 else "Lá quyết định"
                    left_threshold = round(tree_.threshold[left_child], 2)
                    left_samples = tree_.n_node_samples[left_child]
                    left_pct = round(left_samples / root_samples * 100, 1)
                    chart_points.append({
                        "name": f"{left_feature} <= {left_threshold}" if tree_.feature[left_child] != -2 else f"Dự báo: {y_classes[np.argmax(tree_.value[left_child])]}",
                        "value": left_pct,
                        "label": "Rẽ trái"
                    })
                else:
                    chart_points.append({"name": "Nhánh trống", "value": 0, "label": "Rẽ trái"})
                    
                if right_child != -1:
                    right_feature = feature_names[tree_.feature[right_child]] if tree_.feature[right_child] != -2 else "Lá quyết định"
                    right_threshold = round(tree_.threshold[right_child], 2)
                    right_samples = tree_.n_node_samples[right_child]
                    right_pct = round(right_samples / root_samples * 100, 1)
                    chart_points.append({
                        "name": f"{right_feature} <= {right_threshold}" if tree_.feature[right_child] != -2 else f"Dự báo: {y_classes[np.argmax(tree_.value[right_child])]}",
                        "value": right_pct,
                        "label": "Rẽ phải"
                    })
                else:
                    chart_points.append({"name": "Nhánh trống", "value": 0, "label": "Rẽ phải"})
                    
                if left_child != -1 and tree_.children_left[left_child] != -1:
                    ll_child = tree_.children_left[left_child]
                    ll_samples = tree_.n_node_samples[ll_child]
                    chart_points.append({
                        "name": f"Dự báo: {y_classes[np.argmax(tree_.value[ll_child])]}",
                        "value": round(ll_samples / root_samples * 100, 1),
                        "label": "Cụm A"
                    })
                else:
                    lbl = f"Dự báo: {y_classes[np.argmax(tree_.value[left_child])]}" if left_child != -1 else "N/A"
                    chart_points.append({"name": lbl, "value": chart_points[1]["value"] if left_child != -1 else 0, "label": "Cụm A"})
                    
                if left_child != -1 and tree_.children_right[left_child] != -1:
                    lr_child = tree_.children_right[left_child]
                    lr_samples = tree_.n_node_samples[lr_child]
                    chart_points.append({
                        "name": f"Dự báo: {y_classes[np.argmax(tree_.value[lr_child])]}",
                        "value": round(lr_samples / root_samples * 100, 1),
                        "label": "Cụm B"
                    })
                else:
                    chart_points.append({"name": "Lá dự báo tĩnh", "value": 15.0, "label": "Cụm B"})
                    
            metrics = {
                "Tổng số nút": tree_.node_count,
                "Độ sâu tối đa": max_depth,
                "Độ chính xác tự thân": f"{clf.score(X_df, y_encoded)*100:.1f}%"
            }
            logs.append(f"[MÔ HÌNH] Huấn luyện Cây quyết định hoàn tất. Tổng số nút: {tree_.node_count}.")
            summary = f"### Kết quả phân loại Cây Quyết Định (Decision Tree)\n\nHệ thống đã huấn luyện thành công mô hình cây phân loại để dự báo biến **{y_col}**:\n\n- **Độ chính xác (Accuracy)**: {metrics['Độ chính xác tự thân']}\n- **Thuộc tính quan trọng nhất**: **{feature_names[np.argmax(clf.feature_importances_)]}** đóng vai trò phân tách chủ yếu tại node gốc."
            
        elif algorithm == "Linear Regression":
            from sklearn.linear_model import LinearRegression
            colX = request.columnX if request.columnX in df.columns else df.columns[0]
            colY = request.columnY if request.columnY in df.columns else (df.columns[1] if len(df.columns) > 1 else df.columns[0])
            
            logs.append(f"[THAM SỐ] Chạy Hồi quy tuyến tính. Biến độc lập X: '{colX}', Biến mục tiêu Y: '{colY}'")
            
            df_clean = df[[colX, colY]].dropna().copy()
            df_clean[colX] = pd.to_numeric(df_clean[colX], errors='coerce')
            df_clean[colY] = pd.to_numeric(df_clean[colY], errors='coerce')
            df_clean = df_clean.dropna()
            
            if df_clean.empty:
                raise ValueError(f"Không tìm thấy thuộc tính số hợp lệ trong hai cột '{colX}' và '{colY}' để chạy hồi quy tuyến tính.")
                
            X_reg = df_clean[[colX]].values
            y_reg = df_clean[colY].values
            
            model = LinearRegression()
            model.fit(X_reg, y_reg)
            
            coef = float(model.coef_[0])
            intercept = float(model.intercept_)
            r2 = float(model.score(X_reg, y_reg))
            
            x_min, x_max = float(df_clean[colX].min()), float(df_clean[colX].max())
            y_min, y_max = float(df_clean[colY].min()), float(df_clean[colY].max())
            x_range = (x_max - x_min) if (x_max - x_min) > 0 else 1.0
            y_range = (y_max - y_min) if (y_max - y_min) > 0 else 1.0
            def scale_x(v): return round((float(v) - x_min) / x_range * 10, 2)
            def scale_y(v): return round((float(v) - y_min) / y_range * 10, 2)
            
            sample_df = df_clean.copy()
            if len(sample_df) > 500:
                sample_df = sample_df.sample(500, random_state=42)
                
            chart_points = []
            for idx, row in sample_df.iterrows():
                chart_points.append({
                    "id": int(idx),
                    "x": scale_x(row[colX]),
                    "y": scale_y(row[colY]),
                    "group": "Điểm dữ liệu",
                    "isSupport": False
                })
                
            y_pred_min = x_min * coef + intercept
            y_pred_max = x_max * coef + intercept
            
            regression_line = {
                "x1": scale_x(x_min),
                "y1": scale_y(y_pred_min),
                "x2": scale_x(x_max),
                "y2": scale_y(y_pred_max)
            }
            
            metrics = {
                "Hệ số xác định R²": f"{r2:.3f}",
                "Hệ số góc (Slope)": f"{coef:.4f}",
                "Điểm chặn (Intercept)": f"{intercept:.2f}"
            }
            logs.append(f"[MÔ HÌNH] Huấn luyện Hồi quy hoàn tất. Phương trình: Y = {coef:.4f} * X + {intercept:.2f}")
            
            summary = f"### Kết quả hồi quy tuyến tính thực tế\n\nPhương trình hồi quy tuyến tính xác định mối liên hệ giữa **{colY}** (Y) và **{colX}** (X):\n\n"
            summary += f"- **Phương trình hồi quy**: $Y = {coef:.4f} \\times X + {intercept:.2f}$\n"
            summary += f"- **Hệ số xác định $R^2$**: **{r2:.4f}** (Cho biết mức độ giải thích của mô hình đối với biến động dữ liệu).\n"
            
            visualization_data = {
                "type": "regression",
                "chartData": {
                    "points": chart_points,
                    "line": regression_line
                }
            }
            
        else:
            raise ValueError(f"Thuật toán '{algorithm}' chưa được hệ thống hỗ trợ.")
            
        if not visualization_data:
            visualization_type = "rules" if algorithm == "Apriori" else ("tree" if algorithm == "Decision Tree" else "scatter")
            visualization_data = {
                "type": visualization_type,
                "chartData": chart_points
            }
            
        return {
            "summary": summary,
            "features": features,
            "instances": instances,
            "metrics": metrics,
            "logs": logs,
            "visualizationData": visualization_data
        }
        
    except Exception as model_err:
        logs.append(f"[LỖI THỰC THI] Gặp sự cố khi chạy mô hình: {str(model_err)}")
        raise HTTPException(status_code=400, detail=str(model_err))

@app.get("/api/documents")
async def list_documents(current_user: dict = Depends(get_current_user)):
    """
    Endpoint trả về danh sách các tệp đã tải lên trong thư mục data/
    """
    import os
    import math
    
    data_dir = "data"
    if not os.path.exists(data_dir):
        return {"documents": []}
        
    documents_list = []
    user_id = current_user.get("user_id", "default")
    user_prefix = f"{user_id}__"
    
    # Duyệt qua các file trong thư mục data/
    for idx, filename in enumerate(os.listdir(data_dir)):
        # Bỏ qua các file ẩn hoặc rác
        if filename.startswith(".") or filename.startswith("~$") or filename == "desktop.ini":
            continue
            
        # Chỉ hiển thị file của user hiện tại và file dùng chung (không có tiền tố __)
        is_user_file = filename.startswith(user_prefix)
        is_public_file = "__" not in filename
        
        if not (is_user_file or is_public_file):
            continue
            
        file_path = os.path.join(data_dir, filename)
        if not os.path.isfile(file_path):
            continue
            
        # Lấy tên hiển thị
        display_name = filename.replace(user_prefix, "") if is_user_file else filename
            
        # Lấy thông tin kích thước và ngày tạo
        size_bytes = os.path.getsize(file_path)
        mtime = os.path.getmtime(file_path)
        size_mb = size_bytes / (1024 * 1024)
        if size_mb < 0.1:
            size_str = f"{math.ceil(size_bytes / 1024)} KB"
        else:
            size_str = f"{size_mb:.1f} MB"
            
        # Phân loại định dạng
        ext = os.path.splitext(filename)[1].lower()
        doc_type = "pdf"
        if ext in [".csv", ".xlsx", ".json"]:
            doc_type = "dataset"
        elif ext in [".mp4", ".mov", ".avi"]:
            doc_type = "video"
            
        # Hình ảnh minh họa theo định dạng
        image = "https://images.unsplash.com/photo-1517842645767-c639042777db?auto=format&fit=crop&w=400&q=80" # Default PDF
        if doc_type == "dataset":
            image = "https://images.unsplash.com/photo-1551288049-bebda4e38f71?auto=format&fit=crop&w=400&q=80"
        elif doc_type == "video":
            image = "https://images.unsplash.com/photo-1526374965328-7f61d4dc18c5?auto=format&fit=crop&w=400&q=80"
            
        documents_list.append({
            "id": f"lib-file-{idx}",
            "type": doc_type,
            "title": display_name,
            "filename": filename, # Tên thật để dùng khi xóa
            "description": f"Tài liệu tự động nạp vào hệ thống Tri thức (RAG). Loại định dạng: {ext.upper()}",
            "size": size_str,
            "category": doc_type,
            "linkText": "Xem",
            "image": image,
            "rows": "Dữ liệu dạng dòng" if doc_type == "dataset" else None,
            "duration": None,
            "is_public": is_public_file,
            "mtime": mtime
        })

    # Sắp xếp: file của user (is_public=False) lên đầu, tiếp theo là file dùng chung (is_public=True),
    # trong từng nhóm sắp xếp theo thời gian mtime mới nhất lên đầu
    documents_list.sort(key=lambda x: (x["is_public"], -x["mtime"]))
    return {"documents": documents_list}

@app.delete("/api/documents/{filename}")
async def delete_document(filename: str, current_user: dict = Depends(get_current_user)):
    """
    Xóa tài liệu khỏi hệ thống: Xóa file vật lý và dọn dẹp bộ nhớ ChromaDB
    """
    import os
    import pickle
    
    user_id = current_user.get("user_id", "default")
    user_prefix = f"{user_id}__"
    filename = os.path.basename(filename.replace("\\", "/"))
    
    # Ngăn chặn xóa file public hoặc file của người khác
    if not filename.startswith(user_prefix):
        raise HTTPException(status_code=403, detail="You do not have permission to delete this file.")
    
    try:
        # Xóa file vật lý trong data/ bằng đường dẫn tuyệt đối đã kiểm tra.
        data_dir = os.path.abspath("data")
        file_path = os.path.abspath(os.path.join(data_dir, filename))
        if not (file_path == data_dir or file_path.startswith(data_dir + os.sep)):
            raise HTTPException(status_code=400, detail="Invalid file path.")

        physical_deleted = False
        if os.path.isfile(file_path):
            os.remove(file_path)
            physical_deleted = True
            print(f"✅ Đã xóa file vật lý trong data/: {file_path}")
        else:
            print(f"⚠️ Không tìm thấy file vật lý để xóa trong data/: {file_path}")
            
        # Dọn dẹp trong global documents (danh sách chunk trên RAM)
        global documents
        if documents is not None:
            # Lọc ra những chunk KHÔNG thuộc file này
            before_docs = len(documents)
            documents = [
                doc for doc in documents 
                if doc.metadata.get('source_file') != filename and
                   not str(doc.metadata.get('source', '')).endswith(filename)
            ]
            ram_chunks_deleted = before_docs - len(documents)
            
            # Cập nhật lại documents.pkl
            CHROMA_DIR = "chroma_db_new"
            os.makedirs(CHROMA_DIR, exist_ok=True)
            documents_path = os.path.join(CHROMA_DIR, "documents.pkl")
            try:
                with open(documents_path, 'wb') as f:
                    pickle.dump(documents, f)
            except Exception as e:
                print(f"❌ Error saving documents.pkl after deletion: {e}")
                
        # Dọn dẹp trong ChromaDB (Vector store)
        global vectordb
        if vectordb:
            try:
                collection = vectordb._collection
                # Tìm các id có source kết thúc bằng filename hoặc source_file = filename
                all_docs = collection.get()
                ids_to_delete = []
                for i, meta in enumerate(all_docs.get("metadatas", [])):
                    if meta and (meta.get("source_file") == filename or str(meta.get("source", "")).endswith(filename)):
                        ids_to_delete.append(all_docs["ids"][i])
                        
                if ids_to_delete:
                    collection.delete(ids=ids_to_delete)
                    if hasattr(vectordb, "persist"):
                        vectordb.persist()
                    print(f"✅ Đã xóa {len(ids_to_delete)} chunks thuộc file {filename} khỏi ChromaDB.")
            except Exception as e:
                print(f"❌ Error deleting from ChromaDB: {e}")
                
        return {
            "success": True,
            "message": f"Đã xóa thành công {filename}",
            "filename": filename,
            "physical_deleted": physical_deleted,
            "ram_chunks_deleted": locals().get("ram_chunks_deleted", 0),
            "vector_chunks_deleted": len(locals().get("ids_to_delete", [])),
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Lỗi khi xóa: {str(e)}")

@app.get("/api/system/statistics")
async def get_system_statistics():
    """
    Dashboard thống kê cho đồ án — Phần 10
    Trả về: số tài liệu, chunks, model, latency, citations, confidence.
    """
    import time as _time
    
    # Vectordb stats
    vdb_count = 0
    try:
        if vectordb:
            vdb_count = vectordb._collection.count()
    except Exception:
        pass
    
    doc_count = len(documents) if documents else 0
    
    # Unique source files
    source_files = set()
    if documents:
        for doc in documents[:500]:  # sample để nhanh
            src = doc.metadata.get('source_file') or doc.metadata.get('source', '')
            if src:
                import os
                source_files.add(os.path.basename(src))
    
    # Embedding model
    from config import (
        BM25_WEIGHT,
        EMBEDDING_MODEL_NAME,
        LLM_MODEL_NAME,
        LLM_TEMPERATURE,
        RERANK_MODEL,
        RERANK_THRESHOLD,
        RERANK_TOP_K,
        RETRIEVE_K,
        VECTOR_WEIGHT,
    )
    
    # Key manager status
    from reliability.api_key_manager import api_key_manager
    key_status = api_key_manager.get_status()
    
    # Recent session metrics
    total_sessions = len(sessions)
    active_sessions = len([s for s in sessions.values() if len(s["messages"]) > 0])
    total_messages = sum(len(s["messages"]) for s in sessions.values())
    
    return {
        "data_stats": {
            "total_documents": doc_count,
            "total_chunks": vdb_count,
            "unique_source_files": len(source_files),
            "source_files": sorted(list(source_files)),
        },
        "model_stats": {
            "embedding_model": EMBEDDING_MODEL_NAME,
            "llm_model": LLM_MODEL_NAME,
            "reranker_model": RERANK_MODEL,
            "retrieval_strategy": f"Hybrid (Vector {VECTOR_WEIGHT:.0%} + BM25 {BM25_WEIGHT:.0%}) -> CrossEncoder Rerank",
        },
        "session_stats": {
            "total_sessions": total_sessions,
            "active_sessions": active_sessions,
            "total_messages": total_messages,
        },
        "api_key_stats": key_status,
        "pipeline_config": {
            "retrieve_k_per_query": RETRIEVE_K,
            "rerank_top_k": RERANK_TOP_K,
            "rerank_threshold": RERANK_THRESHOLD,
            "llm_temperature": LLM_TEMPERATURE,
            "citation_verification": True,
            "confidence_scoring": True,
        },
        "system_status": {
            "rag_ready": loading_status["ready"],
            "timestamp": datetime.now().isoformat(),
        }
    }


@app.get("/api/system-stats")
async def get_stats(authorization: Optional[str] = Header(None)):
    """Lấy thống kê hệ thống và hoạt động học tập của người dùng hiện tại."""
    current_user = None
    if authorization:
        try:
            token = authorization.split(" ")[1] if " " in authorization else authorization
            payload = auth_manager.verify_token(token)
            if payload:
                current_user = payload
        except Exception:
            pass

    days_map = ["T2", "T3", "T4", "T5", "T6", "T7", "CN"]
    weeks_map = ["Tuần 1", "Tuần 2", "Tuần 3", "Tuần 4"]
    months_map = ["Th1", "Th2", "Th3", "Th4", "Th5", "Th6", "Th7", "Th8", "Th9", "Th10", "Th11", "Th12"]
    now = datetime.utcnow()
    week_start = (now - timedelta(days=now.weekday())).replace(hour=0, minute=0, second=0, microsecond=0)
    week_end = week_start + timedelta(days=7)
    month_start = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
    year_start = now.replace(month=1, day=1, hour=0, minute=0, second=0, microsecond=0)

    def normalize_ts(value):
        if isinstance(value, datetime):
            return value
        if isinstance(value, str):
            try:
                return datetime.fromisoformat(value.replace("Z", "+00:00")).replace(tzinfo=None)
            except Exception:
                return None
        return None

    activity_hours = {d: 0.0 for d in days_map}
    activity_month = {w: 0.0 for w in weeks_map}
    activity_year = {m: 0.0 for m in months_map}
    online_hours_week = {d: 0.0 for d in days_map}
    online_hours_month = {w: 0.0 for w in weeks_map}
    online_hours_year = {m: 0.0 for m in months_map}
    active_ops_week = {d: 0 for d in days_map}
    active_ops_month = {w: 0 for w in weeks_map}
    active_ops_year = {m: 0 for m in months_map}
    login_counts_week = {d: 0 for d in days_map}
    login_counts_month = {w: 0 for w in weeks_map}
    login_counts_year = {m: 0 for m in months_map}
    user_online_time = 0.0
    user_active_ops = 0
    login_count = 0
    real_total_messages = 0

    if current_user:
        email = current_user.get("email", "")
        user_id = current_user.get("user_id", email)
        user_msgs = []
        user_logs = []
        has_auth_chat_messages = False

        try:
            conversations = list(chat_history_manager.conversations_collection.find(
                {"user_id": user_id},
                {"_id": 1},
            ))
            conversation_ids = [str(c["_id"]) for c in conversations]
            if conversation_ids:
                user_msgs = list(chat_history_manager.messages_collection.find({
                    "conversation_id": {"$in": conversation_ids},
                    "role": "user",
                }))
                has_auth_chat_messages = len(user_msgs) > 0
            real_total_messages = chat_history_manager.messages_collection.count_documents({})
        except Exception as e:
            print("Lỗi khi lấy tin nhắn chat history:", e)
            if conv_history:
                try:
                    if conv_history.use_mongodb:
                        user_msgs = list(conv_history.conversations.find({"user_id": user_id}))
                        real_total_messages = conv_history.conversations.count_documents({})
                    else:
                        user_msgs = conv_history.local_history
                        real_total_messages = len(user_msgs)
                except Exception as history_err:
                    print("Lỗi khi lấy tin nhắn user:", history_err)

        if auth_manager.use_mongo:
            try:
                user_logs = list(auth_manager.logs_collection.find({"user_id": user_id}))
            except Exception as e:
                print("Lỗi khi lấy logs user:", e)

        for msg in user_msgs:
            ts = normalize_ts(msg.get("created_at") or msg.get("timestamp"))
            if not ts:
                continue
            day_str = days_map[ts.weekday()]
            week_idx = min(3, (ts.day - 1) // 7)
            week_str = weeks_map[week_idx]
            month_str = months_map[ts.month - 1]
            if week_start <= ts < week_end:
                online_hours_week[day_str] = round(online_hours_week[day_str] + 0.25, 2)
                active_ops_week[day_str] += 1
            if month_start <= ts:
                online_hours_month[week_str] = round(online_hours_month[week_str] + 0.25, 2)
                active_ops_month[week_str] += 1
            if year_start <= ts:
                online_hours_year[month_str] = round(online_hours_year[month_str] + 0.25, 2)
                active_ops_year[month_str] += 1
            activity_hours[day_str] = round(activity_hours[day_str] + 0.25, 2)
            activity_month[week_str] = round(activity_month[week_str] + 0.25, 2)
            activity_year[month_str] = round(activity_year[month_str] + 0.25, 2)

        for log in user_logs:
            ts = normalize_ts(log.get("timestamp"))
            if not ts:
                continue
            action_type = log.get("action_type", "chat")
            day_str = days_map[ts.weekday()]
            week_idx = min(3, (ts.day - 1) // 7)
            week_str = weeks_map[week_idx]
            month_str = months_map[ts.month - 1]

            if week_start <= ts < week_end:
                if action_type == "login":
                    login_counts_week[day_str] += 1
                elif action_type != "chat" or not has_auth_chat_messages:
                    active_ops_week[day_str] += 1
                    online_hours_week[day_str] = round(online_hours_week[day_str] + 0.25, 2)

            if month_start <= ts:
                if action_type == "login":
                    login_counts_month[week_str] += 1
                elif action_type != "chat" or not has_auth_chat_messages:
                    active_ops_month[week_str] += 1
                    online_hours_month[week_str] = round(online_hours_month[week_str] + 0.25, 2)

            if year_start <= ts:
                if action_type == "login":
                    login_counts_year[month_str] += 1
                elif action_type != "chat" or not has_auth_chat_messages:
                    active_ops_year[month_str] += 1
                    online_hours_year[month_str] = round(online_hours_year[month_str] + 0.25, 2)

            if action_type != "login" and (action_type != "chat" or not has_auth_chat_messages):
                activity_hours[day_str] = round(activity_hours[day_str] + 0.25, 2)
                activity_month[week_str] = round(activity_month[week_str] + 0.25, 2)
                activity_year[month_str] = round(activity_year[month_str] + 0.25, 2)

        user_active_ops = len(user_msgs) + len([l for l in user_logs if l.get("action_type") not in ("login", "chat")])

        user_doc = None
        if auth_manager.use_mongo:
            try:
                user_doc = auth_manager.users_collection.find_one({"email": email})
                if user_doc:
                    login_count = int(user_doc.get("login_count", 0) or 0)
            except Exception:
                pass
        else:
            try:
                user_doc = auth_manager.get_user_by_id(user_id)
                if user_doc:
                    login_count = int(user_doc.get("login_count", 0) or 0)
            except Exception:
                pass

        logged_login_total = sum(login_counts_year.values())
        login_count = max(login_count, logged_login_total, sum(login_counts_week.values()))

        # Older accounts may have login_count/last_login but no interaction log.
        # Put that known total into the last-login bucket so the chart does not stay blank.
        if login_count > 0 and logged_login_total == 0:
            last_login = normalize_ts((user_doc or {}).get("last_login")) or now
            day_str = days_map[last_login.weekday()]
            week_idx = min(3, (last_login.day - 1) // 7)
            week_str = weeks_map[week_idx]
            month_str = months_map[last_login.month - 1]
            if year_start <= last_login:
                login_counts_year[month_str] = login_count
            if month_start <= last_login:
                login_counts_month[week_str] = login_count
            if week_start <= last_login < week_end:
                login_counts_week[day_str] = login_count
        user_online_time = round(sum(online_hours_week.values()), 1)
    else:
        online_hours_week = {"T2": 0.5, "T3": 0.0, "T4": 1.2, "T5": 0.0, "T6": 0.8, "T7": 0.0, "CN": 0.0}
        online_hours_month = {"Tuần 1": 2.4, "Tuần 2": 1.8, "Tuần 3": 4.2, "Tuần 4": 3.1}
        online_hours_year = {"Th1": 12.0, "Th2": 10.5, "Th3": 14.2, "Th4": 9.8, "Th5": 16.0, "Th6": 11.5, "Th7": 0.0, "Th8": 0.0, "Th9": 0.0, "Th10": 0.0, "Th11": 0.0, "Th12": 0.0}
        active_ops_week = {"T2": 2, "T3": 0, "T4": 5, "T5": 0, "T6": 3, "T7": 0, "CN": 0}
        active_ops_month = {"Tuần 1": 10, "Tuần 2": 8, "Tuần 3": 16, "Tuần 4": 12}
        active_ops_year = {"Th1": 42, "Th2": 38, "Th3": 51, "Th4": 36, "Th5": 58, "Th6": 44, "Th7": 0, "Th8": 0, "Th9": 0, "Th10": 0, "Th11": 0, "Th12": 0}
        login_counts_week = {"T2": 1, "T3": 0, "T4": 0, "T5": 0, "T6": 0, "T7": 0, "CN": 0}
        login_counts_month = {"Tuần 1": 2, "Tuần 2": 1, "Tuần 3": 3, "Tuần 4": 1}
        login_counts_year = {"Th1": 6, "Th2": 5, "Th3": 8, "Th4": 4, "Th5": 7, "Th6": 6, "Th7": 0, "Th8": 0, "Th9": 0, "Th10": 0, "Th11": 0, "Th12": 0}
        user_online_time = 2.5
        user_active_ops = 10
        login_count = 1
        real_total_messages = 450
        activity_hours = {"T2": 2.4, "T3": 1.8, "T4": 4.2, "T5": 3.1, "T6": 2.7, "T7": 5.8, "CN": 1.9}
        activity_month = {"Tuần 1": 12.0, "Tuần 2": 18.0, "Tuần 3": 9.0, "Tuần 4": 15.0}
        activity_year = {"Th1": 45.0, "Th2": 52.0, "Th3": 38.0, "Th4": 61.0, "Th5": 47.0, "Th6": 55.0}

    docs_count = len(documents) if documents else 0
    calculated_percent = min(100, int((docs_count * 10) + (real_total_messages * 1.5)))

    return {
        "total_sessions": len(sessions),
        "active_sessions": len([s for s in sessions.values() if len(s.get("messages", [])) > 0]),
        "total_messages": real_total_messages or sum(len(s.get("messages", [])) for s in sessions.values()),
        "vectordb_count": vectordb._collection.count() if vectordb and hasattr(vectordb, '_collection') else 0,
        "documents_count": docs_count,
        "percent": calculated_percent,
        "activityDataWeek": [{"day": d, "hours": round(activity_hours[d], 1)} for d in days_map],
        "activityDataMonth": [{"day": w, "hours": round(activity_month[w], 1)} for w in weeks_map],
        "activityDataYear": [{"day": m, "hours": round(activity_year[m], 1)} for m in months_map],
        "user_online_time": user_online_time,
        "user_active_ops": user_active_ops,
        "user_login_count": login_count,
        "online_hours_week": [{"day": d, "val": round(online_hours_week[d], 1)} for d in days_map],
        "online_hours_month": [{"day": w, "val": round(online_hours_month[w], 1)} for w in weeks_map],
        "online_hours_year": [{"day": m, "val": round(online_hours_year[m], 1)} for m in months_map],
        "active_ops_week": [{"day": d, "val": active_ops_week[d]} for d in days_map],
        "active_ops_month": [{"day": w, "val": active_ops_month[w]} for w in weeks_map],
        "active_ops_year": [{"day": m, "val": active_ops_year[m]} for m in months_map],
        "login_counts_week": [{"day": d, "val": login_counts_week[d]} for d in days_map],
        "login_counts_month": [{"day": w, "val": login_counts_month[w]} for w in weeks_map],
        "login_counts_year": [{"day": m, "val": login_counts_year[m]} for m in months_map],
        "week_start": week_start.date().isoformat(),
        "week_end": (week_end - timedelta(days=1)).date().isoformat(),
        "timestamp": datetime.now().isoformat(),
    }
@app.post("/api/reset-offline")
async def reset_offline_mode():
    """Reset IS_OFFLINE_MODE và reload API keys từ .env (không cần restart backend)"""
    import rag as rag_module
    from dotenv import load_dotenv
    from reliability.api_key_manager import init_api_keys, api_key_manager

    # Force reload .env vào os.environ
    load_dotenv(override=True)

    # Xóa GOOGLE_API_KEY nếu không có trong .env (tránh override langchain)
    import os
    if not os.path.exists(".env") or "GOOGLE_API_KEY" not in open(".env").read():
        os.environ.pop("GOOGLE_API_KEY", None)

    # Reset healthy status của tất cả keys cũ, sau đó reload
    for k in api_key_manager.keys:
        k.is_healthy = True
        k.failures = 0
        k.cooldown_until = None
        k.requests_today = 0
        k.requests_this_minute = 0

    init_api_keys()
    rag_module.IS_OFFLINE_MODE = False

    available = api_key_manager.get_available_key()
    return {
        "success": True,
        "keys_loaded": len(api_key_manager.keys),
        "key_available": available.name if available else None,
        "google_api_key_present": bool(os.getenv("GOOGLE_API_KEY")),
        "message": "Đã reset offline mode và reload API keys thành công."
    }

# ============================================================================
# RUN SERVER
# ============================================================================
@app.get("/api/user/weak-topics")
async def get_weak_topics(current_user: dict = Depends(get_current_user)):
    """Trả về danh sách các chủ đề điểm yếu của user"""
    user_id = current_user.get("user_id", "default")
    if user_id == "default":
        return {"weak_topics": []}
    
    import asyncio
    weak_topics = await asyncio.to_thread(
        auth_manager.get_weak_topics, user_id, 14
    )
    return {"weak_topics": weak_topics}

@app.get("/api/user/recent-lessons")
async def get_recent_lessons(current_user: dict = Depends(get_current_user), limit: int = 4):
    """Return recent completed quizzes from real user data."""
    user_id = current_user.get("user_id", "default")
    if user_id == "default":
        return {"lessons": []}

    limit = max(1, min(int(limit or 4), 12))

    def normalize_quiz_row(row: Dict[str, Any]) -> Dict[str, Any]:
        score = row.get("score") or {}
        total_score = score.get("total_score", row.get("correct", 0))
        max_score = score.get("max_score", row.get("total_questions", row.get("answered_questions", 0)))
        percentage = score.get("percentage")
        if percentage is None:
            percentage = (float(total_score or 0) / max(1, float(max_score or 0))) * 100

        created_at = row.get("created_at") or row.get("timestamp") or row.get("updated_at")
        created_at_value = created_at.isoformat() if hasattr(created_at, "isoformat") else str(created_at or "")
        topic = str(row.get("topic") or "Trắc nghiệm").strip() or "Trắc nghiệm"
        answered = int(row.get("answered_questions") or max_score or 0)
        total = int(row.get("total_questions") or max_score or answered or 0)

        return {
            "id": str(row.get("quiz_id") or row.get("id") or created_at_value or topic),
            "title": topic,
            "subtitle": "Trắc nghiệm đã hoàn thành",
            "topic": topic,
            "score": round(float(total_score or 0), 2),
            "max_score": round(float(max_score or total or 0), 2),
            "percentage": round(float(percentage or 0), 1),
            "grade": score.get("grade", ""),
            "answered_questions": answered,
            "total_questions": total,
            "created_at": created_at_value,
        }

    lessons: List[Dict[str, Any]] = []
    if auth_manager.use_mongo:
        rows = list(
            auth_manager.db.quiz_results.find({"user_id": user_id}, {"_id": 0})
            .sort("created_at", -1)
            .limit(limit)
        )
        lessons = [normalize_quiz_row(row) for row in rows]
    else:
        try:
            from learning_tracker import get_tracker
            data = get_tracker()._load_user_data(user_id)
            rows = sorted(data.get("quiz_attempts", []), key=lambda item: item.get("timestamp", ""), reverse=True)
            lessons = [normalize_quiz_row(row) for row in rows[:limit]]
        except Exception as exc:
            print(f"⚠️ Could not load recent lessons fallback: {exc}")

    return {"lessons": lessons}

if __name__ == "__main__":
    import uvicorn
    
    print("🚀 Starting RAG System API Server...")
    print("📖 API Documentation: http://localhost:8000/docs")
    print("🔍 Health Check: http://localhost:8000/health")
    
    uvicorn.run(
        "backend_api:app",
        host="0.0.0.0",
        port=8000,
        reload=False,  # Tắt reload để tăng tốc startup và giảm overhead
        log_level="info"
    )

