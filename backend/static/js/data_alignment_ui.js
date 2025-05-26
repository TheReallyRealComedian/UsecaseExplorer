// backend/static/js/data_alignment_ui.js
document.addEventListener('DOMContentLoaded', function() {

    const areaAlignmentSelects = document.querySelectorAll('.area-alignment-select');
    const usecaseAlignmentSelects = document.querySelectorAll('.usecase-alignment-select');
    const saveAllChangesBtn = document.getElementById('saveAllChangesBtn');
    const cancelAllChangesBtn = document.getElementById('cancelAllChangesBtn');
    const pendingChangesCountSpan = document.getElementById('pendingChangesCount');
    const alignmentStatusSpan = document.getElementById('alignmentStatus');

    // Object to store pending changes
    // Keys are entity_id, values are { type: 'step_area'|'usecase_step', new_id: ID }
    const pendingChanges = {}; // Map: entity_id -> { type, originalId, newId, rowElement }

    // --- Utility Functions ---

    // Function to show ephemeral flash messages
    function showEphemeralFlashMessage(message, category) {
        let flashContainer = document.querySelector('.flash-messages');
        if (!flashContainer) {
            flashContainer = document.createElement('div');
            flashContainer.classList.add('flash-messages');
            document.querySelector('main.page-content').prepend(flashContainer);
        } else {
            // Clear any previous JS-generated messages
            Array.from(flashContainer.children).forEach(child => {
                if (child.dataset.fromJs) {
                    child.remove();
                }
            });
        }
        
        const alertDiv = document.createElement('div');
        alertDiv.classList.add('alert', `alert-${category}`);
        alertDiv.textContent = message;
        alertDiv.dataset.fromJs = true;
        flashContainer.appendChild(alertDiv);

        setTimeout(() => {
            alertDiv.remove();
            if (flashContainer.children.length === 0) {
                flashContainer.remove();
            }
        }, 5000);
    }

    // Function to update the pending changes UI
    function updatePendingChangesUI() {
        const count = Object.keys(pendingChanges).length;
        pendingChangesCountSpan.textContent = count;
        if (count > 0) {
            saveAllChangesBtn.disabled = false;
            cancelAllChangesBtn.disabled = false;
            alignmentStatusSpan.textContent = `${count} pending change${count === 1 ? '' : 's'}.`;
        } else {
            saveAllChangesBtn.disabled = true;
            cancelAllChangesBtn.disabled = true;
            alignmentStatusSpan.textContent = 'No pending changes.';
        }
    }

    // Function to add/remove 'unsaved-change' class
    function toggleUnsavedClass(element, isUnsaved) {
        if (element) {
            const row = element.closest('tr'); // Find the table row
            if (row) {
                if (isUnsaved) {
                    row.classList.add('unsaved-change');
                } else {
                    row.classList.remove('unsaved-change');
                }
            }
        }
    }

    // --- Event Listeners for Dropdowns (Collect Changes) ---

    areaAlignmentSelects.forEach(select => {
        // Store original value on the element for quick lookup and reset
        const row = select.closest('tr');
        select.dataset.originalValue = row.dataset.originalAreaId; 

        select.addEventListener('change', function() {
            const stepId = this.dataset.stepId;
            const newAreaId = this.value;
            const originalAreaId = this.dataset.originalValue;
            const rowElement = this.closest('tr');

            // Explicitly convert to integers for comparison
            if (parseInt(newAreaId) !== parseInt(originalAreaId)) { // MODIFIED LINE
                pendingChanges[stepId] = {
                    type: 'step_area',
                    entity_id: stepId,
                    new_id: newAreaId,
                    original_id: originalAreaId,
                    element: this, // Store reference to the select element
                    row: rowElement // Store reference to the row for visual cue
                };
                toggleUnsavedClass(this, true);
            } else {
                delete pendingChanges[stepId];
                toggleUnsavedClass(this, false);
            }
            updatePendingChangesUI();
        });
    });

    usecaseAlignmentSelects.forEach(select => {
        // Store original value on the element for quick lookup and reset
        const row = select.closest('tr');
        select.dataset.originalValue = row.dataset.originalStepId;

        select.addEventListener('change', function() {
            const usecaseId = this.dataset.usecaseId;
            const newProcessStepId = this.value;
            const originalProcessStepId = this.dataset.originalValue;
            const rowElement = this.closest('tr');

            // Explicitly convert to integers for comparison
            if (parseInt(newProcessStepId) !== parseInt(originalProcessStepId)) { // MODIFIED LINE
                pendingChanges[usecaseId] = {
                    type: 'usecase_step',
                    entity_id: usecaseId,
                    new_id: newProcessStepId,
                    original_id: originalProcessStepId,
                    element: this,
                    row: rowElement
                };
                toggleUnsavedClass(this, true);
            } else {
                delete pendingChanges[usecaseId];
                toggleUnsavedClass(this, false);
            }
            updatePendingChangesUI();
        });
    });

    // --- Save All Changes Button Logic ---

    saveAllChangesBtn.addEventListener('click', function() {
        if (Object.keys(pendingChanges).length === 0) {
            showEphemeralFlashMessage('No changes to save.', 'info');
            return;
        }

        if (!confirm('Are you sure you want to save all pending changes?')) {
            return;
        }

        const updatesToSend = {
            step_area_updates: [],
            usecase_step_updates: []
        };

        for (const key in pendingChanges) {
            const change = pendingChanges[key];
            if (change.type === 'step_area') {
                updatesToSend.step_area_updates.push({
                    step_id: parseInt(change.entity_id),
                    new_area_id: parseInt(change.new_id)
                });
            } else if (change.type === 'usecase_step') {
                updatesToSend.usecase_step_updates.push({
                    usecase_id: parseInt(change.entity_id),
                    new_process_step_id: parseInt(change.new_id)
                });
            }
        }

        // Disable buttons and update status
        saveAllChangesBtn.disabled = true;
        cancelAllChangesBtn.disabled = true;
        alignmentStatusSpan.textContent = 'Saving changes...';

        fetch('/data-alignment/batch-update', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify(updatesToSend)
        })
        .then(response => {
            if (!response.ok) {
                return response.json().then(errorData => {
                    throw new Error(errorData.message || `Server responded with status ${response.status}`);
                });
            }
            return response.json();
        })
        .then(data => {
            if (data.success) {
                // If there were any updates (even if some failed), show success message
                showEphemeralFlashMessage(`Successfully saved ${data.successful_updates} of ${data.total_updates} changes. Reloading page...`, 'success');
                // The backend also flashes messages, so a reload will show those.
                
                // Clear local pending changes and remove visual cues
                for (const key in pendingChanges) {
                    toggleUnsavedClass(pendingChanges[key].element, false);
                }
                Object.keys(pendingChanges).forEach(key => delete pendingChanges[key]);
                updatePendingChangesUI();

                // Reload the page after a short delay
                setTimeout(() => { location.reload(); }, 1500);

            } else {
                // If the overall success flag is false (meaning some or all failed)
                const failedCount = data.failed_updates ? data.failed_updates.length : 0;
                let errorMessage = `Failed to save ${failedCount} of ${data.total_updates} changes. Check console for details.`;
                showEphemeralFlashMessage(errorMessage, 'danger');
                console.error("Batch update failed details:", data.failed_updates);
                // Don't clear pending changes, allow user to try again or cancel
            }
        })
        .catch(error => {
            showEphemeralFlashMessage('Network or server error during save: ' + error.message, 'danger');
            console.error('Fetch error for batch-update:', error);
        })
        .finally(() => {
            // Re-enable buttons if not reloading
            if (!saveAllChangesBtn.disabled) { // Only if not already disabled by a pending reload
                saveAllChangesBtn.disabled = false;
                cancelAllChangesBtn.disabled = false;
                updatePendingChangesUI(); // Re-evaluate status message
            }
        });
    });

    // --- Cancel All Changes Button Logic ---

    cancelAllChangesBtn.addEventListener('click', function() {
        if (Object.keys(pendingChanges).length === 0) {
            showEphemeralFlashMessage('No changes to cancel.', 'info');
            return;
        }

        if (!confirm('Are you sure you want to discard all pending changes?')) {
            return;
        }

        // Revert all dropdowns to their original values
        for (const key in pendingChanges) {
            const change = pendingChanges[key];
            change.element.value = change.original_id; // Revert select value
            toggleUnsavedClass(change.element, false); // Remove highlight
        }

        // Clear the pending changes object
        Object.keys(pendingChanges).forEach(key => delete pendingChanges[key]);
        updatePendingChangesUI(); // Update UI status
        showEphemeralFlashMessage('All pending changes discarded.', 'info');
    });

    // Initial UI update on page load
    updatePendingChangesUI();

    // On page load, if there are any Flask-generated flash messages, ensure they are visible.
    const flaskAlerts = document.querySelectorAll('.flash-messages .alert');
    flaskAlerts.forEach(alert => {
        alert.dataset.fromFlask = true;
    });
});