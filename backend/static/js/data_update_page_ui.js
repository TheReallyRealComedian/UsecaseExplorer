// backend/static/js/data_update_page_ui.js

document.addEventListener('DOMContentLoaded', function() {
    // --- Form Submission Logs (Keep these) ---
    // ... (existing form submission logs remain unchanged) ...
    const databaseImportForm = document.getElementById('databaseImportForm');
    if (databaseImportForm) {
        databaseImportForm.onsubmit = function() { console.log('Database import form submitted'); return true; };
    }
    const stepUploadForm = document.getElementById('stepUploadForm');
    if (stepUploadForm) {
         stepUploadForm.onsubmit = function() { console.log('Step upload form submitted'); return true; };
    }
    const usecaseUploadForm = document.getElementById('usecaseUploadForm');
    if(usecaseUploadForm) {
        usecaseUploadForm.onsubmit = function() { console.log('Use Case upload form submitted'); return true; };
    }
    const psPsRelevanceForm = document.getElementById('psPsRelevanceForm');
    if (psPsRelevanceForm) {
        psPsRelevanceForm.onsubmit = function() { console.log('PS-PS Relevance upload form submitted'); return true; };
    }
    const usecaseAreaRelevanceForm = document.getElementById('usecaseAreaRelevanceForm');
    if (usecaseAreaRelevanceForm) {
        usecaseAreaRelevanceForm.onsubmit = function() { console.log('UC-Area Relevance upload form submitted'); return true; };
    }
    const usecaseStepRelevanceForm = document.getElementById('usecaseStepRelevanceForm');
    if (usecaseStepRelevanceForm) {
        usecaseStepRelevanceForm.onsubmit = function() { console.log('UC-Step Relevance form submitted'); return true; };
    }
    const usecaseUsecaseRelevanceForm = document.getElementById('usecaseUsecaseRelevanceForm');
    if (usecaseUsecaseRelevanceForm) {
        usecaseUsecaseRelevanceForm.onsubmit = function() { console.log('UC-UC Relevance form submitted'); return true; };
    }

    // --- Logic for "Prepare Steps for Update" (Keep these) ---
    const prepareStepsBtn = document.getElementById('prepareStepsBtn');
    const prepareStepsForm = document.getElementById('prepareStepsForm');
    const selectedStepsHiddenInput = document.getElementById('selected_update_steps_ids_hidden');
    const selectAllStepsCheckbox = document.getElementById('selectAllStepsCheckbox');
    const stepCheckboxes = document.querySelectorAll('.step-checkbox');

    if (prepareStepsBtn && prepareStepsForm && selectedStepsHiddenInput) {
        prepareStepsBtn.addEventListener('click', function() {
            const selectedIds = Array.from(document.querySelectorAll('.step-checkbox:checked'))
                                .map(cb => cb.value);
            if (selectedIds.length === 0) {
                alert('Please select at least one process step to update.');
                return;
            }
            selectedStepsHiddenInput.value = selectedIds.join(',');
            prepareStepsForm.submit();
        });
    }

    if (selectAllStepsCheckbox && stepCheckboxes.length > 0) {
        selectAllStepsCheckbox.addEventListener('change', function() {
            stepCheckboxes.forEach(cb => {
                if (cb.closest('tr') && cb.closest('tr').style.display !== 'none') {
                    cb.checked = this.checked;
                } else if (!cb.closest('tr')) { // Should not happen if table exists
                    cb.checked = this.checked;
                }
            });
        });
    }
    
    // --- Logic for "Prepare Use Cases for Update" (Keep these) ---
    const prepareUsecasesBtn = document.getElementById('prepareUsecasesBtn');
    const prepareUsecasesForm = document.getElementById('prepareUsecasesForm');
    const selectedUsecasesHiddenInput = document.getElementById('selected_update_usecases_ids_hidden');
    const selectAllUsecasesCheckbox = document.getElementById('selectAllUsecasesCheckbox');
    const usecaseCheckboxes = document.querySelectorAll('.usecase-checkbox');

    if (prepareUsecasesBtn && prepareUsecasesForm && selectedUsecasesHiddenInput) {
        prepareUsecasesBtn.addEventListener('click', function() {
            const selectedIds = Array.from(document.querySelectorAll('.usecase-checkbox:checked'))
                                .map(cb => cb.value);
            if (selectedIds.length === 0) {
                alert('Please select at least one use case to update.');
                return;
            }
            selectedUsecasesHiddenInput.value = selectedIds.join(',');
            prepareUsecasesForm.submit();
        });
    }

     if (selectAllUsecasesCheckbox && usecaseCheckboxes.length > 0) {
        selectAllUsecasesCheckbox.addEventListener('change', function() {
            usecaseCheckboxes.forEach(cb => {
                if (cb.closest('tr') && cb.closest('tr').style.display !== 'none') {
                    cb.checked = this.checked;
                } else if (!cb.closest('tr')) {
                    cb.checked = this.checked;
                }
            });
        });
    }

    // --- Logic for Area Filter Tabs (Process Steps table - Keep this) ---
    const stepAreaFilterTabsContainer = document.getElementById('stepAreaFilterTabs');
    const processStepsTable = document.getElementById('processStepsTable');
    
    if (stepAreaFilterTabsContainer && processStepsTable) {
        const stepTableRows = processStepsTable.querySelectorAll('tbody tr');

        stepAreaFilterTabsContainer.addEventListener('click', function(event) {
            const clickedButton = event.target.closest('button.btn');
            if (!clickedButton || !clickedButton.dataset.areaId) return;

            stepAreaFilterTabsContainer.querySelectorAll('button.btn').forEach(btn => btn.classList.remove('active'));
            clickedButton.classList.add('active');

            const selectedAreaId = clickedButton.dataset.areaId;

            stepTableRows.forEach(row => {
                const rowAreaId = row.dataset.stepAreaId;
                if (selectedAreaId === 'all' || rowAreaId === selectedAreaId) {
                    row.style.display = ''; 
                } else {
                    row.style.display = 'none';
                }
            });
            if (selectAllStepsCheckbox) selectAllStepsCheckbox.checked = false;
        });
    }
    
    // --- NEW: Logic for Use Case Table Filtering ---
    const usecaseAreaFilterTabs = document.getElementById('usecaseAreaFilterTabs');
    const useCasesTable = document.getElementById('useCasesTable');
    const usecaseFilterDropdownContainers = document.querySelectorAll('#useCasesBody .filter-dropdown-container');
    const clearAllUsecaseFiltersBtn = document.getElementById('clearAllUsecaseFiltersBtn');

    // Store for active filter selections for use cases
    let activeUsecaseFilters = {
        areaId: 'all', // From tabs
        stepName: new Set(),
        wave: new Set(),
        benefit: new Set(),
        effort: new Set()
    };

    // Helper: Map priority to benefit text (from Jinja macro)
    function mapPriorityToBenefitText(priority) {
        if (priority === 1 || priority === "1") return "High";
        if (priority === 2 || priority === "2") return "Medium";
        if (priority === 3 || priority === "3") return "Low";
        return "N/A";
    }

    // Helper: Get unique values for a use case field
    function getUniqueUsecaseValues(fieldKey) {
        const values = new Set();
        if (!allUsecasesDataForJS) return Array.from(values);

        allUsecasesDataForJS.forEach(uc => {
            let value;
            if (fieldKey === 'wave') value = uc.wave;
            else if (fieldKey === 'effort') value = uc.effort_level;
            else if (fieldKey === 'benefit') {
                // Use quality_improvement_quant if available, else map from priority
                value = uc.quality_improvement_quant ? uc.quality_improvement_quant : mapPriorityToBenefitText(uc.priority);
            }
            
            if (value !== null && value !== undefined && String(value).trim() !== "") {
                values.add(String(value).trim());
            } else {
                values.add("N/A"); // Treat empty/null as "N/A" for filtering
            }
        });
        return Array.from(values).sort();
    }
    
    // Populate a single filter dropdown for use cases
    function populateUsecaseFilterDropdown(container) {
        const filterType = container.dataset.filterType;
        const optionsList = container.querySelector('.filter-options-list');
        optionsList.innerHTML = ''; // Clear existing
        
        let uniqueValues;
        if (filterType === 'stepName') {
            // Steps are populated based on selected area
            const selectedAreaId = activeUsecaseFilters.areaId;
            let stepsForFilter = allStepsDataForJS;
            if (selectedAreaId !== 'all') {
                stepsForFilter = allStepsDataForJS.filter(step => step.area_id && step.area_id.toString() === selectedAreaId);
            }
            uniqueValues = stepsForFilter.map(step => ({ id: step.id.toString(), name: `${step.name} (BI_ID: ${step.bi_id})` }))
                                       .sort((a,b) => a.name.localeCompare(b.name));
        } else {
            uniqueValues = getUniqueUsecaseValues(filterType).map(val => ({ id: val, name: val }));
        }

        const currentSelections = activeUsecaseFilters[filterType] || new Set();

        uniqueValues.forEach(valObj => {
            const checkboxId = `uc-filter-${filterType}-${valObj.id.toString().replace(/\s+/g, '-')}`;
            const listItem = document.createElement('label');
            listItem.classList.add('filter-option-item', 'd-block', 'px-2', 'py-1'); // Bootstrap-like styling
            
            const checkbox = document.createElement('input');
            checkbox.type = 'checkbox';
            checkbox.value = valObj.id; // Use ID for steps, value string for others
            checkbox.id = checkboxId;
            checkbox.classList.add('form-check-input', 'me-2');
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

    function updateUsecaseFilterIndicator(container) {
        const filterType = container.dataset.filterType;
        const indicator = container.querySelector('.filter-indicator');
        const selections = activeUsecaseFilters[filterType];
        if (indicator) {
            if (selections && selections.size > 0) {
                indicator.textContent = `(${selections.size})`;
            } else {
                indicator.textContent = '';
            }
        }
    }

    // Apply all active filters to the Use Cases table
    function applyUsecaseFilters() {
        if (!useCasesTable) return;
        const usecaseTableRows = useCasesTable.querySelectorAll('tbody tr');

        usecaseTableRows.forEach(row => {
            const rowAreaId = row.dataset.ucAreaId;
            const rowStepId = row.dataset.ucStepId;
            const rowWave = row.dataset.ucWave || "N/A";
            const rowBenefit = row.dataset.ucBenefit || "N/A";
            const rowEffort = row.dataset.ucEffort || "N/A";

            let visible = true;

            // Area filter
            if (activeUsecaseFilters.areaId !== 'all' && rowAreaId !== activeUsecaseFilters.areaId) {
                visible = false;
            }
            // Step Name filter
            if (visible && activeUsecaseFilters.stepName.size > 0 && !activeUsecaseFilters.stepName.has(rowStepId)) {
                visible = false;
            }
            // Wave filter
            if (visible && activeUsecaseFilters.wave.size > 0 && !activeUsecaseFilters.wave.has(rowWave)) {
                visible = false;
            }
            // Benefit filter
            if (visible && activeUsecaseFilters.benefit.size > 0 && !activeUsecaseFilters.benefit.has(rowBenefit)) {
                visible = false;
            }
            // Effort filter
            if (visible && activeUsecaseFilters.effort.size > 0 && !activeUsecaseFilters.effort.has(rowEffort)) {
                visible = false;
            }

            row.style.display = visible ? '' : 'none';
        });
        if (selectAllUsecasesCheckbox) selectAllUsecasesCheckbox.checked = false;
    }

    // Event listener for Use Case Area Filter Tabs
    if (usecaseAreaFilterTabs) {
        usecaseAreaFilterTabs.addEventListener('click', function(event) {
            const clickedButton = event.target.closest('button.btn');
            if (!clickedButton || !clickedButton.dataset.areaId) return;

            usecaseAreaFilterTabs.querySelectorAll('button.btn').forEach(btn => btn.classList.remove('active'));
            clickedButton.classList.add('active');
            
            activeUsecaseFilters.areaId = clickedButton.dataset.areaId;
            // Repopulate Step Name filter based on new area selection
            const stepNameFilterContainer = document.querySelector('.filter-dropdown-container[data-filter-type="stepName"]');
            if (stepNameFilterContainer) {
                activeUsecaseFilters.stepName.clear(); // Clear previous step selections
                populateUsecaseFilterDropdown(stepNameFilterContainer);
            }
            applyUsecaseFilters();
        });
    }

    // Initialize and add event listeners for new filter dropdowns
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
                // Close other dropdowns
                usecaseFilterDropdownContainers.forEach(otherContainer => {
                    if (otherContainer !== container) {
                        otherContainer.querySelector('.filter-dropdown-menu').classList.remove('show');
                    }
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
    
    // Close dropdowns if clicking outside
    document.addEventListener('click', (event) => {
        usecaseFilterDropdownContainers.forEach(container => {
            if (!container.contains(event.target)) {
                container.querySelector('.filter-dropdown-menu').classList.remove('show');
            }
        });
    });

    // Clear All Usecase Filters Button
    if (clearAllUsecaseFiltersBtn) {
        clearAllUsecaseFiltersBtn.addEventListener('click', () => {
            // Reset Area tabs
            if (usecaseAreaFilterTabs) {
                usecaseAreaFilterTabs.querySelectorAll('button.btn').forEach(btn => btn.classList.remove('active'));
                const allAreasBtn = usecaseAreaFilterTabs.querySelector('button[data-area-id="all"]');
                if (allAreasBtn) allAreasBtn.classList.add('active');
            }
            activeUsecaseFilters.areaId = 'all';

            // Reset dropdown filters
            usecaseFilterDropdownContainers.forEach(container => {
                const filterType = container.dataset.filterType;
                activeUsecaseFilters[filterType].clear();
                populateUsecaseFilterDropdown(container); // Repopulates and unchecks
                updateUsecaseFilterIndicator(container);
            });
            applyUsecaseFilters();
        });
    }
    
    // Initial population of step name filter (based on "All Areas")
    const stepNameFilterContainer = document.querySelector('.filter-dropdown-container[data-filter-type="stepName"]');
    if (stepNameFilterContainer) {
        populateUsecaseFilterDropdown(stepNameFilterContainer);
    }

    // Initial application of filters if any are pre-selected (though unlikely here)
    applyUsecaseFilters();


    // --- Generic Collapse Icon Toggler for Card Headers ---
    const collapsibleCardHeaders = [
        document.getElementById('fullDbMgmtHeader'),
        document.getElementById('processStepsHeader'),
        document.getElementById('useCasesHeader')
    ];

    collapsibleCardHeaders.forEach(header => {
        if (header) {
            const button = header.querySelector('button[data-bs-toggle="collapse"]');
            if (button) {
                const targetId = button.getAttribute('data-bs-target');
                if (targetId && targetId.startsWith('#')) {
                    const collapseElement = document.getElementById(targetId.substring(1));
                    const iconElement = button.querySelector('i.fas');

                    if (collapseElement && iconElement) {
                        // Initial state based on 'show' class
                        if (collapseElement.classList.contains('show')) {
                            iconElement.classList.remove('fa-chevron-down');
                            iconElement.classList.add('fa-chevron-up');
                        } else {
                            iconElement.classList.remove('fa-chevron-up');
                            iconElement.classList.add('fa-chevron-down');
                        }
                        // Event listeners for state change
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
            }
        }
    });

}); // End of DOMContentLoaded