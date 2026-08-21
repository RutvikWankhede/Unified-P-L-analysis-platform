document.addEventListener('DOMContentLoaded', () => {
    fetch('/api/v1/pl/workflows')
        .then(res => res.json())
        .then(data => {
            const tableBody = document.getElementById('workflow-table-body');
            if(tableBody && Array.isArray(data)) {
                tableBody.innerHTML = '';
                data.forEach(workflow => {
                    const row = document.createElement('tr');
                    row.className = 'hover:bg-gray-50/50';
                    row.innerHTML = `
                        <td class="px-6 py-4 flex items-center gap-2"><i class="w-3.5 h-3.5 text-text-secondary" data-lucide="file-text"></i> ${workflow.process_instance_id || workflow.id}</td>
                        <td class="px-6 py-4">${workflow.workflow_name || 'Workflow'}</td>
                        <td class="px-6 py-4 font-mono text-[10px]">${workflow.id}</td>
                        <td class="px-6 py-4">${workflow.status}</td>
                        <td class="px-6 py-4 text-center">
                            <span class="bg-blue-50 text-info-blue px-2 py-0.5 rounded-badge text-[9px] font-bold uppercase">${workflow.status}</span>
                        </td>
                        <td class="px-6 py-4">
                            <div class="flex items-center gap-2">
                                <div class="w-16 h-1.5 bg-gray-100 rounded-full overflow-hidden"><div class="h-full bg-primary-blue w-[100%]"></div></div>
                                <span class="text-[10px]">100%</span>
                            </div>
                        </td>
                        <td class="px-6 py-4 text-[10px]">${new Date(workflow.started_at).toLocaleString()}</td>
                        <td class="px-6 py-4 text-text-secondary">${workflow.completed_at ? new Date(workflow.completed_at).toLocaleString() : '—'}</td>
                        <td class="px-6 py-4">
                            <div class="flex items-center gap-2 text-text-secondary"><i class="w-4 h-4 cursor-pointer hover:text-primary-blue" data-lucide="eye"></i></div>
                        </td>
                    `;
                    tableBody.appendChild(row);
                });
                lucide.createIcons();
            }
        });
});
