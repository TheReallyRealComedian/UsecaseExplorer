// backend/static/js/review_process_links_ui.js
document.addEventListener('DOMContentLoaded', function () {
    const focusAreaSelect = document.getElementById('focusAreaSelect');
    const comparisonAreaSelect = document.getElementById('comparisonAreaSelect');
    const loadDiagramBtn = document.getElementById('loadDiagramBtn');
    const sankeyDiagramContainer = document.getElementById('sankeyDiagramContainer');
    const sankeyPlaceholder = document.getElementById('sankeyPlaceholder');

    const linkModalElement = document.getElementById('linkModal');
    const linkModal = new bootstrap.Modal(linkModalElement);
    const modalLabel = document.getElementById('linkModalLabel');
    const modalLinkIdInput = document.getElementById('modalLinkId');
    const modalSourceStepIdInput = document.getElementById('modalSourceStepId'); // Hidden input for source step ID
    const modalTargetStepIdInput = document.getElementById('modalTargetStepId'); // Hidden input for target step ID (used on create)
    const modalSourceStepDisplay = document.getElementById('modalSourceStepDisplay');
    const modalTargetStepDisplay = document.getElementById('modalTargetStepDisplay'); // Can be span or select
    const modalRelevanceScoreInput = document.getElementById('modalRelevanceScore');
    const modalRelevanceContentInput = document.getElementById('modalRelevanceContent');
    const modalRelevanceContentPreview = document.getElementById('modalRelevanceContentPreview');
    const modalSaveLinkBtn = document.getElementById('modalSaveLinkBtn');
    const modalDeleteLinkBtn = document.getElementById('modalDeleteLinkBtn');

    let sankeyChart = null;
    let currentChartData = { nodes: [], links: [] };

    if (sankeyDiagramContainer && typeof echarts !== 'undefined') {
        sankeyChart = echarts.init(sankeyDiagramContainer);
        window.addEventListener('resize', function() {
            if (sankeyChart) {
                sankeyChart.resize();
            }
        });
    } else {
        console.warn("ECharts or Sankey container not found. Diagram functionality will be limited.");
    }
    
    function showFlashMessage(message, category = 'info') {
        const flashContainer = document.querySelector('.flash-messages') || document.createElement('div');
        if (!flashContainer.classList.contains('flash-messages')) {
            flashContainer.classList.add('flash-messages');
            const pageContent = document.querySelector('.page-content');
            if (pageContent) {
                 const firstChild = pageContent.firstChild;
                 pageContent.insertBefore(flashContainer, firstChild);
            } else {
                console.warn("'.page-content' not found, flash message cannot be prepended.");
                document.body.prepend(flashContainer);
            }
        }
        
        const alertDiv = document.createElement('div');
        alertDiv.classList.add('alert', `alert-${category}`, 'alert-dismissible', 'fade', 'show');
        alertDiv.setAttribute('role', 'alert');
        alertDiv.innerHTML = `${message}<button type="button" class="btn-close" data-bs-dismiss="alert" aria-label="Close"></button>`;
        flashContainer.appendChild(alertDiv);

        setTimeout(() => {
            const bsAlert = bootstrap.Alert.getInstance(alertDiv);
            if (bsAlert) {
                bsAlert.close();
            } else if (alertDiv.parentElement) {
                alertDiv.remove();
            }
        }, 7000);
    }


    function renderSankey(data) {
        currentChartData = data;
        if (sankeyPlaceholder) sankeyPlaceholder.style.display = 'none';
        if (!sankeyChart) return;

        const option = {
            tooltip: {
                trigger: 'item',
                triggerOn: 'mousemove|click',
                formatter: function (params) {
                    if (params.dataType === 'edge') {
                        return `<strong>Link:</strong> ${params.data.source} <i class="fas fa-arrow-right"></i> ${params.data.target}<br/>
                                <strong>Score:</strong> ${params.data.value}<br/>
                                <strong>Content:</strong> ${params.data.data.content_snippet || 'N/A'}<br/>
                                <em>Click to edit/review link</em>`;
                    } else if (params.dataType === 'node') {
                        const originalNode = currentChartData.nodes.find(n => n.name === params.name);
                        return `<strong>Step:</strong> ${params.name}<br/>
                                (ID: ${originalNode ? originalNode.id : 'N/A'})<br/> 
                                <em>Click to add link from this step</em>`;
                    }
                    return '';
                }
            },
            series: [
                {
                    type: 'sankey',
                    layout: 'none',
                    emphasis: {
                        focus: 'adjacency'
                    },
                    data: data.nodes.map(node => ({
                        name: node.name,
                        id: node.id,
                        itemStyle: node.itemStyle
                    })),
                    links: data.links,
                    lineStyle: {
                        color: 'source',
                        curveness: 0.5,
                        opacity: 0.6
                    },
                    label: {
                        show: true,
                        formatter: '{b}',
                        overflow: 'truncate',
                        width: 150,
                        ellipsis: '...'
                    },
                    nodeAlign: 'justify',
                    draggable: true,
                    animationDuration: 1000
                }
            ]
        };
        sankeyChart.setOption(option, true);
    }

    loadDiagramBtn.addEventListener('click', async () => {
        const focusAreaId = focusAreaSelect.value;
        const selectedComparisonOptions = Array.from(comparisonAreaSelect.selectedOptions);
        const comparisonAreaIds = selectedComparisonOptions.map(opt => opt.value);

        if (!focusAreaId) {
            showFlashMessage('Please select a Focus Area.', 'warning');
            return;
        }
        
        loadDiagramBtn.disabled = true;
        loadDiagramBtn.innerHTML = '<span class="spinner-border spinner-border-sm" role="status" aria-hidden="true"></span> Loading...';
        if (sankeyPlaceholder) sankeyPlaceholder.textContent = 'Loading diagram data...';

        try {
            const params = new URLSearchParams({ focus_area_id: focusAreaId });
            comparisonAreaIds.forEach(id => params.append('comparison_area_ids[]', id));
            
            const response = await fetch(`/review/api/process-links/data?${params.toString()}`);
            if (!response.ok) {
                const errorData = await response.json();
                throw new Error(errorData.error || `Server error: ${response.status}`);
            }
            const data = await response.json();
            if (data.nodes && data.nodes.length > 0) {
                renderSankey(data);
            } else {
                if (sankeyPlaceholder) sankeyPlaceholder.textContent = 'No links or steps found for the selected criteria. Adjust your selections.';
                if(sankeyChart) sankeyChart.clear();
                currentChartData = { nodes: [], links: [] };
            }
        } catch (error) {
            console.error('Error fetching Sankey data:', error);
            showFlashMessage(`Error loading diagram: ${error.message}`, 'danger');
            if (sankeyPlaceholder) sankeyPlaceholder.textContent = 'Error loading diagram. Check console or server logs.';
        } finally {
            loadDiagramBtn.disabled = false;
            loadDiagramBtn.innerHTML = 'Load Diagram';
        }
    });

    if (sankeyChart) {
        sankeyChart.on('click', async function (params) {
            if (params.dataType === 'edge' && params.data && params.data.data && params.data.data.link_id) {
                const linkId = params.data.data.link_id;
                openLinkModal(linkId);
            } else if (params.dataType === 'node' && params.data && params.data.id) {
                const sourceStepId = params.data.id; 
                const sourceStepEchartsName = params.name;
                openLinkModal(null, sourceStepId, sourceStepEchartsName);
            }
        });
    }
    
    async function openLinkModal(linkId = null, sourceStepId = null, sourceStepEchartsName = null) {
        modalLinkIdInput.value = '';
        modalSourceStepIdInput.value = '';
        modalTargetStepIdInput.value = '';
        modalSourceStepDisplay.textContent = 'Loading...';
        modalTargetStepDisplay.innerHTML = 'Loading...';
        modalRelevanceScoreInput.value = '50';
        modalRelevanceContentInput.value = '';
        modalRelevanceContentPreview.innerHTML = '<em>No content provided.</em>';
        modalDeleteLinkBtn.style.display = 'none';
        modalSaveLinkBtn.textContent = 'Save Link';
        modalSaveLinkBtn.disabled = false;
        if (modalDeleteLinkBtn) modalDeleteLinkBtn.disabled = false;


        if (linkId) { // Editing existing link
            modalLabel.textContent = 'Review/Edit Link';
            modalDeleteLinkBtn.style.display = 'block';
            modalLinkIdInput.value = linkId;
            modalSaveLinkBtn.textContent = 'Save Changes';

            try {
                const response = await fetch(`/review/api/process-links/link/${linkId}`);
                if (!response.ok) throw new Error('Failed to fetch link details.');
                const linkData = await response.json();

                modalSourceStepIdInput.value = linkData.source_step_id;
                modalTargetStepIdInput.value = linkData.target_step_id;
                modalSourceStepDisplay.textContent = `${linkData.source_step_name} (Area: ${linkData.source_area_name})`;
                modalTargetStepDisplay.innerHTML = `<span>${linkData.target_step_name} (Area: ${linkData.target_area_name})</span>`;
                modalRelevanceScoreInput.value = linkData.relevance_score;
                modalRelevanceContentInput.value = linkData.relevance_content || '';
                modalRelevanceContentPreview.innerHTML = linkData.relevance_content ? marked.parse(linkData.relevance_content) : '<em>No content provided.</em>';
            } catch (error) {
                showFlashMessage(`Error loading link details: ${error.message}`, 'danger');
                return;
            }
        } else if (sourceStepId && sourceStepEchartsName) { // Creating new link
            modalLabel.textContent = 'Create New Link';
            modalSourceStepIdInput.value = sourceStepId;
            modalSourceStepDisplay.textContent = sourceStepEchartsName;

            let targetStepOptionsHtml = '<option value="">-- Select Target Step --</option>';
            if (currentChartData.nodes && currentChartData.nodes.length > 0) {
                currentChartData.nodes.forEach(node => {
                    if (node.id !== sourceStepId) {
                        targetStepOptionsHtml += `<option value="${node.id}">${node.name}</option>`;
                    }
                });
            } else {
                 targetStepOptionsHtml = '<option value="">-- No target steps available in current view --</option>';
            }
            modalTargetStepDisplay.innerHTML = `<select id="modalTargetStepSelect" class="form-select">${targetStepOptionsHtml}</select>`;
            modalRelevanceContentPreview.innerHTML = '<em>No content provided.</em>';
        } else {
            showFlashMessage("Modal error: Insufficient data to open.", "warning");
            return;
        }
        linkModal.show();
    }

    modalRelevanceContentInput.addEventListener('input', function() {
        modalRelevanceContentPreview.innerHTML = this.value ? marked.parse(this.value) : '<em>No content provided.</em>';
    });

    modalSaveLinkBtn.addEventListener('click', async () => {
        modalSaveLinkBtn.disabled = true;
        modalSaveLinkBtn.innerHTML = '<span class="spinner-border spinner-border-sm" role="status" aria-hidden="true"></span> Saving...';

        const linkId = modalLinkIdInput.value;
        const score = modalRelevanceScoreInput.value;
        const content = modalRelevanceContentInput.value;
        
        const sourceStepId = modalSourceStepIdInput.value; 
        let targetStepId;

        const payload = {
            relevance_score: parseInt(score),
            relevance_content: content.trim() === '' ? null : content.trim()
        };

        let url, method;

        if (linkId) { // Update
            url = `/review/api/process-links/link/${linkId}`;
            method = 'PUT';
            targetStepId = modalTargetStepIdInput.value;
        } else { // Create
            url = `/review/api/process-links/link`;
            method = 'POST';
            const targetSelect = document.getElementById('modalTargetStepSelect');
            if (!targetSelect || !targetSelect.value) {
                showFlashMessage('Please select a target step.', 'warning');
                modalSaveLinkBtn.disabled = false;
                modalSaveLinkBtn.innerHTML = 'Save Link';
                return;
            }
            targetStepId = targetSelect.value;

            payload.source_step_id = parseInt(sourceStepId);
            payload.target_step_id = parseInt(targetStepId);

            if (payload.source_step_id === payload.target_step_id) {
                 showFlashMessage('Cannot link a step to itself.', 'warning');
                 modalSaveLinkBtn.disabled = false;
                 modalSaveLinkBtn.innerHTML = 'Save Link';
                 return;
            }
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
                linkModal.hide();
                loadDiagramBtn.click(); // Reload diagram to show changes
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

    modalDeleteLinkBtn.addEventListener('click', async () => {
        const linkId = modalLinkIdInput.value;
        if (!linkId) return;

        if (confirm('Are you sure you want to delete this link? This action cannot be undone.')) {
            modalDeleteLinkBtn.disabled = true;
            modalDeleteLinkBtn.innerHTML = '<span class="spinner-border spinner-border-sm" role="status" aria-hidden="true"></span> Deleting...';
            try {
                const response = await fetch(`/review/api/process-links/link/${linkId}`, { method: 'DELETE' });
                const result = await response.json();
                if (result.success) {
                    showFlashMessage(result.message, 'success');
                    linkModal.hide();
                    loadDiagramBtn.click(); // Reload diagram to reflect deletion
                } else {
                    showFlashMessage(`Error: ${result.error || 'Could not delete link.'}`, 'danger');
                }
            } catch (error) {
                showFlashMessage(`Network error: ${error.message}`, 'danger');
            } finally {
                modalDeleteLinkBtn.disabled = false;
                modalDeleteLinkBtn.innerHTML = 'Delete Link';
            }
        }
    });
    
    focusAreaSelect.addEventListener('change', function() {
        const focusValue = this.value;
        Array.from(comparisonAreaSelect.options).forEach(opt => {
            if (opt.value === focusValue && focusValue !== "") {
                opt.disabled = true;
                if (opt.selected) {
                    opt.selected = false; // Deselect if it was selected
                }
            } else {
                opt.disabled = false;
            }
        });
        // Potentially trigger a re-render or update of Comparison Area Select if using a library like Choices.js
        // For standard select, this is usually enough.
    });
});