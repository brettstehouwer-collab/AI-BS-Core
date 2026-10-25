# AI-BS interface organization and modernization

Status: potential future track, deferred until the current six-phase functional plan and its required release checks are complete. This records the user's request and preliminary recommendations; it does not authorize starting a redesign now or add a new completion requirement to the existing six-phase goal.

## User goal

Make the entire AI-BS experience feel organized, distinctive and modern. Address crowded, clustered controls across the site and related applications while retaining the system's capabilities. BS-Chat remains the central monitoring and execution workspace. Preserve documents, screenplay projects, saved work, customized models, permissions, shortcuts and working integrations.

## Preliminary evidence, not a whole-site visual audit

- `frontend/main.jsx` imports `frontend/src/index.css`; that shared stylesheet is active at the web entry point.
- The inspected stylesheet has 1,470 lines, 67 `!important` occurrences, two `:root` blocks and 11 backdrop-filter declarations. Counts alone do not prove bugs or poor performance. Some overrides intentionally support readability.
- Global CSS defines purple/cyan glass-style tokens and configurable layout/typography variables. `frontend/tailwind.config.js` separately defines blue/slate surfaces, typography and semantic status colors. Both provide useful foundations; their relationship needs to be made consistent.
- `frontend/App.jsx` imports `components/Sidebar.jsx`, `TopNavbar.jsx`, `MobileBottomNav.jsx`, `MobileNavDrawer.jsx` and the global layout customizer. Sidebar styling also uses inline declarations. Existing navigation, command search, simple/pro settings and readability options should be reused where they work.
- `frontend/src/layouts/DashboardLayout.jsx` exists with another navigation vocabulary, but its active use was not established in this review. A file named `components/Layout.jsx` contains specialized venue UI; filenames alone do not establish duplicate app shells or disposable code.
- Earlier user screenshots show several navigation/action/status rows competing for attention. The preliminary concern is information hierarchy and density, not a demonstrated failure of every tool. Native application styling and every screen still require their own later audit.

## Recommended organization

1. **One global shell.** A compact header for identity, search and essential system state; one grouped sidebar for workspaces; one contextual toolbar for the selected workspace. Keep local subtabs within that workspace instead of adding more global control bars.
2. **Group by the work being done.** Proposed groups to test against the actual inventory: Build/BS-Chat, Creative Production, Business/Clients, Automation/Operations, and System/Security. Keep every current route/action reachable. Map existing labels, deep links and public/client portals before changing navigation.
3. **Favorites and All Tools.** Put frequently used actions in user-controlled favorites. Keep a searchable complete tool directory and command palette. Consolidate duplicate shortcuts to the same action after mapping their actual handlers; retain specialized workflows.
4. **Clear action hierarchy.** Give each screen a clear primary task. Keep common actions visible; place diagnostics and infrequent advanced controls in labeled panels. Keep cancellation, errors, access requirements and current execution environment easy to find. Do not turn an unverified capability into a green status badge.
5. **Calmer visual hierarchy.** Use consistent spacing, readable type, intentional panel sizes and less persistent decorative emphasis. Preserve an AI-BS identity through a restrained purple/cyan brand treatment rather than giving every button a different accent. Reserve status colors for consistent meanings.
6. **Responsive layouts.** Organize phone, laptop, large-display and native views intentionally. Test scrolling, mobile keyboards, docking, zoom and touch targets; do not rely on horizontal overflow to expose essential controls. Preserve high-legibility/Mom View and keyboard navigation.

## CSS and component direction

Create one agreed design-token vocabulary for colors, spacing, typography, surfaces, borders, focus states and stacking order, mapped into the existing CSS/Tailwind system. Gradually replace scattered values and broad overrides with shared components and workspace-scoped styles. Inventory active imports and mirrors before consolidating files; preserve required mirrors and archived before-images. No blanket CSS rewrite or framework replacement is selected.

Retain native application toolkits and apply equivalent visual standards through platform-appropriate theme adapters. CSS governs the web UI; a web stylesheet is not itself a native-Windows redesign. Public/client portals should have appropriate task-focused navigation and preserve their access boundaries, rather than exposing administrator controls.

## Protect the Creation Studio

Keep application chrome typography separate from screenplay/page formatting. Preserve the editor's element styles, Courier-based document requirements, indentation, pagination, keyboard flow, project save paths, autosave, SQLite/disk records and import/export behavior. Verify known manuscript copies, PDF/DOCX/print references and keyboard workflows before/after changes. Do not change or migrate original documents to achieve a visual redesign.

Preserve saved layout preferences, navigation state, drafts, chat histories and accessibility settings. If preferences require migration, retain their original serialized values and provide rollback. Do not clear browser storage as a design cleanup.

## Later delivery sequence

1. Inventory screens, actions, routes, actual component imports, role-specific views and user workflows; mark verified behavior and unresolved dependencies.
2. Present a few concrete design directions and desktop/mobile/native layout prototypes for the user's visual review.
3. Establish tokens and shared components, then pilot the global shell and one workspace.
4. Migrate remaining workspaces incrementally, preserving routes, features, permissions, documents and rollback snapshots.
5. Check accessibility, responsiveness, performance and feature parity; release each verified platform with correct versions and a rollback path.

Start with organization and a navigation/density pass; determine from the inventory whether a complete visual overhaul is warranted. Do not delete source, storage, media or documents under the label of UI cleanup. Any broader file/store consolidation requires a separate reviewed inventory that distinguishes originals, required mirrors, backups and genuinely redundant paths.

Current action: planning/source inspection only. No CSS, live navigation, layout preference, document, native binary or deployed website was changed for this request.
