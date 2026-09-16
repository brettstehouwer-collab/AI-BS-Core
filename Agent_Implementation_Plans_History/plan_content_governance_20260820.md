# Implementation Plan - Risk-Weighted Sentiment & Compliance Scoring System (Content Governance Engine)

Implement a Quantifiable Risk Scoring (QRS) tool powered by `aibs_reasoning_engine.py` and `aibs_autograd_engine.py` for corporate communications, email drafting, ad campaigns, and executive correspondence.

## Proposed Changes

### Backend Engine & API Layer

#### [MODIFY] [aibs_reasoning_engine.py](file:///C:/AI-BS/backend/aibs_reasoning_engine.py)
- Implement `AIBSRiskGovernanceEngine` class:
  1. **Semantic Vector Mapping**: Evaluates text across 6 core risk vectors:
     - Litigation & Legal Liability Risk
     - Harassment & HR Policy Risk
     - PR & Sociocultural Polarization Risk
     - Discriminatory & Bias Sentiment
     - Confidentiality & Data Breach Risk
     - Aggressive & High-Conflict Tone
  2. **Contextual Weighting Matrix**: Applies dynamic multipliers based on Context Category (HR, Legal, Marketing, Sales, Executive) and Target Audience (Internal Staff, External Client, Public Press Release, Executive Board).
  3. **Quantifiable Risk Scoring ($S_f$)**: Computes $S_f = \sum (Risk\_Vector_i \times Context\_Weight_{ij})$ normalized to 0-100%.
  4. **Dynamic Thresholding ($\tau$)**: Compares $S_f$ against configurable threshold $\tau$ (default 45%) to trigger `SAFE`, `CAUTION`, or `DANGER ZONE / RED FLAG`.
  5. **Terminology Optimization Engine**: Generates professional/technical terminology refinements ("Original Casual" -> "Refined Executive") to de-risk correspondence before dispatch.

#### [NEW] [content_governance_router.py](file:///C:/AI-BS/backend/routers/content_governance_router.py)
- Build FastAPI router endpoints:
  - `POST /api/v1/content-governance/analyze`: Accepts `{ text, context_category, target_audience, custom_threshold }` and returns complete vector scores, risk level, heat map data, and phrasing recommendations.
  - `GET /api/v1/content-governance/categories`: Returns supported audience and category presets with default weights.

#### [MODIFY] [AI_BS_Backend.py](file:///C:/AI-BS/backend/AI_BS_Backend.py)
- Import and register `content_governance_router`.

---

### Frontend UI Tool Layer

#### [NEW] [ContentGovernanceRiskModal.jsx](file:///C:/AI-BS/frontend/components/ContentGovernanceRiskModal.jsx) & [ContentGovernanceRiskModal.css](file:///C:/AI-BS/frontend/components/ContentGovernanceRiskModal.css)
- Build full-featured modal & standalone review suite:
  - Text area input with live auto-analysis or manually triggered "🛡️ Audit & Analyze Risk" button.
  - Context & Audience Selectors (Internal, External, Public Press Release, Executive Board).
  - Risk Meter & Gauge ($S_f$ score indicator with color-coded status pills: Green `SAFE`, Yellow `CAUTION`, Red `DANGER ZONE / RED FLAG`).
  - Radar / Vector Bar Breakdown for the 6 risk categories.
  - Interactive Threshold Slider ($\tau$) allowing real-time sensitivity adjustments.
  - Terminology Refinement HUD showing "Original Phrasing" vs "Refined Phrasing" with a 1-click "Replace & Apply" button.

#### [MODIFY] [EmailClientTab.jsx](file:///C:/AI-BS/frontend/components/EmailClientTab.jsx)
- Add `"🛡️ Compliance & Risk Review"` action button to the email compose window. Clicking opens `ContentGovernanceRiskModal` pre-populated with draft email text, allowing instant analysis before sending.

#### [MODIFY] [AdvertisingTab.jsx](file:///C:/AI-BS/frontend/components/AdvertisingTab.jsx)
- Add `"🛡️ Ad Risk & Policy Check"` button in the Campaign Generator tool to audit ad copy against public PR & compliance thresholds.

#### [MODIFY] [DefinitionsModuleTab.jsx](file:///C:/AI-BS/frontend/components/DefinitionsModuleTab.jsx)
- Add interactive "🛡️ Risk Scoring Engine (Content Governance)" card & live demonstration module into the Jargon & Architectural Tools section.

#### [MODIFY] [SimpleDashboardPortal.jsx](file:///C:/AI-BS/frontend/components/SimpleDashboardPortal.jsx)
- Add quick-launch tool tile for "Content Risk Governance Engine" under Stehouwer Publishing tools.

---

## User Review Required

> [!NOTE]
> The Content Governance Engine runs entirely locally using `aibs_reasoning_engine.py` and local NLP heuristics without external API costs, strictly adhering to AI-BS cost constraints.

## Verification Plan

### Automated Tests
- Test backend endpoint:
  ```powershell
  powershell -Command "Invoke-RestMethod -Uri 'http://127.0.0.1:8000/api/v1/content-governance/analyze' -Method Post -ContentType 'application/json' -Body '{\"text\":\"We need sensitivity analysis when sending things over threshold of sensitivity for redflags\",\"context_category\":\"marketing\",\"target_audience\":\"external_client\"}'"
  ```

### Manual Verification
- Launch Vite dev server and open `http://localhost:5173`.
- Open `EmailClientTab`, draft a message, and click `"🛡️ Compliance & Risk Review"` to verify real-time vector scoring, threshold triggers, and 1-click terminology refinement replacement.
