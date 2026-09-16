"""
backend/routers/sitemap_seo_router.py
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Dynamic XML Sitemap & Search Engine Ping Protocol Router (v5.292.0)
Scales domain outreach across Googlebot, Bingbot, IndexNow, Google Images, and Google Video.
Implements 4-Phase Architecture:
- Phase I: Node Proliferation & Priority Hierarchy
- Phase II: Media Protocol Namespaces (Image & Video XML)
- Phase III: Dynamic Re-Generation & Multi-Search-Engine Pinging
- Phase IV: Semantic Structured Data Telemetry
"""

import os
import time
import datetime
import logging
import httpx
from typing import Dict, List, Any, Optional
from fastapi import APIRouter, HTTPException, BackgroundTasks, Response
from pydantic import BaseModel

logger = logging.getLogger("SitemapSeoRouter")

router = APIRouter(prefix="/api/v1/seo", tags=["SEO & Dynamic Sitemap Engine"])

DIST_DIR = r"C:\StehouwerPublishing.com\website-rebuild\dist"
PUBLIC_DIR = r"C:\StehouwerPublishing.com\website-rebuild\public"
SITEMAP_DIST_PATH = os.path.join(DIST_DIR, "sitemap.xml")
SITEMAP_PUB_PATH = os.path.join(PUBLIC_DIR, "sitemap.xml")

DOMAIN_BASE = "https://stehouwer-publishing.com"

# In-memory ping history ledger
PING_LEDGER: List[Dict[str, Any]] = []

FEED_DIST_PATH = os.path.join(DIST_DIR, "feed.json")
FEED_PUB_PATH = os.path.join(PUBLIC_DIR, "feed.json")
SCHEMA_DIST_PATH = os.path.join(DIST_DIR, "schema.jsonld")
SCHEMA_PUB_PATH = os.path.join(PUBLIC_DIR, "schema.jsonld")
OPENAPI_DIST_PATH = os.path.join(DIST_DIR, "openapi.yaml")
OPENAPI_PUB_PATH = os.path.join(PUBLIC_DIR, "openapi.yaml")

class PingRequest(BaseModel):
    sitemap_url: Optional[str] = f"{DOMAIN_BASE}/sitemap.xml"
    include_indexnow: Optional[bool] = True

class SitemapEntry:
    def __init__(
        self,
        loc: str,
        priority: float = 0.8,
        changefreq: str = "weekly",
        lastmod: Optional[str] = None,
        images: Optional[List[Dict[str, str]]] = None,
        video: Optional[Dict[str, Any]] = None
    ):
        self.loc = loc
        self.priority = priority
        self.changefreq = changefreq
        self.lastmod = lastmod or datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%d")
        self.images = images or []
        self.video = video

def get_canonical_nodes() -> List[SitemapEntry]:
    today = datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%d")
    
    # Standard Media Assets
    hero_image = {
        "loc": f"{DOMAIN_BASE}/images/hero_bg.jpg",
        "title": "Stehouwer Publishing LLC - Corporate Brand & Literary Engine"
    }
    echos_cover = {
        "loc": f"{DOMAIN_BASE}/images/echos_within_cover.jpg",
        "title": "Echoes Within - Novel Cover by Julie Stehouwer"
    }
    judge_cover = {
        "loc": f"{DOMAIN_BASE}/images/judge_made_him_go_cover.jpg",
        "title": "The Judge Made Him Go - Novel Cover by Brett Stehouwer"
    }
    brett_profile = {
        "loc": f"{DOMAIN_BASE}/images/brett.jpg",
        "title": "Brett Stehouwer - Author, Systems Architect & Co-Founder"
    }
    julie_profile = {
        "loc": f"{DOMAIN_BASE}/images/julie.jpg",
        "title": "Julie Stehouwer - Founder, Executive Publisher & Author"
    }

    live_video = {
        "thumbnail_loc": f"{DOMAIN_BASE}/images/hero_bg.jpg",
        "title": "Stehouwer Publishing Live Broadcast & HLS Streaming Engine",
        "description": "Continuous live HLS broadcasting, AI audio demos, and creative content production stream.",
        "content_loc": f"{DOMAIN_BASE}/hls/live.m3u8",
        "player_loc": f"{DOMAIN_BASE}/live",
        "live": "yes",
        "publication_date": f"{today}T00:00:00+00:00",
        "family_friendly": "yes"
    }

    nodes = [
        # Phase I: Hierarchy & Proliferation
        SitemapEntry(
            loc=f"{DOMAIN_BASE}/",
            priority=1.0,
            changefreq="daily",
            lastmod=today,
            images=[hero_image, echos_cover, judge_cover]
        ),
        SitemapEntry(
            loc=f"{DOMAIN_BASE}/marketing",
            priority=0.8,
            changefreq="weekly",
            lastmod=today,
            images=[hero_image]
        ),
        SitemapEntry(
            loc=f"{DOMAIN_BASE}/advertising",
            priority=0.8,
            changefreq="weekly",
            lastmod=today,
            images=[hero_image]
        ),
        SitemapEntry(
            loc=f"{DOMAIN_BASE}/authors",
            priority=0.8,
            changefreq="weekly",
            lastmod=today,
            images=[julie_profile, brett_profile]
        ),
        SitemapEntry(
            loc=f"{DOMAIN_BASE}/library",
            priority=0.8,
            changefreq="weekly",
            lastmod=today,
            images=[echos_cover, judge_cover]
        ),
        SitemapEntry(
            loc=f"{DOMAIN_BASE}/film-tv",
            priority=0.8,
            changefreq="weekly",
            lastmod=today,
            images=[hero_image, echos_cover]
        ),
        SitemapEntry(
            loc=f"{DOMAIN_BASE}/live",
            priority=0.8,
            changefreq="daily",
            lastmod=today,
            images=[hero_image],
            video=live_video
        ),
        SitemapEntry(
            loc=f"{DOMAIN_BASE}/guestbook",
            priority=0.7,
            changefreq="weekly",
            lastmod=today,
            images=[hero_image]
        ),
        SitemapEntry(
            loc=f"{DOMAIN_BASE}/ai-bs-docs",
            priority=0.7,
            changefreq="monthly",
            lastmod=today,
            images=[hero_image]
        ),
        SitemapEntry(
            loc=f"{DOMAIN_BASE}/blog/project-noco",
            priority=0.6,
            changefreq="weekly",
            lastmod=today,
            images=[hero_image]
        ),
        SitemapEntry(
            loc=f"{DOMAIN_BASE}/api/docs",
            priority=0.6,
            changefreq="monthly",
            lastmod=today
        )
    ]
    
    return nodes

# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# Framework 1: XML Sitemap Engine (W3C Standard)
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

def generate_sitemap_xml() -> str:
    """Constructs W3C compliant XML sitemap with Image & Video extension namespaces."""
    nodes = get_canonical_nodes()
    
    xml_lines = [
        '<?xml version="1.0" encoding="UTF-8"?>',
        '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9"',
        '        xmlns:image="http://www.google.com/schemas/sitemap-image/1.1"',
        '        xmlns:video="http://www.google.com/schemas/sitemap-video/1.1">',
    ]

    for node in nodes:
        xml_lines.append('  <url>')
        xml_lines.append(f'    <loc>{node.loc}</loc>')
        xml_lines.append(f'    <lastmod>{node.lastmod}</lastmod>')
        xml_lines.append(f'    <changefreq>{node.changefreq}</changefreq>')
        xml_lines.append(f'    <priority>{node.priority:.1f}</priority>')
        
        # Image Protocol Integration (Phase II)
        for img in node.images:
            xml_lines.append('    <image:image>')
            xml_lines.append(f'      <image:loc>{img["loc"]}</image:loc>')
            if "title" in img:
                xml_lines.append(f'      <image:title>{img["title"]}</image:title>')
            xml_lines.append('    </image:image>')

        # Video Protocol Integration (Phase II)
        if node.video:
            v = node.video
            xml_lines.append('    <video:video>')
            xml_lines.append(f'      <video:thumbnail_loc>{v["thumbnail_loc"]}</video:thumbnail_loc>')
            xml_lines.append(f'      <video:title>{v["title"]}</video:title>')
            xml_lines.append(f'      <video:description>{v["description"]}</video:description>')
            if "content_loc" in v:
                xml_lines.append(f'      <video:content_loc>{v["content_loc"]}</video:content_loc>')
            if "player_loc" in v:
                xml_lines.append(f'      <video:player_loc>{v["player_loc"]}</video:player_loc>')
            if "publication_date" in v:
                xml_lines.append(f'      <video:publication_date>{v["publication_date"]}</video:publication_date>')
            if "live" in v:
                xml_lines.append(f'      <video:live>{v["live"]}</video:live>')
            xml_lines.append('    </video:video>')

        xml_lines.append('  </url>')

    xml_lines.append('</urlset>')
    return '\n'.join(xml_lines)

# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# Framework 2: JSON Feed 1.1 Specification (https://jsonfeed.org/version/1.1)
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

def generate_json_feed_1_1() -> Dict[str, Any]:
    """Generates official JSON Feed 1.1 syndication data for modern mobile and feed parsers."""
    now_iso = datetime.datetime.now(datetime.timezone.utc).isoformat()
    return {
        "version": "https://jsonfeed.org/version/1.1",
        "title": "Stehouwer Publishing L.L.C. Official Broadcast & Feed",
        "home_page_url": DOMAIN_BASE,
        "feed_url": f"{DOMAIN_BASE}/feed.json",
        "description": "Chronological publication releases, AI-BS technical documentation, live audio/video streams, and marketing announcements.",
        "user_comment": "Official JSON Feed 1.1 syndication stream for Stehouwer Publishing and the AI-BS autonomous ecosystem.",
        "icon": f"{DOMAIN_BASE}/images/hero_bg.jpg",
        "favicon": f"{DOMAIN_BASE}/images/hero_bg.jpg",
        "language": "en-US",
        "authors": [
            {
                "name": "Julie Stehouwer",
                "url": f"{DOMAIN_BASE}/authors",
                "avatar": f"{DOMAIN_BASE}/images/julie.jpg"
            },
            {
                "name": "Brett Stehouwer",
                "url": f"{DOMAIN_BASE}/authors",
                "avatar": f"{DOMAIN_BASE}/images/brett.jpg"
            }
        ],
        "items": [
            {
                "id": f"{DOMAIN_BASE}/live",
                "url": f"{DOMAIN_BASE}/live",
                "title": "Stehouwer Publishing Sovereign Live Broadcast Engine",
                "summary": "Continuous 24/7 sovereign live HLS broadcast powered by AI-BS Audio/Video Bridge.",
                "content_html": "<p>Experience continuous high-definition live streaming, AI audio synthesis demos, and screenplay productions broadcasted straight from the AI-BS broadcasting kernel.</p>",
                "image": f"{DOMAIN_BASE}/images/hero_bg.jpg",
                "date_published": "2026-09-15T00:00:00Z",
                "date_modified": now_iso,
                "tags": ["Live Stream", "HLS", "AI Broadcast", "Stehouwer Media"],
                "attachments": [
                    {
                        "url": f"{DOMAIN_BASE}/hls/live.m3u8",
                        "mime_type": "application/x-mpegURL",
                        "title": "HLS Stream Manifest",
                        "size_in_bytes": 0
                    }
                ]
            },
            {
                "id": f"{DOMAIN_BASE}/library/echoes-within",
                "url": f"{DOMAIN_BASE}/library",
                "title": "Echoes Within by Julie Stehouwer",
                "summary": "Acclaimed novel exploring suspense, emotional resilience, and intricate family legacies.",
                "content_html": "<p><em>Echoes Within</em> is a landmark publication from Stehouwer Publishing, delving into the powerful narratives of legacy and discovery.</p>",
                "image": f"{DOMAIN_BASE}/images/echos_within_cover.jpg",
                "date_published": "2026-01-15T00:00:00Z",
                "date_modified": now_iso,
                "tags": ["Books", "Fiction", "Julie Stehouwer", "Publishing"]
            },
            {
                "id": f"{DOMAIN_BASE}/library/the-judge-made-him-go",
                "url": f"{DOMAIN_BASE}/library",
                "title": "The Judge Made Him Go by Brett Stehouwer",
                "summary": "Compelling biographical journey navigating adversity, perseverance, and transformation.",
                "content_html": "<p><em>The Judge Made Him Go</em> chronicles a true biographical odyssey of perseverance, institutional confrontation, and redemption.</p>",
                "image": f"{DOMAIN_BASE}/images/judge_made_him_go_cover.jpg",
                "date_published": "2026-02-01T00:00:00Z",
                "date_modified": now_iso,
                "tags": ["Biography", "Memoir", "Brett Stehouwer", "Books"]
            },
            {
                "id": f"{DOMAIN_BASE}/blog/project-noco",
                "url": f"{DOMAIN_BASE}/blog/project-noco",
                "title": "Project NoCo - Technical Architecture & Sovereign Autonomous AI",
                "summary": "Whitepaper on zero-cost local autonomous intelligence, high-throughput GPU orchestration, and distributed workflows.",
                "content_html": "<p>Project NoCo integrates the AI-BS autonomous orchestration core, running local LLMs across RTX 4090 hardware with 18-port collision-free routing.</p>",
                "image": f"{DOMAIN_BASE}/images/hero_bg.jpg",
                "date_published": "2026-08-01T00:00:00Z",
                "date_modified": now_iso,
                "tags": ["AI-BS", "Architecture", "Technology", "Local LLMs"]
            }
        ]
    }

# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# Framework 3: JSON-LD Linked Data Multi-Entity Schema Graph
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

def generate_schema_org_json_ld() -> Dict[str, Any]:
    """Generates comprehensive Schema.org JSON-LD multi-entity graph for search engine semantic parsers."""
    return {
        "@context": "https://schema.org",
        "@graph": [
            {
                "@type": ["Organization", "PublishingHouse"],
                "@id": f"{DOMAIN_BASE}/#organization",
                "name": "Stehouwer Publishing L.L.C.",
                "url": DOMAIN_BASE,
                "logo": f"{DOMAIN_BASE}/images/hero_bg.jpg",
                "description": "Independent publishing house, literary rights management, marketing strategy, audio production, and film & television adaptation.",
                "foundingLocation": "Grand Haven, Michigan, USA",
                "founder": [
                    {
                        "@type": "Person",
                        "name": "Julie Stehouwer",
                        "jobTitle": "Founder & Executive Publisher"
                    },
                    {
                        "@type": "Person",
                        "name": "Brett Stehouwer",
                        "jobTitle": "Co-Founder, Author & AI Systems Architect"
                    }
                ],
                "contactPoint": {
                    "@type": "ContactPoint",
                    "telephone": "+1-616-406-7993",
                    "contactType": "customer service",
                    "email": "stehouwerjulie@gmail.com",
                    "areaServed": "Worldwide",
                    "availableLanguage": "English"
                },
                "sameAs": [
                    "https://www.facebook.com/julie.a.stehouwer/",
                    "https://ai-bs-dashboard.web.app"
                ]
            },
            {
                "@type": "LocalBusiness",
                "@id": f"{DOMAIN_BASE}/#localbusiness",
                "name": "Stehouwer Publishing L.L.C.",
                "image": f"{DOMAIN_BASE}/images/hero_bg.jpg",
                "telephone": "+1-616-406-7993",
                "email": "stehouwerjulie@gmail.com",
                "address": {
                    "@type": "PostalAddress",
                    "addressLocality": "Grand Haven",
                    "addressRegion": "MI",
                    "addressCountry": "US"
                },
                "priceRange": "$$"
            },
            {
                "@type": "WebSite",
                "@id": f"{DOMAIN_BASE}/#website",
                "url": DOMAIN_BASE,
                "name": "Stehouwer Publishing",
                "publisher": {
                    "@id": f"{DOMAIN_BASE}/#organization"
                },
                "inLanguage": "en-US"
            },
            {
                "@type": "BroadcastService",
                "@id": f"{DOMAIN_BASE}/#broadcast",
                "name": "Stehouwer Publishing Live HLS Audio/Video Engine",
                "broadcastDisplayName": "AI-BS Sovereign Live Stream",
                "broadcaster": {
                    "@id": f"{DOMAIN_BASE}/#organization"
                }
            },
            {
                "@type": "Book",
                "@id": f"{DOMAIN_BASE}/#book-echoes-within",
                "name": "Echoes Within",
                "author": {
                    "@type": "Person",
                    "name": "Julie Stehouwer"
                },
                "publisher": {
                    "@id": f"{DOMAIN_BASE}/#organization"
                },
                "image": f"{DOMAIN_BASE}/images/echos_within_cover.jpg",
                "inLanguage": "English",
                "genre": "Fiction / Suspense",
                "bookFormat": "https://schema.org/Paperback"
            },
            {
                "@type": "Book",
                "@id": f"{DOMAIN_BASE}/#book-the-judge-made-him-go",
                "name": "The Judge Made Him Go",
                "author": {
                    "@type": "Person",
                    "name": "Brett Stehouwer"
                },
                "publisher": {
                    "@id": f"{DOMAIN_BASE}/#organization"
                },
                "image": f"{DOMAIN_BASE}/images/judge_made_him_go_cover.jpg",
                "inLanguage": "English",
                "genre": "Memoir / Biography",
                "bookFormat": "https://schema.org/Paperback"
            },
            {
                "@type": "SoftwareApplication",
                "@id": f"{DOMAIN_BASE}/#software-aibs",
                "name": "AI-BS (Autonomous Intelligence & Build System)",
                "operatingSystem": "Windows 11 / WSL2 Ubuntu",
                "applicationCategory": "DeveloperApplication / AI Engine",
                "creator": {
                    "@type": "Person",
                    "name": "Brett Stehouwer"
                },
                "description": "Zero-cost local autonomous intelligence orchestrating multi-agent reasoning, high-throughput GPU inference, and distributed workflows."
            }
        ]
    }

# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# Framework 4: OpenAPI 3.1 YAML / Microservices Map
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

def generate_openapi_yaml(app=None) -> str:
    """Exports structured OpenAPI 3.1 YAML definition for programmatic API client generators."""
    import yaml
    if app is not None and hasattr(app, "openapi"):
        openapi_dict = app.openapi()
    else:
        # Fallback canonical OpenAPI definition
        openapi_dict = {
            "openapi": "3.1.0",
            "info": {
                "title": "Stehouwer Publishing & AI-BS Sovereign API Gateway",
                "version": "5.292.0",
                "description": "Programmatic microservices endpoint map for SEO syndication, live telemetry, and autonomous intelligence workflows."
            },
            "servers": [
                {"url": DOMAIN_BASE, "description": "Production Domain Gateway"},
                {"url": "http://127.0.0.1:8000", "description": "Local AI-BS Backend Host"}
            ],
            "paths": {
                "/api/v1/seo/sitemap.xml": {
                    "get": {
                        "summary": "Serve W3C Dynamic XML Sitemap",
                        "responses": {"200": {"description": "XML sitemap stream", "content": {"application/xml": {}}}}
                    }
                },
                "/api/v1/seo/feed.json": {
                    "get": {
                        "summary": "Serve JSON Feed 1.1 Specification",
                        "responses": {"200": {"description": "JSON Feed 1.1 syndication object", "content": {"application/feed+json": {}}}}
                    }
                },
                "/api/v1/seo/json-ld": {
                    "get": {
                        "summary": "Serve Schema.org Multi-Entity Linked Data Graph",
                        "responses": {"200": {"description": "Schema.org Linked Data JSON-LD graph", "content": {"application/ld+json": {}}}}
                    }
                },
                "/api/v1/seo/openapi.yaml": {
                    "get": {
                        "summary": "Serve OpenAPI YAML Specification",
                        "responses": {"200": {"description": "OpenAPI YAML API contract", "content": {"application/yaml": {}}}}
                    }
                },
                "/api/v1/seo/sitemap/ping": {
                    "post": {
                        "summary": "Trigger Multi-Search Engine Ping (Google, Bing, IndexNow)",
                        "responses": {"200": {"description": "Ping dispatch results"}}
                    }
                }
            }
        }
    return yaml.dump(openapi_dict, sort_keys=False, default_flow_style=False)

# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# Disk Synchronization Utility
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

def write_all_syndication_assets_to_disk() -> Dict[str, Any]:
    """Writes all 4 syndication artifacts (XML sitemap, JSON Feed, JSON-LD, OpenAPI YAML) to disk."""
    import json
    os.makedirs(DIST_DIR, exist_ok=True)
    
    # 1. XML Sitemap
    xml_content = generate_sitemap_xml()
    with open(SITEMAP_DIST_PATH, "w", encoding="utf-8") as f:
        f.write(xml_content)
    if os.path.exists(PUBLIC_DIR):
        with open(SITEMAP_PUB_PATH, "w", encoding="utf-8") as f:
            f.write(xml_content)

    # 2. JSON Feed 1.1
    feed_data = generate_json_feed_1_1()
    feed_json = json.dumps(feed_data, indent=2, ensure_ascii=False)
    with open(FEED_DIST_PATH, "w", encoding="utf-8") as f:
        f.write(feed_json)
    if os.path.exists(PUBLIC_DIR):
        with open(FEED_PUB_PATH, "w", encoding="utf-8") as f:
            f.write(feed_json)

    # 3. JSON-LD Graph
    schema_data = generate_schema_org_json_ld()
    schema_json = json.dumps(schema_data, indent=2, ensure_ascii=False)
    with open(SCHEMA_DIST_PATH, "w", encoding="utf-8") as f:
        f.write(schema_json)
    if os.path.exists(PUBLIC_DIR):
        with open(SCHEMA_PUB_PATH, "w", encoding="utf-8") as f:
            f.write(schema_json)

    # 4. OpenAPI YAML
    openapi_yaml = generate_openapi_yaml()
    with open(OPENAPI_DIST_PATH, "w", encoding="utf-8") as f:
        f.write(openapi_yaml)
    if os.path.exists(PUBLIC_DIR):
        with open(OPENAPI_PUB_PATH, "w", encoding="utf-8") as f:
            f.write(openapi_yaml)

    return {
        "status": "success",
        "synced_files": {
            "sitemap_xml": SITEMAP_DIST_PATH,
            "feed_json": FEED_DIST_PATH,
            "schema_jsonld": SCHEMA_DIST_PATH,
            "openapi_yaml": OPENAPI_DIST_PATH
        },
        "timestamp": time.time()
    }

async def execute_search_engine_pings(sitemap_url: str) -> Dict[str, Any]:
    """Executes asynchronous pings to Google, Bing, and IndexNow endpoints."""
    ping_results = []
    
    # 1. Googlebot Ping
    google_ping_url = f"https://www.google.com/ping?sitemap={sitemap_url}"
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            resp = await client.get(google_ping_url)
            ping_results.append({
                "engine": "Google",
                "url": google_ping_url,
                "status_code": resp.status_code,
                "success": resp.status_code in [200, 204]
            })
    except Exception as e:
        ping_results.append({
            "engine": "Google",
            "url": google_ping_url,
            "status_code": 0,
            "error": str(e),
            "success": False
        })

    # 2. Bingbot Ping
    bing_ping_url = f"https://www.bing.com/ping?sitemap={sitemap_url}"
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            resp = await client.get(bing_ping_url)
            ping_results.append({
                "engine": "Bing",
                "url": bing_ping_url,
                "status_code": resp.status_code,
                "success": resp.status_code in [200, 204]
            })
    except Exception as e:
        ping_results.append({
            "engine": "Bing",
            "url": bing_ping_url,
            "status_code": 0,
            "error": str(e),
            "success": False
        })

    # 3. IndexNow Fast Indexing Protocol (Microsoft Bing, Yandex, Seznam, Naver)
    indexnow_url = "https://api.indexnow.org/indexnow"
    key_hex = "e8b7c2a19f044b369c47e09876543210"
    nodes = get_canonical_nodes()
    url_list = [n.loc for n in nodes]
    indexnow_payload = {
        "host": "stehouwer-publishing.com",
        "key": key_hex,
        "keyLocation": f"{DOMAIN_BASE}/{key_hex}.txt",
        "urlList": url_list
    }
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            resp = await client.post(indexnow_url, json=indexnow_payload)
            ping_results.append({
                "engine": "IndexNow (Bing/Yandex/Seznam)",
                "url": indexnow_url,
                "status_code": resp.status_code,
                "success": resp.status_code in [200, 202]
            })
    except Exception as e:
        ping_results.append({
            "engine": "IndexNow",
            "url": indexnow_url,
            "status_code": 0,
            "error": str(e),
            "success": False
        })

    record = {
        "timestamp": time.time(),
        "sitemap_url": sitemap_url,
        "results": ping_results
    }
    PING_LEDGER.append(record)
    if len(PING_LEDGER) > 50:
        PING_LEDGER.pop(0)

    return record

# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# API Endpoints & Framework MIME Broadcasting
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

@router.get("/sitemap.xml")
async def serve_dynamic_sitemap():
    """Serves real-time dynamic XML sitemap with XML content headers."""
    xml_data = generate_sitemap_xml()
    return Response(content=xml_data, media_type="application/xml")

@router.get("/feed.json")
async def serve_json_feed():
    """Serves JSON Feed 1.1 Specification (application/feed+json)."""
    import json
    feed_data = generate_json_feed_1_1()
    return Response(content=json.dumps(feed_data, indent=2, ensure_ascii=False), media_type="application/feed+json")

@router.get("/json-ld")
@router.get("/schema.jsonld")
async def serve_json_ld_graph():
    """Serves Schema.org Linked Data Entity Graph (application/ld+json)."""
    import json
    schema_data = generate_schema_org_json_ld()
    return Response(content=json.dumps(schema_data, indent=2, ensure_ascii=False), media_type="application/ld+json")

@router.get("/openapi.yaml")
async def serve_openapi_yaml():
    """Serves OpenAPI 3.1 YAML API Contract (application/yaml)."""
    yaml_content = generate_openapi_yaml()
    return Response(content=yaml_content, media_type="application/yaml")

@router.post("/sitemap/generate")
@router.post("/syndicate/all")
async def generate_and_save_all_syndication(background_tasks: BackgroundTasks):
    """Compiles and synchronizes all syndication frameworks (XML, JSON Feed, JSON-LD, OpenAPI YAML) to disk."""
    disk_res = write_all_syndication_assets_to_disk()
    nodes = get_canonical_nodes()
    total_images = sum(len(n.images) for n in nodes)
    total_videos = sum(1 for n in nodes if n.video)

    return {
        "status": "success",
        "message": "All syndication formats (XML Sitemap, JSON Feed 1.1, JSON-LD, OpenAPI YAML) successfully synchronized.",
        "url_count": len(nodes),
        "image_count": total_images,
        "video_count": total_videos,
        "disk_sync": disk_res
    }

@router.post("/sitemap/ping")
async def ping_search_engines(payload: Optional[PingRequest] = None):
    """Transmits real-time sitemap indexing requests to search engine APIs."""
    sitemap_url = payload.sitemap_url if payload else f"{DOMAIN_BASE}/sitemap.xml"
    # Ensure fresh assets are on disk first
    write_all_syndication_assets_to_disk()
    
    ping_record = await execute_search_engine_pings(sitemap_url)
    return {
        "status": "success",
        "ping_record": ping_record
    }

@router.get("/status")
async def get_seo_telemetry():
    """Returns real-time SEO and sitemap metadata telemetry."""
    nodes = get_canonical_nodes()
    total_images = sum(len(n.images) for n in nodes)
    total_videos = sum(1 for n in nodes if n.video)
    
    mtime = 0
    if os.path.exists(SITEMAP_DIST_PATH):
        mtime = os.path.getmtime(SITEMAP_DIST_PATH)

    return {
        "status": "operational",
        "domain": DOMAIN_BASE,
        "frameworks": {
            "xml_sitemap": f"{DOMAIN_BASE}/sitemap.xml",
            "json_feed": f"{DOMAIN_BASE}/feed.json",
            "json_ld": f"{DOMAIN_BASE}/schema.jsonld",
            "openapi_yaml": f"{DOMAIN_BASE}/openapi.yaml"
        },
        "total_urls": len(nodes),
        "total_indexed_images": total_images,
        "total_indexed_videos": total_videos,
        "sitemap_last_modified_timestamp": mtime,
        "sitemap_last_modified_iso": datetime.datetime.fromtimestamp(mtime, datetime.timezone.utc).isoformat() if mtime else None,
        "recent_pings": PING_LEDGER[-5:],
        "namespaces": {
            "core": "http://www.sitemaps.org/schemas/sitemap/0.9",
            "image": "http://www.google.com/schemas/sitemap-image/1.1",
            "video": "http://www.google.com/schemas/sitemap-video/1.1"
        }
    }

