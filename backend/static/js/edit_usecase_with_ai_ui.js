// backend/static/js/edit_usecase_with_ai_ui.js
document.addEventListener('DOMContentLoaded', function () {
    // Retrieve data directly from window variables
    const currentUsecaseData = window.GLOBAL_USECASE_DATA_FOR_AI || null;
    const default_ai_system_prompt_content = window.GLOBAL_DEFAULT_AI_SYSTEM_PROMPT || '';
    const aiSuggestibleFields = window.GLOBAL_AI_SUGGESTIBLE_FIELDS || [];

    if (!currentUsecaseData) {
        console.error("CRITICAL: currentUsecaseData could not be loaded from global variable.");
        // Potentially disable functionality or show an error to the user
    }

    // --- DOM Elements ---
    const llmModelSelectAi = document.getElementById('llmModelSelectAi');
    const aiImagePreview = document.getElementById('aiImagePreview');
    const fetchAiSuggestionsBtn = document.getElementById('fetchAiSuggestionsBtn');
    const aiErrorLog = document.getElementById('aiErrorLog');
    const loadingSpinner = fetchAiSuggestionsBtn.querySelector('.loading-spinner');

    const aiSuggestionsContainer = document.getElementById('aiSuggestionsContainer');
    const currentValuesDisplay = document.getElementById('currentValuesDisplay');
    const aiSuggestionsDisplay = document.getElementById('aiSuggestionsDisplay');
    const applyAiSuggestionsBtn = document.getElementById('applyAiSuggestionsBtn');

    const mainUsecaseEditForm = document.getElementById('mainUsecaseEditForm');

    const aiSystemPromptInput = document.getElementById('aiSystemPromptInput');
    const toggleAiSystemPromptEditorBtn = document.getElementById('toggleAiSystemPromptEditorBtn');
    const systemPromptCollapse = document.getElementById('aiSystemPromptEditorCollapse');

    const clearAiImageBtn = document.getElementById('clearAiImageBtn');

    // NEW & UPDATED IMAGE INPUT DOM ELEMENTS
    const aiImageUpload = document.getElementById('aiImageUpload'); // Hidden file input
    const aiImageDropZone = document.getElementById('aiImageDropZone'); // Clickable div for upload/drag
    const aiImageDropZoneText = document.getElementById('aiImageDropZoneText');

    const enableScreenshotPasteCheckbox = document.getElementById('enableScreenshotPaste');
    const screenshotPasteArea = document.getElementById('screenshotPasteArea');
    const screenshotPasteAreaText = document.getElementById('screenshotPasteAreaText');
    // END NEW & UPDATED

    let currentImageBase64 = null;
    let currentImageMimeType = null;

    // --- Populate System Prompt Textarea ---
    if (aiSystemPromptInput && default_ai_system_prompt_content) {
        aiSystemPromptInput.value = default_ai_system_prompt_content.trim();
    }

    // --- Toggle icon for system prompt collapse ---
    if (systemPromptCollapse && toggleAiSystemPromptEditorBtn) {
        const icon = toggleAiSystemPromptEditorBtn.querySelector('i');
        systemPromptCollapse.addEventListener('show.bs.collapse', function () {
            if (icon) {
                icon.classList.remove('fa-cog');
                icon.classList.add('fa-chevron-up');
            }
            toggleAiSystemPromptEditorBtn.innerHTML = `<i class="fas fa-chevron-up"></i> Hide System Prompt`;
        });
        systemPromptCollapse.addEventListener('hide.bs.collapse', function () {
            if (icon) {
                icon.classList.remove('fa-chevron-up');
                icon.classList.add('fa-cog');
            }
            toggleAiSystemPromptEditorBtn.innerHTML = `<i class="fas fa-cog"></i> Edit System Prompt`;
        });
    }

    // --- Populate LLM Model Dropdown ---
    async function populateLlmModels() {
        try {
            const response = await fetch('/llm/get_llm_models');
            const data = await response.json();
            if (data.success && data.models) {
                llmModelSelectAi.innerHTML = ''; // Clear "Loading..."
                if (data.models.length > 0) {
                    data.models.forEach(model => {
                        const option = document.createElement('option');
                        option.value = model;
                        option.textContent = model;
                        llmModelSelectAi.appendChild(option);
                    });

                    const defaultApolloModel = data.models.find(m => m.toLowerCase().includes("apollo") && m.toLowerCase().includes("claude_3_5_sonnet"));
                    const preferredVisionModels = [
                        defaultApolloModel,
                        "openai-gpt-4o",
                        "openai-gpt-4-turbo",
                        "anthropic-claude-3-opus-20240229",
                        "anthropic-claude-3-sonnet-20240229",
                        "google-gemini-1.5-pro-latest"
                    ].filter(Boolean);

                    let selected = false;
                    for (const pModel of preferredVisionModels) {
                        if (data.models.includes(pModel)) {
                            llmModelSelectAi.value = pModel;
                            selected = true;
                            break;
                        }
                    }
                    if (!selected && data.models.length > 0) {
                         llmModelSelectAi.value = data.models[0];
                    }

                } else {
                    llmModelSelectAi.innerHTML = '<option value="">No models found</option>';
                    llmModelSelectAi.disabled = true;
                    fetchAiSuggestionsBtn.disabled = true;
                }
            } else {
                llmModelSelectAi.innerHTML = '<option value="">Error loading models</option>';
                llmModelSelectAi.disabled = true;
                fetchAiSuggestionsBtn.disabled = true;
            }
        } catch (error) {
            llmModelSelectAi.innerHTML = '<option value="">Network error loading models</option>';
            llmModelSelectAi.disabled = true;
            fetchAiSuggestionsBtn.disabled = true;
            console.error("Error fetching LLM models:", error);
        }
    }

    // --- Image Handling Unified Functions ---
    function resetImageState() {
        aiImagePreview.src = '#';
        aiImagePreview.style.display = 'none';
        clearAiImageBtn.style.display = 'none';
        currentImageBase64 = null;
        currentImageMimeType = null;
        
        // Reset text for upload/drag area
        if (aiImageDropZoneText) {
            aiImageDropZoneText.textContent = 'Click to upload, or drag & drop an image here.';
        }
        aiImageUpload.value = ''; // Clear file input selection

        // Reset text for paste area if it's active
        if (enableScreenshotPasteCheckbox.checked && screenshotPasteAreaText) {
             screenshotPasteAreaText.textContent = 'Press Ctrl+V or Cmd+V anywhere on this page to paste a screenshot.';
        }
        
        // Ensure styling is reset
        aiImageDropZone.classList.remove('drag-over');
        screenshotPasteArea.classList.remove('drag-over'); // Just in case
    }

    if (clearAiImageBtn) {
        clearAiImageBtn.addEventListener('click', resetImageState);
    }

    // Main function to process any image file (from upload, drag, or paste)
    function processImageFile(file) {
        if (file && file.type.startsWith('image/')) {
            aiErrorLog.textContent = '';
            const reader = new FileReader();
            reader.onload = function(e) {
                aiImagePreview.src = e.target.result;
                aiImagePreview.style.display = 'block';
                clearAiImageBtn.style.display = 'inline-block';

                const parts = e.target.result.split(',');
                if (parts.length === 2) {
                    const mimeTypePart = parts[0].split(':')[1].split(';')[0];
                    currentImageBase64 = parts[1];
                    currentImageMimeType = mimeTypePart;

                    // Update relevant text area after successful image load
                    if (aiImageDropZoneText) {
                        aiImageDropZoneText.textContent = `Selected: ${file.name}`;
                    }
                    if (enableScreenshotPasteCheckbox.checked && screenshotPasteAreaText) {
                        screenshotPasteAreaText.textContent = `Screenshot loaded from clipboard.`;
                    }

                } else {
                    resetImageState();
                    aiErrorLog.textContent = 'Error processing image data.';
                }
            }
            reader.onerror = function() {
                resetImageState();
                aiErrorLog.textContent = 'Error reading image file.';
            }
            reader.readAsDataURL(file);
        } else {
            resetImageState();
            aiErrorLog.textContent = 'Invalid file type. Please select an image.';
        }
    }

    // --- Event Listeners for Upload / Drag & Drop Area (`aiImageDropZone`) ---
    if (aiImageDropZone && aiImageUpload) {
        aiImageDropZone.addEventListener('click', () => {
            aiImageUpload.click(); // Triggers the hidden file input
        });

        aiImageUpload.addEventListener('change', function(event) {
            if (event.target.files && event.target.files[0]) {
                processImageFile(event.target.files[0]);
            }
        });

        // Drag & Drop Handlers for aiImageDropZone
        aiImageDropZone.addEventListener('dragover', function(event) {
            event.preventDefault();
            event.stopPropagation();
            aiImageDropZone.classList.add('drag-over');
        });

        aiImageDropZone.addEventListener('dragleave', function(event) {
            event.preventDefault();
            event.stopPropagation();
            aiImageDropZone.classList.remove('drag-over');
        });

        aiImageDropZone.addEventListener('drop', function(event) {
            event.preventDefault();
            event.stopPropagation();
            aiImageDropZone.classList.remove('drag-over');
            if (event.dataTransfer.files && event.dataTransfer.files[0]) {
                processImageFile(event.dataTransfer.files[0]);
            }
        });
    }

    // --- Event Listeners for Screenshot Pasting (`enableScreenshotPasteCheckbox` & `screenshotPasteArea`) ---
    let globalPasteListener = null; // To store reference to the dynamically added listener

    function handleGlobalImagePaste(event) {
        // Only process if the checkbox is checked AND no image is currently loaded
        if (!enableScreenshotPasteCheckbox.checked || currentImageBase64) {
            return; 
        }

        const items = (event.clipboardData || event.originalEvent.clipboardData).items;
        let imageFound = false;
        for (let i = 0; i < items.length; i++) {
            if (items[i].type.indexOf('image') !== -1) {
                const blob = items[i].getAsFile();
                if (blob) {
                    event.preventDefault(); // Prevent default paste behavior (e.g., into a text input)
                    processImageFile(blob);
                    imageFound = true;
                    break;
                }
            }
        }
        if (imageFound) {
            // Optional: Provide a brief visual cue on the paste area
            screenshotPasteArea.classList.add('image-loaded-success');
            setTimeout(() => {
                screenshotPasteArea.classList.remove('image-loaded-success');
            }, 500);
        }
    }

    if (enableScreenshotPasteCheckbox && screenshotPasteArea && screenshotPasteAreaText) {
        enableScreenshotPasteCheckbox.addEventListener('change', function() {
            if (this.checked) {
                screenshotPasteArea.style.display = 'block';
                screenshotPasteArea.classList.add('active-paste');
                screenshotPasteAreaText.textContent = 'Press Ctrl+V or Cmd+V anywhere on this page to paste a screenshot.';
                
                // Attach the global paste listener
                if (!globalPasteListener) { // Ensure it's only attached once
                    globalPasteListener = handleGlobalImagePaste;
                    // Listen on the document body to capture pastes anywhere
                    document.body.addEventListener('paste', globalPasteListener);
                }
            } else {
                screenshotPasteArea.style.display = 'none';
                screenshotPasteArea.classList.remove('active-paste');
                
                // Detach the global paste listener
                if (globalPasteListener) {
                    document.body.removeEventListener('paste', globalPasteListener);
                    globalPasteListener = null;
                }
                // Clear any image if the checkbox is unchecked
                resetImageState(); 
            }
        });
        
        // Initial state: hide paste area if checkbox is not checked on load
        if (!enableScreenshotPasteCheckbox.checked) {
            screenshotPasteArea.style.display = 'none';
        }

        // Add visual feedback for focus on the paste area itself
        screenshotPasteArea.addEventListener('focus', () => {
            screenshotPasteArea.classList.add('focused');
        });
        screenshotPasteArea.addEventListener('blur', () => {
            screenshotPasteArea.classList.remove('focused');
        });
    }

    // --- Fetch AI Suggestions ---
    fetchAiSuggestionsBtn.addEventListener('click', async function() {
        if (!currentUsecaseData) {
            aiErrorLog.textContent = 'Error: Use case data not loaded.';
            return;
        }
        if (!currentImageBase64 || !currentImageMimeType) {
            aiErrorLog.textContent = 'Please provide an image (upload/drag or paste) first.';
            return;
        }
        if (!llmModelSelectAi.value) {
            aiErrorLog.textContent = 'Please select an LLM model.';
            return;
        }
        aiErrorLog.textContent = '';
        loadingSpinner.style.display = 'inline-block';
        fetchAiSuggestionsBtn.disabled = true;
        aiSuggestionsContainer.style.display = 'none';

        const systemPromptOverride = aiSystemPromptInput ? aiSystemPromptInput.value.trim() : null;

        try {
            const payload = {
                usecase_id: currentUsecaseData.id,
                image_base64: currentImageBase64,
                image_mime_type: currentImageMimeType,
                model: llmModelSelectAi.value,
                system_prompt_override: systemPromptOverride
            };

            const response = await fetch('/llm/analyze-usecase-image', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify(payload)
            });

            const result = await response.json();

            if (result.success && result.suggestions) {
                displayAiSuggestions(result.suggestions);
                aiSuggestionsContainer.style.display = 'block';
            } else {
                aiErrorLog.textContent = `Error from AI: ${result.message || 'Unknown error'}`;
                if (result.raw_response) {
                    console.warn("AI Raw Response on error:", result.raw_response);
                }
            }
        } catch (error) {
            console.error('Error fetching AI suggestions:', error);
            aiErrorLog.textContent = 'Network or server error. Could not fetch AI suggestions.';
        } finally {
            loadingSpinner.style.display = 'none';
            fetchAiSuggestionsBtn.disabled = false;
        }
    });

    // --- Display AI Suggestions and Current Values ---
    function displayAiSuggestions(suggestions) {
        if (!currentUsecaseData) return;

        currentValuesDisplay.innerHTML = '';
        aiSuggestionsDisplay.innerHTML = '';

        aiSuggestibleFields.forEach(fieldKey => {
            // Get current value from currentUsecaseData (which now includes new fields)
            const currentVal = currentUsecaseData.hasOwnProperty(fieldKey) ? (currentUsecaseData[fieldKey] || '') : 'Field not in data';
            const suggestedVal = suggestions[fieldKey] !== undefined ? suggestions[fieldKey] : currentVal;

            const currentDiv = document.createElement('div');
            currentDiv.classList.add('mb-3');
            currentDiv.innerHTML = `
                <label class="form-label fw-bold">${fieldKey.replace(/_/g, ' ').replace(/\b\w/g, l => l.toUpperCase())}:</label>
                <div class="current-value-display-ai">${currentVal || '<em>N/A</em>'}</div>
            `;
            currentValuesDisplay.appendChild(currentDiv);

            const suggestionDiv = document.createElement('div');
            suggestionDiv.classList.add('mb-3');
            const inputId = `ai_suggestion_${fieldKey}`;

            let inputElement;
            // List of fields that should be textarea for better editing
            const longTextFields = [
                'summary', 'business_problem_solved', 'target_solution_description',
                'effort_quantification', 'potential_quantification', 'dependencies_text',
                'pilot_site_factory_text' // New field added to textarea
            ];

            if (longTextFields.includes(fieldKey)) {
                inputElement = `<textarea class="form-control ai-suggestion-input" id="${inputId}" name="${inputId}" rows="3">${suggestedVal || ''}</textarea>`;
            } else {
                inputElement = `<input type="text" class="form-control ai-suggestion-input" id="${inputId}" name="${inputId}" value="${suggestedVal || ''}">`;
            }

            suggestionDiv.innerHTML = `
                <label for="${inputId}" class="form-label fw-bold">${fieldKey.replace(/_/g, ' ').replace(/\b\w/g, l => l.toUpperCase())}:</label>
                ${inputElement}
            `;
            aiSuggestionsDisplay.appendChild(suggestionDiv);
        });
    }

    // --- Apply AI Suggestions to Main Form ---
    applyAiSuggestionsBtn.addEventListener('click', function() {
        if (!mainUsecaseEditForm) {
            console.error("Main use case edit form not found!");
            return;
        }

        aiSuggestibleFields.forEach(fieldKey => {
            const aiInput = document.getElementById(`ai_suggestion_${fieldKey}`);
            const mainFormInput = mainUsecaseEditForm.elements[fieldKey]; // Access by name/id

            if (aiInput && mainFormInput) {
                mainFormInput.value = aiInput.value;
                mainFormInput.classList.add('border-success');
                setTimeout(() => mainFormInput.classList.remove('border-success'), 2000);
            }
        });
        alert('AI suggestions applied to the main form below. Review and save.');
    });

    // --- Initializations ---
    populateLlmModels();

});