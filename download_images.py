#!/usr/bin/env python3
"""
Download curated Unsplash images for Creator Report articles.
Run from: cd ~/ai-systems/tools/creator-report && python3 download_images.py

All images are from Unsplash (free to use, no attribution required for web).
Each article gets 1 hero + 2-3 inline images.
"""

import os
import json
import urllib.request
import sys
import time

IMG_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "static", "images", "articles")
os.makedirs(IMG_DIR, exist_ok=True)

# Curated Unsplash image IDs mapped to each article
# Format: { slug: { "hero": photo_id, "inline": [photo_id, photo_id, ...] } }
# Unsplash photo URL pattern: https://images.unsplash.com/photo-{id}?w=1200&q=80

IMAGES = {
    "sophie-rain-100-million-onlyfans-earnings": {
        "hero": "photo-1611162616305-c69b3fa7fbe0",  # Social media on phone
        "hero_alt": "Social media app notifications on smartphone screen",
        "inline": [
            ("photo-1563986768609-322da13575f2", "Woman with ring light filming content"),
            ("photo-1611162618071-b39a2ec055fb", "Social media platform icons on screen"),
            ("photo-1579621970563-ebec7560ff3e", "Money and financial growth concept"),
        ]
    },
    "onlyfans-ai-policy-2026-deepfake-ban": {
        "hero": "photo-1677442136019-21780ecad995",  # AI abstract
        "hero_alt": "Artificial intelligence technology abstract visualization",
        "inline": [
            ("photo-1620712943543-bcc4688e7485", "AI robot face digital art"),
            ("photo-1555949963-ff9fe0c870eb", "Digital security and verification concept"),
            ("photo-1551288049-bebda4e38f71", "Data dashboard and analytics screen"),
        ]
    },
    "creator-economy-254-billion-where-money-flows": {
        "hero": "photo-1611974789855-9c2a0a7236a3",  # Stock market data
        "hero_alt": "Financial market data and charts showing economic growth",
        "inline": [
            ("photo-1460925895917-afdab827c52f", "Business charts and market analysis"),
            ("photo-1553729459-afe8f2e2ed08", "Currency and global financial flow"),
            ("photo-1504868584819-f8e8b4b6d7e3", "Digital content creation workspace"),
        ]
    },
    "age-verification-25-states-adult-content-2026": {
        "hero": "photo-1589829545856-d10d557cf95f",  # Gavel and legal
        "hero_alt": "Legal gavel representing legislation and regulatory compliance",
        "inline": [
            ("photo-1450101499163-c8848e968838", "United States Capitol building"),
            ("photo-1432888498266-38ffec3eaf0a", "Digital identity verification on device"),
            ("photo-1526374965328-7f61d4dc18c5", "Digital code and cybersecurity concept"),
        ]
    },
    "bonnie-blue-arrest-bali-international-legal-risk": {
        "hero": "photo-1555899434-94d1368aa7af",  # Passport and travel
        "hero_alt": "International passport and travel documents on world map",
        "inline": [
            ("photo-1537996194471-e657df975ab4", "Bali tropical landscape and culture"),
            ("photo-1589994965851-a8f479c573a1", "Airport departures board showing flights"),
            ("photo-1507003211169-0a1dd7228f2d", "Person looking contemplative"),
        ]
    },
    "onlyfans-25-billion-creator-payouts-economics": {
        "hero": "photo-1579621970563-ebec7560ff3e",  # Money growth
        "hero_alt": "Growing stack of money representing creator economy payouts",
        "inline": [
            ("photo-1554224155-6726b3ff858f", "Financial calculations and spreadsheets"),
            ("photo-1611974789855-9c2a0a7236a3", "Stock trading data on monitors"),
            ("photo-1563986768609-322da13575f2", "Content creator with professional setup"),
        ]
    },
    "tiktok-ban-creators-platform-diversification-2025": {
        "hero": "photo-1611162618071-b39a2ec055fb",  # Social media apps
        "hero_alt": "Social media platform apps on smartphone representing platform diversification",
        "inline": [
            ("photo-1596558450268-9c27524ba856", "Person recording video content on phone"),
            ("photo-1432888498266-38ffec3eaf0a", "Multiple devices showing different platforms"),
            ("photo-1460925895917-afdab827c52f", "Business strategy and planning charts"),
        ]
    },
    "creator-tax-playbook-2026": {
        "hero": "photo-1554224155-6726b3ff858f",  # Tax forms calculator
        "hero_alt": "Tax forms and calculator on desk for financial planning",
        "inline": [
            ("photo-1450101499163-c8848e968838", "Government building representing tax policy"),
            ("photo-1551288049-bebda4e38f71", "Financial dashboard and analytics"),
            ("photo-1579621970563-ebec7560ff3e", "Money and financial documents"),
        ]
    },
    "creator-burnout-growth-era-over": {
        "hero": "photo-1474631245212-32dc3c8310c6",  # Burned out person
        "hero_alt": "Exhausted person at desk representing creator burnout",
        "inline": [
            ("photo-1504868584819-f8e8b4b6d7e3", "Cluttered desk with content creation equipment"),
            ("photo-1507003211169-0a1dd7228f2d", "Person looking stressed and fatigued"),
            ("photo-1506126613408-eca07ce68773", "Meditation and wellness concept"),
        ]
    },
    "patreon-apple-fee-squeeze-creator-exits": {
        "hero": "photo-1563013544-824ae1b704d3",  # Payment on phone
        "hero_alt": "Online payment notification showing platform fee deductions",
        "inline": [
            ("photo-1611162616305-c69b3fa7fbe0", "App store and digital platform icons"),
            ("photo-1460925895917-afdab827c52f", "Financial charts showing declining revenue"),
            ("photo-1596558450268-9c27524ba856", "Creator filming independent content"),
        ]
    },
    "creator-ma-boom-52-deals": {
        "hero": "photo-1560472355-536de3962603",  # Business handshake
        "hero_alt": "Business professionals closing a major acquisition deal",
        "inline": [
            ("photo-1611974789855-9c2a0a7236a3", "Market data showing deal volume"),
            ("photo-1551288049-bebda4e38f71", "Corporate analytics and due diligence data"),
            ("photo-1504868584819-f8e8b4b6d7e3", "Media company production workspace"),
        ]
    },
    "global-regulation-creator-compliance": {
        "hero": "photo-1529107386315-e1a2ed48a620",  # World flags
        "hero_alt": "International flags representing global regulatory landscape",
        "inline": [
            ("photo-1524492412937-b28074a5d7da", "Indian landmark representing India tech policy"),
            ("photo-1513635269975-59663e0ac1ad", "London skyline representing UK regulation"),
            ("photo-1526374965328-7f61d4dc18c5", "Digital compliance and data protection"),
        ]
    },
    "livestreaming-tech-stack-900-million-hours": {
        "hero": "photo-1598550476439-6847785fcea6",  # Streaming setup
        "hero_alt": "Professional livestreaming studio setup with camera and monitors",
        "inline": [
            ("photo-1558618666-fcd25c85f82e", "Server room powering streaming infrastructure"),
            ("photo-1596558450268-9c27524ba856", "Streamer creating live content"),
            ("photo-1551288049-bebda4e38f71", "Real-time analytics dashboard"),
        ]
    },
    "celebrity-creators-onlyfans-2025": {
        "hero": "photo-1522158637959-30ab5018e439",  # Red carpet celebrity
        "hero_alt": "Celebrity spotlight and red carpet event with cameras",
        "inline": [
            ("photo-1611162616305-c69b3fa7fbe0", "Social media following and engagement metrics"),
            ("photo-1563986768609-322da13575f2", "Professional content creation studio"),
            ("photo-1579621970563-ebec7560ff3e", "Revenue and earnings visualization"),
        ]
    },
}

UNSPLASH_BASE = "https://images.unsplash.com"

def download(photo_id, filename, size="w=1200&q=80"):
    filepath = os.path.join(IMG_DIR, filename)
    if os.path.exists(filepath) and os.path.getsize(filepath) > 5000:
        print(f"  SKIP {filename} (already exists)")
        return True

    url = f"{UNSPLASH_BASE}/{photo_id}?{size}"
    try:
        req = urllib.request.Request(url, headers={
            "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36"
        })
        with urllib.request.urlopen(req, timeout=30) as resp:
            data = resp.read()
            with open(filepath, "wb") as f:
                f.write(data)
        kb = len(data) / 1024
        print(f"  OK   {filename} ({kb:.0f} KB)")
        return True
    except Exception as e:
        print(f"  FAIL {filename}: {e}")
        return False


def main():
    print("Downloading Creator Report article images from Unsplash...\n")

    total = 0
    success = 0

    for slug, img_data in IMAGES.items():
        print(f"\n{slug}:")

        # Hero image
        total += 1
        if download(img_data["hero"], f"{slug}.jpg"):
            success += 1

        # Inline images
        for i, (photo_id, alt_text) in enumerate(img_data["inline"], 1):
            total += 1
            if download(photo_id, f"{slug}-{i}.jpg", "w=900&q=80"):
                success += 1

        time.sleep(0.3)  # Be nice to Unsplash

    print(f"\n{'='*50}")
    print(f"Done: {success}/{total} images downloaded")
    print(f"Location: {IMG_DIR}")

    # Now update articles.json
    if success > 0:
        print("\nUpdating articles.json with image paths...")
        articles_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "data", "articles.json")
        articles = json.load(open(articles_path))

        for article in articles:
            slug = article["slug"]
            if slug in IMAGES:
                img_data = IMAGES[slug]
                article["hero_image"] = f"/static/images/articles/{slug}.jpg"
                article["hero_image_alt"] = img_data["hero_alt"]
                article["hero_image_credit"] = "Unsplash"

                # Add inline image references
                inline_images = []
                for i, (photo_id, alt_text) in enumerate(img_data["inline"], 1):
                    inline_images.append({
                        "src": f"/static/images/articles/{slug}-{i}.jpg",
                        "alt": alt_text
                    })
                article["inline_images"] = inline_images

        with open(articles_path, "w") as f:
            json.dump(articles, f, indent=2)
        print("articles.json updated with local paths and inline images.")


if __name__ == "__main__":
    main()
