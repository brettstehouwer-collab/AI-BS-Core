# Tasks: Local ComfyUI Suite Upgrade (Freedom, Img2Img, & Interrogation)

- [x] Update `backend/tools/tool_registry.py` to remove stylistic bans (`cartoon`, `anime`, `illustration`, `3d sketch`) and forced metal prompts from `generate_comfy_image` <!-- id: 0 -->
- [x] Add `generate_comfy_img2img` tool in `backend/tools/tool_registry.py` with `LoadImage` -> `VAEEncode` -> `KSampler` workflow <!-- id: 1 -->
- [x] Add `interrogate_image` / `extract_image_prompt` tool in `backend/tools/tool_registry.py` utilizing local computer vision to generate structured tags <!-- id: 2 -->
- [x] Overhaul `detect_tool_intent` and `clean_tool_prompt` in `backend/core/hybrid_reasoning_engine.py` and `backend/AI_BS_Backend.py` with regex support for text-to-image, img2img, and interrogation <!-- id: 3 -->
- [x] Update `backend/core/sovereign_reasoning/dispatcher.py` (`stehouwer_system_prompt`), `backend/models/stehouwer_llm.Modelfile`, and `aibs_personal_intelligence.db` with unrestricted sovereign creative directives <!-- id: 4 -->
- [x] Run programmatic verification of intent routing, img2img payload structure, and prompt interrogation <!-- id: 5 -->
- [x] Sweep frontend UI version badge to `v5.225.0`, compile build, and deploy to Firebase Hosting <!-- id: 6 -->
- [x] Synchronize Master Architectural Ledger (`AI_BS_MASTER_ARCHITECTURAL_LEDGER.md`), Ecosystem Manual (`docs/AI_BS_MASTER_ECOSYSTEM_MANUAL.md`), and Master Historical Chronologies <!-- id: 7 -->
