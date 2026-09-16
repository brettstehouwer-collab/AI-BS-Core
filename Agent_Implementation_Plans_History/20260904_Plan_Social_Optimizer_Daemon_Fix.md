# Implementation Plan: Facebook & Social Outreach Optimizer Platform Generator (v5.170.0)

Upgrade and consolidate the **Personal Brand Studio** (`personal_brand`) and backend social optimization services into a dedicated **Facebook & Social Outreach Optimizer Platform Generator**. The system will intelligently analyze any input context, auto-detect optimal formatting (Long-Form Storytelling vs Short-Form Hook Punch), generate dual versions, and produce dynamic 3-tier mixed hashtag blocks (3–6 target limit) with automated comment-drop link helpers and Meta reach penalty protection.

## Proposed Architectural Components

### 1. Backend Social Optimizer Engine (`backend/routers/social_outreach_router.py` & `backend/core/social_optimizer_engine.py`)
- **Multi-Tenant FastAPI Endpoint (`/api/social/optimize`):**
  - Accepts raw text, book excerpts, voice transcripts, or business announcements.
  - Performs intelligent topic classification (e.g., Trauma Recovery / Memoir, Tech & Software Engineering, Business / Lead Gen, Personal Growth / Resilience, Creative Writing).
  - Generates both:
    - **Long-Form Narrative Post:** 1-2 sentence paragraphs, scroll-stopping hooks (<90 chars), whitespace pacing for "See More" algorithm triggers, zero in-body outbound links.
    - **Short-Form Punch Post:** High-impact hook, 3-5 visual emoji anchors, direct emotional punch under 280-400 characters.
  - Assembles **3 Mixed Hashtag Boxes (3 to 6 tags per box)** combining:
    - *Box 1: Core Outreach Mix* (Balanced primary niche + authentic tone + entity anchor).
    - *Box 2: Discovery & Community Mix* (High-volume reader/community tags + vulnerability).
    - *Box 3: Algorithmic & Search Mix* (High-velocity search tags + physiological/tactical specifics).
  - **Comment-Drop Link Protocol:** Extracts outbound URLs from raw input, creates a safe post body with "(Link in first comment)", and produces the ready-to-copy **First Comment Block** with the clean URL to bypass Meta's reach suppression penalty.
  - Multi-tenant isolation with `client_id` default `stehouwer_publishing`.

### 2. Frontend UI Overhaul (`PersonalBrandStudioTab.jsx` & mirror `frontend/components/PersonalBrandStudioTab.jsx`)
- **Auto-Detection & Format Switcher:** Toggle between `Auto-Detect (Recommended)`, `Force Long-Form Narrative`, and `Force Short-Form Punch`.
- **Side-by-Side Dual Format View:** Displays both Long-Form and Short-Form variations generated from the same context with instant 1-click clipboard copy.
- **Interactive Mixed Hashtag Box Matrix:** 
  - Visual cards for **Box 1 (Core)**, **Box 2 (Discovery)**, and **Box 3 (Search/Video)**.
  - 1-click "Append to Post" and 1-click "Copy Tags" buttons.
  - Real-time Tag Counter badge with safety indicators (Green: 3–6 tags; Amber: >6 tags risk).
- **First Comment Link Dropper Deck:** Dedicated card showing the extracted URL target (e.g. `https://stehouwer-publishing.com/library`) with a 1-click "Copy Comment #1" button.
- **Meta Algorithm Health Checker:** Visual inspection indicators:
  - 🟢 Zero Outbound Links in Body (Anti-Suppression Active)
  - 🟢 High-Engagement "See More" Fold Break
  - 🟢 Tag Ceiling Compliant (3–6 tags)

### 3. Master Ledgers, Documentation & Version Parity
- Register router in `backend/AI_BS_Backend.py`.
- Bump system version to `v5.170.0` across all UI badges, manuals, and ledgers.
- Archive task and implementation plan into `Agent_Tasks_History/` and `Agent_Implementation_Plans_History/`.

## Verification Plan
### Automated Tests
- Test Python social optimizer module with various prompts (autobiographical memoir, tech hardware build, business pressure washing).
- Verify JSON schema and tag box generation limits (strictly 3 to 6 tags per box).
### Manual Verification
- Test interactive UI in browser across both long-form and short-form generation modes.
- Verify 1-click clipboard copy functions for post text, hashtag blocks, and first comment link.
