function generatePDF() {
    const btn = event.target;
    const originalText = btn.innerHTML;
    btn.disabled = true;
    btn.innerHTML = 'Generating PDF...';

    fetch(`/tests/${window.testId}/generate-pdf/`, {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
        }
    })
    .then(response => response.json())
    .then(data => {
        btn.disabled = false;
        btn.innerHTML = originalText;

        if (data.error) {
            Toast.error('PDF Generation Failed', data.error);
        } else {
            Toast.success('PDF Generated', data.message);
            // Open PDF in new tab
            if (data.pdf_url) {
                window.open(data.pdf_url, '_blank');
            }
        }
    })
    .catch(error => {
        btn.disabled = false;
        btn.innerHTML = originalText;
        Toast.error('PDF Generation Error', 'An error occurred while generating PDF');
        console.error('Error:', error);
    });
}

function confirmDelete() {
    if (confirm('Are you sure you want to delete this test? This action cannot be undone.')) {
        deleteTest();
    }
}

function deleteTest() {
    const btn = event.target;
    btn.disabled = true;
    btn.innerHTML = 'Deleting...';

    fetch(`/tests/${window.testId}/delete/`, {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
        }
    })
    .then(response => response.json())
    .then(data => {
        if (data.error) {
            btn.disabled = false;
            btn.innerHTML = 'Delete Test';
            Toast.error('Delete Failed', data.error);
        } else {
            Toast.success('Test Deleted', data.message);
            setTimeout(() => {
                window.location.href = '/tests/';
            }, 1500);
        }
    })
    .catch(error => {
        btn.disabled = false;
        btn.innerHTML = 'Delete Test';
        Toast.error('Delete Error', 'An error occurred while deleting the test');
        console.error('Error:', error);
    });
}

function duplicateTest() {
    const btn = event.target;
    const originalText = btn.innerHTML;
    btn.disabled = true;
    btn.innerHTML = 'Duplicating...';

    fetch(`/tests/${window.testId}/duplicate/`, {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
        }
    })
    .then(response => response.json())
    .then(data => {
        btn.disabled = false;
        btn.innerHTML = originalText;

        if (data.error) {
            Toast.error('Duplication Failed', data.error);
        } else {
            Toast.success('Test Duplicated', data.message);
            // Redirect to the new test after a short delay
            setTimeout(() => {
                window.location.href = '/tests/' + data.test_id + '/';
            }, 1500);
        }
    })
    .catch(error => {
        btn.disabled = false;
        btn.innerHTML = originalText;
        Toast.error('Duplication Error', 'An error occurred while duplicating the test');
        console.error('Error:', error);
    });
}

// File upload handlers
document.addEventListener('DOMContentLoaded', function() {
    const imageUploads = document.getElementById('image-uploads');
    const zipUpload = document.getElementById('zip-upload');

    if (imageUploads) {
        imageUploads.addEventListener('change', function(e) {
            const files = Array.from(e.target.files);
            if (files.length > 0) {
                uploadFiles(files, false);
            }
        });
    }

    if (zipUpload) {
        zipUpload.addEventListener('change', function(e) {
            const file = e.target.files[0];
            if (file) {
                uploadFiles([file], true);
            }
        });
    }

    // Add event listeners for search and sort
    const searchInput = document.getElementById('search-submissions');
    const sortSelect = document.getElementById('sort-submissions');

    if (searchInput) {
        searchInput.addEventListener('input', filterAndSortSubmissions);
    }

    if (sortSelect) {
        sortSelect.addEventListener('change', filterAndSortSubmissions);
    }
});

function uploadFiles(files, isZip) {
    const statusDiv = document.getElementById('upload-status');
    statusDiv.innerHTML = 'Processing submissions...';
    statusDiv.style.color = '#fff';

    const formData = new FormData();

    if (isZip) {
        formData.append('zip_file', files[0]);
    } else {
        files.forEach(file => {
            formData.append('files', file);
        });
    }

    fetch(`/tests/${window.testId}/upload-submissions/`, {
        method: 'POST',
        body: formData
    })
    .then(response => response.json())
    .then(data => {
        if (data.error) {
            statusDiv.innerHTML = '';
            Toast.error('Upload Failed', data.error);
        } else {
            statusDiv.innerHTML = '';

            // Show results
            if (data.results && data.results.length > 0) {
                let successCount = data.results.filter(r => r.success).length;
                let failedResults = data.results.filter(r => !r.success);

                // Show success toast
                Toast.success('Upload Complete', `Successfully processed ${successCount}/${data.results.length} submissions`);

                // Show error details for failed submissions
                if (failedResults.length > 0) {
                    failedResults.forEach(result => {
                        Toast.error('Processing Failed', `${result.filename}: ${result.error}`, 7000);
                    });
                }
            } else {
                Toast.success('Upload Complete', data.message);
            }

            // Reload submissions
            loadSubmissions();

            // Reset file inputs
            document.getElementById('image-uploads').value = '';
            document.getElementById('zip-upload').value = '';
        }
    })
    .catch(error => {
        statusDiv.innerHTML = '';
        Toast.error('Upload Error', 'An error occurred while uploading submissions');
        console.error('Error:', error);
    });
}

// Global submissions data
let allSubmissions = [];

function loadSubmissions() {
    const submissionsDiv = document.getElementById('submissions-list');

    fetch(`/tests/${window.testId}/submissions/`)
    .then(response => response.json())
    .then(data => {
        if (data.submissions && data.submissions.length > 0) {
            allSubmissions = data.submissions;
            displaySubmissions(allSubmissions);
        } else {
            submissionsDiv.innerHTML = '<p style="color: #aaa;">No submissions yet. Upload student answer sheets to grade them automatically.</p>';
        }
    })
    .catch(error => {
        submissionsDiv.innerHTML = '<p style="color: #ff4444;">Error loading submissions</p>';
        console.error('Error:', error);
    });
}

function displaySubmissions(submissions) {
    const submissionsDiv = document.getElementById('submissions-list');

    if (submissions.length === 0) {
        submissionsDiv.innerHTML = '<p style="color: #aaa;">No submissions match your search.</p>';
        return;
    }

    let html = '';
    submissions.forEach(sub => {
        let scoreClass = 'poor';
        if (sub.percentage >= 80) scoreClass = 'excellent';
        else if (sub.percentage >= 60) scoreClass = 'good';

        html += `
            <a href="/tests/${window.testId}/submissions/${sub.id}/" class="submission-card" data-name="${sub.student_name}">
                <div class="submission-info">
                    <div class="submission-name">${sub.student_name}</div>
                    <div class="submission-meta">
                        Submitted: ${sub.submitted_at}
                    </div>
                </div>
                <div class="submission-score ${scoreClass}">
                    ${sub.score}/${sub.total}<br>
                    <span style="font-size: 12px;">${sub.percentage}%</span>
                </div>
            </a>
        `;
    });
    submissionsDiv.innerHTML = html;
}

function filterAndSortSubmissions() {
    const searchTerm = document.getElementById('search-submissions').value.toLowerCase();
    const sortOption = document.getElementById('sort-submissions').value;

    // Filter
    let filtered = allSubmissions.filter(sub =>
        sub.student_name.toLowerCase().includes(searchTerm)
    );

    // Sort
    filtered.sort((a, b) => {
        switch(sortOption) {
            case 'percentage-desc':
                return b.percentage - a.percentage;
            case 'percentage-asc':
                return a.percentage - b.percentage;
            case 'name-asc':
                return a.student_name.localeCompare(b.student_name);
            case 'name-desc':
                return b.student_name.localeCompare(a.student_name);
            case 'date-desc':
                return new Date(b.submitted_at) - new Date(a.submitted_at);
            case 'date-asc':
                return new Date(a.submitted_at) - new Date(b.submitted_at);
            default:
                return 0;
        }
    });

    displaySubmissions(filtered);
}

// Load submissions on page load
loadSubmissions();

function showAnalytics() {
    const section = document.getElementById('analytics-section');
    const content = document.getElementById('analytics-content');

    if (section.style.display === 'none') {
        section.style.display = 'block';
        content.innerHTML = '<p style="color: #ccc;">Loading analytics...</p>';

        fetch(`/tests/${window.testId}/analytics/`)
        .then(response => response.json())
        .then(data => {
            if (data.count === 0) {
                content.innerHTML = '<p style="color: #aaa;">No submissions to analyze yet.</p>';
                Toast.info('No Data', 'Upload some submissions first to see analytics');
                return;
            }

            let html = `
                <div class="analytics-grid">
                    <div class="stat-card">
                        <div class="stat-value">${data.total_submissions}</div>
                        <div class="stat-label">Total Submissions</div>
                    </div>
                    <div class="stat-card">
                        <div class="stat-value">${data.average_score}/${window.numQuestions}</div>
                        <div class="stat-label">Average Score</div>
                    </div>
                    <div class="stat-card">
                        <div class="stat-value">${data.average_percentage}%</div>
                        <div class="stat-label">Average Percentage</div>
                    </div>
                    <div class="stat-card">
                        <div class="stat-value">${data.pass_rate}%</div>
                        <div class="stat-label">Pass Rate (≥60%)</div>
                    </div>
                </div>

                <h3 style="color: #fff; margin-bottom: 15px;">Score Distribution</h3>
                <div class="analytics-grid" style="grid-template-columns: repeat(3, 1fr); margin-bottom: 30px;">
                    <div class="stat-card">
                        <div class="stat-value" style="color: #69c8a0;">${data.score_distribution.excellent}</div>
                        <div class="stat-label">Excellent (≥80%)</div>
                    </div>
                    <div class="stat-card">
                        <div class="stat-value" style="color: #667eea;">${data.score_distribution.good}</div>
                        <div class="stat-label">Good (60-79%)</div>
                    </div>
                    <div class="stat-card">
                        <div class="stat-value" style="color: #ff4444;">${data.score_distribution.needs_improvement}</div>
                        <div class="stat-label">Needs Improvement (<60%)</div>
                    </div>
                </div>

                <h3 style="color: #fff; margin-bottom: 15px; margin-top: 20px;">Grade Distribution</h3>
                <div style="background: #3a3a3a; padding: 20px; border-radius: 10px; margin-bottom: 30px;">
                    <div class="grade-bar" style="margin-bottom: 15px;">
                        <div style="display: flex; justify-content: space-between; margin-bottom: 5px;">
                            <span style="color: #69c8a0; font-weight: 600;">A (90-100%)</span>
                            <span style="color: #aaa;">${data.score_distribution.excellent > 0 ? Math.round((data.score_distribution.excellent / data.total_submissions) * 100) : 0}%</span>
                        </div>
                        <div style="width: 100%; height: 24px; background: #2a2a2a; border-radius: 6px; overflow: hidden;">
                            <div style="width: ${data.score_distribution.excellent > 0 ? (data.score_distribution.excellent / data.total_submissions * 100) : 0}%; height: 100%; background: linear-gradient(90deg, #69c8a0, #58b38e); transition: width 0.3s;"></div>
                        </div>
                    </div>
                    <div class="grade-bar" style="margin-bottom: 15px;">
                        <div style="display: flex; justify-content: space-between; margin-bottom: 5px;">
                            <span style="color: #667eea; font-weight: 600;">B/C (60-89%)</span>
                            <span style="color: #aaa;">${data.score_distribution.good > 0 ? Math.round((data.score_distribution.good / data.total_submissions) * 100) : 0}%</span>
                        </div>
                        <div style="width: 100%; height: 24px; background: #2a2a2a; border-radius: 6px; overflow: hidden;">
                            <div style="width: ${data.score_distribution.good > 0 ? (data.score_distribution.good / data.total_submissions * 100) : 0}%; height: 100%; background: linear-gradient(90deg, #667eea, #5568d3); transition: width 0.3s;"></div>
                        </div>
                    </div>
                    <div class="grade-bar">
                        <div style="display: flex; justify-content: space-between; margin-bottom: 5px;">
                            <span style="color: #ff4444; font-weight: 600;">D/F (<60%)</span>
                            <span style="color: #aaa;">${data.score_distribution.needs_improvement > 0 ? Math.round((data.score_distribution.needs_improvement / data.total_submissions) * 100) : 0}%</span>
                        </div>
                        <div style="width: 100%; height: 24px; background: #2a2a2a; border-radius: 6px; overflow: hidden;">
                            <div style="width: ${data.score_distribution.needs_improvement > 0 ? (data.score_distribution.needs_improvement / data.total_submissions * 100) : 0}%; height: 100%; background: linear-gradient(90deg, #ff4444, #cc0000); transition: width 0.3s;"></div>
                        </div>
                    </div>
                </div>

                <h3 style="color: #fff; margin-bottom: 15px;">Hardest Questions</h3>
                <ul class="difficulty-list">
            `;

            data.question_difficulty.forEach(q => {
                html += `
                    <li class="difficulty-item">
                        <span style="color: #fff;">
                            <strong>Q${q.question_num}:</strong> ${q.question_text}
                        </span>
                        <div style="display: flex; align-items: center; gap: 10px;">
                            <div class="difficulty-bar">
                                <div class="difficulty-fill" style="width: ${q.difficulty_percentage}%"></div>
                            </div>
                            <span style="color: #aaa; min-width: 50px;">${q.difficulty_percentage}%</span>
                        </div>
                    </li>
                `;
            });

            html += '</ul>';
            content.innerHTML = html;
        })
        .catch(error => {
            content.innerHTML = '<p style="color: #ff4444;">Error loading analytics</p>';
            Toast.error('Analytics Error', 'Failed to load analytics data');
            console.error('Error:', error);
        });
    } else {
        section.style.display = 'none';
    }
}

function exportResults() {
    Toast.info('Exporting...', 'Preparing CSV file for download');
    window.location.href = `/tests/${window.testId}/export/`;
    // Show success after a short delay (file download doesn't trigger response)
    setTimeout(() => {
        Toast.success('Export Complete', 'CSV file downloaded successfully');
    }, 1000);
}

function showEditTitleForm() {
    document.getElementById('title-edit-form').style.display = 'flex';
    document.getElementById('edit-title-btn').style.display = 'none';
    document.getElementById('title-input').focus();
}

function cancelTitleEdit() {
    document.getElementById('title-edit-form').style.display = 'none';
    document.getElementById('edit-title-btn').style.display = 'inline-block';
    // Reset input to original value
    document.getElementById('title-input').value = document.getElementById('test-title-display').textContent;
}

function saveTitleEdit() {
    const title = document.getElementById('title-input').value.trim();

    if (!title) {
        Toast.error('Validation Error', 'Test title is required');
        return;
    }

    // Disable inputs during save
    const inputs = document.querySelectorAll('#title-edit-form input, #title-edit-form button');
    inputs.forEach(el => el.disabled = true);

    fetch(`/tests/${window.testId}/update-name/`, {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
        },
        body: JSON.stringify({
            title: title
        })
    })
    .then(response => response.json())
    .then(data => {
        inputs.forEach(el => el.disabled = false);

        if (data.error) {
            Toast.error('Update Failed', data.error);
        } else {
            // Update the display title
            document.getElementById('test-title-display').textContent = data.title;

            // Also update the page title
            document.title = data.title + ' - SmartGrader';

            // Hide the form
            cancelTitleEdit();

            Toast.success('Title Updated', 'Test title has been successfully updated');
        }
    })
    .catch(error => {
        inputs.forEach(el => el.disabled = false);
        Toast.error('Update Error', 'An error occurred while updating the title');
        console.error('Error:', error);
    });
}

function copyEnrollmentCode() {
    const code = document.getElementById('enrollment-code').textContent;
    navigator.clipboard.writeText(code).then(() => {
        Toast.success('Copied!', `Enrollment code "${code}" copied to clipboard`);
    }).catch(err => {
        Toast.error('Copy Failed', 'Could not copy enrollment code');
        console.error('Copy error:', err);
    });
}
