import { api } from './api.js';
import { initEchart, safeSetOption } from './chart-engine.js';

document.addEventListener('DOMContentLoaded', async () => {
    let baselineData = {
        revenue: 0,
        expense: 0,
        profit: 0,
        margin: 0,
        departments: []
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
    let comparisonChart = chartEl ? initEchart(chartEl) : null;

    // Controls
    const sliderRev = document.getElementById('slider-rev-growth');
    const inputRev = document.getElementById('input-rev-growth');
    const sliderExp = document.getElementById('slider-exp-growth');
    const inputExp = document.getElementById('input-exp-growth');
    const selectDept = document.getElementById('select-whatif-dept');
    const selectPreset = document.getElementById('scenario-preset');
    const btnReset = document.getElementById('btn-reset-scenario');
    const btnApply = document.getElementById('btn-apply-scenario');

    async function loadActiveDataset() {
        try {
            const active = await api.get('/api/v1/datasets/active').catch(() => null);
            if (active && active.filename) {
                const pill = document.getElementById('active-dataset-name');
                if (pill) pill.textContent = active.filename.replace('.csv', '').replace('.xlsx', '');
            }
        } catch (e) {
            console.warn('Dataset info fetch error:', e);
        }
    }

    async function loadBaselineData() {
        try {
            const [summary, charts] = await Promise.all([
                api.get('/api/v1/pl/summary?dept=all').catch(() => null),
                api.get('/api/v1/pl/charts?agg=monthly').catch(() => null)
            ]);

            if (summary && summary.kpis) {
                baselineData.revenue = summary.kpis.revenue || 0;
                baselineData.expense = summary.kpis.expense || 0;
                baselineData.profit = summary.kpis.profit !== undefined ? summary.kpis.profit : (baselineData.revenue - baselineData.expense);
                baselineData.margin = (baselineData.revenue > 0) ? ((baselineData.profit / baselineData.revenue) * 100) : 0;
            } else if (summary) {
                baselineData.revenue = summary.total_revenue || 0;
                baselineData.expense = summary.total_expense || 0;
                baselineData.profit = summary.net_profit || (baselineData.revenue - baselineData.expense);
                baselineData.margin = summary.net_margin_percentage || ((baselineData.profit / (baselineData.revenue || 1)) * 100);
            }

            if (charts && charts.department_breakdown) {
                baselineData.departments = charts.department_breakdown.map(d => ({
                    name: d.department || d.name || 'General',
                    revenue: d.revenue || 0,
                    expense: d.expense || 0,
                    profit: (d.revenue || 0) - (d.expense || 0)
                }));
            }

            // Populate department selector
            if (selectDept && baselineData.departments.length > 0) {
                selectDept.innerHTML = '<option value="all" selected>All Departments (Enterprise Wide)</option>';
                baselineData.departments.forEach(d => {
                    const opt = document.createElement('option');
                    opt.value = d.name;
                    opt.textContent = `${d.name} (${formatCurrency(d.revenue)})`;
                    selectDept.appendChild(opt);
                });
            }

            recalculateScenario();
        } catch (err) {
            console.error('Failed to load baseline data for What-If:', err);
        }
    }

    function recalculateScenario() {
        const revGrowthPct = parseFloat(sliderRev.value) || 0;
        const expGrowthPct = parseFloat(sliderExp.value) || 0;
        const targetDept = selectDept ? selectDept.value : 'all';

        let scenRev = 0;
        let scenExp = 0;
        const deptImpacts = [];

        if (targetDept === 'all' || targetDept.toLowerCase() === 'overall') {
            scenRev = baselineData.revenue * (1 + revGrowthPct / 100);
            scenExp = baselineData.expense * (1 + expGrowthPct / 100);

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
                    scenRev: dScenRev
                });
            });
        } else {
            // Apply adjustment ONLY to the selected department's contribution
            baselineData.departments.forEach(d => {
                if (d.name.toLowerCase() === targetDept.toLowerCase()) {
                    const dScenRev = d.revenue * (1 + revGrowthPct / 100);
                    const dScenExp = d.expense * (1 + expGrowthPct / 100);
                    const dScenProf = dScenRev - dScenExp;
                    const dDiff = dScenProf - d.profit;
                    scenRev += dScenRev;
                    scenExp += dScenExp;
                    deptImpacts.push({
                        name: d.name,
                        baseProfit: d.profit,
                        scenProfit: dScenProf,
                        diff: dDiff,
                        baseRev: d.revenue,
                        scenRev: dScenRev
                    });
                } else {
                    scenRev += d.revenue;
                    scenExp += d.expense;
                    deptImpacts.push({
                        name: d.name,
                        baseProfit: d.profit,
                        scenProfit: d.profit,
                        diff: 0,
                        baseRev: d.revenue,
                        scenRev: d.revenue
                    });
                }
            });
        }

        const scenProf = scenRev - scenExp;
        const scenMargin = scenRev > 0 ? (scenProf / scenRev) * 100 : 0;

        const revDiff = scenRev - baselineData.revenue;
        const expDiff = scenExp - baselineData.expense;
        const profDiff = scenProf - baselineData.profit;
        const marginDiff = scenMargin - baselineData.margin;

        // 1. Update KPI comparison cards
        const baseRevEl = document.getElementById('kpi-base-rev');
        const scenRevEl = document.getElementById('kpi-scen-rev');
        const revDiffEl = document.getElementById('kpi-diff-rev');

        if (baseRevEl) baseRevEl.textContent = formatCurrency(baselineData.revenue);
        if (scenRevEl) scenRevEl.textContent = formatCurrency(scenRev);
        if (revDiffEl) {
            const isPos = revDiff >= 0;
            revDiffEl.className = isPos ? 'font-bold text-emerald-600' : 'font-bold text-rose-500';
            const pctText = baselineData.revenue > 0 ? ((revDiff / baselineData.revenue) * 100).toFixed(1) : '0.0';
            revDiffEl.textContent = `${isPos ? '+' : ''}${formatCurrency(revDiff)} (${revDiff >= 0 ? '+' : ''}${pctText}%)`;
        }

        const baseExpEl = document.getElementById('kpi-base-exp');
        const scenExpEl = document.getElementById('kpi-scen-exp');
        const expDiffEl = document.getElementById('kpi-diff-exp');

        if (baseExpEl) baseExpEl.textContent = formatCurrency(baselineData.expense);
        if (scenExpEl) scenExpEl.textContent = formatCurrency(scenExp);
        if (expDiffEl) {
            const isPos = expDiff <= 0; // lower expense is positive
            expDiffEl.className = isPos ? 'font-bold text-emerald-600' : 'font-bold text-rose-500';
            const pctText = baselineData.expense > 0 ? ((expDiff / baselineData.expense) * 100).toFixed(1) : '0.0';
            expDiffEl.textContent = `${expDiff >= 0 ? '+' : ''}${formatCurrency(expDiff)} (${expDiff >= 0 ? '+' : ''}${pctText}%)`;
        }

        const baseProfEl = document.getElementById('kpi-base-prof');
        const scenProfEl = document.getElementById('kpi-scen-prof');
        const profDiffEl = document.getElementById('kpi-diff-prof');

        if (baseProfEl) baseProfEl.textContent = formatCurrency(baselineData.profit);
        if (scenProfEl) scenProfEl.textContent = formatCurrency(scenProf);
        if (profDiffEl) {
            const isPos = profDiff >= 0;
            profDiffEl.className = isPos ? 'font-bold text-emerald-600' : 'font-bold text-rose-500';
            const profPct = baselineData.profit !== 0 ? ((profDiff / Math.abs(baselineData.profit)) * 100) : 0;
            profDiffEl.textContent = `${isPos ? '+' : ''}${formatCurrency(profDiff)} (${profDiff >= 0 ? '+' : ''}${profPct.toFixed(1)}%)`;
        }

        const baseMrgEl = document.getElementById('kpi-base-mrg');
        const scenMrgEl = document.getElementById('kpi-scen-mrg');
        const mrgDiffEl = document.getElementById('kpi-diff-mrg');

        if (baseMrgEl) baseMrgEl.textContent = `${baselineData.margin.toFixed(1)}%`;
        if (scenMrgEl) scenMrgEl.textContent = `${scenMargin.toFixed(1)}%`;
        if (mrgDiffEl) {
            const isPos = marginDiff >= 0;
            mrgDiffEl.className = isPos ? 'font-bold text-emerald-600' : 'font-bold text-rose-500';
            mrgDiffEl.textContent = `${isPos ? '+' : ''}${marginDiff.toFixed(1)} pp`;
        }

        // 2. Render Comparative Chart
        renderComparativeChart(baselineData.revenue, scenRev, baselineData.expense, scenExp, baselineData.profit, scenProf);

        // 3. Render Department Impact Ranking
        renderDepartmentImpact(deptImpacts);

        // 4. Render Dynamic What-If Insights
        renderWhatIfInsights(revGrowthPct, expGrowthPct, profDiff, marginDiff, deptImpacts, targetDept);
    }

    function renderComparativeChart(bRev, sRev, bExp, sExp, bProf, sProf) {
        if (!comparisonChart) return;

        safeSetOption(comparisonChart, {
            title: { text: '' },
            tooltip: {
                trigger: 'axis',
                backgroundColor: '#ffffff',
                borderColor: '#e2e8f0',
                borderWidth: 1,
                textStyle: { color: '#0f172a', fontSize: 11, fontFamily: 'Inter' },
                formatter: (params) => {
                    if (!params || !params.length) return '';
                    let html = `<div style="padding:4px 8px;font-size:11px">
                        <b>${params[0].axisValue}</b><br/>`;
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

        container.innerHTML = '';
        const sorted = [...deptImpacts].sort((a, b) => Math.abs(b.diff) - Math.abs(a.diff));

        sorted.forEach(d => {
            const isPos = d.diff >= 0;
            const badgeClass = isPos ? 'bg-emerald-50 text-emerald-700 border-emerald-200' : 'bg-rose-50 text-rose-700 border-rose-200';
            const sign = isPos ? '+' : '';

            const row = document.createElement('div');
            row.className = 'py-2.5 flex items-center justify-between';
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

    function renderWhatIfInsights(revGrowth, expGrowth, profDiff, marginDiff, deptImpacts, targetDept) {
        const container = document.getElementById('whatif-insights-container');
        if (!container) return;

        container.innerHTML = '';
        const topDept = [...deptImpacts].sort((a, b) => Math.abs(b.diff) - Math.abs(a.diff))[0];
        const scopeDesc = targetDept === 'all' ? 'Enterprise-wide' : `${targetDept} Department`;

        const insights = [
            {
                title: 'Bottom-Line Net Sensitivity',
                desc: `Applying a <b>${revGrowth >= 0 ? '+' : ''}${revGrowth}%</b> revenue shift with a <b>${expGrowth >= 0 ? '+' : ''}${expGrowth}%</b> expense change (${scopeDesc}) creates a <b>${profDiff >= 0 ? '+' : ''}${formatCurrency(profDiff)}</b> bottom-line variance.`,
                icon: 'trending_up',
                color: profDiff >= 0 ? 'text-emerald-600' : 'text-rose-500',
                bg: profDiff >= 0 ? 'bg-emerald-50/50 border-emerald-100' : 'bg-rose-50/50 border-rose-100'
            },
            {
                title: 'Operating Margin Elasticity',
                desc: `Projected operating margin shifts by <b>${marginDiff >= 0 ? '+' : ''}${marginDiff.toFixed(1)} percentage points</b>, demonstrating the leverage difference between topline growth and fixed cost discipline.`,
                icon: 'percent',
                color: marginDiff >= 0 ? 'text-indigo-600' : 'text-amber-600',
                bg: 'bg-slate-50 border-slate-100'
            },
            {
                title: 'Primary Scenario Driver',
                desc: topDept ? `<b>${topDept.name}</b> experiences the largest impact with a projected <b>${topDept.diff >= 0 ? '+' : ''}${formatCurrency(topDept.diff)}</b> variance.` : 'Enterprise wide department impact balanced.',
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

    // Two-way sync controls
    sliderRev.addEventListener('input', (e) => {
        inputRev.value = e.target.value;
        selectPreset.value = 'custom';
        recalculateScenario();
    });
    inputRev.addEventListener('input', (e) => {
        sliderRev.value = e.target.value;
        selectPreset.value = 'custom';
        recalculateScenario();
    });

    sliderExp.addEventListener('input', (e) => {
        inputExp.value = e.target.value;
        selectPreset.value = 'custom';
        recalculateScenario();
    });
    inputExp.addEventListener('input', (e) => {
        sliderExp.value = e.target.value;
        selectPreset.value = 'custom';
        recalculateScenario();
    });

    selectDept.addEventListener('change', recalculateScenario);

    selectPreset.addEventListener('change', (e) => {
        const val = e.target.value;
        if (val === 'best_case') {
            sliderRev.value = 10; inputRev.value = 10;
            sliderExp.value = -5; inputExp.value = -5;
        } else if (val === 'expected_case') {
            sliderRev.value = 0; inputRev.value = 0;
            sliderExp.value = 0; inputExp.value = 0;
        } else if (val === 'worst_case') {
            sliderRev.value = -10; inputRev.value = -10;
            sliderExp.value = 5;  inputExp.value = 5;
        } else if (val === 'growth') {
            sliderRev.value = 15; inputRev.value = 15;
            sliderExp.value = 5;  inputExp.value = 5;
        } else if (val === 'cost_cut') {
            sliderRev.value = 0;  inputRev.value = 0;
            sliderExp.value = -10; inputExp.value = -10;
        }
        recalculateScenario();
    });

    btnReset.addEventListener('click', () => {
        sliderRev.value = 0; inputRev.value = 0;
        sliderExp.value = 0; inputExp.value = 0;
        selectDept.value = 'all';
        selectPreset.value = 'expected_case';
        recalculateScenario();
    });

    btnApply.addEventListener('click', recalculateScenario);

    await loadActiveDataset();
    await loadBaselineData();

    window.addEventListener('resize', () => {
        comparisonChart?.resize();
    });
});
