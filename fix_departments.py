import os
import re

file_path = r"c:\Users\HP\.gemini\antigravity-ide\scratch\P&L system\unified-pl-system\frontend_v2\departments.html"

with open(file_path, 'r', encoding='utf-8') as f:
    content = f.read()

# 1. Global Spacing & Layout
content = content.replace('class="ml-[260px] flex-1 p-8"', 'class="ml-[260px] flex-1 px-6 py-4"')
content = content.replace('mb-8', 'mb-4')
content = content.replace('gap-6', 'gap-4')

# 2. Page Header
header_old_regex = r'<header class="flex items-center justify-between mb-4">\s*<div>\s*<h1 class="text-2xl font-bold text-slate-900">Department Analysis</h1>\s*<p class="text-sm text-slate-500">Analyze department-wise performance</p>\s*</div>\s*</header>'

header_new = """<header class="flex items-center justify-between mb-4">
<div>
<h1 class="text-2xl font-bold text-slate-900">Department Analysis</h1>
<p class="text-sm text-slate-500">Analyze financial performance by department</p>
</div>
<div class="flex items-center gap-3">
    <div class="bg-white border border-slate-200 rounded px-2 py-1 flex items-center text-xs font-medium shadow-sm">
        <select class="bg-transparent border-none focus:ring-0 p-0 text-xs font-medium text-slate-700 outline-none">
            <option>All Departments</option>
            <option>Finance</option>
            <option>Sales</option>
            <option>IT</option>
            <option>Marketing</option>
            <option>HR</option>
        </select>
    </div>
    <div class="bg-white border border-slate-200 rounded px-3 py-1 flex items-center text-xs font-medium shadow-sm text-slate-700 cursor-pointer">
        May 13 - May 19, 2025
        <svg class="w-3 h-3 ml-2 text-slate-400" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path d="M19 9l-7 7-7-7" stroke-linecap="round" stroke-linejoin="round" stroke-width="2"></path></svg>
    </div>
</div>
</header>"""
content = re.sub(header_old_regex, header_new, content, flags=re.DOTALL)

# 3. KPI Cards padding and icon sizes
content = content.replace('p-6 rounded-card', 'p-4 rounded-card')
content = content.replace('w-10 h-10', 'w-8 h-8')
content = content.replace('w-6 h-6', 'w-4 h-4')
content = content.replace('text-xl font-bold', 'text-lg font-bold')

# 4. Main Analytics Row: Add "Profit / Rev" to Left Panel (Profit by Department)
left_panel_header_old_regex = r'<div class="flex items-center justify-between mb-4">\s*<h4 class="font-bold text-slate-800">Profit by Department</h4>\s*<svg.*?</svg>\s*</div>'
left_panel_header_new = """<div class="flex items-center justify-between mb-4">
<h4 class="font-bold text-slate-800 text-sm">Profit by Department</h4>
<div class="flex items-center border border-slate-200 rounded text-[10px] font-medium overflow-hidden">
    <button class="px-2 py-0.5 bg-slate-100 text-slate-800 border-r border-slate-200">Profit</button>
    <button class="px-2 py-0.5 text-slate-500 hover:bg-slate-50">Rev</button>
</div>
</div>"""
content = re.sub(left_panel_header_old_regex, left_panel_header_new, content, flags=re.DOTALL)

# Right Panel (Department Trend) header font size
content = content.replace('<h4 class="font-bold text-slate-800">Department Trend (Profit)</h4>', '<h4 class="font-bold text-slate-800 text-sm">Department Trend (Profit)</h4>')

# 5. Bottom Section
content = content.replace('py-4', 'py-2')
content = content.replace('pb-4', 'pb-2')
content = content.replace('<h4 class="font-bold text-slate-800">Department Summary Table</h4>', '<h4 class="font-bold text-slate-800 text-sm">Department Summary Table</h4>')
content = content.replace('<h4 class="font-bold text-slate-800 mb-4">Top Performers</h4>', '<h4 class="font-bold text-slate-800 text-sm mb-4">Top Performers</h4>')
content = content.replace('<h4 class="font-bold text-slate-800 mb-6">Top Performers</h4>', '<h4 class="font-bold text-slate-800 text-sm mb-4">Top Performers</h4>')

# Write back
with open(file_path, 'w', encoding='utf-8') as f:
    f.write(content)

print("Modifications applied successfully.")
