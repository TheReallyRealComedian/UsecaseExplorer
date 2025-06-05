// backend/static/js/data_update_page_ui.js

document.addEventListener('DOMContentLoaded', function() {
    // --- Form Submission Logs (Keep these) ---
    const databaseImportForm = document.getElementById('databaseImportForm');
    if (databaseImportForm) {
        databaseImportForm.onsubmit = function() {
            console.log('Database import form submitted');
            return true; // Allow submission
        };
    }
    const stepUploadForm = document.getElementById('stepUploadForm');
    if (stepUploadForm) {
        stepUploadForm.onsubmit = function() {
            console.log('Step upload form submitted');
            return true;
        };
    }
    const usecaseUploadForm = document.getElementById('usecaseUploadForm');
    if (usecaseUploadForm) {
        usecaseUploadForm.onsubmit = function() {
            console.log('Use Case upload form submitted');
            return true;
        };
    }
    const psPsRelevanceForm = document.getElementById('psPsRelevanceForm');
    if (psPsRelevanceForm) {
        psPsRelevanceForm.onsubmit = function() {
            console.log('PS-PS Relevance upload form submitted');
            return true;
        };
    }
    const usecaseAreaRelevanceForm = document.getElementById('usecaseAreaRelevanceForm');
    if (usecaseAreaRelevanceForm) {
        usecaseAreaRelevanceForm.onsubmit = function() {
            console.log('UC-Area Relevance upload form submitted');
            return true;
        };
    }
    const usecaseStepRelevanceForm = document.getElementById('usecaseStepRelevanceForm');
    if (usecaseStepRelevanceForm) {
        usecaseStepRelevanceForm.onsubmit = function() {
            console.log('UC-Step Relevance form submitted');
            return true;
        };
    }
    const usecaseUsecaseRelevanceForm = document.getElementById('usecaseUsecaseRelevanceForm');
    if (usecaseUsecaseRelevanceForm) {
        usecaseUsecaseRelevanceForm.onsubmit = function() {
            console.log('UC-UC Relevance form submitted');
            return true;
        };
    }


    // --- Logic for "Prepare Steps for Update" ---
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
            console.log('Preparing steps for update. IDs:', selectedStepsHiddenInput.value);
            prepareStepsForm.submit();
        });
    }

    if (selectAllStepsCheckbox && stepCheckboxes.length > 0) {
        selectAllStepsCheckbox.addEventListener('change', function() {
            stepCheckboxes.forEach(cb => cb.checked = this.checked);
        });
    }

    // --- Logic for "Prepare Use Cases for Update" ---
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
            console.log('Preparing use cases for update. IDs:', selectedUsecasesHiddenInput.value);
            prepareUsecasesForm.submit();
        });
    }

    if (selectAllUsecasesCheckbox && usecaseCheckboxes.length > 0) {
        selectAllUsecasesCheckbox.addEventListener('change', function() {
            usecaseCheckboxes.forEach(cb => cb.checked = this.checked);
        });
    }

    // The previous filtering logic for <select> elements is removed as those selects are gone.
    // If table filtering is needed, new specific JS would be added here.
    // For now, we'll rely on the browser's native table display.

}); // End of DOMContentLoaded