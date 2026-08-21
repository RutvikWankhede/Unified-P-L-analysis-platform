import './auth.js';

document.addEventListener('DOMContentLoaded', () => {
 // Load preferences
 const currency = localStorage.getItem('base_currency') || 'INR';
 const dateFormat = localStorage.getItem('date_format') || 'MM/DD/YYYY';

 const currencySelect = document.getElementById('currency-select');
 const dateFormatSelect = document.getElementById('date-format-select');

 if (currencySelect) currencySelect.value = currency;
 if (dateFormatSelect) dateFormatSelect.value = dateFormat;

 // Attach saveSettings globally so inline onclick works
 window.saveSettings = () => {
 if (currencySelect) localStorage.setItem('base_currency', currencySelect.value);
 if (dateFormatSelect) localStorage.setItem('date_format', dateFormatSelect.value);
 
 // Show brief success toast/alert
 const originalText = event.target.textContent;
 event.target.textContent = "Saved!";
 event.target.classList.add("bg-green-500");
 event.target.classList.remove("bg-primary");
 
 setTimeout(() => {
 event.target.textContent = originalText;
 event.target.classList.remove("bg-green-500");
 event.target.classList.add("bg-primary");
 }, 1500);
 };

 window.switchTab = (tabId, btn) => {
 // Hide all tabs
 document.querySelectorAll('[id^="tab-"]').forEach(el => {
 el.classList.add('hidden');
 });
 
 // Show selected tab
 const tab = document.getElementById('tab-' + tabId);
 if (tab) tab.classList.remove('hidden');
 
 // Update nav buttons
 const parent = btn.parentElement;
 parent.querySelectorAll('button').forEach(b => {
 b.className = "w-full text-left px-4 py-3 rounded-lg text-sm font-semibold text-slate-600 hover:bg-slate-50";
 });
 
 // Active button styles
 btn.className = "w-full text-left px-4 py-3 rounded-lg text-sm font-semibold bg-primary/10 text-primary";
 };
});
