import os
import re

out_dir = r"C:\Users\HP\.gemini\antigravity-ide\scratch\P&L system\frontend_v2"

for filename in os.listdir(out_dir):
    if not filename.endswith('.html'): continue
    filepath = os.path.join(out_dir, filename)
    with open(filepath, 'r', encoding='utf-8') as f:
        html = f.read()

    def replace_nl_in_d(match):
        d_val = match.group(2).replace('\n', ' ').replace('\r', '')
        return f'<path{match.group(1)}d="{d_val}"'
        
    html = re.sub(r'<path([^>]*?)d="([^"]*?)"', replace_nl_in_d, html)

    with open(filepath, 'w', encoding='utf-8') as f:
        f.write(html)
        
print("SVG path newlines fixed with spaces.")
