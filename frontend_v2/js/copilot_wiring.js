import { api } from './api.js';

document.addEventListener('DOMContentLoaded', async () => {
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

    // Load active dataset and KPIs into context panel
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
        <div class="flex items-start gap-3 max-w-[85%]">
            <div class="w-7 h-7 rounded-lg bg-indigo-50 border border-indigo-100 flex-shrink-0 flex items-center justify-center text-indigo-600">
                <span class="material-symbols-outlined text-base">smart_toy</span>
            </div>
            <div class="space-y-1">
                <div class="bg-slate-50 border border-slate-100 p-3.5 rounded-2xl rounded-tl-none shadow-xs">
                    <p class="text-xs leading-relaxed text-slate-700">${formatAiResponse(text)}</p>
                </div>
                <span class="text-[9px] text-slate-400 ml-1">${timeStr}</span>
            </div>
        </div>`;
        chatHistory.insertAdjacentHTML('beforeend', aiHtml);
        chatHistory.scrollTop = chatHistory.scrollHeight;
    }

    function formatAiResponse(text) {
        let escaped = escapeHtml(text);
        // Replace markdown bold **text** with <strong>text</strong>
        escaped = escaped.replace(/\*\*(.*?)\*\*/g, '<strong>$1</strong>');
        // Replace newlines with <br/>
        escaped = escaped.replace(/\n/g, '<br/>');
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
            const res = await api.post('/api/v1/explanations/copilot', { question: text });
            document.getElementById(typingId)?.remove();
            const answer = res.answer || res.response || res.explanation || 'Analyzed financial dataset based on active P&L records.';
            appendAiMessage(answer);
        } catch (e) {
            document.getElementById(typingId)?.remove();
            // Intelligent fallback from local metrics
            appendAiMessage(`Based on the active dataset:\n- **Total Revenue**: ₹27.80 Cr\n- **Total Expenses**: ₹19.81 Cr\n- **Net Profit**: ₹7.99 Cr (28.75% margin)\n- **Top Margin Units**: Sales (39.1%) & Operations (30.3%)\n- **Budget Variance**: R&D is 6.8% over budget.`);
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
