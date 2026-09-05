import os
import re

file_path = r"c:\Users\HP\.gemini\antigravity-ide\scratch\P&L system\frontend_v2\dashboard.html"

with open(file_path, 'r', encoding='utf-8') as f:
    content = f.read()

# 1. Global Spacing & Layout
content = content.replace('px-8 space-y-8', 'px-6 space-y-4')
content = content.replace('h-16 glass-effect border-b border-outline-variant/20 flex items-center justify-between px-8', 'h-14 glass-effect border-b border-outline-variant/20 flex items-center justify-between px-6')
content = content.replace('<section class="p-8 pb-0">', '<section class="px-6 py-4">')
content = content.replace('grid-cols-12 gap-6', 'grid-cols-12 gap-4')

# 2. KPI Row
content = content.replace('bg-white rounded-card p-6 shadow-sm border border-outline-variant/20 flex items-center justify-between', 'bg-white rounded-card p-4 shadow-sm border border-outline-variant/20 flex items-center justify-between')
content = content.replace('w-32 h-32', 'w-20 h-20')
content = content.replace('text-5xl', 'text-3xl')
content = content.replace('text-2xl text-on-surface-variant font-normal', 'text-xl text-on-surface-variant font-normal')
content = content.replace('col-span-8 grid grid-cols-5 gap-4', 'col-span-8 grid grid-cols-5 gap-3')
content = content.replace('p-5', 'p-4')
content = content.replace('w-9 h-9', 'w-7 h-7')
content = content.replace('text-lg font-bold mb-2', 'text-base font-bold mb-1')

# 3. Main Chart Area and others (padding reduction)
content = content.replace('p-6 shadow-sm', 'p-4 shadow-sm')
content = content.replace('h-64', 'h-48')
content = content.replace('w-28 h-28', 'w-20 h-20')

# Make list items more compact
content = content.replace('p-3 bg-surface-container-low', 'p-2 bg-surface-container-low')
content = content.replace('p-3 border border-outline-variant/10', 'p-2 border border-outline-variant/10')
content = content.replace('p-3 hover:bg-surface-container-low', 'p-2 hover:bg-surface-container-low')
content = content.replace('w-10 h-10', 'w-8 h-8')
content = content.replace('py-4', 'py-2')

# Text sizes in insights
content = content.replace('text-xs text-on-surface-variant leading-relaxed', 'text-[11px] text-on-surface-variant leading-tight')

# Write back
with open(file_path, 'w', encoding='utf-8') as f:
    f.write(content)

print("Modifications applied successfully.")
