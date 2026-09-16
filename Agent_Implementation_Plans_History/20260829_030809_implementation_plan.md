# Adaptive Protocol Router (APR) Implementation

This plan outlines the architectural upgrade to `syndication_router.py` to implement the Adaptive Protocol Router (APR) for 100% execution efficiency. 

## Background
Currently, the AI-BS Omni-Channel Syndicator fires a monolithic, uniform payload across 35 nodes. This causes 403 errors on IndexNow when pinging 3rd-party domains (like IMDb or YouTube) and crashes XML-RPC parsers due to tracking parameters containing unescaped `&` symbols. Furthermore, blind execution wastes backend threads on protocols that are guaranteed to fail.

## Proposed Changes

We will introduce a strict **APR Pipeline** inside `execute_broadcast` before any threads are allocated.

### 1. URL Inspection & Domain Classification
We will implement an APR classifier that evaluates the `target_url`:
- **Owned Domains** (`stehouwer-publishing.com`, `ai-bs-dashboard.web.app`): Flagged as `OWNED`.
- **External/Social Domains** (IMDb, Amazon, YouTube, TikTok): Flagged as `THIRD_PARTY`.

### 2. APR Parameter Sanitization
A new `sanitize_url_for_protocol(url, protocol)` helper will strip out toxic tracking parameters (e.g., `utm_*`, `ref`, `ref_`, `fbclid`). 
- **XML-RPC Protection**: We will safely retain critical application state parameters (like `v=` for YouTube) while stripping all extraneous query strings to guarantee 100% XML-RPC parser compliance without breaking the core link.

### 3. Segregated Delivery Pipelines
Based on the APR classification, the dispatcher will dynamically assemble the target fleet:
- **If `OWNED`**: Full deployment (IndexNow, WebSub, XML-RPC, Decentralized, Aggregators, Archival, Social, Local Sitemap).
- **If `THIRD_PARTY`**: Targeted deployment. **IndexNow and Local Sitemap Sync will be aggressively filtered out** to prevent 403 authorization rejections and polluting your local domain sitemaps with external URLs. 

### `c:\AI-BS\backend\modules\syndication_router.py`
#### [MODIFY] `syndication_router.py`
- Add `classify_url(url)` to categorize domains.
- Add `sanitize_apr_url(url, protocol)` to rebuild query strings dynamically.
- Modify `execute_broadcast` to filter `base_targets` dynamically using the classification flag before thread execution.
- Update `ping_xmlrpc`, `ping_aggregator`, and `ping_archival` to utilize the APR sanitized URLs rather than stripping all queries blindly.

## Open Questions
- Do you want to explicitly define any other domains as `OWNED` besides `stehouwer-publishing.com` and `ai-bs-dashboard.web.app`?
- Should we completely drop aggregator pings (PingFarm, Pingomatic) for `THIRD_PARTY` URLs, or are they still effective for external SEO velocity?

## Verification Plan
1. **Manual Dry-Run**: Broadcast an IMDb link (3rd-party) and a Stehouwer-Publishing link (Owned) via the UI.
2. **Result Matrix Validation**: Verify that IndexNow is bypassed entirely for the IMDb link, and that XML-RPC successfully fires without parameter crashing.
