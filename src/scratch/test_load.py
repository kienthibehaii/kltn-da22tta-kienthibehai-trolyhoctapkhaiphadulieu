import os
import sys

# Add parent directory to sys.path to find local modules
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

# Ensure UTF-8 output on Windows
sys.stdout.reconfigure(encoding='utf-8')

from loader import load_pdf, load_ppt, load_docx, clean_text

data_folder = "data"
print("="*60)
print(f"ANALYZE DATA FOLDER: {data_folder}")
print("="*60)

for filename in os.listdir(data_folder):
    file_path = os.path.join(data_folder, filename)
    if filename.endswith(".pdf"):
        try:
            docs = load_pdf(file_path)
            print(f"✅ Success: {filename} - {len(docs)} pages")
        except Exception as e:
            print(f"❌ Failed: {filename} - Error: {e}")
    elif filename.endswith(".pptx"):
        try:
            docs = load_ppt(file_path)
            print(f"✅ Success: {filename} - {len(docs)} slides")
        except Exception as e:
            print(f"❌ Failed: {filename} - Error: {e}")
    elif filename.endswith(".docx"):
        try:
            docs = load_docx(file_path)
            print(f"✅ Success: {filename} - {len(docs)} documents nodes")
        except Exception as e:
            print(f"❌ Failed: {filename} - Error: {e}")
    else:
        print(f"ℹ️ Skipped non-matching file: {filename}")
