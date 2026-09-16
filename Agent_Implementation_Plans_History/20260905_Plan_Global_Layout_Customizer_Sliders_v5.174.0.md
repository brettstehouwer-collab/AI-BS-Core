# Global CSS Layout & Typography Customizer with Real-Time Sliders

Add a comprehensive, program-wide layout customizer control center for AI-BS with interactive sliders and instant live feedback for:
1. **Text Size Scaling** (`--aibs-font-scale` / spot font sizing)
2. **Box & Card Size / Padding** (`--aibs-card-padding`, `--aibs-box-padding`, `--aibs-card-min-width`)
3. **Typography & Font Styles** (Outfit, Inter, Space Grotesk, JetBrains Mono, Dyslexic-friendly, Retro Neon)
4. **Border Radius & Glassmorphism Depth** (`--aibs-border-radius`, `--aibs-glass-blur`, `--aibs-border-glow`)
5. **Content Spacing & Grid Gap** (`--aibs-gap-scale`)

---

## User Review Required

> [!IMPORTANT]
> - **Persistent Configuration:** Layout customizations will persist automatically in `localStorage` under `aibs_layout_customizer_settings` with 1-click **Reset to System Defaults** and quick preset modes (*Compact Dense*, *Standard Balanced*, *Ultra Spacious*, *High Readability*, *Cyber Neon*).
> - **Global CSS Variable Injection:** Injected dynamically into `:root` and `.app-shell` so that all 32+ tabs, subinterfaces, chat bubbles, cards, buttons, sidebars, and panels adapt live in real time.
> - **Dedicated Floating Quick HUD + Top Navbar Button:** Accessible via a `🎨 Layout Sliders` button on the top navigation bar and a sleek collapsible floating widget with real-time slider controls and instant preview.

---

## Proposed Changes

### Frontend Design System & CSS Variables

#### [MODIFY] [index.css](file:///C:/AI-BS/frontend/src/index.css) & [frontend/style.css](file:///C:/AI-BS/frontend/style.css)
- Define standard dynamic CSS variables in `:root`:
  - `--aibs-font-scale`: Default `1` (range `0.75` to `1.5`)
  - `--aibs-card-padding`: Default `24px` (range `10px` to `48px`)
  - `--aibs-box-radius`: Default `16px` (range `0px` to `32px`)
  - `--aibs-gap-scale`: Default `20px` (range `8px` to `40px`)
  - `--aibs-glass-blur`: Default `16px` (range `0px` to `32px`)
  - `--aibs-glass-opacity`: Default `0.6` (range `0.2` to `0.95`)
  - `--aibs-primary-font`: Default `'Outfit', 'Inter', sans-serif`
- Bind existing `.glass-card`, `.tab-container`, `.message-bubble`, `.glass-panel`, `.adv-kpi-card`, and typography classes to consume these CSS variables dynamically.

---

### Component Architecture

#### [NEW] [GlobalLayoutCustomizerModal.jsx](file:///C:/AI-BS/frontend/src/components/GlobalLayoutCustomizerModal.jsx) (and mirror in `frontend/components/`)
- Interactive layout control panel featuring:
  - **Live Sliders:**
    - 🔤 Base Font Size / Scale (`75%` – `150%`)
    - 📦 Box & Card Internal Padding (`10px` – `48px`)
    - 📐 Corner Roundness / Border Radius (`0px` – `32px`)
    - ↔️ Grid & Component Spacing / Gap (`8px` – `40px`)
    - 🪟 Glassmorphism Blur Depth (`0px` – `32px`)
    - 🎨 Background Glass Opacity (`20%` – `95%`)
  - **Font Style Selector (with live preview):**
    - Outfit (Modern Geometric)
    - Inter (Clean Corporate)
    - Space Grotesk (Tech Editorial)
    - JetBrains Mono (Code / Hacker)
    - OpenDyslexic / Lexend (Maximum Legibility)
  - **1-Click Presets:**
    - ⚡ *Compact Pro* (Dense tables, small padding, max screen real estate)
    - ⚖️ *Standard Balanced* (Default AI-BS aesthetic)
    - 🌌 *Ultra Spacious* (Generous padding & relaxed margins)
    - 👓 *Big Text & Focus* (Elevated font scaling & contrast)
    - 🔮 *Cyber Neon* (Sharp corners, heavy glass blur & vivid borders)
  - **1-Click Reset to Default**

#### [MODIFY] [TopNavbar.jsx](file:///C:/AI-BS/frontend/src/components/TopNavbar.jsx) & [frontend/components/TopNavbar.jsx](file:///C:/AI-BS/frontend/components/TopNavbar.jsx)
- Add the `🎨 Layout & Sliders` trigger button to the Top Navigation ribbon.
- Mount the `GlobalLayoutCustomizerModal`.

#### [MODIFY] [App.jsx](file:///C:/AI-BS/frontend/App.jsx)
- Initialize and inject saved layout CSS variable overrides onto `document.documentElement.style` on startup and state changes.

---

## Verification Plan

### Automated / Build Tests
- Execute `npm run build` from `C:\AI-BS\frontend` to ensure 0 syntax errors or bundling warnings.
- Deploy to Firebase Hosting (`firebase deploy --only hosting --non-interactive`) per project rules.

### Manual Verification
- Test all 6 slider channels (Font Size, Box Padding, Border Radius, Gap Spacing, Glass Blur, Opacity) in the UI.
- Verify that changes apply live across Command Center, BS-Chat, System Health, and Industry Hubs.
- Test 1-click presets and the Reset to Default button.
- Verify persistence in `localStorage` across page refreshes.
