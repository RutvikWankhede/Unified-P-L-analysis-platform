import re
import sys

def process_dashboard(html):
    # 1. Inject IDs for KPIs
    html = re.sub(r'<p class="text-5xl font-bold">96 <span', '<p class="text-5xl font-bold" id="kpi-health-score">96 <span', html)
    html = re.sub(r'<p class="text-xl font-bold mb-3">₹5\.32 Cr</p>', '<p class="text-xl font-bold mb-3" id="kpi-total-revenue">₹5.32 Cr</p>', html)
    html = re.sub(r'<p class="text-xl font-bold mb-3">₹3\.11 Cr</p>', '<p class="text-xl font-bold mb-3" id="kpi-total-expense">₹3.11 Cr</p>', html)
    html = re.sub(r'<p class="text-xl font-bold mb-3">₹2\.21 Cr</p>', '<p class="text-xl font-bold mb-3" id="kpi-net-profit">₹2.21 Cr</p>', html)
    html = re.sub(r'<p class="text-xl font-bold mb-3">₹2\.46 Cr</p>', '<p class="text-xl font-bold mb-3" id="kpi-forecasted-profit">₹2.46 Cr</p>', html)

    # 2. Inject ID for Chart
    html = html.replace('id="mainChart"', 'id="chart-revenue-expense"')

    # 3. Inject ID for Table Body and template row
    tbody_pattern = r'(<tbody class="divide-y divide-outline-variant/10">)'
    html = re.sub(tbody_pattern, r'\1\n<!-- Template Row -->', html)
    html = html.replace('<tbody class="divide-y divide-outline-variant/10">', '<tbody class="divide-y divide-outline-variant/10" id="dept-table-body">')
    
    # We will just mark the first <tr> after dept-table-body
    parts = html.split('id="dept-table-body">\n<!-- Template Row -->\n<tr>')
    if len(parts) == 2:
        html = parts[0] + 'id="dept-table-body">\n<tr data-row-template="true">' + parts[1]

    # 4. Inject ID for AI panels
    html = html.replace('<div class="space-y-4 flex-1">', '<div class="space-y-4 flex-1" id="ai-insights-container">')
    parts = html.split('id="ai-insights-container">\n<div class="p-3 bg-surface-container-low')
    if len(parts) == 2:
        html = parts[0] + 'id="ai-insights-container">\n<div data-row-template="true" class="p-3 bg-surface-container-low' + parts[1]

    # Anomaly overview
    html = html.replace('<div class="flex-1 pl-6 space-y-2">', '<div class="flex-1 pl-6 space-y-2" id="anomaly-overview-container">')

    # Recent Uploads
    ru_header = '<h3 class="font-bold text-base">Recent Uploads</h3>'
    idx = html.find(ru_header)
    if idx != -1:
        next_div = html.find('<div class="space-y-4">', idx)
        if next_div != -1:
            html = html[:next_div] + '<div class="space-y-4" id="recent-uploads-container">' + html[next_div+len('<div class="space-y-4">'):]
            # template for uploads
            parts = html.split('id="recent-uploads-container">\n<!-- Upload Item 1 -->\n<div class="flex items-center')
            if len(parts) == 2:
                html = parts[0] + 'id="recent-uploads-container">\n<!-- Upload Item 1 -->\n<div data-row-template="true" class="flex items-center' + parts[1]

    # Workflow Status
    ws_header = '<h3 class="font-bold text-base">Workflow Status</h3>'
    idx = html.find(ws_header)
    if idx != -1:
        next_div = html.find('<div class="space-y-4">', idx)
        if next_div != -1:
            html = html[:next_div] + '<div class="space-y-4" id="workflow-status-container">' + html[next_div+len('<div class="space-y-4">'):]
            parts = html.split('id="workflow-status-container">\n<!-- Workflow Item 1 -->\n<div class="group flex items-center')
            if len(parts) == 2:
                html = parts[0] + 'id="workflow-status-container">\n<!-- Workflow Item 1 -->\n<div data-row-template="true" class="group flex items-center' + parts[1]

    # Inject Script Tag
    if '<script src="js/dashboard_wiring.js"></script>' not in html:
        html = html.replace('</body>', '<script src="js/dashboard_wiring.js"></script>\n</body>')
    return html

def process_departments(html):
    # IDs for Department Page specific things
    # Department KPIs
    html = re.sub(r'<p class="text-3xl font-bold mt-1">₹14\.2 Cr</p>', '<p class="text-3xl font-bold mt-1" id="kpi-total-revenue">₹14.2 Cr</p>', html)
    html = re.sub(r'<p class="text-3xl font-bold mt-1">₹8\.5 Cr</p>', '<p class="text-3xl font-bold mt-1" id="kpi-total-expense">₹8.5 Cr</p>', html)
    html = re.sub(r'<p class="text-3xl font-bold mt-1">₹5\.7 Cr</p>', '<p class="text-3xl font-bold mt-1" id="kpi-net-profit">₹5.7 Cr</p>', html)
    html = re.sub(r'<p class="text-3xl font-bold mt-1">40\.1%</p>', '<p class="text-3xl font-bold mt-1" id="kpi-health-score">40.1%</p>', html)

    # Chart
    html = html.replace('id="revenueExpenseChart"', 'id="chart-department-profit"')
    html = html.replace('id="budgetUtilizationChart"', 'id="chart-department-trend"')

    # Table
    html = html.replace('<tbody class="divide-y divide-outline-variant/10">', '<tbody class="divide-y divide-outline-variant/10" id="dept-table-body">')
    parts = html.split('id="dept-table-body">\n<tr class="hover:bg-surface-container-lowest transition-colors group">')
    if len(parts) == 2:
        html = parts[0] + 'id="dept-table-body">\n<tr data-row-template="true" class="hover:bg-surface-container-lowest transition-colors group">' + parts[1]
    
    # Inject Script Tag
    if '<script src="js/departments_wiring.js"></script>' not in html:
        html = html.replace('</body>', '<script src="js/departments_wiring.js"></script>\n</body>')
    return html

if __name__ == "__main__":
    file_path = sys.argv[1]
    with open(file_path, 'r', encoding='utf-8') as f:
        content = f.read()

    if 'dashboard' in file_path:
        content = process_dashboard(content)
    elif 'department' in file_path:
        content = process_departments(content)

    with open(file_path, 'w', encoding='utf-8') as f:
        f.write(content)
    print(f"Processed {file_path}")
