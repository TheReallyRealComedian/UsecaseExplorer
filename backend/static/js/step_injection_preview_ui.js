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
            statusBadge.classList.remove('bg-success', 'bg-warning', 'text-dark', 'bg-secondary', 'bg-danger');
            if (item.status === 'new') statusBadge.classList.add('bg-success');
            else if (item.status === 'update') statusBadge.classList.add('bg-warning', 'text-dark');
            else if (item.status === 'no_change') statusBadge.classList.add('bg-secondary');
            else if (item.status === 'skipped') statusBadge.classList.add('bg-danger');
        }

        // Update name input in main table
        const nameInput = rowElement.querySelector('.row-final-value-input[data-field="name"]');
        if (nameInput) {
            nameInput.value = item.new_values.name || '';
            nameInput.disabled = (item.status === 'skipped' || (item.status === 'no_change' && !item.conflicts.name));
        }

        // Update area select in main table
        const areaSelect = rowElement.querySelector('.row-final-area-select[data-field="area_id"]');
        if (areaSelect) {
            areaSelect.value = item.new_values.area_id;
            areaSelect.disabled = (item.status === 'skipped' || (item.status === 'no_change' && !item.conflicts.area_id));
        }

        // Update row action radio buttons
        const actionRadios = rowElement.querySelectorAll(`.action-radio[name="action_${item.bi_id}"]`);
        actionRadios.forEach(radio => {
            radio.checked = (radio.value === item.action);
            // Disable Add/Update buttons as per business logic:
            if (item.status === 'new') { // This logic reflects initial state/business rules
                if (radio.value === 'update') radio.disabled = true; else radio.disabled = false;
            } else if (item.status === 'update' || item.status === 'no_change') {
                if (radio.value === 'add') radio.disabled = true; else radio.disabled = false;
            } else if (item.status === 'skipped') {
                radio.disabled = true; // All action radios disabled if originally skipped
            } else {
                radio.disabled = false;
            }
        });

        // Add/remove unsaved-change class
        if (item.status === 'update' || item.status === 'new') {
            rowElement.classList.add('unsaved-change'); // Always highlight if it's new/update
        } else {
            rowElement.classList.remove('unsaved-change');
        }

        // Update message area for the row
        const messageDisplay = rowElement.querySelector('.message-display');
        if (messageDisplay) {
            messageDisplay.textContent = item.messages[0] || '';
        }
    }


    // --- Modal Population Logic ---
    function populateModal(rowIndex) {
        currentModalRowIndex = rowIndex;
        const item = previewData[rowIndex];

        // Set modal header
        modalStepName.textContent = item.name;
        modalStepBiId.textContent = item.bi_id;

        // Populate Area select in modal
        modalAreaSelect.value = item.new_values.area_id;
        modalAreaDbValue.textContent = item.db_data.area_name || 'N/A';
        modalAreaJsonValue.textContent = item.area_name || 'N/A';
        modalAreaSelect.disabled = (item.action === 'skip' || (item.status === 'no_change' && !item.conflicts.area_id));


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
                // Conflict: Show both DB and JSON values, enable radios/manual input
                fieldGroup.classList.add('is-conflict');
                conflictMessage.style.display = 'block';

                const dbValue = item.conflicts[fieldKey].old_value || '';
                const jsonValue = item.conflicts[fieldKey].new_value || '';
                const preselectedFinalValue = item.new_values[fieldKey];

                dbContentPre.textContent = (dbValue === "N/A (Empty)") ? 'N/A' : dbValue;
                jsonContentPre.textContent = (jsonValue === "N/A (Empty)") ? 'N/A' : jsonValue;

                // Set manual input to the current new_values (which might be a resolution or old/new value)
                manualInput.value = preselectedFinalValue !== null ? preselectedFinalValue : '';

                // Select the radio that matches the current 'new_values'
                if (preselectedFinalValue === dbValue) {
                    if (radioDb) radioDb.checked = true;
                } else if (preselectedFinalValue === jsonValue) {
                    if (radioJson) radioJson.checked = true;
                } else {
                    // It's a manual override, or a "null" that doesn't match an "N/A (Empty)" option
                    if (radioManual) radioManual.checked = true;
                }
            } else if (item.status === 'new') {
                // New item: Only JSON value (which is also the db_value and new_value)
                fieldGroup.classList.add('is-new-field');
                dbContentPre.textContent = 'N/A (No existing DB value)';
                jsonContentPre.textContent = item.json_data[fieldKey] || 'N/A';
                manualInput.value = item.new_values[fieldKey] !== null ? item.new_values[fieldKey] : '';
                
                // No radios needed for new fields, as there's no conflict choice
                if (radioDb) radioDb.style.display = 'none'; // Hide DB radio
                if (radioJson) radioJson.style.display = 'none'; // Hide JSON radio
                if (radioManual) radioManual.style.display = 'none'; // Hide Manual radio
            } else if (item.status === 'no_change' && !item.conflicts[fieldKey]) {
                // No change for this field: Show DB value, disable manual input
                fieldGroup.classList.add('is-no-change');
                dbContentPre.textContent = item.db_data[fieldKey] || 'N/A';
                jsonContentPre.textContent = item.json_data[fieldKey] || 'N/A'; // Show JSON too for context
                manualInput.value = item.db_data[fieldKey] !== null ? item.db_data[fieldKey] : '';
                manualInput.disabled = true; // Cannot edit if no change
                
                if (radioDb) radioDb.style.display = 'none'; // Hide DB radio
                if (radioJson) radioJson.style.display = 'none'; // Hide JSON radio
                if (radioManual) radioManual.style.display = 'none'; // Hide Manual radio
            } else { // Fallback for fields not explicitly conflicting, but present in new_values
                dbContentPre.textContent = item.db_data[fieldKey] || 'N/A';
                jsonContentPre.textContent = item.json_data[fieldKey] || 'N/A';
                manualInput.value = item.new_values[fieldKey] !== null ? item.new_values[fieldKey] : '';

                if (radioDb) radioDb.style.display = 'none'; // Hide DB radio
                if (radioJson) radioJson.style.display = 'none'; // Hide JSON radio
                if (radioManual) radioManual.style.display = 'none'; // Hide Manual radio
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
                manualInput.value = item.conflicts[fieldKey].old_value || '';
            } else if (target.value === 'json') {
                manualInput.value = item.conflicts[fieldKey].new_value || '';
            } else if (target.value === 'manual') {
                // Do nothing, user will type
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
            // If user manually edits, default to manual choice if it exists
            const manualRadio = modalFieldsContainer.querySelector(`#modal_manual_choice_${fieldKey}`);
            if (manualRadio && !manualRadio.disabled) {
                manualRadio.checked = true;
            }
        }
    });

    // --- Save Modal Changes ---
    saveModalChangesBtn.addEventListener('click', function() {
        const item = previewData[currentModalRowIndex];

        // Update name in new_values (from main table, but also for consistency in modal data)
        const rowElement = getRowElement(currentModalRowIndex);
        const nameInput = rowElement.querySelector('.row-final-value-input[data-field="name"]');
        if (nameInput) {
            item.new_values.name = nameInput.value.trim() === '' ? null : nameInput.value.trim();
        }

        // Update Area ID from modal select
        const newAreaId = parseInt(modalAreaSelect.value);
        if (item.new_values.area_id !== newAreaId) {
            item.new_values.area_id = newAreaId;
            // Update area name in item.new_values for display consistency
            const selectedArea = allAreasData.find(area => area.id === newAreaId);
            item.new_values.area_name = selectedArea ? selectedArea.name : 'N/A';
            // Mark as update if action was no_change (since area changed)
            if (item.action === 'no_change') item.action = 'update';
        }

        // Collect values for other fields from modal
        for (const fieldKey in stepDetailFieldsConfig) {
            const manualInput = modalFieldsContainer.querySelector(`#modal_manual_input_${fieldKey}`);
            if (manualInput && !manualInput.disabled) { // Only read from enabled inputs
                const newValue = manualInput.value.trim() === '' ? null : manualInput.value.trim();
                if (item.new_values[fieldKey] !== newValue) {
                    item.new_values[fieldKey] = newValue;
                     // If an action was 'no_change' but a field was manually updated, switch to 'update'
                    if (item.action === 'no_change') item.action = 'update';
                }
            }
        }

        // If the item was originally 'no_change' but now has actual changes in `new_values`
        // compared to `db_data` (excluding timestamp fields, etc.), promote its status to 'update'.
        // This is a more robust check for 'no_change' items.
        if (item.status === 'no_change' && item.action === 'no_change') { // Check if it's still 'no_change' in action
            let actuallyChanged = false;
            for (const fieldKey in stepDetailFieldsConfig) {
                const newValue = item.new_values[fieldKey];
                const dbValue = item.db_data[fieldKey] || null; // Treat empty string as null from DB
                if (newValue !== dbValue) {
                    actuallyChanged = true;
                    break;
                }
            }
            if (item.new_values.name !== (item.db_data.name || null)) actuallyChanged = true;
            if (item.new_values.area_id !== (item.db_data.area_id || null)) actuallyChanged = true;

            if (actuallyChanged) {
                item.action = 'update'; // Promote to update
            }
        }


        // Update main table row visuals
        updateRowVisuals(currentModalRowIndex);

        // Close modal
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
                newValue = parseInt(newValue);
            }

            if (item.new_values[field] !== newValue) {
                item.new_values[field] = newValue;
                // If the item was originally 'no_change' but now a field has changed,
                // we should promote its action to 'update'.
                if (item.action === 'no_change') {
                    item.action = 'update';
                }
                updateRowVisuals(rowIndex); // Update visuals immediately
            }
        }
    });

    // Event listener for row-level Action radio buttons
    previewTableBody.addEventListener('change', function(event) {
        const target = event.target;
        if (target.classList.contains('action-radio')) {
            const rowIndex = parseInt(target.dataset.rowIndex);
            const item = previewData[rowIndex];
            item.action = target.value;
            updateRowVisuals(rowIndex); // Update visuals immediately
        }
    });

    // --- Global Action Buttons (Confirm/Cancel Import) ---

    confirmImportBtn.addEventListener('click', async function() {
        if (!confirm('Are you sure you want to finalize the import with the displayed changes?')) {
            return;
        }

        const resolvedData = [];
        let isValid = true;
        let firstInvalidRow = null;

        previewData.forEach((item, index) => {
            if (item.action === 'add' || item.action === 'update') {
                // Re-validate critical fields before sending
                const name = item.new_values.name;
                const area_id = item.new_values.area_id;

                if (!name) {
                    isValid = false;
                    flashMessage(`Name is required for step ${item.bi_id}.`, 'danger');
                    if (firstInvalidRow === null) firstInvalidRow = index;
                }
                if (!area_id) {
                    isValid = false;
                    flashMessage(`Area is required for step ${item.bi_id}.`, 'danger');
                    if (firstInvalidRow === null) firstInvalidRow = index;
                }
            }
            resolvedData.push({
                bi_id: item.bi_id,
                action: item.action,
                final_data: item.new_values // new_values holds the current resolved state
            });
        });

        if (!isValid) {
            // Scroll to the first invalid row if detected
            if (firstInvalidRow !== null) {
                getRowElement(firstInvalidRow).scrollIntoView({ behavior: 'smooth', block: 'center' });
            }
            return;
        }

        confirmImportBtn.disabled = true;
        cancelImportBtn.disabled = true;

        try {
            const response = await fetch('/injection/steps/finalize', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify(resolvedData),
            });

            const result = await response.json();
            if (result.success) {
                flashMessage(`Process Step import complete: Added ${result.added_count}, Updated ${result.updated_count}, Failed ${result.failed_count}. Redirecting...`, 'success');
                setTimeout(() => { window.location.href = '/injection'; }, 1500);
            } else {
                flashMessage(`Import failed: ${result.message || JSON.stringify(result.messages)}`, 'danger');
                console.error('Finalize import failed:', result.messages);
            }
        } catch (error) {
            flashMessage('Network error during import finalization.', 'danger');
            console.error('Fetch error:', error);
        } finally {
            confirmImportBtn.disabled = false;
            cancelImportBtn.disabled = false;
        }
    });

    cancelImportBtn.addEventListener('click', function() {
        if (confirm('Are you sure you want to cancel the import and discard all changes?')) {
            window.location.href = '/injection'; // Redirect back to the main injection page
        }
    });

    // --- Bootstrap Modal instance and initial setup ---
    const stepDetailModalInstance = new bootstrap.Modal(stepDetailModal);

    // Initial setup of main table rows
    previewData.forEach((item, index) => {
        updateRowVisuals(index);
    });

    // Map area IDs to names for display in modal
    const areaIdToNameMap = {};
    allAreasData.forEach(area => {
        areaIdToNameMap[area.id] = area.name;
    });

    // Flash message helper (for JS-generated messages)
    function flashMessage(message, category) {
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

});