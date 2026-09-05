/**
 * api.js - Central API client for Unified P&L Intelligence Platform
 * All HTTP calls go through this module. Never use raw fetch() in page scripts.
 */

const API_BASE = window.__API_BASE__ || (
  window.location.port === '3000'
    ? `${window.location.protocol}//${window.location.hostname}:8000`
    : (window.location.hostname === 'localhost' || window.location.hostname === '127.0.0.1' ? `${window.location.protocol}//${window.location.hostname}:8000` : '')
);
const WS_BASE = API_BASE.replace('http', 'ws');

const endpoints = {
 // Auth
 login: '/api/v1/auth/login',
 refresh: '/api/v1/auth/refresh',
 logout: '/api/v1/auth/logout',
 me: '/api/v1/auth/me',
 updateMe: '/api/v1/auth/me',
 auditLogs: '/api/v1/auth/audit-logs',
 forgotPassword: '/api/v1/auth/forgot-password',

 // P&L Core
 summary: '/api/v1/pl/summary',
 kpis: '/api/v1/pl/summary',
 charts: '/api/v1/pl/charts',
 timeseries: '/api/v1/pl/charts',
 forecast: '/api/v1/pl/forecast',
 departments: '/api/v1/pl/departments',
 departmentSummary: '/api/v1/pl/departments/summary',
 departmentTrend: '/api/v1/pl/departments/trend',
 records: '/api/v1/pl/records',
 workflows: '/api/v1/pl/workflows',
 upload: '/api/v1/pl/upload',
 finalizeUpload: '/api/v1/pl/finalize-upload',

 // Datasets
 datasetsRecent: '/api/v1/datasets/recent',
 datasetsUpload: '/api/v1/pl/upload',
 schemaMapping: (id) => `/api/v1/datasets/${id}/schema-mapping`,
 pipelineStatus: (id) => `/api/v1/datasets/${id}/pipeline-status`,
 datasetQuality: (id) => `/api/v1/datasets/${id}/quality`,

 // Anomalies
 anomalies: '/api/v1/anomalies/',
 anomalyDecision: (id)=> `/api/v1/anomalies/${id}/status`,

 // AI Features
 copilotQuery: '/api/v1/explanations/copilot',
 aiRecommendations: '/api/v1/recommendations/',
 explanations: (id) => `/api/v1/explanations/${id}`,

 // Reports
 reports: '/api/v1/reports',
 reportCsv: '/api/v1/reports/csv',
 reportPdf: '/api/v1/reports/pdf',
 reportExecutive: '/api/v1/reports/executive',

 // System
 health: '/api/v1/system/health',
 notifications: '/api/v1/notifications/',
 notificationsReadAll: '/api/v1/notifications/read-all',
};

// Token storage
let _accessToken = sessionStorage.getItem('pl_access_token') || localStorage.getItem('pl_access_token') || null;
let _isRefreshing = false;
let _refreshQueue = [];

function setAccessToken(token, persistent = false) {
 _accessToken = token;
 if (token) {
 sessionStorage.setItem('pl_access_token', token);
 if (persistent) localStorage.setItem('pl_access_token', token);
 } else {
 sessionStorage.removeItem('pl_access_token');
 localStorage.removeItem('pl_access_token');
 }
}

function getAccessToken() {
 return _accessToken;
}

function isAuthenticated() {
 return !!_accessToken;
}

async function request(method, path, body = null, options = {}) {
 const url = `${API_BASE}${path}`;
 const headers = { 'Content-Type': 'application/json' };

 if (_accessToken) {
 headers['Authorization'] = `Bearer ${_accessToken}`;
 }

 const fetchOptions = { method, headers, ...options };

 // Don't JSON stringify FormData
 if (body && !(body instanceof FormData)) {
 fetchOptions.body = JSON.stringify(body);
 } else if (body instanceof FormData) {
 delete headers['Content-Type']; // Let browser set multipart boundary
 fetchOptions.body = body;
 }

 let response;
 try {
 response = await fetch(url, fetchOptions);
 } catch (err) {
 throw { type: 'network', message: 'Network error. Is the backend running?' };
 }

 // Handle 401 with token refresh
 if (response.status === 401 && !options._isRetry) {
 try {
 const newToken = await _refreshAccessToken();
 headers['Authorization'] = `Bearer ${newToken}`;
 const retryOpts = { ...fetchOptions, headers, _isRetry: true };
 response = await fetch(url, retryOpts);
 } catch (refreshErr) {
 setAccessToken(null);
 const currentUrl = encodeURIComponent(window.location.pathname + window.location.search);
 window.location.href = `/login.html?return_to=${currentUrl}`;
 throw { type: 'auth', message: 'Session expired' };
 }
 }

 if (!response.ok) {
 let errorData = {};
 try { errorData = await response.json(); } catch (_) {}
 throw { type: 'http', status: response.status, data: errorData, message: errorData.detail || `HTTP ${response.status}` };
 }

 // Handle empty responses (204)
 if (response.status === 204) return null;

 const contentType = response.headers.get('content-type') || '';
 if (contentType.includes('application/json')) {
 const data = await response.json();
 return normalizeData(data);
 }
 return response;
}

// Automatically map backend fields to frontend expected fields
function normalizeData(obj) {
 if (Array.isArray(obj)) {
 return obj.map(normalizeData);
 } else if (obj !== null && typeof obj === 'object') {
 const normalized = {};
 for (const [key, value] of Object.entries(obj)) {
 let newKey = key;
 if (key === 'total_revenue') newKey = 'revenue';
 else if (key === 'total_expense') newKey = 'expense';
 else if (key === 'net_profit') newKey = 'profit';
 else if (key === 'total_profit') newKey = 'profit';
 
 normalized[newKey] = normalizeData(value);
 }
 return normalized;
 }
 return obj;
}

async function _refreshAccessToken() {
 if (_isRefreshing) {
 return new Promise((resolve, reject) => {
 _refreshQueue.push({ resolve, reject });
 });
 }

 _isRefreshing = true;
 try {
 const res = await fetch(`${API_BASE}${endpoints.refresh}`, {
 method: 'POST',
 credentials: 'include',
 });

 if (!res.ok) throw new Error('Refresh failed');

 const data = await res.json();
 setAccessToken(data.access_token);
 _refreshQueue.forEach(q => q.resolve(data.access_token));
 return data.access_token;
 } catch (err) {
 _refreshQueue.forEach(q => q.reject(err));
 throw err;
 } finally {
 _isRefreshing = false;
 _refreshQueue = [];
 }
}

// Upload helper that uses FormData
async function uploadFile(path, file) {
 const formData = new FormData();
 formData.append('file', file);

 const headers = {};
 if (_accessToken) {
 headers['Authorization'] = `Bearer ${_accessToken}`;
 }

 const response = await fetch(`${API_BASE}${path}`, {
 method: 'POST',
 headers,
 body: formData,
 });

 if (!response.ok) {
 let errorData = {};
 try { errorData = await response.json(); } catch (_) {}
 throw { type: 'http', status: response.status, data: errorData };
 }
 return response.json();
}

// Download helper for binary responses (PDF/CSV)
async function download(path, filename, options = {}) {
 const headers = { 'Content-Type': 'application/json' };
 if (_accessToken) headers['Authorization'] = `Bearer ${_accessToken}`;

 const fetchOpts = { method: options.method || 'GET', headers };
 if (options.body) fetchOpts.body = JSON.stringify(options.body);

 const response = await fetch(`${API_BASE}${path}`, fetchOpts);
 if (!response.ok) throw new Error(`Download failed: ${response.status}`);

 const blob = await response.blob();
 const url = URL.createObjectURL(blob);
 const a = document.createElement('a');
 a.href = url;
 a.download = filename;
 document.body.appendChild(a);
 a.click();
 document.body.removeChild(a);
 URL.revokeObjectURL(url);
}

export const api = {
 get: (path) => request('GET', path),
 post: (path, body) => request('POST', path, body),
 put: (path, body) => request('PUT', path, body),
 patch: (path, body) => request('PATCH', path, body),
 delete: (path) => request('DELETE', path),
 uploadFile,
 download,
 endpoints,
 setAccessToken,
 getAccessToken,
 isAuthenticated,
};

// Global WebSocket setup
let ws;
function initWebSocket() {
 if (ws || !_accessToken) return;
 ws = new WebSocket(`${WS_BASE}/api/v1/ws?token=${_accessToken}`);
 ws.onmessage = (event) => {
 try {
 const data = JSON.parse(event.data);
 // Dispatch custom event for real-time updates
 const customEvent = new CustomEvent('pl:update', { detail: data });
 window.dispatchEvent(customEvent);
 } catch (e) {
 console.error('WebSocket parsing error', e);
 }
 };
 ws.onclose = () => {
 ws = null;
 setTimeout(initWebSocket, 5000); // Reconnect
 };
}

if (_accessToken) {
 initWebSocket();
}

// Hook into login/logout
const originalSetAccessToken = setAccessToken;
api.setAccessToken = (token, persistent) => {
 originalSetAccessToken(token, persistent);
 if (token) initWebSocket();
 else if (ws) { ws.close(); ws = null; }
};

// Intercept all raw fetch calls to automatically inject the Authorization header
const originalFetch = window.fetch;
window.fetch = async function(resource, config) {
  if (typeof resource === 'string' && (resource.startsWith('/api') || resource.includes('/api/'))) {
    if (resource.startsWith('/api') && API_BASE && !resource.startsWith(API_BASE)) {
      resource = API_BASE + resource;
    }
    config = config || {};
    if (!config.headers) {
      config.headers = {};
    }
    if (_accessToken) {
      if (config.headers instanceof Headers) {
        if (!config.headers.has('Authorization')) {
          config.headers.set('Authorization', `Bearer ${_accessToken}`);
        }
      } else if (Array.isArray(config.headers)) {
        config.headers.push(['Authorization', `Bearer ${_accessToken}`]);
      } else {
        if (!config.headers['Authorization']) {
          config.headers['Authorization'] = `Bearer ${_accessToken}`;
        }
      }
    }
  }
  return originalFetch.call(this, resource, config);
};
