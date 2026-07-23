"""Test 3 scenarios: in-context, out-of-context, partial context."""
import sys, os, urllib.request, json
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.stdout.reconfigure(encoding='utf-8', errors='replace')

BASE = "http://127.0.0.1:8000"

def ask(question, session="prompt_test"):
    req = urllib.request.Request(
        f"{BASE}/api/question", method="POST",
        headers={"Content-Type": "application/json"},
        data=json.dumps({"question": question, "session_id": session}).encode()
    )
    with urllib.request.urlopen(req, timeout=90) as r:
        return json.loads(r.read())

print("="*65)

# Test 1: Câu hỏi có đáp án trong tài liệu
print("\n[TEST 1] In-context: Bai tap lon chiem bao nhieu phan tram?")
d = ask("Bai tap lon chiem bao nhieu phan tram tong diem hoc phan?", "t1")
ans = d.get("answer", "")
cits = d.get("citations", [])
has_inline = any(f"[{i}]" in ans for i in range(1, 6))
has_sources = "Nguồn" in ans or "nguồn" in ans or len(cits) > 0
not_hallucinated = "Tôi không tìm thấy" not in ans
print(f"  Has inline [N]:    {has_inline}")
print(f"  Has source block:  {has_sources}")
print(f"  Answered (not N/F):{not_hallucinated}")
print(f"  Citations count:   {len(cits)}")
print(f"  Answer preview:    {ans[:250]}")

print("\n[TEST 2] Out-of-context: topic không có trong tài liệu")
d2 = ask("Thoi tiet Ha Noi hom nay the nao?", "t2")
ans2 = d2.get("answer", "")
refused = "không tìm thấy" in ans2.lower() or "không có thông tin" in ans2.lower()
print(f"  Correctly refused: {refused}")
print(f"  Answer:            {ans2[:200]}")

print("\n[TEST 3] Partial context: câu hỏi kỹ thuật — source phải đúng")
d3 = ask("KDD la gi?", "t3")
ans3 = d3.get("answer", "")
cits3 = d3.get("citations", [])
not_hallucinated3 = "Tôi không tìm thấy" not in ans3
has_cite3 = any(f"[{i}]" in ans3 for i in range(1, 6))
print(f"  Answered:    {not_hallucinated3}")
print(f"  Has inline:  {has_cite3}")
print(f"  Sources:     {[c.get('filename','?')[:25] for c in cits3]}")
print(f"  Answer:      {ans3[:250]}")

print("\n" + "="*65)
print("ASSERTIONS:")
assert has_inline, "Test1: phải có inline citation [N]"
print("  [1] Inline citations present: OK")
assert not_hallucinated, "Test1: phải trả lời câu hỏi có trong tài liệu"
print("  [2] In-context answered: OK")
assert refused, f"Test2: câu hỏi ngoài context phải từ chối. Got: {ans2[:100]}"
print("  [3] Out-of-context refused: OK")
assert not_hallucinated3, "Test3: KDD phải có trong tài liệu"
print("  [4] KDD answered from context: OK")
print("\nALL ASSERTIONS PASSED")
