document.addEventListener('DOMContentLoaded', () => {
    const loginForm = document.getElementById('login-form');
    const errorBanner = document.getElementById('error-banner');
    const submitBtn = document.getElementById('login-btn');

    if (!loginForm) return;

    loginForm.addEventListener('submit', async (e) => {
        e.preventDefault();
        
        const username = loginForm.username.value;
        const password = loginForm.password.value;
        
        errorBanner.style.display = 'none';
        submitBtn.disabled = true;
        submitBtn.textContent = 'Authenticating...';

        try {
            const res = await window.api.login(username, password);
            localStorage.setItem('token', res.access_token);
            window.location.href = 'dashboard.html';
        } catch (err) {
            errorBanner.textContent = err.message || 'Login failed';
            errorBanner.style.display = 'block';
            submitBtn.disabled = false;
            submitBtn.textContent = 'Login';
        }
    });
});
