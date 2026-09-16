# Task: Global Layout & Space Restoration, Studio Viewport Architecture & Red Banner Dismissal (v5.180.0)

## Objectives
- [x] Investigate massive space and layout distortion issues reported on `unified_creation` and across tabs.
- [x] Identify root cause: `frontend/style.css` rule forcing `flex-wrap: wrap !important; gap: 10px;` on all `subinterface-content div[style*="display: flex"]`.
- [x] Excise toxic flex-wrap rules from `style.css`.
- [x] Fix `index.css` global scroll rules: replace component names with actual tab keys (`.unified_creation-subinterface`, `.ide-subinterface`, etc.) and restore dedicated 100% viewport heights.
- [x] Insert `flexWrap: 'nowrap'` on `UniversalCreationSuite.jsx`, `PlaywrightTab.jsx`, and `ScreenwritingTab.jsx`.
- [x] Add 1-click dismiss button to Mom Mode top red banner in `TopNavbar.jsx` with `localStorage` persistence (`aibs_dismiss_mom_banner`), freeing up 50px of vertical space.
- [x] Add compact toolbar exemptions in `MomMode.css`.
- [x] Bump version to `v5.180.0` across UI badges.
- [x] Compile bundle (`npm run build`) in 22.45s and deploy live to Firebase Hosting (`https://ai-bs-dashboard.web.app`).
