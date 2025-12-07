document.getElementById('login-form').addEventListener('submit', async function(e) {
    e.preventDefault();

    const submitBtn = document.getElementById('submit-btn');
    const errorDiv = document.getElementById('error-message');
    const successDiv = document.getElementById('success-message');

    errorDiv.style.display = 'none';
    successDiv.style.display = 'none';

    const email = document.getElementById('email').value;
    const password = document.getElementById('password').value;

    submitBtn.disabled = true;
    submitBtn.textContent = 'Logging in...';

    try {
        const response = await fetch('/accounts/api-login/', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({ email, password })
        });

        const data = await response.json();

        if (response.ok) {
            successDiv.textContent = 'Login successful! Redirecting...';
            successDiv.style.display = 'block';
            setTimeout(() => {
                // Redirect based on role
                if (data.role === 'teacher') {
                    window.location.href = '/tests/';
                } else {
                    window.location.href = '/student/';
                }
            }, 1000);
        } else {
            errorDiv.textContent = data.error || 'Login failed';
            errorDiv.style.display = 'block';
            submitBtn.disabled = false;
            submitBtn.textContent = 'Login';
        }
    } catch (error) {
        errorDiv.textContent = 'An error occurred. Please try again.';
        errorDiv.style.display = 'block';
        submitBtn.disabled = false;
        submitBtn.textContent = 'Login';
    }
});
