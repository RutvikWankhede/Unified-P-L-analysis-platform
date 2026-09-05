import re
import os

base_dir = r"c:\Users\HP\.gemini\antigravity-ide\scratch\P&L system\unified-pl-system\frontend_v2"

# 1. Update pl_dashboard.html
dash_path = os.path.join(base_dir, "pl_dashboard.html")
with open(dash_path, "r", encoding="utf-8") as f:
    dash = f.read()

# Inject stylesheet
if "design-system.css" not in dash:
    dash = dash.replace('<link rel="stylesheet" href="css/sidebar.css">', '<link rel="stylesheet" href="css/sidebar.css">\n    <link rel="stylesheet" href="css/design-system.css">')

# Update row 1 grid (KPIs) to be 2-col or wider grid. The reference has a wider first card.
# The user said: "Dashboard top stat cards: too cramped, small text. Reference has larger cards, more padding, 2-col or wider grid."
# Let's replace the grid-cols-6 with grid-cols-12 and make them col-span-2 (for 6 cards) or 4+2x4? The reference has 6 cards. Let's make it a flex wrap or a grid-cols-12 where each is col-span-2.
dash = dash.replace('<section class="grid grid-cols-6 gap-4">', '<section class="grid grid-cols-12 gap-[var(--ds-grid-gap)]">')

kpi_pattern = re.compile(r'<div class="col-span-1 bg-white rounded-\[12px\] shadow-sm border border-outline-variant/20 p-4 flex flex-col justify-between">', re.DOTALL)
dash = kpi_pattern.sub('<div class="col-span-2 ds-card flex flex-col justify-between">', dash)
dash = dash.replace('text-xl font-bold text-slate-800', 'ds-stat')
dash = dash.replace('text-[10px] font-bold uppercase tracking-wider', 'ds-label')

with open(dash_path, "w", encoding="utf-8") as f:
    f.write(dash)


# 2. Update departments.html
dept_path = os.path.join(base_dir, "departments.html")
with open(dept_path, "r", encoding="utf-8") as f:
    dept = f.read()

if "design-system.css" not in dept:
    dept = dept.replace('<link rel="stylesheet" href="css/sidebar.css">', '<link rel="stylesheet" href="css/sidebar.css">\n    <link rel="stylesheet" href="css/design-system.css">')

# Update KPI cards
dept = dept.replace('<section class="grid grid-cols-4 gap-4 mb-4">', '<section class="grid grid-cols-4 gap-[var(--ds-grid-gap)] mb-[var(--ds-grid-gap)]">')
dept = dept.replace('bg-white p-4 rounded-card border border-card-border custom-shadow', 'ds-card')
dept = dept.replace('text-lg font-bold', 'ds-stat')
dept = dept.replace('text-xs text-slate-400', 'ds-label')
dept = dept.replace('gap-4 mb-4', 'gap-[var(--ds-grid-gap)] mb-[var(--ds-grid-gap)]') # general grid gaps

# Fix Dept bars: replace hardcoded HTML with echarts container
html_bars_pattern = re.compile(r'<div class="space-y-4">.*?</div>\s*<button', re.DOTALL)
new_bars = '<div id="chart-dept-contribution" style="width:100%;height:var(--ds-chart-height-std);"></div>\n<button'
dept = html_bars_pattern.sub(new_bars, dept)

# Update Trend chart height
dept = dept.replace('height:240px;', 'height:var(--ds-chart-height-std);')

with open(dept_path, "w", encoding="utf-8") as f:
    f.write(dept)


# 3. Update pl_dashboard_wiring.js
dash_js_path = os.path.join(base_dir, "js", "pl_dashboard_wiring.js")
with open(dash_js_path, "r", encoding="utf-8") as f:
    dash_js = f.read()

# Fix Line chart: grid bottom 15%, width/thickness, max 3 series
dash_js = dash_js.replace("grid: { left: '2%', right: '2%', bottom: '5%', top: '30px', containLabel: true }", "grid: { left: '5%', right: '5%', bottom: '15%', top: '30px', containLabel: true }")
dash_js = dash_js.replace("axisLabel: { fontSize: 10 }", "axisLabel: { fontSize: 11, rotate: 45, interval: 'auto' }")
dash_js = dash_js.replace("smooth: true,", "smooth: true, lineStyle: { width: 4 },")
dash_js = dash_js.replace("height:256px;", "height:400px;")

with open(dash_js_path, "w", encoding="utf-8") as f:
    f.write(dash_js)


# 4. Update departments_wiring.js
dept_js_path = os.path.join(base_dir, "js", "departments_wiring.js")
with open(dept_js_path, "r", encoding="utf-8") as f:
    dept_js = f.read()

# Fix trend chart: max 4 series, thicker lines
dept_js = dept_js.replace("const series = Object.entries(trendData).map(([dept, pts], i) => ({", "const series = Object.entries(trendData).slice(0, 4).map(([dept, pts], i) => ({")
dept_js = dept_js.replace("lineStyle: { width: 2 }", "lineStyle: { width: 4 }")
dept_js = dept_js.replace("grid: { left: '3%', right: '4%', bottom: '15%', containLabel: true }", "grid: { left: '3%', right: '4%', bottom: '20%', containLabel: true }")
dept_js = dept_js.replace("Object.keys(trendData).map", "Object.keys(trendData).slice(0, 4).map")

with open(dept_js_path, "w", encoding="utf-8") as f:
    f.write(dept_js)

print("Files updated")
