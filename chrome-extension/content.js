// Content script for HTML fragment selection
let selectionMode = false;
let hoveredElement = null;
let selectionBanner = null;
let selectedFragments = []; // Array to store multiple selected fragments
let selectedElements = []; // Track DOM elements to highlight them

// Initialize message listener
chrome.runtime.onMessage.addListener((request, sender, sendResponse) => {
  if (request.action === 'startSelection') {
    startSelectionMode();
    sendResponse({ success: true });
  } else if (request.action === 'selectBody') {
    const bodyHTML = document.body.outerHTML;
    chrome.runtime.sendMessage({
      action: 'htmlSelected',
      html: bodyHTML,
      url: window.location.href
    });
    sendResponse({ success: true });
  } else if (request.action === 'stopSelection') {
    stopSelectionMode();
    sendResponse({ success: true });
  } else if (request.action === 'clearSelections') {
    clearSelectedFragments();
    sendResponse({ success: true });
  }
  return true; // Keep channel open for async response
});

/**
 * Start element selection mode
 */
function startSelectionMode() {
  if (selectionMode) return;

  selectionMode = true;

  // Create selection banner
  updateSelectionBanner();

  // Add button listeners
  document.getElementById('html-labeler-cancel').addEventListener('click', stopSelectionMode);
  document.getElementById('html-labeler-done').addEventListener('click', finishSelection);

  // Add event listeners
  document.addEventListener('mouseover', handleMouseOver, true);
  document.addEventListener('mouseout', handleMouseOut, true);
  document.addEventListener('click', handleClick, true);
  document.addEventListener('keydown', handleKeyDown, true);
}

/**
 * Update selection banner with current count
 */
function updateSelectionBanner() {
  if (selectionBanner) {
    selectionBanner.remove();
  }

  selectionBanner = document.createElement('div');
  selectionBanner.id = 'html-labeler-banner';

  const count = selectedFragments.length;
  const countText = count > 0 ? ` (${count} selected)` : '';

  selectionBanner.innerHTML = `
    <div style="display: flex; align-items: center; justify-content: space-between; width: 100%;">
      <span>🎯 Multi-Fragment Selection${countText} - Click elements to add</span>
      <div style="display: flex; gap: 10px;">
        <button id="html-labeler-done" style="
          background: #10b981;
          color: white;
          border: none;
          padding: 5px 15px;
          border-radius: 4px;
          cursor: pointer;
          font-size: 14px;
          ${count === 0 ? 'opacity: 0.5; cursor: not-allowed;' : ''}
        " ${count === 0 ? 'disabled' : ''}>Done</button>
        <button id="html-labeler-cancel" style="
          background: #ff4444;
          color: white;
          border: none;
          padding: 5px 15px;
          border-radius: 4px;
          cursor: pointer;
          font-size: 14px;
        ">Cancel (Esc)</button>
      </div>
    </div>
  `;
  document.body.appendChild(selectionBanner);
}

/**
 * Clear all selected fragments
 */
function clearSelectedFragments() {
  // Remove highlights from selected elements
  selectedElements.forEach(el => {
    el.style.outline = '';
    el.style.backgroundColor = '';
  });

  selectedFragments = [];
  selectedElements = [];

  if (selectionMode) {
    updateSelectionBanner();
    // Re-add button listeners
    document.getElementById('html-labeler-cancel').addEventListener('click', stopSelectionMode);
    document.getElementById('html-labeler-done').addEventListener('click', finishSelection);
  }
}

/**
 * Finish selection and send all fragments
 */
function finishSelection() {
  if (selectedFragments.length === 0) return;

  // Combine all selected HTML fragments
  const combinedHTML = selectedFragments.join('\n\n<!-- FRAGMENT SEPARATOR -->\n\n');
  const url = window.location.href;

  // Send to background
  chrome.runtime.sendMessage({
    action: 'htmlSelected',
    html: combinedHTML,
    url: url,
    fragmentCount: selectedFragments.length
  });

  // Clear selections and stop mode
  clearSelectedFragments();
  stopSelectionMode();
}

/**
 * Stop element selection mode
 */
function stopSelectionMode() {
  if (!selectionMode) return;

  selectionMode = false;

  // Remove banner
  if (selectionBanner) {
    selectionBanner.remove();
    selectionBanner = null;
  }

  // Remove hover effect
  if (hoveredElement) {
    hoveredElement.style.outline = '';
    hoveredElement = null;
  }

  // Clear selected fragments highlights
  clearSelectedFragments();

  // Remove event listeners
  document.removeEventListener('mouseover', handleMouseOver, true);
  document.removeEventListener('mouseout', handleMouseOut, true);
  document.removeEventListener('click', handleClick, true);
  document.removeEventListener('keydown', handleKeyDown, true);
}

/**
 * Handle mouse over element
 */
function handleMouseOver(event) {
  if (!selectionMode) return;

  // Ignore banner
  if (event.target.id === 'html-labeler-banner' ||
      event.target.closest('#html-labeler-banner')) {
    return;
  }

  event.stopPropagation();
  event.preventDefault();

  // Remove previous highlight
  if (hoveredElement && hoveredElement !== event.target) {
    hoveredElement.style.outline = '';
  }

  // Highlight current element
  hoveredElement = event.target;
  hoveredElement.style.outline = '3px solid #4A90E2';
  hoveredElement.style.outlineOffset = '2px';
}

/**
 * Handle mouse out of element
 */
function handleMouseOut(event) {
  if (!selectionMode) return;

  // Don't remove highlight if moving to child element
  if (event.relatedTarget && event.target.contains(event.relatedTarget)) {
    return;
  }

  if (hoveredElement === event.target) {
    event.target.style.outline = '';
  }
}

/**
 * Handle element click
 */
function handleClick(event) {
  if (!selectionMode) return;

  // Ignore banner clicks
  if (event.target.id === 'html-labeler-banner' ||
      event.target.closest('#html-labeler-banner')) {
    return;
  }

  event.stopPropagation();
  event.preventDefault();

  // Check if element is already selected
  const elementIndex = selectedElements.indexOf(event.target);

  if (elementIndex > -1) {
    // Deselect if already selected
    selectedElements.splice(elementIndex, 1);
    selectedFragments.splice(elementIndex, 1);
    event.target.style.outline = '';
    event.target.style.backgroundColor = '';
  } else {
    // Add to selection
    const selectedHTML = event.target.outerHTML;
    selectedFragments.push(selectedHTML);
    selectedElements.push(event.target);

    // Highlight selected element with green
    event.target.style.outline = '3px solid #10b981';
    event.target.style.outlineOffset = '2px';
    event.target.style.backgroundColor = 'rgba(16, 185, 129, 0.1)';
  }

  // Update banner count
  updateSelectionBanner();

  // Re-add button listeners after banner update
  document.getElementById('html-labeler-cancel').addEventListener('click', stopSelectionMode);
  document.getElementById('html-labeler-done').addEventListener('click', finishSelection);

  // Remove hover highlight
  if (hoveredElement) {
    hoveredElement.style.outline = '';
    hoveredElement = null;
  }
}

/**
 * Handle keyboard events
 */
function handleKeyDown(event) {
  if (!selectionMode) return;

  // Escape key to cancel
  if (event.key === 'Escape') {
    event.preventDefault();
    event.stopPropagation();
    stopSelectionMode();
  }
}
