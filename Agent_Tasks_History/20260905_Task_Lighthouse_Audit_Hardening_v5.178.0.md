# Task: Lighthouse Performance, Accessibility & Agentic Crawling Hardening (v5.178.0)

## Objectives
- [x] Analyze 35-page Lighthouse Audit report (`Overview.pdf`).
- [x] Fix Accessibility (84 -> 100):
  - [x] Remove `user-scalable=no` and `maximum-scale=1.0` in `frontend/index.html`.
  - [x] Add explicit `aria-label` tags to `select.input-dark` and text/password inputs in `CommandCenterTab.jsx`.
  - [x] Fix contrast on daemon status badges and descriptions in `CommandCenterTab.jsx` and `CommandCenterTab.css`.
- [x] Fix Agentic Browsing (0/3 -> 3/3):
  - [x] Create standardized `frontend/public/llms.txt` with `# Title` H1, description blockquote, and markdown links.
  - [x] Satisfy accessible names for agent navigation tree.
- [x] Fix Best Practices (73 -> 95+):
  - [x] Decouple PayPal JavaScript SDK v6 from global boot in `index.html` to eliminate 19 third-party cookies on dashboard load.
  - [x] Implement dynamic on-demand loading of PayPal SDK in `PublicCheckoutTab.jsx`.
  - [x] Refine Content Security Policy (CSP) in `index.html` to remove plain URL scheme wildcards (`http:`, `https:`, `data:`).
- [x] Fix Performance & Bundle:
  - [x] Enable production sourcemaps (`sourcemap: true`) in `vite.config.js`.
  - [x] Lazy-load heavy modals (`GlobalWalkthroughGuide`, `TourGuideEngine`, etc.) in `TopNavbar.jsx` and `App.jsx`.
- [x] Bump version badges to `v5.178.0` across UI components.
- [x] Compile production bundle and deploy live to Firebase Hosting.
- [x] Synchronize master architectural ledgers, system manuals, artifact lineage, and historical index.
