# compare_chunking.py - So sánh chiến lược chunking cũ vs mới
import sys
sys.path.insert(0, '.')

print("=" * 80)
print("SO SÁNH CHIẾN LƯỢC CHUNKING")
print("=" * 80)

print("\n📚 CHIẾN LƯỢC CŨ (1000/200)")
print("-" * 80)
from loader import load_all_documents as load_old
chunks_old = load_old("data")

print(f"\n✅ Kết quả:")
print(f"  - Tổng chunks: {len(chunks_old)}")
lengths_old = [len(c.page_content) for c in chunks_old]
print(f"  - Độ dài TB: {sum(lengths_old)/len(lengths_old):.0f} chars")
print(f"  - Độ dài min/max: {min(lengths_old)}/{max(lengths_old)} chars")

# Đếm chunks bị cắt giữa câu
broken_old = sum(1 for c in chunks_old if c.page_content.strip() and c.page_content.strip()[-1] not in '.!?')
print(f"  - Chunks bị cắt giữa câu: {broken_old} ({broken_old/len(chunks_old)*100:.1f}%)")

print("\n" + "=" * 80)
print("📚 CHIẾN LƯỢC MỚI (1200/250)")
print("-" * 80)
from loader_improved import load_all_documents as load_new
chunks_new = load_new("data")

print(f"\n✅ Kết quả:")
print(f"  - Tổng chunks: {len(chunks_new)}")
lengths_new = [len(c.page_content) for c in chunks_new]
print(f"  - Độ dài TB: {sum(lengths_new)/len(lengths_new):.0f} chars")
print(f"  - Độ dài min/max: {min(lengths_new)}/{max(lengths_new)} chars")

# Đếm chunks bị cắt giữa câu
broken_new = sum(1 for c in chunks_new if c.page_content.strip() and c.page_content.strip()[-1] not in '.!?')
print(f"  - Chunks bị cắt giữa câu: {broken_new} ({broken_new/len(chunks_new)*100:.1f}%)")

# Thống kê content types (chỉ có ở version mới)
content_types = {}
for chunk in chunks_new:
    ct = chunk.metadata.get('content_type', 'unknown')
    content_types[ct] = content_types.get(ct, 0) + 1

print(f"\n📝 Phân loại nội dung (mới):")
for ct, count in sorted(content_types.items(), key=lambda x: x[1], reverse=True):
    print(f"  - {ct}: {count} chunks ({count/len(chunks_new)*100:.1f}%)")

print("\n" + "=" * 80)
print("📊 SO SÁNH")
print("=" * 80)

print(f"\n🔢 Số lượng chunks:")
print(f"  - Cũ: {len(chunks_old)}")
print(f"  - Mới: {len(chunks_new)}")
print(f"  - Chênh lệch: {len(chunks_new) - len(chunks_old)} ({(len(chunks_new) - len(chunks_old))/len(chunks_old)*100:+.1f}%)")

print(f"\n📏 Độ dài trung bình:")
avg_old = sum(lengths_old)/len(lengths_old)
avg_new = sum(lengths_new)/len(lengths_new)
print(f"  - Cũ: {avg_old:.0f} chars")
print(f"  - Mới: {avg_new:.0f} chars")
print(f"  - Chênh lệch: {avg_new - avg_old:+.0f} chars ({(avg_new - avg_old)/avg_old*100:+.1f}%)")

print(f"\n✂️ Chunks bị cắt giữa câu:")
print(f"  - Cũ: {broken_old} ({broken_old/len(chunks_old)*100:.1f}%)")
print(f"  - Mới: {broken_new} ({broken_new/len(chunks_new)*100:.1f}%)")
print(f"  - Cải thiện: {broken_old - broken_new} chunks ({(broken_old - broken_new)/broken_old*100:.1f}%)")

print("\n" + "=" * 80)
print("🎯 KẾT LUẬN")
print("=" * 80)

if len(chunks_new) < len(chunks_old) and avg_new > avg_old:
    print("\n✅ Chiến lược MỚI TỐT HƠN:")
    print("  - Ít chunks hơn → Hiệu quả hơn")
    print("  - Chunks dài hơn → Context tốt hơn")
    print("  - Ít bị cắt giữa câu → Chất lượng cao hơn")
    print("  - Có phân loại content type → Xử lý thông minh hơn")
    print("\n💡 KHUYẾN NGHỊ: Sử dụng chiến lược mới")
else:
    print("\n⚠️ Cần xem xét thêm")
    print("  - So sánh chất lượng retrieval")
    print("  - Test với câu hỏi thực tế")

print("\n📝 Mẫu chunks để so sánh:")
print("\n--- CHUNK CŨ (mẫu) ---")
print(f"Length: {len(chunks_old[100].page_content)} chars")
print(chunks_old[100].page_content[:400])

print("\n--- CHUNK MỚI (mẫu) ---")
print(f"Length: {len(chunks_new[100].page_content)} chars")
print(f"Type: {chunks_new[100].metadata.get('content_type', 'unknown')}")
print(chunks_new[100].page_content[:400])
