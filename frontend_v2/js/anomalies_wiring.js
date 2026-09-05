import { api } from './api.js';
import { showModal } from './shell.js';

document.addEventListener('DOMContentLoaded', async () => {
  let anomaliesList = [];
  let currentDeptFilter = 'all';

  function formatCurrency(val) {
    if (val === null || val === undefined || isNaN(val)) return '—';
    const abs = Math.abs(val);
    const sign = val < 0 ? '-' : '';
    if (abs >= 10000000) return `${sign}₹${(abs / 10000000).toFixed(2)} Cr`;
    if (abs >= 100000) return `${sign}₹${(abs / 100000).toFixed(2)} L`;
    if (abs >= 1000) return `${sign}₹${(abs / 1000).toFixed(1)} K`;
    return `${sign}₹${abs.toLocaleString('en-IN')}`;
  }

  async function fetchAnomalies() {
    try {
      const res = await api.get('/api/v1/anomalies/?limit=200').catch(() => null);
      if (res) {
        anomaliesList = Array.isArray(res) ? res : (res.anomalies || res.items || []);
      }
      updateUI();
    } catch (err) {
      console.warn('Failed to fetch anomalies:', err);
    }
  }

  function updateUI() {
    let filtered = [...anomaliesList];
    if (currentDeptFilter !== 'all') {
      filtered = filtered.filter(a => {
        const d = a.department || a.domain || (a.pl_record && a.pl_record.domain) || '';
        return d.toLowerCase() === currentDeptFilter.toLowerCase();
      });
    }

    // 1. Update KPI Cards
    const total = filtered.length;
    const critical = filtered.filter(a => (a.severity || '').toLowerCase() === 'critical').length;
    const high = filtered.filter(a => (a.severity || '').toLowerCase() === 'high').length;
    const medium = filtered.filter(a => (a.severity || '').toLowerCase() === 'medium').length;
    const low = filtered.filter(a => (a.severity || '').toLowerCase() === 'low').length;

    const totalEl = document.getElementById('kpi-anom-total');
    const critEl = document.getElementById('kpi-anom-critical');
    const highEl = document.getElementById('kpi-anom-high');
    const medEl = document.getElementById('kpi-anom-medium');
    const lowEl = document.getElementById('kpi-anom-low');

    if (totalEl) totalEl.textContent = total;
    if (critEl) critEl.textContent = critical;
    if (highEl) highEl.textContent = high;
    if (medEl) medEl.textContent = medium;
    if (lowEl) lowEl.textContent = low;

    // 2. Update Table
    const tbody = document.getElementById('anomalies-tbody') || document.querySelector('table tbody');
    if (tbody) {
      tbody.innerHTML = '';
      if (filtered.length === 0) {
        tbody.innerHTML = '<tr><td colspan="7" class="text-center py-6 text-slate-400 text-xs font-medium">No anomalies detected for selected filter.</td></tr>';
      } else {
        filtered.slice(0, 15).forEach((a, idx) => {
          const dateStr = a.date || (a.detected_at ? new Date(a.detected_at).toLocaleDateString() : `May ${15 + (idx % 4)}, 2025`);
          const dept = a.department || a.domain || (a.pl_record && a.pl_record.domain) || 'General';
          const lineItem = a.account || a.line_item || (a.pl_record && a.pl_record.line_item) || 'Expense';
          const desc = a.description || a.explanation || `Statistical variance in ${lineItem}`;
          const sev = (a.severity || 'Medium').toLowerCase();
          const amt = a.impact_amount || a.amount || (a.pl_record && a.pl_record.amount) || 0;
          const status = a.status || 'New';

          const sevBadge = sev === 'critical'
            ? '<span class="inline-flex items-center gap-1 px-2 py-0.5 rounded text-[11px] font-bold bg-rose-50 text-rose-600 border border-rose-100"><span class="w-1.5 h-1.5 rounded-full bg-rose-500"></span> Critical</span>'
            : (sev === 'high'
            ? '<span class="inline-flex items-center gap-1 px-2 py-0.5 rounded text-[11px] font-bold bg-amber-50 text-amber-700 border border-amber-100"><span class="w-1.5 h-1.5 rounded-full bg-amber-500"></span> High</span>'
            : (sev === 'medium'
            ? '<span class="inline-flex items-center gap-1 px-2 py-0.5 rounded text-[11px] font-semibold bg-indigo-50 text-indigo-700 border border-indigo-100"><span class="w-1.5 h-1.5 rounded-full bg-indigo-500"></span> Medium</span>'
            : '<span class="inline-flex items-center gap-1 px-2 py-0.5 rounded text-[11px] font-medium bg-emerald-50 text-emerald-700 border border-emerald-100"><span class="w-1.5 h-1.5 rounded-full bg-emerald-500"></span> Low</span>'));

          const statusBadge = status === 'Resolved'
            ? '<span class="px-2 py-0.5 rounded-full text-[10px] font-semibold bg-emerald-50 text-emerald-700 border border-emerald-100">Resolved</span>'
            : '<span class="px-2 py-0.5 rounded-full text-[10px] font-semibold bg-blue-50 text-blue-700 border border-blue-100">Open</span>';

          const tr = document.createElement('tr');
          tr.className = 'hover:bg-slate-50/50 transition-colors';
          tr.innerHTML = `
            <td class="py-3 px-4 font-medium text-slate-700 whitespace-nowrap">${dateStr}</td>
            <td class="py-3 px-4 font-semibold text-slate-900">${dept}</td>
            <td class="py-3 px-4 text-slate-700">${lineItem}</td>
            <td class="py-3 px-4 text-slate-500 max-w-xs truncate">${desc}</td>
            <td class="py-3 px-4">${sevBadge}</td>
            <td class="py-3 px-4 font-bold text-slate-800">${formatCurrency(amt)}</td>
            <td class="py-3 px-4">${statusBadge}</td>
          `;
          tbody.appendChild(tr);
        });
      }
    }
  }

  await fetchAnomalies();

  // Run detection button
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
      runBtn.innerHTML = '<span class="material-symbols-outlined text-sm">play_arrow</span> Run Detection';
    });
  }

  // Department Filter
  const deptFilter = document.getElementById('filter-anom-dept');
  if (deptFilter) {
    deptFilter.addEventListener('change', (e) => {
      currentDeptFilter = e.target.value;
      updateUI();
    });
  }

  // View All Anomalies modal trigger
  const viewAllBtn = document.getElementById('btn-view-all-anomalies');
  if (viewAllBtn) {
    viewAllBtn.addEventListener('click', () => {
      openAnomaliesModal();
    });
  }

  // Heatmap cell click interaction
  document.querySelectorAll('.heatmap-cell').forEach(cell => {
    cell.addEventListener('click', () => {
      openAnomaliesModal();
    });
  });

  function openAnomaliesModal() {
    const data = (anomaliesList.length > 0 ? anomaliesList : []).map(a => ({
      'Date': a.date || (a.detected_at ? new Date(a.detected_at).toLocaleDateString() : 'May 18, 2025'),
      'Department': a.department || a.domain || (a.pl_record && a.pl_record.domain) || 'General',
      'Account': a.account || a.line_item || (a.pl_record && a.pl_record.line_item) || 'Expense',
      'Description': a.description || a.explanation || 'Anomaly detected in financial data',
      'Severity': a.severity || 'Medium',
      'Amount': formatCurrency(a.impact_amount || a.amount || (a.pl_record && a.pl_record.amount) || 0),
      'Status': a.status || 'New'
    }));

    showModal('All Detected Anomalies', ['Date', 'Department', 'Account', 'Description', 'Severity', 'Amount', 'Status'], data);
  }
});
