import re, os
files = ['dashboard.html', 'departments.html', 'datasets.html', 'anomalies.html', 'reports.html', 'copilot.html', 'workflow.html']
for f in files:
    path = os.path.join('frontend_v2', f)
    if not os.path.exists(path): continue
    content = open(path, encoding='utf-8').read()
    
    # Strip <aside> ... </aside>
    # In some files it's enclosed in <!-- BEGIN: Sidebar --> ... <!-- END: Sidebar -->
    content = re.sub(r'<!-- BEGIN: Sidebar -->.*?<!-- END: Sidebar -->', '<div id="sidebar-container"></div>', content, flags=re.DOTALL)
    
    # Also catch <aside> directly if not enclosed
    content = re.sub(r'<aside id="sidebar".*?</aside>', '<div id="sidebar-container"></div>', content, flags=re.DOTALL)
    
    # Ensure shell.js is imported
    if 'src="js/shell.js"' not in content:
        content = content.replace('</body>', '    <script type="module" src="js/shell.js"></script>\n</body>')
        
    open(path, 'w', encoding='utf-8').write(content)
print('Done updating sidebars')
