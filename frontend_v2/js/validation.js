import { api } from './api.js';
import { showSkeleton, hideSkeleton } from './skeletons.js';

let datasetId = null;

document.addEventListener('DOMContentLoaded', () => {
 const urlParams = new URLSearchParams(window.location.search);
 datasetId = urlParams.get('dataset_id');
 
 if (!datasetId) {
 alert("No dataset specified.");
 window.location.href = "/dashboard.html";
 return;
 }
 
 loadValidationResults();
 
 // Attach global functions
 window.runValidation = runValidation;
 window.completePipeline = completePipeline;
});

async function loadValidationResults() {
 const container = document.getElementById('validation-rules-container');
 const summaryContainer = document.getElementById('validation-summary-container');
 
 showSkeleton(container, 'list');
 summaryContainer.innerHTML = '';
 document.getElementById('btn-continue').disabled = true;
 document.getElementById('btn-rerun').disabled = true;
 
 try {
 const res = await api.get(api.endpoints.validationRules(datasetId));
 hideSkeleton(container);
 renderValidation(res);
 } catch(e) {
 container.innerHTML = `<div class="text-error" style="padding: var(--space-5);">Failed to load validation results.</div>`;
 document.getElementById('btn-rerun').disabled = false;
 }
}

async function runValidation() {
 const btn = document.getElementById('btn-rerun');
 btn.classList.add('btn--loading');
 
 try {
 await api.post(api.endpoints.validationRules(datasetId), {});
 // Fetch fresh results
 await loadValidationResults();
 } catch(e) {
 alert("Failed to rerun validation.");
 } finally {
 btn.classList.remove('btn--loading');
 }
}

async function completePipeline() {
 const btn = document.getElementById('btn-continue');
 btn.classList.add('btn--loading');
 
 try {
 // Resume pipeline from validation step
 await api.post(`/api/v1/datasets/${datasetId}/resume`, {});
 // Redirect back to upload page which handles the rest of the pipeline UI
 window.location.href = `/upload.html`; 
 } catch(e) {
 alert("Failed to continue pipeline.");
 btn.classList.remove('btn--loading');
 }
}

function renderValidation(data) {
 const rules = data.rules || [];
 const errors = rules.filter(r => r.status === 'error').length;
 const warnings = rules.filter(r => r.status === 'warning').length;
 const passed = rules.filter(r => r.status === 'pass').length;
 
 const hasBlockers = errors > 0;
 
 // Update Buttons
 document.getElementById('btn-rerun').disabled = false;
 document.getElementById('btn-continue').disabled = hasBlockers;
 
 // Render Summary
 const summaryContainer = document.getElementById('validation-summary-container');
 let summaryHtml = '';
 
 if (hasBlockers) {
 summaryHtml = `
 <div style="background: rgba(255, 93, 93, 0.1); border: 1px solid var(--danger); border-radius: var(--radius-md); padding: var(--space-4); display: flex; align-items: flex-start; gap: var(--space-4);">
 <span class="material-symbols-outlined text-danger" style="font-size: 32px;">error</span>
 <div>
 <h3 class="text-h3 text-danger" style="margin-bottom: var(--space-1);">Validation Failed</h3>
 <p class="text-body text-secondary">Found ${errors} critical errors that must be resolved before proceeding.</p>
 </div>
 </div>
 `;
 } else if (warnings > 0) {
 summaryHtml = `
 <div style="background: rgba(255, 178, 36, 0.1); border: 1px solid var(--warning); border-radius: var(--radius-md); padding: var(--space-4); display: flex; align-items: flex-start; gap: var(--space-4);">
 <span class="material-symbols-outlined text-warning" style="font-size: 32px;">warning</span>
 <div>
 <h3 class="text-h3 text-warning" style="margin-bottom: var(--space-1);">Validation Passed with Warnings</h3>
 <p class="text-body text-secondary">Found ${warnings} warnings. You can proceed, but review them first.</p>
 </div>
 </div>
 `;
 } else {
 summaryHtml = `
 <div style="background: rgba(74, 225, 118, 0.1); border: 1px solid var(--success); border-radius: var(--radius-md); padding: var(--space-4); display: flex; align-items: flex-start; gap: var(--space-4);">
 <span class="material-symbols-outlined text-success" style="font-size: 32px;">check_circle</span>
 <div>
 <h3 class="text-h3 text-success" style="margin-bottom: var(--space-1);">Validation Passed</h3>
 <p class="text-body text-secondary">All ${passed} rules passed successfully.</p>
 </div>
 </div>
 `;
 }
 summaryContainer.innerHTML = summaryHtml;
 
 // Group rules
 const categories = {};
 rules.forEach(r => {
 if(!categories[r.category]) categories[r.category] = [];
 categories[r.category].push(r);
 });
 
 const rulesContainer = document.getElementById('validation-rules-container');
 let rulesHtml = '';
 
 Object.keys(categories).forEach(cat => {
 rulesHtml += `
 <div class="glass-card" style="margin-bottom: var(--space-5);">
 <h3 class="text-h3 mb-4">${cat}</h3>
 <div style="display: flex; flex-direction: column; gap: var(--space-3);">
 `;
 
 categories[cat].forEach(rule => {
 let icon = '';
 let color = '';
 let bg = '';
 
 if (rule.status === 'pass') {
 icon = 'check_circle'; color = 'var(--success)'; bg = 'rgba(74, 225, 118, 0.05)';
 } else if (rule.status === 'warning') {
 icon = 'warning'; color = 'var(--warning)'; bg = 'rgba(255, 178, 36, 0.05)';
 } else {
 icon = 'error'; color = 'var(--danger)'; bg = 'rgba(255, 93, 93, 0.05)';
 }
 
 rulesHtml += `
 <div style="display: flex; align-items: flex-start; gap: var(--space-4); padding: var(--space-3); background: ${bg}; border-radius: var(--radius-sm); border: 1px solid rgba(255,255,255,0.05);">
 <span class="material-symbols-outlined" style="color: ${color};">${icon}</span>
 <div>
 <h4 class="text-body font-bold" style="margin-bottom: var(--space-1);">${rule.name}</h4>
 <p class="text-caption text-secondary">${rule.description}</p>
 ${rule.details ? `<div class="text-caption mono" style="margin-top: var(--space-2); color: ${color};">${rule.details}</div>` : ''}
 </div>
 </div>
 `;
 });
 
 rulesHtml += `</div></div>`;
 });
 
 rulesContainer.innerHTML = rulesHtml;
}
