/**
 * reports.js - Financial Reporting Suite & Decision Support
 * ========================================================
 * Powers the redesigned Report page with dynamic data from active dataset.
 */
import { api } from './api.js';
import { initEchart, safeSetOption } from './chart-engine.js';

document.addEventListener('DOMContentLoaded', async () => {
  // ── Currency and Number Formatters ──────────────────────────────
  const formatCurrency = (val) => {
    if (val === null || val === undefined || isNaN(val)) return '—';
    const abs = Math.abs(val);
    const sign = val < 0 ? '-' : '';
    if (abs >= 1000000000) return `${sign}₹${(abs / 1000000000).toFixed(2)} B`;
    if (abs >= 10000000) return `${sign}₹${(abs / 10000000).toFixed(2)} Cr`;
    if (abs >= 100000) return `${sign}₹${(abs / 100000).toFixed(2)} L`;
    if (abs >= 1000) return `${sign}₹${(abs / 1000).toFixed(1)} K`;
    return `${sign}₹${abs.toLocaleString('en-IN', { maximumFractionDigits: 0 })}`;
  };

  const formatShort = (val) => {
    if (val === null || val === undefined || isNaN(val)) return '0';
    const abs = Math.abs(val);
    const sign = val < 0 ? '-' : '';
    if (abs >= 10000000) return `${sign}${(abs / 10000000).toFixed(1)} Cr`;
    if (abs >= 100000) return `${sign}${(abs / 100000).toFixed(1)} L`;
    if (abs >= 1000) return `${sign}${(abs / 1000).toFixed(0)} K`;
    return `${sign}${abs}`;
  };

  // ── Global Chart Instances ──────────────────────────────────────
  const pnlChartEl = document.getElementById('chart-pnl-trend');
  const pnlChart = pnlChartEl ? initEchart(pnlChartEl) : null;

  const deptChartEl = document.getElementById('chart-department-performance');
  const deptChart = deptChartEl ? initEchart(deptChartEl) : null;

  let currentDeptMetric = 'all';
  let cachedReportData = null;
  let sortColumn = 'profit';
  let sortAscending = false;

  // ── Zoom Controls for P&L Chart ─────────────────────────────────
  function setupZoomControls(chart, inBtnId, outBtnId, resetBtnId) {
    if (!chart) return;
    let zoomSpan = 100;
    const inBtn = document.getElementById(inBtnId);
    const outBtn = document.getElementById(outBtnId);
    const resetBtn = document.getElementById(resetBtnId);

    if (inBtn) {
      inBtn.addEventListener('click', () => {
        zoomSpan = Math.max(20, zoomSpan - 25);
        const start = Math.max(0, 50 - zoomSpan / 2);
        const end = Math.min(100, 50 + zoomSpan / 2);
        chart.dispatchAction({ type: 'dataZoom', start, end });
      });
    }
    if (outBtn) {
      outBtn.addEventListener('click', () => {
        zoomSpan = Math.min(100, zoomSpan + 25);
        const start = Math.max(0, 50 - zoomSpan / 2);
        const end = Math.min(100, 50 + zoomSpan / 2);
        chart.dispatchAction({ type: 'dataZoom', start, end });
      });
    }
    if (resetBtn) {
      resetBtn.addEventListener('click', () => {
        zoomSpan = 100;
        chart.dispatchAction({ type: 'dataZoom', start: 0, end: 100 });
        chart.dispatchAction({ type: 'restore' });
      });
    }
  }
  setupZoomControls(pnlChart, 'zoom-in-pnl', 'zoom-out-pnl', 'zoom-reset-pnl');

  // ── Export Menu Toggle & Actions ────────────────────────────────
  const exportBtn = document.getElementById('btn-export-report');
  const exportMenu = document.getElementById('export-menu');
  if (exportBtn && exportMenu) {
    exportBtn.addEventListener('click', (e) => {
      e.stopPropagation();
      exportMenu.classList.toggle('hidden');
    });
    document.addEventListener('click', () => exportMenu.classList.add('hidden'));
  }

  const exportCsvBtn = document.getElementById('export-action-csv');
  if (exportCsvBtn) {
    exportCsvBtn.addEventListener('click', () => {
      const dept = document.getElementById('report-dept-select')?.value || 'all';
      window.open(`/api/v1/reports/csv?scope=${encodeURIComponent(dept === 'all' ? 'All Departments' : dept)}`, '_blank');
    });
  }

  const exportPdfBtn = document.getElementById('export-action-pdf');
  if (exportPdfBtn) {
    exportPdfBtn.addEventListener('click', () => {
      window.open('/api/v1/reports/pdf', '_blank');
    });
  }

  const exportPrintBtn = document.getElementById('export-action-print');
  if (exportPrintBtn) {
    exportPrintBtn.addEventListener('click', () => {
      window.print();
    });
  }

  // ── Filter Initialization ───────────────────────────────────────
  async function initFilters() {
    try {
      const active = await api.get('/api/v1/datasets/active').catch(() => null);
      if (active && active.filename) {
        const pill = document.getElementById('active-dataset-pill');
        if (pill) pill.textContent = active.filename.replace('.csv', '').replace('.xlsx', '');
      }

      const deptsRes = await api.get('/api/v1/pl/departments').catch(() => null);
      const deptSelect = document.getElementById('report-dept-select');
      if (deptSelect && deptsRes && deptsRes.departments) {
        const currVal = deptSelect.value;
        deptSelect.innerHTML = '<option value="all">All Departments</option>';
        deptsRes.departments.forEach(d => {
          if (d && d !== 'All Departments' && d !== 'Unknown') {
            const opt = document.createElement('option');
            opt.value = d;
            opt.textContent = d;
            deptSelect.appendChild(opt);
          }
        });
        if (currVal && Array.from(deptSelect.options).some(o => o.value === currVal)) {
          deptSelect.value = currVal;
        }
      }
    } catch (e) {
      console.warn('Filter initialization error:', e);
    }
  }

  // ── Load & Render Main Report ───────────────────────────────────
  async function loadReport() {
    const dept = document.getElementById('report-dept-select')?.value || 'all';
    const period = document.getElementById('report-period-select')?.value || 'all';
    const agg = document.getElementById('report-agg-select')?.value || 'monthly';

    try {
      const res = await api.get(`/api/v1/reports/data?report_type=all&dept=${encodeURIComponent(dept)}&period=${encodeURIComponent(period)}&agg=${encodeURIComponent(agg)}`);
      if (!res) return;
      cachedReportData = res;

      // 1. Update Periods list in dropdown if empty
      const periodSelect = document.getElementById('report-period-select');
      if (periodSelect && res.periods_list && periodSelect.options.length <= 1) {
        periodSelect.innerHTML = '';
        res.periods_list.forEach(p => {
          const opt = document.createElement('option');
          opt.value = p === 'All Periods' ? 'all' : p;
          opt.textContent = p;
          if (opt.value === period) opt.selected = true;
          periodSelect.appendChild(opt);
        });
      }

      // 2. Render Section B: Executive KPIs
      renderExecutiveKpis(res.kpis);

      // 3. Render Section C: P&L Performance Trend Chart
      renderPnlTrendChart(res.pnl_trend);

      // 4. Render Section D: Department Performance Chart
      renderDepartmentChart(res.department_performance, currentDeptMetric);

      // 5. Render Section E: Budget vs Actual Variance
      renderBudgetSection(res.budget_vs_actual);

      // 6. Render Section F: Financial Summary Table
      renderSummaryTable(res.financial_summary || res.department_performance || []);

      // 7. Render Section G: Management Insights
      renderManagementInsights(res.management_insights || []);

    } catch (err) {
      console.error('Failed to load report data:', err);
    }
  }

  // ── Section B: Executive KPIs ───────────────────────────────────
  function renderExecutiveKpis(kpis) {
    if (!kpis) return;

    const revEl = document.getElementById('kpi-total-revenue');
    const expEl = document.getElementById('kpi-total-expense');
    const profEl = document.getElementById('kpi-net-profit');
    const marginEl = document.getElementById('kpi-net-margin');
    const budgetStatusEl = document.getElementById('kpi-budget-status');
    const budgetVarEl = document.getElementById('kpi-budget-variance');
    const budgetIcon = document.getElementById('kpi-budget-icon');

    if (revEl) revEl.textContent = formatCurrency(kpis.total_revenue);
    if (expEl) expEl.textContent = formatCurrency(kpis.total_expense);
    if (profEl) {
      profEl.textContent = formatCurrency(kpis.net_profit);
      profEl.className = `text-lg font-bold mt-1 ${kpis.net_profit >= 0 ? 'text-emerald-600' : 'text-rose-600'}`;
    }
    if (marginEl) {
      marginEl.textContent = `${(kpis.net_margin || 0).toFixed(1)}%`;
      marginEl.className = `text-lg font-bold mt-1 ${(kpis.net_margin || 0) >= 0 ? 'text-slate-900' : 'text-rose-600'}`;
    }

    if (budgetStatusEl) {
      if (kpis.has_budget && kpis.total_budget) {
        budgetStatusEl.textContent = kpis.budget_status;
        budgetStatusEl.className = `text-lg font-bold mt-1 ${kpis.budget_status === 'On Budget' ? 'text-emerald-600' : 'text-rose-600'}`;
        if (budgetVarEl) {
          const sign = kpis.budget_variance > 0 ? '+' : '';
          budgetVarEl.textContent = `${sign}${formatCurrency(kpis.budget_variance)} (${Math.abs(kpis.budget_variance_pct).toFixed(1)}%)`;
        }
        if (budgetIcon) {
          budgetIcon.textContent = kpis.budget_status === 'On Budget' ? 'check_circle' : 'warning';
          budgetIcon.className = `material-symbols-outlined text-xs ${kpis.budget_status === 'On Budget' ? 'text-emerald-600' : 'text-rose-600'}`;
        }
      } else {
        budgetStatusEl.textContent = 'Actuals Only';
        budgetStatusEl.className = 'text-lg font-bold text-slate-700 mt-1';
        if (budgetVarEl) budgetVarEl.textContent = 'Budget Baseline Unset';
        if (budgetIcon) {
          budgetIcon.textContent = 'info';
          budgetIcon.className = 'material-symbols-outlined text-xs text-slate-400';
        }
      }
    }
  }

  // ── Section C: P&L Performance Trend Chart ──────────────────────
  function renderPnlTrendChart(trendData) {
    if (!pnlChart) return;
    const emptyEl = document.getElementById('pnl-trend-empty');

    if (!trendData || !trendData.periods || trendData.periods.length === 0) {
      pnlChart.clear();
      if (emptyEl) emptyEl.classList.remove('hidden');
      return;
    }
    if (emptyEl) emptyEl.classList.add('hidden');

    const periods = trendData.periods;
    const revVals = trendData.revenue || [];
    const expVals = trendData.expenses || trendData.expense || [];
    const profVals = trendData.profit || [];

    safeSetOption(pnlChart, {
      tooltip: {
        trigger: 'axis',
        axisPointer: { type: 'cross' },
        backgroundColor: '#ffffff',
        borderColor: '#e2e8f0',
        borderWidth: 1,
        extraCssText: 'box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.1), 0 2px 4px -2px rgba(0, 0, 0, 0.06); border-radius: 8px;',
        textStyle: { color: '#0f172a', fontSize: 11, fontFamily: 'Inter, sans-serif' },
        formatter: (params) => {
          let html = `<div style="padding:4px 8px;font-size:11px;color:#0f172a"><div style="font-weight:600;margin-bottom:4px;border-bottom:1px solid #e2e8f0;padding-bottom:2px">${params[0]?.axisValue}</div>`;
          params.forEach(p => {
            html += `<div style="display:flex;align-items:center;justify-content:space-between;gap:12px;margin:2px 0">
              <span style="display:flex;align-items:center;gap:4px">
                <span style="display:inline-block;width:7px;height:7px;border-radius:50%;background:${p.color}"></span>
                <span>${p.seriesName}:</span>
              </span>
              <b>${formatCurrency(p.value)}</b>
            </div>`;
          });
          html += '</div>';
          return html;
        }
      },
      grid: { left: '3%', right: '3%', top: '10%', bottom: '12%', containLabel: true },
      dataZoom: [{ type: 'inside' }],
      xAxis: {
        type: 'category',
        data: periods,
        boundaryGap: false,
        axisLine: { lineStyle: { color: '#E2E8F0' } },
        axisTick: { show: false },
        axisLabel: { color: '#64748B', fontSize: 10, interval: 'auto' }
      },
      yAxis: {
        type: 'value',
        axisLabel: {
          formatter: (v) => formatShort(v),
          color: '#94A3B8',
          fontSize: 10
        },
        splitLine: { lineStyle: { color: '#F1F5F9' } }
      },
      series: [
        {
          name: 'Revenue',
          type: 'line',
          smooth: 0.35,
          symbol: 'circle',
          symbolSize: 4,
          data: revVals,
          itemStyle: { color: '#3B82F6' },
          lineStyle: { width: 2.5, color: '#3B82F6' },
          areaStyle: {
            color: {
              type: 'linear', x: 0, y: 0, x2: 0, y2: 1,
              colorStops: [{ offset: 0, color: '#3B82F622' }, { offset: 1, color: '#3B82F600' }]
            }
          }
        },
        {
          name: 'Expense',
          type: 'line',
          smooth: 0.35,
          symbol: 'circle',
          symbolSize: 4,
          data: expVals,
          itemStyle: { color: '#EF4444' },
          lineStyle: { width: 2.5, color: '#EF4444' },
          areaStyle: {
            color: {
              type: 'linear', x: 0, y: 0, x2: 0, y2: 1,
              colorStops: [{ offset: 0, color: '#EF444422' }, { offset: 1, color: '#EF444400' }]
            }
          }
        },
        {
          name: 'Net Profit',
          type: 'line',
          smooth: 0.35,
          symbol: 'circle',
          symbolSize: 4,
          data: profVals,
          itemStyle: { color: '#10B981' },
          lineStyle: { width: 2.5, color: '#10B981' },
          areaStyle: {
            color: {
              type: 'linear', x: 0, y: 0, x2: 0, y2: 1,
              colorStops: [{ offset: 0, color: '#10B98122' }, { offset: 1, color: '#10B98100' }]
            }
          }
        }
      ]
    });
  }

  // ── Section D: Department Performance Chart ─────────────────────
  function renderDepartmentChart(deptList, metric = 'all') {
    if (!deptChart) return;
    const emptyEl = document.getElementById('dept-chart-empty');

    if (!deptList || deptList.length === 0) {
      deptChart.clear();
      if (emptyEl) emptyEl.classList.remove('hidden');
      return;
    }
    if (emptyEl) emptyEl.classList.add('hidden');

    const names = deptList.map(d => d.department);
    const series = [];

    if (metric === 'all' || metric === 'revenue') {
      series.push({
        name: 'Revenue',
        type: 'bar',
        barMaxWidth: 16,
        itemStyle: { color: '#3B82F6', borderRadius: [3, 3, 0, 0] },
        data: deptList.map(d => d.revenue)
      });
    }
    if (metric === 'all' || metric === 'expense') {
      series.push({
        name: 'Expense',
        type: 'bar',
        barMaxWidth: 16,
        itemStyle: { color: '#EF4444', borderRadius: [3, 3, 0, 0] },
        data: deptList.map(d => d.expense)
      });
    }
    if (metric === 'all' || metric === 'profit') {
      series.push({
        name: 'Net Profit',
        type: 'bar',
        barMaxWidth: 16,
        itemStyle: { color: '#10B981', borderRadius: [3, 3, 0, 0] },
        data: deptList.map(d => d.profit)
      });
    }
    if (metric === 'margin') {
      series.push({
        name: 'Margin %',
        type: 'bar',
        barMaxWidth: 20,
        itemStyle: { color: '#5B5CEB', borderRadius: [3, 3, 0, 0] },
        data: deptList.map(d => Number((d.margin || 0).toFixed(1)))
      });
    }

    safeSetOption(deptChart, {
      tooltip: {
        trigger: 'axis',
        axisPointer: { type: 'shadow' },
        backgroundColor: '#ffffff',
        borderColor: '#e2e8f0',
        borderWidth: 1,
        textStyle: { color: '#0f172a', fontSize: 11, fontFamily: 'Inter, sans-serif' },
        formatter: (params) => {
          let html = `<div style="padding:4px 8px;font-size:11px;color:#0f172a"><div style="font-weight:600;margin-bottom:4px;border-bottom:1px solid #e2e8f0;padding-bottom:2px">${params[0]?.axisValue}</div>`;
          params.forEach(p => {
            const formatted = metric === 'margin' ? `${p.value}%` : formatCurrency(p.value);
            html += `<div style="display:flex;align-items:center;justify-content:space-between;gap:12px;margin:2px 0">
              <span style="display:flex;align-items:center;gap:4px">
                <span style="display:inline-block;width:7px;height:7px;border-radius:50%;background:${p.color}"></span>
                <span>${p.seriesName}:</span>
              </span>
              <b>${formatted}</b>
            </div>`;
          });
          html += '</div>';
          return html;
        }
      },
      legend: { top: 0, icon: 'circle', textStyle: { fontSize: 10, color: '#64748B' } },
      grid: { left: '3%', right: '3%', top: '35px', bottom: '15%', containLabel: true },
      xAxis: {
        type: 'category',
        data: names,
        axisLine: { lineStyle: { color: '#E2E8F0' } },
        axisTick: { show: false },
        axisLabel: {
          color: '#64748B',
          fontSize: 9,
          rotate: names.length > 6 ? 30 : 0,
          interval: 0
        }
      },
      yAxis: {
        type: 'value',
        axisLabel: {
          formatter: (v) => metric === 'margin' ? `${v}%` : formatShort(v),
          color: '#94A3B8',
          fontSize: 10
        },
        splitLine: { lineStyle: { color: '#F1F5F9' } }
      },
      series
    });
  }

  // Department Metric Switch Handlers
  const metricSwitchContainer = document.getElementById('dept-metric-switch');
  if (metricSwitchContainer) {
    metricSwitchContainer.querySelectorAll('button').forEach(btn => {
      btn.addEventListener('click', () => {
        metricSwitchContainer.querySelectorAll('button').forEach(b => {
          b.className = 'px-2 py-0.5 rounded-md text-[10px] font-medium text-slate-600 hover:text-slate-900 cursor-pointer';
        });
        btn.className = 'px-2 py-0.5 rounded-md text-[10px] font-bold bg-white text-slate-900 shadow-xs cursor-pointer';
        currentDeptMetric = btn.getAttribute('data-metric') || 'all';
        if (cachedReportData && cachedReportData.department_performance) {
          renderDepartmentChart(cachedReportData.department_performance, currentDeptMetric);
        }
      });
    });
  }

  // ── Section E: Budget vs Actual ─────────────────────────────────
  function renderBudgetSection(budgetData) {
    const wrapper = document.getElementById('budget-content-wrapper');
    const badge = document.getElementById('budget-summary-badge');
    if (!wrapper) return;

    if (!budgetData || !budgetData.has_budget || !budgetData.total_budget) {
      if (badge) badge.textContent = 'Actuals Baseline';
      wrapper.innerHTML = `
        <div class="h-full flex flex-col items-center justify-center text-center p-6 bg-slate-50/80 rounded-xl border border-slate-100">
          <div class="w-10 h-10 rounded-full bg-purple-50 border border-purple-100 flex items-center justify-center text-purple-600 mb-2.5">
            <span class="material-symbols-outlined text-xl">balance</span>
          </div>
          <h4 class="text-xs font-bold text-slate-800">Budget data unavailable for this dataset</h4>
          <p class="text-[11px] text-slate-500 max-w-xs mt-1 leading-relaxed">
            The active dataset contains real transaction actuals without a mapped budget column. All financial metrics accurately reflect actual inflows and spend.
          </p>
          <span class="mt-3 px-2.5 py-0.5 rounded-full text-[10px] font-semibold bg-slate-200/70 text-slate-600">
            Historical Actuals Reporting
          </span>
        </div>
      `;
      return;
    }

    if (badge) badge.textContent = budgetData.status || 'Audited';

    const items = (budgetData.departments || []).filter(d => d.budget && d.budget > 0);
    const topOver = items.filter(d => (d.variance || 0) > 0).slice(0, 3);
    const topUnder = items.filter(d => (d.variance || 0) <= 0).slice(0, 3);

    let html = `
      <div class="space-y-3">
        <!-- Top Stats Row -->
        <div class="grid grid-cols-2 gap-2">
          <div class="p-2.5 bg-slate-50 rounded-xl border border-slate-100">
            <span class="text-[10px] font-bold text-slate-400 uppercase">Allocated Budget</span>
            <div class="text-sm font-bold text-slate-900 mt-0.5">${formatCurrency(budgetData.total_budget)}</div>
          </div>
          <div class="p-2.5 ${budgetData.total_variance > 0 ? 'bg-rose-50/60 border-rose-100' : 'bg-emerald-50/60 border-emerald-100'} rounded-xl border">
            <span class="text-[10px] font-bold ${budgetData.total_variance > 0 ? 'text-rose-600' : 'text-emerald-600'} uppercase">Net Variance</span>
            <div class="text-sm font-bold ${budgetData.total_variance > 0 ? 'text-rose-700' : 'text-emerald-700'} mt-0.5">
              ${budgetData.total_variance > 0 ? '+' : ''}${formatCurrency(budgetData.total_variance)}
            </div>
          </div>
        </div>

        <!-- Department Variance Progress Bars -->
        <div class="space-y-2 max-h-44 overflow-y-auto pr-1">
    `;

    items.slice(0, 5).forEach(item => {
      const pct = item.budget > 0 ? Math.min(100, Math.round((item.expense / item.budget) * 100)) : 0;
      const isOver = item.variance > 0;
      html += `
        <div>
          <div class="flex items-center justify-between text-[11px] mb-0.5">
            <span class="font-semibold text-slate-800">${item.department}</span>
            <span class="text-[10px] ${isOver ? 'text-rose-600 font-bold' : 'text-emerald-600 font-semibold'}">
              ${formatCurrency(item.expense)} / ${formatCurrency(item.budget)} (${isOver ? '+' : ''}${item.variance_pct ? item.variance_pct.toFixed(0) : 0}%)
            </span>
          </div>
          <div class="w-full bg-slate-100 rounded-full h-1.5 overflow-hidden">
            <div class="${isOver ? 'bg-rose-500' : 'bg-emerald-500'} h-1.5 rounded-full" style="width: ${pct}%"></div>
          </div>
        </div>
      `;
    });

    html += `
        </div>
      </div>
    `;

    wrapper.innerHTML = html;
  }

  // ── Section F: Financial Summary Statement (Sortable Table) ────
  function renderSummaryTable(rows) {
    const tbody = document.getElementById('summary-table-body');
    const countEl = document.getElementById('table-row-count');
    if (!tbody) return;

    if (!rows || rows.length === 0) {
      tbody.innerHTML = `<tr><td colspan="9" class="px-4 py-8 text-center text-slate-400 text-xs">No financial records found for the active filter criteria.</td></tr>`;
      if (countEl) countEl.textContent = '0 departments';
      return;
    }

    if (countEl) countEl.textContent = `${rows.length} operating divisions`;

    // Sort rows
    const sorted = [...rows].sort((a, b) => {
      let valA = a[sortColumn];
      let valB = b[sortColumn];
      if (typeof valA === 'string') {
        return sortAscending ? valA.localeCompare(valB) : valB.localeCompare(valA);
      }
      valA = valA || 0;
      valB = valB || 0;
      return sortAscending ? valA - valB : valB - valA;
    });

    let html = '';
    sorted.forEach((row, idx) => {
      const margin = row.margin !== undefined && row.margin !== null ? row.margin : ((row.profit / row.revenue) * 100);
      const isProfitable = (row.profit || 0) >= 0;
      const marginColor = margin >= 20 ? 'text-emerald-600 bg-emerald-50' : (margin >= 0 ? 'text-blue-600 bg-blue-50' : 'text-rose-600 bg-rose-50');

      let statusBadge = '<span class="text-slate-400 text-[10px]">—</span>';
      if (row.has_budget && row.status) {
        const isOver = row.status === 'Over Budget';
        statusBadge = `<span class="inline-flex items-center px-2 py-0.5 rounded-full text-[9px] font-bold ${isOver ? 'bg-rose-50 text-rose-700 border border-rose-200' : 'bg-emerald-50 text-emerald-700 border border-emerald-200'}">${row.status}</span>`;
      } else if (isProfitable) {
        statusBadge = `<span class="inline-flex items-center px-2 py-0.5 rounded-full text-[9px] font-bold bg-emerald-50 text-emerald-700 border border-emerald-200">Profitable</span>`;
      } else {
        statusBadge = `<span class="inline-flex items-center px-2 py-0.5 rounded-full text-[9px] font-bold bg-rose-50 text-rose-700 border border-rose-200">Loss</span>`;
      }

      html += `
        <tr class="hover:bg-slate-50/70 transition-colors">
          <td class="px-4 py-2.5 font-semibold text-slate-900 flex items-center gap-2">
            <span class="w-5 h-5 rounded-md bg-slate-100 text-slate-600 font-bold text-[10px] flex items-center justify-center">${idx + 1}</span>
            <span>${row.department}</span>
          </td>
          <td class="px-4 py-2.5 text-right font-medium text-slate-900">${formatCurrency(row.revenue)}</td>
          <td class="px-4 py-2.5 text-right font-medium text-slate-600">${formatCurrency(row.expense)}</td>
          <td class="px-4 py-2.5 text-right font-bold ${isProfitable ? 'text-emerald-600' : 'text-rose-600'}">${formatCurrency(row.profit)}</td>
          <td class="px-4 py-2.5 text-right">
            <span class="px-2 py-0.5 rounded-md text-[10px] font-bold ${marginColor}">${margin.toFixed(1)}%</span>
          </td>
          <td class="px-4 py-2.5 text-right text-slate-600">${row.has_budget ? formatCurrency(row.budget) : '—'}</td>
          <td class="px-4 py-2.5 text-right font-medium ${(row.variance || 0) > 0 ? 'text-rose-600' : 'text-emerald-600'}">
            ${row.has_budget ? `${(row.variance || 0) > 0 ? '+' : ''}${formatCurrency(row.variance)}` : '—'}
          </td>
          <td class="px-4 py-2.5 text-right font-semibold ${(row.variance_pct || 0) > 0 ? 'text-rose-600' : 'text-emerald-600'}">
            ${row.has_budget ? `${(row.variance_pct || 0) > 0 ? '+' : ''}${(row.variance_pct || 0).toFixed(1)}%` : '—'}
          </td>
          <td class="px-4 py-2.5 text-center">${statusBadge}</td>
        </tr>
      `;
    });

    tbody.innerHTML = html;
  }

  // Sortable Table Header Clicks
  document.querySelectorAll('.sortable-th').forEach(th => {
    th.addEventListener('click', () => {
      const col = th.getAttribute('data-col');
      if (sortColumn === col) {
        sortAscending = !sortAscending;
      } else {
        sortColumn = col;
        sortAscending = false;
      }
      if (cachedReportData) {
        renderSummaryTable(cachedReportData.financial_summary || cachedReportData.department_performance || []);
      }
    });
  });

  // ── Section G: Management Insights ──────────────────────────────
  function renderManagementInsights(insights) {
    const container = document.getElementById('management-insights-container');
    if (!container) return;

    if (!insights || insights.length === 0) {
      container.innerHTML = `<div class="col-span-2 text-slate-400 text-xs">No analytical insights available for the selected parameters.</div>`;
      return;
    }

    const icons = ['verified', 'trending_up', 'insights', 'account_balance', 'analytics', 'crisis_alert'];
    let html = '';
    insights.forEach((item, idx) => {
      const icon = icons[idx % icons.length];
      html += `
        <div class="flex items-start gap-2.5 p-3 rounded-xl bg-white border border-slate-100 custom-shadow">
          <span class="material-symbols-outlined text-primary text-sm mt-0.5">${icon}</span>
          <p class="text-slate-700 text-xs leading-relaxed font-normal">${item}</p>
        </div>
      `;
    });

    container.innerHTML = html;
  }

  // ── Event Listeners ─────────────────────────────────────────────
  const deptSelect = document.getElementById('report-dept-select');
  const periodSelect = document.getElementById('report-period-select');
  const aggSelect = document.getElementById('report-agg-select');
  const refreshBtn = document.getElementById('btn-refresh-report');

  if (deptSelect) deptSelect.addEventListener('change', loadReport);
  if (periodSelect) periodSelect.addEventListener('change', loadReport);
  if (aggSelect) aggSelect.addEventListener('change', loadReport);
  if (refreshBtn) refreshBtn.addEventListener('click', loadReport);

  // Resize charts on window resize
  window.addEventListener('resize', () => {
    if (pnlChart) pnlChart.resize();
    if (deptChart) deptChart.resize();
  });

  // Initial Load
  await initFilters();
  await loadReport();
});
