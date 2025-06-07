// backend/static/js/review_process_links_ui.js

import { initializeLLMChat } from './common_llm_chat.js';

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
    const modalSourceStepIdInput = document.getElementById('modalSourceStepId');
    const modalTargetStepIdInput = document.getElementById('modalTargetStepId');
    const modalSourceStepDisplay = document.getElementById('modalSourceStepDisplay');
    const modalTargetStepDisplay = document.getElementById('modalTargetStepDisplay');
    const modalRelevanceScoreInput = document.getElementById('modalRelevanceScore');
    const modalRelevanceContentInput = document.getElementById('modalRelevanceContent');
    const modalRelevanceContentPreview = document.getElementById('modalRelevanceContentPreview');
    const modalSaveLinkBtn = document.getElementById('modalSaveLinkBtn');
    const modalDeleteLinkBtn = document.getElementById('modalDeleteLinkBtn');

    // Modal Instance
    let linkModal = null;

    // Store current link data fetched from the API
    let currentLinksData = [];
    let allStepsForTargetSelect = [];


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

        if (currentSortColumn === columnKey) {
            currentSortDirection = currentSortDirection === 'asc' ? 'desc' : 'asc';
        } else {
            currentSortColumn = columnKey;
            currentSortDirection = 'asc';
        }

        linksTable.querySelectorAll('th').forEach(th => th.classList.remove('sorted-asc', 'sorted-desc'));
        const activeHeader = linksTable.querySelector(`th[data-sort="${columnKey}"]`);
        if (activeHeader) activeHeader.classList.add(`sorted-${currentSortDirection}`);

        rows.sort((rowA, rowB) => {
            const linkA = currentLinksData.find(l => l.id === parseInt(rowA.dataset.linkId));
            const linkB = currentLinksData.find(l => l.id === parseInt(rowB.dataset.linkId));
            if (!linkA || !linkB) return 0;

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

            if (valueA < valueB) return currentSortDirection === 'asc' ? -1 : 1;
            if (valueA > valueB) return currentSortDirection === 'asc' ? 1 : -1;
            return 0;
        });
        tbody.innerHTML = '';
        rows.forEach(row => tbody.appendChild(row));
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

    async function openLinkModal(linkId = null, sourceStepIdFromButton = null) {
        const modal = getLinkModal();
        if (!modal) return;

        modalLinkIdInput.value = '';
        modalSourceStepIdInput.value = '';
        modalTargetStepIdInput.value = '';
        modalSourceStepDisplay.textContent = 'Loading...';
        modalTargetStepDisplay.innerHTML = 'Loading...';
        modalRelevanceScoreInput.value = '50';
        modalRelevanceContentInput.value = '';
        modalRelevanceContentPreview.innerHTML = typeof marked !== 'undefined' && marked.parse ? marked.parse('<em>No content provided.</em>') : '<em>No content provided.</em>';
        modalDeleteLinkBtn.style.display = 'none';
        modalSaveLinkBtn.textContent = 'Save Link';
        modalSaveLinkBtn.disabled = false;
        modalDeleteLinkBtn.disabled = false;

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
                modalSourceStepIdInput.value = linkData.source_step_id;
                modalTargetStepIdInput.value = linkData.target_step_id;
                modalSourceStepDisplay.textContent = `${sanitizeText(linkData.source_step_name)} (Area: ${sanitizeText(linkData.source_area_name)})`;
                modalTargetStepDisplay.innerHTML = `${sanitizeText(linkData.target_step_name)} (Area: ${sanitizeText(linkData.target_area_name)})`;
                modalRelevanceScoreInput.value = linkData.relevance_score;
                modalRelevanceContentInput.value = linkData.relevance_content || '';
                modalRelevanceContentPreview.innerHTML = typeof marked !== 'undefined' && marked.parse ? (linkData.relevance_content ? marked.parse(linkData.relevance_content) : marked.parse('<em>No content provided.</em>')) : (linkData.relevance_content || 'No content provided.');
            } catch (error) {
                showFlashMessage(`Error loading link details: ${error.message}`, 'danger');
                if (modal) modal.hide(); return;
            }
        } else {
             modalLabel.textContent = 'Create New Link';
             let sourceSelectHtml = '<option value="">-- Select Source Step --</option>';
             let targetSelectHtml = '<option value="">-- Select Target Step --</option>';
             if (allStepsForTargetSelect && allStepsForTargetSelect.length > 0) {
                 const sortedSteps = [...allStepsForTargetSelect].sort((a, b) => (a.name || '').localeCompare(b.name || ''));
                 sortedSteps.forEach(step => {
                     const optionText = `${sanitizeText(step.name)} (${sanitizeText(step.area_name)} - BI_ID: ${sanitizeText(step.bi_id)})`;
                     sourceSelectHtml += `<option value="${step.id}">${optionText}</option>`;
                     targetSelectHtml += `<option value="${step.id}">${optionText}</option>`;
                 });
             }
             modalSourceStepDisplay.innerHTML = `<select id="modalSourceStepSelect" class="form-select" required>${sourceSelectHtml}</select>`;
             modalTargetStepDisplay.innerHTML = `<select id="modalTargetStepSelect" class="form-select" required>${targetSelectHtml}</select>`;
             const sourceSelect = document.getElementById('modalSourceStepSelect');
             const targetSelect = document.getElementById('modalTargetStepSelect');
             if (sourceSelect) sourceSelect.addEventListener('change', function() { modalSourceStepIdInput.value = this.value; });
             if (targetSelect) targetSelect.addEventListener('change', function() { modalTargetStepIdInput.value = this.value; });
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
         addNewLinkBtn.addEventListener('click', () => { openLinkModal(null, null); });
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
            if (isNaN(score) || score < 0 || score > 100) { showFlashMessage('Relevance score must be a number between 0 and 100.', 'warning'); return; }
            modalSaveLinkBtn.disabled = true;
            modalSaveLinkBtn.innerHTML = '<span class="spinner-border spinner-border-sm"></span> Saving...';
            const payload = { relevance_score: score, relevance_content: content.trim() === '' ? null : content.trim() };
            let url, method;
            if (linkId) {
                url = `/review/api/process-links/link/${linkId}`; method = 'PUT';
            } else {
                url = `/review/api/process-links/link`; method = 'POST';
                const sourceSelect = document.getElementById('modalSourceStepSelect');
                const targetSelect = document.getElementById('modalTargetStepSelect');
                if (!sourceSelect || !targetSelect || !sourceSelect.value || !targetSelect.value) {
                     showFlashMessage('Please select both source and target steps.', 'warning');
                     modalSaveLinkBtn.disabled = false; modalSaveLinkBtn.innerHTML = 'Save Link'; return;
                 }
                const sourceStepId = parseInt(sourceSelect.value);
                const targetStepId = parseInt(targetSelect.value);
                if (isNaN(sourceStepId) || isNaN(targetStepId)) {
                    showFlashMessage('Invalid step(s) selected.', 'warning');
                    modalSaveLinkBtn.disabled = false; modalSaveLinkBtn.innerHTML = 'Save Link'; return;
                }
                 if (sourceStepId === targetStepId) {
                    showFlashMessage('Cannot link a step to itself.', 'warning');
                    modalSaveLinkBtn.disabled = false; modalSaveLinkBtn.innerHTML = 'Save Link'; return;
                }
                payload.source_step_id = sourceStepId; payload.target_step_id = targetStepId;
            }
            try {
                const response = await fetch(url, { method: method, headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(payload) });
                const result = await response.json();
                if (result.success) {
                    showFlashMessage(result.message, 'success');
                    if (modal) modal.hide();
                    if (loadDiagramBtn) loadDiagramBtn.click();
                } else { showFlashMessage(`Error: ${result.error || 'Could not save link.'}`, 'danger');}
            } catch (error) { showFlashMessage(`Network error: ${error.message}`, 'danger');
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
                    } else { showFlashMessage(`Error: ${result.error || 'Could not delete link.'}`, 'danger'); }
                } catch (error) { showFlashMessage(`Network error: ${error.message}`, 'danger');
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

    async function fetchAllStepsForSelect() {
         try {
             const response = await fetch('/steps/api/all');
             if (!response.ok) throw new Error('Failed to fetch all steps for select dropdowns.');
             const stepsData = await response.json();
             allStepsForTargetSelect = stepsData.map(s => ({
                 id: s.id,
                 name: s.name,
                 area_name: s.area_name || 'N/A',
                 bi_id: s.bi_id
             }));
             console.log(`Fetched ${allStepsForTargetSelect.length} steps for modal selects.`);
         } catch (error) {
             console.error('Error fetching all steps for modal selects:', error);
         }
    }
    fetchAllStepsForSelect();

    window.cleanupReviewProcessLinksUI = function() {
        if (linkModal && typeof linkModal.dispose === 'function') {
            linkModal.dispose();
            linkModal = null;
        }
    };

});