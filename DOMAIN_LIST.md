# Domain List for Manual Fragment Collection

Based on the schemas defined in PROBLEM_STATEMENT_2.md, here are domains organized by fragment type for manual HTML collection.

**Note**: Use the Chrome Extension in `chrome-extension/` directory to easily collect and label HTML fragments from these domains. See `chrome-extension/README.md` for installation and usage instructions.

## Product Cards

- **amazon.com** - Various product pages
- **etsy.com** - Handmade/vintage items
- **ebay.com** - Auction listings
- **walmart.com** - Retail products
- **target.com** - Retail products
- **newegg.com** - Electronics
- **bestbuy.com** - Electronics
- **rei.com** - Outdoor gear
- **wayfair.com** - Furniture
- **shopify.com** - Independent stores

## Event Listings

- **eventbrite.com** - Event discovery
- **meetup.com** - Group events
- **ticketmaster.com** - Concert/sports tickets
- **stubhub.com** - Ticket resale
- **seatgeek.com** - Events and tickets
- **bandsintown.com** - Concert listings

## Contact/Person Cards

- **linkedin.com** - Professional profiles (team pages)
- **about.us pages** - Company team sections
- **university faculty pages** - Academic profiles
- **crunchbase.com** - Executive profiles
- **angellist.com** - Startup team pages

## Pricing Tables

- **stripe.com/pricing** - Payment processing
- **slack.com/pricing** - Collaboration tool
- **notion.so/pricing** - Productivity tool
- **github.com/pricing** - Code hosting
- **atlassian.com** - Various tools (Jira, Confluence)
- **hubspot.com/pricing** - Marketing software
- **mailchimp.com/pricing** - Email marketing
- **zoom.us/pricing** - Video conferencing
- **airtable.com/pricing** - Database tool

## Recipe Cards

- **allrecipes.com** - Community recipes
- **foodnetwork.com** - Chef recipes
- **seriouseats.com** - Tested recipes
- **bonappetit.com** - Magazine recipes
- **tasty.co** - Video recipes
- **cooking.nytimes.com** - NYT recipes
- **delish.com** - Quick recipes
- **bbcgoodfood.com** - UK recipes
- **inspiredtaste.net** - Food blog
- **loveandlemons.com** - Healthy recipes
- **recipetineats.com** - Australian blog

## Job Postings

- **linkedin.com/jobs** - Professional network
- **indeed.com** - Job aggregator
- **glassdoor.com** - Reviews + jobs
- **lever.co** - Startup job boards (jobs.lever.co/*)
- **greenhouse.io** - ATS job boards (boards.greenhouse.io/*)
- **workable.com** - Job board software
- **angellist.com** - Startup jobs
- **stackoverflow.com/jobs** - Developer jobs
- **ycombinator.com/jobs** - YC startup jobs

## Review Blocks

- **amazon.com** - Product reviews
- **yelp.com** - Business reviews
- **tripadvisor.com** - Travel reviews
- **trustpilot.com** - Company reviews
- **g2.com** - Software reviews
- **capterra.com** - Software reviews
- **producthunt.com** - Product reviews
- **imdb.com** - Movie reviews
- **goodreads.com** - Book reviews

## Article Metadata

- **medium.com** - Blog posts
- **dev.to** - Developer articles
- **substack.com** - Newsletter articles
- **blogs on company sites** - Various
- **news.ycombinator.com** (linked articles)
- **reddit.com** (linked articles)

## Negative Examples: Error Pages

Try any broken URL on major sites:
- **github.com/404**
- **stackoverflow.com/questions/99999999**
- **twitter.com/nonexistent**

## Negative Examples: Login Walls

- **nytimes.com** - Paywalled articles
- **wsj.com** - Subscription content
- **medium.com** - Member-only stories
- **bloomberg.com** - Premium content
- **ft.com** - Financial Times articles

## Negative Examples: SPA Shells

- **react.dev** - React docs (view source)
- **vuejs.org** - Vue docs
- **angular.io** - Angular docs
- Many modern web apps that heavily rely on JS

## Collection Strategy

### Pro Tips

1. **Use View Source, not Inspect**: Get the raw HTML delivered by the server, not the DOM after JS execution
2. **Look for RSS/API alternatives**: Some sites have cleaner structured data via feeds
3. **Check Schema.org markup**: Many sites already have JSON-LD that can guide your schema design
4. **Start with 2-3 domains per type**: You only need 50-100 base examples total
5. **Prioritize diversity**: Different HTML patterns matter more than volume from one site

### Target Metrics

- **50-100 seed examples** across all fragment types
- **5-10 real HTML examples** per fragment type
- **Varying levels of noise** around each fragment
- **Some malformed/messy HTML** for robustness
- **Manually written expected JSON** for each example

### Next Steps

1. Define exact JSON schemas for each fragment type
2. Collect 5-10 seed examples per type from these domains
3. Manually annotate the expected JSON output
4. Generate synthetic variations to reach 5,000 training examples
5. Proceed to fine-tuning
