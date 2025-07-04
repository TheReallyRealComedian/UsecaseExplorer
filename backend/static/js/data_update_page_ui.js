// backend/static/js/data_update_page_ui.js

document.addEventListener('DOMContentLoaded', function() {
    // --- Form Submission Logs ---
    const databaseImportForm = document.getElementById('databaseImportForm');
    if (databaseImportForm) {
        databaseImportForm.onsubmit = () => {
            console.log('Database import form submitted');
            return true;
        };
    }
    const stepUploadForm = document.getElementById('stepUploadForm');
    if (stepUploadForm) {
        stepUploadForm.onsubmit = () => {
            console.log('Step upload form submitted');
            return true;
        };
    }
    const usecaseUploadForm = document.getElementById('usecaseUploadForm');
    if (usecaseUploadForm) {
        usecaseUploadForm.onsubmit = () => {
            console.log('Use Case upload form submitted');
            return true;
        };
    }
    const psPsRelevanceForm = document.getElementById('psPsRelevanceForm');
    if (psPsRelevanceForm) {
        psPsRelevanceForm.onsubmit = () => {
            console.log('PS-PS Relevance upload form submitted');
            return true;
        };
    }
    const usecaseAreaRelevanceForm = document.getElementById('usecaseAreaRelevanceForm');
    if (usecaseAreaRelevanceForm) {
        usecaseAreaRelevanceForm.onsubmit = () => {
            console.log('UC-Area Relevance upload form submitted');
            return true;
        };
    }
    const usecaseStepRelevanceForm = document.getElementById('usecaseStepRelevanceForm');
    if (usecaseStepRelevanceForm) {
        usecaseStepRelevanceForm.onsubmit = () => {
            console.log('UC-Step Relevance form submitted');
            return true;
        };
    }
    const usecaseUsecaseRelevanceForm = document.getElementById('usecaseUsecaseRelevanceForm');
    if (usecaseUsecaseRelevanceForm) {
        usecaseUsecaseRelevanceForm.onsubmit = () => {
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
            const selectedIds = Array.from(document.querySelectorAll('.step-checkbox:checked')).map(cb => cb.value);
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
                cb.checked = this.checked;
            });
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
            const selectedIds = Array.from(document.querySelectorAll('.usecase-checkbox:checked')).map(cb => cb.value);
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
                cb.checked = this.checked;
            });
        });
    }

    // --- Generic Collapse Icon Toggler for Card Headers ---
    const collapsibleCardHeaders = document.querySelectorAll('.card-header [data-bs-toggle="collapse"]');
    collapsibleCardHeaders.forEach(button => {
        const targetId = button.getAttribute('data-bs-target');
        if (!targetId || !targetId.startsWith('#')) return;

        const collapseElement = document.getElementById(targetId.substring(1));
        const iconElement = button.querySelector('i.fas');
        if (!collapseElement || !iconElement) return;

        const updateIcon = () => {
            if (collapseElement.classList.contains('show')) {
                iconElement.classList.remove('fa-chevron-down');
                iconElement.classList.add('fa-chevron-up');
            } else {
                iconElement.classList.remove('fa-chevron-up');
                iconElement.classList.add('fa-chevron-down');
            }
        };

        collapseElement.addEventListener('shown.bs.collapse', updateIcon);
        collapseElement.addEventListener('hidden.bs.collapse', updateIcon);
        updateIcon();
    });

});