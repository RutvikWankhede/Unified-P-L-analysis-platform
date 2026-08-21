import re

with open('frontend_v2/forecast.html', 'r', encoding='utf-8') as f:
    text = f.read()

# 1. Replace sidebar
text = re.sub(r'<aside.*?</aside>', '<div id="sidebar-container"></div>', text, flags=re.DOTALL)

# 2. Add scripts to body
if 'js/shell.js' not in text:
    text = text.replace('</body>', '<script type="module" src="js/shell.js"></script>\n<script type="module" src="js/forecast_wiring.js"></script>\n</body>')

# 3. Strip inline script for chart
text = re.sub(r'<script data-purpose="canvas-setup">.*?</script>', '', text, flags=re.DOTALL)

# 4. Inject KPI IDs
text = text.replace('₹2.46 Cr', '<span id="kpi-forecast-profit">₹2.46 Cr</span>')
text = text.replace('92%</p>', '<span id="kpi-model-confidence">92%</span></p>')
text = text.replace('May 18, 2025</p>', '<span id="kpi-model-date">May 18, 2025</span></p>')

# 5. Inject Chart ID (it already has id='chart-container' and id='forecastSplineChart', but I'll add the new aggregations HTML)
chart_tools_html = '''
<div class="flex bg-gray-100 p-0.5 rounded-lg" id="chart-aggregations">
    <button class="px-4 py-1 text-[10px] font-bold text-text-secondary hover:bg-white rounded-md transition-all" data-agg="daily">Daily</button>
    <button class="px-4 py-1 text-[10px] font-bold text-text-secondary hover:bg-white rounded-md transition-all" data-agg="weekly">Weekly</button>
    <button class="px-4 py-1 text-[10px] font-bold bg-brand text-white rounded-md" data-agg="monthly">Monthly</button>
    <button class="px-4 py-1 text-[10px] font-bold text-text-secondary hover:bg-white rounded-md transition-all" data-agg="quarterly">Quarterly</button>
</div>
<div class="flex bg-gray-100 p-0.5 rounded-lg ml-2">
    <button class="px-3 py-1 text-[10px] font-bold text-text-secondary hover:bg-white rounded-md" id="btn-zoom-in">+</button>
    <button class="px-3 py-1 text-[10px] font-bold text-text-secondary hover:bg-white rounded-md" id="btn-zoom-out">-</button>
    <button class="px-3 py-1 text-[10px] font-bold text-text-secondary hover:bg-white rounded-md" id="btn-expand">[ ]</button>
</div>
'''

text = re.sub(r'<div class="flex bg-gray-100 p-0\.5 rounded-lg">\s*<button class="px-4 py-1 text-\[10px\] font-bold bg-brand text-white rounded-md">Chart</button>\s*<button class="px-4 py-1 text-\[10px\] font-bold text-text-secondary">Table</button>\s*</div>', chart_tools_html, text)

# 6. Add Scenario Projections
scenarios_html = '''
<!-- BEGIN: Scenario Projections -->
<section class="col-span-12 bg-white p-6 rounded-custom border border-border-light shadow-sm mt-6">
    <h3 class="text-sm font-bold text-gray-900 mb-6">Scenario Projections</h3>
    <div class="grid grid-cols-3 gap-6" id="scenario-container">
        <!-- Best Case -->
        <div class="p-4 border border-green-200 bg-green-50 rounded-lg">
            <p class="text-[11px] font-bold text-green-700 uppercase mb-2">Best Case</p>
            <h4 class="text-xl font-bold text-green-900" id="scenario-best">₹3.10 Cr</h4>
            <p class="text-xs text-green-600 mt-1">High growth, optimal conditions</p>
        </div>
        <!-- Expected Case -->
        <div class="p-4 border border-brand/30 bg-blue-50 rounded-lg">
            <p class="text-[11px] font-bold text-brand uppercase mb-2">Expected Case</p>
            <h4 class="text-xl font-bold text-slate-900" id="scenario-expected">₹2.46 Cr</h4>
            <p class="text-xs text-slate-500 mt-1">Baseline trajectory</p>
        </div>
        <!-- Worst Case -->
        <div class="p-4 border border-red-200 bg-red-50 rounded-lg">
            <p class="text-[11px] font-bold text-red-700 uppercase mb-2">Worst Case</p>
            <h4 class="text-xl font-bold text-red-900" id="scenario-worst">₹1.80 Cr</h4>
            <p class="text-xs text-red-600 mt-1">Market downturn</p>
        </div>
    </div>
</section>
<!-- END: Scenario Projections -->
'''
text = text.replace('<!-- Bottom Panels Grid -->', scenarios_html + '\n<!-- Bottom Panels Grid -->')

with open('frontend_v2/forecast.html', 'w', encoding='utf-8') as f:
    f.write(text)

print('Updated forecast.html')
