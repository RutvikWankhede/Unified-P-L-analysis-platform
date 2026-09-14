/**
 * pl_dashboard_wiring.js
 * Complete end-to-end data flow and chart wiring for pl_dashboard.html.
 */
import { api } from './api.js';

function formatCurrency(val) {
    if (val === null || val === undefined) return 'Not available';
    const abs = Math.abs(val);
    const sign = val < 0 ? '-' : '';
    if (abs >= 10000000) return `${sign}₹${(abs / 10000000).toFixed(2)} Cr`;
    if (abs >= 100000) return `${sign}₹${(abs / 100000).toFixed(2)} L`;
    return `${sign}₹${abs.toLocaleString('en-IN', { maximumFractionDigits: 0 })}`;
}

function setKpi(id, value, trendPct) {
    const el = document.getElementById(id);
    if (!el) return;
    el.textContent = (value !== null && value !== undefined) ? formatCurrency(value) : 'Not available';
    const parent = el.closest('.bg-white');
    if (!parent || trendPct === undefined || trendPct === null) return;
    const trendEl = parent.querySelector('[class*="flex items-center gap-1"]');
    if (!trendEl) return;
    const isExp = id === 'kpi-total-expense';
    const isGood = isExp ? trendPct <= 0 : trendPct >= 0;
    const colorClass = isGood ? 'text-success' : 'text-danger';
    const arrow = trendPct >= 0 ? 'arrow_upward' : 'arrow_downward';
    trendEl.className = `flex items-center gap-1 ${colorClass} text-xs font-medium`;
    trendEl.innerHTML = `<span class="material-symbols-outlined text-sm">${arrow}</span><span>${Math.abs(trendPct).toFixed(1)}% <span class="text-on-surface-variant font-normal">vs prior</span></span>`;
}

function setHealthScore(score) {
    const el = document.getElementById('kpi-health-score');
    if (!el) return;
    el.innerHTML = `${Math.round(score || 85)} <span class="text-2xl text-on-surface-variant font-normal">/100</span>`;
}

// ── Revenue vs Expense Chart ──────────────────────────────────────────────────
let revExpChartInstance = null;
function drawRevenueExpenseChart(periods, revData, expData, profData) {
    const canvas = document.getElementById('chart-revenue-expense');
    if (!canvas || !window.echarts) return;
    const parent = canvas.parentElement;
    if (!parent) return;
    parent.querySelectorAll('canvas, .absolute').forEach(el => el.remove());
    
    let chartDiv = document.getElementById('chart-revenue-expense-ec');
    if (!chartDiv) {
        chartDiv = document.createElement('div');
        chartDiv.id = 'chart-revenue-expense-ec';
        chartDiv.style.cssText = 'position:absolute; inset:0; width:100%; height:100%;';
        parent.insertBefore(chartDiv, parent.firstChild);
    }
    
    if (revExpChartInstance) {
        try { revExpChartInstance.dispose(); } catch (_) {}
    }
    revExpChartInstance = window.echarts.init(chartDiv);
    
    const series = [];
    if (revData?.length) series.push({ name: 'Revenue', type: 'line', smooth: true, lineStyle: { width: 3 }, data: revData, itemStyle: { color: '#5b5ceb' }, areaStyle: { opacity: 0.05 } });
    if (expData?.length) series.push({ name: 'Expense', type: 'line', smooth: true, lineStyle: { width: 3 }, data: expData, itemStyle: { color: '#ef4444' }, areaStyle: { opacity: 0.05 } });
    if (profData?.length) series.push({ name: 'Net Profit', type: 'line', smooth: true, lineStyle: { width: 3 }, data: profData, itemStyle: { color: '#10b981' }, areaStyle: { opacity: 0.05 } });
    
    if (!series.length) return;
    revExpChartInstance.setOption({
        tooltip: { trigger: 'axis' },
        legend: { top: 0, icon: 'circle', itemGap: 16 },
        grid: { left: '2%', right: '2%', bottom: '5%', top: '25px', containLabel: true },
        xAxis: { type: 'category', boundaryGap: false, data: periods, axisLabel: { fontSize: 10, rotate: 45, interval: 'auto' } },
        yAxis: { type: 'value', axisLabel: { formatter: v => formatCurrency(v), fontSize: 10 }, scale: true, splitLine: { lineStyle: { type: 'dashed' } } },
        series
    });
}

// ── Cash Flow Trend Chart ─────────────────────────────────────────────────────
let cashFlowChartInstance = null;
async function loadCashFlowTrend() {
    const agg = document.getElementById('ctrl-cf-agg')?.value || 'monthly';
    const container = document.getElementById('chart-cash-flow');
    if (!container || !window.echarts) return;

    const res = await api.get(`/api/v1/pl/charts?agg=${agg}`).catch(() => null);
    if (!res || !res.periods) return;

    const mode = res.cash_flow_mode || 'estimated';
    const subtitleEl = document.getElementById('cf-subtitle');
    if (subtitleEl) {
        subtitleEl.textContent = mode === 'actual' ? 'Actual Cash Inflow − Outflow' : 'Estimated Cash Flow (Revenue − Expense)';
    }

    const periods = res.periods || [];
    const trendData = (res.cashflow_trend || []).map(d => d.value);

    if (cashFlowChartInstance) {
        try { cashFlowChartInstance.dispose(); } catch (_) {}
    }
    cashFlowChartInstance = window.echarts.init(container);

    cashFlowChartInstance.setOption({
        tooltip: {
            trigger: 'axis',
            axisPointer: { type: 'cross' },
            formatter: (params) => {
                if (!params || !params.length) return '';
                const p = params[0];
                return `<div style="padding:4px 8px"><b>${p.name}</b><br/>${mode === 'estimated' ? 'Estimated Cash Flow' : 'Net Cash Flow'}: <b>${formatCurrency(p.value)}</b></div>`;
            }
        },
        legend: { top: 0, icon: 'circle' },
        grid: { left: '2%', right: '4%', bottom: '5%', top: '15px', containLabel: true },
        xAxis: { type: 'category', boundaryGap: false, data: periods, axisLabel: { fontSize: 10, rotate: 45, interval: 'auto' } },
        yAxis: { type: 'value', axisLabel: { formatter: v => formatCurrency(v), fontSize: 10 }, splitLine: { lineStyle: { type: 'dashed' } } },
        series: [{
            name: mode === 'estimated' ? 'Estimated Cash Flow' : 'Net Cash Flow',
            type: 'line',
            smooth: true, lineStyle: { width: 4 },
            itemStyle: { color: '#0d9488' },
            areaStyle: { opacity: 0.1, color: '#0d9488' },
            data: trendData
        }]
    });
}

// ── Budget vs Actual Chart ────────────────────────────────────────────────────
let budgetChartInstance = null;
async function loadBudgetvsActual() {
    const agg = document.getElementById('ctrl-bdg-agg')?.value || 'monthly';
    const container = document.getElementById('chart-budget-actual');
    if (!container || !window.echarts) return;

    const chartsRes = await api.get(`/api/v1/pl/charts?agg=${agg}`).catch(() => null);
    const resData = await api.get('/api/v1/pl/departments/summary').catch(() => ({ departments: [] }));
    const deptSummaries = resData.departments || [];
    const budgetTrend = chartsRes?.budget_trend || [];

    const hasBudget = (chartsRes && (chartsRes.has_budget_data || (budgetTrend && budgetTrend.some(b => b.budget > 0)))) || (deptSummaries.length > 0 && deptSummaries.some(d => d.budget !== undefined && d.budget !== null && d.budget > 0));

    if (budgetChartInstance) {
        try { budgetChartInstance.dispose(); } catch (_) {}
    }
    budgetChartInstance = window.echarts.init(container);

    if (!hasBudget && (!budgetTrend || !budgetTrend.length)) {
        budgetChartInstance.setOption({
            title: {
                text: 'Budget Variance Analysis: Click "Set Budget" to define budgets for departments.',
                left: 'center',
                top: 'center',
                textStyle: { fontSize: 12, color: '#94a3b8', fontWeight: 'normal' }
            }
        });
        return;
    }

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

    const sumActual = actual.reduce((a, b) => a + b, 0);
    const sumBudget = budget.reduce((a, b) => a + b, 0);
    const diff = sumActual - sumBudget;

    const summaryEl = document.getElementById('budget-ai-summary');
    if (summaryEl) {
        summaryEl.textContent = `Total spend is ${diff > 0 ? 'over' : 'under'} budget by ${formatCurrency(Math.abs(diff))}. ${diff > 0 ? 'Review high variance areas.' : 'Cost control within target.'}`;
    }

    budgetChartInstance.setOption({
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
        legend: { top: 0, icon: 'circle', itemGap: 16 },
        grid: { left: '2%', right: '4%', bottom: '5%', top: '15px', containLabel: true },
        xAxis: { type: 'value', axisLabel: { formatter: v => formatCurrency(v), fontSize: 10 }, splitLine: { lineStyle: { type: 'dashed' } } },
        yAxis: { type: 'category', data: depts, inverse: true, axisLabel: { fontSize: 10, interval: 0, width: 80, overflow: 'truncate' } },
        series: [
            { name: 'Budget', type: 'bar', itemStyle: { color: '#94a3b8', borderRadius: [0, 4, 4, 0] }, data: budget },
            { name: 'Actual', type: 'bar', itemStyle: { color: '#6366f1', borderRadius: [0, 4, 4, 0] }, data: actual }
        ]
    });
}

// ── Set Budget Modal ─────────────────────────────────────────────────────────
function setupBudgetModal() {
    const btnSetBudget = document.getElementById('btn-set-budget');
    const budgetModal = document.getElementById('budget-modal');
    const budgetModalContent = document.getElementById('budget-modal-content');
    const btnCloseBudget = document.getElementById('btn-close-budget');
    const btnCancelBudget = document.getElementById('btn-cancel-budget');
    const budgetForm = document.getElementById('budget-form');

    if (!btnSetBudget || !budgetModal) return;

    async function openModal() {
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
            if (budgetModalContent) budgetModalContent.classList.remove('scale-95');
        }, 10);
    }

    function closeModal() {
        budgetModal.classList.add('opacity-0');
        if (budgetModalContent) budgetModalContent.classList.add('scale-95');
        setTimeout(() => {
            budgetModal.classList.add('hidden');
            budgetModal.classList.remove('flex');
        }, 200);
    }

    btnSetBudget.addEventListener('click', openModal);
    if (btnCloseBudget) btnCloseBudget.addEventListener('click', closeModal);
    if (btnCancelBudget) btnCancelBudget.addEventListener('click', closeModal);

    if (budgetForm) {
        budgetForm.addEventListener('submit', async (e) => {
            e.preventDefault();
            const dept = document.getElementById('budget-dept')?.value;
            const period = document.getElementById('budget-period')?.value || 'monthly';
            const amount = parseFloat(document.getElementById('budget-amount')?.value || 0);

            if (!dept || isNaN(amount) || amount < 0) return;

            await api.post('/api/v1/pl/budget', { department: dept, period: period, monthly_amount: amount }).catch(() => null);
            closeModal();
            loadBudgetvsActual();
        });
    }
}

// ── Anomaly Overview ─────────────────────────────────────────────────────────
function updateAnomalyOverview(anomalies) {
    const container = document.getElementById('anomaly-overview-container');
    if (!container) return;
    const counts = { Critical: 0, High: 0, Medium: 0, Low: 0 };
    anomalies.forEach(a => {
        const s = (a.severity || a.score_label || 'Low');
        const k = s.charAt(0).toUpperCase() + s.slice(1).toLowerCase();
        if (k in counts) counts[k]++; else counts.Low++;
    });
    const totalEl = container.closest('.col-span-3')?.querySelector('.text-2xl.font-bold');
    if (totalEl) totalEl.textContent = anomalies.length;
    const colors = { Critical: 'bg-danger', High: 'bg-warning', Medium: 'bg-primary', Low: 'bg-blue-300' };
    container.innerHTML = Object.entries(counts).map(([label, count]) => `
        <div class="flex items-center justify-between text-xs">
            <div class="flex items-center gap-2">
                <div class="w-2 h-2 rounded-full ${colors[label]}"></div>
                <span class="text-on-surface-variant">${label}</span>
            </div>
            <span class="font-bold">${count}</span>
        </div>`).join('');
}

// ── Department Summary Table ────────────────────────────────────────────────
function updateDeptTable(departments) {
    const tbody = document.getElementById('dept-table-body');
    if (!tbody || !departments?.length) return;
    const iconMap = { Finance: 'account_balance', Sales: 'store', IT: 'laptop', Marketing: 'campaign', HR: 'groups', Operations: 'precision_manufacturing', Engineering: 'code' };
    const colorMap = { Finance: 'bg-primary/10 text-primary', Sales: 'bg-success/10 text-success', IT: 'bg-blue-100 text-blue-600', Marketing: 'bg-pink-100 text-pink-600', HR: 'bg-yellow-100 text-yellow-600', Operations: 'bg-orange-100 text-orange-600', Engineering: 'bg-indigo-100 text-indigo-600' };
    tbody.innerHTML = departments.map(d => {
        const name = d.department || d.name || 'Unknown';
        const rev = d.revenue || 0, exp = d.expense || 0, prof = d.profit || (rev - exp);
        const margin = rev > 0 ? (prof / rev * 100) : 0;
        return `<tr>
            <td class="py-4"><div class="flex items-center gap-3">
                <div class="w-6 h-6 rounded ${colorMap[name] || 'bg-primary/10 text-primary'} flex items-center justify-center">
                    <span class="material-symbols-outlined text-sm">${iconMap[name] || 'business'}</span>
                </div>
                <span class="font-semibold">${name}</span>
            </div></td>
            <td class="py-4">${formatCurrency(rev)}</td>
            <td class="py-4">${formatCurrency(exp)}</td>
            <td class="py-4">${formatCurrency(prof)}</td>
            <td class="py-4"><div class="flex items-center gap-2">
                <span>${margin.toFixed(1)}%</span>
                <div class="w-12 h-1.5 bg-surface-container-low rounded-full overflow-hidden">
                    <div class="bg-success h-full" style="width:${Math.min(Math.max(margin,0),100)}%"></div>
                </div>
            </div></td>
        </tr>`;
    }).join('');
}

// ── Recent Uploads ──────────────────────────────────────────────────────────
function updateRecentUploads(datasets) {
    const container = document.getElementById('recent-uploads-container');
    if (!container || !datasets?.length) return;
    const statusStyles = { active: 'bg-success/10 text-success', processed: 'bg-success/10 text-success', pending: 'bg-warning/10 text-warning', mapped: 'bg-primary/10 text-primary', error: 'bg-danger/10 text-danger' };
    container.innerHTML = datasets.slice(0, 4).map(ds => {
        const filename = ds.filename || ds.name || 'Unknown';
        const dateStr = ds.created_at ? new Date(ds.created_at).toLocaleDateString('en-IN', { day: 'numeric', month: 'short', year: 'numeric' }) : '';
        const size = ds.file_size_bytes ? `${(ds.file_size_bytes / (1024 * 1024)).toFixed(1)} MB` : '';
        const status = (ds.status || 'processed').toLowerCase();
        const cls = statusStyles[status] || 'bg-primary/10 text-primary';
        return `<div class="flex items-center justify-between p-3 border border-outline-variant/10 rounded-xl">
            <div class="flex items-center gap-3">
                <div class="w-10 h-10 bg-success/10 text-success rounded-lg flex items-center justify-center">
                    <span class="material-symbols-outlined">table_chart</span>
                </div>
                <div>
                    <p class="text-xs font-bold">${filename}</p>
                    <p class="text-[10px] text-on-surface-variant">${dateStr}${size ? ' • ' + size : ''}</p>
                </div>
            </div>
            <span class="text-[10px] font-bold px-2 py-1 ${cls} rounded uppercase tracking-tighter">${status.charAt(0).toUpperCase()+status.slice(1)}</span>
        </div>`;
    }).join('');
}

// ── DOM Load & Event Bindings ────────────────────────────────────────────────
document.addEventListener('DOMContentLoaded', async () => {
    try {
        const summary = await api.get('/api/v1/pl/summary?agg=yearly');
        if (summary?.kpis) {
            const k = summary.kpis;
            setKpi('kpi-total-revenue', k.revenue, k.revenue_growth);
            setKpi('kpi-total-expense', k.expense, k.expense_growth);
            setKpi('kpi-net-profit', k.profit, k.profit_growth);
            setHealthScore(k.health_score);

            const caps = summary.capabilities || {};
            const cfMode = caps.cashFlow?.mode || 'estimated';
            const cfVal = k.cash_flow !== null && k.cash_flow !== undefined ? k.cash_flow : k.profit;
            const cfLabelEl = document.getElementById('kpi-cash-flow-label');
            const cfSubEl = document.getElementById('kpi-cash-flow-sub');
            if (cfLabelEl) cfLabelEl.textContent = cfMode === 'actual' ? 'Cash Flow' : 'Estimated Cash Flow';
            if (cfSubEl) cfSubEl.textContent = cfMode === 'actual' ? 'Actual cash inflow − outflow' : 'Derived from Revenue − Expense';
            setKpi('kpi-cash-flow', cfVal, null);

            const fcVal = k.forecast_profit ?? k.forecasted_profit ?? (k.forecast && k.forecast.value);
            if (fcVal !== undefined && fcVal !== null) {
                setKpi('kpi-forecast', fcVal, null);
                setKpi('kpi-forecasted-profit', fcVal, null);
            }
            const fcLbl = document.getElementById('kpi-forecast-label');
            if (fcLbl) fcLbl.textContent = 'Forecast';
        }
    } catch (e) { console.warn('[pl_dashboard_wiring] KPI load failed:', e); }

    try {
        const charts = await api.get('/api/v1/pl/charts?agg=monthly');
        if (charts) {
            const periods = charts.periods || [];
            const rev = (charts.revenue_trend || []).map(d => d.value);
            const exp = (charts.expense_trend || []).map(d => d.value);
            const prof = (charts.profit_trend || []).map(d => d.value);
            drawRevenueExpenseChart(periods, rev, exp, prof);
        }
    } catch (e) { console.warn('[pl_dashboard_wiring] Chart load failed:', e); }

    loadCashFlowTrend();
    loadBudgetvsActual();
    setupBudgetModal();

    const cfAggEl = document.getElementById('ctrl-cf-agg');
    if (cfAggEl) cfAggEl.addEventListener('change', loadCashFlowTrend);

    const bdgAggEl = document.getElementById('ctrl-bdg-agg');
    if (bdgAggEl) bdgAggEl.addEventListener('change', loadBudgetvsActual);

    try {
        const anomalyRes = await api.get('/api/v1/anomalies/?limit=50');
        const anomalies = Array.isArray(anomalyRes) ? anomalyRes : (anomalyRes?.anomalies || []);
        updateAnomalyOverview(anomalies);
    } catch (e) { console.warn('[pl_dashboard_wiring] Anomaly load failed:', e); }

    try {
        const deptRes = await api.get('/api/v1/pl/departments/summary?agg=yearly&limit=8');
        const departments = Array.isArray(deptRes) ? deptRes : (deptRes?.departments || []);
        updateDeptTable(departments);
    } catch (e) { console.warn('[pl_dashboard_wiring] Dept load failed:', e); }

    try {
        const uploadsRes = await api.get('/api/v1/datasets/recent').catch(() => api.get('/api/v1/datasets/'));
        const datasets = Array.isArray(uploadsRes) ? uploadsRes : (uploadsRes?.datasets || uploadsRes?.items || []);
        updateRecentUploads(datasets);
    } catch (e) { console.warn('[pl_dashboard_wiring] Uploads load failed:', e); }

    window.addEventListener('resize', () => {
        if (revExpChartInstance) try { revExpChartInstance.resize(); } catch (_) {}
        if (cashFlowChartInstance) try { cashFlowChartInstance.resize(); } catch (_) {}
        if (budgetChartInstance) try { budgetChartInstance.resize(); } catch (_) {}
    });
});
