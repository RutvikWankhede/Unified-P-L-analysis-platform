document.addEventListener('DOMContentLoaded', () => {
    fetch('/api/v1/auth/audit-logs')
        .then(res => res.json())
        .then(data => {
            const tableBody = document.getElementById('audit-table-body');
            if(tableBody && Array.isArray(data)) {
                tableBody.innerHTML = '';
                data.forEach(log => {
                    const row = document.createElement('tr');
                    row.className = 'border-b border-gray-50 hover:bg-gray-50/50 transition-colors text-xs font-medium';
                    
                    let icon = 'activity';
                    let iconColor = 'bg-blue-100/50 text-blue-600';
                    
                    if(log.action_type === 'LOGIN') {
                        icon = 'log-in';
                        iconColor = 'bg-emerald-100/50 text-emerald-600';
                    } else if(log.action_type === 'CREATE' || log.action_type === 'UPLOAD') {
                        icon = 'upload-cloud';
                        iconColor = 'bg-purple-100/50 text-purple-600';
                    } else if(log.action_type === 'DELETE') {
                        icon = 'trash-2';
                        iconColor = 'bg-red-100/50 text-red-600';
                    } else if(log.action_type === 'UPDATE') {
                        icon = 'edit-3';
                        iconColor = 'bg-orange-100/50 text-orange-600';
                    }
                    
                    row.innerHTML = `
                        <td class="px-8 py-4 whitespace-nowrap">
                            <div class="flex items-center gap-4">
                                <div class="p-1.5 ${iconColor} rounded-lg">
                                    <i class="w-3.5 h-3.5" data-lucide="${icon}"></i>
                                </div>
                                ${new Date(log.timestamp).toLocaleString()}
                            </div>
                        </td>
                        <td class="px-6 py-4 font-bold">System User</td>
                        <td class="px-6 py-4">${log.action_type}</td>
                        <td class="px-6 py-4">${log.resource_type}</td>
                        <td class="px-6 py-4 text-text-muted">${log.description || 'System activity recorded'}</td>
                        <td class="px-8 py-4 font-mono text-gray-500">${log.ip_address || 'Local'}</td>
                    `;
                    tableBody.appendChild(row);
                });
                lucide.createIcons();
            }
        })
        .catch(e => console.error("Error fetching audit data:", e));
});
