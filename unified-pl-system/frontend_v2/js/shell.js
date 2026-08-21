/**
 * shell.js - Application Chrome (Sidebar + Navigation)
 * =====================================================
 * Single source of truth for the sidebar.
 * Injected into every authenticated page via <div id="sidebar-container">.
 *
 * Responsibilities:
 * - Route guard (redirect to login if no token)
 * - Inject sidebar HTML
 * - Populate real user info from JWT
 * - Auto-highlight active nav item
 * - Wire notification bell popover
 * - Wire logout button
 * - Global search keyboard shortcut
 */

import { api } from './api.js';

// ─── Route Guard (runs synchronously before render) ──────────────────────────
// Secondary check: the inline <script> in each page already does a fast check.
// This module-level guard handles the case where sessionStorage is cleared
// between the inline check and module execution.
(function guardRoute() {
    const PUBLIC = ['login.html', 'forgot-password.html', 'index.html'];
    const page = window.location.pathname.split('/').pop() || 'login.html';
    if (!PUBLIC.includes(page) && !api.isAuthenticated()) {
        const ret = encodeURIComponent(window.location.pathname + window.location.search);
        window.location.replace(`login.html?return_to=${ret}`);
    }
})();

// ─── Navigation Map ──────────────────────────────────────────────────────────
const NAV_ITEMS = [
    { href: 'dashboard.html',  icon: 'grid_view',    label: 'Dashboard' },
    { href: 'departments.html',icon: 'domain',        label: 'Departments' },
    { href: 'datasets.html',   icon: 'upload_file',   label: 'Upload / Datasets' },
    { href: 'forecast.html',   icon: 'trending_up',   label: 'Forecast' },
    { href: 'anomalies.html',  icon: 'warning',       label: 'Anomaly Detection' },
    { href: 'copilot.html',    icon: 'smart_toy',     label: 'AI Copilot' },
    { href: 'workflow.html',   icon: 'account_tree',  label: 'Workflow' },
    { href: 'reports.html',    icon: 'description',   label: 'Reports' },
    { href: 'audit.html',      icon: 'history',       label: 'Audit Trail' },
    { href: 'settings.html',   icon: 'settings',      label: 'Settings' },
];

// Pages that share a nav item (so they highlight correctly)
const PAGE_ALIASES = {
    // Old filenames that might be bookmarked / linked from backend
    'upload.html':     'datasets.html',
    'anomaly.html':    'anomalies.html',
    'ai-copilot.html': 'copilot.html',
    // Sub-pages that roll up to a parent nav item
    'department.html':    'departments.html',
    'schema-mapping.html':'datasets.html',
    'validation.html':    'datasets.html',
    'executive.html':     'reports.html',
    'export.html':        'reports.html',
    'pivot.html':         'reports.html',
    'recommendations.html':'reports.html',
};

// ─── User info from JWT ──────────────────────────────────────────────────────
function getUserInfo() {
    try {
        const token = api.getAccessToken();
        if (!token) return { name: 'Admin', initials: 'A', role: 'Administrator' };
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

// ─── Sidebar HTML Builder ─────────────────────────────────────────────────────
function buildSidebar(user, activePage) {
    const navHTML = NAV_ITEMS.map(item => {
        const isActive = item.href === activePage;
        const activeClass = isActive
            ? 'nav-item group relative flex items-center gap-3 px-4 py-3 mb-1 text-sm rounded-xl bg-indigo-50 text-indigo-600 font-semibold transition-all duration-300'
            : 'nav-item group relative flex items-center gap-3 px-4 py-3 mb-1 text-sm rounded-xl text-slate-500 font-medium hover:bg-slate-50 hover:text-slate-900 transition-all duration-300';
        const iconClass = isActive 
            ? 'material-symbols-outlined text-[20px] text-indigo-600 transition-transform duration-300' 
            : 'material-symbols-outlined text-[20px] text-slate-400 group-hover:text-slate-700 transition-transform duration-300 group-hover:scale-110';
        
        return `<a class="${activeClass}" href="${item.href}" data-path="${item.href}">
            <span class="${iconClass}" style="font-family: 'Material Symbols Outlined', sans-serif !important;">${item.icon}</span> 
            <span class="nav-label flex-1 truncate">${item.label}</span>
            ${isActive ? '<div class="absolute right-2 w-1.5 h-1.5 rounded-full bg-indigo-600"></div>' : ''}
        </a>`;
    }).join('');

    const isLight = localStorage.getItem('theme') !== 'dark';
    const themeBtnClass = isLight ? 'bg-indigo-500' : 'bg-slate-300';
    const themeKnobClass = isLight ? 'translate-x-4' : 'translate-x-0';

    return `<!-- Sidebar -->
<aside id="main-sidebar" class="w-[260px] h-screen fixed left-0 top-0 bg-white border-r border-slate-200 flex flex-col z-50 transition-all duration-300">
    
    <!-- Logo Section -->
    <div class="h-20 px-6 flex items-center justify-between cursor-pointer border-b border-slate-100" onclick="window.location.href='dashboard.html'">
        <div class="flex items-center gap-3 sidebar-brand overflow-hidden">
            <div class="w-9 h-9 bg-indigo-600 rounded-xl flex items-center justify-center text-white flex-shrink-0 shadow-sm shadow-indigo-200">
                <span class="material-symbols-outlined text-xl" style="font-family: 'Material Symbols Outlined' !important;">analytics</span>
            </div>
            <div class="flex-1 min-w-0 sidebar-text transition-opacity duration-300">
                <h1 class="text-[15px] font-bold leading-tight text-slate-900 truncate">Unified P&L</h1>
                <p class="text-[11px] font-medium text-slate-500 truncate mt-0.5">Enterprise Platform</p>
            </div>
        </div>
        <button id="sidebar-toggle" class="w-8 h-8 flex items-center justify-center rounded-lg text-slate-400 hover:text-slate-800 hover:bg-slate-100 transition-all">
            <span class="material-symbols-outlined text-[20px]" style="font-family: 'Material Symbols Outlined' !important;">menu_open</span>
        </button>
    </div>

    <!-- Navigation Menu -->
    <nav class="flex-1 px-4 py-6 overflow-y-auto hide-scrollbar flex flex-col">
        <div class="text-[11px] font-bold text-slate-400 uppercase tracking-wider mb-3 px-2 sidebar-text">Menu</div>
        ${navHTML}
    </nav>

    <!-- Bottom Section -->
    <div class="px-4 pb-6 pt-4 sidebar-bottom border-t border-slate-100 bg-slate-50/50">
        
        <!-- Company Selector -->
        <button class="w-full flex flex-col text-left px-4 py-3 rounded-xl bg-white border border-slate-200 shadow-sm mb-4 hover:border-indigo-300 hover:shadow-md transition-all duration-300 group relative">
            <div class="flex items-center justify-between w-full mb-1">
                <span class="text-[10px] text-slate-500 uppercase font-bold tracking-wider">Company</span>
                <span class="material-symbols-outlined text-[16px] text-slate-400 group-hover:text-indigo-600 transition-colors" style="font-family: 'Material Symbols Outlined' !important;">expand_more</span>
            </div>
            <span class="text-sm font-bold text-slate-800 truncate block w-full">TechNova Solutions</span>
        </button>

        <!-- User Card -->
        <div class="flex items-center justify-between px-3 py-3 mb-4 rounded-xl bg-white border border-slate-100 hover:border-slate-300 hover:shadow-sm transition-all group cursor-pointer relative" id="user-card">
            <div class="relative flex-shrink-0">
                <div class="w-10 h-10 rounded-full bg-indigo-100 text-indigo-700 flex items-center justify-center font-bold text-sm border-2 border-white shadow-sm">
                    ${user.initials}
                </div>
                <div class="absolute bottom-0 right-0 w-3 h-3 rounded-full bg-green-500 border-2 border-white"></div>
            </div>
            <div class="flex-1 min-w-0 px-3 sidebar-text">
                <p class="text-sm font-bold text-slate-800 truncate">${user.name}</p>
                <p class="text-[11px] font-medium text-slate-500 truncate mt-0.5">${user.role}</p>
            </div>
            <button id="logout-btn" title="Sign out" class="w-8 h-8 rounded-lg flex items-center justify-center text-slate-400 hover:text-red-500 hover:bg-red-50 transition-all opacity-0 group-hover:opacity-100 sidebar-text">
                <span class="material-symbols-outlined text-[18px]" style="font-family: 'Material Symbols Outlined' !important;">logout</span>
            </button>
        </div>

        <!-- Theme Toggle -->
        <div class="flex items-center justify-between px-4 py-3 rounded-xl bg-white border border-slate-200">
            <div class="flex items-center gap-2.5 text-slate-600 sidebar-text">
                <span class="material-symbols-outlined text-[18px]" style="font-family: 'Material Symbols Outlined' !important;">light_mode</span>
                <span class="text-[13px] font-semibold" id="theme-toggle-label">Light Theme</span>
            </div>
            <button id="theme-toggle-btn" class="w-10 h-6 ${themeBtnClass} rounded-full relative transition-colors duration-300 focus:outline-none shrink-0">
                <div id="theme-toggle-knob" class="w-4 h-4 bg-white rounded-full absolute top-[4px] left-[4px] transform ${themeKnobClass} transition-transform duration-300 shadow-sm"></div>
            </button>
        </div>
    </div>
</aside>
<style>
    /* Global Material Icons Fix */
    .material-symbols-outlined {
        font-family: 'Material Symbols Outlined', sans-serif !important;
        font-feature-settings: 'liga' !important;
        -webkit-font-feature-settings: 'liga' !important;
    }
    
    /* Sidebar Collapsed State */
    .sidebar-collapsed { width: 88px !important; }
    .sidebar-collapsed .sidebar-text { display: none !important; opacity: 0; }
    .sidebar-collapsed .nav-item { justify-content: center; padding: 0.75rem !important; }
    .sidebar-collapsed .nav-label { display: none; }
    .sidebar-collapsed #sidebar-toggle { transform: rotate(180deg); margin: 0 auto; }
    .sidebar-collapsed .sidebar-brand { display: none; }
    .sidebar-collapsed .sidebar-bottom { padding: 1rem 0.75rem !important; }
    .sidebar-collapsed #user-card { justify-content: center; padding: 0.5rem; background: transparent; border: none; box-shadow: none; }
</style>`;
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
            <button id="noti-clear-btn" class="text-primary hover:text-indigo-700 font-semibold bg-transparent border-none cursor-pointer">Mark all read</button>
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
        const targets = { anomaly: 'anomaly.html', workflow: 'workflow.html', report: 'reports.html', forecast: 'forecast.html' };
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
    const searchInput = document.querySelector('input[*="Search"]');
    if (!searchInput) return;

    const ROUTES = [
        ['report', 'reports.html'],
        ['anomal', 'anomaly.html'],
        ['alert', 'anomaly.html'],
        ['forecast', 'forecast.html'],
        ['predict', 'forecast.html'],
        ['workflow', 'workflow.html'],
        ['upload', 'upload.html'],
        ['dataset', 'upload.html'],
        ['csv', 'upload.html'],
        ['copilot', 'ai-copilot.html'],
        ['setting', 'settings.html'],
        ['config', 'settings.html'],
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
document.addEventListener('DOMContentLoaded', () => {
    const container = document.getElementById('sidebar-container');
    if (!container) return; // Not an app page

    // Determine active page
    const currentPage = window.location.pathname.split('/').pop() || 'dashboard.html';
    const activePage = PAGE_ALIASES[currentPage] || currentPage;

    // Build and inject sidebar
    const user = getUserInfo();
    container.innerHTML = buildSidebar(user, activePage);

    // Wire interactions
    initLogout();
    initSearch();
    initNotifications();

    // Theme toggle setup
    const themeBtn = document.getElementById('theme-toggle-btn');
    const themeKnob = document.getElementById('theme-toggle-knob');
    const themeLabel = document.getElementById('theme-toggle-label');
    
    if (themeBtn && themeKnob) {
        themeBtn.addEventListener('click', () => {
            let isLight = localStorage.getItem('theme') !== 'dark';
            isLight = !isLight;
            localStorage.setItem('theme', isLight ? 'light' : 'dark');
            
            if (isLight) {
                themeBtn.classList.add('bg-[#6366F1]');
                themeBtn.classList.remove('bg-gray-300');
                themeKnob.classList.add('left-5');
                themeKnob.classList.remove('left-1');
                if(themeLabel) themeLabel.innerText = 'Light Theme';
            } else {
                themeBtn.classList.remove('bg-[#6366F1]');
                themeBtn.classList.add('bg-gray-300');
                themeKnob.classList.remove('left-5');
                themeKnob.classList.add('left-1');
                if(themeLabel) themeLabel.innerText = 'Dark Theme';
            }
            window.dispatchEvent(new Event('themeChanged'));
        });
    }

    // Adjust main content margin since sidebar width is now 260px
    const mainContent = document.querySelector('main');
    if (mainContent) {
        mainContent.classList.remove('ml-[280px]', 'ml-[240px]', 'ml-[80px]');
        mainContent.classList.add('ml-[260px]');
    }

    // Update topbar greeting if present
    const greetingEl = document.getElementById('greeting-text');
    if (greetingEl) {
        const hour = new Date().getHours();
        const part = hour < 12 ? 'morning' : hour < 18 ? 'afternoon' : 'evening';
        greetingEl.textContent = `Good ${part}, ${user.name}! 👋`;
    }

    // Sidebar Toggle
    const sidebar = document.getElementById('main-sidebar');
    const toggleBtn = document.getElementById('sidebar-toggle');
    const isCollapsed = localStorage.getItem('sidebar_collapsed') === 'true';

    if (isCollapsed && sidebar) {
        sidebar.classList.add('sidebar-collapsed');
        if (mainContent) {
            mainContent.classList.remove('ml-[260px]');
            mainContent.classList.add('ml-[88px]');
        }
    }

    if (toggleBtn && sidebar) {
        toggleBtn.addEventListener('click', (e) => {
            e.stopPropagation();
            sidebar.classList.toggle('sidebar-collapsed');
            const collapsed = sidebar.classList.contains('sidebar-collapsed');
            localStorage.setItem('sidebar_collapsed', collapsed);
            
            if (mainContent) {
                if (collapsed) {
                    mainContent.classList.remove('ml-[260px]');
                    mainContent.classList.add('ml-[88px]');
                } else {
                    mainContent.classList.remove('ml-[88px]');
                    mainContent.classList.add('ml-[260px]');
                }
            }
        });
    }
});

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

// Make globally available for inline onclick handlers if needed
window.showModal = showModal;
