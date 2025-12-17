// Popup logic for HTML Fragment Labeler
let currentHTML = '';
let currentURL = '';

// DOM elements
const selectFragmentBtn = document.getElementById('selectFragmentBtn');
const selectBodyBtn = document.getElementById('selectBodyBtn');
const htmlPreview = document.getElementById('htmlPreview');
const charCount = document.getElementById('charCount');
const fragmentTypeSelect = document.getElementById('fragmentType');
const jsonEditor = document.getElementById('jsonEditor');
const validationMessage = document.getElementById('validationMessage');
const saveBtn = document.getElementById('saveBtn');
const clearBtn = document.getElementById('clearBtn');

// Event listeners
selectFragmentBtn.addEventListener('click', handleSelectFragment);
selectBodyBtn.addEventListener('click', handleSelectBody);
fragmentTypeSelect.addEventListener('change', handleFragmentTypeChange);
jsonEditor.addEventListener('input', handleJsonEdit);
saveBtn.addEventListener('click', handleSave);
clearBtn.addEventListener('click', handleClear);

// Listen for messages from content script
chrome.runtime.onMessage.addListener((request, sender, sendResponse) => {
  if (request.action === 'htmlSelected') {
    currentHTML = request.html;
    currentURL = request.url;
    displayHTML(request.html);

    // If fragment type is selected, trigger auto-extraction
    if (fragmentTypeSelect.value) {
      loadTemplateWithExtraction();
    }
  }
});

/**
 * Handle "Select Fragment" button click
 */
async function handleSelectFragment() {
  try {
    // Get current tab
    const [tab] = await chrome.tabs.query({ active: true, currentWindow: true });

    // Inject content script if needed and start selection mode
    await chrome.scripting.executeScript({
      target: { tabId: tab.id },
      files: ['content.js']
    });

    // Send message to start selection
    chrome.tabs.sendMessage(tab.id, { action: 'startSelection' });

    // Close popup (will reopen when user makes selection)
    // window.close();
  } catch (error) {
    console.error('Error starting selection:', error);
    alert('Failed to start selection mode. Make sure you have permission to access this page.');
  }
}

/**
 * Handle "Select Full Body" button click
 */
async function handleSelectBody() {
  try {
    // Get current tab
    const [tab] = await chrome.tabs.query({ active: true, currentWindow: true });

    // Inject content script if needed
    await chrome.scripting.executeScript({
      target: { tabId: tab.id },
      files: ['content.js']
    });

    // Request body HTML
    chrome.tabs.sendMessage(tab.id, { action: 'selectBody' });
  } catch (error) {
    console.error('Error selecting body:', error);
    alert('Failed to select body HTML. Make sure you have permission to access this page.');
  }
}

/**
 * Display HTML in preview textarea
 */
function displayHTML(html) {
  // Store full HTML but display truncated version if too long
  htmlPreview.value = html;
  updateCharCount(html.length);

  // Enable save button if both HTML and JSON are valid
  updateSaveButtonState();
}

/**
 * Update character count display
 */
function updateCharCount(count) {
  charCount.textContent = `${count.toLocaleString()} characters`;
}

/**
 * Handle fragment type selection change
 */
function handleFragmentTypeChange() {
  const selectedType = fragmentTypeSelect.value;

  if (!selectedType) {
    jsonEditor.value = '';
    jsonEditor.placeholder = 'Select a fragment type to load the template...';
    updateSaveButtonState();
    return;
  }

  loadTemplateWithExtraction();
}

/**
 * Load template and apply auto-extraction if HTML is available
 */
function loadTemplateWithExtraction() {
  const selectedType = fragmentTypeSelect.value;

  if (!selectedType) return;

  try {
    // Get base template
    let template = getSchemaTemplate(selectedType);

    // If HTML is available, apply auto-extraction
    if (currentHTML) {
      const extracted = autoExtractFields(currentHTML, selectedType);
      template = populateTemplate(template, extracted);
    }

    // Display in JSON editor
    jsonEditor.value = JSON.stringify(template, null, 2);
    jsonEditor.placeholder = '';

    // Validate
    validateJSON();
    updateSaveButtonState();
  } catch (error) {
    console.error('Error loading template:', error);
    showValidationError('Failed to load template: ' + error.message);
  }
}

/**
 * Handle JSON editor input
 */
function handleJsonEdit() {
  validateJSON();
  updateSaveButtonState();
}

/**
 * Validate JSON in editor
 */
function validateJSON() {
  const jsonText = jsonEditor.value.trim();

  if (!jsonText) {
    clearValidationMessage();
    return false;
  }

  try {
    const parsed = JSON.parse(jsonText);

    // Check if it has "TODO" values
    const jsonString = JSON.stringify(parsed);
    if (jsonString.includes('"TODO"')) {
      showValidationWarning('⚠️ Some fields still contain "TODO" placeholders');
      return true; // Still valid JSON, just a warning
    }

    showValidationSuccess('✓ Valid JSON');
    return true;
  } catch (error) {
    showValidationError('✗ Invalid JSON: ' + error.message);
    return false;
  }
}

/**
 * Show validation error
 */
function showValidationError(message) {
  validationMessage.textContent = message;
  validationMessage.className = 'validation-message error';
  jsonEditor.classList.add('invalid');
}

/**
 * Show validation warning
 */
function showValidationWarning(message) {
  validationMessage.textContent = message;
  validationMessage.className = 'validation-message warning';
  jsonEditor.classList.remove('invalid');
}

/**
 * Show validation success
 */
function showValidationSuccess(message) {
  validationMessage.textContent = message;
  validationMessage.className = 'validation-message success';
  jsonEditor.classList.remove('invalid');
}

/**
 * Clear validation message
 */
function clearValidationMessage() {
  validationMessage.textContent = '';
  validationMessage.className = 'validation-message';
  jsonEditor.classList.remove('invalid');
}

/**
 * Update save button enabled/disabled state
 */
function updateSaveButtonState() {
  const hasHTML = currentHTML.trim() !== '';
  const hasValidJSON = validateJSON() && jsonEditor.value.trim() !== '';
  const hasFragmentType = fragmentTypeSelect.value !== '';

  saveBtn.disabled = !(hasHTML && hasValidJSON && hasFragmentType);
}

/**
 * Handle save button click
 */
function handleSave() {
  if (saveBtn.disabled) return;

  try {
    // Parse JSON
    const label = JSON.parse(jsonEditor.value);

    // Create annotation object
    const annotation = {
      html: currentHTML,
      label: label,
      url: currentURL,
      timestamp: new Date().toISOString()
    };

    // Generate filename
    const fragmentType = fragmentTypeSelect.value;
    const timestamp = new Date().toISOString().replace(/[:.]/g, '-').slice(0, -5);
    const filename = `annotation_${fragmentType}_${timestamp}.json`;

    // Convert to JSON blob
    const jsonBlob = new Blob([JSON.stringify(annotation, null, 2)], {
      type: 'application/json'
    });

    // Create download URL
    const url = URL.createObjectURL(jsonBlob);

    // Trigger download
    chrome.downloads.download({
      url: url,
      filename: filename,
      saveAs: true
    }, (downloadId) => {
      if (chrome.runtime.lastError) {
        console.error('Download error:', chrome.runtime.lastError);
        alert('Failed to save annotation: ' + chrome.runtime.lastError.message);
      } else {
        // Show success message
        showValidationSuccess('✓ Annotation saved successfully!');

        // Optional: Auto-clear after save
        // setTimeout(handleClear, 2000);
      }
    });

  } catch (error) {
    console.error('Error saving annotation:', error);
    alert('Failed to save annotation: ' + error.message);
  }
}

/**
 * Handle clear button click
 */
function handleClear() {
  if (confirm('Clear all fields and start over?')) {
    currentHTML = '';
    currentURL = '';
    htmlPreview.value = '';
    updateCharCount(0);
    fragmentTypeSelect.value = '';
    jsonEditor.value = '';
    jsonEditor.placeholder = 'Select a fragment type to load the template...';
    clearValidationMessage();
    updateSaveButtonState();
  }
}

// Initialize on load
document.addEventListener('DOMContentLoaded', () => {
  updateSaveButtonState();
});
