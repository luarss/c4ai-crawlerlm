// Popup logic for HTML Fragment Labeler
let currentHTML = '';
let currentURL = '';

// URL list management
let urlList = [];
let currentUrlIndex = 0;

// Annotation counts
let annotationCounts = {};
const TARGET_COUNT = 10; // Target number of annotations per category

// DOM elements
const loadUrlsBtn = document.getElementById('loadUrlsBtn');
const openNextUrlBtn = document.getElementById('openNextUrlBtn');
const urlStatus = document.getElementById('urlStatus');
const selectFragmentBtn = document.getElementById('selectFragmentBtn');
const selectBodyBtn = document.getElementById('selectBodyBtn');
const htmlPreview = document.getElementById('htmlPreview');
const charCount = document.getElementById('charCount');
const fragmentCount = document.getElementById('fragmentCount');
const fragmentTypeSelect = document.getElementById('fragmentType');
const jsonEditor = document.getElementById('jsonEditor');
const validationMessage = document.getElementById('validationMessage');
const fixJsonBtn = document.getElementById('fixJsonBtn');
const saveBtn = document.getElementById('saveBtn');
const clearBtn = document.getElementById('clearBtn');

// Event listeners
loadUrlsBtn.addEventListener('click', handleLoadUrls);
openNextUrlBtn.addEventListener('click', handleOpenNextUrl);
selectFragmentBtn.addEventListener('click', handleSelectFragment);
selectBodyBtn.addEventListener('click', handleSelectBody);
fragmentTypeSelect.addEventListener('change', handleFragmentTypeChange);
jsonEditor.addEventListener('input', handleJsonEdit);
fixJsonBtn.addEventListener('click', handleFixJson);
saveBtn.addEventListener('click', handleSave);
clearBtn.addEventListener('click', handleClear);

/**
 * Handle "Load URLs" button click
 */
async function handleLoadUrls() {
  try {
    // Show loading state
    urlStatus.textContent = '📋 Loading URLs from server...';
    urlStatus.className = 'url-status loading';
    loadUrlsBtn.disabled = true;

    // Fetch URLs from server
    const response = await fetch('http://localhost:8000/urls');
    const result = await response.json();

    if (response.ok && result.success) {
      urlList = result.urls;
      currentUrlIndex = 0;

      // Show success message
      urlStatus.textContent = `✓ Loaded ${result.count} URLs (0/${result.count} opened)`;
      urlStatus.className = 'url-status active';

      // Enable "Open Next URL" button
      openNextUrlBtn.disabled = false;

      // Save state
      await saveState();
    } else {
      throw new Error(result.error || 'Failed to load URLs');
    }
  } catch (error) {
    console.error('Error loading URLs:', error);

    // Check if server is running
    if (error.message.includes('fetch') || error.message.includes('NetworkError')) {
      urlStatus.textContent = '✗ Server not running! Start: python annotation_server.py';
    } else {
      urlStatus.textContent = '✗ Failed to load URLs: ' + error.message;
    }
    urlStatus.className = 'url-status loading';
  } finally {
    loadUrlsBtn.disabled = false;
  }
}

/**
 * Handle "Open Next URL" button click
 */
async function handleOpenNextUrl() {
  if (currentUrlIndex >= urlList.length) {
    urlStatus.textContent = '✓ All URLs opened! You\'ve completed the list.';
    urlStatus.className = 'url-status active';
    openNextUrlBtn.disabled = true;
    return;
  }

  const nextUrl = urlList[currentUrlIndex];
  currentUrlIndex++;

  // Update status
  urlStatus.textContent = `📍 Opened URL ${currentUrlIndex}/${urlList.length}: ${nextUrl.substring(0, 60)}...`;
  urlStatus.className = 'url-status active';

  // Update button text if this is the last URL
  if (currentUrlIndex >= urlList.length) {
    openNextUrlBtn.textContent = '✓ All URLs Opened';
    openNextUrlBtn.disabled = true;
  }

  // Save state BEFORE opening the tab (because opening with active:true will close the popup)
  await saveState();

  // Open URL in a new tab (this will close the popup)
  await chrome.tabs.create({ url: nextUrl, active: true });
}

/**
 * Fetch annotation counts from server
 */
async function fetchCounts() {
  try {
    const response = await fetch('http://localhost:8000/counts');
    const result = await response.json();

    if (response.ok && result.success) {
      annotationCounts = result.counts;
      updateDropdownWithCounts();
    } else {
      console.warn('Failed to fetch counts:', result.error);
    }
  } catch (error) {
    console.warn('Could not fetch counts (server may not be running):', error);
  }
}

/**
 * Update dropdown options with counts
 */
function updateDropdownWithCounts() {
  const options = fragmentTypeSelect.querySelectorAll('option');

  options.forEach(option => {
    const fragmentType = option.value;

    // Skip the placeholder option
    if (!fragmentType) return;

    // Get count for this type (default to 0 if not found)
    const count = annotationCounts[fragmentType] || 0;

    // Get the original label (without count)
    let baseLabel = option.getAttribute('data-base-label');
    if (!baseLabel) {
      // Store original label on first run
      baseLabel = option.textContent;
      option.setAttribute('data-base-label', baseLabel);
    }

    // Update label with count and add checkmark if complete
    const isComplete = count >= TARGET_COUNT;
    const checkmark = isComplete ? '✓ ' : '';
    option.textContent = `${checkmark}${baseLabel} (${count}/${TARGET_COUNT})`;

    // Add CSS class for styling
    if (isComplete) {
      option.classList.add('complete');
    } else {
      option.classList.remove('complete');
    }
  });
}

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
function displayHTML(html, count = 1) {
  htmlPreview.value = html;
  updateCharCount(html.length);

  // Update fragment count display
  if (count > 1) {
    fragmentCount.textContent = `(${count} fragments)`;
  } else {
    fragmentCount.textContent = '';
  }

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
async function handleFragmentTypeChange() {
  const selectedType = fragmentTypeSelect.value;

  if (!selectedType) {
    jsonEditor.value = '';
    jsonEditor.placeholder = 'Select a fragment type to load the template...';
    updateSaveButtonState();
    await saveState();
    return;
  }

  loadTemplateWithExtraction();
  await saveState();
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
async function handleJsonEdit() {
  validateJSON();
  updateSaveButtonState();
  await saveState();
}

/**
 * Handle "Fix JSON" button click
 */
async function handleFixJson() {
  const jsonText = jsonEditor.value.trim();

  if (!jsonText) {
    showValidationWarning('⚠️ No JSON to fix. The editor is empty.');
    return;
  }

  try {
    // Use the jsonrepair library (loaded from jsonrepair.min.js)
    // The library exports to window.JSONRepair object
    if (typeof JSONRepair === 'undefined' || typeof JSONRepair.jsonrepair !== 'function') {
      throw new Error('JSON repair library not loaded');
    }

    const fixed = JSONRepair.jsonrepair(jsonText);

    // Try to parse and prettify the fixed JSON
    const parsed = JSON.parse(fixed);
    const prettified = JSON.stringify(parsed, null, 2);

    // Update editor with fixed JSON
    jsonEditor.value = prettified;

    // Show success message
    showValidationSuccess('✓ JSON fixed successfully!');

    // Validate and update state
    validateJSON();
    updateSaveButtonState();
    await saveState();
  } catch (error) {
    // If repair failed, show error
    showValidationError('✗ Could not fix JSON: ' + error.message);
  }
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
async function handleSave() {
  if (saveBtn.disabled) return;

  try {
    // Disable save button during save
    saveBtn.disabled = true;
    saveBtn.textContent = '💾 Saving...';

    // Parse JSON
    const label = JSON.parse(jsonEditor.value);

    // Create annotation object
    const annotation = {
      html: currentHTML,
      label: label,
      url: currentURL,
      timestamp: new Date().toISOString()
    };

    // Send to local server
    const response = await fetch('http://localhost:8000/save', {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify(annotation)
    });

    const result = await response.json();

    if (response.ok && result.success) {
      // Show success message with filename
      showValidationSuccess(`✓ Saved: ${result.filename}`);

      // Refresh counts
      await fetchCounts();

      // Auto-clear after 1.5 seconds
      setTimeout(() => {
        handleClear(true); // Pass true to skip confirmation
      }, 1500);
    } else {
      throw new Error(result.error || 'Server returned error');
    }

  } catch (error) {
    console.error('Error saving annotation:', error);

    // Check if server is running
    if (error.message.includes('fetch') || error.message.includes('NetworkError')) {
      showValidationError('✗ Server not running! Start: python annotation_server.py');
    } else {
      showValidationError('✗ Failed to save: ' + error.message);
    }
  } finally {
    // Re-enable save button
    saveBtn.disabled = false;
    saveBtn.textContent = '💾 Save Annotation';
    updateSaveButtonState(); // Recheck state
  }
}

/**
 * Handle clear button click
 */
async function handleClear(skipConfirmation = false) {
  if (skipConfirmation || confirm('Clear all fields and start over?')) {
    currentHTML = '';
    currentURL = '';
    htmlPreview.value = '';
    updateCharCount(0);
    fragmentTypeSelect.value = '';
    jsonEditor.value = '';
    jsonEditor.placeholder = 'Select a fragment type to load the template...';
    clearValidationMessage();
    updateSaveButtonState();
    await saveState();
  }
}

/**
 * Save state to chrome.storage
 */
async function saveState() {
  const state = {
    currentHTML: currentHTML,
    currentURL: currentURL,
    urlList: urlList,
    currentUrlIndex: currentUrlIndex,
    fragmentType: fragmentTypeSelect.value,
    jsonEditorValue: jsonEditor.value
  };

  await chrome.storage.local.set({ popupState: state });
}

/**
 * Restore state from chrome.storage
 */
async function restoreState() {
  const result = await chrome.storage.local.get('popupState');
  const state = result.popupState;

  if (state) {
    // Restore URL list state
    if (state.urlList && state.urlList.length > 0) {
      urlList = state.urlList;
      currentUrlIndex = state.currentUrlIndex ?? 0;

      urlStatus.textContent = `✓ Loaded ${urlList.length} URLs (${currentUrlIndex}/${urlList.length} opened)`;
      urlStatus.className = 'url-status active';
      openNextUrlBtn.disabled = currentUrlIndex >= urlList.length;

      if (currentUrlIndex >= urlList.length) {
        openNextUrlBtn.textContent = '✓ All URLs Opened';
      }
    }

    // Restore HTML selection
    if (state.currentHTML) {
      currentHTML = state.currentHTML;
      currentURL = state.currentURL;
      displayHTML(state.currentHTML, state.fragmentCount || 1);
    }

    // Restore fragment type
    if (state.fragmentType) {
      fragmentTypeSelect.value = state.fragmentType;
    }

    // Restore JSON editor (only if not a new selection)
    if (state.jsonEditorValue && !state.newSelectionMade) {
      jsonEditor.value = state.jsonEditorValue;
      validateJSON();
    }

    // If a new selection was made, trigger auto-extraction
    if (state.newSelectionMade && state.currentHTML) {
      if (fragmentTypeSelect.value) {
        loadTemplateWithExtraction();
      }

      // Clear the flag
      state.newSelectionMade = false;
      chrome.storage.local.set({ popupState: state });
    }

    updateSaveButtonState();
  }
}

// Listen for storage changes (when HTML is selected while side panel is open)
chrome.storage.onChanged.addListener((changes, areaName) => {
  if (areaName === 'local' && changes.popupState) {
    const newState = changes.popupState.newValue;

    // If new HTML was selected, update the UI
    if (newState && newState.newSelectionMade && newState.currentHTML) {
      currentHTML = newState.currentHTML;
      currentURL = newState.currentURL;
      displayHTML(newState.currentHTML, newState.fragmentCount || 1);

      // If fragment type is selected, trigger auto-extraction
      if (fragmentTypeSelect.value) {
        loadTemplateWithExtraction();
      }

      // Clear the flag
      newState.newSelectionMade = false;
      chrome.storage.local.set({ popupState: newState });
    }
  }
});

// Initialize on load
document.addEventListener('DOMContentLoaded', async () => {
  await restoreState();
  await fetchCounts();
  updateSaveButtonState();
});
