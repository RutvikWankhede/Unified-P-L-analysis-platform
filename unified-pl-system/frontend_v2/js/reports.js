import { api } from './api.js';
import './auth.js';

window.nextStep = function(step) {
 // Hide all
 for(let i=1; i<=4; i++) {
 const el = document.getElementById('step-' + i);
 if(el) el.classList.add('hidden');
 
 // Header styling
 const header = document.querySelector(\[data-step="\"]\);
 if(header) {
 if(i <= step) {
 header.classList.add('step-active');
 header.classList.remove('text-slate-400');
 } else {
 header.classList.remove('step-active');
 header.classList.add('text-slate-400');
 }
 }
 }
 
 // Show target
 const target = document.getElementById('step-' + step);
 if(target) target.classList.remove('hidden');
};

window.generateReport = async function() {
 window.nextStep(4);
 
 const loading = document.getElementById('gen-loading');
 const success = document.getElementById('gen-success');
 
 loading.classList.remove('hidden');
 loading.classList.add('flex');
 success.classList.add('hidden');
 success.classList.remove('flex');
 
 try {
 // Collect settings
 const format = document.querySelector('input[name="format"]:checked').value;
 
 // Simulate API call to generate
 await new Promise(r => setTimeout(r, 2000));
 const endpoint = format === 'pdf' ? api.endpoints.reportPdf : api.endpoints.reportCsv;
 await api.post(endpoint, { modules: ['dashboard'], format }).catch(()=>null);
 
 loading.classList.add('hidden');
 loading.classList.remove('flex');
 success.classList.remove('hidden');
 success.classList.add('flex');
 
 loadHistory();
 
 } catch (err) {
 console.error("Report generation failed", err);
 loading.innerHTML = '<p class="text-red-500 font-bold">Failed to generate report</p>';
 }
};

window.downloadReport = function() {
 alert('Downloading report...');
};

window.resetWizard = function() {
 window.nextStep(1);
};

document.addEventListener('DOMContentLoaded', loadHistory);

async function loadHistory() {
 const tbody = document.getElementById('history-tbody');
 try {
 let reports = await api.get(api.endpoints.reports).catch(()=>null);
 if (!reports || !reports.length) {
 reports = [
 { name: 'Executive Summary Q2', format: 'PDF', author: 'Admin', date: '2 hours ago' },
 { name: 'Department Budget Variance', format: 'Excel', author: 'Admin', date: 'Yesterday' }
 ];
 }
 
 tbody.innerHTML = reports.map(r => \
 <tr>
 <td class="px-6 py-4 font-semibold text-slate-900 ">\</td>
 <td class="px-6 py-4">
 <span class="px-2 py-1 bg-slate-100 text-slate-700 rounded text-[10px] font-bold">\</span>
 </td>
 <td class="px-6 py-4 text-slate-500 ">\</td>
 <td class="px-6 py-4 text-slate-500 ">\</td>
 <td class="px-6 py-4">
 <button class="text-primary hover:underline text-xs font-semibold flex items-center gap-1"><span class="material-symbols-outlined text-sm">download</span> Download</button>
 </td>
 </tr>
 \).join('');
 } catch (err) {
 console.error(err);
 }
}
