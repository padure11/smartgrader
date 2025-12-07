document.getElementById('enroll-form').addEventListener('submit', async function(e) {
    e.preventDefault();

    const codeInput = document.getElementById('enrollment-code');
    const code = codeInput.value.trim().toUpperCase();

    if (!code) {
        Toast.error('Error', 'Please enter an enrollment code');
        return;
    }

    try {
        const response = await fetch('/student/enroll/', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({ enrollment_code: code })
        });

        const data = await response.json();

        if (response.ok) {
            Toast.success('Success', data.message);
            codeInput.value = '';
            // Reload page after 1 second to show the new enrollment
            setTimeout(() => {
                window.location.reload();
            }, 1000);
        } else {
            Toast.error('Error', data.error || 'Failed to enroll');
        }
    } catch (error) {
        Toast.error('Error', 'Network error. Please try again.');
        console.error('Enrollment error:', error);
    }
});
