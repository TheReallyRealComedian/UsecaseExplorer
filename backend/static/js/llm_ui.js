// backend/static/js/llm_ui.js
document.addEventListener('DOMContentLoaded', function () {
    // Custom Selects Initialization
    initializeCustomSelects();
    // Search Functionality Initialization
    initializeSearch();
    // Update counts for custom selects on page load
    updateAllCounts();

    // Chat elements
    const chatDisplay = document.getElementById('chatDisplay');
    const chatInput = document.getElementById('chatInput');
    const sendMessageButton = document.getElementById('sendMessageButton');
    const clearChatButton = document.getElementById('clearChatButton');
    const llmModelSelect = document.getElementById('llmModelSelect');

    // System Prompt elements
    const systemPromptInput = document.getElementById('systemPromptInput');
    const saveSystemPromptButton = document.getElementById('saveSystemPromptButton');
    const saveSystemPromptMessage = document.getElementById('saveSystemPromptMessage');

    // --- Custom Select Implementation ---
    function initializeCustomSelects() {
        document.querySelectorAll('.select-option').forEach(option => {
            option.addEventListener('click', function() {
                this.classList.toggle('selected');
                updateHiddenInputs(this.dataset.name);
                updateCount(this.dataset.name);
            });
        });
    }

    // Update hidden inputs for form submission
    function updateHiddenInputs(inputName) {
        const container = document.getElementById(inputName.replace('_ids', '') + '_hidden_inputs');
        if (!container) return;
        
        container.innerHTML = '';
        
        const selectedOptions = document.querySelectorAll(`.select-option[data-name="${inputName}"].selected`);
        selectedOptions.forEach(option => {
            const input = document.createElement('input');
            input.type = 'hidden';
            input.name = inputName;
            input.value = option.dataset.value;
            container.appendChild(input);
        });
    }

    // Update selection counts
    function updateCount(inputName) {
        const countElement = document.getElementById(inputName + '_selected_count');
        if (!countElement) return;
        
        const selectedCount = document.querySelectorAll(`.select-option[data-name="${inputName}"].selected`).length;
        countElement.textContent = `${selectedCount} selected`;
    }

    function updateAllCounts() {
        updateCount('area_ids');
        updateCount('step_ids');
        updateCount('usecase_ids');
    }

    // --- Search functionality ---
    function initializeSearch() {
        // Area search
        document.getElementById('area_search')?.addEventListener('input', function() {
            filterOptions(this.value, 'area-select-container');
            // Trigger filtering for steps and use cases if their options depend on selected areas
            filterOptions(document.getElementById('step_search')?.value || '', 'step-select-container');
            filterOptions(document.getElementById('usecase_search')?.value || '', 'usecase-select-container');
        });
        
        // Step search
        document.getElementById('step_search')?.addEventListener('input', function() {
            filterOptions(this.value, 'step-select-container');
            // Trigger filtering for use cases
            filterOptions(document.getElementById('usecase_search')?.value || '', 'usecase-select-container');
        });
        
        // Use case search
        document.getElementById('usecase_search')?.addEventListener('input', function() {
            filterOptions(this.value, 'usecase-select-container');
        });
    }

    function filterOptions(searchTerm, containerId) {
        const container = document.getElementById(containerId);
        if (!container) return;
        
        const options = container.querySelectorAll('.select-option');
        const term = searchTerm.toLowerCase();
        
        // Get currently selected Area and Step IDs for dependency filtering
        const selectedAreaIds = Array.from(document.querySelectorAll('.select-option[data-name="area_ids"].selected'))
                                .map(opt => opt.dataset.value);
        const selectedStepIds = Array.from(document.querySelectorAll('.select-option[data-name="step_ids"].selected'))
                               .map(opt => opt.dataset.value);

        options.forEach(option => {
            const text = option.textContent.toLowerCase();
            const optionAreaId = option.dataset.areaId;
            const optionStepId = option.dataset.stepId;

            let matchesSearch = text.includes(term);
            let matchesAreaFilter = true;
            let matchesStepFilter = true;

            // Apply Area filter for Steps and Use Cases
            if (selectedAreaIds.length > 0) {
                if (optionAreaId) {
                    matchesAreaFilter = selectedAreaIds.includes(optionAreaId);
                } else if (containerId === 'step-select-container' || containerId === 'usecase-select-container') {
                    // If an area is selected, but this step/use case has no areaId, it won't match
                    matchesAreaFilter = false;
                }
            }

            // Apply Step filter for Use Cases
            if (containerId === 'usecase-select-container' && selectedStepIds.length > 0) {
                if (optionStepId) {
                    matchesStepFilter = selectedStepIds.includes(optionStepId);
                } else {
                    // If a step is selected, but this use case has no stepId, it won't match
                    matchesStepFilter = false;
                }
            }

            if (matchesSearch && matchesAreaFilter && matchesStepFilter) {
                option.style.display = 'block';
            } else {
                option.style.display = 'none';
            }
        });
    }

    // --- Select All / Clear All functions for custom selects ---
    function selectAll(type) {
        const containerMap = {
            'areas': 'area-select-container',
            'steps': 'step-select-container', 
            'usecases': 'usecase-select-container'
        };
        
        const inputNameMap = {
            'areas': 'area_ids',
            'steps': 'step_ids',
            'usecases': 'usecase_ids'
        };
        
        const container = document.getElementById(containerMap[type]);
        if (!container) return;
        
        const options = container.querySelectorAll('.select-option');
        options.forEach(option => {
            if (option.style.display !== 'none') { // Only select visible options
                option.classList.add('selected');
            }
        });
        
        const inputName = inputNameMap[type];
        updateHiddenInputs(inputName);
        updateCount(inputName);
        
        // After selecting all, re-apply dependent filters
        if (type === 'areas') {
            filterOptions(document.getElementById('step_search')?.value || '', 'step-select-container');
            filterOptions(document.getElementById('usecase_search')?.value || '', 'usecase-select-container');
        } else if (type === 'steps') {
            filterOptions(document.getElementById('usecase_search')?.value || '', 'usecase-select-container');
        }
    }

    function clearAll(type) {
        const containerMap = {
            'areas': 'area-select-container',
            'steps': 'step-select-container',
            'usecases': 'usecase-select-container'
        };
        
        const inputNameMap = {
            'areas': 'area_ids',
            'steps': 'step_ids', 
            'usecases': 'usecase_ids'
        };
        
        const container = document.getElementById(containerMap[type]);
        if (!container) return;
        
        const options = container.querySelectorAll('.select-option');
        options.forEach(option => option.classList.remove('selected'));
        
        const inputName = inputNameMap[type];
        updateHiddenInputs(inputName);
        updateCount(inputName);

        // After clearing all, re-apply dependent filters
        if (type === 'areas') {
            filterOptions(document.getElementById('step_search')?.value || '', 'step-select-container');
            filterOptions(document.getElementById('usecase_search')?.value || '', 'usecase-select-container');
        } else if (type === 'steps') {
            filterOptions(document.getElementById('usecase_search')?.value || '', 'usecase-select-container');
        }
    }

    // --- Event Listeners for Custom Select All/Clear All Buttons ---
    document.getElementById('selectAllAreas')?.addEventListener('click', () => selectAll('areas'));
    document.getElementById('clearAllAreas')?.addEventListener('click', () => clearAll('areas'));
    
    document.getElementById('selectAllSteps')?.addEventListener('click', () => selectAll('steps'));
    document.getElementById('clearAllSteps')?.addEventListener('click', () => clearAll('steps'));
    
    document.getElementById('selectAllUsecases')?.addEventListener('click', () => selectAll('usecases'));
    document.getElementById('clearAllUsecases')?.addEventListener('click', () => clearAll('usecases'));

    // --- Logic for dependent filtering of custom selects when options are clicked ---
    // This ensures that when a selection changes, the dependent lists are re-filtered visually.
    document.querySelectorAll('.select-option[data-name="area_ids"]').forEach(option => {
        option.addEventListener('click', () => {
            // Re-apply filters for steps and usecases based on current selections and search terms
            filterOptions(document.getElementById('step_search')?.value || '', 'step-select-container');
            filterOptions(document.getElementById('usecase_search')?.value || '', 'usecase-select-container');
        });
    });

    document.querySelectorAll('.select-option[data-name="step_ids"]').forEach(option => {
        option.addEventListener('click', () => {
            // Re-apply filters for usecases based on current selections and search terms
            filterOptions(document.getElementById('usecase_search')?.value || '', 'usecase-select-container');
        });
    });

    // --- JSON Preview Control ---
    const copyJsonButton = document.getElementById('copyJsonButton');
    const jsonDataPreview = document.getElementById('jsonDataPreview'); // The <pre> tag
    const jsonPreviewContainer = document.getElementById('jsonPreviewContainer'); // The wrapping div
    const toggleJsonPreviewButton = document.getElementById('toggleJsonPreview');
    const tokenCountDisplay = document.getElementById('tokenCountDisplay'); // The token count paragraph

    // Determine if there is actual data to display/copy
    const hasData = jsonDataPreview && 
                    jsonDataPreview.textContent.trim() !== '{"process_steps": [], "use_cases": []}' &&
                    jsonDataPreview.textContent.trim() !== 'null' && 
                    jsonDataPreview.textContent.trim() !== '';

    // Conditionally show/hide buttons and token count based on whether data exists
    if (copyJsonButton) copyJsonButton.style.display = hasData ? 'inline-block' : 'none';
    // FIX: Corrected typo here from toggleJsonJsonPreviewButton to toggleJsonPreviewButton
    if (toggleJsonPreviewButton) toggleJsonPreviewButton.style.display = hasData ? 'inline-block' : 'none'; 
    if (tokenCountDisplay) tokenCountDisplay.style.display = hasData ? 'block' : 'none';

    // Toggle JSON Preview visibility
    if (toggleJsonPreviewButton && jsonPreviewContainer) {
        toggleJsonPreviewButton.addEventListener('click', () => {
            const isHidden = jsonPreviewContainer.style.display === 'none';
            if (isHidden) {
                jsonPreviewContainer.style.display = 'block';
                toggleJsonPreviewButton.innerHTML = '<i class="fas fa-eye-slash me-1"></i>Hide JSON';
            } else {
                jsonPreviewContainer.style.display = 'none';
                toggleJsonPreviewButton.innerHTML = '<i class="fas fa-eye me-1"></i>Show JSON';
            }
        });
    }

    // Copy JSON to Clipboard
    if (copyJsonButton && jsonDataPreview) {
        copyJsonButton.addEventListener('click', () => {
            if (!hasData) {
                alert('No data to copy.');
                return;
            }
            navigator.clipboard.writeText(jsonDataPreview.textContent)
                .then(() => {
                    const originalHTML = copyJsonButton.innerHTML;
                    copyJsonButton.innerHTML = '<i class="fas fa-check me-1"></i>Copied!';
                    copyJsonButton.classList.remove('btn-outline-secondary', 'btn-danger');
                    copyJsonButton.classList.add('btn-success');
                    setTimeout(() => {
                        copyJsonButton.innerHTML = originalHTML;
                        copyJsonButton.classList.remove('btn-success');
                        copyJsonButton.classList.add('btn-outline-secondary');
                    }, 2000);
                })
                .catch(err => {
                    console.error('Failed to copy JSON: ', err);
                    const originalHTML = copyJsonButton.innerHTML;
                    copyJsonButton.innerHTML = '<i class="fas fa-times me-1"></i>Failed!';
                    copyJsonButton.classList.remove('btn-outline-secondary', 'btn-success');
                    copyJsonButton.classList.add('btn-danger');
                     setTimeout(() => {
                        copyJsonButton.innerHTML = originalHTML;
                        copyJsonButton.classList.remove('btn-danger');
                        copyJsonButton.classList.add('btn-outline-secondary');
                    }, 2000);
                });
        });
    }


    // --- LLM Chat Window Logic ---
    // Function to convert markdown to HTML
    function markdownToHtml(markdownText) {
        // Check if marked library is available (it's loaded via CDN in the template)
        if (typeof marked !== 'undefined' && typeof marked.parse === 'function') {
            return marked.parse(markdownText);
        }
        console.warn("Marked.js not loaded or 'marked.parse' function not found. Markdown will not be rendered.");
        return markdownText;
    }

    // Function to add a message to the chat display
    function addMessageToChat(role, content) {
        const messageElement = document.createElement('div');
        messageElement.classList.add('chat-bubble', `chat-bubble-${role}`);
        messageElement.innerHTML = markdownToHtml(content);
        chatDisplay.appendChild(messageElement);
        chatDisplay.scrollTop = chatDisplay.scrollHeight;
    }

    // Populate chat history on load (from Flask template)
    if (chatDisplay) {
        // Remove the placeholder message if there's actual chat history
        if (chatDisplay.children.length === 1 && chatDisplay.children[0].classList.contains('chat-placeholder')) {
            chatDisplay.innerHTML = '';
        }
        chatDisplay.scrollTop = chatDisplay.scrollHeight; // Scroll to bottom on load
    }

    // Handle sending message
    if (sendMessageButton && chatInput && llmModelSelect) {
        sendMessageButton.addEventListener('click', async () => {
            const message = chatInput.value.trim();
            const selectedModel = llmModelSelect.value;
            // The system prompt is retrieved on the server, not directly sent from here
            // const systemPrompt = systemPromptInput ? systemPromptInput.value.trim() : '';

            if (!message || !selectedModel) {
                alert('Please enter a message and select a model.');
                return;
            }

            addMessageToChat('user', message);
            chatInput.value = '';

            sendMessageButton.disabled = true;
            chatInput.disabled = true;
            llmModelSelect.disabled = true;
            if (systemPromptInput) systemPromptInput.disabled = true;
            if (saveSystemPromptButton) saveSystemPromptButton.disabled = true;

            const loadingBubble = document.createElement('div');
            loadingBubble.classList.add('chat-bubble', 'chat-bubble-assistant');
            loadingBubble.innerHTML = '<i class="fas fa-spinner fa-spin me-2"></i>Thinking...';
            chatDisplay.appendChild(loadingBubble);
            chatDisplay.scrollTop = chatDisplay.scrollHeight;

            try {
                const response = await fetch('/llm/chat', {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json',
                    },
                    body: JSON.stringify({
                        message: message,
                        model: selectedModel,
                    }),
                });

                const data = await response.json();

                if (data.success) {
                    loadingBubble.remove();
                    addMessageToChat('assistant', data.message);
                } else {
                    // Update loading bubble with error message
                    loadingBubble.innerHTML = `<i class="fas fa-exclamation-triangle me-2"></i>Error: ${data.message}`;
                    loadingBubble.style.backgroundColor = 'var(--raw-alert-danger-bg)';
                    loadingBubble.style.color = 'var(--raw-alert-danger-text)';
                    console.error('LLM Chat Error:', data.message);
                }
            } catch (error) {
                console.error('Network or server error:', error);
                // Update loading bubble with network error
                loadingBubble.innerHTML = `<i class="fas fa-exclamation-triangle me-2"></i>Network Error: Could not reach LLM service.`;
                loadingBubble.style.backgroundColor = 'var(--raw-alert-danger-bg)';
                loadingBubble.style.color = 'var(--raw-alert-danger-text)';
            } finally {
                // Re-enable input fields and buttons
                sendMessageButton.disabled = false;
                chatInput.disabled = false;
                llmModelSelect.disabled = false;
                if (systemPromptInput) systemPromptInput.disabled = false;
                if (saveSystemPromptButton) saveSystemPromptButton.disabled = false;
                chatInput.focus(); // Focus on input for next message
            }
        });

        // Send message on Enter key press in chat input
        chatInput.addEventListener('keypress', (e) => {
            if (e.key === 'Enter') {
                sendMessageButton.click();
            }
        });
    }

    // Handle clear chat button
    if (clearChatButton && chatDisplay) {
        clearChatButton.addEventListener('click', async () => {
            if (confirm('Are you sure you want to clear the entire chat history? This cannot be undone.')) {
                try {
                    const response = await fetch('/llm/chat/clear', { method: 'POST' });
                    const data = await response.json();
                    if (data.success) {
                        // Replace content with original placeholder
                        chatDisplay.innerHTML = '<div class="chat-placeholder"><i class="fas fa-comments"></i><p>Start a conversation with the LLM about your prepared data</p></div>';
                        alert('Chat history cleared!');
                    } else {
                        alert(`Failed to clear chat history: ${data.message}`);
                    }
                } catch (error) {
                    console.error('Error clearing chat history:', error);
                    alert('Network error: Could not clear chat history.');
                }
            }
        });
    }

    // --- Handle saving system prompt ---
    if (saveSystemPromptButton && systemPromptInput && saveSystemPromptMessage) {
        saveSystemPromptButton.addEventListener('click', async () => {
            const prompt = systemPromptInput.value.trim();
            saveSystemPromptButton.disabled = true;
            systemPromptInput.disabled = true;
            saveSystemPromptMessage.textContent = 'Saving...';
            saveSystemPromptMessage.style.color = 'var(--text-color-medium)';

            try {
                const response = await fetch('/llm/system-prompt', {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json',
                    },
                    body: JSON.stringify({ prompt: prompt }),
                });

                const data = await response.json();

                if (data.success) {
                    saveSystemPromptMessage.textContent = 'Saved!';
                    saveSystemPromptMessage.style.color = 'var(--alert-success-text)';
                } else {
                    saveSystemPromptMessage.textContent = `Error: ${data.message}`;
                    saveSystemPromptMessage.style.color = 'var(--alert-danger-text)';
                    console.error('Save System Prompt Error:', data.message);
                }
            } catch (error) {
                saveSystemPromptMessage.textContent = `Network Error: Could not save prompt.`;
                saveSystemPromptMessage.style.color = 'var(--alert-danger-text)';
                console.error('Network Error saving system prompt:', error);
            } finally {
                saveSystemPromptButton.disabled = false;
                systemPromptInput.disabled = false;
                // Clear message after a short delay
                setTimeout(() => {
                    saveSystemPromptMessage.textContent = '';
                }, 3000);
            }
        });
    }

    // --- Bootstrap Collapse Icon Toggle Logic ---
    // Select all collapse headers that should have dynamic icons
    const collapseHeaders = [
        document.getElementById('selectionCriteriaHeader'),
        document.getElementById('preparedDataHeader'),
        document.getElementById('llmChatHeader'),
        document.getElementById('systemPromptHeader')
    ];

    collapseHeaders.forEach(header => {
        if (header) {
            const targetId = header.getAttribute('data-bs-target');
            const collapseElement = document.getElementById(targetId.substring(1)); // Remove '#'
            const iconElement = header.querySelector('i');

            if (collapseElement && iconElement) {
                // Set initial icon state based on 'show' class
                if (collapseElement.classList.contains('show')) {
                    iconElement.classList.remove('fa-chevron-down');
                    iconElement.classList.add('fa-chevron-up');
                } else {
                    iconElement.classList.remove('fa-chevron-up');
                    iconElement.classList.add('fa-chevron-down');
                }

                // Add event listeners for Bootstrap collapse events
                collapseElement.addEventListener('shown.bs.collapse', () => {
                    iconElement.classList.remove('fa-chevron-down');
                    iconElement.classList.add('fa-chevron-up');
                });
                collapseElement.addEventListener('hidden.bs.collapse', () => {
                    iconElement.classList.remove('fa-chevron-up');
                    iconElement.classList.add('fa-chevron-down');
                });
            }
        }
    });

}); // End of DOMContentLoaded

// --- GLOBAL FUNCTIONS FOR FIELD CHECKBOXES (MOVED OUTSIDE DOMContentLoaded) ---
// These functions are called directly from onclick attributes in the HTML
function selectAllStepFields() {
    const checkboxes = document.querySelectorAll('input[name="step_fields"]');
    console.log('Found step checkboxes:', checkboxes.length); // Debug
    checkboxes.forEach(cb => cb.checked = true);
}

function clearAllStepFields() {
    const checkboxes = document.querySelectorAll('input[name="step_fields"]');
    checkboxes.forEach(cb => cb.checked = false);
}

function selectAllUsecaseFields() {
    const checkboxes = document.querySelectorAll('input[name="usecase_fields"]');
    console.log('Found usecase checkboxes:', checkboxes.length); // Debug
    checkboxes.forEach(cb => cb.checked = true);
}

function clearAllUsecaseFields() {
    const checkboxes = document.querySelectorAll('input[name="usecase_fields"]');
    checkboxes.forEach(cb => cb.checked = false);
}