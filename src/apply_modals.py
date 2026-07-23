
import json
data = json.load(open('extracted_modals.json', encoding='utf-8'))
calls = [c for group in data if group for c in group if c and c.get('name') == 'multi_replace_file_content']
chunks = calls[0]['args']['ReplacementChunks']
if isinstance(chunks, str):
    chunks = json.loads(chunks)

content = open(r'frontend\src\components\QuizTab.tsx', encoding='utf-8').read()
for chunk in chunks:
    target = chunk['TargetContent']
    replacement = chunk['ReplacementContent']
    if target in content:
        content = content.replace(target, replacement)
    else:
        print('Target not found:', repr(target[:50]))

open(r'frontend\src\components\QuizTab.tsx', 'w', encoding='utf-8').write(content)
print('Done QuizTab')
