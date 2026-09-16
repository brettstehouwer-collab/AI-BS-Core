# AI Media Assistant & Auto-Tool Orchestration

You requested an automatic tool-selection helper that leverages NLP to orchestrate the best tool types, automatically applying adjustments based on your vision, and allowing continuous conversational iteration. 

We will build an **Intelligent Media Assistant** directly into the Banquet Architect Studio (and architected to be reusable for other media tools).

## Open Questions
> [!NOTE]
> 1. **LLM Dependency:** Since this requires real-time tool selection (JSON function calling), we need an LLM capable of structured output. Given our strict free/local constraints, should I hook this directly into the existing `stehouwer_llm` local Ollama routing, or do you have a specific local model you prefer for JSON function calling (e.g., `qwen2.5-coder` or `llama3.1`)?
> 2. **UI Placement:** Should this Assistant be a floating chat widget inside the Banquet Architect Studio, or should it replace the manual sliders entirely with a conversational interface?

## Proposed Changes

---

### Frontend Framework
#### [MODIFY] [BanquetArchitectTab.jsx](file:///C:/AI-BS/frontend/components/BanquetArchitectTab.jsx)
- **Conversational Interface:** Add a sleek "AI Studio Assistant" chat panel to the UI.
- **State Auto-Binding:** The assistant will return structured JSON commands (e.g., `{"action": "SET_STYLE", "value": "tuscan"}`) instead of just text. The React component will parse these commands and automatically update the `tableCount`, `floralColor`, `lightingRig`, and `stylePreset` state variables.
- **Auto-Triggering:** If the NLP engine determines the user's intent is to generate a new 2D image or push to the 3D Unreal engine, it will automatically trigger the `handleGenerate2D()` or `handleSyncToUnreal()` functions on your behalf.

---

### Backend Logic & NLP
#### [NEW] `handle_media_assistant_nlp` in [demo_noto.py](file:///C:/AI-BS/backend/demo_noto.py)
- We will build an NLP pipeline (utilizing the `AIBSHybridNLPParser` and `spaCy` we built previously) to parse the user's natural language request.
- The NLP engine will map the request against available tools:
  - `UPDATE_2D_PROMPT`: Modifies the underlying descriptive prompt.
  - `SET_3D_ENVIRONMENT`: Adjusts tables, lighting, and floral colors.
  - `TRIGGER_RENDER`: Fires off the ComfyUI API.
  - `SYNC_UNREAL`: Fires the Web Remote Control API.
- It returns both a conversational reply ("I've adjusted the room for a corporate gala at 25 tables...") and the executable JSON payload.

#### [MODIFY] [demo_noto_router.py](file:///C:/AI-BS/backend/demo_noto_router.py)
- Add the `/api/v1/demos/noto/media-assistant` endpoint to route these conversational requests.

## Verification Plan
### Automated Parsing Tests
- I will simulate complex prompts (e.g., "Actually, let's do an elegant setup with 15 tables and warm lighting, then render it.") and verify the backend correctly decomposes this into multiple JSON tool actions.

### Manual Verification
- You will be able to type "Change to 30 tables" in the Assistant box, and watch the UI slider automatically slide to 30 and the system automatically push the command to Unreal Engine.
