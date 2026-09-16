# Parameter Normalization & Dynamic Routing Refactor

This plan details the implementation of strict payload normalization and dynamic protocol routing within the Omni-Channel Broadcast matrix to prevent third-party URL rejection (IndexNow HTTP 422 errors) and XML-RPC/WebSub parsing failures.

## User Review Required

Please review the proposed `verified_domains` list below. If there are other root domains you own where the IndexNow verification key is hosted, they must be added to this list. 

## Open Questions

- The current verified domains for IndexNow are assumed to be `stehouwer-publishing.com` and `ai-bs-dashboard.web.app`. Should we include any others?

## Proposed Changes

### Backend Syndication Router

#### [MODIFY] `syndication_router.py`
We will rewrite the internal ping functions inside `execute_broadcast` to implement the Parameter Failure Matrix logic.

**1. Third-Party URL Isolation (IndexNow Guardrail)**
- Define `verified_domains = ["stehouwer-publishing.com", "ai-bs-dashboard.web.app"]`.
- Inside `ping_indexnow`, iterate over `url_list` and filter out any URLs whose domain is not in `verified_domains`. 
- If the filtered list is empty (e.g. broadcasting Amazon, IMDb, TikTok, YouTube only), the engine will instantly bypass IndexNow with a `BYPASSED (3rd-Party Domain)` status, completely eliminating HTTP 400/403/422 failures.

**2. Strict URL Sanitization & XML-RPC Normalization**
- Introduce a helper to strip tracking parameters (`?ref=...`, `&utm_source=...`) to prevent unescaped ampersands (`&`) from breaking XML-RPC payloads.
- Update `ping_xmlrpc` to explicitly use the `weblogUpdates.ping(title, url)` standard 2-parameter signature, ensuring maximum compatibility across vintage Weblog ping servers.

**3. WebSub & REST Aggregator Normalization**
- Force `ping_websub` to send strict `application/x-www-form-urlencoded` headers with exact keys (`hub.mode`, `hub.url`).
- Update `ping_aggregator` to sanitize all GET query parameters using `urllib.parse.quote()` to prevent URL parsing crashes on remote nodes.

## Verification Plan

### Automated Tests
- Run `python backend/test_omnichannel_syndication.py` to ensure local tests still pass.

### Manual Verification
- We will trigger a broadcast for a 3rd-party domain (e.g. your TikTok or IMDb link) and verify that IndexNow returns a clean `BYPASSED` status rather than HTTP 422, while XML-RPC and WebSub successfully accept the sanitized parameters.
