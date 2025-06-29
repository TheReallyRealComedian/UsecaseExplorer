document.addEventListener('DOMContentLoaded', function() {
    const usecaseAreaFilterTabs = document.getElementById('usecaseAreaFilterTabs');
    const useCasesTable = document.getElementById('useCasesTable');
    const usecaseFilterDropdownContainers = document.querySelectorAll('.filter-dropdown-container');
    const clearAllUsecaseFiltersBtn = document.getElementById('clearAllUsecaseFiltersBtn');

    let activeUsecaseFilters = {
        areaId: 'all',
        stepName: new Set(),
        wave: new Set()
    };

    function getUniqueUsecaseValues(fieldKey) {
        const values = new Set();
        if (!allUsecasesDataForJS) return Array.from(values);
        allUsecasesDataForJS.forEach(uc => {
            let value = uc[fieldKey];
            if (value !== null && value !== undefined && String(value).trim() !== "") {
                values.add(String(value).trim());
            } else {
                values.add("N/A");
            }
        });
        return Array.from(values).sort();
    }

    function populateUsecaseFilterDropdown(container) {
        const filterType = container.dataset.filterType;
        const optionsList = container.querySelector('.filter-options-list');
        optionsList.innerHTML = '';

        let uniqueValues;
        if (filterType === 'stepName') {
            const selectedAreaId = activeUsecaseFilters.areaId;
            let stepsForFilter = allStepsDataForJS;
            if (selectedAreaId !== 'all') {
                stepsForFilter = allStepsDataForJS.filter(step => step.area_id && step.area_id.toString() === selectedAreaId);
            }
            uniqueValues = stepsForFilter.map(step => ({ id: step.id.toString(), name: step.name }))
                .sort((a, b) => a.name.localeCompare(b.name));
        } else {
            uniqueValues = getUniqueUsecaseValues(filterType).map(val => ({ id: val, name: val }));
        }

        const currentSelections = activeUsecaseFilters[filterType] || new Set();

        uniqueValues.forEach(valObj => {
            const checkboxId = `uc-filter-${filterType}-${valObj.id.toString().replace(/\s+/g, '-')}`;
            const listItem = document.createElement('label');
            listItem.className = 'filter-option-item d-block px-2 py-1';

            const checkbox = document.createElement('input');
            checkbox.type = 'checkbox';
            checkbox.value = valObj.id;
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

    function updateUsecaseFilterIndicator(container) {
        const filterType = container.dataset.filterType;
        const indicator = container.querySelector('.filter-indicator');
        const selections = activeUsecaseFilters[filterType];
        if (indicator) {
            indicator.textContent = (selections && selections.size > 0) ? `(${selections.size})` : '';
        }
    }

    function applyUsecaseFilters() {
        if (!useCasesTable) return;
        const usecaseTableRows = useCasesTable.querySelectorAll('tbody tr');

        usecaseTableRows.forEach(row => {
            const rowAreaId = row.dataset.ucAreaId;
            const rowStepId = row.dataset.ucStepId;
            const rowWave = (row.dataset.ucWave || "N/A").trim();

            let visible = true;
            if (activeUsecaseFilters.areaId !== 'all' && rowAreaId !== activeUsecaseFilters.areaId) {
                visible = false;
            }
            if (visible && activeUsecaseFilters.stepName.size > 0 && !activeUsecaseFilters.stepName.has(rowStepId)) {
                visible = false;
            }
            if (visible && activeUsecaseFilters.wave.size > 0 && !activeUsecaseFilters.wave.has(rowWave)) {
                visible = false;
            }
            row.style.display = visible ? '' : 'none';
        });
    }

    if (usecaseAreaFilterTabs) {
        usecaseAreaFilterTabs.addEventListener('click', function(event) {
            const clickedButton = event.target.closest('button.btn');
            if (!clickedButton || !clickedButton.dataset.areaId) return;

            usecaseAreaFilterTabs.querySelectorAll('button.btn').forEach(btn => btn.classList.remove('active'));
            clickedButton.classList.add('active');

            activeUsecaseFilters.areaId = clickedButton.dataset.areaId;
            const stepNameFilterContainer = document.querySelector('.filter-dropdown-container[data-filter-type="stepName"]');
            if (stepNameFilterContainer) {
                activeUsecaseFilters.stepName.clear();
                populateUsecaseFilterDropdown(stepNameFilterContainer);
            }
            applyUsecaseFilters();
        });
    }

    usecaseFilterDropdownContainers.forEach(container => {
        const toggleButton = container.querySelector('.filter-dropdown-toggle');
        const dropdownMenu = container.querySelector('.filter-dropdown-menu');
        const selectAllButton = container.querySelector('.select-all-action');
        const clearSelectionButton = container.querySelector('.clear-selection-action');
        const filterType = container.dataset.filterType;

        populateUsecaseFilterDropdown(container);

        if (toggleButton && dropdownMenu) {
            toggleButton.addEventListener('click', (event) => {
                event.stopPropagation();
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

    document.addEventListener('click', (event) => {
        usecaseFilterDropdownContainers.forEach(container => {
            if (!container.contains(event.target)) {
                container.querySelector('.filter-dropdown-menu').classList.remove('show');
            }
        });
    });

    if (clearAllUsecaseFiltersBtn) {
        clearAllUsecaseFiltersBtn.addEventListener('click', () => {
            if (usecaseAreaFilterTabs) {
                usecaseAreaFilterTabs.querySelectorAll('button.btn').forEach(btn => btn.classList.remove('active'));
                const allBtn = usecaseAreaFilterTabs.querySelector('button[data-area-id="all"]');
                if (allBtn) allBtn.classList.add('active');
            }
            activeUsecaseFilters.areaId = 'all';
            usecaseFilterDropdownContainers.forEach(container => {
                const filterType = container.dataset.filterType;
                activeUsecaseFilters[filterType].clear();
                populateUsecaseFilterDropdown(container);
            });
            applyUsecaseFilters();
        });
    }
    
    function makeTableSortable(tableElement) {
        if (!tableElement) return;
        tableElement.querySelectorAll('th.sortable').forEach(header => {
            header.addEventListener('click', () => {
                const currentOrder = header.classList.contains('sorted-asc') ? 'asc' : (header.classList.contains('sorted-desc') ? 'desc' : 'none');
                const sortOrder = (currentOrder === 'asc') ? 'desc' : 'asc';
                tableElement.querySelectorAll('th.sortable').forEach(th => th.classList.remove('sorted-asc', 'sorted-desc'));
                header.classList.add(sortOrder === 'asc' ? 'sorted-asc' : 'sorted-desc');
                
                const tbody = tableElement.querySelector('tbody');
                if (!tbody) return;
                const rows = Array.from(tbody.querySelectorAll('tr'));
                const colIndex = Array.from(header.parentNode.children).indexOf(header);

                rows.sort((a, b) => {
                    let valA = (a.cells[colIndex] && a.cells[colIndex].dataset.sortValue !== undefined) ? a.cells[colIndex].dataset.sortValue : (a.cells[colIndex] ? a.cells[colIndex].textContent.trim() : '');
                    let valB = (b.cells[colIndex] && b.cells[colIndex].dataset.sortValue !== undefined) ? b.cells[colIndex].dataset.sortValue : (b.cells[colIndex] ? b.cells[colIndex].textContent.trim() : '');
                    
                    const numA = parseFloat(valA);
                    const numB = parseFloat(valB);

                    if (!isNaN(numA) && !isNaN(numB)) {
                        return sortOrder === 'asc' ? numA - numB : numB - numA;
                    } else {
                        return sortOrder === 'asc' ? valA.localeCompare(valB) : valB.localeCompare(valA);
                    }
                });
                rows.forEach(row => tbody.appendChild(row));
            });
        });
    }
    
    makeTableSortable(useCasesTable);
    applyUsecaseFilters();
});