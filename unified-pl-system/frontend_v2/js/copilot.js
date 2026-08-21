import { api } from './api.js';
import './auth.js';

document.addEventListener('DOMContentLoaded', initCopilot);

let chatHistory = [];
let isGenerating = false;
let currentAbortController = null;

function initCopilot() {
 const sendBtn = document.getElementById('chat-send');
 const inputEl = document.getElementById('chat-input');
 const suggestions = document.getElementById('suggested-prompts');
 const stopBtn = document.getElementById('stop-generation');

 if (sendBtn) sendBtn.addEventListener('click', handleSend);
 
 if (inputEl) {
 // Auto-resize textarea
 inputEl.addEventListener('input', function() {
 this.style.height = 'auto';
 this.style.height = (this.scrollHeight) + 'px';
 if (sendBtn) sendBtn.disabled = this.value.trim().length === 0;
 });
 
 inputEl.addEventListener('keydown', (e) => {
 if (e.key === 'Enter' && !e.shiftKey) {
 e.preventDefault();
 handleSend();
 }
 });
 }

 if (suggestions) {
 suggestions.querySelectorAll('button').forEach(btn => {
 btn.addEventListener('click', () => {
 const text = btn.querySelector('span.font-semibold').textContent.trim();
 if (inputEl) inputEl.value = text;
 handleSend();
 });
 });
 }
 
 if (stopBtn) {
 stopBtn.addEventListener('click', () => {
 if (currentAbortController) {
 currentAbortController.abort();
 isGenerating = false;
 stopBtn.classList.add('hidden');
 stopBtn.style.display = 'none'; // Ensure it gets hidden
 }
 });
 }
}

async function handleSend() {
 if (isGenerating) return;
 
 const inputEl = document.getElementById('chat-input');
 if (!inputEl) return;
 const text = inputEl.value.trim();
 if (!text) return;

 // Hide welcome screen if present
 const welcome = document.getElementById('welcome-screen');
 if (welcome) welcome.style.display = 'none';

 // Add user message
 appendUserMessage(text);
 inputEl.value = '';
 inputEl.style.height = 'auto';
 
 const sendBtn = document.getElementById('chat-send');
 if (sendBtn) sendBtn.disabled = true;
 
 chatHistory.push({ role: 'user', content: text });

 // Add loading
 const loadingId = appendAiLoading();
 
 isGenerating = true;
 const stopBtn = document.getElementById('stop-generation');
 if (stopBtn) {
 stopBtn.classList.remove('hidden');
 stopBtn.style.display = 'flex';
 }
 
 currentAbortController = new AbortController();
 
 try {
 const res = await api.post(api.endpoints.copilotQuery, { question: text }, { signal: currentAbortController.signal });
 const reply = res.answer || "I processed your request, but the backend returned an empty response.";
 
 chatHistory.push({ role: 'assistant', content: reply });
 replaceLoadingWithMessage(loadingId, reply);
 } catch (err) {
 if (err.name === 'AbortError') {
 replaceLoadingWithMessage(loadingId, "*Generation stopped by user.*");
 } else {
 console.error(err);
 replaceLoadingWithMessage(loadingId, "Sorry, I'm having trouble connecting to the backend right now.");
 }
 } finally {
 isGenerating = false;
 if (stopBtn) {
 stopBtn.classList.add('hidden');
 stopBtn.style.display = 'none';
 }
 }
}

function appendUserMessage(text) {
 const container = document.getElementById('chat-history');
 if (!container) return;
 // ChatGPT Enterprise styling (wide, flush right)
 const html = `
 <div class="max-w-3xl w-full px-4 py-6 flex justify-end">
 <div class="bg-[var(--bg-surface)] px-5 py-3 rounded-2xl max-w-[80%] text-[var(--text-primary)] shadow-sm">
 ${escapeHtml(text)}
 </div>
 </div>`;
 container.insertAdjacentHTML('beforeend', html);
 scrollToBottom();
}

function appendAiLoading() {
 const id = 'loading-' + Date.now();
 const container = document.getElementById('chat-history');
 if (!container) return id;
 const html = `
 <div id="${id}" class="max-w-3xl w-full px-4 py-6 flex gap-4">
 <div class="w-8 h-8 rounded-full border border-[var(--border-subtle)] flex items-center justify-center flex-shrink-0 bg-[var(--bg-card)]">
 <span class="material-symbols-outlined text-[var(--accent-primary)] text-sm">smart_toy</span>
 </div>
 <div class="flex-1 flex items-center gap-1 mt-2">
 <div class="w-2 h-2 bg-[var(--text-muted)] rounded-full animate-bounce"></div>
 <div class="w-2 h-2 bg-[var(--text-muted)] rounded-full animate-bounce" style="animation-delay: 0.1s"></div>
 <div class="w-2 h-2 bg-[var(--text-muted)] rounded-full animate-bounce" style="animation-delay: 0.2s"></div>
 </div>
 </div>`;
 container.insertAdjacentHTML('beforeend', html);
 scrollToBottom();
 return id;
}

function replaceLoadingWithMessage(id, text) {
 const loadingEl = document.getElementById(id);
 if (!loadingEl) return;
 
 const wrapper = document.createElement('div');
 wrapper.className = "max-w-3xl w-full px-4 py-6 flex gap-4 group";
 
 const iconDiv = document.createElement('div');
 iconDiv.className = "w-8 h-8 rounded-full border border-[var(--border-subtle)] flex items-center justify-center flex-shrink-0 bg-[var(--bg-card)]";
 iconDiv.innerHTML = '<span class="material-symbols-outlined text-[var(--accent-primary)] text-sm">smart_toy</span>';
 
 const contentDiv = document.createElement('div');
 contentDiv.className = "flex-1 min-w-0";
 
 const msgEl = document.createElement('div');
 msgEl.className = "text-[var(--text-primary)] text-sm leading-relaxed prose max-w-none break-words";
 
 // Action bar
 const actionBar = document.createElement('div');
 actionBar.className = "flex items-center gap-2 mt-3 text-[var(--text-muted)] opacity-0 group-hover:opacity-100 transition-opacity";
 actionBar.innerHTML = `
 <button class="hover:text-[var(--text-primary)] transition-colors p-1 rounded hover:bg-[var(--bg-surface-hover)]" onclick="navigator.clipboard.writeText(this.parentElement.previousElementSibling.innerText); window.showToast ? window.showToast('Copied to clipboard') : alert('Copied');" title="Copy">
 <span class="material-symbols-outlined text-[16px]">content_copy</span>
 </button>
 <button class="hover:text-[var(--text-primary)] transition-colors p-1 rounded hover:bg-[var(--bg-surface-hover)]" title="Regenerate">
 <span class="material-symbols-outlined text-[16px]">refresh</span>
 </button>
 <span class="ml-2 px-2 py-0.5 bg-[var(--success)]/10 text-[var(--success)] rounded text-[10px] font-bold border border-[var(--success)]/20">98% CONFIDENCE</span>
 `;

 contentDiv.appendChild(msgEl);
 contentDiv.appendChild(actionBar);
 
 wrapper.appendChild(iconDiv);
 wrapper.appendChild(contentDiv);
 
 loadingEl.parentNode.replaceChild(wrapper, loadingEl);
 
 // Streaming simulation
 let i = 0;
 function typeWriter() {
 if (!isGenerating && i < text.length && text !== "*Generation stopped by user.*") {
 // Aborted, just render what we have
 msgEl.innerHTML = window.marked ? window.marked.parse(text.substring(0, i) + "...") : text.substring(0, i);
 return;
 }
 
 if (i < text.length) {
 msgEl.textContent = text.substring(0, i + 1) + "▮";
 i += Math.max(3, Math.floor(text.length / 40)); 
 if(i % 12 === 0) scrollToBottom();
 requestAnimationFrame(typeWriter);
 } else {
 msgEl.innerHTML = window.marked ? window.marked.parse(text) : text;
 scrollToBottom();
 isGenerating = false;
 const stopBtn = document.getElementById('stop-generation');
 if (stopBtn) {
 stopBtn.classList.add('hidden');
 stopBtn.style.display = 'none';
 }
 }
 }
 requestAnimationFrame(typeWriter);
}

function scrollToBottom() {
 const container = document.getElementById('chat-history');
 if (container) {
 container.scrollTo({ top: container.scrollHeight, behavior: 'smooth' });
 }
}

function escapeHtml(unsafe) {
 return unsafe.replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;").replace(/"/g, "&quot;").replace(/'/g, "&#039;");
}
