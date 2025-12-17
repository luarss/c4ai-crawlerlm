# HTML Fragment Labeler - Chrome Extension

A Chrome extension for manually annotating HTML fragments with structured JSON labels for machine learning dataset creation.

## Features

- 📋 **URL List Loader**: Load and open domains from `DOMAIN_LIST.md` one by one
- 🎯 **Multi-Fragment Selection**: Select multiple HTML elements from a page and combine them
- 📄 **Full Page Capture**: Capture entire `<body>` HTML
- 🏷️ **Schema Templates**: Pre-defined templates for recipe, event, job, person, pricing, and negative examples
- 🤖 **Auto-Extraction**: Basic field pre-population from HTML structure
- ✓ **JSON Validation**: Real-time validation with error messages
- 💾 **Auto-Save**: Automatically saves to `./data/manual/` via local server
- 🔄 **Auto-Clear**: Clears form after successful save for rapid batch annotation
- 💾 **State Persistence**: Keeps your selections even when popup loses focus

## Installation

### 1. Install Dependencies (First Time Only)

The server requires FastAPI and uvicorn:

```bash
# Install all dev dependencies (from project root)
uv sync --all-extras
```

### 2. Start the Local Server (Required)

The extension saves annotations to `./data/manual/` and loads domains from `DOMAIN_LIST.md` via a local server. Start it first:

```bash
cd chrome-extension
python annotation_server.py
```

You should see:
```
🚀 Annotation Server Running
Listening on: http://localhost:8000
Saving to: ../data/manual/

Endpoints:
  GET  /urls  - Fetch URL list
  POST /save  - Save annotation
```

**Keep this server running** while using the extension.

### 3. Load Extension in Chrome

1. Open Chrome and navigate to `chrome://extensions/`
2. Enable "Developer mode" (toggle in top-right corner)
3. Click "Load unpacked"
4. Select the `chrome-extension/` directory
5. The extension icon should appear in your toolbar

## Usage

### Step 0 (Optional): Load Domain List

The extension can automatically load domains from `DOMAIN_LIST.md` and open them one by one:

1. Click "Load URL List" button
2. The extension will fetch all domains from DOMAIN_LIST.md (~70+ domains)
3. Click "Open Next URL" to open each domain in a new tab
4. The status bar shows your progress (e.g., "Opened URL 5/70")
5. Continue clicking "Open Next URL" and annotating each page

This is perfect for batch annotation workflows where you need to collect HTML fragments from all domains in your list.

### Step 1: Navigate to a Webpage

Go to any webpage you want to annotate (e.g., a recipe page, product listing, event page, etc.)

**Option A: Use the URL Loader (recommended for batch annotation)**
- Use the "Load URL List" and "Open Next URL" buttons (see Step 0 above)

**Option B: Navigate manually**
- Visit any webpage directly

### Step 2: Open Extension

Click the extension icon in your Chrome toolbar to open the popup.

### Step 3: Select HTML

**Option A: Select Multiple Fragments**
1. Click "Select Fragment" button
2. A banner will appear: "Multi-Fragment Selection - Click elements to add"
3. Hover over elements on the page (they'll be highlighted in blue)
4. Click elements to select them (they turn green)
5. Click selected elements again to deselect them
6. The banner shows count: "(3 selected)"
7. Click "Done" when finished, or "Cancel (Esc)" to abort
8. Multiple fragments are combined with separators

**Option B: Select Full Body**
- Click "Select Full Body" to capture the entire page HTML

### Step 4: Choose Fragment Type

Select the appropriate fragment type from the dropdown:

**Positive Examples:**
- Recipe
- Event
- Pricing Table
- Job Posting
- Person/Contact

**Negative Examples:**
- Error Page
- Auth Required
- Empty SPA Shell

### Step 5: Review & Edit JSON

The JSON editor will auto-populate with:
- Schema template for the selected type
- Basic extracted fields (titles, prices, dates, etc.)

Review and edit the JSON to accurately represent the HTML content. Replace any "TODO" placeholders with actual values.

### Step 6: Save Annotation

Click "Save Annotation" to automatically save to `./data/manual/`:

- ✓ File saved as `annotation_<type>_<timestamp>.json`
- ✓ Success message shows the filename
- ✓ Form auto-clears after 1.5 seconds for rapid batch annotation
- ✓ Server terminal shows live save confirmations

The saved JSON format:
```json
{
  "html": "<div class='recipe'>...</div>",
  "label": {
    "type": "recipe",
    "name": "Chocolate Chip Cookies",
    "ingredients": ["2 cups flour", "1 cup sugar"],
    ...
  },
  "url": "https://example.com/page",
  "timestamp": "2025-12-17T10:30:00Z"
}
```

**Pro Tip**: Leave the extension popup open and keep annotating. Each save auto-clears the form so you can quickly select the next fragment.

## Schema Types

### Recipe
- name, description, author
- prep_time, cook_time, total_time
- servings, ingredients, instructions
- rating (score, review_count)

### Event
- title, datetime, location, venue_name
- price, organizer, attendee_count
- description, event_type

### Pricing Table
- plans[] with name, price, features
- currency, billing_period

### Job Posting
- title, company, location
- department, posted_date, employment_type
- description

### Person
- name, title, bio
- email, phone, linkedin
- image_url

### Error Page (Negative)
- error_code (404, 500, etc.)
- message, description

### Auth Required (Negative)
- message, description
- content_available: false

### Empty SPA Shell (Negative)
- framework (react, vue, angular)
- content_available: false

## Auto-Extraction

The extension automatically extracts common patterns:

- **Titles**: h1, h2, h3 → name/title fields
- **Prices**: $XX.XX format → price fields
- **Dates**: `<time datetime="">` → date fields
- **Lists**: ul/ol → ingredients/features/instructions
- **Emails**: Email regex → email field
- **Images**: First img src → image_url field

Review and correct all auto-extracted values before saving.

## Tips

1. **Use domain loader for batch annotation**: Load DOMAIN_LIST.md and use "Open Next URL" to systematically go through all domains
2. **Start with diverse examples**: Collect 5-10 examples per schema type
3. **Include noise**: Select fragments with surrounding HTML (ads, navigation, etc.)
4. **Verify JSON**: Make sure no "TODO" placeholders remain
5. **Use keyboard shortcuts**: Press `Esc` to cancel selection mode
6. **Batch annotation**: Keep the popup open and annotate multiple pages - the form auto-clears after each save

## Troubleshooting

**"Server not running!" error?**
- Start the server: `python annotation_server.py`
- Make sure it's running on port 8000
- Check server terminal for errors

**Extension icon not showing?**
- The icon was auto-generated during installation
- If missing, reload the extension in `chrome://extensions/`

**"Failed to start selection mode"?**
- Some pages (chrome://, file://) are restricted
- Try a regular webpage (http:// or https://)

**Auto-extraction not working?**
- Auto-extraction is conservative and may not extract everything
- Manually fill in missing fields

**Save button disabled?**
- Ensure you've selected HTML
- Ensure you've chosen a fragment type
- Check JSON is valid (no syntax errors)

**Annotations not appearing in `./data/manual/`?**
- Check server terminal for errors
- Verify server is running in `chrome-extension/` directory
- Server saves relative to its own location: `../data/manual/`

## File Structure

```
chrome-extension/
├── manifest.json          # Extension configuration
├── popup.html            # Extension UI
├── popup.js              # UI logic
├── content.js            # Page interaction script
├── content.css           # Selection mode styles
├── background.js         # Service worker
├── styles.css            # Popup styles
├── schemas.js            # Schema templates & extraction
├── annotation_server.py  # Local server for saving annotations
├── icon.png             # Extension icon (auto-generated)
└── README.md            # This file
```

## Development

To modify the extension:

1. Edit files in `chrome-extension/`
2. Go to `chrome://extensions/`
3. Click the reload icon on the extension card
4. Test your changes

## Data Collection Workflow

1. **Define schema** (already done in `schemas.js`)
2. **Collect 50-100 base examples** using this extension
3. **Generate synthetic variations** using `scripts/04_generate.py`
4. **Convert to chat format** using `scripts/05_convert_to_chat_format.py`
5. **Fine-tune model** (Task B)

## License

Part of the CrawlerLM project.
