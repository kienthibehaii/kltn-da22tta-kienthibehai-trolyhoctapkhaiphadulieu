# BÁO CÁO ĐÁNH GIÁ HỆ THỐNG - MinerAI RAG System

**Ngày đánh giá:** 04/06/2026  
**Người thực hiện:** Kiên Thị Bé Hai - MSSV: 110122218  
**Trường:** Đại học Trà Vinh

---

## 📋 MỤC LỤC

1. [Tổng quan hệ thống](#1-tổng-quan-hệ-thống)
2. [Kiến trúc hệ thống](#2-kiến-trúc-hệ-thống)
3. [Phân lớp chức năng](#3-phân-lớp-chức-năng)
4. [Quy trình hoạt động](#4-quy-trình-hoạt-động)
5. [Công nghệ sử dụng](#5-công-nghệ-sử-dụng)
6. [Đánh giá điểm mạnh](#6-đánh-giá-điểm-mạnh)
7. [Phát hiện điểm yếu](#7-phát-hiện-điểm-yếu)
8. [Khuyến nghị cải tiến](#8-khuyến-nghị-cải-tiến)

---

## 1. TỔNG QUAN HỆ THỐNG

### 1.1. Thông tin dự án
- **Tên hệ thống:** MinerAI - Hệ thống Trợ lý Học tập Khai phá Dữ liệu
- **Loại hệ thống:** Full-Stack RAG (Retrieval-Augmented Generation) System
- **Mục đích:** Hỗ trợ sinh viên học tập môn Khai phá Dữ liệu thông qua AI
- **Trạng thái:** ✅ Hoàn thành & Sẵn sàng sử dụng

### 1.2. Phạm vi chức năng chính
```
┌─────────────────────────────────────────────┐
│         MinerAI RAG System                  │
├─────────────────────────────────────────────┤
│ ✓ Hỏi đáp thông minh (RAG-powered Q&A)    │
│ ✓ Tóm tắt tài liệu (Document Summarization)│
│ ✓ Hệ thống Quiz tương tác (Interactive Quiz)│
│ ✓ So sánh LLM vs RAG (Comparison Mode)     │
│ ✓ Multi-Document QA (Cross-document)       │
│ ✓ Educational Engine (AI Tutor 7-step)     │
│ ✓ Xác thực người dùng (JWT Authentication) │
│ ✓ Lưu lịch sử hội thoại (Chat History)     │
│ ✓ Metrics & Analytics (Real-time)          │
└─────────────────────────────────────────────┘
```

### 1.3. Kiến trúc tổng thể
- **Frontend:** React 19 + TypeScript + Vite + TailwindCSS
- **Backend:** Python FastAPI + Uvicorn (ASGI)
- **AI/ML:** Google Gemini 2.5 Flash + LangChain
- **Vector Database:** ChromaDB với 5,984 chunks
- **Embeddings:** HuggingFace (sentence-transformers/all-MiniLM-L6-v2)
- **Search:** Hybrid (Vector Search + BM25)
- **Database:** MongoDB (optional) + In-memory sessions

---

## 2. KIẾN TRÚC HỆ THỐNG

### 2.1. Kiến trúc tổng quan (Layered Architecture)

```
┌─────────────────────────────────────────────────────────────┐
│                    PRESENTATION LAYER                        │
│  ┌────────────────────────────────────────────────────────┐ │
│  │  Frontend (React 19 + TypeScript + Vite)              │ │
│  │  - Giao diện người dùng (7 tabs)                      │ │
│  │  - Components: Sidebar, Header, MentorTab, QuizTab... │ │
│  │  - Real-time rendering & State management             │ │
│  └────────────────────────────────────────────────────────┘ │
└─────────────────────────────────────────────────────────────┘
                              ↕ HTTP/REST API
┌─────────────────────────────────────────────────────────────┐
│                     APPLICATION LAYER                        │
│  ┌────────────────────────────────────────────────────────┐ │
│  │  Backend API (FastAPI + Uvicorn)                      │ │
│  │  - RESTful API endpoints                              │ │
│  │  - Request validation (Pydantic models)               │ │
│  │  - CORS middleware                                    │ │
│  │  - JWT Authentication                                 │ │
│  │  - Session management                                 │ │
│  └────────────────────────────────────────────────────────┘ │
└─────────────────────────────────────────────────────────────┘
                              ↕
┌─────────────────────────────────────────────────────────────┐
│                      BUSINESS LOGIC LAYER                    │
│  ┌────────────────┬──────────────┬────────────────────────┐ │
│  │ RAG Pipeline   │ Quiz System  │ Educational Engine     │ │
│  │ - Retrieval    │ - Generator  │ - 7-step teaching      │ │
│  │ - Reranking    │ - Evaluator  │ - Adaptive learning    │ │
│  │ - Generation   │ - Scoring    │ - Progress tracking    │ │
│  └────────────────┴──────────────┴────────────────────────┘ │
│  ┌──────────────────────────────────────────────────────