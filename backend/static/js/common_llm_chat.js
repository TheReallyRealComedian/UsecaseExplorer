// UsecaseExplorer/backend/static/js/common_llm_chat.js

/**
 * Reusable module for LLM chat functionality, including text and image input.
 *
 * @param {string} chatDisplayId - ID of the div element where chat messages are displayed.
 * @param {string} chatInputId - ID of the textarea/input for user text messages.
 * @param {string} sendMessageButtonId - ID of the button to send messages.
 * @param {string} clearChatButtonId - ID of the button to clear chat history.
 * @param {string} llmModelSelectId - ID of the select element for LLM model selection.
 * @param {string} systemPromptInputId - ID of the textarea for system prompt (optional, can be null).
 * @param {string} saveSystemPromptButtonId - ID of the button to save system prompt (optional, can be null).
 * @param {string} imagePasteAreaId - ID of the div/element where images can be pasted/dropped (optional, for multimodal chat).
 * @param {string} imagePreviewId - ID of the img element to display pasted image (optional, for multimodal chat).
 * @param {string} clearImageButtonId - ID of the button to clear pasted image (optional, for multimodal chat).
 */
export function initializeLLMChat(
    chatDisplayId, chatInputId, sendMessageButtonId, clearChatButtonId, llmModelSelectId,
    systemPromptInputId = null, saveSystemPromptButtonId = null,
    imagePasteAreaId = null, imagePreviewId = null, clearImageButtonId = null
) {
    const chatDisplay = document.getElementById(chatDisplayId);
    const chatInput = document.getElementById(chatInputId);
    const sendMessageButton = document.getElementById(sendMessageButtonId);
    const clearChatButton = document.getElementById(clearChatButtonId);
    const llmModelSelect = document.getElementById(llmModelSelectId);
    const systemPromptInput = systemPromptInputId ? document.getElementById(systemPromptInputId) : null;
    const saveSystemPromptButton = saveSystemPromptButtonId ? document.getElementById(saveSystemPromptButtonId) : null;
    const imagePasteArea = imagePasteAreaId ? document.getElementById(imagePasteAreaId) : null;
    const imagePreview = imagePreviewId ? document.getElementById(imagePreviewId) : null;
    const clearImageButton = clearImageButtonId ? document.getElementById(clearImageButtonId) : null;

    let currentImageBase64 = null; // Stores the Base64 string of the pasted image

    // --- Helper Functions ---

    // Function to convert markdown to HTML using marked.js
    function markdownToHtml(markdownText) {
        if (typeof marked !== 'undefined' && typeof marked.parse === 'function') {
            return marked.parse(markdownText);
        }
        console.warn("Marked.js not loaded or 'marked.parse' function not found. Markdown will not be rendered.");
        return markdownText;
    }

    // Function to add a message to the chat display
    function addMessageToChat(role, content, imageUrl = null) {
        const messageElement = document.createElement('div');
        messageElement.classList.add('chat-bubble', `chat-bubble-${role}`);
        
        // Add image preview if available
        if (imageUrl) {
            const img = document.createElement('img');
            img.src = imageUrl;
            img.style.maxWidth = '100%';
            img.style.height = 'auto';
            img.style.marginBottom = '10px';
            img.style.borderRadius = '8px';
            img.style.border = '1px solid var(--border-color)';
            messageElement.appendChild(img);
        }

        // Add text content
        const textContent = document.createElement('div');
        textContent.innerHTML = markdownToHtml(content);
        messageElement.appendChild(textContent);

        chatDisplay.appendChild(messageElement);
        chatDisplay.scrollTop = chatDisplay.scrollHeight;
    }

    // Function to clear the image input area
    function clearImageInput() {
        currentImageBase64 = null;
        if (imagePreview) {
            imagePreview.src = '';
            imagePreview.style.display = 'none';
        }
        if (clearImageButton) {
            clearImageButton.style.display = 'none';
        }
        if (imagePasteArea) {
            imagePasteArea.textContent = 'Paste (Ctrl+V) or drag & drop a screenshot here.';
            imagePasteArea.classList.remove('has-image');
            imagePasteArea.style.cursor = 'pointer'; // Restore cursor
        }
    }

    // --- Core Event Listeners ---

    // Initial setup: Populate chat history from API
    // If the chatDisplay already has content (e.g., from Flask template rendering),
    // we assume it's valid history and just ensure scroll. If it's just a placeholder,
    // we'll clear it when fetching history.
    if (chatDisplay) {
        // If it contains only the placeholder element, clear it for dynamic history loading
        if (chatDisplay.children.length === 1 && chatDisplay.children[0].classList.contains('chat-placeholder')) {
            chatDisplay.innerHTML = '';
        }
        chatDisplay.scrollTop = chatDisplay.scrollHeight;
    }
    
    // --- New: Fetch and populate LLM models ---
    async function fetchAndPopulateModels() {
        try {
            const response = await fetch('/llm/get_llm_models');
            const data = await response.json();
            if (data.success && data.models) {
                llmModelSelect.innerHTML = ''; // Clear "Loading models..."
                if (data.models.length > 0) {
                    data.models.forEach(model => {
                        const option = document.createElement('option');
                        option.value = model;
                        option.textContent = model;
                        llmModelSelect.appendChild(option);
                    });
                    llmModelSelect.value = data.models[0]; // Select the first one by default
                } else {
                    const option = document.createElement('option');
                    option.value = "";
                    option.textContent = "No models found";
                    llmModelSelect.appendChild(option);
                    llmModelSelect.disabled = true;
                    sendMessageButton.disabled = true;
                }
            } else {
                llmModelSelect.innerHTML = '<option value="">Error loading models</option>';
                llmModelSelect.disabled = true;
                sendMessageButton.disabled = true;
                console.error("Failed to load LLM models:", data.message);
            }
        } catch (error) {
            llmModelSelect.innerHTML = '<option value="">Network error loading models</option>';
            llmModelSelect.disabled = true;
            sendMessageButton.disabled = true;
            console.error("Network error fetching LLM models:", error);
        }
    }

    // --- New: Fetch and populate chat history ---
    async function fetchAndPopulateChatHistory() {
        try {
            const response = await fetch('/llm/get_chat_history');
            const data = await response.json();
            if (data.success && data.history) {
                chatDisplay.innerHTML = ''; // Clear the chat display, including any placeholder
                if (data.history.length > 0) {
                    data.history.forEach(msg => {
                        addMessageToChat(msg.role, msg.content); // History is text-only from API
                    });
                } else {
                    chatDisplay.innerHTML = '<div class="chat-placeholder"><i class="fas fa-comments"></i><p>Start a conversation with the LLM!</p></div>';
                }
                chatDisplay.scrollTop = chatDisplay.scrollHeight;
            } else {
                console.error("Failed to load chat history:", data.message);
            }
        } catch (error) {
            console.error("Network error fetching chat history:", error);
        }
    }

    // Call fetch functions on initialization
    fetchAndPopulateModels();
    // Only fetch history if the chat display starts empty (not pre-rendered by Flask)
    // This avoids double-loading if the main llm_data_prep.html already renders history.
    if (chatDisplay.children.length === 0 || (chatDisplay.children.length === 1 && chatDisplay.children[0].classList.contains('chat-placeholder'))) {
        fetchAndPopulateChatHistory();
    }


    // Send message handler
    if (sendMessageButton && chatInput && llmModelSelect) {
        sendMessageButton.addEventListener('click', async () => {
            const message = chatInput.value.trim();
            const selectedModel = llmModelSelect.value;
            // systemPromptContent is read client-side for each send from the input field
            const systemPromptContent = systemPromptInput ? systemPromptInput.value.trim() : ''; // This is not used in the payload to Flask currently, backend uses user.system_prompt.

            if (!message && !currentImageBase64) {
                alert('Please enter a message or paste an image.');
                return;
            }
            if (!selectedModel) {
                alert('Please select an LLM model.');
                return;
            }

            // Display user message in chat *before* constructing the payload (good for UX)
            addMessageToChat('user', message, currentImageBase64 ? `data:image/png;base64,${currentImageBase64}` : null);
            
            // Construct the payload with the current state of inputs
            const payload = {
                message: message,
                model: selectedModel,
            };
            if (currentImageBase64) { // This check will now correctly be true if an image was pasted
                payload.image_base64 = currentImageBase64;
            }

            console.log("Frontend sending payload to Flask:", payload); // Log the payload *before* clearing inputs

            // Clear input fields and image *after* payload construction, but before the async network request
            chatInput.value = '';
            clearImageInput(); // This now happens *after* currentImageBase64 has been used for 'payload'

            // Disable UI elements to prevent double-submission
            sendMessageButton.disabled = true;
            chatInput.disabled = true;
            llmModelSelect.disabled = true;
            if (systemPromptInput) systemPromptInput.disabled = true;
            if (saveSystemPromptButton) saveSystemPromptButton.disabled = true;
            if (clearImageButton) clearImageButton.disabled = true;

            const loadingBubble = document.createElement('div');
            loadingBubble.classList.add('chat-bubble', 'chat-bubble-assistant');
            loadingBubble.innerHTML = '<i class="fas fa-spinner fa-spin me-2"></i>Thinking...';
            chatDisplay.appendChild(loadingBubble);
            chatDisplay.scrollTop = chatDisplay.scrollHeight;

            try {
                // Now, the 'payload' being sent via fetch will correctly include 'image_base64'
                const response = await fetch('/llm/chat', { 
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify(payload),
                });

                const data = await response.json();

                if (data.success) {
                    loadingBubble.remove();
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
                // Re-enable UI elements
                sendMessageButton.disabled = false;
                chatInput.disabled = false;
                llmModelSelect.disabled = false;
                if (systemPromptInput) systemPromptInput.disabled = false;
                if (saveSystemPromptButton) saveSystemPromptButton.disabled = false;
                if (clearImageButton) clearImageButton.disabled = false;
                chatInput.focus();
            }
        });

        // Send message on Enter key press in chat input (Shift+Enter for new line)
        chatInput.addEventListener('keypress', (e) => {
            if (e.key === 'Enter' && !e.shiftKey) {
                e.preventDefault();
                sendMessageButton.click();
            }
        });
    }

    // Clear chat history handler
    if (clearChatButton && chatDisplay) {
        clearChatButton.addEventListener('click', async () => {
            if (confirm('Are you sure you want to clear the entire chat history? This cannot be undone.')) {
                try {
                    const response = await fetch('/llm/chat/clear', { method: 'POST' });
                    const data = await response.json();
                    if (data.success) {
                        chatDisplay.innerHTML = '<div class="chat-placeholder"><i class="fas fa-comments"></i><p>Start a conversation with the LLM!</p></div>';
                        // After clearing, re-fetch the empty history to update state consistently
                        // fetchAndPopulateChatHistory(); // This would re-add the placeholder from API
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

    // Save system prompt handler
    if (saveSystemPromptButton && systemPromptInput) {
        // Create a dedicated message element next to the button for feedback
        const saveSystemPromptMessage = document.createElement('span');
        saveSystemPromptMessage.classList.add('ms-3', 'small', 'text-muted');
        // Insert it right after the button
        saveSystemPromptButton.parentNode.insertBefore(saveSystemPromptMessage, saveSystemPromptButton.nextSibling);

        saveSystemPromptButton.addEventListener('click', async () => {
            const prompt = systemPromptInput.value.trim();
            saveSystemPromptButton.disabled = true;
            systemPromptInput.disabled = true;
            saveSystemPromptMessage.textContent = 'Saving...';
            saveSystemPromptMessage.style.color = 'var(--text-secondary)'; // Use a neutral color for 'Saving'

            try {
                const response = await fetch('/llm/system-prompt', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
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

    // --- Image Paste/Drop Functionality ---
    if (imagePasteArea && imagePreview && clearImageButton) {
        imagePasteArea.addEventListener('paste', handleImagePaste);
        imagePasteArea.addEventListener('dragover', handleDragOver);
        imagePasteArea.addEventListener('drop', handleImageDrop);
        clearImageButton.addEventListener('click', clearImageInput);

        // Add this listener for debugging
        imagePasteArea.addEventListener('dragenter', (event) => {
            console.log('Drag entered imagePasteArea');
        });
        imagePasteArea.addEventListener('dragleave', (event) => {
            console.log('Drag left imagePasteArea');
        });
    }

    // Prevents default paste behavior and processes image data from clipboard
    function handleImagePaste(event) {
        event.preventDefault();
        console.log('handleImagePaste triggered');
        const items = (event.clipboardData || event.originalEvent.clipboardData).items;
        processImageItems(items);
    }

    // Highlights drop area on drag over
    function handleDragOver(event) {
        event.preventDefault();
        event.stopPropagation();
        if (imagePasteArea) {
            imagePasteArea.classList.add('drag-over');
        }
    }

    // Processes image data dropped onto the area
    function handleImageDrop(event) {
        event.preventDefault();
        event.stopPropagation();
        if (imagePasteArea) {
            imagePasteArea.classList.remove('drag-over');
        }
        console.log('handleImageDrop triggered');
        const items = event.dataTransfer.items;
        processImageItems(items);
    }

    // Reads and displays image from DataTransferItem list
    function processImageItems(items) {
        console.log('processImageItems: Starting to process items.', items);
        if (!items || items.length === 0) {
            console.log('processImageItems: No items found.');
            return;
        }

        let imageFound = false;
        for (let i = 0; i < items.length; i++) {
            console.log(`  Item ${i}: type = ${items[i].type}, kind = ${items[i].kind}`);
            if (items[i].type.indexOf('image') !== -1) {
                const file = items[i].getAsFile();
                if (file) {
                    imageFound = true;
                    console.log(`  Image file found! Name: ${file.name}, Type: ${file.type}, Size: ${file.size} bytes`);
                    
                    const reader = new FileReader();
                    
                    reader.onload = function(e) {
                        console.log('FileReader onload: Image loaded into FileReader.');
                        console.log('  e.target.result (first 50 chars):', e.target.result ? e.target.result.substring(0, 50) + '...' : 'empty result');
                        
                        const base64Data = e.target.result.split(',')[1]; // Extract Base64 part
                        
                        // Add validation before assigning
                        if (!base64Data || base64Data.length < 100) { // arbitrary length check
                            console.error('  Extracted Base64 data appears too short or invalid.');
                            return; // Don't proceed with invalid data
                        }

                        currentImageBase64 = base64Data;
                        console.log('  currentImageBase64 set (first 50 chars):', currentImageBase64.substring(0, 50) + '...');
                        
                        if (imagePreview) {
                            imagePreview.src = e.target.result; // Display full data URL
                            imagePreview.style.display = 'block';
                            console.log('  Image preview updated.');
                        }
                        if (clearImageButton) {
                            clearImageButton.style.display = 'inline-block';
                            console.log('  Clear image button displayed.');
                        }
                        if (imagePasteArea) {
                            imagePasteArea.textContent = 'Image loaded. Add your prompt and send.';
                            imagePasteArea.classList.add('has-image');
                            imagePasteArea.style.cursor = 'default';
                            console.log('  Image paste area updated for loaded image.');
                        }
                    };

                    reader.onerror = function(e) {
                        console.error('FileReader onerror: Error reading file:', e);
                    };

                    reader.readAsDataURL(file);
                    break; // Only process the first image found
                } else {
                    console.warn(`  Item ${i}: Is an image type, but getAsFile() returned null.`);
                }
            }
        }
        if (!imageFound) {
            console.log('processImageItems: No image items found in clipboard/dragged data.');
        }
    }
}