"""Quick rebuild of BM25 index from documents.pkl"""
import os, pickle, time
os.environ['KMP_DUPLICATE_LIB_OK'] = 'True'

from rank_bm25 import BM25Okapi

DOCS_PATH = "chroma_db_new/documents.pkl"
BM25_PATH = "chroma_db_new/bm25_index.pkl"

print("1. Loading documents...")
t0 = time.time()
with open(DOCS_PATH, 'rb') as f:
    documents = pickle.load(f)
print(f"   Loaded {len(documents)} documents in {time.time()-t0:.1f}s")

print("2. Tokenizing documents for BM25...")
t0 = time.time()
def tokenize(text):
    import re
    # Simple word tokenization for Vietnamese + English
    return re.findall(r'\b\w+\b', text.lower())

tokenized_docs = [tokenize(doc.page_content) for doc in documents]
print(f"   Tokenized {len(tokenized_docs)} docs in {time.time()-t0:.1f}s")

print("3. Creating BM25 index...")
t0 = time.time()
bm25 = BM25Okapi(tokenized_docs)
print(f"   BM25 index created in {time.time()-t0:.1f}s")

print("4. Saving BM25 index...")
t0 = time.time()
with open(BM25_PATH, 'wb') as f:
    pickle.dump({'bm25': bm25, 'documents': documents}, f)
print(f"   Saved to {BM25_PATH} in {time.time()-t0:.1f}s")

# Quick test
print("5. Testing BM25...")
test_tokens = tokenize("decision tree code")
scores = bm25.get_scores(test_tokens)
non_zero = sum(1 for s in scores if s > 0)
print(f"   Non-zero scores for 'decision tree code': {non_zero}/{len(scores)}")
print("DONE!")
