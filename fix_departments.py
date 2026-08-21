import re

with open('frontend_v2/js/departments.js', 'r', encoding='utf-8') as f:
    txt = f.read()

# Replace the treemap block
pattern = r"(?s)// 1\. Department Contribution \(Treemap/Donut\) from /charts.*?</div>`;\n }"
replacement = """// 1. Department Contribution (Horizontal Bar Chart)
 const summaryData = await api.get('/departments/summary');
 window.deptSummaryData = summaryData; // store for re-rendering
 renderDeptContributionChart();
 
 const metricSelect = document.getElementById('dept-contrib-metric');
 const scopeSelect = document.getElementById('dept-contrib-scope');
 if (metricSelect) metricSelect.addEventListener('change', renderDeptContributionChart);
 if (scopeSelect) scopeSelect.addEventListener('change', renderDeptContributionChart);"""
txt = re.sub(pattern, replacement, txt)

# Remove the appended functions if they exist (to append cleanly)
txt = re.sub(r'(?s)\n+function updateDeptTrendBadges.*?$', '', txt)
txt = re.sub(r'(?s)\n+function renderDeptContributionChart.*?$', '', txt)

# Append the functions properly
txt += """

function updateDeptTrendBadges(allSeries) {
    // Generate trend badges based on trend data
    const badgesContainer = document.getElementById('dept-trend-badges');
    if (!badgesContainer) return;
    badgesContainer.innerHTML = '';
}

function renderDeptContributionChart() {
    const chartDom = document.getElementById('chart-dept-contribution');
    if (!chartDom) return;
    
    let data = window.deptSummaryData || [];
    if (!data.length) {
        chartDom.innerHTML = `<div class="flex h-full items-center justify-center text-slate-400">No Data Available</div>`;
        return;
    }
    
    const metric = document.getElementById('dept-contrib-metric')?.value || 'profit';
    let scope = document.getElementById('dept-contrib-scope')?.value || 'all';
    
    // Sort descending by metric
    data = [...data].sort((a, b) => b[metric] - a[metric]);
    
    // Filter scope
    if (scope !== 'all') {
        data = data.slice(0, parseInt(scope));
    }
    
    // Reverse for ECharts horizontal bar (draws from bottom up)
    data.reverse();
    
    const departments = data.map(d => d.department);
    const values = data.map(d => d[metric]);
    
    const colors = {
        profit: '#10b981', // emerald
        revenue: '#3b82f6', // blue
        expense: '#ef4444', // red
        margin: '#8b5cf6'  // violet
    };
    
    const myChart = initEchart(chartDom);
    const option = {
        tooltip: {
            trigger: 'axis',
            axisPointer: { type: 'shadow' },
            formatter: function (params) {
                const val = params[0].value;
                const fmt = metric === 'margin' ? val.toFixed(1) + '%' : window.formatCurrency(val);
                return `<b>${params[0].name}</b><br/>${params[0].marker} ${metric.charAt(0).toUpperCase() + metric.slice(1)}: ${fmt}`;
            }
        },
        grid: { left: '3%', right: '4%', bottom: '3%', top: '5%', containLabel: true },
        xAxis: { 
            type: 'value',
            splitLine: { lineStyle: { color: '#f1f5f9', type: 'dashed' } },
            axisLabel: { 
                formatter: metric === 'margin' ? '{value}%' : (v) => formatCurrencyShort(v),
                color: '#64748b'
            }
        },
        yAxis: { 
            type: 'category', 
            data: departments,
            axisLabel: { color: '#475569', fontWeight: '500' },
            axisLine: { show: false },
            axisTick: { show: false }
        },
        series: [{
            type: 'bar',
            data: values,
            itemStyle: { 
                color: colors[metric] || '#3b82f6',
                borderRadius: [0, 4, 4, 0]
            },
            label: {
                show: true,
                position: 'right',
                formatter: (p) => metric === 'margin' ? p.value.toFixed(1) + '%' : formatCurrencyShort(p.value),
                color: '#64748b',
                fontSize: 10
            }
        }]
    };
    
    safeSetOption(myChart, option, true);
    
    // Update insight text
    const insightText = document.getElementById('dept-contrib-insight-text');
    if (insightText && data.length > 0) {
        const topDept = data[data.length - 1]; // last one is the highest because we reversed
        const metricName = metric === 'margin' ? 'Margin' : metric.charAt(0).toUpperCase() + metric.slice(1);
        const fmt = metric === 'margin' ? topDept[metric].toFixed(1) + '%' : formatCurrencyShort(topDept[metric]);
        insightText.innerHTML = `<strong>${topDept.department}</strong> leads in ${metricName} with <strong>${fmt}</strong>.`;
    }
}
"""

with open('frontend_v2/js/departments.js', 'w', encoding='utf-8') as f:
    f.write(txt)
print("Done")
