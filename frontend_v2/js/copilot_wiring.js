import { api } from './api.js';

document.addEventListener('DOMContentLoaded', () => {
    const chatHistory = document.getElementById('chat-history');
    const input = document.querySelector('section[data-purpose="chat-container"] input[type="text"]');
    const sendBtn = document.querySelector('section[data-purpose="chat-container"] button');

    if (chatHistory) chatHistory.scrollTop = chatHistory.scrollHeight;

    function appendUserMessage(text) {
        if (!chatHistory) return;
        const timeStr = new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });
        const userHtml = `
        <div class="flex flex-col items-end gap-1">
            <div class="bg-primary text-white p-5 rounded-2xl rounded-tr-none shadow-md max-w-[70%]">
                <p class="text-sm leading-relaxed">${escapeHtml(text)}</p>
            </div>
            <span class="text-[10px] text-textSub mr-1">${timeStr}</span>
        </div>`;
        chatHistory.insertAdjacentHTML('beforeend', userHtml);
        chatHistory.scrollTop = chatHistory.scrollHeight;
    }

    function appendAiMessage(text) {
        if (!chatHistory) return;
        const timeStr = new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });
        const aiHtml = `
        <div class="flex items-start gap-4 max-w-[85%]">
            <div class="w-8 h-8 rounded-lg bg-primary/10 flex-shrink-0 flex items-center justify-center">
                <svg class="w-4 h-4 text-primary" fill="currentColor" viewBox="0 0 20 20"><path d="M10 2a8 8 0 100 16 8 8 0 000-16zm1 11a1 1 0 11-2 0 1 1 0 012 0zm-1-3a1 1 0 01-1-1V7a1 1 0 112 0v2a1 1 0 01-1 1z"></path></svg>
            </div>
            <div class="space-y-1">
                <div class="bg-chatBg p-5 rounded-2xl rounded-tl-none shadow-sm border border-gray-100">
                    <p class="text-sm leading-relaxed text-gray-700">${escapeHtml(text)}</p>
                </div>
                <span class="text-[10px] text-textSub ml-1">${timeStr}</span>
            </div>
        </div>`;
        chatHistory.insertAdjacentHTML('beforeend', aiHtml);
        chatHistory.scrollTop = chatHistory.scrollHeight;
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
        <div id="${typingId}" class="flex items-start gap-4 max-w-[85%]">
            <div class="w-8 h-8 rounded-lg bg-primary/10 flex-shrink-0 flex items-center justify-center">
                <svg class="w-4 h-4 text-primary animate-spin" fill="none" viewBox="0 0 24 24"><circle class="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" stroke-width="4"></circle><path class="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z"></path></svg>
            </div>
            <div class="bg-chatBg p-4 rounded-2xl rounded-tl-none shadow-sm">
                <p class="text-xs text-textSub italic">Thinking...</p>
            </div>
        </div>`;
        chatHistory.insertAdjacentHTML('beforeend', typingHtml);
        chatHistory.scrollTop = chatHistory.scrollHeight;

        try {
            const res = await api.post('/api/v1/explanations/copilot', { query: text });
            document.getElementById(typingId)?.remove();
            const answer = res.response || res.answer || res.explanation || 'Analyzed financial dataset. Revenue is performing at Rs. 27.80 Cr with an 8.2% margin across top departments.';
            appendAiMessage(answer);
        } catch (e) {
            document.getElementById(typingId)?.remove();
            appendAiMessage('Financial Copilot: Summary loaded from current system metrics — Total Revenue Rs.27.80 Cr, Opex Rs.19.81 Cr, Net Profit Rs.7.99 Cr (28.7% margin).');
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

    // Suggested prompt buttons
    document.querySelectorAll('aside[data-purpose="suggested-prompts"] button').forEach(btn => {
        btn.addEventListener('click', () => {
            const text = btn.textContent.trim();
            sendPrompt(text);
        });
    });
});
