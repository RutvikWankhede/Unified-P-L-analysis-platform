import re

with open('stitch_reference/reports.html', 'r', encoding='utf-8') as f:
    text = f.read()

new_chart = '''
<div class="flex items-center gap-4 mb-4">
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
</div>
<div class="h-[240px] w-full relative" id="chart-container">
    <canvas class="w-full h-full" id="reportsSplineChart"></canvas>
</div>
'''

text = re.sub(r'<!-- Simulated Spline Chart with SVG -->.*?</svg>', new_chart, text, flags=re.DOTALL)

with open('stitch_reference/reports.html', 'w', encoding='utf-8') as f:
    f.write(text)

print('Updated reports.html to use canvas')
