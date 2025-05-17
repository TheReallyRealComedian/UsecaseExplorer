document.addEventListener('DOMContentLoaded', function () {
    const areaSelect = document.getElementById('area_ids');
    const stepSelect = document.getElementById('step_ids');
    const fieldCheckboxes = document.querySelectorAll('input[name="fields"]');

    const areaSearchInput = document.getElementById('area_search');
    const stepSearchInput = document.getElementById('step_search');

    // Store original options for filtering
    let originalAreaOptions = [];
    if (areaSelect) {
        originalAreaOptions = Array.from(areaSelect.options).map(opt => ({
            value: opt.value,
            text: opt.text,
            element: opt.cloneNode(true) // Keep a clone of the original option element
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

    // --- Helper: Update selected counts ---
    function updateSelectedCount(selectElement) {
        // Derives the span ID from the select element's ID (e.g., 'area_ids' -> 'area_ids_selected_count')
        if (!selectElement) return;
        const displayElementId = selectElement.id + '_selected_count';
        const displayElement = document.getElementById(displayElementId);

        if (displayElement) { // Check if the span element actually exists
            const count = selectElement.selectedOptions.length;
            displayElement.textContent = count > 0 ? ` (${count} selected)` : '';
        }
    }

    // --- Filtering and Select/Clear All Logic ---
    function filterAndRebuildSelect(selectElement, originalOptions, searchTerm, areaFilterIds = null) {
        if (!selectElement) return;
        const selectedValues = Array.from(selectElement.selectedOptions).map(opt => opt.value);
        selectElement.innerHTML = ''; // Clear current options

        originalOptions.forEach(optData => {
            const matchesSearch = !searchTerm || optData.text.toLowerCase().includes(searchTerm.toLowerCase());
            let matchesArea = true;
            // If areaFilterIds is provided (meaning we are filtering steps based on areas)
            // and there are selected areas, and the current option has an areaId
            if (areaFilterIds && areaFilterIds.length > 0 && optData.areaId) {
                matchesArea = areaFilterIds.includes(optData.areaId);
            } else if (areaFilterIds && areaFilterIds.length > 0 && !optData.areaId && selectElement.id === 'step_ids') {
                // Special case for steps: if areas are selected, but a step has no areaId, it shouldn't match
                matchesArea = false;
            }


            if (matchesSearch && matchesArea) {
                const newOption = optData.element.cloneNode(true); // Use the stored clone
                if (selectedValues.includes(newOption.value)) {
                    newOption.selected = true;
                }
                selectElement.add(newOption);
            }
        });
        updateSelectedCount(selectElement); // Update count after rebuilding
    }

    if (areaSearchInput && areaSelect) {
        areaSearchInput.addEventListener('input', () => {
            filterAndRebuildSelect(areaSelect, originalAreaOptions, areaSearchInput.value);
        });
    }

    if (stepSearchInput && stepSelect) {
        stepSearchInput.addEventListener('input', () => {
            const selectedAreaIds = areaSelect ? Array.from(areaSelect.selectedOptions).map(opt => opt.value) : [];
            filterAndRebuildSelect(stepSelect, originalStepOptions, stepSearchInput.value, selectedAreaIds);
        });
    }

    if (areaSelect) {
        areaSelect.addEventListener('change', () => {
            const selectedAreaIds = Array.from(areaSelect.selectedOptions).map(opt => opt.value);
            // When areas change, re-filter steps based on new area selection AND current step search term
            filterAndRebuildSelect(stepSelect, originalStepOptions, stepSearchInput ? stepSearchInput.value : '', selectedAreaIds);
            updateSelectedCount(areaSelect); // Update area count
        });
    }
    
    if (stepSelect) { // Listener for stepSelect to update its own count when its selection changes
        stepSelect.addEventListener('change', () => {
             updateSelectedCount(stepSelect);
        });
    }

    function setupSelectControls(selectElement, selectAllButtonId, clearAllButtonId) {
        const selectAllButton = document.getElementById(selectAllButtonId);
        const clearAllButton = document.getElementById(clearAllButtonId);

        if (!selectElement || !selectAllButton || !clearAllButton) return;

        selectAllButton.addEventListener('click', () => {
            Array.from(selectElement.options).forEach(opt => {
                // Only select options that are currently visible (not filtered out by search)
                // Checking opt.style.display might be unreliable if not explicitly set.
                // A better way is to rely on the options currently in the selectElement after filtering.
                opt.selected = true;
            });
            selectElement.dispatchEvent(new Event('change')); // Trigger 'change' to update counts and dependent filters
        });

        clearAllButton.addEventListener('click', () => {
            Array.from(selectElement.options).forEach(opt => opt.selected = false);
            selectElement.dispatchEvent(new Event('change'));
        });
    }

    setupSelectControls(areaSelect, 'selectAllAreas', 'clearAllAreas');
    setupSelectControls(stepSelect, 'selectAllSteps', 'clearAllSteps');

    // Select All / Clear All for Field Checkboxes
    const selectAllFieldsBtn = document.getElementById('selectAllFields');
    const clearAllFieldsBtn = document.getElementById('clearAllFields');

    if (selectAllFieldsBtn && fieldCheckboxes.length > 0) { // check fieldCheckboxes.length
        selectAllFieldsBtn.addEventListener('click', () => fieldCheckboxes.forEach(cb => cb.checked = true));
    }
    if (clearAllFieldsBtn && fieldCheckboxes.length > 0) { // check fieldCheckboxes.length
        clearAllFieldsBtn.addEventListener('click', () => fieldCheckboxes.forEach(cb => cb.checked = false));
    }

    // Copy JSON to Clipboard
    const copyJsonButton = document.getElementById('copyJsonButton');
    const jsonDataPreview = document.getElementById('jsonDataPreview');

    if (copyJsonButton && jsonDataPreview) {
        copyJsonButton.addEventListener('click', () => {
            navigator.clipboard.writeText(jsonDataPreview.textContent)
                .then(() => {
                    const originalText = copyJsonButton.innerHTML; // Use innerHTML to preserve icon
                    copyJsonButton.innerHTML = '<i class="fas fa-check me-1"></i>Copied!';
                    copyJsonButton.classList.add('btn-success');
                    copyJsonButton.classList.remove('btn-outline-secondary');
                    setTimeout(() => {
                        copyJsonButton.innerHTML = originalText;
                        copyJsonButton.classList.remove('btn-success');
                        copyJsonButton.classList.add('btn-outline-secondary');
                    }, 2000);
                })
                .catch(err => {
                    console.error('Failed to copy JSON: ', err);
                    const originalText = copyJsonButton.innerHTML;
                    copyJsonButton.innerHTML = '<i class="fas fa-times me-1"></i>Failed!';
                    copyJsonButton.classList.add('btn-danger');
                    copyJsonButton.classList.remove('btn-outline-secondary');
                     setTimeout(() => {
                        copyJsonButton.innerHTML = originalText;
                        copyJsonButton.classList.remove('btn-danger');
                        copyJsonButton.classList.add('btn-outline-secondary');
                    }, 2000);
                    // alert('Failed to copy. Please copy manually or check browser permissions.');
                });
        });
    }

    // Initial setup calls after DOM is ready
    if (areaSelect) {
        filterAndRebuildSelect(areaSelect, originalAreaOptions, areaSearchInput ? areaSearchInput.value : ''); // Initial filter for areas based on its search
        areaSelect.dispatchEvent(new Event('change')); // This will trigger updateSelectedCount for areas AND filter steps
    }
    if (stepSelect) {
         // Steps are initially filtered by the areaSelect's 'change' event.
         // We still need to update its count based on pre-selected values (if any from server-side render).
         updateSelectedCount(stepSelect);
    }
});