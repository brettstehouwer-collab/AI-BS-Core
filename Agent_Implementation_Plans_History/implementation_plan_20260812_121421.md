# Unified Media Vault (Parent Module)

The goal is to create a new dedicated parent module (Master Hub) that automatically aggregates, categorizes, and beautifully displays all media (images, videos, 3D renders) generated anywhere within the AI-BS ecosystem.

## User Review Required

> [!IMPORTANT]
> **Module Placement:** I am proposing adding this as a completely new Top-Level "Master Hub" in the sidebar navigation called **"Media & Asset Vault"**. Does this sound good, or would you prefer it nested inside an existing hub like "Creator Studio"?

> [!NOTE]
> **Categorization Logic:** The backend will automatically categorize media based on file naming conventions (prefixes) from `C:\AI-BS\ComfyUI\ComfyUI\output`. I have defined several categories below. Let me know if you want any specific folder structures or naming rules adjusted.

## Proposed Changes

---

### Backend API (Data Aggregation)

#### [MODIFY] [AI_BS_Backend.py](file:///C:/AI-BS/backend/AI_BS_Backend.py)
- **Add new endpoint `GET /api/media-vault/all`**:
  - Scans `C:\AI-BS\ComfyUI\ComfyUI\output`.
  - Parses file extensions (`.png`, `.mp4`, `.webp`, `.gif`) and file sizes.
  - Groups files into logical categories based on prefixes:
    - **Commercial Assets:** `AI_BS_COMMERCIAL_`
    - **UltraHD Renders:** `AI_BS_UltraHD_`, `AI_BS_HD_`
    - **Cinematic Video (Wan2.1 / LTX):** `WanVideo_`, `LTX_Video_`, `Wan2_Tour_`
    - **Virtual Staging:** `VirtualStaged_`
    - **3D & Prototypes:** `AI_BS_3D_Model_`
    - **LoRA / Workflows:** `AI_BS_LoRA_Output_`, `AI_BS_Workflow_Gen_`
    - **Standard / Uncategorized:** `ComfyUI_`, `sample_`, `z-image-turbo_`
  - Returns a structured JSON payload with media metadata and routing URLs (`/api/comfy/media?filename=...`).

---

### Frontend Components (UI & Routing)

#### [NEW] [UnifiedMediaVaultTab.jsx](file:///C:/AI-BS/frontend/components/UnifiedMediaVaultTab.jsx)
- A new React component that acts as the dashboard for the vault.
- Implements a modern, dynamic UI with:
  - Sidebar or top-level pill navigation to filter by category.
  - Masonry grid layout for mixed aspect ratio images.
  - Hover-to-play support for video files.
  - Modal lightbox for viewing high-res media in full screen.

#### [NEW] [UnifiedMediaVaultTab.css](file:///C:/AI-BS/frontend/components/UnifiedMediaVaultTab.css)
- CSS for the Media Vault module (glassmorphism, vibrant active states, smooth grid animations, premium dark aesthetic).

#### [MODIFY] [navigationConfig.js](file:///C:/AI-BS/frontend/navigationConfig.js)
- Add a new master hub object for the `media_vault`.
- Map the sub-tab to `UnifiedMediaVaultTab.jsx`.

#### [MODIFY] [App.jsx](file:///C:/AI-BS/frontend/App.jsx)
- Import `UnifiedMediaVaultTab`.
- Add conditional rendering logic for `activeHub === 'media_vault'`.

## Verification Plan

### Automated Tests
- N/A

### Manual Verification
1. Open the AI-BS dashboard.
2. Click the new "Media & Asset Vault" icon in the sidebar.
3. Verify that all 190+ files currently in the ComfyUI output folder are loaded, categorized properly, and rendering visually.
4. Verify that video playback and full-screen image viewing works perfectly.
