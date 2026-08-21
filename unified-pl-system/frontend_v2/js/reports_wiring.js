import { api } from './api.js';
import './auth.js';
import { state } from './state.js';

document.addEventListener('DOMContentLoaded', initReports);

async function initReports() {
    window.addEventListener('globalFiltersChanged', loadReports);
    await loadReports();
    
    // Wire up Generate Report Modal
    const btnGenerate = document.getElementById('btn-generate-report');
    const modal = document.getElementById('generate-report-modal');
    const panel = document.getElementById('generate-report-panel');
    const closeBtn = document.getElementById('close-generate-modal');
    
    if (btnGenerate && modal) {
        btnGenerate.addEventListener('click', () => {
            modal.classList.remove('hidden');
            // Small delay to allow display block to apply before transition
            setTimeout(() => {
                modal.classList.remove('opacity-0');
                panel.classList.remove('scale-95');
                panel.classList.add('scale-100');
            }, 10);
        });
        
        const hideModal = () => {
            modal.classList.add('opacity-0');
            panel.classList.remove('scale-100');
            panel.classList.add('scale-95');
            setTimeout(() => {
                modal.classList.add('hidden');
            }, 300);
        };
        
        closeBtn.addEventListener('click', hideModal);
        
        // Handle Submit
        const submitBtn = document.getElementById('btn-submit-generate');
        if (submitBtn) {
            submitBtn.addEventListener('click', async () => {
                const type = document.getElementById('report-type').value;
                const format = document.querySelector('input[name="report-format"]:checked').value;
                const startDate = document.getElementById('report-start-date').value;
                const endDate = document.getElementById('report-end-date').value;
                const scope = document.getElementById('report-scope').value;
                
                // Add a new mock report to the table to reflect generation history
                const newReport = { 
                    id: Math.floor(Math.random() * 1000) + 6, 
                    name: `${type.replace(/ /g, '_')}_Generated`, 
                    category: 'Custom', 
                    type: type, 
                    date: new Date().toLocaleString(), 
                    author: 'Current User', 
                    format: format, 
                    size: '--', 
                    status: 'Processing' 
                };
                
                if (window.reportsTabulator) {
                    window.reportsTabulator.addRow(newReport, true);
                }
                
                try {
                    submitBtn.innerText = 'Generating...';
                    await api.download('/api/v1/reports/generate', `${type.replace(/ /g, '_')}_Report.${format.toLowerCase()}`, {
                        method: 'POST',
                        body: {
                            format: format.toLowerCase(),
                            type: type,
                            scope: scope,
                            start_date: startDate,
                            end_date: endDate
                        }
                    });
                } catch(e) {
                    console.error("Failed to generate report", e);
                    alert("Failed to generate report");
                } finally {
                    submitBtn.innerText = 'Generate';
                    hideModal();
                }
            });
        }
        
        // Handle Download All
        const downloadAllBtn = document.getElementById('btn-download-all');
        if (downloadAllBtn) {
            downloadAllBtn.addEventListener('click', () => {
                if (window.reportsTabulator) {
                    window.reportsTabulator.download('csv', 'all_reports_export.csv');
                }
                hideModal();
            });
        }
    }
}

async function loadReports() {
    const container = document.getElementById('reports-grid');
    if (!container) return;

    // In a real scenario, this would fetch from an API like:
    // const query = window.location.search;
    // const data = await api.get('/api/v1/pl/reports' + query);
    
    // For now, we mock reports based on current state filters
    const currentDept = state.filters.department || 'All';
    const mockReports = [
        { id: 1, name: `P&L_${state.filters.date.replace(/ /g, '_')}`, category: 'Financial', type: 'P&L Report', date: 'May 19, 2025 10:30 AM', author: 'Rutvik Wankhede', format: 'PDF', size: '2.4 MB', status: 'Completed' },
        { id: 2, name: `${currentDept}_Performance`, category: 'Department', type: 'Performance Report', date: 'May 18, 2025 03:15 PM', author: 'System (Auto)', format: 'Excel', size: '1.8 MB', status: 'Completed' },
        { id: 3, name: `Anomaly_Report`, category: 'Analytics', type: 'Anomaly Report', date: 'May 18, 2025 11:45 AM', author: 'Rutvik Wankhede', format: 'PDF', size: '1.6 MB', status: 'Completed' },
        { id: 4, name: `Forecast_Q2_2025`, category: 'Strategic', type: 'Forecast', date: 'May 17, 2025 01:20 PM', author: 'System (Auto)', format: 'Excel', size: '3.1 MB', status: 'Completed' },
        { id: 5, name: `Cost_Center_Audit_Q2`, category: 'Compliance', type: 'Audit', date: 'May 19, 2025 12:10 PM', author: 'Sarah Jenkins', format: 'PDF', size: '--', status: 'Processing' },
    ];

    if (window.reportsTabulator) {
        window.reportsTabulator.setData(mockReports);
        return;
    }

    window.reportsTabulator = new Tabulator(container, {
        data: mockReports,
        layout: "fitColumns",
        responsiveLayout: "collapse",
        pagination: "local",
        paginationSize: 10,
        movableColumns: true,
        initialSort: [{column: "date", dir: "desc"}],
        columns: [
            {
                title: "Report Name", field: "name", widthGrow: 2,
                formatter: function(cell) {
                    const d = cell.getData();
                    const iconColor = d.format === 'Excel' ? 'bg-green-50 text-green-600' : 'bg-purple-50 text-purple-600';
                    const icon = d.format === 'Excel' ? 'grid_on' : 'picture_as_pdf';
                    return `<div class="flex items-center gap-3">
                        <div class="w-8 h-8 ${iconColor} rounded flex items-center justify-center">
                            <span class="material-symbols-outlined text-sm">${icon}</span>
                        </div>
                        <span class="font-semibold text-gray-700">${d.name}</span>
                    </div>`;
                }
            },
            { title: "Category", field: "category" },
            { title: "Type", field: "type" },
            { title: "Generated On", field: "date" },
            { title: "Generated By", field: "author" },
            { title: "Format", field: "format" },
            { title: "Size", field: "size" },
            {
                title: "Status", field: "status", hozAlign: "center",
                formatter: function(cell) {
                    const status = cell.getValue();
                    if (status === 'Completed') {
                        return `<span class="px-3 py-1 bg-status-green text-status-green-text text-[11px] font-bold rounded-full">Completed</span>`;
                    }
                    return `<span class="px-3 py-1 bg-orange-50 text-orange-600 text-[11px] font-bold rounded-full">Processing</span>`;
                }
            },
            {
                title: "Actions", field: "actions", hozAlign: "right", headerSort: false,
                formatter: function(cell) {
                    const d = cell.getData();
                    if (d.status === 'Processing') {
                        return `<div class="flex items-center justify-end gap-3 text-gray-400">
                            <span class="material-symbols-outlined text-sm cursor-not-allowed opacity-50">download</span>
                            <span class="material-symbols-outlined text-sm cursor-not-allowed opacity-50">share</span>
                            <span class="material-symbols-outlined text-sm cursor-pointer hover:text-red-500 transition-colors">delete</span>
                        </div>`;
                    }
                    return `<div class="flex items-center justify-end gap-3 text-gray-400">
                        <span class="material-symbols-outlined text-sm cursor-pointer hover:text-primary transition-colors" onclick="window.reportsTabulator.download('csv', '${d.name}.csv')">download</span>
                        <span class="material-symbols-outlined text-sm cursor-pointer hover:text-primary transition-colors">share</span>
                        <span class="material-symbols-outlined text-sm cursor-pointer hover:text-primary transition-colors">more_vert</span>
                    </div>`;
                }
            }
        ]
    });
}
