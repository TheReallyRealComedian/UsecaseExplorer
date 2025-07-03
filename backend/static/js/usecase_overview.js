// backend/static/js/usecase_overview.js

document.addEventListener('DOMContentLoaded', function() {
    // --- DOM Elements from usecase_overview.html ---
    const usecaseAreaFilterTabs = document.getElementById('usecaseAreaFilterTabs');
    const useCasesTable = document.getElementById('useCasesTable');
    const usecaseFilterDropdownContainers = document.querySelectorAll('.filter-dropdown-container');
    const clearAllUsecaseFiltersBtn = document.getElementById('clearAllUsecaseFiltersBtn');

    // --- State Management ---
    // Store for active filter selections. Initialized based on the page's default view.
    let activeUsecaseFilters = {
        areaId: 'all', // From tabs
        stepName: new Set(),
        wave: new Set()
    };

    // --- Helper Functions ---

    /**
     * Gets unique values for a specific field from the global use cases data.
     * @param {string} fieldKey The key of the field to get unique values for (e.g., 'wave').
     * @returns {string[]} A sorted array of unique string values.
     */
    function getUniqueUsecaseValues(fieldKey) {
        const values = new Set();
        if (!allUsecasesDataForJS) return Array.from(values);

        allUsecasesDataForJS.forEach(uc => {
            let value = uc[fieldKey];
            if (value !== null && value !== undefined && String(value).trim() !== "") {
                values.add(String(value).trim());
            } else {
                values.add("N/A"); // Treat empty/null as "N/A" for consistent filtering
            }
        });
        return Array.from(values).sort();
    }

    /**
     * Populates a filter dropdown menu with checkboxes based on available data.
     * @param {HTMLElement} container The container element for the dropdown.
     */
    function populateUsecaseFilterDropdown(container) {
        const filterType = container.dataset.filterType;
        const optionsList = container.querySelector('.filter-options-list');
        optionsList.innerHTML = ''; // Clear existing options

        let uniqueValues;
        if (filterType === 'stepName') {
            const selectedAreaId = activeUsecaseFilters.areaId;
            let stepsForFilter = allStepsDataForJS;
            if (selectedAreaId !== 'all') {
                stepsForFilter = allStepsDataForJS.filter(step => step.area_id && step.area_id.toString() === selectedAreaId);
            }
            uniqueValues = stepsForFilter.map(step => ({
                    id: step.id.toString(),
                    name: `${step.name} (BI_ID: ${step.bi_id})`
                }))
                .sort((a, b) => a.name.localeCompare(b.name));
        } else { // Handles 'wave' and any other simple value filters
            uniqueValues = getUniqueUsecaseValues(filterType).map(val => ({
                id: val,
                name: val
            }));
        }

        const currentSelections = activeUsecaseFilters[filterType] || new Set();

        uniqueValues.forEach(valObj => {
            const checkboxId = `uc-filter-${filterType}-${valObj.id.toString().replace(/\s+/g, '-')}`;
            const listItem = document.createElement('label');
            listItem.className = 'filter-option-item d-block px-2 py-1';

            const checkbox = document.createElement('input');
            checkbox.type = 'checkbox';
            checkbox.value = valObj.id; // Use ID for steps, value string for others
            checkbox.id = checkboxId;
            checkbox.className = 'form-check-input me-2';
            checkbox.checked = currentSelections.has(valObj.id.toString());

            checkbox.addEventListener('change', () => {
                if (checkbox.checked) {
                    activeUsecaseFilters[filterType].add(valObj.id.toString());
                } else {
                    activeUsecaseFilters[filterType].delete(valObj.id.toString());
                }
                applyUsecaseFilters();
                updateUsecaseFilterIndicator(container);
            });

            listItem.appendChild(checkbox);
            listItem.appendChild(document.createTextNode(valObj.name));
            optionsList.appendChild(listItem);
        });
        updateUsecaseFilterIndicator(container);
    }

    /**
     * Updates the '(x)' indicator on a filter button to show the number of selected options.
     * @param {HTMLElement} container The dropdown container element.
     */
    function updateUsecaseFilterIndicator(container) {
        const filterType = container.dataset.filterType;
        const indicator = container.querySelector('.filter-indicator');
        const selections = activeUsecaseFilters[filterType];
        if (indicator) {
            indicator.textContent = (selections && selections.size > 0) ? `(${selections.size})` : '';
        }
    }

    /**
     * Applies all active filters to the use cases table, showing or hiding rows as needed.
     */
    function applyUsecaseFilters() {
        if (!useCasesTable) return;
        const usecaseTableRows = useCasesTable.querySelectorAll('tbody tr');

        usecaseTableRows.forEach(row => {
            const rowAreaId = row.dataset.ucAreaId;
            const rowStepId = row.dataset.ucStepId;
            const rowWave = (row.dataset.ucWave || "N/A").trim();

            let isVisible = true;

            // Area filter (from tabs)
            if (activeUsecaseFilters.areaId !== 'all' && rowAreaId !== activeUsecaseFilters.areaId) {
                isVisible = false;
            }
            // Step Name filter (from dropdown)
            if (isVisible && activeUsecaseFilters.stepName.size > 0 && !activeUsecaseFilters.stepName.has(rowStepId)) {
                isVisible = false;
            }
            // Wave filter (from dropdown)
            if (isVisible && activeUsecaseFilters.wave.size > 0 && !activeUsecaseFilters.wave.has(rowWave)) {
                isVisible = false;
            }

            row.style.display = isVisible ? '' : 'none';
        });
    }

    /**
     * Makes a table's headers clickable for sorting.
     * @param {HTMLElement} tableElement The table to make sortable.
     */
    function makeTableSortable(tableElement) {
        if (!tableElement) return;
        tableElement.querySelectorAll('th.sortable').forEach(header => {
            header.addEventListener('click', () => {
                const currentOrder = header.classList.contains('sorted-asc') ? 'asc' : (header.classList.contains('sorted-desc') ? 'desc' : 'none');
                const sortOrder = (currentOrder === 'asc') ? 'desc' : 'asc';

                // Reset other headers' sort indicators
                tableElement.querySelectorAll('th.sortable').forEach(th => th.classList.remove('sorted-asc', 'sorted-desc'));
                header.classList.add(sortOrder === 'asc' ? 'sorted-asc' : 'sorted-desc');

                const tbody = tableElement.querySelector('tbody');
                if (!tbody) return;
                const rows = Array.from(tbody.querySelectorAll('tr'));
                const colIndex = Array.from(header.parentNode.children).indexOf(header);

                rows.sort((a, b) => {
                    let valA = a.cells[colIndex].dataset.sortValue !== undefined ? a.cells[colIndex].dataset.sortValue : (a.cells[colIndex] ? a.cells[colIndex].textContent.trim() : '');
                    let valB = b.cells[colIndex].dataset.sortValue !== undefined ? b.cells[colIndex].dataset.sortValue : (b.cells[colIndex] ? b.cells[colIndex].textContent.trim() : '');

                    const numA = parseFloat(valA);
                    const numB = parseFloat(valB);

                    if (!isNaN(numA) && !isNaN(numB)) {
                        return sortOrder === 'asc' ? numA - numB : numB - numA;
                    } else {
                        return sortOrder === 'asc' ? valA.localeCompare(valB, undefined, {
                            numeric: true
                        }) : valB.localeCompare(valA, undefined, {
                            numeric: true
                        });
                    }
                });
                // Re-append sorted rows
                rows.forEach(row => tbody.appendChild(row));
            });
        });
    }

    // --- Event Listener Setup ---

    // Listener for Area Filter Tabs
    if (usecaseAreaFilterTabs) {
        usecaseAreaFilterTabs.addEventListener('click', function(event) {
            const clickedButton = event.target.closest('button.btn');
            if (!clickedButton || !clickedButton.dataset.areaId) return;

            usecaseAreaFilterTabs.querySelectorAll('button.btn').forEach(btn => btn.classList.remove('active'));
            clickedButton.classList.add('active');

            activeUsecaseFilters.areaId = clickedButton.dataset.areaId;

            // When area changes, we need to repopulate the step filter to show only relevant steps
            const stepNameFilterContainer = document.querySelector('.filter-dropdown-container[data-filter-type="stepName"]');
            if (stepNameFilterContainer) {
                activeUsecaseFilters.stepName.clear();
                populateUsecaseFilterDropdown(stepNameFilterContainer);
            }
            applyUsecaseFilters();
        });
    }

    // Setup for all filter dropdowns
    usecaseFilterDropdownContainers.forEach(container => {
        const toggleButton = container.querySelector('.filter-dropdown-toggle');
        const dropdownMenu = container.querySelector('.filter-dropdown-menu');
        const selectAllButton = container.querySelector('.select-all-action');
        const clearSelectionButton = container.querySelector('.clear-selection-action');
        const filterType = container.dataset.filterType;

        populateUsecaseFilterDropdown(container); // Initial population

        if (toggleButton && dropdownMenu) {
            toggleButton.addEventListener('click', (event) => {
                event.stopPropagation();
                // Close other dropdowns before opening this one
                usecaseFilterDropdownContainers.forEach(other => {
                    if (other !== container) other.querySelector('.filter-dropdown-menu').classList.remove('show');
                });
                dropdownMenu.classList.toggle('show');
            });
        }
        if (selectAllButton) {
            selectAllButton.addEventListener('click', () => {
                const checkboxes = container.querySelectorAll('.filter-options-list input[type="checkbox"]');
                activeUsecaseFilters[filterType].clear();
                checkboxes.forEach(cb => {
                    cb.checked = true;
                    activeUsecaseFilters[filterType].add(cb.value);
                });
                applyUsecaseFilters();
                updateUsecaseFilterIndicator(container);
            });
        }
        if (clearSelectionButton) {
            clearSelectionButton.addEventListener('click', () => {
                const checkboxes = container.querySelectorAll('.filter-options-list input[type="checkbox"]');
                checkboxes.forEach(cb => cb.checked = false);
                activeUsecaseFilters[filterType].clear();
                applyUsecaseFilters();
                updateUsecaseFilterIndicator(container);
            });
        }
    });

    // Global listener to close dropdowns when clicking outside
    document.addEventListener('click', (event) => {
        usecaseFilterDropdownContainers.forEach(container => {
            if (!container.contains(event.target)) {
                container.querySelector('.filter-dropdown-menu').classList.remove('show');
            }
        });
    });

    // Listener for the "Clear All Filters" button
    if (clearAllUsecaseFiltersBtn) {
        clearAllUsecaseFiltersBtn.addEventListener('click', () => {
            // Reset Area tabs
            if (usecaseAreaFilterTabs) {
                usecaseAreaFilterTabs.querySelectorAll('button.btn').forEach(btn => btn.classList.remove('active'));
                const allBtn = usecaseAreaFilterTabs.querySelector('button[data-area-id="all"]');
                if (allBtn) allBtn.classList.add('active');
            }
            activeUsecaseFilters.areaId = 'all';

            // Reset dropdown filters
            usecaseFilterDropdownContainers.forEach(container => {
                const filterType = container.dataset.filterType;
                activeUsecaseFilters[filterType].clear();
                populateUsecaseFilterDropdown(container); // This will uncheck all and update indicators
            });
            applyUsecaseFilters();
        });
    }

    // --- Initial Page Load Actions ---
    makeTableSortable(useCasesTable);
    applyUsecaseFilters(); // Apply once on load in case of any pre-set states (unlikely here)
});