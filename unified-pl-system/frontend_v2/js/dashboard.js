import { api } from './api.js';
import './auth.js';
import { autoCategoricalChart, autoTimeSeriesChart, autoBarChart, renderDashboardMainChart, renderSparkline } from './chart-engine.js';

document.addEventListener('DOMContentLoaded', initDashboard);

async function initDashboard() {
 setGreeting();
 await Promise.allSettled([
 loadKPIs(),
 loadCharts(),
 loadRecommendations(),
 loadAnomalies(),
 loadTopCostCenters(),
 loadScheduledReports(),
 ]);
 initGlobalFilters();
 initInsightsModal();
}

import { state } from './state.js';

function initGlobalFilters() {
    window.addEventListener('globalFiltersChanged', (e) => {
        initDashboard();
    });
}

function initInsightsModal() {
    const btn = document.getElementById('viewAllInsightsBtn');
    const modal = document.getElementById('insightsModal');
    const closeBtn = document.getElementById('closeInsightsModal');
    
    if(btn && modal && closeBtn) {
        btn.addEventListener('click', async () => {
            modal.classList.remove('hidden');
            await loadFullInsights();
        });
        
        closeBtn.addEventListener('click', () => {
            modal.classList.add('hidden');
        });
        
        modal.addEventListener('click', (e) => {
            if(e.target === modal) modal.classList.add('hidden');
        });
    }
}

async function loadFullInsights() {
    try {
        const data = await api.get(`${api.endpoints.aiRecommendations}?limit=all`);
        const items = Array.isArray(data) ? data : (data.items || []);
        
        const insightsContainer = document.getElementById('full-insights-list');
        const recsContainer = document.getElementById('full-recommendations-list');
        
        if(!insightsContainer || !recsContainer) return;
        
        if(items.length === 0) {
            insightsContainer.innerHTML = '<p class="text-sm text-slate-500">No insights available.</p>';
            recsContainer.innerHTML = '<p class="text-sm text-slate-500">No recommendations available.</p>';
            return;
        }
        
        const icons = { 'cost_reduction': 'savings', 'revenue_growth': 'trending_up', 'risk_mitigation': 'shield', 'default': 'lightbulb' };
        const colors = { 'High': 'text-rose-600 bg-rose-50', 'Medium': 'text-amber-500 bg-amber-50', 'Low': 'text-blue-600 bg-blue-50' };

        const html = items.map(r => {
            const icon = icons[r.category] || icons.default;
            const colorClass = colors[r.priority] || 'text-blue-600 bg-blue-50';
            return `
            <div class="p-4 bg-slate-50 rounded-xl flex gap-4 border border-slate-100">
                <div class="w-10 h-10 rounded-xl ${colorClass} flex-shrink-0 flex items-center justify-center">
                    <span class="material-symbols-outlined">${icon}</span>
                </div>
                <div>
                    <div class="flex items-center gap-2 mb-1">
                        <h4 class="font-bold text-slate-900">${r.title || r.recommendation || 'AI Insight'}</h4>
                        <span class="text-[10px] uppercase font-bold px-2 py-0.5 rounded-full ${colorClass}">${r.priority || 'Info'}</span>
                    </div>
                    <p class="text-sm text-slate-600 leading-relaxed">${r.description || ''}</p>
                    <p class="text-xs text-slate-400 mt-2 flex items-center gap-1">
                        <span class="material-symbols-outlined text-[12px]">schedule</span> ${r.created_at ? new Date(r.created_at).toLocaleString() : 'Just now'}
                    </p>
                </div>
            </div>`;
        }).join('');
        
        insightsContainer.innerHTML = html;
        
        // Since both are recommendations from backend, we just show recommendations here.
        // We'll populate the recommendations list similarly.
        recsContainer.innerHTML = html;
        
    } catch (err) {
        console.error('Failed to load full insights:', err);
    }
}


function setGreeting() {
 const greetingEl = document.getElementById('greeting-text');
 if (!greetingEl) return;
 const hour = new Date().getHours();
 const part = hour < 12 ? 'morning' : hour < 18 ? 'afternoon' : 'evening';
 
 try {
 const token = api.getAccessToken();
 if (token) {
 const payload = JSON.parse(atob(token.split('.')[1]));
 const name = payload.sub || 'there';
 greetingEl.textContent = `Good ${part}, ${name}! 👋`;
 return;
 }
 } catch (_) {}
 greetingEl.textContent = `Good ${part}! 👋`;
}

async function loadKPIs() {
 try {
 const data = await api.get(`${api.endpoints.summary}${window.location.search}`);
 const kpis = data.kpis;
 if (!kpis) return;

 setEl('kpi-revenue', formatCurrency(kpis.revenue));
 setEl('kpi-expense', formatCurrency(kpis.expense));
 setEl('kpi-profit', formatCurrency(kpis.profit));
 // Use real forecast from API, don't estimate from profit
 setEl('kpi-forecast', kpis.forecasted_profit != null
 ? formatCurrency(kpis.forecasted_profit)
 : formatCurrency(kpis.forecast_profit) || '—');
 setEl('kpi-health-score', Math.round(kpis.health_score ?? 0) || '—');
 setEl('kpi-anomalies', kpis.active_anomalies ?? 0);
 setEl('kpi-health-label', getHealthLabel(kpis.health_score));
 
 // Render Mini Sparklines
 const randData = () => Array.from({length: 10}, () => Math.random() * 100);
 renderSparkline('spark-liquidity', randData(), '#10b981');
 renderSparkline('spark-debt', randData(), '#6366f1');
 renderSparkline('spark-margin', randData(), '#f59e0b');
 renderSparkline('spark-netmargin', randData(), '#2563eb');
 renderSparkline('spark-current', randData(), '#059669');
 renderSparkline('spark-ccc', randData(), '#4f46e5');
 renderSparkline('spark-roa', randData(), '#db2777');
 renderSparkline('spark-roe', randData(), '#9333ea');
 renderSparkline('spark-quality-trend', randData(), '#10b981');
 
 } catch (err) {
 console.error('KPI load failed:', err);
 }
}

async function loadCharts() {
 try {
 const data = await api.get(`${api.endpoints.charts}${window.location.search}`);
 if (!data) return;

 const mainChartDom = document.getElementById('mainChart');
 if (mainChartDom && data.revenue_trend && data.expense_trend) {
 const dates = data.revenue_trend.map(d => d.period);
 const rev = data.revenue_trend.map(d => d.value);
 const exp = data.expense_trend.map(d => d.value);
 const prof = data.revenue_trend.map((d, i) => d.value - data.expense_trend[i].value);
 window.mainChartInstance = renderDashboardMainChart(mainChartDom, dates, rev, exp, prof);
 }

 const cashFlowDom = document.getElementById('cashFlowChart');
 if (cashFlowDom && data.revenue_trend && data.expense_trend) {
 const dates = data.revenue_trend.map(d => d.period);
 const values = data.revenue_trend.map((d, i) => d.value - data.expense_trend[i].value);
 window.cashFlowChartInstance = autoTimeSeriesChart(cashFlowDom, dates, values, 'Free Cash Flow');
 }
 } catch (err) {
 console.error('Charts load failed:', err);
 }
}

async function loadTopCostCenters() {
 try {
 const data = await api.get(`${api.endpoints.summary}${window.location.search}`);
 if (data && data.domains) {
 renderDeptTable(data.domains);
 const deptFilter = document.getElementById('global-dept-filter');
 if (deptFilter && deptFilter.options.length === 1) {
 data.domains.forEach(d => {
 const opt = document.createElement('option');
 opt.value = d.domain;
 opt.textContent = d.domain;
 deptFilter.appendChild(opt);
 });
 const urlParams = new URLSearchParams(window.location.search);
 if (urlParams.has('dept')) deptFilter.value = urlParams.get('dept');
 }
 }
 } catch (err) {
 console.error('Top Cost Centers load failed:', err);
 }
}

async function loadScheduledReports() {
 try {
 const data = await api.get(api.endpoints.reports);
 const container = document.getElementById('scheduled-reports-container');
 if (!container) return;

 const items = Array.isArray(data) ? data : (data.items || []);
 if (items.length === 0) {
 container.innerHTML = '<p class="text-xs text-slate-500 p-3">No scheduled reports. <a href="reports.html" class="text-blue-600 font-semibold">Schedule one →</a></p>';
 return;
 }

 const statusColors = { 'READY': 'bg-emerald-50 text-emerald-600', 'SCHEDULED': 'bg-blue-50 text-blue-600', 'FAILED': 'bg-rose-50 text-rose-600', 'GENERATING': 'bg-amber-50 text-amber-600' };
 
 container.innerHTML = items.slice(0, 4).map(r => {
 const status = r.status || 'SCHEDULED';
 const colorClass = statusColors[status] || statusColors.SCHEDULED;
 const date = r.scheduled_for ? new Date(r.scheduled_for).toLocaleDateString() : 'Next run pending';

 return `
 <div class="flex items-center justify-between p-3 border border-slate-200 rounded-xl hover:bg-slate-50 transition-colors cursor-pointer" onclick="window.location.href='reports.html'">
 <div class="flex items-center gap-3">
 <div class="w-10 h-10 ${colorClass} rounded-lg flex items-center justify-center flex-shrink-0">
 <span class="material-symbols-outlined text-sm">event_note</span>
 </div>
 <div>
 <p class="text-xs font-bold text-slate-900">${r.name || 'Financial Report'}</p>
 <p class="text-[10px] text-slate-500">${date} • ${r.frequency || 'Weekly'}</p>
 </div>
 </div>
 <span class="${colorClass} px-2 py-0.5 rounded text-[10px] font-bold uppercase">${status}</span>
 </div>`;
 }).join('');
 } catch (err) {
 console.error('Reports load failed:', err);
 const container = document.getElementById('scheduled-reports-container');
 if (container) container.innerHTML = '<p class="text-xs text-slate-500 p-3">Could not load scheduled reports.</p>';
 }
}

async function loadRecommendations() {
 try {
 const data = await api.get(api.endpoints.aiRecommendations);
 const container = document.getElementById('ai-insights-container');
 if (!container) return;

 const items = Array.isArray(data) ? data : (data.items || []);
 if (items.length === 0) {
 container.innerHTML = '<p class="text-xs text-slate-500 p-3">No AI insights available yet. Upload data to generate recommendations.</p>';
 return;
 }

 const icons = { 'cost_reduction': 'savings', 'revenue_growth': 'trending_up', 'risk_mitigation': 'shield', 'default': 'lightbulb' };
 const colors = { 'High': 'text-rose-600 bg-rose-50', 'Medium': 'text-amber-500 bg-amber-50', 'Low': 'text-blue-600 bg-blue-50' };

 container.innerHTML = items.slice(0, 4).map(r => {
 const icon = icons[r.category] || icons.default;
 const colorClass = colors[r.priority] || 'text-blue-600 bg-blue-50';
 return `
 <div class="p-3 bg-white rounded-xl flex gap-3 border border-slate-100">
 <div class="w-8 h-8 rounded-lg ${colorClass} flex-shrink-0 flex items-center justify-center">
 <span class="material-symbols-outlined text-sm">${icon}</span>
 </div>
 <p class="text-xs text-slate-600 leading-relaxed">
 <span class="font-bold text-slate-900">${r.title || r.recommendation || 'AI Insight'}</span>
 ${r.description ? ' — ' + r.description.substring(0, 80) + '...' : ''}
 </p>
 </div>`;
 }).join('');
 } catch (err) {
 console.error('Recommendations load failed:', err);
 }
}

async function loadAnomalies() {
 try {
 const data = await api.get(`${api.endpoints.anomalies}${window.location.search}`);
 const summaryData = await api.get(`${api.endpoints.summary}${window.location.search}`);
 const items = Array.isArray(data) ? data : [];

 const totalEl = document.getElementById('anomaly-total');
 if (totalEl) totalEl.textContent = summaryData.kpis?.active_anomalies ?? items.length;

 const critical = items.filter(a => a.severity === 'Critical').length;
 const high = items.filter(a => a.severity === 'High').length;
 const medium = items.filter(a => a.severity === 'Medium').length;
 const low = items.filter(a => a.severity === 'Low').length;

 const chartDom = document.getElementById('anomalyChart');
 if (chartDom) {
 const chartData = [
 { name: 'Critical', value: critical },
 { name: 'High', value: high },
 { name: 'Medium', value: medium },
 { name: 'Low', value: low }
 ].filter(d => d.value > 0);
 
 window.anomalyChartInstance = autoCategoricalChart(chartDom, chartData, 'Severity');
 }

 const alertsContainer = document.getElementById('alerts-list-container');
 if (alertsContainer && items.length > 0) {
 const topItems = items.sort((a,b) => {
 const s = { 'Critical': 4, 'High': 3, 'Medium': 2, 'Low': 1 };
 return (s[b.severity] || 0) - (s[a.severity] || 0);
 }).slice(0, 3);
 
 const badgeColors = { 'Critical': 'bg-rose-50 text-rose-600', 'High': 'bg-amber-50 text-amber-600', 'Medium': 'bg-blue-50 text-blue-600', 'Low': 'bg-emerald-50 text-emerald-600' };

 alertsContainer.innerHTML = topItems.map(a => `
 <div class="p-3 bg-white rounded-xl border border-slate-200 flex flex-col cursor-pointer hover:bg-slate-50 transition" onclick="window.location.href='anomaly.html?id=${a.id}'">
 <div class="flex items-center justify-between mb-1">
 <span class="text-xs font-bold text-slate-900 truncate">${a.line_item || a.description || 'Alert'}</span>
 <span class="px-1.5 py-0.5 rounded ${badgeColors[a.severity] || badgeColors.Low} text-[10px] font-bold uppercase">${a.severity}</span>
 </div>
 <p class="text-[10px] text-slate-500">${a.description || 'Action required'}</p>
 </div>
 `).join('');
 } else if (alertsContainer) {
 alertsContainer.innerHTML = '<p class="text-xs text-slate-500 p-3">No active alerts.</p>';
 }
 } catch (err) {
 console.error('Anomalies load failed:', err);
 }
}

function renderDeptTable(depts = []) {
 const container = document.getElementById('dept-perf-tbody');
 if (!container || !depts.length) return;
 
 // If it's a tbody, we need to replace the entire table with a div for Tabulator
 let tableEl = container.closest('table');
 let targetDom = container;
 
 if (tableEl) {
    const newDiv = document.createElement('div');
    newDiv.id = 'dept-perf-grid';
    newDiv.className = 'w-full';
    tableEl.parentNode.replaceChild(newDiv, tableEl);
    targetDom = newDiv;
 } else {
    targetDom = document.getElementById('dept-perf-grid') || container;
 }

 const icons = ['account_balance', 'store', 'laptop', 'campaign', 'groups', 'precision_manufacturing'];
 const colors = ['text-blue-600 bg-blue-50', 'text-emerald-500 bg-emerald-50', 'text-indigo-500 bg-indigo-50', 'text-pink-500 bg-pink-50', 'text-amber-500 bg-amber-50', 'text-purple-500 bg-purple-50'];

 const tableData = depts.map((d, i) => {
     return {
         ...d,
         icon: icons[i % icons.length],
         color: colors[i % colors.length]
     }
 });

 if (window.deptTabulator) {
     window.deptTabulator.setData(tableData);
     return;
 }

 window.deptTabulator = new Tabulator(targetDom, {
     data: tableData,
     layout: "fitColumns",
     responsiveLayout: "collapse",
     pagination: "local",
     paginationSize: 5,
     movableColumns: true,
     initialSort: [{column: "revenue", dir: "desc"}],
     columns: [
         {
             title: "Department", field: "domain", widthGrow: 2,
             formatter: function(cell) {
                 const d = cell.getData();
                 return `<div class="flex items-center gap-2 cursor-pointer" onclick="window.location.href='department.html?dept=${encodeURIComponent(d.domain)}'">
                    <div class="w-6 h-6 rounded ${d.color} flex items-center justify-center">
                        <span class="material-symbols-outlined text-sm">${d.icon}</span>
                    </div>
                    <span class="font-semibold text-slate-900">${d.domain}</span>
                 </div>`;
             }
         },
         {
             title: "Revenue", field: "revenue", hozAlign: "right",
             formatter: cell => formatCurrencyShort(cell.getValue())
         },
         {
             title: "Expense", field: "expense", hozAlign: "right",
             formatter: cell => formatCurrencyShort(cell.getValue())
         },
         {
             title: "Budget Used", field: "budget_used", hozAlign: "center",
             formatter: function(cell) {
                 const val = cell.getValue() || 0;
                 return `<div class="flex flex-col gap-1 text-xs text-slate-500 w-full px-2">
                    <span class="text-right">${val}%</span>
                    <div class="w-full h-1.5 bg-slate-200 rounded-full overflow-hidden">
                        <div class="h-full ${val > 90 ? 'bg-rose-500' : 'bg-blue-600'} rounded-full" style="width:${Math.min(100, val)}%"></div>
                    </div>
                 </div>`;
             }
         },
         {
             title: "Trend", field: "trend", hozAlign: "right",
             formatter: function(cell) {
                 const val = cell.getValue() || 0;
                 const isDown = val < 0;
                 return `<span class="text-xs font-semibold ${!isDown ? 'text-rose-500' : 'text-emerald-500'} flex items-center justify-end gap-1">
                    <span class="material-symbols-outlined text-sm">${!isDown ? 'arrow_upward' : 'arrow_downward'}</span> ${Math.abs(val)}%
                 </span>`;
             }
         }
     ]
 });
}

function setEl(id, value) {
 const el = document.getElementById(id);
 if (el) el.textContent = value;
}

function formatCurrency(val) {
 if (val == null || isNaN(val)) return '—';
 const abs = Math.abs(val);
 if (abs >= 10000000) return '₹' + (val / 10000000).toFixed(2) + ' Cr';
 if (abs >= 100000) return '₹' + (val / 100000).toFixed(2) + ' L';
 return new Intl.NumberFormat('en-IN', { style: 'currency', currency: 'INR', maximumFractionDigits: 0 }).format(val);
}

function formatCurrencyShort(val) {
 if (val == null || isNaN(val)) return '—';
 const abs = Math.abs(val);
 if (abs >= 10000000) return (val / 10000000).toFixed(2) + ' Cr';
 if (abs >= 100000) return (val / 100000).toFixed(1) + ' L';
 return val.toLocaleString('en-IN');
}

function getHealthLabel(score) {
 if (score >= 90) return 'Excellent';
 if (score >= 75) return 'Good';
 if (score >= 60) return 'Fair';
 return 'Critical';
}
