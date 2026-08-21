import { api } from './api.js';
import './auth.js';
import { autoTimeSeriesChart } from './chart-engine.js';

/**
 * department.js - Single Department Detail page
 */

document.addEventListener('DOMContentLoaded', initDepartmentDetail);

async function initDepartmentDetail() {
 const urlParams = new URLSearchParams(window.location.search);
 const deptName = urlParams.get('dept') || 'Finance'; // Fallback to Finance if none specified
 
 document.getElementById('dept-title').textContent = deptName;

 try {
 // We would normally fetch specific dept details here.
 // For now, fetch summary and filter for the dept
 const summaryData = await api.get(api.endpoints.summary);
 const depts = summaryData.domains || [];
 
 const dept = depts.find(d => d.domain.toLowerCase() === deptName.toLowerCase());
 
 if (dept) {
 setEl('kpi-rev', formatCurrencyShort(dept.revenue));
 setEl('kpi-exp', formatCurrencyShort(dept.expense));
 setEl('kpi-profit', formatCurrencyShort(dept.profit));
 setEl('kpi-margin', (dept.profit_margin || 0).toFixed(1) + '%');
 
 const health = dept.health_score || 0;
 setEl('kpi-risk', health >= 80 ? 'Low' : health >= 60 ? 'Medium' : 'High');
 setEl('kpi-variance', dept.profit >= 0 ? '+5.2%' : '-2.1%'); // Placeholder variance
 
 // Calculate rank
 const sorted = [...depts].sort((a, b) => b.revenue - a.revenue);
 const rank = sorted.findIndex(d => d.domain === dept.domain) + 1;
 setEl('kpi-ranking', `#${rank} of ${depts.length}`);
 } else {
 document.getElementById('dept-title').textContent = deptName + ' (Not Found)';
 }

 // Load Charts
 const chartData = await api.get(api.endpoints.charts);
 if (chartData && chartData.revenue_trend && chartData.expense_trend) {
 const trendDom = document.getElementById('dept-detail-chart');
 if (trendDom) {
 const dates = chartData.revenue_trend.map(d => d.period);
 // Simulate department-specific trend by scaling
 const scale = (dept ? dept.revenue : 100000) / 1000000;
 const values = chartData.revenue_trend.map((d, i) => (d.value - chartData.expense_trend[i].value) * scale);
 autoTimeSeriesChart(trendDom, dates, values, 'Profit Trend');
 }
 }

 // Load Cost centers
 const tbody = document.getElementById('cost-centers-tbody');
 if (tbody) {
 //  cost centers for the department
 const costCenters = [
 { name: 'Personnel', spend: (dept?.expense || 500000) * 0.6, utilized: 95 },
 { name: 'Software', spend: (dept?.expense || 500000) * 0.2, utilized: 80 },
 { name: 'Travel', spend: (dept?.expense || 500000) * 0.1, utilized: 45 },
 { name: 'Misc', spend: (dept?.expense || 500000) * 0.1, utilized: 110 }
 ];
 
 tbody.innerHTML = costCenters.map(c => `
 <tr>
 <td class="px-6 py-4 font-medium text-slate-900">${c.name}</td>
 <td class="px-6 py-4 text-slate-600">${formatCurrencyShort(c.spend)}</td>
 <td class="px-6 py-4">
 <div class="flex flex-col gap-1 text-xs text-slate-500">
 ${c.utilized}%
 <div class="w-full h-1.5 bg-slate-200 rounded-full overflow-hidden">
 <div class="h-full ${c.utilized > 100 ? 'bg-rose-500' : 'bg-blue-600'} rounded-full" style="width:${Math.min(100, c.utilized)}%"></div>
 </div>
 </div>
 </td>
 </tr>
 `).join('');
 }

 // Load Anomalies
 const anomalyData = await api.get(api.endpoints.anomalies);
 const anomalies = anomalyData || [];
 const list = document.getElementById('anomalies-list');
 if (list) {
 if (anomalies.length > 0) {
 list.innerHTML = anomalies.slice(0, 3).map(a => `
 <div class="p-3 bg-rose-50 text-rose-600 rounded-lg text-sm border border-rose-100 cursor-pointer" onclick="window.location.href='anomaly.html?id=${a.id}'">
 <strong>${a.severity}</strong>: ${a.description}
 </div>
 `).join('');
 } else {
 list.innerHTML = '<p class="text-sm text-slate-500 text-center py-4">No active anomalies.</p>';
 }
 }

 // Load AI Recs
 const recData = await api.get(api.endpoints.aiRecommendations);
 const recs = recData.items || recData || [];
 const recList = document.getElementById('ai-recs');
 if (recList) {
 if (recs.length > 0) {
 recList.innerHTML = recs.slice(0, 3).map(r => `
 <div class="p-3 bg-blue-50 text-blue-700 rounded-lg text-sm border border-blue-100">
 <strong>Insight:</strong> ${r.title || r.recommendation}
 </div>
 `).join('');
 } else {
 recList.innerHTML = '<p class="text-sm text-slate-500 py-4">No AI recommendations available.</p>';
 }
 }

 } catch (err) {
 console.error('Dept detail failed:', err);
 }
}

function setEl(id, val) { const el = document.getElementById(id); if (el) el.textContent = val; }

function formatCurrencyShort(val) {
 if (val == null || isNaN(val)) return '—';
 const abs = Math.abs(val);
 if (abs >= 10000000) return '₹' + (val / 10000000).toFixed(2) + ' Cr';
 if (abs >= 100000) return '₹' + (val / 100000).toFixed(1) + ' L';
 return '₹' + val.toLocaleString('en-IN');
}
