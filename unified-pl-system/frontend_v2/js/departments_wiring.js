import { api } from './api.js';
import { initEchart, safeSetOption } from './chart-engine.js';
async function initDepartmentsWiring() {
  // =========================================================================
  // HELPER FORMATTERS & CENTRALIZED DETERMINISTIC COLOR SYSTEM
  // =========================================================================
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

  const DEPARTMENT_COLORS = {
    'Sales': '#3B82F6',           // Blue
    'Operations': '#10B981',      // Emerald Green
    'Finance': '#6366F1',         // Indigo
    'IT': '#F97316',              // Orange
    'Technology': '#F97316',
    'Engineering': '#F97316',
    'Information Technology': '#F97316',
    'R&D': '#2563EB',             // Royal Blue
    'Research & Development': '#2563EB',
    'Logistics': '#0D9488',       // Teal
    'Supply Chain': '#0D9488',
    'Marketing': '#8B5CF6',       // Purple
    'Procurement': '#EF4444',     // Red
    'Administration': '#06B6D4',  // Cyan
    'Customer Support': '#EAB308',// Amber/Yellow
    'Support': '#EAB308',
    'Human Resources': '#EC4899', // Pink
    'HR': '#EC4899',
    'Legal': '#84CC16',           // Lime
    'Commercial': '#0284C7',      // Sky Blue
    'Executive': '#4F46E5',       // Deep Violet
    'Product': '#D946EF',         // Fuchsia
    'Quality Assurance': '#14B8A6',// Light Teal
    'Security': '#64748B',        // Slate
  };

  const DISTINCT_PALETTE = [
    '#3B82F6', '#10B981', '#6366F1', '#F97316', '#2563EB',
    '#0D9488', '#8B5CF6', '#EF4444', '#06B6D4', '#EAB308',
    '#EC4899', '#84CC16', '#0284C7', '#4F46E5', '#D946EF',
    '#14B8A6', '#F43F5E', '#A855F7', '#64748B', '#059669'
  ];

  function getDepartmentColor(deptName) {
    if (!deptName) return '#3B82F6';
    if (DEPARTMENT_COLORS[deptName]) return DEPARTMENT_COLORS[deptName];
    const match = Object.keys(DEPARTMENT_COLORS).find(k => k.toLowerCase() === deptName.toLowerCase());
    if (match) return DEPARTMENT_COLORS[match];
    let hash = 0;
    for (let i = 0; i < deptName.length; i++) {
      hash = deptName.charCodeAt(i) + ((hash << 5) - hash);
    }
    const idx = Math.abs(hash) % DISTINCT_PALETTE.length;
    return DISTINCT_PALETTE[idx];
  }

  // Setup generic zoom controls
  function setupZoomControls(chartInstance, zoomInId, zoomOutId, resetId) {
    if (!chartInstance) return;
    let zoomLevel = 1.0;
    const btnIn = document.getElementById(zoomInId);
    const btnOut = document.getElementById(zoomOutId);
    const btnReset = document.getElementById(resetId);

    if (btnIn) {
      btnIn.addEventListener('click', () => {
        zoomLevel = Math.max(0.2, zoomLevel - 0.2);
        chartInstance.dispatchAction({
          type: 'dataZoom',
          start: 0,
          end: Math.round(zoomLevel * 100)
        });
      });
    }
    if (btnOut) {
      btnOut.addEventListener('click', () => {
        zoomLevel = Math.min(1.0, zoomLevel + 0.2);
        chartInstance.dispatchAction({
          type: 'dataZoom',
          start: 0,
          end: Math.round(zoomLevel * 100)
        });
      });
    }
    if (btnReset) {
      btnReset.addEventListener('click', () => {
        zoomLevel = 1.0;
        chartInstance.dispatchAction({
          type: 'dataZoom',
          start: 0,
          end: 100
        });
      });
    }
  }

  // Sparkline chart renderer
  function renderSparkline(elementId, data, color) {
    const el = document.getElementById(elementId);
    if (!el || !data || data.length === 0) return;
    const spark = initEchart(el);
    if (!spark) return;
    safeSetOption(spark, {
      grid: { left: 0, right: 0, top: 2, bottom: 2 },
      xAxis: { type: 'category', show: false, data: data.map((_, i) => i) },
      yAxis: { type: 'value', show: false, min: 'dataMin' },
      series: [{
        type: 'line',
        data: data,
        smooth: true,
        showSymbol: false,
        lineStyle: { width: 1.5, color: color },
        areaStyle: {
          color: {
            type: 'linear',
            x: 0, y: 0, x2: 0, y2: 1,
            colorStops: [
              { offset: 0, color: color + '33' },
              { offset: 1, color: color + '00' }
            ]
          }
        }
      }]
    });
  }

  let allDepartments = [];
  let summaryTableData = [];
  let currentTableSort = { col: 'profit', asc: false };
  let selectedTrendDepts = new Set(); // Multi-select state

  // =========================================================================
  // 1. KPI CARDS & ACTIVE DATASET WIRING
  // =========================================================================
  async function loadKPIs() {
    try {
      const summary = await api.get('/api/v1/pl/summary?dept=all').catch(() => null);
      if (summary && summary.kpis) {
        const k = summary.kpis;
        const rEl = document.getElementById('kpi-total-revenue');
        const eEl = document.getElementById('kpi-total-expenses');
        const pEl = document.getElementById('kpi-net-profit');
        const mEl = document.getElementById('kpi-net-margin');

        if (rEl && k.revenue !== undefined) rEl.textContent = formatCurrency(k.revenue);
        if (eEl && k.expense !== undefined) eEl.textContent = formatCurrency(k.expense);
        if (pEl && k.profit !== undefined) pEl.textContent = formatCurrency(k.profit);

        // Dynamically calculate Net Margin % = (Net Profit / Revenue) * 100
        const calcMargin = (k.revenue && k.revenue > 0) ? ((k.profit / k.revenue) * 100) : (k.profit_margin || 0.0);
        if (mEl) mEl.textContent = `${calcMargin.toFixed(1)}%`;

        // Trends
        const rGr = document.getElementById('kpi-revenue-trend');
        const eGr = document.getElementById('kpi-expense-trend');
        const pGr = document.getElementById('kpi-profit-trend');
        const mGr = document.getElementById('kpi-margin-trend');

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

      // Sparklines from historical charts data
      const chartData = await api.get('/api/v1/pl/charts?dept=all&agg=monthly').catch(() => null);
      if (chartData) {
        if (chartData.revenue_trend) renderSparkline('sparkline-revenue', chartData.revenue_trend.map(d => d.value), '#3B82F6');
        if (chartData.expense_trend) renderSparkline('sparkline-expenses', chartData.expense_trend.map(d => d.value), '#EF4444');
        if (chartData.profit_trend) renderSparkline('sparkline-profit', chartData.profit_trend.map(d => d.value), '#10B981');
        if (chartData.revenue_trend && chartData.profit_trend) {
          const margins = chartData.revenue_trend.map((r, i) => {
            const p = chartData.profit_trend[i]?.value || 0;
            return r.value > 0 ? (p / r.value * 100) : 0;
          });
          renderSparkline('sparkline-margin', margins, '#8B5CF6');
        }
      }

      // Populate department dropdowns and multi-select
      const deptRes = await api.get('/api/v1/pl/departments/summary').catch(() => null);
      if (deptRes && deptRes.departments && deptRes.departments.length > 0) {
        allDepartments = deptRes.departments.map(d => d.department).filter(d => d && d !== 'All Departments' && d !== 'Unknown');

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
          if (currentVal && (currentVal === 'all' || allDepartments.includes(currentVal))) {
            sel.value = currentVal;
          }
        };

        populateDropdown('ctrl-budget-dept');

        // Initialize Trend Multi-Select Checkboxes
        setupTrendMultiSelect(allDepartments);
      }
    } catch (err) {
      console.warn('Department KPIs error:', err);
    }
  }

  // =========================================================================
  // 2. ROW 1 LEFT: DEPARTMENT PERFORMANCE (EXACT DASHBOARD REUSE)
  // =========================================================================
  const deptPerfEl = document.getElementById('chart-dept-performance');
  const deptPerfChart = deptPerfEl ? initEchart(deptPerfEl) : null;
  setupZoomControls(deptPerfChart, 'zoom-in-dept-perf', 'zoom-out-dept-perf', 'zoom-reset-dept-perf');

  async function loadDeptPerformance(metric = 'profit', limit = 'top5') {
    if (!deptPerfChart) return;
    try {
      const res = await api.get(`/api/v1/pl/department-performance?metric=${metric}&limit=${limit}`);
      if (res && res.departments && res.departments.length > 0) {
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
          grid: { left: 4, right: 56, top: 10, bottom: 8, containLabel: true },
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

  const ctrlDeptPerfMetric = document.getElementById('ctrl-dept-perf-metric');
  const ctrlDeptPerfRange = document.getElementById('ctrl-dept-perf-range');

  const triggerDeptPerf = () => {
    loadDeptPerformance(
      ctrlDeptPerfMetric ? ctrlDeptPerfMetric.value : 'profit',
      ctrlDeptPerfRange ? ctrlDeptPerfRange.value : 'top5'
    );
  };

  if (ctrlDeptPerfMetric) ctrlDeptPerfMetric.addEventListener('change', triggerDeptPerf);
  if (ctrlDeptPerfRange) ctrlDeptPerfRange.addEventListener('change', triggerDeptPerf);

  loadDeptPerformance('profit', 'top5');

  // =========================================================================
  // 3. ROW 1 RIGHT: DEPARTMENT TREND (MULTI-SELECT DEPARTMENTS + TIME AGG + ZOOM)
  // =========================================================================
  const deptTrendEl = document.getElementById('chart-dept-trend');
  const deptTrendChart = deptTrendEl ? initEchart(deptTrendEl) : null;
  setupZoomControls(deptTrendChart, 'zoom-in-dept-trend', 'zoom-out-dept-trend', 'zoom-reset-dept-trend');

  // Setup Multi-Select Department Component
  function setupTrendMultiSelect(depts) {
    const listEl = document.getElementById('trend-dept-checkbox-list');
    const labelEl = document.getElementById('trend-dept-select-label');
    const badgeEl = document.getElementById('trend-dept-count-badge');
    const dropdownEl = document.getElementById('dropdown-dept-trend-multiselect');
    const btnToggle = document.getElementById('btn-dept-trend-multiselect');
    const btnSelectAll = document.getElementById('btn-trend-select-all');
    const btnClearAll = document.getElementById('btn-trend-clear-all');
    const btnApply = document.getElementById('btn-trend-apply-filter');

    if (!listEl) return;

    // Default select all departments initially
    selectedTrendDepts = new Set(depts);

    const updateLabelAndBadge = () => {
      if (selectedTrendDepts.size === depts.length || selectedTrendDepts.size === 0) {
        if (labelEl) labelEl.textContent = `All (${depts.length})`;
      } else if (selectedTrendDepts.size === 1) {
        if (labelEl) labelEl.textContent = Array.from(selectedTrendDepts)[0];
      } else {
        if (labelEl) labelEl.textContent = `${selectedTrendDepts.size} Depts`;
      }
      if (badgeEl) badgeEl.textContent = `${selectedTrendDepts.size} of ${depts.length} selected`;
    };

    listEl.innerHTML = '';
    depts.forEach(dept => {
      const color = getDepartmentColor(dept);
      const row = document.createElement('label');
      row.className = 'flex items-center gap-2 p-1.5 rounded-lg hover:bg-slate-50 cursor-pointer text-xs select-none transition-colors';
      row.innerHTML = `
        <input type="checkbox" value="${dept}" ${selectedTrendDepts.has(dept) ? 'checked' : ''} class="w-3.5 h-3.5 text-indigo-600 rounded border-slate-300 focus:ring-indigo-500 cursor-pointer">
        <span class="w-2.5 h-2.5 rounded-full flex-shrink-0" style="background:${color}"></span>
        <span class="text-slate-800 font-medium text-[11px] truncate flex-1">${dept}</span>
      `;

      const chk = row.querySelector('input');
      chk.addEventListener('change', (e) => {
        if (e.target.checked) {
          selectedTrendDepts.add(dept);
        } else {
          selectedTrendDepts.delete(dept);
        }
        updateLabelAndBadge();
        triggerDeptTrend();
      });

      listEl.appendChild(row);
    });

    updateLabelAndBadge();

    // Toggle Dropdown Popover
    if (btnToggle && dropdownEl) {
      btnToggle.onclick = (e) => {
        e.stopPropagation();
        dropdownEl.classList.toggle('hidden');
      };
      document.addEventListener('click', (e) => {
        if (!dropdownEl.contains(e.target) && !btnToggle.contains(e.target)) {
          dropdownEl.classList.add('hidden');
        }
      });
    }

    // Select All
    if (btnSelectAll) {
      btnSelectAll.onclick = () => {
        selectedTrendDepts = new Set(depts);
        listEl.querySelectorAll('input[type="checkbox"]').forEach(c => c.checked = true);
        updateLabelAndBadge();
        triggerDeptTrend();
      };
    }

    // Clear All
    if (btnClearAll) {
      btnClearAll.onclick = () => {
        selectedTrendDepts.clear();
        listEl.querySelectorAll('input[type="checkbox"]').forEach(c => c.checked = false);
        updateLabelAndBadge();
        triggerDeptTrend();
      };
    }

    if (btnApply && dropdownEl) {
      btnApply.onclick = () => {
        dropdownEl.classList.add('hidden');
        triggerDeptTrend();
      };
    }
  }

  async function loadDeptTrend(agg = 'monthly', metric = 'profit', dept = 'all') {
    if (!deptTrendChart) return;
    try {
      const metricTitleMap = {
        'profit': 'Department Trend — Net Profit',
        'revenue': 'Department Trend — Revenue',
        'expense': 'Department Trend — Expense',
        'margin_pct': 'Department Trend — Net Margin'
      };
      const titleEl = document.getElementById('title-dept-trend');
      if (titleEl && metricTitleMap[metric]) {
        titleEl.textContent = metricTitleMap[metric];
      }

      // If dept is empty or empty array, fallback to 'all'
      let deptQuery = dept;
      if (Array.isArray(dept)) {
        deptQuery = dept.length > 0 ? dept.join(',') : 'all';
      } else if (dept instanceof Set) {
        deptQuery = dept.size > 0 ? Array.from(dept).join(',') : 'all';
      }

      const res = await api.get(`/api/v1/pl/departments/trend?agg=${agg}&metric=${metric}&dept=${encodeURIComponent(deptQuery)}`);
      if (res && res.periods && res.periods.length > 0 && res.series && Object.keys(res.series).length > 0) {
        const periods = res.periods;
        const isPct = res.is_percentage || metric === 'margin_pct';
        const seriesEntries = Object.entries(res.series);

        // Format readable X-axis period labels
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

        const displayPeriods = periods.map(formatPeriod);

        const seriesList = seriesEntries.map(([deptName, dataPoints]) => {
          const color = getDepartmentColor(deptName);
          return {
            name: deptName,
            type: 'line',
            smooth: 0.35,
            symbol: 'circle',
            symbolSize: periods.length > 20 ? 3 : 5,
            showSymbol: periods.length <= 30,
            data: dataPoints,
            itemStyle: { color: color },
            lineStyle: { color: color, width: 2 }
          };
        });

        safeSetOption(deptTrendChart, {
          tooltip: {
            trigger: 'axis',
            backgroundColor: '#ffffff',
            borderColor: '#e2e8f0',
            borderWidth: 1,
            extraCssText: 'box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.1), 0 2px 4px -2px rgba(0, 0, 0, 0.06); border-radius: 8px; z-index: 99;',
            textStyle: { color: '#0f172a', fontSize: 11, fontFamily: 'Inter, sans-serif' },
            formatter: (params) => {
              const rawP = periods[params[0]?.dataIndex] || params[0]?.axisValue;
              const formattedP = formatPeriod(rawP);
              let html = `<div style="padding:4px 8px;font-size:11px;color:#0f172a">
                <div style="font-weight:600;margin-bottom:4px;border-bottom:1px solid #e2e8f0;padding-bottom:2px">${formattedP} (${metric.toUpperCase().replace('_', ' ')})</div>`;
              params.forEach(p => {
                const valFmt = isPct ? `${p.value}%` : formatCurrency(p.value);
                html += `<div style="display:flex;align-items:center;justify-content:space-between;gap:14px;margin:2px 0">
                  <span style="display:flex;align-items:center;gap:5px">
                    <span style="display:inline-block;width:7px;height:7px;border-radius:50%;background:${p.color}"></span>
                    <span>${p.seriesName}:</span>
                  </span>
                  <b>${valFmt}</b>
                </div>`;
              });
              html += '</div>';
              return html;
            }
          },
          legend: {
            show: true,
            top: 4,
            left: 'center',
            type: 'scroll',
            pageIconSize: 10,
            pageTextStyle: { fontSize: 9, color: '#64748B' },
            itemWidth: 8,
            itemHeight: 8,
            itemGap: 14,
            icon: 'circle',
            textStyle: { fontSize: 10, color: '#475569', fontWeight: 500, fontFamily: 'Inter, sans-serif' }
          },
          grid: { left: 8, right: 16, top: 38, bottom: 20, containLabel: true },
          dataZoom: [{ type: 'inside' }],
          xAxis: {
            type: 'category',
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
              formatter: (v) => isPct ? `${v}%` : formatShort(v),
              color: '#94A3B8',
              fontSize: 10,
              fontFamily: 'Inter, sans-serif'
            },
            splitLine: { lineStyle: { color: '#F1F5F9' } }
          },
          series: seriesList
        }, true);
      } else {
        safeSetOption(deptTrendChart, {
          title: {
            text: 'No trend series selected',
            left: 'center',
            top: 'center',
            textStyle: { color: '#94A3B8', fontSize: 12, fontWeight: 'normal' }
          },
          series: []
        }, true);
      }
    } catch (err) {
      console.warn('Dept trend error:', err);
    }
  }

  const ctrlDeptTrendMetric = document.getElementById('ctrl-dept-trend-metric');
  const ctrlDeptTrendAgg = document.getElementById('ctrl-dept-trend-agg');

  const triggerDeptTrend = () => {
    const selectedList = selectedTrendDepts.size > 0 ? Array.from(selectedTrendDepts) : 'all';
    loadDeptTrend(
      ctrlDeptTrendAgg ? ctrlDeptTrendAgg.value : 'monthly',
      ctrlDeptTrendMetric ? ctrlDeptTrendMetric.value : 'profit',
      selectedList
    );
  };

  if (ctrlDeptTrendMetric) ctrlDeptTrendMetric.addEventListener('change', triggerDeptTrend);
  if (ctrlDeptTrendAgg) ctrlDeptTrendAgg.addEventListener('change', triggerDeptTrend);

  loadDeptTrend('monthly', 'profit', 'all');

  // =========================================================================
  // 4. ROW 2: BUDGET VS ACTUAL (FULL WIDTH VISUAL REFERENCE ARCHITECTURE)
  // =========================================================================
  async function loadBudgetActual(dept = 'all', range = 'top5') {
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

        const items = res.items;
        const maxVal = Math.max(...items.map(it => Math.max(it.actual, it.budget)), 1);
        const roundSteps = [0.5e7, 1.0e7, 1.5e7, 2.0e7, 2.5e7, 3.0e7, 3.5e7, 4.0e7, 5.0e7, 10.0e7];
        let maxScale = maxVal * 1.12;
        for (const step of roundSteps) {
          if (step >= maxVal * 1.05) {
            maxScale = step;
            break;
          }
        }

        const numTicks = 6;
        const tickValues = [];
        for (let i = 0; i <= numTicks; i++) {
          tickValues.push((maxScale / numTicks) * i);
        }

        if (rowsEl) {
          rowsEl.innerHTML = '';
          items.forEach(item => {
            const deptColor = getDepartmentColor(item.department);
            const actualPct = Math.min((item.actual / maxScale) * 100, 100);
            const budgetPct = Math.min((item.budget / maxScale) * 100, 100);

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

                <!-- Budget Target Background Bar -->
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

        if (axisEl) {
          axisEl.innerHTML = `
            <div class="w-28 flex-shrink-0"></div>
            <div class="flex-1 flex justify-between mx-3 font-medium text-[10px] text-slate-400">
              ${tickValues.map(tv => `<span>${formatShort(tv)}</span>`).join('')}
            </div>
            <div class="w-[112px] flex-shrink-0"></div>
          `;
        }

        // Summary card
        const sumIconContainer = document.getElementById('budget-summary-icon-container');
        const sumIcon = document.getElementById('budget-summary-icon');
        const sumTitle = document.getElementById('budget-summary-title');
        const sumSubtitle = document.getElementById('budget-summary-subtitle');
        const onCountEl = document.getElementById('budget-on-target-count');
        const overCountEl = document.getElementById('budget-over-target-count');

        const isOverallOver = res.total_variance > 0;
        if (sumIconContainer) {
          sumIconContainer.className = isOverallOver 
            ? 'w-9 h-9 rounded-full flex items-center justify-center bg-rose-100 text-rose-600 flex-shrink-0'
            : 'w-9 h-9 rounded-full flex items-center justify-center bg-emerald-100 text-emerald-600 flex-shrink-0';
        }
        if (sumIcon) sumIcon.textContent = isOverallOver ? 'north_east' : 'south_east';
        if (sumTitle) {
          sumTitle.className = isOverallOver ? 'text-xs font-bold text-rose-600 tracking-tight' : 'text-xs font-bold text-emerald-600 tracking-tight';
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

  const triggerBudgetActual = () => {
    loadBudgetActual(
      ctrlBudgetDept ? ctrlBudgetDept.value : 'all',
      ctrlBudgetRange ? ctrlBudgetRange.value : 'top5'
    );
  };

  if (ctrlBudgetRange) ctrlBudgetRange.addEventListener('change', triggerBudgetActual);
  if (ctrlBudgetDept) ctrlBudgetDept.addEventListener('change', triggerBudgetActual);

  loadBudgetActual('all', 'top5');

  // =========================================================================
  // 5. ROW 3 LEFT: DEPARTMENT SUMMARY TABLE (DATA-DRIVEN & SORTABLE)
  // =========================================================================
  function renderSummaryTable() {
    const tbody = document.getElementById('dept-summary-tbody');
    if (!tbody || summaryTableData.length === 0) return;

    let filtered = [...summaryTableData];

    // Apply sorting
    filtered.sort((a, b) => {
      let vA = a[currentTableSort.col];
      let vB = b[currentTableSort.col];
      if (currentTableSort.col === 'vs_prev') {
        vA = a.vs_prev_period_pct ?? -9999;
        vB = b.vs_prev_period_pct ?? -9999;
      }
      if (typeof vA === 'string') {
        return currentTableSort.asc ? vA.localeCompare(vB) : vB.localeCompare(vA);
      }
      vA = vA ?? 0;
      vB = vB ?? 0;
      return currentTableSort.asc ? (vA - vB) : (vB - vA);
    });

    tbody.innerHTML = '';
    filtered.forEach(d => {
      const color = getDepartmentColor(d.department);
      const vsPrev = d.vs_prev_period_pct;
      let vsPrevHtml = '<span class="text-slate-400 font-normal">—</span>';
      if (vsPrev !== null && vsPrev !== undefined) {
        const sign = vsPrev >= 0 ? '+' : '';
        const colorCls = vsPrev >= 0 ? 'text-emerald-600' : 'text-rose-500';
        vsPrevHtml = `<span class="${colorCls} font-semibold">${sign}${vsPrev}%</span>`;
      }

      const tr = document.createElement('tr');
      tr.className = 'hover:bg-slate-50/70 transition-colors';
      tr.innerHTML = `
        <td class="py-2.5 px-3 font-medium text-slate-800 flex items-center gap-2">
          <span class="w-2 h-2 rounded-full flex-shrink-0" style="background:${color}"></span>
          <span class="font-semibold text-slate-900">${d.department}</span>
        </td>
        <td class="py-2.5 px-3 font-medium text-slate-700 text-right">${formatCurrency(d.revenue)}</td>
        <td class="py-2.5 px-3 text-slate-600 text-right">${formatCurrency(d.expense)}</td>
        <td class="py-2.5 px-3 font-semibold text-slate-900 text-right">${formatCurrency(d.profit)}</td>
        <td class="py-2.5 px-3 text-slate-700 font-medium text-right">${(d.margin || 0).toFixed(1)}%</td>
        <td class="py-2.5 px-3 text-right">${vsPrevHtml}</td>
      `;
      tbody.appendChild(tr);
    });
  }

  // Setup click sorting on table headers
  const tableHeaders = document.querySelectorAll('#dept-summary-table th[data-sort]');
  tableHeaders.forEach(th => {
    th.addEventListener('click', () => {
      const col = th.getAttribute('data-sort');
      if (currentTableSort.col === col) {
        currentTableSort.asc = !currentTableSort.asc;
      } else {
        currentTableSort.col = col;
        currentTableSort.asc = false;
      }
      renderSummaryTable();
    });
  });

  // =========================================================================
  // 6. ROW 3 RIGHT: TOP PERFORMERS (ALL DEPARTMENTS RANKED 1..N)
  // =========================================================================
  function renderTopPerformers() {
    const topContainer = document.getElementById('top-performers-container');
    const badgeEl = document.getElementById('top-performers-count-badge');
    if (!topContainer || summaryTableData.length === 0) return;

    // Rank all departments by profit descending
    const ranked = [...summaryTableData].sort((a, b) => (b.profit || 0) - (a.profit || 0));
    topContainer.innerHTML = '';
    if (badgeEl) badgeEl.textContent = `${ranked.length} Units`;

    ranked.forEach((d, idx) => {
      const deptColor = getDepartmentColor(d.department);
      const badgeClass = idx === 0 ? 'bg-amber-100 text-amber-800 border-amber-300' :
                         (idx === 1 ? 'bg-slate-200 text-slate-700 border-slate-300' :
                         (idx === 2 ? 'bg-orange-100 text-orange-800 border-orange-300' : 'bg-slate-100 text-slate-500 border-slate-200'));

      const div = document.createElement('div');
      div.className = 'flex items-center justify-between p-2.5 rounded-xl bg-slate-50/80 hover:bg-slate-100/70 border border-slate-100/90 transition-colors';
      div.innerHTML = `
        <div class="flex items-center gap-3">
          <div class="w-6 h-6 rounded-full ${badgeClass} border flex items-center justify-center font-bold text-[11px] flex-shrink-0">
            ${idx + 1}
          </div>
          <div>
            <div class="flex items-center gap-1.5">
              <span class="w-2 h-2 rounded-full flex-shrink-0" style="background:${deptColor}"></span>
              <p class="text-xs font-bold text-slate-900 truncate max-w-[130px]">${d.department}</p>
            </div>
            <p class="text-[10px] text-slate-500 font-medium">Margin: <b>${(d.margin || 0).toFixed(1)}%</b></p>
          </div>
        </div>
        <div class="text-right flex-shrink-0">
          <p class="text-xs font-bold text-slate-900">${formatCurrency(d.profit)}</p>
          <p class="text-[9px] text-emerald-600 font-semibold">Net Profit</p>
        </div>
      `;
      topContainer.appendChild(div);
    });
  }

  // Load Department Summary & Top Performers
  async function loadDepartmentSummary() {
    try {
      const res = await api.get('/api/v1/pl/departments/summary').catch(() => null);
      if (res && res.departments && res.departments.length > 0) {
        summaryTableData = res.departments.filter(d => d.department && d.department !== 'All Departments' && d.department !== 'Unknown');
        renderSummaryTable();
        renderTopPerformers();
      }
    } catch (err) {
      console.warn('Summary table error:', err);
    }
  }

  // Initial load
  await loadKPIs();
  await loadDepartmentSummary();

  // Global window resize listener
  window.addEventListener('resize', () => {
    deptPerfChart?.resize();
    deptTrendChart?.resize();
  });
}

if (document.readyState === 'loading') {
  document.addEventListener('DOMContentLoaded', initDepartmentsWiring);
} else {
  initDepartmentsWiring();
}

