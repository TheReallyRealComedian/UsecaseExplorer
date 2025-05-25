// backend/static/js/ui.js
document.addEventListener('DOMContentLoaded', function () {
    const areaSelect = document.getElementById('area_ids');
    const stepSelect = document.getElementById('step_ids');
    const usecaseSelect = document.getElementById('usecase_ids'); // NEW

    const stepFieldCheckboxes = document.querySelectorAll('input[name="step_fields"]'); // RENAMED
    const usecaseFieldCheckboxes = document.querySelectorAll('input[name="usecase_fields"]'); // NEW

    const areaSearchInput = document.getElementById('area_search');
    const stepSearchInput = document.getElementById('step_search');
    const usecaseSearchInput = document.getElementById('usecase_search'); // NEW

    // Store original options for filtering
    let originalAreaOptions = [];
    if (areaSelect) {
        originalAreaOptions = Array.from(areaSelect.options).map(opt => ({
            value: opt.value,
            text: opt.text,
            element: opt.cloneNode(true)
        }));
    }

    let originalStepOptions = [];
    if (stepSelect) {
        originalStepOptions = Array.from(stepSelect.options).map(opt => ({
            value: opt.value,
            text: opt.text,
            areaId: opt.dataset.areaId || '',
            element: opt.cloneNode(true)
        }));
    }

    let originalUsecaseOptions = []; // NEW
    if (usecaseSelect) {
        originalUsecaseOptions = Array.from(usecaseSelect.options).map(opt => ({
            value: opt.value,
            text: opt.text,
            areaId: opt.dataset.areaId || '',
            stepId: opt.dataset.stepId || '',
            element: opt.cloneNode(true)
        }));
    }

    // --- Helper: Update selected counts ---
    function updateSelectedCount(selectElement) {
        if (!selectElement) return;
        const displayElementId = selectElement.id + '_selected_count';
        const displayElement = document.getElementById(displayElementId);

        if (displayElement) {
            const count = selectElement.selectedOptions.length;
            displayElement.textContent = count > 0 ? ` (${count} selected)` : '';
        }
    }

    // --- Filtering and Rebuilding Selects ---
    function filterAndRebuildSelect(selectElement, originalOptions, searchTerm, areaFilterIds = null, stepFilterIds = null) {
        if (!selectElement) return;
        const selectedValues = Array.from(selectElement.selectedOptions).map(opt => opt.value);
        selectElement.innerHTML = ''; // Clear current options

        originalOptions.forEach(optData => {
            const matchesSearch = !searchTerm || optData.text.toLowerCase().includes(searchTerm.toLowerCase());
            let matchesArea = true;
            let matchesStep = true; // NEW

            // Apply area filter if provided
            if (areaFilterIds && areaFilterIds.length > 0) {
                if (optData.areaId) {
                    matchesArea = areaFilterIds.includes(optData.areaId);
                } else if (selectElement.id === 'step_ids' || selectElement.id === 'usecase_ids') {
                    matchesArea = false;
                }
            }

            // NEW: Apply step filter if provided (only for usecases)
            if (stepFilterIds && stepFilterIds.length > 0 && selectElement.id === 'usecase_ids') {
                if (optData.stepId) {
                    matchesStep = stepFilterIds.includes(optData.stepId);
                } else {
                    matchesStep = false;
                }
            }

            if (matchesSearch && matchesArea && matchesStep) {
                const newOption = optData.element.cloneNode(true);
                if (selectedValues.includes(newOption.value)) {
                    newOption.selected = true;
                }
                selectElement.add(newOption);
            }
        });
        updateSelectedCount(selectElement); // Update count after rebuilding
    }

    // --- Event Listeners for Filtering ---
    if (areaSearchInput && areaSelect) {
        areaSearchInput.addEventListener('input', () => {
            filterAndRebuildSelect(areaSelect, originalAreaOptions, areaSearchInput.value);
            const selectedAreaIds = Array.from(areaSelect.selectedOptions).map(opt => opt.value);
            filterAndRebuildSelect(stepSelect, originalStepOptions, stepSearchInput.value, selectedAreaIds);
            const selectedStepIds = Array.from(stepSelect.selectedOptions).map(opt => opt.value);
            filterAndRebuildSelect(usecaseSelect, originalUsecaseOptions, usecaseSearchInput.value, selectedAreaIds, selectedStepIds); // NEW
        });
    }

    if (stepSearchInput && stepSelect) {
        stepSearchInput.addEventListener('input', () => {
            const selectedAreaIds = areaSelect ? Array.from(areaSelect.selectedOptions).map(opt => opt.value) : [];
            filterAndRebuildSelect(stepSelect, originalStepOptions, stepSearchInput.value, selectedAreaIds);
            const selectedStepIds = Array.from(stepSelect.selectedOptions).map(opt => opt.value);
            filterAndRebuildSelect(usecaseSelect, originalUsecaseOptions, usecaseSearchInput.value, selectedAreaIds, selectedStepIds); // NEW
        });
    }

    if (usecaseSearchInput && usecaseSelect) { // NEW
        usecaseSearchInput.addEventListener('input', () => {
            const selectedAreaIds = areaSelect ? Array.from(areaSelect.selectedOptions).map(opt => opt.value) : [];
            const selectedStepIds = stepSelect ? Array.from(stepSelect.selectedOptions).map(opt => opt.value) : [];
            filterAndRebuildSelect(usecaseSelect, originalUsecaseOptions, usecaseSearchInput.value, selectedAreaIds, selectedStepIds);
        });
    }

    if (areaSelect) {
        areaSelect.addEventListener('change', () => {
            const selectedAreaIds = Array.from(areaSelect.selectedOptions).map(opt => opt.value);
            filterAndRebuildSelect(stepSelect, originalStepOptions, stepSearchInput ? stepSearchInput.value : '', selectedAreaIds);
            const selectedStepIds = Array.from(stepSelect.selectedOptions).map(opt => opt.value);
            filterAndRebuildSelect(usecaseSelect, originalUsecaseOptions, usecaseSearchInput ? usecaseSearchInput.value : '', selectedAreaIds, selectedStepIds); // NEW
            updateSelectedCount(areaSelect);
        });
    }
    
    if (stepSelect) {
        stepSelect.addEventListener('change', () => {
            const selectedAreaIds = areaSelect ? Array.from(areaSelect.selectedOptions).map(opt => opt.value) : [];
            const selectedStepIds = Array.from(stepSelect.selectedOptions).map(opt => opt.value);
            filterAndRebuildSelect(usecaseSelect, originalUsecaseOptions, usecaseSearchInput ? usecaseSearchInput.value : '', selectedAreaIds, selectedStepIds); // NEW
            updateSelectedCount(stepSelect);
        });
    }

    if (usecaseSelect) { // NEW
        usecaseSelect.addEventListener('change', () => {
             updateSelectedCount(usecaseSelect);
        });
    }

    function setupSelectControls(selectElement, selectAllButtonId, clearAllButtonId) {
        const selectAllButton = document.getElementById(selectAllButtonId);
        const clearAllButton = document.getElementById(clearAllButtonId);

        if (!selectElement || !selectAllButton || !clearAllButton) return;

        selectAllButton.addEventListener('click', () => {
            Array.from(selectElement.options).forEach(opt => {
                opt.selected = true;
            });
            selectElement.dispatchEvent(new Event('change'));
        });

        clearAllButton.addEventListener('click', () => {
            Array.from(selectElement.options).forEach(opt => opt.selected = false);
            selectElement.dispatchEvent(new Event('change'));
        });
    }

    setupSelectControls(areaSelect, 'selectAllAreas', 'clearAllAreas');
    setupSelectControls(stepSelect, 'selectAllSteps', 'clearAllSteps');
    setupSelectControls(usecaseSelect, 'selectAllUsecases', 'clearAllUsecases'); // NEW

    // Select All / Clear All for Field Checkboxes
    const selectAllStepFieldsBtn = document.getElementById('selectAllStepFields'); // RENAMED
    const clearAllStepFieldsBtn = document.getElementById('clearAllStepFields'); // RENAMED
    const selectAllUsecaseFieldsBtn = document.getElementById('selectAllUsecaseFields'); // NEW
    const clearAllUsecaseFieldsBtn = document.getElementById('clearAllUsecaseFields'); // NEW

    if (selectAllStepFieldsBtn && stepFieldCheckboxes.length > 0) {
        selectAllStepFieldsBtn.addEventListener('click', () => stepFieldCheckboxes.forEach(cb => cb.checked = true));
    }
    if (clearAllStepFieldsBtn && stepFieldCheckboxes.length > 0) {
        clearAllStepFieldsBtn.addEventListener('click', () => stepFieldCheckboxes.forEach(cb => cb.checked = false));
    }

    if (selectAllUsecaseFieldsBtn && usecaseFieldCheckboxes.length > 0) { // NEW
        selectAllUsecaseFieldsBtn.addEventListener('click', () => usecaseFieldCheckboxes.forEach(cb => cb.checked = true));
    }
    if (clearAllUsecaseFieldsBtn && usecaseFieldCheckboxes.length > 0) { // NEW
        clearAllUsecaseFieldsBtn.addEventListener('click', () => usecaseFieldCheckboxes.forEach(cb => cb.checked = false));
    }

    // JSON Preview Control
    const copyJsonButton = document.getElementById('copyJsonButton');
    const jsonDataPreview = document.getElementById('jsonDataPreview');
    const jsonPreviewContainer = document.getElementById('jsonPreviewContainer');
    const toggleJsonPreviewButton = document.getElementById('toggleJsonPreview');
    const tokenCountDisplay = document.getElementById('tokenCountDisplay');

    // Determine if there is actual data to display/copy
    const hasData = jsonDataPreview && 
                    jsonDataPreview.textContent.trim() !== '{"process_steps": [], "use_cases": []}' && // Check for empty JSON dict
                    jsonDataPreview.textContent.trim() !== 'null' && 
                    jsonDataPreview.textContent.trim() !== '';

    // Conditionally show/hide buttons and token count based on whether data exists
    if (copyJsonButton) copyJsonButton.style.display = hasData ? 'inline-block' : 'none';
    if (toggleJsonPreviewButton) toggleJsonPreviewButton.style.display = hasData ? 'inline-block' : 'none';
    if (tokenCountDisplay) tokenCountDisplay.style.display = hasData ? 'block' : 'none';

    // Toggle JSON Preview visibility
    if (toggleJsonPreviewButton && jsonPreviewContainer && hasData) {
        toggleJsonPreviewButton.addEventListener('click', () => {
            const isHidden = jsonPreviewContainer.style.display === 'none';
            if (isHidden) {
                jsonPreviewContainer.style.display = 'block';
                toggleJsonPreviewButton.innerHTML = '<i class="fas fa-eye-slash me-1"></i>Hide JSON';
            } else {
                jsonPreviewContainer.style.display = 'none';
                toggleJsonPreviewButton.innerHTML = '<i class="fas fa-eye me-1"></i>Show JSON';
            }
        });
    }

    // Copy JSON to Clipboard
    if (copyJsonButton && jsonDataPreview && hasData) {
        copyJsonButton.addEventListener('click', () => {
            navigator.clipboard.writeText(jsonDataPreview.textContent)
                .then(() => {
                    const originalHTML = copyJsonButton.innerHTML;
                    copyJsonButton.innerHTML = '<i class="fas fa-check me-1"></i>Copied!';
                    copyJsonButton.classList.remove('btn-outline-secondary', 'btn-danger');
                    copyJsonButton.classList.add('btn-success');
                    setTimeout(() => {
                        copyJsonButton.innerHTML = originalHTML;
                        copyJsonButton.classList.remove('btn-success');
                        copyJsonButton.classList.add('btn-outline-secondary');
                    }, 2000);
                })
                .catch(err => {
                    console.error('Failed to copy JSON: ', err);
                    const originalHTML = copyJsonButton.innerHTML;
                    copyJsonButton.innerHTML = '<i class="fas fa-times me-1"></i>Failed!';
                    copyJsonButton.classList.remove('btn-outline-secondary', 'btn-success');
                    copyJsonButton.classList.add('btn-danger');
                     setTimeout(() => {
                        copyJsonButton.innerHTML = originalHTML;
                        copyJsonButton.classList.remove('btn-danger');
                        copyJsonButton.classList.add('btn-outline-secondary');
                    }, 2000);
                });
        });
    }

    // Initial setup calls for selected counts after DOM is ready
    if (areaSelect) {
        // Trigger change for areas to also filter steps initially based on pre-selected areas
        filterAndRebuildSelect(areaSelect, originalAreaOptions, areaSearchInput ? areaSearchInput.value : '');
        areaSelect.dispatchEvent(new Event('change')); 
    }
    // Update step count. The step options are already filtered by the areaSelect.dispatchEvent('change') above.
    if (stepSelect) { 
        updateSelectedCount(stepSelect);
    }
    // NEW: Update usecase count
    if (usecaseSelect) {
        updateSelectedCount(usecaseSelect);
    }
});