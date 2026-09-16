# Tasks: Parameter Normalization & Dynamic Routing Refactor

- [x] Phase 1: Dynamic Protocol Routing in `syndication_router.py`
  - [x] Implement `verified_domains` list and apply to `ping_indexnow`.
  - [x] Implement URL stripping logic to sanitize targets.
  - [x] Refactor `ping_xmlrpc` to enforce standard 2-parameter signature.
  - [x] Refactor `ping_websub` and `ping_aggregator` for strict formatting.
- [x] Phase 2: Verification
  - [x] Run automated tests.
  - [x] Manually verify TikTok/IMDb bypasses IndexNow but hits XML-RPC/WebSub successfully.
- [ ] Phase 3: Master Ledger & Archiving
  - [ ] Archive Tasks and Plans.
  - [ ] Generate Walkthrough.
