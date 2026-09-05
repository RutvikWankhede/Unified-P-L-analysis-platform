import { api } from './api.js';
import './auth.js';
import { state } from './state.js';

document.addEventListener('DOMContentLoaded', initExport);

function initExport() {
    const draggables = document.querySelectorAll('[draggable="true"]');
    const dropZone = document.querySelector('.border-dashed');
    const tableHead = document.querySelector('thead tr');
    const tableBody = document.querySelector('tbody');

    let selectedColumns = ['Date', 'Department'];

    draggables.forEach(draggable => {
        draggable.addEventListener('dragstart', () => {
            draggable.classList.add('opacity-50');
            draggable.dataset.dragging = 'true';
        });

        draggable.addEventListener('dragend', () => {
            draggable.classList.remove('opacity-50');
            delete draggable.dataset.dragging;
        });
    });

    dropZone.addEventListener('dragover', e => {
        e.preventDefault();
        dropZone.classList.add('bg-primary/5');
    });

    dropZone.addEventListener('dragleave', () => {
        dropZone.classList.remove('bg-primary/5');
    });

    dropZone.addEventListener('drop', e => {
        e.preventDefault();
        dropZone.classList.remove('bg-primary/5');
        
        const dragged = document.querySelector('[data-dragging="true"]');
        if (!dragged) return;

        const columnName = dragged.querySelector('span').innerText;
        
        if (!selectedColumns.includes(columnName)) {
            selectedColumns.push(columnName);
            renderSelectedColumns();
            renderTablePreview();
        }
    });

    function renderSelectedColumns() {
        // Clear all except the drop placeholder text
        const placeholder = dropZone.querySelector('.text-slate-400');
        dropZone.innerHTML = '';
        
        selectedColumns.forEach(col => {
            const el = document.createElement('div');
            el.className = 'px-4 py-2 bg-primary/10 text-primary border border-primary/20 rounded-lg text-sm font-semibold flex items-center gap-2 flex-shrink-0';
            el.innerHTML = `${col} <button class="hover:text-red-500 remove-col" data-col="${col}"><span class="material-symbols-outlined text-[14px]">close</span></button>`;
            dropZone.appendChild(el);
        });
        
        dropZone.appendChild(placeholder);
        
        // Add remove listeners
        document.querySelectorAll('.remove-col').forEach(btn => {
            btn.addEventListener('click', (e) => {
                const col = e.currentTarget.dataset.col;
                selectedColumns = selectedColumns.filter(c => c !== col);
                renderSelectedColumns();
                renderTablePreview();
            });
        });
    }

    function renderTablePreview() {
        // Update Headers
        tableHead.innerHTML = '';
        selectedColumns.forEach(col => {
            const th = document.createElement('th');
            th.className = 'p-3';
            th.innerText = col;
            tableHead.appendChild(th);
        });
        const addColTh = document.createElement('th');
        addColTh.className = 'p-3 text-slate-300';
        addColTh.innerHTML = '<em>+ Add Column</em>';
        tableHead.appendChild(addColTh);

        // Update Rows (Mock Data for preview)
        const mockRows = [
            { 'Date': '2025-05-01', 'Department': 'Sales', 'Gross Revenue': '₹45,00,000', 'Net Profit': '₹12,00,000', 'Operating Expenses': '₹33,00,000', 'EBITDA': '₹15,00,000', 'Department ID': 'D01' },
            { 'Date': '2025-05-01', 'Department': 'Marketing', 'Gross Revenue': '₹25,00,000', 'Net Profit': '₹4,00,000', 'Operating Expenses': '₹21,00,000', 'EBITDA': '₹5,00,000', 'Department ID': 'D02' },
            { 'Date': '2025-05-02', 'Department': 'Sales', 'Gross Revenue': '₹48,00,000', 'Net Profit': '₹13,50,000', 'Operating Expenses': '₹34,50,000', 'EBITDA': '₹16,00,000', 'Department ID': 'D01' }
        ];

        tableBody.innerHTML = '';
        mockRows.forEach(row => {
            const tr = document.createElement('tr');
            selectedColumns.forEach(col => {
                const td = document.createElement('td');
                td.className = 'p-3';
                td.innerText = row[col] || '--';
                tr.appendChild(td);
            });
            const emptyTd = document.createElement('td');
            emptyTd.className = 'p-3';
            tr.appendChild(emptyTd);
            tableBody.appendChild(tr);
        });
    }

    // Attach export function to window
    window.exportReport = async function() {
        const btn = document.querySelector('button[onclick="exportReport()"]');
        const origText = btn.innerHTML;
        btn.innerHTML = '<span class="material-symbols-outlined text-sm animate-spin">refresh</span> Exporting...';
        
        try {
            // Simulated delay for export
            await new Promise(r => setTimeout(r, 1000));
            // In a real scenario: await api.download('/api/v1/reports/csv', 'Custom_Export.csv', { method: 'POST', body: { columns: selectedColumns } });
            
            // For now, create a mock CSV and download it
            let csvContent = "data:text/csv;charset=utf-8," + selectedColumns.join(",") + "\n";
            csvContent += selectedColumns.map(c => "MockData").join(",") + "\n";
            
            const encodedUri = encodeURI(csvContent);
            const link = document.createElement("a");
            link.setAttribute("href", encodedUri);
            link.setAttribute("download", "custom_report.csv");
            document.body.appendChild(link);
            link.click();
            document.body.removeChild(link);
            
        } catch (e) {
            console.error(e);
            alert("Export failed");
        } finally {
            btn.innerHTML = origText;
        }
    };

    // Initial render
    renderSelectedColumns();
    renderTablePreview();
}
