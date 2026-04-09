"""
The Creator Report — Editorial resource on the creator economy.
Drives organic traffic to Vault (vaultplacement.com).
"""

import json
import os
import uuid
from datetime import datetime, timezone
from functools import wraps

from flask import (
    Flask, render_template, request, jsonify, abort, Response, url_for,
    session, redirect, flash
)

app = Flask(__name__)
app.secret_key = os.environ.get("SECRET_KEY", "creator-report-dev-key")

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_DIR = os.path.join(BASE_DIR, "data")
ARTICLES_FILE = os.path.join(DATA_DIR, "articles.json")
ANALYTICS_FILE = os.path.join(DATA_DIR, "analytics.json")

DOMAIN = "thecreatorreport.co"
SITE_URL = f"https://{DOMAIN}"

CATEGORIES = {
    "platform-news": {"name": "Platform News", "description": "Updates, policy changes, and algorithm shifts across major creator platforms"},
    "creator-stories": {"name": "Creator Stories", "description": "Real journeys, income breakdowns, and career transitions"},
    "money": {"name": "Money", "description": "Revenue strategies, tax playbooks, and financial planning for creators"},
    "trends": {"name": "Trends", "description": "Industry shifts, cultural movements, and data-driven analysis"},
    "legal": {"name": "Legal", "description": "Copyright, contracts, privacy, and the regulation landscape"},
    "tools": {"name": "Tools", "description": "Tech, apps, equipment, and workflows that power creator businesses"},
    "opinion": {"name": "Opinion", "description": "Sharp takes, industry commentary, and predictions"},
}

# ---------------------------------------------------------------------------
# Admin auth
# ---------------------------------------------------------------------------

ADMIN_USER = os.environ.get("CR_ADMIN_USER", "admin")
ADMIN_PASS = os.environ.get("CR_ADMIN_PASS", "changeme")

QUEUE_DIR = os.path.join(DATA_DIR, "queue")


def admin_required(f):
    @wraps(f)
    def wrapped(*args, **kwargs):
        if not session.get("admin"):
            return redirect(url_for("admin_login"))
        return f(*args, **kwargs)
    return wrapped


# ---------------------------------------------------------------------------
# Markdown converter
# ---------------------------------------------------------------------------

def markdown_to_html(md):
    """Simple markdown-to-HTML converter for basic formatting."""
    if not md:
        return ""

    html = md

    # Blockquotes
    html = html.replace("\n> ", "\n<blockquote>")
    html = html.replace("> ", "<blockquote>")
    # Close blockquotes at line breaks
    lines = html.split("\n")
    result = []
    in_blockquote = False
    for line in lines:
        if line.startswith("<blockquote>"):
            if not in_blockquote:
                in_blockquote = True
            result.append(line)
        else:
            if in_blockquote and line.strip():
                result.append("</blockquote>\n" + line)
                in_blockquote = False
            else:
                result.append(line)
    if in_blockquote:
        result.append("</blockquote>")
    html = "\n".join(result)

    # Headers
    html = html.replace("\n### ", "\n<h3>")
    html = html.replace("### ", "<h3>")
    html = html.replace("\n## ", "\n<h2>")
    html = html.replace("## ", "<h2>")

    # Bold and italic
    html = html.replace("**", "<strong>")
    html = html.replace("*", "<em>")

    # Lines
    html = html.replace("\n- ", "\n<li>")
    html = html.replace("- ", "<li>")

    # Links
    import re
    html = re.sub(r'\[([^\]]+)\]\(([^)]+)\)', r'<a href="\2">\1</a>', html)

    # Paragraphs
    paras = html.split("\n\n")
    paras = [f"<p>{p}</p>" if p.strip() and not p.strip().startswith("<") else p for p in paras]
    html = "\n".join(paras)

    return html


# ---------------------------------------------------------------------------
# Data helpers
# ---------------------------------------------------------------------------

def load_json(path, default=None):
    if default is None:
        default = []
    try:
        with open(path, "r") as f:
            return json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        return default


def save_json(path, data):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w") as f:
        json.dump(data, f, indent=2, default=str)


def get_articles():
    return load_json(ARTICLES_FILE, [])


def save_articles(articles):
    save_json(ARTICLES_FILE, articles)


def get_article_by_slug(slug):
    for a in get_articles():
        if a.get("slug") == slug:
            return a
    return None


def get_articles_by_category(category):
    return [a for a in get_articles() if a.get("category") == category and a.get("status") == "published"]


def get_published_articles():
    articles = [a for a in get_articles() if a.get("status") == "published"]
    articles.sort(key=lambda a: a.get("published_date", ""), reverse=True)
    return articles


# ---------------------------------------------------------------------------
# Template context
# ---------------------------------------------------------------------------

@app.context_processor
def inject_globals():
    return {
        "categories": CATEGORIES,
        "site_url": SITE_URL,
        "domain": DOMAIN,
        "current_year": datetime.now().year,
        "vault_base": "https://vaultplacement.com/apply",
    }


# ---------------------------------------------------------------------------
# Page routes
# ---------------------------------------------------------------------------

@app.route("/")
def home():
    articles = get_published_articles()
    featured = articles[0] if articles else None
    latest = articles[:4]  # 4 most recent articles
    by_cat = {}
    for cat_slug in CATEGORIES:
        by_cat[cat_slug] = [a for a in articles if a.get("category") == cat_slug][:4]
    return render_template("home.html", featured=featured, latest=latest, by_category=by_cat, articles=articles)


@app.route("/category/<slug>")
def category_page(slug):
    if slug not in CATEGORIES:
        abort(404)
    articles = get_articles_by_category(slug)
    articles.sort(key=lambda a: a.get("published_date", ""), reverse=True)
    return render_template("category.html", category_slug=slug, category=CATEGORIES[slug], articles=articles)


@app.route("/article/<slug>")
def article_page(slug):
    article = get_article_by_slug(slug)
    if not article or article.get("status") != "published":
        abort(404)
    # Increment views
    articles = get_articles()
    for a in articles:
        if a["slug"] == slug:
            a["views"] = a.get("views", 0) + 1
            break
    save_articles(articles)
    # Gather related
    related = []
    for rs in article.get("related_articles", []):
        ra = get_article_by_slug(rs)
        if ra:
            related.append(ra)
    return render_template("article.html", article=article, related=related)


@app.route("/about")
def about():
    return render_template("about.html")


# ---------------------------------------------------------------------------
# Comments
# ---------------------------------------------------------------------------

COMMENTS_FILE = os.path.join(DATA_DIR, "comments.json")

def load_comments():
    if os.path.exists(COMMENTS_FILE):
        with open(COMMENTS_FILE, "r") as f:
            return json.load(f)
    return {}

def save_comments(data):
    with open(COMMENTS_FILE, "w") as f:
        json.dump(data, f, indent=2)

@app.route("/api/comments/<slug>", methods=["GET"])
def get_comments(slug):
    comments = load_comments()
    return jsonify({"comments": comments.get(slug, [])})

@app.route("/api/comments/<slug>", methods=["POST"])
def post_comment(slug):
    data = request.get_json() or {}
    name = data.get("name", "").strip()[:50]
    text = data.get("text", "").strip()[:1000]
    if not name or not text:
        return jsonify({"error": "Name and comment required"}), 400

    comments = load_comments()
    if slug not in comments:
        comments[slug] = []

    comment = {
        "id": str(uuid.uuid4())[:8],
        "name": name,
        "text": text,
        "date": datetime.now(timezone.utc).strftime("%b %d, %Y"),
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }
    comments[slug].append(comment)
    save_comments(comments)
    return jsonify({"ok": True, "comment": comment})

# ---------------------------------------------------------------------------
# Sitemap
# ---------------------------------------------------------------------------

@app.route("/sitemap.xml")
def sitemap():
    articles = get_published_articles()
    xml = ['<?xml version="1.0" encoding="UTF-8"?>']
    xml.append('<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">')
    # Homepage
    xml.append(f"  <url><loc>{SITE_URL}/</loc><changefreq>daily</changefreq><priority>1.0</priority></url>")
    # About
    xml.append(f"  <url><loc>{SITE_URL}/about</loc><changefreq>monthly</changefreq><priority>0.5</priority></url>")
    # Categories
    for slug in CATEGORIES:
        xml.append(f"  <url><loc>{SITE_URL}/category/{slug}</loc><changefreq>weekly</changefreq><priority>0.8</priority></url>")
    # Articles
    for a in articles:
        lastmod = a.get("updated_date") or a.get("published_date", "")
        xml.append(f'  <url><loc>{SITE_URL}/article/{a["slug"]}</loc><lastmod>{lastmod}</lastmod><changefreq>monthly</changefreq><priority>0.9</priority></url>')
    xml.append("</urlset>")
    return Response("\n".join(xml), mimetype="application/xml")


@app.route("/robots.txt")
def robots():
    return Response(
        "User-agent: *\nAllow: /\nSitemap: https://thecreatorreport.co/sitemap.xml\n",
        mimetype="text/plain"
    )


@app.route("/og-image")
def og_image():
    """Serve dynamic OG image as SVG (lightweight, no dependencies)."""
    svg = '''<?xml version="1.0" encoding="UTF-8"?>
<svg width="1200" height="630" xmlns="http://www.w3.org/2000/svg">
  <!-- Background -->
  <rect width="1200" height="630" fill="#0a0a0a"/>
  <!-- Accent bar -->
  <rect width="1200" height="8" fill="#e63946"/>
  <!-- Text -->
  <text x="600" y="280" font-size="80" font-weight="bold" text-anchor="middle" fill="#ffffff" font-family="Georgia, serif">The Creator Report</text>
  <text x="600" y="380" font-size="40" text-anchor="middle" fill="#aaaaaa" font-family="system-ui, sans-serif">Creator Economy Intelligence</text>
</svg>'''
    return Response(svg, mimetype="image/svg+xml")


# ---------------------------------------------------------------------------
# API routes
# ---------------------------------------------------------------------------

@app.route("/api/articles", methods=["GET"])
def api_articles():
    articles = get_published_articles()
    category = request.args.get("category")
    if category:
        articles = [a for a in articles if a.get("category") == category]
    # Return without content_html to keep response light
    light = []
    for a in articles:
        item = {k: v for k, v in a.items() if k != "content_html"}
        light.append(item)
    return jsonify(light)


@app.route("/api/articles/<slug>", methods=["GET"])
def api_article(slug):
    article = get_article_by_slug(slug)
    if not article:
        return jsonify({"error": "Not found"}), 404
    return jsonify(article)


@app.route("/api/articles", methods=["POST"])
def api_create_article():
    data = request.get_json()
    if not data or not data.get("title"):
        return jsonify({"error": "Title is required"}), 400

    slug = data.get("slug") or data["title"].lower().replace(" ", "-").replace("'", "")
    slug = "".join(c for c in slug if c.isalnum() or c == "-")

    # Handle content_html vs content_md
    content_html = data.get("content_html", "")
    if not content_html and data.get("content_md"):
        content_html = markdown_to_html(data["content_md"])

    article = {
        "id": str(uuid.uuid4()),
        "slug": slug,
        "title": data["title"],
        "subtitle": data.get("subtitle", ""),
        "category": data.get("category", "platform-news"),
        "author": data.get("author", "The Creator Report"),
        "published_date": data.get("published_date", datetime.now().strftime("%Y-%m-%d")),
        "updated_date": data.get("updated_date", datetime.now().strftime("%Y-%m-%d")),
        "content_html": content_html,
        "content_md": data.get("content_md", ""),
        "meta_title": data.get("meta_title", data["title"][:60]),
        "meta_description": data.get("meta_description", ""),
        "hero_image_alt": data.get("hero_image_alt", ""),
        "pull_quotes": data.get("pull_quotes", []),
        "key_stats": data.get("key_stats", []),
        "tags": data.get("tags", []),
        "read_time_minutes": data.get("read_time_minutes", 5),
        "faq_items": data.get("faq_items", []),
        "related_articles": data.get("related_articles", []),
        "status": data.get("status", "published"),
        "views": 0,
        "cta_clicks": 0,
    }

    articles = get_articles()
    articles.append(article)
    save_articles(articles)
    return jsonify(article), 201


@app.route("/api/track", methods=["POST"])
def api_track():
    data = request.get_json()
    if not data or not data.get("event"):
        return jsonify({"error": "Event type required"}), 400

    event = {
        "id": str(uuid.uuid4()),
        "event": data["event"],
        "slug": data.get("slug", ""),
        "category": data.get("category", ""),
        "value": data.get("value", ""),
        "utm_source": data.get("utm_source", ""),
        "utm_medium": data.get("utm_medium", ""),
        "utm_campaign": data.get("utm_campaign", ""),
        "referrer": data.get("referrer", ""),
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "user_agent": request.headers.get("User-Agent", ""),
    }

    analytics = load_json(ANALYTICS_FILE, {"events": []})
    analytics["events"].append(event)
    save_json(ANALYTICS_FILE, analytics)

    # If it's a CTA click, increment on the article
    if data["event"] == "cta_click" and data.get("slug"):
        articles = get_articles()
        for a in articles:
            if a["slug"] == data["slug"]:
                a["cta_clicks"] = a.get("cta_clicks", 0) + 1
                break
        save_articles(articles)

    return jsonify({"ok": True}), 200


@app.route("/api/analytics/summary", methods=["GET"])
def api_analytics_summary():
    analytics = load_json(ANALYTICS_FILE, {"events": []})
    events = analytics.get("events", [])

    summary = {
        "total_events": len(events),
        "pageviews": sum(1 for e in events if e.get("event") == "pageview"),
        "cta_clicks": sum(1 for e in events if e.get("event") == "cta_click"),
        "unique_slugs": len(set(e.get("slug", "") for e in events if e.get("slug"))),
        "by_event": {},
        "top_articles": {},
    }

    for e in events:
        evt = e.get("event", "unknown")
        summary["by_event"][evt] = summary["by_event"].get(evt, 0) + 1
        slug = e.get("slug", "")
        if slug and evt == "pageview":
            summary["top_articles"][slug] = summary["top_articles"].get(slug, 0) + 1

    # Sort top articles
    summary["top_articles"] = dict(
        sorted(summary["top_articles"].items(), key=lambda x: x[1], reverse=True)[:10]
    )

    return jsonify(summary)


@app.route("/health", methods=["GET"])
@app.route("/api/health", methods=["GET"])
def health():
    return jsonify({
        "status": "ok",
        "articles": len(get_articles()),
        "timestamp": datetime.now(timezone.utc).isoformat(),
    })


# ---------------------------------------------------------------------------
# Error handlers
# ---------------------------------------------------------------------------

@app.errorhandler(404)
def not_found(e):
    return render_template("base.html", page_title="Not Found", page_content="<h1>404 — Page not found</h1>"), 404


# ---------------------------------------------------------------------------
# Run
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    os.makedirs(DATA_DIR, exist_ok=True)
    if not os.path.exists(ARTICLES_FILE):
        save_json(ARTICLES_FILE, [])
    if not os.path.exists(ANALYTICS_FILE):
        save_json(ANALYTICS_FILE, {"events": []})
    port = int(os.environ.get("PORT", 5003))
    debug = os.environ.get("FLASK_ENV") == "development"
    app.run(debug=debug, host="0.0.0.0", port=port)
