document.addEventListener('DOMContentLoaded', async () => {
    // Check auth
    if (!localStorage.getItem('token')) {
        window.location.href = 'index.html';
        return;
    }

    document.getElementById('logout-btn').addEventListener('click', (e) => {
        e.preventDefault();
        localStorage.removeItem('token');
        window.location.href = 'index.html';
    });

    try {
        const anomalies = await window.api.getAnomalies();
        
        document.getElementById('kpi-anomalies').textContent = anomalies.length;
        const highSev = anomalies.filter(a => a.severity === 'High').length;
        document.getElementById('kpi-high-sev').textContent = highSev;
        
        const tbody = document.querySelector('#recent-anomalies-table tbody');
        
        if (anomalies.length === 0) {
            tbody.innerHTML = `<tr><td colspan="3" style="text-align: center;">
                <div class="empty-state" style="padding: 20px;">
                    <span class="material-symbols-outlined">check_circle</span>
                    <p>No anomalies detected</p>
                </div>
            </td></tr>`;
        } else {
            anomalies.slice(0, 5).forEach(a => {
                const tr = document.createElement('tr');
                tr.innerHTML = `
                    <td><span style="color: ${a.severity === 'High' ? 'var(--color-accent-red)' : 'var(--color-accent-amber)'}">${a.severity}</span></td>
                    <td>${a.anomaly_score.toFixed(2)}</td>
                    <td>${a.status}</td>
                `;
                tbody.appendChild(tr);
            });
        }

        // We mock domain revenue for the chart since we don't have a specific GET /summary endpoint response yet
        const data = [
            { name: 'Retail', revenue: 4000 },
            { name: 'Corporate', revenue: 3000 },
            { name: 'Investment', revenue: 2000 },
            { name: 'SME', revenue: 2780 },
        ];

        document.getElementById('kpi-revenue').textContent = '$11.78M';

        // Render Recharts
        const { BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer } = window.Recharts;
        const renderChart = () => {
            return (
                <ResponsiveContainer width="100%" height="100%">
                    <BarChart data={data}>
                        <CartesianGrid strokeDasharray="3 3" stroke="#2E4A7A" />
                        <XAxis dataKey="name" stroke="#8A9BB5" />
                        <YAxis stroke="#8A9BB5" />
                        <Tooltip contentStyle={{ backgroundColor: '#1C2E4A', border: 'none', borderRadius: '6px' }} />
                        <Bar dataKey="revenue" fill="#1A6EFD" radius={[4, 4, 0, 0]} />
                    </BarChart>
                </ResponsiveContainer>
            );
        };
        const root = ReactDOM.createRoot(document.getElementById('chart-container'));
        root.render(renderChart());

    } catch (err) {
        console.error(err);
        if (window.UI) window.UI.showToast('Failed to load dashboard data', 'error');
    }
});
