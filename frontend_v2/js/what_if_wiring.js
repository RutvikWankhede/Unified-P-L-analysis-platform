/**
 * what_if_wiring.js - Dynamic What-If Financial Simulation & Stress Testing Engine
 * ===============================================================================
 * Single Source of Truth grounded in the active enterprise dataset.
 * Features:
 * - Direct baseline synchronization with Dashboard & Reports KPIs
 * - Multi-scope sensitivity simulation (Enterprise-wide or granular Department)
 * - Real-time scenario recalculation across Revenue Growth & Expense Adjustments
 * - Side-by-side comparative visualization (ECharts)
 * - Ranked departmental profit elasticity breakdown
 * - Dynamic algorithmic narrative verdict & insight cards
 * - Strict client-side isolation (Zero modification to source financial ledger)
 */

import { api } from './api.js';
import { initEchart, safeSetOption } from './chart-engine.js';

let comparisonChart = null;

async function initWhatIf() {
    let baselineData = {
        revenue: 0,
        expense: 0,
        profit: 0,
        margin: 0,
        departments: [],
        isLoading: true,
        hasError: false,
        errorMessage: ''
    };

    const formatCurrency = (val) => {
        if (val === null || val === undefined || isNaN(val)) return '₹0 Cr';
        const abs = Math.abs(val);
        const sign = val < 0 ? '-' : '';
        if (abs >= 1000000000) return `${sign}₹${(abs / 1000000000).toFixed(2)} B`;
        if (abs >= 10000000) return `${sign}₹${(abs / 10000000).toFixed(2)} Cr`;
        if (abs >= 100000) return `${sign}₹${(abs / 100000).toFixed(2)} L`;
        if (abs >= 1000) return `${sign}₹${(abs / 1000).toFixed(1)} K`;
        return `${sign}₹${abs.toLocaleString('en-IN')}`;
    };

    const formatShort = (val) => {
        if (val === null || val === undefined || isNaN(val)) return '0';
        const abs = Math.abs(val);
        const sign = val < 0 ? '-' : '';
        if (abs >= 1000000000) return `${sign}${(abs / 1000000000).toFixed(1)}B`;
        if (abs >= 10000000) return `${sign}${(abs / 10000000).toFixed(1)}Cr`;
        if (abs >= 100000) return `${sign}${(abs / 100000).toFixed(1)}L`;
        if (abs >= 1000) return `${sign}${(abs / 1000).toFixed(0)}K`;
        return `${sign}${abs}`;
    };

    const chartEl = document.getElementById('chart-whatif-comparison');
    if (chartEl) {
        comparisonChart = initEchart(chartEl);
    }

    // Controls
    const sliderRev = document.getElementById('slider-rev-growth');
    const inputRev = document.getElementById('input-rev-growth');
    const sliderExp = document.getElementById('slider-exp-growth');
    const inputExp = document.getElementById('input-exp-growth');
    const selectDept = document.getElementById('select-whatif-dept');
    const selectPreset = document.getElementById('scenario-preset');
    const btnReset = document.getElementById('btn-reset-scenario');
    const btnApply = document.getElementById('btn-apply-scenario');

    function showLoadingState() {
        const ids = ['kpi-base-rev', 'kpi-scen-rev', 'kpi-base-exp', 'kpi-scen-exp', 'kpi-base-prof', 'kpi-scen-prof', 'kpi-base-mrg', 'kpi-scen-mrg'];
        ids.forEach(id => {
            const el = document.getElementById(id);
            if (el) el.innerHTML = '<span class="animate-pulse text-slate-400 font-normal text-xs">Loading...</span>';
        });
        const narrativeEl = document.getElementById('whatif-narrative-text');
        if (narrativeEl) narrativeEl.textContent = 'Loading baseline financial data from active dataset...';
    }

    function showErrorState(msg) {
        const baseRevEl = document.getElementById('kpi-base-rev');
        if (baseRevEl) baseRevEl.innerHTML = `<span class="text-rose-500 font-normal text-xs">${msg || 'Error loading'}</span>`;
        const narrativeEl = document.getElementById('whatif-narrative-text');
        if (narrativeEl) narrativeEl.innerHTML = `<span class="text-rose-400">Failed to load active financial dataset: ${msg}. Please verify connection and retry.</span>`;
    }

    async function loadActiveDataset() {
        try {
            const active = await api.get('/api/v1/datasets/active').catch(() => null);
            if (active && (active.filename || active.name)) {
                const name = active.filename ? active.filename.replace('.csv', '').replace('.xlsx', '') : (active.name || 'Active Dataset');
                const pill = document.getElementById('active-dataset-name');
                if (pill) pill.textContent = name;
            }
        } catch (e) {
            console.warn('Active dataset fetch error:', e);
        }
    }

    async function loadBaselineData() {
        showLoadingState();
        try {
            const [summary, charts] = await Promise.all([
                api.get('/api/v1/pl/summary').catch(() => null),
                api.get('/api/v1/pl/charts?agg=monthly').catch(() => null)
            ]);

            if (!summary && !charts) {
                baselineData.hasError = true;
                baselineData.errorMessage = 'Backend service unavailable';
                showErrorState('Service unavailable');
                return;
            }

            if (summary && summary.kpis) {
                baselineData.revenue = Number(summary.kpis.revenue || 0);
                baselineData.expense = Number(summary.kpis.expense || 0);
                baselineData.profit = summary.kpis.profit !== undefined ? Number(summary.kpis.profit) : (baselineData.revenue - baselineData.expense);
                baselineData.margin = summary.kpis.profit_margin !== undefined 
                    ? Number(summary.kpis.profit_margin) 
                    : (baselineData.revenue > 0 ? ((baselineData.profit / baselineData.revenue) * 100) : 0);
            } else if (summary) {
                baselineData.revenue = Number(summary.total_revenue || 0);
                baselineData.expense = Number(summary.total_expenses || summary.total_expense || 0);
                baselineData.profit = Number(summary.net_profit !== undefined ? summary.net_profit : (baselineData.revenue - baselineData.expense));
                baselineData.margin = Number(summary.net_margin_percentage || (baselineData.revenue > 0 ? ((baselineData.profit / baselineData.revenue) * 100) : 0));
            }

            if (charts && charts.department_breakdown && Array.isArray(charts.department_breakdown)) {
                baselineData.departments = charts.department_breakdown.map(d => {
                    const r = Number(d.revenue || 0);
                    const e = Number(d.expense || 0);
                    const p = d.profit !== undefined && d.profit !== null ? Number(d.profit) : (r - e);
                    return {
                        name: d.department || d.name || 'General',
                        revenue: r,
                        expense: e,
                        profit: p,
                        margin: r > 0 ? ((p / r) * 100) : 0
                    };
                });
            }

            // Populate department selector
            if (selectDept && baselineData.departments.length > 0) {
                const currentSelection = selectDept.value || 'all';
                selectDept.innerHTML = '<option value="all">All Departments (Enterprise Wide)</option>';
                baselineData.departments.forEach(d => {
                    const opt = document.createElement('option');
                    opt.value = d.name;
                    opt.textContent = `${d.name} (${formatCurrency(d.revenue)})`;
                    if (d.name === currentSelection) opt.selected = true;
                    selectDept.appendChild(opt);
                });
                if (currentSelection === 'all') {
                    selectDept.value = 'all';
                }
            }

            baselineData.isLoading = false;
            recalculateScenario();
        } catch (err) {
            console.error('Failed to load baseline data for What-If:', err);
            baselineData.hasError = true;
            baselineData.errorMessage = err.message || 'Data fetch failed';
            showErrorState(baselineData.errorMessage);
        }
    }

    function recalculateScenario() {
        if (baselineData.isLoading || baselineData.hasError) return;

        const revGrowthPct = parseFloat(sliderRev ? sliderRev.value : (inputRev ? inputRev.value : 0)) || 0;
        const expGrowthPct = parseFloat(sliderExp ? sliderExp.value : (inputExp ? inputExp.value : 0)) || 0;
        const targetDept = selectDept ? selectDept.value : 'all';

        let effectiveBaseRev = 0;
        let effectiveBaseExp = 0;
        let effectiveBaseProf = 0;
        let effectiveBaseMargin = 0;

        let scenRev = 0;
        let scenExp = 0;
        let scenProf = 0;
        let scenMargin = 0;

        const deptImpacts = [];

        if (targetDept === 'all' || targetDept.toLowerCase() === 'overall') {
            effectiveBaseRev = baselineData.revenue;
            effectiveBaseExp = baselineData.expense;
            effectiveBaseProf = baselineData.profit;
            effectiveBaseMargin = baselineData.margin;

            scenRev = effectiveBaseRev * (1 + revGrowthPct / 100);
            scenExp = effectiveBaseExp * (1 + expGrowthPct / 100);
            scenProf = scenRev - scenExp;
            scenMargin = scenRev > 0 ? (scenProf / scenRev) * 100 : 0;

            baselineData.departments.forEach(d => {
                const dScenRev = d.revenue * (1 + revGrowthPct / 100);
                const dScenExp = d.expense * (1 + expGrowthPct / 100);
                const dScenProf = dScenRev - dScenExp;
                const dDiff = dScenProf - d.profit;
                deptImpacts.push({
                    name: d.name,
                    baseProfit: d.profit,
                    scenProfit: dScenProf,
                    diff: dDiff,
                    baseRev: d.revenue,
                    scenRev: dScenRev,
                    baseExp: d.expense,
                    scenExp: dScenExp
                });
            });
        } else {
            // Find selected department
            const matchedDept = baselineData.departments.find(d => d.name.toLowerCase() === targetDept.toLowerCase());
            if (matchedDept) {
                effectiveBaseRev = matchedDept.revenue;
                effectiveBaseExp = matchedDept.expense;
                effectiveBaseProf = matchedDept.profit;
                effectiveBaseMargin = matchedDept.margin;

                scenRev = effectiveBaseRev * (1 + revGrowthPct / 100);
                scenExp = effectiveBaseExp * (1 + expGrowthPct / 100);
                scenProf = scenRev - scenExp;
                scenMargin = scenRev > 0 ? (scenProf / scenRev) * 100 : 0;

                baselineData.departments.forEach(d => {
                    if (d.name.toLowerCase() === targetDept.toLowerCase()) {
                        deptImpacts.push({
                            name: d.name,
                            baseProfit: d.profit,
                            scenProfit: scenProf,
                            diff: scenProf - d.profit,
                            baseRev: d.revenue,
                            scenRev: scenRev,
                            baseExp: d.expense,
                            scenExp: scenExp
                        });
                    } else {
                        deptImpacts.push({
                            name: d.name,
                            baseProfit: d.profit,
                            scenProfit: d.profit,
                            diff: 0,
                            baseRev: d.revenue,
                            scenRev: d.revenue,
                            baseExp: d.expense,
                            scenExp: d.expense
                        });
                    }
                });
            } else {
                effectiveBaseRev = baselineData.revenue;
                effectiveBaseExp = baselineData.expense;
                effectiveBaseProf = baselineData.profit;
                effectiveBaseMargin = baselineData.margin;
                scenRev = effectiveBaseRev * (1 + revGrowthPct / 100);
                scenExp = effectiveBaseExp * (1 + expGrowthPct / 100);
                scenProf = scenRev - scenExp;
                scenMargin = scenRev > 0 ? (scenProf / scenRev) * 100 : 0;
            }
        }

        const revDiff = scenRev - effectiveBaseRev;
        const expDiff = scenExp - effectiveBaseExp;
        const profDiff = scenProf - effectiveBaseProf;
        const marginDiff = scenMargin - effectiveBaseMargin;

        // 1. Update KPI comparison cards
        const baseRevEl = document.getElementById('kpi-base-rev');
        const scenRevEl = document.getElementById('kpi-scen-rev');
        const revDiffEl = document.getElementById('kpi-diff-rev');

        if (baseRevEl) baseRevEl.textContent = formatCurrency(effectiveBaseRev);
        if (scenRevEl) scenRevEl.textContent = formatCurrency(scenRev);
        if (revDiffEl) {
            const isPos = revDiff >= 0;
            revDiffEl.className = isPos ? 'font-bold text-emerald-600' : 'font-bold text-rose-500';
            const pctText = effectiveBaseRev > 0 ? ((revDiff / effectiveBaseRev) * 100).toFixed(1) : '0.0';
            revDiffEl.textContent = `${isPos ? '+' : ''}${formatCurrency(revDiff)} (${revDiff >= 0 ? '+' : ''}${pctText}%)`;
        }

        const baseExpEl = document.getElementById('kpi-base-exp');
        const scenExpEl = document.getElementById('kpi-scen-exp');
        const expDiffEl = document.getElementById('kpi-diff-exp');

        if (baseExpEl) baseExpEl.textContent = formatCurrency(effectiveBaseExp);
        if (scenExpEl) scenExpEl.textContent = formatCurrency(scenExp);
        if (expDiffEl) {
            const isPos = expDiff <= 0;
            expDiffEl.className = isPos ? 'font-bold text-emerald-600' : 'font-bold text-rose-500';
            const pctText = effectiveBaseExp > 0 ? ((expDiff / effectiveBaseExp) * 100).toFixed(1) : '0.0';
            expDiffEl.textContent = `${expDiff >= 0 ? '+' : ''}${formatCurrency(expDiff)} (${expDiff >= 0 ? '+' : ''}${pctText}%)`;
        }

        const baseProfEl = document.getElementById('kpi-base-prof');
        const scenProfEl = document.getElementById('kpi-scen-prof');
        const profDiffEl = document.getElementById('kpi-diff-prof');

        if (baseProfEl) baseProfEl.textContent = formatCurrency(effectiveBaseProf);
        if (scenProfEl) {
            scenProfEl.textContent = formatCurrency(scenProf);
            scenProfEl.className = `text-base font-bold ${scenProf >= 0 ? 'text-slate-900' : 'text-rose-600'}`;
        }
        if (profDiffEl) {
            const isPos = profDiff >= 0;
            profDiffEl.className = isPos ? 'font-bold text-emerald-600' : 'font-bold text-rose-500';
            const profPct = effectiveBaseProf !== 0 ? ((profDiff / Math.abs(effectiveBaseProf)) * 100) : 0;
            profDiffEl.textContent = `${isPos ? '+' : ''}${formatCurrency(profDiff)} (${profDiff >= 0 ? '+' : ''}${profPct.toFixed(1)}%)`;
        }

        const baseMrgEl = document.getElementById('kpi-base-mrg');
        const scenMrgEl = document.getElementById('kpi-scen-mrg');
        const mrgDiffEl = document.getElementById('kpi-diff-mrg');

        if (baseMrgEl) baseMrgEl.textContent = `${effectiveBaseMargin.toFixed(1)}%`;
        if (scenMrgEl) {
            scenMrgEl.textContent = `${scenMargin.toFixed(1)}%`;
            scenMrgEl.className = `text-base font-bold ${scenMargin >= 0 ? 'text-slate-900' : 'text-rose-600'}`;
        }
        if (mrgDiffEl) {
            const isPos = marginDiff >= 0;
            mrgDiffEl.className = isPos ? 'font-bold text-emerald-600' : 'font-bold text-rose-500';
            mrgDiffEl.textContent = `${isPos ? '+' : ''}${marginDiff.toFixed(1)} pp`;
        }

        // 2. Render Comparative Chart
        renderComparativeChart(effectiveBaseRev, scenRev, effectiveBaseExp, scenExp, effectiveBaseProf, scenProf);

        // 3. Render Department Impact Ranking
        renderDepartmentImpact(deptImpacts);

        // 4. Render Dynamic What-If Insights
        renderWhatIfInsights(
            revGrowthPct, expGrowthPct,
            effectiveBaseRev, scenRev,
            effectiveBaseExp, scenExp,
            effectiveBaseProf, scenProf,
            effectiveBaseMargin, scenMargin,
            profDiff, marginDiff,
            deptImpacts, targetDept
        );
    }

    function renderComparativeChart(bRev, sRev, bExp, sExp, bProf, sProf) {
        if (!comparisonChart) return;

        safeSetOption(comparisonChart, {
            tooltip: {
                trigger: 'axis',
                backgroundColor: '#ffffff',
                borderColor: '#e2e8f0',
                borderWidth: 1,
                textStyle: { color: '#0f172a', fontSize: 11, fontFamily: 'Inter' },
                formatter: (params) => {
                    if (!params || !params.length) return '';
                    let html = `<div style="padding:4px 8px;font-size:11px"><b>${params[0].axisValue}</b><br/>`;
                    params.forEach(p => {
                        html += `<div style="display:flex;justify-content:space-between;gap:12px;margin:2px 0">
                            <span>${p.marker} ${p.seriesName}:</span>
                            <b>${formatCurrency(p.value)}</b>
                        </div>`;
                    });
                    html += '</div>';
                    return html;
                }
            },
            legend: { show: false },
            grid: { left: 8, right: 16, top: 16, bottom: 20, containLabel: true },
            xAxis: {
                type: 'category',
                data: ['Revenue', 'Total Expense', 'Net Profit'],
                axisLine: { lineStyle: { color: '#E2E8F0' } },
                axisTick: { show: false },
                axisLabel: { color: '#64748B', fontSize: 10, fontFamily: 'Inter' }
            },
            yAxis: {
                type: 'value',
                axisLine: { show: false },
                axisTick: { show: false },
                axisLabel: {
                    color: '#94A3B8',
                    fontSize: 10,
                    fontFamily: 'Inter',
                    formatter: (v) => formatShort(v)
                },
                splitLine: { lineStyle: { color: '#F1F5F9' } }
            },
            series: [
                {
                    name: 'Baseline',
                    type: 'bar',
                    data: [bRev, bExp, bProf],
                    itemStyle: { color: '#CBD5E1', borderRadius: [4, 4, 0, 0] },
                    barMaxWidth: 36
                },
                {
                    name: 'Scenario',
                    type: 'bar',
                    data: [sRev, sExp, sProf],
                    itemStyle: {
                        color: new echarts.graphic.LinearGradient(0, 0, 0, 1, [
                            { offset: 0, color: '#5B5CEB' },
                            { offset: 1, color: '#818CF8' }
                        ]),
                        borderRadius: [4, 4, 0, 0]
                    },
                    barMaxWidth: 36
                }
            ]
        }, true);
    }

    function renderDepartmentImpact(deptImpacts) {
        const container = document.getElementById('dept-impact-container');
        if (!container) return;

        if (!deptImpacts || deptImpacts.length === 0) {
            container.innerHTML = '<p class="text-slate-400 text-xs py-4 text-center">No departmental breakdowns available.</p>';
            return;
        }

        container.innerHTML = '';
        const sorted = [...deptImpacts].sort((a, b) => Math.abs(b.diff) - Math.abs(a.diff));

        sorted.forEach(d => {
            const isPos = d.diff >= 0;
            const badgeClass = isPos ? 'bg-emerald-50 text-emerald-700 border-emerald-200' : 'bg-rose-50 text-rose-700 border-rose-200';
            const sign = isPos ? '+' : '';

            const row = document.createElement('div');
            row.className = 'py-2.5 flex items-center justify-between border-b border-slate-50 last:border-none';
            row.innerHTML = `
                <div>
                    <p class="text-xs font-bold text-slate-800">${d.name}</p>
                    <p class="text-[10px] text-slate-400">Baseline: ${formatCurrency(d.baseProfit)} → Scenario: ${formatCurrency(d.scenProfit)}</p>
                </div>
                <div class="text-right">
                    <span class="px-2 py-0.5 rounded text-[10px] font-bold border ${badgeClass}">
                        ${sign}${formatCurrency(d.diff)}
                    </span>
                </div>
            `;
            container.appendChild(row);
        });
    }

    function renderWhatIfInsights(
        revGrowth, expGrowth,
        bRev, sRev,
        bExp, sExp,
        bProf, sProf,
        bMargin, sMargin,
        profDiff, marginDiff,
        deptImpacts, targetDept
    ) {
        const container = document.getElementById('whatif-insights-container');
        const narrativeEl = document.getElementById('whatif-narrative-text');

        const topDept = [...deptImpacts].sort((a, b) => Math.abs(b.diff) - Math.abs(a.diff))[0];
        const scopeDesc = targetDept === 'all' ? 'Enterprise-wide' : `${targetDept} Scope`;

        if (narrativeEl) {
            if (revGrowth === 0 && expGrowth === 0) {
                narrativeEl.innerHTML = `Operating in <b>Base Case (Audited Actuals)</b> for <i>${scopeDesc}</i>: Baseline Revenue is <b>${formatCurrency(bRev)}</b> with Expenses of <b>${formatCurrency(bExp)}</b>, yielding <b>${formatCurrency(bProf)}</b> net profit (<b>${bMargin.toFixed(1)}%</b> margin). Adjust levers above to simulate financial decisions.`;
            } else {
                let actionDesc = [];
                if (revGrowth !== 0) actionDesc.push(`${revGrowth > 0 ? 'Expanding' : 'Compressing'} revenue by ${Math.abs(revGrowth)}%`);
                if (expGrowth !== 0) actionDesc.push(`${expGrowth < 0 ? 'Reducing' : 'Increasing'} expenses by ${Math.abs(expGrowth)}%`);
                const actionStr = actionDesc.join(' while ') || 'Simulating adjustments';

                narrativeEl.innerHTML = `${actionStr} on <b>${scopeDesc}</b> shifts modeled revenue to <b>${formatCurrency(sRev)}</b> and expenses to <b>${formatCurrency(sExp)}</b>, generating <b>${formatCurrency(sProf)}</b> in net profit (${profDiff >= 0 ? '+' : ''}${formatCurrency(profDiff)} net variance) and moving operating margin from <b>${bMargin.toFixed(1)}%</b> to <b>${sMargin.toFixed(1)}%</b> (${marginDiff >= 0 ? '+' : ''}${marginDiff.toFixed(1)} pp).`;
            }
        }

        if (!container) return;
        container.innerHTML = '';

        const insights = [
            {
                title: 'Bottom-Line Net Sensitivity',
                desc: `Applying a <b>${revGrowth >= 0 ? '+' : ''}${revGrowth}%</b> revenue shift with a <b>${expGrowth >= 0 ? '+' : ''}${expGrowth}%</b> expense adjustment on <i>${scopeDesc}</i> creates a <b>${profDiff >= 0 ? '+' : ''}${formatCurrency(profDiff)}</b> bottom-line variance.`,
                icon: 'trending_up',
                color: profDiff >= 0 ? 'text-emerald-600' : 'text-rose-500',
                bg: profDiff >= 0 ? 'bg-emerald-50/50 border-emerald-100' : 'bg-rose-50/50 border-rose-100'
            },
            {
                title: 'Operating Margin Elasticity',
                desc: `Projected operating margin shifts by <b>${marginDiff >= 0 ? '+' : ''}${marginDiff.toFixed(1)} percentage points</b> (from ${bMargin.toFixed(1)}% to ${sMargin.toFixed(1)}%), illustrating operating leverage across fixed and variable cost structures.`,
                icon: 'percent',
                color: marginDiff >= 0 ? 'text-indigo-600' : 'text-amber-600',
                bg: 'bg-slate-50 border-slate-100'
            },
            {
                title: 'Primary Scenario Driver',
                desc: topDept && targetDept === 'all'
                    ? `<b>${topDept.name}</b> experiences the largest financial impact with a projected <b>${topDept.diff >= 0 ? '+' : ''}${formatCurrency(topDept.diff)}</b> variance.`
                    : `Active scope focused on <b>${scopeDesc}</b> with <b>${formatCurrency(sProf)}</b> projected profit.`,
                icon: 'domain',
                color: 'text-primary',
                bg: 'bg-indigo-50/40 border-indigo-100/60'
            }
        ];

        insights.forEach(item => {
            const card = document.createElement('div');
            card.className = `p-3.5 rounded-xl border ${item.bg} flex items-start gap-3`;
            card.innerHTML = `
                <span class="material-symbols-outlined text-lg ${item.color} mt-0.5 shrink-0">${item.icon}</span>
                <div>
                    <h5 class="text-xs font-bold text-slate-900">${item.title}</h5>
                    <p class="text-[11px] text-slate-600 leading-relaxed mt-1">${item.desc}</p>
                </div>
            `;
            container.appendChild(card);
        });
    }

    // Sync input <-> slider controls
    if (sliderRev && inputRev) {
        sliderRev.addEventListener('input', (e) => {
            inputRev.value = e.target.value;
            if (selectPreset) selectPreset.value = 'custom';
            recalculateScenario();
        });
        inputRev.addEventListener('input', (e) => {
            sliderRev.value = e.target.value;
            if (selectPreset) selectPreset.value = 'custom';
            recalculateScenario();
        });
    }

    if (sliderExp && inputExp) {
        sliderExp.addEventListener('input', (e) => {
            inputExp.value = e.target.value;
            if (selectPreset) selectPreset.value = 'custom';
            recalculateScenario();
        });
        inputExp.addEventListener('input', (e) => {
            sliderExp.value = e.target.value;
            if (selectPreset) selectPreset.value = 'custom';
            recalculateScenario();
        });
    }

    if (selectDept) {
        selectDept.addEventListener('change', recalculateScenario);
    }

    if (selectPreset) {
        selectPreset.addEventListener('change', (e) => {
            const val = e.target.value;
            if (val === 'best_case') {
                if (sliderRev) sliderRev.value = 10;
                if (inputRev) inputRev.value = 10;
                if (sliderExp) sliderExp.value = -5;
                if (inputExp) inputExp.value = -5;
            } else if (val === 'expected_case') {
                if (sliderRev) sliderRev.value = 0;
                if (inputRev) inputRev.value = 0;
                if (sliderExp) sliderExp.value = 0;
                if (inputExp) inputExp.value = 0;
            } else if (val === 'worst_case') {
                if (sliderRev) sliderRev.value = -10;
                if (inputRev) inputRev.value = -10;
                if (sliderExp) sliderExp.value = 5;
                if (inputExp) inputExp.value = 5;
            } else if (val === 'growth') {
                if (sliderRev) sliderRev.value = 15;
                if (inputRev) inputRev.value = 15;
                if (sliderExp) sliderExp.value = 5;
                if (inputExp) inputExp.value = 5;
            } else if (val === 'cost_cut') {
                if (sliderRev) sliderRev.value = 0;
                if (inputRev) inputRev.value = 0;
                if (sliderExp) sliderExp.value = -10;
                if (inputExp) inputExp.value = -10;
            }
            recalculateScenario();
        });
    }

    if (btnReset) {
        btnReset.addEventListener('click', () => {
            if (sliderRev) sliderRev.value = 0;
            if (inputRev) inputRev.value = 0;
            if (sliderExp) sliderExp.value = 0;
            if (inputExp) inputExp.value = 0;
            if (selectDept) selectDept.value = 'all';
            if (selectPreset) selectPreset.value = 'expected_case';
            recalculateScenario();
        });
    }

    if (btnApply) {
        btnApply.addEventListener('click', () => {
            recalculateScenario();
            // User feedback toast indicating isolation
            let toast = document.getElementById('whatif-toast');
            if (!toast) {
                toast = document.createElement('div');
                toast.id = 'whatif-toast';
                toast.className = 'fixed bottom-6 right-6 z-50 flex items-center gap-2.5 px-4 py-3 rounded-xl shadow-xl text-xs font-semibold bg-slate-900 text-white border border-slate-700 transition-all transform duration-300 opacity-0 translate-y-4';
                document.body.appendChild(toast);
            }
            toast.innerHTML = '<span class="material-symbols-outlined text-base text-emerald-400">check_circle</span><span>Scenario active in simulation mode. Source dataset remains isolated.</span>';
            setTimeout(() => {
                toast.classList.remove('opacity-0', 'translate-y-4');
                toast.classList.add('opacity-100', 'translate-y-0');
            }, 10);
            setTimeout(() => {
                toast.classList.remove('opacity-100', 'translate-y-0');
                toast.classList.add('opacity-0', 'translate-y-4');
            }, 3000);
        });
    }

    await loadActiveDataset();
    await loadBaselineData();

    window.addEventListener('resize', () => {
        comparisonChart?.resize();
    });
}

if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', initWhatIf);
} else {
    initWhatIf();
}
