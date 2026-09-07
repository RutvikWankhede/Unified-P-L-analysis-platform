import { api } from './api.js';
import { initEchart, safeSetOption } from './chart-engine.js';

document.addEventListener('DOMContentLoaded', async () => {
  let currentReportType = 'executive';
  let reportChart = null;

  const formatCurrency = (val) => {
    if (val === null || val === undefined || isNaN(val)) return '₹0';
    const abs = Math.abs(val);
    const sign = val < 0 ? '-' : '';
    if (abs >= 1000000000) return `${sign}₹${(abs / 1000000000).toFixed(2)} B`;
    if (abs >= 10000000) return `${sign}₹${(abs / 10000000).toFixed(2)} Cr`;
    if (abs >= 100000) return `${sign}₹${(abs / 100000).toFixed(2)} L`;
    if (abs >= 1000) return `${sign}₹${(abs / 1000).toFixed(1)} K`;
    return `${sign}₹${abs.toLocaleString('en-IN')}`;
  };

  const chartEl = document.getElementById('chart-report-trend');
  if (chartEl) {
    reportChart = initEchart(chartEl);
  }

  // Populate Active Dataset pill & department filter
  async function initFilters() {
    try {
      const active = await api.get('/api/v1/datasets/active').catch(() => null);
      if (active && active.filename) {
        const pill = document.getElementById('active-dataset-pill');
        if (pill) pill.textContent = active.filename.replace('.csv', '').replace('.xlsx', '');
      }

      const summary = await api.get('/api/v1/pl/summary?dept=all').catch(() => null);
      const deptSelect = document.getElementById('report-filter-dept');
      if (deptSelect && summary && summary.departments) {
        deptSelect.innerHTML = '<option value="all">All Departments</option>';
        summary.departments.forEach(d => {
          if (d && d !== 'All Departments' && d !== 'Unknown') {
            const opt = document.createElement('option');
            opt.value = d;
            opt.textContent = d;
            deptSelect.appendChild(opt);
          }
        });
      }
    } catch (e) {
      console.warn('Filter init error:', e);
    }
  }

  async function loadReport(type = currentReportType) {
    currentReportType = type;

    // Highlight active card
    document.querySelectorAll('.report-card').forEach(card => {
      if (card.getAttribute('data-report-type') === type) {
        card.classList.add('active');
      } else {
        card.classList.remove('active');
      }
    });

    const dept = document.getElementById('report-filter-dept')?.value || 'all';
    const period = document.getElementById('report-filter-period')?.value || 'monthly';

    try {
      const res = await api.get(`/api/v1/reports/data?report_type=${type}&dept=${dept}&period=${period}`);
      if (!res) return;

      // Update Header
      const titleEl = document.getElementById('report-display-title');
      const descEl = document.getElementById('report-display-desc');
      const timeEl = document.getElementById('report-timestamp');
      const dsEl = document.getElementById('report-dataset-name');

      if (titleEl) titleEl.textContent = res.title;
      if (descEl) descEl.textContent = res.description;
      if (timeEl) timeEl.textContent = res.generated_at;
      if (dsEl) dsEl.textContent = res.dataset_name;

      // Update KPIs Grid
      const kpiGrid = document.getElementById('report-kpi-grid');
      if (kpiGrid && res.kpis) {
        kpiGrid.innerHTML = '';
        const k = res.kpis;

        if (type === 'executive') {
          kpiGrid.innerHTML = `
            <div class="p-3 bg-blue-50/60 rounded-xl border border-blue-100">
              <p class="text-[10px] font-bold text-blue-700 uppercase">Total Revenue</p>
              <h4 class="text-base font-bold text-slate-900 mt-0.5">${formatCurrency(k.primary_value)}</h4>
            </div>
            <div class="p-3 bg-rose-50/60 rounded-xl border border-rose-100">
              <p class="text-[10px] font-bold text-rose-700 uppercase">Total Expenses</p>
              <h4 class="text-base font-bold text-slate-900 mt-0.5">${formatCurrency(k.secondary_value)}</h4>
            </div>
            <div class="p-3 bg-emerald-50/60 rounded-xl border border-emerald-100">
              <p class="text-[10px] font-bold text-emerald-700 uppercase">Net Profit</p>
              <h4 class="text-base font-bold text-emerald-600 mt-0.5">${formatCurrency(k.net_profit)}</h4>
            </div>
            <div class="p-3 bg-indigo-50/60 rounded-xl border border-indigo-100">
              <p class="text-[10px] font-bold text-indigo-700 uppercase">Operating Margin</p>
              <h4 class="text-base font-bold text-indigo-600 mt-0.5">${k.operating_margin?.toFixed(2)}%</h4>
            </div>
          `;
        } else if (type === 'department') {
          kpiGrid.innerHTML = `
            <div class="p-3 bg-indigo-50/60 rounded-xl border border-indigo-100">
              <p class="text-[10px] font-bold text-indigo-700 uppercase">Tracked Units</p>
              <h4 class="text-base font-bold text-slate-900 mt-0.5">${k.tracked_departments} Departments</h4>
            </div>
            <div class="p-3 bg-emerald-50/60 rounded-xl border border-emerald-100">
              <p class="text-[10px] font-bold text-emerald-700 uppercase">Top Profit Unit</p>
              <h4 class="text-base font-bold text-slate-900 mt-0.5">${k.top_performing_dept} (${formatCurrency(k.top_dept_profit)})</h4>
            </div>
            <div class="p-3 bg-blue-50/60 rounded-xl border border-blue-100">
              <p class="text-[10px] font-bold text-blue-700 uppercase">Top Revenue Unit</p>
              <h4 class="text-base font-bold text-slate-900 mt-0.5">${k.top_revenue_dept} (${formatCurrency(k.top_dept_revenue)})</h4>
            </div>
            <div class="p-3 bg-amber-50/60 rounded-xl border border-amber-100">
              <p class="text-[10px] font-bold text-amber-700 uppercase">Data Health</p>
              <h4 class="text-base font-bold text-slate-900 mt-0.5">100% Normalized</h4>
            </div>
          `;
        } else if (type === 'variance') {
          const isOver = k.net_variance > 0;
          kpiGrid.innerHTML = `
            <div class="p-3 bg-slate-50 rounded-xl border border-slate-200">
              <p class="text-[10px] font-bold text-slate-600 uppercase">Allocated Budget</p>
              <h4 class="text-base font-bold text-slate-900 mt-0.5">${formatCurrency(k.total_budget)}</h4>
            </div>
            <div class="p-3 bg-blue-50/60 rounded-xl border border-blue-100">
              <p class="text-[10px] font-bold text-blue-700 uppercase">Actual Expenditure</p>
              <h4 class="text-base font-bold text-slate-900 mt-0.5">${formatCurrency(k.total_actual_spend)}</h4>
            </div>
            <div class="p-3 ${isOver ? 'bg-rose-50/60 border-rose-100' : 'bg-emerald-50/60 border-emerald-100'} rounded-xl border">
              <p class="text-[10px] font-bold ${isOver ? 'text-rose-700' : 'text-emerald-700'} uppercase">Net Variance</p>
              <h4 class="text-base font-bold ${isOver ? 'text-rose-600' : 'text-emerald-600'} mt-0.5">${formatCurrency(Math.abs(k.net_variance))} (${k.variance_percentage?.toFixed(1)}%)</h4>
            </div>
            <div class="p-3 bg-amber-50/60 rounded-xl border border-amber-100">
              <p class="text-[10px] font-bold text-amber-700 uppercase">Over-Budget Units</p>
              <h4 class="text-base font-bold text-slate-900 mt-0.5">${k.over_budget_count} Units</h4>
            </div>
          `;
        } else if (type === 'anomaly') {
          kpiGrid.innerHTML = `
            <div class="p-3 bg-indigo-50/60 rounded-xl border border-indigo-100">
              <p class="text-[10px] font-bold text-indigo-700 uppercase">Total Anomalies</p>
              <h4 class="text-base font-bold text-slate-900 mt-0.5">${k.total_anomalies}</h4>
            </div>
            <div class="p-3 bg-rose-50/60 rounded-xl border border-rose-100">
              <p class="text-[10px] font-bold text-rose-700 uppercase">Critical Severity</p>
              <h4 class="text-base font-bold text-rose-600 mt-0.5">${k.critical_count}</h4>
            </div>
            <div class="p-3 bg-amber-50/60 rounded-xl border border-amber-100">
              <p class="text-[10px] font-bold text-amber-700 uppercase">High Severity</p>
              <h4 class="text-base font-bold text-amber-600 mt-0.5">${k.high_count}</h4>
            </div>
            <div class="p-3 bg-emerald-50/60 rounded-xl border border-emerald-100">
              <p class="text-[10px] font-bold text-emerald-700 uppercase">Medium / Low</p>
              <h4 class="text-base font-bold text-slate-900 mt-0.5">${(k.medium_count || 0) + (k.low_count || 0)}</h4>
            </div>
          `;
        } else {
          kpiGrid.innerHTML = `
            <div class="p-3 bg-indigo-50/60 rounded-xl border border-indigo-100">
              <p class="text-[10px] font-bold text-indigo-700 uppercase">Expected Profit</p>
              <h4 class="text-base font-bold text-indigo-600 mt-0.5">${formatCurrency(k.expected_profit)}</h4>
            </div>
            <div class="p-3 bg-emerald-50/60 rounded-xl border border-emerald-100">
              <p class="text-[10px] font-bold text-emerald-700 uppercase">Best Case (+15%)</p>
              <h4 class="text-base font-bold text-emerald-600 mt-0.5">${formatCurrency(k.best_case_profit)}</h4>
            </div>
            <div class="p-3 bg-rose-50/60 rounded-xl border border-rose-100">
              <p class="text-[10px] font-bold text-rose-700 uppercase">Worst Case (-15%)</p>
              <h4 class="text-base font-bold text-rose-600 mt-0.5">${formatCurrency(k.worst_case_profit)}</h4>
            </div>
            <div class="p-3 bg-blue-50/60 rounded-xl border border-blue-100">
              <p class="text-[10px] font-bold text-blue-700 uppercase">Confidence (R²)</p>
              <h4 class="text-base font-bold text-blue-600 mt-0.5">${k.confidence_score?.toFixed(1)}%</h4>
            </div>
          `;
        }
      }

      // Update Chart
      if (reportChart && res.trend) {
        const tr = res.trend;
        const periods = tr.periods || [];

        if (type === 'executive' || type === 'department') {
          safeSetOption(reportChart, {
            tooltip: { trigger: 'axis' },
            legend: { data: ['Revenue', 'Expenses', 'Net Profit'], top: 0 },
            grid: { left: '8%', right: '4%', top: '15%', bottom: '15%', containLabel: true },
            xAxis: { type: 'category', data: periods },
            yAxis: { type: 'value', axisLabel: { formatter: (v) => formatCurrency(v) } },
            series: [
              { name: 'Revenue', type: 'bar', data: tr.revenue || [], itemStyle: { color: '#3B82F6' } },
              { name: 'Expenses', type: 'bar', data: tr.expenses || [], itemStyle: { color: '#EF4444' } },
              { name: 'Net Profit', type: 'line', data: tr.profit || [], itemStyle: { color: '#10B981' }, lineStyle: { width: 3 } }
            ]
          });
        } else if (type === 'variance') {
          safeSetOption(reportChart, {
            tooltip: { trigger: 'axis' },
            legend: { data: ['Actual Spend'], top: 0 },
            grid: { left: '8%', right: '4%', top: '15%', bottom: '15%', containLabel: true },
            xAxis: { type: 'category', data: periods },
            yAxis: { type: 'value', axisLabel: { formatter: (v) => formatCurrency(v) } },
            series: [
              { name: 'Actual Spend', type: 'bar', data: tr.expenses || [], itemStyle: { color: '#2563EB' } }
            ]
          });
        } else if (type === 'anomaly') {
          const deptNames = (res.departments || []).map(d => d.department);
          const anomCounts = (res.departments || []).map(d => d.anomalies_count);
          safeSetOption(reportChart, {
            tooltip: { trigger: 'axis' },
            grid: { left: '8%', right: '4%', top: '15%', bottom: '25%', containLabel: true },
            xAxis: { type: 'category', data: deptNames, axisLabel: { rotate: 30, fontSize: 10 } },
            yAxis: { type: 'value', name: 'Anomalies' },
            series: [
              { name: 'Anomalies', type: 'bar', data: anomCounts, itemStyle: { color: '#EF4444' } }
            ]
          });
        } else {
          safeSetOption(reportChart, {
            tooltip: { trigger: 'axis' },
            legend: { data: ['Historical', 'Projected Horizon'], top: 0 },
            grid: { left: '8%', right: '4%', top: '15%', bottom: '15%', containLabel: true },
            xAxis: { type: 'category', data: periods },
            yAxis: { type: 'value', axisLabel: { formatter: (v) => formatCurrency(v) } },
            series: [
              { name: 'Historical', type: 'line', data: tr.actual || [], itemStyle: { color: '#3B82F6' }, lineStyle: { width: 2.5 } },
              { name: 'Projected Horizon', type: 'line', data: tr.forecast || [], itemStyle: { color: '#8B5CF6' }, lineStyle: { width: 2.5, type: 'dashed' } }
            ]
          });
        }
      }

      // Update Narrative & Drivers
      const narrativeEl = document.getElementById('report-narrative-text');
      if (narrativeEl) narrativeEl.textContent = res.narrative_summary;

      const driversList = document.getElementById('report-drivers-list');
      if (driversList && res.drivers) {
        driversList.innerHTML = '';
        res.drivers.forEach(d => {
          const li = document.createElement('li');
          li.className = 'flex items-start gap-1.5';
          li.innerHTML = `<span class="text-primary font-bold">•</span><span>${d}</span>`;
          driversList.appendChild(li);
        });
      }

      // Update Department Table
      const tableBody = document.getElementById('report-table-body');
      if (tableBody && res.departments) {
        tableBody.innerHTML = '';
        res.departments.forEach((d, idx) => {
          const tr = document.createElement('tr');
          tr.className = 'hover:bg-slate-50/80 transition-colors';
          const isOver = d.variance > 0;
          tr.innerHTML = `
            <td class="px-4 py-3 font-semibold text-slate-400">#${idx + 1}</td>
            <td class="px-4 py-3 font-bold text-slate-900">${d.department}</td>
            <td class="px-4 py-3 text-right font-medium text-slate-700">${formatCurrency(d.revenue)}</td>
            <td class="px-4 py-3 text-right font-medium text-slate-700">${formatCurrency(d.expense)}</td>
            <td class="px-4 py-3 text-right font-bold text-emerald-600">${formatCurrency(d.profit)}</td>
            <td class="px-4 py-3 text-right font-semibold text-indigo-600">${d.margin?.toFixed(1)}%</td>
            <td class="px-4 py-3 text-right font-medium ${isOver ? 'text-rose-600' : 'text-emerald-600'}">
              ${d.budget > 0 ? (isOver ? '+' : '') + formatCurrency(d.variance) : 'No Target'}
            </td>
            <td class="px-4 py-3 text-center">
              <span class="inline-block px-2 py-0.5 rounded-full text-[10px] font-bold ${d.anomalies_count > 0 ? 'bg-rose-50 text-rose-600 border border-rose-100' : 'bg-emerald-50 text-emerald-600 border border-emerald-100'}">
                ${d.anomalies_count}
              </span>
            </td>
          `;
          tableBody.appendChild(tr);
        });
      }
    } catch (e) {
      console.warn('Report load error:', e);
    }
  }

  // Card click handlers
  document.querySelectorAll('.report-card').forEach(card => {
    card.addEventListener('click', () => {
      const type = card.getAttribute('data-report-type');
      if (type) loadReport(type);
    });
  });

  // Filter change handlers
  document.getElementById('report-filter-dept')?.addEventListener('change', () => loadReport());
  document.getElementById('report-filter-period')?.addEventListener('change', () => loadReport());
  document.getElementById('btn-generate-report')?.addEventListener('click', () => loadReport());

  // Export CSV
  document.getElementById('btn-export-csv')?.addEventListener('click', () => {
    const scope = document.getElementById('report-filter-dept')?.value || 'All Departments';
    window.location.href = `/api/v1/reports/csv?scope=${encodeURIComponent(scope)}`;
  });

  // Export PDF
  document.getElementById('btn-export-pdf')?.addEventListener('click', () => {
    window.open('/api/v1/reports/pdf', '_blank');
  });

  window.addEventListener('resize', () => {
    reportChart?.resize();
  });

  await initFilters();
  await loadReport('executive');
});
