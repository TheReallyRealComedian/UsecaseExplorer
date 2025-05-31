// backend/static/js/breadcrumb_ui.js

document.addEventListener('DOMContentLoaded', function() {

    // Global data passed from Flask template (defined in base.html)
    // These variables should be available in the global scope due to their placement in base.html
    const allAreas = allAreasFlat;
    const allSteps = allStepsFlat;
    const allUsecases = allUsecasesFlat;

    const currentArea = currentAreaId;
    const currentStep = currentStepId;
    const currentUsecase = currentUsecaseId;

    // Get breadcrumb container elements
    const areaBreadcrumbContainer = document.getElementById('area-breadcrumb-container');
    const stepBreadcrumbContainer = document.getElementById('step-breadcrumb-container');
    const usecaseBreadcrumbContainer = document.getElementById('usecase-breadcrumb-container');

    /**
     * Populates a Bootstrap dropdown menu with list items.
     * @param {HTMLElement} dropdownMenuElement The <ul> element for the dropdown menu.
     * @param {Array<Object>} items An array of objects, each with 'name' and 'url' properties.
     * @param {string} currentItemId (optional) The ID of the currently active item, to skip it from the list.
     * @param {string} separatorLabel (optional) Label for the separator if any items are listed after a separator.
     * @param {boolean} addSeparator Indicates whether a separator should be added before the current item's children (e.g. all steps for an area).
     * @param {Array<Object>} childrenItems (optional) Items to be listed as children after the separator.
     */
    function populateDropdown(dropdownMenuElement, items, currentItemId = null, separatorLabel = null, addSeparator = false, childrenItems = []) {
        dropdownMenuElement.innerHTML = ''; // Clear existing items

        if (!items || items.length === 0) {
            const li = document.createElement('li');
            li.innerHTML = '<span class="dropdown-item text-muted">No items found.</span>';
            dropdownMenuElement.appendChild(li);
            return;
        }

        let addedCount = 0;

        // Add main items
        items.forEach(item => {
            // Skip the current item to avoid self-linking in the dropdown
            if (currentItemId !== null && item.id === currentItemId) {
                return; // Don't add the current item itself to the list
            }
            const li = document.createElement('li');
            li.innerHTML = `<a class="dropdown-item" href="${item.url}">${item.name}</a>`;
            dropdownMenuElement.appendChild(li);
            addedCount++;
        });

        // Add separator and children if requested
        if (addSeparator && childrenItems && childrenItems.length > 0) {
            if (addedCount > 0) { // Only add divider if there were previous items
                const divider = document.createElement('li');
                divider.innerHTML = '<hr class="dropdown-divider">';
                dropdownMenuElement.appendChild(divider);
            }
            const labelLi = document.createElement('li');
            labelLi.innerHTML = `<h6 class="dropdown-header">${separatorLabel}</h6>`;
            dropdownMenuElement.appendChild(labelLi);

            childrenItems.forEach(child => {
                const li = document.createElement('li');
                li.innerHTML = `<a class="dropdown-item" href="${child.url}">${child.name}</a>`;
                dropdownMenuElement.appendChild(li);
            });
        }
    }


    // --- Event Listeners for Breadcrumb Dropdowns ---

    // Area Breadcrumb Dropdown
    if (areaBreadcrumbContainer) {
        areaBreadcrumbContainer.addEventListener('show.bs.dropdown', function () {
            const dropdownMenu = this.querySelector('.dropdown-menu');
            const currentAreaId = parseInt(this.dataset.itemId);

            let allOtherAreas = allAreas.filter(a => a.id !== currentAreaId);

            let stepsInCurrentArea = [];
            if (currentAreaId) {
                stepsInCurrentArea = allSteps.filter(step => step.area_id === currentAreaId);
            }

            populateDropdown(dropdownMenu, allOtherAreas, currentAreaId, 'Steps in this Area:', true, stepsInCurrentArea);
        });
    }

    // Step Breadcrumb Dropdown
    if (stepBreadcrumbContainer) {
        stepBreadcrumbContainer.addEventListener('show.bs.dropdown', function () {
            const dropdownMenu = this.querySelector('.dropdown-menu');
            const currentStepId = parseInt(this.dataset.itemId);
            const parentAreaId = parseInt(this.dataset.parentAreaId);

            let otherStepsInSameArea = allSteps.filter(step =>
                step.id !== currentStepId &&
                step.area_id === parentAreaId // Only steps within the same logical parent area
            );

            let usecasesInCurrentStep = [];
            if (currentStepId) {
                usecasesInCurrentStep = allUsecases.filter(uc => uc.step_id === currentStepId);
            }
            
            populateDropdown(dropdownMenu, otherStepsInSameArea, currentStepId, 'Use Cases in this Step:', true, usecasesInCurrentStep);
        });
    }

    // Use Case Breadcrumb Dropdown
    if (usecaseBreadcrumbContainer) {
        usecaseBreadcrumbContainer.addEventListener('show.bs.dropdown', function () {
            const dropdownMenu = this.querySelector('.dropdown-menu');
            const currentUsecaseId = parseInt(this.dataset.itemId);
            const parentStepId = parseInt(this.dataset.parentStepId);

            let otherUsecasesInSameStep = allUsecases.filter(uc =>
                uc.id !== currentUsecaseId &&
                uc.step_id === parentStepId // Only use cases within the same logical parent step
            );

            // No children for use cases in the dropdown, just other use cases
            populateDropdown(dropdownMenu, otherUsecasesInSameStep, currentUsecaseId);
        });
    }
});