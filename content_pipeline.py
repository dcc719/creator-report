"""
Creator Report — Content Pipeline
Generates, queues, and publishes articles using Claude.

Modes:
  --generate          Generate articles from editorial calendar or trending topics
  --approve <slug>    Approve a queued article for publishing
  --list-queue        Show pending articles awaiting approval
  --publish-approved  Publish all approved articles to the live site
  --breaking "topic"  Generate a breaking news article immediately (still needs approval)

Requires: ANTHROPIC_API_KEY env var (or .env file)
"""

import os
import sys
import json
import uuid
import argparse
import re
from datetime import datetime, timedelta
from pathlib import Path

try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

try:
    import anthropic
except ImportError:
    print("Missing anthropic package. Run: pip install anthropic")
    sys.exit(1)

try:
    import requests
except ImportError:
    print("Missing requests package. Run: pip install requests")
    sys.exit(1)

# --- Config ---
BASE_DIR = Path(__file__).parent
DATA_DIR = BASE_DIR / "data"
QUEUE_DIR = DATA_DIR / "queue"
ARTICLES_FILE = DATA_DIR / "articles.json"
CALENDAR_FILE = DATA_DIR / "editorial_calendar.json"
PUBLISHED_LOG = DATA_DIR / "published_log.json"

ANTHROPIC_API_KEY = os.environ.get("ANTHROPIC_API_KEY", "")
CR_API_URL = os.environ.get("CR_API_URL", "https://thecreatorreport.co")

# Unsplash images by category (pre-verified working IDs)
CATEGORY_IMAGES = {
    "platform-news": [
        "photo-1611162617213-7d7a39e9b1d7",
        "photo-1611605698335-8b1569810432",
        "photo-1620712943543-bcc4688e7485",
    ],
    "creator-stories": [
        "photo-1526304640581-d334cdbbf45e",
        "photo-1470229722913-7c0e2dbbafd3",
        "photo-1529156069898-49953e39b3ac",
    ],
    "money": [
        "photo-1460925895917-afdab827c52f",
        "photo-1579621970563-ebec7560ff3e",
        "photo-1554224155-6726b3ff858f",
    ],
    "trends": [
        "photo-1504711434969-e33886168d9c",
        "photo-1542744173-8e7e53415bb0",
        "photo-1451187580459-43490279c0fa",
    ],
    "legal": [
        "photo-1589829545856-d10d557cf95f",
        "photo-1507679799987-c73779587ccf",
        "photo-1436450412740-6b988f486c6b",
    ],
    "tools": [
        "photo-1519389950473-47ba0277781c",
        "photo-1488590528505-98d2b5aba04b",
        "photo-1550751827-4bd374c3f58b",
    ],
    "opinion": [
        "photo-1504711434969-e33886168d9c",
        "photo-1506126613408-eca07ce68773",
        "photo-1523240795612-9a054b0db644",
    ],
}

# Author personas (no Drew — per his rules)
AUTHORS = [
    "Maya Torres",
    "James Chen",
    "Priya Kapoor",
    "Alex Rivera",
    "Sarah Kim",
]

SYSTEM_PROMPT = """You are a senior editorial writer for The Creator Report, a premium publication covering the creator economy. Your writing style:

- Sharp, confident, no-fluff journalism. Think Bloomberg meets The Information.
- Lead with the most interesting fact or insight, not background.
- Use real data points when available. If speculating, be honest about it.
- No em dashes. Use commas, periods, or " - " instead.
- No AI-sounding words: avoid "leverage", "facilitate", "comprehensive", "robust", "crucial", "essential", "landscape", "navigate" (metaphorically), "furthermore", "moreover", "myriad", "delve", "empower", "pivotal", "realm", "unlock".
- Use contractions naturally. Write like a smart journalist, not a press release.
- Short paragraphs. Mix sentence lengths.
- Include specific numbers, names, and platforms whenever possible.
- Content should genuinely inform the reader, not just fill space.
- Articles should be 800-1500 words.
- NEVER mention Vault or any agency by name. The site funnels to Vault subtly through design, not through articles.

You MUST respond with valid JSON in this exact format:
{
  "title": "Article headline - punchy, specific, under 80 chars",
  "subtitle": "One sentence expanding on the headline",
  "category": "one of: platform-news, creator-stories, money, trends, legal, tools, opinion",
  "content_md": "Full article in markdown. Use ## for subheadings. Use > for quotes. Use **bold** sparingly.",
  "meta_title": "SEO title under 60 chars",
  "meta_description": "SEO description under 155 chars",
  "pull_quotes": ["1-3 compelling pull quotes from the article"],
  "key_stats": [{"value": "$X", "label": "description"}, ...],
  "tags": ["tag1", "tag2", "tag3", "tag4", "tag5"],
  "read_time_minutes": 5,
  "faq_items": [{"question": "Q?", "answer": "A."}, ...]
}"""


def load_json(path, default=None):
    if default is None:
        default = []
    if path.exists():
        with open(path) as f:
            return json.load(f)
    return default


def save_json(path, data):
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w") as f:
        json.dump(data, f, indent=2)


def get_existing_slugs():
    articles = load_json(ARTICLES_FILE)
    return {a["slug"] for a in articles}


def pick_image(category):
    import random
    images = CATEGORY_IMAGES.get(category, CATEGORY_IMAGES["trends"])
    img_id = random.choice(images)
    return f"https://images.unsplash.com/{img_id}?w=1200&h=630&fit=crop&q=80"


def pick_author():
    import random
    return random.choice(AUTHORS)


def generate_slug(title):
    slug = title.lower().strip()
    slug = re.sub(r"[^a-z0-9\s-]", "", slug)
    slug = re.sub(r"[\s]+", "-", slug)
    slug = re.sub(r"-+", "-", slug).strip("-")
    return slug[:80]


def generate_article(topic, category_hint=None):
    """Generate an article using Claude."""
    if not ANTHROPIC_API_KEY:
        print("Error: ANTHROPIC_API_KEY not set")
        sys.exit(1)

    client = anthropic.Anthropic(api_key=ANTHROPIC_API_KEY)

    prompt = f"""Write an article about: {topic}

Today's date is {datetime.now().strftime('%B %d, %Y')}.

{"Suggested category: " + category_hint if category_hint else "Pick the most appropriate category."}

Remember: respond with ONLY valid JSON, no markdown code fences."""

    response = client.messages.create(
        model="claude-sonnet-4-20250514",
        max_tokens=4096,
        system=SYSTEM_PROMPT,
        messages=[{"role": "user", "content": prompt}],
    )

    text = response.content[0].text.strip()
    # Strip markdown code fences if present
    if text.startswith("```"):
        text = re.sub(r"^```\w*\n?", "", text)
        text = re.sub(r"\n?```$", "", text)

    try:
        article_data = json.loads(text)
    except json.JSONDecodeError:
        print(f"Failed to parse Claude response as JSON:")
        print(text[:500])
        return None

    # Build full article object
    slug = generate_slug(article_data["title"])
    category = article_data.get("category", category_hint or "trends")
    author = pick_author()

    article = {
        "id": str(uuid.uuid4()),
        "slug": slug,
        "title": article_data["title"],
        "subtitle": article_data.get("subtitle", ""),
        "category": category,
        "author": author,
        "published_date": datetime.now().strftime("%Y-%m-%d"),
        "updated_date": datetime.now().strftime("%Y-%m-%d"),
        "content_html": "",  # Will be converted server-side from content_md
        "content_md": article_data.get("content_md", ""),
        "meta_title": article_data.get("meta_title", article_data["title"][:60]),
        "meta_description": article_data.get("meta_description", ""),
        "hero_image": pick_image(category),
        "hero_image_alt": f"Illustration for {article_data['title']}",
        "hero_image_credit": "Unsplash",
        "pull_quotes": article_data.get("pull_quotes", []),
        "key_stats": article_data.get("key_stats", []),
        "tags": article_data.get("tags", []),
        "read_time_minutes": article_data.get("read_time_minutes", 5),
        "faq_items": article_data.get("faq_items", []),
        "related_articles": [],
        "status": "draft",
        "views": 0,
        "cta_clicks": 0,
        "inline_images": [],
    }

    return article


def queue_article(article):
    """Save article to approval queue."""
    QUEUE_DIR.mkdir(parents=True, exist_ok=True)
    filepath = QUEUE_DIR / f"{article['slug']}.json"
    article["queued_at"] = datetime.now().isoformat()
    article["approved"] = False
    save_json(filepath, article)
    return filepath


def list_queue():
    """List all queued articles."""
    if not QUEUE_DIR.exists():
        print("No articles in queue.")
        return

    files = sorted(QUEUE_DIR.glob("*.json"))
    if not files:
        print("No articles in queue.")
        return

    for f in files:
        article = load_json(f, {})
        status = "APPROVED" if article.get("approved") else "PENDING"
        print(f"  [{status}] {article.get('slug', f.stem)}")
        print(f"           {article.get('title', 'No title')}")
        print(f"           Category: {article.get('category')} | Author: {article.get('author')}")
        print(f"           Queued: {article.get('queued_at', 'unknown')}")
        print()


def approve_article(slug):
    """Mark a queued article as approved."""
    filepath = QUEUE_DIR / f"{slug}.json"
    if not filepath.exists():
        print(f"Article '{slug}' not found in queue.")
        return False

    article = load_json(filepath, {})
    article["approved"] = True
    article["approved_at"] = datetime.now().isoformat()
    save_json(filepath, article)
    print(f"Approved: {article.get('title', slug)}")
    return True


def publish_to_local(article):
    """Publish article directly to local articles.json."""
    articles = load_json(ARTICLES_FILE)

    # Check for duplicate slugs
    existing = {a["slug"] for a in articles}
    if article["slug"] in existing:
        print(f"  Slug '{article['slug']}' already exists, skipping.")
        return False

    article["status"] = "published"
    article.pop("queued_at", None)
    article.pop("approved", None)
    article.pop("approved_at", None)

    articles.insert(0, article)  # Newest first
    save_json(ARTICLES_FILE, articles)
    return True


def publish_approved():
    """Publish all approved articles."""
    if not QUEUE_DIR.exists():
        print("No articles in queue.")
        return

    files = sorted(QUEUE_DIR.glob("*.json"))
    published = 0

    for f in files:
        article = load_json(f, {})
        if not article.get("approved"):
            continue

        if publish_to_local(article):
            print(f"  Published: {article.get('title', f.stem)}")
            # Log it
            log = load_json(PUBLISHED_LOG)
            log.append({
                "slug": article["slug"],
                "title": article["title"],
                "published_at": datetime.now().isoformat(),
            })
            save_json(PUBLISHED_LOG, log)

            # Remove from queue
            f.unlink()
            published += 1

    if published:
        print(f"\n{published} article(s) published to articles.json.")
        print("Push to GitHub to deploy: cd ~/ai-systems && git add -A && git commit -m 'new articles' && git push origin main")
    else:
        print("No approved articles to publish.")


def load_calendar():
    """Load editorial calendar."""
    return load_json(CALENDAR_FILE, [])


def generate_from_calendar():
    """Generate articles scheduled for today or overdue."""
    calendar = load_calendar()
    today = datetime.now().strftime("%Y-%m-%d")
    existing = get_existing_slugs()
    generated = 0

    for item in calendar:
        if item.get("generated"):
            continue
        if item.get("scheduled_date", "") > today:
            continue

        topic = item["topic"]
        print(f"Generating: {topic}")

        article = generate_article(topic, item.get("category"))
        if article:
            filepath = queue_article(article)
            print(f"  Queued: {filepath.name}")
            item["generated"] = True
            item["generated_at"] = datetime.now().isoformat()
            item["slug"] = article["slug"]
            generated += 1

    # Save updated calendar
    save_json(CALENDAR_FILE, calendar)
    return generated


def seed_calendar():
    """Create a starter editorial calendar if none exists."""
    if CALENDAR_FILE.exists():
        cal = load_json(CALENDAR_FILE)
        if cal:
            print("Editorial calendar already has entries.")
            return

    today = datetime.now()
    topics = [
        {"topic": "How creator agencies actually make money in 2026 - the real revenue splits and economics", "category": "money"},
        {"topic": "TikTok's creator fund is dead, what replaced it, and whether it's actually better", "category": "platform-news"},
        {"topic": "The rise of faceless creator accounts and why they're outearning traditional influencers", "category": "trends"},
        {"topic": "What happens when a top creator leaves their management agency - the messy reality", "category": "creator-stories"},
        {"topic": "OnlyFans vs Fansly in 2026: which platform actually pays creators more", "category": "platform-news"},
        {"topic": "How to structure an LLC as a content creator - state by state breakdown for 2026", "category": "legal"},
        {"topic": "The AI content creation tools that are actually worth paying for in 2026", "category": "tools"},
        {"topic": "Why 90% of creators who hire agencies quit within 6 months", "category": "opinion"},
        {"topic": "Instagram's new subscription features and what they mean for creator revenue", "category": "platform-news"},
        {"topic": "The tax mistakes that cost creators thousands every year", "category": "money"},
        {"topic": "How micro-influencers (under 50K followers) are building six-figure businesses", "category": "creator-stories"},
        {"topic": "The DMCA crisis: how content theft is costing adult creators millions", "category": "legal"},
        {"topic": "YouTube Shorts vs TikTok vs Reels - which short-form platform pays best in 2026", "category": "platform-news"},
        {"topic": "The creator middle class is disappearing and here's the data to prove it", "category": "trends"},
    ]

    calendar = []
    for i, item in enumerate(topics):
        scheduled = (today + timedelta(days=i * 2 + 1)).strftime("%Y-%m-%d")
        calendar.append({
            "topic": item["topic"],
            "category": item["category"],
            "scheduled_date": scheduled,
            "generated": False,
        })

    save_json(CALENDAR_FILE, calendar)
    print(f"Created editorial calendar with {len(calendar)} topics.")
    print(f"First article scheduled: {calendar[0]['scheduled_date']}")
    print(f"Last article scheduled: {calendar[-1]['scheduled_date']}")


# --- CLI ---

def main():
    parser = argparse.ArgumentParser(description="Creator Report Content Pipeline")
    parser.add_argument("--generate", action="store_true", help="Generate articles from calendar")
    parser.add_argument("--breaking", type=str, help="Generate breaking news article on a topic")
    parser.add_argument("--approve", type=str, help="Approve a queued article by slug")
    parser.add_argument("--approve-all", action="store_true", help="Approve all queued articles")
    parser.add_argument("--list-queue", action="store_true", help="List queued articles")
    parser.add_argument("--publish", action="store_true", help="Publish approved articles")
    parser.add_argument("--seed-calendar", action="store_true", help="Create starter editorial calendar")
    parser.add_argument("--topic", type=str, help="Generate a single article on a specific topic")
    parser.add_argument("--category", type=str, help="Category hint for --topic or --breaking")

    args = parser.parse_args()

    if args.seed_calendar:
        seed_calendar()
    elif args.generate:
        n = generate_from_calendar()
        print(f"\nGenerated {n} article(s).")
    elif args.breaking:
        print(f"Generating breaking article: {args.breaking}")
        article = generate_article(args.breaking, args.category)
        if article:
            filepath = queue_article(article)
            print(f"Queued for approval: {filepath.name}")
            print(f"Title: {article['title']}")
            print(f"\nTo approve: python content_pipeline.py --approve {article['slug']}")
    elif args.topic:
        print(f"Generating article: {args.topic}")
        article = generate_article(args.topic, args.category)
        if article:
            filepath = queue_article(article)
            print(f"Queued for approval: {filepath.name}")
            print(f"Title: {article['title']}")
    elif args.approve:
        approve_article(args.approve)
    elif args.approve_all:
        if not QUEUE_DIR.exists():
            print("No articles in queue.")
            return
        for f in QUEUE_DIR.glob("*.json"):
            article = load_json(f, {})
            if not article.get("approved"):
                approve_article(f.stem)
    elif args.list_queue:
        list_queue()
    elif args.publish:
        publish_approved()
    else:
        parser.print_help()


if __name__ == "__main__":
    main()
