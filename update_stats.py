#!/usr/bin/env python3
"""
cinemoto999 Media Kit — Weekly Stats Updater
Updates YouTube subscribers via API. Instagram + TikTok via scrape attempt.
Runs weekly via launchd.
"""

import json
import os
import re
import urllib.request
import urllib.parse
from datetime import datetime

DIR = os.path.dirname(os.path.abspath(__file__))
KIT = os.path.join(DIR, "media-kit.html")
STATS_FILE = os.path.join(DIR, "stats_cache.json")

def _read(env_var, filename):
    val = os.environ.get(env_var)
    if val:
        return val.strip()
    path = os.path.join(DIR, filename)
    if os.path.exists(path):
        return open(path).read().strip()
    return None

YOUTUBE_API_KEY = _read("YOUTUBE_API_KEY", "youtube_api_key.txt")
YOUTUBE_CHANNEL_HANDLE = "cinemoto999"

IG_PAGE_TOKEN = _read("IG_PAGE_TOKEN", "ig_page_token.txt")
IG_ACCOUNT_ID = _read("IG_ACCOUNT_ID", "ig_account_id.txt") or "17841466902799245"

# ── Load cached stats (fallback if APIs fail) ─────────────────────────────────

def load_cache():
    if os.path.exists(STATS_FILE):
        return json.load(open(STATS_FILE))
    return {"youtube": None, "instagram": None, "tiktok": None, "updated": None}

def save_cache(stats):
    with open(STATS_FILE, "w") as f:
        json.dump(stats, f, indent=2)

# ── YouTube Data API v3 ───────────────────────────────────────────────────────

def get_youtube_subs():
    if not YOUTUBE_API_KEY:
        print("  No YouTube API key — skipping YouTube.")
        return None
    try:
        url = (
            f"https://www.googleapis.com/youtube/v3/channels"
            f"?part=statistics"
            f"&forHandle={YOUTUBE_CHANNEL_HANDLE}"
            f"&key={YOUTUBE_API_KEY}"
        )
        req = urllib.request.Request(url)
        with urllib.request.urlopen(req, timeout=10) as resp:
            data = json.loads(resp.read())
        items = data.get("items", [])
        if not items:
            print("  YouTube: channel not found.")
            return None
        subs = int(items[0]["statistics"]["subscriberCount"])
        print(f"  YouTube: {subs:,} subscribers")
        return subs
    except Exception as e:
        print(f"  YouTube API error: {e}")
        return None

# ── Instagram Graph API ───────────────────────────────────────────────────────

def get_instagram_followers():
    if not IG_PAGE_TOKEN:
        print("  No IG page token — skipping Instagram.")
        return None
    try:
        url = (
            f"https://graph.facebook.com/v21.0/{IG_ACCOUNT_ID}"
            f"?fields=followers_count"
            f"&access_token={IG_PAGE_TOKEN}"
        )
        with urllib.request.urlopen(url, timeout=10) as resp:
            data = json.loads(resp.read())
        count = int(data["followers_count"])
        print(f"  Instagram: {count:,} followers")
        return count
    except Exception as e:
        print(f"  Instagram API error: {e}")
        return None

# ── TikTok scrape ─────────────────────────────────────────────────────────────

def get_tiktok_followers():
    try:
        url = "https://www.tiktok.com/@cinemoto999"
        req = urllib.request.Request(url, headers={
            "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36",
            "Accept-Language": "en-US,en;q=0.9",
        })
        with urllib.request.urlopen(req, timeout=10) as resp:
            html = resp.read().decode("utf-8", errors="replace")
        m = re.search(r'"followerCount":(\d+)', html)
        if m:
            count = int(m.group(1))
            print(f"  TikTok: {count:,} followers")
            return count
        print("  TikTok: could not parse follower count from page.")
        return None
    except Exception as e:
        print(f"  TikTok scrape failed: {e}")
        return None

# ── Format number as short string (e.g. 12400 → "12.4K") ────────────────────

def fmt(n):
    if n is None:
        return None
    if n >= 1_000_000:
        return f"{n/1_000_000:.1f}M".rstrip("0").rstrip(".")
    if n >= 1_000:
        v = n / 1_000
        return f"{v:.1f}K" if v % 1 != 0 else f"{int(v)}K"
    return str(n)

# ── Patch HTML ────────────────────────────────────────────────────────────────

def update_html(yt, ig, tt):
    html = open(KIT).read()

    if yt is not None:
        html = re.sub(
            r'(<!-- YT_SUBS -->)[^<]*',
            f'<!-- YT_SUBS -->{fmt(yt)}',
            html
        )
    if ig is not None:
        html = re.sub(
            r'(<!-- IG_FOLLOWERS -->)[^<]*',
            f'<!-- IG_FOLLOWERS -->{fmt(ig)}',
            html
        )
    if tt is not None:
        html = re.sub(
            r'(<!-- TT_FOLLOWERS -->)[^<]*',
            f'<!-- TT_FOLLOWERS -->{fmt(tt)}',
            html
        )

    # Stamp the update date in the hero label
    date_str = datetime.now().strftime("%B %Y")
    html = re.sub(
        r'Media Kit &middot; \w+ \d{4}',
        f'Media Kit &middot; {date_str}',
        html
    )

    with open(KIT, "w") as f:
        f.write(html)
    print(f"  media-kit.html updated.")

# ── Main ──────────────────────────────────────────────────────────────────────

def run():
    print(f"[{datetime.now().strftime('%Y-%m-%d %H:%M')}] Updating cinemoto999 stats...")
    cache = load_cache()

    yt = get_youtube_subs()
    ig = get_instagram_followers()
    tt = get_tiktok_followers()

    # Fall back to cached values if live fetch failed
    yt = yt if yt is not None else cache.get("youtube")
    ig = ig if ig is not None else cache.get("instagram")
    tt = tt if tt is not None else cache.get("tiktok")

    save_cache({"youtube": yt, "instagram": ig, "tiktok": tt,
                "updated": datetime.now().isoformat()})
    update_html(yt, ig, tt)
    print(f"Done. YT={fmt(yt)} IG={fmt(ig)} TT={fmt(tt)}")

if __name__ == "__main__":
    run()
