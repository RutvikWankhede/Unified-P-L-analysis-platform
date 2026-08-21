import os
import re

html_files = [f for f in os.listdir('frontend_v2') if f.endswith('.html')]

replacements = {
    'bg-[var(--bg-canvas)]': 'bg-slate-50',
    'bg-[var(--bg-surface)]': 'bg-white',
    'bg-[var(--bg-card)]': 'bg-white',
    'bg-[var(--bg-surface-hover)]': 'bg-slate-50',
    'text-[var(--text-primary)]': 'text-slate-900',
    'text-[var(--text-secondary)]': 'text-slate-600',
    'text-[var(--text-muted)]': 'text-slate-500',
    'border-[var(--border-subtle)]': 'border-slate-200',
    'text-[var(--accent-primary)]': 'text-blue-600',
    'bg-[var(--accent-primary)]': 'bg-blue-600',
    'border-[var(--accent-primary)]': 'border-blue-600',
    'text-[var(--success)]': 'text-emerald-500',
    'bg-[var(--success)]': 'bg-emerald-500',
    'border-[var(--success)]': 'border-emerald-500',
    'text-[var(--danger)]': 'text-rose-500',
    'bg-[var(--danger)]': 'bg-rose-500',
    'border-[var(--danger)]': 'border-rose-500',
    'text-warning': 'text-amber-500',
    'text-danger': 'text-rose-500',
}

for file in html_files:
    path = os.path.join('frontend_v2', file)
    with open(path, 'r', encoding='utf-8') as f:
        content = f.read()
    
    # Remove old css links
    content = re.sub(r'<link rel="stylesheet" href="\./styles/.*\.css">\n?', '', content)
    
    for old, new in replacements.items():
        content = content.replace(old, new)
        
    with open(path, 'w', encoding='utf-8') as f:
        f.write(content)

print("CSS replacement complete.")
