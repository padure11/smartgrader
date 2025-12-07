function showEditForm() {
    document.getElementById('name-edit-form').style.display = 'flex';
    document.getElementById('edit-name-btn').style.display = 'none';
    document.getElementById('first-name-input').focus();
}

function cancelEdit() {
    document.getElementById('name-edit-form').style.display = 'none';
    document.getElementById('edit-name-btn').style.display = 'inline-block';
}

function saveNameEdit() {
    const firstName = document.getElementById('first-name-input').value.trim();
    const lastName = document.getElementById('last-name-input').value.trim();

    if (!firstName || !lastName) {
        Toast.error('Validation Error', 'Both first name and last name are required');
        return;
    }

    // Disable inputs during save
    const inputs = document.querySelectorAll('#name-edit-form input, #name-edit-form button');
    inputs.forEach(el => el.disabled = true);

    // Use global variables set by the template
    const url = `/tests/${window.testId}/submissions/${window.submissionId}/update-name/`;

    fetch(url, {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
        },
        body: JSON.stringify({
            first_name: firstName,
            last_name: lastName
        })
    })
    .then(response => response.json())
    .then(data => {
        inputs.forEach(el => el.disabled = false);

        if (data.error) {
            Toast.error('Update Failed', data.error);
        } else {
            // Update the display name
            document.getElementById('student-name-display').textContent = data.full_name;

            // Also update the page title
            const testTitle = window.testTitle || '';
            document.title = data.full_name + ' - ' + testTitle;

            // Hide the form
            cancelEdit();

            Toast.success('Name Updated', 'Student name has been successfully updated');
        }
    })
    .catch(error => {
        inputs.forEach(el => el.disabled = false);
        Toast.error('Update Error', 'An error occurred while updating the name');
        console.error('Error:', error);
    });
}
