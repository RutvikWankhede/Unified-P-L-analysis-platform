import { api } from './api.js';

function formatCurrency(val) {
    if (val === null || val === undefined) return '—';
    const abs = Math.abs(val);
    if (abs >= 10000000) return `Rs.${(abs / 10000000).toFixed(2)} Cr`;
    if (abs >= 100000) return `Rs.${(abs / 100000).toFixed(2)} L`;
    return `Rs.${abs.toLocaleString('en-IN')}`;
}

async function loadAnomaliesPage() {
    const tbody = document.getElementById('anomalies-table-body') || document.querySelector('table tbody');
    if (!tbody) return;

    try {
        const res = await api.get('/api/v1/anomalies/?limit=50');
        const items = Array.isArray(res) ? res : (res?.anomalies || res?.items || []);

        // Update KPI cards
        const total = items.length;
        const critical = items.filter(a => (a.severity || '').toLowerCase() === 'critical').length;
        const high = items.filter(a => (a.severity || '').toLowerCase() === 'high').length;
        const medium = items.filter(a => (a.severity || '').toLowerCase() === 'medium').length;
        const low = items.filter(a => (a.severity || '').toLowerCase() === 'low').length;

        const kpiSection = document.querySelector('[data-purpose="kpi-section"]');
        if (kpiSection) {
            const vals = kpiSection.querySelectorAll('.text-xl.font-bold');
            if (vals.length >= 5) {
                vals[0].textContent = total;
                vals[1].textContent = critical;
                vals[2].textContent = high;
                vals[3].textContent = medium;
                vals[4].textContent = low;
            }
        }

        if (!items.length) {
            tbody.innerHTML = `<tr><td colspan="8" class="text-center py-8 text-slate-400 text-sm">No anomalies detected.</td></tr>`;
            return;
        }

        const severityBadges = {
            critical: 'bg-red-100 text-red-700 border border-red-200',
            high: 'bg-orange-100 text-orange-700 border border-orange-200',
            medium: 'bg-yellow-100 text-yellow-700 border border-yellow-200',
            low: 'bg-blue-100 text-blue-700 border border-blue-200'
        };

        const statusBadges = {
            new: 'bg-green-100 text-green-700',
            pending: 'bg-amber-100 text-amber-700',
            'in review': 'bg-blue-100 text-blue-700',
            resolved: 'bg-slate-100 text-slate-600'
        };

        tbody.innerHTML = items.map(a => {
            const sev = (a.severity || a.score_label || 'low').toLowerCase();
            const status = (a.status || 'New').toLowerCase();
            const dateStr = a.detected_at || a.date ? new Date(a.detected_at || a.date).toLocaleDateString('en-IN', { day: 'numeric', month: 'short', year: 'numeric' }) : 'May 18, 2025';
            const dept = a.department || a.domain || 'General';
            const account = a.line_item || a.account || 'Expense Item';
            const desc = a.description || a.explanation || 'Anomaly detected in transaction pattern';
            const amt = a.amount || a.metric_value || 0;

            const sBadge = severityBadges[sev] || severityBadges.low;
            const stBadge = statusBadges[status] || statusBadges.new;

            return `
            <tr class="hover:bg-slate-50/50 transition-colors">
                <td class="px-6 py-4 text-xs font-medium text-slate-600">${dateStr}</td>
                <td class="px-6 py-4 text-xs font-bold text-slate-800">${dept}</td>
                <td class="px-6 py-4 text-xs text-slate-600">${account}</td>
                <td class="px-6 py-4 text-xs text-slate-500">${desc}</td>
                <td class="px-6 py-4">
                    <span class="inline-flex items-center px-2.5 py-0.5 rounded-md text-[10px] font-bold uppercase tracking-tight ${sBadge}">${sev}</span>
                </td>
                <td class="px-6 py-4 text-xs font-bold text-slate-800">${formatCurrency(amt)}</td>
                <td class="px-6 py-4 text-center">
                    <span class="inline-flex items-center px-2.5 py-0.5 rounded-md text-[10px] font-bold uppercase tracking-tight ${stBadge}">${status}</span>
                </td>
                <td class="px-6 py-4 text-center">
                    <button onclick="alert('Anomaly Details:\\n\\nItem: ${account}\\nDept: ${dept}\\nSeverity: ${sev.toUpperCase()}\\nDetails: ${desc}')" class="text-primary hover:text-blue-700 p-1 rounded-full hover:bg-blue-50 transition-colors" title="View details">
                        <svg class="w-5 h-5 inline" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path d="M13 16h-1v-4h-1m1-4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z"></path></svg>
                    </button>
                </td>
            </tr>`;
        }).join('');
    } catch (e) {
        console.warn('Failed to load anomalies:', e);
    }
}

document.addEventListener('DOMContentLoaded', () => {
    loadAnomaliesPage();

    const runBtn = document.querySelector('button:has(svg) span, button') ;
    // Wire Run Detection button
    document.querySelectorAll('button').forEach(btn => {
        if (btn.textContent.includes('Run Detection')) {
            btn.addEventListener('click', async () => {
                btn.disabled = true;
                btn.textContent = 'Detecting...';
                try {
                    await api.post('/api/v1/anomalies/detect');
                } catch (_) {}
                await loadAnomaliesPage();
                btn.disabled = false;
                btn.innerHTML = `<svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path d="M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15"></path></svg> Run Detection`;
            });
        }
    });
});
