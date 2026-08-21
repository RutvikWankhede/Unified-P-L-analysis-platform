document.addEventListener('DOMContentLoaded', () => {
    // Wire Recent Uploads Table
    window.loadRecentUploads = function() {
        const tbody = document.getElementById('recent-uploads-table-body');
        if(!tbody) return;
        
        const template = tbody.querySelector('[data-row-template="true"]');
        if(!template) return;
        
        template.style.display = 'none'; // hide the template

        // clear other rows except template
        Array.from(tbody.children).forEach(child => {
            if (!child.hasAttribute('data-row-template')) {
                child.remove();
            }
        });

        // Fetch from backend
        fetch('/api/v1/datasets/recent')
            .then(r => r.json())
            .then(data => {
                data.forEach(upload => {
                    const clone = template.cloneNode(true);
                    clone.removeAttribute('data-row-template');
                    clone.style.display = '';
                    
                    const tds = clone.querySelectorAll('td');
                    if(tds.length >= 6) {
                        // File name
                        tds[0].innerText = upload.filename || 'Unknown';
                        // Rows
                        tds[1].innerText = (upload.rows || upload.records_count || 0).toLocaleString();
                        // Columns
                        tds[2].innerText = (upload.columns || upload.file_size || 0).toLocaleString();
                        // Uploaded By
                        tds[3].innerText = upload.uploaded_by || 'System';
                        // Uploaded On
                        tds[4].innerText = upload.uploaded_on || upload.uploaded_at || new Date().toLocaleString();
                        // Status
                        const statusSpan = tds[5].querySelector('span');
                        if(statusSpan) {
                            statusSpan.innerText = upload.status || 'PROCESSED';
                            if((upload.status || '').toLowerCase() === 'mapped') {
                                statusSpan.className = 'px-3 py-1 text-[10px] font-bold uppercase tracking-wide bg-warning-bg text-warning-text rounded-full';
                            } else if ((upload.status || '').toLowerCase() === 'failed') {
                                statusSpan.className = 'px-3 py-1 text-[10px] font-bold uppercase tracking-wide bg-red-100 text-red-600 rounded-full';
                            } else {
                                statusSpan.className = 'px-3 py-1 text-[10px] font-bold uppercase tracking-wide bg-success-bg text-success-text rounded-full';
                            }
                        }
                    }
                    tbody.appendChild(clone);
                });
            })
            .catch(e => console.error("Error fetching recent datasets", e));
    };
    
    // Initial load
    window.loadRecentUploads();

    // Interactive Drag and Drop Upload Zone
    const uploadCards = document.querySelectorAll('[data-purpose="upload-card"]');
    uploadCards.forEach(card => {
        const zone = card.querySelector('.upload-zone-border');
        if(!zone) return;
        
        // Prevent defaults
        ['dragenter', 'dragover', 'dragleave', 'drop'].forEach(eventName => {
            zone.addEventListener(eventName, preventDefaults, false);
        });

        function preventDefaults(e) {
            e.preventDefault();
            e.stopPropagation();
        }

        // Highlight
        ['dragenter', 'dragover'].forEach(eventName => {
            zone.addEventListener(eventName, highlight, false);
        });
        ['dragleave', 'drop'].forEach(eventName => {
            zone.addEventListener(eventName, unhighlight, false);
        });

        function highlight(e) {
            zone.classList.add('bg-blue-50/50');
            zone.classList.add('border-primary');
        }

        function unhighlight(e) {
            zone.classList.remove('bg-blue-50/50');
            zone.classList.remove('border-primary');
        }

        zone.addEventListener('drop', handleDrop, false);
        function handleDrop(e) {
            let dt = e.dataTransfer;
            let files = dt.files;
            handleFiles(files);
        }

        async function handleFiles(files) {
            if(files.length > 0) {
                const file = files[0];
                const originalHtml = zone.innerHTML;
                try {
                    // Uploading state
                    zone.innerHTML = `
                        <div class="flex flex-col items-center justify-center p-12">
                            <span class="material-symbols-outlined text-4xl text-primary animate-bounce mb-4">cloud_upload</span>
                            <p class="text-lg font-bold text-text-dark mb-2">Uploading ${file.name}...</p>
                            <div class="w-48 h-2 bg-slate-100 rounded-full overflow-hidden">
                                <div class="h-full bg-primary w-1/2 animate-pulse rounded-full"></div>
                            </div>
                        </div>`;
                    
                    const formData = new FormData();
                    formData.append('file', file);
                    
                    const res = await fetch('/api/v1/pl/upload', {
                        method: 'POST',
                        body: formData
                    });
                    
                    if (res.ok) {
                        const data = await res.json();

                        // Show Live Status Panel & Schema Mapping UI
                        
                        let previewRowsHtml = '';
                        if (data.analysis && data.analysis.preview_rows && data.analysis.preview_rows.length > 0) {
                            const headers = Object.keys(data.analysis.preview_rows[0]);
                            previewRowsHtml = `
                                <div class="mb-6">
                                    <h3 class="text-sm font-bold text-slate-800 mb-2">Uploaded File Preview (First 5 rows)</h3>
                                    <p class="text-xs text-slate-500 mb-2">Previewing first 5 lines of spreadsheet.</p>
                                    <div class="overflow-x-auto rounded-xl border border-slate-200">
                                        <table class="w-full text-left text-xs">
                                            <thead class="bg-slate-50 text-slate-600 border-b border-slate-200">
                                                <tr>${headers.map(h => `<th class="px-3 py-2 font-semibold whitespace-nowrap">${h}</th>`).join('')}</tr>
                                            </thead>
                                            <tbody class="divide-y divide-slate-100 bg-white">
                                                ${data.analysis.preview_rows.map(row => `
                                                    <tr class="hover:bg-slate-50">
                                                        ${headers.map(h => `<td class="px-3 py-2 text-slate-700 whitespace-nowrap">${row[h] !== null && row[h] !== undefined ? row[h] : ''}</td>`).join('')}
                                                    </tr>
                                                `).join('')}
                                            </tbody>
                                        </table>
                                    </div>
                                </div>
                            `;
                        }

                        const requiredFields = ['date', 'amount', 'category', 'line_item'];
                        const fallbackFormulas = {
                            'department': 'All Departments [Smart Fallback]',
                            'is_anomaly': 'False [Smart Fallback]',
                            'anomaly_score': '0.0 [Smart Fallback]',
                            'tax': 'Amount × 0.15 [Smart Fallback]',
                            'unit_cost': 'Amount × 0.70 [Smart Fallback]'
                        };

                        let mappingRowsHtml = '';
                        if (data.schema_mapping && data.schema_mapping.mappings) {
                            const allColumns = data.schema_mapping.detected_columns || [];
                            mappingRowsHtml = Object.entries(data.schema_mapping.mappings).map(([canonical, mappingObj]) => {
                                const isRequired = requiredFields.includes(canonical);
                                const badge = isRequired ? `<span class="px-2 py-0.5 rounded text-[10px] font-bold bg-red-100 text-red-600">REQUIRED</span>` : `<span class="px-2 py-0.5 rounded text-[10px] font-bold bg-slate-100 text-slate-500">OPTIONAL</span>`;
                                const fallbackTxt = !isRequired && fallbackFormulas[canonical] ? `<div class="text-[10px] text-slate-500 mt-1">${fallbackFormulas[canonical]}</div>` : '';
                                
                                let selectHtml = `<select class="w-full text-sm border-slate-200 rounded-lg mapping-select" data-canonical="${canonical}">`;
                                selectHtml += `<option value="">-- Select Column --</option>`;
                                allColumns.forEach(col => {
                                    const selected = col === mappingObj.mapped_to ? 'selected' : '';
                                    selectHtml += `<option value="${col}" ${selected}>${col}</option>`;
                                });
                                selectHtml += `</select>`;
                                
                                return `
                                    <tr class="border-b border-slate-100 hover:bg-slate-50">
                                        <td class="py-3 px-4">
                                            <div class="flex items-center gap-2">
                                                <span class="font-medium text-slate-800">${canonical.replace('_', ' ').toUpperCase()}</span>
                                                ${badge}
                                            </div>
                                            ${fallbackTxt}
                                        </td>
                                        <td class="py-3 px-4">${selectHtml}</td>
                                    </tr>
                                `;
                            }).join('');
                        }

                        zone.innerHTML = `
                            <div class="w-full text-left p-6">
                                <!-- Live Ingest Controller Panel -->
                                <div class="bg-blue-50 border border-blue-100 rounded-xl p-4 mb-6 flex items-center justify-between">
                                    <div>
                                        <h3 class="text-sm font-bold text-blue-900">Ingest Controller</h3>
                                        <p class="text-xs text-blue-700">${file.name} (${(file.size / 1024).toFixed(1)} KB)</p>
                                    </div>
                                    <div class="flex items-center gap-2 text-sm font-medium text-blue-800 bg-blue-100 px-3 py-1 rounded-full">
                                        <span class="material-symbols-outlined text-sm animate-pulse">pending</span>
                                        Awaiting mapping confirmation
                                    </div>
                                </div>
                                
                                ${previewRowsHtml}
                                
                                <div>
                                    <h3 class="text-sm font-bold text-slate-800 mb-2">Map Uploaded Columns to System Fields</h3>
                                    <div class="border border-slate-200 rounded-xl overflow-hidden mb-6">
                                        <table class="w-full text-left">
                                            <tbody class="divide-y divide-slate-100">
                                                ${mappingRowsHtml}
                                            </tbody>
                                        </table>
                                    </div>
                                </div>
                                
                                <div class="flex justify-end gap-3">
                                    <button id="btn-reset-upload" class="px-5 py-2 text-sm font-bold text-slate-600 bg-slate-100 hover:bg-slate-200 rounded-xl transition-colors">Reset Upload</button>
                                    <button id="btn-confirm-ingest" class="px-5 py-2 text-sm font-bold text-white bg-primary hover:bg-opacity-90 rounded-xl shadow-md transition-all flex items-center gap-2">
                                        Confirm & Ingest
                                    </button>
                                </div>
                            </div>
                        `;

                        document.getElementById('btn-reset-upload').onclick = () => { zone.innerHTML = originalHtml; bindBrowseBtn(); };
                        
                        document.getElementById('btn-confirm-ingest').onclick = async () => {
                            const btn = document.getElementById('btn-confirm-ingest');
                            btn.disabled = true;
                            btn.innerHTML = `<span class="material-symbols-outlined text-sm animate-spin">autorenew</span> Processing...`;
                            
                            // Update status panel
                            const statusEl = zone.querySelector('.bg-blue-100.px-3');
                            if(statusEl) {
                                statusEl.innerHTML = `<span class="material-symbols-outlined text-sm animate-spin">autorenew</span> Processing...`;
                            }
                            
                            const selects = zone.querySelectorAll('.mapping-select');
                            const updatedMappings = {};
                            selects.forEach(s => {
                                if (s.value) {
                                    updatedMappings[s.dataset.canonical] = s.value;
                                }
                            });
                            
                            try {
                                const finalizeRes = await fetch('/api/v1/pl/finalize-upload', {
                                    method: 'POST',
                                    headers: { 'Content-Type': 'application/json' },
                                    body: JSON.stringify({
                                        upload_id: data.upload_id,
                                        mapping: updatedMappings,
                                        filename: file.name
                                    })
                                });
                                
                                if (finalizeRes.ok) {
                                    const finalizeData = await finalizeRes.json();
                                    
                                    // Set active dataset globally
                                    await fetch('/api/v1/datasets/active', {
                                        method: 'POST',
                                        headers: { 'Content-Type': 'application/json' },
                                        body: JSON.stringify({ dataset_id: finalizeData.upload_id, filename: file.name })
                                    });
                                    
                                    zone.innerHTML = `
                                    <div class="flex flex-col items-center justify-center p-12">
                                        <div class="w-16 h-16 bg-success-bg rounded-full flex items-center justify-center mb-4">
                                            <span class="material-symbols-outlined text-3xl text-success-text">check_circle</span>
                                        </div>
                                        <p class="text-xl font-bold text-text-dark mb-2">Dataset Ready</p>
                                        <p class="text-sm text-text-muted mb-8">${finalizeData.records_ingested || 'Many'} rows processed successfully</p>
                                        <div class="flex gap-4">
                                            <button id="btn-upload-another" class="px-6 py-2 bg-slate-100 text-slate-700 font-bold rounded-xl hover:bg-slate-200 transition-colors">Upload Another</button>
                                            <button id="btn-go-dashboard" class="px-6 py-2 bg-primary text-white font-bold rounded-xl hover:bg-opacity-90 shadow-lg shadow-blue-200 transition-all">Go to Dashboard</button>
                                        </div>
                                    </div>`;
                                    
                                    document.getElementById('btn-upload-another').onclick = () => { zone.innerHTML = originalHtml; bindBrowseBtn(); };
                                    document.getElementById('btn-go-dashboard').onclick = () => { window.location.href = 'dashboard.html'; };
                                    
                                    if (window.loadRecentUploads) window.loadRecentUploads();
                                } else {
                                    throw new Error('Finalization failed');
                                }
                            } catch (err) {
                                console.error(err);
                                alert('Error during ingestion. Please try again.');
                                btn.disabled = false;
                                btn.innerHTML = 'Confirm & Ingest';
                            }
                        };

                    } else {
                        const err = await res.json();
                        // Error state
                        zone.innerHTML = `
                        <div class="flex flex-col items-center justify-center p-12">
                            <div class="w-16 h-16 bg-red-50 rounded-full flex items-center justify-center mb-4">
                                <span class="material-symbols-outlined text-3xl text-red-500">error</span>
                            </div>
                            <p class="text-lg font-bold text-text-dark mb-2">Upload Failed</p>
                            <p class="text-sm text-red-500 mb-6">${err.detail || 'Unknown error occurred'}</p>
                            <button id="btn-upload-retry" class="px-6 py-2 bg-slate-100 text-slate-700 font-bold rounded-xl hover:bg-slate-200 transition-colors">Try Again</button>
                        </div>`;
                        document.getElementById('btn-upload-retry').onclick = () => { zone.innerHTML = originalHtml; bindBrowseBtn(); };
                    }
                } catch (e) {
                    console.error("Upload error", e);
                    zone.innerHTML = `
                        <div class="flex flex-col items-center justify-center p-12 text-center">
                            <span class="material-symbols-outlined text-4xl text-red-500 mb-4">wifi_off</span>
                            <p class="text-lg font-bold text-text-dark mb-2">Connection Error</p>
                            <p class="text-sm text-text-muted mb-6">Could not connect to the server.</p>
                            <button id="btn-upload-retry" class="px-6 py-2 bg-slate-100 text-slate-700 font-bold rounded-xl hover:bg-slate-200 transition-colors">Try Again</button>
                        </div>`;
                    document.getElementById('btn-upload-retry').onclick = () => { zone.innerHTML = originalHtml; bindBrowseBtn(); };
                }
            }
        }
        
        function bindBrowseBtn() {
            const btn = zone.querySelector('button');
            if (btn) {
                btn.onclick = () => {
                    const input = document.createElement('input');
                    input.type = 'file';
                    input.accept = '.csv,.xls,.xlsx';
                    input.onchange = (e) => handleFiles(e.target.files);
                    input.click();
                };
            }
        }
        
        bindBrowseBtn();
    });

    // Tab Switching Logic
    const tabs = document.querySelectorAll('.border-b.border-border-light a');
    const uploadCard = document.querySelector('[data-purpose="upload-card"]');
    const guidelinesCard = document.querySelector('[data-purpose="guidelines-card"]');
    const dataQualityCard = document.getElementById('data-quality-card');

    tabs.forEach(tab => {
        tab.addEventListener('click', (e) => {
            e.preventDefault();
            // Reset active state
            tabs.forEach(t => {
                t.classList.remove('active-tab', 'text-primary', 'font-semibold');
                t.classList.add('text-text-muted');
                t.style.borderBottom = 'none';
            });

            // Set active state on clicked tab
            tab.classList.remove('text-text-muted');
            tab.classList.add('active-tab', 'text-primary', 'font-semibold');
            tab.style.borderBottom = '2px solid #5b5ceb';

            // View switching
            const tabText = tab.innerText.trim();
            if (tabText === 'Data Quality') {
                if(uploadCard) uploadCard.classList.add('hidden');
                if(guidelinesCard) guidelinesCard.classList.add('hidden');
                if(dataQualityCard) dataQualityCard.classList.remove('hidden');
            } else if (tabText === 'Upload Data') {
                if(uploadCard) uploadCard.classList.remove('hidden');
                if(guidelinesCard) guidelinesCard.classList.remove('hidden');
                if(dataQualityCard) dataQualityCard.classList.add('hidden');
            }
        });
    });
});
