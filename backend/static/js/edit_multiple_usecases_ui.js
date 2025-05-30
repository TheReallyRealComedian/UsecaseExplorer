// UsecaseExplorer/backend/static/js/edit_multiple_usecases_ui.js
import { initializeLLMChat } from './common_llm_chat.js'; // Import the new common module

document.addEventListener('DOMContentLoaded', function() {
    const usecasesData = INITIAL_USETYPE_DATA; // Passed from Flask template
    const pendingChanges = {}; // Maps ucId to a dict of {fieldName: newValue}

    // --- UI Elements (Bulk Edit specific) ---
    const saveAllChangesBtnTop = document.getElementById('saveAllChangesBtn');
    const cancelAllChangesBtnTop = document.getElementById('cancelAllChangesBtn');
    const pendingChangesCountTop = document.getElementById('pendingChangesCount');
    const saveAllChangesBtnBottom = document.getElementById('saveAllChangesBtnBottom');
    const cancelAllChangesBtnBottom = document.getElementById('cancelAllChangesBtnBottom');
    const pendingChangesCountBottom = document.getElementById('pendingChangesCountBottom');

    // --- LLM Helper specific UI Elements (New IDs for this page) ---
    // These IDs must match the ones defined in edit_multiple_usecases.html
    const llmHelperChatDisplayId = 'llmHelperChatDisplay';
    const llmHelperChatInputId = 'llmHelperChatInput';
    const llmHelperSendMessageButtonId = 'llmHelperSendMessageButton';
    const llmHelperClearChatButtonId = 'llmHelperClearChatButton';
    const llmHelperModelSelectId = 'llmHelperModelSelect';
    const llmHelperSystemPromptInputId = 'llmHelperSystemPromptInput'; // Unique ID for this page's system prompt
    const llmHelperSaveSystemPromptButtonId = 'llmHelperSaveSystemPromptButton'; // Unique ID for this page's save button
    const llmHelperImagePasteAreaId = 'llmHelperImagePasteArea';
    const llmHelperImagePreviewId = 'llmHelperImagePreview';
    const llmHelperClearImageButtonId = 'llmHelperClearImageButton';


    // --- Helper Functions (Bulk Edit specific) ---
    function updatePendingChangesCount() {
        let count = Object.keys(pendingChanges).length;
        pendingChangesCountTop.textContent = `${count} pending change${count === 1 ? '' : 's'}`;
        pendingChangesCountBottom.textContent = `${count} pending change${count === 1 ? '' : 's'}`;
        saveAllChangesBtnTop.disabled = (count === 0);
        cancelAllChangesBtnTop.disabled = (count === 0);
        saveAllChangesBtnBottom.disabled = (count === 0);
        cancelAllChangesBtnBottom.disabled = (count === 0);
    }

    function toggleFieldHighlight(ucId, fieldKey, isChanged) {
        const cardElement = document.querySelector(`.edit-usecase-card[data-uc-id="${ucId}"]`);
        if (!cardElement) return;
        const fieldRow = cardElement.querySelector(`.field-row[data-field-key="${fieldKey}"]`);
        if (fieldRow) {
            if (isChanged) {
                fieldRow.classList.add('unsaved-field-change');
            } else {
                fieldRow.classList.remove('unsaved-field-change');
            }
        }
    }

    function showFlashMessage(message, category) {
        let flashContainer = document.querySelector('.flash-messages');
        if (!flashContainer) {
            flashContainer = document.createElement('div');
            flashContainer.classList.add('flash-messages');
            document.querySelector('.page-content').prepend(flashContainer);
        }
        
        const alertDiv = document.createElement('div');
        alertDiv.classList.add('alert', `alert-${category}`);
        alertDiv.textContent = message;
        flashContainer.appendChild(alertDiv);

        setTimeout(() => {
            alertDiv.remove();
        }, 5000);
    }

    // --- Event Handlers for Individual Inputs (Bulk Edit specific) ---
    document.querySelectorAll('.new-value-input, .new-value-select').forEach(input => {
        input.addEventListener('input', function() {
            const ucId = parseInt(this.dataset.ucId);
            const fieldKey = this.dataset.field;
            let newValue = this.value;

            // Handle specific input types
            if (this.tagName === 'SELECT') {
                newValue = parseInt(newValue);
            } else if (this.type === 'number') {
                newValue = newValue.trim() === '' ? null : parseInt(newValue); // Allow null for empty number input
            } else {
                newValue = newValue.trim() === '' ? null : newValue.trim(); // Treat empty string as null for textareas/text inputs
            }

            // Find the original value for comparison
            const ucItem = usecasesData.find(u => u.id === ucId);
            let originalValue;
            if (fieldKey === 'process_step_id') {
                originalValue = ucItem.current_process_step_id;
            } else {
                originalValue = ucItem['current_' + fieldKey];
            }

            // Update usecasesData's new_values
            ucItem.new_values[fieldKey] = newValue;

            if (newValue !== originalValue) {
                if (!pendingChanges[ucId]) {
                    pendingChanges[ucId] = { id: ucId, updated_fields: {} };
                }
                pendingChanges[ucId].updated_fields[fieldKey] = newValue;
                toggleFieldHighlight(ucId, fieldKey, true);
            } else {
                // Value reverted to original, remove from pending changes
                if (pendingChanges[ucId]) {
                    delete pendingChanges[ucId].updated_fields[fieldKey];
                    if (Object.keys(pendingChanges[ucId].updated_fields).length === 0) {
                        delete pendingChanges[ucId];
                    }
                }
                toggleFieldHighlight(ucId, fieldKey, false);
            }
            updatePendingChangesCount();
        });
    });

    // --- Save All Changes Functionality (Bulk Edit specific) ---
    async function saveAllChanges() {
        if (Object.keys(pendingChanges).length === 0) {
            showFlashMessage('No changes to save.', 'info');
            return;
        }

        if (!confirm('Are you sure you want to save all pending changes?')) {
            return;
        }

        // Disable buttons
        saveAllChangesBtnTop.disabled = true;
        cancelAllChangesBtnTop.disabled = true;
        saveAllChangesBtnBottom.disabled = true;
        cancelAllChangesBtnBottom.disabled = true;
        pendingChangesCountTop.textContent = 'Saving...';
        pendingChangesCountBottom.textContent = 'Saving...';

        // Prepare data for API call
        const changesPayload = Object.values(pendingChanges);

        try {
            const response = await fetch('/data-update/usecases/save-all-changes', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify(changesPayload),
            });

            const result = await response.json();

            if (result.success) {
                showFlashMessage(result.message, 'success');
                // Update original values in usecasesData and clear pendingChanges
                usecasesData.forEach(ucItem => {
                    if (pendingChanges[ucItem.id]) {
                        for (const fieldKey in pendingChanges[ucItem.id].updated_fields) {
                            // Update the 'current' value to the new saved value
                            if (fieldKey === 'process_step_id') {
                                 ucItem.current_process_step_id = ucItem.new_values.process_step_id;
                                 // Also update the displayed step name for consistency
                                 const selectedStep = ALL_STEPS_DATA_FOR_DROPDOWN.find(ps => ps.id === ucItem.new_values.process_step_id);
                                 ucItem.current_process_step_name = selectedStep ? selectedStep.name : 'N/A';
                            } else {
                                ucItem['current_' + fieldKey] = ucItem.new_values[fieldKey];
                            }
                            toggleFieldHighlight(ucItem.id, fieldKey, false);
                        }
                    }
                });
                // Clear pending changes completely
                Object.keys(pendingChanges).forEach(key => delete pendingChanges[key]);
                updatePendingChangesCount();
                // Optionally, reload the page or redirect to data_update_page after a delay
                setTimeout(() => { window.location.href = '/data-update'; }, 1500);

            } else {
                showFlashMessage(result.message, 'danger');
                // Keep pending changes, re-enable buttons
                saveAllChangesBtnTop.disabled = false;
                cancelAllChangesBtnTop.disabled = false;
                saveAllChangesBtnBottom.disabled = false;
                cancelAllChangesBtnBottom.disabled = false;
                updatePendingChangesCount(); // Re-evaluate status message
            }
        } catch (error) {
            console.error('Fetch error during bulk save:', error);
            showFlashMessage('Network error during save. Please check your connection.', 'danger');
            // Re-enable buttons
            saveAllChangesBtnTop.disabled = false;
            cancelAllChangesBtnTop.disabled = false;
            saveAllChangesBtnBottom.disabled = false;
            cancelAllChangesBtnBottom.disabled = false;
            updatePendingChangesCount(); // Re-evaluate status message
        }
    }

    // --- Discard All Changes Functionality (Bulk Edit specific) ---
    function discardAllChanges() {
        if (Object.keys(pendingChanges).length === 0) {
            showFlashMessage('No changes to discard.', 'info');
            return;
        }

        if (!confirm('Are you sure you want to discard all pending changes?')) {
            return;
        }

        usecasesData.forEach(ucItem => {
            for (const fieldKey in EDITABLE_FIELDS_CONFIG) {
                const inputElement = document.querySelector(`.edit-usecase-card[data-uc-id="${ucItem.id}"] .new-value-${fieldKey === 'process_step_id' ? 'select' : 'input'}[data-field="${fieldKey}"]`);
                if (inputElement) {
                    let originalValue;
                    if (fieldKey === 'process_step_id') {
                        originalValue = ucItem.current_process_step_id;
                    } else {
                        originalValue = ucItem['current_' + fieldKey];
                    }
                    // Set input value back to original
                    inputElement.value = originalValue === null ? '' : originalValue;
                    // Update usecasesData's new_values to reflect discard
                    ucItem.new_values[fieldKey] = originalValue;
                    toggleFieldHighlight(ucItem.id, fieldKey, false);
                }
            }
        });
        // Clear pending changes completely
        Object.keys(pendingChanges).forEach(key => delete pendingChanges[key]);
        updatePendingChangesCount();
        showFlashMessage('All pending changes have been discarded.', 'info');
    }

    // Attach global buttons (Bulk Edit specific)
    saveAllChangesBtnTop.addEventListener('click', saveAllChanges);
    saveAllChangesBtnBottom.addEventListener('click', saveAllChanges);
    cancelAllChangesBtnTop.addEventListener('click', discardAllChanges);
    cancelAllChangesBtnBottom.addEventListener('click', discardAllChanges);

    // Initial update of count and button states (Bulk Edit specific)
    updatePendingChangesCount();

    // --- Initialize LLM Chat Helper on this page using the common module ---
    const llmHelperHeader = document.getElementById('llmHelperHeader'); // This is the div.card-header
    
    // **FIX START**
    // Get the actual button element inside the header that controls the collapse
    let collapseToggleButton = null;
    if (llmHelperHeader) {
        collapseToggleButton = llmHelperHeader.querySelector('[data-bs-toggle="collapse"]');
    }

    if (llmHelperHeader && collapseToggleButton) { // Ensure both elements exist
        const targetId = collapseToggleButton.getAttribute('data-bs-target');
        const collapseElement = document.getElementById(targetId.substring(1)); // Get the target element by ID
        const iconElement = collapseToggleButton.querySelector('i'); // Get icon from the button
        
        if (collapseElement && iconElement) {
            // Set initial icon state based on 'show' class
            if (collapseElement.classList.contains('show')) {
                iconElement.classList.remove('fa-chevron-down');
                iconElement.classList.add('fa-chevron-up');
            } else {
                iconElement.classList.remove('fa-chevron-up');
                iconElement.classList.add('fa-chevron-down');
            }

            // Add event listeners for Bootstrap collapse events
            collapseElement.addEventListener('shown.bs.collapse', () => {
                iconElement.classList.remove('fa-chevron-down');
                iconElement.classList.add('fa-chevron-up');
            });
            collapseElement.addEventListener('hidden.bs.collapse', () => {
                iconElement.classList.remove('fa-chevron-up');
                iconElement.classList.add('fa-chevron-down');
            });
        }
    }
    // **FIX END**

    // Initialize LLM Chat Helper
    initializeLLMChat(
        llmHelperChatDisplayId,
        llmHelperChatInputId,
        llmHelperSendMessageButtonId,
        llmHelperClearChatButtonId,
        llmHelperModelSelectId,
        llmHelperSystemPromptInputId,
        llmHelperSaveSystemPromptButtonId,
        llmHelperImagePasteAreaId,
        llmHelperImagePreviewId,
        llmHelperClearImageButtonId
    );
});