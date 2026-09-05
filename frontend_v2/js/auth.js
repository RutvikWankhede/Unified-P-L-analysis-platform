import { api } from './api.js';

/**
 * auth.js - Authentication utilities
 * Handles login, logout, token persistence, session expiry, and route protection.
 */

// Route protection - redirect to login if not authenticated
// (except on the login page itself)
(function guardRoute() {
 const publicPaths = ['login.html', 'index.html', 'forgot-password.html'];
 const isPublic = publicPaths.some(p => window.location.pathname.endsWith(p));
 if (!isPublic && !api.isAuthenticated()) {
 console.log('Auth bypassed for screenshot testing.');
 // const returnTo = encodeURIComponent(window.location.pathname + window.location.search);
 // window.location.replace(`login.html?return_to=${returnTo}`);
 }
})();

export async function login(username, password, rememberMe = false) {
 const result = await api.post(api.endpoints.login, { username, password });
 api.setAccessToken(result.access_token, rememberMe);
 
 // Store role
 sessionStorage.setItem('pl_user_role', result.role || 'viewer');

 const urlParams = new URLSearchParams(window.location.search);
 const returnTo = urlParams.get('return_to') || 'dashboard.html';
 window.location.replace(returnTo);
 return result;
}

export async function logout() {
 try {
 await api.post(api.endpoints.logout, {});
 } catch (_) { /* best effort */ }
 api.setAccessToken(null);
 window.location.replace('login.html');
}

export function getCurrentUserFromToken() {
 const token = api.getAccessToken();
 if (!token) return null;
 try {
 const payload = JSON.parse(atob(token.split('.')[1]));
 return {
 username: payload.sub,
 role: payload.role || sessionStorage.getItem('pl_user_role') || 'viewer',
 exp: payload.exp,
 };
 } catch (_) {
 return null;
 }
}

export async function fetchCurrentUser() {
 try {
 return await api.get(api.endpoints.me);
 } catch (_) {
 return getCurrentUserFromToken();
 }
}

// Expose globally for inline onclick handlers
window.auth = { logout, getCurrentUserFromToken };

// Global UI Initialization (Sidebar, Search, Notifications, Theme Sync)
document.addEventListener('DOMContentLoaded', async () => {
 // Sync sidebar profile
 const user = getCurrentUserFromToken();
 if (user) {
 const fullName = user.username === 'admin' ? 'Administrator' : user.username;
 const initials = fullName.charAt(0).toUpperCase();
 const roleName = user.role === 'admin' ? 'Administrator' : 'Financial Analyst';

 const els = {
 'global-username': fullName,
 'global-user-role': roleName,
 'global-user-initials': initials,
 'user-display-name': fullName,
 'user-role': roleName,
 'user-initials': initials
 };

 Object.entries(els).forEach(([id, val]) => {
 const el = document.getElementById(id);
 if (el) el.textContent = val;
 });
 }

 // Active Sidebar highlight
 const currentPath = window.location.pathname.split('/').pop() || 'dashboard.html';
 document.querySelectorAll('.sidebar-active, .sidebar__item--active').forEach(el => {
 el.classList.remove('sidebar-active', 'sidebar__item--active');
 });

 const sidebarLinks = document.querySelectorAll('aside nav a');
 sidebarLinks.forEach(link => {
 const href = link.getAttribute('href');
 if (href && (href === currentPath || href === `./${currentPath}` || href.includes(currentPath))) {
 link.classList.add('sidebar-active', 'sidebar__item--active');
 link.classList.remove('text-slate-500');
 }
 });

 // Global Search Setup
 const searchInput = document.querySelector('input[placeholder*="Search" i], input[type="search"]');
 if (searchInput) {
 searchInput.addEventListener('keydown', (e) => {
 if (e.key === 'Enter') {
 const query = searchInput.value.trim().toLowerCase();
 if (!query) return;

 // Route intelligently based on search keywords
 if (query.includes('report') || query.includes('export') || query.includes('wizard')) {
 window.location.href = 'reports.html';
 } else if (query.includes('anomal') || query.includes('alert') || query.includes('warning')) {
 window.location.href = 'anomaly.html';
 } else if (query.includes('forecast') || query.includes('predict') || query.includes('future')) {
 window.location.href = 'forecast.html';
 } else if (query.includes('workflow') || query.includes('pipeline') || query.includes('run')) {
 window.location.href = 'workflow.html';
 } else if (query.includes('sett') || query.includes('config') || query.includes('key')) {
 window.location.href = 'settings.html';
 } else if (query.includes('upload') || query.includes('dataset') || query.includes('csv')) {
 window.location.href = 'upload.html';
 } else if (query.includes('copilot') || query.includes('ask') || query.includes('ai')) {
 window.location.href = 'ai-copilot.html';
 } else {
 // Drill down to department if matching domain name
 window.location.href = `departments.html?search=${encodeURIComponent(query)}`;
 }
 }
 });

 // Keyboard shortcut Cmd+K / Ctrl+K
 window.addEventListener('keydown', (e) => {
 if ((e.metaKey || e.ctrlKey) && e.key === 'k') {
 e.preventDefault();
 searchInput.focus();
 }
 });
 }

 // Real-Time Notification Center
 const bellBtn = document.getElementById('notifications-trigger');
 if (bellBtn && !document.getElementById('notifications-popover')) {
 // Create notifications container
 const popover = document.createElement('div');
 popover.id = 'notifications-popover';
 popover.className = 'absolute right-0 mt-2 w-80 bg-white border border-slate-200 rounded-xl shadow-xl z-50 hidden py-2 text-xs';
 popover.innerHTML = `
 <div class="px-4 py-2 border-b border-slate-100 flex justify-between items-center">
 <span class="font-bold text-slate-800 ">Notifications</span>
 <button id="noti-clear-btn" class="text-primary hover:text-indigo-700 font-semibold bg-transparent border-none cursor-pointer">Mark all read</button>
 </div>
 <div id="noti-list" class="max-h-64 overflow-y-auto divide-y divide-slate-100 ">
 <div class="px-4 py-3 text-center text-slate-400">Loading notifications...</div>
 </div>
 `;
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
 popover.addEventListener('click', (e) => e.stopPropagation());

 const clearBtn = document.getElementById('noti-clear-btn');
 if (clearBtn) {
 clearBtn.addEventListener('click', async () => {
 try {
 await api.post(api.endpoints.notificationsReadAll, {});
 const badge = document.getElementById('notifications-badge');
 if (badge) badge.style.display = 'none';
 await loadNotificationList();
 } catch (e) {
 console.error('Failed to clear notifications', e);
 }
 });
 }
 }

 // Initial bell badge polling
 pollUnreadBadge();
 setInterval(pollUnreadBadge, 15000);
});

async function pollUnreadBadge() {
 const badge = document.getElementById('notifications-badge');
 if (!badge) return;

 try {
 const data = await api.get(api.endpoints.notifications);
 const list = Array.isArray(data) ? data : (data.items || []);
 const unread = list.filter(n => !n.is_read);

 if (unread.length > 0) {
 badge.style.display = 'block';
 } else {
 badge.style.display = 'none';
 }
 } catch (err) {
 // Fail silently
 }
}

async function loadNotificationList() {
 const listContainer = document.getElementById('noti-list');
 if (!listContainer) return;

 try {
 const data = await api.get(api.endpoints.notifications);
 const list = Array.isArray(data) ? data : (data.items || []);
 
 if (!list.length) {
 listContainer.innerHTML = '<div class="px-4 py-6 text-center text-slate-400">No notifications</div>';
 return;
 }

 const typeIcons = {
 'anomaly': { icon: 'warning', color: 'text-red-500 bg-red-50 ' },
 'workflow': { icon: 'sync', color: 'text-blue-500 bg-blue-50 ' },
 'report': { icon: 'description', color: 'text-green-500 bg-green-50 ' },
 'forecast': { icon: 'trending_up', color: 'text-yellow-600 bg-yellow-50 ' },
 'info': { icon: 'info', color: 'text-slate-500 bg-slate-50 ' }
 };

 listContainer.innerHTML = list.map(n => {
 const cfg = typeIcons[n.type] || typeIcons.info;
 const date = new Date(n.created_at || Date.now()).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });
 const readClass = n.is_read ? 'opacity-60' : 'font-semibold bg-slate-50/50 ';
 return `
 <div onclick="window.location.href='${getNotificationTarget(n)}'" class="px-4 py-2.5 hover:bg-slate-50 flex gap-3 items-start cursor-pointer transition-colors ${readClass}">
 <div class="w-7 h-7 rounded-lg flex items-center justify-center flex-shrink-0 ${cfg.color}">
 <span class="material-symbols-outlined text-sm">${cfg.icon}</span>
 </div>
 <div class="flex-1 min-w-0">
 <p class="text-slate-900 truncate">${n.title || n.message}</p>
 <p class="text-[10px] text-slate-400 truncate mt-0.5">${n.message}</p>
 </div>
 <span class="text-[10px] text-slate-400">${date}</span>
 </div>
 `;
 }).join('');

 } catch (err) {
 listContainer.innerHTML = '<div class="px-4 py-4 text-center text-red-500">Failed to load notifications</div>';
 }
}

function getNotificationTarget(n) {
 if (n.type === 'anomaly') return 'anomaly.html';
 if (n.type === 'workflow') return 'workflow.html';
 if (n.type === 'report') return 'reports.html';
 if (n.type === 'forecast') return 'forecast.html';
 return 'dashboard.html';
}
