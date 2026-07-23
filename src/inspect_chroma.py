import os
from embed_store import load_vector_store

persist_dir = os.path.abspath('chroma_db_new')
vectordb = load_vector_store(persist_dir)
print('COUNT=', vectordb._collection.count())
results = vectordb.similarity_search('khai phá dữ liệu', k=3)
for i, doc in enumerate(results, 1):
    print(f'--- DOC {i} ---')
    print(doc.page_content[:1200])
    print('METADATA=', doc.metadata)
    print()
