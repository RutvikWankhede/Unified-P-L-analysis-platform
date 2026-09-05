import os
import re

frontend_dir = 'frontend_v2'
unified_dir = os.path.join('unified-pl-system', 'frontend_v2')

def clean_page(filepath, src_content=None):
    if src_content is None:
        if not os.path.exists(filepath):
            return
        with open(filepath, 'r', encoding='utf-8', errors='ignore') as f:
            content = f.read()
    else:
        content = src_content

    # 1. Remove legacy hardcoded sidebars
    content = re.sub(r'<!-- BEGIN: Sidebar -->.*?<!-- END: Sidebar -->', '<div id="sidebar-container"></div>', content, flags=re.DOTALL)
    content = re.sub(r'<aside[^>]*>.*?</aside>', '<div id="sidebar-container"></div>', content, flags=re.DOTALL)
    content = re.sub(r'<div class="sidebar" id="sidebar">.*?</div>\s*</div>', '<div id="sidebar-container"></div>', content, flags=re.DOTALL)

    # 2. Ensure only ONE sidebar-container
    containers = content.count('<div id="sidebar-container"></div>')
    if containers > 1:
        # replace all but the first
        first_idx = content.find('<div id="sidebar-container"></div>')
        after = content[first_idx + len('<div id="sidebar-container"></div>'):]
        after = after.replace('<div id="sidebar-container"></div>', '')
        content = content[:first_idx + len('<div id="sidebar-container"></div>')] + after
    elif containers == 0:
        content = re.sub(r'(<body[^>]*>)', r'\1\n    <div id="sidebar-container"></div>', content, count=1, flags=re.IGNORECASE)

    # 3. Ensure sidebar.css in head
    if 'sidebar.css' not in content:
        content = re.sub(r'(</head>)', r'    <link rel="stylesheet" href="css/sidebar.css">\n\1', content, count=1, flags=re.IGNORECASE)

    # 4. Ensure shell.js before </body>
    if 'shell.js' not in content:
        content = re.sub(r'(</body>)', r'    <script type="module" src="js/shell.js"></script>\n\1', content, count=1, flags=re.IGNORECASE)

    # 5. Remove any leftover window.location.replace redirects to pl_dashboard / pl_forecast
    content = re.sub(r"<script>window\.location\.replace\('(?:pl_dashboard\.html|pl_forecast\.html)'\);</script>", "", content)

    with open(filepath, 'w', encoding='utf-8') as f:
        f.write(content)
    print(f"Updated: {filepath}")

# 1. Base Dashboard
dash_src = os.path.join(unified_dir, 'pl_dashboard.html')
dash_content = open(dash_src, encoding='utf-8').read()
clean_page(os.path.join(frontend_dir, 'pl_dashboard.html'), dash_content)
clean_page(os.path.join(frontend_dir, 'dashboard.html'), dash_content)

# 2. Forecast
fc_src = os.path.join(frontend_dir, 'pl_forecast.html')
fc_content = open(fc_src, encoding='utf-8').read()
clean_page(os.path.join(frontend_dir, 'pl_forecast.html'), fc_content)
clean_page(os.path.join(frontend_dir, 'forecast.html'), fc_content)

# 3. Anomalies
anom_src = os.path.join(unified_dir, 'anomalies.html')
anom_content = open(anom_src, encoding='utf-8').read()
clean_page(os.path.join(frontend_dir, 'anomalies.html'), anom_content)

# 4. Datasets & Upload
datasets_path = os.path.join(frontend_dir, 'datasets.html')
clean_page(datasets_path)
with open(datasets_path, encoding='utf-8') as f:
    datasets_content = f.read()
clean_page(os.path.join(frontend_dir, 'upload.html'), datasets_content)

# 5. Other target pages
pages = ['departments.html', 'copilot.html', 'workflow.html', 'reports.html', 'audit.html', 'settings.html']
for p in pages:
    clean_page(os.path.join(frontend_dir, p))

# Also sync other existing secondary pages in frontend_v2 so all pages share the sidebar
secondary = ['about.html', 'ai-insights.html', 'analytics.html', 'dataset-quality.html', 'executive.html',
             'export.html', 'financial-health.html', 'help.html', 'notifications.html', 'pivot.html',
             'profile.html', 'recommendations.html', 'schema-mapping.html', 'users.html', 'validation.html']
for p in secondary:
    clean_page(os.path.join(frontend_dir, p))

print("All pages successfully updated in frontend_v2!")
