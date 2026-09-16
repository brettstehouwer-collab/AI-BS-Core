# Implementation Plan: Lighthouse Performance, Accessibility & Agentic Crawling Hardening (v5.178.0)

## Overview
Comprehensive remediation of performance, accessibility, best practices, and agentic browsing issues detected during Lighthouse 13.4.1 audit on `Overview.pdf`.

## Architectural Changes
1. **Accessibility (`index.html`, `CommandCenterTab.jsx`, `CommandCenterTab.css`):**
   - Removed viewport scaling suppression to allow screen zoom up to 500%.
   - Added `aria-label` attributes to the recursive background loop selector (`Every 15m`), task description, Telegram token, HF model registry, and SSD RAM cache inputs.
   - Raised contrast of green, red, amber status badge text and background opacity in `STATUS_STYLES` and lightened `.daemon-desc` from `#6b7280` to `#94a3b8`.
2. **Agentic Crawling & LLM Indexing (`frontend/public/llms.txt`):**
   - Published RFC-compliant `llms.txt` defining the AI-BS ecosystem with top-level H1, blockquote summary, and structured links to Command Center, Bible Hub, Shared Cloud Drive, ROI Blueprint, Screenplay Studio, Prestige Wash OS, and Neural Intelligence.
3. **Third-Party Cookie Elimination & Security Hardening (`index.html`, `PublicCheckoutTab.jsx`):**
   - Removed PayPal SDK script tag and preconnect link from `index.html`.
   - Injected script dynamically inside `PublicCheckoutTab.jsx` `useEffect`, preventing 19 third-party cookies from loading on initial visit.
   - Replaced wildcard schemes in `index.html` CSP with explicit allowlists.
4. **Bundle Code-Splitting & Sourcemaps (`vite.config.js`, `TopNavbar.jsx`, `App.jsx`):**
   - Enabled `sourcemap: true` in `vite.config.js`.
   - Lazy-loaded `GlobalWalkthroughGuide`, `TourGuideEngine`, `TeamLiveChatModal`, and client portals with `Suspense`.

## Verification
- Built cleanly in 26.72s with `npm run build`.
- Deployed 1076 files to `https://ai-bs-dashboard.web.app` via Firebase Hosting CLI.
