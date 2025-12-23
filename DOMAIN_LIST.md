# Domain List for Automated Fragment Collection

**Priority Order**: Domains are ordered by auto-extraction accuracy (see `EXTRACTION_TEST_RESULTS.md`).

**High Priority** (90-100% auto-extraction) - Collect these first
**Medium Priority** (not yet tested) - Collect after validating high-priority schemas
**Lower Priority** (alternative schemas) - Defer or skip

**Note**: Use `scripts/auto_extract_annotations.py` for automated extraction from these domains. See `NEXT_STEPS.md` for usage instructions.

---

## Job Postings (100% Auto-Extraction Accuracy)

**Priority**: #1 - Perfect auto-extraction, abundant availability

- **jobs.lever.co** - Startup job boards (e.g., jobs.lever.co/anthropic, jobs.lever.co/stripe)
- **job-boards.greenhouse.io** - ATS job boards (e.g., boards.greenhouse.io/gitlab)
- **linkedin.com/jobs** - Professional network
- **indeed.com** - Job aggregator
- **glassdoor.com** - Reviews + jobs
- **workable.com** - Job board software
- **angellist.com** - Startup jobs
- **ycombinator.com/jobs** - YC startup jobs

---

## Recipe Cards (91% Auto-Extraction Accuracy)

**Priority**: #2 - Excellent auto-extraction, very high availability

- **allrecipes.com** - Community recipes (best coverage)
- **foodnetwork.com** - Chef recipes
- **tasty.co** - Video recipes
- **bbcgoodfood.com** - UK recipes

---

## Event Listings (90% Auto-Extraction Accuracy)

**Priority**: #3 - Excellent auto-extraction, high availability

- **eventbrite.com** - Event discovery (best coverage)
- **meetup.com** - Group events
- **livenation.sg** - Listings
- **sistic.com.sg** - Listings
- **catch.sg** - Listings

---

## Contact/Person Cards (Not Yet Tested)

**Priority**: #4 - Medium priority, test extraction first

- **linkedin.com** - Professional profiles (team pages)
- **university faculty pages** - Academic profiles
- **crunchbase.com** - Executive profiles
- **angellist.com** - Startup team pages

---

## Pricing Tables (Not Yet Tested)

**Priority**: #5 - Medium-low priority, complex nested structure

- **stripe.com/pricing** - Payment processing
- **slack.com/pricing** - Collaboration tool
- **notion.so/pricing** - Productivity tool
- **github.com/pricing** - Code hosting
- **atlassian.com** - Various tools (Jira, Confluence)
- **hubspot.com/pricing** - Marketing software
- **mailchimp.com/pricing** - Email marketing
- **zoom.us/pricing** - Video conferencing
- **airtable.com/pricing** - Database tool

---

## Product Cards (Alternative Schema - Lower Priority)

**Priority**: #6 - Not in core schema set, defer until later

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

---

## Review Blocks (Alternative Schema - Lower Priority)

**Priority**: #7 - Not in core schema set, defer until later

- **amazon.com** - Product reviews
- **yelp.com** - Business reviews
- **tripadvisor.com** - Travel reviews
- **trustpilot.com** - Company reviews
- **g2.com** - Software reviews
- **capterra.com** - Software reviews
- **producthunt.com** - Product reviews
- **imdb.com** - Movie reviews
- **goodreads.com** - Book reviews

---

## Article Metadata (Alternative Schema - Lower Priority)

**Priority**: #8 - Not in core schema set, defer until later

- **medium.com** - Blog posts
- **dev.to** - Developer articles
- **substack.com** - Newsletter articles
- **blogs on company sites** - Various
- **news.ycombinator.com** (linked articles)
- **reddit.com** (linked articles)

---

## Negative Examples: Error Pages

**Priority**: Include ~10 examples for robustness

Try any broken URL on major sites:
- **github.com/404**
- **stackoverflow.com/questions/99999999**
- **twitter.com/nonexistent**

---

## Negative Examples: Login Walls

**Priority**: Include ~10 examples for robustness

- **nytimes.com** - Paywalled articles
- **wsj.com** - Subscription content
- **medium.com** - Member-only stories
- **bloomberg.com** - Premium content
- **ft.com** - Financial Times articles

---

## Negative Examples: SPA Shells

**Priority**: Include ~10 examples for robustness

- **react.dev** - React docs (view source)
- **vuejs.org** - Vue docs
- **angular.io** - Angular docs
- Many modern web apps that heavily rely on JS

---

## Collection Strategy

### Automated Collection Workflow

1. **Focus on High-Priority Schemas First** (High Priority marked)
   - Job postings: 50 URLs (100% auto-extraction)
   - Recipes: 50 URLs (91% auto-extraction)
   - Events: 30 URLs (90% auto-extraction)

2. **Use Automated Script**:
   ```bash
   python scripts/auto_extract_annotations.py \
     --urls data/job_urls.txt \
     --schema job_posting \
     --output data/manual
   ```

3. **Manual Review Pass** (~1-2 hours for 130 examples)
   - Fix the ~5-10% errors
   - Clean up UI text artifacts
   - Verify all fields are correct

4. **Test Medium-Priority Schemas** (Medium Priority marked)
   - Run extraction on 5-10 examples first
   - Measure accuracy
   - If >70%, collect full 30-50 examples
   - If <70%, improve extraction logic first

5. **Generate Synthetic Variations**
   - Use existing pipeline: `scripts/04_generate.py`
   - Target 5,000 total training examples

### Target Metrics

- **130+ seed examples** from high-priority schemas (job, recipe, event)
- **90-100% auto-extraction accuracy** (validated)
- **1-2 hours manual review** instead of 20+ hours annotation
- **40x speedup** compared to manual collection

### Quick Start

See `NEXT_STEPS.md` for detailed instructions on:
1. Creating URL lists
2. Running automated extraction
3. Reviewing and fixing errors
4. Generating synthetic variations
5. Converting to chat format

### Why This Order Works

1. **Job postings (100%)** - Perfect extraction, build confidence
2. **Recipes (91%)** - Excellent extraction, easy to find
3. **Events (90%)** - Excellent extraction, good availability
4. **Person/Contact** - Test next, may need extraction tuning
5. **Pricing tables** - Complex structure, test after simpler schemas
6. **Product/Review/Article** - Alternative schemas, defer until core schemas complete
7. **Negative examples** - Small set needed for robustness (~10 each)
