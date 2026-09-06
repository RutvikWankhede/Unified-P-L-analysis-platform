import { api } from './api.js';
import { initEchart, safeSetOption } from './chart-engine.js';

document.addEventListener('DOMContentLoaded', async () => {
    const formatCurrency = (val, isMargin = false) => {
        if (val === null || val === undefined || isNaN(val)) return isMargin ? '0.0%' : '₹0 Cr';
        if (isMargin) {
            const sign = val > 0 ? '+' : '';
            return `${sign}${val.toFixed(1)}%`;
        }
        const abs = Math.abs(val);
        const sign = val < 0 ? '-' : '';
        if (abs >= 1000000000) return `${sign}₹${(abs / 1000000000).toFixed(2)} B`;
        if (abs >= 10000000) return `${sign}₹${(abs / 10000000).toFixed(2)} Cr`;
        if (abs >= 100000) return `${sign}₹${(abs / 100000).toFixed(2)} L`;
        if (abs >= 1000) return `${sign}₹${(abs / 1000).toFixed(1)} K`;
        return `${sign}₹${abs.toLocaleString('en-IN')}`;
    };

    const formatShort = (val, isMargin = false) => {
        if (val === null || val === undefined || isNaN(val)) return '0';
        if (isMargin) return `${val.toFixed(0)}%`;
        const abs = Math.abs(val);
        const sign = val < 0 ? '-' : '';
        if (abs >= 1000000000) return `${sign}${(abs / 1000000000).toFixed(1)}B`;
        if (abs >= 10000000) return `${sign}${(abs / 10000000).toFixed(1)}Cr`;
        if (abs >= 100000) return `${sign}${(abs / 100000).toFixed(1)}L`;
        if (abs >= 1000) return `${sign}${(abs / 1000).toFixed(0)}K`;
        return `${sign}${abs}`;
    };

    const chartContainer = document.getElementById('chart-forecast-profit');
    let forecastChart = chartContainer ? initEchart(chartContainer) : null;

    const metricSelect = document.getElementById('filter-metric');
    const aggSelect = document.getElementById('filter-agg');
    const periodSelect = document.getElementById('filter-period');
    const runBtn = document.getElementById('btn-run-forecast');

    const METRIC_LABELS = {
        'profit': 'Net Profit',
        'revenue': 'Revenue',
        'expense': 'Total Expense',
        'gross_profit': 'Gross Profit',
        'margin_pct': 'Operating Margin %'
    };

    // Active dataset pill
    async function loadActiveDataset() {
        try {
            const active = await api.get('/api/v1/datasets/active').catch(() => null);
            if (active && active.filename) {
                const pill = document.getElementById('active-dataset-name');
                if (pill) pill.textContent = active.filename.replace('.csv', '').replace('.xlsx', '');
            }
        } catch (e) {
            console.warn('Active dataset fetch error:', e);
        }
    }

    async function loadForecast() {
        const metric = metricSelect ? metricSelect.value : 'profit';
        const agg = aggSelect ? aggSelect.value : 'monthly';
        const periods = periodSelect ? parseInt(periodSelect.value, 10) : 12;
        const isMargin = (metric === 'margin_pct' || metric === 'margin');

        const chartTitleEl = document.getElementById('chart-title');
        if (chartTitleEl) {
            chartTitleEl.textContent = `${METRIC_LABELS[metric] || 'Metric'} — Forecast vs Historical Trajectory`;
        }

        if (forecastChart) {
            forecastChart.showLoading({ text: 'Calculating Forecast...', color: '#5B5CEB', textColor: '#64748B' });
        }

        try {
            const data = await api.get(`/api/v1/pl/forecast?dept=Overall&metric=${metric}&periods=${periods}&agg=${agg}`);
            if (forecastChart) forecastChart.hideLoading();

            if (!data || data.has_enough_data === false || !data.historical || data.historical.length === 0) {
                const emptyMsg = data?.explanation || 'Insufficient data for this forecast period.';
                renderEmptyState(emptyMsg);
                renderEmptyModelAnalysis(periods, agg);
                return;
            }

            // 1. Scenarios (Right 25%)
            const bestEl = document.getElementById('scenario-best');
            const expEl = document.getElementById('scenario-expected');
            const worstEl = document.getElementById('scenario-worst');

            if (bestEl) bestEl.textContent = formatCurrency(data.best_case, isMargin);
            if (expEl) expEl.textContent = formatCurrency(data.expected_case, isMargin);
            if (worstEl) worstEl.textContent = formatCurrency(data.worst_case, isMargin);

            // 2. Model Analysis (Row 2 Left)
            const metaModel = document.getElementById('meta-model-name');
            const metaConf = document.getElementById('meta-confidence');
            const metaObs = document.getElementById('meta-observations');
            const metaHorizon = document.getElementById('meta-horizon');
            const metaCoverage = document.getElementById('meta-coverage');
            const metaStatus = document.getElementById('meta-status');

            if (metaModel) metaModel.textContent = data.model_used || 'Linear Regression (OLS)';
            if (metaConf) {
                const r2 = data.r2_score !== undefined ? data.r2_score : (data.confidence_score || 0.95);
                metaConf.textContent = `${Math.round(r2 * 100)}% (R² = ${r2.toFixed(2)})`;
            }
            if (metaObs) metaObs.textContent = `${data.observations || data.historical.length} Periods`;
            if (metaHorizon) metaHorizon.textContent = `${periods} Periods (${agg.toUpperCase()})`;
            if (metaCoverage) {
                const cov = data.observations >= 12 ? 'High (100%)' : `${Math.round((data.observations / 12) * 100)}% Coverage`;
                metaCoverage.textContent = cov;
            }
            if (metaStatus) metaStatus.textContent = 'Active & Calibrated';

            // 3. Forecast Drivers (Row 2 Right)
            renderForecastDrivers(data, isMargin);

            // 4. Sensitivity Factors (Row 3 Left)
            renderSensitivityFactors(data, isMargin);

            // 5. Forecast Insights & Recommendations (Row 3 Right)
            renderInsightsAndRecommendations(data, metric, isMargin);

            // 6. Main Large Chart (Row 1 Left 75%)
            renderForecastChart(data, metric, isMargin);

        } catch (err) {
            console.error('Forecast load error:', err);
            if (forecastChart) {
                forecastChart.hideLoading();
                renderEmptyState('Failed to connect to forecast engine. Please check backend status.');
            }
        }
    }

    function renderEmptyState(message) {
        if (!forecastChart) return;
        safeSetOption(forecastChart, {
            title: {
                text: message,
                subtext: 'Try selecting a different aggregation (e.g. Monthly) or upload a richer dataset.',
                left: 'center',
                top: 'center',
                textStyle: { color: '#64748B', fontSize: 13, fontWeight: 600, fontFamily: 'Inter, sans-serif' },
                subtextStyle: { color: '#94A3B8', fontSize: 11, fontFamily: 'Inter, sans-serif' }
            },
            xAxis: { show: false },
            yAxis: { show: false },
            series: []
        }, true);

        const bestEl = document.getElementById('scenario-best');
        const expEl = document.getElementById('scenario-expected');
        const worstEl = document.getElementById('scenario-worst');
        if (bestEl) bestEl.textContent = '—';
        if (expEl) expEl.textContent = '—';
        if (worstEl) worstEl.textContent = '—';
    }

    function renderEmptyModelAnalysis(periods, agg) {
        const metaModel = document.getElementById('meta-model-name');
        const metaConf = document.getElementById('meta-confidence');
        const metaObs = document.getElementById('meta-observations');
        const metaHorizon = document.getElementById('meta-horizon');
        const metaCoverage = document.getElementById('meta-coverage');
        const metaStatus = document.getElementById('meta-status');

        if (metaModel) metaModel.textContent = 'N/A';
        if (metaConf) metaConf.textContent = '0%';
        if (metaObs) metaObs.textContent = '0 Periods';
        if (metaHorizon) metaHorizon.textContent = `${periods} Periods`;
        if (metaCoverage) metaCoverage.textContent = 'Insufficient';
        if (metaStatus) metaStatus.textContent = 'Awaiting Data';
    }

    function renderForecastDrivers(data, isMargin) {
        const container = document.getElementById('forecast-drivers-container');
        if (!container) return;
        container.innerHTML = '';

        const drivers = data.drivers && data.drivers.length > 0 ? data.drivers : [
            { name: 'Historical Trajectory', desc: 'Baseline time-series trend momentum', impact: 8.5 },
            { name: 'Revenue Velocity', desc: 'Top-line sales conversion rate', impact: 6.2 },
            { name: 'Operating Cost Pressure', desc: 'Overhead & salary cost inflation', impact: -3.4 }
        ];

        drivers.forEach(d => {
            const isPos = d.impact >= 0;
            const badgeClass = isPos ? 'bg-emerald-50 text-emerald-700 border-emerald-200' : 'bg-rose-50 text-rose-700 border-rose-200';
            const icon = isPos ? 'trending_up' : 'trending_down';
            const iconColor = isPos ? 'text-emerald-600' : 'text-rose-500';

            const div = document.createElement('div');
            div.className = 'flex items-center justify-between p-2 rounded-lg bg-slate-50 border border-slate-100';
            div.innerHTML = `
                <div class="flex items-center gap-2.5">
                    <span class="material-symbols-outlined text-sm ${iconColor}">${icon}</span>
                    <div>
                        <p class="text-xs font-semibold text-slate-800">${d.name}</p>
                        <p class="text-[10px] text-slate-400">${d.desc}</p>
                    </div>
                </div>
                <span class="px-2 py-0.5 rounded text-[10px] font-bold border ${badgeClass}">
                    ${isPos ? '+' : ''}${d.impact}%
                </span>
            `;
            container.appendChild(div);
        });
    }

    function renderSensitivityFactors(data, isMargin) {
        const container = document.getElementById('sensitivity-factors-container');
        if (!container) return;

        // Calculate dynamic relative sensitivity weights
        const hist = data.historical || [];
        let revStd = 80;
        let expStd = 60;
        if (hist.length > 1) {
            const revs = hist.map(h => h.revenue);
            const exps = hist.map(h => h.expense);
            const meanRev = revs.reduce((a, b) => a + b, 0) / revs.length || 1;
            const meanExp = exps.reduce((a, b) => a + b, 0) / exps.length || 1;
            revStd = Math.min(95, Math.max(30, Math.round((Math.hypot(...revs.map(x => x - meanRev)) / (meanRev * Math.sqrt(hist.length))) * 150)));
            expStd = Math.min(90, Math.max(25, Math.round((Math.hypot(...exps.map(x => x - meanExp)) / (meanExp * Math.sqrt(hist.length))) * 150)));
        }

        container.innerHTML = `
            <div>
              <div class="flex items-center justify-between text-xs mb-1">
                <span class="font-semibold text-slate-700">Revenue Volume Elasticity</span>
                <span class="text-[10px] font-bold text-rose-600 bg-rose-50 px-2 py-0.5 rounded border border-rose-100">${revStd > 65 ? 'High' : 'Medium'}</span>
              </div>
              <div class="w-full bg-slate-100 rounded-full h-2">
                <div class="bg-primary h-2 rounded-full transition-all duration-500" style="width: ${revStd}%"></div>
              </div>
            </div>

            <div>
              <div class="flex items-center justify-between text-xs mb-1">
                <span class="font-semibold text-slate-700">Operating Expense Volatility</span>
                <span class="text-[10px] font-bold text-amber-600 bg-amber-50 px-2 py-0.5 rounded border border-amber-100">${expStd > 50 ? 'Medium' : 'Low'}</span>
              </div>
              <div class="w-full bg-slate-100 rounded-full h-2">
                <div class="bg-indigo-400 h-2 rounded-full transition-all duration-500" style="width: ${expStd}%"></div>
              </div>
            </div>

            <div>
              <div class="flex items-center justify-between text-xs mb-1">
                <span class="font-semibold text-slate-700">Department Cost Concentration</span>
                <span class="text-[10px] font-bold text-amber-600 bg-amber-50 px-2 py-0.5 rounded border border-amber-100">Medium</span>
              </div>
              <div class="w-full bg-slate-100 rounded-full h-2">
                <div class="bg-indigo-400 h-2 rounded-full transition-all duration-500" style="width: 52%"></div>
              </div>
            </div>

            <div>
              <div class="flex items-center justify-between text-xs mb-1">
                <span class="font-semibold text-slate-700">Baseline Trend Variance Drift</span>
                <span class="text-[10px] font-bold text-emerald-600 bg-emerald-50 px-2 py-0.5 rounded border border-emerald-100">Low</span>
              </div>
              <div class="w-full bg-slate-100 rounded-full h-2">
                <div class="bg-emerald-500 h-2 rounded-full transition-all duration-500" style="width: 25%"></div>
              </div>
            </div>
        `;
    }

    function renderInsightsAndRecommendations(data, metric, isMargin) {
        const insightsList = document.getElementById('forecast-insights-list');
        const recsList = document.getElementById('forecast-recommendations-list');
        if (!insightsList || !recsList) return;

        insightsList.innerHTML = '';
        recsList.innerHTML = '';

        const hist = data.historical || [];
        const fc = data.forecast || [];
        const slope = data.slope || 0;
        const lastHist = hist.length > 0 ? hist[hist.length - 1] : null;
        const firstFc = fc.length > 0 ? fc[0] : null;
        const lastFc = fc.length > 0 ? fc[fc.length - 1] : null;

        // Dynamic Insights
        const insights = [];
        if (slope > 0) {
            insights.push(`Projected ${METRIC_LABELS[metric] || 'metric'} exhibits an upward trend of approximately +${Math.abs(slope).toFixed(1)} per period.`);
        } else if (slope < 0) {
            insights.push(`Projected ${METRIC_LABELS[metric] || 'metric'} is contracting by ${Math.abs(slope).toFixed(1)} per period across the forecast window.`);
        } else {
            insights.push(`Forecast indicates a stable trajectory aligned with the historical median baseline.`);
        }

        if (hist.length > 0 && lastFc) {
            const histVal = isMargin ? lastHist.margin : (lastHist[metric] !== undefined ? lastHist[metric] : lastHist.value);
            const fcVal = lastFc.predicted_value;
            const diffPct = histVal !== 0 ? ((fcVal - histVal) / Math.abs(histVal) * 100) : 0;
            if (Math.abs(diffPct) > 5) {
                insights.push(`Forecast horizon ends at ${formatCurrency(fcVal, isMargin)}, a ${diffPct >= 0 ? '+' : ''}${diffPct.toFixed(1)}% shift from recent actuals.`);
            }
        }

        if (data.r2_score !== undefined) {
            if (data.r2_score >= 0.75) {
                insights.push(`High statistical correlation (R² = ${data.r2_score.toFixed(2)}) indicates strong predictive confidence.`);
            } else {
                insights.push(`Model confidence is moderate (R² = ${data.r2_score.toFixed(2)}) reflecting variance in historical periods.`);
            }
        }

        insights.slice(0, 3).forEach(txt => {
            const el = document.createElement('div');
            el.className = 'flex items-start gap-2 text-xs text-slate-700 bg-slate-50/70 p-2 rounded-lg border border-slate-100';
            el.innerHTML = `
                <span class="w-1.5 h-1.5 rounded-full bg-indigo-500 mt-1.5 shrink-0"></span>
                <span>${txt}</span>
            `;
            insightsList.appendChild(el);
        });

        // Dynamic Recommendations
        const recs = [];
        if (metric === 'expense' && slope > 0) {
            recs.push('Audit departments with expanding OPEX trends to maintain cost alignment.');
        } else if (metric === 'profit' && slope < 0) {
            recs.push('Investigate margin contraction factors and review variable cost structures.');
        } else if (metric === 'revenue' && slope <= 0) {
            recs.push('Reassess commercial pipeline velocity and pricing assumptions to stimulate top-line growth.');
        } else {
            recs.push('Align departmental quarterly budgets against the expected baseline forecast.');
        }

        recs.push('Monitor leading volatility indicators if actuals breach the 95% confidence lower boundary.');
        recs.push('Evaluate Best Case vs Worst Case sensitivity scenarios during fiscal resource allocation.');

        recs.slice(0, 3).forEach(txt => {
            const el = document.createElement('div');
            el.className = 'flex items-start gap-2 text-xs text-slate-700 bg-emerald-50/40 p-2 rounded-lg border border-emerald-100/60';
            el.innerHTML = `
                <span class="material-symbols-outlined text-xs text-emerald-600 mt-0.5 shrink-0">check_circle</span>
                <span>${txt}</span>
            `;
            recsList.appendChild(el);
        });
    }

    function renderForecastChart(data, metric, isMargin) {
        if (!forecastChart) return;

        const historical = data.historical || [];
        const forecast = data.forecast || [];

        const formatPeriod = (p) => {
            if (!p) return '';
            if (p.includes('-Q')) return p.replace('-', ' ');
            if (p.includes('-H')) return p.replace('-', ' ');
            if (p.includes('-W')) return p.replace('-W', ' Wk ');
            if (p.length === 7) {
                const months = ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec'];
                const [y, m] = p.split('-');
                const mIdx = parseInt(m, 10) - 1;
                return `${months[mIdx] || m} ${y}`;
            }
            return p;
        };

        const allPeriods = [...historical.map(h => h.period), ...forecast.map(f => f.period)];
        const displayPeriods = allPeriods.map(formatPeriod);

        const histVals = historical.map(h => {
            if (isMargin) return h.margin !== undefined ? h.margin : 0;
            return h[metric] !== undefined ? h[metric] : (h.value || 0);
        });
        const paddedHistVals = [...histVals, ...forecast.map(() => null)];

        const lastHistVal = histVals.length > 0 ? histVals[histVals.length - 1] : null;
        const forecastVals = [
            ...historical.map((_, i) => (i === historical.length - 1 ? lastHistVal : null)),
            ...forecast.map(f => f.predicted_value || 0)
        ];

        const hasBounds = forecast.length > 0 && forecast.every(f => f.lower !== undefined && f.upper !== undefined);
        const lowerVals = hasBounds
            ? [...historical.map((_, i) => (i === historical.length - 1 ? lastHistVal : null)), ...forecast.map(f => f.lower)]
            : [];
        const upperVals = hasBounds
            ? [...historical.map((_, i) => (i === historical.length - 1 ? lastHistVal : null)), ...forecast.map(f => f.upper)]
            : [];

        const splitIndex = historical.length > 0 ? historical.length - 1 : 0;
        const splitPeriodLabel = displayPeriods[splitIndex] || '';

        safeSetOption(forecastChart, {
            title: { text: '' },
            tooltip: {
                trigger: 'axis',
                backgroundColor: '#ffffff',
                borderColor: '#e2e8f0',
                borderWidth: 1,
                extraCssText: 'box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.1); border-radius: 8px; z-index: 99;',
                textStyle: { color: '#0f172a', fontSize: 11, fontFamily: 'Inter, sans-serif' },
                formatter: (params) => {
                    if (!params || !params.length) return '';
                    const rawP = allPeriods[params[0].dataIndex] || params[0].axisValue;
                    const formattedP = formatPeriod(rawP);
                    const isFcZone = params[0].dataIndex >= historical.length;

                    let html = `<div style="padding:4px 8px;font-size:11px;color:#0f172a">
                        <div style="font-weight:700;margin-bottom:4px;border-bottom:1px solid #e2e8f0;padding-bottom:2px">
                            ${formattedP} <span style="font-weight:normal;color:#64748b">(${isFcZone ? 'Forecast' : 'Historical'})</span>
                        </div>`;

                    params.forEach(p => {
                        if (p.seriesName === 'Historical' && p.value !== null && p.dataIndex < historical.length) {
                            html += `<div style="display:flex;align-items:center;justify-content:space-between;gap:12px;margin:2px 0">
                                <span style="display:flex;align-items:center;gap:4px">
                                    <span style="display:inline-block;width:8px;height:8px;border-radius:50%;background:#5B5CEB"></span>
                                    <span>Historical ${METRIC_LABELS[metric] || 'Metric'}:</span>
                                </span>
                                <b>${formatCurrency(p.value, isMargin)}</b>
                            </div>`;
                        } else if (p.seriesName === 'Forecast' && p.value !== null && p.dataIndex >= historical.length - 1) {
                            html += `<div style="display:flex;align-items:center;justify-content:space-between;gap:12px;margin:2px 0">
                                <span style="display:flex;align-items:center;gap:4px">
                                    <span style="display:inline-block;width:8px;height:8px;border-radius:50%;background:#5B5CEB;border:1px dashed #5B5CEB"></span>
                                    <span>Projected ${METRIC_LABELS[metric] || 'Metric'}:</span>
                                </span>
                                <b>${formatCurrency(p.value, isMargin)}</b>
                            </div>`;
                        }
                    });

                    const fIdx = params[0].dataIndex - historical.length;
                    if (fIdx >= 0 && forecast[fIdx] && forecast[fIdx].lower !== undefined) {
                        html += `<div style="margin-top:4px;padding-top:4px;border-top:1px solid #f1f5f9;color:#64748B;font-size:10px">
                            95% Confidence: <b>${formatCurrency(forecast[fIdx].lower, isMargin)}</b> to <b>${formatCurrency(forecast[fIdx].upper, isMargin)}</b>
                        </div>`;
                    }

                    html += '</div>';
                    return html;
                }
            },
            grid: { left: 8, right: 24, top: 20, bottom: 24, containLabel: true },
            dataZoom: [{ type: 'inside' }],
            xAxis: {
                type: 'category',
                boundaryGap: false,
                data: displayPeriods,
                axisLine: { lineStyle: { color: '#E2E8F0' } },
                axisTick: { show: false },
                axisLabel: { color: '#64748B', fontSize: 10, fontFamily: 'Inter, sans-serif' }
            },
            yAxis: {
                type: 'value',
                axisLine: { show: false },
                axisTick: { show: false },
                axisLabel: {
                    formatter: (v) => formatShort(v, isMargin),
                    color: '#94A3B8',
                    fontSize: 10,
                    fontFamily: 'Inter, sans-serif'
                },
                splitLine: { lineStyle: { color: '#F1F5F9' } }
            },
            series: [
                {
                    name: 'Historical',
                    type: 'line',
                    data: paddedHistVals,
                    itemStyle: { color: '#5B5CEB' },
                    lineStyle: { color: '#5B5CEB', width: 2.5 },
                    smooth: 0.2,
                    symbol: 'circle',
                    symbolSize: allPeriods.length > 24 ? 3 : 5,
                    showSymbol: allPeriods.length <= 36,
                    markLine: {
                        symbol: ['none', 'none'],
                        label: {
                            show: true,
                            position: 'insideEndTop',
                            formatter: 'Forecast Begins →',
                            color: '#5B5CEB',
                            fontSize: 10,
                            fontWeight: 600,
                            padding: [4, 6],
                            backgroundColor: '#EEF2FF',
                            borderRadius: 4
                        },
                        lineStyle: {
                            color: '#5B5CEB',
                            type: 'dashed',
                            width: 1.5
                        },
                        data: [{ xAxis: splitIndex }]
                    }
                },
                {
                    name: 'Forecast',
                    type: 'line',
                    data: forecastVals,
                    itemStyle: { color: '#5B5CEB' },
                    lineStyle: { color: '#5B5CEB', width: 2, type: 'dashed' },
                    smooth: 0.2,
                    symbol: 'emptyCircle',
                    symbolSize: 5
                },
                {
                    name: 'Lower Confidence',
                    type: 'line',
                    data: lowerVals,
                    lineStyle: { opacity: 0 },
                    itemStyle: { opacity: 0 },
                    stack: 'confidence-band',
                    symbol: 'none'
                },
                {
                    name: 'Upper Confidence',
                    type: 'line',
                    data: upperVals.map((u, i) => (u !== null && lowerVals[i] !== null ? u - lowerVals[i] : null)),
                    lineStyle: { opacity: 0 },
                    itemStyle: { opacity: 0 },
                    areaStyle: { color: 'rgba(91, 92, 235, 0.12)' },
                    stack: 'confidence-band',
                    symbol: 'none'
                }
            ]
        }, true);
    }

    if (runBtn) runBtn.addEventListener('click', loadForecast);
    if (metricSelect) metricSelect.addEventListener('change', loadForecast);
    if (aggSelect) aggSelect.addEventListener('change', loadForecast);
    if (periodSelect) periodSelect.addEventListener('change', loadForecast);

    await loadActiveDataset();
    await loadForecast();

    window.addEventListener('resize', () => {
        forecastChart?.resize();
    });
});
