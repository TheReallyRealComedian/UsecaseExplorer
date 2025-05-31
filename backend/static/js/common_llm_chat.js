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

    let currentImageBase64 = null;
    let currentImageMimeType = null;

    // --- Helper Functions ---

    function markdownToHtml(markdownText) {
        if (typeof marked !== 'undefined' && typeof marked.parse === 'function') {
            return marked.parse(markdownText);
        }
        console.warn("Marked.js not loaded or 'marked.parse' function not found. Markdown will not be rendered.");
        return markdownText;
    }

    function addMessageToChat(role, content, imageUrl = null) {
        const messageElement = document.createElement('div');
        messageElement.classList.add('chat-bubble', `chat-bubble-${role}`);

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

        const textContent = document.createElement('div');
        textContent.innerHTML = markdownToHtml(content);
        messageElement.appendChild(textContent);

        chatDisplay.appendChild(messageElement);
        chatDisplay.scrollTop = chatDisplay.scrollHeight;
    }

    function clearImageInput() {
        currentImageBase64 = null;
        currentImageMimeType = null;
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
            imagePasteArea.style.cursor = 'pointer';
        }
    }

    /**
     * Resizes and compresses an image file to a maximum size (MAX_SIZE) and returns its Base64 data.
     * Converts non-JPEG/PNG types to PNG for consistent output.
     * @param {File} file - The image file to process.
     * @returns {Promise<{ base64Data: string, mimeType: string }>} A promise that resolves with the Base64 data and MIME type, or rejects on error.
     */
    function resizeAndCompressImage(file) {
        return new Promise((resolve, reject) => {
            const reader = new FileReader();
            reader.onload = (e) => {
                const img = new Image();
                img.onload = () => {
                    const canvas = document.createElement('canvas');
                    const ctx = canvas.getContext('2d');

                    const MAX_SIZE = 1024; // Max width or height in pixels
                    let width = img.width;
                    let height = img.height;

                    if (width > height) {
                        if (width > MAX_SIZE) {
                            height *= MAX_SIZE / width;
                            width = MAX_SIZE;
                        }
                    } else {
                        if (height > MAX_SIZE) {
                            width *= MAX_SIZE / height;
                            height = MAX_SIZE;
                        }
                    }

                    canvas.width = width;
                    canvas.height = height;

                    ctx.drawImage(img, 0, 0, width, height);

                    let outputMimeType = file.type;
                    let quality = 0.9; // Default JPEG quality

                    if (outputMimeType !== 'image/png' && outputMimeType !== 'image/jpeg' && outputMimeType !== 'image/jpg') {
                        // For other types (e.g., GIF), convert to PNG to ensure compatibility and reasonable size.
                        outputMimeType = 'image/png';
                    }

                    try {
                        const resizedDataUrl = canvas.toDataURL(outputMimeType, quality);
                        const base64Data = resizedDataUrl.split(',')[1];
                        resolve({ base64Data, mimeType: outputMimeType });
                    } catch (canvasError) {
                        console.error('Canvas toDataURL error:', canvasError);
                        reject('Failed to convert image via canvas.');
                    }
                };
                img.onerror = (imgError) => {
                    console.error('Image loading error for resizing:', imgError);
                    reject('Failed to load image for processing.');
                };
                img.src = e.target.result;
            };
            reader.onerror = (readError) => {
                console.error('FileReader error:', readError);
                reject('Failed to read image file.');
            };
            reader.readAsDataURL(file);
        });
    }

    // --- Core Event Listeners ---

    if (chatDisplay) {
        if (chatDisplay.children.length === 1 && chatDisplay.children[0].classList.contains('chat-placeholder')) {
            chatDisplay.innerHTML = '';
        }
        chatDisplay.scrollTop = chatDisplay.scrollHeight;
    }

    async function fetchAndPopulateModels() {
        try {
            const response = await fetch('/llm/get_llm_models');
            const data = await response.json();
            if (data.success && data.models) {
                llmModelSelect.innerHTML = '';
                if (data.models.length > 0) {
                    data.models.forEach(model => {
                        const option = document.createElement('option');
                        option.value = model;
                        option.textContent = model;
                        llmModelSelect.appendChild(option);
                    });
                    llmModelSelect.value = data.models[0];
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

    async function fetchAndPopulateChatHistory() {
        try {
            const response = await fetch('/llm/get_chat_history');
            const data = await response.json();
            if (data.success && data.history) {
                chatDisplay.innerHTML = '';
                if (data.history.length > 0) {
                    data.history.forEach(msg => {
                        addMessageToChat(msg.role, msg.content);
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

    fetchAndPopulateModels();
    if (chatDisplay.children.length === 0 || (chatDisplay.children.length === 1 && chatDisplay.children[0].classList.contains('chat-placeholder'))) {
        fetchAndPopulateChatHistory();
    }

    if (sendMessageButton && chatInput && llmModelSelect) {
        sendMessageButton.addEventListener('click', async () => {
            const message = chatInput.value.trim();
            const selectedModel = llmModelSelect.value;
            const systemPromptContent = systemPromptInput ? systemPromptInput.value.trim() : '';

            if (!message && !currentImageBase64) {
                alert('Please enter a message or paste an image.');
                return;
            }
            if (!selectedModel) {
                alert('Please select an LLM model.');
                return;
            }

            const displayImageUrl = currentImageBase64 && currentImageMimeType
                ? `data:${currentImageMimeType};base64,${currentImageBase64}`
                : null;
            addMessageToChat('user', message, displayImageUrl);

            const payload = {
                message: message,
                model: selectedModel,
                image_base64: currentImageBase64,
                image_mime_type: currentImageMimeType
            };

            // Construct the content array for multimodal input
            payload.content = [];
            if (message) payload.content.push({ type: "text", text: message });
            if (currentImageBase64 && currentImageMimeType) {
                payload.content.push({
                    type: "image_url",
                    image_url: { url: `data:${currentImageMimeType};base64,${currentImageBase64}` }
                });
            }

            console.log("Frontend sending payload to Flask:", payload);

            chatInput.value = '';
            clearImageInput();

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
                    loadingBubble.classList.add('chat-bubble-error'); // Add the new error class
                    console.error('LLM Chat Error:', data.message);
                }
            } catch (error) {
                console.error('Network or server error:', error);
                loadingBubble.innerHTML = `<i class="fas fa-exclamation-triangle me-2"></i>Network Error: Could not reach LLM service.`;
                loadingBubble.classList.add('chat-bubble-error'); // Add the new error class
            } finally {
                sendMessageButton.disabled = false;
                chatInput.disabled = false;
                llmModelSelect.disabled = false;
                if (systemPromptInput) systemPromptInput.disabled = false;
                if (saveSystemPromptButton) saveSystemPromptButton.disabled = false;
                if (clearImageButton) clearImageButton.disabled = false;
                chatInput.focus();
            }
        });

        chatInput.addEventListener('keypress', (e) => {
            if (e.key === 'Enter' && !e.shiftKey) {
                e.preventDefault();
                sendMessageButton.click();
            }
        });
    }

    if (clearChatButton && chatDisplay) {
        clearChatButton.addEventListener('click', async () => {
            if (confirm('Are you sure you want to clear the entire chat history? This cannot be undone.')) {
                try {
                    const response = await fetch('/llm/chat/clear', { method: 'POST' });
                    const data = await response.json();
                    if (data.success) {
                        chatDisplay.innerHTML = '<div class="chat-placeholder"><i class="fas fa-comments"></i><p>Start a conversation with the LLM!</p></div>';
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

    if (saveSystemPromptButton && systemPromptInput) {
        const saveSystemPromptMessage = document.createElement('span');
        saveSystemPromptMessage.classList.add('ms-3', 'small', 'text-muted');
        saveSystemPromptButton.parentNode.insertBefore(saveSystemPromptMessage, saveSystemPromptButton.nextSibling);

        saveSystemPromptButton.addEventListener('click', async () => {
            const prompt = systemPromptInput.value.trim();
            saveSystemPromptButton.disabled = true;
            systemPromptInput.disabled = true;
            saveSystemPromptMessage.textContent = 'Saving...';
            saveSystemPromptMessage.style.color = 'var(--text-secondary)';

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

        imagePasteArea.addEventListener('dragenter', (event) => {
            console.log('Drag entered imagePasteArea');
        });
        imagePasteArea.addEventListener('dragleave', (event) => {
            console.log('Drag left imagePasteArea');
        });
    }

    function handleImagePaste(event) {
        event.preventDefault();
        console.log('handleImagePaste triggered');
        const items = (event.clipboardData || event.originalEvent.clipboardData).items;
        processImageItems(items);
    }

    function handleDragOver(event) {
        event.preventDefault();
        event.stopPropagation();
        if (imagePasteArea) {
            imagePasteArea.classList.add('drag-over');
        }
    }

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

    async function processImageItems(items) {
        console.log('processImageItems: Starting to process items.', items);
        if (!items || items.length === 0) {
            console.log('processImageItems: No items found.');
            return;
        }

        let imageFile = null;
        for (let i = 0; i < items.length; i++) {
            if (items[i].type.indexOf('image') !== -1) {
                imageFile = items[i].getAsFile();
                if (imageFile) {
                    break;
                }
            }
        }

        if (imageFile) {
            console.log(`Image file found! Name: ${imageFile.name}, Type: ${imageFile.type}, Size: ${imageFile.size} bytes`);
            
            if (imagePasteArea) {
                imagePasteArea.textContent = 'Processing image... please wait.';
                imagePasteArea.classList.add('has-image');
                imagePasteArea.style.cursor = 'wait';
            }

            try {
                const { base64Data, mimeType } = await resizeAndCompressImage(imageFile);

                currentImageBase64 = base64Data;
                currentImageMimeType = mimeType;
                
                console.log('Image processed. New MIME Type:', currentImageMimeType, 'New Base64 Length:', currentImageBase64.length);

                if (imagePreview) {
                    imagePreview.src = `data:${currentImageMimeType};base64,${currentImageBase64}`;
                    imagePreview.style.display = 'block';
                }
                if (clearImageButton) {
                    clearImageButton.style.display = 'inline-block';
                }
                if (imagePasteArea) {
                    imagePasteArea.textContent = 'Image loaded. Add your prompt and send.';
                    imagePasteArea.style.cursor = 'default';
                }
            } catch (error) {
                console.error('Error processing image:', error);
                alert('Failed to process image: ' + error);
                clearImageInput();
                if (imagePasteArea) {
                    imagePasteArea.textContent = 'Paste (Ctrl+V) or drag & drop a screenshot here.';
                    imagePasteArea.classList.remove('has-image');
                    imagePasteArea.style.cursor = 'pointer';
                }
            }
        } else {
            console.log('processImageItems: No image items found in clipboard/dragged data.');
        }
    }
}