// Background service worker for HTML Fragment Labeler
// Handles extension lifecycle events

// Installation handler
chrome.runtime.onInstalled.addListener((details) => {
  if (details.reason === 'install') {
    console.log('HTML Fragment Labeler extension installed');
  } else if (details.reason === 'update') {
    console.log('HTML Fragment Labeler extension updated');
  }
});

// Keep service worker alive for message passing
chrome.runtime.onMessage.addListener((request, sender, sendResponse) => {
  // Forward messages between content script and popup
  return true;
});
