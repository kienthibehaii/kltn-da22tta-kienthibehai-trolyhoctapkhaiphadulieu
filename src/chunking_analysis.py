# chunking_analysis.py - Phân tích và đề xuất chiến lược chunking
from langchain_text_splitters import RecursiveCharacterTextSplitter
from loader import load_pdf
import re

def analyze_content_structure(text):
    """Phân tích cấu trúc nội dung"""
    analysis = {
        'has_sections': bool(re.search(r'\n\d+\.\d+', text)),  # 1.1, 2.3, etc.
        'has_bullets': '•' in text or '◦' in text or bool(re.search(r'\n\s*[-*]', text)),
        'has_formulas': any(char in text for char in ['∑', '∫', '√', '≤', '≥', '∈']),
        'has_tables': 'Table' in text or '|' in text,
        'has_figures': 'Figure' in text or 'Fig.' in text,
        'has_algorithms': 'algorithm' in text.lower() or 'procedure' in text.lower(),
        'paragraph_count': len([p for p in text.split('\n\n') if len(p.strip()) > 50]),
        'avg_line_length': sum(len(line) for line in text.split('\n')) / max(len(text.split('\n')), 1)
    }
    return analysis

def test_chunking_strategy(docs, chunk_size, chunk_overlap, separators):
    """Test một chiến lược chunking"""
    splitter = RecursiveCharacterTextSplitter(
        chunk_size=chunk_size,
        chunk_overlap=chunk_overlap,
        length_function=len,
        separators=separators
    )
    
    chunks = splitter.split_documents(docs)
    
    # Thống kê
    lengths = [len(c.page_content) for c in chunks]
    
    # Đếm chunks bị cắt giữa câu
    broken_chunks = 0
    for chunk in chunks:
        content = chunk.page_content.strip()
        if content and not content[-1] in '.!?':
            broken_chunks += 1
    
    return {
        'total_chunks': len(chunks),
        'avg_length': sum(lengths) / len(lengths) if lengths else 0,
        'min_length': min(lengths) if lengths else 0,
        'max_length': max(lengths) if lengths else 0,
        'broken_chunks': broken_chunks,
        'broken_ratio': broken_chunks / len(chunks) if chunks else 0,
        'chunks': chunks
    }

def main():
    print("=" * 80)
    print("PHÂN TÍCH CHIẾN LƯỢC CHUNKING")
    print("=" * 80)
    
    # Load mẫu 50 trang
    print("\n📚 Đang load 50 trang đầu từ PDF...")
    docs = load_pdf('data/Data.Mining.Concepts.and.Techniques.2nd.Ed-1558609016.pdf')[:50]
    
    # Phân tích cấu trúc
    print("\n📊 Phân tích cấu trúc nội dung:")
    sample_pages = [d for d in docs if len(d.page_content) > 1000][:5]
    
    for i, doc in enumerate(sample_pages, 1):
        analysis = analyze_content_structure(doc.page_content)
        print(f"\n  Trang mẫu {i}:")
        print(f"    - Có sections: {analysis['has_sections']}")
        print(f"    - Có bullets: {analysis['has_bullets']}")
        print(f"    - Có công thức: {analysis['has_formulas']}")
        print(f"    - Có bảng: {analysis['has_tables']}")
        print(f"    - Có hình: {analysis['has_figures']}")
        print(f"    - Có algorithms: {analysis['has_algorithms']}")
        print(f"    - Số đoạn văn: {analysis['paragraph_count']}")
        print(f"    - Độ dài dòng TB: {analysis['avg_line_length']:.0f} chars")
    
    # Test các chiến lược khác nhau
    print("\n" + "=" * 80)
    print("SO SÁNH CÁC CHIẾN LƯỢC CHUNKING")
    print("=" * 80)
    
    strategies = [
        {
            'name': 'Hiện tại (1000/200)',
            'chunk_size': 1000,
            'chunk_overlap': 200,
            'separators': ["\n\n", "\n", ".", " ", ""]
        },
        {
            'name': 'Lớn hơn (1500/300)',
            'chunk_size': 1500,
            'chunk_overlap': 300,
            'separators': ["\n\n", "\n", ".", " ", ""]
        },
        {
            'name': 'Nhỏ hơn (800/150)',
            'chunk_size': 800,
            'chunk_overlap': 150,
            'separators': ["\n\n", "\n", ".", " ", ""]
        },
        {
            'name': 'Ưu tiên đoạn văn (1200/250)',
            'chunk_size': 1200,
            'chunk_overlap': 250,
            'separators': ["\n\n\n", "\n\n", "\n", ". ", "! ", "? ", ", ", " ", ""]
        },
        {
            'name': 'Semantic-aware (1000/200)',
            'chunk_size': 1000,
            'chunk_overlap': 200,
            'separators': [
                "\n\n\n",  # Ngắt giữa các sections
                "\n\n",    # Ngắt giữa các đoạn
                "\n",      # Ngắt dòng
                ". ",      # Ngắt câu
                "! ",
                "? ",
                "; ",
                ", ",
                " ",
                ""
            ]
        }
    ]
    
    results = []
    for strategy in strategies:
        print(f"\n🔍 Test: {strategy['name']}")
        result = test_chunking_strategy(
            docs,
            strategy['chunk_size'],
            strategy['chunk_overlap'],
            strategy['separators']
        )
        result['name'] = strategy['name']
        results.append(result)
        
        print(f"  ✓ Tổng chunks: {result['total_chunks']}")
        print(f"  ✓ Độ dài TB: {result['avg_length']:.0f} chars")
        print(f"  ✓ Độ dài min/max: {result['min_length']}/{result['max_length']}")
        print(f"  ✓ Chunks bị cắt giữa câu: {result['broken_chunks']} ({result['broken_ratio']*100:.1f}%)")
    
    # Đề xuất
    print("\n" + "=" * 80)
    print("ĐỀ XUẤT CHIẾN LƯỢC TỐI ƯU")
    print("=" * 80)
    
    # Tìm chiến lược tốt nhất (ít bị cắt nhất, độ dài hợp lý)
    best = min(results, key=lambda x: x['broken_ratio'])
    
    print(f"\n🏆 Chiến lược tốt nhất: {best['name']}")
    print(f"   - Tổng chunks: {best['total_chunks']}")
    print(f"   - Độ dài trung bình: {best['avg_length']:.0f} chars")
    print(f"   - Tỷ lệ bị cắt: {best['broken_ratio']*100:.1f}%")
    
    # Hiển thị mẫu chunks
    print(f"\n📄 Mẫu chunks từ chiến lược tốt nhất:")
    for i in [0, len(best['chunks'])//2, len(best['chunks'])-1]:
        if i < len(best['chunks']):
            chunk = best['chunks'][i]
            print(f"\n--- Chunk {i+1} ({len(chunk.page_content)} chars) ---")
            print(chunk.page_content[:300] + "...")
    
    # Đề xuất cụ thể
    print("\n" + "=" * 80)
    print("KHUYẾN NGHỊ")
    print("=" * 80)
    
    print("""
📌 Dựa trên phân tích, đề xuất cấu hình chunking:

1. CHUNK SIZE: 1200-1500 chars
   - Lý do: Tài liệu học thuật có đoạn văn dài, cần context đủ lớn
   - Trang PDF trung bình ~2600 chars → 2 chunks/trang là hợp lý

2. CHUNK OVERLAP: 250-300 chars
   - Lý do: Đảm bảo không mất ngữ cảnh giữa các chunks
   - ~20% overlap giúp giữ được tính liên tục

3. SEPARATORS (theo thứ tự ưu tiên):
   - "\\n\\n\\n" : Ngắt giữa các sections lớn
   - "\\n\\n"   : Ngắt giữa các đoạn văn
   - "\\n"      : Ngắt dòng
   - ". "       : Ngắt câu (có dấu cách sau dấu chấm)
   - "! ", "? " : Ngắt câu cảm thán/nghi vấn
   - "; "       : Ngắt mệnh đề
   - ", "       : Ngắt cụm từ (cuối cùng)
   - " "        : Ngắt từ
   - ""         : Ngắt ký tự (fallback)

4. ĐẶC BIỆT CHO TÀI LIỆU HỌC THUẬT:
   - Giữ nguyên công thức toán học trong 1 chunk
   - Giữ nguyên algorithms/pseudocode trong 1 chunk
   - Giữ nguyên tables nếu có thể
   - Ưu tiên ngắt tại ranh giới sections

5. XỬ LÝ ĐẶC BIỆT:
   - Trang trống (<100 chars): Bỏ qua
   - Trang mục lục: Có thể bỏ qua hoặc chunk riêng
   - Trang tham khảo: Chunk riêng với metadata đặc biệt
""")

if __name__ == "__main__":
    main()
