// backend/static/js/edit_usecase_with_ai_ui.js
document.addEventListener('DOMContentLoaded', function () {
    // Passed from template:
    // const currentUsecaseData (contains all current fields of the use case being edited)
    // const aiSuggestibleFields (array of field names AI can suggest for)

    // --- DOM Elements ---
    const llmModelSelectAi = document.getElementById('llmModelSelectAi');
    const aiImageUpload = document.getElementById('aiImageUpload');
    const aiImagePreview = document.getElementById('aiImagePreview');
    const fetchAiSuggestionsBtn = document.getElementById('fetchAiSuggestionsBtn');
    const aiErrorLog = document.getElementById('aiErrorLog');
    const loadingSpinner = fetchAiSuggestionsBtn.querySelector('.loading-spinner');

    const aiSuggestionsContainer = document.getElementById('aiSuggestionsContainer');
    const currentValuesDisplay = document.getElementById('currentValuesDisplay');
    const aiSuggestionsDisplay = document.getElementById('aiSuggestionsDisplay'); // For editable AI suggestions
    const applyAiSuggestionsBtn = document.getElementById('applyAiSuggestionsBtn');
    
    const mainUsecaseEditForm = document.getElementById('mainUsecaseEditForm');

    let currentImageBase64 = null;
    let currentImageMimeType = null;

    // --- Populate LLM Model Dropdown ---
    async function populateLlmModels() {
        try {
            const response = await fetch('/llm/get_llm_models');
            const data = await response.json();
            if (data.success && data.models) {
                llmModelSelectAi.innerHTML = ''; // Clear "Loading..."
                if (data.models.length > 0) {
                    data.models.forEach(model => {
                        // Consider filtering for vision-capable models if identifiable
                        // For now, adding all. User needs to pick a vision one.
                        const option = document.createElement('option');
                        option.value = model;
                        option.textContent = model;
                        llmModelSelectAi.appendChild(option);
                    });
                    // Try to pre-select a common vision model if available
                    const preferredVisionModels = ["openai-gpt-4o", "openai-gpt-4-turbo", "anthropic-claude-3-opus-20240229", "google-gemini-1.5-pro-latest"];
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

    // --- Image Handling ---
    aiImageUpload.addEventListener('change', function(event) {
        const file = event.target.files[0];
        if (file) {
            aiErrorLog.textContent = ''; // Clear previous errors
            const reader = new FileReader();
            reader.onload = function(e) {
                aiImagePreview.src = e.target.result;
                aiImagePreview.style.display = 'block';
                
                // Store base64 and mimeType
                // Simple split, for more robust handling, consider libraries or more checks
                const parts = e.target.result.split(',');
                if (parts.length === 2) {
                    const mimeTypePart = parts[0].split(':')[1].split(';')[0];
                    currentImageBase64 = parts[1];
                    currentImageMimeType = mimeTypePart;
                } else {
                    currentImageBase64 = null;
                    currentImageMimeType = null;
                    aiErrorLog.textContent = 'Error processing image data.';
                }
            }
            reader.onerror = function() {
                currentImageBase64 = null;
                currentImageMimeType = null;
                aiErrorLog.textContent = 'Error reading image file.';
                aiImagePreview.style.display = 'none';
            }
            reader.readAsDataURL(file);
        } else {
            aiImagePreview.style.display = 'none';
            currentImageBase64 = null;
            currentImageMimeType = null;
        }
    });

    // --- Fetch AI Suggestions ---
    fetchAiSuggestionsBtn.addEventListener('click', async function() {
        if (!currentImageBase64 || !currentImageMimeType) {
            aiErrorLog.textContent = 'Please upload an image first.';
            return;
        }
        if (!llmModelSelectAi.value) {
            aiErrorLog.textContent = 'Please select an LLM model.';
            return;
        }
        aiErrorLog.textContent = '';
        loadingSpinner.style.display = 'inline-block';
        fetchAiSuggestionsBtn.disabled = true;
        aiSuggestionsContainer.style.display = 'none'; // Hide previous suggestions

        try {
            const payload = {
                usecase_id: currentUsecaseData.id,
                image_base64: currentImageBase64,
                image_mime_type: currentImageMimeType,
                model: llmModelSelectAi.value
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
        currentValuesDisplay.innerHTML = '';
        aiSuggestionsDisplay.innerHTML = '';

        aiSuggestibleFields.forEach(fieldKey => {
            const currentVal = currentUsecaseData[fieldKey] || '';
            const suggestedVal = suggestions[fieldKey] !== undefined ? suggestions[fieldKey] : currentVal; // Default to current if no suggestion

            // Current Value (Left Column)
            const currentDiv = document.createElement('div');
            currentDiv.classList.add('mb-3');
            currentDiv.innerHTML = `
                <label class="form-label fw-bold">${fieldKey.replace(/_/g, ' ').replace(/\b\w/g, l => l.toUpperCase())}:</label>
                <div class="current-value-display-ai">${currentVal || '<em>N/A</em>'}</div>
            `;
            currentValuesDisplay.appendChild(currentDiv);

            // AI Suggestion (Right Column - Editable)
            const suggestionDiv = document.createElement('div');
            suggestionDiv.classList.add('mb-3');
            const inputId = `ai_suggestion_${fieldKey}`;
            
            let inputElement;
            // For longer text fields, use textarea. For shorter ones, use input type text.
            // This is a simple heuristic, you might want a more sophisticated way or a config.
            const longTextFields = ['summary', 'inspiration', 'business_problem_solved', 'target_solution_description', 'technologies_text', 'further_ideas', 'raw_content', 'requirements', 'ideation_notes', 'effort_quantification', 'potential_quantification', 'dependencies_text', 'contact_persons_text', 'related_projects_text'];

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
            const mainFormInput = mainUsecaseEditForm.elements[fieldKey];

            if (aiInput && mainFormInput) {
                mainFormInput.value = aiInput.value;
                // Optional: Add a visual cue that the field was updated by AI
                mainFormInput.classList.add('border-success'); 
                setTimeout(() => mainFormInput.classList.remove('border-success'), 2000);
            }
        });
        alert('AI suggestions applied to the main form below. Review and save.');
    });

    // --- Initializations ---
    populateLlmModels();

}); // End of DOMContentLoaded