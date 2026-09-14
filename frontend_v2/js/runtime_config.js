// Runtime configuration for Unified P&L Intelligence Platform
// In Docker / Production (served via Nginx reverse proxy on port 3000 or 80), API base is relative.
// In local standalone dev mode, run.py dynamically injects the active backend port.
if (typeof window !== 'undefined') {
  if (!window.__RUNTIME_CONFIG_SET__) {
    if (window.location.port === '3000' || window.location.port === '80' || !window.location.port) {
      window.__BACKEND_PORT__ = 8000;
      window.__API_BASE__ = "";
      window.__FRONTEND_PORT__ = 3000;
    } else {
      window.__BACKEND_PORT__ = 8000;
      window.__API_BASE__ = "http://127.0.0.1:8000";
      window.__FRONTEND_PORT__ = 3000;
    }
  }
}
