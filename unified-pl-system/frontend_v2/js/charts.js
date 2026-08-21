const ECHARTS_COMMON = {
 backgroundColor: 'transparent',
 textStyle: {
 fontFamily: 'Inter, system-ui, sans-serif'
 },
 tooltip: {
 trigger: 'axis',
 backgroundColor: 'var(--bg-surface)',
 borderColor: 'var(--border-subtle)',
 textStyle: { color: 'var(--text-primary)' },
 padding: 12,
 borderRadius: 8,
 shadowBlur: 20,
 shadowColor: 'rgba(0,0,0,0.2)'
 }
};

let activeCharts = [];

window.addEventListener('resize', () => {
 activeCharts.forEach(c => c && c.resize());
});

/**
 * safeInit — like echarts.init() but schedules a resize on the next frame
 * if the container has zero dimensions at init time (the chart race condition).
 */
function safeInit(container) {
    const chart = safeInit(container);
    if (container.offsetWidth === 0 || container.offsetHeight === 0) {
        requestAnimationFrame(() => { try { chart.resize(); } catch (_) {} });
    }
    activeCharts.push(chart);
    return chart;
}

/**
 * safeSetOption — sets option and forces a resize on the next frame so that
 * charts initialised with zero dimensions re-measure once laid out.
 */
function safeSetOption(chart, option, notMerge = false) {
    if (!chart) return;
    chart.setOption(option, notMerge);
    requestAnimationFrame(() => { try { chart.resize(); } catch (_) {} });
}

export function renderDualLineChart(containerId, chartsResult) {
 const container = document.getElementById(containerId);
 if (!container || !window.echarts || !chartsResult) return null;
 
 const chart = safeInit(container);
 
 const option = {
 ...ECHARTS_COMMON,
 color: ['#0066FF', '#FF3B30'],
 legend: {
 data: ['Revenue', 'Expense'],
 textStyle: { color: 'var(--text-secondary)' },
 bottom: 0
 },
 grid: { top: 30, right: 10, bottom: 40, left: 60 },
 xAxis: {
 type: 'category',
 data: chartsResult.revenue_trend.map(d => d.period),
 axisLine: { lineStyle: { color: 'var(--border-subtle)' } },
 axisLabel: { color: 'var(--text-secondary)' }
 },
 yAxis: {
 type: 'value',
 splitLine: { lineStyle: { color: 'var(--border-subtle)', type: 'dashed' } },
 axisLabel: { 
 color: 'var(--text-secondary)',
 formatter: (value) => new Intl.NumberFormat('en-US', { notation: 'compact' }).format(value)
 }
 },
 series: [
 {
 name: 'Revenue',
 type: 'line',
 smooth: true,
 data: chartsResult.revenue_trend.map(d => d.value),
 lineStyle: { width: 3 },
 symbol: 'none'
 },
 {
 name: 'Expense',
 type: 'line',
 smooth: true,
 data: chartsResult.expense_trend.map(d => d.value),
 lineStyle: { width: 3 },
 symbol: 'none'
 }
 ]
 };
 
 chart.setOption(option);
 activeCharts.push(chart);
 return chart;
}

export function renderWaterfallChart(containerId, data) {
 const container = document.getElementById(containerId);
 if (!container || !window.echarts || !data || !data.length) return null;
 
 const chart = safeInit(container);
 
 // Transform data for ECharts waterfall
 // Usually waterfall requires a transparent 'base' series
 let baseData = [];
 let posData = [];
 let negData = [];
 
 let currentBase = 0;
 
 data.forEach(item => {
 if (item.type === 'revenue' || item.type === 'profit') {
 baseData.push(0);
 posData.push(item.value);
 negData.push('-');
 currentBase = item.value;
 } else if (item.type === 'expense') {
 baseData.push(currentBase - item.value);
 posData.push('-');
 negData.push(item.value);
 currentBase -= item.value;
 } else {
 baseData.push(0);
 posData.push(item.value);
 negData.push('-');
 }
 });

 const option = {
 ...ECHARTS_COMMON,
 grid: { top: 30, right: 10, bottom: 20, left: 60 },
 xAxis: {
 type: 'category',
 data: data.map(d => d.name),
 axisLine: { lineStyle: { color: 'var(--border-subtle)' } },
 axisLabel: { color: 'var(--text-secondary)' }
 },
 yAxis: {
 type: 'value',
 splitLine: { lineStyle: { color: 'var(--border-subtle)', type: 'dashed' } },
 axisLabel: { 
 color: 'var(--text-secondary)',
 formatter: (value) => new Intl.NumberFormat('en-US', { notation: 'compact' }).format(value)
 }
 },
 series: [
 {
 name: 'Base',
 type: 'bar',
 stack: 'Total',
 itemStyle: { color: 'transparent' },
 data: baseData
 },
 {
 name: 'Positive',
 type: 'bar',
 stack: 'Total',
 itemStyle: { color: 'var(--success)' },
 data: posData
 },
 {
 name: 'Negative',
 type: 'bar',
 stack: 'Total',
 itemStyle: { color: 'var(--danger)' },
 data: negData
 }
 ]
 };
 
 chart.setOption(option);
 activeCharts.push(chart);
 return chart;
}

export function renderDonutChart(containerId, departmentBreakdown) {
 const container = document.getElementById(containerId);
 if (!container || !window.echarts || !departmentBreakdown) return null;
 
 const chart = safeInit(container);
 
 const data = departmentBreakdown.map(d => ({
 name: d.department,
 value: d.expense
 })).sort((a,b) => b.value - a.value);
 
 const option = {
 ...ECHARTS_COMMON,
 tooltip: {
 trigger: 'item',
 backgroundColor: 'var(--bg-surface)',
 borderColor: 'var(--border-subtle)',
 textStyle: { color: 'var(--text-primary)' }
 },
 series: [
 {
 type: 'pie',
 radius: ['50%', '70%'],
 avoidLabelOverlap: false,
 itemStyle: {
 borderRadius: 4,
 borderColor: 'var(--bg-panel)',
 borderWidth: 2
 },
 label: {
 show: false,
 position: 'center'
 },
 emphasis: {
 label: {
 show: true,
 fontSize: '16',
 fontWeight: 'bold',
 color: 'var(--text-primary)'
 }
 },
 labelLine: { show: false },
 data: data
 }
 ]
 };
 
 chart.setOption(option);
 activeCharts.push(chart);
 return chart;
}

export function renderRadarChart(containerId, departmentBreakdown) {
 const container = document.getElementById(containerId);
 if (!container || !window.echarts || !departmentBreakdown || departmentBreakdown.length === 0) return null;
 
 const chart = safeInit(container);
 
 const maxVal = Math.max(...departmentBreakdown.map(d => Math.max(d.revenue, d.expense)));
 
 const indicators = departmentBreakdown.map(d => ({ name: d.department, max: maxVal * 1.1 }));
 
 const option = {
 ...ECHARTS_COMMON,
 radar: {
 indicator: indicators,
 splitLine: { lineStyle: { color: 'var(--border-subtle)' } },
 splitArea: { show: false },
 axisLine: { lineStyle: { color: 'var(--border-subtle)' } }
 },
 series: [
 {
 type: 'radar',
 data: [
 {
 value: departmentBreakdown.map(d => d.revenue),
 name: 'Revenue',
 itemStyle: { color: '#0066FF' },
 areaStyle: { color: 'rgba(0, 102, 255, 0.2)' }
 },
 {
 value: departmentBreakdown.map(d => d.expense),
 name: 'Expense',
 itemStyle: { color: '#FF3B30' },
 areaStyle: { color: 'rgba(255, 59, 48, 0.2)' }
 }
 ]
 }
 ]
 };
 
 chart.setOption(option);
 activeCharts.push(chart);
 return chart;
}

export function renderTreemap(containerId, departmentBreakdown) {
 const container = document.getElementById(containerId);
 if (!container || !window.echarts || !departmentBreakdown) return null;
 
 const chart = safeInit(container);
 
 const data = departmentBreakdown.map(d => ({
 name: d.department,
 value: d.expense
 }));
 
 const option = {
 ...ECHARTS_COMMON,
 series: [{
 type: 'treemap',
 data: data,
 roam: false,
 nodeClick: false,
 breadcrumb: { show: false },
 itemStyle: {
 borderColor: 'var(--bg-panel)',
 borderWidth: 2,
 gapWidth: 2
 }
 }]
 };
 
 chart.setOption(option);
 activeCharts.push(chart);
 return chart;
}

export function renderScatterChart(containerId, scatterData) {
 const container = document.getElementById(containerId);
 if (!container || !window.echarts || !scatterData) return null;
 
 const chart = safeInit(container);
 
 const data = scatterData.map(d => [d.x, d.y, d.domain, d.line_item]);
 
 const option = {
 ...ECHARTS_COMMON,
 grid: { top: 30, right: 10, bottom: 20, left: 60 },
 xAxis: {
 type: 'value',
 splitLine: { lineStyle: { color: 'var(--border-subtle)', type: 'dashed' } },
 axisLabel: { color: 'var(--text-secondary)' }
 },
 yAxis: {
 type: 'value',
 splitLine: { lineStyle: { color: 'var(--border-subtle)', type: 'dashed' } },
 axisLabel: { 
 color: 'var(--text-secondary)',
 formatter: (value) => new Intl.NumberFormat('en-US', { notation: 'compact' }).format(value)
 }
 },
 series: [
 {
 type: 'scatter',
 symbolSize: 8,
 data: data,
 itemStyle: {
 color: 'var(--accent-primary)',
 opacity: 0.6
 }
 }
 ]
 };
 
 chart.setOption(option);
 activeCharts.push(chart);
 return chart;
}

export function renderHeatmap(containerId, chartsResult) {
 const container = document.getElementById(containerId);
 if (!container || !window.echarts || !chartsResult || !chartsResult.heatmap) return null;
 
 const chart = safeInit(container);
 
 const option = {
 ...ECHARTS_COMMON,
 tooltip: { position: 'top' },
 grid: { top: 30, right: 10, bottom: 40, left: 80 },
 xAxis: {
 type: 'category',
 data: chartsResult.periods,
 splitArea: { show: true },
 axisLine: { lineStyle: { color: 'var(--border-subtle)' } },
 axisLabel: { color: 'var(--text-secondary)' }
 },
 yAxis: {
 type: 'category',
 data: chartsResult.departments,
 splitArea: { show: true },
 axisLine: { lineStyle: { color: 'var(--border-subtle)' } },
 axisLabel: { color: 'var(--text-secondary)' }
 },
 visualMap: {
 min: 0,
 max: Math.max(...chartsResult.heatmap.map(d => d[2]), 100),
 calculable: true,
 orient: 'horizontal',
 left: 'center',
 bottom: 0,
 inRange: { color: ['#f1f5f9', '#2563eb', '#1e3a8a'] },
 textStyle: { color: 'var(--text-secondary)' }
 },
 series: [{
 type: 'heatmap',
 data: chartsResult.heatmap,
 label: { show: false },
 emphasis: {
 itemStyle: {
 shadowBlur: 10,
 shadowColor: 'rgba(0, 0, 0, 0.5)'
 }
 }
 }]
 };
 
 chart.setOption(option);
 activeCharts.push(chart);
 return chart;
}

export function renderForecastAreaChart(containerId, history, forecast) {
 const container = document.getElementById(containerId);
 if (!container || !window.echarts) return null;
 
 const chart = safeInit(container);
 
 const combinedPeriods = [...new Set([
 ...history.map(h => h.period), 
 ...forecast.map(f => f.ds.substring(0,7))
 ])].sort();
 
 let historyData = [];
 let forecastData = [];
 
 combinedPeriods.forEach(p => {
 let hItem = history.find(h => h.period === p);
 let fItem = forecast.find(f => f.ds.substring(0,7) === p);
 
 historyData.push(hItem ? hItem.value : '-');
 forecastData.push(fItem ? fItem.yhat : '-');
 });

 const option = {
 ...ECHARTS_COMMON,
 color: ['#10B981', '#3B82F6'],
 legend: {
 data: ['Actual', 'Forecast'],
 textStyle: { color: 'var(--text-secondary)' },
 bottom: 0
 },
 grid: { top: 30, right: 10, bottom: 40, left: 60 },
 xAxis: {
 type: 'category',
 data: combinedPeriods,
 axisLine: { lineStyle: { color: 'var(--border-subtle)' } },
 axisLabel: { color: 'var(--text-secondary)' }
 },
 yAxis: {
 type: 'value',
 splitLine: { lineStyle: { color: 'var(--border-subtle)', type: 'dashed' } },
 axisLabel: { 
 color: 'var(--text-secondary)',
 formatter: (value) => new Intl.NumberFormat('en-US', { notation: 'compact' }).format(value)
 }
 },
 series: [
 {
 name: 'Actual',
 type: 'line',
 data: historyData,
 lineStyle: { width: 3 },
 areaStyle: { opacity: 0.1 },
 symbol: 'none'
 },
 {
 name: 'Forecast',
 type: 'line',
 data: forecastData,
 lineStyle: { width: 2, type: 'dashed' },
 areaStyle: { opacity: 0.1 },
 symbol: 'none'
 }
 ]
 };
 
 chart.setOption(option);
 activeCharts.push(chart);
 return chart;
}

export function renderSunburstChart(containerId, data) {
 const container = document.getElementById(containerId);
 if (!container || !window.echarts || !data) return null;
 
 const chart = safeInit(container);
 
 const option = {
 ...ECHARTS_COMMON,
 series: {
 type: 'sunburst',
 data: data,
 radius: [0, '90%'],
 label: {
 rotate: 'radial',
 color: 'var(--text-primary)'
 },
 itemStyle: {
 borderColor: 'var(--bg-panel)',
 borderWidth: 2
 }
 }
 };
 
 chart.setOption(option);
 activeCharts.push(chart);
 return chart;
}
