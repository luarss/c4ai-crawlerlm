# Phase 1 Review: Understanding the Real Task

## The Goal

We're building a **small language model** (e.g., Qwen 0.6B) that can:

1. Take a messy HTML snippet containing embedded data
2. Identify the actual data-carrying fragment within the noise
3. Extract it into clean, structured JSON

Strong LLMs (OpenAI GPT series, Claude models, Gemini models) can already do this. The challenge is: **can we fine-tune a small model to do it reliably?**

This is fundamentally a **data extraction** task, not a **web page conversion** task.

---

## What is a "Data Fragment"?

A **data fragment** is a small HTML component that carries structured information worth extracting.

### Examples of Data Fragments

| Type | Contains |
|------|----------|
| Product card | name, price, rating, image, description, availability |
| Pricing table | plan names, features, prices, billing period |
| Contact block | name, email, phone, address, social links |
| Event listing | title, date, time, location, description, ticket price |
| Recipe card | title, ingredients, steps, prep time, servings |
| Review block | author, rating, review text, date, helpful votes |
| Job posting | title, company, location, salary range, requirements |
| Article metadata | title, author, publish date, reading time, tags |
| Person/profile card | name, title, bio, photo, social links |
| Address/location | street, city, state, zip, country, coordinates |

### What is NOT a Data Fragment

- Navigation bars
- Footers with generic links
- Cookie consent banners
- Pure layout containers (`<div class="wrapper">`)
- Script tags
- Style blocks
- Ads (unless extracting ad data is the goal)
- Boilerplate "related articles" sections

---

## The Role of Noise

This is critical: **we want noise around the fragment**.

Real-world HTML is messy. A product card doesn't exist in isolation - it's surrounded by:
- Navigation menus
- Sidebar ads
- Related products
- Script tags
- Tracking pixels
- Cookie banners
- Footer links

The model must learn to:
1. **Locate** the data-carrying fragment within noise
2. **Ignore** irrelevant surrounding elements
3. **Extract** only the meaningful structured data

A model trained on clean, isolated fragments will fail on real HTML. A model trained on messy, noisy HTML with embedded fragments will generalize.

---

## Schema-First Thinking

The correct approach:

```
1. Define the JSON schema (what fields, what types, what structure)
       |
       v
2. Identify what HTML patterns map to each field
       |
       v
3. Collect/generate examples that cover those patterns
       |
       v
4. Include variations: noise levels, malformed HTML, missing fields
       |
       v
5. Train and evaluate
```

**NOT:**

```
1. Crawl lots of web pages
       |
       v
2. Filter for "quality"
       |
       v
3. Hope a schema emerges
```

The schema drives the data collection, not the other way around.

---

## Where Phase 1 Went Wrong

### 1. Wrong Unit of Work

| You Did | Should Be |
|---------|-----------|
| Full web pages (469 pages) | HTML snippets with embedded data fragments |
| Common Crawl at scale | Small, deliberate collection of fragment types |
| Page-level filtering | Fragment-level identification |

### 2. Filtering Out the Valuable Cases

You filtered out:
- SPA pages → Could contain data fragments worth extracting
- Error pages → Model should learn to output `{type: "error"}` or empty
- Login walls → Model should NOT hallucinate missing content
- "Low quality" pages → Often contain the messy, nested structures we need

For a search index, filtering these makes sense. For a robustness dataset, these ARE the interesting cases.

### 3. Quality Score Optimizes for Wrong Goal

Your quality score favors:
- 500-5000 word count → biases toward articles
- Vocabulary richness → biases toward well-written content
- Semantic HTML → biases toward clean, modern markup

The task explicitly needs:
- Short fragments (a product card might be 50 words)
- Messy markup (nested tables, div soup, inconsistent classes)
- Noise around the signal

### 4. Token Thresholds Miscalibrated

- **Minimum 4K tokens**: Throws away small but valuable fragments. A product card with surrounding noise might be 500-2000 tokens. These are gold.
- **Maximum 128K tokens**: Qwen 0.6B likely has 32K context. 128K is unusable without truncation.

Better range for this task: **200 - 8000 tokens** (fragment + reasonable noise context)

### 5. No Schema Definition

The JSON schema should be defined FIRST. Without it, you're collecting data without knowing what you're collecting it for.

---

## Concrete Examples

Here are examples of what the training data should look like. Notice:
- The HTML is messy with noise around the fragment
- The JSON extracts only the meaningful data
- The model must learn to find signal in noise

---

### Example 1: Product Card with Noise

**Input HTML:**
```html
<div class="page-wrapper">
  <nav class="main-nav">
    <a href="/">Home</a>
    <a href="/products">Products</a>
    <a href="/cart">Cart (3)</a>
  </nav>

  <div class="sidebar-ad">
    <img src="ad-banner.jpg" />
    <span>Special offer! Click here</span>
  </div>

  <div class="product-card" data-id="12847">
    <img src="/img/wireless-headphones.jpg" class="product-img" />
    <h2 class="product-title">Sony WH-1000XM5 Wireless Headphones</h2>
    <div class="rating">
      <span class="stars">★★★★☆</span>
      <span class="count">(2,847 reviews)</span>
    </div>
    <div class="price-block">
      <span class="original-price">$399.99</span>
      <span class="sale-price">$328.00</span>
      <span class="discount">-18%</span>
    </div>
    <p class="description">Industry-leading noise canceling with Auto NC Optimizer. Crystal clear hands-free calling. Up to 30-hour battery life.</p>
    <div class="availability in-stock">In Stock</div>
    <button class="add-to-cart">Add to Cart</button>
  </div>

  <div class="related-products">
    <h3>You might also like</h3>
    <!-- more product cards -->
  </div>

  <script>trackPageView('product-12847');</script>
</div>
```

**Expected JSON:**
```json
{
  "type": "product",
  "name": "Sony WH-1000XM5 Wireless Headphones",
  "price": {
    "current": 328.00,
    "original": 399.99,
    "currency": "USD",
    "discount_percent": 18
  },
  "rating": {
    "score": 4.0,
    "max": 5.0,
    "review_count": 2847
  },
  "description": "Industry-leading noise canceling with Auto NC Optimizer. Crystal clear hands-free calling. Up to 30-hour battery life.",
  "availability": "in_stock",
  "image_url": "/img/wireless-headphones.jpg",
  "product_id": "12847"
}
```

---

### Example 2: Event Listing with Messy Markup

**Input HTML:**
```html
<body>
<div id="__next">
  <header>
    <div class="logo">EventBrite Clone</div>
    <input type="search" placeholder="Search events..." />
  </header>

  <main>
    <div class="cookie-notice" style="position:fixed;bottom:0;">
      We use cookies. <button>Accept</button>
    </div>

    <article class="event-item">
      <div class="event-image-wrap">
        <img src="jazz-night.jpg" loading="lazy"/>
        <span class="event-category">Music</span>
      </div>
      <div class="event-details">
        <h2>
          <a href="/events/jazz-night-2024">
            Jazz Night at Blue Note
          </a>
        </h2>
        <div class="event-meta">
          <time datetime="2024-03-15T20:00:00">Fri, Mar 15 · 8:00 PM</time>
          <address>Blue Note Jazz Club, 131 W 3rd St, New York, NY</address>
        </div>
        <div class="event-price">
          <span>From </span><strong>$45.00</strong>
        </div>
        <p class="event-desc">An evening of smooth jazz featuring the Marcus Miller Quartet. Two sets with intermission. Full bar and dinner service available.</p>
      </div>
    </article>

    <div class="ad-slot" id="gpt-slot-1"></div>
  </main>

  <script src="analytics.js"></script>
  <script>gtag('event', 'page_view');</script>
</div>
</body>
```

**Expected JSON:**
```json
{
  "type": "event",
  "title": "Jazz Night at Blue Note",
  "category": "Music",
  "datetime": "2024-03-15T20:00:00",
  "datetime_formatted": "Fri, Mar 15 · 8:00 PM",
  "venue": {
    "name": "Blue Note Jazz Club",
    "address": "131 W 3rd St, New York, NY"
  },
  "price": {
    "from": 45.00,
    "currency": "USD"
  },
  "description": "An evening of smooth jazz featuring the Marcus Miller Quartet. Two sets with intermission. Full bar and dinner service available.",
  "url": "/events/jazz-night-2024",
  "image_url": "jazz-night.jpg"
}
```

---

### Example 3: Contact/Person Card (Malformed HTML)

**Input HTML:**
```html
<div class=team-section>
  <h2>Our Team</h2>

  <div class="person-card>
    <img src=sarah-chen.jpg>
    <div class="info">
      <h3>Dr. Sarah Chen</h2>  <!-- mismatched tags -->
      <p class="title">Chief Technology Officer
      <p class="bio">Sarah leads our engineering team with 15+ years of experience in distributed systems. Previously at Google and Amazon. PhD from MIT in Computer Science.</p>
      <div class="contact-info">
        <a href="mailto:sarah@company.com">sarah@company.com</a>
        <a href="tel:+1-555-0123">+1 (555) 012-3456</a>
        <a href="https://linkedin.com/in/sarahchen">LinkedIn</a>
        <a href="https://twitter.com/sarahchen">@sarahchen</a>
      </div>
    </div>
  </div>

  <!-- tracking pixel -->
  <img src="https://track.example.com/pixel.gif" width="1" height="1" />
</div>
```

**Expected JSON:**
```json
{
  "type": "person",
  "name": "Dr. Sarah Chen",
  "title": "Chief Technology Officer",
  "bio": "Sarah leads our engineering team with 15+ years of experience in distributed systems. Previously at Google and Amazon. PhD from MIT in Computer Science.",
  "contact": {
    "email": "sarah@company.com",
    "phone": "+1 (555) 012-3456"
  },
  "social": {
    "linkedin": "https://linkedin.com/in/sarahchen",
    "twitter": "https://twitter.com/sarahchen"
  },
  "image_url": "sarah-chen.jpg"
}
```

Note: The HTML has malformed tags (missing quotes, mismatched h3/h2, unclosed p). The model must handle this gracefully.

---

### Example 4: Pricing Table

**Input HTML:**
```html
<section class="pricing" id="pricing">
  <script>console.log('pricing section loaded');</script>

  <h2 class="section-title">Choose Your Plan</h2>
  <p class="section-subtitle">All plans include 14-day free trial</p>

  <div class="pricing-grid">
    <div class="plan-card">
      <div class="plan-name">Starter</div>
      <div class="plan-price">
        <span class="currency">$</span>
        <span class="amount">9</span>
        <span class="period">/month</span>
      </div>
      <ul class="features">
        <li class="included">5 projects</li>
        <li class="included">10GB storage</li>
        <li class="included">Email support</li>
        <li class="not-included">API access</li>
        <li class="not-included">Custom domain</li>
      </ul>
      <a href="/signup?plan=starter" class="cta-btn">Start Free Trial</a>
    </div>

    <div class="plan-card featured">
      <div class="badge">Most Popular</div>
      <div class="plan-name">Professional</div>
      <div class="plan-price">
        <span class="currency">$</span>
        <span class="amount">29</span>
        <span class="period">/month</span>
      </div>
      <ul class="features">
        <li class="included">Unlimited projects</li>
        <li class="included">100GB storage</li>
        <li class="included">Priority support</li>
        <li class="included">API access</li>
        <li class="included">Custom domain</li>
      </ul>
      <a href="/signup?plan=pro" class="cta-btn">Start Free Trial</a>
    </div>

    <div class="plan-card">
      <div class="plan-name">Enterprise</div>
      <div class="plan-price">
        <span class="contact">Contact us</span>
      </div>
      <ul class="features">
        <li class="included">Everything in Pro</li>
        <li class="included">Unlimited storage</li>
        <li class="included">24/7 phone support</li>
        <li class="included">SLA guarantee</li>
        <li class="included">Dedicated account manager</li>
      </ul>
      <a href="/contact-sales" class="cta-btn">Contact Sales</a>
    </div>
  </div>

  <noscript>Please enable JavaScript to view pricing</noscript>
</section>
```

**Expected JSON:**
```json
{
  "type": "pricing_table",
  "title": "Choose Your Plan",
  "trial_period": "14-day free trial",
  "plans": [
    {
      "name": "Starter",
      "price": {
        "amount": 9,
        "currency": "USD",
        "period": "month"
      },
      "features": {
        "included": ["5 projects", "10GB storage", "Email support"],
        "not_included": ["API access", "Custom domain"]
      },
      "cta_url": "/signup?plan=starter",
      "highlighted": false
    },
    {
      "name": "Professional",
      "price": {
        "amount": 29,
        "currency": "USD",
        "period": "month"
      },
      "features": {
        "included": ["Unlimited projects", "100GB storage", "Priority support", "API access", "Custom domain"],
        "not_included": []
      },
      "cta_url": "/signup?plan=pro",
      "highlighted": true,
      "badge": "Most Popular"
    },
    {
      "name": "Enterprise",
      "price": {
        "amount": null,
        "contact_sales": true
      },
      "features": {
        "included": ["Everything in Pro", "Unlimited storage", "24/7 phone support", "SLA guarantee", "Dedicated account manager"],
        "not_included": []
      },
      "cta_url": "/contact-sales",
      "highlighted": false
    }
  ]
}
```

---

### Example 5: Recipe Card with Inline Noise

**Input HTML:**
```html
<div class="recipe-page">
  <div class="breadcrumb">Home > Recipes > Desserts > Cookies</div>

  <!-- AdSense -->
  <ins class="adsbygoogle" data-ad-client="ca-pub-xxx"></ins>

  <article class="recipe" itemscope itemtype="https://schema.org/Recipe">
    <h1 itemprop="name">Classic Chocolate Chip Cookies</h1>

    <div class="recipe-meta">
      <span class="author">By <span itemprop="author">Julia Baker</span></span>
      <span class="date">Published: <time itemprop="datePublished" datetime="2024-01-15">Jan 15, 2024</time></span>
      <span class="rating" itemprop="aggregateRating" itemscope itemtype="https://schema.org/AggregateRating">
        <span itemprop="ratingValue">4.8</span>/<span itemprop="bestRating">5</span>
        (<span itemprop="reviewCount">342</span> reviews)
      </span>
    </div>

    <div class="recipe-times">
      <div><strong>Prep:</strong> <time itemprop="prepTime" datetime="PT15M">15 min</time></div>
      <div><strong>Cook:</strong> <time itemprop="cookTime" datetime="PT12M">12 min</time></div>
      <div><strong>Total:</strong> <time itemprop="totalTime" datetime="PT27M">27 min</time></div>
      <div><strong>Servings:</strong> <span itemprop="recipeYield">24 cookies</span></div>
    </div>

    <p itemprop="description">Chewy, gooey chocolate chip cookies with crispy edges. This recipe has been perfected over 10 years of testing!</p>

    <div class="newsletter-popup" style="display:none;">
      Subscribe for more recipes!
      <input type="email" placeholder="Enter email" />
    </div>

    <h2>Ingredients</h2>
    <ul class="ingredients" itemprop="recipeIngredient">
      <li>2 1/4 cups all-purpose flour</li>
      <li>1 tsp baking soda</li>
      <li>1 tsp salt</li>
      <li>1 cup (2 sticks) butter, softened</li>
      <li>3/4 cup granulated sugar</li>
      <li>3/4 cup packed brown sugar</li>
      <li>2 large eggs</li>
      <li>2 tsp vanilla extract</li>
      <li>2 cups chocolate chips</li>
    </ul>

    <h2>Instructions</h2>
    <ol class="instructions" itemprop="recipeInstructions">
      <li>Preheat oven to 375°F (190°C).</li>
      <li>Mix flour, baking soda, and salt in a bowl.</li>
      <li>Beat butter and sugars until creamy.</li>
      <li>Add eggs and vanilla to butter mixture.</li>
      <li>Gradually blend in flour mixture.</li>
      <li>Stir in chocolate chips.</li>
      <li>Drop rounded tablespoons onto ungreased baking sheets.</li>
      <li>Bake for 9 to 11 minutes or until golden brown.</li>
    </ol>

    <script type="application/ld+json">{"@context":"schema.org"}</script>
  </article>

  <div class="comments-section">
    <h3>Comments (47)</h3>
    <!-- user comments here -->
  </div>
</div>
```

**Expected JSON:**
```json
{
  "type": "recipe",
  "name": "Classic Chocolate Chip Cookies",
  "author": "Julia Baker",
  "date_published": "2024-01-15",
  "rating": {
    "score": 4.8,
    "max": 5.0,
    "review_count": 342
  },
  "times": {
    "prep_minutes": 15,
    "cook_minutes": 12,
    "total_minutes": 27
  },
  "servings": "24 cookies",
  "description": "Chewy, gooey chocolate chip cookies with crispy edges. This recipe has been perfected over 10 years of testing!",
  "ingredients": [
    "2 1/4 cups all-purpose flour",
    "1 tsp baking soda",
    "1 tsp salt",
    "1 cup (2 sticks) butter, softened",
    "3/4 cup granulated sugar",
    "3/4 cup packed brown sugar",
    "2 large eggs",
    "2 tsp vanilla extract",
    "2 cups chocolate chips"
  ],
  "instructions": [
    "Preheat oven to 375°F (190°C).",
    "Mix flour, baking soda, and salt in a bowl.",
    "Beat butter and sugars until creamy.",
    "Add eggs and vanilla to butter mixture.",
    "Gradually blend in flour mixture.",
    "Stir in chocolate chips.",
    "Drop rounded tablespoons onto ungreased baking sheets.",
    "Bake for 9 to 11 minutes or until golden brown."
  ]
}
```

---

### Example 6: Job Posting (Deeply Nested)

**Input HTML:**
```html
<!DOCTYPE html>
<html>
<head><title>Software Engineer - TechCorp</title></head>
<body>
  <div id="app">
    <div class="container">
      <div class="row">
        <div class="col-12">
          <div class="job-header">
            <div class="company-info">
              <img src="techcorp-logo.png" class="logo" />
              <div>
                <h1 class="company-name">TechCorp</h1>
                <div class="company-meta">
                  <span>Technology</span> · <span>1000-5000 employees</span>
                </div>
              </div>
            </div>
          </div>

          <div class="job-posting">
            <h2 class="job-title">Senior Software Engineer</h2>
            <div class="job-meta">
              <span class="location">San Francisco, CA (Hybrid)</span>
              <span class="job-type">Full-time</span>
              <span class="experience">5+ years</span>
              <span class="posted">Posted 3 days ago</span>
            </div>

            <div class="salary-range">
              <strong>$150,000 - $200,000</strong> per year
            </div>

            <div class="job-description">
              <h3>About the Role</h3>
              <p>We're looking for a Senior Software Engineer to join our Platform team. You'll be building the core infrastructure that powers our products.</p>

              <h3>Requirements</h3>
              <ul>
                <li>5+ years of experience in software development</li>
                <li>Strong proficiency in Python or Go</li>
                <li>Experience with distributed systems</li>
                <li>BS/MS in Computer Science or equivalent</li>
              </ul>

              <h3>Benefits</h3>
              <ul>
                <li>Competitive salary and equity</li>
                <li>Health, dental, and vision insurance</li>
                <li>Unlimited PTO</li>
                <li>401(k) matching</li>
              </ul>
            </div>

            <button class="apply-btn" onclick="openModal()">Apply Now</button>
          </div>

          <script>
            function openModal() { /* ... */ }
            trackEvent('job_view', 'senior-swe');
          </script>
        </div>
      </div>
    </div>
  </div>
</body>
</html>
```

**Expected JSON:**
```json
{
  "type": "job_posting",
  "title": "Senior Software Engineer",
  "company": {
    "name": "TechCorp",
    "industry": "Technology",
    "size": "1000-5000 employees",
    "logo_url": "techcorp-logo.png"
  },
  "location": {
    "city": "San Francisco",
    "state": "CA",
    "remote_policy": "Hybrid"
  },
  "employment_type": "Full-time",
  "experience_required": "5+ years",
  "salary": {
    "min": 150000,
    "max": 200000,
    "currency": "USD",
    "period": "year"
  },
  "description": "We're looking for a Senior Software Engineer to join our Platform team. You'll be building the core infrastructure that powers our products.",
  "requirements": [
    "5+ years of experience in software development",
    "Strong proficiency in Python or Go",
    "Experience with distributed systems",
    "BS/MS in Computer Science or equivalent"
  ],
  "benefits": [
    "Competitive salary and equity",
    "Health, dental, and vision insurance",
    "Unlimited PTO",
    "401(k) matching"
  ],
  "posted_relative": "3 days ago"
}
```

---

### Example 7: Review Block (User-Generated Content)

**Input HTML:**
```html
<div class="reviews-container">
  <div class="reviews-header">
    <h2>Customer Reviews</h2>
    <div class="overall-rating">4.6 out of 5</div>
  </div>

  <div class="filters">
    <button>All</button>
    <button>5 star</button>
    <button>4 star</button>
  </div>

  <div class="review-item" data-review-id="r-28374">
    <div class="reviewer">
      <img src="avatars/user123.jpg" class="avatar" />
      <div>
        <span class="reviewer-name">Michael T.</span>
        <span class="verified">Verified Purchase</span>
      </div>
    </div>
    <div class="review-rating">
      <span class="stars">★★★★★</span>
      <span class="review-title">Exceeded my expectations!</span>
    </div>
    <div class="review-date">Reviewed on December 5, 2024</div>
    <div class="review-body">
      <p>I've been using this for 3 months now and it's been fantastic. The build quality is excellent and it works exactly as described. Battery life is amazing - I only charge it once a week with daily use.</p>
      <p>Only minor complaint is the app could be more intuitive, but it's not a dealbreaker.</p>
    </div>
    <div class="review-helpful">
      <span>47 people found this helpful</span>
      <button>Helpful</button>
      <button>Report</button>
    </div>
  </div>

  <div class="ad-banner">Sponsored: Check out similar products!</div>
</div>
```

**Expected JSON:**
```json
{
  "type": "review",
  "review_id": "r-28374",
  "reviewer": {
    "name": "Michael T.",
    "avatar_url": "avatars/user123.jpg",
    "verified_purchase": true
  },
  "rating": {
    "score": 5,
    "max": 5
  },
  "title": "Exceeded my expectations!",
  "date": "December 5, 2024",
  "body": "I've been using this for 3 months now and it's been fantastic. The build quality is excellent and it works exactly as described. Battery life is amazing - I only charge it once a week with daily use.\n\nOnly minor complaint is the app could be more intuitive, but it's not a dealbreaker.",
  "helpful_count": 47
}
```

---

### Example 8: Error Page (Negative Example)

**Input HTML:**
```html
<!DOCTYPE html>
<html>
<head>
  <title>Page Not Found - Example.com</title>
  <style>
    body { font-family: Arial; text-align: center; padding: 50px; }
    .error-code { font-size: 120px; color: #ccc; }
  </style>
</head>
<body>
  <div class="error-container">
    <div class="error-code">404</div>
    <h1>Oops! Page not found</h1>
    <p>The page you're looking for doesn't exist or has been moved.</p>
    <a href="/" class="home-link">Go back home</a>
  </div>

  <script>
    logError('404', window.location.pathname);
  </script>
</body>
</html>
```

**Expected JSON:**
```json
{
  "type": "error_page",
  "error_code": 404,
  "message": "Oops! Page not found",
  "description": "The page you're looking for doesn't exist or has been moved."
}
```

Note: The model should recognize this is NOT a data fragment and output minimal/typed response. This is a **negative example** - important for teaching the model what NOT to extract.

---

### Example 9: Login Wall (Negative Example)

**Input HTML:**
```html
<div class="auth-wall">
  <div class="blur-content">
    <!-- Content is blurred/hidden -->
    <div style="filter: blur(5px); pointer-events: none;">
      <h2>Premium Article Title</h2>
      <p>Lorem ipsum dolor sit amet consectetur...</p>
    </div>
  </div>

  <div class="login-prompt">
    <h2>Sign in to continue reading</h2>
    <p>This content is available to registered users only.</p>
    <form>
      <input type="email" placeholder="Email" />
      <input type="password" placeholder="Password" />
      <button type="submit">Sign In</button>
    </form>
    <p>Don't have an account? <a href="/signup">Sign up free</a></p>
  </div>
</div>
```

**Expected JSON:**
```json
{
  "type": "auth_required",
  "message": "Sign in to continue reading",
  "description": "This content is available to registered users only.",
  "content_available": false
}
```

Note: The model should NOT hallucinate the article content. It should recognize the auth wall and report that content is not available.

---

### Example 10: Empty SPA Shell (Negative Example)

**Input HTML:**
```html
<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>My React App</title>
  <link rel="stylesheet" href="/static/css/main.css">
</head>
<body>
  <noscript>You need to enable JavaScript to run this app.</noscript>
  <div id="root"></div>
  <script src="/static/js/bundle.js"></script>
  <script src="/static/js/main.chunk.js"></script>
</body>
</html>
```

**Expected JSON:**
```json
{
  "type": "empty_shell",
  "framework": "react",
  "content_available": false,
  "reason": "client_side_rendering"
}
```

Note: This is a SPA that requires JavaScript to render content. Raw HTML has no extractable data.

---

## Revised Task: What To Do Now

### Step 1: Define Your Schema (Do This First)

Create a document listing:
- What fragment types you'll support (product, event, recipe, job, review, contact, pricing, etc.)
- What fields each type has
- What negative types you'll include (error_page, auth_required, empty_shell)

This is your contract. The data collection serves the schema, not the other way around.

### Step 2: Collect/Generate Fragment Examples

For each fragment type:
1. Find or create 5-10 real HTML examples
2. Include varying levels of noise around the fragment
3. Include some malformed/messy HTML
4. Manually write the expected JSON for each

Target: 50-100 seed examples across all types.

### Step 3: Expand Synthetically

From your seed examples:
1. Vary the noise (add/remove surrounding elements)
2. Vary the structure (reorder elements, change class names)
3. Inject defects (missing tags, inconsistent formatting)
4. Generate variations with different data values

Target: 5,000 training examples total.

### Step 4: Proceed to Fine-Tuning

With a proper dataset:
1. Format for instruction fine-tuning
2. Train on Qwen 0.6B (or similar)
3. Evaluate on held-out test set
4. Analyze failure cases

---

## Summary

The core shift:
- **From**: Crawl pages → filter for quality → hope schema emerges
- **To**: Define schema → collect fragments with noise → expand deliberately

The model learns to find signal in noise. The dataset teaches it what signal looks like and what noise to ignore.

Your 469 HTML files aren't wasted - but they need to be processed differently. Instead of filtering to "best 50 pages," you should be extracting data-carrying fragments from within those pages, with their surrounding noise intact.
