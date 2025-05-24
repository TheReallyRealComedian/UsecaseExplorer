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
        if (!selectElement) return;
        const displayElementId = selectElement.id + '_selected_count';
        const displayElement = document.getElementById(displayElementId);

        if (displayElement) {
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
            if (areaFilterIds && areaFilterIds.length > 0 && optData.areaId) {
                matchesArea = areaFilterIds.includes(optData.areaId);
            } else if (areaFilterIds && areaFilterIds.length > 0 && !optData.areaId && selectElement.id === 'step_ids') {
                matchesArea = false;
            }

            if (matchesSearch && matchesArea) {
                const newOption = optData.element.cloneNode(true);
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
            filterAndRebuildSelect(stepSelect, originalStepOptions, stepSearchInput ? stepSearchInput.value : '', selectedAreaIds);
        });
    }

    if (areaSelect) {
        areaSelect.addEventListener('change', () => {
            const selectedAreaIds = Array.from(areaSelect.selectedOptions).map(opt => opt.value);
            filterAndRebuildSelect(stepSelect, originalStepOptions, stepSearchInput ? stepSearchInput.value : '', selectedAreaIds);
            updateSelectedCount(areaSelect);
        });
    }
    
    if (stepSelect) {
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

    // Select All / Clear All for Field Checkboxes
    const selectAllFieldsBtn = document.getElementById('selectAllFields');
    const clearAllFieldsBtn = document.getElementById('clearAllFields');

    if (selectAllFieldsBtn && fieldCheckboxes.length > 0) {
        selectAllFieldsBtn.addEventListener('click', () => fieldCheckboxes.forEach(cb => cb.checked = true));
    }
    if (clearAllFieldsBtn && fieldCheckboxes.length > 0) {
        clearAllFieldsBtn.addEventListener('click', () => fieldCheckboxes.forEach(cb => cb.checked = false));
    }

    // JSON Preview Control
    const copyJsonButton = document.getElementById('copyJsonButton');
    const jsonDataPreview = document.getElementById('jsonDataPreview'); // The <pre> tag
    const jsonPreviewContainer = document.getElementById('jsonPreviewContainer'); // The wrapping div
    const toggleJsonPreviewButton = document.getElementById('toggleJsonPreview');
    const tokenCountDisplay = document.getElementById('tokenCountDisplay'); // The token count paragraph

    // Determine if there is actual data to display/copy
    const hasData = jsonDataPreview && 
                    jsonDataPreview.textContent.trim() !== '[]' && 
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
});