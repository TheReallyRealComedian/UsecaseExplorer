// backend/static/js/main.js

/**
 * Initializes sorting functionality for a table with 'sortable' headers.
 * @param {string} tableId The ID of the table element to make sortable.
 */
function initializeTableSorter(tableId) {
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
                const valA = a.cells[colIndex]?.dataset.sortValue !== undefined ? a.cells[colIndex].dataset.sortValue : a.cells[colIndex]?.textContent.trim() || '';
                const valB = b.cells[colIndex]?.dataset.sortValue !== undefined ? b.cells[colIndex].dataset.sortValue : b.cells[colIndex]?.textContent.trim() || '';

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
}

// Expose the function to the global scope so it can be called from templates.
window.initializeTableSorter = initializeTableSorter;