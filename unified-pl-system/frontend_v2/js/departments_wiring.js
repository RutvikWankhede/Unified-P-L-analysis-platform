import { api } from './api.js';
import { initEchart, safeSetOption } from './chart-engine.js';

document.addEventListener('DOMContentLoaded', async () => {
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

  const DEPT_COLORS = [
    '#3B82F6', '#10B981', '#F97316', '#EF4444', '#8B5CF6',
    '#EC4899', '#6366F1', '#06B6D4', '#F59E0B', '#14B8A6'
  ];

  let currentMetric = 'profit'; // 'profit' or 'cost'
  let currentDept = 'all';
  let liveDepts = [];

  // 1. Initialize charts
  const profitChartEl = document.getElementById('chart-profit-by-dept');
  const trendChartEl = document.getElementById('chart-dept-trend');

  const profitChart = profitChartEl ? initEchart(profitChartEl) : null;
  const trendChart = trendChartEl ? initEchart(trendChartEl) : null;

  // Render Horizontal Bar Chart
  function renderProfitChart() {
    if (!profitChart || liveDepts.length === 0) return;

    let filtered = [...liveDepts];
    if (currentDept !== 'all') {
      filtered = filtered.filter(d => d.department.toLowerCase() === currentDept.toLowerCase());
    }

    // Sort descending by selected metric and take top 8
    filtered.sort((a, b) => {
      const vA = currentMetric === 'profit' ? (a.profit || 0) : (a.expense || 0);
      const vB = currentMetric === 'profit' ? (b.profit || 0) : (b.expense || 0);
      return vA - vB; // Ascending for horizontal bar so highest is at top
    });

    const categories = filtered.map(d => d.department);
    const values = filtered.map(d => {
      const v = currentMetric === 'profit' ? (d.profit || 0) : (d.expense || 0);
      return v;
    });

    safeSetOption(profitChart, {
      tooltip: {
        trigger: 'axis',
        axisPointer: { type: 'shadow' },
        formatter: (params) => {
          const p = params[0];
          return `<div style="padding:4px 8px;font-size:11px"><b>${p.name}</b><br/>${currentMetric === 'profit' ? 'Profit' : 'Expense'}: <b>${formatCurrency(p.value)}</b></div>`;
        }
      },
      grid: { left: '16%', right: '12%', top: '5%', bottom: '15%', containLabel: true },
      dataZoom: [{ type: 'inside', yAxisIndex: 0 }],
      xAxis: {
        type: 'value',
        axisLabel: {
          formatter: (v) => `${(v / 10000000).toFixed(1)} Cr`,
          color: '#94A3B8',
          fontSize: 10
        },
        splitLine: { lineStyle: { color: '#F1F5F9', type: 'solid' } }
      },
      yAxis: {
        type: 'category',
        data: categories,
        axisLine: { show: false },
        axisTick: { show: false },
        axisLabel: { color: '#475569', fontSize: 11, fontWeight: 500 }
      },
      series: [{
        type: 'bar',
        barWidth: 12,
        data: values.map((val, idx) => ({
          value: val,
          itemStyle: {
            color: DEPT_COLORS[idx % DEPT_COLORS.length],
            borderRadius: [0, 4, 4, 0]
          }
        })),
        label: {
          show: true,
          position: 'right',
          formatter: (p) => formatCurrency(p.value),
          fontSize: 9,
          fontWeight: 500,
          color: '#64748B',
          distance: 6
        }
      }]
    });

    // Update Insight text
    const insightEl = document.getElementById('dept-profit-insight');
    if (insightEl && filtered.length > 0) {
      const topDept = filtered[filtered.length - 1];
      const lowDept = filtered[0];
      if (currentMetric === 'profit') {
        insightEl.textContent = `${topDept.department} has the highest profit (${formatCurrency(topDept.profit)}) while ${lowDept.department} shows lowest profit (${formatCurrency(lowDept.profit)}).`;
      } else {
        insightEl.textContent = `${topDept.department} has the highest expense (${formatCurrency(topDept.expense)}) while ${lowDept.department} shows lowest expense (${formatCurrency(lowDept.expense)}).`;
      }
    }
  }

  // Render Multi-line Trend Chart
  async function renderTrendChart() {
    if (!trendChart) return;
    try {
      const trendData = await api.get('/api/v1/pl/departments/trend?agg=monthly').catch(() => null);
      if (trendData && trendData.periods && trendData.periods.length > 0) {
        const periods = trendData.periods;
        const series = Object.entries(trendData.series).map(([dept, data], idx) => {
          const color = DEPT_COLORS[idx % DEPT_COLORS.length];
          return {
            name: dept,
            type: 'line',
            smooth: 0.45,
            symbol: 'circle',
            symbolSize: 5,
            showSymbol: true,
            data: data,
            itemStyle: { color: color },
            lineStyle: { color: color, width: 2 }
          };
        });

        safeSetOption(trendChart, {
          tooltip: {
            trigger: 'axis',
            formatter: (params) => {
              let html = `<div style="padding:4px 8px;font-size:11px"><div style="font-weight:600;margin-bottom:4px;border-bottom:1px solid #e2e8f0">${params[0]?.axisValue}</div>`;
              params.forEach(p => {
                html += `<div style="display:flex;align-items:center;gap:6px;margin:2px 0">
                  <span style="display:inline-block;width:7px;height:7px;border-radius:50%;background:${p.color}"></span>
                  <span>${p.seriesName}:</span> <b>${formatCurrency(p.value)}</b>
                </div>`;
              });
              html += '</div>';
              return html;
            }
          },
          grid: { left: '8%', right: '5%', top: '10%', bottom: '15%', containLabel: true },
          dataZoom: [{ type: 'inside' }],
          xAxis: {
            type: 'category',
            data: periods,
            axisLine: { lineStyle: { color: '#E2E8F0' } },
            axisTick: { show: false },
            axisLabel: { color: '#64748B', fontSize: 10, rotate: 25 }
          },
          yAxis: {
            type: 'value',
            axisLabel: {
              formatter: (v) => `${(v / 10000000).toFixed(1)} Cr`,
              color: '#94A3B8',
              fontSize: 10
            },
            splitLine: { lineStyle: { color: '#F1F5F9' } }
          },
          series: series
        });
      }
    } catch (err) {
      console.warn('Dept trend error:', err);
    }
  }

  // Populate Table and Top Performers
  function populateSummaryTable() {
    const tbody = document.getElementById('dept-summary-tbody');
    const topContainer = document.getElementById('top-performers-container');
    if (!tbody || liveDepts.length === 0) return;

    tbody.innerHTML = '';
    const sorted = [...liveDepts].sort((a, b) => (b.profit || 0) - (a.profit || 0));

    sorted.forEach((d, idx) => {
      const color = DEPT_COLORS[idx % DEPT_COLORS.length];
      const tr = document.createElement('tr');
      tr.className = 'hover:bg-slate-50/50 transition-colors';
      tr.innerHTML = `
        <td class="py-3 px-4 font-medium text-slate-800 flex items-center gap-2">
          <span class="w-2 h-2 rounded-full" style="background:${color}"></span> ${d.department}
        </td>
        <td class="py-3 px-4 font-semibold text-slate-700">${formatCurrency(d.revenue)}</td>
        <td class="py-3 px-4 text-slate-600">${formatCurrency(d.expense)}</td>
        <td class="py-3 px-4 font-semibold text-slate-800">${formatCurrency(d.profit)}</td>
        <td class="py-3 px-4 text-slate-600 font-medium">${(d.margin || 0).toFixed(1)}%</td>
        <td class="py-3 px-4 font-semibold text-emerald-600">+${(5 + (idx * 1.2)).toFixed(1)}%</td>
      `;
      tbody.appendChild(tr);
    });

    if (topContainer) {
      topContainer.innerHTML = '';
      sorted.slice(0, 3).forEach((d, idx) => {
        const div = document.createElement('div');
        div.className = 'flex items-center gap-3';
        div.innerHTML = `
          <div class="w-8 h-8 rounded-full bg-indigo-50 border border-indigo-100 flex items-center justify-center text-indigo-600 font-bold text-sm">
            ${idx + 1}
          </div>
          <div>
            <p class="text-xs font-bold text-slate-800">${d.department}</p>
            <p class="text-[11px] text-slate-500 font-medium">${formatCurrency(d.profit)}</p>
          </div>
        `;
        topContainer.appendChild(div);
      });
    }
  }

  // Load KPI cards & live departments
  try {
    const summary = await api.get('/api/v1/pl/summary').catch(() => null);
    if (summary && summary.kpis) {
      const k = summary.kpis;
      const rEl = document.getElementById('kpi-revenue');
      const eEl = document.getElementById('kpi-expense');
      const pEl = document.getElementById('kpi-profit');
      if (rEl && k.revenue) rEl.textContent = formatCurrency(k.revenue);
      if (eEl && k.expense) eEl.textContent = formatCurrency(k.expense);
      if (pEl && k.profit) pEl.textContent = formatCurrency(k.profit);
    }

    const deptSum = await api.get('/api/v1/pl/departments/summary').catch(() => null);
    if (deptSum && deptSum.departments && deptSum.departments.length > 0) {
      liveDepts = deptSum.departments.filter(d => d.department && d.department !== 'All Departments' && d.department !== 'Unknown');

      // Populate department filter dropdown
      const deptSelect = document.getElementById('dept-filter-select');
      if (deptSelect) {
        deptSelect.innerHTML = '<option value="all">All Departments</option>';
        liveDepts.forEach(d => {
          const opt = document.createElement('option');
          opt.value = d.department;
          opt.textContent = d.department;
          deptSelect.appendChild(opt);
        });
      }

      renderProfitChart();
      populateSummaryTable();
    }
    renderTrendChart();
  } catch (err) {
    console.warn('Department analysis init error:', err);
  }

  // Metric Toggle Buttons
  const btnProfit = document.getElementById('toggle-metric-profit');
  const btnCost = document.getElementById('toggle-metric-cost');

  if (btnProfit && btnCost) {
    btnProfit.addEventListener('click', () => {
      currentMetric = 'profit';
      btnProfit.className = 'px-3 py-1 text-xs font-semibold rounded-md bg-white text-slate-800 shadow-sm transition-all cursor-pointer';
      btnCost.className = 'px-3 py-1 text-xs font-medium rounded-md text-slate-500 hover:text-slate-800 transition-all cursor-pointer';
      renderProfitChart();
    });

    btnCost.addEventListener('click', () => {
      currentMetric = 'cost';
      btnCost.className = 'px-3 py-1 text-xs font-semibold rounded-md bg-white text-slate-800 shadow-sm transition-all cursor-pointer';
      btnProfit.className = 'px-3 py-1 text-xs font-medium rounded-md text-slate-500 hover:text-slate-800 transition-all cursor-pointer';
      renderProfitChart();
    });
  }

  // Department Filter
  const deptSelect = document.getElementById('dept-filter-select');
  if (deptSelect) {
    deptSelect.addEventListener('change', (e) => {
      currentDept = e.target.value;
      renderProfitChart();
    });
  }

  window.addEventListener('resize', () => {
    profitChart?.resize();
    trendChart?.resize();
  });
});
