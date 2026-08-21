import { api } from './api.js';
import { generatePalette, initEchart, safeSetOption } from './chart-engine.js';

document.addEventListener('DOMContentLoaded', () => {
    const formatCurrency = (val) => {
        if (!val && val !== 0) return '₹0';
        if (Math.abs(val) >= 10000000) return `₹${(val / 10000000).toFixed(2)} Cr`;
        if (Math.abs(val) >= 100000) return `₹${(val / 100000).toFixed(2)} L`;
        return `₹${val.toLocaleString('en-IN', {maximumFractionDigits: 0})}`;
    };

    // ── State ──────────────────────────────────────────────────────────────────
    let deptData = [];
    let trendData = {};
    let contribMetric = 'profit';
    let contribScope = '5';

    // ── Chart instances ────────────────────────────────────────────────────────
    let contribChart = null;
    let trendChart = null;

    const contribContainer = document.getElementById('chart-dept-contribution');
    const trendContainer = document.getElementById('dept-trend-chart');

    if (contribContainer) contribChart = initEchart(contribContainer);
    if (trendContainer) trendChart = initEchart(trendContainer);

    // ── Contribution Chart ─────────────────────────────────────────────────────
    function renderContribChart() {
        if (!contribChart || !deptData.length) return;
        let sorted = [...deptData].sort((a, b) => (b[contribMetric] || 0) - (a[contribMetric] || 0));
        if (contribScope !== 'all') {
            sorted = sorted.slice(0, parseInt(contribScope));
        }
        const labels = sorted.map(d => d.department || 'Unknown');
        const values = sorted.map(d => {
            if (contribMetric === 'margin') {
                return d.revenue > 0 ? parseFloat(((d.profit / d.revenue) * 100).toFixed(1)) : 0;
            }
            return d[contribMetric] || 0;
        });
        const palette = generatePalette(labels.length);
        const formatter = contribMetric === 'margin'
            ? (v) => `${v.toFixed(1)}%`
            : (v) => formatCurrency(v);

        safeSetOption(contribChart, {
            tooltip: {
                trigger: 'axis',
                axisPointer: { type: 'shadow' },
                formatter: (params) => {
                    const p = params[0];
                    return `<div style="padding:4px 8px"><b>${p.name}</b><br/>${formatter(p.value)}</div>`;
                }
            },
            grid: { left: '3%', right: '4%', bottom: '5%', containLabel: true },
            xAxis: {
                type: 'value',
                axisLabel: { formatter: contribMetric === 'margin' ? (v) => `${v}%` : (v) => formatCurrency(v) }
            },
            yAxis: { type: 'category', data: labels, axisLabel: { fontSize: 11 } },
            series: [{
                name: contribMetric,
                type: 'bar',
                data: values.map((v, i) => ({ value: v, itemStyle: { color: palette[i] } })),
                label: {
                    show: true,
                    position: 'right',
                    formatter: (p) => formatter(p.value),
                    fontSize: 10,
                    color: '#64748b'
                },
                barMaxWidth: 32
            }]
        });

        // Add interactivity: click to highlight department in trend chart
        contribChart.off('click');
        contribChart.on('click', (params) => {
            if (!trendChart) return;
            const deptName = params.name;
            const option = trendChart.getOption();
            if (!option || !option.series) return;
            
            // Check if already highlighted, if so, reset
            const isHighlighted = option.series.some(s => s.name === deptName && s.lineStyle && s.lineStyle.width === 4);
            
            const newSeries = option.series.map(s => {
                if (isHighlighted) {
                    // Reset
                    s.lineStyle = { ...s.lineStyle, width: 2 };
                    s.itemStyle = { ...s.itemStyle, opacity: 1 };
                } else {
                    // Highlight selected, fade others
                    if (s.name === deptName) {
                        s.lineStyle = { ...s.lineStyle, width: 4 };
                        s.itemStyle = { ...s.itemStyle, opacity: 1 };
                    } else {
                        s.lineStyle = { ...s.lineStyle, width: 1 };
                        s.itemStyle = { ...s.itemStyle, opacity: 0.2 };
                    }
                }
                return s;
            });
            trendChart.setOption({ series: newSeries });
        });
    }

    // ── Trend Chart ────────────────────────────────────────────────────────────
    function renderTrendChart() {
        if (!trendChart || !Object.keys(trendData).length) return;

        const periods = Object.values(trendData)[0]?.map(pt => pt.period) || [];
        const palette = generatePalette(Object.keys(trendData).length);
        const series = Object.entries(trendData).map(([dept, pts], i) => ({
            name: dept,
            type: 'line',
            data: pts.map(pt => pt.profit || 0),
            smooth: true,
            itemStyle: { color: palette[i] },
            lineStyle: { width: 2 },
            symbolSize: 5
        }));

        // Render legend badges
        const badgesCt = document.getElementById('dept-trend-badges');
        if (badgesCt) {
            badgesCt.innerHTML = Object.keys(trendData).map((dept, i) =>
                `<span style="background:${palette[i]}20;color:${palette[i]};border:1px solid ${palette[i]}40" class="px-2 py-0.5 rounded text-[10px] font-bold">${dept}</span>`
            ).join('');
        }

        safeSetOption(trendChart, {
            tooltip: {
                trigger: 'axis',
                formatter: (params) => {
                    const header = `<div style="font-weight:600;border-bottom:1px solid #e5e7eb;padding-bottom:4px;margin-bottom:4px;">${params[0]?.axisValue}</div>`;
                    const rows = params.map(p => `<div><span style="display:inline-block;width:8px;height:8px;border-radius:50%;background:${p.color};margin-right:6px;"></span>${p.seriesName}: <b>${formatCurrency(p.value)}</b></div>`).join('');
                    return `<div style="padding:4px 8px">${header}${rows}</div>`;
                }
            },
            legend: { show: false },
            grid: { left: '3%', right: '4%', bottom: '15%', containLabel: true },
            dataZoom: [
                { type: 'inside', start: 0, end: 100 },
                { type: 'slider', start: 0, end: 100, bottom: 25 }
            ],
            xAxis: { type: 'category', data: periods, boundaryGap: false, axisLabel: { fontSize: 10, rotate: 30 } },
            yAxis: { type: 'value', axisLabel: { formatter: (v) => formatCurrency(v) } },
            series
        });

        // Trigger a resize on next tick to handle rendering within hidden tabs
        setTimeout(() => { if (trendChart) trendChart.resize(); }, 50);
    }

    // ── KPIs and Table ─────────────────────────────────────────────────────────
    function renderKpisAndTable(data) {
        let totRev = 0, totExp = 0;
        data.forEach(d => {
            totRev += (d.revenue || 0);
            totExp += (d.expense || 0);
        });
        const totProfit = totRev - totExp;

        const revEl = document.getElementById('kpi-total-revenue');
        if (revEl) {
            const valEl = revEl.querySelector('.kpi-value');
            if (valEl) valEl.innerText = formatCurrency(totRev);
        }
        const expEl = document.getElementById('kpi-total-expense');
        if (expEl) {
            const valEl = expEl.querySelector('.kpi-value');
            if (valEl) valEl.innerText = formatCurrency(totExp);
        }
        const profEl = document.getElementById('kpi-net-profit');
        if (profEl) {
            const valEl = profEl.querySelector('.kpi-value');
            if (valEl) valEl.innerText = formatCurrency(totProfit);
        }
        const healthEl = document.getElementById('kpi-margin');
        if (healthEl) {
            const valEl = healthEl.querySelector('.kpi-value');
            if (valEl && totRev > 0) {
                valEl.innerText = ((totProfit / totRev) * 100).toFixed(1) + '%';
            }
        }

        // Table — replace static rows with live data
        const tbody = document.getElementById('dept-table-body');
        if (tbody) {
            const sorted = [...data].sort((a, b) => (b.profit || 0) - (a.profit || 0));
            const colors = ['bg-blue-500', 'bg-emerald-400', 'bg-orange-400', 'bg-purple-400', 'bg-pink-400', 'bg-yellow-400', 'bg-indigo-400', 'bg-teal-400'];
            tbody.innerHTML = sorted.map((d, i) => {
                const margin = d.revenue > 0 ? ((d.profit / d.revenue) * 100).toFixed(1) : '0.0';
                const isPos = (d.profit || 0) >= 0;
                const arrowSvg = isPos
                    ? `<svg class="w-3 h-3" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path d="M5 10l7-7 7 7" stroke-linecap="round" stroke-linejoin="round" stroke-width="2"></path></svg>`
                    : `<svg class="w-3 h-3" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path d="M19 14l-7 7-7-7" stroke-linecap="round" stroke-linejoin="round" stroke-width="2"></path></svg>`;
                const trendClass = isPos ? 'text-success' : 'text-danger';
                return `<tr class="border-b border-slate-50 last:border-0 hover:bg-slate-50 transition-colors">
                    <td class="py-4 flex items-center gap-2"><span class="w-2 h-2 rounded-full ${colors[i % colors.length]}"></span>${d.department || 'N/A'}</td>
                    <td class="py-4">${formatCurrency(d.revenue)}</td>
                    <td class="py-4">${formatCurrency(d.expense)}</td>
                    <td class="py-4">${formatCurrency(d.profit)}</td>
                    <td class="py-4 text-slate-500">${margin}%</td>
                    <td class="py-4"><span class="flex items-center gap-1 ${trendClass} text-xs font-bold">${arrowSvg}${Math.abs(d.trend_pct || 0).toFixed(1)}%</span></td>
                </tr>`;
            }).join('');
        }

        // Top performers panel — use a specific container id
        const topPerfEl = document.getElementById('top-performers-list');
        if (topPerfEl) {
            if (!data.length) {
                topPerfEl.innerHTML = '<div class="text-xs text-slate-400 italic p-2 text-center">No data available.</div>';
                return;
            }
            const sorted = [...data].sort((a, b) => (b.profit || 0) - (a.profit || 0)).slice(0, 3);
            const rankColors = ['text-blue-600', 'text-slate-400', 'text-amber-500'];
            topPerfEl.innerHTML = sorted.map((d, i) => `
                <div class="flex items-center gap-4">
                    <span class="text-lg font-bold ${rankColors[i]} w-4">${i + 1}</span>
                    <div>
                        <p class="text-sm font-bold">${d.department}</p>
                        <p class="text-[10px] text-slate-400">Profit: ${formatCurrency(d.profit)}</p>
                    </div>
                </div>`).join('');
        }
    }

    // ── Insights with timeout ──────────────────────────────────────────────────
    function loadInsights(data) {
        const insightEl = document.getElementById('dept-contrib-insight-text');
        if (!insightEl) return;

        const timeout = setTimeout(() => {
            insightEl.textContent = 'Unable to load AI insights at this time. Check back later.';
        }, 12000);

        // Generate insight from data directly (fast, no API call needed)
        try {
            const sorted = [...data].sort((a, b) => (b.profit || 0) - (a.profit || 0));
            const top = sorted[0];
            const bottom = sorted[sorted.length - 1];
            const total = data.reduce((s, d) => s + (d.profit || 0), 0);
            const topShare = total > 0 ? ((top.profit / total) * 100).toFixed(1) : 0;
            clearTimeout(timeout);
            insightEl.textContent = `${top?.department || 'Top dept'} leads with ₹${formatCurrency(top?.profit)} profit (${topShare}% of total). ${bottom?.department || 'Bottom dept'} needs attention at ₹${formatCurrency(bottom?.profit)}.`;
        } catch (e) {
            clearTimeout(timeout);
            insightEl.textContent = 'Insight computation unavailable.';
        }
    }

    // ── Main Data Load ─────────────────────────────────────────────────────────
    async function loadAll() {
        if (contribChart) contribChart.showLoading({ text: 'Loading departments...', color: '#6366F1' });
        if (trendChart) trendChart.showLoading({ text: 'Loading trend...', color: '#6366F1' });

        try {
            // First check capabilities
            const summaryRes = await api.get('/api/v1/pl/summary').catch(() => null);
            const caps = summaryRes?.capabilities || {};
            
            if (caps.has_departments === false) {
                const main = document.getElementById('main-content') || document.querySelector('main');
                if (main) {
                    const header = main.querySelector('header');
                    const headerHtml = header ? header.outerHTML : '';
                    main.innerHTML = `
                        ${headerHtml}
                        <div class="px-8 py-12 flex flex-col items-center justify-center text-center max-w-xl mx-auto min-h-[400px]">
                            <div class="w-16 h-16 rounded-full bg-slate-100 flex items-center justify-center mb-6 text-slate-400">
                                <span class="material-symbols-outlined text-3xl" style="font-size: 36px; font-family: 'Material Symbols Outlined' !important;">domain_disabled</span>
                            </div>
                            <h2 class="text-xl font-bold text-slate-800 mb-2">Department Analysis Unavailable</h2>
                            <p class="text-sm text-slate-500 mb-6 leading-relaxed">This dataset does not contain a "Department" or "Business Unit" dimension. All metrics are aggregated at the organizational level.</p>
                            <div class="px-4 py-3 bg-slate-50 border border-slate-100 rounded-xl text-xs text-slate-500 flex items-center gap-2">
                                <span class="material-symbols-outlined text-slate-400 text-sm" style="font-family: 'Material Symbols Outlined' !important;">info</span>
                                <span>To view department breakdowns, upload a dataset containing a <b>department</b> or <b>domain</b> column.</span>
                            </div>
                        </div>
                    `;
                    if (contribChart) { try { contribChart.clear(); contribChart.dispose(); } catch (_) {} }
                    if (trendChart) { try { trendChart.clear(); trendChart.dispose(); } catch (_) {} }
                    return;
                }
            }

            const deptReq = api.get(api.endpoints.departmentSummary);
            const trendReq = api.get(api.endpoints.departmentTrend || '/api/v1/pl/departments/trend').catch(() => null);
            
            const [deptRes, trendRes] = await Promise.all([deptReq, trendReq]);
            
            deptData = (deptRes && Array.isArray(deptRes.departments)) ? deptRes.departments : [];

            renderKpisAndTable(deptData);
            renderContribChart();
            loadInsights(deptData);

            // Process trend data
            if (trendRes && typeof trendRes === 'object') {
                if (trendRes.series && trendRes.periods) {
                    trendData = {};
                    for (const [dept, values] of Object.entries(trendRes.series)) {
                        trendData[dept] = trendRes.periods.map((p, i) => ({
                            period: p,
                            profit: values[i]
                        }));
                    }
                } else {
                    trendData = trendRes;
                }
            } else {
                trendData = {};
            }

            renderTrendChart();
            if (contribChart) contribChart.hideLoading();
            if (trendChart) trendChart.hideLoading();
        } catch (e) {
            console.error('Error loading department data:', e);
            const insightEl = document.getElementById('dept-contrib-insight-text');
            if (insightEl) insightEl.textContent = 'Failed to load department data.';
            if (contribChart) contribChart.hideLoading();
            if (trendChart) trendChart.hideLoading();
        }
    }

    // ── Filter Wire-up ─────────────────────────────────────────────────────────
    const metricSel = document.getElementById('dept-contrib-metric');
    const scopeSel = document.getElementById('dept-contrib-scope');
    const trendAggSel = document.getElementById('dept-trend-agg');

    if (metricSel) {
        metricSel.addEventListener('change', () => {
            contribMetric = metricSel.value;
            renderContribChart();
        });
    }
    if (scopeSel) {
        scopeSel.addEventListener('change', () => {
            contribScope = scopeSel.value;
            renderContribChart();
        });
    }
    if (trendAggSel) {
        trendAggSel.addEventListener('change', async () => {
            if (trendChart) trendChart.showLoading({ text: 'Loading trend...', color: '#6366F1' });
            const agg = trendAggSel.value;
            const trendRes = await api.get(`/api/v1/pl/departments/trend?agg=${agg}`).catch(() => null);
            if (trendRes && trendRes.series && trendRes.periods) {
                trendData = {};
                for (const [dept, values] of Object.entries(trendRes.series)) {
                    trendData[dept] = trendRes.periods.map((p, i) => ({
                        period: p,
                        profit: values[i]
                    }));
                }
            }
            renderTrendChart();
            if (trendChart) trendChart.hideLoading();
        });
    }

    window.addEventListener('resize', () => {
        if (contribChart) contribChart.resize();
        if (trendChart) trendChart.resize();
    });

    loadAll();
});
