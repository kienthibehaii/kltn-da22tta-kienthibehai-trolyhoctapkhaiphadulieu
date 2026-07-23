"""
rebuild_vectorstore.py - Rebuild ChromaDB tu dau

Dung:
    python rebuild_vectorstore.py
    python rebuild_vectorstore.py --force
"""
import os, shutil, sys, time

TARGET_DIR = "chroma_db_new"

def backup_old(d):
    bk = d + "_backup"
    if os.path.exists(bk): shutil.rmtree(bk, ignore_errors=True)
    if os.path.exists(d):
        try: shutil.copytree(d, bk); print(f"Da backup sang {bk}")
        except Exception as e: print(f"Khong the backup: {e}")

def delete_old(d):
    if not os.path.exists(d): return
    try:
        shutil.rmtree(d); print(f"Da xoa {d}")
    except PermissionError:
        tmp = d + f"_old_{int(time.time())}"
        try:
            os.rename(d, tmp)
            print(f"File bi lock => doi ten sang: {tmp}")
            print("  Xoa thu muc do sau khi dung backend.")
        except Exception as e:
            print(f"Khong the xoa/rename: {e}\n  => Hay dung backend truoc.")
            sys.exit(1)

def rebuild(d):
    from config import USE_SEMANTIC_CHUNKING
    from loader import load_all_documents
    from embed_store import create_vector_store
    print("\nDang doc tai lieu tu data/ ...")
    chunks = load_all_documents("data", use_semantic_chunking=USE_SEMANTIC_CHUNKING)
    if not chunks: print("Khong co tai lieu!"); sys.exit(1)
    print(f"Tong chunks: {len(chunks)}")
    print("Dang embedding va luu ChromaDB...")
    vdb = create_vector_store(chunks, persist_directory=d)
    print(f"\nHOAN TAT  |  Vectors={vdb._collection.count()}  Chunks={len(chunks)}  Dir={d}")
    print("BM25 index se tu dong tao khi backend khoi dong.")

if __name__ == "__main__":
    if "--force" not in sys.argv:
        from config import EMBEDDING_MODEL_NAME
        print(f"Target: {TARGET_DIR}\nModel : {EMBEDDING_MODEL_NAME}")
        if input("Tiep tuc? (y/n): ").strip().lower() != "y":
            sys.exit(0)
    backup_old(TARGET_DIR)
    delete_old(TARGET_DIR)
    rebuild(TARGET_DIR)
