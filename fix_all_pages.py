"""
Batch fix script: inject missing scripts into all HTML pages
"""
import os
import re

base = r'c:\Users\HP\.gemini\antigravity-ide\scratch\P&L system\frontend_v2'

ECHARTS_SCRIPT = '<script src="https://cdn.jsdelivr.net/npm/echarts@5.5.0/dist/echarts.min.js"></script>'
SHELL_SCRIPT = '<script type="module" src="js/shell.js"></script>'
SIDEBAR_DIV = '<div id="sidebar-container"></div>'

def get_wiring_script(page):
    mapping = {
        'departments.html': 'js/departments_wiring.js',
        'copilot.html': 'js/copilot_wiring.js',
        'workflow.html': 'js/workflow_wiring.js',
        'audit.html': 'js/audit_wiring.js',
        'settings.html': 'js/settings_wiring.js',
    }
    return mapping.get(page)

fixes = {
    'departments.html': {
        'need_echarts': True,
        'need_wiring': 'js/departments_wiring.js',
    },
    'datasets.html': {
        'need_echarts': True,
    },
    'reports.html': {
        'need_echarts': True,
    },
    'forecast.html': {
        'need_sidebar': True,
        'need_shell': True,
    },
    'copilot.html': {
        'need_echarts': True,
        'need_wiring': 'js/copilot_wiring.js',
    },
    'workflow.html': {
        'need_echarts': True,
        'need_wiring': 'js/workflow_wiring.js',
    },
    'audit.html': {
        'need_echarts': True,
        'need_wiring': 'js/audit_wiring.js',
        'need_sidebar': True,
        'need_shell': True,
    },
    'settings.html': {
        'need_wiring': 'js/settings_wiring.js',
    },
}

for page, needed in fixes.items():
    path = os.path.join(base, page)
    content = open(path, 'r', encoding='utf-8').read()
    original = content

    # Step 1: Add sidebar div if needed
    if needed.get('need_sidebar') and 'id="sidebar-container"' not in content:
        # Insert after <body ...>
        content = re.sub(r'(<body[^>]*>)', r'\1\n<div id="sidebar-container"></div>', content, count=1)
        print(f'  [{page}] Added sidebar-container div')

    # Step 2: Build the block of scripts to inject before </body>
    inject_lines = []

    if needed.get('need_echarts') and 'echarts.min.js' not in content:
        inject_lines.append(ECHARTS_SCRIPT)
    if needed.get('need_shell') and 'shell.js' not in content:
        inject_lines.append(SHELL_SCRIPT)
    if needed.get('need_wiring'):
        wiring_src = needed['need_wiring']
        if wiring_src not in content:
            inject_lines.append(f'<script type="module" src="{wiring_src}"></script>')

    if inject_lines:
        inject_block = '\n    '.join(inject_lines)
        # Find </body> and insert just before it
        content = re.sub(r'(</body>)', f'    {inject_block}\n\\1', content, count=1)
        print(f'  [{page}] Injected: {inject_lines}')

    if content != original:
        with open(path, 'w', encoding='utf-8') as f:
            f.write(content)
        print(f'  [{page}] SAVED')
    else:
        print(f'  [{page}] No changes needed')

print('\nDone.')
