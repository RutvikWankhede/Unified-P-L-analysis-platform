/**
 * chart-engine.js
 * Intelligent dynamic charting wrapper for Apache ECharts.
 *
 * ROOT CAUSE FIX (v9):
 *   echarts.init() called when a container has 0×0 dimensions stores those
 *   dimensions internally and refuses to render even after setOption().
 *   The fix is two-pronged:
 *     1. initEchart() records the init size and schedules a resize if the
 *        container was zero-sized at init time.
 *     2. safeSetOption() always calls chart.resize() inside a
 *        requestAnimationFrame AFTER setOption(), so ECharts re-measures the
 *        container's *real* post-layout dimensions before painting.
 *   All callers in this file and in wiring files should use safeSetOption()
 *   instead of chart.setOption() directly.
 */

export const formatCurrency = (val) => {
    let currency = 'INR';
    try {
        const saved = localStorage.getItem('pl_global_filters');
        if (saved) {
            const parsed = JSON.parse(saved);
            currency = parsed.currency || 'INR';
        }
    } catch (e) {}

    const isUSD = currency.includes('USD') || currency.includes('$');
    const sym = isUSD ? '$' : '₹';

    if (!val && val !== 0) return `${sym}0`;

    if (isUSD) {
        if (val >= 1000000000) return `${sym}${(val / 1000000000).toFixed(2)}B`;
        if (val >= 1000000) return `${sym}${(val / 1000000).toFixed(2)}M`;
        if (val >= 1000) return `${sym}${(val / 1000).toFixed(1)}K`;
        return `${sym}${val.toLocaleString()}`;
    } else {
        if (val >= 10000000) return `${sym}${(val / 10000000).toFixed(2)} Cr`;
        if (val >= 100000) return `${sym}${(val / 100000).toFixed(2)} L`;
        return `${sym}${val.toLocaleString()}`;
    }
};

// Generate an adaptive, non-repeating color palette using HSL distribution
export function initEchart(container, opts = {}) {
    let chart = echarts.getInstanceByDom(container);
    if (!chart) {
        const dpr = Math.max(window.devicePixelRatio || 1, 2);
        const initOpts = {
            renderer: 'svg',
            devicePixelRatio: dpr,
            ...opts
        };
        chart = echarts.init(container, null, initOpts);

        // If the container was zero-sized at init time (happens when the page
        // hasn't finished laying out yet), schedule an immediate resize so that
        // ECharts gets real dimensions as soon as the browser paints.
        if (container.offsetWidth === 0 || container.offsetHeight === 0) {
            requestAnimationFrame(() => {
                try { chart.resize(); } catch (_) {}
            });
        }

        if (window.ResizeObserver) {
            const ro = new ResizeObserver(() => {
                try { chart.resize(); } catch (_) {}
            });
            ro.observe(container);
        } else {
            window.addEventListener('resize', () => {
                try { chart.resize(); } catch (_) {}
            });
        }
    }
    return chart;
}


/**
 * safeSetOption — call this instead of chart.setOption() everywhere.
 * It applies the option and then forces a resize in the next animation frame
 * so that a chart initialised in a hidden/zero-size container will re-measure
 * and render correctly once it becomes visible.
 *
 * @param {echarts.ECharts} chart
 * @param {object} option
 * @param {boolean} [notMerge=false]  pass true to replace (same as setOption 2nd arg)
 */
export function safeSetOption(chart, option, notMerge = false) {
    if (!chart) return;
    chart.setOption(option, notMerge);
    // Force re-measure on next paint. This cures the "blank chart on first
    // load" race condition where the container was 0×0 at echarts.init() time.
    requestAnimationFrame(() => {
        try { chart.resize(); } catch (_) {}
    });
}

export function generatePalette(count) {
    const colors = [];
    const saturation = 70;
    const lightness = 55;

    // Enterprise SaaS baseline colors (Stitch/Stripe inspired)
    const basePalette = [
        '#3B82F6', '#10B981', '#F59E0B', '#EF4444',
        '#8B5CF6', '#EC4899', '#06B6D4', '#F97316'
    ];

    if (count <= basePalette.length) {
        return basePalette.slice(0, count);
    }

    // If more colors needed, evenly distribute across color wheel
    const step = 360 / count;
    for (let i = 0; i < count; i++) {
        const hue = Math.floor(i * step);
        colors.push(`hsl(${hue}, ${saturation}%, ${lightness}%)`);
    }
    return colors;
}

/**
 * Automatically render the best chart type for categorical data.
 * @param {HTMLElement} container - DOM element to render in
 * @param {Array} data - Array of objects [{ name: 'A', value: 10 }, ...]
 * @param {string} [title='']
 * @returns {echarts.ECharts} - The ECharts instance
 */
export function autoCategoricalChart(container, data, title = '') {
    const chart = initEchart(container);
    const count = data.length;
    const palette = generatePalette(count);

    // Sort data descending
    const sortedData = [...data].sort((a, b) => b.value - a.value);

    let option = {
        title: { text: title, left: 'center', textStyle: { fontSize: 14, fontWeight: 600, color: '#0F172A' } },
        tooltip: { trigger: 'item', formatter: '{b}: {c} ({d}%)' },
        color: palette,
    };

    if (count === 0) {
        chart.clear();
        return chart;
    }

    if (count <= 3) {
        // Simple Pie
        option.series = [{
            type: 'pie',
            radius: '65%',
            data: sortedData,
            emphasis: { itemStyle: { shadowBlur: 10, shadowOffsetX: 0, shadowColor: 'rgba(0, 0, 0, 0.5)' } },
            label: { show: true, formatter: '{b}\n{d}%' }
        }];
    } else if (count <= 10) {
        // Donut Chart
        option.series = [{
            type: 'pie',
            radius: ['40%', '70%'],
            avoidLabelOverlap: true,
            itemStyle: { borderRadius: 4, borderColor: '#fff', borderWidth: 2 },
            label: { show: true, position: 'outside', formatter: '{b}' },
            data: sortedData
        }];
    } else if (count <= 20) {
        // Rose Chart
        option.series = [{
            type: 'pie',
            radius: [20, '80%'],
            center: ['50%', '50%'],
            roseType: 'area',
            itemStyle: { borderRadius: 8 },
            data: sortedData
        }];
    } else if (count < 50) {
        // Treemap for many categories
        option.tooltip.formatter = '{b}: {c}';
        option.series = [{
            type: 'treemap',
            roam: false,
            nodeClick: false,
            breadcrumb: { show: false },
            itemStyle: { borderColor: '#fff' },
            data: sortedData
        }];
    } else {
        // Sunburst for 50+
        const sunburstData = sortedData.map(d => ({ name: d.name, value: d.value }));
        option.tooltip.formatter = '{b}: {c}';
        option.series = [{
            type: 'sunburst',
            data: sunburstData,
            radius: [0, '90%'],
            label: { rotate: 'radial' }
        }];
    }

    safeSetOption(chart, option);
    return chart;
}

/**
 * Render an auto-adjusting timeseries / line chart
 */
export function autoTimeSeriesChart(container, dates, values, seriesName = 'Value', isCurrency = true) {
    const chart = initEchart(container);

    const option = {
        tooltip: {
            trigger: 'axis',
            formatter: function (params) {
                let val = params[0].value;
                if (isCurrency) val = new Intl.NumberFormat('en-US', { style: 'currency', currency: 'USD' }).format(val);
                return `${params[0].name}<br/><b>${params[0].seriesName}:</b> ${val}`;
            }
        },
        grid: { left: '3%', right: '4%', bottom: '3%', containLabel: true },
        xAxis: {
            type: 'category',
            boundaryGap: false,
            data: dates,
            axisLine: { lineStyle: { color: '#CBD5E1' } },
            axisLabel: { color: '#64748B' }
        },
        yAxis: {
            type: 'value',
            axisLine: { show: false },
            axisTick: { show: false },
            splitLine: { lineStyle: { color: '#F1F5F9', type: 'dashed' } },
            axisLabel: {
                color: '#64748B',
                formatter: (value) => {
                    if (value >= 1000000) return (value / 1000000).toFixed(1) + 'M';
                    if (value >= 1000) return (value / 1000).toFixed(1) + 'k';
                    return value;
                }
            }
        },
        series: [{
            name: seriesName,
            type: 'line',
            smooth: true,
            symbol: 'none',
            itemStyle: { color: '#3B82F6' },
            areaStyle: {
                color: new echarts.graphic.LinearGradient(0, 0, 0, 1, [
                    { offset: 0, color: 'rgba(59, 130, 246, 0.3)' },
                    { offset: 1, color: 'rgba(59, 130, 246, 0)' }
                ])
            },
            data: values
        }]
    };

    safeSetOption(chart, option);
    return chart;
}

/**
 * Render an auto-adjusting Bar chart (horizontal or vertical depending on data length)
 */
export function autoBarChart(container, labels, values, seriesName = 'Value') {
    const chart = initEchart(container);
    const count = labels.length;

    // If we have many labels, horizontal bar is better for readability
    const isHorizontal = count > 8;

    const option = {
        tooltip: { trigger: 'axis', axisPointer: { type: 'shadow' } },
        grid: { left: '3%', right: '4%', bottom: '3%', containLabel: true },
        xAxis: isHorizontal
            ? { type: 'value', splitLine: { lineStyle: { color: '#F1F5F9' } } }
            : { type: 'category', data: labels, axisLabel: { interval: 0, rotate: count > 5 ? 30 : 0, color: '#64748B' } },
        yAxis: isHorizontal
            ? { type: 'category', data: labels, axisLabel: { color: '#64748B' } }
            : { type: 'value', splitLine: { lineStyle: { color: '#F1F5F9' } } },
        series: [{
            name: seriesName,
            type: 'bar',
            itemStyle: { color: '#10B981', borderRadius: isHorizontal ? [0, 4, 4, 0] : [4, 4, 0, 0] },
            data: values
        }]
    };

    safeSetOption(chart, option);
    return chart;
}

function getChartCurrencyInfo() {
    const el = document.getElementById('filter-currency');
    const currency = el ? el.value : 'INR';
    const isUSD = currency === 'USD';
    return { isUSD, sym: isUSD ? '$' : '₹' };
}

function formatChartCurrencyShort(val) {
    const { isUSD, sym } = getChartCurrencyInfo();
    if (!val && val !== 0) return `${sym}0`;
    if (isUSD) {
        if (val >= 1000000) return `${sym}${(val / 1000000).toFixed(1)}M`;
        if (val >= 1000) return `${sym}${(val / 1000).toFixed(1)}K`;
        return `${sym}${val}`;
    } else {
        if (val >= 10000000) return `${sym}${(val / 10000000).toFixed(1)}Cr`;
        if (val >= 100000) return `${sym}${(val / 100000).toFixed(1)}L`;
        return `${sym}${val}`;
    }
}

function formatChartCurrencyFull(val) {
    const { isUSD } = getChartCurrencyInfo();
    return new Intl.NumberFormat(isUSD ? 'en-US' : 'en-IN', { style: 'currency', currency: isUSD ? 'USD' : 'INR', maximumFractionDigits: 0 }).format(val);
}

/**
 * Render advanced dashboard chart with 3 series (Revenue, Expense, Profit) and zoom/export
 */
export function renderDashboardMainChart(container, dates, revenue, expense, profit) {
    const chart = initEchart(container);
    const option = {
        tooltip: {
            trigger: 'axis',
            axisPointer: { type: 'cross', label: { backgroundColor: '#6a7985' } },
            formatter: function (params) {
                let res = `<b>${params[0].name}</b><br/>`;
                params.forEach(p => {
                    let val = formatChartCurrencyFull(p.value);
                    res += `${p.marker} ${p.seriesName}: <span style="font-weight:bold">${val}</span><br/>`;
                });
                return res;
            }
        },
        legend: { data: ['Revenue', 'Expense', 'Profit'], top: '2%', itemGap: 20 },
        grid: { left: '3%', right: '4%', bottom: '15%', top: '15%', containLabel: true },
        toolbox: {
            feature: {
                dataZoom: { yAxisIndex: 'none' },
                restore: {},
                saveAsImage: { type: 'png', name: 'PL_Dashboard_Chart' },
                dataView: { readOnly: true }
            }
        },
        xAxis: {
            type: 'category',
            boundaryGap: false,
            data: dates,
            axisLine: { lineStyle: { color: '#E2E8F0' } },
            axisLabel: { color: '#64748B', margin: 12 }
        },
        yAxis: {
            type: 'value',
            splitLine: { lineStyle: { color: '#F1F5F9', type: 'solid' } },
            axisLabel: {
                color: '#64748B',
                formatter: (value) => formatChartCurrencyShort(value)
            }
        },
        dataZoom: [
            { type: 'inside', start: 0, end: 100 },
            { start: 0, end: 100, bottom: 0, height: 20, borderColor: 'transparent', backgroundColor: '#F8FAFC' }
        ],
        series: [
            {
                name: 'Revenue', type: 'line', smooth: true,
                data: revenue,
                lineStyle: { width: 3, shadowColor: 'rgba(99,102,241,0.3)', shadowBlur: 10, shadowOffsetY: 5 },
                itemStyle: { color: '#6366f1' },
                areaStyle: {
                    color: new echarts.graphic.LinearGradient(0, 0, 0, 1, [
                        { offset: 0, color: 'rgba(99,102,241,0.2)' },
                        { offset: 1, color: 'rgba(99,102,241,0.01)' }
                    ])
                }
            },
            {
                name: 'Expense', type: 'line', smooth: true,
                data: expense,
                lineStyle: { width: 3, shadowColor: 'rgba(244,63,94,0.3)', shadowBlur: 10, shadowOffsetY: 5 },
                itemStyle: { color: '#f43f5e' },
                areaStyle: {
                    color: new echarts.graphic.LinearGradient(0, 0, 0, 1, [
                        { offset: 0, color: 'rgba(244,63,94,0.2)' },
                        { offset: 1, color: 'rgba(244,63,94,0.01)' }
                    ])
                }
            },
            {
                name: 'Profit', type: 'line', smooth: true,
                data: profit,
                lineStyle: { width: 3, shadowColor: 'rgba(16,185,129,0.3)', shadowBlur: 10, shadowOffsetY: 5 },
                itemStyle: { color: '#10b981' },
                areaStyle: {
                    color: new echarts.graphic.LinearGradient(0, 0, 0, 1, [
                        { offset: 0, color: 'rgba(16,185,129,0.2)' },
                        { offset: 1, color: 'rgba(16,185,129,0.01)' }
                    ])
                }
            }
        ]
    };
    safeSetOption(chart, option, true);
    return chart;
}

/**
 * Render a mini sparkline chart
 */
export function renderSparkline(containerId, data, color = '#6366f1') {
    const container = document.getElementById(containerId);
    if (!container) return;

    const chart = initEchart(container);
    const option = {
        grid: { left: 0, right: 0, top: 0, bottom: 0 },
        xAxis: { type: 'category', show: false, boundaryGap: false, data: data.map((_, i) => i) },
        yAxis: { type: 'value', show: false, scale: true },
        tooltip: { show: false },
        series: [{
            type: 'line',
            data: data,
            smooth: true,
            symbol: 'none',
            lineStyle: { color: color, width: 2 },
            areaStyle: {
                color: new echarts.graphic.LinearGradient(0, 0, 0, 1, [
                    { offset: 0, color: color },
                    { offset: 1, color: 'rgba(255,255,255,0)' }
                ]),
                opacity: 0.3
            }
        }]
    };
    safeSetOption(chart, option);
    return chart;
}
