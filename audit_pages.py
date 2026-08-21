import os
base = r'c:\Users\HP\.gemini\antigravity-ide\scratch\P&L system\frontend_v2'
pages = ['dashboard.html','departments.html','datasets.html','anomalies.html','reports.html',
         'forecast.html','copilot.html','workflow.html','audit.html','settings.html']
sid_key = 'id="sidebar-container"'
for p in pages:
    path = os.path.join(base, p)
    content = open(path, 'r', encoding='utf-8').read()
    echarts = 'echarts.min.js' in content
    wiring = '_wiring.js' in content
    sidebar = sid_key in content
    shell = 'shell.js' in content
    print(f'{p} | echarts={echarts} | wiring={wiring} | sidebar={sidebar} | shell={shell}')
