import { api } from './api.js';
import './auth.js';
import { autoBarChart, autoCategoricalChart, autoTimeSeriesChart, initEchart, safeSetOption } from './chart-engine.js';

/**
 * departments.js - Departments page using ECharts engine
 */

document.addEventListener('DOMContentLoaded', initDepartments);

import { state } from './state.js';

async function initDepartments() {
 await Promise.allSettled([
 loadDepartmentSummary(),
 loadDepartmentCharts(),
 loadDeptRecommendations(),
 ]);
 window.addEventListener('globalFiltersChanged', () => {
    initDepartments();
 });
}

async function loadDeptRecommendations() {
    try {
        const data = await api.get(api.endpoints.aiRecommendations);
        const container = document.getElementById('dept-ai-recommendation');
        if (!container) return;
        
        const items = Array.isArray(data) ? data : (data.items || []);
        if (items.length === 0) {
            container.innerHTML = '<p class="text-sm text-slate-500">No department insights currently.</p>';
            return;
        }
        
        // Pick one for department analysis (e.g. cost reduction)
        const rec = items.find(r => r.category === 'cost_reduction') || items[0];
        const colors = { 'High': 'text-rose-600 bg-rose-50', 'Medium': 'text-amber-500 bg-amber-50', 'Low': 'text-blue-600 bg-blue-50' };
        const colorClass = colors[rec.priority] || 'text-blue-600 bg-blue-50';
        
        container.innerHTML = `
            <div class="mb-2 flex items-center gap-2">
                <span class="text-xs uppercase font-bold px-2 py-0.5 rounded-full ${colorClass}">${rec.priority || 'Info'}</span>
                <span class="text-sm font-bold text-slate-800">${rec.title || rec.recommendation}</span>
            </div>
            <p class="text-xs text-slate-600 leading-relaxed mb-3">${rec.description || ''}</p>
            <button class="text-xs text-primary font-bold hover:underline flex items-center gap-1">
                Take Action <span class="material-symbols-outlined text-[14px]">arrow_forward</span>
            </button>
        `;
        
        const btnViewAll = document.getElementById('btn-view-all-dept-recs');
        if (btnViewAll && window.showModal) {
            btnViewAll.onclick = () => {
                const modalData = items.map(i => ({
                    Category: i.category,
                    Priority: i.priority,
                    Recommendation: i.title || i.recommendation,
                    Action: i.description || ''
                }));
                window.showModal("All Department Recommendations", ["Category", "Priority", "Recommendation", "Action"], modalData);
            };
        }
    } catch (err) {
        console.error('Failed to load dept recommendations:', err);
    }
}

let allDepts = [];

async function loadDepartmentSummary() {
 const container = document.getElementById('departments-grid') || document.querySelector('.table-container');
 
 try {
 const data = await api.get(api.endpoints.departmentSummary);
 allDepts = data.departments || [];

 if (!allDepts.length) {
 if (container) container.innerHTML = '<p class="text-slate-400 text-sm">No department data available.</p>';
 return;
 }

 renderDeptTable(allDepts);

 } catch (err) {
 console.error('Dept summary failed:', err);
 if (container) container.innerHTML = '<p class="text-red-500 text-sm">Failed to load departments</p>';
 }
}

async function loadDepartmentCharts() {
 try {
 // 1. Department Contribution (Treemap/Donut) from /charts
 const dataCharts = await api.get(api.endpoints.charts);
 const breakdown = dataCharts.department_breakdown || [];
 const treemapDom = document.getElementById('deptTreemap');
 if (breakdown.length && treemapDom) {
     autoCategoricalChart(treemapDom, breakdown.map(d => ({name: d.department || 'Unassigned', value: d.profit})), '');
 } else if (treemapDom) {
     treemapDom.innerHTML = `<div class="w-full h-full flex flex-col items-center justify-center text-slate-400 min-h-[300px]">
         <span class="material-symbols-outlined text-4xl mb-2">query_stats</span>
         <p class="text-sm font-semibold">No Data Available</p>
     </div>`;
 }
 
 // 2. Department Trend (Profit) from /departments/trend
 const dataTrend = await api.get(api.endpoints.departmentTrend);
 const trendDom = document.getElementById('dept-trend-chart');
 if (trendDom && dataTrend && dataTrend.periods && dataTrend.series) {
     let allSeries = [];
     
     // Calculate total profit for sorting
     for (const [dept, values] of Object.entries(dataTrend.series)) {
         const totalProfit = values.reduce((sum, v) => sum + (v || 0), 0);
         allSeries.push({
             name: dept,
             totalProfit,
             type: 'line',
             smooth: true,
             data: values,
             symbolSize: 4,
             lineStyle: { width: 3 },
             emphasis: { focus: 'series' }
         });
     }
     
     // Sort by total profit descending
     allSeries.sort((a, b) => b.totalProfit - a.totalProfit);
     
     // Default top 5 are selected
     let selectedDepts = new Set(allSeries.slice(0, 5).map(s => s.name));
     
     const myChart = initEchart(trendDom);
     
     const updateChart = () => {
         const activeSeries = allSeries.filter(s => selectedDepts.has(s.name));
         const option = {
             tooltip: { 
                 trigger: 'axis',
                 axisPointer: { type: 'cross', label: { backgroundColor: '#6a7985' } }
             },
             legend: { show: false }, // Using custom UI instead
             grid: { left: '3%', right: '4%', bottom: '12%', top: '20px', containLabel: true },
             xAxis: { type: 'category', boundaryGap: false, data: dataTrend.periods, axisLabel: { color: '#64748b', fontSize: 11 } },
             yAxis: { type: 'value', axisLabel: { color: '#64748b', fontSize: 11, formatter: (val) => formatCurrencyShort(val) }, splitLine: { lineStyle: { color: '#f1f5f9' } } },
             dataZoom: [
                 { type: 'inside', start: 0, end: 100 },
                 { type: 'slider', start: 0, end: 100, bottom: 5 }
             ],
             series: activeSeries
         };
         safeSetOption(myChart, option, true);
     };
     
     // Build custom multi-select UI
     let controlContainer = document.getElementById('dept-trend-controls');
     if (!controlContainer) {
         controlContainer = document.createElement('div');
         controlContainer.id = 'dept-trend-controls';
         controlContainer.className = 'flex flex-wrap gap-2 mb-4 px-4';
         trendDom.parentNode.insertBefore(controlContainer, trendDom);
     }
     
     const renderControls = () => {
         controlContainer.innerHTML = '';
         
         // Select Dropdown
         const selectWrapper = document.createElement('div');
         selectWrapper.className = 'relative mr-2';
         
         const select = document.createElement('select');
         select.className = 'appearance-none bg-white border border-slate-200 text-slate-700 py-1.5 pl-3 pr-8 rounded-lg text-sm font-semibold hover:border-primary focus:outline-none focus:ring-2 focus:ring-primary/20 cursor-pointer min-w-[160px]';
         select.innerHTML = `<option value="">+ Add Department...</option>` + 
            allSeries.filter(s => !selectedDepts.has(s.name)).map(s => `<option value="${s.name}">${s.name}</option>`).join('');
            
         select.onchange = (e) => {
             const val = e.target.value;
             if (val && selectedDepts.size < 8) {
                 selectedDepts.add(val);
                 renderControls();
                 updateChart();
             } else if (val) {
                 console.warn("Max 8 departments allowed");
                 select.value = '';
             }
         };
         
         const icon = document.createElement('span');
         icon.className = 'material-symbols-outlined absolute right-2 top-1/2 -translate-y-1/2 text-slate-400 pointer-events-none text-lg';
         icon.innerText = 'arrow_drop_down';
         
         selectWrapper.appendChild(select);
         selectWrapper.appendChild(icon);
         controlContainer.appendChild(selectWrapper);
         
         // Chips
         const chipsContainer = document.createElement('div');
         chipsContainer.className = 'flex flex-wrap gap-2 items-center';
         
         Array.from(selectedDepts).forEach(name => {
             const chip = document.createElement('div');
             chip.className = 'flex items-center gap-1 px-3 py-1 bg-primary/10 text-primary rounded-full text-xs font-bold border border-primary/20';
             chip.innerHTML = `<span>${name}</span>`;
             
             const removeBtn = document.createElement('button');
             removeBtn.className = 'material-symbols-outlined text-[14px] hover:text-red-500 cursor-pointer ml-1 leading-none';
             removeBtn.innerText = 'close';
             removeBtn.onclick = () => {
                 if (selectedDepts.size > 1) {
                     selectedDepts.delete(name);
                     renderControls();
                     updateChart();
                 }
             };
             
             chip.appendChild(removeBtn);
             chipsContainer.appendChild(chip);
         });
         
         controlContainer.appendChild(chipsContainer);
     };
     
     renderControls();
     updateChart();
     
     // Remove old HTML legend if it exists from previous design
     const oldHtmlLegend = trendDom.previousElementSibling?.querySelector?.('.flex.gap-4');
     if (oldHtmlLegend) oldHtmlLegend.style.display = 'none';
 }
 } catch (err) {
 console.error('Dept charts failed:', err);
 }
}

function renderDeptTable(depts) {
 const container = document.getElementById('departments-grid') || document.querySelector('.table-container');
 if (!container) return;

 const colors = ['bg-blue-500', 'bg-emerald-500', 'bg-orange-500', 'bg-pink-500', 'bg-violet-500'];
 const tableData = depts.map((d, i) => {
     return {
         ...d,
         color: colors[i % colors.length]
     }
 });

 if (window.deptMainTabulator) {
     window.deptMainTabulator.setData(tableData);
     return;
 }

 window.deptMainTabulator = new Tabulator(container, {
     data: tableData,
     layout: "fitColumns",
     responsiveLayout: "collapse",
     pagination: "local",
     paginationSize: 10,
     movableColumns: true,
     initialSort: [{column: "revenue", dir: "desc"}],
     columns: [
         {
             title: "Department", field: "domain", widthGrow: 2,
             formatter: function(cell) {
                 const d = cell.getData();
                 return `<div class="flex items-center gap-2 font-medium text-slate-900 cursor-pointer" onclick="window.location.href='department.html?dept=${encodeURIComponent(d.domain)}'">
                    <span class="w-2 h-2 rounded-full ${d.color}"></span> ${d.domain || 'Unassigned'}
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
             title: "Profit", field: "profit", hozAlign: "right",
             formatter: cell => `<span class="font-semibold">${formatCurrencyShort(cell.getValue())}</span>`
         },
         {
             title: "Margin", field: "profit_margin", hozAlign: "right",
             formatter: cell => `${(cell.getValue() || 0).toFixed(1)}%`
         }
     ]
 });
 
 // Add export buttons if they don't exist
 const parent = container.parentElement;
 if (parent && !parent.querySelector('.export-buttons')) {
     const btnContainer = document.createElement('div');
     btnContainer.className = 'export-buttons flex gap-2 justify-end mb-3 mt-3';
     btnContainer.innerHTML = `
         <button id="export-csv" class="px-3 py-1.5 text-xs font-semibold bg-white border border-slate-200 rounded-lg hover:bg-slate-50 transition text-slate-600 flex items-center gap-1"><span class="material-symbols-outlined text-sm">download</span> CSV</button>
         <button id="export-xlsx" class="px-3 py-1.5 text-xs font-semibold bg-white border border-slate-200 rounded-lg hover:bg-slate-50 transition text-slate-600 flex items-center gap-1"><span class="material-symbols-outlined text-sm">grid_on</span> Excel</button>
     `;
     parent.insertBefore(btnContainer, container);
     
     document.getElementById('export-csv').addEventListener('click', () => {
         window.deptMainTabulator.download("csv", "departments.csv");
     });
     // Require xlsx.js for actual excel export, fallback to csv for now
     document.getElementById('export-xlsx').addEventListener('click', () => {
         window.deptMainTabulator.download("csv", "departments_excel_compatible.csv");
     });
 }
}

function formatCurrencyShort(val) {
 if (val == null || isNaN(val)) return '—';
 const abs = Math.abs(val);
 if (abs >= 10000000) return '₹' + (val / 10000000).toFixed(2) + ' Cr';
 if (abs >= 100000) return '₹' + (val / 100000).toFixed(1) + ' L';
 return '₹' + val.toLocaleString('en-IN');
}
