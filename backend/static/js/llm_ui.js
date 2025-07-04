// UsecaseExplorer/backend/static/js/llm_ui.js
document.addEventListener('DOMContentLoaded', function () {
    // Custom Selects Initialization
    initializeCustomSelects();
    // Search Functionality Initialization
    initializeSearch();
    // Update counts for custom selects on page load
    updateAllCounts();

    // --- Custom Select Implementation ---
    function initializeCustomSelects() {
        document.querySelectorAll('.select-option').forEach(option => {
            option.addEventListener('click', function() {
                this.classList.toggle('selected');
                updateHiddenInputs(this.dataset.name);
                updateCount(this.dataset.name);
            });
        });
    }

    function updateHiddenInputs(inputName) {
        const container = document.getElementById(inputName.replace('_ids', '').replace('_values', '') + '_hidden_inputs'); // Adjusted for wave_values
        if (!container) return;
        
        container.innerHTML = '';
        
        const selectedOptions = document.querySelectorAll(`.select-option[data-name="${inputName}"].selected`);
        selectedOptions.forEach(option => {
            const input = document.createElement('input');
            input.type = 'hidden';
            input.name = inputName;
            input.value = option.dataset.value;
            container.appendChild(input);
        });
    }

    function updateCount(inputName) {
        const countElement = document.getElementById(inputName + '_selected_count');
        if (!countElement) return;
        
        const selectedCount = document.querySelectorAll(`.select-option[data-name="${inputName}"].selected`).length;
        countElement.textContent = `${selectedCount} selected`;
    }

    function updateAllCounts() {
        updateCount('area_ids');
        updateCount('step_ids');
        updateCount('usecase_ids');
        updateCount('wave_values'); // NEW
    }

    // --- Search functionality ---
    function initializeSearch() {
        document.getElementById('area_search')?.addEventListener('input', function() {
            filterOptions(this.value, 'area-select-container');
            // Re-filter dependent selects when area search changes
            filterOptions(document.getElementById('step_search')?.value || '', 'step-select-container');
            filterOptions(document.getElementById('usecase_search')?.value || '', 'usecase-select-container');
        });
        
        document.getElementById('step_search')?.addEventListener('input', function() {
            filterOptions(this.value, 'step-select-container');
            // Re-filter use case select when step search changes
            filterOptions(document.getElementById('usecase_search')?.value || '', 'usecase-select-container');
        });
        
        document.getElementById('usecase_search')?.addEventListener('input', function() {
            filterOptions(this.value, 'usecase-select-container');
        });

        document.getElementById('wave_search')?.addEventListener('input', function() { // NEW
            filterOptions(this.value, 'wave-select-container');
            // Re-filter use case select when wave search changes
            filterOptions(document.getElementById('usecase_search')?.value || '', 'usecase-select-container');
        });
    }

    function filterOptions(searchTerm, containerId) {
        const container = document.getElementById(containerId);
        if (!container) return;
        
        const options = container.querySelectorAll('.select-option');
        const term = searchTerm.toLowerCase();
        
        const selectedAreaIds = Array.from(document.querySelectorAll('.select-option[data-name="area_ids"].selected'))
                                .map(opt => opt.dataset.value);
        const selectedStepIds = Array.from(document.querySelectorAll('.select-option[data-name="step_ids"].selected'))
                               .map(opt => opt.dataset.value);
        const selectedWaveValues = Array.from(document.querySelectorAll('.select-option[data-name="wave_values"].selected')) // NEW
                                .map(opt => opt.dataset.value); // NEW

        options.forEach(option => {
            const text = option.textContent.toLowerCase();
            const optionAreaId = option.dataset.areaId;
            const optionStepId = option.dataset.stepId;
            const optionWave = option.dataset.wave; // NEW

            let matchesSearch = text.includes(term);
            let matchesAreaFilter = true;
            let matchesStepFilter = true;
            let matchesWaveFilter = true; // NEW

            // Filter steps based on selected areas
            if (containerId === 'step-select-container') {
                if (selectedAreaIds.length > 0 && optionAreaId && !selectedAreaIds.includes(optionAreaId)) {
                    matchesAreaFilter = false;
                }
            }
            // Filter use cases based on selected areas, steps, and waves
            else if (containerId === 'usecase-select-container') {
                if (selectedAreaIds.length > 0 && optionAreaId && !selectedAreaIds.includes(optionAreaId)) {
                    matchesAreaFilter = false;
                }
                if (selectedStepIds.length > 0 && optionStepId && !selectedStepIds.includes(optionStepId)) {
                    matchesStepFilter = false;
                }
                if (selectedWaveValues.length > 0) { // NEW Wave Filter Logic
                    if (optionWave) { // Ensure the use case option has a wave attribute
                        matchesWaveFilter = selectedWaveValues.includes(optionWave);
                    } else { // If a wave filter is active, and the use case has no wave, it doesn't match
                        matchesWaveFilter = false;
                    }
                }
            }
            // For area and wave containers, only search term matters for now.
            // If a wave filter should affect steps (e.g. show steps that have UCs of a certain wave), that's more complex.

            if (matchesSearch && matchesAreaFilter && matchesStepFilter && matchesWaveFilter) { // MODIFIED
                option.style.display = 'block';
            } else {
                option.style.display = 'none';
            }
        });
    }

    // --- Select All / Clear All functions ---
    function selectAll(type) {
        const containerMap = {
            'areas': 'area-select-container',
            'steps': 'step-select-container', 
            'usecases': 'usecase-select-container',
            'waves': 'wave-select-container' // NEW
        };
        
        const inputNameMap = {
            'areas': 'area_ids',
            'steps': 'step_ids', 
            'usecases': 'usecase_ids',
            'waves': 'wave_values' // NEW
        };
        
        const container = document.getElementById(containerMap[type]);
        if (!container) return;
        
        const options = container.querySelectorAll('.select-option');
        options.forEach(option => {
            if (option.style.display !== 'none') { // Only select visible options
                option.classList.add('selected');
            }
        });
        
        const inputName = inputNameMap[type];
        updateHiddenInputs(inputName);
        updateCount(inputName);
        
        // Trigger dependent filtering
        if (type === 'areas') {
            filterOptions(document.getElementById('step_search')?.value || '', 'step-select-container');
            filterOptions(document.getElementById('usecase_search')?.value || '', 'usecase-select-container');
        } else if (type === 'steps') {
            filterOptions(document.getElementById('usecase_search')?.value || '', 'usecase-select-container');
        } else if (type === 'waves') { // NEW
            filterOptions(document.getElementById('usecase_search')?.value || '', 'usecase-select-container');
        }
    }

    function clearAll(type) {
        const containerMap = {
            'areas': 'area-select-container',
            'steps': 'step-select-container',
            'usecases': 'usecase-select-container',
            'waves': 'wave-select-container' // NEW
        };
        
        const inputNameMap = {
            'areas': 'area_ids',
            'steps': 'step_ids', 
            'usecases': 'usecase_ids',
            'waves': 'wave_values' // NEW
        };
        
        const container = document.getElementById(containerMap[type]);
        if (!container) return;
        
        const options = container.querySelectorAll('.select-option');
        options.forEach(option => option.classList.remove('selected'));
        
        const inputName = inputNameMap[type];
        updateHiddenInputs(inputName);
        updateCount(inputName);

        // Trigger dependent filtering
        if (type === 'areas') {
            filterOptions(document.getElementById('step_search')?.value || '', 'step-select-container');
            filterOptions(document.getElementById('usecase_search')?.value || '', 'usecase-select-container');
        } else if (type === 'steps') {
            filterOptions(document.getElementById('usecase_search')?.value || '', 'usecase-select-container');
        } else if (type === 'waves') { // NEW
            filterOptions(document.getElementById('usecase_search')?.value || '', 'usecase-select-container');
        }
    }

    // --- Event Listeners for Custom Select All/Clear All Buttons ---
    document.getElementById('selectAllAreas')?.addEventListener('click', () => selectAll('areas'));
    document.getElementById('clearAllAreas')?.addEventListener('click', () => clearAll('areas'));
    
    document.getElementById('selectAllSteps')?.addEventListener('click', () => selectAll('steps'));
    document.getElementById('clearAllSteps')?.addEventListener('click', () => clearAll('steps'));
    
    document.getElementById('selectAllUsecases')?.addEventListener('click', () => selectAll('usecases'));
    document.getElementById('clearAllUsecases')?.addEventListener('click', () => clearAll('usecases'));

    document.getElementById('selectAllWaves')?.addEventListener('click', () => selectAll('waves')); // NEW
    document.getElementById('clearAllWaves')?.addEventListener('click', () => clearAll('waves'));   // NEW


    // --- Logic for dependent filtering of custom selects when options are clicked ---
    document.querySelectorAll('.select-option[data-name="area_ids"]').forEach(option => {
        option.addEventListener('click', () => {
            filterOptions(document.getElementById('step_search')?.value || '', 'step-select-container');
            filterOptions(document.getElementById('usecase_search')?.value || '', 'usecase-select-container');
        });
    });

    document.querySelectorAll('.select-option[data-name="step_ids"]').forEach(option => {
        option.addEventListener('click', () => {
            filterOptions(document.getElementById('usecase_search')?.value || '', 'usecase-select-container');
        });
    });

    document.querySelectorAll('.select-option[data-name="wave_values"]').forEach(option => { // NEW
        option.addEventListener('click', () => {
            filterOptions(document.getElementById('usecase_search')?.value || '', 'usecase-select-container');
        });
    });

    // --- JSON Preview Control ---
    const copyJsonButton = document.getElementById('copyJsonButton');
    const jsonDataPreview = document.getElementById('jsonDataPreview');
    const jsonPreviewContainer = document.getElementById('jsonPreviewContainer');
    const tokenCountDisplay = document.getElementById('tokenCountDisplay');

    const hasData = jsonDataPreview && 
                    jsonDataPreview.textContent.trim() !== '{"process_steps": [], "use_cases": []}' &&
                    jsonDataPreview.textContent.trim() !== 'null' && 
                    jsonDataPreview.textContent.trim() !== '';

    if (copyJsonButton) copyJsonButton.style.display = hasData ? 'inline-block' : 'none';
    if (tokenCountDisplay) tokenCountDisplay.style.display = hasData ? 'block' : 'none';

    if (copyJsonButton && jsonDataPreview) {
        copyJsonButton.addEventListener('click', () => {
            if (!hasData) {
                alert('No data to copy.');
                return;
            }
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

    // --- Bootstrap Collapse Icon Toggle Logic ---
    const collapseHeaders = [
        document.getElementById('selectionCriteriaHeader'),
        document.getElementById('preparedDataHeader'),
        document.getElementById('relevanceLinkBody')
    ];

    collapseHeaders.forEach(header => {
        if (header) {
            const targetId = header.getAttribute('data-bs-target');
            if (targetId) {
                const collapseElement = document.getElementById(targetId.substring(1));
                const iconElement = header.querySelector('i');

                if (collapseElement && iconElement) {
                    // Initial state
                    if (collapseElement.classList.contains('show')) {
                        iconElement.classList.remove('fa-chevron-down');
                        iconElement.classList.add('fa-chevron-up');
                    } else {
                        iconElement.classList.remove('fa-chevron-up');
                        iconElement.classList.add('fa-chevron-down');
                    }

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
    });

    // --- NEW: Event listeners for Select All / Clear All field checkboxes ---
    document.getElementById('selectAllStepFieldsBtn')?.addEventListener('click', () => {
        document.querySelectorAll('input[name="step_fields"]').forEach(cb => cb.checked = true);
    });
    document.getElementById('clearAllStepFieldsBtn')?.addEventListener('click', () => {
        document.querySelectorAll('input[name="step_fields"]').forEach(cb => cb.checked = false);
    });

    document.getElementById('selectAllUsecaseFieldsBtn')?.addEventListener('click', () => {
        document.querySelectorAll('input[name="usecase_fields"]').forEach(cb => cb.checked = true);
    });
    document.getElementById('clearAllUsecaseFieldsBtn')?.addEventListener('click', () => {
        document.querySelectorAll('input[name="usecase_fields"]').forEach(cb => cb.checked = false);
    });
});