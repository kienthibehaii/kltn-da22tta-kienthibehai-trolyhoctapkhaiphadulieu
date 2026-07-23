# 🎓 Hệ thống Trợ lý Học tập Khai phá Dữ liệu

> **Full Stack RAG System** với Backend Python (FastAPI) và Frontend React

[![Python](https://img.shields.io/badge/Python-3.10+-blue.svg)](https://www.python.org/)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.104+-green.svg)](https://fastapi.tiangolo.com/)
[![React](https://img.shields.io/badge/React-18.2-blue.svg)](https://react.dev/)
[![Vite](https://img.shields.io/badge/Vite-5.0-purple.svg)](https://vitejs.dev/)

---

## 📋 Giới thiệu

Hệ thống sử dụng công nghệ **RAG (Retrieval-Augmented Generation)** kết hợp với **Gemini API** để hỗ trợ học tập môn Khai phá Dữ liệu.

### ✨ Tính năng chính:

- 💬 **Hỏi đáp thông minh** với RAG + Context-aware
- 📝 **Tóm tắt tài liệu** theo chủ đề
- ❓ **Quiz ôn tập** tự động (API ready)
- ⚖️ **So sánh** LLM vs RAG (API ready)
- 📊 **Thống kê** hệ thống real-time
- 🔄 **Dịch tự động** Việt ↔ Anh
- 📚 **Citations** chi tiết với relevance scores
- 🔀 **Hybrid Search** (Vector + BM25)
- 🎯 **Reranking** với Cross-encoder

---

## 🚀 Quick Start

### 1. Cài đặt

```bash
# Clone repository
git clone [your-repo-url]
cd [project-folder]

# Install backend dependencies
pip install -r requirements.txt

# Install frontend dependencies
cd frontend
npm install
cd ..
```

### 2. Cấu hình

Tạo file `.env`:
```env
GOOGLE_API_KEY=your_gemini_api_key_here
MONGODB_URI=your_mongodb_uri_here  # Optional
```

### 3. Chạy ứng dụng

```bash
# Cách 1: Tự động (Khuyến nghị)
START_FULLSTACK.bat

# Cách 2: Thủ công
# Terminal 1
python backend_api.py

# Terminal 2
cd frontend
npm run dev
```

### 4. Truy cập

- **Frontend**: http://localhost:3000
- **Backend API**: http://localhost:8000
- **API Docs**: http://localhost:8000/docs

---

## 🏗️ Kiến trúc

```
┌─────────────────────────────────────────┐
│         Frontend (React + Vite)         │
│         http://localhost:3000           │
└─────────────────┬───────────────────────┘
                  │ REST API
                  │ (Vite Proxy)
┌─────────────────▼───────────────────────┐
│       Backend (FastAPI + Uvicorn)       │
│         http://localhost:8000           │
├─────────────────────────────────────────┤
│  ┌──────────────────────────────────┐  │
│  │        RAG Pipeline              │  │
│  │  ┌────────┐  ┌────────┐         │  │
│  │  │Vector  │  │ BM25   │         │  │
│  │  │Search  │  │Search  │         │  │
│  │  └───┬────┘  └───┬────┘         │  │
│  │      └────┬──────┘               │  │
│  │           │ Hybrid               │  │
│  │      ┌────▼────┐                 │  │
│  │      │Reranking│                 │  │
│  │      └────┬────┘                 │  │
│  │           │                      │  │
│  │      ┌────▼────┐                 │  │
│  │      │ Gemini  │                 │  │
│  │      │  API    │                 │  │
│  │      └─────────┘                 │  │
│  └──────────────────────────────────┘  │
└─────────────────────────────────────────┘
```

---

## 📁 Cấu trúc dự án

```
.
├── backend_api.py              # Backend FastAPI
├── rag.py                      # RAG pipeline
├── embed_store.py              # Vector store
├── requirements.txt            # Python dependencies
│
├── frontend/                   # Frontend React
│   ├── src/
│   │   ├── components/        # UI components
│   │   ├── pages/            # Page components
│   │   ├── services/         # API client
│   │   └── App.jsx           # Main app
│   ├── package.json          # Node dependencies
│   └── vite.config.js        # Vite config
│
├── chroma_db/                  # Vector database
├── data/                       # Source documents
│
├── START_FULLSTACK.bat        # Start both
├── START_BACKEND_API.bat      # Start backend
├── START_FRONTEND.bat         # Start frontend
├── test_connection.py         # Test backend
│
└── README.md                   # This file
```

---

## 🎯 Tính năng chi tiết

### 1. 💬 Hỏi đáp (Chat)

- Real-time messaging
- Context-aware (nhớ lịch sử)
- Auto translation (Việt ↔ Anh)
- Citations với relevance scores
- Response time tracking
- Markdown rendering

**Example:**
```
User: "Clustering là gì?"
Bot: [Câu trả lời chi tiết với 3 citations]
     📚 Nguồn 1: chapter7.pdf - Trang 411 (92% liên quan)
     📚 Nguồn 2: slides.pptx - Slide 15 (85% liên quan)
     📚 Nguồn 3: textbook.pdf - Trang 203 (78% liên quan)
```

### 2. 📝 Tóm tắt (Summary)

- Tóm tắt theo chủ đề
- Tóm tắt tổng quan
- Citations từ tài liệu
- Markdown formatting

### 3. 📊 Thống kê (Stats)

- Total sessions
- Active sessions
- Total messages
- VectorDB count (5,448 vectors)
- Documents count (1,193 docs)
- Real-time refresh

### 4. ❓ Quiz (API Ready)

- Auto-generate quiz
- Multiple choice & short answer
- Auto-evaluation
- Score calculation
- Feedback & explanations

### 5. ⚖️ Comparison (API Ready)

- LLM vs RAG comparison
- Performance metrics
- Winner determination

---

## 🔧 Công nghệ sử dụng

### Backend:
- **Framework**: FastAPI 0.104+
- **Server**: Uvicorn
- **LLM**: Google Gemini 2.5 Flash
- **Vector DB**: ChromaDB
- **Embeddings**: HuggingFace (all-MiniLM-L6-v2)
- **Search**: Hybrid (Vector + BM25)
- **Reranking**: Cross-encoder
- **Database**: MongoDB (optional)

### Frontend:
- **Framework**: React 18
- **Build Tool**: Vite 5
- **Routing**: React Router 6
- **HTTP Client**: Axios
- **Markdown**: React Markdown
- **Icons**: Lucide React

---

## 📊 Performance

### Backend:
- **Startup**: ~15s (load vector DB)
- **Response Time**: 
  - Question: 30-60s
  - Summary: 30-45s
  - Stats: < 1s
- **Memory**: ~500MB

### Frontend:
- **Initial Load**: < 2s
- **Bundle Size**: ~200KB (gzipped)
- **Page Transition**: < 100ms

---

## 🧪 Testing

### Test Backend:
```bash
# Quick test
python test_connection.py

# Full test
python test_backend_quick.py
```

### Test Frontend:
```bash
# Open browser
http://localhost:3000

# Check DevTools (F12)
# - No console errors
# - Network requests successful
```

---

## 📚 Documentation

### Guides:
- `BACKEND_API_GUIDE.md` - Backend API documentation (60+ pages)
- `BACKEND_README.md` - Backend quick start
- `frontend/README.md` - Frontend guide
- `FIX_CONNECTION_GUIDE.md` - Fix connection issues
- `USER_GUIDE.md` - User manual (attempted)

### Reports:
- `BACKEND_COMPLETION_REPORT.md` - Backend completion
- `FRONTEND_COMPLETION.md` - Frontend completion
- `PROJECT_FINAL_SUMMARY.md` - Project summary

---

## 🐛 Troubleshooting

### Backend không chạy:
```bash
# Check port 8000
netstat -ano | findstr :8000

# Kill if needed
taskkill /F /PID <PID>

# Start backend
python backend_api.py
```

### Frontend không kết nối:
```bash
# Test backend first
python test_connection.py

# Restart frontend
cd frontend
npm run dev
```

### CORS errors:
- ✅ Đã fix: Sử dụng Vite proxy
- ✅ Backend CORS enabled
- ✅ Relative URLs trong API client

---

## 🚀 Deployment

### Backend (Docker):
```dockerfile
FROM python:3.10-slim
WORKDIR /app
COPY requirements.txt .
RUN pip install -r requirements.txt
COPY . .
EXPOSE 8000
CMD ["uvicorn", "backend_api:app", "--host", "0.0.0.0"]
```

### Frontend:
```bash
# Build
cd frontend
npm run build

# Deploy to Vercel/Netlify/etc
```

---

## 📝 TODO

### High Priority:
- [ ] Complete QuizPage frontend
- [ ] Complete ComparisonPage frontend
- [ ] Add authentication (JWT)
- [ ] Add rate limiting

### Medium Priority:
- [ ] Dark mode
- [ ] Export chat history
- [ ] Voice input
- [ ] File upload

### Low Priority:
- [ ] PWA support
- [ ] i18n
- [ ] Analytics

---

## 🤝 Contributing

1. Fork the repository
2. Create feature branch
3. Commit changes
4. Push to branch
5. Open Pull Request

---

## 📄 License

This project is for educational purposes.

---

## 👨‍🎓 Tác giả

**Kiên Thị Bé Hai**  
MSSV: 110122218  
Trường: Đại học Trà Vinh  
Năm: 2026

---

## 🙏 Acknowledgments

- Google Gemini API
- LangChain
- FastAPI
- React
- Vite

---

## 📞 Liên hệ

- Email: [your-email]
- GitHub: [your-github]
- LinkedIn: [your-linkedin]

---

**⭐ Nếu project hữu ích, hãy cho một star! ⭐**

---

**Status**: ✅ **HOÀN THÀNH & SẴN SÀNG SỬ DỤNG**

**Last Updated**: 21/05/2026
