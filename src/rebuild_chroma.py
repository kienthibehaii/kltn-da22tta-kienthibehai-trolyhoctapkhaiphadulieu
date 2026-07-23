"""Quick rebuild of ChromaDB vectors from existing documents.pkl"""
import os
import pickle
import shutil
os.environ['KMP_DUPLICATE_LIB_OK'] = 'True'

from embed_store import create_vector_store, get_embeddings

DOCS_PATH = "chroma_db_new/documents.pkl"
CHROMA_DIR = "chroma_db_new"

print("1. Loading documents from documents.pkl...")
with open(DOCS_PATH, 'rb') as f:
    documents = pickle.load(f)
print(f"   Loaded {len(documents)} documents")

print("2. Removing old empty ChromaDB...")
for item in os.listdir(CHROMA_DIR):
    item_path = os.path.join(CHROMA_DIR, item)
    if os.path.isdir(item_path) and item != "documents.pkl" and item != "bm25_index.pkl":
        try:
            if os.path.exists(item_path):
                shutil.rmtree(item_path)
                print(f"   Removed {item}")
        except Exception as e:
            print(f"   Could not remove {item}: {e}")
# Also remove chroma.sqlite3
sqlite_path = os.path.join(CHROMA_DIR, "chroma.sqlite3")
if os.path.exists(sqlite_path):
    os.remove(sqlite_path)
    print("   Removed chroma.sqlite3")

print("3. Creating new vector store with all documents...")
vectordb = create_vector_store(documents, persist_directory=CHROMA_DIR)
count = vectordb._collection.count()
print(f"DONE: Vector store has {count} vectors now!")
