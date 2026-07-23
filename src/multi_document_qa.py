# multi_document_qa.py - Multi-document QA với tổng hợp thông tin
import os
import asyncio
import concurrent.futures
from typing import List, Dict, Tuple
from collections import defaultdict
from dotenv import load_dotenv
from langchain_google_genai import ChatGoogleGenerativeAI
from llm_router import get_llm

load_dotenv()

def _extract_key_points_single(doc, question: str) -> Dict:
    """
    Trích xuất key points từ MỘT document (chạy trong thread pool).
    Tách ra để asyncio.gather có thể gọi song song.
    """
    from reliability.api_key_manager import api_key_manager

    metadata = doc.metadata
    source = metadata.get('source', 'Unknown')
    page = metadata.get('page', 'N/A')
    slide = metadata.get('slide', None)

    filename = source.replace('\\', '/').split('/')[-1] if ('/' in source or '\\' in source) else source
    content = doc.page_content.strip()

    prompt = f"""Extract 2-3 key points from this document relevant to the question.
Be concise and specific.

Question: {question}

Document:
{content[:1000]}

Key points:"""

    key_points = None
    keys_pool_size = len(api_key_manager.keys)
    attempts_limit = max(keys_pool_size, 3)

    for attempt in range(attempts_limit):
        key_info = api_key_manager.get_available_key()
        if not key_info:
            break
        try:
            llm = get_llm(task_type="general")
            response = llm.invoke(prompt)
            key_points = response.content if hasattr(response, 'content') else str(response)
            api_key_manager.record_key_success(key_info.key)
            break
        except Exception as e:
            error_msg = str(e)
            is_quota = any(kw in error_msg for kw in ["RESOURCE_EXHAUSTED", "429", "503", "UNAVAILABLE"])
            api_key_manager.record_key_failure(key_info.key, is_quota_error=is_quota)

    if not key_points:
        sentences = content.split('.')[:2]
        key_points = '. '.join(sentences) + '.'

    return {
        'filename': filename,
        'page': page,
        'slide': slide,
        'key_points': key_points,
        'content': content,
        'full_source': source,
        'relevance_score': metadata.get('relevance_score', None),
    }

class MultiDocumentQA:
    """
    Xử lý câu hỏi từ nhiều tài liệu và tổng hợp thành câu trả lời duy nhất
    """
    
    def __init__(self):
        self.llm = get_llm(task_type="complex")
    
    def group_documents_by_source(self, documents: List) -> Dict[str, List]:
        """
        Nhóm documents theo nguồn (file)
        
        Returns:
            Dict với key là filename, value là list documents từ file đó
        """
        grouped = defaultdict(list)
        
        for doc in documents:
            source = doc.metadata.get('source', 'Unknown')
            
            # Lấy tên file
            if '/' in source or '\\' in source:
                filename = source.replace('\\', '/').split('/')[-1]
            else:
                filename = source
            
            grouped[filename].append(doc)
        
        return dict(grouped)
    
    def extract_key_points_per_document(self, documents: List, question: str) -> List[Dict]:
        """
        Trích xuất key points từ tất cả documents SONG SONG bằng ThreadPoolExecutor.
        Giảm từ N sequential LLM calls → N parallel calls.
        """
        with concurrent.futures.ThreadPoolExecutor(max_workers=min(len(documents), 5)) as pool:
            futures = [pool.submit(_extract_key_points_single, doc, question) for doc in documents]
            results = [f.result() for f in concurrent.futures.as_completed(futures)]
        # Giữ thứ tự gốc (as_completed không đảm bảo thứ tự)
        ordered = []
        for doc in documents:
            source = doc.metadata.get('source', 'Unknown')
            filename = source.replace('\\', '/').split('/')[-1] if ('/' in source or '\\' in source) else source
            page = doc.metadata.get('page', 'N/A')
            slide = doc.metadata.get('slide', None)
            for r in results:
                if r['filename'] == filename and str(r['page']) == str(page) and str(r.get('slide')) == str(slide):
                    ordered.append(r)
                    break
        return ordered if ordered else results
    
    def remove_duplicate_information(self, key_points_list: List[Dict]) -> List[Dict]:
        """
        Loại bỏ thông tin trùng lặp giữa các documents
        
        Returns:
            List of dicts với thông tin không trùng lặp
        """
        unique_points = []
        
        def get_norm(val):
            if val is None:
                return ""
            return str(val).strip().lower()
            
        for item in key_points_list:
            found = False
            for up in unique_points:
                same_file = get_norm(up.get('filename')) == get_norm(item.get('filename'))
                same_page = get_norm(up.get('page')) == get_norm(item.get('page'))
                same_slide = get_norm(up.get('slide')) == get_norm(item.get('slide'))
                if same_file and same_page and same_slide:
                    found = True
                    break
            
            if not found:
                unique_points.append(item)
        
        return unique_points
    
    def synthesize_answer(self, question: str, key_points_list: List[Dict]) -> str:
        """
        Tổng hợp câu trả lời từ nhiều nguồn
        
        Returns:
            Câu trả lời tổng hợp với trích nguồn inline
        """
        # Tạo context từ key points
        context_parts = []
        for i, item in enumerate(key_points_list, 1):
            filename = item['filename']
            page = item['page']
            slide = item['slide']
            key_points = item['key_points']
            
            # Format nguồn
            if slide:
                source_ref = f"Document [{i}] ({filename} - Slide {slide})"
            elif page != 'N/A':
                source_ref = f"Document [{i}] ({filename} - Trang {page})"
            else:
                source_ref = f"Document [{i}] ({filename})"
            
            context_parts.append(f"{source_ref}:\n{key_points}")
        
        context = "\n\n".join(context_parts)
        
        # Prompt cho tổng hợp
        prompt = f"""You are an AI assistant specialized in synthesizing information from multiple sources.

Your task is to answer the question by combining information from multiple documents.

IMPORTANT REQUIREMENTS:
1. Synthesize information from ALL provided sources into ONE coherent answer
2. Do NOT repeat the same information multiple times
3. Cite sources inline using [i] format (e.g., [1]) when using information from Document [i]
4. Organize the answer logically (introduction, main points, conclusion)
5. If sources provide different perspectives, mention all of them
6. If sources contradict, note the contradiction

Question: {question}

Information from multiple sources:
{context}

Synthesized Answer (with inline citations [i]):"""
        
        from reliability.api_key_manager import api_key_manager
        keys_pool_size = len(api_key_manager.keys)
        attempts_limit = max(keys_pool_size, 3)
        answer = None
        
        for attempt in range(attempts_limit):
            key_info = api_key_manager.get_available_key()
            if not key_info:
                print("⚠️ Không có API key khả dụng để tổng hợp câu trả lời!")
                break
                
            current_key = key_info.key
            try:
                llm = get_llm(task_type="complex")
                response = llm.invoke(prompt)
                answer = response.content if hasattr(response, 'content') else str(response)
                
                # Record success
                api_key_manager.record_key_success(current_key)
                break
            except Exception as e:
                error_msg = str(e)
                is_quota = any(kw in error_msg for kw in ["RESOURCE_EXHAUSTED", "429", "503", "UNAVAILABLE"])
                api_key_manager.record_key_failure(current_key, is_quota_error=is_quota)
                print(f"⚠️ Lỗi tổng hợp câu trả lời với key {key_info.name} (lượt {attempt+1}/{attempts_limit}): {error_msg[:150]}")
        
        if not answer:
            # Fallback: Ghép key points lại
            answer = f"Based on multiple sources:\n\n"
            for i, item in enumerate(key_points_list, 1):
                answer += f"From {item['filename']}: {item['key_points']}\n\n"
        
        return answer
    
    def ask_multi_document(
        self, 
        question: str, 
        documents: List,
        use_synthesis: bool = True
    ) -> Tuple[str, List[Dict]]:
        """
        Hỏi câu hỏi với multi-document QA
        
        Args:
            question: Câu hỏi
            documents: List documents đã được retrieve và rerank
            use_synthesis: Có tổng hợp hay không (False = chỉ list key points)
        
        Returns:
            (answer, key_points_list)
        """
        print(f"\n📚 Multi-document QA với {len(documents)} documents")
        
        # Nhóm theo nguồn
        grouped = self.group_documents_by_source(documents)
        print(f"📂 Từ {len(grouped)} tài liệu khác nhau:")
        for filename, docs in grouped.items():
            print(f"   - {filename}: {len(docs)} chunks")
        
        # Trích xuất key points
        print("\n🔍 Đang trích xuất key points từ mỗi document...")
        key_points_list = self.extract_key_points_per_document(documents, question)
        
        # Loại bỏ trùng lặp
        print("🧹 Đang loại bỏ thông tin trùng lặp...")
        unique_points = self.remove_duplicate_information(key_points_list)
        print(f"✅ Còn lại {len(unique_points)} nguồn unique")
        
        if use_synthesis:
            # Tổng hợp câu trả lời
            print("\n🔄 Đang tổng hợp câu trả lời từ nhiều nguồn...")
            answer = self.synthesize_answer(question, unique_points)
        else:
            # Chỉ list key points
            answer = "Key points from multiple sources:\n\n"
            for i, item in enumerate(unique_points, 1):
                filename = item['filename']
                page = item['page']
                answer += f"{i}. From {filename} (Page {page}):\n"
                answer += f"   {item['key_points']}\n\n"
        
        return answer, unique_points
    
    def format_multi_document_citations(self, key_points_list: List[Dict]) -> List[Dict]:
        """
        Format citations cho multi-document QA
        
        Returns:
            List of citation dicts
        """
        citations = []
        
        for i, item in enumerate(key_points_list, 1):
            citation = {
                'index': i,
                'filename': item['filename'],
                'page': item['page'],
                'slide': item.get('slide'),
                'content': item['content'][:800] + ("..." if len(item['content']) > 800 else ""),
                'key_points': item['key_points'],
                'full_source': item['full_source'],
                'relevance_score': item.get('relevance_score')
            }
            citations.append(citation)
        
        return citations

def ask_question_multi_document(
    chain, 
    retriever, 
    question: str,
    conversation_context: str = "",
    use_rerank: bool = True,
    use_multi_doc: bool = True
) -> Tuple[str, List, List[Dict]]:
    """
    Wrapper function để hỏi câu hỏi với multi-document QA
    
    Args:
        chain: QA chain
        retriever: Document retriever
        question: Câu hỏi
        conversation_context: Context từ lịch sử
        use_rerank: Sử dụng reranking
        use_multi_doc: Sử dụng multi-document synthesis
    
    Returns:
        (answer, source_docs, citations)
    """
    from rag import detect_language, translate_text
    
    # Phát hiện ngôn ngữ
    input_language = detect_language(question)
    
    # Nếu có context, thêm vào câu hỏi
    if conversation_context:
        question_with_context = f"{conversation_context}\n\nCurrent question: {question}"
    else:
        question_with_context = question
    
    # Dịch sang tiếng Anh nếu cần
    if input_language == "Vietnamese":
        print("🌐 Đang dịch câu hỏi sang tiếng Anh...")
        question_en = translate_text(question_with_context, "English")
        print(f"📝 Câu hỏi tiếng Anh: {question_en}")
    else:
        question_en = question_with_context
    
    # Retrieve documents
    print("🔍 Đang retrieve documents...")
    if hasattr(retriever, 'invoke'):
        initial_docs = retriever.invoke(question_en, k=10)
    else:
        initial_docs = retriever.get_relevant_documents(question_en)[:10]
    
    print(f"📊 Retrieved {len(initial_docs)} documents")
    
    # Rerank nếu cần
    if use_rerank and len(initial_docs) > 3:
        from reranker import create_reranker
        
        reranker = create_reranker(method="hybrid")
        scored_docs = reranker.rerank(question_en, initial_docs, top_k=5)
        scored_docs = reranker.filter_irrelevant(scored_docs, threshold=0.3)
        
        source_docs = [doc for doc, score in scored_docs]
        
        # Lưu scores vào metadata
        for i, (doc, score) in enumerate(scored_docs):
            doc.metadata['relevance_score'] = score
    else:
        source_docs = initial_docs[:5]
    
    print(f"✅ Sử dụng {len(source_docs)} documents")
    
    # Multi-document QA
    if use_multi_doc and len(source_docs) > 1:
        multi_qa = MultiDocumentQA()
        answer, key_points_list = multi_qa.ask_multi_document(
            question_en, 
            source_docs,
            use_synthesis=True
        )
        
        # Format citations
        citations = multi_qa.format_multi_document_citations(key_points_list)
    else:
        # Fallback: Dùng cách cũ
        from rag import ask_question
        answer, source_docs, citations = ask_question(
            chain, retriever, question,
            conversation_context=conversation_context,
            use_rerank=use_rerank
        )
        return answer, source_docs, citations
    
    # Dịch về tiếng Việt nếu cần
    if input_language == "Vietnamese":
        print("🌐 Đang dịch câu trả lời về tiếng Việt...")
        answer = translate_text(answer, "Vietnamese")
    
    return answer, source_docs, citations

if __name__ == "__main__":
    # Test multi-document QA
    from embed_store import load_vector_store, load_documents
    from rag import create_qa_chain
    
    print("📦 Đang load RAG pipeline...")
    vectordb = load_vector_store("chroma_db")
    
    try:
        documents = load_documents("chroma_db")
        qa_chain, retriever = create_qa_chain(vectordb, documents=documents, use_hybrid=True)
    except:
        qa_chain, retriever = create_qa_chain(vectordb, use_hybrid=False)
    
    print("✅ Đã load pipeline")
    
    # Test question
    question = "What are the main clustering algorithms?"
    
    print(f"\n❓ Câu hỏi: {question}")
    
    answer, sources, citations = ask_question_multi_document(
        qa_chain,
        retriever,
        question,
        use_multi_doc=True
    )
    
    print("\n" + "="*80)
    print("📝 CÂU TRẢ LỜI:")
    print("="*80)
    print(answer)
    
    print("\n" + "="*80)
    print("📚 NGUỒN TÀI LIỆU:")
    print("="*80)
    for citation in citations:
        print(f"\n{citation['index']}. {citation['filename']} - Trang {citation['page']}")
        print(f"   Key points: {citation['key_points'][:100]}...")
