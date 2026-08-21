import re

def process_dashboard(html):
    # KPIs
    html = html.replace('<p class="text-5xl font-bold">96', '<p class="text-5xl font-bold" id="kpi-health-score">96')
    html = html.replace('<p class="text-xl font-bold mb-3">₹5.32 Cr</p>', '<p class="text-xl font-bold mb-3" id="kpi-total-revenue">₹5.32 Cr</p>')
    html = html.replace('<p class="text-xl font-bold mb-3">₹3.11 Cr</p>', '<p class="text-xl font-bold mb-3" id="kpi-total-expense">₹3.11 Cr</p>')
    html = html.replace('<p class="text-xl font-bold mb-3">₹2.21 Cr</p>', '<p class="text-xl font-bold mb-3" id="kpi-net-profit">₹2.21 Cr</p>')
    html = html.replace('<p class="text-xl font-bold mb-3">₹2.46 Cr</p>', '<p class="text-xl font-bold mb-3" id="kpi-forecasted-profit">₹2.46 Cr</p>')

    # Chart
    # mainChart already has id="mainChart", we can keep it or add chart-revenue-expense
    html = html.replace('id="mainChart"', 'id="chart-revenue-expense"')

    # Table body
    html = html.replace('<tbody class="divide-y divide-outline-variant/10">', '<tbody class="divide-y divide-outline-variant/10" id="dept-table-body">')

    # Add data-row-template to first row, remove others
    # This is tricky with simple replace. Let's do a regex for table rows.
    tbody_start = html.find('id="dept-table-body"')
    if tbody_start != -1:
        tbody_end = html.find('</tbody>', tbody_start)
        tbody_content = html[tbody_start:tbody_end]
        
        # find all <tr>
        trs = [m.start() for m in re.finditer(r'<tr', tbody_content)]
        if len(trs) > 1:
            # keep first tr, make it template
            first_tr_end = tbody_content.find('</tr>') + 5
            first_tr = tbody_content[trs[0]:first_tr_end].replace('<tr', '<tr data-row-template="true"')
            html = html[:tbody_start] + tbody_content[:trs[0]] + first_tr + '\n' + html[tbody_end:]

    # AI Panels
    html = html.replace('<div class="space-y-4 flex-1">', '<div class="space-y-4 flex-1" id="ai-insights-container">')
    # Make first insight a template
    ai_start = html.find('id="ai-insights-container"')
    if ai_start != -1:
        ai_end = html.find('</div>\n<button', ai_start)
        ai_content = html[ai_start:ai_end]
        divs = [m.start() for m in re.finditer(r'<div class="p-3 bg-surface-container-low rounded-xl flex gap-3">', ai_content)]
        if len(divs) > 1:
            first_div_end = ai_content.find('</div>', ai_content.find('</div>', divs[0]+1)+1) + 6
            first_div = ai_content[divs[0]:first_div_end].replace('<div', '<div data-row-template="true"')
            html = html[:ai_start] + ai_content[:divs[0]] + first_div + '\n' + html[ai_end:]

    # Recent Uploads
    html = html.replace('<div class="space-y-4">', '<div class="space-y-4" id="recent-uploads-container">', 1)
    
    # Workflow Status
    workflow_idx = html.find('Workflow Status')
    if workflow_idx != -1:
        # find the next space-y-4
        target_idx = html.find('<div class="space-y-4">', workflow_idx)
        if target_idx != -1:
            html = html[:target_idx] + '<div class="space-y-4" id="workflow-status-container">' + html[target_idx+len('<div class="space-y-4">'):]

    # JS Injection
    js_to_inject = """
<script>
document.addEventListener('DOMContentLoaded', () => {
    // Fetch summary
    fetch('/api/pl/summary')
        .then(r => r.json())
        .then(data => {
            const sum = data.total_summary || {};
            if(sum.revenue) document.getElementById('kpi-total-revenue').innerText = `₹${(sum.revenue/10000000).toFixed(2)} Cr`;
            if(sum.expense) document.getElementById('kpi-total-expense').innerText = `₹${(sum.expense/10000000).toFixed(2)} Cr`;
            if(sum.profit) document.getElementById('kpi-net-profit').innerText = `₹${(sum.profit/10000000).toFixed(2)} Cr`;
            if(data.health_score) document.getElementById('kpi-health-score').innerText = data.health_score;
            if(data.forecasted_profit) document.getElementById('kpi-forecasted-profit').innerText = `₹${(data.forecasted_profit/10000000).toFixed(2)} Cr`;
        });
        
    // Example fetch departments
    fetch('/api/pl/summary')
        .then(r => r.json())
        .then(data => {
            const tbody = document.getElementById('dept-table-body');
            const template = tbody.querySelector('[data-row-template="true"]');
            if(template && data.domains) {
                tbody.innerHTML = '';
                data.domains.forEach(d => {
                    const clone = template.cloneNode(true);
                    clone.removeAttribute('data-row-template');
                    clone.style.display = '';
                    const td = clone.querySelectorAll('td');
                    if(td.length >= 4) {
                        td[0].querySelector('span.font-semibold').innerText = d.domain || 'N/A';
                        td[1].innerText = `${(d.revenue/10000000).toFixed(2)} Cr`;
                        td[2].innerText = `${(d.expense/10000000).toFixed(2)} Cr`;
                        td[3].innerText = `${(d.profit/10000000).toFixed(2)} Cr`;
                    }
                    tbody.appendChild(clone);
                });
            }
        });
});
</script>
"""
    html = html.replace('</body>', js_to_inject + '</body>')
    return html

import sys
file_path = sys.argv[1]
with open(file_path, 'r', encoding='utf-8') as f:
    content = f.read()

if 'dashboard' in file_path:
    content = process_dashboard(content)

with open(file_path, 'w', encoding='utf-8') as f:
    f.write(content)
print(f"Processed {file_path}")
