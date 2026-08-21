import os
import re

file_path = r"C:\Users\HP\.gemini\antigravity-ide\scratch\P&L system\frontend_v2\dashboard.html"

with open(file_path, 'r', encoding='utf-8') as f:
    html = f.read()

# Inject KPIs
html = html.replace('?5.32 Cr</p>', '?5.32 Cr</p>').replace(
    '<p class="text-xl font-bold mb-3">?5.32 Cr</p>',
    '<p id="kpi-total-revenue" class="text-xl font-bold mb-3">?5.32 Cr</p>'
)

html = html.replace(
    '<p class="text-xl font-bold mb-3">?3.11 Cr</p>',
    '<p id="kpi-total-expense" class="text-xl font-bold mb-3">?3.11 Cr</p>'
)

html = html.replace(
    '<p class="text-xl font-bold mb-3">?2.21 Cr</p>',
    '<p id="kpi-net-profit" class="text-xl font-bold mb-3">?2.21 Cr</p>'
)

html = html.replace(
    '<p class="text-xl font-bold mb-3">?2.46 Cr</p>',
    '<p id="kpi-forecasted-profit" class="text-xl font-bold mb-3">?2.46 Cr</p>'
)

html = re.sub(
    r'<p class="text-xl font-bold mb-3">92\s*<span class="text-on-surface-variant font-normal">/100</span></p>',
    '<p id="kpi-health-score" class="text-xl font-bold mb-3">92 <span class="text-on-surface-variant font-normal">/100</span></p>',
    html
)

# Inject table body ID
# The table body usually comes after </thead>
html = html.replace('<tbody class="divide-y divide-outline-variant/20">', '<tbody id="dept-table-body" class="divide-y divide-outline-variant/20">')

# Inject data-row-template on the first row
# Find the first <tr class="hover:bg-surface-container-low transition-colors group"> after tbody
html = re.sub(
    r'(<tbody id="dept-table-body"[^>]*>\s*)<tr class="hover:bg-surface-container-low transition-colors group">',
    r'\1<tr data-row-template="true" class="hover:bg-surface-container-low transition-colors group">',
    html,
    count=1
)

with open(file_path, 'w', encoding='utf-8') as f:
    f.write(html)
print("Injected IDs into dashboard.html")
