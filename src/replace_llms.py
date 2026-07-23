import re

with open('rag.py', 'r', encoding='utf-8') as f:
    content = f.read()

# Replace ChatGoogleGenerativeAI( ... ) spanning multiple lines
pattern = r'ChatGoogleGenerativeAI\([^)]*\)'
content = re.sub(pattern, 'get_llm(task_type="general")', content)

if 'from llm_router import get_llm' not in content:
    content = 'from llm_router import get_llm\n' + content

with open('rag.py', 'w', encoding='utf-8') as f:
    f.write(content)

print('Replaced successfully')
