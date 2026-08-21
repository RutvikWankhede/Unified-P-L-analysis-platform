import re

with open('frontend_v2/js/datasets_wiring.js', 'r', encoding='utf-8') as f:
    txt = f.read()

pattern = r"(?s)let mappingRowsHtml = '';.*?zone\.innerHTML = `"
replacement = """const allCanonicalFields = [
                            'date', 'amount', 'category', 'line_item',
                            'department', 'currency', 'cost_center'
                        ];

                        let mappingRowsHtml = '';
                        if (data.schema_mapping && data.schema_mapping.mappings) {
                            const allColumns = data.schema_mapping.detected_columns || [];
                            mappingRowsHtml = allCanonicalFields.map(canonical => {
                                const mappingObj = data.schema_mapping.mappings[canonical] || {};
                                const isRequired = requiredFields.includes(canonical);
                                const badge = isRequired ? `<span class="px-2 py-0.5 rounded text-[10px] font-bold bg-red-100 text-red-600">REQUIRED</span>` : `<span class="px-2 py-0.5 rounded text-[10px] font-bold bg-slate-100 text-slate-500">OPTIONAL</span>`;
                                const fallbackTxt = !isRequired && fallbackFormulas[canonical] ? `<div class="text-[10px] text-slate-500 mt-1">${fallbackFormulas[canonical]}</div>` : '';
                                
                                let confidenceBadge = '';
                                let mappedTo = mappingObj.mapped_to || '';
                                
                                if (mappingObj.confidence !== undefined) {
                                    if (mappingObj.confidence < 70) {
                                        mappedTo = ""; // Clear mapping if confidence is low
                                    } else {
                                        confidenceBadge = `<span class="px-2 py-0.5 ml-2 rounded text-[10px] font-bold bg-green-100 text-green-700">${Math.round(mappingObj.confidence)}% Match</span>`;
                                    }
                                }
                                
                                let selectHtml = `<select class="w-full text-sm border-slate-200 rounded-lg mapping-select" data-canonical="${canonical}">`;
                                selectHtml += `<option value="">-- Select Column --</option>`;
                                allColumns.forEach(col => {
                                    const selected = col === mappedTo ? 'selected' : '';
                                    selectHtml += `<option value="${col}" ${selected}>${col}</option>`;
                                });
                                selectHtml += `</select>`;
                                
                                return `
                                    <tr class="border-b border-slate-100 hover:bg-slate-50">
                                        <td class="py-3 px-4">
                                            <div class="flex items-center gap-2">
                                                <span class="font-medium text-slate-800">${canonical.replace('_', ' ').toUpperCase()}</span>
                                                ${badge}
                                                ${confidenceBadge}
                                            </div>
                                            ${fallbackTxt}
                                        </td>
                                        <td class="py-3 px-4">${selectHtml}</td>
                                    </tr>
                                `;
                            }).join('');
                        }

                        zone.innerHTML = `"""

txt = re.sub(pattern, replacement, txt)

with open('frontend_v2/js/datasets_wiring.js', 'w', encoding='utf-8') as f:
    f.write(txt)
print("Done")
