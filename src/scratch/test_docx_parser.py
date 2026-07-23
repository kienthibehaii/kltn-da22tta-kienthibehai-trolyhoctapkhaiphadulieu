import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.stdout.reconfigure(encoding='utf-8', errors='replace')

from loader import load_docx

docs = load_docx('data/220269_ Khai pha du lieu - AI.docx')
print(f'Total sections: {len(docs)}\n')

# Tìm section chứa bảng đánh giá (tỷ lệ %)
for i, doc in enumerate(docs):
    c = doc.page_content
    if any(k in c for k in ['25%', '50%', 'Tỷ lệ', 'Kiểm tra lý thuyết']):
        print(f'=== Section {i+1} [{doc.metadata.get("section","")}] ===')
        print(c[:800])
        print()
        break

# Tìm section chứa nội dung học phần
for i, doc in enumerate(docs):
    c = doc.page_content
    if 'Bài 1' in c and 'GIỚI THIỆU' in c:
        print(f'=== Section {i+1} [{doc.metadata.get("section","")}] ===')
        print(c[:600])
        print()
        break

# Tìm section bullet list
for i, doc in enumerate(docs):
    c = doc.page_content
    if '•' in c:
        print(f'=== Section {i+1} [bullet list] ===')
        print(c[:400])
        print()
        break

# Xem section học liệu (key-value table)
for i, doc in enumerate(docs):
    c = doc.page_content
    if 'Giáo trình' in c or 'Tài liệu tham khảo' in c:
        print(f'=== Section {i+1} [tai lieu] ===')
        print(c[:500])
        print()
        break
