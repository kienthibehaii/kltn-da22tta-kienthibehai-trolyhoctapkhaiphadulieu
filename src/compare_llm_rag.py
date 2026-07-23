# compare_llm_rag.py - So sánh LLM trực tiếp vs RAG
import os
import time
from dotenv import load_dotenv
from langchain_google_genai import ChatGoogleGenerativeAI
from embed_store import load_vector_store, load_documents
from rag import create_qa_chain, ask_question

load_dotenv()

class LLMRAGComparator:
    """
    So sánh câu trả lời giữa LLM trực tiếp và RAG
    """
    
    def __init__(self):
        self.llm = ChatGoogleGenerativeAI(
            model="gemini-2.5-flash",
            google_api_key=os.getenv("GOOGLE_API_KEY"),
            temperature=0.3,
            convert_system_message_to_human=True
        )
        
        # Load RAG pipeline
        print("📦 Đang load RAG pipeline...")
        vectordb = load_vector_store("chroma_db")
        
        try:
            documents = load_documents("chroma_db")
            self.qa_chain, self.retriever = create_qa_chain(
                vectordb, 
                documents=documents, 
                use_hybrid=True
            )
            print("✅ Đã load RAG pipeline (Hybrid + Rerank)")
        except:
            self.qa_chain, self.retriever = create_qa_chain(
                vectordb, 
                use_hybrid=False
            )
            print("✅ Đã load RAG pipeline (Vector only)")
    
    def ask_llm_direct(self, question: str) -> dict:
        """
        Hỏi LLM trực tiếp (không dùng RAG)
        
        Returns:
            dict với keys: answer, time, has_source
        """
        print("\n🤖 MODE 1: LLM Trực tiếp (Không RAG)")
        print("-" * 80)
        
        prompt = f"""You are an AI assistant specialized in Data Mining education.
Answer the following question based on your general knowledge.

Question: {question}

Answer (provide detailed, accurate response):"""
        
        start_time = time.time()
        
        try:
            response = self.llm.invoke(prompt)
            answer = response.content if hasattr(response, 'content') else str(response)
            response_time = time.time() - start_time
            
            result = {
                'answer': answer,
                'time': response_time,
                'has_source': False,
                'sources': [],
                'citations': [],
                'success': True
            }
            
            print(f"✅ Hoàn thành trong {response_time:.2f}s")
            
        except Exception as e:
            print(f"❌ Lỗi: {e}")
            result = {
                'answer': f"Lỗi: {str(e)}",
                'time': time.time() - start_time,
                'has_source': False,
                'sources': [],
                'citations': [],
                'success': False
            }
        
        return result
    
    def ask_rag(self, question: str) -> dict:
        """
        Hỏi sử dụng RAG (retrieve + LLM)
        
        Returns:
            dict với keys: answer, time, has_source, sources, citations
        """
        print("\n📚 MODE 2: RAG (Retrieve + LLM)")
        print("-" * 80)
        
        start_time = time.time()
        
        try:
            answer, sources, citations = ask_question(
                self.qa_chain,
                self.retriever,
                question,
                conversation_context="",
                use_rerank=True
            )
            
            response_time = time.time() - start_time
            
            result = {
                'answer': answer,
                'time': response_time,
                'has_source': True,
                'sources': sources,
                'citations': citations,
                'success': True
            }
            
            print(f"✅ Hoàn thành trong {response_time:.2f}s")
            print(f"📄 Sử dụng {len(sources)} nguồn tài liệu")
            
        except Exception as e:
            print(f"❌ Lỗi: {e}")
            result = {
                'answer': f"Lỗi: {str(e)}",
                'time': time.time() - start_time,
                'has_source': False,
                'sources': [],
                'citations': [],
                'success': False
            }
        
        return result
    
    def compare(self, question: str) -> dict:
        """
        So sánh câu trả lời giữa LLM trực tiếp và RAG
        
        Returns:
            dict với keys: question, llm_result, rag_result, comparison
        """
        print("\n" + "=" * 80)
        print("SO SÁNH LLM TRỰC TIẾP VS RAG")
        print("=" * 80)
        print(f"\n❓ Câu hỏi: {question}")
        print()
        
        # Hỏi LLM trực tiếp
        llm_result = self.ask_llm_direct(question)
        
        # Hỏi RAG
        rag_result = self.ask_rag(question)
        
        # So sánh
        comparison = self._analyze_comparison(llm_result, rag_result)
        
        return {
            'question': question,
            'llm_result': llm_result,
            'rag_result': rag_result,
            'comparison': comparison
        }
    
    def _analyze_comparison(self, llm_result: dict, rag_result: dict) -> dict:
        """
        Phân tích so sánh giữa 2 kết quả
        """
        comparison = {}
        
        # So sánh độ dài (chi tiết)
        llm_length = len(llm_result['answer'])
        rag_length = len(rag_result['answer'])
        
        comparison['length'] = {
            'llm': llm_length,
            'rag': rag_length,
            'difference': rag_length - llm_length,
            'winner': 'RAG' if rag_length > llm_length else 'LLM' if llm_length > rag_length else 'Tie'
        }
        
        # So sánh thời gian
        comparison['time'] = {
            'llm': llm_result['time'],
            'rag': rag_result['time'],
            'difference': rag_result['time'] - llm_result['time'],
            'winner': 'LLM' if llm_result['time'] < rag_result['time'] else 'RAG'
        }
        
        # So sánh nguồn
        comparison['sources'] = {
            'llm': 0,
            'rag': len(rag_result.get('citations', [])),
            'winner': 'RAG' if rag_result['has_source'] else 'None'
        }
        
        # Đếm số từ khóa kỹ thuật (ước lượng độ chính xác)
        technical_keywords = [
            'algorithm', 'data', 'mining', 'clustering', 'classification',
            'association', 'rules', 'supervised', 'unsupervised', 'learning',
            'model', 'training', 'testing', 'validation', 'accuracy',
            'precision', 'recall', 'f1', 'score', 'metric'
        ]
        
        llm_keywords = sum(1 for kw in technical_keywords if kw.lower() in llm_result['answer'].lower())
        rag_keywords = sum(1 for kw in technical_keywords if kw.lower() in rag_result['answer'].lower())
        
        comparison['technical_depth'] = {
            'llm': llm_keywords,
            'rag': rag_keywords,
            'winner': 'RAG' if rag_keywords > llm_keywords else 'LLM' if llm_keywords > rag_keywords else 'Tie'
        }
        
        # Tổng kết
        rag_wins = sum(1 for metric in ['length', 'sources', 'technical_depth'] 
                       if comparison[metric]['winner'] == 'RAG')
        llm_wins = sum(1 for metric in ['time'] 
                       if comparison[metric]['winner'] == 'LLM')
        
        comparison['overall_winner'] = 'RAG' if rag_wins > llm_wins else 'LLM' if llm_wins > rag_wins else 'Tie'
        comparison['rag_advantages'] = rag_wins
        comparison['llm_advantages'] = llm_wins
        
        return comparison
    
    def display_comparison(self, result: dict):
        """
        Hiển thị kết quả so sánh đẹp
        """
        print("\n" + "=" * 80)
        print("KẾT QUẢ SO SÁNH")
        print("=" * 80)
        
        llm_result = result['llm_result']
        rag_result = result['rag_result']
        comparison = result['comparison']
        
        # Hiển thị câu trả lời
        print("\n📝 CÂU TRẢ LỜI:")
        print("-" * 80)
        
        print("\n🤖 LLM Trực tiếp:")
        print(llm_result['answer'][:300] + ("..." if len(llm_result['answer']) > 300 else ""))
        
        print("\n📚 RAG:")
        print(rag_result['answer'][:300] + ("..." if len(rag_result['answer']) > 300 else ""))
        
        # Bảng so sánh
        print("\n" + "=" * 80)
        print("📊 BẢNG SO SÁNH CHI TIẾT")
        print("=" * 80)
        
        print(f"\n{'Tiêu chí':<25} {'LLM Trực tiếp':<25} {'RAG':<25} {'Thắng':<10}")
        print("-" * 85)
        
        # Độ chi tiết (length)
        llm_len = comparison['length']['llm']
        rag_len = comparison['length']['rag']
        winner = comparison['length']['winner']
        winner_icon = "🏆" if winner == "RAG" else "⭐" if winner == "LLM" else "🤝"
        print(f"{'Độ chi tiết (ký tự)':<25} {llm_len:<25} {rag_len:<25} {winner} {winner_icon}")
        
        # Thời gian
        llm_time = f"{comparison['time']['llm']:.2f}s"
        rag_time = f"{comparison['time']['rag']:.2f}s"
        winner = comparison['time']['winner']
        winner_icon = "🏆" if winner == "RAG" else "⭐" if winner == "LLM" else "🤝"
        print(f"{'Thời gian phản hồi':<25} {llm_time:<25} {rag_time:<25} {winner} {winner_icon}")
        
        # Nguồn tài liệu
        llm_sources = "Không có"
        rag_sources = f"{comparison['sources']['rag']} nguồn"
        winner = comparison['sources']['winner']
        winner_icon = "🏆" if winner == "RAG" else "⭐" if winner == "LLM" else "❌"
        print(f"{'Nguồn tài liệu':<25} {llm_sources:<25} {rag_sources:<25} {winner} {winner_icon}")
        
        # Độ sâu kỹ thuật
        llm_tech = f"{comparison['technical_depth']['llm']} keywords"
        rag_tech = f"{comparison['technical_depth']['rag']} keywords"
        winner = comparison['technical_depth']['winner']
        winner_icon = "🏆" if winner == "RAG" else "⭐" if winner == "LLM" else "🤝"
        print(f"{'Độ sâu kỹ thuật':<25} {llm_tech:<25} {rag_tech:<25} {winner} {winner_icon}")
        
        print("-" * 85)
        
        # Tổng kết
        print("\n" + "=" * 80)
        print("🏆 TỔNG KẾT")
        print("=" * 80)
        
        overall = comparison['overall_winner']
        rag_adv = comparison['rag_advantages']
        llm_adv = comparison['llm_advantages']
        
        if overall == 'RAG':
            print(f"\n✅ RAG THẮNG với {rag_adv} ưu điểm vượt trội!")
            print("\n💡 Lý do:")
            if comparison['sources']['winner'] == 'RAG':
                print("   ✓ Có nguồn tài liệu tham khảo cụ thể")
            if comparison['length']['winner'] == 'RAG':
                print("   ✓ Câu trả lời chi tiết hơn")
            if comparison['technical_depth']['winner'] == 'RAG':
                print("   ✓ Độ sâu kỹ thuật cao hơn")
        elif overall == 'LLM':
            print(f"\n✅ LLM TRỰC TIẾP THẮNG với {llm_adv} ưu điểm!")
            print("\n💡 Lý do:")
            if comparison['time']['winner'] == 'LLM':
                print("   ✓ Phản hồi nhanh hơn")
        else:
            print("\n🤝 HÒA - Cả hai đều có ưu điểm riêng")
        
        # Highlight sự khác biệt
        print("\n" + "=" * 80)
        print("🔍 SỰ KHÁC BIỆT NỔI BẬT")
        print("=" * 80)
        
        print("\n📌 LLM Trực tiếp:")
        print("   ✓ Nhanh hơn" if comparison['time']['winner'] == 'LLM' else "   ✗ Chậm hơn")
        print("   ✗ Không có nguồn tham khảo")
        print("   ✗ Có thể hallucination (tưởng tượng thông tin)")
        print("   ✓ Câu trả lời tổng quát" if comparison['length']['winner'] != 'RAG' else "   ✗ Câu trả lời ngắn hơn")
        
        print("\n📌 RAG:")
        print("   ✗ Chậm hơn" if comparison['time']['winner'] == 'LLM' else "   ✓ Tốc độ tương đương")
        print(f"   ✓ Có {comparison['sources']['rag']} nguồn tài liệu cụ thể")
        print("   ✓ Thông tin chính xác từ tài liệu")
        print("   ✓ Câu trả lời chi tiết hơn" if comparison['length']['winner'] == 'RAG' else "   ✗ Câu trả lời ngắn hơn")
        
        # Hiển thị nguồn RAG
        if rag_result.get('citations'):
            print("\n" + "=" * 80)
            print("📚 NGUỒN TÀI LIỆU CỦA RAG")
            print("=" * 80)
            
            for citation in rag_result['citations'][:3]:  # Hiển thị top 3
                print(f"\n📄 {citation['filename']} - ", end="")
                if citation['slide']:
                    print(f"Slide {citation['slide']}")
                elif citation['page'] != 'N/A':
                    print(f"Trang {citation['page']}")
                else:
                    print("N/A")
                
                # Hiển thị relevance score nếu có
                if citation.get('relevance_score'):
                    score = citation['relevance_score']
                    emoji = "🟢" if score >= 0.7 else "🟡" if score >= 0.5 else "🟠"
                    print(f"   {emoji} Độ liên quan: {score:.2f}")
                
                print(f"   📖 {citation['content'][:150]}...")
        
        print("\n" + "=" * 80)

def compare_single_question(question: str):
    """
    So sánh một câu hỏi đơn lẻ
    """
    comparator = LLMRAGComparator()
    result = comparator.compare(question)
    comparator.display_comparison(result)
    return result

def compare_multiple_questions(questions: list):
    """
    So sánh nhiều câu hỏi
    """
    comparator = LLMRAGComparator()
    results = []
    
    for i, question in enumerate(questions, 1):
        print(f"\n{'='*80}")
        print(f"CÂU HỎI {i}/{len(questions)}")
        print(f"{'='*80}")
        
        result = comparator.compare(question)
        comparator.display_comparison(result)
        results.append(result)
        
        if i < len(questions):
            print("\n" + "="*80)
            input("Nhấn Enter để tiếp tục...")
    
    # Tổng kết tất cả
    print("\n" + "="*80)
    print("📊 TỔNG KẾT TẤT CẢ CÂU HỎI")
    print("="*80)
    
    rag_wins = sum(1 for r in results if r['comparison']['overall_winner'] == 'RAG')
    llm_wins = sum(1 for r in results if r['comparison']['overall_winner'] == 'LLM')
    ties = sum(1 for r in results if r['comparison']['overall_winner'] == 'Tie')
    
    print(f"\nTổng số câu hỏi: {len(questions)}")
    print(f"RAG thắng: {rag_wins} câu")
    print(f"LLM thắng: {llm_wins} câu")
    print(f"Hòa: {ties} câu")
    
    if rag_wins > llm_wins:
        print(f"\n🏆 RAG THẮNG TỔNG THỂ!")
    elif llm_wins > rag_wins:
        print(f"\n🏆 LLM THẮNG TỔNG THỂ!")
    else:
        print(f"\n🤝 HÒA TỔNG THỂ!")
    
    return results

if __name__ == "__main__":
    # Test với một câu hỏi
    question = "Clustering là gì?"
    compare_single_question(question)
