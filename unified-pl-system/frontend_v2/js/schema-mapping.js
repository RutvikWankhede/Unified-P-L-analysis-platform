import { api } from './api.js';
import { showSkeleton, hideSkeleton } from './skeletons.js';

let datasetId = null;
let currentMapping = [];
let sourceHeaders = [];

document.addEventListener('DOMContentLoaded', () => {
 const urlParams = new URLSearchParams(window.location.search);
 datasetId = urlParams.get('dataset_id');
 
 if (!datasetId) {
 alert("No dataset specified.");
 window.location.href = "/dashboard.html";
 return;
 }
 
 loadMappingProposal();
 
 document.getElementById('btn-confirm').addEventListener('click', confirmMapping);
});

async function loadMappingProposal() {
 const tbody = document.getElementById('mapping-table-body');
 tbody.innerHTML = `<tr><td colspan="3"><div class="skeleton" style="height:200px; width:100%;"></div></td></tr>`;
 
 try {
 const res = await api.get(api.endpoints.schemaMapping(datasetId));
 currentMapping = res.mapping || [];
 sourceHeaders = res.source_headers || [];
 
 renderTable();
 } catch(e) {
 tbody.innerHTML = `<tr><td colspan="3" class="text-error" style="text-align:center; padding: var(--space-5);">Failed to load mapping proposal. <button class="btn btn--ghost btn--sm" onclick="location.reload()">Retry</button></td></tr>`;
 }
}

function renderTable() {
 const tbody = document.getElementById('mapping-table-body');
 
 const optionsHtml = sourceHeaders.map(h => `<option value="${h}">${h}</option>`).join('');
 const ignoreOption = `<option value="__ignore__">-- Not present in this dataset --</option>`;
 const defaultOption = `<option value="" disabled>Select a column...</option>`;
 
 const html = currentMapping.map((field, idx) => {
 const isRequired = field.required ? '*' : '';
 let badge = '';
 
 if (field.confidence === 'High') {
 badge = `<span class="badge badge--success" style="width: 100px; justify-content:center;">High</span>`;
 } else if (field.confidence === 'Medium') {
 badge = `<span class="badge badge--warning" style="width: 100px; justify-content:center;">Medium</span>`;
 } else {
 badge = `<span class="badge badge--danger" style="width: 100px; justify-content:center;">Low</span>`;
 }
 
 let selectHtml = `<select class="select mapping-select" data-canonical="${field.canonical_field}" style="margin:0;">`;
 if (!field.proposed_source) {
 selectHtml += defaultOption;
 }
 selectHtml += optionsHtml + ignoreOption + `</select>`;
 
 return `
 <tr>
 <td style="padding: var(--space-4);">
 <div style="display:flex; flex-direction:column;">
 <span class="text-h3">${field.canonical_field}${isRequired}</span>
 <span class="text-caption text-secondary">${field.description || ''}</span>
 </div>
 </td>
 <td style="padding: var(--space-4);">
 ${selectHtml}
 </td>
 <td style="padding: var(--space-4);">
 ${badge}
 </td>
 </tr>
 `;
 }).join('');
 
 tbody.innerHTML = html;
 
 // Set initial values
 const selects = document.querySelectorAll('.mapping-select');
 selects.forEach((sel, idx) => {
 const prop = currentMapping[idx].proposed_source;
 if (prop) {
 sel.value = prop;
 } else {
 sel.value = "";
 }
 
 sel.addEventListener('change', validateForm);
 });
 
 validateForm();
}

function validateForm() {
 const selects = document.querySelectorAll('.mapping-select');
 let isValid = true;
 
 selects.forEach(sel => {
 if (!sel.value) {
 isValid = false;
 }
 });
 
 document.getElementById('btn-confirm').disabled = !isValid;
}

async function confirmMapping() {
 const selects = document.querySelectorAll('.mapping-select');
 const finalMapping = {};
 
 selects.forEach(sel => {
 const canonical = sel.getAttribute('data-canonical');
 const source = sel.value;
 finalMapping[canonical] = source === '__ignore__' ? null : source;
 });
 
 const btn = document.getElementById('btn-confirm');
 btn.classList.add('btn--loading');
 btn.disabled = true;
 
 try {
 await api.post(api.endpoints.schemaMapping(datasetId), { mapping: finalMapping });
 window.location.href = `/validation.html?dataset_id=${datasetId}`;
 } catch(e) {
 alert("Failed to save mapping.");
 btn.classList.remove('btn--loading');
 btn.disabled = false;
 }
}
