import os

file_path = r'c:\Users\HP\.gemini\antigravity-ide\scratch\P&L system\frontend_v2\department.html'
with open(file_path, 'r', encoding='utf-8') as f:
    content = f.read()

content = content.replace('""', '"')

with open(file_path, 'w', encoding='utf-8') as f:
    f.write(content)
print('Fixed quotes in department.html')
