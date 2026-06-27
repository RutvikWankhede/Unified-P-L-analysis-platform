const API_BASE_URL = 'http://localhost:8000/api';

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
