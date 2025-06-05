// backend/static/js/review_process_links_ui.js

import { initializeLLMChat } from './common_llm_chat.js'; // Assuming common_llm_chat is needed elsewhere or kept for future integration, otherwise remove

document.addEventListener('DOMContentLoaded', function () {
    // DOM Element Selectors
    const focusAreaSelect = document.getElementById('focusAreaSelect');
    const comparisonAreaSelect = document.getElementById('comparisonAreaSelect');
    const loadDiagramBtn = document.getElementById('loadDiagramBtn'); // Renamed to "Load Links" in HTML
    const linksTableBody = document.getElementById('linksTableBody');
    const linksPlaceholder = document.getElementById('linksPlaceholder');
    const linksTable = document.getElementById('linksTable');
    const addNewLinkBtn = document.getElementById('addNewLinkBtn'); // New button

    // Filter Input Elements
    const filterSourceInput = document.getElementById('filterSource');
    const filterTargetInput = document.getElementById('filterTarget');
    const filterMinScoreInput = document.getElementById('filterMinScore');
    const filterMaxScoreInput = document.getElementById('filterMaxScore');
    const filterContentInput = document.getElementById('filterContent');


    // Modal DOM Elements
    const linkModalElement = document.getElementById('linkReviewModal'); // Renamed modal ID
    const modalLabel = document.getElementById('linkReviewModalLabel');
    const modalLinkIdInput = document.getElementById('modalLinkId');
    const modalSourceStepIdInput = document.getElementById('modalSourceStepId');
    const modalTargetStepIdInput = document.getElementById('modalTargetStepId');
    const modalSourceStepDisplay = document.getElementById('modalSourceStepDisplay');
    const modalTargetStepDisplay = document.getElementById('modalTargetStepDisplay'); // This will become a container for text or select
    const modalRelevanceScoreInput = document.getElementById('modalRelevanceScore');
    const modalRelevanceContentInput = document.getElementById('modalRelevanceContent');
    const modalRelevanceContentPreview = document.getElementById('modalRelevanceContentPreview');
    const modalSaveLinkBtn = document.getElementById('modalSaveLinkBtn');
    const modalDeleteLinkBtn = document.getElementById('modalDeleteLinkBtn');

    // Modal Instance
    let linkModal = null; // Will be initialized on first use

    // Store current link data fetched from the API for client-side operations (filtering, sorting)
    let currentLinksData = [];

    // Store all available steps for the "Add New Link" target dropdown
    let allStepsForTargetSelect = [];


    // --- Utility Functions ---
    function showFlashMessage(message, category = 'info') {
         // Use the base.html flash message container if available
        const flashContainer = document.querySelector('.flash-messages') || document.createElement('div');
         if (!flashContainer.closest('.page-content')) { // Prevent creating duplicate containers
              flashContainer.classList.add('flash-messages');
              const pageContent = document.querySelector('.page-content');
              if (pageContent) { pageContent.prepend(flashContainer); } else { document.body.prepend(flashContainer); }
         }

        const alertDiv = document.createElement('div');
        alertDiv.classList.add('alert', `alert-${category}`);
        alertDiv.textContent = message;
        flashContainer.appendChild(alertDiv);

        setTimeout(() => {
            alertDiv.remove();
        }, 5000);
    }

    // Helper function to sanitize text content
    function sanitizeText(text) {
        if (text === null || text === undefined) return '';
        const div = document.createElement('div');
        div.textContent = text;
        return div.innerHTML;
    }

    // Function to populate the table body
    function populateLinksTable(links) {
        linksTableBody.innerHTML = ''; // Clear existing rows
        currentLinksData = links; // Store the raw data

        if (!links || links.length === 0) {
            linksPlaceholder.textContent = 'No relevance links found for the selected criteria.';
            linksPlaceholder.style.display = 'block';
            return;
        }

        linksPlaceholder.style.display = 'none';

        links.forEach(link => {
            const row = document.createElement('tr');
            row.dataset.linkId = link.id; // Store link ID on the row

            row.innerHTML = `
                <td>${sanitizeText(link.source_step_name)}<br><small class="text-muted">(${sanitizeText(link.source_area_name)} - ${sanitizeText(link.source_step_bi_id)})</small></td>
                <td>${sanitizeText(link.target_step_name)}<br><small class="text-muted">(${sanitizeText(link.target_area_name)} - ${sanitizeText(link.target_step_bi_id)})</small></td>
                <td>${link.relevance_score}/100</td>
                <td><div class="content-snippet">${sanitizeText(link.relevance_content_snippet)}</div></td>
                <td>
                    <button class="btn btn-sm btn-secondary edit-link-btn me-1" data-link-id="${link.id}">Edit</button>
                    <button class="btn btn-sm btn-danger delete-link-btn" data-link-id="${link.id}">Delete</button>
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
                                sanitizeText(link.source_step_name).toLowerCase().includes(sourceTerm) ||
                                sanitizeText(link.source_step_bi_id).toLowerCase().includes(sourceTerm) ||
                                sanitizeText(link.source_area_name).toLowerCase().includes(sourceTerm);
            const targetMatch = !targetTerm ||
                                sanitizeText(link.target_step_name).toLowerCase().includes(targetTerm) ||
                                sanitizeText(link.target_step_bi_id).toLowerCase().includes(targetTerm) ||
                                sanitizeText(link.target_area_name).toLowerCase().includes(targetTerm);
            const scoreMatch = (!isNaN(minScore) ? link.relevance_score >= minScore : true) &&
                               (!isNaN(maxScore) ? link.relevance_score <= maxScore : true);
            const contentMatch = !contentTerm ||
                                 sanitizeText(link.relevance_content).toLowerCase().includes(contentTerm);

            return sourceMatch && targetMatch && scoreMatch && contentMatch;
        });

        renderFilteredTable(filteredLinks);
    }

    // Render only the currently filtered/sorted data
    function renderFilteredTable(linksToRender) {
         linksTableBody.innerHTML = ''; // Clear existing rows

         if (!linksToRender || linksToRender.length === 0) {
             linksPlaceholder.textContent = 'No links match the current filters.';
             linksPlaceholder.style.display = 'block';
             return;
         }

         linksPlaceholder.style.display = 'none';

         linksToRender.forEach(link => {
            const row = document.createElement('tr');
            row.dataset.linkId = link.id;

            row.innerHTML = `
                <td>${sanitizeText(link.source_step_name)}<br><small class="text-muted">(${sanitizeText(link.source_area_name)} - ${sanitizeText(link.source_step_bi_id)})</small></td>
                <td>${sanitizeText(link.target_step_name)}<br><small class="text-muted">(${sanitizeText(link.target_area_name)} - ${sanitizeText(link.target_step_bi_id)})</small></td>
                <td>${link.relevance_score}/100</td>
                <td><div class="content-snippet">${sanitizeText(link.relevance_content_snippet)}</div></td>
                 <td>
                    <button class="btn btn-sm btn-secondary edit-link-btn me-1" data-link-id="${link.id}">Edit</button>
                    <button class="btn btn-sm btn-danger delete-link-btn" data-link-id="${link.id}">Delete</button>
                </td>
            `;
             linksTableBody.appendChild(row);
        });
    }


    // --- Client-Side Sorting ---
    let currentSortColumn = null;
    let currentSortDirection = 'asc';

    function sortTable(columnKey) {
        if (currentSortColumn === columnKey) {
            currentSortDirection = currentSortDirection === 'asc' ? 'desc' : 'asc';
        } else {
            currentSortColumn = columnKey;
            currentSortDirection = 'asc';
        }

        // Remove sorting classes from all headers
        linksTable.querySelectorAll('th').forEach(th => {
            th.classList.remove('sorted-asc', 'sorted-desc');
        });

        // Add sorting class to the current header
        linksTable.querySelector(`th[data-sort="${columnKey}"]`).classList.add(`sorted-${currentSortDirection}`);

        // Get currently filtered data
        const sourceTerm = filterSourceInput.value.toLowerCase().trim();
        const targetTerm = filterTargetInput.value.toLowerCase().trim();
        const minScore = parseInt(filterMinScoreInput.value);
        const maxScore = parseInt(filterMaxScoreInput.value);
        const contentTerm = filterContentInput.value.toLowerCase().trim();

         const filteredLinks = currentLinksData.filter(link => {
            const sourceMatch = !sourceTerm ||
                                sanitizeText(link.source_step_name).toLowerCase().includes(sourceTerm) ||
                                sanitizeText(link.source_step_bi_id).toLowerCase().includes(sourceTerm) ||
                                sanitizeText(link.source_area_name).toLowerCase().includes(sourceTerm);
            const targetMatch = !targetTerm ||
                                sanitizeText(link.target_step_name).toLowerCase().includes(targetTerm) ||
                                sanitizeText(link.target_step_bi_id).toLowerCase().includes(targetTerm) ||
                                sanitizeText(link.target_area_name).toLowerCase().includes(targetTerm);
            const scoreMatch = (!isNaN(minScore) ? link.relevance_score >= minScore : true) &&
                               (!isNaN(maxScore) ? link.relevance_score <= maxScore : true);
            const contentMatch = !contentTerm ||
                                 sanitizeText(link.relevance_content).toLowerCase().includes(contentTerm);

            return sourceMatch && targetMatch && scoreMatch && contentMatch;
        });


        // Sort the filtered data
        filteredLinks.sort((a, b) => {
            let valueA = a[columnKey];
            let valueB = b[columnKey];

            // Special handling for different data types
            if (typeof valueA === 'string') valueA = valueA.toLowerCase();
            if (typeof valueB === 'string') valueB = valueB.toLowerCase();
            if (columnKey === 'relevance_score') {
                valueA = parseInt(valueA);
                valueB = parseInt(valueB);
            }

            if (valueA < valueB) return currentSortDirection === 'asc' ? -1 : 1;
            if (valueA > valueB) return currentSortDirection === 'asc' ? 1 : -1;
            return 0;
        });

        renderFilteredTable(filteredLinks); // Render the sorted, filtered data
    }

    // --- Modal Management ---
    // Helper to get or create modal instance
    function getLinkModal() {
         if (!linkModal) {
            if (linkModalElement && typeof window.bootstrap !== 'undefined' && typeof window.bootstrap.Modal === 'function') {
                linkModal = new window.bootstrap.Modal(linkModalElement);
                console.log("Bootstrap Modal initialized successfully on demand.");
            } else {
                console.error("Link review modal element #linkReviewModal or Bootstrap Modal library not found. Cannot initialize modal.");
                showFlashMessage("Modal components missing or Bootstrap not ready. Please check console.", "danger");
                return null;
            }
         }
         return linkModal;
    }

    async function openLinkModal(linkId = null, sourceStepId = null) {
        const modal = getLinkModal();
        if (!modal) return;

        // Check all essential modal elements are present
         if (!modalLinkIdInput || !modalSourceStepIdInput || !modalTargetStepIdInput ||
            !modalSourceStepDisplay || !modalTargetStepDisplay || !modalRelevanceScoreInput ||
            !modalRelevanceContentInput || !modalRelevanceContentPreview || !modalDeleteLinkBtn ||
            !modalSaveLinkBtn || !modalLabel) {
            console.error("One or more modal DOM elements are not found. Cannot open modal.");
            showFlashMessage("Modal components missing. Please check console.", "danger");
            return;
        }


        // Reset modal form
        modalLinkIdInput.value = '';
        modalSourceStepIdInput.value = '';
        modalTargetStepIdInput.value = ''; // Clear this as it might be text or select container
        modalSourceStepDisplay.textContent = 'Loading...';
        modalTargetStepDisplay.innerHTML = 'Loading...'; // Use innerHTML because it might be a <select>
        modalRelevanceScoreInput.value = '50';
        modalRelevanceContentInput.value = '';
        if (typeof marked !== 'undefined' && marked.parse) {
            modalRelevanceContentPreview.innerHTML = marked.parse('<em>No content provided.</em>');
        } else {
            modalRelevanceContentPreview.innerHTML = '<em>No content provided.</em>';
        }
        modalDeleteLinkBtn.style.display = 'none';
        modalSaveLinkBtn.textContent = 'Save Link';
        modalSaveLinkBtn.disabled = false;
        modalDeleteLinkBtn.disabled = false;

        if (linkId) {
            // --- Editing Existing Link ---
            modalLabel.textContent = 'Review/Edit Link';
            modalLinkIdInput.value = linkId;
            modalSaveLinkBtn.textContent = 'Save Changes';
            modalDeleteLinkBtn.style.display = 'block'; // Show delete button for existing links

            try {
                // Use the existing API endpoint to fetch details for one link
                const response = await fetch(`/review/api/process-links/link/${linkId}`);
                if (!response.ok) throw new Error('Failed to fetch link details.');
                const linkData = await response.json();

                modalSourceStepIdInput.value = linkData.source_step_id;
                modalTargetStepIdInput.value = linkData.target_step_id;
                modalSourceStepDisplay.textContent = `${sanitizeText(linkData.source_step_name)} (Area: ${sanitizeText(linkData.source_area_name)})`;
                // For existing links, just display the target step name
                modalTargetStepDisplay.innerHTML = `${sanitizeText(linkData.target_step_name)} (Area: ${sanitizeText(linkData.target_area_name)})`;

                modalRelevanceScoreInput.value = linkData.relevance_score;
                modalRelevanceContentInput.value = linkData.relevance_content || '';

                // Update Markdown preview
                if (typeof marked !== 'undefined' && marked.parse) {
                    modalRelevanceContentPreview.innerHTML = linkData.relevance_content ? marked.parse(linkData.relevance_content) : marked.parse('<em>No content provided.</em>');
                } else {
                     modalRelevanceContentPreview.textContent = linkData.relevance_content || 'No content provided.';
                }


            } catch (error) {
                showFlashMessage(`Error loading link details: ${error.message}`, 'danger');
                if (modal) modal.hide();
                return;
            }

        } else if (sourceStepId) {
            // --- Creating New Link (from a specific step) ---
             modalLabel.textContent = 'Create New Link';
             modalSourceStepIdInput.value = sourceStepId;

             // Find the source step data from the previously fetched links (or refetch if necessary)
             const sourceStepData = currentLinksData.find(link => link.source_step_id === sourceStepId);
             if (sourceStepData) {
                 modalSourceStepDisplay.textContent = `${sanitizeText(sourceStepData.source_step_name)} (Area: ${sanitizeText(sourceStepData.source_area_name)})`;
             } else {
                 // Fallback: might need to fetch step details if not in currentLinksData
                 modalSourceStepDisplay.textContent = `Step ID ${sourceStepId}`; // Basic display
                 // A more robust solution would fetch the step name/area via another API call here
                 console.warn(`Source step ID ${sourceStepId} not found in currentLinksData for new link creation.`);
             }

             // Populate target step dropdown with ALL other steps
             if (allStepsForTargetSelect.length === 0) {
                 try {
                     // Fetch all steps if not already available
                     const response = await fetch('/api/steps'); // Assuming an API endpoint for all steps
                     if (!response.ok) throw new Error('Failed to fetch all steps.');
                     const stepsData = await response.json();
                     allStepsForTargetSelect = stepsData; // Store for future use
                 } catch (error) {
                     console.error('Error fetching all steps for target select:', error);
                     showFlashMessage(`Could not load all steps for target selection: ${error.message}`, 'danger');
                 }
             }

             let targetStepOptionsHtml = '<option value="">-- Select Target Step --</option>';
             if (allStepsForTargetSelect && allStepsForTargetSelect.length > 0) {
                 // Sort steps alphabetically, exclude the source step itself
                 const sortedTargetNodes = allStepsForTargetSelect
                     .filter(step => parseInt(step.id) !== parseInt(sourceStepId)) // Exclude source step
                     .sort((a, b) => (a.name || '').localeCompare(b.name || '')); // Sort by name

                 sortedTargetNodes.forEach(step => {
                     targetStepOptionsHtml += `<option value="${step.id}">${sanitizeText(step.name)} (${sanitizeText(step.area_name)} - BI_ID: ${sanitizeText(step.bi_id)})</option>`;
                 });
             } else {
                 targetStepOptionsHtml = '<option value="">-- No other steps available --</option>';
             }
             // Replace the target step display span with the select dropdown
             modalTargetStepDisplay.innerHTML = `<select id="modalTargetStepSelect" class="form-select" required>${targetStepOptionsHtml}</select>`;

             // Add event listener to the dynamically created select
             const targetSelect = document.getElementById('modalTargetStepSelect');
             if (targetSelect) {
                 targetSelect.addEventListener('change', function() {
                     modalTargetStepIdInput.value = this.value; // Update hidden input
                 });
             }

            if (typeof marked !== 'undefined' && marked.parse) {
                modalRelevanceContentPreview.innerHTML = marked.parse('<em>No content provided.</em>');
            } else {
                modalRelevanceContentPreview.textContent = 'No content provided.';
            }


        } else {
            // --- Creating New Link (global add button) ---
            // In this case, we need to select *both* source and target steps.
            // This flow is slightly more complex and would require two selects.
            // For now, we can perhaps just open the modal and require selection,
            // or implement a dedicated "Add New Link" button that presents two selects.
            // Let's assume the "Add New Link" button calls this with sourceStepId = null initially.
            // A full implementation for this case would need more modal structure.
            // For simplicity, let's focus on adding from a specific step for now,
            // or adjust the "Add New Link" button to trigger the modal with an empty state,
            // presenting both source and target selects. Let's go with the latter for the button.
            modalLabel.textContent = 'Create New Link';

            // Populate Source step dropdown with ALL steps
            if (allStepsForTargetSelect.length === 0) { // Reuse the check/fetch for all steps
                 try {
                     const response = await fetch('/api/steps'); // Assuming an API endpoint for all steps
                     if (!response.ok) throw new Error('Failed to fetch all steps.');
                     const stepsData = await response.json();
                     allStepsForTargetSelect = stepsData; // Store for future use
                 } catch (error) {
                     console.error('Error fetching all steps for source/target select:', error);
                     showFlashMessage(`Could not load all steps for selection: ${error.message}`, 'danger');
                 }
             }

            let sourceStepOptionsHtml = '<option value="">-- Select Source Step --</option>';
            let targetStepOptionsHtml = '<option value="">-- Select Target Step --</option>';

            if (allStepsForTargetSelect && allStepsForTargetSelect.length > 0) {
                const sortedSteps = allStepsForTargetSelect.sort((a, b) => (a.name || '').localeCompare(b.name || ''));
                sortedSteps.forEach(step => {
                    const optionText = `${sanitizeText(step.name)} (${sanitizeText(step.area_name)} - BI_ID: ${sanitizeText(step.bi_id)})`;
                    sourceStepOptionsHtml += `<option value="${step.id}">${optionText}</option>`;
                    targetStepOptionsHtml += `<option value="${step.id}">${optionText}</option>`;
                });
            } else {
                 sourceStepOptionsHtml = '<option value="">-- No steps available --</option>';
                 targetStepOptionsHtml = '<option value="">-- No steps available --</option>';
            }

            // Replace display spans with select dropdowns
             modalSourceStepDisplay.innerHTML = `<select id="modalSourceStepSelect" class="form-select" required>${sourceStepOptionsHtml}</select>`;
             modalTargetStepDisplay.innerHTML = `<select id="modalTargetStepSelect" class="form-select" required>${targetStepOptionsHtml}</select>`;

             // Add event listeners to the dynamically created selects
             const sourceSelect = document.getElementById('modalSourceStepSelect');
             const targetSelect = document.getElementById('modalTargetStepSelect');

             if (sourceSelect) {
                 sourceSelect.addEventListener('change', function() {
                     modalSourceStepIdInput.value = this.value; // Update hidden input
                 });
             }
              if (targetSelect) {
                 targetSelect.addEventListener('change', function() {
                     modalTargetStepIdInput.value = this.value; // Update hidden input
                 });
             }

             if (typeof marked !== 'undefined' && marked.parse) {
                modalRelevanceContentPreview.innerHTML = marked.parse('<em>No content provided.</em>');
            } else {
                modalRelevanceContentPreview.textContent = 'No content provided.';
            }

        }

        // Show the modal
        if (modal) {
            modal.show();
        }
    }


    // --- Event Listeners ---
    if (loadDiagramBtn) {
        loadDiagramBtn.addEventListener('click', async () => {
            if (!focusAreaSelect || !comparisonAreaSelect) {
                showFlashMessage('Focus or comparison area select elements not found.', 'danger');
                return;
            }
            const focusAreaId = focusAreaSelect.value;
            const selectedComparisonOptions = Array.from(comparisonAreaSelect.selectedOptions);
            const comparisonAreaIds = selectedComparisonOptions.map(opt => opt.value);

            if (!focusAreaId) {
                showFlashMessage('Please select a Focus Area.', 'warning');
                return;
            }

            loadDiagramBtn.disabled = true;
            loadDiagramBtn.innerHTML = '<span class="spinner-border spinner-border-sm" role="status" aria-hidden="true"></span> Loading...';
            linksPlaceholder.textContent = 'Loading links...';
            linksPlaceholder.style.display = 'block';
            linksTableBody.innerHTML = ''; // Clear table while loading

            try {
                const params = new URLSearchParams({ focus_area_id: focusAreaId });
                comparisonAreaIds.forEach(id => params.append('comparison_area_ids[]', id));

                const response = await fetch(`/review/api/process-links/data?${params.toString()}`);
                if (!response.ok) {
                     let errorMsg = `Server error: ${response.status}`;
                    try { const errorData = await response.json(); errorMsg = errorData.error || errorMsg; } catch (e) { /* Ignore */ }
                    throw new Error(errorMsg);
                }
                const data = await response.json();
                if (data.error) { throw new Error(data.error); }

                // Store and populate the table
                currentLinksData = data.links || []; // Store fetched data
                populateLinksTable(currentLinksData); // Populate initially
                applyClientSideFilters(); // Apply any existing filters to the loaded data


            } catch (error) {
                console.error('Error in loadDiagramBtn:', error);
                showFlashMessage(`Error loading links: ${error.message}`, 'danger');
                 linksPlaceholder.textContent = `Error loading links: ${error.message}. Check console.`;
                 linksPlaceholder.style.display = 'block';
                 currentLinksData = []; // Ensure data is empty on error
            } finally {
                loadDiagramBtn.disabled = false;
                loadDiagramBtn.innerHTML = 'Load Links';
            }
        });
    }

    if (addNewLinkBtn) {
        // Assuming an API endpoint /api/steps that returns [{id, name, area_name, bi_id}, ...]
        // We need all steps to populate the source/target dropdowns in the modal
         addNewLinkBtn.addEventListener('click', () => {
            // Call openLinkModal with no linkId or sourceStepId to indicate creating a new link globally
             openLinkModal(null, null);
         });
    } else {
         console.warn("addNewLinkBtn not found. Cannot add global 'Add New Link' functionality.");
    }


    // Event delegation for Edit and Delete buttons in the table body
    if (linksTableBody) {
        linksTableBody.addEventListener('click', function(event) {
            const target = event.target;
            const linkId = target.dataset.linkId;

            if (target.classList.contains('edit-link-btn') && linkId) {
                 openLinkModal(parseInt(linkId)); // Open modal for editing
            } else if (target.classList.contains('delete-link-btn') && linkId) {
                 // Trigger delete action directly
                 handleDeleteLink(parseInt(linkId));
            }
        });
    }


    // Event listeners for Filter Inputs (trigger client-side filtering)
    if (filterSourceInput) filterSourceInput.addEventListener('input', applyClientSideFilters);
    if (filterTargetInput) filterTargetInput.addEventListener('input', applyClientSideFilters);
    if (filterMinScoreInput) filterMinScoreInput.addEventListener('input', applyClientSideFilters);
    if (filterMaxScoreInput) filterMaxScoreInput.addEventListener('input', applyClientSideFilters);
    if (filterContentInput) filterContentInput.addEventListener('input', applyClientSideFilters);


    // Event listener for table header clicks (trigger client-side sorting)
    if (linksTable) {
         linksTable.querySelectorAll('th[data-sort]').forEach(header => {
             header.addEventListener('click', function() {
                 const sortKey = this.dataset.sort;
                 if (sortKey) {
                     sortTable(sortKey);
                 }
             });
         });
    }


    // Markdown preview in modal (listener already exists, ensure it works with new modal ID)
    if (modalRelevanceContentInput && modalRelevanceContentPreview) {
        modalRelevanceContentInput.addEventListener('input', function() {
            if (typeof marked !== 'undefined' && marked.parse) {
                modalRelevanceContentPreview.innerHTML = this.value ? marked.parse(this.value) : marked.parse('<em>No content provided.</em>');
            } else {
                modalRelevanceContentPreview.textContent = this.value || 'No content provided.';
            }
        });
    }


    // Modal Save Button
    if (modalSaveLinkBtn) {
        modalSaveLinkBtn.addEventListener('click', async () => {
            const modal = getLinkModal();
             if (!modal || !modalRelevanceScoreInput || !modalRelevanceContentInput || !modalSaveLinkBtn || !modalDeleteLinkBtn) { // Added more checks
                showFlashMessage('Modal save components missing or modal not initialized.', 'danger');
                return;
            }

            const linkId = modalLinkIdInput.value ? parseInt(modalLinkIdInput.value) : null; // Use null for new links
            const score = parseInt(modalRelevanceScoreInput.value);
            const content = modalRelevanceContentInput.value;

            // Basic validation for relevance score
            if (isNaN(score) || score < 0 || score > 100) {
                showFlashMessage('Relevance score must be a number between 0 and 100.', 'warning');
                return; // Stop execution if validation fails
            }

            modalSaveLinkBtn.disabled = true;
            modalSaveLinkBtn.innerHTML = '<span class="spinner-border spinner-border-sm" role="status" aria-hidden="true"></span> Saving...';

            const payload = {
                relevance_score: score,
                relevance_content: content.trim() === '' ? null : content.trim()
            };

            let url, method;

            if (linkId) {
                // --- Update Existing Link ---
                url = `/review/api/process-links/link/${linkId}`;
                method = 'PUT';
                 // For PUT, source and target IDs should not be sent in the payload (they are in the URL or implicit)
                 // Ensure hidden inputs are correct if they were populated from the original link data
                 const sourceStepId = parseInt(modalSourceStepIdInput.value);
                 const targetStepId = parseInt(modalTargetStepIdInput.value);
                 // You might add a check here that source/target IDs didn't somehow become invalid,
                 // although the PUT endpoint doesn't strictly need them in the payload.
                 if (isNaN(sourceStepId) || isNaN(targetStepId)) {
                      console.error("Invalid source or target step ID for PUT operation.");
                      showFlashMessage('Internal error: Invalid step IDs for update.', 'danger');
                      modalSaveLinkBtn.disabled = false; modalSaveLinkBtn.innerHTML = 'Save Changes';
                      return; // Stop
                 }

            } else {
                // --- Create New Link ---
                url = `/review/api/process-links/link`;
                method = 'POST';

                // Get source and target IDs from the select elements (for new links)
                const sourceSelect = document.getElementById('modalSourceStepSelect');
                const targetSelect = document.getElementById('modalTargetStepSelect');

                if (!sourceSelect || !targetSelect || !sourceSelect.value || !targetSelect.value) {
                     showFlashMessage('Please select both source and target steps.', 'warning');
                     modalSaveLinkBtn.disabled = false; modalSaveLinkBtn.innerHTML = 'Save Link';
                     return; // Stop
                 }

                const sourceStepId = parseInt(sourceSelect.value);
                const targetStepId = parseInt(targetSelect.value);

                if (isNaN(sourceStepId) || isNaN(targetStepId)) {
                    showFlashMessage('Invalid step(s) selected.', 'warning');
                    modalSaveLinkBtn.disabled = false; modalSaveLinkBtn.innerHTML = 'Save Link';
                    return; // Stop
                }
                 if (sourceStepId === targetStepId) {
                    showFlashMessage('Cannot link a step to itself.', 'warning');
                    modalSaveLinkBtn.disabled = false; modalSaveLinkBtn.innerHTML = 'Save Link';
                    return; // Stop
                }

                payload.source_step_id = sourceStepId;
                payload.target_step_id = targetStepId;
            }

            try {
                const response = await fetch(url, { method: method, headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(payload) });
                const result = await response.json();
                if (result.success) {
                    showFlashMessage(result.message, 'success');
                    if (modal) modal.hide();
                    // Refresh the table data after saving
                    if (loadDiagramBtn) loadDiagramBtn.click();
                } else {
                    // Handle API errors (e.g., link already exists for POST)
                    showFlashMessage(`Error: ${result.error || 'Could not save link.'}`, 'danger');
                    console.error('Save Link API Error:', result.error);
                }
            } catch (error) {
                 console.error('Network error during save:', error);
                 showFlashMessage(`Network error: ${error.message}`, 'danger');
            } finally {
                 modalSaveLinkBtn.disabled = false;
                 modalSaveLinkBtn.innerHTML = linkId ? 'Save Changes' : 'Save Link';
                 // Do not reset delete button state here, it's handled on modal open
            }
        });
    } else {
        console.error("modalSaveLinkBtn not found");
    }

    // Modal Delete Button
    if (modalDeleteLinkBtn) {
        modalDeleteLinkBtn.addEventListener('click', async () => {
             const modal = getLinkModal();
             if (!modal || !modalLinkIdInput || !modalDeleteLinkBtn || !modalSaveLinkBtn) { // Added more checks
                showFlashMessage('Modal delete components missing or modal not initialized.', 'danger');
                return;
            }
            const linkId = modalLinkIdInput.value ? parseInt(modalLinkIdInput.value) : null;
            if (!linkId) {
                 console.error("Delete button clicked without a link ID in the modal.");
                 showFlashMessage("Error: Cannot delete link without an ID.", "danger");
                 return; // Should not happen if button is hidden for new links
            }

            if (confirm('Are you sure you want to delete this link? This action cannot be undone.')) {
                modalDeleteLinkBtn.disabled = true;
                modalSaveLinkBtn.disabled = true; // Also disable save while deleting
                modalDeleteLinkBtn.innerHTML = '<span class="spinner-border spinner-border-sm" role="status" aria-hidden="true"></span> Deleting...';

                try {
                    const response = await fetch(`/review/api/process-links/link/${linkId}`, { method: 'DELETE' });
                    const result = await response.json();
                    if (result.success) {
                        showFlashMessage(result.message, 'success');
                        if (modal) modal.hide();
                         // Refresh the table data after deleting
                        if (loadDiagramBtn) loadDiagramBtn.click();
                    } else {
                        showFlashMessage(`Error: ${result.error || 'Could not delete link.'}`, 'danger');
                         console.error('Delete Link API Error:', result.error);
                    }
                } catch (error) {
                     console.error('Network error during delete:', error);
                     showFlashMessage(`Network error: ${error.message}`, 'danger');
                } finally {
                     // Re-enable buttons even on failure to allow closing modal
                     modalDeleteLinkBtn.disabled = false;
                     modalSaveLinkBtn.disabled = false;
                     modalDeleteLinkBtn.innerHTML = 'Delete Link';
                }
            }
        });
    }

    // Ensure comparison area select disables the focus area option
    if (focusAreaSelect && comparisonAreaSelect) {
        focusAreaSelect.addEventListener('change', function() {
            const focusValue = this.value;
            Array.from(comparisonAreaSelect.options).forEach(opt => {
                if (opt.value === focusValue && focusValue !== "") {
                    opt.disabled = true;
                    if (opt.selected) { opt.selected = false; }
                } else { opt.disabled = false; }
            });
        });
        // Trigger change on load to handle any pre-selected focus area disabling in comparison
        focusAreaSelect.dispatchEvent(new Event('change'));
    }


    // --- Initial Load ---
    // Optionally, trigger a load on page load if default areas are set or for a static view
    // if (focusAreaSelect && focusAreaSelect.value) {
    //    loadDiagramBtn.click();
    // }


    // Assuming you have an API endpoint `/api/steps` that returns an array of all steps
    // formatted like [{id: 1, name: 'Step A', area_name: 'Area X', bi_id: 'PS-001'}, ...]
    // Fetch all steps on page load so they are available for the "Add New Link" modal
    async function fetchAllStepsForSelect() {
         try {
             // Assuming this endpoint exists and returns necessary step data
             const response = await fetch('/api/steps'); 
             if (!response.ok) throw new Error('Failed to fetch all steps for select.');
             const stepsData = await response.json();
             allStepsForTargetSelect = stepsData;
             console.log(`Fetched ${allStepsForTargetSelect.length} steps for modal selects.`);
         } catch (error) {
             console.error('Error fetching all steps for modal selects:', error);
             // Do not show a flash message here, it's not critical to initial page load
         }
    }
    // Fetch all steps when the DOM is ready
    fetchAllStepsForSelect();


    // --- Cleanup Function ---
    window.cleanupReviewProcessLinksUI = function() {
        // No ECharts resize handler to remove
        if (linkModal) {
            linkModal.dispose();
            linkModal = null;
        }
        // Remove other custom event listeners if necessary for more complex apps
        // For this simple case, they are mostly attached via delegation or to elements that persist.
    };

}); // End of DOMContentLoaded