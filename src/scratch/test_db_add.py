import os
import sys

# Add parent path to import local modules
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

# Ensure UTF-8 output on Windows
sys.stdout.reconfigure(encoding='utf-8')

from loader import load_all_documents
from embed_store import get_embeddings
from langchain_community.vectorstores import Chroma

print("📚 Step 1: Loading documents...")
chunks = load_all_documents("data", use_semantic_chunking=False)
# Test with only first 10 chunks to see if it works or fails
test_chunks = chunks[:10]

print("🎨 Step 2: Getting embedding model...")
embeddings = get_embeddings()

print("🔧 Step 3: Instantiating Chroma DB...")
db = Chroma(persist_directory="chroma_db_test", embedding_function=embeddings)
print("✅ Chroma DB instantiated successfully!")

print("➕ Step 4: Adding 10 test documents...")
try:
    db.add_documents(test_chunks)
    print("✅ Successfully added documents!")
except Exception as e:
    import traceback
    print("❌ Failed adding documents:")
    traceback.print_exc()
