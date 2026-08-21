document.addEventListener('DOMContentLoaded', () => {
    // Load preferences
    fetch('/api/v1/auth/me')
        .then(res => res.json())
        .then(data => {
            if (data.preferences) {
                const curSelect = document.getElementById('currency-select');
                const dtSelect = document.getElementById('date-format-select');
                
                if (curSelect && data.preferences.currency) {
                    curSelect.value = data.preferences.currency;
                }
                if (dtSelect && data.preferences.date_format) {
                    dtSelect.value = data.preferences.date_format;
                }
            }
        })
        .catch(e => console.error('Failed to load settings:', e));
});

window.saveSettings = function() {
    const curSelect = document.getElementById('currency-select');
    const dtSelect = document.getElementById('date-format-select');
    
    if(!curSelect || !dtSelect) return;
    
    const prefs = {
        currency: curSelect.value,
        date_format: dtSelect.value
    };
    
    // Animate button
    const btn = event.currentTarget || event.target;
    const oldText = btn.innerText;
    btn.innerText = 'Saving...';
    btn.disabled = true;
    
    fetch('/api/v1/auth/me', {
        method: 'PUT',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ preferences: prefs })
    })
    .then(res => {
        if(res.ok) {
            btn.innerText = 'Saved!';
            setTimeout(() => {
                btn.innerText = oldText;
                btn.disabled = false;
            }, 2000);
        } else {
            throw new Error('Failed to save');
        }
    })
    .catch(e => {
        console.error(e);
        btn.innerText = 'Error';
        setTimeout(() => {
            btn.innerText = oldText;
            btn.disabled = false;
        }, 2000);
    });
};
