/**
 * shell.js - Application Chrome (Unified P&L Canonical Sidebar + Navigation)
 * ==========================================================================
 * Single source of truth for the sidebar.
 * Injected into every authenticated page via <div id="sidebar-container">.
 *
 * Responsibilities:
 * - Route guard (redirect to login if no token)
 * - Dynamically inject canonical sidebar HTML matching visual reference
 * - Auto-highlight active nav item based on current route
 * - Support responsive collapse/expand with localStorage persistence
 * - Wire logout, search shortcuts, and notifications
 */

import { api } from './api.js';

export function escapeHtml(str) {
    if (str == null) return '';
    return String(str)
        .replace(/&/g, '&amp;')
        .replace(/</g, '&lt;')
        .replace(/>/g, '&gt;')
        .replace(/"/g, '&quot;')
        .replace(/'/g, '&#039;');
}
if (typeof window !== 'undefined') {
    window.escapeHtml = escapeHtml;
}

// ─── Route Guard (runs synchronously before render) ──────────────────────────
(function guardRoute() {
    const PUBLIC = ['login.html', 'forgot-password.html', 'index.html'];
    const page = window.location.pathname.split('/').pop() || 'login.html';
    if (!PUBLIC.includes(page) && !api.isAuthenticated()) {
        const ret = encodeURIComponent(window.location.pathname + window.location.search);
        window.location.replace(`login.html?return_to=${ret}`);
    }
})();

// ─── Canonical Navigation Map (EXACT 9 items in exact order) ─────────────────
const NAV_ITEMS = [
    { href: 'dashboard.html',   icon: 'grid_view',     label: 'Dashboard' },
    { href: 'departments.html', icon: 'domain',        label: 'Departments' },
    { href: 'datasets.html',    icon: 'upload_file',   label: 'Upload / Datasets' },
    { href: 'forecast.html',    icon: 'trending_up',   label: 'Forecast' },
    { href: 'anomalies.html',   icon: 'warning',       label: 'Anomaly Detection' },
    { href: 'copilot.html',     icon: 'smart_toy',     label: 'AI Copilot' },
    { href: 'what-if.html',     icon: 'tune',          label: 'What-If Analysis' },
    { href: 'reports.html',     icon: 'description',   label: 'Reports' },
    { href: 'settings.html',    icon: 'settings',      label: 'Settings' },
];

// Pages that map to a canonical parent nav item
const PAGE_ALIASES = {
    // 1. Dashboard
    '':                    'dashboard.html',
    'index.html':          'dashboard.html',
    'dashboard.html':      'dashboard.html',
    'pl_dashboard.html':   'dashboard.html',

    // 2. Departments
    'departments.html':    'departments.html',
    'department.html':     'departments.html',

    // 3. Upload / Datasets
    'datasets.html':       'datasets.html',
    'upload.html':         'datasets.html',
    'dataset-quality.html':'datasets.html',
    'schema-mapping.html': 'datasets.html',
    'validation.html':     'datasets.html',

    // 4. Forecast
    'forecast.html':       'forecast.html',
    'pl_forecast.html':    'forecast.html',

    // 5. Anomaly Detection
    'anomalies.html':      'anomalies.html',
    'anomaly.html':        'anomalies.html',

    // 6. AI Copilot
    'copilot.html':        'copilot.html',
    'ai-copilot.html':     'copilot.html',

    // 7. What-If Analysis (replaces Workflow)
    'what-if.html':        'what-if.html',
    'whatif.html':         'what-if.html',
    'workflow.html':       'what-if.html',

    // 8. Reports
    'reports.html':        'reports.html',
    'executive.html':      'reports.html',
    'export.html':         'reports.html',
    'pivot.html':          'reports.html',
    'recommendations.html':'reports.html',
    'financial-health.html':'reports.html',
    'analytics.html':      'reports.html',

    // 9. Settings
    'settings.html':       'settings.html',
    'users.html':          'settings.html',
    'profile.html':        'settings.html',
    'audit.html':          'settings.html',
    'audit-trail.html':    'settings.html',
};

// ─── User info from JWT ──────────────────────────────────────────────────────
function getUserInfo() {
    try {
        const token = api.getAccessToken();
        if (!token) return { name: 'Admin', initials: 'A', role: 'Administrator', username: 'admin' };
        const payload = JSON.parse(atob(token.split('.')[1]));
        const sub = payload.sub || 'Admin';
        const roleName = payload.role === 'admin' ? 'Administrator' : 'Financial Analyst';
        const displayName = sub === 'admin' ? 'Admin' : sub.charAt(0).toUpperCase() + sub.slice(1);
        const initials = displayName.split(' ').map(w => w[0]).join('').toUpperCase().slice(0, 2);
        return { name: displayName, initials, role: roleName, username: sub };
    } catch (_) {
        return { name: 'Admin', initials: 'A', role: 'Administrator', username: 'admin' };
    }
}

// ─── Canonical Sidebar HTML Builder ──────────────────────────────────────────
function buildSidebar(activePage) {
    const navHTML = NAV_ITEMS.map(item => {
        const isActive = item.href === activePage;
        const itemClass = isActive ? 'sidebar-item active' : 'sidebar-item';
        
        return `<a class="${itemClass}" href="${item.href}" data-path="${item.href}" id="nav-${item.href.replace('.html', '')}">
            <span class="material-symbols-outlined sidebar-item-icon">${item.icon}</span>
            <span class="sidebar-item-text">${item.label}</span>
            ${isActive ? '<span class="sidebar-active-dot"></span>' : ''}
        </a>`;
    }).join('');

    return `<!-- Unified P&L Canonical Sidebar -->
<aside id="main-sidebar">
    <!-- Header / Brand Section -->
    <div class="sidebar-header">
        <a class="sidebar-brand" href="dashboard.html">
            <div class="sidebar-logo-icon">
                <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
                    <rect x="3" y="3" width="18" height="18" rx="3"></rect>
                    <path d="M8 17v-3"></path>
                    <path d="M12 17v-6"></path>
                    <path d="M16 17v-8"></path>
                </svg>
            </div>
            <div class="sidebar-brand-text">
                <h1 class="sidebar-title">Unified P&amp;L</h1>
                <p class="sidebar-subtitle">Enterprise Platform</p>
            </div>
        </a>
        <button id="sidebar-toggle" class="sidebar-toggle-btn" title="Toggle Navigation" aria-label="Toggle navigation">
            <span class="material-symbols-outlined">menu_open</span>
        </button>
    </div>

    <!-- Navigation Menu -->
    <nav class="sidebar-nav">
        <span class="sidebar-section-label">MENU</span>
        <div class="sidebar-menu">
            ${navHTML}
        </div>
    </nav>

    <!-- Active Dataset Footer Badge -->
    <div class="sidebar-dataset-badge px-3 py-3 border-t border-slate-100 bg-slate-50/50 mt-auto" data-active-dataset-container="true">
        <div class="flex items-center gap-2 p-2 rounded-xl bg-white border border-slate-200/80 shadow-2xs cursor-pointer hover:border-indigo-300 transition-all">
            <span class="w-2 h-2 rounded-full bg-emerald-500 animate-pulse flex-shrink-0"></span>
            <div class="flex flex-col text-left min-w-0">
                <span class="text-[8px] font-extrabold uppercase tracking-wider text-slate-400">ACTIVE DATASET</span>
                <span class="font-bold text-slate-800 text-[11px] truncate" id="sidebar-active-dataset-name">unified_pnl_enterprise_demo</span>
                <span class="text-[9px] font-semibold text-emerald-600" id="sidebar-active-dataset-type">● Seed Dataset</span>
            </div>
        </div>
    </div>
</aside>`;
}

// ─── Ensure Essential Stylesheets ───────────────────────────────────────────
function ensureStylesheets() {
    if (!document.querySelector('link[href*="sidebar.css"]')) {
        const link = document.createElement('link');
        link.rel = 'stylesheet';
        link.href = 'css/sidebar.css';
        document.head.appendChild(link);
    }
    if (!document.querySelector('link[href*="Material+Symbols"]')) {
        const fontLink = document.createElement('link');
        fontLink.rel = 'stylesheet';
        fontLink.href = 'https://fonts.googleapis.com/css2?family=Material+Symbols+Outlined:opsz,wght,FILL,GRAD@20..48,100..700,0..1,-50..200';
        document.head.appendChild(fontLink);
    }
}

// ─── Notification Popover ─────────────────────────────────────────────────────
async function initNotifications() {
    const bellBtn = document.getElementById('notifications-trigger');
    if (!bellBtn || document.getElementById('notifications-popover')) return;

    const badge = document.getElementById('notifications-badge');
    const popover = document.createElement('div');
    popover.id = 'notifications-popover';
    popover.className = 'absolute right-0 mt-2 w-80 bg-white border border-slate-200 rounded-xl shadow-xl z-50 hidden py-2 text-xs';
    popover.innerHTML = `
        <div class="px-4 py-2 border-b border-slate-100 flex justify-between items-center">
            <span class="font-bold text-slate-800">Notifications</span>
            <button id="noti-clear-btn" class="text-indigo-600 hover:text-indigo-700 font-semibold bg-transparent border-none cursor-pointer">Mark all read</button>
        </div>
        <div id="noti-list" class="max-h-64 overflow-y-auto divide-y divide-slate-100">
            <div class="px-4 py-3 text-center text-slate-400">Loading...</div>
        </div>`;

    bellBtn.parentElement.style.position = 'relative';
    bellBtn.parentElement.appendChild(popover);

    bellBtn.addEventListener('click', async (e) => {
        e.stopPropagation();
        popover.classList.toggle('hidden');
        if (!popover.classList.contains('hidden')) {
            await loadNotificationList();
        }
    });

    document.addEventListener('click', () => popover.classList.add('hidden'));
    popover.addEventListener('click', e => e.stopPropagation());

    const clearBtn = document.getElementById('noti-clear-btn');
    if (clearBtn) {
        clearBtn.addEventListener('click', async () => {
            try {
                await api.post(api.endpoints.notificationsReadAll, {});
                if (badge) badge.style.display = 'none';
                await loadNotificationList();
            } catch (_) {}
        });
    }

    await pollNotificationBadge(badge);
    setInterval(() => pollNotificationBadge(badge), 15000);
}

async function pollNotificationBadge(badge) {
    if (!badge) return;
    try {
        const data = await api.get(api.endpoints.notifications);
        const list = Array.isArray(data) ? data : (data.items || []);
        const unread = list.filter(n => !n.is_read).length;
        badge.style.display = unread > 0 ? 'block' : 'none';
        if (unread > 0) badge.textContent = unread > 9 ? '9+' : unread;
    } catch (_) {}
}

async function loadNotificationList() {
    const listEl = document.getElementById('noti-list');
    if (!listEl) return;
    try {
        const data = await api.get(api.endpoints.notifications);
        const list = Array.isArray(data) ? data : (data.items || []);
        if (!list.length) {
            listEl.innerHTML = '<div class="px-4 py-6 text-center text-slate-400">No notifications</div>';
            return;
        }
        const typeIcons = {
            anomaly: { icon: 'warning', color: 'text-red-500 bg-red-50' },
            workflow: { icon: 'sync', color: 'text-blue-500 bg-blue-50' },
            report: { icon: 'description', color: 'text-green-500 bg-green-50' },
            forecast: { icon: 'trending_up', color: 'text-yellow-600 bg-yellow-50' },
            info: { icon: 'info', color: 'text-slate-500 bg-slate-50' },
        };
        const targets = { anomaly: 'anomalies.html', workflow: 'what-if.html', report: 'reports.html', forecast: 'forecast.html' };
        listEl.innerHTML = list.map(n => {
            const cfg = typeIcons[n.type] || typeIcons.info;
            const time = new Date(n.created_at || Date.now()).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });
            const readClass = n.is_read ? 'opacity-60' : 'font-semibold bg-slate-50/50';
            const target = targets[n.type] || 'dashboard.html';
            return `<div onclick="window.location.href='${target}'" class="px-4 py-2.5 hover:bg-slate-50 flex gap-3 items-start cursor-pointer transition-colors ${readClass}">
                <div class="w-7 h-7 rounded-lg flex items-center justify-center flex-shrink-0 ${cfg.color}">
                    <span class="material-symbols-outlined text-sm">${cfg.icon}</span>
                </div>
                <div class="flex-1 min-w-0">
                    <p class="text-slate-900 truncate">${n.title || n.message || 'Notification'}</p>
                    <p class="text-[10px] text-slate-400 truncate mt-0.5">${n.message || ''}</p>
                </div>
                <span class="text-[10px] text-slate-400 flex-shrink-0">${time}</span>
            </div>`;
        }).join('');
    } catch (_) {
        if (listEl) listEl.innerHTML = '<div class="px-4 py-4 text-center text-red-500">Failed to load</div>';
    }
}

// ─── Global Search ────────────────────────────────────────────────────────────
function initSearch() {
    const searchInput = document.querySelector('input[placeholder*="Search"]');
    if (!searchInput) return;

    const ROUTES = [
        ['report', 'reports.html'],
        ['anomal', 'anomalies.html'],
        ['alert', 'anomalies.html'],
        ['forecast', 'forecast.html'],
        ['predict', 'forecast.html'],
        ['workflow', 'what-if.html'],
        ['upload', 'datasets.html'],
        ['dataset', 'datasets.html'],
        ['copilot', 'copilot.html'],
        ['setting', 'settings.html'],
        ['what', 'what-if.html'],
        ['simul', 'what-if.html'],
        ['scenario', 'what-if.html'],
        ['audit', 'audit.html'],
        ['dept', 'departments.html'],
    ];

    searchInput.addEventListener('keydown', e => {
        if (e.key !== 'Enter') return;
        const q = searchInput.value.trim().toLowerCase();
        if (!q) return;
        const match = ROUTES.find(([kw]) => q.includes(kw));
        window.location.href = match ? match[1] : `departments.html?search=${encodeURIComponent(q)}`;
    });

    window.addEventListener('keydown', e => {
        if ((e.metaKey || e.ctrlKey) && e.key === 'k') {
            e.preventDefault();
            searchInput.focus();
        }
    });
}

// ─── Logout ───────────────────────────────────────────────────────────────────
function initLogout() {
    document.addEventListener('click', async e => {
        if (e.target.closest('#logout-btn')) {
            try { await api.post(api.endpoints.logout, {}); } catch (_) {}
            api.setAccessToken(null);
            window.location.replace('login.html');
        }
    });
}

// ─── Main Init ───────────────────────────────────────────────────────────────
function initSidebar() {
    ensureStylesheets();

    let container = document.getElementById('sidebar-container');
    if (!container) {
        // If container doesn't exist, create it at the top of body
        container = document.createElement('div');
        container.id = 'sidebar-container';
        document.body.prepend(container);
    }

    // Determine active page
    let rawPage = window.location.pathname.split('/').pop() || 'dashboard.html';
    rawPage = rawPage.split('?')[0].split('#')[0];
    if (!rawPage) rawPage = 'dashboard.html';

    const activePage = PAGE_ALIASES[rawPage] || rawPage;

    // Inject canonical sidebar
    container.innerHTML = buildSidebar(activePage);

    // Remove any legacy duplicate sidebars on the page
    document.querySelectorAll('aside:not(#main-sidebar), div.sidebar:not(#main-sidebar)').forEach(el => {
        el.remove();
    });

    // Wire interactions
    initLogout();
    initSearch();
    initNotifications();

    // Wire Sidebar Toggle & restore collapsed state
    const sidebar = document.getElementById('main-sidebar');
    const toggleBtn = document.getElementById('sidebar-toggle');
    const isCollapsed = localStorage.getItem('sidebar_collapsed') === 'true';

    if (isCollapsed && sidebar) {
        sidebar.classList.add('sidebar-collapsed');
        document.body.classList.add('sidebar-is-collapsed');
    }

    if (toggleBtn && sidebar) {
        toggleBtn.addEventListener('click', (e) => {
            e.stopPropagation();
            sidebar.classList.toggle('sidebar-collapsed');
            const collapsed = sidebar.classList.contains('sidebar-collapsed');
            if (collapsed) {
                document.body.classList.add('sidebar-is-collapsed');
            } else {
                document.body.classList.remove('sidebar-is-collapsed');
            }
            localStorage.setItem('sidebar_collapsed', collapsed);
        });
    }

    // Update greeting if present on topbar
    const user = getUserInfo();
    const greetingEl = document.getElementById('greeting-text');
    if (greetingEl) {
        const hour = new Date().getHours();
        const part = hour < 12 ? 'morning' : hour < 18 ? 'afternoon' : 'evening';
        greetingEl.textContent = `Good ${part}, ${user.name}! 👋`;
    }

    // Synchronize Active Dataset Pill & Dataset Switcher across all pages
    initActiveDatasetSync();
}

// ─── Universal Active Dataset Sync & Switcher ──────────────────────────────
async function initActiveDatasetSync() {
    try {
        const active = await api.get('/api/v1/datasets/active').catch(() => null);
        if (active) {
            const isSeed = active.is_seeded || active.is_seed || active.dataset_id === "899540e5-fa49-49e8-b87a-6965b44fd71f";
            const displayName = (active.filename || 'unified_pnl_enterprise_demo.xlsx').replace('.csv', '').replace('.xlsx', '');
            const badgeType = isSeed ? 'Seed Dataset' : 'Uploaded Dataset';
            const dotColor = isSeed ? 'bg-emerald-500' : 'bg-indigo-500';
            const textColor = isSeed ? 'text-emerald-700' : 'text-indigo-700';
            const bgColor = isSeed ? 'bg-emerald-50/90 border-emerald-200/80' : 'bg-indigo-50/90 border-indigo-200/80';

            // 1. Update sidebar dataset badge
            const sbName = document.getElementById('sidebar-active-dataset-name');
            const sbType = document.getElementById('sidebar-active-dataset-type');
            if (sbName) sbName.textContent = displayName;
            if (sbType) {
                sbType.textContent = `● ${badgeType}`;
                sbType.className = `text-[9px] font-semibold ${isSeed ? 'text-emerald-600' : 'text-indigo-600'}`;
            }

            // 2. Update all custom dataset badge containers in page headers
            document.querySelectorAll('[data-active-dataset-container="true"]').forEach(el => {
                el.style.cursor = 'pointer';
                el.title = 'Click to switch active dataset';
                el.onclick = (e) => {
                    e.preventDefault();
                    e.stopPropagation();
                    openDatasetSwitcherModal();
                };
            });

            // 3. Update active dataset name pill
            const pill = document.getElementById('active-dataset-name') || document.getElementById('active-dataset-pill');
            if (pill) {
                pill.textContent = displayName;
                const container = pill.closest('.rounded-full') || pill.closest('[class*="rounded"]');
                if (container) {
                    container.style.cursor = 'pointer';
                    container.title = 'Click to switch active dataset';
                    container.onclick = (e) => {
                        e.preventDefault();
                        e.stopPropagation();
                        openDatasetSwitcherModal();
                    };
                }
            }
        }
    } catch (_) {}
}

async function openDatasetSwitcherModal() {
    let modal = document.getElementById('dataset-switcher-modal');
    if (!modal) {
        modal = document.createElement('div');
        modal.id = 'dataset-switcher-modal';
        modal.className = 'fixed inset-0 z-50 flex items-center justify-center p-4 bg-slate-900/40 backdrop-blur-xs animate-in fade-in duration-150';
        modal.innerHTML = `
            <div class="bg-white rounded-2xl shadow-2xl border border-slate-200 max-w-lg w-full overflow-hidden flex flex-col max-h-[80vh]">
                <div class="p-4 border-b border-slate-100 flex items-center justify-between bg-slate-50/50">
                    <div class="flex items-center gap-2.5">
                        <div class="w-8 h-8 rounded-lg bg-indigo-50 border border-indigo-100 flex items-center justify-center text-indigo-600">
                            <span class="material-symbols-outlined text-lg">dataset</span>
                        </div>
                        <div>
                            <h3 class="font-bold text-sm text-slate-900">Switch Active Dataset</h3>
                            <p class="text-[11px] text-slate-500">Select a dataset to update all application analytics</p>
                        </div>
                    </div>
                    <button id="close-dataset-modal-btn" class="text-slate-400 hover:text-slate-600 p-1 rounded-lg hover:bg-slate-100 transition-colors">
                        <span class="material-symbols-outlined text-lg">close</span>
                    </button>
                </div>
                <div class="p-4 overflow-y-auto space-y-2 flex-1" id="dataset-switcher-list">
                    <div class="text-center py-6 text-slate-400 text-xs">Loading available datasets...</div>
                </div>
                <div class="p-3 border-t border-slate-100 bg-slate-50 flex items-center justify-between">
                    <a href="datasets.html" class="text-xs text-indigo-600 hover:text-indigo-800 font-semibold flex items-center gap-1">
                        <span class="material-symbols-outlined text-sm">upload_file</span> Upload New Dataset
                    </a>
                    <button id="close-dataset-modal-footer" class="px-3 py-1.5 rounded-lg bg-slate-800 hover:bg-slate-900 text-white text-xs font-semibold shadow-xs transition-colors">
                        Close
                    </button>
                </div>
            </div>
        `;
        document.body.appendChild(modal);

        modal.querySelector('#close-dataset-modal-btn').addEventListener('click', () => modal.remove());
        modal.querySelector('#close-dataset-modal-footer').addEventListener('click', () => modal.remove());
        modal.addEventListener('click', (e) => {
            if (e.target === modal) modal.remove();
        });
    }

    const listEl = modal.querySelector('#dataset-switcher-list');
    try {
        const datasets = await api.get('/api/v1/datasets/list').catch(() => []);
        if (!Array.isArray(datasets) || datasets.length === 0) {
            listEl.innerHTML = '<div class="text-center py-6 text-slate-400 text-xs">No datasets found in database.</div>';
            return;
        }

        listEl.innerHTML = datasets.map(d => {
            const isActive = d.is_active || d.status === 'ACTIVE';
            return `
                <div class="p-3 rounded-xl border ${isActive ? 'border-indigo-500 bg-indigo-50/40 ring-1 ring-indigo-500/20' : 'border-slate-200 hover:border-slate-300 hover:bg-slate-50/50'} flex items-center justify-between transition-all">
                    <div class="flex items-center gap-3 min-w-0">
                        <div class="w-8 h-8 rounded-lg ${isActive ? 'bg-indigo-600 text-white' : 'bg-slate-100 text-slate-500'} flex items-center justify-center flex-shrink-0">
                            <span class="material-symbols-outlined text-base">description</span>
                        </div>
                        <div class="min-w-0">
                            <p class="text-xs font-bold text-slate-900 truncate">${d.filename || 'Dataset'}</p>
                            <p class="text-[10px] text-slate-400">${(d.rows || d.row_count || 0).toLocaleString()} rows • ${d.uploaded_at ? d.uploaded_at.slice(0, 10) : 'Active'}</p>
                        </div>
                    </div>
                    <div>
                        ${isActive ? 
                            '<span class="inline-flex items-center gap-1 px-2.5 py-1 rounded-full text-[10px] font-bold bg-emerald-100 text-emerald-800"><span class="w-1.5 h-1.5 rounded-full bg-emerald-500"></span> Active</span>' : 
                            `<button class="btn-switch-dataset px-3 py-1 bg-white hover:bg-indigo-600 hover:text-white text-indigo-600 border border-indigo-200 text-xs font-semibold rounded-lg shadow-2xs transition-all cursor-pointer" data-id="${d.dataset_id}" data-fn="${d.filename}">Activate</button>`
                        }
                    </div>
                </div>
            `;
        }).join('');

        listEl.querySelectorAll('.btn-switch-dataset').forEach(btn => {
            btn.addEventListener('click', async () => {
                const id = btn.getAttribute('data-id');
                const fn = btn.getAttribute('data-fn');
                btn.disabled = true;
                btn.textContent = 'Switching...';
                try {
                    await api.post(`/api/v1/datasets/${id}/activate`, { dataset_id: id, filename: fn });
                    modal.remove();
                    window.location.reload();
                } catch (err) {
                    alert('Failed to switch dataset: ' + err.message);
                    btn.disabled = false;
                    btn.textContent = 'Activate';
                }
            });
        });
    } catch (err) {
        listEl.innerHTML = `<div class="text-center py-6 text-rose-500 text-xs">Failed to load datasets: ${escapeHtml(err.message)}</div>`;
    }
}

if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', initSidebar);
} else {
    initSidebar();
}

// Expose logout globally for any inline onclick handlers
window.appLogout = async () => {
    try { await api.post(api.endpoints.logout, {}); } catch (_) {}
    api.setAccessToken(null);
    window.location.replace('login.html');
};

// Reusable Modal Component
export function showModal(title, columns, data) {
    let modal = document.getElementById('global-modal');
    if (!modal) {
        modal = document.createElement('div');
        modal.id = 'global-modal';
        modal.className = 'fixed inset-0 z-50 flex items-center justify-center hidden';
        modal.innerHTML = `
            <div class="absolute inset-0 bg-slate-900/40 backdrop-blur-sm" id="global-modal-backdrop"></div>
            <div class="relative bg-white rounded-xl shadow-xl w-full max-w-2xl mx-4 max-h-[80vh] flex flex-col overflow-hidden animate-in fade-in zoom-in-95 duration-200">
                <div class="flex items-center justify-between px-6 py-4 border-b border-slate-100">
                    <h3 class="font-bold text-lg text-slate-800" id="global-modal-title">Title</h3>
                    <button id="global-modal-close" class="text-slate-400 hover:text-slate-600 transition-colors">
                        <span class="material-symbols-outlined">close</span>
                    </button>
                </div>
                <div class="p-6 overflow-y-auto custom-scrollbar">
                    <table class="w-full text-sm text-left">
                        <thead class="text-xs text-slate-500 bg-slate-50 uppercase" id="global-modal-thead"></thead>
                        <tbody id="global-modal-tbody" class="divide-y divide-slate-100"></tbody>
                    </table>
                </div>
            </div>
        `;
        document.body.appendChild(modal);
        
        document.getElementById('global-modal-close').addEventListener('click', () => {
            modal.classList.add('hidden');
        });
        document.getElementById('global-modal-backdrop').addEventListener('click', () => {
            modal.classList.add('hidden');
        });
    }
    
    document.getElementById('global-modal-title').innerText = title;
    
    const thead = document.getElementById('global-modal-thead');
    thead.innerHTML = `<tr>${columns.map(c => `<th class="px-4 py-3 font-medium">${c}</th>`).join('')}</tr>`;
    
    const tbody = document.getElementById('global-modal-tbody');
    tbody.innerHTML = data.map(row => 
        `<tr>${columns.map(c => `<td class="px-4 py-3 text-slate-700">${row[c] || ''}</td>`).join('')}</tr>`
    ).join('');
    
    modal.classList.remove('hidden');
}

window.showModal = showModal;
