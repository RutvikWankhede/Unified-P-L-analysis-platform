/**
 * reports.js - Enterprise Financial Reporting Suite & Decision Support
 * ====================================================================
 * Powers:
 * - Dynamic generation of 10 canonical enterprise report types
 * - Group aggregation filtering (Commercial, Technology, Operations, Corporate)
 * - Live KPI calculations grounded in the active dataset
 * - Specialized visual components per report type (Forecast, Anomaly, What-If, Budget, Cash Flow, etc.)
 * - Rich Management Recommendations (Issue -> Evidence -> Business Impact -> Action -> Priority)
 * - Genuine multi-format download flows (PDF, Excel .xlsx, CSV)
 * - Persistent Report History audit log
 */

import { api } from './api.js';
import { initEchart, safeSetOption, formatCurrency } from './chart-engine.js';

let cachedReportData = null;
let activeCharts = {};
let reportHistory = [];

const formatShort = (val) => {
  if (val === null || val === undefined || isNaN(val)) return '₹0';
  const abs = Math.abs(val);
  const sign = val < 0 ? '-' : '';
  if (abs >= 1000000000) return `${sign}₹${(abs / 1000000000).toFixed(2)} B`;
  if (abs >= 10000000) return `${sign}₹${(abs / 10000000).toFixed(2)} Cr`;
  if (abs >= 100000) return `${sign}₹${(abs / 100000).toFixed(2)} L`;
  if (abs >= 1000) return `${sign}₹${(abs / 1000).toFixed(1)} K`;
  return `${sign}₹${abs.toLocaleString('en-IN')}`;
};

// ── History Management ──────────────────────────────────────────
function loadHistory() {
  try {
    const stored = localStorage.getItem('unified_pl_report_history');
    if (stored) {
      reportHistory = JSON.parse(stored);
    } else {
      reportHistory = [];
    }
  } catch (e) {
    reportHistory = [];
  }
  renderHistoryTable();
}

function addHistoryEntry(title, type, dataset, scope, format) {
  const entry = {
    id: 'REP-' + Date.now().toString().slice(-6),
    title: title || 'Financial Report',
    type: type || 'Overall',
    dataset: dataset || 'Active Dataset',
    scope: scope || 'All Departments',
    generated: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }),
    user: 'Financial Controller',
    format: (format || 'PDF').toUpperCase(),
    status: 'Ready',
    timestamp: Date.now()
  };
  reportHistory.unshift(entry);
  if (reportHistory.length > 20) reportHistory.pop();
  try {
    localStorage.setItem('unified_pl_report_history', JSON.stringify(reportHistory));
  } catch (e) {}
  renderHistoryTable();
}

function renderHistoryTable() {
  const tbody = document.getElementById('history-table-body');
  if (!tbody) return;

  if (reportHistory.length === 0) {
    tbody.innerHTML = `
      <tr>
        <td colspan="9" class="px-4 py-8 text-center text-slate-400">
          <span class="material-symbols-outlined text-2xl text-slate-300 block mb-1">history_toggle_off</span>
          No reports generated in this session yet. Click "Generate Report" or export a report to log history.
        </td>
      </tr>
    `;
    return;
  }

  tbody.innerHTML = reportHistory.map(h => {
    const fmtColor = h.format === 'PDF' ? 'bg-rose-50 text-rose-600 border-rose-100' :
                     h.format === 'EXCEL' || h.format === 'XLSX' ? 'bg-emerald-50 text-emerald-600 border-emerald-100' :
                     'bg-blue-50 text-blue-600 border-blue-100';
    return `
      <tr class="hover:bg-slate-50/80 transition-colors">
        <td class="px-4 py-3 font-semibold text-slate-900">${h.title}</td>
        <td class="px-4 py-3 text-slate-600">${h.type}</td>
        <td class="px-4 py-3 text-slate-500 font-mono text-[11px]">${h.dataset}</td>
        <td class="px-4 py-3 text-slate-700">${h.scope}</td>
        <td class="px-4 py-3 text-slate-500">${h.generated}</td>
        <td class="px-4 py-3 text-slate-600">${h.user}</td>
        <td class="px-4 py-3 text-center">
          <span class="inline-block px-2 py-0.5 rounded text-[10px] font-bold border ${fmtColor}">${h.format}</span>
        </td>
        <td class="px-4 py-3 text-center">
          <span class="inline-flex items-center gap-1 text-[10px] font-semibold text-emerald-600">
            <span class="w-1.5 h-1.5 rounded-full bg-emerald-500"></span> Ready
          </span>
        </td>
        <td class="px-4 py-3 text-center">
          <button class="btn-download-history text-primary hover:text-indigo-800 text-xs font-semibold inline-flex items-center gap-1 cursor-pointer" data-id="${h.id}" data-format="${h.format.toLowerCase()}">
            <span class="material-symbols-outlined text-sm">download</span> Download
          </button>
        </td>
      </tr>
    `;
  }).join('');

  tbody.querySelectorAll('.btn-download-history').forEach(btn => {
    btn.addEventListener('click', () => {
      const fmt = btn.getAttribute('data-format') || 'pdf';
      downloadCurrentReport(fmt);
    });
  });
}

// ── Toast Notification Helper ──────────────────────────────────
function showToast(message, type = 'success') {
  let toast = document.getElementById('report-toast');
  if (!toast) {
    toast = document.createElement('div');
    toast.id = 'report-toast';
    toast.className = 'fixed bottom-6 right-6 z-50 flex items-center gap-2.5 px-4 py-3 rounded-xl shadow-xl text-xs font-semibold transition-all transform duration-300 opacity-0 translate-y-4';
    document.body.appendChild(toast);
  }
  const bgClass = type === 'success' ? 'bg-slate-900 text-white border border-slate-700' :
                  type === 'error' ? 'bg-rose-900 text-white border border-rose-700' :
                  'bg-blue-900 text-white border border-blue-700';
  const icon = type === 'success' ? 'check_circle' : (type === 'error' ? 'error' : 'info');
  const iconColor = type === 'success' ? 'text-emerald-400' : (type === 'error' ? 'text-rose-400' : 'text-blue-400');
  toast.className = `fixed bottom-6 right-6 z-50 flex items-center gap-2.5 px-4 py-3 rounded-xl shadow-xl text-xs font-semibold transition-all transform duration-300 ${bgClass}`;
  toast.innerHTML = `<span class="material-symbols-outlined text-base ${iconColor}">${icon}</span><span>${message}</span>`;
  
  setTimeout(() => {
    toast.classList.remove('opacity-0', 'translate-y-4');
    toast.classList.add('opacity-100', 'translate-y-0');
  }, 10);

  setTimeout(() => {
    toast.classList.remove('opacity-100', 'translate-y-0');
    toast.classList.add('opacity-0', 'translate-y-4');
  }, 3500);
}

// ── Filter Initialization ───────────────────────────────────────
async function initFilters() {
  try {
    const active = await api.get('/api/v1/datasets/active').catch(() => null);
    if (active && (active.filename || active.name)) {
      const name = active.filename ? active.filename.replace('.csv', '').replace('.xlsx', '') : (active.name || 'Active Dataset');
      const pill = document.getElementById('active-dataset-pill');
      if (pill) pill.textContent = name;
      const metaDataset = document.getElementById('preview-meta-dataset');
      if (metaDataset) metaDataset.textContent = name;
    }

    const deptsRes = await api.get('/api/v1/pl/departments').catch(() => null);
    const deptSelect = document.getElementById('report-dept-select');
    if (deptSelect && deptsRes && deptsRes.departments) {
      const currVal = deptSelect.value;
      let html = '<option value="all" selected>All Departments</option>';
      
      html += '<optgroup label="Department Groups / Aggregations">';
      html += '<option value="Commercial">Commercial (Sales & Marketing)</option>';
      html += '<option value="Technology">Technology (IT & R&D)</option>';
      html += '<option value="Operations">Operations (Logistics & Procurement)</option>';
      html += '<option value="Corporate">Corporate / G&A</option>';
      html += '</optgroup>';

      html += '<optgroup label="Specific Operating Units">';
      deptsRes.departments.forEach(d => {
        if (d && d !== 'All Departments' && d !== 'Unknown' && d !== 'All') {
          html += `<option value="${d}">${d}</option>`;
        }
      });
      html += '</optgroup>';

      deptSelect.innerHTML = html;
      if (currVal && Array.from(deptSelect.options).some(o => o.value === currVal)) {
        deptSelect.value = currVal;
      }
    }

    // Check URL parameters
    const urlParams = new URLSearchParams(window.location.search);
    const typeParam = urlParams.get('type') || urlParams.get('report_type');
    const deptParam = urlParams.get('dept');
    const periodParam = urlParams.get('period');

    if (typeParam) {
      const typeSelect = document.getElementById('report-type-select');
      if (typeSelect && Array.from(typeSelect.options).some(o => o.value.toLowerCase() === typeParam.toLowerCase())) {
        typeSelect.value = typeParam.toLowerCase();
      }
    }
    if (deptParam && deptSelect) {
      if (Array.from(deptSelect.options).some(o => o.value.toLowerCase() === deptParam.toLowerCase())) {
        deptSelect.value = deptParam;
      }
    }
    if (periodParam) {
      const periodSelect = document.getElementById('report-period-select');
      if (periodSelect) periodSelect.value = periodParam;
    }

  } catch (e) {
    console.warn('Filter initialization error:', e);
  }
}

// ── Download Handling ───────────────────────────────────────────
async function downloadCurrentReport(format) {
  const reportType = document.getElementById('report-type-select')?.value || 'overall';
  const dept = document.getElementById('report-dept-select')?.value || 'all';
  const period = document.getElementById('report-period-select')?.value || 'all';
  const agg = 'monthly';
  const fmt = format.toLowerCase();

  const today = new Date().toISOString().split('T')[0];
  const typeFormatted = reportType.replace(/_/g, ' ').replace(/\b\w/g, c => c.toUpperCase()).replace(/\s+/g, '_');
  const ext = (fmt === 'excel' || fmt === 'xlsx') ? 'xlsx' : fmt;
  const fileName = `Unified_PnL_${typeFormatted}_Report_${today}.${ext}`;

  const endpoint = `/api/v1/reports/${fmt}?report_type=${encodeURIComponent(reportType)}&dept=${encodeURIComponent(dept)}&period=${encodeURIComponent(period)}&agg=${encodeURIComponent(agg)}`;

  showToast(`Preparing ${fmt.toUpperCase()} download...`, 'info');

  try {
    const token = (api && typeof api.getAccessToken === 'function') ? api.getAccessToken() : (sessionStorage.getItem('pl_access_token') || localStorage.getItem('pl_access_token'));
    const headers = {};
    if (token) headers['Authorization'] = `Bearer ${token}`;

    const apiBase = (typeof window.__API_BASE__ !== 'undefined' && window.__API_BASE__ !== null)
      ? window.__API_BASE__
      : (
        (window.location.port === '3000' || window.location.port === '80' || !window.location.port)
          ? ''
          : (window.location.hostname === 'localhost' || window.location.hostname === '127.0.0.1' ? `${window.location.protocol}//${window.location.hostname}:8000` : '')
      );
    const fullUrl = `${apiBase}${endpoint}`;

    const response = await fetch(fullUrl, { headers });
    if (!response.ok) {
      let errDetail = `HTTP ${response.status}`;
      try {
        const jsonErr = await response.json();
        if (jsonErr.detail) errDetail = jsonErr.detail;
      } catch (_) {}
      throw new Error(errDetail);
    }

    const blob = await response.blob();
    const downloadUrl = window.URL.createObjectURL(blob);
    const link = document.createElement('a');
    link.href = downloadUrl;
    link.download = fileName;
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
    window.URL.revokeObjectURL(downloadUrl);

    // Record in audit log history
    const datasetName = document.getElementById('preview-meta-dataset')?.textContent || 'Active Dataset';
    const title = cachedReportData ? cachedReportData.title : `${typeFormatted} Financial Report`;
    addHistoryEntry(title, typeFormatted, datasetName, dept === 'all' ? 'All Departments' : dept, fmt);
    showToast(`${fmt.toUpperCase()} report downloaded successfully!`, 'success');
  } catch (err) {
    console.error('Report download error:', err);
    showToast(`Report download failed: ${err.message || 'Server error'}`, 'error');
  }
}

// ── Load & Render Main Report ───────────────────────────────────
async function loadReport(showFeedback = false) {
  const reportType = document.getElementById('report-type-select')?.value || 'overall';
  const dept = document.getElementById('report-dept-select')?.value || 'all';
  const period = document.getElementById('report-period-select')?.value || 'all';
  const generateBtn = document.getElementById('btn-generate-report');
  const generateIcon = document.getElementById('generate-icon');

  if (generateBtn) {
    generateBtn.disabled = true;
    generateBtn.classList.add('opacity-75', 'cursor-wait');
    const btnSpan = generateBtn.querySelector('span:not(.material-symbols-outlined)');
    if (btnSpan) btnSpan.textContent = 'Generating report...';
  }
  if (generateIcon) {
    generateIcon.textContent = 'progress_activity';
    generateIcon.classList.add('animate-spin');
  }

  try {
    const res = await api.get(`/api/v1/reports/data?report_type=${encodeURIComponent(reportType)}&dept=${encodeURIComponent(dept)}&period=${encodeURIComponent(period)}&agg=monthly`);
    if (!res) throw new Error('No data received from backend reporting service');
    cachedReportData = res;

    // 1. Update Periods list in dropdown if needed
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

    // 2. Render Meta Header Banner
    renderMetaBanner(res);

    // 3. Render 6 KPI Summary Cards
    renderSummaryKpis(res.kpis);

    // 4. Render Dynamic View based on Report Type
    renderDynamicReportView(res);

    // 5. Render Observations & Recommendations
    renderInsightsAndRecommendations(res.management_insights || res.management_insights_ranked || [], res.recommendations || res.action_plan_matrix || []);

    if (showFeedback) {
      const datasetName = document.getElementById('preview-meta-dataset')?.textContent || 'Active Dataset';
      const title = res.title || `${reportType.toUpperCase()} Financial Report`;
      const scopeText = dept === 'all' ? 'All Departments' : dept;
      addHistoryEntry(title, res.report_key || reportType, datasetName, scopeText, 'PDF');
      showToast('Report generated and added to History!', 'success');

      if (generateBtn) {
        const btnSpan = generateBtn.querySelector('span:not(.material-symbols-outlined)');
        if (btnSpan) btnSpan.textContent = 'Report Generated!';
        setTimeout(() => {
          if (btnSpan) btnSpan.textContent = 'Generate Report';
        }, 1800);
      }
    }

  } catch (err) {
    console.error('Failed to load report data:', err);
    showToast(`Report generation failed: ${err.message || 'Unable to process dataset'}`, 'error');
  } finally {
    if (generateBtn) {
      generateBtn.disabled = false;
      generateBtn.classList.remove('opacity-75', 'cursor-wait');
      const btnSpan = generateBtn.querySelector('span:not(.material-symbols-outlined)');
      if (btnSpan && (!showFeedback || btnSpan.textContent === 'Generating report...')) {
        btnSpan.textContent = 'Generate Report';
      }
    }
    if (generateIcon) {
      generateIcon.textContent = 'play_arrow';
      generateIcon.classList.remove('animate-spin');
    }
  }
}

// ── Meta Header Banner ──────────────────────────────────────────
function renderMetaBanner(res) {
  const titleEl = document.getElementById('preview-report-title');
  const descEl = document.getElementById('preview-report-desc');
  const badgeEl = document.getElementById('preview-report-type-badge');
  const metaDataset = document.getElementById('preview-meta-dataset');
  const metaDept = document.getElementById('preview-meta-dept');
  const metaPeriod = document.getElementById('preview-meta-period');
  const metaGen = document.getElementById('preview-meta-generated');

  if (titleEl) titleEl.textContent = res.title || 'Enterprise Financial Report';
  if (descEl) descEl.textContent = res.description || 'Comprehensive financial performance analysis';
  if (badgeEl) badgeEl.textContent = res.report_type || 'Report';
  if (metaDataset) metaDataset.textContent = res.dataset_name || 'Active Dataset';
  if (metaDept) metaDept.textContent = res.active_filters?.dept === 'all' ? 'All Departments' : res.active_filters?.dept;
  if (metaPeriod) metaPeriod.textContent = res.active_filters?.period === 'all' ? 'All Periods' : res.active_filters?.period;
  if (metaGen) metaGen.textContent = res.generated_at || 'Just Now';
}

// ── 6 KPI Summary Cards ─────────────────────────────────────────
function renderSummaryKpis(kpis) {
  if (!kpis) return;

  const revEl = document.getElementById('kpi-total-revenue');
  const expEl = document.getElementById('kpi-total-expense');
  const profEl = document.getElementById('kpi-net-profit');
  const marginEl = document.getElementById('kpi-net-margin');
  const deptCountEl = document.getElementById('kpi-dept-count');
  const anomCountEl = document.getElementById('kpi-anomalies-count');

  const totalRev = Number(kpis.total_revenue ?? kpis.revenue ?? 0);
  const totalExp = Number(kpis.total_expense ?? kpis.expense ?? 0);
  const netProf = Number(kpis.net_profit ?? kpis.profit ?? kpis.total_profit ?? (totalRev - totalExp));
  const netMargin = Number(kpis.net_margin ?? kpis.margin ?? (totalRev > 0 ? (netProf / totalRev * 100) : 0));
  const depts = Number(kpis.tracked_departments ?? kpis.department_count ?? kpis.departments ?? 0);
  const anoms = Number(kpis.total_anomalies ?? kpis.anomalies ?? 0);

  if (revEl) revEl.textContent = formatCurrency(totalRev);
  if (expEl) expEl.textContent = formatCurrency(totalExp);
  if (profEl) {
    profEl.textContent = formatCurrency(netProf);
    profEl.className = `text-lg font-bold tracking-tight ${netProf >= 0 ? 'text-emerald-600' : 'text-rose-600'}`;
  }
  if (marginEl) {
    marginEl.textContent = `${netMargin.toFixed(1)}%`;
    marginEl.className = `text-lg font-bold tracking-tight ${netMargin >= 0 ? 'text-slate-900' : 'text-rose-600'}`;
  }
  if (deptCountEl) deptCountEl.textContent = depts;
  if (anomCountEl) anomCountEl.textContent = anoms;
}

// ── Dynamic Report View Rendering ───────────────────────────────
function renderDynamicReportView(res) {
  const container = document.getElementById('dynamic-report-view-container');
  if (!container) return;

  const rKey = (res.report_key || 'overall').toLowerCase();

  // 1. ANOMALY REPORT VIEW
  if (rKey === 'anomaly') {
    renderAnomalyReportView(container, res);
  }
  // 2. FORECAST REPORT VIEW
  else if (rKey === 'forecast') {
    renderForecastReportView(container, res);
  }
  // 3. WHAT-IF / SCENARIO REPORT VIEW
  else if (rKey === 'whatif' || rKey === 'scenario') {
    renderWhatIfReportView(container, res);
  }
  // 4. BUDGET VS ACTUAL REPORT VIEW
  else if (rKey === 'budget' || rKey === 'variance') {
    renderBudgetReportView(container, res);
  }
  // 5. DEPARTMENT PERFORMANCE REPORT VIEW
  else if (rKey === 'department') {
    renderDepartmentReportView(container, res);
  }
  // 6. CASH FLOW REPORT VIEW
  else if (rKey === 'cashflow') {
    renderCashFlowReportView(container, res);
  }
  // 7. REVENUE & EXPENSE REPORT VIEW
  else if (rKey === 'revenue_expense' || rKey === 'rev_exp') {
    renderRevenueExpenseReportView(container, res);
  }
  // 8. EXECUTIVE SUMMARY VIEW
  else if (rKey === 'executive') {
    renderExecutiveReportView(container, res);
  }
  // 9. OVERALL / P&L REPORT VIEW (DEFAULT)
  else {
    renderOverallReportView(container, res);
  }
}

// ────────────────────────────────────────────────────────────────
// VIEW 1: ANOMALY REPORT
// ────────────────────────────────────────────────────────────────
function renderAnomalyReportView(container, res) {
  const spec = res.report_specific || res.risk_intelligence || {};
  const tableData = res.table_data || [];

  let html = `
    <!-- Anomaly Severity Breakdown Cards -->
    <section class="grid grid-cols-2 sm:grid-cols-4 gap-3.5">
      <div class="dash-card custom-shadow border-l-4 border-l-rose-600">
        <div class="text-[10px] uppercase font-bold text-slate-400">Critical Severity</div>
        <div class="text-2xl font-bold text-rose-600 mt-1">${spec.critical || spec.critical_count || 0}</div>
        <div class="text-[11px] text-slate-500 mt-0.5">High financial impact outliers</div>
      </div>
      <div class="dash-card custom-shadow border-l-4 border-l-orange-500">
        <div class="text-[10px] uppercase font-bold text-slate-400">High Severity</div>
        <div class="text-2xl font-bold text-orange-600 mt-1">${spec.high || spec.high_count || 0}</div>
        <div class="text-[11px] text-slate-500 mt-0.5">Priority variance breach</div>
      </div>
      <div class="dash-card custom-shadow border-l-4 border-l-amber-400">
        <div class="text-[10px] uppercase font-bold text-slate-400">Medium Severity</div>
        <div class="text-2xl font-bold text-amber-600 mt-1">${spec.medium || spec.medium_count || 0}</div>
        <div class="text-[11px] text-slate-500 mt-0.5">Statistical drift flagged</div>
      </div>
      <div class="dash-card custom-shadow border-l-4 border-l-sky-400">
        <div class="text-[10px] uppercase font-bold text-slate-400">Low Severity</div>
        <div class="text-2xl font-bold text-sky-600 mt-1">${spec.low || spec.low_count || 0}</div>
        <div class="text-[11px] text-slate-500 mt-0.5">Minor variance notices</div>
      </div>
    </section>

    <!-- Anomaly Data Table -->
    <section class="dash-card custom-shadow">
      <div class="flex items-center justify-between pb-3 mb-3 border-b border-slate-100">
        <div>
          <h3 class="text-sm font-bold text-slate-900">Flagged Anomaly Ledger Details</h3>
          <p class="text-[11px] text-slate-500 mt-0.5">Machine learning surveillance outliers requiring operational signoff</p>
        </div>
        <span class="text-xs text-slate-500 font-semibold">${tableData.length} records flagged</span>
      </div>

      <div class="overflow-x-auto border border-slate-200 rounded-xl custom-scroll">
        <table class="w-full text-left border-collapse text-xs">
          <thead>
            <tr class="text-[10px] uppercase tracking-wider text-slate-500 border-b border-slate-200 bg-slate-50/80">
              <th class="px-4 py-3 font-bold">Period</th>
              <th class="px-4 py-3 font-bold">Department</th>
              <th class="px-4 py-3 font-bold">Line Item</th>
              <th class="px-4 py-3 font-bold text-center">Severity</th>
              <th class="px-4 py-3 font-bold text-right">Impact Amount</th>
              <th class="px-4 py-3 font-bold">Surveillance Reason</th>
              <th class="px-4 py-3 font-bold text-center">Status</th>
            </tr>
          </thead>
          <tbody class="divide-y divide-slate-100 text-slate-700 bg-white">
            ${tableData.length > 0 ? tableData.map(r => {
              const s = (r.severity || 'medium').toLowerCase();
              const badge = s === 'critical' ? 'bg-rose-100 text-rose-800' :
                            s === 'high' ? 'bg-orange-100 text-orange-800' :
                            s === 'medium' ? 'bg-amber-100 text-amber-800' :
                            'bg-sky-100 text-sky-800';
              return `
                <tr class="hover:bg-slate-50/80">
                  <td class="px-4 py-3 font-mono text-[11px] text-slate-600">${r.period}</td>
                  <td class="px-4 py-3 font-semibold text-slate-900">${r.department}</td>
                  <td class="px-4 py-3 text-slate-700">${r.line_item}</td>
                  <td class="px-4 py-3 text-center"><span class="px-2 py-0.5 rounded text-[10px] font-bold ${badge}">${r.severity}</span></td>
                  <td class="px-4 py-3 text-right font-bold text-slate-900">${formatCurrency(r.amount || r.impact_amount)}</td>
                  <td class="px-4 py-3 text-slate-500 text-[11px] max-w-xs truncate" title="${r.description}">${r.description}</td>
                  <td class="px-4 py-3 text-center"><span class="text-[10px] font-semibold text-slate-600 bg-slate-100 px-2 py-0.5 rounded">${r.status}</span></td>
                </tr>
              `;
            }).join('') : `
              <tr>
                <td colspan="7" class="px-4 py-8 text-center text-slate-400">
                  No anomaly records found for the selected scope.
                </td>
              </tr>
            `}
          </tbody>
        </table>
      </div>
    </section>
  `;

  container.innerHTML = html;
}

// ────────────────────────────────────────────────────────────────
// VIEW 2: FORECAST REPORT
// ────────────────────────────────────────────────────────────────
function renderForecastReportView(container, res) {
  const spec = res.report_specific || res.forecast_and_outlook || {};
  const scen = spec.scenarios || {};

  let html = `
    <!-- Forecast Baseline & Projections -->
    <section class="grid grid-cols-1 md:grid-cols-3 gap-4">
      <div class="dash-card custom-shadow bg-gradient-to-br from-white to-blue-50/30">
        <div class="flex items-center justify-between">
          <span class="text-[10px] uppercase font-bold text-slate-400">Forecasted Revenue</span>
          <span class="text-xs font-bold text-blue-600 bg-blue-50 px-2 py-0.5 rounded">${scen.expected?.growth || '+8.0%'}</span>
        </div>
        <div class="text-2xl font-bold text-slate-900 mt-2">${formatCurrency(spec.forecast_revenue || spec.projected_revenue || 0)}</div>
        <div class="text-[11px] text-slate-500 mt-1">Baseline: ${formatCurrency(spec.baseline_revenue || 0)}</div>
      </div>

      <div class="dash-card custom-shadow bg-gradient-to-br from-white to-emerald-50/30">
        <div class="flex items-center justify-between">
          <span class="text-[10px] uppercase font-bold text-slate-400">Forecasted Net Profit</span>
          <span class="text-xs font-bold text-emerald-600 bg-emerald-50 px-2 py-0.5 rounded">Expanded</span>
        </div>
        <div class="text-2xl font-bold text-emerald-600 mt-2">${formatCurrency(spec.forecast_profit || spec.projected_profit || 0)}</div>
        <div class="text-[11px] text-slate-500 mt-1">Baseline: ${formatCurrency(spec.baseline_profit || 0)}</div>
      </div>

      <div class="dash-card custom-shadow">
        <div class="text-[10px] uppercase font-bold text-slate-400">Model Confidence & Horizon</div>
        <div class="text-2xl font-bold text-primary mt-2">${spec.confidence_score || 95.0}%</div>
        <div class="text-[11px] text-slate-500 mt-1">${spec.horizon || 'Next 4 Quarters'}  *  ${spec.model_name || 'Ensemble Model'}</div>
      </div>
    </section>

    <!-- Scenario Projection Bands -->
    <section class="dash-card custom-shadow">
      <h3 class="text-sm font-bold text-slate-900 mb-3 pb-2 border-b border-slate-100">Scenario Projection Bands</h3>
      <div class="grid grid-cols-1 md:grid-cols-3 gap-4">
        <div class="p-4 rounded-xl border border-emerald-100 bg-emerald-50/20">
          <div class="text-xs font-bold text-emerald-800">Best Case Scenario</div>
          <div class="text-lg font-bold text-slate-900 mt-1">${formatCurrency(scen.best_case?.revenue || 0)}</div>
          <div class="text-[11px] text-emerald-700 mt-0.5">Net Profit: ${formatCurrency(scen.best_case?.profit || 0)} (${scen.best_case?.growth || '+18.8%'})</div>
        </div>

        <div class="p-4 rounded-xl border border-blue-100 bg-blue-50/20">
          <div class="text-xs font-bold text-blue-800">Expected Base Forecast</div>
          <div class="text-lg font-bold text-slate-900 mt-1">${formatCurrency(scen.expected?.revenue || 0)}</div>
          <div class="text-[11px] text-blue-700 mt-0.5">Net Profit: ${formatCurrency(scen.expected?.profit || 0)} (${scen.expected?.growth || '+8.0%'})</div>
        </div>

        <div class="p-4 rounded-xl border border-rose-100 bg-rose-50/20">
          <div class="text-xs font-bold text-rose-800">Worst Case Stress Floor</div>
          <div class="text-lg font-bold text-slate-900 mt-1">${formatCurrency(scen.worst_case?.revenue || 0)}</div>
          <div class="text-[11px] text-rose-700 mt-0.5">Net Profit: ${formatCurrency(scen.worst_case?.profit || 0)} (${scen.worst_case?.growth || '-0.6%'})</div>
        </div>
      </div>
    </section>
  `;

  container.innerHTML = html;
}

// ────────────────────────────────────────────────────────────────
// VIEW 3: WHAT-IF / SCENARIO REPORT
// ────────────────────────────────────────────────────────────────
function renderWhatIfReportView(container, res) {
  const spec = res.report_specific || res.whatif_opportunities || {};
  const base = spec.base_case || {};
  const sim = spec.simulated_case || {};

  let html = `
    <!-- Simulated vs Actual Banner -->
    <section class="p-3 bg-amber-50 border border-amber-200 rounded-xl text-xs text-amber-900 flex items-center gap-2">
      <span class="material-symbols-outlined text-amber-600 text-base">science</span>
      <div><b>Simulation Notice:</b> The metrics below represent stress-tested mathematical simulations based on <i>${sim.assumptions || '+10% Revenue Expansion, +5% OPEX Adjustment'}</i> and are strictly separate from audited historical actuals.</div>
    </section>

    <!-- Side-by-Side Comparison -->
    <section class="grid grid-cols-1 md:grid-cols-2 gap-4">
      <!-- Base Case -->
      <div class="dash-card custom-shadow border-slate-200">
        <div class="text-xs font-bold text-slate-500 uppercase tracking-wider">Base Case (Audited Baseline)</div>
        <div class="mt-3 space-y-2 text-xs">
          <div class="flex justify-between py-1 border-b border-slate-100"><span>Revenue:</span><b>${formatCurrency(base.revenue || 0)}</b></div>
          <div class="flex justify-between py-1 border-b border-slate-100"><span>Expense:</span><b>${formatCurrency(base.expense || 0)}</b></div>
          <div class="flex justify-between py-1 border-b border-slate-100"><span>Net Profit:</span><b class="text-emerald-600">${formatCurrency(base.profit || 0)}</b></div>
          <div class="flex justify-between py-1"><span>Margin:</span><b>${(base.margin || 0).toFixed(1)}%</b></div>
        </div>
      </div>

      <!-- Simulated Case -->
      <div class="dash-card custom-shadow border-indigo-200 bg-indigo-50/10">
        <div class="flex justify-between items-center">
          <div class="text-xs font-bold text-primary uppercase tracking-wider">Simulated Outcome</div>
          <span class="text-[10px] font-bold text-emerald-600 bg-emerald-50 px-2 py-0.5 rounded">+${formatCurrency(sim.profit_delta || 0)} Profit</span>
        </div>
        <div class="mt-3 space-y-2 text-xs">
          <div class="flex justify-between py-1 border-b border-indigo-100/50"><span>Simulated Revenue:</span><b>${formatCurrency(sim.revenue || 0)}</b></div>
          <div class="flex justify-between py-1 border-b border-indigo-100/50"><span>Simulated Expense:</span><b>${formatCurrency(sim.expense || 0)}</b></div>
          <div class="flex justify-between py-1 border-b border-indigo-100/50"><span>Simulated Net Profit:</span><b class="text-emerald-600">${formatCurrency(sim.profit || 0)}</b></div>
          <div class="flex justify-between py-1"><span>Simulated Margin:</span><b class="text-primary">${(sim.margin || 0).toFixed(1)}%</b></div>
        </div>
      </div>
    </section>
  `;

  container.innerHTML = html;
}

// ────────────────────────────────────────────────────────────────
// VIEW 4: BUDGET VS ACTUAL REPORT
// ────────────────────────────────────────────────────────────────
function renderBudgetReportView(container, res) {
  const spec = res.report_specific || res.budget_vs_actual || {};
  const depts = res.department_performance || [];

  let html = `
    <!-- Budget Summary KPIs -->
    <section class="grid grid-cols-1 sm:grid-cols-3 gap-4">
      <div class="dash-card custom-shadow">
        <div class="text-[10px] uppercase font-bold text-slate-400">Total Budget Allocation</div>
        <div class="text-2xl font-bold text-slate-900 mt-1">${formatCurrency(spec.total_budget || 0)}</div>
        <div class="text-[11px] text-slate-500 mt-0.5">Approved fiscal baseline</div>
      </div>

      <div class="dash-card custom-shadow">
        <div class="text-[10px] uppercase font-bold text-slate-400">Total Actual Expenditures</div>
        <div class="text-2xl font-bold text-slate-900 mt-1">${formatCurrency(spec.total_actual || 0)}</div>
        <div class="text-[11px] text-slate-500 mt-0.5">Recorded operational spend</div>
      </div>

      <div class="dash-card custom-shadow">
        <div class="text-[10px] uppercase font-bold text-slate-400">Net Budget Variance</div>
        <div class="text-2xl font-bold ${spec.total_variance > 0 ? 'text-rose-600' : 'text-emerald-600'} mt-1">
          ${formatCurrency(Math.abs(spec.total_variance || 0))}
        </div>
        <div class="text-[11px] ${spec.total_variance > 0 ? 'text-rose-600' : 'text-emerald-600'} mt-0.5 font-semibold">
          ${spec.total_variance > 0 ? 'Over Budget' : 'Under Budget'} (${Math.abs(spec.total_variance_pct || 0).toFixed(1)}%)
        </div>
      </div>
    </section>

    <!-- Department Budget Table -->
    <section class="dash-card custom-shadow">
      <h3 class="text-sm font-bold text-slate-900 mb-3 pb-2 border-b border-slate-100">Department Budget Variance Statement</h3>
      <div class="overflow-x-auto border border-slate-200 rounded-xl custom-scroll">
        <table class="w-full text-left border-collapse text-xs">
          <thead>
            <tr class="text-[10px] uppercase tracking-wider text-slate-500 border-b border-slate-200 bg-slate-50/80">
              <th class="px-4 py-3 font-bold">Department</th>
              <th class="px-4 py-3 font-bold text-right">Actual Spend</th>
              <th class="px-4 py-3 font-bold text-right">Budgeted Cap</th>
              <th class="px-4 py-3 font-bold text-right">Variance (INR)</th>
              <th class="px-4 py-3 font-bold text-right">Variance %</th>
              <th class="px-4 py-3 font-bold text-center">Status</th>
            </tr>
          </thead>
          <tbody class="divide-y divide-slate-100 text-slate-700 bg-white">
            ${depts.map(d => {
              const isOver = d.variance && d.variance > 0;
              const statusBadge = d.has_budget
                ? (isOver ? 'bg-rose-100 text-rose-800' : 'bg-emerald-100 text-emerald-800')
                : 'bg-slate-100 text-slate-600';
              return `
                <tr class="hover:bg-slate-50/80">
                  <td class="px-4 py-3 font-semibold text-slate-900">${d.department}</td>
                  <td class="px-4 py-3 text-right font-semibold">${formatCurrency(d.expense)}</td>
                  <td class="px-4 py-3 text-right text-slate-600">${d.has_budget ? formatCurrency(d.budget) : '—'}</td>
                  <td class="px-4 py-3 text-right font-bold ${isOver ? 'text-rose-600' : 'text-emerald-600'}">
                    ${d.variance !== null && d.variance !== undefined ? formatCurrency(Math.abs(d.variance)) : '—'}
                  </td>
                  <td class="px-4 py-3 text-right text-slate-600">
                    ${d.variance_pct !== null && d.variance_pct !== undefined ? `${Math.abs(d.variance_pct).toFixed(1)}%` : '—'}
                  </td>
                  <td class="px-4 py-3 text-center">
                    <span class="px-2 py-0.5 rounded text-[10px] font-bold ${statusBadge}">${d.status || 'Normal'}</span>
                  </td>
                </tr>
              `;
            }).join('')}
          </tbody>
        </table>
      </div>
    </section>
  `;

  container.innerHTML = html;
}

// ────────────────────────────────────────────────────────────────
// VIEW 5: DEPARTMENT PERFORMANCE REPORT
// ────────────────────────────────────────────────────────────────
function renderDepartmentReportView(container, res) {
  const depts = res.department_performance || [];
  const topProf = depts[0] || {};
  const topRev = depts.length > 0 ? [...depts].sort((a,b) => b.revenue - a.revenue)[0] : {};
  const topMgn = depts.length > 0 ? [...depts].sort((a,b) => b.margin - a.margin)[0] : {};
  const lowMgn = depts.length > 0 ? [...depts].sort((a,b) => a.margin - b.margin)[0] : {};

  let html = `
    <!-- Leader Cards -->
    <section class="grid grid-cols-2 sm:grid-cols-4 gap-3.5">
      <div class="dash-card custom-shadow border-l-4 border-l-emerald-500">
        <div class="text-[10px] uppercase font-bold text-slate-400">Highest Profit Anchor</div>
        <div class="text-base font-bold text-slate-900 mt-1">${topProf.department || '—'}</div>
        <div class="text-[11px] text-emerald-600 font-semibold mt-0.5">${formatCurrency(topProf.profit || 0)} (${(topProf.margin || 0).toFixed(1)}%)</div>
      </div>

      <div class="dash-card custom-shadow border-l-4 border-l-blue-500">
        <div class="text-[10px] uppercase font-bold text-slate-400">Top Revenue Driver</div>
        <div class="text-base font-bold text-slate-900 mt-1">${topRev.department || '—'}</div>
        <div class="text-[11px] text-blue-600 font-semibold mt-0.5">${formatCurrency(topRev.revenue || 0)}</div>
      </div>

      <div class="dash-card custom-shadow border-l-4 border-l-indigo-500">
        <div class="text-[10px] uppercase font-bold text-slate-400">Highest Margin Unit</div>
        <div class="text-base font-bold text-slate-900 mt-1">${topMgn.department || '—'}</div>
        <div class="text-[11px] text-indigo-600 font-semibold mt-0.5">${(topMgn.margin || 0).toFixed(1)}% Operating Margin</div>
      </div>

      <div class="dash-card custom-shadow border-l-4 border-l-amber-500">
        <div class="text-[10px] uppercase font-bold text-slate-400">Cost Attention Unit</div>
        <div class="text-base font-bold text-slate-900 mt-1">${lowMgn.department || '—'}</div>
        <div class="text-[11px] text-amber-600 font-semibold mt-0.5">${(lowMgn.margin || 0).toFixed(1)}% Margin</div>
      </div>
    </section>

    <!-- Department Ranking Table -->
    <section class="dash-card custom-shadow">
      <h3 class="text-sm font-bold text-slate-900 mb-3 pb-2 border-b border-slate-100">Division Scorecard &amp; Profit Ranking</h3>
      <div class="overflow-x-auto border border-slate-200 rounded-xl custom-scroll">
        <table class="w-full text-left border-collapse text-xs">
          <thead>
            <tr class="text-[10px] uppercase tracking-wider text-slate-500 border-b border-slate-200 bg-slate-50/80">
              <th class="px-4 py-3 font-bold w-14">Rank</th>
              <th class="px-4 py-3 font-bold">Department</th>
              <th class="px-4 py-3 font-bold text-right">Revenue</th>
              <th class="px-4 py-3 font-bold text-right">Expense</th>
              <th class="px-4 py-3 font-bold text-right">Net Profit</th>
              <th class="px-4 py-3 font-bold text-right">Margin %</th>
              <th class="px-4 py-3 font-bold text-center">Anomalies</th>
              <th class="px-4 py-3 font-bold text-center">Budget Status</th>
            </tr>
          </thead>
          <tbody class="divide-y divide-slate-100 text-slate-700 bg-white">
            ${depts.map((d, idx) => `
              <tr class="hover:bg-slate-50/80">
                <td class="px-4 py-3 font-bold text-slate-400">#${idx + 1}</td>
                <td class="px-4 py-3 font-semibold text-slate-900">${d.department}</td>
                <td class="px-4 py-3 text-right font-semibold text-blue-600">${formatCurrency(d.revenue)}</td>
                <td class="px-4 py-3 text-right text-slate-600">${formatCurrency(d.expense)}</td>
                <td class="px-4 py-3 text-right font-bold ${d.profit >= 0 ? 'text-emerald-600' : 'text-rose-600'}">${formatCurrency(d.profit)}</td>
                <td class="px-4 py-3 text-right font-semibold text-slate-900">${(d.margin || 0).toFixed(1)}%</td>
                <td class="px-4 py-3 text-center"><span class="px-2 py-0.5 rounded text-[10px] font-bold ${d.anomalies_count > 0 ? 'bg-rose-50 text-rose-600' : 'bg-slate-50 text-slate-400'}">${d.anomalies_count || 0}</span></td>
                <td class="px-4 py-3 text-center"><span class="px-2 py-0.5 rounded text-[10px] font-semibold ${d.status === 'On Budget' || d.status === 'Under Budget' ? 'bg-emerald-50 text-emerald-700' : (d.status === 'Over Budget' || d.status === 'Materially Over' ? 'bg-rose-50 text-rose-700' : 'bg-slate-50 text-slate-600')}">${d.status || '—'}</span></td>
              </tr>
            `).join('')}
          </tbody>
        </table>
      </div>
    </section>
  `;

  container.innerHTML = html;
}

// ────────────────────────────────────────────────────────────────
// VIEW 6: CASH FLOW REPORT
// ────────────────────────────────────────────────────────────────
function renderCashFlowReportView(container, res) {
  const kpis = res.kpis || {};
  const totalRev = Number(kpis.total_revenue || 0);
  const totalExp = Number(kpis.total_expense || 0);
  const netCash = Number(kpis.net_profit || (totalRev - totalExp));

  let html = `
    <!-- Cash Flow Cards -->
    <section class="grid grid-cols-1 sm:grid-cols-3 gap-4">
      <div class="dash-card custom-shadow">
        <div class="text-[10px] uppercase font-bold text-slate-400">Operating Inflow</div>
        <div class="text-2xl font-bold text-blue-600 mt-1">${formatCurrency(totalRev)}</div>
        <div class="text-[11px] text-slate-500 mt-0.5">Customer receivables & revenue</div>
      </div>
      <div class="dash-card custom-shadow">
        <div class="text-[10px] uppercase font-bold text-slate-400">Operating Outflow</div>
        <div class="text-2xl font-bold text-rose-600 mt-1">${formatCurrency(totalExp)}</div>
        <div class="text-[11px] text-slate-500 mt-0.5">Operating expenditures & payroll</div>
      </div>
      <div class="dash-card custom-shadow bg-gradient-to-br from-white to-emerald-50/20">
        <div class="text-[10px] uppercase font-bold text-slate-400">Net Cash Conversion</div>
        <div class="text-2xl font-bold ${netCash >= 0 ? 'text-emerald-600' : 'text-rose-600'} mt-1">${formatCurrency(netCash)}</div>
        <div class="text-[11px] text-emerald-600 mt-0.5 font-semibold">Free cash flow generated</div>
      </div>
    </section>

    <!-- Cash Flow Trajectory Chart -->
    <section class="dash-card custom-shadow w-full">
      <div class="flex items-center justify-between mb-3 pb-2 border-b border-slate-100">
        <div>
          <h2 class="text-sm font-bold text-slate-900">Cash Flow Trajectory</h2>
          <p class="text-[11px] text-slate-500 mt-0.5">Periodic net cash flow trend</p>
        </div>
      </div>
      <div class="w-full relative" style="height: 280px;">
        <div id="chart-overall-pnl-trend" style="width: 100%; height: 280px;"></div>
      </div>
    </section>
  `;

  container.innerHTML = html;
  setTimeout(() => renderTrendChart(res), 50);
}

// ────────────────────────────────────────────────────────────────
// VIEW 7: REVENUE & EXPENSE REPORT
// ────────────────────────────────────────────────────────────────
function renderRevenueExpenseReportView(container, res) {
  const depts = res.department_performance || [];

  let html = `
    <!-- Top-Line & OPEX Breakdown -->
    <section class="dash-card custom-shadow w-full">
      <div class="flex items-center justify-between mb-3 pb-2 border-b border-slate-100">
        <div>
          <h2 class="text-sm font-bold text-slate-900">Revenue &amp; Expense Trajectory</h2>
          <p class="text-[11px] text-slate-500 mt-0.5">Comparative operating trends</p>
        </div>
      </div>
      <div class="w-full relative" style="height: 280px;">
        <div id="chart-overall-pnl-trend" style="width: 100%; height: 280px;"></div>
      </div>
    </section>

    <!-- Division Expense Distribution -->
    <section class="dash-card custom-shadow">
      <h3 class="text-sm font-bold text-slate-900 mb-3 pb-2 border-b border-slate-100">Division Revenue vs Spend Breakdown</h3>
      <div class="overflow-x-auto border border-slate-200 rounded-xl custom-scroll">
        <table class="w-full text-left border-collapse text-xs">
          <thead>
            <tr class="text-[10px] uppercase tracking-wider text-slate-500 border-b border-slate-200 bg-slate-50/80">
              <th class="px-4 py-3 font-bold">Department</th>
              <th class="px-4 py-3 font-bold text-right">Revenue</th>
              <th class="px-4 py-3 font-bold text-right">Expense</th>
              <th class="px-4 py-3 font-bold text-right">Net Contribution</th>
              <th class="px-4 py-3 font-bold text-right">Margin %</th>
            </tr>
          </thead>
          <tbody class="divide-y divide-slate-100 text-slate-700 bg-white">
            ${depts.map(d => `
              <tr class="hover:bg-slate-50/80">
                <td class="px-4 py-3 font-semibold text-slate-900">${d.department}</td>
                <td class="px-4 py-3 text-right font-semibold text-blue-600">${formatCurrency(d.revenue)}</td>
                <td class="px-4 py-3 text-right text-slate-600">${formatCurrency(d.expense)}</td>
                <td class="px-4 py-3 text-right font-bold ${d.profit >= 0 ? 'text-emerald-600' : 'text-rose-600'}">${formatCurrency(d.profit)}</td>
                <td class="px-4 py-3 text-right font-semibold text-slate-900">${(d.margin || 0).toFixed(1)}%</td>
              </tr>
            `).join('')}
          </tbody>
        </table>
      </div>
    </section>
  `;

  container.innerHTML = html;
  setTimeout(() => renderTrendChart(res), 50);
}

// ────────────────────────────────────────────────────────────────
// VIEW 8: EXECUTIVE SUMMARY
// ────────────────────────────────────────────────────────────────
function renderExecutiveReportView(container, res) {
  const brief = res.executive_brief || {};
  const depts = res.department_performance || [];
  const topProf = depts[0] || {};
  const verdict = brief.verdict_status || 'HEALTHY';
  const verdictBg = verdict === 'HEALTHY' ? 'bg-emerald-50 border-emerald-200 text-emerald-800' : (verdict === 'WATCH' ? 'bg-amber-50 border-amber-200 text-amber-800' : 'bg-rose-50 border-rose-200 text-rose-800');

  let html = `
    <!-- Executive Verdict Callout -->
    <section class="p-4 rounded-xl border ${verdictBg} flex items-start gap-3">
      <span class="material-symbols-outlined text-xl mt-0.5">verified</span>
      <div>
        <div class="text-xs font-bold uppercase tracking-wider">Executive Health Classification: ${verdict}</div>
        <p class="text-xs mt-1 leading-relaxed font-medium">${brief.executive_verdict || res.narrative_summary || 'Operating within standard financial bounds.'}</p>
      </div>
    </section>

    <!-- Strategic Performance Grid -->
    <section class="grid grid-cols-1 md:grid-cols-2 gap-4">
      <div class="dash-card custom-shadow">
        <h4 class="font-bold text-xs text-slate-900 mb-2">Key Profit Anchors</h4>
        <div class="space-y-2 text-xs">
          <div class="flex justify-between py-1.5 border-b border-slate-100">
            <span class="text-slate-600">Top Performing Unit:</span>
            <b class="text-slate-900">${topProf.department || 'Commercial'} (${formatCurrency(topProf.profit || 0)})</b>
          </div>
          <div class="flex justify-between py-1.5 border-b border-slate-100">
            <span class="text-slate-600">Enterprise Margin Conversion:</span>
            <b class="text-emerald-600">${(res.kpis?.net_margin || 0).toFixed(1)}%</b>
          </div>
          <div class="flex justify-between py-1.5">
            <span class="text-slate-600">Financial Health Score:</span>
            <b class="text-primary">${brief.financial_health_score || 95}/100</b>
          </div>
        </div>
      </div>

      <div class="dash-card custom-shadow">
        <h4 class="font-bold text-xs text-slate-900 mb-2">Surveillance &amp; Variance Oversight</h4>
        <div class="space-y-2 text-xs">
          <div class="flex justify-between py-1.5 border-b border-slate-100">
            <span class="text-slate-600">Audit Ledger Outliers:</span>
            <b class="${(res.kpis?.total_anomalies || 0) > 0 ? 'text-rose-600' : 'text-slate-900'}">${res.kpis?.total_anomalies || 0} flagged</b>
          </div>
          <div class="flex justify-between py-1.5 border-b border-slate-100">
            <span class="text-slate-600">Budget Compliance:</span>
            <b class="${res.kpis?.budget_status === 'Materially Over' ? 'text-rose-600' : 'text-emerald-600'}">${res.kpis?.budget_status || 'Under Budget'}</b>
          </div>
          <div class="flex justify-between py-1.5">
            <span class="text-slate-600">Forward Outlook Trajectory:</span>
            <b class="text-emerald-600">${formatCurrency(res.kpis?.forecast_profit || 0)} Projected Profit</b>
          </div>
        </div>
      </div>
    </section>
  `;

  container.innerHTML = html;
}

// ────────────────────────────────────────────────────────────────
// VIEW 9: OVERALL / P&L FINANCIAL REPORT
// ────────────────────────────────────────────────────────────────
function renderOverallReportView(container, res) {
  const depts = res.department_performance || [];

  let html = `
    <!-- Financial Performance Trajectory Chart -->
    <section class="dash-card custom-shadow w-full">
      <div class="flex flex-col sm:flex-row sm:items-center justify-between gap-2 mb-3 pb-2 border-b border-slate-100">
        <div>
          <h2 class="text-sm font-bold text-slate-900 flex items-center gap-1.5">
            <span class="material-symbols-outlined text-base text-primary">show_chart</span>
            <span>Financial Performance Trajectory</span>
          </h2>
          <p class="text-[11px] text-slate-500 mt-0.5">Historical trend of Revenue, Operating Expenses, and Net Profit</p>
        </div>

        <!-- Legend -->
        <div class="flex items-center gap-3 text-[11px] font-medium text-slate-600">
          <span class="inline-flex items-center gap-1.5"><span class="w-2.5 h-2.5 rounded-full bg-[#3B82F6]"></span> Revenue</span>
          <span class="inline-flex items-center gap-1.5"><span class="w-2.5 h-2.5 rounded-full bg-[#EF4444]"></span> Expense</span>
          <span class="inline-flex items-center gap-1.5"><span class="w-2.5 h-2.5 rounded-full bg-[#10B981]"></span> Net Profit</span>
        </div>
      </div>

      <div class="w-full relative" style="height: 300px;">
        <div id="chart-overall-pnl-trend" style="width: 100%; height: 300px;"></div>
      </div>
    </section>

    <!-- Department Breakdown Statement Table -->
    <section class="dash-card custom-shadow w-full">
      <h3 class="text-sm font-bold text-slate-900 mb-3 pb-2 border-b border-slate-100">Department Performance Summary</h3>
      <div class="overflow-x-auto border border-slate-200 rounded-xl custom-scroll">
        <table class="w-full text-left border-collapse text-xs">
          <thead>
            <tr class="text-[10px] uppercase tracking-wider text-slate-500 border-b border-slate-200 bg-slate-50/80">
              <th class="px-4 py-3 font-bold w-14">Rank</th>
              <th class="px-4 py-3 font-bold">Department</th>
              <th class="px-4 py-3 font-bold text-right">Revenue</th>
              <th class="px-4 py-3 font-bold text-right">Expenses</th>
              <th class="px-4 py-3 font-bold text-right">Net Profit</th>
              <th class="px-4 py-3 font-bold text-right">Margin %</th>
              <th class="px-4 py-3 font-bold text-center">Status</th>
            </tr>
          </thead>
          <tbody class="divide-y divide-slate-100 text-slate-700 bg-white">
            ${depts.map((d, idx) => `
              <tr class="hover:bg-slate-50/80">
                <td class="px-4 py-3 font-bold text-slate-400">#${idx + 1}</td>
                <td class="px-4 py-3 font-semibold text-slate-900">${d.department}</td>
                <td class="px-4 py-3 text-right font-semibold text-blue-600">${formatCurrency(d.revenue)}</td>
                <td class="px-4 py-3 text-right text-slate-600">${formatCurrency(d.expense)}</td>
                <td class="px-4 py-3 text-right font-bold ${d.profit >= 0 ? 'text-emerald-600' : 'text-rose-600'}">${formatCurrency(d.profit)}</td>
                <td class="px-4 py-3 text-right font-semibold text-slate-900">${(d.margin || 0).toFixed(1)}%</td>
                <td class="px-4 py-3 text-center"><span class="px-2 py-0.5 rounded text-[10px] font-semibold ${d.status === 'On Budget' || d.status === 'Under Budget' ? 'bg-emerald-50 text-emerald-700' : (d.status === 'Over Budget' || d.status === 'Materially Over' ? 'bg-rose-50 text-rose-700' : 'bg-slate-50 text-slate-600')}">${d.status || 'Normal'}</span></td>
              </tr>
            `).join('')}
          </tbody>
        </table>
      </div>
    </section>
  `;

  container.innerHTML = html;
  setTimeout(() => renderTrendChart(res), 50);
}

function renderTrendChart(res) {
  const chartEl = document.getElementById('chart-overall-pnl-trend');
  if (!chartEl) return;

  const chart = initEchart(chartEl);
  const trend = res.pnl_trend || res.trend || res.performance_at_a_glance || {};
  const periods = trend.periods || [];
  const rev = trend.revenue || [];
  const exp = trend.expenses || trend.expense || [];
  const prof = trend.profit || [];

  safeSetOption(chart, {
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
    grid: { left: 10, right: 20, top: 20, bottom: 20, containLabel: true },
    xAxis: {
      type: 'category',
      data: periods,
      axisLabel: { fontSize: 10, color: '#64748b', fontFamily: 'Inter' },
      axisLine: { lineStyle: { color: '#e2e8f0' } }
    },
    yAxis: {
      type: 'value',
      axisLabel: { fontSize: 10, color: '#94a3b8', fontFamily: 'Inter', formatter: (v) => formatShort(v) },
      splitLine: { lineStyle: { color: '#f1f5f9' } }
    },
    series: [
      { name: 'Revenue', type: 'line', data: rev, itemStyle: { color: '#3B82F6' }, lineStyle: { width: 2 }, smooth: true, showSymbol: false },
      { name: 'Expense', type: 'line', data: exp, itemStyle: { color: '#EF4444' }, lineStyle: { width: 2 }, smooth: true, showSymbol: false },
      { name: 'Net Profit', type: 'line', data: prof, itemStyle: { color: '#10B981' }, lineStyle: { width: 2.5 }, smooth: true, showSymbol: false }
    ]
  }, true);
}

// ── Observations & Management Recommendations ──────────────────
function renderInsightsAndRecommendations(insights, recs) {
  const obsContainer = document.getElementById('report-insights-container');
  const recContainer = document.getElementById('report-recommendations-container');

  if (obsContainer) {
    if (!insights || insights.length === 0) {
      obsContainer.innerHTML = '<p class="text-slate-400 text-xs py-2">No specific observations generated for this slice.</p>';
    } else {
      obsContainer.innerHTML = insights.map((item, idx) => {
        if (typeof item === 'object' && item !== null) {
          const finding = item.finding || item.title || item.desc || JSON.stringify(item);
          const evidence = item.evidence ? `<p class="text-[11px] text-slate-500 mt-0.5"><b>Evidence:</b> ${item.evidence}</p>` : '';
          const impact = item.impact ? `<p class="text-[11px] text-indigo-600 mt-0.5 font-medium"><b>Business Impact:</b> ${item.impact}</p>` : '';
          return `
            <div class="p-2.5 rounded-lg border border-slate-100 bg-slate-50/50 space-y-0.5">
              <div class="flex items-start gap-2">
                <span class="w-4 h-4 rounded-full bg-indigo-50 text-primary text-[10px] font-bold flex items-center justify-center shrink-0 mt-0.5">${idx + 1}</span>
                <p class="font-semibold text-slate-900 text-xs leading-snug">${finding}</p>
              </div>
              <div class="pl-6">${evidence}${impact}</div>
            </div>
          `;
        } else {
          return `
            <div class="flex items-start gap-2 p-1.5 rounded hover:bg-slate-50">
              <span class="w-4 h-4 rounded-full bg-indigo-50 text-primary text-[10px] font-bold flex items-center justify-center shrink-0 mt-0.5">${idx + 1}</span>
              <p class="leading-relaxed text-slate-700 text-xs">${item}</p>
            </div>
          `;
        }
      }).join('');
    }
  }

  if (recContainer) {
    if (!recs || recs.length === 0) {
      recContainer.innerHTML = '<p class="text-slate-400 text-xs py-2">No action items required at this time.</p>';
    } else {
      recContainer.innerHTML = recs.map((item) => {
        if (typeof item === 'object' && item !== null) {
          const prio = (item.priority || 'MEDIUM').toUpperCase();
          const prioBadge = prio === 'CRITICAL' || prio === 'HIGH'
            ? 'bg-rose-100 text-rose-800'
            : prio === 'MEDIUM'
            ? 'bg-amber-100 text-amber-800'
            : 'bg-indigo-100 text-indigo-800';

          const issue = item.issue || item.title || item.action_type || 'Operational Initiative';
          const evidence = item.evidence || item.reason || '';
          const action = item.action || item.suggested_action || item.description || '';
          const impact = item.business_impact || item.expected_benefit || item.direction || '';
          const owner = item.owner || item.action_owner || '';
          const horizon = item.horizon || item.implementation_timeline || '';

          return `
            <div class="p-3 rounded-xl border border-emerald-100/80 bg-white shadow-xs space-y-1.5">
              <div class="flex items-center justify-between gap-2">
                <span class="px-2 py-0.5 rounded text-[9px] font-bold uppercase tracking-wider ${prioBadge}">
                  ${prio} Priority
                </span>
                ${horizon ? `<span class="text-[10px] font-semibold text-slate-400 bg-slate-100 px-2 py-0.5 rounded">${horizon}</span>` : ''}
              </div>
              <h5 class="text-xs font-bold text-slate-900 leading-snug">${issue}</h5>
              ${evidence ? `<p class="text-[11px] text-slate-500 leading-normal"><b class="text-slate-700">Evidence:</b> ${evidence}</p>` : ''}
              ${action ? `<div class="flex items-start gap-1.5 text-[11px] text-emerald-800 font-medium bg-emerald-50/60 p-2 rounded-lg border border-emerald-100/50"><span class="material-symbols-outlined text-sm text-emerald-600 shrink-0">check_circle</span><span><b>Action:</b> ${action}</span></div>` : ''}
              ${impact ? `<p class="text-[10px] text-indigo-700 font-semibold">Impact: ${impact}</p>` : ''}
              ${owner ? `<div class="text-[10px] text-slate-400 text-right">Owner: <span class="font-medium text-slate-600">${owner}</span></div>` : ''}
            </div>
          `;
        } else {
          return `
            <div class="flex items-start gap-2 p-2 rounded-lg border border-emerald-100/50 bg-emerald-50/20">
              <span class="material-symbols-outlined text-emerald-600 text-sm shrink-0 mt-0.5">verified</span>
              <p class="leading-relaxed text-slate-700 text-xs font-medium">${item}</p>
            </div>
          `;
        }
      }).join('');
    }
  }
}

// ── Event Handlers & Initialization ─────────────────────────────
async function initReports() {
  const reportTypeSelect = document.getElementById('report-type-select');
  if (reportTypeSelect) {
    reportTypeSelect.addEventListener('change', () => loadReport());
  }

  const deptSelect = document.getElementById('report-dept-select');
  if (deptSelect) {
    deptSelect.addEventListener('change', () => loadReport());
  }

  const periodSelect = document.getElementById('report-period-select');
  if (periodSelect) {
    periodSelect.addEventListener('change', () => loadReport());
  }

  const generateBtn = document.getElementById('btn-generate-report');
  if (generateBtn) {
    generateBtn.addEventListener('click', () => loadReport(true));
  }

  const clearHistoryBtn = document.getElementById('btn-clear-history');
  if (clearHistoryBtn) {
    clearHistoryBtn.addEventListener('click', () => {
      reportHistory = [];
      localStorage.removeItem('unified_pl_report_history');
      renderHistoryTable();
    });
  }

  // Export dropdown
  const exportBtn = document.getElementById('btn-export-report');
  const exportMenu = document.getElementById('export-menu');
  if (exportBtn && exportMenu) {
    exportBtn.addEventListener('click', (e) => {
      e.stopPropagation();
      exportMenu.classList.toggle('hidden');
    });
    document.addEventListener('click', () => exportMenu.classList.add('hidden'));
  }

  const exportPdfBtn = document.getElementById('export-action-pdf');
  if (exportPdfBtn) {
    exportPdfBtn.addEventListener('click', () => downloadCurrentReport('pdf'));
  }

  const exportExcelBtn = document.getElementById('export-action-excel');
  if (exportExcelBtn) {
    exportExcelBtn.addEventListener('click', () => downloadCurrentReport('excel'));
  }

  const exportCsvBtn = document.getElementById('export-action-csv');
  if (exportCsvBtn) {
    exportCsvBtn.addEventListener('click', () => downloadCurrentReport('csv'));
  }

  // Initial Boot
  loadHistory();
  await initFilters();
  await loadReport();
}

if (document.readyState === 'loading') {
  document.addEventListener('DOMContentLoaded', initReports);
} else {
  initReports();
}
