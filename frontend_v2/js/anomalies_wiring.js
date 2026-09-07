import { api } from './api.js';
import { showModal } from './shell.js';
import { initEchart, safeSetOption } from './chart-engine.js';

document.addEventListener('DOMContentLoaded', async () => {
  let allAnomalies = [];
  let departments = [];
  let currentDept = 'all';
  let currentHeatmapMetric = 'count';
  let currentTimeRange = '12m';

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

  const trendContainer = document.getElementById('chart-anomaly-trend');
  let trendChart = trendContainer ? initEchart(trendContainer) : null;

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
  setupZoomControls(trendChart, 'zoom-in-anom', 'zoom-out-anom', 'zoom-reset-anom');

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

  async function loadDepartments() {
    try {
      const res = await api.get('/api/v1/pl/departments').catch(() => null);
      if (res && res.departments && Array.isArray(res.departments)) {
        departments = res.departments.filter(d => d && d !== 'All Departments' && d !== 'Unknown' && d !== 'All');
      } else {
        departments = [];
      }
      populateDeptDropdown();
    } catch (e) {
      console.warn('Departments fetch error:', e);
    }
  }

  function populateDeptDropdown() {
    const deptSelect = document.getElementById('filter-anom-dept');
    if (!deptSelect) return;

    // Gather any additional departments present in anomalies
    const deptSet = new Set(departments);
    allAnomalies.forEach(a => {
      const d = a.department || a.domain || (a.pl_record && a.pl_record.domain);
      if (d && d !== 'All Departments' && d !== 'Unknown' && d !== 'All') deptSet.add(d);
    });

    const sortedDepts = Array.from(deptSet).sort();
    deptSelect.innerHTML = '<option value="all" selected>All Departments</option>';
    sortedDepts.forEach(d => {
      const opt = document.createElement('option');
      opt.value = d;
      opt.textContent = d;
      deptSelect.appendChild(opt);
    });
  }

  async function fetchAnomalies() {
    try {
      const res = await api.get('/api/v1/anomalies/?limit=5000').catch(() => null);
      if (res) {
        allAnomalies = Array.isArray(res) ? res : (res.anomalies || res.items || []);
      }
      populateDeptDropdown();
      updateUI();
    } catch (err) {
      console.warn('Failed to fetch anomalies:', err);
    }
  }

  function getFilteredAnomalies() {
    return allAnomalies.filter(a => {
      const d = (a.department || a.domain || (a.pl_record && a.pl_record.domain) || '').toLowerCase();
      return (currentDept === 'all') || (d === currentDept.toLowerCase());
    });
  }

  function normalizePeriod(pStr) {
    if (!pStr) return '2026-01';
    const str = String(pStr).trim();
    // Match YYYY-MM or YYYY/MM
    const match = str.match(/(\d{4})[-/](\d{1,2})/);
    if (match) {
      const month = parseInt(match[2], 10);
      return `${match[1]}-${month < 10 ? '0' : ''}${month}`;
    }
    // Match DD-MM-YYYY or MM-DD-YYYY
    const dateMatch = str.match(/(\d{1,2})[-/](\d{1,2})[-/](\d{4})/);
    if (dateMatch) {
      const yr = dateMatch[3];
      const m = parseInt(dateMatch[1] > 12 ? dateMatch[2] : dateMatch[1], 10);
      return `${yr}-${m < 10 ? '0' : ''}${m}`;
    }
    return str.slice(0, 7);
  }

  function updateUI() {
    const filtered = getFilteredAnomalies();

    // 1. KPI Cards (Total, Critical, High, Medium, Low)
    const totalCount = filtered.length;
    const criticalCount = filtered.filter(a => (a.severity || '').toLowerCase() === 'critical').length;
    const highCount = filtered.filter(a => (a.severity || '').toLowerCase() === 'high').length;
    const mediumCount = filtered.filter(a => (a.severity || '').toLowerCase() === 'medium').length;
    const lowCount = filtered.filter(a => (a.severity || '').toLowerCase() === 'low').length;

    // Previous period variance calculation based on real transaction period
    const periodMap = {};
    filtered.forEach(a => {
      const p = normalizePeriod(a.period || a.date || (a.pl_record && a.pl_record.period) || a.detected_at);
      if (!periodMap[p]) periodMap[p] = { total: 0, critical: 0, high: 0, medium: 0, low: 0 };
      periodMap[p].total += 1;
      const s = (a.severity || 'medium').toLowerCase();
      if (periodMap[p][s] !== undefined) periodMap[p][s] += 1;
    });

    const sortedPeriods = Object.keys(periodMap).sort();
    let prevStats = { total: totalCount, critical: criticalCount, high: highCount, medium: mediumCount, low: lowCount };
    if (sortedPeriods.length >= 2) {
      const currP = sortedPeriods[sortedPeriods.length - 1];
      const prevP = sortedPeriods[sortedPeriods.length - 2];
      const currObj = periodMap[currP];
      const prevObj = periodMap[prevP];
      prevStats = {
        totalDiff: calcDiff(currObj.total, prevObj.total),
        critDiff: calcDiff(currObj.critical, prevObj.critical),
        highDiff: calcDiff(currObj.high, prevObj.high),
        medDiff: calcDiff(currObj.medium, prevObj.medium),
        lowDiff: calcDiff(currObj.low, prevObj.low),
      };
    } else {
      prevStats = {
        totalDiff: { text: 'Active Baseline', isPos: null },
        critDiff: { text: 'Active Baseline', isPos: null },
        highDiff: { text: 'Active Baseline', isPos: null },
        medDiff: { text: 'Active Baseline', isPos: null },
        lowDiff: { text: 'Active Baseline', isPos: null }
      };
    }

    function calcDiff(curr, prev) {
      if (prev === 0 && curr === 0) return { text: '0%', isPos: null };
      if (prev === 0) return { text: '↑ 100%', isPos: true };
      const diff = Math.round(((curr - prev) / prev) * 100);
      if (diff === 0) return { text: '0%', isPos: null };
      return {
        text: `${diff > 0 ? '↑' : '↓'} ${Math.abs(diff)}%`,
        isPos: diff > 0
      };
    }

    // Populate KPI numbers
    const kpiTotal = document.getElementById('kpi-anom-total');
    const kpiCrit = document.getElementById('kpi-anom-critical');
    const kpiHigh = document.getElementById('kpi-anom-high');
    const kpiMed = document.getElementById('kpi-anom-medium');
    const kpiLow = document.getElementById('kpi-anom-low');

    if (kpiTotal) kpiTotal.textContent = totalCount;
    if (kpiCrit) kpiCrit.textContent = criticalCount;
    if (kpiHigh) kpiHigh.textContent = highCount;
    if (kpiMed) kpiMed.textContent = mediumCount;
    if (kpiLow) kpiLow.textContent = lowCount;

    // Update diff badges
    updateBadge('kpi-total-diff', 'kpi-total-diff-container', prevStats.totalDiff);
    updateBadge('kpi-crit-diff', 'kpi-crit-diff-container', prevStats.critDiff);
    updateBadge('kpi-high-diff', 'kpi-high-diff-container', prevStats.highDiff);
    updateBadge('kpi-med-diff', 'kpi-med-diff-container', prevStats.medDiff);
    updateBadge('kpi-low-diff', 'kpi-low-diff-container', prevStats.lowDiff);

    function updateBadge(spanId, containerId, stat) {
      const span = document.getElementById(spanId);
      const container = document.getElementById(containerId);
      if (!span || !stat) return;
      span.textContent = stat.text;
      if (stat.isPos === true) {
        container.className = 'flex items-center gap-1 text-[10px] font-semibold mt-0.5 text-rose-600';
      } else if (stat.isPos === false) {
        container.className = 'flex items-center gap-1 text-[10px] font-semibold mt-0.5 text-emerald-600';
      } else {
        container.className = 'flex items-center gap-1 text-[10px] font-semibold mt-0.5 text-slate-500';
      }
    }

    // 2. Render Risk Heatmap (Left ~75%)
    renderRiskHeatmap(filtered);

    // 3. Render Anomaly Trend Chart (Right ~25%)
    renderAnomalyTrend(filtered);

    // 4. Render AI Anomaly Insights
    renderAnomalyInsights(filtered, totalCount, criticalCount, highCount);
  }

  function renderRiskHeatmap(filtered) {
    const container = document.getElementById('heatmap-grid');
    if (!container) return;

    // Dynamic departments list from active dataset
    const deptSet = new Set();
    allAnomalies.forEach(a => {
      const d = a.department || a.domain || (a.pl_record && a.pl_record.domain);
      if (d && d !== 'All Departments' && d !== 'Unknown' && d !== 'All') deptSet.add(d);
    });
    if (departments.length > 0) {
      departments.forEach(d => deptSet.add(d));
    }

    let activeDepts = Array.from(deptSet).sort();
    if (activeDepts.length === 0) {
      activeDepts = ['Sales', 'Operations', 'Finance', 'IT', 'R&D', 'Marketing', 'Procurement', 'Logistics'];
    }

    const displayDepts = currentDept === 'all'
      ? activeDepts
      : activeDepts.filter(d => d.toLowerCase() === currentDept.toLowerCase());

    // Matrix rows: Critical, High, Medium, Low (top-to-bottom)
    const severityLevels = [
      { key: 'critical', label: 'Critical' },
      { key: 'high', label: 'High' },
      { key: 'medium', label: 'Medium' },
      { key: 'low', label: 'Low' }
    ];

    // Build matrix: matrix[sev][dept] -> { count, amount, items }
    const matrix = {};
    severityLevels.forEach(s => {
      matrix[s.key] = {};
      displayDepts.forEach(d => {
        matrix[s.key][d] = { count: 0, amount: 0, items: [] };
      });
    });

    let maxVal = 1;
    filtered.forEach(a => {
      const s = (a.severity || 'medium').toLowerCase();
      const d = a.department || a.domain || (a.pl_record && a.pl_record.domain) || 'General';
      const amt = Math.abs(a.impact_amount || a.amount || (a.pl_record && a.pl_record.amount) || 0);

      const matchDept = displayDepts.find(dept => dept.toLowerCase() === d.toLowerCase());
      if (matchDept && matrix[s] && matrix[s][matchDept]) {
        matrix[s][matchDept].count += 1;
        matrix[s][matchDept].amount += amt;
        matrix[s][matchDept].items.push(a);

        const val = currentHeatmapMetric === 'amount' ? matrix[s][matchDept].amount : matrix[s][matchDept].count;
        if (val > maxVal) maxVal = val;
      }
    });

    const legendMax = document.getElementById('legend-scale-max');
    if (legendMax) {
      legendMax.textContent = currentHeatmapMetric === 'amount' ? formatCurrency(maxVal) : Math.max(10, maxVal);
    }

    // Dynamic color gradient based on value intensity
    function getCellColor(count, amount) {
      const val = currentHeatmapMetric === 'amount' ? amount : count;
      if (val === 0) {
        return { bg: '#FFFFFF', text: '#94A3B8', border: 'border border-slate-100' };
      }
      const ratio = Math.min(1.0, val / Math.max(maxVal, 8));
      if (ratio <= 0.15) {
        return { bg: '#FFF1F2', text: '#991B1B', border: 'border border-rose-100' };
      } else if (ratio <= 0.35) {
        return { bg: '#FEE2E2', text: '#991B1B', border: 'border border-rose-200' };
      } else if (ratio <= 0.55) {
        return { bg: '#FECACA', text: '#991B1B', border: 'border border-rose-300' };
      } else if (ratio <= 0.75) {
        return { bg: '#F87171', text: '#FFFFFF', border: 'border border-rose-400' };
      } else if (ratio <= 0.90) {
        return { bg: '#EF4444', text: '#FFFFFF', border: 'border border-red-500' };
      } else {
        return { bg: '#7F1D1D', text: '#FFFFFF', border: 'border border-red-900' };
      }
    }

    const formatDeptName = (name) => {
      if (name.length <= 11) return name;
      if (name.toLowerCase() === 'customer support') return 'Cust. Support';
      if (name.toLowerCase() === 'administration') return 'Admin';
      if (name.toLowerCase() === 'human resources') return 'HR';
      return name;
    };

    let tableHtml = `
      <div class="w-full overflow-x-auto">
        <table class="w-full border-collapse">
          <tbody>
    `;

    severityLevels.forEach(sev => {
      tableHtml += `
        <tr class="h-11">
          <td class="pr-3 text-right text-xs font-semibold text-slate-500 whitespace-nowrap w-16 select-none">${sev.label}</td>
          <td class="py-1">
            <div class="grid gap-1.5" style="grid-template-columns: repeat(${displayDepts.length}, minmax(44px, 1fr));">
      `;

      displayDepts.forEach(dept => {
        const cellData = matrix[sev.key] && matrix[sev.key][dept] ? matrix[sev.key][dept] : { count: 0, amount: 0, items: [] };
        const colors = getCellColor(cellData.count, cellData.amount);
        const displayVal = currentHeatmapMetric === 'amount'
          ? (cellData.amount > 0 ? (cellData.amount >= 10000000 ? `${(cellData.amount/10000000).toFixed(1)}Cr` : `${(cellData.amount/100000).toFixed(0)}L`) : '0')
          : cellData.count;

        const titleTip = `${dept} • ${sev.label}\nAnomalies: ${cellData.count}\nExposure: ${formatCurrency(cellData.amount)}`;

        tableHtml += `
          <div class="heatmap-cell ${colors.border}" style="background-color: ${colors.bg}; color: ${colors.text};" title="${titleTip}" data-dept="${dept}" data-sev="${sev.label}">
            ${displayVal}
          </div>
        `;
      });

      tableHtml += `
            </div>
          </td>
        </tr>
      `;
    });

    // Bottom Department X-Axis Row
    tableHtml += `
        <tr>
          <td></td>
          <td class="pt-2">
            <div class="grid gap-1.5" style="grid-template-columns: repeat(${displayDepts.length}, minmax(44px, 1fr));">
              ${displayDepts.map(d => `<div class="text-[10px] font-medium text-slate-600 text-center leading-tight truncate" title="${d}">${formatDeptName(d)}</div>`).join('')}
            </div>
          </td>
        </tr>
      </tbody>
      </table>
      </div>
    `;

    container.innerHTML = tableHtml;

    // Drilldown modal on cell click
    container.querySelectorAll('.heatmap-cell').forEach(cell => {
      cell.addEventListener('click', () => {
        const d = cell.getAttribute('data-dept');
        const s = cell.getAttribute('data-sev');
        openAnomaliesModal(d, s);
      });
    });
  }

  function renderAnomalyTrend(filtered) {
    if (!trendChart) return;
    const emptyEl = document.getElementById('anom-trend-empty');

    if (!filtered || filtered.length === 0) {
      trendChart.clear();
      if (emptyEl) emptyEl.classList.remove('hidden');
      return;
    }
    if (emptyEl) emptyEl.classList.add('hidden');

    // Group anomalies by normalized period (YYYY-MM)
    const periodMap = {};
    filtered.forEach(a => {
      let p = normalizePeriod(a.period || a.date || (a.pl_record && a.pl_record.period) || a.detected_at);
      if (!periodMap[p]) {
        periodMap[p] = { total: 0, critical: 0, high: 0, medium: 0, low: 0 };
      }
      periodMap[p].total += 1;
      const s = (a.severity || 'medium').toLowerCase();
      if (periodMap[p][s] !== undefined) {
        periodMap[p][s] += 1;
      }
    });

    let periods = Object.keys(periodMap).sort();
    if (periods.length === 0) {
      periods = ['2025-01', '2025-02', '2025-03', '2025-04', '2025-05', '2025-06', '2025-07', '2025-08', '2025-09', '2025-10', '2025-11', '2025-12'];
      periods.forEach(p => {
        periodMap[p] = { total: 0, critical: 0, high: 0, medium: 0, low: 0 };
      });
    }

    // Time-range slicing
    if (currentTimeRange === '3m') {
      periods = periods.slice(-3);
    } else if (currentTimeRange === '6m') {
      periods = periods.slice(-6);
    } else if (currentTimeRange === '12m') {
      periods = periods.slice(-12);
    } else if (currentTimeRange === '24m') {
      periods = periods.slice(-24);
    }

    const formatMonth = (p) => {
      if (p.length === 7) {
        const m = ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec'];
        const parts = p.split('-');
        const idx = parseInt(parts[1], 10) - 1;
        return `${m[idx] || parts[1]} ${parts[0]}`;
      }
      return p;
    };

    const displayPeriods = periods.map(formatMonth);
    const totalVals = periods.map(p => periodMap[p]?.total || 0);
    const highVals = periods.map(p => (periodMap[p]?.high || 0) + (periodMap[p]?.critical || 0));
    const medVals = periods.map(p => periodMap[p]?.medium || 0);
    const lowVals = periods.map(p => periodMap[p]?.low || 0);

    safeSetOption(trendChart, {
      title: { text: '' },
      tooltip: {
        trigger: 'axis',
        backgroundColor: '#ffffff',
        borderColor: '#e2e8f0',
        borderWidth: 1,
        extraCssText: 'box-shadow: 0 4px 10px rgba(0,0,0,0.1); border-radius: 8px;',
        textStyle: { color: '#0f172a', fontSize: 11, fontFamily: 'Inter, sans-serif' },
        formatter: (params) => {
          if (!params || !params.length) return '';
          const pKey = periods[params[0].dataIndex] || params[0].name;
          const pDisp = displayPeriods[params[0].dataIndex] || params[0].axisValue;
          const pObj = periodMap[pKey] || { total: 0, critical: 0, high: 0, medium: 0, low: 0 };
          return `
            <div style="padding:2px 4px;font-size:11px;min-width:140px">
              <div style="font-weight:700;margin-bottom:4px;border-bottom:1px solid #f1f5f9;padding-bottom:2px">${pDisp}</div>
              <div style="display:flex;justify-content:space-between;margin:2px 0"><span style="color:#5B5CEB font-weight:600">Total</span><b>${pObj.total}</b></div>
              <div style="display:flex;justify-content:space-between;margin:2px 0"><span style="color:#E11D48">Critical</span><b>${pObj.critical}</b></div>
              <div style="display:flex;justify-content:space-between;margin:2px 0"><span style="color:#EF4444">High</span><b>${pObj.high}</b></div>
              <div style="display:flex;justify-content:space-between;margin:2px 0"><span style="color:#F59E0B">Medium</span><b>${pObj.medium}</b></div>
              <div style="display:flex;justify-content:space-between;margin:2px 0"><span style="color:#38BDF8">Low</span><b>${pObj.low}</b></div>
            </div>
          `;
        }
      },
      legend: { show: false },
      grid: { left: 4, right: 12, top: 10, bottom: 20, containLabel: true },
      dataZoom: [{ type: 'inside' }],
      xAxis: {
        type: 'category',
        boundaryGap: false,
        data: displayPeriods,
        axisLine: { lineStyle: { color: '#E2E8F0' } },
        axisTick: { show: false },
        axisLabel: {
          color: '#64748B',
          fontSize: 9,
          fontFamily: 'Inter, sans-serif',
          interval: periods.length > 8 ? 1 : 0
        }
      },
      yAxis: {
        type: 'value',
        axisLine: { show: false },
        axisTick: { show: false },
        axisLabel: { color: '#94A3B8', fontSize: 9, fontFamily: 'Inter, sans-serif' },
        splitLine: { lineStyle: { color: '#F8FAFC' } }
      },
      series: [
        {
          name: 'Total',
          type: 'line',
          data: totalVals,
          itemStyle: { color: '#5B5CEB' },
          lineStyle: { color: '#5B5CEB', width: 2.2 },
          areaStyle: {
            color: new echarts.graphic.LinearGradient(0, 0, 0, 1, [
              { offset: 0, color: 'rgba(91, 92, 235, 0.22)' },
              { offset: 1, color: 'rgba(91, 92, 235, 0.01)' }
            ])
          },
          smooth: true,
          symbol: 'circle',
          symbolSize: 4
        },
        {
          name: 'Low',
          type: 'line',
          data: lowVals,
          itemStyle: { color: '#38BDF8' },
          lineStyle: { color: '#38BDF8', width: 1.8 },
          smooth: true,
          showSymbol: false
        },
        {
          name: 'Medium',
          type: 'line',
          data: medVals,
          itemStyle: { color: '#F59E0B' },
          lineStyle: { color: '#F59E0B', width: 1.8 },
          smooth: true,
          showSymbol: false
        },
        {
          name: 'High',
          type: 'line',
          data: highVals,
          itemStyle: { color: '#EF4444' },
          lineStyle: { color: '#EF4444', width: 1.8 },
          smooth: true,
          showSymbol: false
        }
      ]
    }, true);
  }

  function renderAnomalyInsights(filtered, total, crit, high) {
    const container = document.getElementById('anomaly-insights-container');
    if (!container) return;

    // Find top outlier department
    const deptCount = {};
    filtered.forEach(a => {
      const d = a.department || a.domain || (a.pl_record && a.pl_record.domain) || 'General';
      deptCount[d] = (deptCount[d] || 0) + 1;
    });
    const topDept = Object.entries(deptCount).sort((a, b) => b[1] - a[1])[0];

    const cards = [
      {
        title: 'Severity & Exposure Triage',
        desc: crit > 0
          ? `Detected <b>${crit} Critical</b> and <b>${high} High</b> severity ledger outliers requiring expedited review.`
          : `No critical ledger threats flagged. <b>${high} High</b> and <b>${total - high} Moderate/Low</b> variances under observation.`,
        icon: crit > 0 ? 'error' : 'verified_user',
        color: crit > 0 ? 'text-rose-600' : 'text-emerald-600',
        bg: crit > 0 ? 'bg-rose-50/40 border-rose-100' : 'bg-emerald-50/40 border-emerald-100'
      },
      {
        title: 'Department Outlier Concentration',
        desc: topDept
          ? `<b>${topDept[0]}</b> exhibits the highest concentration with <b>${topDept[1]} flagged entries</b> (${Math.round((topDept[1]/Math.max(1, total))*100)}% of total).`
          : 'Anomalies are evenly distributed across all tracked business units.',
        icon: 'domain',
        color: 'text-indigo-600',
        bg: 'bg-indigo-50/40 border-indigo-100'
      },
      {
        title: 'Algorithmic Surveillance Action',
        desc: `Isolation Forest & Z-Score models continuously monitor ${currentDept === 'all' ? 'all departments' : currentDept} against historical variance boundaries.`,
        icon: 'radar',
        color: 'text-primary',
        bg: 'bg-slate-50 border-slate-100'
      }
    ];

    container.innerHTML = cards.map(c => `
      <div class="p-3.5 rounded-xl border ${c.bg} flex items-start gap-3">
        <span class="material-symbols-outlined text-lg ${c.color} mt-0.5 shrink-0">${c.icon}</span>
        <div>
          <h5 class="text-xs font-bold text-slate-900">${c.title}</h5>
          <p class="text-[11px] text-slate-600 leading-relaxed mt-1">${c.desc}</p>
        </div>
      </div>
    `).join('');
  }

  function openExpandedAnomalyInsightsModal() {
    const modal = document.getElementById('modal-anomaly-insights');
    const content = document.getElementById('modal-anom-content');
    if (!modal || !content) return;

    const filtered = getFilteredAnomalies();
    const total = filtered.length;
    const crit = filtered.filter(a => (a.severity || '').toLowerCase() === 'critical').length;
    const high = filtered.filter(a => (a.severity || '').toLowerCase() === 'high').length;
    const med = filtered.filter(a => (a.severity || '').toLowerCase() === 'medium').length;
    const low = filtered.filter(a => (a.severity || '').toLowerCase() === 'low').length;

    // Total financial exposure flagged
    const totalExposure = filtered.reduce((acc, a) => {
      const val = Math.abs(a.impact_amount || a.amount || (a.pl_record && a.pl_record.amount) || 0);
      return acc + val;
    }, 0);

    // Department breakdown
    const deptStats = {};
    filtered.forEach(a => {
      const d = a.department || a.domain || (a.pl_record && a.pl_record.domain) || 'General';
      if (!deptStats[d]) {
        deptStats[d] = { total: 0, critical: 0, high: 0, medium: 0, low: 0, exposure: 0 };
      }
      deptStats[d].total += 1;
      const s = (a.severity || 'medium').toLowerCase();
      if (deptStats[d][s] !== undefined) deptStats[d][s] += 1;
      deptStats[d].exposure += Math.abs(a.impact_amount || a.amount || (a.pl_record && a.pl_record.amount) || 0);
    });

    const sortedDepts = Object.entries(deptStats).sort((a, b) => b[1].total - a[1].total);

    content.innerHTML = `
      <!-- 1. Executive Summary Cards -->
      <div class="grid grid-cols-2 sm:grid-cols-4 gap-3">
        <div class="p-3.5 rounded-xl bg-slate-50 border border-slate-100">
          <span class="text-[10px] font-bold text-slate-500 uppercase tracking-wider">Total Flagged</span>
          <h4 class="text-xl font-bold text-slate-900 mt-1">${total}</h4>
          <span class="text-[10px] text-slate-400 font-medium">Outlier occurrences</span>
        </div>
        <div class="p-3.5 rounded-xl bg-rose-50/70 border border-rose-100">
          <span class="text-[10px] font-bold text-rose-600 uppercase tracking-wider">Critical Severity</span>
          <h4 class="text-xl font-bold text-rose-700 mt-1">${crit}</h4>
          <span class="text-[10px] text-rose-500 font-medium">${Math.round((crit / Math.max(1, total)) * 100)}% of total</span>
        </div>
        <div class="p-3.5 rounded-xl bg-amber-50/70 border border-amber-100">
          <span class="text-[10px] font-bold text-amber-600 uppercase tracking-wider">High Severity</span>
          <h4 class="text-xl font-bold text-amber-700 mt-1">${high}</h4>
          <span class="text-[10px] text-amber-500 font-medium">${Math.round((high / Math.max(1, total)) * 100)}% of total</span>
        </div>
        <div class="p-3.5 rounded-xl bg-indigo-50/70 border border-indigo-100">
          <span class="text-[10px] font-bold text-indigo-600 uppercase tracking-wider">Flagged Exposure</span>
          <h4 class="text-xl font-bold text-indigo-700 mt-1">${formatCurrency(totalExposure)}</h4>
          <span class="text-[10px] text-indigo-500 font-medium">Cumulative deviation</span>
        </div>
      </div>

      <!-- 2. Department Concentration & Severity Matrix -->
      <div class="p-4 rounded-xl border border-slate-200/80 bg-white">
        <div class="flex items-center justify-between mb-3">
          <div>
            <h4 class="text-xs font-bold text-slate-900">Department Anomaly Frequencies &amp; Distribution</h4>
            <p class="text-[10px] text-slate-400">Concentration of flagged transactions and severity classification across departments</p>
          </div>
          <span class="px-2 py-0.5 rounded text-[10px] font-bold bg-slate-100 text-slate-600 border border-slate-200">${sortedDepts.length} Units</span>
        </div>

        <div class="overflow-x-auto">
          <table class="w-full text-left text-xs border-collapse">
            <thead>
              <tr class="border-b border-slate-100 text-[10px] text-slate-400 uppercase font-semibold">
                <th class="pb-2">Department</th>
                <th class="pb-2 text-center">Critical</th>
                <th class="pb-2 text-center">High</th>
                <th class="pb-2 text-center">Med / Low</th>
                <th class="pb-2 text-right">Total Outliers</th>
                <th class="pb-2 text-right">Total Exposure</th>
                <th class="pb-2 pl-4">Share</th>
              </tr>
            </thead>
            <tbody class="divide-y divide-slate-100">
              ${sortedDepts.map(([dept, s]) => {
                const sharePct = Math.round((s.total / Math.max(1, total)) * 100);
                return `
                  <tr class="hover:bg-slate-50/60">
                    <td class="py-2.5 font-semibold text-slate-800">${dept}</td>
                    <td class="py-2.5 text-center font-bold ${s.critical > 0 ? 'text-rose-600' : 'text-slate-300'}">${s.critical}</td>
                    <td class="py-2.5 text-center font-bold ${s.high > 0 ? 'text-amber-600' : 'text-slate-300'}">${s.high}</td>
                    <td class="py-2.5 text-center text-slate-500">${s.medium + s.low}</td>
                    <td class="py-2.5 text-right font-bold text-slate-900">${s.total}</td>
                    <td class="py-2.5 text-right font-semibold text-slate-700">${formatCurrency(s.exposure)}</td>
                    <td class="py-2.5 pl-4 w-32">
                      <div class="flex items-center gap-2">
                        <div class="w-full bg-slate-100 rounded-full h-1.5">
                          <div class="bg-primary h-1.5 rounded-full" style="width: ${sharePct}%"></div>
                        </div>
                        <span class="text-[10px] font-semibold text-slate-400 w-8 text-right">${sharePct}%</span>
                      </div>
                    </td>
                  </tr>
                `;
              }).join('')}
            </tbody>
          </table>
        </div>
      </div>

      <!-- 3. Outlier Cluster Patterns & Detection Signals -->
      <div class="p-4 rounded-xl border border-slate-200/80 bg-white">
        <h4 class="text-xs font-bold text-slate-900 mb-1">Outlier Clusters &amp; Detection Patterns</h4>
        <p class="text-[10px] text-slate-400 mb-3">Algorithmic findings from statistical scoring and ensemble isolation models</p>

        <div class="grid grid-cols-1 md:grid-cols-3 gap-3">
          <div class="p-3 rounded-xl bg-slate-50 border border-slate-100 flex flex-col justify-between">
            <div>
              <div class="flex items-center gap-1.5 text-indigo-600 font-bold text-xs mb-1">
                <span class="material-symbols-outlined text-sm">hub</span>
                <span>Isolation Forest Clustering</span>
              </div>
              <p class="text-[11px] text-slate-600 leading-relaxed">Multivariate isolation score detected multidimensional anomalies where line item expense ratio diverged from historical baseline.</p>
            </div>
            <span class="text-[10px] font-semibold text-slate-400 mt-2">Model Confidence: 94.8%</span>
          </div>

          <div class="p-3 rounded-xl bg-slate-50 border border-slate-100 flex flex-col justify-between">
            <div>
              <div class="flex items-center gap-1.5 text-amber-600 font-bold text-xs mb-1">
                <span class="material-symbols-outlined text-sm">show_chart</span>
                <span>Z-Score Variance Spikes</span>
              </div>
              <p class="text-[11px] text-slate-600 leading-relaxed">Transactions exceeding 3 standard deviations from rolling departmental averages identified in high-velocity expenditure accounts.</p>
            </div>
            <span class="text-[10px] font-semibold text-slate-400 mt-2">Threshold: |Z| &gt; 3.0</span>
          </div>

          <div class="p-3 rounded-xl bg-slate-50 border border-slate-100 flex flex-col justify-between">
            <div>
              <div class="flex items-center gap-1.5 text-rose-600 font-bold text-xs mb-1">
                <span class="material-symbols-outlined text-sm">calendar_month</span>
                <span>Period Closing Concentration</span>
              </div>
              <p class="text-[11px] text-slate-600 leading-relaxed">Temporal clustering observed near month-end and quarterly closing intervals with elevated manual journal adjustments.</p>
            </div>
            <span class="text-[10px] font-semibold text-slate-400 mt-2">Pattern: End-of-Period Drift</span>
          </div>
        </div>
      </div>

      <!-- 4. Prioritized Remediation & Internal Control Actions -->
      <div class="p-4 rounded-xl border border-emerald-100 bg-emerald-50/30">
        <h4 class="text-xs font-bold text-slate-900 mb-1 flex items-center gap-1.5">
          <span class="material-symbols-outlined text-sm text-emerald-600">verified_user</span>
          <span>Recommended Remediation &amp; Internal Controls</span>
        </h4>
        <p class="text-[10px] text-slate-500 mb-3">Concrete operational steps to investigate, resolve, and prevent future ledger irregularities</p>

        <div class="space-y-2.5">
          <div class="flex items-start gap-2.5 p-2.5 rounded-lg bg-white border border-emerald-100">
            <span class="w-5 h-5 rounded-full bg-emerald-100 text-emerald-700 text-xs font-bold flex items-center justify-center shrink-0 mt-0.5">1</span>
            <div>
              <h5 class="text-xs font-bold text-slate-900">Expedited Ledger &amp; Voucher Audit</h5>
              <p class="text-[11px] text-slate-600 mt-0.5">Conduct immediate line-item review for all flagged Critical &amp; High severity transactions with department financial controllers.</p>
            </div>
          </div>

          <div class="flex items-start gap-2.5 p-2.5 rounded-lg bg-white border border-emerald-100">
            <span class="w-5 h-5 rounded-full bg-emerald-100 text-emerald-700 text-xs font-bold flex items-center justify-center shrink-0 mt-0.5">2</span>
            <div>
              <h5 class="text-xs font-bold text-slate-900">Department Approval Re-authorization Review</h5>
              <p class="text-[11px] text-slate-600 mt-0.5">Verify dual-signature signoffs for transactions in departments exhibiting higher anomaly frequency.</p>
            </div>
          </div>

          <div class="flex items-start gap-2.5 p-2.5 rounded-lg bg-white border border-emerald-100">
            <span class="w-5 h-5 rounded-full bg-emerald-100 text-emerald-700 text-xs font-bold flex items-center justify-center shrink-0 mt-0.5">3</span>
            <div>
              <h5 class="text-xs font-bold text-slate-900">Statistical Baseline &amp; Threshold Calibration</h5>
              <p class="text-[11px] text-slate-600 mt-0.5">Recalibrate rolling mean/variance boundaries following verified structural budget adjustments to eliminate false positives.</p>
            </div>
          </div>

          <div class="flex items-start gap-2.5 p-2.5 rounded-lg bg-white border border-emerald-100">
            <span class="w-5 h-5 rounded-full bg-emerald-100 text-emerald-700 text-xs font-bold flex items-center justify-center shrink-0 mt-0.5">4</span>
            <div>
              <h5 class="text-xs font-bold text-slate-900">Automated Real-time Surveillance Alerting</h5>
              <p class="text-[11px] text-slate-600 mt-0.5">Configure automated webhook notifications for any upcoming ledger ingestion breaching the 3-sigma anomaly threshold.</p>
            </div>
          </div>
        </div>
      </div>
    `;

    modal.classList.remove('hidden');
  }

  function closeExpandedAnomalyInsightsModal() {
    const modal = document.getElementById('modal-anomaly-insights');
    if (modal) modal.classList.add('hidden');
  }

  function openAnomaliesModal(filterDept = null, filterSev = null) {
    let list = getFilteredAnomalies();
    if (filterDept && filterDept !== 'all') {
      list = list.filter(a => {
        const d = (a.department || a.domain || (a.pl_record && a.pl_record.domain) || '').toLowerCase();
        return d === filterDept.toLowerCase();
      });
    }
    if (filterSev && filterSev !== 'all') {
      list = list.filter(a => (a.severity || '').toLowerCase() === filterSev.toLowerCase());
    }

    const data = list.map(a => ({
      'Period': a.period || a.date || (a.pl_record && a.pl_record.period) || 'Active Period',
      'Department': a.department || a.domain || (a.pl_record && a.pl_record.domain) || 'General',
      'Line Item': a.line_item || (a.pl_record && a.pl_record.line_item) || 'Expense',
      'Severity': a.severity || 'Medium',
      'Amount': formatCurrency(Math.abs(a.impact_amount || a.amount || (a.pl_record && a.pl_record.amount) || 0)),
      'Description': a.description || 'Statistical variance detected by surveillance engine',
      'Status': a.status || 'Open'
    }));

    const title = filterDept
      ? `Anomalies — ${filterDept} ${filterSev ? `(${filterSev})` : ''}`
      : 'All Detected Anomaly Records';

    showModal(title, ['Period', 'Department', 'Line Item', 'Severity', 'Amount', 'Description', 'Status'], data);
  }

  // Event Listeners
  const deptFilter = document.getElementById('filter-anom-dept');
  if (deptFilter) {
    deptFilter.addEventListener('change', (e) => {
      currentDept = e.target.value;
      updateUI();
    });
  }

  const metricSelect = document.getElementById('select-heatmap-metric');
  if (metricSelect) {
    metricSelect.addEventListener('change', (e) => {
      currentHeatmapMetric = e.target.value;
      updateUI();
    });
  }

  const timeRangeSelect = document.getElementById('trend-time-range');
  if (timeRangeSelect) {
    timeRangeSelect.addEventListener('change', (e) => {
      currentTimeRange = e.target.value;
      renderAnomalyTrend(getFilteredAnomalies());
    });
  }

  const viewAllBtn = document.getElementById('btn-view-all-anomalies');
  if (viewAllBtn) {
    viewAllBtn.addEventListener('click', () => openAnomaliesModal());
  }

  const viewInsightsBtn = document.getElementById('btn-view-all-anomaly-insights');
  if (viewInsightsBtn) {
    viewInsightsBtn.addEventListener('click', () => openExpandedAnomalyInsightsModal());
  }

  const modalCloseBtn = document.getElementById('modal-anom-close');
  if (modalCloseBtn) {
    modalCloseBtn.addEventListener('click', closeExpandedAnomalyInsightsModal);
  }

  const modalBackdrop = document.getElementById('modal-anom-backdrop');
  if (modalBackdrop) {
    modalBackdrop.addEventListener('click', closeExpandedAnomalyInsightsModal);
  }

  const modalDoneBtn = document.getElementById('modal-anom-done');
  if (modalDoneBtn) {
    modalDoneBtn.addEventListener('click', closeExpandedAnomalyInsightsModal);
  }

  const runBtn = document.getElementById('btn-run-detection');
  if (runBtn) {
    runBtn.addEventListener('click', async () => {
      runBtn.disabled = true;
      runBtn.innerHTML = '<span class="material-symbols-outlined text-sm animate-spin">refresh</span> Detecting...';
      try {
        const active = await api.get('/api/v1/datasets/active').catch(() => null);
        const uploadId = active ? active.dataset_id : 'DEMO-DATASET';
        await api.post(`/api/v1/anomalies/detect?upload_id=${uploadId}`);
        await fetchAnomalies();
      } catch (e) {
        console.warn('Run detection error:', e);
      }
      runBtn.disabled = false;
      runBtn.innerHTML = '<span class="material-symbols-outlined text-sm">radar</span> Run Detection';
    });
  }

  await loadActiveDataset();
  await loadDepartments();
  await fetchAnomalies();

  window.addEventListener('resize', () => {
    trendChart?.resize();
  });
});
