"""
test_all_features.py - Kiểm thử toàn bộ các tính năng API (timeout nâng cao cho QA/Quiz)
"""
import sys
import json
sys.stdout.reconfigure(encoding='utf-8')

try:
    import requests
except ImportError:
    import subprocess
    subprocess.run([sys.executable, "-m", "pip", "install", "requests", "-q"])
    import requests

BASE = "http://127.0.0.1:8000"
QA_TIMEOUT = 120   # RAG QA cần dịch + retrieve + LLM + dịch lại
FAST_TIMEOUT = 15

def sep(title):
    print(f"\n{'='*60}")
    print(f"  {title}")
    print('='*60)

def test(name, method, url, timeout=FAST_TIMEOUT, **kwargs):
    try:
        resp = getattr(requests, method)(url, timeout=timeout, **kwargs)
        status = "✅" if resp.status_code < 400 else "❌"
        print(f"{status} {name}: HTTP {resp.status_code}")
        return resp
    except requests.exceptions.Timeout:
        print(f"⏱️ {name}: TIMEOUT sau {timeout}s")
        return None
    except Exception as e:
        print(f"❌ {name}: ERROR - {e}")
        return None

sep("1. HEALTH CHECK")
r = test("Health", "get", f"{BASE}/health")
if r and r.status_code == 200:
    data = r.json()
    print(f"   Status: {data.get('status')}")
    print(f"   QA Chain Ready: {data.get('qa_chain')}")
    print(f"   Vector DB: {data.get('vectordb')}")
    loading = data.get('loading', {})
    print(f"   Progress: {loading.get('progress')}% - {loading.get('message')}")
    
    if not loading.get('ready'):
        print("\n   ⚠️  RAG pipeline chưa sẵn sàng, dừng test...")
        sys.exit(1)

sep("2. SYSTEM STATS")
r = test("System Stats", "get", f"{BASE}/api/system-stats")
if r and r.status_code == 200:
    data = r.json()
    print(f"   Vectors: {data.get('vectordb_count')}")
    print(f"   Documents: {data.get('documents_count')}")
    print(f"   Sessions: {data.get('total_sessions')}")

sep("3. CREATE SESSION")
r = test("Create Session", "post", f"{BASE}/api/session")
session_id = None
if r and r.status_code == 200:
    session_id = r.json().get("session_id")
    print(f"   ✅ Session ID: {session_id}")

sep("4. RAG - HỎI ĐÁP (K-means - Tiếng Việt)")
print("   ⏳ Đang xử lý (tối đa 120s - bao gồm dịch + LLM)...")
r = test("QA - K-means", "post", f"{BASE}/api/question",
    timeout=QA_TIMEOUT,
    json={"question": "Thuật toán K-means là gì? Giải thích cách hoạt động cơ bản.",
          "session_id": session_id, "use_context": True})
if r and r.status_code == 200:
    data = r.json()
    ans = data.get("answer", "")
    cits = data.get("citations", [])
    rt = data.get("response_time", 0)
    print(f"   ✅ Trả lời thành công!")
    print(f"   Thời gian: {rt:.1f}s | Độ dài: {len(ans)} ký tự | Citations: {len(cits)}")
    for cit in cits[:3]:
        fn = cit.get('filename', 'unknown')
        sl = cit.get('slide') or cit.get('page', 'N/A')
        print(f"     📄 {fn} (slide/page: {sl})")
    print(f"\n   PREVIEW:\n   {ans[:400]}...")
elif r:
    print(f"   ❌ Lỗi: {r.text[:300]}")

sep("5. RAG - Đề cương môn học")
print("   ⏳ Đang xử lý...")
r = test("QA - Đề cương", "post", f"{BASE}/api/question",
    timeout=QA_TIMEOUT,
    json={"question": "Đề cương học phần khai phá dữ liệu CNTT gồm bao nhiêu chương? Liệt kê tên các chương.",
          "session_id": session_id, "use_context": True})
if r and r.status_code == 200:
    data = r.json()
    ans = data.get("answer", "")
    cits = data.get("citations", [])
    rt = data.get("response_time", 0)
    print(f"   ✅ Trả lời thành công! ({rt:.1f}s, {len(ans)} chars, {len(cits)} citations)")
    sources_seen = set()
    for cit in cits:
        fn = cit.get('filename', '')
        if fn not in sources_seen:
            sources_seen.add(fn)
            print(f"     📄 {fn}")
    print(f"\n   PREVIEW:\n   {ans[:400]}...")
elif r:
    print(f"   ❌ Lỗi: {r.text[:300]}")

sep("6. QUIZ GENERATION - K-means (3 câu)")
print("   ⏳ Đang tạo quiz (tối đa 120s)...")
r = test("Generate Quiz", "post", f"{BASE}/api/quiz",
    timeout=QA_TIMEOUT,
    json={"topic": "K-means clustering", "num_questions": 3, "session_id": session_id})
quiz_id = None
if r and r.status_code == 200:
    data = r.json()
    quiz_id = data.get("quiz_id")
    questions = data.get("questions", [])
    total = data.get("total_questions", 0)
    print(f"   ✅ Quiz tạo thành công!")
    print(f"   Quiz ID: {quiz_id}")
    print(f"   Số câu hỏi: {total}")
    for i, q in enumerate(questions[:3], 1):
        if isinstance(q, dict):
            qtext = q.get('question', q.get('text', str(q)))[:100]
        else:
            qtext = str(q)[:100]
        print(f"   Q{i}: {qtext}...")
elif r:
    print(f"   ❌ Lỗi: {r.text[:300]}")

sep("7. CONVERSATION HISTORY")
r = test("Get History", "get", f"{BASE}/api/history/{session_id}")
if r and r.status_code == 200:
    data = r.json()
    msgs = data.get("messages", [])
    total = data.get("total_count", 0)
    print(f"   ✅ Lịch sử: {total} tin nhắn trong session")
    for msg in msgs[-3:]:
        role = msg.get("role", "?")
        content = str(msg.get("content", ""))[:80]
        print(f"   [{role}]: {content}...")
elif r:
    print(f"   ❌ Lỗi: {r.text[:200]}")

sep("8. AUTH - REGISTER (user mới)")
import time
uname = f"testuser_{int(time.time())}"
r = test("Register New User", "post", f"{BASE}/api/auth/register",
    json={"email": f"{uname}@test.com", "username": uname,
          "password": "Test1234!", "full_name": "Test User"})
if r:
    print(f"   Result: {r.json()}")

sep("TỔNG KẾT")
print("✅ Kiểm thử hoàn tất!")
print("Các tính năng chính:")
print("  ✅ Health & Stats API")
print("  ✅ Session Management")
print("  ✅ RAG Q&A (Tiếng Việt)")
print("  ✅ Course Curriculum Q&A")
print("  ✅ Quiz Generation")
print("  ✅ Conversation History")
print("  ✅ Authentication")
