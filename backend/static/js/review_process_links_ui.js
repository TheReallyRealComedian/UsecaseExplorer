// backend/static/js/review_process_links_ui.js

import { initializeLLMChat } from './common_llm_chat.js'; // Assuming this is still relevant for other parts of the page, otherwise remove

document.addEventListener('DOMContentLoaded', function () {
    const focusAreaSelect = document.getElementById('focusAreaSelect');
    const comparisonAreaSelect = document.getElementById('comparisonAreaSelect');
    const loadDiagramBtn = document.getElementById('loadDiagramBtn');
    const linksTableBody = document.getElementById('linksTableBody');
    const linksPlaceholder = document.getElementById('linksPlaceholder');
    const linksTable = document.getElementById('linksTable');
    const addNewLinkBtn = document.getElementById('addNewLinkBtn');

    // Filter Input Elements
    const filterSourceInput = document.getElementById('filterSource');
    const filterTargetInput = document.getElementById('filterTarget');
    const filterMinScoreInput = document.getElementById('filterMinScore');
    const filterMaxScoreInput = document.getElementById('filterMaxScore');
    const filterContentInput = document.getElementById('filterContent');

    // Modal DOM Elements
    const linkModalElement = document.getElementById('linkReviewModal');
    const modalLabel = document.getElementById('linkReviewModalLabel');
    const modalLinkIdInput = document.getElementById('modalLinkId');
    
    const modalSourceStepSelect = document.getElementById('modalSourceStepSelect');
    const modalTargetStepSelect = document.getElementById('modalTargetStepSelect');
    
    const modalRelevanceScoreInput = document.getElementById('modalRelevanceScore');
    const modalRelevanceContentInput = document.getElementById('modalRelevanceContent');
    const modalRelevanceContentPreview = document.getElementById('modalRelevanceContentPreview');
    const modalSaveLinkBtn = document.getElementById('modalSaveLinkBtn');
    const modalDeleteLinkBtn = document.getElementById('modalDeleteLinkBtn');

    // NEW: Delete All Links Button
    const deleteAllStepLinksBtn = document.getElementById('deleteAllStepLinksBtn');


    // Modal Instance
    let linkModal = null;

    // Store current link data fetched from the API
    let currentLinksData = [];
    let allStepsForModalSelects = []; 


    // --- Utility Functions ---
    function showFlashMessage(message, category = 'info') {
        const flashContainer = document.querySelector('.flash-messages') || document.createElement('div');
        if (!flashContainer.closest('.page-content')) {
            flashContainer.classList.add('flash-messages');
            const pageContent = document.querySelector('.page-content');
            if (pageContent) { pageContent.prepend(flashContainer); } else { document.body.prepend(flashContainer); }
        }
        const alertDiv = document.createElement('div');
        alertDiv.classList.add('alert', `alert-${category}`);
        alertDiv.textContent = message;
        flashContainer.appendChild(alertDiv);
        setTimeout(() => { alertDiv.remove(); }, 5000);
    }

    function sanitizeText(text) {
        if (text === null || text === undefined) return '';
        const div = document.createElement('div');
        div.textContent = text;
        return div.innerHTML;
    }

    function populateLinksTable(links) {
        linksTableBody.innerHTML = '';
        currentLinksData = links; 

        if (!links || links.length === 0) {
            linksPlaceholder.textContent = 'No relevance links found for the selected criteria.';
            linksPlaceholder.style.display = 'block';
            if (linksTable) linksTable.style.display = 'none';
            return;
        }

        linksPlaceholder.style.display = 'none';
        if (linksTable) linksTable.style.display = '';

        links.forEach(link => {
            const row = document.createElement('tr');
            row.dataset.linkId = link.id;
            row.innerHTML = `
                <td>${sanitizeText(link.source_step_name)}<br><small class="text-muted">(${sanitizeText(link.source_area_name)} - ${sanitizeText(link.source_step_bi_id)})</small></td>
                <td>${sanitizeText(link.target_step_name)}<br><small class="text-muted">(${sanitizeText(link.target_area_name)} - ${sanitizeText(link.target_step_bi_id)})</small></td>
                <td>${link.relevance_score}/100</td>
                <td><div class="content-snippet">${sanitizeText(link.relevance_content_snippet)}</div></td>
                <td>
                    <button class="btn btn-sm btn-secondary edit-link-btn me-1" data-link-id="${link.id}" title="Edit Link"><i class="fas fa-edit"></i></button>
                    <button class="btn btn-sm btn-danger delete-link-btn" data-link-id="${link.id}" title="Delete Link"><i class="fas fa-trash"></i></button>
                </td>
            `;
            linksTableBody.appendChild(row);
        });
    }

    // --- Client-Side Filtering ---
    function applyClientSideFilters() {
        const sourceTerm = filterSourceInput.value.toLowerCase().trim();
        const targetTerm = filterTargetInput.value.toLowerCase().trim();
        const minScore = parseInt(filterMinScoreInput.value);
        const maxScore = parseInt(filterMaxScoreInput.value);
        const contentTerm = filterContentInput.value.toLowerCase().trim();

        const filteredLinks = currentLinksData.filter(link => {
            const sourceMatch = !sourceTerm ||
                                (link.source_step_name && sanitizeText(link.source_step_name).toLowerCase().includes(sourceTerm)) ||
                                (link.source_step_bi_id && sanitizeText(link.source_step_bi_id).toLowerCase().includes(sourceTerm)) ||
                                (link.source_area_name && sanitizeText(link.source_area_name).toLowerCase().includes(sourceTerm));
            const targetMatch = !targetTerm ||
                                (link.target_step_name && sanitizeText(link.target_step_name).toLowerCase().includes(targetTerm)) ||
                                (link.target_step_bi_id && sanitizeText(link.target_step_bi_id).toLowerCase().includes(targetTerm)) ||
                                (link.target_area_name && sanitizeText(link.target_area_name).toLowerCase().includes(targetTerm));
            const scoreMatch = (isNaN(minScore) || link.relevance_score >= minScore) &&
                               (isNaN(maxScore) || link.relevance_score <= maxScore);
            const contentMatch = !contentTerm ||
                                 (link.relevance_content && sanitizeText(link.relevance_content).toLowerCase().includes(contentTerm));
            return sourceMatch && targetMatch && scoreMatch && contentMatch;
        });
        renderFilteredTable(filteredLinks);
    }

    function renderFilteredTable(linksToRender) {
        linksTableBody.innerHTML = '';
        if (!linksToRender || linksToRender.length === 0) {
            linksPlaceholder.textContent = 'No links match the current filters.';
            linksPlaceholder.style.display = 'block';
            if (linksTable) linksTable.style.display = 'none';
            return;
        }
        linksPlaceholder.style.display = 'none';
        if (linksTable) linksTable.style.display = '';
        linksToRender.forEach(link => {
            const row = document.createElement('tr');
            row.dataset.linkId = link.id;
            row.innerHTML = `
                <td>${sanitizeText(link.source_step_name)}<br><small class="text-muted">(${sanitizeText(link.source_area_name)} - ${sanitizeText(link.source_step_bi_id)})</small></td>
                <td>${sanitizeText(link.target_step_name)}<br><small class="text-muted">(${sanitizeText(link.target_area_name)} - ${sanitizeText(link.target_step_bi_id)})</small></td>
                <td>${link.relevance_score}/100</td>
                <td><div class="content-snippet">${sanitizeText(link.relevance_content_snippet)}</div></td>
                <td>
                    <button class="btn btn-sm btn-secondary edit-link-btn me-1" data-link-id="${link.id}" title="Edit Link"><i class="fas fa-edit"></i></button>
                    <button class="btn btn-sm btn-danger delete-link-btn" data-link-id="${link.id}" title="Delete Link"><i class="fas fa-trash"></i></button>
                </td>
            `;
            linksTableBody.appendChild(row);
        });
    }

    // --- Client-Side Sorting ---
    let currentSortColumn = null;
    let currentSortDirection = 'asc';
    function sortTable(columnKey) {
        const tbody = linksTable.querySelector('tbody');
        if (!tbody) return;
        
        const rows = Array.from(tbody.querySelectorAll('tr'));
        const linksToSort = rows.map(row => currentLinksData.find(l => l.id === parseInt(row.dataset.linkId))).filter(Boolean);


        if (currentSortColumn === columnKey) {
            currentSortDirection = currentSortDirection === 'asc' ? 'desc' : 'asc';
        } else {
            currentSortColumn = columnKey;
            currentSortDirection = 'asc';
        }

        linksTable.querySelectorAll('th').forEach(th => th.classList.remove('sorted-asc', 'sorted-desc'));
        const activeHeader = linksTable.querySelector(`th[data-sort="${columnKey}"]`);
        if (activeHeader) activeHeader.classList.add(`sorted-${currentSortDirection}`);

        linksToSort.sort((linkA, linkB) => {
            let valueA, valueB;
            switch (columnKey) {
                case 'source_step_name': valueA = linkA.source_step_name; valueB = linkB.source_step_name; break;
                case 'target_step_name': valueA = linkA.target_step_name; valueB = linkB.target_step_name; break;
                case 'relevance_score': valueA = linkA.relevance_score; valueB = linkB.relevance_score; break;
                case 'relevance_content_snippet': valueA = linkA.relevance_content || ""; valueB = linkB.relevance_content || ""; break;
                default: return 0;
            }

            if (typeof valueA === 'string') valueA = valueA.toLowerCase();
            if (typeof valueB === 'string') valueB = valueB.toLowerCase();
            
            if (columnKey === 'relevance_score') {
                valueA = Number(valueA);
                valueB = Number(valueB);
            }

            if (valueA < valueB) return currentSortDirection === 'asc' ? -1 : 1;
            if (valueA > valueB) return currentSortDirection === 'asc' ? 1 : -1;
            return 0;
        });
        renderFilteredTable(linksToSort);
    }

    async function handleDeleteLink(linkId) {
        if (!linkId) { showFlashMessage('Invalid link ID for deletion.', 'danger'); return; }
        if (confirm('Are you sure you want to delete this link? This action cannot be undone.')) {
            const rowToDelete = linksTableBody.querySelector(`tr[data-link-id="${linkId}"]`);
            if (rowToDelete) {
                rowToDelete.style.opacity = '0.5';
                const deleteButton = rowToDelete.querySelector('.delete-link-btn');
                if (deleteButton) deleteButton.disabled = true;
            }
            try {
                const response = await fetch(`/review/api/process-links/link/${linkId}`, { method: 'DELETE' });
                const result = await response.json();
                if (result.success) {
                    showFlashMessage(result.message, 'success');
                    if (currentLinksData) {
                         currentLinksData = currentLinksData.filter(link => link.id !== linkId);
                         applyClientSideFilters(); 
                    }
                } else {
                    showFlashMessage(`Error: ${result.error || 'Could not delete link.'}`, 'danger');
                    if (rowToDelete) {
                        rowToDelete.style.opacity = '1';
                        const deleteButton = rowToDelete.querySelector('.delete-link-btn');
                        if (deleteButton) deleteButton.disabled = false;
                    }
                }
            } catch (error) {
                 showFlashMessage(`Network error: ${error.message}`, 'danger');
                 if (rowToDelete) {
                    rowToDelete.style.opacity = '1';
                    const deleteButton = rowToDelete.querySelector('.delete-link-btn');
                    if (deleteButton) deleteButton.disabled = false;
                 }
            }
        }
    }

    function getLinkModal() {
         if (!linkModal) {
            if (linkModalElement && typeof window.bootstrap !== 'undefined' && typeof window.bootstrap.Modal === 'function') {
                linkModal = new window.bootstrap.Modal(linkModalElement);
            } else { console.error("Link review modal element or Bootstrap Modal library not found."); return null; }
         }
         return linkModal;
    }
    
    function populateStepSelect(selectElement, steps, selectedValue = null) {
        selectElement.innerHTML = '<option value="">-- Select Step --</option>'; 
        if (steps && steps.length > 0) {
            const sortedSteps = [...steps].sort((a, b) => (a.name || '').localeCompare(b.name || ''));
            sortedSteps.forEach(step => {
                const optionText = `${sanitizeText(step.name)} (${sanitizeText(step.area_name)} - BI_ID: ${sanitizeText(step.bi_id)})`;
                const option = new Option(optionText, step.id);
                if (selectedValue && parseInt(selectedValue) === step.id) {
                    option.selected = true;
                }
                selectElement.appendChild(option);
            });
        }
    }


    async function openLinkModal(linkId = null) {
        const modal = getLinkModal();
        if (!modal) return;

        modalLinkIdInput.value = '';
        modalRelevanceScoreInput.value = '50';
        modalRelevanceContentInput.value = '';
        modalRelevanceContentPreview.innerHTML = typeof marked !== 'undefined' && marked.parse ? marked.parse('<em>No content provided.</em>') : '<em>No content provided.</em>';
        modalDeleteLinkBtn.style.display = 'none';
        modalSaveLinkBtn.textContent = 'Save Link';
        modalSaveLinkBtn.disabled = false;
        modalDeleteLinkBtn.disabled = false;

        populateStepSelect(modalSourceStepSelect, allStepsForModalSelects);
        populateStepSelect(modalTargetStepSelect, allStepsForModalSelects);
        
        if (linkId) {
            modalLabel.textContent = 'Review/Edit Link';
            modalLinkIdInput.value = linkId;
            modalSaveLinkBtn.textContent = 'Save Changes';
            modalDeleteLinkBtn.style.display = 'block';
            try {
                const response = await fetch(`/review/api/process-links/link/${linkId}`);
                if (!response.ok) throw new Error('Failed to fetch link details.');
                const linkData = await response.json();
                if (linkData.error) throw new Error(linkData.error);

                modalSourceStepSelect.value = linkData.source_step_id;
                modalTargetStepSelect.value = linkData.target_step_id;
                
                modalRelevanceScoreInput.value = linkData.relevance_score;
                modalRelevanceContentInput.value = linkData.relevance_content || '';
                modalRelevanceContentPreview.innerHTML = typeof marked !== 'undefined' && marked.parse ? (linkData.relevance_content ? marked.parse(linkData.relevance_content) : marked.parse('<em>No content provided.</em>')) : (linkData.relevance_content || 'No content provided.');
            } catch (error) {
                showFlashMessage(`Error loading link details: ${error.message}`, 'danger');
                if (modal) modal.hide(); return;
            }
        } else {
             modalLabel.textContent = 'Create New Link';
             modalSourceStepSelect.value = "";
             modalTargetStepSelect.value = "";
        }
        if (modal) modal.show();
    }

    if (loadDiagramBtn) {
        loadDiagramBtn.addEventListener('click', async () => {
            const focusAreaId = focusAreaSelect.value;
            const selectedComparisonOptions = Array.from(comparisonAreaSelect.selectedOptions);
            const comparisonAreaIds = selectedComparisonOptions.map(opt => opt.value).filter(id => id !== "");
            if (!focusAreaId) { showFlashMessage('Please select a Focus Area.', 'warning'); return; }
            loadDiagramBtn.disabled = true;
            loadDiagramBtn.innerHTML = '<span class="spinner-border spinner-border-sm"></span> Loading...';
            linksPlaceholder.textContent = 'Loading links...';
            linksPlaceholder.style.display = 'block';
            linksTableBody.innerHTML = '';
            if (linksTable) linksTable.style.display = 'none';
            try {
                const params = new URLSearchParams({ focus_area_id: focusAreaId });
                comparisonAreaIds.forEach(id => params.append('comparison_area_ids[]', id));
                const response = await fetch(`/review/api/process-links/data?${params.toString()}`);
                if (!response.ok) {
                     let errorMsg = `Server error: ${response.status}`;
                    try { const errorData = await response.json(); errorMsg = errorData.error || errorMsg; } catch (e) {}
                    throw new Error(errorMsg);
                }
                const data = await response.json();
                if (data.error) { throw new Error(data.error); }
                currentLinksData = data.links || []; 
                populateLinksTable(currentLinksData); 
                applyClientSideFilters(); 
            } catch (error) {
                showFlashMessage(`Error loading links: ${error.message}`, 'danger');
                 linksPlaceholder.textContent = `Error loading links: ${error.message}.`;
                 linksPlaceholder.style.display = 'block';
                 currentLinksData = [];
            } finally {
                loadDiagramBtn.disabled = false;
                loadDiagramBtn.innerHTML = 'Load Links';
            }
        });
    }

    if (addNewLinkBtn) {
         addNewLinkBtn.addEventListener('click', () => { openLinkModal(null); });
    }

    if (linksTableBody) {
        linksTableBody.addEventListener('click', function(event) {
            const targetButton = event.target.closest('button');
            if (!targetButton) return;
            const linkId = targetButton.dataset.linkId;
            if (targetButton.classList.contains('edit-link-btn') && linkId) {
                 openLinkModal(parseInt(linkId));
            } else if (targetButton.classList.contains('delete-link-btn') && linkId) {
                 handleDeleteLink(parseInt(linkId));
            }
        });
    }

    if (filterSourceInput) filterSourceInput.addEventListener('input', applyClientSideFilters);
    if (filterTargetInput) filterTargetInput.addEventListener('input', applyClientSideFilters);
    if (filterMinScoreInput) filterMinScoreInput.addEventListener('input', applyClientSideFilters);
    if (filterMaxScoreInput) filterMaxScoreInput.addEventListener('input', applyClientSideFilters);
    if (filterContentInput) filterContentInput.addEventListener('input', applyClientSideFilters);

    if (linksTable) {
         linksTable.querySelectorAll('th[data-sort]').forEach(header => {
             header.addEventListener('click', function() {
                 const sortKey = this.dataset.sort;
                 if (sortKey) sortTable(sortKey);
             });
         });
    }

    if (modalRelevanceContentInput && modalRelevanceContentPreview) {
        modalRelevanceContentInput.addEventListener('input', function() {
            modalRelevanceContentPreview.innerHTML = typeof marked !== 'undefined' && marked.parse ? (this.value ? marked.parse(this.value) : marked.parse('<em>No content provided.</em>')) : (this.value || 'No content provided.');
        });
    }

    if (modalSaveLinkBtn) {
        modalSaveLinkBtn.addEventListener('click', async () => {
            const modal = getLinkModal();
            if (!modal) return;
            
            const linkId = modalLinkIdInput.value ? parseInt(modalLinkIdInput.value) : null;
            const score = parseInt(modalRelevanceScoreInput.value);
            const content = modalRelevanceContentInput.value;

            const selectedSourceStepId = modalSourceStepSelect.value;
            const selectedTargetStepId = modalTargetStepSelect.value;

            if (!selectedSourceStepId || !selectedTargetStepId) {
                showFlashMessage('Please select both source and target process steps.', 'warning');
                return;
            }
            if (selectedSourceStepId === selectedTargetStepId) {
                showFlashMessage('Source and Target steps cannot be the same.', 'warning');
                return;
            }
            if (isNaN(score) || score < 0 || score > 100) {
                showFlashMessage('Relevance score must be a number between 0 and 100.', 'warning');
                return;
            }

            modalSaveLinkBtn.disabled = true;
            modalSaveLinkBtn.innerHTML = '<span class="spinner-border spinner-border-sm"></span> Saving...';
            
            const payload = { 
                relevance_score: score, 
                relevance_content: content.trim() === '' ? null : content.trim(),
                source_step_id: parseInt(selectedSourceStepId), 
                target_step_id: parseInt(selectedTargetStepId) 
            };
            
            let url, method;
            if (linkId) { 
                url = `/review/api/process-links/link/${linkId}`; 
                method = 'PUT';
            } else { 
                url = `/review/api/process-links/link`; 
                method = 'POST';
            }

            try {
                const response = await fetch(url, { 
                    method: method, 
                    headers: { 'Content-Type': 'application/json' }, 
                    body: JSON.stringify(payload) 
                });
                const result = await response.json();
                if (result.success) {
                    showFlashMessage(result.message, 'success');
                    if (modal) modal.hide();
                    if (loadDiagramBtn) loadDiagramBtn.click(); 
                } else { 
                    showFlashMessage(`Error: ${result.error || 'Could not save link.'}`, 'danger');
                }
            } catch (error) { 
                showFlashMessage(`Network error: ${error.message}`, 'danger');
            } finally {
                 modalSaveLinkBtn.disabled = false;
                 modalSaveLinkBtn.innerHTML = linkId ? 'Save Changes' : 'Save Link';
            }
        });
    }

    if (modalDeleteLinkBtn) {
        modalDeleteLinkBtn.addEventListener('click', async () => {
             const modal = getLinkModal(); if (!modal) return;
            const linkId = modalLinkIdInput.value ? parseInt(modalLinkIdInput.value) : null;
            if (!linkId) return;
            if (confirm('Are you sure you want to delete this link? This action cannot be undone.')) {
                modalDeleteLinkBtn.disabled = true; modalSaveLinkBtn.disabled = true;
                modalDeleteLinkBtn.innerHTML = '<span class="spinner-border spinner-border-sm"></span> Deleting...';
                try {
                    const response = await fetch(`/review/api/process-links/link/${linkId}`, { method: 'DELETE' });
                    const result = await response.json();
                    if (result.success) {
                        showFlashMessage(result.message, 'success');
                        if (modal) modal.hide();
                        if (loadDiagramBtn) loadDiagramBtn.click(); 
                    } else { 
                        showFlashMessage(`Error: ${result.error || 'Could not delete link.'}`, 'danger'); 
                    }
                } catch (error) { 
                    showFlashMessage(`Network error: ${error.message}`, 'danger');
                } finally {
                     modalDeleteLinkBtn.disabled = false; modalSaveLinkBtn.disabled = false;
                     modalDeleteLinkBtn.innerHTML = 'Delete Link';
                }
            }
        });
    }

    if (focusAreaSelect && comparisonAreaSelect) {
        focusAreaSelect.addEventListener('change', function() {
            const focusValue = this.value;
            Array.from(comparisonAreaSelect.options).forEach(opt => {
                opt.disabled = (opt.value === focusValue && focusValue !== "");
                if (opt.disabled && opt.selected) { opt.selected = false; }
            });
        });
        focusAreaSelect.dispatchEvent(new Event('change'));
    }

    async function fetchAllStepsForModalSelects() { 
         try {
             const response = await fetch('/steps/api/all'); 
             if (!response.ok) throw new Error('Failed to fetch all steps for select dropdowns.');
             const stepsData = await response.json();
             allStepsForModalSelects = stepsData; 
             console.log(`Fetched ${allStepsForModalSelects.length} steps for modal selects.`);
             
             if (modalSourceStepSelect) populateStepSelect(modalSourceStepSelect, allStepsForModalSelects);
             if (modalTargetStepSelect) populateStepSelect(modalTargetStepSelect, allStepsForModalSelects);

         } catch (error) {
             console.error('Error fetching all steps for modal selects:', error);
             showFlashMessage('Could not load steps for link creation/editing.', 'danger');
         }
    }
    fetchAllStepsForModalSelects(); 

    // --- NEW: Delete All Step Links Functionality ---
    if (deleteAllStepLinksBtn) {
        deleteAllStepLinksBtn.addEventListener('click', async () => {
            const confirmationText = "Are you absolutely sure you want to delete ALL links between process steps? This action cannot be undone and will remove all existing step-to-step relevance links.";
            if (confirm(confirmationText)) {
                const finalConfirmation = prompt("To confirm, please type 'DELETE ALL LINKS' (all uppercase) in the box below:");
                if (finalConfirmation === "DELETE ALL LINKS") {
                    deleteAllStepLinksBtn.disabled = true;
                    deleteAllStepLinksBtn.innerHTML = '<span class="spinner-border spinner-border-sm"></span> Deleting...';
                    try {
                        const response = await fetch('/review/api/process-links/delete-all', {
                            method: 'POST',
                            headers: {
                                'Content-Type': 'application/json',
                                // Add CSRF token header if your application uses them for POST requests
                                // 'X-CSRFToken': getCsrfToken() // Example
                            }
                        });
                        const result = await response.json();
                        if (response.ok && result.success) {
                            showFlashMessage(result.message || 'All process step links deleted successfully.', 'success');
                            currentLinksData = []; // Clear local data store
                            populateLinksTable(currentLinksData); // Refresh table (will show as empty)
                        } else {
                            showFlashMessage(`Error: ${result.error || 'Could not delete all links.'}`, 'danger');
                        }
                    } catch (error) {
                        showFlashMessage(`Network error: ${error.message}`, 'danger');
                        console.error("Error deleting all step links:", error);
                    } finally {
                        deleteAllStepLinksBtn.disabled = false;
                        deleteAllStepLinksBtn.innerHTML = '<i class="fas fa-trash-alt me-1"></i> Delete All Step-to-Step Links';
                    }
                } else if (finalConfirmation !== null) { // User typed something but it was wrong
                    alert("Incorrect confirmation text. Action cancelled.");
                } else { // User cancelled the prompt
                    alert("Action cancelled.");
                }
            }
        });
    }
    // --- END NEW ---


    window.cleanupReviewProcessLinksUI = function() {
        if (linkModal && typeof linkModal.dispose === 'function') {
            linkModal.dispose();
            linkModal = null;
        }
        // Remove other event listeners if necessary, though usually not needed if elements are removed/page changes
        // NEW: Cleanup for delete all button if dynamic listeners were added (not the case here)
        // if (deleteAllStepLinksBtn) { /* remove listeners if any */ }
    };

});