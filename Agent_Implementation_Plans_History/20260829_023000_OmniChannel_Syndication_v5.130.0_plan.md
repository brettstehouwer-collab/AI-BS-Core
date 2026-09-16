# Implementation Plan: Omni-Channel Automated Broadcast & Campaign Matrix (v5.130.0)

Expand the Automated Posting & Syndication Suite into a complete Omni-Channel Advertising Matrix that automatically triggers search crawlers, direct Discord/Telegram community webhooks, Bluesky/Mastodon open social posts, multi-URL campaign multiplexing, and dynamic sitemap/RSS auto-sync upon clicking "FIRE SEND".

---

## User Review Required

> [!NOTE]
> All new channels use **100% free open protocols and webhooks** (Discord Webhooks, Telegram Bot API, Bluesky AT Protocol, Mastodon ActivityPub, and local XML generation). Zero paid API tokens are required. If specific external keys are unset, channels report an operational `STANDBY / READY` status without throwing errors or blocking the broadcast.

---

## Proposed Changes

### Phase 1: Backend Omni-Channel Dispatch Engines

#### [MODIFY] [backend/modules/syndication_router.py](file:///C:/AI-BS/backend/modules/syndication_router.py)
- Expand `BroadcastRequest`:
  - `urls: Optional[List[str]] = None` (for multi-URL campaign multiplexing).
  - `channels: Optional[Dict[str, bool]] = None` (toggles for Discord, Telegram, Bluesky, Mastodon, Sitemap).
  - `custom_ad_copy: Optional[str] = None`
- Implement **Discord Rich Embed Webhook Dispatcher**:
  - Dispatches formatted rich embeds with author identity, thumbnail, description, target URL, and timestamp.
- Implement **Telegram Channel Bot Dispatcher**:
  - Sends Markdown-formatted broadcast announcements to public/private Telegram groups or channels.
- Implement **Bluesky AT Protocol & Mastodon ActivityPub Auto-Posters**:
  - Communicates directly with free decentralized APIs to create posts and rich link previews.
- Implement **Dynamic Sitemap.xml & Feed.xml Local Engine**:
  - Automatically updates `C:\StehouwerPublishing.com\sitemap.xml` and `feed.xml` on disk and pings WebSub hubs with the updated RSS payload.

---

### Phase 2: Frontend Omni-Channel Campaign Matrix UI

#### [MODIFY] [frontend/components/SyndicationTab.jsx](file:///C:/AI-BS/frontend/components/SyndicationTab.jsx)
- Add **Campaign Multiplexer Mode**:
  - "🎯 Single Custom Target"
  - "🌐 Full Media Footprint" (5 URLs: Site + Amazon + YouTube + IMDb + Facebook)
  - "🎵 Music & Sound Fleet" (Site + Audio Suites + Sound Vault)
  - "🎬 Literary & Film Suite" (Site + Amazon Book + IMDb + Screenwriting)
- Add **Social & Community Channels Matrix**:
  - Interactive toggle pills for Discord, Telegram, Bluesky, Mastodon, and Dynamic Sitemap/RSS.
- Update **Results Console**:
  - Adds dedicated telemetry panels for Social/Community Webhooks alongside the 30-node search fleet.

#### [COPY] [BroadcastStudioApp/src/components/SyndicationTab.jsx](file:///C:/AI-BS/BroadcastStudioApp/src/components/SyndicationTab.jsx)
- Synchronize all frontend upgrades to the desktop application.

---

### Phase 3: Automated Verification & Testing

#### [NEW] [backend/test_omnichannel_syndication.py](file:///C:/AI-BS/backend/test_omnichannel_syndication.py)
- Validates multi-URL batch multiplexing, Discord webhook formatting, Telegram payload generation, Bluesky/Mastodon graceful fallback, and local `sitemap.xml` / `feed.xml` synchronization.

---

### Phase 4 & 5: Version Parity, Cloud Deployment & Master Ledgers Sync

- Bump version badges to **`v5.130.0`** across `App.jsx`, `Sidebar.jsx`, `TopNavbar.jsx`, `ChatTab.jsx`, `EcosystemBlueprintTab.jsx`, `BroadcastStudio.jsx`, and `SyndicationTab.jsx`.
- Compile and deploy frontend live to Firebase Hosting (`ai-bs-dashboard.web.app`).
- Update `AI_BS_MASTER_ARCHITECTURAL_LEDGER.md` (`v5.130.0`).
- Update `docs/AI_BS_MASTER_ECOSYSTEM_MANUAL.md` (`v5.130.0`), copy to `saved_data/artifacts/20260829_AI_BS_Master_Ecosystem_Manual.md`, and log in `NotebookLM_Records/artifact_history.md`.
- Append to `MASTER_TASKS_CHRONOLOGY.md`, `MASTER_IMPLEMENTATION_PLANS_CHRONOLOGY.md`, and `MASTER_HISTORICAL_INDEX.md`.

---

## Verification Plan

### Automated Tests
- Run `python backend/test_omnichannel_syndication.py` and verify all tests pass.

### Live Cloud Deployment
- Verify successful Firebase Hosting deployment on `https://ai-bs-dashboard.web.app`.
