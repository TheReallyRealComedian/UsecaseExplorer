// backend/static/js/breadcrumb_ui.js
(function() {
    'use strict';

    // App-specific namespace on the window object
    window.usecaseExplorer = window.usecaseExplorer || {};

    window.usecaseExplorer.initializeBreadcrumbs = function() {
        // Cache for navigation data to avoid re-fetching on every dropdown click
        let navDataCache = null;

        /**
         * Fetches and caches navigation data from the API.
         * @returns {Promise<Object>} A promise that resolves with the navigation data.
         */
        async function getNavigationData() {
            if (navDataCache) {
                return navDataCache;
            }
            try {
                const response = await fetch('/api/navigation_data');
                if (!response.ok) {
                    throw new Error(`Network response was not ok: ${response.statusText}`);
                }
                const data = await response.json();
                navDataCache = data; // Cache the successful response
                return navDataCache;
            } catch (error) {
                console.error('Failed to fetch navigation data:', error);
                // Return empty object on failure to prevent further errors
                return { areas: [], steps: [], usecases: [] };
            }
        }

        // Get breadcrumb container elements
        const areaBreadcrumbContainer = document.getElementById('area-breadcrumb-container');
        const stepBreadcrumbContainer = document.getElementById('step-breadcrumb-container');
        const usecaseBreadcrumbContainer = document.getElementById('usecase-breadcrumb-container');
        const allAreasBreadcrumbContainer = document.getElementById('all-areas-breadcrumb-container');
        const allStepsBreadcrumbContainer = document.getElementById('all-steps-breadcrumb-container');
        const allUsecasesBreadcrumbContainer = document.getElementById('all-usecases-breadcrumb-container');


        function populateDropdown(dropdownMenuElement, items, currentItemId = null, separatorLabel = null, addSeparator = false, childrenItems = []) {
            dropdownMenuElement.innerHTML = ''; // Clear existing items

            if (!items || items.length === 0) {
                const li = document.createElement('li');
                li.innerHTML = '<span class="dropdown-item text-muted">No items found.</span>';
                dropdownMenuElement.appendChild(li);
                return;
            }

            let addedCount = 0;
            const sortedItems = [...items].sort((a, b) => a.name.localeCompare(b.name));

            sortedItems.forEach(item => {
                const li = document.createElement('li');
                li.innerHTML = `<a class="dropdown-item" href="${item.url}">${item.name}</a>`;
                dropdownMenuElement.appendChild(li);
                addedCount++;
            });

            if (addSeparator && childrenItems && childrenItems.length > 0) {
                if (addedCount > 0) {
                    const divider = document.createElement('li');
                    divider.innerHTML = '<hr class="dropdown-divider">';
                    dropdownMenuElement.appendChild(divider);
                }
                const labelLi = document.createElement('li');
                labelLi.innerHTML = `<h6 class="dropdown-header">${separatorLabel}</h6>`;
                dropdownMenuElement.appendChild(labelLi);

                const sortedChildrenItems = [...childrenItems].sort((a, b) => a.name.localeCompare(b.name));

                sortedChildrenItems.forEach(child => {
                    const li = document.createElement('li');
                    li.innerHTML = `<a class="dropdown-item" href="${child.url}">${child.name}</a>`;
                    dropdownMenuElement.appendChild(li);
                });
            }
        }

        // Event Listeners for Breadcrumb Dropdowns
        if (areaBreadcrumbContainer) {
            areaBreadcrumbContainer.addEventListener('show.bs.dropdown', async function () {
                const dropdownMenu = this.querySelector('.dropdown-menu');
                dropdownMenu.innerHTML = '<li><span class="dropdown-item text-muted">Loading...</span></li>';
                const currentAreaId = parseInt(this.dataset.itemId);
                
                const navData = await getNavigationData();
                const allAreas = navData.areas;
                const allSteps = navData.steps;
        
                let stepsInCurrentArea = [];
                if (currentAreaId) {
                    stepsInCurrentArea = allSteps.filter(step => step.area_id === currentAreaId);
                }
        
                populateDropdown(dropdownMenu, allAreas, currentAreaId, 'Steps in this Area:', true, stepsInCurrentArea);
            });
        }

        if (stepBreadcrumbContainer) {
            stepBreadcrumbContainer.addEventListener('show.bs.dropdown', async function () {
                const dropdownMenu = this.querySelector('.dropdown-menu');
                dropdownMenu.innerHTML = '<li><span class="dropdown-item text-muted">Loading...</span></li>';
                const currentStepId = parseInt(this.dataset.itemId);
                const parentAreaId = parseInt(this.dataset.parentAreaId);

                const navData = await getNavigationData();
                const allSteps = navData.steps;
                const allUsecases = navData.usecases;

                let allStepsInSameArea = allSteps.filter(step => step.area_id === parentAreaId);
                let usecasesInCurrentStep = [];
                if (currentStepId) {
                    usecasesInCurrentStep = allUsecases.filter(uc => uc.step_id === currentStepId);
                }
                
                populateDropdown(dropdownMenu, allStepsInSameArea, currentStepId, 'Use Cases in this Step:', true, usecasesInCurrentStep);
            });
        }

        if (usecaseBreadcrumbContainer) {
            usecaseBreadcrumbContainer.addEventListener('show.bs.dropdown', async function () {
                const dropdownMenu = this.querySelector('.dropdown-menu');
                dropdownMenu.innerHTML = '<li><span class="dropdown-item text-muted">Loading...</span></li>';
                const currentUsecaseId = parseInt(this.dataset.itemId);
                const parentStepId = parseInt(this.dataset.parentStepId);
                
                const navData = await getNavigationData();
                const allUsecases = navData.usecases;
        
                let allUsecasesInSameStep = allUsecases.filter(uc => uc.step_id === parentStepId);
        
                populateDropdown(dropdownMenu, allUsecasesInSameStep, currentUsecaseId);
            });
        }

        if (allAreasBreadcrumbContainer) {
            allAreasBreadcrumbContainer.addEventListener('show.bs.dropdown', async function () {
                const dropdownMenu = this.querySelector('.dropdown-menu');
                dropdownMenu.innerHTML = '<li><span class="dropdown-item text-muted">Loading...</span></li>';
                const navData = await getNavigationData();
                populateDropdown(dropdownMenu, navData.areas, null); 
            });
        }

        if (allStepsBreadcrumbContainer) {
            allStepsBreadcrumbContainer.addEventListener('show.bs.dropdown', async function () {
                const dropdownMenu = this.querySelector('.dropdown-menu');
                dropdownMenu.innerHTML = '<li><span class="dropdown-item text-muted">Loading...</span></li>';
                const navData = await getNavigationData();
                populateDropdown(dropdownMenu, navData.steps, null);
            });
        }

        if (allUsecasesBreadcrumbContainer) {
            allUsecasesBreadcrumbContainer.addEventListener('show.bs.dropdown', async function () {
                const dropdownMenu = this.querySelector('.dropdown-menu');
                dropdownMenu.innerHTML = '<li><span class="dropdown-item text-muted">Loading...</span></li>';
                const navData = await getNavigationData();
                populateDropdown(dropdownMenu, navData.usecases, null);
            });
        }
    };
})();