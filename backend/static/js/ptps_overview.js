// backend/static/js/ptps_overview.js
(function() {
    'use strict';

    window.usecaseExplorer = window.usecaseExplorer || {};

    window.usecaseExplorer.initializePtpsOverview = function() {
        const dataIsland = document.getElementById('ptps-page-data-island');
        const pageData = dataIsland ? JSON.parse(dataIsland.textContent) : {};
        // The page_data will contain a key 'all_steps_for_js_filtering'
        // which has step.id, step.name, step.bi_id, step.area_id
        const allStepsDataForJS = pageData.all_steps_for_js_filtering || []; 
        const initialFilterAreaId = pageData.initial_filter_area_id || 'all'; // Get from page_data

        const ptpAreaFilterTabs = document.getElementById('ptpAreaFilterTabs');
        const processStepsOverviewTable = document.getElementById('processStepsOverviewTable');

        let activePtpsFilterAreaId = initialFilterAreaId; // Initialize with value from page_data

        /**
         * Applies the current area filter to the process steps table.
         * Shows or hides table rows based on the selected area ID.
         */
        function applyPtpsFilters() {
            if (!processStepsOverviewTable) return;

            const stepTableRows = processStepsOverviewTable.querySelectorAll('tbody tr');

            stepTableRows.forEach(row => {
                const rowAreaId = row.dataset.stepAreaId; // Get area ID from data attribute on the row
                let isVisible = true;

                // If a specific area is selected (not 'all'), and the row's area doesn't match, hide it.
                if (activePtpsFilterAreaId !== 'all' && rowAreaId !== activePtpsFilterAreaId) {
                    isVisible = false;
                }

                row.style.display = isVisible ? '' : 'none';
            });
        }

        // --- Event Listener for Area Filter Buttons ---
        if (ptpAreaFilterTabs) {
            ptpAreaFilterTabs.addEventListener('click', function(event) {
                const clickedButton = event.target.closest('button.btn');
                if (!clickedButton || !clickedButton.dataset.areaId) return; // Ensure a button with data-area-id was clicked

                // Remove 'active' class from all buttons and add to the clicked one
                ptpAreaFilterTabs.querySelectorAll('button.btn').forEach(btn => btn.classList.remove('active'));
                clickedButton.classList.add('active');

                // Update the active filter ID and re-apply filters
                activePtpsFilterAreaId = clickedButton.dataset.areaId;
                applyPtpsFilters();
            });
        }

        // --- Initial filter application based on URL parameter (or default) ---
        // Find and 'click' the corresponding button based on initialFilterAreaId
        const targetButton = ptpAreaFilterTabs.querySelector(`button[data-area-id="${initialFilterAreaId}"]`);
        if (targetButton) {
            targetButton.click(); // This will set activePtpsFilterAreaId and call applyPtpsFilters
        } else {
            // Fallback: If initialFilterAreaId somehow doesn't match a button, ensure 'All Areas' is active
            ptpAreaFilterTabs.querySelector('button[data-area-id="all"]').classList.add('active');
            activePtpsFilterAreaId = 'all'; // Ensure state is correct
            applyPtpsFilters(); // Apply filters explicitly
        }
    };
})();