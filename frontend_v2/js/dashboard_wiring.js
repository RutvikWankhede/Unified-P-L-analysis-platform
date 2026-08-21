import { generatePalette, initEchart, safeSetOption } from './chart-engine.js';
import { api } from './api.js';

document.addEventListener('DOMContentLoaded', () => {
    // 1. Currency Formatter
    const formatCurrency = (val) => {
        const currency = document.getElementById('global-currency') ? document.getElementById('global-currency').value : 'INR';
        const isUSD = currency === 'USD';
        const isEUR = currency === 'EUR';
        
        let rate = 1;
        if (isUSD) rate = 83;
        if (isEUR) rate = 90;
        
        const sym = isUSD ? '$' : isEUR ? '€' : '₹';
        if (!val && val !== 0) return `${sym}0`;
        
        val = val / rate;
        
        if (isUSD || isEUR) {
            if (val >= 1000000) return `${sym}${(val / 1000000).toFixed(2)}M`;
            if (val >= 1000) return `${sym}${(val / 1000).toFixed(1)}K`;
            return `${sym}${val.toLocaleString(isUSD ? 'en-US' : 'de-DE', {maximumFractionDigits: 0})}`;
        } else {
            if (val >= 10000000) return `${sym}${(val / 10000000).toFixed(2)} Cr`;
            if (val >= 100000) return `${sym}${(val / 100000).toFixed(2)} L`;
            return `${sym}${val.toLocaleString('en-IN', {maximumFractionDigits: 0})}`;
        }
    };

    // 2. Animated Counter
    function animateValue(obj, start, end, duration, formatFn = (v) => v) {
        let startTimestamp = null;
        const step = (timestamp) => {
            if (!startTimestamp) startTimestamp = timestamp;
            const progress = Math.min((timestamp - startTimestamp) / duration, 1);
            // easeOutQuart
            const easeProgress = 1 - Math.pow(1 - progress, 4);
            obj.innerHTML = formatFn(start + easeProgress * (end - start));
            if (progress < 1) {
                window.requestAnimationFrame(step);
            } else {
                obj.innerHTML = formatFn(end);
            }
        };
        window.requestAnimationFrame(step);
    }

    // 3. ECharts Common Toolbox
    const getStandardToolbox = () => ({
        show: true,
        feature: {
            dataZoom: { yAxisIndex: 'none', title: { zoom: 'Zoom', back: 'Reset Zoom' } },
            restore: { title: 'Reset' },
            saveAsImage: { type: 'png', title: 'Save PNG' }
        },
        right: 0,
        top: 0
    });
    const standardDataZoom = [
        { type: 'inside', xAxisIndex: [0] },
        { type: 'slider', xAxisIndex: [0], bottom: 0, height: 15 }
    ];

    let dashboardCharts = {};

    function initCharts() {
        const ids = [
            'chart-rev-exp-profit', 'chart-anomaly-overview', 'chart-dept-performance',
            'chart-expense-dist', 'chart-forecast-actual', 'chart-cash-flow', 'chart-budget-actual',
            'sparkline-revenue', 'sparkline-expense', 'sparkline-profit', 'sparkline-margin',
            'sparkline-cash-flow', 'sparkline-forecast', 'sparkline-health'
        ];
        ids.forEach(id => {
            const el = document.getElementById(id);
            if (el) dashboardCharts[id] = initEchart(el);
        });
    }

    // 4. Chart Loaders
    async function loadKPIs() {
        const currency = document.getElementById('global-currency').value;
        const res = await api.get(`/api/v1/pl/summary?currency=${currency}&agg=yearly`).catch(() => null);
        if (!res || !res.kpis) return;
        const k = res.kpis;
        const caps = res.capabilities || {};

        const updateKpi = (id, value, trend, isCurrency = true, available = true) => {
            const container = document.getElementById(`kpi-${id}`);
            if (!container) return;
            const valEl = container.querySelector('.kpi-value');
            const trendEl = container.querySelector('.kpi-trend');
            
            if (valEl) {
                if (!available || value === null || value === undefined) {
                    valEl.innerText = 'Not available';
                    valEl.style.fontSize = '16px';
                    valEl.style.color = '#94a3b8';
                    if (trendEl) trendEl.style.display = 'none';
                    return;
                }
                valEl.style.fontSize = '';
                valEl.style.color = '';
                if (trendEl) trendEl.style.display = '';

                const formatFn = isCurrency ? formatCurrency : (v) => id === 'health' ? Math.round(v) + '/100' : v.toFixed(1) + '%';
                const currentVal = parseFloat(valEl.dataset.target) || 0;
                valEl.dataset.target = value;
                animateValue(valEl, currentVal, value, 1000, formatFn);
            }
            if (trendEl && trend !== undefined) {
                const icon = trend >= 0 ? 'arrow_upward' : 'arrow_downward';
                const colorClass = id === 'expense' ? (trend > 0 ? 'text-danger' : 'text-success') : (trend >= 0 ? 'text-success' : 'text-danger');
                trendEl.className = `text-[10px] ${colorClass} font-bold flex items-center z-10 kpi-trend`;
                trendEl.innerHTML = `<span class="material-symbols-outlined text-[12px]">${icon}</span> <span>${Math.abs(trend).toFixed(1)}%</span> <span class="text-slate-400 font-normal ml-1">vs prior</span>`;
            }
        };

        const hasRev = caps.revenue?.available !== false;
        const hasExp = caps.expense?.available !== false;
        const hasProf = caps.profit?.available !== false;
        const hasMargin = caps.margin?.available !== false;
        const hasCF = caps.cashFlow?.available !== false;
        const hasBudget = caps.budget?.available !== false;

        const cfVal = k.cash_flow !== null && k.cash_flow !== undefined ? k.cash_flow : (hasRev && hasExp ? k.profit : null);
        const cfMode = caps.cashFlow?.mode || (hasRev && hasExp ? 'estimated' : 'unavailable');
        const cfContainer = document.getElementById('kpi-cash-flow');
        if (cfContainer) {
            const cfHeaderEl = cfContainer.querySelector('.kpi-header');
            if (cfHeaderEl) {
                cfHeaderEl.innerHTML = (cfMode === 'estimated' ? 'Estimated Cash Flow' : 'Cash Flow') + ' <span class="material-symbols-outlined" style="color: var(--color-accent-teal);">account_balance_wallet</span>';
            }
        }
        updateKpi('cash-flow', cfVal, 2.1, true, cfMode !== 'unavailable');
        
        const fcstVal = k.forecasted_profit !== null && k.forecasted_profit !== undefined ? k.forecasted_profit : null;
        updateKpi('forecast', fcstVal, 4.5, true, fcstVal !== null);
        updateKpi('health', k.health_score || 85, 0.5, false, true);

        if (document.querySelector('.header-health-score')) {
            document.querySelector('.header-health-score').innerText = `Evaluating... ${Math.round(k.health_score || 85)}`;
        }
        
        if (caps.has_departments === false) {
            const deptDropdown = document.getElementById('ctrl-rev-dept');
            if (deptDropdown) {
                deptDropdown.value = 'all';
                deptDropdown.disabled = true;
                deptDropdown.title = 'Department breakdown is not available for this dataset.';
            }
        }
        const drawSparkline = (id, data, color, available = true) => {
            if (!dashboardCharts[`sparkline-${id}`]) return;
            if (!available || !data || data.length === 0) {
                setChartError(`sparkline-${id}`, 'N/A');
                return;
            }
            clearChartError(`sparkline-${id}`);
            safeSetOption(dashboardCharts[`sparkline-${id}`], {
                grid: { top: 2, bottom: 2, left: 2, right: 2 },
                xAxis: { type: 'category', show: false, data: data.map((_, i) => i) },
                yAxis: { type: 'value', show: false, scale: true },
                series: [{
                    type: 'line', data: data, smooth: true, showSymbol: false,
                    lineStyle: { color: color, width: 2 },
                    areaStyle: {
                        color: new echarts.graphic.LinearGradient(0, 0, 0, 1, [
                            { offset: 0, color: color }, { offset: 1, color: 'rgba(255,255,255,0)' }
                        ])
                    }
                }]
            });
        };
        const chartsRes = await api.get(`/api/v1/pl/charts?currency=${currency}&agg=yearly`).catch(() => null);
        const revTrend = (hasRev && chartsRes?.revenue_trend) ? chartsRes.revenue_trend.map(d => d.value) : [];
        const expTrend = (hasExp && chartsRes?.expense_trend) ? chartsRes.expense_trend.map(d => d.value) : [];
        const profTrend = (hasProf && revTrend.length) ? revTrend.map((v, i) => v - (expTrend[i] || 0)) : [];
        const cashFlowTrend = chartsRes?.cashflow_trend ? chartsRes.cashflow_trend.map(d => d.value) : [];
        const budgetTrend = chartsRes?.budget_trend ? chartsRes.budget_trend.map(d => d.variance) : [];
        drawSparkline('revenue', revTrend, '#3b82f6', hasRev);
        drawSparkline('expense', expTrend, '#ef4444', hasExp);
        drawSparkline('profit', profTrend, '#10b981', hasProf);
        drawSparkline('margin', hasMargin ? profTrend.map((p, i) => revTrend[i] ? p/revTrend[i] : 0) : [], '#10b981', hasMargin);
        drawSparkline('cash-flow', cashFlowTrend, '#06b6d4', cashFlowTrend.length > 0);
        drawSparkline('forecast', [], '#a855f7', false); // removed fake forecast sparkline
        drawSparkline('health', hasProf ? profTrend.map(p => p*0.5) : [], '#6366f1', true);
    }

    async function loadRevExpProfit() {
        const dept = document.getElementById('ctrl-rev-dept').value;
        const agg = document.getElementById('ctrl-rev-agg').value;
        const currency = document.getElementById('global-currency').value;
        
        dashboardCharts['chart-rev-exp-profit'].showLoading();
        const res = await api.get(`/api/v1/pl/charts?dept=${dept}&agg=${agg}&currency=${currency}`).catch(() => null);
        dashboardCharts['chart-rev-exp-profit'].hideLoading();
        
        if (!res || !res.periods) return;
        
        const labels = res.periods;
        const hasRev = res.revenue_trend && res.revenue_trend.length > 0;
        const hasExp = res.expense_trend && res.expense_trend.length > 0;
        const hasProf = res.profit_trend && res.profit_trend.length > 0;
        
        const rev = hasRev ? res.revenue_trend.map(d => d.value) : [];
        const exp = hasExp ? res.expense_trend.map(d => d.value) : [];
        const prof = hasProf ? res.profit_trend.map(d => d.value) : [];
        
        const series = [];
        if (hasRev) {
            series.push({
                name: 'Revenue', type: 'line', smooth: true,
                itemStyle: { color: '#3b82f6' },
                areaStyle: { opacity: 0.05, color: '#3b82f6' },
                data: rev
            });
        }
        if (hasExp) {
            series.push({
                name: 'Expense', type: 'line', smooth: true,
                itemStyle: { color: '#ef4444' },
                areaStyle: { opacity: 0.05, color: '#ef4444' },
                data: exp
            });
        }
        if (hasProf) {
            series.push({
                name: 'Net Profit', type: 'line', smooth: true,
                itemStyle: { color: '#10b981' },
                areaStyle: { opacity: 0.05, color: '#10b981' },
                data: prof
            });
        }
        
        if (series.length === 0) {
            setChartError('chart-rev-exp-profit', 'Expense and Profit cannot be displayed because the uploaded dataset does not contain sufficient information.');
            return;
        }
        clearChartError('chart-rev-exp-profit');
        
        safeSetOption(dashboardCharts['chart-rev-exp-profit'], {
            tooltip: { trigger: 'axis', axisPointer: { type: 'cross' } },
            legend: { top: 0, icon: 'circle' },
            grid: { left: '3%', right: '4%', bottom: '15%', containLabel: true },
            toolbox: getStandardToolbox(),
            dataZoom: standardDataZoom,
            xAxis: { type: 'category', boundaryGap: false, data: labels },
            yAxis: { type: 'value', axisLabel: { formatter: (val) => formatCurrency(val) } },
            series: series
        });
    }

    async function loadAnomalyOverview() {
        const agg = document.getElementById('ctrl-anom-agg').value;
        const currency = document.getElementById('global-currency').value;
        dashboardCharts['chart-anomaly-overview'].showLoading();
        const res = await api.get(`/api/v1/anomalies/?agg=${agg}&currency=${currency}`).catch(() => []);
        dashboardCharts['chart-anomaly-overview'].hideLoading();
        
        const counts = { Critical: 0, High: 0, Medium: 0, Low: 0 };
        res.forEach(a => counts[a.severity]++);
        const data = [
            { value: counts.Critical, name: 'Critical', itemStyle: { color: '#ef4444' } },
            { value: counts.High, name: 'High', itemStyle: { color: '#f97316' } },
            { value: counts.Medium, name: 'Medium', itemStyle: { color: '#eab308' } },
            { value: counts.Low, name: 'Low', itemStyle: { color: '#3b82f6' } }
        ].filter(d => d.value > 0);
        
        const total = data.reduce((sum, d) => sum + d.value, 0);

        safeSetOption(dashboardCharts['chart-anomaly-overview'], {
            tooltip: { trigger: 'item' },
            legend: { bottom: 0, icon: 'circle', itemWidth: 8, itemHeight: 8, textStyle: { fontSize: 10 } },
            toolbox: { show: true, feature: { saveAsImage: { title: 'Save' } } },
            series: [
                {
                    type: 'pie',
                    radius: ['50%', '70%'],
                    center: ['50%', '45%'],
                    avoidLabelOverlap: false,
                    label: { show: false, position: 'center' },
                    emphasis: {
                        label: { show: true, fontSize: 14, fontWeight: 'bold' }
                    },
                    labelLine: { show: false },
                    data: data.length ? data : [{value: 1, name: 'No Anomalies', itemStyle: {color: '#f1f5f9'}}]
                }
            ]
        });
    }

    async function loadDeptPerformance() {
        const metric = document.getElementById('ctrl-dept-metric').value; // profit, revenue, expense, margin
        const limit = document.getElementById('ctrl-dept-limit').value;
        const currency = document.getElementById('global-currency').value;
        
        let resData = await api.get(`/api/v1/pl/departments/summary?currency=${currency}`).catch(() => ({departments: []}));
        let res = resData.departments || [];
        dashboardCharts['chart-dept-performance'].hideLoading();
        
        if (metric === 'profit') res.sort((a,b) => b.profit - a.profit);
        else if (metric === 'revenue') res.sort((a,b) => b.revenue - a.revenue);
        else if (metric === 'expense') res.sort((a,b) => b.expense - a.expense);
        else if (metric === 'margin') res.sort((a,b) => {
            const marginA = a.revenue > 0 ? (a.profit / a.revenue) : 0;
            const marginB = b.revenue > 0 ? (b.profit / b.revenue) : 0;
            return marginB - marginA;
        });

        if (limit !== 'all') res = res.slice(0, parseInt(limit));
        
        const names = res.map(d => d.department);
        const data = res.map(d => {
            if (metric === 'profit') return d.profit;
            if (metric === 'revenue') return d.revenue;
            if (metric === 'expense') return d.expense;
            if (metric === 'margin') return d.revenue > 0 ? (d.profit / d.revenue * 100).toFixed(1) : '0.0';
        });

        safeSetOption(dashboardCharts['chart-dept-performance'], {
            tooltip: { trigger: 'axis', axisPointer: { type: 'shadow' } },
            grid: { left: '3%', right: '4%', bottom: '5%', containLabel: true },
            toolbox: getStandardToolbox(),
            xAxis: { type: 'value', axisLabel: { formatter: (val) => metric === 'margin' ? val+'%' : formatCurrency(val) } },
            yAxis: { type: 'category', data: names, inverse: true },
            series: [
                {
                    name: metric.charAt(0).toUpperCase() + metric.slice(1),
                    type: 'bar',
                    barMaxWidth: 20,
                    itemStyle: { color: '#6366f1', borderRadius: [0, 4, 4, 0] },
                    data: data
                }
            ]
        });
    }

    async function loadExpenseDist() {
        const metric = document.getElementById('ctrl-dist-metric').value; // expense, revenue
        const currency = document.getElementById('global-currency').value;
        
        const resData = await api.get(`/api/v1/pl/departments/summary?currency=${currency}`).catch(() => ({departments: []}));
        const res = resData.departments || [];
        dashboardCharts['chart-expense-dist'].hideLoading();
        
        const palette = generatePalette(res.length);
        const data = res.map((d, i) => ({
            name: d.department,
            value: metric === 'expense' ? d.expense : d.revenue,
            itemStyle: { color: palette[i] }
        })).sort((a,b) => b.value - a.value);

        safeSetOption(dashboardCharts['chart-expense-dist'], {
            tooltip: { trigger: 'item', formatter: (p) => `${p.name}: ${formatCurrency(p.value)} (${p.percent}%)` },
            legend: { type: 'scroll', orient: 'vertical', right: 0, top: 20, bottom: 20, textStyle: { fontSize: 10 } },
            toolbox: { show: true, feature: { saveAsImage: { title: 'Save' } }, right: 0, top: 0 },
            series: [
                {
                    name: metric === 'expense' ? 'Expense' : 'Revenue',
                    type: 'pie',
                    radius: ['40%', '70%'],
                    center: ['40%', '50%'],
                    itemStyle: { borderRadius: 4, borderColor: '#fff', borderWidth: 2 },
                    label: { show: false },
                    data: data
                }
            ]
        });
    }

    async function loadForecast() {
        const dept = document.getElementById('ctrl-fcst-dept').value;
        const agg = document.getElementById('ctrl-fcst-agg').value;
        const currency = document.getElementById('global-currency').value;
        
        dashboardCharts['chart-forecast-actual'].showLoading();
        const res = await api.get(`/api/v1/pl/forecast?dept=${dept}&agg=${agg}&currency=${currency}&metric=profit`).catch(() => null);
        dashboardCharts['chart-forecast-actual'].hideLoading();

        if (!res) return;
        if (res.has_enough_data === false || !res.historical || res.historical.length === 0) {
            setChartError('chart-forecast-actual', 'Forecast unavailable: The dataset does not contain enough historical observations for reliable forecasting.');
            return;
        }
        clearChartError('chart-forecast-actual');

        const hist = res.historical;
        const fcst = res.forecast;
        
        const labels = [...hist.map(d => d.period), ...fcst.map(d => d.period)];
        const actual = [...hist.map(d => d.profit !== undefined ? d.profit : d.value), ...fcst.map(d => null)];
        const forecast = [...hist.map(d => null), ...fcst.map(d => d.predicted_value || d.predicted_profit)];
        const lower = [...hist.map(d => null), ...fcst.map(d => (d.predicted_value || d.predicted_profit || 0) * 0.85)];
        const upper = [...hist.map(d => null), ...fcst.map(d => (d.predicted_value || d.predicted_profit || 0) * 1.15)];

        const bandData = lower.map((l, i) => upper[i] - l);

        safeSetOption(dashboardCharts['chart-forecast-actual'], {
            tooltip: { trigger: 'axis', axisPointer: { type: 'cross' } },
            legend: { top: 0, icon: 'circle' },
            grid: { left: '3%', right: '4%', bottom: '15%', containLabel: true },
            toolbox: getStandardToolbox(),
            dataZoom: standardDataZoom,
            xAxis: { type: 'category', boundaryGap: false, data: labels },
            yAxis: { type: 'value', axisLabel: { formatter: (val) => formatCurrency(val) } },
            series: [
                {
                    name: 'Actual Profit', type: 'line', smooth: true,
                    itemStyle: { color: '#3b82f6' }, data: actual
                },
                {
                    name: 'Forecast Profit', type: 'line', smooth: true,
                    lineStyle: { type: 'dashed' }, itemStyle: { color: '#8b5cf6' }, data: forecast
                },
                {
                    name: 'Lower Band', type: 'line', data: lower,
                    lineStyle: { opacity: 0 }, stack: 'confidence', symbol: 'none'
                },
                {
                    name: 'Confidence Band', type: 'line', data: bandData,
                    lineStyle: { opacity: 0 }, stack: 'confidence', symbol: 'none',
                    areaStyle: { color: '#8b5cf6', opacity: 0.1 }
                }
            ]
        });
    }

    async function loadCashFlow() {
        const dept = document.getElementById('ctrl-cf-dept').value;
        const agg = document.getElementById('ctrl-cf-agg').value;
        const currency = document.getElementById('global-currency').value;
        
        dashboardCharts['chart-cash-flow'].showLoading();
        const res = await api.get(`/api/v1/pl/charts?dept=${dept}&agg=${agg}&currency=${currency}`).catch(() => null);
        dashboardCharts['chart-cash-flow'].hideLoading();

        if (!res || !res.periods || res.cash_flow_mode === 'unavailable') {
            setChartError('chart-cash-flow', 'Cash Flow Unavailable: The uploaded dataset does not contain sufficient information.');
            return;
        }
        clearChartError('chart-cash-flow');

        const labels = res.periods;
        const hasRev = res.revenue_trend && res.revenue_trend.length > 0;
        const hasExp = res.expense_trend && res.expense_trend.length > 0;
        
        const cashIn = hasRev ? (res.revenue_trend || []).map(d => d.value) : labels.map(() => 0);
        const cashOut = hasExp ? (res.expense_trend || []).map(d => d.value) : labels.map(() => 0);
        const netCash = (res.cashflow_trend || []).map(d => d.value);

        const subTitle = res.cash_flow_mode === 'estimated' ? 'Estimated (Revenue - Expense)' : 'Actual values';

        safeSetOption(dashboardCharts['chart-cash-flow'], {
            title: { text: subTitle, textStyle: { fontSize: 12, color: '#94a3b8', fontWeight: 'normal' }, left: 'center', top: 0 },
            tooltip: { trigger: 'axis', axisPointer: { type: 'shadow' } },
            legend: { top: 0, icon: 'circle' },
            grid: { left: '3%', right: '4%', bottom: '15%', containLabel: true },
            toolbox: getStandardToolbox(),
            dataZoom: standardDataZoom,
            xAxis: { type: 'category', data: labels },
            yAxis: { type: 'value', axisLabel: { formatter: (val) => formatCurrency(val) } },
            series: [
                { name: 'Cash In', type: 'bar', stack: 'Total', itemStyle: { color: '#10b981' }, data: cashIn },
                { name: 'Cash Out', type: 'bar', stack: 'Total', itemStyle: { color: '#ef4444' }, data: cashOut.map(v => -v) },
                { name: 'Net Cash', type: 'line', smooth: true, itemStyle: { color: '#3b82f6', width: 3 }, data: netCash }
            ]
        });
    }

    async function loadBudget() {
        const agg = document.getElementById('ctrl-bdg-agg')?.value || 'monthly';
        const currency = document.getElementById('global-currency')?.value || 'INR';
        
        if (dashboardCharts['chart-budget-actual']) dashboardCharts['chart-budget-actual'].showLoading();
        
        const chartsRes = await api.get(`/api/v1/pl/charts?agg=${agg}&currency=${currency}`).catch(() => null);
        const resData = await api.get(`/api/v1/pl/departments/summary?currency=${currency}`).catch(() => ({departments: []}));
        if (dashboardCharts['chart-budget-actual']) dashboardCharts['chart-budget-actual'].hideLoading();

        const deptSummaries = resData.departments || [];
        const budgetTrend = chartsRes?.budget_trend || [];
        
        const hasBudget = (chartsRes && (chartsRes.has_budget_data || (budgetTrend && budgetTrend.some(b => b.budget > 0)))) || (deptSummaries.length > 0 && deptSummaries.some(d => d.budget !== undefined && d.budget !== null && d.budget > 0));
        
        if (!hasBudget && (!budgetTrend || !budgetTrend.length)) {
            setChartError('chart-budget-actual', 'Budget Variance Analysis: Click "Set Budget" to define budgets for active dataset departments.');
            return;
        }
        clearChartError('chart-budget-actual');

        let depts = [];
        let actual = [];
        let budget = [];
        
        if (deptSummaries.length > 0 && deptSummaries.some(d => d.budget > 0)) {
            depts = deptSummaries.map(d => d.department);
            actual = deptSummaries.map(d => d.expense || 0);
            budget = deptSummaries.map(d => d.budget || 0);
        } else if (budgetTrend.length > 0) {
            depts = budgetTrend.map(b => b.period);
            actual = budgetTrend.map(b => b.actual || 0);
            budget = budgetTrend.map(b => b.budget || 0);
        } else {
            depts = deptSummaries.map(d => d.department);
            actual = deptSummaries.map(d => d.expense || 0);
            budget = deptSummaries.map(() => 0);
        }

        const sumActual = actual.reduce((a,b)=>a+b, 0);
        const sumBudget = budget.reduce((a,b)=>a+b, 0);
        const diff = sumActual - sumBudget;
        
        const summaryEl = document.getElementById('budget-ai-summary');
        if (summaryEl) {
            summaryEl.innerHTML = `<span class="material-symbols-outlined text-[14px] text-brand mr-1 align-text-bottom">smart_toy</span> Total actual spend is ${diff > 0 ? 'over' : 'under'} budget by ${formatCurrency(Math.abs(diff))}. ${diff > 0 ? 'Review highest variance departments.' : 'Excellent cost control.'}`;
        }

        safeSetOption(dashboardCharts['chart-budget-actual'], {
            tooltip: { 
                trigger: 'axis', 
                axisPointer: { type: 'shadow' },
                formatter: (params) => {
                    if (!params || !params.length) return '';
                    const header = `<div style="font-weight:600;border-bottom:1px solid #e5e7eb;padding-bottom:4px;margin-bottom:4px;">${params[0].axisValue}</div>`;
                    let body = params.map(p => `<div><span style="display:inline-block;width:8px;height:8px;border-radius:50%;background:${p.color};margin-right:6px;"></span>${p.seriesName}: <b>${formatCurrency(p.value)}</b></div>`).join('');
                    const act = params.find(p => p.seriesName === 'Actual')?.value || 0;
                    const bdg = params.find(p => p.seriesName === 'Budget')?.value || 0;
                    const varVal = act - bdg;
                    const varPct = bdg > 0 ? ((varVal / bdg) * 100).toFixed(1) : '0.0';
                    body += `<div style="margin-top:4px;font-size:11px;color:${varVal > 0 ? '#ef4444' : '#10b981'};font-weight:bold;">Variance: ${formatCurrency(varVal)} (${varPct}%)</div>`;
                    return `<div style="padding:4px 8px">${header}${body}</div>`;
                }
            },
            legend: { top: 0, icon: 'circle' },
            grid: { left: '3%', right: '4%', bottom: '5%', containLabel: true },
            toolbox: getStandardToolbox(),
            xAxis: { type: 'value', axisLabel: { formatter: (val) => formatCurrency(val) } },
            yAxis: { type: 'category', data: depts, inverse: true },
            series: [
                { name: 'Budget', type: 'bar', itemStyle: { color: '#94a3b8', borderRadius: [0, 4, 4, 0] }, data: budget },
                { name: 'Actual', type: 'bar', itemStyle: { color: '#6366f1', borderRadius: [0, 4, 4, 0] }, data: actual }
            ]
        });
    }

    async function loadInsights() {
        const container = document.getElementById('ai-insights-list');
        const loader = document.getElementById('insights-loading');
        if (!container) return;
        
        if (loader) loader.style.display = 'flex';
        const res = await api.get(`/api/v1/recommendations`).catch(() => []);
        if (loader) loader.style.display = 'none';

        if (!res.length) {
            container.innerHTML = '<div class="text-xs text-slate-500 italic p-4 text-center">No insights available.</div>';
            return;
        }

        let html = '';
        res.slice(0, 4).forEach(ins => {
            const priorityClass = ins.priority === 'High' ? 'bg-red-100 text-red-600' : 'bg-blue-100 text-blue-600';
            html += `
            <div class="p-3 bg-slate-50 border border-slate-100 rounded-lg hover:border-primary/30 transition-colors">
                <div class="flex justify-between items-start mb-1">
                    <h4 class="font-bold text-xs text-slate-800">${ins.title}</h4>
                    <span class="${priorityClass} text-[9px] font-bold px-1.5 py-0.5 rounded uppercase">${ins.priority}</span>
                </div>
                <p class="text-[11px] text-slate-600 line-clamp-2">${ins.reason || ins.description || ''}</p>
            </div>
            `;
        });
        container.innerHTML = html;
    }

    async function loadRecommendations() {
        const container = document.getElementById('ai-decision-center');
        const loader = document.getElementById('recs-loading');
        if (!container) return;
        
        if (loader) loader.style.display = 'flex';
        const res = await api.get(`/api/v1/recommendations`).catch(() => []);
        if (loader) loader.style.display = 'none';

        if (!res.length) {
            container.innerHTML = '<div class="text-xs text-slate-500 italic p-4 text-center">No recommendations available.</div>';
            return;
        }

        let html = '';
        res.slice(0, 5).forEach(ins => {
            if (!ins.suggested_action) return;
            const priorityClass = ins.priority === 'High' ? 'bg-red-100 text-red-600' : 'bg-blue-100 text-blue-600';
            html += `
            <div class="p-4 bg-slate-50 border border-slate-200 rounded-xl hover:shadow-md transition-shadow">
                <div class="flex justify-between items-start mb-2">
                    <h4 class="font-bold text-sm text-slate-800 flex items-center gap-2">
                        <span class="material-symbols-outlined text-primary text-[16px]">psychology</span> ${ins.title}
                    </h4>
                    <span class="${priorityClass} text-[10px] font-bold px-2 py-0.5 rounded-full uppercase tracking-wider">${ins.priority}</span>
                </div>
                <p class="text-xs text-slate-600 mb-3">${ins.reason}</p>
                <div class="bg-white border border-slate-100 p-3 rounded-lg">
                    <div class="text-[10px] text-slate-400 font-bold uppercase tracking-wider mb-1">Recommended Action</div>
                    <p class="text-sm font-semibold text-slate-700">${ins.suggested_action}</p>
                </div>
                ${ins.financial_impact ? `
                <div class="mt-3 flex items-center justify-between">
                    <div class="text-[10px] font-bold text-slate-500 uppercase tracking-wide">Impact</div>
                    <div class="text-sm font-bold text-emerald-600">+${formatCurrency(ins.financial_impact)}</div>
                </div>
                ` : ''}
            </div>
            `;
        });
        container.innerHTML = html;
    }

    // 5. Initialize All
    function fetchAll() {
        loadKPIs();
        loadRevExpProfit();
        loadAnomalyOverview();
        loadDeptPerformance();
        loadExpenseDist();
        loadForecast();
        loadCashFlow();
        loadBudget();
        loadInsights();
        loadRecommendations();
    }

    // 6. Bind Event Listeners
    initCharts();
    fetchAll();

    // Global filters trigger everything
    const globalCurr = document.getElementById('global-currency');
    if (globalCurr) globalCurr.addEventListener('change', fetchAll);

    // Chart specific filters
    const bindFilter = (id, loaderFn) => {
        const el = document.getElementById(id);
        if (el) el.addEventListener('change', loaderFn);
    };

    bindFilter('ctrl-rev-dept', loadRevExpProfit);
    bindFilter('ctrl-rev-agg', loadRevExpProfit);
    bindFilter('ctrl-anom-agg', loadAnomalyOverview);
    bindFilter('ctrl-dept-metric', loadDeptPerformance);
    bindFilter('ctrl-dept-limit', loadDeptPerformance);
    bindFilter('ctrl-dist-metric', loadExpenseDist);
    bindFilter('ctrl-fcst-dept', loadForecast);
    bindFilter('ctrl-fcst-agg', loadForecast);
    bindFilter('ctrl-cf-dept', loadCashFlow);
    bindFilter('ctrl-cf-agg', loadCashFlow);
    bindFilter('ctrl-bdg-agg', loadBudget);

    // Budget modal
    const btnSetBudget = document.getElementById('btn-set-budget');
    const budgetModal = document.getElementById('budget-modal');
    const budgetModalContent = document.getElementById('budget-modal-content');
    const btnCloseBudget = document.getElementById('btn-close-budget');
    const btnCancelBudget = document.getElementById('btn-cancel-budget');
    const budgetForm = document.getElementById('budget-form');

    async function openBudgetModal() {
        if (!budgetModal) return;
        const deptSelect = document.getElementById('budget-dept');
        if (deptSelect) {
            const deptsRes = await api.get('/api/v1/pl/departments').catch(() => null);
            const depts = deptsRes?.departments || ['Finance', 'Sales', 'IT', 'Marketing', 'HR', 'Operations'];
            deptSelect.innerHTML = depts.map(d => `<option value="${d}">${d}</option>`).join('');
        }
        budgetModal.classList.remove('hidden');
        budgetModal.classList.add('flex');
        setTimeout(() => {
            budgetModal.classList.remove('opacity-0');
            budgetModalContent.classList.remove('scale-95');
        }, 10);
    }

    function closeBudgetModal() {
        if (!budgetModal) return;
        budgetModal.classList.add('opacity-0');
        budgetModalContent.classList.add('scale-95');
        setTimeout(() => {
            budgetModal.classList.add('hidden');
            budgetModal.classList.remove('flex');
        }, 300);
    }

    if (btnSetBudget) btnSetBudget.addEventListener('click', openBudgetModal);
    if (btnCloseBudget) btnCloseBudget.addEventListener('click', closeBudgetModal);
    if (btnCancelBudget) btnCancelBudget.addEventListener('click', closeBudgetModal);
    
    if (budgetForm) {
        budgetForm.addEventListener('submit', (e) => {
            e.preventDefault();
            const department = document.getElementById('budget-dept').value;
            const amount = parseFloat(document.getElementById('budget-amount').value);
            
            api.post('/api/v1/pl/budget', { department, amount, budget_amount: amount })
                .then(r => {
                    closeBudgetModal();
                    loadBudget(); // isolated refetch
            }).catch(err => {
                console.error('Budget error:', err);
                alert('Error saving budget.');
            });
        });
    }
});
