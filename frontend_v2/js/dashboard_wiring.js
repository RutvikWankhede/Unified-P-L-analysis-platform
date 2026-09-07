import { api } from './api.js';
import { initEchart, safeSetOption } from './chart-engine.js';

document.addEventListener('DOMContentLoaded', async () => {
  // Global Currency & Number Formatter
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

  const formatShort = (val) => {
    if (val === null || val === undefined || isNaN(val)) return '0';
    const abs = Math.abs(val);
    const sign = val < 0 ? '-' : '';
    if (abs >= 10000000) return `${sign}${(abs / 10000000).toFixed(1)} Cr`;
    if (abs >= 100000) return `${sign}${(abs / 100000).toFixed(1)} L`;
    if (abs >= 1000) return `${sign}${(abs / 1000).toFixed(0)} K`;
    return `${sign}${abs}`;
  };

  // Department color map for distinct, consistent coloring across the platform (Matches Visual Reference)
  const DEPARTMENT_COLORS = {
    'R&D': '#2563EB',                     // Vibrant Blue (Reference)
    'Research & Development': '#2563EB',
    'Logistics': '#0D9488',               // Teal (Reference)
    'Supply Chain': '#0D9488',
    'Marketing': '#8B5CF6',               // Purple (Reference)
    'IT': '#F97316',                      // Orange (Reference)
    'Engineering': '#F97316',
    'Technology': '#F97316',
    'Information Technology': '#F97316',
    'Procurement': '#EF4444',             // Coral Red (Reference)
    'Administration': '#06B6D4',          // Sky Blue (Reference)
    'Customer Support': '#EAB308',        // Amber / Yellow (Reference)
    'Support': '#EAB308',
    'Finance': '#6366F1',                 // Indigo / Slate (Reference)
    'Sales': '#3B82F6',                   // Cobalt Blue
    'Commercial': '#0284C7',
    'Operations': '#10B981',              // Emerald
    'Human Resources': '#EC4899',         // Pink
    'HR': '#EC4899',
    'Legal': '#84CC16',                   // Lime
    'Executive': '#4F46E5',
  };

  const FALLBACK_PALETTE = [
    '#2563EB', '#0D9488', '#8B5CF6', '#F97316', '#EF4444',
    '#06B6D4', '#EAB308', '#6366F1', '#3B82F6', '#10B981',
    '#EC4899', '#84CC16', '#0284C7', '#14B8A6', '#64748B'
  ];

  function getDepartmentColor(deptName) {
    if (!deptName) return '#2563EB';
    if (DEPARTMENT_COLORS[deptName]) return DEPARTMENT_COLORS[deptName];
    const match = Object.keys(DEPARTMENT_COLORS).find(k => k.toLowerCase() === deptName.toLowerCase());
    if (match) return DEPARTMENT_COLORS[match];
    let hash = 0;
    for (let i = 0; i < deptName.length; i++) {
      hash = deptName.charCodeAt(i) + ((hash << 5) - hash);
    }
    const idx = Math.abs(hash) % FALLBACK_PALETTE.length;
    return FALLBACK_PALETTE[idx];
  }

  // Setup generic inside-chart zoom in/out/reset helper for any ECharts instance
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

  // Sparkline helper
  function initSparkline(id, color, data) {
    const el = document.getElementById(id);
    if (!el) return null;
    const chart = initEchart(el);
    const minVal = Math.min(...data);
    safeSetOption(chart, {
      grid: { left: 0, right: 0, top: 2, bottom: 0 },
      xAxis: { type: 'category', show: false, boundaryGap: false },
      yAxis: { type: 'value', show: false, min: minVal * 0.8 },
      series: [{
        type: 'line',
        data: data,
        smooth: 0.4,
        showSymbol: false,
        lineStyle: { color: color, width: 1.5 },
        areaStyle: {
          color: {
            type: 'linear', x: 0, y: 0, x2: 0, y2: 1,
            colorStops: [
              { offset: 0, color: color + '55' },
              { offset: 1, color: color + '00' }
            ]
          }
        }
      }]
    });
    return chart;
  }

  // Default Sparklines
  initSparkline('sparkline-revenue', '#3B82F6', [18, 20, 22, 21, 24, 26, 27.8]);
  initSparkline('sparkline-expenses', '#EF4444', [14, 15, 16, 15.5, 17, 17.5, 18.2]);
  initSparkline('sparkline-profit', '#10B981', [4, 5, 6, 5.5, 7, 7.2, 7.98]);
  initSparkline('sparkline-margin', '#8B5CF6', [24, 25, 26, 25.5, 27, 28, 28.8]);
  initSparkline('sparkline-cashflow', '#F59E0B', [3.8, 4.2, 4.5, 4.3, 4.8, 5.1, 5.42]);
  initSparkline('sparkline-forecast', '#0284C7', [22, 24, 26, 28, 29.5, 30.5, 31.25]);
  initSparkline('sparkline-health', '#F43F5E', [74, 76, 78, 80, 82, 83, 85]);

  // Track global departments list
  let allDepartments = [];

  // =========================================================================
  // 1. POPULATE ACTIVE DATASET & SUMMARY KPIS
  // =========================================================================
  try {
    const active = await api.get('/api/v1/datasets/active').catch(() => null);
    if (active && active.filename) {
      const pill = document.getElementById('active-dataset-name');
      if (pill) pill.textContent = active.filename.replace('.csv', '').replace('.xlsx', '');
    }

    const summary = await api.get('/api/v1/pl/summary').catch(() => null);
    if (summary && summary.kpis) {
      const k = summary.kpis;
      const rEl = document.getElementById('kpi-total-revenue');
      const eEl = document.getElementById('kpi-total-expenses');
      const pEl = document.getElementById('kpi-net-profit');
      const mEl = document.getElementById('kpi-operating-margin');
      const cEl = document.getElementById('kpi-cash-flow');
      const hEl = document.getElementById('kpi-health');

      if (rEl && k.revenue !== undefined) rEl.textContent = formatCurrency(k.revenue);
      if (eEl && k.expense !== undefined) eEl.textContent = formatCurrency(k.expense);
      if (pEl && k.profit !== undefined) pEl.textContent = formatCurrency(k.profit);
      if (mEl && k.profit_margin !== undefined) mEl.textContent = `${k.profit_margin.toFixed(1)}%`;
      if (cEl && k.cash_flow !== undefined) cEl.textContent = formatCurrency(k.cash_flow);
      if (hEl && k.health_score !== undefined) hEl.textContent = `${Math.round(k.health_score)}/100`;

      // Trends
      const rGr = document.getElementById('kpi-growth-revenue');
      const eGr = document.getElementById('kpi-growth-expenses');
      const pGr = document.getElementById('kpi-growth-profit');
      const mGr = document.getElementById('kpi-growth-margin');

      if (rGr && k.revenue_growth !== undefined) {
        const sign = k.revenue_growth >= 0 ? '↑ +' : '↓ ';
        rGr.innerHTML = `<span class="${k.revenue_growth >= 0 ? 'text-emerald-600' : 'text-rose-500'} font-semibold">${sign}${k.revenue_growth.toFixed(1)}%</span> <span class="text-[9px] text-slate-400 font-normal">vs last period</span>`;
      }
      if (eGr && k.expense_growth !== undefined) {
        const sign = k.expense_growth >= 0 ? '↑ +' : '↓ ';
        eGr.innerHTML = `<span class="${k.expense_growth <= 5 ? 'text-emerald-600' : 'text-rose-500'} font-semibold">${sign}${k.expense_growth.toFixed(1)}%</span> <span class="text-[9px] text-slate-400 font-normal">vs last period</span>`;
      }
      if (pGr && k.profit_growth !== undefined) {
        const sign = k.profit_growth >= 0 ? '↑ +' : '↓ ';
        pGr.innerHTML = `<span class="${k.profit_growth >= 0 ? 'text-emerald-600' : 'text-rose-500'} font-semibold">${sign}${k.profit_growth.toFixed(1)}%</span> <span class="text-[9px] text-slate-400 font-normal">vs last period</span>`;
      }
      if (mGr && k.margin_growth !== undefined) {
        const sign = k.margin_growth >= 0 ? '↑ +' : '↓ ';
        mGr.innerHTML = `<span class="${k.margin_growth >= 0 ? 'text-emerald-600' : 'text-rose-500'} font-semibold">${sign}${k.margin_growth.toFixed(1)}%</span> <span class="text-[9px] text-slate-400 font-normal">vs last period</span>`;
      }
    }

    // Populate department dropdowns
    const deptsRes = await api.get('/api/v1/pl/departments').catch(() => null);
    if (deptsRes && deptsRes.departments && deptsRes.departments.length > 0) {
      allDepartments = deptsRes.departments.filter(d => d && d !== 'All Departments' && d !== 'Unknown');
      const populateDropdown = (selectId) => {
        const sel = document.getElementById(selectId);
        if (!sel) return;
        const currentVal = sel.value;
        sel.innerHTML = '<option value="all">All Departments</option>';
        allDepartments.forEach(dept => {
          const opt = document.createElement('option');
          opt.value = dept;
          opt.textContent = dept;
          sel.appendChild(opt);
        });
        if (currentVal && allDepartments.includes(currentVal)) {
          sel.value = currentVal;
        }
      };

      populateDropdown('ctrl-rev-dept');
      populateDropdown('ctrl-anom-dept');
      populateDropdown('ctrl-exp-dist-dept');
      populateDropdown('ctrl-fcst-dept');
      populateDropdown('ctrl-cf-dept');
      populateDropdown('ctrl-budget-dept');
    }
  } catch (err) {
    console.warn('Dashboard KPI fetch error:', err);
  }

  // =========================================================================
  // 2. ROW 1 LEFT: REVENUE VS EXPENSES VS NET PROFIT (WITH AGG + DEPT + ZOOM)
  // =========================================================================
  const revExpChartEl = document.getElementById('chart-rev-exp-profit');
  const revExpChart = revExpChartEl ? initEchart(revExpChartEl) : null;
  setupZoomControls(revExpChart, 'zoom-in-rev', 'zoom-out-rev', 'zoom-reset-rev');

  async function loadRevExpChart(dept = 'all', agg = 'monthly') {
    if (!revExpChart) return;
    try {
      const data = await api.get(`/api/v1/pl/charts?dept=${encodeURIComponent(dept)}&agg=${encodeURIComponent(agg)}`);
      if (!data || !data.periods || data.periods.length === 0) {
        revExpChart.clear();
        return;
      }
      const periods = data.periods;
      const revVals = (data.revenue_trend || []).map(r => r.value);
      const expVals = (data.expense_trend || []).map(r => r.value);
      const profVals = (data.profit_trend || []).map(r => r.value);

        safeSetOption(revExpChart, {
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
                html += `<div style="display:flex;align-items:center;justify-content:space-between;gap:8px;margin:2px 0">
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
          grid: { left: '8%', right: '3%', top: '10%', bottom: '15%', containLabel: true },
          dataZoom: [{ type: 'inside' }],
          xAxis: {
            type: 'category',
            data: periods,
            boundaryGap: false,
            axisLine: { lineStyle: { color: '#E2E8F0' } },
            axisTick: { show: false },
            axisLabel: { color: '#64748B', fontSize: 10 }
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
              symbolSize: 5,
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
              name: 'Expenses',
              type: 'line',
              smooth: 0.35,
              symbol: 'circle',
              symbolSize: 5,
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
              symbolSize: 5,
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
    } catch (err) {
      console.warn('RevExp chart error:', err);
    }
  }

  const ctrlRevDept = document.getElementById('ctrl-rev-dept');
  const ctrlRevAgg = document.getElementById('ctrl-rev-agg');
  const btnRefreshRev = document.getElementById('btn-refresh-rev-chart');

  const triggerRevExp = () => {
    loadRevExpChart(
      ctrlRevDept ? ctrlRevDept.value : 'all',
      ctrlRevAgg ? ctrlRevAgg.value : 'monthly'
    );
  };

  if (ctrlRevDept) ctrlRevDept.addEventListener('change', triggerRevExp);
  if (ctrlRevAgg) ctrlRevAgg.addEventListener('change', triggerRevExp);
  if (btnRefreshRev) btnRefreshRev.addEventListener('click', triggerRevExp);

  loadRevExpChart('all', 'monthly');

  // =========================================================================
  // 3. ROW 1 RIGHT: ANOMALY OVERVIEW (PIE/DONUT MATCHING REFERENCE DESIGN)
  // =========================================================================
  const anomOverviewEl = document.getElementById('chart-anomaly-overview');
  const anomOverviewChart = anomOverviewEl ? initEchart(anomOverviewEl) : null;

  async function loadAnomalyOverview(period = 'overall', dept = 'all') {
    const wrapper = document.getElementById('anom-content-wrapper');
    const emptyState = document.getElementById('anom-empty-state');

    try {
      const res = await api.get(`/api/v1/pl/anomaly-overview?period=${period}&dept=${dept}`).catch(() => null);
      if (!res) return;

      const critEl = document.getElementById('anom-crit-count');
      const highEl = document.getElementById('anom-high-count');
      const medEl = document.getElementById('anom-med-count');
      const lowEl = document.getElementById('anom-low-count');

      if (critEl) critEl.textContent = res.critical_count ?? 0;
      if (highEl) highEl.textContent = res.high_count ?? 0;
      if (medEl) medEl.textContent = res.medium_count ?? 0;
      if (lowEl) lowEl.textContent = res.low_count ?? 0;

      if (res.total_anomalies === 0) {
        if (wrapper) wrapper.classList.add('hidden');
        if (emptyState) emptyState.classList.remove('hidden');
        return;
      } else {
        if (wrapper) wrapper.classList.remove('hidden');
        if (emptyState) emptyState.classList.add('hidden');
      }

      if (anomOverviewChart) {
        const data = (res.severities || []).map(s => ({
          value: s.count,
          name: s.name,
          itemStyle: { color: s.color }
        })).filter(d => d.value > 0);

        safeSetOption(anomOverviewChart, {
          title: {
            text: `{val|${res.total_anomalies}}\n{label|Total}`,
            left: 'center',
            top: '32%',
            textStyle: {
              rich: {
                val: {
                  fontSize: 22,
                  fontWeight: 'bold',
                  color: '#0F172A',
                  lineHeight: 26,
                  align: 'center'
                },
                label: {
                  fontSize: 11,
                  color: '#64748B',
                  fontWeight: '500',
                  lineHeight: 14,
                  align: 'center'
                }
              }
            }
          },
          tooltip: {
            trigger: 'item',
            backgroundColor: '#ffffff',
            borderColor: '#e2e8f0',
            borderWidth: 1,
            extraCssText: 'box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.1), 0 2px 4px -2px rgba(0, 0, 0, 0.06); border-radius: 8px;',
            textStyle: { color: '#0f172a', fontSize: 11, fontFamily: 'Inter, sans-serif' },
            formatter: (params) => {
              return `<div style="padding:4px 6px;font-size:11px;color:#0f172a"><span style="display:inline-block;width:8px;height:8px;border-radius:50%;background:${params.color};margin-right:4px"></span><b>${params.name}</b>: <b>${params.value}</b> (${params.percent}%)</div>`;
            }
          },
          series: [{
            type: 'pie',
            radius: ['64%', '84%'],
            center: ['50%', '50%'],
            avoidLabelOverlap: false,
            label: { show: false },
            itemStyle: {
              borderColor: '#ffffff',
              borderWidth: 2
            },
            data: data
          }]
        });
      }
    } catch (err) {
      console.warn('Anomaly overview error:', err);
    }
  }

  const ctrlAnomPeriod = document.getElementById('ctrl-anom-period');
  const ctrlAnomDept = document.getElementById('ctrl-anom-dept');

  const triggerAnom = () => {
    loadAnomalyOverview(
      ctrlAnomPeriod ? ctrlAnomPeriod.value : 'overall',
      ctrlAnomDept ? ctrlAnomDept.value : 'all'
    );
  };

  if (ctrlAnomPeriod) ctrlAnomPeriod.addEventListener('change', triggerAnom);
  if (ctrlAnomDept) ctrlAnomDept.addEventListener('change', triggerAnom);

  loadAnomalyOverview('overall', 'all');

  // =========================================================================
  // 4. ROW 2 LEFT: DEPARTMENT PERFORMANCE (METRIC + RANGE + ZOOM)
  // =========================================================================
  const deptPerfEl = document.getElementById('chart-dept-performance');
  const deptPerfChart = deptPerfEl ? initEchart(deptPerfEl) : null;
  setupZoomControls(deptPerfChart, 'zoom-in-dept', 'zoom-out-dept', 'zoom-reset-dept');

  async function loadDeptPerformance(metric = 'profit', limit = 'top5') {
    if (!deptPerfChart) return;
    try {
      const res = await api.get(`/api/v1/pl/department-performance?metric=${metric}&limit=${limit}`);
      if (res && res.departments && res.departments.length > 0) {
        // Reverse for horizontal bar chart (top ranked at top)
        const depts = [...res.departments].reverse();
        const vals = [...res.values].reverse();
        const isPct = metric === 'margin_pct';

        safeSetOption(deptPerfChart, {
          tooltip: {
            trigger: 'axis',
            axisPointer: { type: 'shadow' },
            backgroundColor: '#ffffff',
            borderColor: '#e2e8f0',
            borderWidth: 1,
            extraCssText: 'box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.1), 0 2px 4px -2px rgba(0, 0, 0, 0.06); border-radius: 8px; z-index: 99;',
            textStyle: { color: '#0f172a', fontSize: 11, fontFamily: 'Inter, sans-serif' },
            formatter: (params) => {
              const deptName = params[0]?.name;
              const item = res.items ? res.items.find(it => it.department === deptName) : null;
              const valFormatted = isPct ? `${params[0]?.value}%` : formatCurrency(params[0]?.value);
              const deptColor = getDepartmentColor(deptName);
              let html = `<div style="padding:4px 8px;font-size:11px;color:#0f172a">
                <div style="display:flex;align-items:center;gap:6px;margin-bottom:4px;border-bottom:1px solid #e2e8f0;padding-bottom:2px">
                  <span style="display:inline-block;width:8px;height:8px;border-radius:50%;background:${deptColor}"></span>
                  <b style="color:#0f172a;font-size:11px">${deptName}</b>
                </div>`;
              html += `<div style="margin:2px 0">${metric.toUpperCase().replace('_', ' ')}: <b>${valFormatted}</b></div>`;
              if (item) {
                html += `<div style="color:#64748B;font-size:10px;margin-top:2px">Rev: ${formatCurrency(item.revenue)} | Exp: ${formatCurrency(item.expense)}</div>`;
                html += `<div style="color:#64748B;font-size:10px">Net Margin: <b>${item.margin_pct}%</b></div>`;
              }
              html += '</div>';
              return html;
            }
          },
          grid: { left: 4, right: 52, top: 10, bottom: 8, containLabel: true },
          dataZoom: [{ type: 'inside', yAxisIndex: 0 }],
          xAxis: {
            type: 'value',
            axisLabel: {
              formatter: (v) => isPct ? `${v}%` : formatShort(v),
              color: '#94A3B8',
              fontSize: 10,
              fontFamily: 'Inter, sans-serif'
            },
            splitLine: { lineStyle: { color: '#F1F5F9' } }
          },
          yAxis: {
            type: 'category',
            data: depts,
            axisLine: { show: false },
            axisTick: { show: false },
            axisLabel: {
              color: '#1e293b',
              fontSize: 11,
              fontWeight: 600,
              fontFamily: 'Inter, sans-serif',
              width: 95,
              overflow: 'truncate',
              ellipsis: '...'
            }
          },
          series: [{
            type: 'bar',
            barWidth: depts.length > 8 ? 9 : (depts.length > 5 ? 13 : 16),
            label: {
              show: true,
              position: 'right',
              distance: 8,
              formatter: (params) => isPct ? `${params.value}%` : formatShort(params.value),
              fontSize: 10,
              color: '#475569',
              fontWeight: 600,
              fontFamily: 'Inter, sans-serif'
            },
            data: depts.map((dName, idx) => {
              const c = getDepartmentColor(dName);
              return {
                value: vals[idx],
                itemStyle: {
                  color: c,
                  borderRadius: [0, 4, 4, 0]
                }
              };
            })
          }]
        });
      }
    } catch (err) {
      console.warn('Dept perf error:', err);
    }
  }

  const ctrlDeptMetric = document.getElementById('ctrl-dept-metric');
  const ctrlDeptRange = document.getElementById('ctrl-dept-range');

  const triggerDeptPerf = () => {
    loadDeptPerformance(
      ctrlDeptMetric ? ctrlDeptMetric.value : 'profit',
      ctrlDeptRange ? ctrlDeptRange.value : 'top5'
    );
  };

  if (ctrlDeptMetric) ctrlDeptMetric.addEventListener('change', triggerDeptPerf);
  if (ctrlDeptRange) ctrlDeptRange.addEventListener('change', triggerDeptPerf);

  loadDeptPerformance('profit', 'top5');

  // =========================================================================
  // 5. ROW 2 CENTER: FINANCIAL DISTRIBUTION (METRIC + DEPT DYNAMIC)
  // =========================================================================
  const expDistEl = document.getElementById('chart-expense-dist');
  const expDistChart = expDistEl ? initEchart(expDistEl) : null;

  async function loadExpenseDistribution(metric = 'expense', dept = 'all') {
    if (!expDistChart) return;
    const bodyEl = document.getElementById('expense-dist-body');
    const emptyEl = document.getElementById('expense-empty-state');
    const legendEl = document.getElementById('expense-dist-legend');
    const titleEl = document.getElementById('title-dist-card');

    const metricTitleMap = {
      'expense': 'Expense Distribution',
      'revenue': 'Revenue Distribution',
      'profit': 'Profit Distribution',
      'margin_pct': 'Net Margin % Distribution'
    };
    if (titleEl) {
      titleEl.textContent = metricTitleMap[metric] || 'Expense Distribution';
    }

    try {
      const res = await api.get(`/api/v1/pl/expense-distribution?metric=${metric}&dept=${dept}`);
      if (res && res.has_data && res.categories && res.categories.length > 0) {
        if (bodyEl) bodyEl.classList.remove('hidden');
        if (emptyEl) emptyEl.classList.add('hidden');

        const isMargin = res.is_percentage || metric === 'margin_pct';
        const chartData = res.categories.map(c => {
          const catColor = getDepartmentColor(c.name) || c.color;
          return {
            name: c.name,
            value: c.amount,
            percentage: c.percentage,
            itemStyle: { color: catColor }
          };
        });

        safeSetOption(expDistChart, {
          tooltip: {
            trigger: 'item',
            backgroundColor: '#ffffff',
            borderColor: '#e2e8f0',
            borderWidth: 1,
            extraCssText: 'box-shadow: 0 4px 12px -2px rgba(0, 0, 0, 0.1), 0 2px 4px -2px rgba(0, 0, 0, 0.06); border-radius: 8px; z-index: 9999;',
            textStyle: { color: '#0f172a', fontSize: 11, fontFamily: 'Inter, sans-serif' },
            formatter: (params) => {
              const d = params.data;
              const valDisplay = isMargin ? `${d.value}%` : formatCurrency(d.value);
              const labelDesc = isMargin ? 'Margin Share' : `of total ${metric}`;
              return `<div style="padding:4px 6px;font-size:11px;color:#0f172a">
                <div style="font-weight:700;margin-bottom:2px">${params.name}</div>
                <div style="font-size:12px;font-weight:600;color:#2563EB">${valDisplay}</div>
                <div style="font-size:10px;color:#64748B;margin-top:2px"><b>${d.percentage || params.percent}%</b> ${labelDesc}</div>
              </div>`;
            }
          },
          series: [{
            type: 'pie',
            radius: ['52%', '80%'],
            center: ['50%', '50%'],
            avoidLabelOverlap: false,
            label: { show: false },
            itemStyle: {
              borderColor: '#ffffff',
              borderWidth: 2
            },
            data: chartData
          }]
        });

        if (legendEl) {
          legendEl.innerHTML = '';
          res.categories.forEach(c => {
            const row = document.createElement('div');
            row.className = 'flex items-center justify-between py-1 border-b border-slate-50 last:border-0';
            const valDisplay = isMargin ? `${c.amount}%` : formatCurrency(c.amount);
            const catColor = getDepartmentColor(c.name) || c.color;
            row.innerHTML = `
              <span class="flex items-center gap-1.5 truncate max-w-[100px]" title="${c.name}">
                <span class="w-2 h-2 rounded-full flex-shrink-0" style="background:${catColor}"></span>
                <span class="truncate text-slate-700 font-medium">${c.name}</span>
              </span>
              <div class="flex items-center gap-1.5 flex-shrink-0">
                <span class="font-semibold text-slate-900">${valDisplay}</span>
                <span class="text-slate-400 text-[9px] w-8 text-right">${c.percentage}%</span>
              </div>
            `;
            legendEl.appendChild(row);
          });
        }
      } else {
        if (bodyEl) bodyEl.classList.add('hidden');
        if (emptyEl) emptyEl.classList.remove('hidden');
      }
    } catch (err) {
      console.warn('Expense distribution error:', err);
      if (bodyEl) bodyEl.classList.add('hidden');
      if (emptyEl) emptyEl.classList.remove('hidden');
    }
  }

  const ctrlExpDistMetric = document.getElementById('ctrl-exp-dist-metric');
  const ctrlExpDistDept = document.getElementById('ctrl-exp-dist-dept');

  const triggerExpDist = () => {
    loadExpenseDistribution(
      ctrlExpDistMetric ? ctrlExpDistMetric.value : 'expense',
      ctrlExpDistDept ? ctrlExpDistDept.value : 'all'
    );
  };

  if (ctrlExpDistMetric) ctrlExpDistMetric.addEventListener('change', triggerExpDist);
  if (ctrlExpDistDept) ctrlExpDistDept.addEventListener('change', triggerExpDist);

  loadExpenseDistribution('expense', 'all');

  // =========================================================================
  // 6. ROW 2 RIGHT: DATA-DRIVEN INSIGHTS & EXTENDED VIEW ALL MODAL
  // =========================================================================
  let loadedInsights = [];
  async function loadInsights() {
    const container = document.getElementById('insights-container');
    if (!container) return;

    try {
      const res = await api.get('/api/v1/pl/insights').catch(() => null);
      if (res && res.insights && res.insights.length > 0) {
        loadedInsights = res.insights;
        container.innerHTML = '';

        loadedInsights.slice(0, 4).forEach(ins => {
          const icon = ins.category === 'Revenue' ? 'trending_up' :
                       (ins.category === 'Expenses' ? 'warning' :
                       (ins.category === 'Margin' ? 'favorite' : 'auto_awesome'));
          const iconColor = ins.type === 'POSITIVE' ? 'text-emerald-600' :
                            (ins.type === 'WARNING' ? 'text-rose-500' : 'text-purple-600');
          const badgeBg = ins.badge === 'CRITICAL' || ins.badge === 'ALERT' ? 'bg-rose-50 text-rose-600 border-rose-100' :
                          (ins.badge === 'HIGH IMPACT' ? 'bg-indigo-50 text-indigo-600 border-indigo-100' : 'bg-blue-50 text-blue-600 border-blue-100');

          const div = document.createElement('div');
          div.className = 'flex items-start justify-between gap-2';
          div.innerHTML = `
            <div class="flex items-start gap-1.5">
              <span class="material-symbols-outlined ${iconColor} text-sm mt-0.5">${icon}</span>
              <div>
                <p class="text-[10px] font-bold text-slate-800 leading-tight">${ins.title}</p>
                <p class="text-[9px] text-slate-500 leading-tight mt-0.5">${ins.description}</p>
              </div>
            </div>
            <span class="px-1.5 py-0.2 rounded text-[8px] font-bold ${badgeBg} border flex-shrink-0">${ins.badge}</span>
          `;
          container.appendChild(div);
        });
      }
    } catch (err) {
      console.warn('Insights error:', err);
    }
  }
  loadInsights();

  // Wire Extended Insights Modal
  const btnViewAllInsights = document.getElementById('btn-view-all-insights');
  const modalInsights = document.getElementById('modal-insights');
  const closeModalInsights = document.getElementById('close-modal-insights');
  const btnCloseInsightsFooter = document.getElementById('btn-close-insights-footer');

  if (btnViewAllInsights && modalInsights) {
    btnViewAllInsights.addEventListener('click', () => {
      const list = document.getElementById('modal-insights-list');
      if (list) {
        list.innerHTML = '';
        loadedInsights.forEach((ins, idx) => {
          const card = document.createElement('div');
          card.className = 'p-4 rounded-xl border border-slate-200 bg-white shadow-xs space-y-2.5';
          card.innerHTML = `
            <div class="flex items-center justify-between">
              <span class="font-bold text-sm text-slate-900">${idx + 1}. ${ins.title}</span>
              <span class="px-2.5 py-1 rounded-md text-xs font-bold bg-indigo-50 text-indigo-700 border border-indigo-100">${ins.category} • ${ins.department}</span>
            </div>
            <p class="text-xs text-slate-700 leading-relaxed">${ins.description}</p>
            <div class="grid grid-cols-2 gap-2.5 bg-slate-50 p-3 rounded-lg text-xs text-slate-700 border border-slate-100">
              <div><span class="font-bold text-slate-900">Metric:</span> ${ins.metric}</div>
              <div><span class="font-bold text-slate-900">Current Value:</span> ${typeof ins.current_value === 'number' ? formatCurrency(ins.current_value) : ins.current_value}</div>
              <div><span class="font-bold text-slate-900">Change:</span> <span class="${ins.change_pct >= 0 ? 'text-emerald-600 font-semibold' : 'text-rose-600 font-semibold'}">${ins.change_pct >= 0 ? '+' : ''}${ins.change_pct}%</span></div>
              <div><span class="font-bold text-slate-900">Period:</span> ${ins.time_period || 'Historical Multi-Period'}</div>
            </div>
            <div class="bg-slate-50 p-3 rounded-lg text-xs text-slate-700 border border-slate-100 space-y-1.5 leading-relaxed">
              <div><span class="font-bold text-slate-900">Why It Matters:</span> ${ins.why_it_matters}</div>
              <div><span class="font-bold text-slate-900">Supporting Data:</span> ${ins.supporting_data}</div>
              <div><span class="font-bold text-slate-900">Interpretation:</span> ${ins.interpretation}</div>
              <div><span class="font-bold text-slate-900">Suggested Action:</span> ${ins.suggested_action}</div>
            </div>
          `;
          list.appendChild(card);
        });
      }
      modalInsights.classList.remove('hidden');
    });
  }
  if (closeModalInsights) closeModalInsights.addEventListener('click', () => modalInsights?.classList.add('hidden'));
  if (btnCloseInsightsFooter) btnCloseInsightsFooter.addEventListener('click', () => modalInsights?.classList.add('hidden'));

  // =========================================================================
  // 7. ROW 3 LEFT: FORECAST VS ACTUAL (WITH DEPT + PERIOD + VARIANCE IN TOOLTIP)
  // =========================================================================
  const fcstEl = document.getElementById('chart-forecast-actual');
  const fcstChart = fcstEl ? initEchart(fcstEl) : null;
  setupZoomControls(fcstChart, 'zoom-in-fcst', 'zoom-out-fcst', 'zoom-reset-fcst');

  async function loadForecastActual(dept = 'all', period = 'monthly') {
    if (!fcstChart) return;
    try {
      const res = await api.get(`/api/v1/pl/forecast-vs-actual?dept=${dept}&period=${period}`);
      if (res && res.periods && res.periods.length > 0) {
        safeSetOption(fcstChart, {
          tooltip: {
            trigger: 'axis',
            backgroundColor: '#ffffff',
            borderColor: '#e2e8f0',
            borderWidth: 1,
            extraCssText: 'box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.1), 0 2px 4px -2px rgba(0, 0, 0, 0.06); border-radius: 8px;',
            textStyle: { color: '#0f172a', fontSize: 11, fontFamily: 'Inter, sans-serif' },
            formatter: (params) => {
              let html = `<div style="padding:4px 8px;font-size:11px;color:#0f172a"><div style="font-weight:600;margin-bottom:4px;border-bottom:1px solid #e2e8f0;padding-bottom:2px">${params[0]?.axisValue}</div>`;
              let actVal = null;
              let fcstVal = null;
              params.forEach(p => {
                if (p.value !== null && p.value !== undefined && !p.seriesName.includes('Confidence')) {
                  html += `<div style="display:flex;align-items:center;justify-content:space-between;gap:6px;margin:2px 0">
                    <span style="display:flex;align-items:center;gap:4px">
                      <span style="display:inline-block;width:7px;height:7px;border-radius:50%;background:${p.color}"></span>
                      <span>${p.seriesName}:</span>
                    </span>
                    <b>${formatCurrency(p.value)}</b>
                  </div>`;
                  if (p.seriesName === 'Actual') actVal = p.value;
                  if (p.seriesName === 'Forecast') fcstVal = p.value;
                }
              });
              if (actVal !== null && fcstVal !== null) {
                const diff = actVal - fcstVal;
                const diffPct = fcstVal !== 0 ? (diff / fcstVal * 100).toFixed(1) : 0;
                const sign = diff >= 0 ? '+' : '';
                const color = diff >= 0 ? '#10B981' : '#EF4444';
                html += `<div style="margin-top:4px;border-top:1px solid #e2e8f0;padding-top:2px;color:${color}">Variance: <b>${formatCurrency(diff)} (${sign}${diffPct}%)</b></div>`;
              }
              html += '</div>';
              return html;
            }
          },
          grid: { left: '8%', right: '4%', top: '10%', bottom: '15%', containLabel: true },
          dataZoom: [{ type: 'inside' }],
          xAxis: {
            type: 'category',
            data: res.periods,
            axisLine: { lineStyle: { color: '#E2E8F0' } },
            axisTick: { show: false },
            axisLabel: { color: '#64748B', fontSize: 10 }
          },
          yAxis: {
            type: 'value',
            axisLabel: { formatter: (v) => formatShort(v), color: '#94A3B8', fontSize: 10 },
            splitLine: { lineStyle: { color: '#F1F5F9' } }
          },
          series: [
            {
              name: 'Actual',
              type: 'line',
              smooth: 0.4,
              symbol: 'circle',
              symbolSize: 5,
              data: res.actual,
              itemStyle: { color: '#3B82F6' },
              lineStyle: { width: 2.5, color: '#3B82F6' }
            },
            {
              name: 'Forecast',
              type: 'line',
              smooth: 0.4,
              symbol: 'circle',
              symbolSize: 5,
              data: res.forecast,
              itemStyle: { color: '#8B5CF6' },
              lineStyle: { width: 2.5, type: 'dashed', color: '#8B5CF6' }
            },
            {
              name: 'Confidence Upper',
              type: 'line',
              smooth: 0.4,
              symbol: 'none',
              data: res.confidence_upper,
              lineStyle: { opacity: 0 },
              stack: 'confidence-band',
              areaStyle: { color: '#DDD6FE', opacity: 0.35 }
            },
            {
              name: 'Confidence Lower',
              type: 'line',
              smooth: 0.4,
              symbol: 'none',
              data: res.confidence_lower,
              lineStyle: { opacity: 0 },
              stack: 'confidence-band',
              areaStyle: { color: '#FFFFFF', opacity: 1 }
            }
          ]
        });
      }
    } catch (err) {
      console.warn('Forecast actual error:', err);
    }
  }

  const ctrlFcstDept = document.getElementById('ctrl-fcst-dept');
  const ctrlFcstPeriod = document.getElementById('ctrl-fcst-period');

  const triggerFcst = () => {
    loadForecastActual(
      ctrlFcstDept ? ctrlFcstDept.value : 'all',
      ctrlFcstPeriod ? ctrlFcstPeriod.value : 'monthly'
    );
  };

  if (ctrlFcstDept) ctrlFcstDept.addEventListener('change', triggerFcst);
  if (ctrlFcstPeriod) ctrlFcstPeriod.addEventListener('change', triggerFcst);

  loadForecastActual('all', 'monthly');

  // =========================================================================
  // 8. ROW 3 RIGHT: CASH FLOW TREND (INFLOW/OUTFLOW/NET WITH DEPT + PERIOD)
  // =========================================================================
  const cfChartEl = document.getElementById('chart-cash-flow');
  const cfChart = cfChartEl ? initEchart(cfChartEl) : null;
  setupZoomControls(cfChart, 'zoom-in-cf', 'zoom-out-cf', 'zoom-reset-cf');

  async function loadCashFlowTrend(dept = 'all', period = 'monthly') {
    if (!cfChart) return;
    try {
      const res = await api.get(`/api/v1/pl/cash-flow-trend?dept=${dept}&period=${period}`);
      if (res && res.periods && res.periods.length > 0) {
        const inflowData = (res.inflow || []).map(v => Math.abs(v));
        const outflowData = (res.outflow || []).map(v => -Math.abs(v));
        const netFlowData = res.net_flow || [];
        const barW = res.periods.length > 20 ? 9 : (res.periods.length > 10 ? 13 : 18);

        safeSetOption(cfChart, {
          legend: {
            show: true,
            top: 2,
            itemWidth: 8,
            itemHeight: 8,
            itemGap: 16,
            icon: 'circle',
            textStyle: { fontSize: 11, color: '#475569', fontWeight: 500, fontFamily: 'Inter, sans-serif' },
            data: ['Inflow', 'Outflow', 'Net Flow']
          },
          tooltip: {
            trigger: 'axis',
            axisPointer: { type: 'shadow' },
            backgroundColor: '#ffffff',
            borderColor: '#e2e8f0',
            borderWidth: 1,
            extraCssText: 'box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.1), 0 2px 4px -2px rgba(0, 0, 0, 0.06); border-radius: 8px; z-index: 99;',
            textStyle: { color: '#0f172a', fontSize: 11, fontFamily: 'Inter, sans-serif' },
            formatter: (params) => {
              const pName = params[0]?.axisValue || '';
              const idx = params[0]?.dataIndex ?? 0;
              const rawInflow = res.inflow?.[idx] ?? 0;
              const rawOutflow = res.outflow?.[idx] ?? 0;
              const rawNet = res.net_flow?.[idx] ?? 0;
              const netColor = rawNet >= 0 ? '#10B981' : '#EF4444';

              let html = `<div style="padding:4px 8px;font-size:11px;color:#0f172a">
                <div style="font-weight:600;margin-bottom:6px;border-bottom:1px solid #e2e8f0;padding-bottom:3px">${pName}</div>
                <div style="display:flex;align-items:center;justify-content:space-between;gap:16px;margin:3px 0">
                  <span style="display:flex;align-items:center;gap:5px;color:#475569">
                    <span style="display:inline-block;width:7px;height:7px;border-radius:50%;background:#10B981"></span>
                    <span>Inflow:</span>
                  </span>
                  <b style="color:#10B981">+${formatCurrency(rawInflow)}</b>
                </div>
                <div style="display:flex;align-items:center;justify-content:space-between;gap:16px;margin:3px 0">
                  <span style="display:flex;align-items:center;gap:5px;color:#475569">
                    <span style="display:inline-block;width:7px;height:7px;border-radius:50%;background:#EF4444"></span>
                    <span>Outflow:</span>
                  </span>
                  <b style="color:#EF4444">-${formatCurrency(rawOutflow)}</b>
                </div>
                <div style="display:flex;align-items:center;justify-content:space-between;gap:16px;margin-top:6px;border-top:1px dashed #e2e8f0;padding-top:4px">
                  <span style="display:flex;align-items:center;gap:5px;color:#475569">
                    <span style="display:inline-block;width:7px;height:7px;border-radius:50%;background:#3B82F6"></span>
                    <span style="font-weight:600">Net Flow:</span>
                  </span>
                  <b style="color:${netColor}">${formatCurrency(rawNet)}</b>
                </div>
              </div>`;
              return html;
            }
          },
          grid: { left: 8, right: 16, top: 32, bottom: 26, containLabel: true },
          dataZoom: [
            { type: 'inside' },
            {
              type: 'slider',
              height: 10,
              bottom: 2,
              borderColor: 'transparent',
              backgroundColor: '#F1F5F9',
              fillerColor: 'rgba(59, 130, 246, 0.15)',
              handleSize: '0%',
              showDetail: false
            }
          ],
          xAxis: {
            type: 'category',
            data: res.periods,
            axisLine: { lineStyle: { color: '#E2E8F0' } },
            axisTick: { show: false },
            axisLabel: { color: '#64748B', fontSize: 10, fontFamily: 'Inter, sans-serif' }
          },
          yAxis: {
            type: 'value',
            axisLine: { show: false },
            axisTick: { show: false },
            axisLabel: {
              formatter: (v) => formatShort(Math.abs(v)),
              color: '#94A3B8',
              fontSize: 10,
              fontFamily: 'Inter, sans-serif'
            },
            splitLine: { lineStyle: { color: '#F1F5F9' } }
          },
          series: [
            {
              name: 'Inflow',
              type: 'bar',
              stack: 'cashflow',
              barWidth: barW,
              data: inflowData,
              itemStyle: { color: '#10B981', borderRadius: [3, 3, 0, 0] }
            },
            {
              name: 'Outflow',
              type: 'bar',
              stack: 'cashflow',
              barWidth: barW,
              data: outflowData,
              itemStyle: { color: '#EF4444', borderRadius: [0, 0, 3, 3] }
            },
            {
              name: 'Net Flow',
              type: 'line',
              smooth: 0.25,
              symbol: 'circle',
              symbolSize: 5,
              data: netFlowData,
              itemStyle: { color: '#3B82F6', borderColor: '#ffffff', borderWidth: 1 },
              lineStyle: { width: 2, color: '#3B82F6' },
              z: 10
            }
          ]
        });
      }
    } catch (err) {
      console.warn('Cash flow error:', err);
    }
  }

  const ctrlCfDept = document.getElementById('ctrl-cf-dept');
  const ctrlCfPeriod = document.getElementById('ctrl-cf-period');

  const triggerCf = () => {
    loadCashFlowTrend(
      ctrlCfDept ? ctrlCfDept.value : 'all',
      ctrlCfPeriod ? ctrlCfPeriod.value : 'monthly'
    );
  };

  if (ctrlCfDept) ctrlCfDept.addEventListener('change', triggerCf);
  if (ctrlCfPeriod) ctrlCfPeriod.addEventListener('change', triggerCf);

  loadCashFlowTrend('all', 'monthly');

  // =========================================================================
  // =========================================================================
  // 9. ROW 4: BUDGET VS ACTUAL (VISUAL REFERENCE INFORMATION ARCHITECTURE)
  // =========================================================================
  async function loadBudgetActual(dept = 'all', range = 'all') {
    const container = document.getElementById('budget-actual-chart-container');
    const rowsEl = document.getElementById('budget-actual-rows');
    const axisEl = document.getElementById('budget-actual-axis');
    const emptyEl = document.getElementById('budget-empty-state');
    const summaryCard = document.getElementById('budget-summary-card');

    try {
      const res = await api.get(`/api/v1/pl/budget-vs-actual?dept=${dept}&range=${range}`);
      if (res && res.has_data && res.items && res.items.length > 0) {
        if (container) container.classList.remove('hidden');
        if (summaryCard) summaryCard.classList.remove('hidden');
        if (emptyEl) emptyEl.classList.add('hidden');

        // Populate department dropdown if needed
        const ctrlDept = document.getElementById('ctrl-budget-dept');
        if (ctrlDept && res.all_departments && res.all_departments.length > 0) {
          const currentVal = ctrlDept.value;
          ctrlDept.innerHTML = '<option value="all">All Departments</option>';
          res.all_departments.forEach(d => {
            const opt = document.createElement('option');
            opt.value = d;
            opt.textContent = d;
            ctrlDept.appendChild(opt);
          });
          if (currentVal && (currentVal === 'all' || res.all_departments.includes(currentVal))) {
            ctrlDept.value = currentVal;
          }
        }

        const items = res.items;

        // Calculate max scale for crisp bar proportions and axis ticks
        const maxVal = Math.max(...items.map(it => Math.max(it.actual, it.budget)), 1);
        // Find a clean round upper bound (e.g. 2.5 Cr, 3.0 Cr)
        const roundSteps = [0.5e7, 1.0e7, 1.5e7, 2.0e7, 2.5e7, 3.0e7, 3.5e7, 4.0e7, 5.0e7, 10.0e7];
        let maxScale = maxVal * 1.12;
        for (const step of roundSteps) {
          if (step >= maxVal * 1.05) {
            maxScale = step;
            break;
          }
        }

        // Generate 5-6 clean axis ticks
        const numTicks = 5;
        const tickValues = [];
        for (let i = 0; i <= numTicks; i++) {
          tickValues.push((maxScale / numTicks) * i);
        }

        // Render dynamic Department comparison rows
        if (rowsEl) {
          rowsEl.innerHTML = '';
          items.forEach(item => {
            const deptColor = getDepartmentColor(item.department);
            const actualPct = Math.min((item.actual / maxScale) * 100, 100);
            const budgetPct = Math.min((item.budget / maxScale) * 100, 100);

            // Variance text & colors
            const isOver = item.variance > 0;
            const isUnder = item.variance < 0;
            let varClass = 'text-slate-700 font-medium';
            let varSign = '';
            let varPctSign = '';
            let varPctClass = 'text-slate-700 font-medium';

            if (isOver) {
              varClass = 'text-[#DC2626] font-semibold';
              varSign = '+';
              varPctClass = 'text-[#DC2626] font-semibold';
              varPctSign = '+';
            } else if (isUnder) {
              varClass = 'text-[#059669] font-semibold';
              varSign = '-';
              varPctClass = 'text-[#059669] font-semibold';
              varPctSign = '';
            }

            // Status Badge Classes
            let statusBadgeClass = 'bg-[#EFF6FF] text-[#2563EB] border border-[#DBEAFE]';
            if (item.status === 'Over Budget') {
              statusBadgeClass = 'bg-[#FEF2F2] text-[#DC2626] border border-[#FEE2E2]';
            } else if (item.status === 'Slightly Over') {
              statusBadgeClass = 'bg-[#FFFBEB] text-[#D97706] border border-[#FEF3C7]';
            } else if (item.status === 'Under Budget') {
              statusBadgeClass = 'bg-[#ECFDF5] text-[#059669] border border-[#D1FAE5]';
            } else if (item.status === 'On Track') {
              statusBadgeClass = 'bg-[#EFF6FF] text-[#2563EB] border border-[#DBEAFE]';
            }

            const row = document.createElement('div');
            row.className = 'flex items-center justify-between py-1 px-1 rounded-lg hover:bg-slate-50/70 transition-colors group';
            row.innerHTML = `
              <!-- Left: Department Label -->
              <div class="w-28 flex-shrink-0 text-xs font-semibold text-slate-800 truncate pr-2" title="${item.department}">
                ${item.department}
              </div>

              <!-- Center: Horizontal Comparison Bar Container -->
              <div class="flex-1 relative h-6 flex items-center mx-3">
                <!-- Vertical Dotted Grid Alignment Lines -->
                <div class="absolute inset-0 flex justify-between pointer-events-none opacity-30">
                  ${tickValues.map(() => '<span class="border-r border-dashed border-slate-300 h-full"></span>').join('')}
                </div>

                <!-- Budget Target Background Bar (Lighter Bar) -->
                <div class="absolute left-0 h-4 bg-slate-200/90 rounded-r-md transition-all duration-300 pointer-events-none" style="width: ${budgetPct}%; z-index: 1;" title="Budget Target: ${formatCurrency(item.budget)}"></div>

                <!-- Actual Spend Foreground Bar -->
                <div class="absolute left-0 h-3.5 rounded-r-md transition-all duration-300 shadow-2xs" style="width: ${actualPct}%; background-color: ${deptColor}; z-index: 2;" title="Actual Spend: ${formatCurrency(item.actual)}"></div>

                <!-- Budget Target Marker (Dark Vertical Tick) -->
                <div class="absolute h-5 w-[2px] bg-slate-900 rounded-full transition-all duration-300 cursor-help" style="left: ${budgetPct}%; z-index: 3; transform: translateX(-50%);" title="Budget Target Marker: ${formatCurrency(item.budget)}"></div>
              </div>

              <!-- Right: Data Columns (Actual, Budget, Variance, Variance %, Status) -->
              <div class="flex items-center text-right text-xs pr-1 flex-shrink-0 font-medium">
                <span class="w-20 font-semibold text-slate-900">${formatCurrency(item.actual)}</span>
                <span class="w-20 text-slate-400 font-normal">${formatCurrency(item.budget)}</span>
                <span class="w-24 ${varClass}">${varSign}${formatCurrency(Math.abs(item.variance))}</span>
                <span class="w-20 ${varPctClass}">${varPctSign}${item.variance_pct}%</span>
                <span class="w-28 text-center flex justify-center">
                  <span class="inline-block px-2.5 py-0.5 rounded-full text-[10px] font-semibold ${statusBadgeClass}">
                    ${item.status}
                  </span>
                </span>
              </div>
            `;
            rowsEl.appendChild(row);
          });
        }

        // Render bottom scale ticks
        if (axisEl) {
          axisEl.innerHTML = `
            <div class="w-28 flex-shrink-0"></div>
            <div class="flex-1 flex justify-between mx-3 font-medium text-[10px] text-slate-400">
              ${tickValues.map(tv => `<span>${formatShort(tv)}</span>`).join('')}
            </div>
            <div class="w-[112px] flex-shrink-0"></div>
          `;
        }

        // Update Bottom Summary Card
        const sumIconContainer = document.getElementById('budget-summary-icon-container');
        const sumIcon = document.getElementById('budget-summary-icon');
        const sumTitle = document.getElementById('budget-summary-title');
        const sumSubtitle = document.getElementById('budget-summary-subtitle');
        const onCountEl = document.getElementById('budget-on-target-count');
        const overCountEl = document.getElementById('budget-over-target-count');

        const isOverallOver = res.total_variance > 0;
        if (sumIconContainer) {
          sumIconContainer.className = isOverallOver 
            ? 'w-10 h-10 rounded-full flex items-center justify-center bg-rose-100 text-rose-600 flex-shrink-0'
            : 'w-10 h-10 rounded-full flex items-center justify-center bg-emerald-100 text-emerald-600 flex-shrink-0';
        }
        if (sumIcon) {
          sumIcon.textContent = isOverallOver ? 'north_east' : 'south_east';
        }
        if (sumTitle) {
          sumTitle.className = isOverallOver ? 'text-sm font-bold text-rose-600 tracking-tight' : 'text-sm font-bold text-emerald-600 tracking-tight';
          sumTitle.textContent = `${Math.abs(res.total_variance_pct)}% ${isOverallOver ? 'over budget' : 'under budget'}`;
        }
        if (sumSubtitle) {
          sumSubtitle.textContent = res.highest_variance_pct > 0 
            ? `${res.highest_variance_dept} has the highest variance (+${res.highest_variance_pct}%).`
            : 'All departments operating within allocated budget targets.';
        }
        if (onCountEl) onCountEl.textContent = res.on_budget_count ?? 0;
        if (overCountEl) overCountEl.textContent = res.over_budget_count ?? 0;

      } else {
        if (container) container.classList.add('hidden');
        if (summaryCard) summaryCard.classList.add('hidden');
        if (emptyEl) emptyEl.classList.remove('hidden');
      }
    } catch (err) {
      console.warn('Budget vs actual error:', err);
      if (container) container.classList.add('hidden');
      if (summaryCard) summaryCard.classList.add('hidden');
      if (emptyEl) emptyEl.classList.remove('hidden');
    }
  }

  const ctrlBudgetRange = document.getElementById('ctrl-budget-range');
  const ctrlBudgetDept = document.getElementById('ctrl-budget-dept');
  const btnBudgetOptions = document.getElementById('btn-budget-options');

  const triggerBudgetActual = () => {
    loadBudgetActual(
      ctrlBudgetDept ? ctrlBudgetDept.value : 'all',
      ctrlBudgetRange ? ctrlBudgetRange.value : 'all'
    );
  };

  if (ctrlBudgetRange) ctrlBudgetRange.addEventListener('change', triggerBudgetActual);
  if (ctrlBudgetDept) ctrlBudgetDept.addEventListener('change', triggerBudgetActual);
  if (btnBudgetOptions) btnBudgetOptions.addEventListener('click', triggerBudgetActual);

  loadBudgetActual('all', 'all');

  // =========================================================================
  // 10. ROW 4 RIGHT: RECOMMENDATIONS (AI) & IN-PLACE MODAL
  // =========================================================================
  let loadedRecommendations = [];
  async function loadRecommendations() {
    const container = document.getElementById('recommendations-container');
    if (!container) return;

    try {
      const res = await api.get('/api/v1/recommendations').catch(() => null);
      if (res && Array.isArray(res) && res.length > 0) {
        loadedRecommendations = res;
        container.innerHTML = '';
        loadedRecommendations.slice(0, 4).forEach(rec => {
          const cat = (rec.category || '').toLowerCase();
          const icon = cat.includes('revenue') ? 'campaign' :
                       (cat.includes('cost') || cat.includes('expense') ? 'account_balance_wallet' :
                       (cat.includes('margin') ? 'trending_up' :
                       (cat.includes('risk') ? 'warning' : 'smart_toy')));
          const impactBadge = rec.priority === 'High'
            ? 'bg-rose-50 text-rose-600 border-rose-100'
            : (rec.priority === 'Medium' ? 'bg-amber-50 text-amber-600 border-amber-100' : 'bg-blue-50 text-blue-600 border-blue-100');

          const div = document.createElement('div');
          div.className = 'p-2 rounded-lg bg-slate-50/70 border border-slate-100 flex flex-col justify-between';
          div.innerHTML = `
            <div class="flex items-start justify-between gap-1">
              <div class="flex items-start gap-1.5">
                <span class="material-symbols-outlined text-indigo-600 text-sm mt-0.5">${icon}</span>
                <div>
                  <p class="text-[10px] font-bold text-slate-800 leading-tight">${rec.title}</p>
                  <p class="text-[9px] text-slate-500 leading-tight mt-0.5 line-clamp-2">${rec.reason}</p>
                </div>
              </div>
              <span class="px-1.5 py-0.2 rounded text-[8px] font-bold ${impactBadge} border flex-shrink-0">${rec.priority}</span>
            </div>
            <div class="mt-1 pt-1 border-t border-slate-100 flex items-center justify-between text-[9px]">
              <span class="text-slate-500 font-medium">Dept: <b>${rec.department || 'All'}</b></span>
              <span class="text-indigo-600 font-semibold truncate max-w-[130px]">${rec.suggested_action}</span>
            </div>
          `;
          container.appendChild(div);
        });
      }
    } catch (err) {
      console.warn('Recommendations error:', err);
    }
  }
  loadRecommendations();

  // Wire Extended Recommendations Modal
  const btnViewAllRecommendations = document.getElementById('btn-view-all-recommendations');
  const modalRecommendations = document.getElementById('modal-recommendations');
  const closeModalRecommendations = document.getElementById('close-modal-recommendations');
  const btnCloseRecommendationsFooter = document.getElementById('btn-close-recommendations-footer');

  if (btnViewAllRecommendations && modalRecommendations) {
    btnViewAllRecommendations.addEventListener('click', () => {
      const list = document.getElementById('modal-recommendations-list');
      if (list) {
        list.innerHTML = '';
        loadedRecommendations.forEach((rec, idx) => {
          const badgeBg = rec.priority === 'High' ? 'bg-rose-50 text-rose-700 border-rose-200' :
                          (rec.priority === 'Medium' ? 'bg-amber-50 text-amber-700 border-amber-200' : 'bg-blue-50 text-blue-700 border-blue-200');
          const card = document.createElement('div');
          card.className = 'p-4 rounded-xl border border-slate-200 bg-white shadow-xs space-y-2.5';
          card.innerHTML = `
            <div class="flex items-center justify-between">
              <span class="font-bold text-sm text-slate-900">${idx + 1}. ${rec.title}</span>
              <div class="flex items-center gap-2">
                <span class="px-2.5 py-1 rounded-md text-xs font-bold ${badgeBg} border">${rec.priority} Priority</span>
                <span class="px-2.5 py-1 rounded-md text-xs font-bold bg-indigo-50 text-indigo-700 border border-indigo-100">${rec.department || 'Enterprise'}</span>
              </div>
            </div>
            <p class="text-xs text-slate-700 leading-relaxed">${rec.reason}</p>
            <div class="grid grid-cols-2 gap-2.5 bg-slate-50 p-3 rounded-lg text-xs text-slate-700 border border-slate-100">
              <div><span class="font-bold text-slate-900">Category:</span> ${rec.category || 'Strategic Advisory'}</div>
              <div><span class="font-bold text-slate-900">Financial Impact:</span> <span class="text-emerald-600 font-semibold">${typeof rec.financial_impact === 'number' ? formatCurrency(rec.financial_impact) : rec.financial_impact}</span></div>
              <div><span class="font-bold text-slate-900">Confidence Score:</span> ${rec.confidence || 90}%</div>
              <div><span class="font-bold text-slate-900">Expected Benefit:</span> ${rec.expected_benefit || 'EBITDA expansion'}</div>
            </div>
            <div class="bg-indigo-50/50 p-3 rounded-lg text-xs text-slate-800 border border-indigo-100 flex items-center justify-between gap-3">
              <div><span class="font-bold text-slate-900">Suggested Action:</span> ${rec.suggested_action}</div>
              <button class="px-3.5 py-1.5 rounded-lg bg-indigo-600 hover:bg-indigo-700 text-white text-xs font-semibold shadow-xs transition-colors flex-shrink-0 cursor-pointer">
                ${rec.action_button || 'Implement'}
              </button>
            </div>
          `;
          list.appendChild(card);
        });
      }
      modalRecommendations.classList.remove('hidden');
    });
  }
  if (closeModalRecommendations) closeModalRecommendations.addEventListener('click', () => modalRecommendations?.classList.add('hidden'));
  if (btnCloseRecommendationsFooter) btnCloseRecommendationsFooter.addEventListener('click', () => modalRecommendations?.classList.add('hidden'));

  // Close modals on backdrop click or Escape key
  if (modalInsights) {
    modalInsights.addEventListener('click', (e) => {
      if (e.target === modalInsights) modalInsights.classList.add('hidden');
    });
  }
  if (modalRecommendations) {
    modalRecommendations.addEventListener('click', (e) => {
      if (e.target === modalRecommendations) modalRecommendations.classList.add('hidden');
    });
  }
  window.addEventListener('keydown', (e) => {
    if (e.key === 'Escape') {
      modalInsights?.classList.add('hidden');
      modalRecommendations?.classList.add('hidden');
    }
  });

  // Global window resize listener
  window.addEventListener('resize', () => {
    revExpChart?.resize();
    anomOverviewChart?.resize();
    deptPerfChart?.resize();
    expDistChart?.resize();
    fcstChart?.resize();
    cfChart?.resize();
    budgetChart?.resize();
  });
});
