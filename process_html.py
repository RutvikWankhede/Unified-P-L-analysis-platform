import os
import shutil
import re

files = ['anomalies.html', 'copilot.html', 'workflow.html', 'reports.html', 'audit.html', 'settings.html']
wiring_map = {
    'anomalies.html': 'anomalies_wiring.js',
    'copilot.html': 'copilot_wiring.js',
    'workflow.html': 'workflow_wiring.js',
    'reports.html': 'reports_wiring.js',
    'audit.html': 'audit_wiring.js',
    'settings.html': 'settings_wiring.js'
}

os.makedirs('stitch_reference', exist_ok=True)

for f in files:
    src = f'frontend_v2/{f}'
    dst = f'stitch_reference/{f}'
    shutil.copy(src, dst)
    
    with open(src, 'r', encoding='utf-8') as file:
        text = file.read()
    
    # 1. Replace sidebar
    text = re.sub(r'<aside.*?</aside>', '<div id="sidebar-container"></div>', text, flags=re.DOTALL)
    
    # 2. Add shell.js and specific wiring file if not present
    wiring_js = wiring_map.get(f)
    if 'js/shell.js' not in text:
        text = text.replace('</body>', f'<script type="module" src="js/shell.js"></script>\n</body>')
    if wiring_js and wiring_js not in text:
        text = text.replace('</body>', f'<script type="module" src="js/{wiring_js}"></script>\n</body>')
        
    # 3. Add table body id
    text = re.sub(r'<tbody[^>]*>', lambda m: m.group(0) if 'id=' in m.group(0) else m.group(0)[:-1] + ' id="' + f.split('.')[0] + '-table-body\">', text)
    
    # 4. Inject specific IDs if missing (we will do this manually for specific pages if needed, but table body is generally enough to start)
    
    # 5. Remove any local canvas setup scripts to enforce backend wiring
    text = re.sub(r'<script data-purpose="canvas-setup">.*?</script>', '', text, flags=re.DOTALL)
    text = re.sub(r'<script data-purpose="chart-rendering">.*?</script>', '', text, flags=re.DOTALL)
    
    with open(src, 'w', encoding='utf-8') as file:
        file.write(text)

print('Updated all HTML files successfully!')
