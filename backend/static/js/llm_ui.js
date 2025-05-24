document.addEventListener('DOMContentLoaded', function () {
    const areaSelect = document.getElementById('area_ids');
    const stepSelect = document.getElementById('step_ids');
    const fieldCheckboxes = document.querySelectorAll('input[name="fields"]');

    const areaSearchInput = document.getElementById('area_search');
    const stepSearchInput = document.getElementById('step_search');

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

    // Store original options for filtering
    let originalAreaOptions = [];
    if (areaSelect) {
        originalAreaOptions = Array.from(areaSelect.options).map(opt => ({
            value: opt.value,
            text: opt.text,
            element: opt.cloneNode(true) // Keep a clone of the original option element
        }));
    }

    let originalStepOptions = [];
    if (stepSelect) {
        originalStepOptions = Array.from(stepSelect.options).map(opt => ({
            value: opt.value,
            text: opt.text,
            areaId: opt.dataset.areaId || '',
            element: opt.cloneNode(true)
        }));
    }

    // --- Helper: Update selected counts ---
    function updateSelectedCount(selectElement) {
        if (!selectElement) return;
        const displayElementId = selectElement.id + '_selected_count';
        const displayElement = document.getElementById(displayElementId);

        if (displayElement) {
            const count = selectElement.selectedOptions.length;
            displayElement.textContent = count > 0 ? ` (${count} selected)` : '';
        }
    }

    // --- Filtering and Select/Clear All Logic ---
    function filterAndRebuildSelect(selectElement, originalOptions, searchTerm, areaFilterIds = null) {
        if (!selectElement) return;
        const selectedValues = Array.from(selectElement.selectedOptions).map(opt => opt.value);
        selectElement.innerHTML = ''; // Clear current options

        originalOptions.forEach(optData => {
            const matchesSearch = !searchTerm || optData.text.toLowerCase().includes(searchTerm.toLowerCase());
            let matchesArea = true;
            if (areaFilterIds && areaFilterIds.length > 0 && optData.areaId) {
                matchesArea = areaFilterIds.includes(optData.areaId);
            } else if (areaFilterIds && areaFilterIds.length > 0 && !optData.areaId && selectElement.id === 'step_ids') {
                matchesArea = false;
            }

            if (matchesSearch && matchesArea) {
                const newOption = optData.element.cloneNode(true);
                if (selectedValues.includes(newOption.value)) {
                    newOption.selected = true;
                }
                selectElement.add(newOption);
            }
        });
        updateSelectedCount(selectElement); // Update count after rebuilding
    }

    if (areaSearchInput && areaSelect) {
        areaSearchInput.addEventListener('input', () => {
            filterAndRebuildSelect(areaSelect, originalAreaOptions, areaSearchInput.value);
        });
    }

    if (stepSearchInput && stepSelect) {
        stepSearchInput.addEventListener('input', () => {
            const selectedAreaIds = areaSelect ? Array.from(areaSelect.selectedOptions).map(opt => opt.value) : [];
            filterAndRebuildSelect(stepSelect, originalStepOptions, stepSearchInput ? stepSearchInput.value : '', selectedAreaIds);
        });
    }

    if (areaSelect) {
        areaSelect.addEventListener('change', () => {
            const selectedAreaIds = Array.from(areaSelect.selectedOptions).map(opt => opt.value);
            filterAndRebuildSelect(stepSelect, originalStepOptions, stepSearchInput ? stepSearchInput.value : '', selectedAreaIds);
            updateSelectedCount(areaSelect);
        });
    }
    
    if (stepSelect) {
        stepSelect.addEventListener('change', () => {
             updateSelectedCount(stepSelect);
        });
    }

    function setupSelectControls(selectElement, selectAllButtonId, clearAllButtonId) {
        const selectAllButton = document.getElementById(selectAllButtonId);
        const clearAllButton = document.getElementById(clearAllButtonId);

        if (!selectElement || !selectAllButton || !clearAllButton) return;

        selectAllButton.addEventListener('click', () => {
            Array.from(selectElement.options).forEach(opt => {
                opt.selected = true;
            });
            selectElement.dispatchEvent(new Event('change'));
        });

        clearAllButton.addEventListener('click', () => {
            Array.from(selectElement.options).forEach(opt => opt.selected = false);
            selectElement.dispatchEvent(new Event('change'));
        });
    }

    setupSelectControls(areaSelect, 'selectAllAreas', 'clearAllAreas');
    setupSelectControls(stepSelect, 'selectAllSteps', 'clearAllSteps');

    // Select All / Clear All for Field Checkboxes
    const selectAllFieldsBtn = document.getElementById('selectAllFields');
    const clearAllFieldsBtn = document.getElementById('clearAllFields');

    if (selectAllFieldsBtn && fieldCheckboxes.length > 0) {
        selectAllFieldsBtn.addEventListener('click', () => fieldCheckboxes.forEach(cb => cb.checked = true));
    }
    if (clearAllFieldsBtn && fieldCheckboxes.length > 0) {
        clearAllFieldsBtn.addEventListener('click', () => fieldCheckboxes.forEach(cb => cb.checked = false));
    }

    // JSON Preview Control
    const copyJsonButton = document.getElementById('copyJsonButton');
    const jsonDataPreview = document.getElementById('jsonDataPreview'); // The <pre> tag
    const jsonPreviewContainer = document.getElementById('jsonPreviewContainer'); // The wrapping div
    const toggleJsonPreviewButton = document.getElementById('toggleJsonPreview');
    const tokenCountDisplay = document.getElementById('tokenCountDisplay'); // The token count paragraph

    // Determine if there is actual data to display/copy
    // The `prepared_data` variable is passed from Flask. If it's [], it means no data.
    // If it's None, it means the form hasn't been submitted yet.
    // So, `prepared_data.length > 0` (via template rendering to `tojson`) is the most reliable check.
    const hasData = jsonDataPreview && jsonDataPreview.textContent.trim() !== '[]' && jsonDataPreview.textContent.trim() !== 'null' && jsonDataPreview.textContent.trim() !== '';

    // Conditionally show/hide buttons and token count based on whether data exists
    // These buttons are now in the card-header, so they are always visible if data exists
    // and we only hide them if hasData is false.
    if (copyJsonButton) copyJsonButton.style.display = hasData ? 'inline-block' : 'none';
    if (toggleJsonPreviewButton) toggleJsonPreviewButton.style.display = hasData ? 'inline-block' : 'none';
    if (tokenCountDisplay) tokenCountDisplay.style.display = hasData ? 'block' : 'none';


    // Toggle JSON Preview visibility
    if (toggleJsonPreviewButton && jsonPreviewContainer) { // No need to check hasData here, display handled by previous block
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
    if (copyJsonButton && jsonDataPreview) { // No need to check hasData here, display handled by previous block
        copyJsonButton.addEventListener('click', () => {
            if (!hasData) { // Double check if data actually exists before trying to copy
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

    // Initial setup calls for selected counts after DOM is ready
    if (areaSelect) {
        filterAndRebuildSelect(areaSelect, originalAreaOptions, areaSearchInput ? areaSearchInput.value : '');
        areaSelect.dispatchEvent(new Event('change')); 
    }
    if (stepSelect) { 
        updateSelectedCount(stepSelect);
    }


    // --- LLM Chat Window Logic ---

    // Function to convert markdown to HTML
    function markdownToHtml(markdownText) {
        // Check if 'marked' exists and if 'marked.parse' is a function
        if (typeof marked !== 'undefined' && typeof marked.parse === 'function') {
            return marked.parse(markdownText);
        }
        console.warn("Marked.js not loaded or 'marked.parse' function not found. Markdown will not be rendered.");
        return markdownText; // Return original text if converter not available
    }

    // Function to add a message to the chat display
    function addMessageToChat(role, content) {
        const messageElement = document.createElement('div');
        messageElement.classList.add('chat-bubble', `chat-bubble-${role}`);
        messageElement.innerHTML = markdownToHtml(content); // Render markdown
        chatDisplay.appendChild(messageElement);
        chatDisplay.scrollTop = chatDisplay.scrollHeight; // Scroll to bottom
    }

    // Populate chat history on load (from Flask template)
    if (chatDisplay) {
        // Clear initial "Start a conversation" message if history exists
        if (chatDisplay.children.length === 1 && chatDisplay.children[0].classList.contains('text-muted')) {
            chatDisplay.innerHTML = '';
        }
        // Flask renders initial chat history directly into the HTML, so we don't need to re-add here
        // We just need to scroll to bottom if there's history
        chatDisplay.scrollTop = chatDisplay.scrollHeight;
    }


    // Handle sending message
    if (sendMessageButton && chatInput && llmModelSelect) {
        sendMessageButton.addEventListener('click', async () => {
            const message = chatInput.value.trim();
            const selectedModel = llmModelSelect.value;
            const systemPrompt = systemPromptInput ? systemPromptInput.value.trim() : ''; // Get system prompt

            if (!message || !selectedModel) {
                alert('Please enter a message and select a model.');
                return;
            }

            addMessageToChat('user', message);
            chatInput.value = ''; // Clear input

            sendMessageButton.disabled = true; // Disable button while loading
            chatInput.disabled = true; // Disable input
            llmModelSelect.disabled = true; // Disable model select
            if (systemPromptInput) systemPromptInput.disabled = true; // Disable system prompt input too
            if (saveSystemPromptButton) saveSystemPromptButton.disabled = true; // Disable save button

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
                        // No need to explicitly send system_prompt here, it's fetched on backend from current_user
                        // system_prompt: systemPrompt // This was my initial thought but the backend already fetches it
                    }),
                });

                const data = await response.json();

                if (data.success) {
                    loadingBubble.remove(); // Remove loading bubble
                    addMessageToChat('assistant', data.message);
                } else {
                    loadingBubble.innerHTML = `<i class="fas fa-exclamation-triangle me-2"></i>Error: ${data.message}`;
                    loadingBubble.style.backgroundColor = 'var(--raw-alert-danger-bg)';
                    loadingBubble.style.color = 'var(--raw-alert-danger-text)';
                    console.error('LLM Chat Error:', data.message);
                }
            } catch (error) {
                console.error('Network or server error:', error);
                loadingBubble.innerHTML = `<i class="fas fa-exclamation-triangle me-2"></i>Network Error: Could not reach LLM service.`;
                loadingBubble.style.backgroundColor = 'var(--raw-alert-danger-bg)';
                loadingBubble.style.color = 'var(--raw-alert-danger-text)';
            } finally {
                sendMessageButton.disabled = false; // Re-enable button
                chatInput.disabled = false; // Re-enable input
                llmModelSelect.disabled = false; // Re-enable model select
                if (systemPromptInput) systemPromptInput.disabled = false; // Re-enable
                if (saveSystemPromptButton) saveSystemPromptButton.disabled = false; // Re-enable
                chatInput.focus(); // Focus input for next message
            }
        });

        chatInput.addEventListener('keypress', (e) => {
            if (e.key === 'Enter') {
                sendMessageButton.click(); // Trigger send on Enter
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
                        chatDisplay.innerHTML = '<p class="text-muted text-center mt-3">Start a conversation with the LLM.</p>';
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

    // Handle saving system prompt
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
                setTimeout(() => {
                    saveSystemPromptMessage.textContent = ''; // Clear message after a few seconds
                }, 3000);
            }
        });
    }

    // --- Bootstrap Collapse Icon Toggle ---
    const selectionCriteriaHeader = document.getElementById('selectionCriteriaHeader');
    const preparedDataHeader = document.getElementById('preparedDataHeader');
    const llmChatHeader = document.getElementById('llmChatHeader');
    const systemPromptHeader = document.getElementById('systemPromptHeader'); // NEW

    // Function to update icon based on collapse state
    function updateCollapseIcon(headerElement, targetId) {
        const collapseElement = document.getElementById(targetId);
        const iconElement = headerElement.querySelector('i');
        
        // This class is added by Bootstrap when the element is actually collapsing/expanding
        collapseElement.addEventListener('shown.bs.collapse', () => {
            iconElement.classList.remove('fa-chevron-down');
            iconElement.classList.add('fa-chevron-up');
        });
        collapseElement.addEventListener('hidden.bs.collapse', () => {
            iconElement.classList.remove('fa-chevron-up');
            iconElement.classList.add('fa-chevron-down');
        });

        // Set initial icon state based on 'show' class
        if (collapseElement.classList.contains('show')) {
            iconElement.classList.remove('fa-chevron-down');
            iconElement.classList.add('fa-chevron-up');
        } else {
            iconElement.classList.remove('fa-chevron-up');
            iconElement.classList.add('fa-chevron-down');
        }
    }

    if (selectionCriteriaHeader) updateCollapseIcon(selectionCriteriaHeader, 'selectionCriteriaBody');
    if (preparedDataHeader) updateCollapseIcon(preparedDataHeader, 'preparedDataBody');
    if (llmChatHeader) updateCollapseIcon(llmChatHeader, 'llmChatBody');
    if (systemPromptHeader) updateCollapseIcon(systemPromptHeader, 'systemPromptBody'); // NEW

    // --- Explicitly initialize Bootstrap Collapses (as a fallback/diagnostic) ---
    // This finds all elements with data-bs-toggle="collapse"
    const collapseToggles = document.querySelectorAll('[data-bs-toggle="collapse"]');
    collapseToggles.forEach(toggle => {
        const targetId = toggle.getAttribute('data-bs-target');
        const collapseElement = document.querySelector(targetId);

        if (collapseElement) {
            // Bootstrap's JS will attach its own listeners to these toggles automatically.
            // This explicit initialization is mostly for components that don't auto-init,
            // or if the DOM is modified *after* Bootstrap's initial scan.
            // For collapse, the data attributes usually suffice, but this ensures they're "seen".
            // No direct 'new bootstrap.Collapse(element)' is usually needed for data-attributes.
            // However, ensuring the elements are ready for Bootstrap's auto-scan can be key.
            
            // The issue is likely *not* that the component isn't being explicitly instantiated,
            // but rather that Bootstrap's core event listeners aren't firing on the toggle.
            // This often points to a JS error or bad cached script.

            // Let's add a console log to confirm these toggles are found.
            console.log("Found collapse toggle:", toggle, "for target:", collapseElement);
        }
    });

}); // End of DOMContentLoaded