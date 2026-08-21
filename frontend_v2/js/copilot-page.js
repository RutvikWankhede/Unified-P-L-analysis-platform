import { api } from './api.js';

document.addEventListener('DOMContentLoaded', () => {
 const input = document.querySelector('input[type="text"]');
 const btn = document.querySelector('button.btn--ghost');
 
 input.addEventListener('keypress', (e) => {
 if (e.key === 'Enter') sendMessage();
 });
 
 btn.addEventListener('click', sendMessage);
});

async function sendMessage() {
 const input = document.querySelector('input[type="text"]');
 const text = input.value.trim();
 if (!text) return;
 
 input.value = '';
 addMessage(text, 'user');
 
 // Loading state
 const typingId = addTypingIndicator();
 
 try {
 const res = await api.post(api.endpoints.copilotQuery, { question: text });
 document.getElementById(typingId).remove();
 addMessage(res.answer || res.message || 'I am sorry, I could not process that request.', 'assistant');
 } catch(err) {
 document.getElementById(typingId).remove();
 addMessage('Sorry, there was an error processing your request.', 'assistant', true);
 }
}

function addMessage(text, sender, isError=false) {
 const container = document.getElementById('chat-messages');
 
 const msg = document.createElement('div');
 msg.style.display = 'flex';
 msg.style.gap = 'var(--space-3)';
 msg.style.marginBottom = 'var(--space-4)';
 
 if (sender === 'user') {
 msg.style.flexDirection = 'row-reverse';
 msg.innerHTML = `
 <div style="width: 32px; height: 32px; border-radius: var(--radius-sm); background: var(--border-strong); display: flex; align-items: center; justify-content: center; color: var(--text-primary);">
 <span class="material-symbols-outlined" style="font-size: 16px;">person</span>
 </div>
 <div style="background: var(--accent-primary); color: var(--bg-canvas); padding: var(--space-3) var(--space-4); border-radius: var(--radius-md); max-width: 80%;">
 <p class="text-body-sm">${escapeHTML(text)}</p>
 </div>
 `;
 } else {
 msg.innerHTML = `
 <div style="width: 32px; height: 32px; border-radius: var(--radius-sm); background: var(--accent-primary-muted); display: flex; align-items: center; justify-content: center; color: var(--accent-primary);">
 <span class="material-symbols-outlined" style="font-size: 16px;">robot_2</span>
 </div>
 <div style="background: var(--bg-surface); color: ${isError ? 'var(--danger)' : 'var(--text-primary)'}; padding: var(--space-3) var(--space-4); border-radius: var(--radius-md); max-width: 80%; border: ${isError ? '1px solid var(--danger)' : '1px solid var(--border-subtle)'};">
 <p class="text-body-sm" style="line-height: 1.5; margin: 0;">${formatMarkdown(escapeHTML(text))}</p>
 </div>
 `;
 }
 
 container.appendChild(msg);
 container.scrollTop = container.scrollHeight;
}

function addTypingIndicator() {
 const container = document.getElementById('chat-messages');
 const id = 'typing-' + Date.now();
 
 const msg = document.createElement('div');
 msg.id = id;
 msg.style.display = 'flex';
 msg.style.gap = 'var(--space-3)';
 msg.style.marginBottom = 'var(--space-4)';
 
 msg.innerHTML = `
 <div style="width: 32px; height: 32px; border-radius: var(--radius-sm); background: var(--accent-primary-muted); display: flex; align-items: center; justify-content: center; color: var(--accent-primary);">
 <span class="material-symbols-outlined" style="font-size: 16px;">robot_2</span>
 </div>
 <div style="background: var(--bg-surface); padding: var(--space-3) var(--space-4); border-radius: var(--radius-md); max-width: 80%; display: flex; align-items: center; gap: 4px; border: 1px solid var(--border-subtle);">
 <div style="width: 6px; height: 6px; border-radius: 50%; background: var(--text-muted); animation: pulse 1s infinite;"></div>
 <div style="width: 6px; height: 6px; border-radius: 50%; background: var(--text-muted); animation: pulse 1s infinite 0.2s;"></div>
 <div style="width: 6px; height: 6px; border-radius: 50%; background: var(--text-muted); animation: pulse 1s infinite 0.4s;"></div>
 </div>
 `;
 
 container.appendChild(msg);
 container.scrollTop = container.scrollHeight;
 return id;
}

function escapeHTML(str) {
 return (str || '').replace(/[&<>'"]/g, 
 tag => ({
 '&': '&amp;',
 '<': '&lt;',
 '>': '&gt;',
 "'": '&#39;',
 '"': '&quot;'
 }[tag])
 );
}

function formatMarkdown(text) {
 text = text.replace(/\\*\\*(.*?)\\*\\*/g, '<strong>$1</strong>');
 text = text.replace(/\\n/g, '<br/>');
 return text;
}
