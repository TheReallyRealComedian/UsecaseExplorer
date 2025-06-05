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

    // Get breadcrumb container elements for DETAIL pages
    const areaBreadcrumbContainer = document.getElementById('area-breadcrumb-container');
    const stepBreadcrumbContainer = document.getElementById('step-breadcrumb-container');
    const usecaseBreadcrumbContainer = document.getElementById('usecase-breadcrumb-container');

    // NEW: Get breadcrumb container elements for OVERVIEW pages
    const allAreasBreadcrumbContainer = document.getElementById('all-areas-breadcrumb-container');
    const allStepsBreadcrumbContainer = document.getElementById('all-steps-breadcrumb-container');
    const allUsecasesBreadcrumbContainer = document.getElementById('all-usecases-breadcrumb-container');


    /**
     * Populates a Bootstrap dropdown menu with list items.
     * @param {HTMLElement} dropdownMenuElement The <ul> element for the dropdown menu.
     * @param {Array<Object>} items An array of objects, each with 'name' and 'url' properties.
     * @param {string|null} currentItemId (optional) The ID of the currently active item, to skip it from the list. Pass null for 'All' lists.
     * @param {string|null} separatorLabel (optional) Label for the separator if any items are listed after a separator.
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
        // Sort items alphabetically by name
        const sortedItems = [...items].sort((a, b) => a.name.localeCompare(b.name));

        sortedItems.forEach(item => {
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

            // Sort children items alphabetically by name
            const sortedChildrenItems = [...childrenItems].sort((a, b) => a.name.localeCompare(b.name));

            sortedChildrenItems.forEach(child => {
                const li = document.createElement('li');
                li.innerHTML = `<a class="dropdown-item" href="${child.url}">${child.name}</a>`;
                dropdownMenuElement.appendChild(li);
            });
        }
    }


    // --- Event Listeners for Breadcrumb Dropdowns (DETAIL Pages) ---

    // Area Breadcrumb Dropdown
    if (areaBreadcrumbContainer) {
        areaBreadcrumbContainer.addEventListener('show.bs.dropdown', function () {
            const dropdownMenu = this.querySelector('.dropdown-menu');
            const currentAreaId = parseInt(this.dataset.itemId);
    
            // Pass all areas to the dropdown. The currentAreaId is now for context if needed, not filtering.
            let stepsInCurrentArea = [];
            if (currentAreaId) {
                stepsInCurrentArea = allSteps.filter(step => step.area_id === currentAreaId);
            }
    
            // Populate with ALL areas, then steps in this area
            populateDropdown(dropdownMenu, allAreas, currentAreaId, 'Steps in this Area:', true, stepsInCurrentArea);
        });
    }

    // Step Breadcrumb Dropdown
    if (stepBreadcrumbContainer) {
        stepBreadcrumbContainer.addEventListener('show.bs.dropdown', function () {
            const dropdownMenu = this.querySelector('.dropdown-menu');
            const currentStepId = parseInt(this.dataset.itemId);
            const parentAreaId = parseInt(this.dataset.parentAreaId);
    
            // Get all steps in the same parent area
            let allStepsInSameArea = allSteps.filter(step =>
                step.area_id === parentAreaId
            );
    
            let usecasesInCurrentStep = [];
            if (currentStepId) {
                usecasesInCurrentStep = allUsecases.filter(uc => uc.step_id === currentStepId);
            }
            
            // Populate with all steps in the same area, then use cases in the current step
            populateDropdown(dropdownMenu, allStepsInSameArea, currentStepId, 'Use Cases in this Step:', true, usecasesInCurrentStep);
        });
    }

    // Use Case Breadcrumb Dropdown
    if (usecaseBreadcrumbContainer) {
        usecaseBreadcrumbContainer.addEventListener('show.bs.dropdown', function () {
            const dropdownMenu = this.querySelector('.dropdown-menu');
            const currentUsecaseId = parseInt(this.dataset.itemId);
            const parentStepId = parseInt(this.dataset.parentStepId);
    
            // Get all use cases in the same parent step
            let allUsecasesInSameStep = allUsecases.filter(uc =>
                uc.step_id === parentStepId
            );
    
            // Populate with all use cases in the same step
            populateDropdown(dropdownMenu, allUsecasesInSameStep, currentUsecaseId);
        });
    }

    // --- NEW: Event Listeners for Breadcrumb Dropdowns (OVERVIEW Pages) ---

    // All Areas Breadcrumb Dropdown
    if (allAreasBreadcrumbContainer) {
        allAreasBreadcrumbContainer.addEventListener('show.bs.dropdown', function () {
            const dropdownMenu = this.querySelector('.dropdown-menu');
            // For 'All Areas', we want to list ALL areas, so currentItemId is null, no children.
            populateDropdown(dropdownMenu, allAreas, null); 
        });
    }

    // All Steps Breadcrumb Dropdown
    if (allStepsBreadcrumbContainer) {
        allStepsBreadcrumbContainer.addEventListener('show.bs.dropdown', function () {
            const dropdownMenu = this.querySelector('.dropdown-menu');
            // For 'All Steps', we want to list ALL steps, so currentItemId is null, no children.
            populateDropdown(dropdownMenu, allSteps, null);
        });
    }

    // All Use Cases Breadcrumb Dropdown
    if (allUsecasesBreadcrumbContainer) {
        allUsecasesBreadcrumbContainer.addEventListener('show.bs.dropdown', function () {
            const dropdownMenu = this.querySelector('.dropdown-menu');
            // For 'All Use Cases', we want to list ALL use cases, so currentItemId is null, no children.
            populateDropdown(dropdownMenu, allUsecases, null);
        });
    }
});