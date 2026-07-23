# analyze_data.py - Phân tích cấu trúc dữ liệu
from loader import load_pdf, load_ppt
import os

def analyze_pdf():
    print("=" * 70)
    print("PHÂN TÍCH PDF")
    print("=" * 70)
    
    docs = load_pdf('data/Data.Mining.Concepts.and.Techniques.2nd.Ed-1558609016.pdf')
    
    # Thống kê độ dài
    lengths = [len(d.page_content) for d in docs]
    print(f"\n📊 Thống kê độ dài trang:")
    print(f"  - Tổng số trang: {len(docs)}")
    print(f"  - Độ dài trung bình: {sum(lengths)/len(lengths):.0f} ký tự")
    print(f"  - Độ dài min: {min(lengths)} ký tự")
    print(f"  - Độ dài max: {max(lengths)} ký tự")
    print(f"  - Trang trống (0 chars): {sum(1 for l in lengths if l == 0)}")
    print(f"  - Trang ngắn (<500 chars): {sum(1 for l in lengths if 0 < l < 500)}")
    print(f"  - Trang trung bình (500-2000): {sum(1 for l in lengths if 500 <= l < 2000)}")
    print(f"  - Trang dài (2000+): {sum(1 for l in lengths if l >= 2000)}")
    
    # Phân tích nội dung mẫu
    print(f"\n📄 Mẫu nội dung:")
    
    # Tìm trang có nội dung thực
    for i, doc in enumerate(docs[40:60], start=40):
        if len(doc.page_content) > 1000:
            print(f"\n--- Trang {i+1} ({len(doc.page_content)} chars) ---")
            content = doc.page_content
            
            # Kiểm tra cấu trúc
            has_sections = any(marker in content for marker in ['1.', '2.', '3.', '4.', '5.'])
            has_bullets = '•' in content or '◦' in content
            has_formulas = any(char in content for char in ['∑', '∫', '√', '≤', '≥'])
            has_code = 'algorithm' in content.lower() or 'procedure' in content.lower()
            
            print(f"  Có sections: {has_sections}")
            print(f"  Có bullets: {has_bullets}")
            print(f"  Có công thức: {has_formulas}")
            print(f"  Có code/algorithm: {has_code}")
            print(f"\n  Nội dung đầu:\n  {content[:400]}")
            break
    
    return docs

def analyze_ppt():
    print("\n" + "=" * 70)
    print("PHÂN TÍCH PPT")
    print("=" * 70)
    
    ppt_files = [f for f in os.listdir('data') if f.endswith('.ppt')]
    print(f"\n📊 Tổng số file PPT: {len(ppt_files)}")
    
    all_slides = []
    for ppt_file in ppt_files[:3]:  # Phân tích 3 file đầu
        docs = load_ppt(f'data/{ppt_file}')
        if docs:
            all_slides.extend(docs)
            print(f"\n📄 {ppt_file}:")
            print(f"  - Số slides: {len(docs)}")
            
            lengths = [len(d.page_content) for d in docs]
            print(f"  - Độ dài trung bình: {sum(lengths)/len(lengths):.0f} chars")
            print(f"  - Độ dài min: {min(lengths)} chars")
            print(f"  - Độ dài max: {max(lengths)} chars")
            
            # Mẫu slide
            if docs:
                print(f"\n  Slide đầu tiên:")
                print(f"  {docs[0].page_content[:300]}")
    
    return all_slides

def analyze_chunks():
    print("\n" + "=" * 70)
    print("PHÂN TÍCH CHUNKS HIỆN TẠI")
    print("=" * 70)
    
    from loader import load_all_documents
    chunks = load_all_documents('data')
    
    lengths = [len(c.page_content) for c in chunks]
    print(f"\n📊 Thống kê chunks:")
    print(f"  - Tổng số chunks: {len(chunks)}")
    print(f"  - Độ dài trung bình: {sum(lengths)/len(lengths):.0f} chars")
    print(f"  - Độ dài min: {min(lengths)} chars")
    print(f"  - Độ dài max: {max(lengths)} chars")
    print(f"  - Chunks <500 chars: {sum(1 for l in lengths if l < 500)}")
    print(f"  - Chunks 500-1000 chars: {sum(1 for l in lengths if 500 <= l < 1000)}")
    print(f"  - Chunks 1000+ chars: {sum(1 for l in lengths if l >= 1000)}")
    
    # Mẫu chunks
    print(f"\n📄 Mẫu chunks:")
    for i in [0, len(chunks)//2, len(chunks)-1]:
        print(f"\n--- Chunk {i+1} ({len(chunks[i].page_content)} chars) ---")
        print(f"Source: {chunks[i].metadata.get('source', 'unknown')}")
        print(f"Content: {chunks[i].page_content[:300]}...")
    
    return chunks

if __name__ == "__main__":
    pdf_docs = analyze_pdf()
    ppt_slides = analyze_ppt()
    chunks = analyze_chunks()
    
    print("\n" + "=" * 70)
    print("KẾT LUẬN")
    print("=" * 70)
    print(f"\n✅ Đã phân tích xong dữ liệu")
    print(f"   - PDF: {len(pdf_docs)} trang")
    print(f"   - PPT: {len(ppt_slides)} slides")
    print(f"   - Chunks: {len(chunks)} chunks")
