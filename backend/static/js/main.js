// backend/static/js/main.js

(function() {
    'use strict';

    // Main app initialization
    document.addEventListener('DOMContentLoaded', function() {
        // Initialize common UI components that are on every page
        if (window.usecaseExplorer && typeof window.usecaseExplorer.initializeBreadcrumbs === 'function') {
            window.usecaseExplorer.initializeBreadcrumbs();
        }

        // If there's an editable cell on the page, initialize inline editing.
        if (document.querySelector('td.editable-cell') && typeof window.usecaseExplorer.initializeInlineTableEditing === 'function') {
            window.usecaseExplorer.initializeInlineTableEditing();
        }

        // If it's the use case overview page, initialize the filters.
        if (document.querySelector('.usecase-overview-page') && typeof window.usecaseExplorer.initializeUsecaseOverview === 'function') {
            window.usecaseExplorer.initializeUsecaseOverview();
        }
        
        // NEW: If it's the PTPS (Process Steps) page, initialize its specific overview logic.
        if (document.querySelector('.ptps-page') && typeof window.usecaseExplorer.initializePtpsOverview === 'function') {
            window.usecaseExplorer.initializePtpsOverview();
        }

        // Expose the table sorter to the global scope so it can be called from templates if needed
        // This is a bridge for any remaining inline scripts
        window.initializeTableSorter = function(tableId) {
            const table = document.getElementById(tableId);
            if (!table) return;

            const headers = table.querySelectorAll('th.sortable');

            headers.forEach(header => {
                header.addEventListener('click', () => {
                    const currentOrder = header.classList.contains('sorted-asc') ? 'asc' : (header.classList.contains('sorted-desc') ? 'desc' : 'none');
                    const sortOrder = (currentOrder === 'asc') ? 'desc' : 'asc';
                    
                    headers.forEach(th => th.classList.remove('sorted-asc', 'sorted-desc'));
                    header.classList.add(sortOrder === 'asc' ? 'sorted-asc' : 'sorted-desc');

                    const tbody = table.querySelector('tbody');
                    if (!tbody) return;
                    
                    const rows = Array.from(tbody.querySelectorAll('tr'));
                    const colIndex = Array.from(header.parentNode.children).indexOf(header);

                    rows.sort((a, b) => {
                        const valA = a.cells[colIndex]?.dataset.sortValue !== undefined ? a.cells[colIndex].dataset.sortValue : (a.cells[colIndex] ? a.cells[colIndex].textContent.trim() : '');
                        const valB = b.cells[colIndex]?.dataset.sortValue !== undefined ? b.cells[colIndex].dataset.sortValue : (b.cells[colIndex] ? b.cells[colIndex].textContent.trim() : '');

                        const numA = parseFloat(valA);
                        const numB = parseFloat(valB);

                        if (!isNaN(numA) && !isNaN(numB)) {
                            return sortOrder === 'asc' ? numA - numB : numB - numA;
                        } else {
                            return sortOrder === 'asc' 
                                ? valA.localeCompare(valB, undefined, { numeric: true, sensitivity: 'base' }) 
                                : valB.localeCompare(valA, undefined, { numeric: true, sensitivity: 'base' });
                        }
                    });

                    rows.forEach(row => tbody.appendChild(row));
                });
            });
        };

        // Initialize table sorters on pages that have them
        if (document.getElementById('areasOverviewTable')) {
            window.initializeTableSorter('areasOverviewTable');
        }
        if (document.getElementById('processStepsOverviewTable')) {
            window.initializeTableSorter('processStepsOverviewTable');
        }
    });

})();