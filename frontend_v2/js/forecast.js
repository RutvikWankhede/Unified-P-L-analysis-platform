/**
 * forecast.js - Forecast Page
 * ============================
 * Loads ALL data from the live backend API.
 * Zero hardcoded values. Zero Math.random().
 * If no uploaded dataset exists, shows a clear empty state.
 */

import { api } from './api.js';
import './auth.js';
import { state } from './state.js';

document.addEventListener('DOMContentLoaded', initForecast);

async function initForecast() {
 const metricSel = document.getElementById('forecast-metric');
 if (metricSel) metricSel.addEventListener('change', loadForecast);
 const periodSel = document.getElementById('forecast-period');
 if (periodSel) periodSel.addEventListener('change', loadForecast);

    const exportBtn = document.querySelector('[onclick*="downloadChart"]');
    if (exportBtn) {
        exportBtn.onclick = () => {
            if (window.forecastChartInstance) {
                const url = window.forecastChartInstance.getDataURL({ type: 'png', backgroundColor: '#fff' });
                const a = document.createElement('a');
                a.download = 'Forecast_Report.png';
                a.href = url;
                a.click();
            }
        };
    }

    window.addEventListener('globalFiltersChanged', loadForecast);
    await loadForecast();
    await loadForecastRecommendations();
}

async function loadForecastRecommendations() {
    try {
        const data = await api.get(api.endpoints.aiRecommendations);
        const container = document.getElementById('forecast-ai-recommendation');
        if (!container) return;
        
        const items = Array.isArray(data) ? data : (data.items || []);
        if (items.length === 0) {
            container.innerHTML = '<p class="text-sm text-slate-500">No forecast insights currently.</p>';
            return;
        }
        
        // Pick one related to risk mitigation or growth
        const rec = items.find(r => r.category === 'risk_mitigation' || r.category === 'revenue_growth') || items[0];
        const colors = { 'High': 'text-rose-600 bg-rose-50', 'Medium': 'text-amber-500 bg-amber-50', 'Low': 'text-blue-600 bg-blue-50' };
        const colorClass = colors[rec.priority] || 'text-blue-600 bg-blue-50';
        
        container.innerHTML = `
            <div class="mb-2 flex items-center gap-2">
                <span class="text-xs uppercase font-bold px-2 py-0.5 rounded-full ${colorClass}">${rec.priority || 'Info'}</span>
                <span class="text-sm font-bold text-slate-800">${rec.title || rec.recommendation}</span>
            </div>
            <p class="text-xs text-slate-600 leading-relaxed mb-3">${rec.description || ''}</p>
            <button class="text-xs text-primary font-bold hover:underline flex items-center gap-1">
                Take Action <span class="material-symbols-outlined text-[14px]">arrow_forward</span>
            </button>
        `;
        
        const btnViewAll = document.getElementById('btn-view-all-forecast-recs');
        if (btnViewAll && window.showModal) {
            btnViewAll.onclick = () => {
                const modalData = items.map(i => ({
                    Category: i.category,
                    Priority: i.priority,
                    Recommendation: i.title || i.recommendation,
                    Action: i.description || ''
                }));
                window.showModal("All Forecast Recommendations", ["Category", "Priority", "Recommendation", "Action"], modalData);
            };
        }
    } catch (err) {
        console.error('Failed to load forecast recommendations:', err);
    }
}

 async function loadForecast() {
 const metric = document.getElementById('forecast-metric')?.value || 'profit';
 const period = document.getElementById('forecast-period')?.value || '6';
 const chartDom = document.getElementById('forecast-chart');

 // Show loading state
 setEl('scenario-best', '…');
 setEl('scenario-expected', '…');
 setEl('scenario-worst', '…');
 setEl('ai-explanation', 'Loading forecast data…');
 setEl('model-accuracy', '…');
 setEl('model-rmse', '…');
 setEl('model-seasonality', '…');

 try {
 const queryParams = new URLSearchParams(window.location.search || '?domain=All');
 queryParams.set('metric', metric);
 queryParams.set('periods', period);
 const query = '?' + queryParams.toString();
 const data = await api.get(api.endpoints.forecast + query);

 if (!data || data.status === 'no_data') {
 showEmptyState(chartDom);
 setEl('scenario-best', '—');
 setEl('scenario-expected', '—');
 setEl('scenario-worst', '—');
 setEl('ai-explanation', 'No dataset uploaded yet. Please upload your financial data to generate forecasts.');
 setEl('model-accuracy', '—');
 setEl('model-rmse', '—');
 setEl('model-seasonality', '—');
 renderDrivers([]);
 return;
 }

 // ── Scenario Projections ──────────────────────────────────────────────
 const best = data.best_case ?? data.scenarios?.best ?? null;
 const expected = data.expected_case ?? data.scenarios?.expected ?? null;
 const worst = data.worst_case ?? data.scenarios?.worst ?? null;

 setEl('scenario-best', best !== null ? formatCurrency(best) : '—');
 setEl('scenario-expected', expected !== null ? formatCurrency(expected) : '—');
 setEl('scenario-worst', worst !== null ? formatCurrency(worst) : '—');

 // ── Model Metrics ─────────────────────────────────────────────────────
 const metrics = data.model_metrics || {};
 const accuracy = metrics.accuracy ?? metrics.mape_pct ?? null;
 const rmse = metrics.rmse ?? null;
 const seasonal = metrics.seasonality ?? metrics.seasonal_pattern ?? null;

 setEl('model-accuracy', accuracy !== null ? `${(accuracy).toFixed(1)}%` : '—');
 setEl('model-rmse', rmse !== null ? formatCurrency(rmse) : '—');
 setEl('model-seasonality', seasonal ?? 'Not detected');

 // ── AI Explanation ────────────────────────────────────────────────────
 const explanation = data.explanation || data.summary
 || 'Forecast generated from uploaded dataset. See scenario projections for best/expected/worst case estimates.';
 setEl('ai-explanation', explanation);

 // ── Feature Drivers ───────────────────────────────────────────────────
 const drivers = data.drivers || data.feature_importance || [];
 renderDrivers(drivers);

 // ── Forecast Chart ────────────────────────────────────────────────────
 renderChart(data, metric);

 } catch (err) {
 console.error('Forecast load failed:', err);
 showErrorState(chartDom, err.message);
 setEl('scenario-best', '—');
 setEl('scenario-expected', '—');
 setEl('scenario-worst', '—');
 setEl('ai-explanation', `Failed to load forecast: ${err.message || 'Backend error'}`);
 }
}

function renderDrivers(drivers) {
 const container = document.getElementById('forecast-drivers');
 if (!container) return;

 if (!drivers.length) {
 container.innerHTML = `
 <div class="flex flex-col items-center justify-center py-8 text-slate-400">
 <span class="material-symbols-outlined text-4xl mb-2">bar_chart</span>
 <p class="text-sm">No driver data available. Upload a dataset to see contributing factors.</p>
 </div>`;
 return;
 }

 container.innerHTML = drivers.map(d => {
 const impact = d.impact ?? d.importance ?? d.value ?? '';
 const impactStr = typeof impact === 'number' ? (impact >= 0 ? `+${impact.toFixed(1)}%` : `${impact.toFixed(1)}%`) : String(impact);
 const isNeg = impactStr.startsWith('-');
 const color = isNeg
 ? 'text-green-600 bg-green-50 border-green-100'
 : 'text-red-500 bg-red-50 border-red-100';
 return `
 <div class="flex justify-between items-center p-3 border border-slate-100 rounded-xl">
 <div>
 <p class="text-sm font-semibold text-slate-900">${d.name || d.feature || 'Factor'}</p>
 <p class="text-xs text-slate-500">${d.desc || d.description || ''}</p>
 </div>
 <span class="px-2 py-1 rounded text-xs font-bold border ${color}">${impactStr}</span>
 </div>`;
 }).join('');
}

function renderChart(data, metric) {
 const chartDom = document.getElementById('forecast-chart');
 if (!chartDom) return;

 if (window.forecastChartInstance) {
 window.forecastChartInstance.dispose();
 window.forecastChartInstance = null;
 }

 // Extract series from API response
 // Expected structure: data.historical = [{period, value}], data.forecast = [{period, value, upper, lower}]
 const historical = data.historical || data.time_series?.historical || [];
 const forecast = data.forecast || data.time_series?.forecast || [];

 if (!historical.length && !forecast.length) {
 showEmptyState(chartDom);
 return;
 }

 // Build label array (union of historical + forecast periods)
 const allPeriods = [
 ...historical.map(d => d.period || d.date || d.month || ''),
 ...forecast.map(d => d.period || d.date || d.month || ''),
 ].filter(Boolean);
 const labels = [...new Set(allPeriods)];

 // Map values to label positions
 const histMap = Object.fromEntries(historical.map(d => [d.period || d.date || d.month, d.value ?? d[metric] ?? d.profit ?? null]));
 const foreMap = Object.fromEntries(forecast.map(d => [d.period || d.date || d.month, d.value ?? d[metric] ?? d.profit ?? null]));
 const upperMap = Object.fromEntries(forecast.map(d => [d.period || d.date || d.month, d.upper ?? d.upper_bound ?? d.confidence_upper ?? null]));
 const lowerMap = Object.fromEntries(forecast.map(d => [d.period || d.date || d.month, d.lower ?? d.lower_bound ?? d.confidence_lower ?? null]));

 const histSeries = labels.map(l => histMap[l] ?? null);
 const foreSeries = labels.map(l => foreMap[l] ?? null);
 const upperSeries = labels.map(l => upperMap[l] ?? null);
 const lowerSeries = labels.map(l => lowerMap[l] ?? null);

 // Confidence band: ECharts stacked area trick
 const lowerBand = labels.map(l => lowerMap[l] ?? null);
 const upperBand = labels.map((l, i) => {
 const u = upperMap[l];
 const lo = lowerMap[l];
 return (u !== null && lo !== null) ? u - lo : null;
 });

 window.forecastChartInstance = echarts.init(chartDom);

 const option = {
 tooltip: { 
 trigger: 'axis', 
 axisPointer: { type: 'cross', label: { backgroundColor: '#6a7985' } },
 formatter: params => {
 const lines = params.filter(p => p.value !== null && p.seriesName !== 'Lower Bound' && p.seriesName !== 'Upper Band');
 return `<b>${params[0]?.axisValue}</b><br/>` +
 lines.map(p => `${p.marker} ${p.seriesName}: ${formatCurrency(p.value)}`).join('<br/>');
 }},
 legend: { data: ['Historical', 'Forecast'], top: 0 },
 grid: { left: '3%', right: '4%', bottom: '10%', top: '40px', containLabel: true },
 xAxis: { type: 'category', boundaryGap: false, data: labels, axisLabel: { color: '#64748b', fontSize: 11 } },
 yAxis: { type: 'value', splitLine: { lineStyle: { color: '#f1f5f9' } }, axisLabel: { color: '#64748b', fontSize: 11, formatter: v => formatCurrencyShort(v) } },
 dataZoom: [{ type: 'inside', start: 0, end: 100 }, { type: 'slider', start: 0, end: 100, bottom: 5 }],
 series: [
 // Confidence lower bound (transparent base)
 { name: 'Lower Bound', type: 'line', data: lowerBand, lineStyle: { opacity: 0 }, stack: 'confidence', symbol: 'none', legendHoverLink: false, tooltip: { show: false } },
 // Confidence upper band (shaded area)
 { name: 'Upper Band', type: 'line', data: upperBand, lineStyle: { opacity: 0 }, areaStyle: { color: 'rgba(91,92,235,0.10)' }, stack: 'confidence', symbol: 'none', legendHoverLink: false, tooltip: { show: false } },
 // Historical line
 { name: 'Historical', type: 'line', data: histSeries, itemStyle: { color: '#475569' }, lineStyle: { width: 2.5 }, smooth: true, symbol: 'circle', symbolSize: 4, z: 3, emphasis: { focus: 'series' } },
 // Forecast line (dashed)
 { name: 'Forecast', type: 'line', data: foreSeries, itemStyle: { color: '#5b5ceb' }, lineStyle: { width: 3, type: 'dashed' }, smooth: true, symbol: 'circle', symbolSize: 4, z: 3, emphasis: { focus: 'series' } },

 ],
 };

 window.forecastChartInstance.setOption(option);

 // Resize observer
 const ro = new ResizeObserver(() => window.forecastChartInstance?.resize());
 ro.observe(chartDom);
}

function showEmptyState(dom) {
 if (!dom) return;
 dom.innerHTML = `
 <div class="flex flex-col items-center justify-center h-full min-h-[200px] text-slate-400">
 <span class="material-symbols-outlined text-5xl mb-3">query_stats</span>
 <p class="text-sm font-semibold">No Forecast Data</p>
 <p class="text-xs mt-1">Upload a financial dataset to generate forecasts</p>
 <a href="upload.html" class="mt-4 px-4 py-2 bg-primary text-white text-xs font-bold rounded-lg hover:bg-indigo-700 transition-colors">Upload Dataset</a>
 </div>`;
}

function showErrorState(dom, message) {
 if (!dom) return;
 dom.innerHTML = `
 <div class="flex flex-col items-center justify-center h-full min-h-[200px] text-red-400">
 <span class="material-symbols-outlined text-5xl mb-3">error</span>
 <p class="text-sm font-semibold">Failed to Load Forecast</p>
 <p class="text-xs mt-1">${message || 'Backend connection error'}</p>
 </div>`;
}

function setEl(id, val) {
 const el = document.getElementById(id);
 if (el) el.textContent = val;
}

function formatCurrency(val) {
 if (val == null || isNaN(val)) return '—';
 const abs = Math.abs(val);
 if (abs >= 10000000) return '₹' + (val / 10000000).toFixed(2) + ' Cr';
 if (abs >= 100000) return '₹' + (val / 100000).toFixed(2) + ' L';
 return new Intl.NumberFormat('en-IN', { style: 'currency', currency: 'INR', maximumFractionDigits: 0 }).format(val);
}

function formatCurrencyShort(val) {
 if (val == null || isNaN(val)) return '—';
 const abs = Math.abs(val);
 if (abs >= 10000000) return '₹' + (val / 10000000).toFixed(1) + ' Cr';
 if (abs >= 100000) return '₹' + (val / 100000).toFixed(1) + ' L';
 return '₹' + val.toLocaleString('en-IN');
}
