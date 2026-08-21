import { api } from './api.js';

let allRecommendations = [];

document.addEventListener('DOMContentLoaded', () => {
 window.loadRecommendations = loadRecommendations;
 
 loadRecommendations();
 
 document.getElementById('filter-buttons').addEventListener('click', (e) => {
 if (e.target.tagName === 'BUTTON') {
 document.querySelectorAll('#filter-buttons button').forEach(b => {
 b.classList.remove('active');
 b.classList.replace('btn--secondary', 'btn--ghost');
 });
 e.target.classList.add('active');
 e.target.classList.replace('btn--ghost', 'btn--secondary');
 
 const filter = e.target.getAttribute('data-filter');
 renderRecommendations(filter);
 }
 });
});

async function loadRecommendations() {
 const container = document.getElementById('recommendations-container');
 container.innerHTML = '<p class="text-secondary">Loading recommendations...</p>';
 
 try {
 const data = await api.get(api.endpoints.aiRecommendations);
 allRecommendations = data || [];
 renderRecommendations('all');
 } catch (err) {
 container.innerHTML = '<p class="text-danger">Failed to load recommendations.</p>';
 }
}

function renderRecommendations(filter) {
 const container = document.getElementById('recommendations-container');
 
 let filtered = allRecommendations;
 if (filter !== 'all') {
 // We map frontend categories to what backend returns. Let's assume action_type maps somewhat.
 // E.g., 'cost' maps to 'Reduce', 'risk' to 'Mitigate', etc. or we just do simple text match
 filtered = allRecommendations.filter(r => r.action_type.toLowerCase().includes(filter.toLowerCase()) || r.description.toLowerCase().includes(filter.toLowerCase()));
 }
 
 if (filtered.length === 0) {
 container.innerHTML = '<p class="text-secondary" style="padding: 24px; text-align: center; border: 1px dashed var(--border-subtle); border-radius: var(--radius-md);">No recommendations found.</p>';
 return;
 }
 
 const getIcon = (type) => {
 type = type.toLowerCase();
 if (type.includes('reduce') || type.includes('cost')) return { icon: 'savings', class: 'icon-cost' };
 if (type.includes('increase') || type.includes('revenue')) return { icon: 'trending_up', class: 'icon-revenue' };
 if (type.includes('investigate') || type.includes('risk')) return { icon: 'security', class: 'icon-risk' };
 return { icon: 'model_training', class: 'icon-process' };
 };

 const html = filtered.map(r => {
 const iconObj = getIcon(r.action_type);
 
 return `
 <div class="recommendation-card">
 <div class="recommendation-icon ${iconObj.class}">
 <span class="material-symbols-outlined">${iconObj.icon}</span>
 </div>
 <div class="recommendation-content">
 <div class="recommendation-title">${r.action_type} - ${r.description.split('.')[0]}</div>
 <div class="recommendation-desc">${r.description}</div>
 <div class="recommendation-meta">
 <div class="recommendation-meta-item">
 <span class="material-symbols-outlined" style="font-size: 16px;">show_chart</span>
 Impact: <span class="impact-${r.expected_impact.toLowerCase()}">${r.expected_impact}</span>
 </div>
 <div class="recommendation-meta-item">
 <span class="material-symbols-outlined" style="font-size: 16px;">schedule</span>
 Timeline: ${r.implementation_timeline}
 </div>
 </div>
 </div>
 <div class="recommendation-actions">
 <button class="btn btn--primary btn--sm">Apply</button>
 <button class="btn btn--ghost btn--sm">Dismiss</button>
 </div>
 </div>
 `;
 }).join('');
 
 container.innerHTML = html;
}
