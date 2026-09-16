# Hybrid Pro Export Options (Raw Metadata vs Baked Proxy)

This document outlines the architectural plan to support multiple export needs: translating the `@xyflow/react` node graph as raw serialized XML filters, versus baking the output into a proxy file.

## User Review Required

> [!IMPORTANT]
> To include the Node Graph in the export payload, we must lift the state out of `NodeCompositor.jsx` and into the global `dawStore.js`. This will allow the main transport bar to read the active nodes and edges. Is this acceptable?

## Open Questions

> [!WARNING]
> 1. **Proxy Baking Mechanism:** Currently, BS-Studio exports MP4s via the `/api/video/export_master` endpoint. Do you want the "Baked Proxy" option to trigger a full `ffmpeg` render on the backend before generating the FCPXML, or should it trigger an HTML5 `<canvas>` recording on the frontend and upload that as the proxy?
> 2. **FCPXML Filter Support:** Native FCPXML supports standard color correction and blurs, but complex AI Generative Fill nodes do not have an equivalent in standard NLEs (Premiere/Resolve). For "Raw Metadata" export, should we ignore AI nodes, or drop them in as disabled placeholder clips?

## Proposed Changes

---

### `dawStore.js` (Frontend State)

Move the `NodeCompositor` state to the global store so it can be bundled in the export payload.

#### [MODIFY] [dawStore.js](file:///C:/AI-BS/frontend/src/components/daw/dawStore.js)
- Add `compositorNodes` and `compositorEdges` to the zustand state.
- Add `setCompositorNodes` and `setCompositorEdges` actions.

---

### `NodeCompositor.jsx` (Frontend UI)

#### [MODIFY] [NodeCompositor.jsx](file:///C:/AI-BS/frontend/src/components/daw/NodeCompositor.jsx)
- Remove local `useState` for nodes and edges.
- Bind `nodes` and `edges` directly to `useStore(state => state.compositorNodes)`, etc.

---

### `MusicDAWStudioTab.jsx` (Frontend UI)

#### [MODIFY] [MusicDAWStudioTab.jsx](file:///C:/AI-BS/frontend/src/components/daw/MusicDAWStudioTab.jsx)
- Update the Pro Export dropdown to include specific intention flags:
  - `fcpxml_raw` (Raw + Metadata)
  - `fcpxml_baked` (Baked Proxy Render)
  - `aaf_raw`
  - `aaf_baked`
- Bundle the `compositorNodes` into the `payload` sent to `/api/export/timeline`.

---

### `export_router.py` (Backend Router)

#### [MODIFY] [export_router.py](file:///C:/AI-BS/backend/routers/export_router.py)
- Accept `compositorNodes` in the `ExportPayload` model.
- If `mode` contains `raw`: Parse `compositorNodes` and generate FCPXML `<filter>` tags attached to the clips (e.g., `<filter id="Color Board">` for ColorTransforms, `<filter id="Gaussian">` for Blurs).
- If `mode` contains `baked`: Trigger the proxy render pipeline (invoke `ffmpeg` or wait for canvas upload), and link the resulting proxy file into the FCPXML `<asset>` tag instead of building a raw sequence spine.

## Verification Plan

### Automated Tests
- N/A

### Manual Verification
1. Export a timeline using "Raw Metadata" and inspect the generated `.fcpxml` file to verify `<filter>` tags are present for Color and Blur nodes.
2. Verify that `NodeCompositor.jsx` still functions correctly after migrating state to `dawStore.js`.
