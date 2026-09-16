# Implementation Plan: Broadcast Studio Streamlabs Overlay Creator, Layer Re-Ordering & Blue Active Highlighting (v5.81.0)

Implement visual glowing blue/cyan active state highlighting for all active sources, add layer re-ordering controls (Move Up ▲ / Move Down ▼) for z-index layer management, and build a Streamlabs-style Professional Overlay Creator suite with custom animated cam borders, stream tickers, alert boxes, custom images, and browser widgets.

## Proposed Changes

1. **Active Source Visual Highlighting (`frontend/src/components/BroadcastStudio.jsx`)**:
   - Style active/enabled sources in the Sources dock with glowing electric blue/cyan theme (`rgba(0, 229, 255, 0.15)` background, `#00e5ff` border, glowing status icon, and `● ACTIVE` badge). Dim inactive/hidden sources.

2. **Layer Re-Ordering Controls (`frontend/src/components/BroadcastStudio.jsx`)**:
   - Add Move Up ▲ and Move Down ▼ buttons to each source item in the Sources dock.
   - Dynamically re-order the `sources` array, controlling the z-index render hierarchy in the `<canvas>` compositor.

3. **Streamlabs Overlay Suite & Designer Modal (`frontend/src/components/BroadcastStudio.jsx`)**:
   - Add 5 new Streamlabs overlay source types: `overlay_frame` (Neon Cam Border), `ticker` (Recent Sub Banner), `alert_box` (Sub/Follower Alert), `image` (Custom Logo), `browser_url` (Browser Widget).
   - Build Streamlabs Overlay Designer modal for customizing neon themes (Cyan Glow, Cyberpunk Magenta, Gold Elite, Emerald Pro), custom text, and alert triggers.
   - Update 60 FPS HTML5 `<canvas>` compositor to draw overlays on top of game and cam layers.

4. **Ecosystem Parity & Version Bump (`v5.81.0`)**:
   - Update version badges across UI components.
   - Update master architectural ledger and ecosystem manual.
   - Persist versioned manual copy and update artifact history.
   - Create save point with keyword `RESUME_AIBS_STREAMLABS_OVERLAY_LAYERS_V581`.
   - Update chronologies and top-level index.

5. **Live Deployment**:
   - Re-build Vite frontend (`npm run build`) and deploy to Firebase Hosting (`ai-bs-dashboard.web.app`).
