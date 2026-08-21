import re

with open('frontend_v2/js/departments.js', 'r', encoding='utf-8') as f:
    txt = f.read()

# Replace updateChart definition
pattern = r"(?s)const updateChart = \(\) => \{.*?safeSetOption\(myChart, option, true\);\n\s*\};"
replacement = """const updateChart = () => {
    const activeSeries = allSeries.filter(s => selectedDepts.has(s.name));
    
    // Update dynamic badges above chart
    const badgesContainer = document.getElementById('dept-trend-badges');
    if (badgesContainer) {
        badgesContainer.innerHTML = activeSeries.map(s => {
            // Find color in series.itemStyle.color or generate one based on index
            const colors = ['#3b82f6', '#10b981', '#f59e0b', '#ef4444', '#8b5cf6', '#06b6d4', '#f43f5e', '#84cc16'];
            const idx = allSeries.findIndex(a => a.name === s.name);
            const color = colors[idx % colors.length];
            // Assign color to series if not present
            s.itemStyle = s.itemStyle || {};
            s.itemStyle.color = color;
            s.lineStyle = s.lineStyle || {};
            s.lineStyle.color = color;
            
            return `<span class="flex items-center gap-1.5"><span class="w-2 h-2 rounded-full" style="background-color: ${color}"></span> ${s.name}</span>`;
        }).join('');
    }
    
    const option = {
        tooltip: { 
            trigger: 'axis',
            axisPointer: { type: 'cross', label: { backgroundColor: '#6a7985' } },
            formatter: function (params) {
                let html = `<b>${params[0].axisValue}</b><br/>`;
                params.forEach(p => {
                    html += `${p.marker} ${p.seriesName}: <b>${window.formatCurrencyShort ? window.formatCurrencyShort(p.value) : p.value}</b><br/>`;
                });
                return html;
            }
        },
        legend: { show: false }, // Using custom UI instead
        grid: { left: '3%', right: '4%', bottom: '12%', top: '20px', containLabel: true },
        xAxis: { type: 'category', boundaryGap: false, data: dataTrend.periods, axisLabel: { color: '#64748b', fontSize: 11 } },
        yAxis: { type: 'value', axisLabel: { color: '#64748b', fontSize: 11, formatter: (val) => window.formatCurrencyShort ? window.formatCurrencyShort(val) : val }, splitLine: { lineStyle: { color: '#f1f5f9' } } },
        dataZoom: [
            { type: 'inside', start: 0, end: 100 },
            { type: 'slider', start: 0, end: 100, bottom: 5 }
        ],
        series: activeSeries
    };
    safeSetOption(myChart, option, true);
};"""

txt = re.sub(pattern, replacement, txt)

with open('frontend_v2/js/departments.js', 'w', encoding='utf-8') as f:
    f.write(txt)
print("Done")
