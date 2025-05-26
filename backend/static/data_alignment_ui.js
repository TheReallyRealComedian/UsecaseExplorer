// backend/static/js/data_alignment_ui.js
document.addEventListener('DOMContentLoaded', function() {

    const areaAlignmentSelects = document.querySelectorAll('.area-alignment-select');
    const usecaseAlignmentSelects = document.querySelectorAll('.usecase-alignment-select');

    function showFlashMessage(message, category) {
        const flashContainer = document.querySelector('.flash-messages') || document.createElement('div');
        if (!flashContainer.classList.contains('flash-messages')) {
            flashContainer.classList.add('flash-messages');
            document.querySelector('main.page-content').prepend(flashContainer); // Prepend to main content
        }
        
        const alertDiv = document.createElement('div');
        alertDiv.classList.add('alert', `alert-${category}`);
        alertDiv.textContent = message;
        flashContainer.appendChild(alertDiv);

        // Remove after 5 seconds
        setTimeout(() => {
            alertDiv.remove();
            if (flashContainer.children.length === 0) {
                flashContainer.remove(); // Remove container if no more alerts
            }
        }, 5000);
    }

    areaAlignmentSelects.forEach(select => {
        // Store initial value to revert on error
        select.dataset.originalValue = select.value;

        select.addEventListener('change', function() {
            const stepId = this.dataset.stepId;
            const newAreaId = this.value;
            const previousValue = this.dataset.originalValue; // The value before this change

            // Show a temporary "Updating..." message
            const originalSelectedOption = this.options[this.selectedIndex];
            const originalText = originalSelectedOption.text;
            originalSelectedOption.text = 'Updating...';
            this.disabled = true;

            fetch('/data-alignment/update_step_area', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/x-www-form-urlencoded',
                },
                body: new URLSearchParams({
                    'step_id': stepId,
                    'new_area_id': newAreaId
                })
            })
            .then(response => {
                if (!response.ok) {
                    // If Flask didn't return 200 OK, parse error message and throw
                    return response.json().then(errorData => {
                        throw new Error(errorData.message || 'Server error');
                    });
                }
                return response.json();
            })
            .then(data => {
                if (data.success) {
                    showFlashMessage('Process Step area updated successfully.', 'success');
                    // Store the new value as the "originalValue" for future changes
                    this.dataset.originalValue = newAreaId;
                } else {
                    showFlashMessage('Error updating: ' + data.message, 'danger');
                    // Revert selection if update failed
                    this.value = previousValue; 
                }
            })
            .catch(error => {
                showFlashMessage('Network or server error during update: ' + error.message, 'danger');
                // Revert selection on network error
                this.value = previousValue;
                console.error('Fetch error:', error);
            })
            .finally(() => {
                originalSelectedOption.text = originalText; // Revert text
                this.disabled = false;
            });
        });
    });


    usecaseAlignmentSelects.forEach(select => {
        // Store initial value to revert on error
        select.dataset.originalValue = select.value;

        select.addEventListener('change', function() {
            const usecaseId = this.dataset.usecaseId;
            const newProcessStepId = this.value;
            const previousValue = this.dataset.originalValue; // The value before this change

            // Show a temporary "Updating..." message
            const originalSelectedOption = this.options[this.selectedIndex];
            const originalText = originalSelectedOption.text;
            originalSelectedOption.text = 'Updating...';
            this.disabled = true;

            fetch('/data-alignment/update_usecase_step', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/x-www-form-urlencoded',
                },
                body: new URLSearchParams({
                    'usecase_id': usecaseId,
                    'new_process_step_id': newProcessStepId
                })
            })
            .then(response => {
                if (!response.ok) {
                    return response.json().then(errorData => {
                        throw new Error(errorData.message || 'Server error');
                    });
                }
                return response.json();
            })
            .then(data => {
                if (data.success) {
                    showFlashMessage('Use Case process step updated successfully.', 'success');
                    this.dataset.originalValue = newProcessStepId;
                } else {
                    showFlashMessage('Error updating: ' + data.message, 'danger');
                    this.value = previousValue;
                }
            })
            .catch(error => {
                showFlashMessage('Network or server error during update: ' + error.message, 'danger');
                this.value = previousValue;
                console.error('Fetch error:', error);
            })
            .finally(() => {
                originalSelectedOption.text = originalText; // Revert text
                this.disabled = false;
            });
        });
    });

    // Initialize Bootstrap Collapses (as a fallback/diagnostic if data-bs-toggle is not enough)
    // In most cases, data-bs-toggle="collapse" and data-bs-target="..." on the button are sufficient.
    // Explicit initialization is rarely needed for static content.
    // var accordions = document.querySelectorAll('.accordion');
    // accordions.forEach(function(accordion) {
    //     new bootstrap.Collapse(accordion, { toggle: false });
    // });
});