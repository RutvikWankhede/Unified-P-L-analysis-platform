import { api } from './api.js';
import './auth.js';

/**
 * upload.js - File upload with pipeline progress and dashboard refresh
 */

const PIPELINE_STAGES = [
 { id: 'upload', label: 'Uploading file', icon: 'cloud_upload' },
 { id: 'schema', label: 'Detecting schema', icon: 'schema' },
 { id: 'validation', label: 'Validating data quality', icon: 'fact_check' },
 { id: 'cleaner', label: 'Cleaning records', icon: 'cleaning_services' },
 { id: 'features', label: 'Building features', icon: 'psychology' },
 { id: 'ml', label: 'Running AI analysis', icon: 'smart_toy' },
 { id: 'workflow', label: 'Routing to workflow', icon: 'account_tree' },
 { id: 'database', label: 'Saving to database', icon: 'storage' },
];

document.addEventListener('DOMContentLoaded', initUpload);

function initUpload() {
 const dropzone = document.getElementById('dropzone') || document.getElementById('upload-zone');
 const fileInput = document.getElementById('file-input');
 const browseBtn = document.getElementById('browse-btn');

 if (dropzone) {
 dropzone.addEventListener('click', () => fileInput && fileInput.click());
 dropzone.addEventListener('dragover', (e) => { e.preventDefault(); dropzone.classList.add('border-primary'); });
 dropzone.addEventListener('dragleave', () => dropzone.classList.remove('border-primary'));
 dropzone.addEventListener('drop', (e) => {
 e.preventDefault();
 dropzone.classList.remove('border-primary');
 if (e.dataTransfer.files.length) handleFile(e.dataTransfer.files[0]);
 });
 }

 if (browseBtn) {
 browseBtn.addEventListener('click', (e) => { e.stopPropagation(); fileInput && fileInput.click(); });
 }

 if (fileInput) {
 fileInput.addEventListener('change', (e) => {
 if (e.target.files.length) handleFile(e.target.files[0]);
 });
 }

 // Reset button
 const resetBtn = document.getElementById('upload-again-btn') || document.getElementById('btn-upload-again');
 if (resetBtn) resetBtn.addEventListener('click', resetUpload);

 // Load recent uploads list
 loadRecentUploads();
}

function handleFile(file) {
 if (!file.name.match(/\.(csv|xlsx|xls)$/i)) {
 showError('Only .csv, .xlsx, or .xls files are accepted.');
 return;
 }

 // Show pipeline UI
 setView('pipeline');
 renderPipeline(0);

 // Animate pipeline stages while uploading
 let stageIdx = 0;
 const interval = setInterval(() => {
 stageIdx = Math.min(stageIdx + 1, PIPELINE_STAGES.length - 1);
 renderPipeline(stageIdx);
 }, 700);

 api.uploadFile(api.endpoints.upload, file)
 .then(data => {
 clearInterval(interval);
 if (data.confidence_ok === false || (data.schema_mapping && data.schema_mapping.overall_confidence < 80)) {
 renderPipeline(1); // Stop at schema step
 setTimeout(() => showMappingUI(data), 400);
 } else {
 renderPipeline(PIPELINE_STAGES.length); // all complete
 setTimeout(() => showSuccess(data), 400);
 }
 })
 .catch(err => {
 clearInterval(interval);
 showError(err.data?.detail || err.message || 'Upload failed. Check backend connection.');
 });
}

function renderPipeline(activeIdx) {
 const container = document.getElementById('pipeline-nodes') || document.getElementById('pipeline-container');
 if (!container) return;

 container.innerHTML = PIPELINE_STAGES.map((stage, i) => {
 let status = 'pending';
 let icon = stage.icon;
 if (i < activeIdx) { status = 'done'; icon = 'check_circle'; }
 else if (i === activeIdx) { status = 'active'; }

 const colors = {
 done: 'bg-green-50 border-green-200 text-green-600',
 active: 'bg-primary/10 border-primary text-primary',
 pending: 'bg-slate-50 border-slate-200 text-slate-400',
 };
 const labelColor = status === 'done' ? 'text-slate-700' : status === 'active' ? 'text-primary font-semibold' : 'text-slate-400';

 return `
 <div class="flex items-center gap-3 py-2 px-3 rounded-xl ${status === 'active' ? 'bg-primary/5' : ''}">
 <div class="w-9 h-9 rounded-xl border ${colors[status]} flex items-center justify-center flex-shrink-0">
 <span class="material-symbols-outlined text-sm ${status === 'active' ? 'animate-pulse' : ''}">${icon}</span>
 </div>
 <div class="flex-1">
 <p class="text-sm ${labelColor}">${stage.label}</p>
 </div>
 <div class="text-xs ${status === 'done' ? 'text-green-600' : status === 'active' ? 'text-primary' : 'text-slate-300'}">
 ${status === 'done' ? 'Done' : status === 'active' ? '…' : ''}
 </div>
 </div>`;
 }).join('');
}

function showSuccess(data) {
 setView('success');

 setEl('upload-records-count', (data.records_ingested || 0).toLocaleString());
 setEl('upload-workflow-id', data.workflow_process_id || 'N/A');
 setEl('upload-confidence', data.confidence_ok ? 'High confidence — auto-ingested' : 'Manual mapping required');
 setEl('upload-filename', data.upload_id || 'Dataset');

 loadRecentUploads();
 showToast(`Upload complete! ${data.records_ingested || 0} records ingested.`, 'success');
}

function showError(msg) {
 setView('error');
 setEl('error-message', msg);
 setEl('upload-error-msg', msg);
}

function setView(view) {
 const views = { upload: 'upload-zone', pipeline: 'pipeline-view', schema: 'schema-view', success: 'success-view', error: 'error-view' };
 Object.values(views).forEach(id => {
 const el = document.getElementById(id);
 if (el) el.style.display = 'none';
 });
 const el = document.getElementById(views[view]);
 if (el) el.style.display = 'block';
}

function resetUpload() {
 setView('upload');
}

let currentUploadData = null;

function showMappingUI(data) {
 setView('schema');
 currentUploadData = data;
 const tbody = document.getElementById('mapping-tbody');
 const btn = document.getElementById('confirm-mapping-btn');
 
 if (!data.schema_mapping || !data.schema_mapping.mappings) {
 tbody.innerHTML = '<tr><td colspan="3" class="px-4 py-4 text-center text-sm text-text-muted">No mapping data available</td></tr>';
 return;
 }
 
 const mappings = data.schema_mapping.mappings;
 const allColumns = data.schema_mapping.detected_columns || [];
 
 const previewRows = data.analysis?.preview_rows || [];
 let previewHtml = '';
 if (previewRows.length > 0) {
     const headers = Object.keys(previewRows[0]);
     previewHtml = `
     <div class="mt-6 mb-4">
         <h3 class="text-sm font-bold text-slate-800 mb-2">Dataset Preview (First 5 Rows)</h3>
         <div class="overflow-x-auto rounded-xl border border-slate-200">
             <table class="w-full text-left text-xs">
                 <thead class="bg-slate-50 text-slate-600 border-b border-slate-200">
                     <tr>${headers.map(h => `<th class="px-3 py-2 font-semibold whitespace-nowrap">${h}</th>`).join('')}</tr>
                 </thead>
                 <tbody class="divide-y divide-slate-100 bg-white">
                     ${previewRows.map(row => `
                         <tr class="hover:bg-slate-50">
                             ${headers.map(h => `<td class="px-3 py-2 text-slate-700 whitespace-nowrap">${row[h] !== null && row[h] !== undefined ? row[h] : ''}</td>`).join('')}
                         </tr>
                     `).join('')}
                 </tbody>
             </table>
         </div>
     </div>
     `;
 }

 let previewContainer = document.getElementById('dataset-preview-container');
 if (!previewContainer) {
     previewContainer = document.createElement('div');
     previewContainer.id = 'dataset-preview-container';
     btn.parentNode.insertBefore(previewContainer, btn);
 }
 previewContainer.innerHTML = previewHtml;

 
 tbody.innerHTML = Object.entries(mappings).map(([canonical, mapping]) => {
 const conf = mapping.confidence || 0;
 const isHigh = conf >= 80;
 const isMed = conf >= 50 && conf < 80;
 const confClass = isHigh ? 'text-success-text bg-success-bg' : (isMed ? 'text-warning-text bg-warning-bg' : 'text-red-600 bg-red-50');
 
 let selectHtml = `<select class="w-full text-sm border-border-light rounded-lg mapping-select" data-canonical="${canonical}">`;
 selectHtml += `<option value="">-- Select Column --</option>`;
 allColumns.forEach(col => {
 const selected = col === mapping.source_column ? 'selected' : '';
 selectHtml += `<option value="${col}" ${selected}>${col}</option>`;
 });
 selectHtml += `</select>`;
 
 return `
 <tr class="hover:bg-surface-main">
 <td class="px-4 py-3 font-medium text-text-dark">${canonical.replace('_', ' ').toUpperCase()}</td>
 <td class="px-4 py-3">${selectHtml}</td>
 <td class="px-4 py-3">
 <span class="px-2 py-1 rounded-full text-xs font-bold ${confClass}">${conf.toFixed(1)}%</span>
 </td>
 </tr>
 `;
 }).join('');
 
 btn.onclick = async () => {
 btn.disabled = true;
 btn.textContent = 'Saving...';
 
 const selects = document.querySelectorAll('.mapping-select');
 const updatedMappings = {};
 selects.forEach(s => {
     if (s.value) {
         updatedMappings[s.value] = s.dataset.canonical;
     }
 });
 
 try {
 const res = await api.post(api.endpoints.finalizeUpload, { 
 upload_id: data.upload_id, 
 mapping: updatedMappings,
 filename: data.filename || 'dataset.csv'
 });
 
 setView('pipeline');
 renderPipeline(1);
 
 let stageIdx = 1;
 const interval = setInterval(() => {
 stageIdx = Math.min(stageIdx + 1, PIPELINE_STAGES.length - 1);
 renderPipeline(stageIdx);
 }, 700);
 
 setTimeout(() => {
 clearInterval(interval);
 renderPipeline(PIPELINE_STAGES.length);
 showSuccess(data);
 }, 3000);
 
 } catch (err) {
 showError('Failed to save mapping');
 }
 };
}

async function loadRecentUploads() {
 const tbody = document.getElementById('uploads-tbody') || document.getElementById('recent-uploads-list');
 if (!tbody) return;

 try {
 const data = await api.get(api.endpoints.datasetsRecent);
 const items = Array.isArray(data) ? data : (data.items || []);

 if (!items.length) {
 tbody.innerHTML = '<tr><td colspan="5" class="py-8 text-center text-slate-400 text-sm">No uploads yet</td></tr>';
 return;
 }

 const statusColors = { completed: 'bg-green-50 text-green-600', processing: 'bg-blue-50 text-blue-600', failed: 'bg-red-50 text-red-500', mapping_required: 'bg-orange-50 text-orange-500' };

 tbody.innerHTML = items.map(d => {
 const status = d.status || 'completed';
 const sc = statusColors[status] || statusColors.completed;
 const date = d.uploaded_at ? new Date(d.uploaded_at).toLocaleDateString('en-IN') : '—';
 const size = d.file_size ? formatFileSize(d.file_size) : '—';
 const records = d.records_count ? d.records_count.toLocaleString() : '—';

 return `
 <tr class="hover:bg-slate-50 transition-colors">
 <td class="py-3 px-4">
 <div class="flex items-center gap-2">
 <span class="material-symbols-outlined text-slate-400 text-sm">description</span>
 <span class="text-sm font-medium text-slate-900">${d.original_filename || d.filename || 'Dataset'}</span>
 </div>
 </td>
 <td class="py-3 px-4 text-sm text-slate-600">${date}</td>
 <td class="py-3 px-4 text-sm text-slate-600">${size}</td>
 <td class="py-3 px-4 text-sm text-slate-600">${records}</td>
 <td class="py-3 px-4">
 <span class="px-2 py-1 rounded-lg text-xs font-bold uppercase ${sc}">${status.replace('_', ' ')}</span>
 </td>
 </tr>`;
 }).join('');
 } catch (err) {
 if (tbody) tbody.innerHTML = '<tr><td colspan="5" class="py-8 text-center text-red-400 text-sm">Could not load uploads</td></tr>';
 }
}

function setEl(id, val) { const el = document.getElementById(id); if (el) el.textContent = val; }

function formatFileSize(bytes) {
 if (!bytes) return '—';
 const kb = bytes / 1024;
 return kb < 1024 ? kb.toFixed(1) + ' KB' : (kb / 1024).toFixed(1) + ' MB';
}

function showToast(msg, type = 'success') {
 const colors = { success: 'bg-green-50 text-green-700 border-green-200', error: 'bg-red-50 text-red-700 border-red-200', info: 'bg-blue-50 text-blue-700 border-blue-200' };
 const icons = { success: 'check_circle', error: 'error', info: 'info' };
 const toast = document.createElement('div');
 toast.className = `fixed bottom-6 right-6 z-50 flex items-center gap-3 px-4 py-3 border rounded-xl shadow-lg text-sm font-medium ${colors[type]}`;
 toast.innerHTML = `<span class="material-symbols-outlined text-base">${icons[type]}</span>${msg}`;
 document.body.appendChild(toast);
 setTimeout(() => { toast.style.opacity = '0'; setTimeout(() => toast.remove(), 300); }, 4500);
}
