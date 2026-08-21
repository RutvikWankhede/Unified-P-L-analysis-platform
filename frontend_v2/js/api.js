// UI utilities for Toasts, Loaders, and Empty States
class UI {
    static showToast(message, type = 'info') {
        let container = document.getElementById('toast-container');
        if (!container) {
            container = document.createElement('div');
            container.id = 'toast-container';
            document.body.appendChild(container);
        }

        const toast = document.createElement('div');
        toast.className = `toast toast-${type}`;
        
        let icon = 'info';
        if (type === 'success') icon = 'check_circle';
        if (type === 'error') icon = 'error';

        toast.innerHTML = `
            <span class="material-symbols-outlined">${icon}</span>
            <span>${message}</span>
        `;
        
        container.appendChild(toast);
        
        // Trigger animation
        setTimeout(() => toast.classList.add('show'), 10);
        
        setTimeout(() => {
            toast.classList.remove('show');
            setTimeout(() => toast.remove(), 300);
        }, 3000);
    }

    static showLoading(containerId) {
        const container = document.getElementById(containerId);
        if (container) {
            container.innerHTML = `
                <div class="loading-state">
                    <div class="spinner"></div>
                    <p>Loading data...</p>
                </div>
            `;
        }
    }

    static showEmptyState(containerId, message = 'No data available', icon = 'inbox') {
        const container = document.getElementById(containerId);
        if (container) {
            container.innerHTML = `
                <div class="empty-state">
                    <span class="material-symbols-outlined">${icon}</span>
                    <p>${message}</p>
                </div>
            `;
        }
    }
}
window.UI = UI;

const API_BASE_URL = 'http://localhost:8000/api/v1';

const api = {
    async request(endpoint, options = {}) {
        const token = localStorage.getItem('token');
        const headers = {
            ...options.headers,
        };

        if (token) {
            headers['Authorization'] = `Bearer ${token}`;
        }

        // Only set Content-Type if we aren't sending FormData
        if (!(options.body instanceof FormData) && !headers['Content-Type']) {
            headers['Content-Type'] = 'application/json';
        }

        const config = {
            ...options,
            headers,
        };

        const response = await fetch(`${API_BASE_URL}${endpoint}`, config);
        
        if (response.status === 401) {
            localStorage.removeItem('token');
            window.location.href = '/index.html';
            throw new Error('Unauthorized');
        }

        if (!response.ok) {
            let err = 'API Error';
            try {
                const data = await response.json();
                err = data.detail || err;
            } catch (e) {}
            throw new Error(err);
        }

        if (response.status === 204) return null;
        return response.json();
    },

    login(username, password) {
        return this.request('/auth/login', {
            method: 'POST',
            body: JSON.stringify({ username, password, email: "dummy@test.com" }) 
        });
    },

    upload(file) {
        const formData = new FormData();
        formData.append('file', file);
        return this.request('/pl/upload', {
            method: 'POST',
            body: formData
        });
    },

    detectAnomalies(uploadId) {
        return this.request(`/anomalies/detect?upload_id=${uploadId}`, { method: 'POST' });
    },

    getAnomalies() {
        return this.request('/anomalies/');
    },

    getAnomalyDetail(id) {
        return this.request(`/anomalies/${id}`);
    }
};

window.api = api;
