// backend/static/js/review_process_links_ui.js

document.addEventListener('DOMContentLoaded', function () {
    // DOM Element Selectors
    const focusAreaSelect = document.getElementById('focusAreaSelect');
    const comparisonAreaSelect = document.getElementById('comparisonAreaSelect');
    const loadDiagramBtn = document.getElementById('loadDiagramBtn');
    const sankeyDiagramContainer = document.getElementById('sankeyDiagramContainer');
    const sankeyPlaceholder = document.getElementById('sankeyPlaceholder');

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

    // Chart and Modal Instances
    let sankeyChart = null;
    let linkModal = null; // Will be initialized on first use
    let currentChartData = { nodes: [], links: [] };

    // ECharts initialization
    if (sankeyDiagramContainer && typeof echarts !== 'undefined') {
        sankeyChart = echarts.init(sankeyDiagramContainer);
        window.addEventListener('resize', function() {
            if (sankeyChart) {
                sankeyChart.resize();
            }
        });
    } else {
        console.error("ECharts library or Sankey container #sankeyDiagramContainer not found.");
        if (sankeyPlaceholder) {
            sankeyPlaceholder.textContent = "Error: Chart library not loaded.";
        }
        if (loadDiagramBtn) loadDiagramBtn.disabled = true;
    }

    // --- Utility Functions ---
    function showFlashMessage(message, category = 'info') {
        const flashContainer = document.querySelector('.flash-messages') || document.createElement('div');
        if (!flashContainer.classList.contains('flash-messages')) {
            flashContainer.classList.add('flash-messages');
            const pageContent = document.querySelector('.page-content');
            if (pageContent) {
                const firstChild = pageContent.firstChild;
                pageContent.insertBefore(flashContainer, firstChild);
            } else {
                document.body.prepend(flashContainer);
            }
        }

        const alertDiv = document.createElement('div');
        alertDiv.classList.add('alert', `alert-${category}`, 'alert-dismissible', 'fade', 'show');
        alertDiv.setAttribute('role', 'alert');
        alertDiv.innerHTML = `${message}<button type="button" class="btn-close" data-bs-dismiss="alert" aria-label="Close"></button>`;
        flashContainer.appendChild(alertDiv);

        setTimeout(() => {
            const bsAlert = (window.bootstrap && window.bootstrap.Alert) ? window.bootstrap.Alert.getInstance(alertDiv) : null;
            if (bsAlert) {
                bsAlert.close();
            } else if (alertDiv.parentElement) {
                alertDiv.remove();
            }
        }, 7000);
    }

    // --- Sankey Rendering ---
    function renderSankey(data) {
        currentChartData = data;
        // console.log("Data received by renderSankey:", JSON.stringify(data, null, 2)); // Already logging this

        if (sankeyPlaceholder) {
            sankeyPlaceholder.style.display = 'none';
        }
        if (!sankeyChart) {
            console.error("sankeyChart instance is null, cannot render.");
            return;
        }

        if (!data || !data.nodes || data.nodes.length === 0) {
            console.warn("No nodes to render in Sankey.");
            sankeyChart.clear();
            if (sankeyPlaceholder) {
                sankeyPlaceholder.textContent = 'No process steps found for the selected criteria to display as nodes.';
                sankeyPlaceholder.style.display = 'block';
            }
            return;
        }
        if (!data.links || data.links.length === 0) {
            console.warn("No links to render in Sankey. Displaying nodes only.");
            // Even without links, nodes should render according to depth if provided.
        }

        const option = {
            title: {
                text: 'Process Step Links',
                subtext: 'Flow based on relevance score',
                left: 'center'
            },
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
                                (DB ID: ${originalNode ? originalNode.id : 'N/A'})<br/>
                                <em>Click to add link from this step</em>`;
                    }
                    return '';
                }
            },
            series: [{
                type: 'sankey',
                orient: 'horizontal', // Explicitly set the orientation (default)
                // Removed 'layout' and 'nodeAlign' to let ECharts use 'depth' for layout
                nodeWidth: 30,        // Width of the node rectangles
                nodeGap: 10,          // Gap between nodes in the same column
                emphasis: {
                    focus: 'adjacency'
                },
                data: data.nodes.map(node => ({
                    name: node.name,
                    id: node.id,
                    itemStyle: node.itemStyle,
                    depth: node.depth // This is the key for automatic layout
                })),
                links: data.links.map(link => ({
                    source: link.source,
                    target: link.target,
                    value: link.value,
                    lineStyle: link.lineStyle,
                    data: link.data
                })),
                lineStyle: {
                    color: 'gradient',
                    curveness: 0.5,
                    opacity: 0.6
                },
                label: {
                    show: true,
                    formatter: '{b}',
                    overflow: 'truncate',
                    width: 150,      // Adjust if labels are too long or getting cut
                    ellipsis: '...'
                },
                draggable: true,
                animationDuration: 1000,
                layoutIterations: 32 // Default is 32, should be fine for most cases
            }]
        };

        console.log("ECharts option object (using default layout with depth, explicit orient):", JSON.stringify(option, null, 2));
        try {
            sankeyChart.setOption(option, true);
        } catch (e) {
            console.error("Error setting ECharts option:", e);
            showFlashMessage(`Error rendering diagram: ${e.message}`, 'danger');
            if (sankeyPlaceholder) {
                sankeyPlaceholder.textContent = `Chart rendering error: ${e.message}`;
                sankeyPlaceholder.style.display = 'block';
            }
        }
    }

    // --- Modal Management ---
    async function openLinkModal(linkId = null, sourceStepId = null, sourceStepEchartsName = null) {
        if (!linkModal) {
            if (linkModalElement && typeof window.bootstrap !== 'undefined' && typeof window.bootstrap.Modal === 'function') {
                linkModal = new window.bootstrap.Modal(linkModalElement);
                console.log("Bootstrap Modal initialized successfully on demand.");
            } else {
                console.error("Link review modal element #linkReviewModal or Bootstrap Modal library (window.bootstrap.Modal) not found. Cannot initialize modal for display.");
                showFlashMessage("Modal components missing or Bootstrap not ready. Please check console.", "danger");
                if (sankeyChart && sankeyChart.off) {
                    sankeyChart.off('click');
                    console.warn("Sankey chart click listener disabled due to modal initialization failure.");
                }
                return;
            }
        }

        if (!modalLinkIdInput || !modalSourceStepIdInput || !modalTargetStepIdInput ||
            !modalSourceStepDisplay || !modalTargetStepDisplay || !modalRelevanceScoreInput ||
            !modalRelevanceContentInput || !modalRelevanceContentPreview || !modalDeleteLinkBtn ||
            !modalSaveLinkBtn || !modalLabel) {
            console.error("One or more modal DOM elements are not found. Cannot open modal.");
            showFlashMessage("Modal components missing. Please check console.", "danger");
            return;
        }

        modalLinkIdInput.value = '';
        modalSourceStepIdInput.value = '';
        modalTargetStepIdInput.value = '';
        modalSourceStepDisplay.textContent = 'Loading...';
        modalTargetStepDisplay.innerHTML = 'Loading...';
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
                if (typeof marked !== 'undefined' && marked.parse) {
                    modalRelevanceContentPreview.innerHTML = linkData.relevance_content ? marked.parse(linkData.relevance_content) : marked.parse('<em>No content provided.</em>');
                } else {
                    modalRelevanceContentPreview.innerHTML = linkData.relevance_content || '<em>No content provided.</em>';
                }
            } catch (error) {
                showFlashMessage(`Error loading link details: ${error.message}`, 'danger');
                if (linkModal) linkModal.hide();
                return;
            }
        } else if (sourceStepId && sourceStepEchartsName) {
            modalLabel.textContent = 'Create New Link';
            modalSourceStepIdInput.value = sourceStepId;
            modalSourceStepDisplay.textContent = sourceStepEchartsName;
            let targetStepOptionsHtml = '<option value="">-- Select Target Step --</option>';
            if (currentChartData.nodes && currentChartData.nodes.length > 0) {
                const sortedTargetNodes = currentChartData.nodes
                    .filter(node => String(node.id) !== String(sourceStepId))
                    .sort((a, b) => a.name.localeCompare(b.name));
                sortedTargetNodes.forEach(node => {
                    targetStepOptionsHtml += `<option value="${node.id}">${node.name}</option>`;
                });
            } else {
                targetStepOptionsHtml = '<option value="">-- No target steps available in current view --</option>';
            }
            modalTargetStepDisplay.innerHTML = `<select id="modalTargetStepSelect" class="form-select">${targetStepOptionsHtml}</select>`;
            if (typeof marked !== 'undefined' && marked.parse) {
                modalRelevanceContentPreview.innerHTML = marked.parse('<em>No content provided.</em>');
            } else {
                modalRelevanceContentPreview.innerHTML = '<em>No content provided.</em>';
            }
        } else {
            showFlashMessage("Modal error: Insufficient data to open (sourceStepId or linkId missing).", "warning");
            return;
        }
        if (linkModal) {
             linkModal.show();
        } else {
            console.error("Cannot show modal because linkModal instance is null.");
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
            if (sankeyPlaceholder) {
                sankeyPlaceholder.textContent = 'Loading diagram data...';
                sankeyPlaceholder.style.display = 'block';
            }
            if (sankeyChart) {
                sankeyChart.clear();
            }

            try {
                const params = new URLSearchParams({ focus_area_id: focusAreaId });
                comparisonAreaIds.forEach(id => params.append('comparison_area_ids[]', id));
                console.log(`Fetching data from: /review/api/process-links/data?${params.toString()}`);
                const response = await fetch(`/review/api/process-links/data?${params.toString()}`);
                if (!response.ok) {
                    let errorMsg = `Server error: ${response.status}`;
                    try { const errorData = await response.json(); errorMsg = errorData.error || errorMsg; } catch (e) { /* Ignore */ }
                    throw new Error(errorMsg);
                }
                const data = await response.json();
                console.log("Data fetched from API:", JSON.stringify(data, null, 2));
                if (data.error) { throw new Error(data.error); }
                if (data.nodes && data.nodes.length > 0) {
                    renderSankey(data);
                } else {
                    if (sankeyPlaceholder) {
                        sankeyPlaceholder.textContent = 'No process steps found for the selected criteria. Adjust your selections or add data.';
                        sankeyPlaceholder.style.display = 'block';
                    }
                    currentChartData = { nodes: [], links: [] };
                    if (sankeyChart) { sankeyChart.clear(); }
                }
            } catch (error) {
                console.error('Error in loadDiagramBtn:', error);
                showFlashMessage(`Error loading diagram: ${error.message}`, 'danger');
                if (sankeyPlaceholder) {
                    sankeyPlaceholder.textContent = `Error loading diagram: ${error.message}. Check console.`;
                    sankeyPlaceholder.style.display = 'block';
                }
            } finally {
                loadDiagramBtn.disabled = false;
                loadDiagramBtn.innerHTML = 'Load Diagram';
            }
        });
    } else {
        console.error("loadDiagramBtn not found");
    }

    if (sankeyChart) {
        sankeyChart.on('click', async function (params) {
            console.log("Sankey click params:", params);
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

    if (modalRelevanceContentInput && modalRelevanceContentPreview) {
        modalRelevanceContentInput.addEventListener('input', function() {
            if (typeof marked !== 'undefined' && marked.parse) {
                modalRelevanceContentPreview.innerHTML = this.value ? marked.parse(this.value) : marked.parse('<em>No content provided.</em>');
            } else {
                modalRelevanceContentPreview.textContent = this.value || 'No content provided.';
            }
        });
    } else {
         console.error("modalRelevanceContentInput or modalRelevanceContentPreview not found");
    }

    if (modalSaveLinkBtn) {
        modalSaveLinkBtn.addEventListener('click', async () => {
            if (!modalLinkIdInput || !modalRelevanceScoreInput || !modalRelevanceContentInput || !modalSourceStepIdInput || !linkModal) {
                showFlashMessage('Modal save components missing or modal not initialized.', 'danger');
                return;
            }
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
            if (linkId) {
                url = `/review/api/process-links/link/${linkId}`;
                method = 'PUT';
                targetStepId = modalTargetStepIdInput.value;
                if (!targetStepId) { console.error("TargetStepID missing for an existing link PUT operation."); }
            } else {
                url = `/review/api/process-links/link`;
                method = 'POST';
                const targetSelect = document.getElementById('modalTargetStepSelect');
                if (!targetSelect || !targetSelect.value) {
                    showFlashMessage('Please select a target step.', 'warning');
                    modalSaveLinkBtn.disabled = false; modalSaveLinkBtn.innerHTML = 'Save Link'; return;
                }
                targetStepId = targetSelect.value;
                payload.source_step_id = parseInt(sourceStepId);
                payload.target_step_id = parseInt(targetStepId);
                if (payload.source_step_id === payload.target_step_id) {
                    showFlashMessage('Cannot link a step to itself.', 'warning');
                    modalSaveLinkBtn.disabled = false; modalSaveLinkBtn.innerHTML = 'Save Link'; return;
                }
            }
            try {
                const response = await fetch(url, { method: method, headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(payload) });
                const result = await response.json();
                if (result.success) {
                    showFlashMessage(result.message, 'success');
                    if (linkModal) linkModal.hide();
                    if (loadDiagramBtn) loadDiagramBtn.click();
                } else { showFlashMessage(`Error: ${result.error || 'Could not save link.'}`, 'danger'); }
            } catch (error) { showFlashMessage(`Network error: ${error.message}`, 'danger');
            } finally { modalSaveLinkBtn.disabled = false; modalSaveLinkBtn.innerHTML = linkId ? 'Save Changes' : 'Save Link'; }
        });
    } else {
        console.error("modalSaveLinkBtn not found");
    }

    if (modalDeleteLinkBtn) {
        modalDeleteLinkBtn.addEventListener('click', async () => {
            if (!modalLinkIdInput || !linkModal) {
                showFlashMessage('Modal delete components missing or modal not initialized.', 'danger');
                return;
            }
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
                        if (linkModal) linkModal.hide();
                        if (loadDiagramBtn) loadDiagramBtn.click();
                    } else { showFlashMessage(`Error: ${result.error || 'Could not delete link.'}`, 'danger'); }
                } catch (error) { showFlashMessage(`Network error: ${error.message}`, 'danger');
                } finally { modalDeleteLinkBtn.disabled = false; modalDeleteLinkBtn.innerHTML = 'Delete Link'; }
            }
        });
    } else {
        console.error("modalDeleteLinkBtn not found");
    }

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
    } else {
        console.error("focusAreaSelect or comparisonAreaSelect not found");
    }
});