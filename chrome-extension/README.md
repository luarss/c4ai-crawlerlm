# HTML Fragment Labeler - Chrome Extension

A Chrome extension for manually annotating HTML fragments with structured JSON labels for machine learning dataset creation.

## Features

- 🎯 **Element Selection**: Click to select any HTML element on a webpage
- 📄 **Full Page Capture**: Capture entire `<body>` HTML
- 🏷️ **Schema Templates**: Pre-defined templates for recipe, event, job, person, pricing, and negative examples
- 🤖 **Auto-Extraction**: Basic field pre-population from HTML structure
- ✓ **JSON Validation**: Real-time validation with error messages
- 💾 **Export**: Download annotations as JSON files

## Installation

### 1. Add Extension Icon (Required)

The extension requires an icon file. Create or download a 128x128 PNG icon:

```bash
# Option 1: Create a simple placeholder icon using ImageMagick
convert -size 128x128 xc:#667eea -pointsize 48 -fill white -gravity center -annotate +0+0 "🏷️" icon.png

# Option 2: Use any 128x128 PNG image and name it icon.png
# Place it in the chrome-extension/ directory
```

Or create a simple icon manually and save it as `icon.png` in the `chrome-extension/` directory.

### 2. Load Extension in Chrome

1. Open Chrome and navigate to `chrome://extensions/`
2. Enable "Developer mode" (toggle in top-right corner)
3. Click "Load unpacked"
4. Select the `chrome-extension/` directory
5. The extension icon should appear in your toolbar

## Usage

### Step 1: Navigate to a Webpage

Go to any webpage you want to annotate (e.g., a recipe page, product listing, event page, etc.)

### Step 2: Open Extension

Click the extension icon in your Chrome toolbar to open the popup.

### Step 3: Select HTML

**Option A: Select Fragment**
1. Click "Select Fragment" button
2. A blue banner will appear: "Selection Mode Active"
3. Hover over elements on the page (they'll be highlighted in blue)
4. Click any element to select it
5. Press `Esc` to cancel selection

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

Click "Save Annotation" to download the labeled data as a JSON file:

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

1. **Start with diverse examples**: Collect 5-10 examples per schema type
2. **Include noise**: Select fragments with surrounding HTML (ads, navigation, etc.)
3. **Verify JSON**: Make sure no "TODO" placeholders remain
4. **Use keyboard shortcuts**: Press `Esc` to cancel selection mode
5. **Batch annotation**: Keep the popup open and annotate multiple pages

## Troubleshooting

**Extension icon not showing?**
- Make sure you created/added `icon.png` (128x128 PNG)

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

## File Structure

```
chrome-extension/
├── manifest.json       # Extension configuration
├── popup.html         # Extension UI
├── popup.js           # UI logic
├── content.js         # Page interaction script
├── content.css        # Selection mode styles
├── background.js      # Service worker
├── styles.css         # Popup styles
├── schemas.js         # Schema templates & extraction
├── icon.png          # Extension icon (you need to add this)
└── README.md         # This file
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
