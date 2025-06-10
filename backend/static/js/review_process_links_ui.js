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

    const deleteAllStepLinksBtn = document.getElementById('deleteAllStepLinksBtn');

    // NEW: Download CSV Button
    const downloadLinksCsvBtn = document.getElementById('downloadLinksCsvBtn');


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
            if (downloadLinksCsvBtn) downloadLinksCsvBtn.style.display = 'none'; // Hide download button
            return;
        }

        linksPlaceholder.style.display = 'none';
        if (linksTable) linksTable.style.display = '';
        if (downloadLinksCsvBtn) downloadLinksCsvBtn.style.display = 'inline-block'; // Show download button


        links.forEach(link => {
            const row = document.createElement('tr');
            row.dataset.linkId = link.id;
            // Store all necessary data for CSV export on the row itself or ensure currentLinksData is used for CSV generation
            row.dataset.sourceStepName = link.source_step_name;
            row.dataset.sourceAreaName = link.source_area_name;
            row.dataset.sourceStepBiId = link.source_step_bi_id;
            row.dataset.targetStepName = link.target_step_name;
            row.dataset.targetAreaName = link.target_area_name;
            row.dataset.targetStepBiId = link.target_step_bi_id;
            row.dataset.relevanceScore = link.relevance_score;
            row.dataset.relevanceContent = link.relevance_content || "";


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
            if (downloadLinksCsvBtn) downloadLinksCsvBtn.style.display = 'none'; // Hide download button
            return;
        }
        linksPlaceholder.style.display = 'none';
        if (linksTable) linksTable.style.display = '';
        if (downloadLinksCsvBtn) downloadLinksCsvBtn.style.display = 'inline-block'; // Show download button

        linksToRender.forEach(link => {
            const row = document.createElement('tr');
            row.dataset.linkId = link.id;
            // Store all necessary data for CSV export on the row itself
            row.dataset.sourceStepName = link.source_step_name;
            row.dataset.sourceAreaName = link.source_area_name;
            row.dataset.sourceStepBiId = link.source_step_bi_id;
            row.dataset.targetStepName = link.target_step_name;
            row.dataset.targetAreaName = link.target_area_name;
            row.dataset.targetStepBiId = link.target_step_bi_id;
            row.dataset.relevanceScore = link.relevance_score;
            row.dataset.relevanceContent = link.relevance_content || ""; // Ensure content is always a string

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
        // Get the data for sorting directly from the row's dataset attributes
        // to ensure we sort what's currently displayed and filtered.
        const linksToSort = rows.map(row => ({
            id: parseInt(row.dataset.linkId),
            source_step_name: row.dataset.sourceStepName,
            source_area_name: row.dataset.sourceAreaName,
            source_step_bi_id: row.dataset.sourceStepBiId,
            target_step_name: row.dataset.targetStepName,
            target_area_name: row.dataset.targetAreaName,
            target_step_bi_id: row.dataset.targetStepBiId,
            relevance_score: parseInt(row.dataset.relevanceScore),
            relevance_content: row.dataset.relevanceContent,
            // relevance_content_snippet can be derived if needed or use relevance_content
        }));


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
                case 'relevance_content_snippet': valueA = linkA.relevance_content || ""; valueB = linkB.relevance_content || ""; break; // Sort by full content
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
        renderFilteredTable(linksToSort); // Re-render the sorted subset
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
            if (downloadLinksCsvBtn) downloadLinksCsvBtn.style.display = 'none'; // Hide download btn during load
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
                 if (downloadLinksCsvBtn) downloadLinksCsvBtn.style.display = 'none';
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
                            }
                        });
                        const result = await response.json();
                        if (response.ok && result.success) {
                            showFlashMessage(result.message || 'All process step links deleted successfully.', 'success');
                            currentLinksData = []; 
                            populateLinksTable(currentLinksData); 
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
                } else if (finalConfirmation !== null) { 
                    alert("Incorrect confirmation text. Action cancelled.");
                } else { 
                    alert("Action cancelled.");
                }
            }
        });
    }

    // --- NEW: CSV Download Functionality ---
    function escapeCsvField(field, delimiter = ';') { // Added delimiter parameter, defaults to semicolon
        if (field === null || field === undefined) {
            return "";
        }
        const stringField = String(field);
        // If the field contains the delimiter, double quote, or newline, enclose it in double quotes
        // and escape any existing double quotes by doubling them.
        if (stringField.includes(delimiter) || stringField.includes('"') || stringField.includes('\n') || stringField.includes('\r')) {
            return `"${stringField.replace(/"/g, '""')}"`;
        }
        return stringField;
    }

    function downloadCsv(data, filename = 'export.csv', delimiter = ';') { // Added delimiter parameter
        const csvRows = [];
        const headers = [
            "Source Step Name", "Source Area", "Source BI_ID",
            "Target Step Name", "Target Area", "Target BI_ID",
            "Score", "Content"
        ];
        // Escape headers themselves in case they contain the delimiter (unlikely here, but good practice)
        csvRows.push(headers.map(header => escapeCsvField(header, delimiter)).join(delimiter));

        data.forEach(row => {
            const csvRow = [
                escapeCsvField(row.source_step_name, delimiter),
                escapeCsvField(row.source_area_name, delimiter),
                escapeCsvField(row.source_step_bi_id, delimiter),
                escapeCsvField(row.target_step_name, delimiter),
                escapeCsvField(row.target_area_name, delimiter),
                escapeCsvField(row.target_step_bi_id, delimiter),
                escapeCsvField(row.relevance_score, delimiter),
                escapeCsvField(row.relevance_content, delimiter) // Use full content for CSV
            ].join(delimiter); // Use the specified delimiter
            csvRows.push(csvRow);
        });

        const csvString = csvRows.join('\r\n');
        // Ensure UTF-8 BOM for better Excel compatibility with special characters
        const BOM = "\uFEFF"; 
        const blob = new Blob([BOM + csvString], { type: 'text/csv;charset=utf-8;' });
        const link = document.createElement('a');
        if (link.download !== undefined) { // Feature detection
            const url = URL.createObjectURL(blob);
            link.setAttribute('href', url);
            link.setAttribute('download', filename);
            link.style.visibility = 'hidden';
            document.body.appendChild(link);
            link.click();
            document.body.removeChild(link);
            URL.revokeObjectURL(url);
        } else {
            alert("CSV download is not supported by your browser.");
        }
    }

    if (downloadLinksCsvBtn) {
        downloadLinksCsvBtn.addEventListener('click', () => {
            // Get currently visible rows from the table
            const visibleRows = Array.from(linksTableBody.querySelectorAll('tr'));
            if (visibleRows.length === 0) {
                showFlashMessage('No data to download.', 'info');
                return;
            }

            const dataToExport = visibleRows.map(row => {
                // Extract data from the row's dataset attributes
                return {
                    source_step_name: row.dataset.sourceStepName,
                    source_area_name: row.dataset.sourceAreaName,
                    source_step_bi_id: row.dataset.sourceStepBiId,
                    target_step_name: row.dataset.targetStepName,
                    target_area_name: row.dataset.targetAreaName,
                    target_step_bi_id: row.dataset.targetStepBiId,
                    relevance_score: parseInt(row.dataset.relevanceScore),
                    relevance_content: row.dataset.relevanceContent
                };
            });

            const timestamp = new Date().toISOString().slice(0, 19).replace(/[-T:]/g, "");
            // Call downloadCsv with the semicolon delimiter
            downloadCsv(dataToExport, `process_step_links_${timestamp}.csv`, ';'); 
        });
    }
    // --- END NEW CSV Download ---


    window.cleanupReviewProcessLinksUI = function() {
        if (linkModal && typeof linkModal.dispose === 'function') {
            linkModal.dispose();
            linkModal = null;
        }
    };

});