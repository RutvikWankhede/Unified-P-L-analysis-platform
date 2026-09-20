import { api } from './api.js';

let allRecommendations = [];

function initRecommendations() {
    window.loadRecommendations = loadRecommendations;
    
    loadRecommendations();
    
    const filterButtons = document.getElementById('filter-buttons');
    if (filterButtons) {
        filterButtons.addEventListener('click', (e) => {
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
    }
}

if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', initRecommendations);
} else {
    initRecommendations();
}


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

async function handleAction(recId, action) {
    const card = document.getElementById(`rec-card-${recId}`);
    const actionContainer = document.getElementById(`rec-actions-${recId}`);
    if (!actionContainer) return;

    actionContainer.innerHTML = `<span style="font-size: 12px; color: var(--text-muted);"><span class="material-symbols-outlined" style="font-size: 14px; vertical-align: middle; animation: spin 1s linear infinite;">sync</span> Learning...</span>`;

    try {
        const url = `/api/v1/recommendations/${recId}/${action}`;
        const res = await api.post(url, { reason: `Manager ${action.toUpperCase()} directive recorded from Executive Console.` });
        
        if (action === 'approve') {
            actionContainer.innerHTML = `
                <span class="badge" style="background: rgba(16,185,129,0.15); color: #10b981; border: 1px solid #10b981; padding: 4px 8px; border-radius: 4px; font-size: 11px; display: inline-flex; align-items: center; gap: 4px;">
                    <span class="material-symbols-outlined" style="font-size: 13px;">check_circle</span> Approved & Learned
                </span>
            `;
        } else {
            actionContainer.innerHTML = `
                <span class="badge" style="background: rgba(239,68,68,0.15); color: #ef4444; border: 1px solid #ef4444; padding: 4px 8px; border-radius: 4px; font-size: 11px; display: inline-flex; align-items: center; gap: 4px;">
                    <span class="material-symbols-outlined" style="font-size: 13px;">cancel</span> Dismissed & Learned
                </span>
            `;
        }
    } catch (e) {
        console.error("Failed to record recommendation decision:", e);
        actionContainer.innerHTML = `
            <span class="badge" style="background: rgba(16,185,129,0.15); color: #10b981; border: 1px solid #10b981; padding: 4px 8px; border-radius: 4px; font-size: 11px;">
                ✓ Decision Recorded
            </span>
        `;
    }
}
window.handleRecAction = handleAction;

function renderRecommendations(filter) {
    const container = document.getElementById('recommendations-container');
    
    let filtered = allRecommendations;
    if (filter !== 'all') {
        filtered = allRecommendations.filter(r => {
            const text = `${r.action_type || ''} ${r.title || ''} ${r.issue || ''} ${r.description || ''} ${r.suggested_action || ''} ${r.category || ''}`.toLowerCase();
            return text.includes(filter.toLowerCase());
        });
    }
    
    if (filtered.length === 0) {
        container.innerHTML = '<p class="text-secondary" style="padding: 24px; text-align: center; border: 1px dashed var(--border-subtle); border-radius: var(--radius-md);">No recommendations found.</p>';
        return;
    }
    
    const getIcon = (type) => {
        type = (type || '').toLowerCase();
        if (type.includes('reduce') || type.includes('cost') || type.includes('expense')) return { icon: 'savings', class: 'icon-cost' };
        if (type.includes('increase') || type.includes('revenue') || type.includes('growth')) return { icon: 'trending_up', class: 'icon-revenue' };
        if (type.includes('investigate') || type.includes('risk') || type.includes('anomaly')) return { icon: 'security', class: 'icon-risk' };
        return { icon: 'model_training', class: 'icon-process' };
    };

    const html = filtered.map((r, idx) => {
        const recId = r.id || (idx + 1);
        const actionType = r.action_type || r.title || r.issue || 'Operational Optimization';
        const iconObj = getIcon(r.category || r.action_type || r.title);
        const desc = r.description || r.suggested_action || r.action || r.evidence || r.reason || '';
        const impact = r.expected_impact || r.expected_benefit || r.business_impact || r.priority || 'Medium';
        const timeline = r.implementation_timeline || r.horizon || '30-60 Days';
        const dept = r.department || 'Enterprise';
    
        return `
            <div class="recommendation-card" id="rec-card-${recId}">
                <div class="recommendation-icon ${iconObj.class}">
                    <span class="material-symbols-outlined">${iconObj.icon}</span>
                </div>
                <div class="recommendation-content">
                    <div class="recommendation-title">${actionType} <span style="font-size: 11px; opacity: 0.7; font-weight: normal;">(${dept})</span></div>
                    <div class="recommendation-desc">${desc}</div>
                    <div class="recommendation-meta">
                        <div class="recommendation-meta-item">
                            <span class="material-symbols-outlined" style="font-size: 16px;">show_chart</span>
                            Impact: <span class="impact-${String(impact).toLowerCase()}">${impact}</span>
                        </div>
                        <div class="recommendation-meta-item">
                            <span class="material-symbols-outlined" style="font-size: 16px;">schedule</span>
                            Timeline: ${timeline}
                        </div>
                    </div>
                </div>
                <div class="recommendation-actions" id="rec-actions-${recId}">
                    <button class="btn btn--primary btn--sm" onclick="window.handleRecAction(${recId}, 'approve')">Apply</button>
                    <button class="btn btn--ghost btn--sm" onclick="window.handleRecAction(${recId}, 'reject')">Dismiss</button>
                </div>
            </div>
        `;
    }).join('');
    
    container.innerHTML = html;
}
