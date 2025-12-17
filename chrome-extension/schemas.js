// Schema templates ported from src/schemas.py
const ANNOTATION_TEMPLATES = {
  recipe: {
    type: "recipe",
    name: "TODO",
    description: "TODO",
    author: "TODO",
    prep_time: "TODO",
    cook_time: "TODO",
    total_time: "TODO",
    servings: "TODO",
    ingredients: ["TODO"],
    instructions: ["TODO"],
    rating: { score: "TODO", review_count: "TODO" }
  },
  event: {
    type: "event",
    title: "TODO",
    datetime: "TODO",
    location: "TODO",
    venue_name: "TODO",
    price: "TODO",
    organizer: "TODO",
    attendee_count: "TODO",
    description: "TODO",
    event_type: "TODO"
  },
  pricing_table: {
    type: "pricing_table",
    plans: [
      {
        name: "TODO",
        price: "TODO",
        price_amount: "TODO",
        currency: "TODO",
        billing_period: "TODO",
        features: ["TODO"],
        description: "TODO"
      }
    ]
  },
  job_posting: {
    type: "job_posting",
    title: "TODO",
    company: "TODO",
    location: "TODO",
    department: "TODO",
    posted_date: "TODO",
    employment_type: "TODO",
    description: "TODO"
  },
  person: {
    type: "person",
    name: "TODO",
    title: "TODO",
    bio: "TODO",
    email: "TODO",
    phone: "TODO",
    linkedin: "TODO",
    image_url: "TODO"
  },
  error_page: {
    type: "error_page",
    error_code: "TODO",
    message: "TODO",
    description: "TODO"
  },
  auth_required: {
    type: "auth_required",
    message: "TODO",
    description: "TODO",
    content_available: false
  },
  empty_shell: {
    type: "empty_shell",
    framework: "TODO",
    content_available: false,
    reason: "client_side_rendering"
  }
};

/**
 * Get schema template for a fragment type
 */
function getSchemaTemplate(fragmentType) {
  if (!ANNOTATION_TEMPLATES[fragmentType]) {
    throw new Error(`Unknown fragment type: ${fragmentType}`);
  }
  // Return a deep copy to avoid mutations
  return JSON.parse(JSON.stringify(ANNOTATION_TEMPLATES[fragmentType]));
}

/**
 * Extract basic fields from HTML to pre-populate the template
 * Conservative approach: only extract if confidence is high
 */
function autoExtractFields(htmlString, fragmentType) {
  const parser = new DOMParser();
  const doc = parser.parseFromString(htmlString, 'text/html');
  const extracted = {};

  // Helper to get first element's text content
  const getFirstText = (selector) => {
    const el = doc.querySelector(selector);
    return el ? el.textContent.trim() : null;
  };

  // Helper to get all matching elements' text
  const getAllText = (selector) => {
    const elements = doc.querySelectorAll(selector);
    return Array.from(elements).map(el => el.textContent.trim()).filter(t => t);
  };

  // Extract title/name from headings
  const titleText = getFirstText('h1') || getFirstText('h2') || getFirstText('h3');

  // Extract first image
  const firstImg = doc.querySelector('img');
  const imageUrl = firstImg ? firstImg.src : null;

  // Type-specific extraction
  switch (fragmentType) {
    case 'recipe':
      if (titleText) extracted.name = titleText;

      // Extract ingredients from lists
      const ingredientList = getAllText('ul li, ol li');
      if (ingredientList.length > 0 && ingredientList.length < 30) {
        // Only if reasonable number of items
        extracted.ingredients = ingredientList;
      }

      // Extract instructions
      const instructionList = doc.querySelectorAll('ol li');
      if (instructionList.length > 0) {
        extracted.instructions = Array.from(instructionList).map(el => el.textContent.trim());
      }

      // Extract author
      const authorText = getFirstText('[itemprop="author"]') ||
                        getFirstText('.author') ||
                        getFirstText('.recipe-author');
      if (authorText) extracted.author = authorText;

      // Extract description
      const descText = getFirstText('[itemprop="description"]') ||
                       getFirstText('.description') ||
                       getFirstText('p');
      if (descText && descText.length > 20 && descText.length < 500) {
        extracted.description = descText;
      }

      if (imageUrl) extracted.image_url = imageUrl;
      break;

    case 'event':
      if (titleText) extracted.title = titleText;

      // Extract datetime
      const timeEl = doc.querySelector('time[datetime]');
      if (timeEl) extracted.datetime = timeEl.getAttribute('datetime');

      // Extract location/venue
      const locationText = getFirstText('address') ||
                          getFirstText('[itemprop="location"]') ||
                          getFirstText('.location') ||
                          getFirstText('.venue');
      if (locationText) {
        extracted.location = locationText;
        extracted.venue_name = locationText.split(',')[0].trim();
      }

      // Extract price
      const priceMatch = doc.body.textContent.match(/\$\d+(?:\.\d{2})?/);
      if (priceMatch) extracted.price = priceMatch[0];

      // Extract description
      const eventDesc = getFirstText('.description') ||
                       getFirstText('[itemprop="description"]') ||
                       getFirstText('p');
      if (eventDesc && eventDesc.length > 20) extracted.description = eventDesc;

      if (imageUrl) extracted.image_url = imageUrl;
      break;

    case 'pricing_table':
      // Extract plan names from headers
      const planNames = getAllText('h2, h3, .plan-name, .tier-name');
      if (planNames.length > 0 && planNames.length <= 5) {
        extracted.plans = planNames.map(name => ({
          name: name,
          price: "TODO",
          features: ["TODO"]
        }));
      }
      break;

    case 'job_posting':
      if (titleText) extracted.title = titleText;

      // Extract company name
      const companyText = getFirstText('.company-name') ||
                         getFirstText('[itemprop="hiringOrganization"]') ||
                         getFirstText('.company');
      if (companyText) extracted.company = companyText;

      // Extract location
      const jobLocation = getFirstText('.location') ||
                         getFirstText('[itemprop="jobLocation"]') ||
                         getFirstText('.job-location');
      if (jobLocation) extracted.location = jobLocation;

      // Extract description
      const jobDesc = getFirstText('.description') ||
                     getFirstText('[itemprop="description"]');
      if (jobDesc && jobDesc.length > 50) extracted.description = jobDesc;
      break;

    case 'person':
      if (titleText) extracted.name = titleText;

      // Extract job title
      const jobTitle = getFirstText('.title') ||
                      getFirstText('[itemprop="jobTitle"]') ||
                      getFirstText('.role');
      if (jobTitle) extracted.title = jobTitle;

      // Extract email
      const emailMatch = doc.body.textContent.match(/[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}/);
      if (emailMatch) extracted.email = emailMatch[0];

      // Extract phone
      const phoneMatch = doc.body.textContent.match(/\(\d{3}\)\s*\d{3}-\d{4}|\d{3}-\d{3}-\d{4}/);
      if (phoneMatch) extracted.phone = phoneMatch[0];

      // Extract LinkedIn
      const linkedinLink = doc.querySelector('a[href*="linkedin.com"]');
      if (linkedinLink) extracted.linkedin = linkedinLink.href;

      // Extract bio
      const bioText = getFirstText('.bio') ||
                     getFirstText('[itemprop="description"]') ||
                     getFirstText('p');
      if (bioText && bioText.length > 30) extracted.bio = bioText;

      if (imageUrl) extracted.image_url = imageUrl;
      break;

    case 'error_page':
      // Extract error code
      const errorCodeMatch = doc.body.textContent.match(/\b(404|500|503|502|403|429)\b/);
      if (errorCodeMatch) extracted.error_code = parseInt(errorCodeMatch[0]);

      if (titleText) extracted.message = titleText;

      const errorDesc = getFirstText('p');
      if (errorDesc) extracted.description = errorDesc;
      break;

    case 'auth_required':
      if (titleText) extracted.message = titleText;

      const authDesc = getFirstText('p');
      if (authDesc) extracted.description = authDesc;
      break;

    case 'empty_shell':
      // Detect framework
      if (htmlString.includes('__next') || htmlString.includes('_reactRoot')) {
        extracted.framework = 'react';
      } else if (htmlString.includes('__nuxt') || htmlString.includes('__NUXT__')) {
        extracted.framework = 'vue';
      } else if (htmlString.includes('ng-version') || htmlString.includes('ng-app')) {
        extracted.framework = 'angular';
      }
      break;

    default:
      // No extraction for unknown types
      break;
  }

  return extracted;
}

/**
 * Merge extracted fields into template
 */
function populateTemplate(template, extracted) {
  const result = JSON.parse(JSON.stringify(template)); // Deep copy

  function merge(target, source) {
    for (const key in source) {
      if (source[key] !== null && source[key] !== undefined) {
        if (typeof source[key] === 'object' && !Array.isArray(source[key]) && typeof target[key] === 'object') {
          merge(target[key], source[key]);
        } else {
          target[key] = source[key];
        }
      }
    }
  }

  merge(result, extracted);
  return result;
}
