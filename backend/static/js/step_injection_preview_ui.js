// backend/static/js/step_injection_preview_ui.js

document.addEventListener('DOMContentLoaded', function() {
    // Global references to data passed from Flask template
    let previewData = INITIAL_PREVIEW_DATA; // This will be mutated as user makes changes
    const stepDetailFieldsConfig = STEP_DETAIL_FIELDS_CONFIG;
    const allAreasData = ALL_AREAS_DATA; // Array of {id, name, description}

    // Main table elements
    const finalizeForm = document.getElementById('finalizeStepImportForm');
    const confirmImportBtn = document.getElementById('confirmImportBtn');
    const cancelImportBtn = document.getElementById('cancelImportBtn');
    const previewTableBody = document.querySelector('#finalizeStepImportForm tbody');

    // Modal elements
    const stepDetailModal = document.getElementById('stepDetailModal');
    const modalStepName = document.getElementById('modalStepName');
    const modalStepBiId = document.getElementById('modalStepBiId');
    const modalAreaSelect = document.getElementById('modalAreaSelect');
    const modalAreaDbValue = document.getElementById('modalAreaDbValue');
    const modalAreaJsonValue = document.getElementById('modalAreaJsonValue');
    const modalFieldsContainer = document.getElementById('modal-fields-container');
    const saveModalChangesBtn = document.getElementById('saveModalChangesBtn');

    // Store the currently active row index when modal is open
    let currentModalRowIndex = -1;

    // --- Helper Functions ---

    function getRowElement(rowIndex) {
        return previewTableBody.querySelector(`tr[data-row-index="${rowIndex}"]`);
    }

    // Function to update the row's appearance in the main table based on changes
    function updateRowVisuals(rowIndex) {
        const rowElement = getRowElement(rowIndex);
        if (!rowElement) return;

        const item = previewData[rowIndex];

        // Update status badge
        const statusBadge = rowElement.querySelector('.status-badge');
        if (statusBadge) {
            statusBadge.textContent = item.status.toUpperCase();
            statusBadge.classList.remove('bg-success', 'bg-warning', 'text-dark', 'bg-secondary', 'bg-danger', 'bg-info'); // Added bg-info removal
            if (item.status === 'new') statusBadge.classList.add('bg-success');
            else if (item.status === 'update') statusBadge.classList.add('bg-warning', 'text-dark');
            else if (item.status === 'no_change') statusBadge.classList.add('bg-secondary');
            else if (item.status === 'skipped') statusBadge.classList.add('bg-danger');
            else statusBadge.classList.add('bg-info'); // Default for any other status
        }

        // Update name input in main table
        const nameInput = rowElement.querySelector('.row-final-value-input[data-field="name"]');
        if (nameInput) {
            nameInput.value = item.new_values.name || '';
            nameInput.disabled = (item.action === 'skip');
        }

        // Update area select in main table
        const areaSelect = rowElement.querySelector('.row-final-area-select[data-field="area_id"]');
        if (areaSelect) {
            areaSelect.value = item.new_values.area_id || '';
            areaSelect.disabled = (item.action === 'skip');
        }

        // --- START FIX for Radio Button Disabling Logic ---
        const actionRadios = rowElement.querySelectorAll(`.action-radio[name="action_${item.bi_id}"]`);
        actionRadios.forEach(radio => {
            radio.checked = (radio.value === item.action);
            
            // New, more robust disabling logic
            const isAddRadio = radio.value === 'add';
            const isUpdateRadio = radio.value === 'update';

            radio.disabled = false; // Enable by default

            if (item.original_status === 'new') {
                if (isUpdateRadio) radio.disabled = true;
            } else if (item.original_status === 'update' || item.original_status === 'no_change') {
                if (isAddRadio) radio.disabled = true;
            } else if (item.original_status === 'skipped') {
                // If the item was skipped for a non-recoverable reason, disable both add and update
                if (isAddRadio || isUpdateRadio) radio.disabled = true;
            }
        });
        // --- END FIX for Radio Button Disabling Logic ---

        // Add/remove unsaved-change class
        if (item.action === 'update' || item.action === 'add') {
            rowElement.classList.add('unsaved-change');
        } else {
            rowElement.classList.remove('unsaved-change');
        }

        // Update message area for the row
        const messageDisplay = rowElement.querySelector('.message-display');
        if (messageDisplay) {
            messageDisplay.textContent = item.messages && item.messages.length > 0 ? item.messages[0] : '';
        }
    }


    // --- Modal Population Logic ---
    function populateModal(rowIndex) {
        currentModalRowIndex = rowIndex;
        const item = previewData[rowIndex];

        // Set modal header
        modalStepName.textContent = item.name || item.new_values.name || 'N/A';
        modalStepBiId.textContent = item.bi_id;

        // Populate Area select in modal
        modalAreaSelect.value = item.new_values.area_id || '';
        modalAreaDbValue.textContent = item.db_data.area_name || 'N/A';
        modalAreaJsonValue.textContent = item.area_name || item.new_values.area_name || 'N/A';
        modalAreaSelect.disabled = (item.action === 'skip');


        // Populate other fields in modal
        for (const fieldKey in stepDetailFieldsConfig) {
            const fieldGroup = modalFieldsContainer.querySelector(`.modal-field-group[data-field-key="${fieldKey}"]`);
            if (!fieldGroup) continue;

            const dbContentPre = fieldGroup.querySelector('.modal-db-content');
            const jsonContentPre = fieldGroup.querySelector('.modal-json-content');
            const manualInput = fieldGroup.querySelector('.modal-final-value-input');
            const conflictMessage = fieldGroup.querySelector('.field-conflict-message');

            const radioDb = fieldGroup.querySelector(`#modal_db_choice_${fieldKey}`);
            const radioJson = fieldGroup.querySelector(`#modal_json_choice_${fieldKey}`);
            const radioManual = fieldGroup.querySelector(`#modal_manual_choice_${fieldKey}`);

            // Reset visibility/checked state
            fieldGroup.classList.remove('is-conflict', 'is-new-field', 'is-no-change');
            if (radioDb) radioDb.checked = false;
            if (radioJson) radioJson.checked = false;
            if (radioManual) radioManual.checked = false;
            conflictMessage.style.display = 'none';

            // All inputs initially disabled if action is skip
            const isDisabledByAction = (item.action === 'skip');
            manualInput.disabled = isDisabledByAction;
            if (radioDb) radioDb.disabled = isDisabledByAction;
            if (radioJson) radioJson.disabled = isDisabledByAction;
            if (radioManual) radioManual.disabled = isDisabledByAction;


            // Handle content and radio selections based on item status and conflicts
            if (fieldKey in item.conflicts) {
                fieldGroup.classList.add('is-conflict');
                conflictMessage.style.display = 'block';

                const dbValue = item.conflicts[fieldKey].old_value;
                const jsonValue = item.conflicts[fieldKey].new_value;
                const preselectedFinalValue = item.new_values[fieldKey];

                dbContentPre.textContent = (dbValue === null || dbValue === undefined || dbValue === "N/A (Empty)") ? 'N/A' : dbValue;
                jsonContentPre.textContent = (jsonValue === null || jsonValue === undefined || jsonValue === "N/A (Empty)") ? 'N/A' : jsonValue;
                manualInput.value = preselectedFinalValue !== null && preselectedFinalValue !== undefined ? preselectedFinalValue : '';

                if (preselectedFinalValue === dbValue) {
                    if (radioDb) radioDb.checked = true;
                } else if (preselectedFinalValue === jsonValue) {
                    if (radioJson) radioJson.checked = true;
                } else {
                    if (radioManual) radioManual.checked = true;
                }
                if (radioDb) radioDb.style.display = '';
                if (radioJson) radioJson.style.display = '';
                if (radioManual) radioManual.style.display = '';

            } else if (item.status === 'new' || item.original_status === 'new') { // Check original_status as well
                fieldGroup.classList.add('is-new-field');
                dbContentPre.textContent = 'N/A (No existing DB value)';
                jsonContentPre.textContent = item.json_data[fieldKey] || 'N/A';
                manualInput.value = item.new_values[fieldKey] !== null && item.new_values[fieldKey] !== undefined ? item.new_values[fieldKey] : '';

                if (radioDb) radioDb.style.display = 'none';
                if (radioJson) radioJson.style.display = 'none';
                if (radioManual) radioManual.style.display = 'none';
            } else if (item.status === 'no_change' && !item.conflicts[fieldKey]) {
                fieldGroup.classList.add('is-no-change');
                dbContentPre.textContent = item.db_data[fieldKey] || 'N/A';
                jsonContentPre.textContent = item.json_data[fieldKey] || 'N/A';
                manualInput.value = item.db_data[fieldKey] !== null && item.db_data[fieldKey] !== undefined ? item.db_data[fieldKey] : '';
                manualInput.disabled = true;

                if (radioDb) radioDb.style.display = 'none';
                if (radioJson) radioJson.style.display = 'none';
                if (radioManual) radioManual.style.display = 'none';
            } else {
                dbContentPre.textContent = item.db_data[fieldKey] || 'N/A';
                jsonContentPre.textContent = item.json_data[fieldKey] || 'N/A';
                manualInput.value = item.new_values[fieldKey] !== null && item.new_values[fieldKey] !== undefined ? item.new_values[fieldKey] : '';

                if (radioDb) radioDb.style.display = 'none';
                if (radioJson) radioJson.style.display = 'none';
                if (radioManual) radioManual.style.display = 'none';
            }
        }
    }

    // --- Modal Interaction Handlers ---

    // Handle radio button changes in modal
    modalFieldsContainer.addEventListener('change', function(event) {
        const target = event.target;
        if (target.classList.contains('modal-radio-choice')) {
            const fieldKey = target.dataset.field;
            const item = previewData[currentModalRowIndex];
            const manualInput = modalFieldsContainer.querySelector(`#modal_manual_input_${fieldKey}`);

            if (target.value === 'db') {
                manualInput.value = (item.conflicts[fieldKey] && item.conflicts[fieldKey].old_value !== undefined) ? item.conflicts[fieldKey].old_value : (item.db_data[fieldKey] || '');
            } else if (target.value === 'json') {
                manualInput.value = (item.conflicts[fieldKey] && item.conflicts[fieldKey].new_value !== undefined) ? item.conflicts[fieldKey].new_value : (item.json_data[fieldKey] || '');
            }
        }
    });

    // Handle manual input changes in modal (deselect radios)
    modalFieldsContainer.addEventListener('input', function(event) {
        const target = event.target;
        if (target.classList.contains('modal-final-value-input')) {
            const fieldKey = target.dataset.field;
            const radios = modalFieldsContainer.querySelectorAll(`input[name="modal_choice_${fieldKey}"]`);
            radios.forEach(radio => radio.checked = false);
            const manualRadio = modalFieldsContainer.querySelector(`#modal_manual_choice_${fieldKey}`);
            if (manualRadio && !manualRadio.disabled) {
                manualRadio.checked = true;
            }
        }
    });

    // --- Save Modal Changes ---
    saveModalChangesBtn.addEventListener('click', function() {
        const item = previewData[currentModalRowIndex];
        let changesMadeInModal = false;

        const rowElement = getRowElement(currentModalRowIndex);
        const nameInput = rowElement.querySelector('.row-final-value-input[data-field="name"]');
        if (nameInput) {
            const newName = nameInput.value.trim() === '' ? null : nameInput.value.trim();
            if (item.new_values.name !== newName) {
                item.new_values.name = newName;
                changesMadeInModal = true;
            }
        }

        const newAreaId = parseInt(modalAreaSelect.value);
        if (item.new_values.area_id !== newAreaId) {
            item.new_values.area_id = newAreaId;
            const selectedArea = allAreasData.find(area => area.id === newAreaId);
            item.new_values.area_name = selectedArea ? selectedArea.name : 'N/A';
            changesMadeInModal = true;
        }

        for (const fieldKey in stepDetailFieldsConfig) {
            const manualInput = modalFieldsContainer.querySelector(`#modal_manual_input_${fieldKey}`);
            if (manualInput && !manualInput.disabled) {
                const newValue = manualInput.value.trim() === '' ? null : manualInput.value.trim();
                if (item.new_values[fieldKey] !== newValue) {
                    item.new_values[fieldKey] = newValue;
                    changesMadeInModal = true;
                }
            }
        }

        if (changesMadeInModal && (item.action === 'skip' || item.action === 'no_change')) {
            item.action = 'update';
        }

        if (item.action === 'update') {
            item.status = 'update';
        } else if (item.action === 'add') {
            item.status = 'new';
        } else if (item.action === 'skip') {
            item.status = 'skipped';
        }


        updateRowVisuals(currentModalRowIndex);
        bootstrap.Modal.getInstance(stepDetailModal).hide();
    });

    // --- Main Table Interaction Handlers ---

    // Event listener for "Review/Edit Details" button
    previewTableBody.addEventListener('click', function(event) {
        const target = event.target;
        if (target.classList.contains('review-details-btn')) {
            const rowIndex = parseInt(target.dataset.rowIndex);
            populateModal(rowIndex);
        }
    });

    // Event listener for row-level Name and Area changes
    previewTableBody.addEventListener('change', function(event) {
        const target = event.target;
        if (target.classList.contains('row-final-value-input') || target.classList.contains('row-final-area-select')) {
            const rowIndex = parseInt(target.closest('tr').dataset.rowIndex);
            const item = previewData[rowIndex];
            const field = target.dataset.field;
            let newValue = target.value.trim() === '' ? null : target.value.trim();

            if (field === 'area_id') {
                newValue = parseInt(newValue) || null; // Ensure it's an int or null
            }

            if (item.new_values[field] !== newValue) {
                item.new_values[field] = newValue;
                if (field === 'area_id') {
                    const selectedArea = allAreasData.find(area => area.id === newValue);
                    item.new_values.area_name = selectedArea ? selectedArea.name : 'N/A';
                }

                if (item.action === 'skip' || item.action === 'no_change') {
                    // If original status allows update, then promote to update
                    if (item.original_status === 'update' || item.original_status === 'no_change' || item.original_status === 'skipped') {
                        item.action = 'update';
                        item.status = 'update';
                    }
                    // If original status was 'new', it should stay 'add' or 'skip'
                    // This direct edit shouldn't change an 'add' to 'update'.
                }
                updateRowVisuals(rowIndex);
            }
        }
    });

    // Event listener for row-level Action radio buttons
    previewTableBody.addEventListener('change', function(event) {
        const target = event.target;
        if (target.classList.contains('action-radio')) {
            const rowIndex = parseInt(target.dataset.rowIndex);
            if (isNaN(rowIndex) || rowIndex < 0 || rowIndex >= previewData.length) {
                console.error("Invalid rowIndex from action-radio:", target.dataset.rowIndex);
                return;
            }
            const item = previewData[rowIndex];
            item.action = target.value;

            if (item.action === 'add') {
                item.status = 'new';
            } else if (item.action === 'update') {
                item.status = 'update';
            } else if (item.action === 'skip') {
                item.status = 'skipped';
            }
            updateRowVisuals(rowIndex);
        }
    });

    // --- Global Action Buttons (Confirm/Cancel Import) ---

    confirmImportBtn.addEventListener('click', async function(event) {
        event.preventDefault();

        if (!confirm('Are you sure you want to finalize the import with the displayed changes?')) {
            return;
        }

        const resolvedData = [];
        let isValid = true;
        let firstInvalidRow = null;

        previewData.forEach((item, index) => {
            if (!['add', 'update', 'skip'].includes(item.action)) {
                console.error(`Item at index ${index} has invalid action: ${item.action}`, item);
                item.action = 'skip'; // Default to skip if action is invalid
            }

            if (item.action === 'add' || item.action === 'update') {
                const name = item.new_values.name;
                const area_id = item.new_values.area_id;

                if (!name) {
                    isValid = false;
                    flashMessage(`Name is required for step ${item.bi_id} (row ${index + 1}). Action set to 'skip'.`, 'danger');
                    item.action = 'skip';
                    item.status = 'skipped';
                    updateRowVisuals(index);
                    if (firstInvalidRow === null) firstInvalidRow = index;
                }
                if (!area_id) {
                    isValid = false;
                    flashMessage(`Area is required for step ${item.bi_id} (row ${index + 1}). Action set to 'skip'.`, 'danger');
                    item.action = 'skip';
                    item.status = 'skipped';
                    updateRowVisuals(index);
                    if (firstInvalidRow === null) firstInvalidRow = index;
                }
            }
            resolvedData.push({
                bi_id: item.bi_id,
                action: item.action,
                final_data: item.new_values
            });
        });

        if (!isValid) {
            if (firstInvalidRow !== null) {
                const rowEl = getRowElement(firstInvalidRow);
                if (rowEl) {
                    rowEl.scrollIntoView({
                        behavior: 'smooth',
                        block: 'center'
                    });
                }
            }
            return;
        }

        confirmImportBtn.disabled = true;
        cancelImportBtn.disabled = true;

        try {
            // --- START FIX for 404 Error ---
            const response = await fetch('/data-management/steps/finalize', {
            // --- END FIX for 404 Error ---
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify(resolvedData),
            });

            const result = await response.json();
            if (response.ok && result.success) {
                flashMessage(`Process Step import complete: Added ${result.added_count || 0}, Updated ${result.updated_count || 0}, Skipped ${result.skipped_count || 0}, Failed ${result.failed_count || 0}. Redirecting...`, 'success');
                setTimeout(() => {
                    window.location.href = '/data-management/';
                }, 2000);
            } else {
                const errorMsg = result.message || (result.messages ? result.messages.join('; ') : `Server error ${response.status}.`);
                flashMessage(`Import failed: ${errorMsg}`, 'danger');
                console.error('Finalize import failed:', result);
            }
        } catch (error) {
            flashMessage(`Network error during import finalization: ${error.message || 'Check console.'}`, 'danger');
            console.error('Fetch error:', error);
        } finally {
            confirmImportBtn.disabled = false;
            cancelImportBtn.disabled = false;
        }
    });

    cancelImportBtn.addEventListener('click', function() {
        if (confirm('Are you sure you want to cancel the import and discard all changes?')) {
            window.location.href = '/data-management/';
        }
    });

    // --- Bootstrap Modal instance and initial setup ---
    const stepDetailModalInstance = new bootstrap.Modal(stepDetailModal);

    // Initial setup of main table rows
    previewData.forEach((item, index) => {
        item.original_status = item.status; // Store original status

        if (item.status === 'new') item.action = 'add';
        else if (item.status === 'update') item.action = 'update';
        else if (item.status === 'no_change') item.action = 'skip'; // Default 'no_change' to 'skip'
        else if (item.status === 'skipped') item.action = 'skip';
        else item.action = 'skip'; // Fallback

        // Ensure new_values.area_name is populated if area_id exists
        if (item.new_values.area_id && !item.new_values.area_name) {
            const area = allAreasData.find(a => a.id === item.new_values.area_id);
            if (area) {
                item.new_values.area_name = area.name;
            }
        }
        updateRowVisuals(index);
    });

    // Map area IDs to names for display in modal
    const areaIdToNameMap = {};
    allAreasData.forEach(area => {
        areaIdToNameMap[area.id] = area.name;
    });

    // Flash message helper
    function flashMessage(message, category) {
        let flashContainer = document.querySelector('.flash-messages');
        if (!flashContainer) {
            flashContainer = document.createElement('div');
            flashContainer.classList.add('flash-messages');
            const pageContentContainer = document.querySelector('.page-content .step-injection-preview-page') || document.querySelector('.page-content');
            if (pageContentContainer) {
                pageContentContainer.prepend(flashContainer);
            } else {
                document.body.prepend(flashContainer); // Fallback
            }
        }

        const alertDiv = document.createElement('div');
        alertDiv.classList.add('alert', `alert-${category}`);
        alertDiv.textContent = message;
        flashContainer.appendChild(alertDiv);

        setTimeout(() => {
            alertDiv.remove();
            if (flashContainer.children.length === 0 && flashContainer.parentElement) {
                flashContainer.remove();
            }
        }, 7000);
    }

});