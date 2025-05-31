// UsecaseExplorer/backend/static/js/llm_ui.js
import { initializeLLMChat } from './common_llm_chat.js'; // Import the new module

document.addEventListener('DOMContentLoaded', function () {
    // Custom Selects Initialization
    initializeCustomSelects();
    // Search Functionality Initialization
    initializeSearch();
    // Update counts for custom selects on page load
    updateAllCounts();

    // Initialize the LLM Chat functionality using the common module
    // This page (llm_data_prep.html) now integrates image input directly into chatInput
    initializeLLMChat(
        'chatDisplay',
        'chatInput',
        'sendMessageButton',
        'clearChatButton',
        'llmModelSelect',
        'systemPromptInput',
        'saveSystemPromptButton',
        'chatInput', // Pass chatInput as the target for image paste/drop
        'imagePreview', // ID of the image preview element
        'clearImageButton' // ID of the button to clear the image
    );

    // --- Custom Select Implementation (existing, no change) ---
    function initializeCustomSelects() {
        document.querySelectorAll('.select-option').forEach(option => {
            option.addEventListener('click', function() {
                this.classList.toggle('selected');
                updateHiddenInputs(this.dataset.name);
                updateCount(this.dataset.name);
            });
        });
    }

    // Update hidden inputs for form submission
    function updateHiddenInputs(inputName) {
        const container = document.getElementById(inputName.replace('_ids', '') + '_hidden_inputs');
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

    // Update selection counts
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
    }

    // --- Search functionality (existing, no change) ---
    function initializeSearch() {
        document.getElementById('area_search')?.addEventListener('input', function() {
            filterOptions(this.value, 'area-select-container');
            filterOptions(document.getElementById('step_search')?.value || '', 'step-select-container');
            filterOptions(document.getElementById('usecase_search')?.value || '', 'usecase-select-container');
        });
        
        document.getElementById('step_search')?.addEventListener('input', function() {
            filterOptions(this.value, 'step-select-container');
            filterOptions(document.getElementById('usecase_search')?.value || '', 'usecase-select-container');
        });
        
        document.getElementById('usecase_search')?.addEventListener('input', function() {
            filterOptions(this.value, 'usecase-select-container');
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

        options.forEach(option => {
            const text = option.textContent.toLowerCase();
            const optionAreaId = option.dataset.areaId;
            const optionStepId = option.dataset.stepId;

            let matchesSearch = text.includes(term);
            let matchesAreaFilter = true;
            let matchesStepFilter = true;

            if (selectedAreaIds.length > 0) {
                if (optionAreaId) {
                    matchesAreaFilter = selectedAreaIds.includes(optionAreaId);
                } else if (containerId === 'step-select-container' || containerId === 'usecase-select-container') {
                    matchesAreaFilter = false;
                }
            }

            if (containerId === 'usecase-select-container' && selectedStepIds.length > 0) {
                if (optionStepId) {
                    matchesStepFilter = selectedStepIds.includes(optionStepId);
                } else {
                    matchesStepFilter = false;
                }
            }

            if (matchesSearch && matchesAreaFilter && matchesStepFilter) {
                option.style.display = 'block';
            } else {
                option.style.display = 'none';
            }
        });
    }

    // --- Select All / Clear All functions for custom selects (existing, no change) ---
    function selectAll(type) {
        const containerMap = {
            'areas': 'area-select-container',
            'steps': 'step-select-container', 
            'usecases': 'usecase-select-container'
        };
        
        const inputNameMap = {
            'areas': 'area_ids',
            'steps': 'step_ids',
            'usecases': 'usecase_ids'
        };
        
        const container = document.getElementById(containerMap[type]);
        if (!container) return;
        
        const options = container.querySelectorAll('.select-option');
        options.forEach(option => {
            if (option.style.display !== 'none') {
                option.classList.add('selected');
            }
        });
        
        const inputName = inputNameMap[type];
        updateHiddenInputs(inputName);
        updateCount(inputName);
        
        if (type === 'areas') {
            filterOptions(document.getElementById('step_search')?.value || '', 'step-select-container');
            filterOptions(document.getElementById('usecase_search')?.value || '', 'usecase-select-container');
        } else if (type === 'steps') {
            filterOptions(document.getElementById('usecase_search')?.value || '', 'usecase-select-container');
        }
    }

    function clearAll(type) {
        const containerMap = {
            'areas': 'area-select-container',
            'steps': 'step-select-container',
            'usecases': 'usecase-select-container'
        };
        
        const inputNameMap = {
            'areas': 'area_ids',
            'steps': 'step_ids', 
            'usecases': 'usecase_ids'
        };
        
        const container = document.getElementById(containerMap[type]);
        if (!container) return;
        
        const options = container.querySelectorAll('.select-option');
        options.forEach(option => option.classList.remove('selected'));
        
        const inputName = inputNameMap[type];
        updateHiddenInputs(inputName);
        updateCount(inputName);

        if (type === 'areas') {
            filterOptions(document.getElementById('step_search')?.value || '', 'step-select-container');
            filterOptions(document.getElementById('usecase_search')?.value || '', 'usecase-select-container');
        } else if (type === 'steps') {
            filterOptions(document.getElementById('usecase_search')?.value || '', 'usecase-select-container');
        }
    }

    // --- Event Listeners for Custom Select All/Clear All Buttons (existing, no change) ---
    document.getElementById('selectAllAreas')?.addEventListener('click', () => selectAll('areas'));
    document.getElementById('clearAllAreas')?.addEventListener('click', () => clearAll('areas'));
    
    document.getElementById('selectAllSteps')?.addEventListener('click', () => selectAll('steps'));
    document.getElementById('clearAllSteps')?.addEventListener('click', () => clearAll('steps'));
    
    document.getElementById('selectAllUsecases')?.addEventListener('click', () => selectAll('usecases'));
    document.getElementById('clearAllUsecases')?.addEventListener('click', () => clearAll('usecases'));

    // --- Logic for dependent filtering of custom selects when options are clicked (existing, no change) ---
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

    // --- JSON Preview Control (existing, no change) ---
    const copyJsonButton = document.getElementById('copyJsonButton');
    const jsonDataPreview = document.getElementById('jsonDataPreview');
    const jsonPreviewContainer = document.getElementById('jsonPreviewContainer');
    const toggleJsonPreviewButton = document.getElementById('toggleJsonPreview');
    const tokenCountDisplay = document.getElementById('tokenCountDisplay');

    const hasData = jsonDataPreview && 
                    jsonDataPreview.textContent.trim() !== '{"process_steps": [], "use_cases": []}' &&
                    jsonDataPreview.textContent.trim() !== 'null' && 
                    jsonDataPreview.textContent.trim() !== '';

    if (copyJsonButton) copyJsonButton.style.display = hasData ? 'inline-block' : 'none';
    if (toggleJsonPreviewButton) toggleJsonPreviewButton.style.display = hasData ? 'inline-block' : 'none'; 
    if (tokenCountDisplay) tokenCountDisplay.style.display = hasData ? 'block' : 'none';

    if (toggleJsonPreviewButton && jsonPreviewContainer) {
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

    // --- Bootstrap Collapse Icon Toggle Logic (existing, no change) ---
    const collapseHeaders = [
        document.getElementById('selectionCriteriaHeader'),
        document.getElementById('preparedDataHeader'),
        document.getElementById('llmChatHeader'),
        document.getElementById('systemPromptHeader'),
        document.getElementById('relevanceLinkBody') // Added to match original
    ];

    collapseHeaders.forEach(header => {
        if (header) {
            const targetId = header.getAttribute('data-bs-target');
            if (targetId) { // Check if targetId is not null or undefined
                const collapseElement = document.getElementById(targetId.substring(1));
                const iconElement = header.querySelector('i');

                if (collapseElement && iconElement) {
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

});

// --- GLOBAL FUNCTIONS FOR FIELD CHECKBOXES (existing, no change) ---
function selectAllStepFields() {
    const checkboxes = document.querySelectorAll('input[name="step_fields"]');
    checkboxes.forEach(cb => cb.checked = true);
}

function clearAllStepFields() {
    const checkboxes = document.querySelectorAll('input[name="step_fields"]');
    checkboxes.forEach(cb => cb.checked = false);
}

function selectAllUsecaseFields() {
    const checkboxes = document.querySelectorAll('input[name="usecase_fields"]');
    checkboxes.forEach(cb => cb.checked = true);
}

function clearAllUsecaseFields() {
    const checkboxes = document.querySelectorAll('input[name="usecase_fields"]');
    checkboxes.forEach(cb => cb.checked = false);
}