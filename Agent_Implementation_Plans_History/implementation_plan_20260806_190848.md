# Unreal Engine Asset Integration Plan

This plan details how the 5,263 discovered Unreal Engine assets will be integrated globally across AI-BS, allowing any tool (including Banquet Architect) to access, search, and utilize them.

## Proposed Architecture

1. **Global Asset Registry Database (`unreal_assets.db`)**
   - We will write a Python ingestion script (`ingest_unreal_assets.py`) that reads `C:\AI-BS\all_unreal_assets.txt`.
   - The script will extract the asset name, infer its type (e.g. Material, Blueprint, StaticMesh) based on its path, and insert it into a lightweight SQLite database: `C:\AI-BS\backend\unreal_assets.db`.

2. **Backend Search API (`unreal_asset_router.py`)**
   - Create a new API router in the backend exposing `GET /api/v1/assets/unreal/search`.
   - Supports query parameters for `keyword`, `asset_type`, and `limit`.
   - Update `AI_BS_Backend.py` to mount this new global router.

3. **Frontend / Generation Tool Integration**
   - Update **BanquetArchitectTab.jsx** (as an initial implementation) to use this global registry. 
   - Instead of hardcoded dropdowns/checkboxes for "Spawn Actors" and "Materials", we will introduce a **Dynamic Asset Browser**. This UI will allow the user to search the 5,000+ assets live and select them for spawning or material overrides.
   - The AI Assistant (NLP Orchestrator) in `demo_noto.py` will also be updated so it can optionally perform a backend DB lookup if the user asks for a very specific asset in natural language (e.g., "Add the default mannequin").

## Open Questions

> [!WARNING]
> Please confirm the following design decisions before execution:
> 1. **Dynamic UI:** Is it acceptable to replace the current hardcoded checkboxes in Banquet Architect with a searchable autocomplete field that queries the live database?
> 2. **AI Action Workflow:** Do you want the AI Media Assistant to *automatically* search the database behind the scenes when a user asks for something, or just rely on the user picking it from the search UI? (Auto-searching behind the scenes adds ~200ms latency but is more "magical").

## Verification Plan
- Run the ingestion script and verify `unreal_assets.db` contains exactly 5,263 rows.
- Hit the `/api/v1/assets/unreal/search?keyword=Material` endpoint to ensure fast (<50ms) search times.
- Verify in Banquet Architect that searching for an asset returns accurate results from the database.
