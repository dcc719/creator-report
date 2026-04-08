# The Creator Report — CONTEXT.md

## Project Overview

The Creator Report is the definitive editorial and journalistic resource on the OnlyFans industry and creator economy. It's the SEO/AEO force multiplier for the entire Onyx ecosystem — every article, every piece of content drives traffic toward Vault (recruiting), toward agency brands, and toward all Onyx properties.

**Status:** Not yet built. This is a net-new project on the Austin critical path.

**Target URL:** TBD (thecreator.report, thecreatorreport.com, or similar)

## Why This Exists

Two strategic purposes:
1. **Traffic engine** — SEO/AEO optimized content that drives organic traffic to Vault. When creators Google "best OnlyFans management agencies" or ask ChatGPT "should I get an OnlyFans manager," The Creator Report should be the answer.
2. **Authority positioning** — Establishes Drew/Onyx as the thought leader in the creator economy space. This isn't a blog — it's THE resource.

## What It Needs to Be by Austin (May 3, 2026)

### Minimum Viable Product
- Live content site with professional editorial design
- 20-50+ articles covering core creator economy topics
- SEO fundamentals: proper meta tags, schema markup, sitemap, robots.txt
- AEO optimization: content structured for AI search engines (Perplexity, ChatGPT Browse, Google AI Overviews)
- Claude API powering content generation at scale
- Clear CTAs driving to Vault on every page
- Social sharing optimized (OG tags, Twitter cards)
- Analytics tracking (Google Analytics or equivalent)
- Mobile responsive

### Content Strategy
Topics that creators and industry people actually search for:
- "How to start on OnlyFans" / getting started guides
- Agency management explainers (what agencies do, how to pick one)
- Revenue optimization strategies
- Content creation best practices
- Platform comparisons (OnlyFans vs Fansly vs others)
- Creator rights and protection (DMCA, content theft)
- Tax and financial guidance for creators
- Social media growth strategies for creators
- Industry news and trends
- Success stories and case studies

### SEO/AEO Architecture
- Each article targets a specific keyword cluster
- Internal linking strategy connecting related articles
- Schema markup: Article, FAQPage, HowTo, Organization
- Structured data for AI consumption
- Fast load times (critical for SEO)
- Clean URLs: `/articles/how-to-start-onlyfans-management`

### Design Requirements
- Editorial/magazine feel — not a generic blog template
- Premium, authoritative design that matches the caliber of content
- Category navigation (Getting Started, Growth, Business, Protection, News)
- Featured/trending articles section
- Newsletter signup (future email marketing funnel)
- "Managed by Vault" or similar subtle branding linking to Vault

## Technical Architecture (Recommended)

### Option A: Static Site Generator (Recommended for speed)
- **Build:** Python script using Claude API to generate articles → renders to static HTML
- **Deploy:** Netlify, Vercel, or GitHub Pages (free, fast, reliable)
- **Pros:** Blazing fast, zero server costs, excellent SEO, easy to scale
- **Cons:** No dynamic features without JavaScript

### Option B: Flask App (Consistent with other tools)
- **Build:** Flask + JSON/SQLite for articles, Claude API for generation
- **Deploy:** Heroku (same as Vault)
- **Pros:** Consistent stack, dynamic features, admin panel possible
- **Cons:** Server costs, slower than static

### Option C: Hybrid
- Static site for public-facing content (speed + SEO)
- Flask admin panel for content management and generation
- Best of both worlds

### Content Generation Pipeline
```
Topic Research → Claude API generates article draft → Human review/edit →
SEO optimization pass → Publish to site → Social distribution →
Analytics tracking → Feed insights back to Vault
```

## Integration Points

- **Vault:** Every article has CTAs driving to Vault application. UTM-tagged links for tracking.
- **Waves:** Traffic and conversion data flows into Waves analytics. Creator leads from Creator Report tracked as source.
- **AASMA (future):** AASMA powers social media distribution of Creator Report content
- **Vault apply form:** "How did you find us?" includes "The Creator Report" option (already exists)

## Content Volume Target

**By Austin:** 20-50 articles minimum. Enough to look like an established resource, not a new blog.

**Ongoing:** Claude API can generate 5-10 articles per day with human oversight. The goal is to become the highest-volume, highest-quality creator economy publication.

## File Structure (Proposed)

```
creator-report/
├── CONTEXT.md              # This file
├── app.py                  # Flask admin/generator (if using Option B/C)
├── generator/
│   ├── generate.py         # Claude API article generation
│   ├── seo_optimizer.py    # SEO pass on generated content
│   └── templates/          # Article HTML templates
├── content/
│   ├── articles/           # Generated article files (markdown or HTML)
│   └── metadata.json       # Article index, categories, tags, publish dates
├── site/
│   ├── index.html          # Homepage
│   ├── articles/           # Published article pages
│   ├── categories/         # Category listing pages
│   └── static/             # CSS, JS, images
├── data/
│   └── analytics.json      # Traffic/conversion tracking
└── requirements.txt
```

## Dependencies (Expected)
```
anthropic          # Claude API for content generation
flask              # If using Option B/C
markdown           # Markdown → HTML conversion
jinja2             # Templating
```

## Environment
`.env` file (never commit):
```
ANTHROPIC_API_KEY=sk-...
```

---

**Last updated:** 2026-04-03
**Status:** Not yet built — Austin sprint critical path
**Priority:** Must be live with 20-50+ articles by May 3, 2026
**Build order:** After Vault rebuild begins, can be built in parallel
