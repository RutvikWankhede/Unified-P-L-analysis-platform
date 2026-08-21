import { api } from './api.js';
import './auth.js';

/**
 * anomaly.js - Anomaly Detection Page
 */

document.addEventListener('DOMContentLoaded', initAnomalies);

async function initAnomalies() {
 await loadAnomalies();

 // Filter buttons
 document.querySelectorAll('[data-severity-filter]').forEach(btn => {
 btn.addEventListener('click', () => {
 document.querySelectorAll('[data-severity-filter]').forEach(b => b.classList.remove('active', 'bg-primary', 'text-white'));
 btn.classList.add('active', 'bg-primary', 'text-white');
 filterAnomalies(btn.dataset.severityFilter);
 });
 });

 // Search
 const searchInput = document.getElementById('anomaly-search');
 if (searchInput) {
 searchInput.addEventListener('input', () => filterBySearch(searchInput.value));
 }
}

let allAnomalies = [];

async function loadAnomalies() {
 const container = document.getElementById('anomaly-list') || document.getElementById('anomalies-container');
 if (container) container.innerHTML = '<div class="text-center py-8 text-slate-400 text-sm">Loading anomalies...</div>';

 try {
 const data = await api.get(api.endpoints.anomalies);
 allAnomalies = Array.isArray(data) ? data : (data.items || []);

 updateSummaryCards(allAnomalies);
 renderAnomalyList(allAnomalies);
 } catch (err) {
 if (container) container.innerHTML = '<div class="text-center py-8 text-red-500 text-sm">Failed to load anomalies. Check backend connection.</div>';
 console.error('Anomalies load failed:', err);
 }
}

function updateSummaryCards(items) {
 const critical = items.filter(a => a.severity === 'Critical').length;
 const high = items.filter(a => a.severity === 'High').length;
 const medium = items.filter(a => a.severity === 'Medium').length;
 const low = items.filter(a => a.severity === 'Low').length;
 const open = items.filter(a => a.status !== 'Resolved').length;

 setEl('total-anomalies', items.length);
 setEl('critical-count', critical);
 setEl('high-count', high);
 setEl('medium-count', medium);
 setEl('low-count', low);
 setEl('open-count', open);
 setEl('resolved-count', items.length - open);
}

function renderAnomalyList(items) {
 const container = document.getElementById('anomaly-list') || document.getElementById('anomalies-container');
 if (!container) return;

 if (!items.length) {
 container.innerHTML = `
 <div class="flex flex-col items-center justify-center py-16 text-slate-400">
 <span class="material-symbols-outlined text-5xl mb-3">check_circle</span>
 <p class="text-sm font-semibold">No anomalies detected</p>
 <p class="text-xs mt-1">Your data looks clean!</p>
 </div>`;
 return;
 }

 const severityColors = {
 'Critical': 'bg-red-50 text-red-600 border-red-100',
 'High': 'bg-orange-50 text-orange-500 border-orange-100',
 'Medium': 'bg-yellow-50 text-yellow-600 border-yellow-100',
 'Low': 'bg-blue-50 text-blue-600 border-blue-100',
 };
 const severityBadge = {
 'Critical': 'bg-red-100 text-red-600',
 'High': 'bg-orange-100 text-orange-500',
 'Medium': 'bg-yellow-100 text-yellow-600',
 'Low': 'bg-blue-100 text-blue-600',
 };
 const statusColors = {
 'Pending': 'bg-orange-50 text-orange-500',
 'Under Review': 'bg-blue-50 text-blue-600',
 'Resolved': 'bg-green-50 text-green-600',
 };

 container.innerHTML = items.map(a => {
 const sColor = severityColors[a.severity] || 'bg-slate-50 text-slate-500 border-slate-100';
 const sBadge = severityBadge[a.severity] || 'bg-slate-100 text-slate-500';
 const stColor = statusColors[a.status] || 'bg-slate-50 text-slate-500';
 const date = a.detected_at ? new Date(a.detected_at).toLocaleDateString('en-IN', { day: '2-digit', month: 'short', year: 'numeric' }) : 'Unknown';
 const score = a.anomaly_score ? (a.anomaly_score * 100).toFixed(0) + '%' : 'N/A';

 return `
 <div class="bg-white border border-slate-100 rounded-2xl p-5 shadow-sm hover:shadow-md transition-all anomaly-item" data-severity="${a.severity}" data-id="${a.id}">
 <div class="flex items-start justify-between gap-4">
 <div class="flex items-start gap-4 flex-1">
 <div class="w-10 h-10 rounded-xl ${sColor.split(' ').slice(0,2).join(' ')} flex items-center justify-center flex-shrink-0 border ${sColor.split(' ')[2] || ''}">
 <span class="material-symbols-outlined text-sm">warning</span>
 </div>
 <div class="flex-1 min-w-0">
 <div class="flex flex-wrap items-center gap-2 mb-1">
 <h3 class="text-sm font-bold text-slate-900 truncate">${a.line_item || a.description || 'Anomalous Entry'}</h3>
 <span class="px-2 py-0.5 rounded-full text-[10px] font-bold uppercase ${sBadge}">${a.severity}</span>
 <span class="px-2 py-0.5 rounded-full text-[10px] font-bold uppercase ${stColor}">${a.status || 'Pending'}</span>
 </div>
 <p class="text-xs text-slate-500 mb-2">${a.description || 'Anomaly detected by ML model'}</p>
 <div class="flex flex-wrap items-center gap-4 text-xs text-slate-400">
 <span class="flex items-center gap-1"><span class="material-symbols-outlined text-xs">domain</span>${a.domain || '—'}</span>
 <span class="flex items-center gap-1"><span class="material-symbols-outlined text-xs">calendar_today</span>${date}</span>
 <span class="flex items-center gap-1"><span class="material-symbols-outlined text-xs">payments</span>₹${(a.amount || 0).toLocaleString('en-IN')}</span>
 <span class="flex items-center gap-1"><span class="material-symbols-outlined text-xs">analytics</span>Score: ${score}</span>
 </div>
 </div>
 </div>
 <div class="flex items-center gap-2 flex-shrink-0">
 ${a.status !== 'Resolved' ? `
 <button onclick="resolveAnomaly(${a.id})" class="text-xs font-semibold text-green-600 hover:text-green-700 bg-green-50 hover:bg-green-100 px-3 py-1.5 rounded-lg transition-colors">
 Resolve
 </button>
 <button onclick="reviewAnomaly(${a.id})" class="text-xs font-semibold text-primary hover:text-indigo-700 bg-primary/10 hover:bg-primary/20 px-3 py-1.5 rounded-lg transition-colors">
 Review
 </button>
 ` : '<span class="text-xs text-green-600 font-semibold">✓ Resolved</span>'}
 </div>
 </div>
 </div>`;
 }).join('');
}

function filterAnomalies(severity) {
 const filtered = severity === 'All' ? allAnomalies : allAnomalies.filter(a => a.severity === severity);
 renderAnomalyList(filtered);
}

function filterBySearch(query) {
 const q = query.toLowerCase();
 const filtered = allAnomalies.filter(a =>
 (a.line_item || '').toLowerCase().includes(q) ||
 (a.description || '').toLowerCase().includes(q) ||
 (a.domain || '').toLowerCase().includes(q)
 );
 renderAnomalyList(filtered);
}

window.resolveAnomaly = async (id) => {
 try {
 await api.patch(`/api/v1/anomalies/${id}/status`, { status: 'Resolved' });
 await loadAnomalies();
 } catch (err) {
 alert('Failed to resolve anomaly: ' + (err.message || 'Unknown error'));
 }
};

window.reviewAnomaly = async (id) => {
 try {
 await api.patch(`/api/v1/anomalies/${id}/status`, { status: 'Under Review' });
 await loadAnomalies();
 } catch (err) {
 alert('Failed to update anomaly: ' + (err.message || 'Unknown error'));
 }
};

function setEl(id, val) {
 const el = document.getElementById(id);
 if (el) el.textContent = val;
}
