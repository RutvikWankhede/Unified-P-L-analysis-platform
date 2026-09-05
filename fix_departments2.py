import os
import re

file_path = r"c:\Users\HP\.gemini\antigravity-ide\scratch\P&L system\unified-pl-system\frontend_v2\departments.html"

with open(file_path, 'r', encoding='utf-8') as f:
    content = f.read()

# Fix the left panel header specifically
left_panel_regex = r'<div class="flex items-center justify-between mb-[0-9]+">\s*<h4 class="font-bold text-slate-800">Profit by Department</h4>\s*<svg.*?</svg>\s*</div>'

left_panel_new = """<div class="flex items-center justify-between mb-4">
<h4 class="font-bold text-slate-800 text-sm">Profit by Department</h4>
<div class="flex items-center border border-slate-200 rounded text-[10px] font-medium overflow-hidden">
    <button class="px-2 py-0.5 bg-slate-100 text-slate-800 border-r border-slate-200">Profit</button>
    <button class="px-2 py-0.5 text-slate-500 hover:bg-slate-50">Rev</button>
</div>
</div>"""

content = re.sub(left_panel_regex, left_panel_new, content, flags=re.DOTALL)

with open(file_path, 'w', encoding='utf-8') as f:
    f.write(content)

print("Second pass modifications applied successfully.")
