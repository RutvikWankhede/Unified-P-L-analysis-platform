import { api } from './api.js';

document.addEventListener('DOMContentLoaded', async () => {
    const sessionId = 'session_' + Math.random().toString(36).substring(2, 9);

    const formatCurrency = (val) => {
        if (val === null || val === undefined || isNaN(val)) return '₹0 Cr';
        const abs = Math.abs(val);
        const sign = val < 0 ? '-' : '';
        if (abs >= 1000000000) return `${sign}₹${(abs / 1000000000).toFixed(2)} B`;
        if (abs >= 10000000) return `${sign}₹${(abs / 10000000).toFixed(2)} Cr`;
        if (abs >= 100000) return `${sign}₹${(abs / 100000).toFixed(2)} L`;
        if (abs >= 1000) return `${sign}₹${(abs / 1000).toFixed(1)} K`;
        return `${sign}₹${abs.toLocaleString('en-IN')}`;
    };

    const chatHistory = document.getElementById('chat-history');
    const input = document.getElementById('copilot-input');
    const sendBtn = document.getElementById('copilot-send-btn');

    // Load active dataset and live KPIs into context panel
    async function loadCopilotContext() {
        try {
            const active = await api.get('/api/v1/datasets/active').catch(() => null);
            if (active && active.filename) {
                const pill = document.getElementById('active-dataset-name');
                if (pill) pill.textContent = active.filename.replace('.csv', '').replace('.xlsx', '');
            }

            const summary = await api.get('/api/v1/pl/summary?dept=all').catch(() => null);
            if (summary && summary.kpis) {
                const k = summary.kpis;
                const rEl = document.getElementById('ctx-revenue');
                const eEl = document.getElementById('ctx-expense');
                const pEl = document.getElementById('ctx-profit');
                const mEl = document.getElementById('ctx-margin');

                if (rEl && k.revenue !== undefined) rEl.textContent = formatCurrency(k.revenue);
                if (eEl && k.expense !== undefined) eEl.textContent = formatCurrency(k.expense);
                if (pEl && k.profit !== undefined) pEl.textContent = formatCurrency(k.profit);
                const calcMargin = (k.revenue && k.revenue > 0) ? ((k.profit / k.revenue) * 100) : (k.profit_margin || 0.0);
                if (mEl) mEl.textContent = `${calcMargin.toFixed(2)}%`;
            }
        } catch (e) {
            console.warn('Copilot context error:', e);
        }
    }

    function appendUserMessage(text) {
        if (!chatHistory) return;
        const timeStr = new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });
        const userHtml = `
        <div class="flex flex-col items-end gap-1">
            <div class="bg-primary text-white p-3.5 rounded-2xl rounded-tr-none shadow-xs max-w-[75%]">
                <p class="text-xs leading-relaxed font-normal">${escapeHtml(text)}</p>
            </div>
            <span class="text-[9px] text-slate-400 mr-1">${timeStr}</span>
        </div>`;
        chatHistory.insertAdjacentHTML('beforeend', userHtml);
        chatHistory.scrollTop = chatHistory.scrollHeight;
    }

    function appendAiMessage(text) {
        if (!chatHistory) return;
        const timeStr = new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });
        const aiHtml = `
        <div class="flex items-start gap-3 max-w-[90%]">
            <div class="w-7 h-7 rounded-lg bg-indigo-50 border border-indigo-100 flex-shrink-0 flex items-center justify-center text-indigo-600">
                <span class="material-symbols-outlined text-base">smart_toy</span>
            </div>
            <div class="space-y-1 w-full">
                <div class="bg-slate-50 border border-slate-100 p-3.5 rounded-2xl rounded-tl-none shadow-xs">
                    <div class="text-xs leading-relaxed text-slate-700">${formatAiResponse(text)}</div>
                </div>
                <span class="text-[9px] text-slate-400 ml-1">${timeStr}</span>
            </div>
        </div>`;
        chatHistory.insertAdjacentHTML('beforeend', aiHtml);
        chatHistory.scrollTop = chatHistory.scrollHeight;
    }

    function formatAiResponse(text) {
        if (!text) return '';

        // Check if text has markdown tables
        if (text.includes('|') && text.includes('\n')) {
            const lines = text.split('\n');
            let inTable = false;
            let tableHtml = '';
            let outLines = [];

            for (let i = 0; i < lines.length; i++) {
                const line = lines[i].trim();
                if (line.startsWith('|') && line.endsWith('|')) {
                    if (!inTable) {
                        inTable = true;
                        tableHtml = '<div class="overflow-x-auto my-2"><table class="w-full text-[11px] border-collapse border border-slate-200 rounded-lg"><tbody>';
                    }
                    if (line.includes('---')) {
                        continue; // skip separator row
                    }
                    const cells = line.split('|').map(c => c.trim()).filter((c, idx, arr) => idx > 0 && idx < arr.length - 1);
                    const isHeader = (i === 0 || (i > 0 && lines[i-1].includes('---')));
                    const rowClass = isHeader ? 'bg-indigo-50/60 font-bold text-slate-800' : 'hover:bg-slate-100/50';
                    tableHtml += `<tr class="${rowClass}">` + cells.map(c => `<td class="border border-slate-200 px-2 py-1">${c.replace(/\*\*(.*?)\*\*/g, '<strong>$1</strong>')}</td>`).join('') + '</tr>';
                } else {
                    if (inTable) {
                        inTable = false;
                        tableHtml += '</tbody></table></div>';
                        outLines.push(tableHtml);
                    }
                    outLines.push(line);
                }
            }
            if (inTable) {
                tableHtml += '</tbody></table></div>';
                outLines.push(tableHtml);
            }
            text = outLines.join('\n');
        }

        let escaped = text;
        // Replace markdown bold **text** with <strong>text</strong>
        escaped = escaped.replace(/\*\*(.*?)\*\*/g, '<strong>$1</strong>');
        // Replace bullet points
        escaped = escaped.replace(/^[•\-\*]\s*(.*?)$/gm, '<div class="flex items-start gap-1.5 my-1"><span class="text-primary font-bold">•</span><span>$1</span></div>');
        // Replace numbered list 1. 2.
        escaped = escaped.replace(/^(\d+)\.\s*(.*?)$/gm, '<div class="flex items-start gap-1.5 my-1"><span class="font-bold text-slate-700">$1.</span><span>$2</span></div>');
        // Replace newlines with <br/> except around tables
        escaped = escaped.replace(/\n\n/g, '<br/><br/>').replace(/\n/g, '<br/>');
        return escaped;
    }

    function escapeHtml(str) {
        return str.replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;");
    }

    async function sendPrompt(promptText) {
        if (!promptText || !promptText.trim()) return;
        const text = promptText.trim();
        if (input) input.value = '';

        appendUserMessage(text);

        // Show typing placeholder
        const typingId = 'typing-' + Date.now();
        const typingHtml = `
        <div id="${typingId}" class="flex items-start gap-3 max-w-[85%]">
            <div class="w-7 h-7 rounded-lg bg-indigo-50 border border-indigo-100 flex-shrink-0 flex items-center justify-center text-indigo-600 animate-pulse">
                <span class="material-symbols-outlined text-base">smart_toy</span>
            </div>
            <div class="bg-slate-50 border border-slate-100 p-3 rounded-2xl rounded-tl-none shadow-xs">
                <p class="text-xs text-slate-400 italic flex items-center gap-1.5">
                    <span class="w-1.5 h-1.5 rounded-full bg-indigo-500 animate-ping"></span>
                    Analyzing active P&amp;L dataset...
                </p>
            </div>
        </div>`;
        chatHistory.insertAdjacentHTML('beforeend', typingHtml);
        chatHistory.scrollTop = chatHistory.scrollHeight;

        try {
            const res = await api.post('/api/v1/copilot/chat', { 
                prompt: text, 
                question: text, 
                session_id: sessionId 
            });
            document.getElementById(typingId)?.remove();
            const answer = res.answer || res.response || res.explanation || 'Analyzed financial dataset based on active P&L records.';
            appendAiMessage(answer);
        } catch (e) {
            document.getElementById(typingId)?.remove();
            appendAiMessage("I couldn't process that question right now. Please ensure the backend server is running and a dataset is active.");
        }
    }

    if (input) {
        input.addEventListener('keydown', (e) => {
            if (e.key === 'Enter') {
                e.preventDefault();
                sendPrompt(input.value);
            }
        });
    }

    if (sendBtn) {
        sendBtn.addEventListener('click', (e) => {
            e.preventDefault();
            if (input) sendPrompt(input.value);
        });
    }

    // Suggested prompt chips
    document.querySelectorAll('.prompt-chip').forEach(btn => {
        btn.addEventListener('click', () => {
            const text = btn.textContent.trim();
            sendPrompt(text);
        });
    });

    await loadCopilotContext();
});
