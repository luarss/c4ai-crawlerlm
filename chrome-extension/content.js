// Content script for HTML fragment selection
let selectionMode = false;
let hoveredElement = null;
let selectionBanner = null;

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
  selectionBanner = document.createElement('div');
  selectionBanner.id = 'html-labeler-banner';
  selectionBanner.innerHTML = `
    <div style="display: flex; align-items: center; justify-content: space-between; width: 100%;">
      <span>🎯 Selection Mode Active - Click any element to select it</span>
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
  `;
  document.body.appendChild(selectionBanner);

  // Add cancel button listener
  document.getElementById('html-labeler-cancel').addEventListener('click', stopSelectionMode);

  // Add event listeners
  document.addEventListener('mouseover', handleMouseOver, true);
  document.addEventListener('mouseout', handleMouseOut, true);
  document.addEventListener('click', handleClick, true);
  document.addEventListener('keydown', handleKeyDown, true);
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

  // Capture HTML
  const selectedHTML = event.target.outerHTML;
  const url = window.location.href;

  // Send to popup
  chrome.runtime.sendMessage({
    action: 'htmlSelected',
    html: selectedHTML,
    url: url
  });

  // Stop selection mode
  stopSelectionMode();
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
