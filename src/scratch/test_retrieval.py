# scratch/test_retrieval.py
import sys
import os
import asyncio

# Add project root to sys.path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.stdout.reconfigure(encoding='utf-8', errors='replace')

from embed_store import load_vector_store, load_documents
from rag import create_qa_chain, analyze_and_route_query, detect_syllabus_question
from backend_api import get_allowed_filenames

async def run_test():
    print("Loading vector database...")
    vectordb = load_vector_store("chroma_db_new")
    documents = load_documents("chroma_db_new")
    
    print("Creating QA chain...")
    chain, retriever = create_qa_chain(vectordb, documents=documents, use_hybrid=True)
    
    user_id = "default"  # check default user allowed files
    allowed_files = get_allowed_filenames(user_id)
    security_filter = {"source": {"$in": allowed_files}}
    
    test_questions = [
        "Thuật toán Cây quyết định (Decision Tree)",
        "Thuật toán Naive Bayes",
        "Làm thế nào để chia tập dữ liệu thành tập huấn luyện (train) và tập kiểm tra (test) trong Python? Cho tôi xem code mẫu"
    ]
    
    data_dir = "data"
    all_files = os.listdir(data_dir) if os.path.exists(data_dir) else []
    
    for q in test_questions:
        print("\n" + "="*50)
        print(f"QUESTION: {q}")
        print("="*50)
        
        # Router analysis
        routing_info = analyze_and_route_query(q)
        print(f"Routing Info: {routing_info}")
        
        target_patterns = routing_info.get("target_file_pattern", [])
        
        # Build metadata filter
        metadata_filter = security_filter
        if target_patterns and len(target_patterns) > 0:
            resolved_files = []
            for pattern in target_patterns:
                pattern_lower = pattern.lower().strip()
                for f in all_files:
                    if pattern_lower in f.lower():
                        resolved_files.append(f)
                        resolved_files.append(f"data/{f}")
                        resolved_files.append(f"data\\{f}")
                        resolved_files.append(os.path.abspath(os.path.join(data_dir, f)))
            if not resolved_files:
                resolved_files = target_patterns
                
            new_filter = {"source": {"$in": resolved_files}}
            metadata_filter = {"$and": [security_filter, new_filter]}
            
        print(f"Resolved Metadata Filter: {metadata_filter}")
        
        expanded_queries = routing_info.get("expanded_queries", [q])
        print(f"Expanded Queries: {expanded_queries}")
        
        for eq in expanded_queries:
            print(f"\n--- Retrieving for: '{eq}' ---")
            try:
                docs = retriever.invoke(eq, k=5, filter=metadata_filter)
                print(f"Retrieved {len(docs)} documents.")
                for idx, doc in enumerate(docs[:3], 1):
                    print(f"  [{idx}] Source: {doc.metadata.get('source')} | File: {doc.metadata.get('source_file')} | Page: {doc.metadata.get('page')}")
                    print(f"      Snippet: {doc.page_content[:120]}...")
            except Exception as e:
                print(f"Error: {e}")

if __name__ == "__main__":
    asyncio.run(run_test())
