import { api } from './api.js';
import './auth.js';

document.addEventListener('DOMContentLoaded', initDeptDetail);

async function initDeptDetail() {
 const urlParams = new URLSearchParams(window.location.search);
 const deptId = urlParams.get('id') || urlParams.get('dept') || 'Finance';
 
 document.getElementById('dept-title').textContent = deptId + ' Department';

 try {
 //  endpoints using summary/charts as fallback
 const summaryData = await api.get(api.endpoints.summary).catch(() => ({ domains: [] }));
 const deptInfo = summaryData.domains?.find(d => d.domain.toLowerCase() === deptId.toLowerCase()) || { revenue: 5000000, expense: 3000000, profit: 2000000, profit_margin: 40 };

 document.getElementById('kpi-rev').textContent = formatCurrencyShort(deptInfo.revenue);
 document.getElementById('kpi-exp').textContent = formatCurrencyShort(deptInfo.expense);
 document.getElementById('kpi-profit').textContent = formatCurrencyShort(deptInfo.profit);
 document.getElementById('kpi-margin').textContent = deptInfo.profit_margin.toFixed(1) + '%';

 // Chart
 const chartsData = await api.get(api.endpoints.charts).catch(() => null);
 renderDetailChart(chartsData);

 // AI Recs
 const recs = await api.get(api.endpoints.aiRecommendations).catch(() => []);
 renderRecs(recs);

 // Anomalies
 const anomalies = await api.get(api.endpoints.anomalies).catch(() => []);
 renderAnomalies(anomalies);

 // Cost Centers (mock logic for demo)
 renderCostCenters();

 } catch (err) {
 console.error('Failed to load dept details', err);
 }
}

function renderDetailChart(data) {
 const canvas = document.getElementById('dept-detail-chart');
 if (!canvas) return;
 const ctx = canvas.getContext('2d');
 
 // mock trend data if not provided
 const labels = ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun'];
 const rev = [120, 150, 140, 180, 160, 200];
 const exp = [80, 90, 85, 100, 95, 110];

 new Chart(ctx, {
 type: 'line',
 data: {
 labels,
 datasets: [
 { label: 'Revenue', data: rev, borderColor: '#10b981', tension: 0.4 },
 { label: 'Expense', data: exp, borderColor: '#ef4444', tension: 0.4 }
 ]
 },
 options: {
 responsive: true, maintainAspectRatio: false,
 plugins: {
 zoom: { zoom: { wheel: { enabled: true }, mode: 'x' }, pan: { enabled: true, mode: 'x' } }
 }
 }
 });
}

function renderRecs(recs) {
 const container = document.getElementById('ai-recs');
 if (!recs || !recs.length) {
 container.innerHTML = '<p class="text-xs text-slate-500">No active recommendations.</p>';
 return;
 }
 container.innerHTML = recs.slice(0, 3).map(r => 
 <div class="p-3 bg-blue-50 rounded-xl">
 <p class="text-xs font-semibold text-slate-900 "></p>
 <p class="text-[10px] text-slate-500 mt-1"></p>
 </div>
 ).join('');
}

function renderAnomalies(items) {
 const container = document.getElementById('anomalies-list');
 if (!items || !items.length) {
 container.innerHTML = '<p class="text-xs text-slate-500">No anomalies detected.</p>';
 return;
 }
 const badgeColors = { 'Critical': 'bg-red-50 text-red-500', 'High': 'bg-orange-50 text-orange-500', 'Medium': 'bg-primary/10 text-primary', 'Low': 'bg-blue-50 text-blue-600' };

 container.innerHTML = items.slice(0, 3).map(a => 
 <div class="flex justify-between items-center p-3 border border-slate-100 rounded-xl">
 <div>
 <p class="text-xs font-semibold text-slate-900 "></p>
 <p class="text-[10px] text-slate-500 "></p>
 </div>
 <span class="px-1.5 py-0.5 rounded text-[10px] font-bold uppercase"></span>
 </div>
 ).join('');
}

function renderCostCenters() {
 const tbody = document.getElementById('cost-centers-tbody');
 const centers = [
 { name: 'Software Licenses', spend: 450000, util: 85 },
 { name: 'Cloud Infrastructure', spend: 820000, util: 92 },
 { name: 'Contractors', spend: 320000, util: 60 }
 ];
 tbody.innerHTML = centers.map(c => 
 <tr>
 <td class="px-6 py-3 font-medium text-slate-900 ">+c.name+</td>
 <td class="px-6 py-3 text-slate-600 ">+formatCurrencyShort(c.spend)+</td>
 <td class="px-6 py-3">
 <div class="flex items-center gap-2">
 <span class="text-xs font-semibold text-slate-600 ">+c.util+%</span>
 <div class="flex-1 h-1.5 bg-slate-100 rounded-full">
 <div class="h-full +(c.util>90?'bg-red-500':'bg-primary')+ rounded-full" style="width:+c.util+%"></div>
 </div>
 </div>
 </td>
 </tr>
 ).join('');
}

function formatCurrencyShort(val) {
 if (!val) return '?0';
 if (Math.abs(val) >= 10000000) return '?'+(val / 10000000).toFixed(1) + ' Cr';
 if (Math.abs(val) >= 100000) return '?'+(val / 100000).toFixed(1) + ' L';
 return '?'+val.toLocaleString('en-IN');
}

window.downloadChart = function(id, prefix) {
 const c = document.getElementById(id);
 if(!c) return;
 const a = document.createElement('a');
 a.download = prefix + '_Report.png';
 a.href = c.toDataURL('image/png');
 a.click();
}
