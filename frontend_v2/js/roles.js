import { getCurrentUser } from './auth.js';

export const SIDEBAR_ITEMS_BY_ROLE = {
 'Admin': ['Dashboard', 'Department', 'Anomaly', 'Forecast', 'Upload', 'Validation', 'Reports', 'Settings', 'Users'],
 'Finance Manager': ['Dashboard', 'Department', 'Anomaly', 'Forecast', 'Upload', 'Validation', 'Reports', 'Settings'],
 'Auditor': ['Dashboard', 'Department', 'Anomaly', 'Forecast', 'Reports', 'Settings'],
 'CEO': ['Dashboard', 'Forecast', 'Reports']
};

export function getRole() {
 const user = getCurrentUser();
 return user ? user.role : 'Guest';
}

export function canAct(action) {
 const role = getRole();
 if (role === 'Admin') return true;
 
 if (role === 'Auditor') {
 // Auditors are read-only app-wide
 return false;
 }
 
 if (role === 'Finance Manager') {
 if (action === 'approve_anomaly' || action === 'reject_anomaly' || action === 'upload_dataset' || action === 'generate_report') {
 return true;
 }
 }
 
 if (role === 'CEO') {
 if (action === 'generate_report') {
 return true;
 }
 return false; // mostly read-only
 }
 
 return false;
}

export function applyRoleGating() {
 const role = getRole();
 const allowedItems = SIDEBAR_ITEMS_BY_ROLE[role] || [];
 
 document.querySelectorAll('[data-sidebar-item]').forEach(el => {
 const itemType = el.getAttribute('data-sidebar-item');
 if (!allowedItems.includes(itemType)) {
 el.style.display = 'none';
 }
 });

 document.querySelectorAll('[data-action]').forEach(el => {
 const action = el.getAttribute('data-action');
 if (!canAct(action)) {
 el.style.display = 'none';
 }
 });
}
