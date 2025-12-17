// Background service worker for HTML Fragment Labeler
// Handles extension lifecycle events and message passing

// Installation handler
chrome.runtime.onInstalled.addListener((details) => {
  if (details.reason === 'install') {
    console.log('HTML Fragment Labeler extension installed');
  } else if (details.reason === 'update') {
    console.log('HTML Fragment Labeler extension updated');
  }
});

// Handle messages from content script
chrome.runtime.onMessage.addListener((request, sender, sendResponse) => {
  if (request.action === 'htmlSelected') {
    // Store the selected HTML in chrome.storage
    chrome.storage.local.get('popupState', (result) => {
      const state = result.popupState || {};

      // Update state with new HTML selection
      state.currentHTML = request.html;
      state.currentURL = request.url;
      state.fragmentCount = request.fragmentCount || 1;
      state.newSelectionMade = true; // Flag to trigger auto-extraction

      // Save updated state
      chrome.storage.local.set({ popupState: state }, () => {
        console.log(`HTML selection saved to storage (${state.fragmentCount} fragment(s))`);
        sendResponse({ success: true });
      });
    });

    return true; // Keep channel open for async response
  }

  return true;
});
