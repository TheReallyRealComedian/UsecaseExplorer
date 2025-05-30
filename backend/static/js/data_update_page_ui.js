// backend/static/js/data_update_page_ui.js

document.addEventListener('DOMContentLoaded', function() {

    // --- References to HTML Elements ---
    // Process Steps elements
    const selectedStepsSelect = document.getElementById('selected_update_steps');
    const stepFilterAreaInput = document.getElementById('stepFilterArea');
    const stepFilterStepInput = document.getElementById('stepFilterStep');

    // Use Cases elements
    const selectedUsecasesSelect = document.getElementById('selected_update_usecases');
    const usecaseFilterAreaInput = document.getElementById('usecaseFilterArea');
    const usecaseFilterStepInput = document.getElementById('usecaseFilterStep');
    const usecaseFilterUsecaseInput = document.getElementById('usecaseFilterUsecase');

    // Datalist elements
    const areaNamesDatalist = document.getElementById('areaNamesDatalist');
    const stepNamesDatalist = document.getElementById('stepNamesDatalist');
    const usecaseNamesDatalist = document.getElementById('usecaseNamesDatalist');


    // --- Store Original Options and Datalist Data ---
    // It's crucial to store a copy of the *original* options from the server
    // so that filtering always works on the complete dataset.
    // Store lowercase names for efficient case-insensitive search.
    let originalStepOptions = [];
    if (selectedStepsSelect) {
        originalStepOptions = Array.from(selectedStepsSelect.options).map(opt => ({
            value: opt.value,
            fullText: opt.textContent, // Store original text for re-display
            areaId: opt.dataset.areaId, // Keep IDs for direct parent matching
            areaName: opt.dataset.areaName ? opt.dataset.areaName.toLowerCase() : '',
            stepName: opt.dataset.stepName ? opt.dataset.stepName.toLowerCase() : ''
        }));
    }

    let originalUsecaseOptions = [];
    if (selectedUsecasesSelect) {
        originalUsecaseOptions = Array.from(selectedUsecasesSelect.options).map(opt => ({
            value: opt.value,
            fullText: opt.textContent, // Store original text for re-display
            areaId: opt.dataset.areaId, // Keep IDs for direct parent matching
            areaName: opt.dataset.areaName ? opt.dataset.areaName.toLowerCase() : '',
            stepId: opt.dataset.stepId, // Keep IDs for direct parent matching
            stepName: opt.dataset.stepName ? opt.dataset.stepName.toLowerCase() : '',
            ucName: opt.dataset.ucName ? opt.dataset.ucName.toLowerCase() : ''
        }));
    }

    // Store original full set of names for datalists.
    // These are *all* possible names, before any filtering.
    let originalAreaNames = [];
    if (areaNamesDatalist) {
        originalAreaNames = Array.from(areaNamesDatalist.options).map(opt => opt.value.toLowerCase());
    }
    let originalStepNames = [];
    if (stepNamesDatalist) {
        originalStepNames = Array.from(stepNamesDatalist.options).map(opt => opt.value.toLowerCase());
    }
    let originalUsecaseNames = [];
    if (usecaseNamesDatalist) {
        originalUsecaseNames = Array.from(usecaseNamesDatalist.options).map(opt => opt.value.toLowerCase());
    }


    // --- Helper for Datalist Population ---
    /**
     * Clears and repopulates a datalist element with new options.
     * @param {HTMLElement} datalistElement The <datalist> DOM element.
     * @param {Array<string>} newOptionsArray An array of string values for the new <option>s.
     */
    function updateDatalistOptions(datalistElement, newOptionsArray) {
        if (!datalistElement) return;
        datalistElement.innerHTML = ''; // Clear existing options
        newOptionsArray.forEach(name => {
            const option = document.createElement('option');
            option.value = name;
            datalistElement.appendChild(option);
        });
    }

    // --- Core Filtering and Rendering Function for <select> elements ---
    /**
     * Filters and re-renders a <select> element.
     * @param {HTMLSelectElement} selectElement The <select> element to filter.
     * @param {Array<Object>} originalData The full array of original option data for this select.
     * @param {Object} filterTerms Object with current filter terms (e.g., {area: '...', step: '...', usecase: '...'}).
     * @param {Array<string>|null} parentVisibleIds Optional: Array of IDs of visible parent elements (e.g., visible step IDs for use cases).
     * @param {string|null} parentIdKey Optional: Key in optData that refers to the parent ID (e.g., 'stepId' for use cases).
     */
    function filterAndRenderSelect(selectElement, originalData, filterTerms, parentVisibleIds = null, parentIdKey = null) {
        if (!selectElement || !originalData) return;

        const currentSelectedValues = Array.from(selectElement.selectedOptions).map(opt => opt.value);
        selectElement.innerHTML = ''; // Clear all current options

        const visibleOptions = originalData.filter(optData => {
            let isVisible = true;

            // Apply direct filters specific to the select's type
            if (selectElement === selectedStepsSelect) {
                if (filterTerms.area && !optData.areaName.includes(filterTerms.area)) isVisible = false;
                if (filterTerms.step && !optData.stepName.includes(filterTerms.step)) isVisible = false;
            } else if (selectElement === selectedUsecasesSelect) {
                if (filterTerms.area && !optData.areaName.includes(filterTerms.area)) isVisible = false;
                if (filterTerms.step && !optData.stepName.includes(filterTerms.step)) isVisible = false;
                if (filterTerms.usecase && !optData.ucName.includes(filterTerms.usecase)) isVisible = false;

                // Apply hierarchical parent filtering if applicable
                // Check if the option's parent ID is in the list of visible parent IDs
                if (parentVisibleIds && parentIdKey && optData[parentIdKey]) {
                    if (!parentVisibleIds.includes(String(optData[parentIdKey]))) {
                        isVisible = false;
                    }
                }
            }
            return isVisible;
        });

        visibleOptions.forEach(optData => {
            const newOption = document.createElement('option');
            newOption.value = optData.value;
            newOption.textContent = optData.fullText; // Use the stored original full text

            // Re-add all original data attributes
            // This is important because originalOptions map has flat data attributes
            for (const key in optData) {
                if (key !== 'value' && key !== 'fullText') { // Exclude internal JS properties
                    newOption.dataset[key] = optData[key];
                }
            }

            // Restore selection state
            if (currentSelectedValues.includes(newOption.value)) {
                newOption.selected = true;
            }
            selectElement.add(newOption);
        });

        // Return the IDs of the options that were just rendered (i.e., are visible)
        return visibleOptions.map(opt => opt.value);
    }

    // --- Master Function to Orchestrate All Filtering (Selects and Datalists) ---
    function updateAllFilters() {
        // 1. Get current filter terms from all inputs
        const stepFilterTerms = {
            area: stepFilterAreaInput.value.toLowerCase().trim(),
            step: stepFilterStepInput.value.toLowerCase().trim()
        };
        const usecaseFilterTerms = {
            area: usecaseFilterAreaInput.value.toLowerCase().trim(),
            step: usecaseFilterStepInput.value.toLowerCase().trim(),
            usecase: usecaseFilterUsecaseInput.value.toLowerCase().trim()
        };

        // 2. Filter Process Steps <select> first
        const currentlyVisibleStepIds = filterAndRenderSelect(selectedStepsSelect, originalStepOptions, stepFilterTerms);

        // 3. Filter Use Cases <select>, passing the visible step IDs as a parent filter
        const currentlyVisibleUsecaseIds = filterAndRenderSelect(selectedUsecasesSelect, originalUsecaseOptions, usecaseFilterTerms, currentlyVisibleStepIds, 'stepId');


        // --- Datalist Updates (Cascading Autocomplete) ---

        // Datalist for Step Names: Depends on Area Filter
        const filteredStepNamesForDatalist = new Set();
        originalStepOptions.forEach(optData => {
            if (stepFilterTerms.area === '' || optData.areaName.includes(stepFilterTerms.area)) {
                filteredStepNamesForDatalist.add(optData.stepName);
            }
        });
        updateDatalistOptions(stepNamesDatalist, Array.from(filteredStepNamesForDatalist).sort());

        // Datalist for Area Names (for Use Case filter): Always all areas, unless filtered directly
        // No change here, as Area Names datalist doesn't cascade FROM anything above it in this hierarchy.
        // It's already populated with all names statically from Flask, which is fine.

        // Datalist for Use Case Names: Depends on Area and Step Filters
        const filteredUsecaseNamesForDatalist = new Set();
        originalUsecaseOptions.forEach(optData => {
            let isVisibleForDatalist = true;
            if (usecaseFilterTerms.area && !optData.areaName.includes(usecaseFilterTerms.area)) isVisibleForDatalist = false;
            if (usecaseFilterTerms.step && !optData.stepName.includes(usecaseFilterTerms.step)) isVisibleForDatalist = false;
            
            if (isVisibleForDatalist) {
                filteredUsecaseNamesForDatalist.add(optData.ucName);
            }
        });
        updateDatalistOptions(usecaseNamesDatalist, Array.from(filteredUsecaseNamesForDatalist).sort());
    }


    // --- Event Listeners for Filter Inputs ---
    // Attach a single event listener to each filter input that triggers `updateAllFilters`
    if (stepFilterAreaInput) stepFilterAreaInput.addEventListener('input', updateAllFilters);
    if (stepFilterStepInput) stepFilterStepInput.addEventListener('input', updateAllFilters);
    if (usecaseFilterAreaInput) usecaseFilterAreaInput.addEventListener('input', updateAllFilters);
    if (usecaseFilterStepInput) usecaseFilterStepInput.addEventListener('input', updateAllFilters);
    if (usecaseFilterUsecaseInput) usecaseFilterUsecaseInput.addEventListener('input', updateAllFilters);


    // --- Initial Filter Application on Page Load ---
    // Call updateAllFilters once on page load to set the initial state correctly.
    // This also rebuilds the select lists with correct data attributes and selection states.
    updateAllFilters();

}); // End of DOMContentLoaded