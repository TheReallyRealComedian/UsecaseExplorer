// backend/static/js/area_overview_inline_edit.js
document.addEventListener('DOMContentLoaded', function () {
    const tables = document.querySelectorAll('.sortable-table'); // Target tables in overview

    // Updated options to include intermediate values
    const benefitOptions = ["Low", "Low/Medium", "Medium", "Medium/High", "High", "N/A"];
    const effortOptions = ["Low", "Low/Medium", "Medium", "Medium/High", "High", "N/A"];
    const waveOptions = ["Wave 1", "Wave 2", "Wave 3", "Waiting list", "N/A"];

    // Helper function to get the priority-based benefit text
    function mapPriorityToBenefitText(priority) {
        if (priority === 1) return "High";
        if (priority === 2) return "Medium";
        if (priority === 3) return "Low";
        return "N/A"; // Default or for priority 4 (Waiting List)
    }


    tables.forEach(table => {
        table.addEventListener('click', function (event) {
            const cell = event.target.closest('.editable-cell');
            if (!cell || cell.classList.contains('is-editing')) {
                return;
            }
            startEdit(cell);
        });
    });

    function startEdit(cell) {
        cell.classList.add('is-editing');
        const originalHTML = cell.innerHTML;
        const originalText = cell.querySelector('a') ? cell.querySelector('a').textContent.trim() : cell.textContent.trim();
        const field = cell.dataset.field;
        const ucId = cell.closest('tr').dataset.ucId;

        cell.dataset.originalHTML = originalHTML;
        cell.innerHTML = '';

        let inputElement;

        if (field === 'name' || field === 'bi_id') {
            inputElement = document.createElement('input');
            inputElement.type = 'text';
            inputElement.value = originalText;
        } else if (field === 'quality_improvement_quant' || field === 'effort_level' || field === 'wave') {
            inputElement = document.createElement('select');
            let optionsArray = [];
            if (field === 'quality_improvement_quant') optionsArray = benefitOptions;
            else if (field === 'effort_level') optionsArray = effortOptions;
            else if (field === 'wave') optionsArray = waveOptions;

            optionsArray.forEach(opt => {
                const option = document.createElement('option');
                option.value = opt;
                option.textContent = opt;
                // Improved selection logic:
                // Handles direct match, N/A for empty, and priority fallback for benefit
                if (opt === originalText ||
                    (originalText === '' && opt === 'N/A') ||
                    (originalText === 'N/A' && opt === 'N/A') ||
                    (field === 'quality_improvement_quant' && originalText === mapPriorityToBenefitText(parseInt(cell.closest('tr').querySelector('td[data-field="quality_improvement_quant"]').dataset.sortValue)) && opt === originalText) ||
                    (field === 'quality_improvement_quant' && !benefitOptions.includes(originalText) && originalText === mapPriorityToBenefitText(parseInt(cell.closest('tr').querySelector('td[data-field="quality_improvement_quant"]').dataset.sortValue)) && opt === 'N/A') // handles if current display is from priority and is N/A
                   ) {
                    option.selected = true;
                }
                inputElement.appendChild(option);
            });
        } else {
            cell.innerHTML = originalHTML;
            cell.classList.remove('is-editing');
            return;
        }

        inputElement.classList.add('form-control', 'form-control-sm');
        cell.appendChild(inputElement);
        inputElement.focus();

        function handleSaveOrCancel(saveChange) {
            const newValue = inputElement.value.trim();
            cell.classList.remove('is-editing');

            if (saveChange && newValue !== originalText && !(field === 'bi_id' && !newValue)) {
                 if (field === 'name' && !newValue) {
                    alert("Use Case Name cannot be empty.");
                    cell.innerHTML = originalHTML;
                    return;
                }
                 if (field === 'bi_id' && !newValue) {
                    alert("UC BI_ID cannot be empty.");
                    cell.innerHTML = originalHTML;
                    return;
                }

                cell.innerHTML = '<i class="fas fa-spinner fa-spin"></i> Saving...';

                fetch(`/usecases/api/usecases/${ucId}/inline-update`, {
                    method: 'PUT',
                    headers: {
                        'Content-Type': 'application/json',
                    },
                    body: JSON.stringify({ [field]: newValue === "N/A" ? null : newValue })
                })
                .then(response => response.json())
                .then(data => {
                    if (data.success) {
                        let displayValue = data.new_value;
                        if (displayValue === null || displayValue === "N/A") {
                             if (field === 'quality_improvement_quant') {
                                displayValue = mapPriorityToBenefitText(data.usecase.priority);
                             } else {
                                displayValue = "N/A";
                             }
                        }

                        if (field === 'name') {
                            const anchor = document.createElement('a');
                            anchor.href = `/usecases/${ucId}`;
                            anchor.textContent = displayValue;
                            cell.innerHTML = '';
                            cell.appendChild(anchor);
                        } else {
                            cell.textContent = displayValue;
                        }
                        if (field === 'bi_id') { // This ensures BI_ID text is updated if it's not the name field.
                            cell.textContent = displayValue;
                        }
                    } else {
                        alert(`Error: ${data.message}`);
                        cell.innerHTML = originalHTML;
                    }
                })
                .catch(error => {
                    console.error('Error saving use case:', error);
                    alert('An error occurred while saving.');
                    cell.innerHTML = originalHTML;
                });
            } else {
                cell.innerHTML = originalHTML;
            }
            // Listeners are implicitly removed when cell.innerHTML is changed.
            // If inputElement was not removed, explicit removal would be needed:
            // inputElement.removeEventListener('blur', onBlur);
            // inputElement.removeEventListener('keydown', onKeyDown);
        }

        const onBlur = () => {
            setTimeout(() => {
                if (cell.contains(inputElement)) {
                    handleSaveOrCancel(true);
                }
            }, 100);
        };

        const onKeyDown = (e) => {
            if (e.key === 'Enter') {
                e.preventDefault();
                handleSaveOrCancel(true);
            } else if (e.key === 'Escape') {
                e.preventDefault();
                handleSaveOrCancel(false);
            }
        };

        inputElement.addEventListener('blur', onBlur);
        inputElement.addEventListener('keydown', onKeyDown);
    }
});