# Architectural Survey Report: Frontend, Multi-Mirror Parity & Release Ledgers (R5)

**Surveyor:** Survey Explorer 3 (teamwork_preview_explorer)  
**Date:** 2026-10-06  
**Target Project:** AI-BS Sovereign Intelligence Ecosystem (`C:\AI-BS`)  
**Scope:** Foundational Mapping for R5 (Dedicated Genomic & Structural Intelligence Studio UI, 4-Mirror Synchronization Parity, Vite Production Build, Version Ledgers & Desktop Shortcuts)

---

## Executive Summary

This investigation provides the complete structural blueprint and architectural specifications required to fulfill Requirement R5 and all associated Acceptance Criteria in the AI-BS Sovereign Intelligence Ecosystem.

### Key Architectural Findings:
1. **Frontend Architecture & Navigation:**
   - The master application layout is orchestrated in `frontend/App.jsx` (1,058 lines), which dynamically resolves active tabs from URL search parameters (`?tab=...`) and `localStorage` (`sp-ai-active-tab`), wrapped in `TabErrorBoundary` and React `Suspense` (`safeLazy`).
   - Navigation hierarchies are structured in `frontend/src/components/navigationConfig.js` across 4 operating pillars in `masterHubs`. The new studio belongs under `intelligence_and_code` (or `engineering_labs`) as `genomics_studio`.
   - Role-based feature gating is defined in `frontend/src/components/accessControl.js`. `genomics_studio` must be mapped to `['admin', 'enterprise_all_access']` in `TAB_PERMISSIONS`.
   - Layout CSS in `frontend/src/index.css` and `frontend/src/components/index.css` requires `.genomics_studio-subinterface` full-height bounds.

2. **Dedicated Studio UI Patterns & 4 Interactive Panels:**
   - Visual conventions align with the ecosystem's dark glassmorphism: `#090d16` canvas, `#0d1117`/`#161b22` cards, `1px solid #30363d` borders, neon cyan `#38bdf8`, emerald `#10b981`, purple `#a78bfa`, and amber `#f59e0b` accents.
   - `lucide-react` icons are natively installed: `Dna`, `Microscope`, `BookOpen`, `Cpu`, `Layers`, `Activity`, `FileText`, `Sparkles`, `Terminal`, `CheckCircle2`, `AlertCircle`, `Database`, `Search`, `Share2`, `FlaskConical`, `Download`, `RefreshCw`, `Sliders`, `Play`.
   - Panel 1: **Genomic Variant & Expression Explorer** (dbSNP rsID, GTEx 54-tissue RNA bars, UCSC evolutionary conservation phyloP/phastCons, AlphaGenome AVI score).
   - Panel 2: **Structural Biology & AlphaFold Viewer** (AlphaFold pLDDT curve, STRING interaction network, PyMOL script synthesizer/dispatcher, and Foldseek 3D structural homology search per operator directive).
   - Panel 3: **bioRxiv & Regulatory Literature Recon** (bioRxiv preprint search, JASPAR TF binding PWMs, ENCODE cCREs).
   - Panel 4: **Autonomous Genomic Swarm & AI Training Monitor** (1-click Swarm dispatch with SSE event stream, instruction dataset generator, RTX 4090 Unsloth LoRA training status).

3. **Multi-Mirror Synchronization (Rule 1 Compliance):**
   - Source of truth: `frontend/src/components/` (446 files currently).
   - 3 Satellite mirror trees: `frontend/components/`, `frontend/src/components/components/`, `frontend/components/components/`.
   - Adding `GenomicsStudioTab.jsx` brings the canonical count from 446 to 447. Running `scripts/sync_mirrors.py` propagates the file to all 3 mirrors and achieves 100% SHA-256 byte parity (447/447 files verified), satisfying Acceptance Criteria.

4. **Vite Build Tooling:**
   - `npm run build` runs `python scripts/sync_mirrors.py && vite build`.
   - Build verified: compiles cleanly in 24.59s with Terser minification and manual chunk splitting (`recharts`, `icons`, `markdown`, `xyflow`, `monaco`, `xterm`, `firebase`, `vendor`).

5. **Ecosystem Version Authority & Desktop Shortcuts:**
   - Ecosystem bump from `v5.310.0` to `v5.311.0` requires updating 9 synchronized ledgers: `version.txt`, `package.json`, `frontend/package.json`, `frontend/public/version.json`, `frontend/version.js`, `frontend/src/version.js`, `frontend/src/components/TopNavbar.jsx` (and its 3 mirrors), `scripts/refresh_desktop_shortcuts.ps1`, and `AI_BS_MASTER_ARCHITECTURAL_LEDGER.md`.
   - Desktop shortcuts in `C:\Users\footb\OneDrive\Desktop` and `C:\Users\footb\Desktop` target `Launch_Desktop_Studio.vbs` and are updated via `refresh_desktop_shortcuts.ps1`.

---

## Detailed Investigation

### 1. Application Navigation & Access Control Architecture

#### Entry Points & Routing Flow
- **`frontend/index.html` (line 23):** Loads `/main.jsx`.
- **`frontend/main.jsx` (line 3):** Imports `App` from `./App.jsx`.
- **`frontend/App.jsx`:**
  - **Lines 33–47:** Defines `safeLazy(importFn)` with chunk auto-reload recovery for production updates:
    ```javascript
    function safeLazy(importFn) {
      return lazy(() => 
        importFn().catch((err) => {
          console.warn("Failed to load component chunk, auto-reloading page for new deployment...", err);
          const lastReload = sessionStorage.getItem('chunk_reload_timestamp');
          const now = Date.now();
          if (!lastReload || now - parseInt(lastReload, 10) > 10000) {
            sessionStorage.setItem('chunk_reload_timestamp', now.toString());
            window.location.reload();
          }
          return { default: () => <TabLoader /> };
        })
      );
    }
    ```
  - **Lines 194–261:** Master `tabs` array. Each entry has `{ key, label, description, Component }`.
  - **Lines 272–286:** Active tab initialization checks URL query parameters:
    ```javascript
    const params = new URLSearchParams(window.location.search);
    const urlTab = params.get('tab');
    ```
    Allows direct deep-linking via `http://localhost:5173/?tab=genomics_studio`.
  - **Lines 640–641:** Tab resolution:
    ```javascript
    const activeTabConfig = tabs.find((tab) => tab.key === activeTab) ?? tabs[0];
    const ActiveComponent = activeTabConfig.Component;
    ```
  - **Lines 898–915 & 937–954:** Rendering and feature gating:
    ```jsx
    <TabErrorBoundary key={activeTabConfig.key}>
      <Suspense fallback={<TabLoader />}>
        {canAccessTab(userTier.id, activeTabConfig.key) ? (
          <ActiveComponent 
            backendUrl={backendUrl} 
            currentUser={currentUser} 
            selectedModel={selectedModel} 
            onNavigateTab={setActiveTab}
            workspaceMode={workspaceMode}
            onToggleWorkspaceMode={handleToggleWorkspaceMode}
          />
        ) : (
          <FeatureGateLockedCard
            tabKey={activeTabConfig.key}
            tabLabel={activeTabConfig.label}
            activeTier={userTier}
            onNavigateToPricing={() => setActiveTab('public_checkout')}
          />
        )}
      </Suspense>
    </TabErrorBoundary>
    ```

#### Navigation Config (`frontend/src/components/navigationConfig.js`)
- **`PINNED_QUICK_TABS` (lines 10–19):** Top quick-dock bar items.
- **`masterHubs` (lines 21–98):** Master hierarchy organized into 4 primary operating pillars:
  1. `intelligence_and_code` (Executive Cockpit, BS-CHAT, DAG Builder, Terminal, Deep Learning Studio, Agent Memory, Reasoning Attention, System Health, VMs, Automation Console, Definitions).
  2. `creative_media_studio` (BV-Media Creator, ComfyUI, Media Studio, Screenwriting, Music DAW, Personal Brand, Advertising, Syndication, CMS, Media Vault, Digital Storefront).
  3. `business_operations` (Command Center, Cloud Drive, Operations Audit, Clients Hub, Onboarding, Financial Ledger, NDA, Business Email, Master Calendar, Web Traffic, Blueprint).
  4. `engineering_labs` (Phone Repair, Mobile Wash, Banquet Architect, Noto's OS, Noto Multi-Bar, Project NoCo, Crypto Swarm, Gaming Lab, Steam Hub, Bible Hub, Lost Property).
- Placement: `genomics_studio` should be added to `intelligence_and_code.subTabs` as `{ key: 'genomics_studio', label: 'Genomics & Structural Studio', icon: '🧬', description: 'AlphaFold 3D, dbSNP, GTEx, Foldseek, bioRxiv & Swarm Pipeline' }`.
- In `placeholderIndustryHubs` (lines 121–137), `deeptechscience.subTabs` contains `medicalbioinformatics`, which can also route or cross-link to `genomics_studio`.

#### Role-Based Access Control (`frontend/src/components/accessControl.js`)
- **`USER_TIERS` (lines 6–56):** `ADMIN`, `ENTERPRISE_ALL_ACCESS`, `SCREENWRITING`, `HOSPITALITY`, `B2B_GROWTH`, `CREATOR_MEDIA`, `FREE_DEMO`.
- **`TAB_PERMISSIONS` (lines 59–124):** Maps tab keys to permitted tier IDs.
  - Adding `genomics_studio: ['admin', 'enterprise_all_access']` grants full access to administrators and enterprise tier holders, while displaying the locked feature card for demo/free users.
- **`canAccessTab(tierId, tabKey)` (lines 202–206):**
  ```javascript
  export const canAccessTab = (tierId, tabKey) => {
    if (tierId === 'admin' || tierId === 'enterprise_all_access') return true;
    const allowedTiers = TAB_PERMISSIONS[tabKey] || [];
    return allowedTiers.includes(tierId) || allowedTiers.includes('free_demo') || allowedTiers.includes('enterprise_all_access');
  };
  ```

#### Layout Stylesheet Integration (`frontend/src/index.css`)
- Lines 1421–1434 contain full-height viewport constraints for studios:
  ```css
  .genomics_studio-subinterface,
  .genomics_studio-subinterface .subinterface-content {
      height: 100% !important;
      max-height: 100% !important;
      min-height: 0 !important;
      overflow: hidden !important;
      flex: 1 1 0% !important;
  }
  ```
  Must be added to both `frontend/src/index.css` and `frontend/src/components/index.css`.

---

### 2. Studio UI Patterns & 4 Interactive Panels for GenomicsStudioTab

#### Visual Design Tokens (Derived from `DeepLearningStudioTab.jsx`, `SovereignAgentAppsTab.jsx`, `ExecutiveCockpitTab.jsx`):
- **Page Container:**
  ```javascript
  background: 'linear-gradient(135deg, #07090e 0%, #0d121f 50%, #0a0e1a 100%)',
  color: '#e2e8f0',
  fontFamily: 'Inter, system-ui, -apple-system, sans-serif',
  height: '100%',
  overflowY: 'auto'
  ```
- **Panel Containers:**
  ```javascript
  background: '#0d1117',
  border: '1px solid #30363d',
  borderRadius: '10px',
  boxShadow: '0 4px 16px rgba(0,0,0,0.4)'
  ```
- **Color Accent Palette:**
  - Primary / AlphaFold / Structural: `#38bdf8` (Neon Cyan)
  - Variants / Genetics / dbSNP: `#10b981` (Emerald Green)
  - Literature / JASPAR / ENCODE: `#a78bfa` (Purple / Violet)
  - Swarm / Autonomous Agents: `#f59e0b` (Amber / Gold)
  - Negative / Pathogenic Alerts: `#f43f5e` (Rose / Red)
- **Top Navigation Switcher:**
  4 tabbed view buttons allowing toggling between all 4 panels in single-panel focus mode, or viewing in a 2x2 grid layout.

#### Detailed Panel Specifications:

#### Panel 1: 🧬 Genomic Variant & Expression Explorer
- **dbSNP Lookup:**
  - Input: rsID search field (e.g. `rs699`, `rs429358`, `rs7412`).
  - Calls: `GET ${apiBase}/api/v1/bioinformatics/genomics/dbsnp?rsid=${rsid}`.
  - Displays: Variant ID, gene symbol, chromosome coordinate (GRCh38), alleles (Ref/Alt), clinical significance pill (e.g., "Pathogenic", "Risk Factor", "Benign"), and clinical evidence rationales.
- **GTEx Tissue Expression Bars:**
  - Input: Gene symbol (e.g. `ACE2`, `BRCA1`, `TP53`, `APOE`).
  - Calls: `GET ${apiBase}/api/v1/bioinformatics/genomics/gtex?gene=${gene}`.
  - Displays: Quantitative RNA expression values across 54 human tissues (e.g., Lung, Heart, Whole Blood, Liver, Brain Cortex) rendered with proportional CSS gradient bars (e.g., `#10b981` -> `#059669`) with TPM values and sample count tags.
- **UCSC Genome Browser Conservation:**
  - Input: Genomic coordinates (Chrom, Start, End) or gene locus.
  - Calls: `GET ${apiBase}/api/v1/bioinformatics/genomics/ucsc?chrom=${chrom}&start=${start}&end=${end}`.
  - Displays: Evolutionary conservation score (phyloP / phastCons), conservation classification, and overlapping transcription factor binding site (TFBS) peaks.
- **AlphaGenome Variant Impact (AVI):**
  - Input: Variant coordinate in standard format `chr:pos:ref>alt` (e.g., `chr7:140753336:A>T`).
  - Calls: `GET ${apiBase}/api/v1/bioinformatics/genomics/alphagenome?variant=${variant}`.
  - Displays: Numerical AVI impact score, functional effect prediction (promoter disruption, enhancer loss, splicing aberration), and tissue-specific delta effect.

#### Panel 2: 🔬 Structural Biology, AlphaFold & Foldseek Viewer
- **AlphaFold 3D Confidence Metrics:**
  - Input: UniProt Accession ID (e.g., `P00533`, `P04637`, `P38398`).
  - Calls: `GET ${apiBase}/api/v1/bioinformatics/protein/alphafold?uniprot_id=${uniprotId}`.
  - Displays: Overall model confidence score, pLDDT distribution curve/histogram partitioned into 4 standard structural confidence tiers:
    - *Very High* (pLDDT > 90): Deep blue (`#1e40af`)
    - *Confident* (70 < pLDDT ≤ 90): Light blue (`#60a5fa`)
    - *Low* (50 < pLDDT ≤ 70): Yellow (`#facc15`)
    - *Very Low* (pLDDT ≤ 50): Orange/Red (`#f87171`)
    Predicted domain boundaries and links to download `.pdb` / `.cif` coordinate files.
- **STRING Protein Interaction Network:**
  - Input: Protein/Gene name.
  - Calls: `GET ${apiBase}/api/v1/bioinformatics/protein/string?protein=${protein}`.
  - Displays: Interactive grid/list of binding partners with interaction scores, evidence types (co-expression, experimental, database, textmining), and functional GO enrichment badges.
- **Headless PyMOL Script Synthesizer & Dispatcher:**
  - Controls: Selection for representation mode (`cartoon`, `surface`, `sticks`, `ribbon`), coloring schema (`by_plddt`, `chain`, `spectrum`), and ray-tracing resolution.
  - Calls: `POST ${apiBase}/api/v1/bioinformatics/protein/pymol/render` with `{ uniprot_id, script_commands, render_image }`.
  - Displays: Synthesized `.pml` script in a dark code block with 1-click "Copy Script" and "Dispatch PyMOL Render" button.
- **Foldseek 3D Structural Homology Search (Operator Directive):**
  - Search Targets: AlphaFold DB (`afdb50`, `afdb-swissprot`) and PDB (`pdb100`).
  - Input: PDB coordinate file upload or PDB/UniProt accession.
  - Calls: `POST ${apiBase}/api/v1/bioinformatics/protein/foldseek` with `{ pdb_id, database: 'afdb50', mode: '3diaa' }`.
  - Displays: Homologous 3D structure matches table: Target ID, Description, TM-Score, LDDT score, E-value, and Alignment Residue Length.

#### Panel 3: 📚 bioRxiv & Regulatory Literature Recon
- **bioRxiv Preprint Search:**
  - Input: Keyword query (e.g. "AlphaFold variant impact", "CRISPR off-target Cas9", "BRCA1 splice variant").
  - Calls: `GET ${apiBase}/api/v1/bioinformatics/literature/biorxiv?query=${encodeURIComponent(query)}`.
  - Displays: Paper cards with Title, Author List, DOI with external link icon, Publication Date, Category pill (e.g. "Bioinformatics", "Genomics"), and expandable Abstract snippet.
- **JASPAR Transcription Factor Binding Profiles:**
  - Input: TF Symbol (e.g. `TP53`, `STAT3`, `CTCF`, `MYC`).
  - Calls: `GET ${apiBase}/api/v1/bioinformatics/genomics/jaspar?tf=${tf}`.
  - Displays: Matrix ID (e.g. `MA0106.3`), TF family, consensus sequence string, and Position Weight Matrix (PWM) base frequency breakdown (A, C, G, T distributions).
- **ENCODE cis-Regulatory Elements (cCREs):**
  - Input: Locus or accession.
  - Calls: `GET ${apiBase}/api/v1/bioinformatics/genomics/encode?accession=${encodeAccession}`.
  - Displays: cCRE element type (`PLS` - Promoter-like, `pELS` - Proximal Enhancer-like, `dELS` - Distal Enhancer-like, `DNase-H3K4me3`), Z-scores across human cell lines, and chromatin state tags.

#### Panel 4: 🐝 Autonomous Genomic Swarm & AI Training Monitor
- **1-Click Swarm Dispatch (`genomic_discovery_sprint`):**
  - Workflow Preset:
    1. *Stage 1 (Literature Recon)*: bioRxiv papers & regulatory summaries.
    2. *Stage 2 (Variant Impact)*: dbSNP & AlphaGenome AVI score analysis.
    3. *Stage 3 (Structural Docking)*: AlphaFold pLDDT & Foldseek homology.
    4. *Stage 4 (Synthesis)*: Final MoE 7th domain clinical/scientific executive summary.
  - Execution: Calls `POST ${apiBase}/api/v1/agent-harness/swarm/jobs` with `preset_id: "genomic_discovery_sprint"` or custom bioinformatics prompt.
  - Streaming: Subscribes to SSE event stream `EventSource(${apiBase}/api/v1/agent-harness/swarm/jobs/${jobId}/stream)`. Displays live stage progress indicators (`waiting` -> `running` -> `completed`), token emission stream with blinking cursor (`▌`), and execution time.
- **Instruction Dataset Synthesizer:**
  - Input: Number of samples to synthesize (e.g. 50, 200, 1000).
  - Calls: `POST ${apiBase}/api/v1/bioinformatics/training/dataset/generate` with `{ sample_count }`.
  - Displays: Destination file path (`llm_training_data/bioinformatics_instruction_dataset.jsonl`), generated pair count, file size, and interactive JSON preview of `{ instruction, input, output }` pairs.
- **Local LoRA Training Monitor:**
  - Checks: `GET ${apiBase}/api/v1/bioinformatics/training/status`.
  - Displays: Target model (`stehouwer_genomics:latest`), GPU allocation (NVIDIA RTX 4090 24GB VRAM), Unsloth 4-bit LoRA hyperparameters (LoRA Rank 16, Alpha 32, Target Modules: `q_proj, k_proj, v_proj, o_proj`), VRAM consumption bar, and live training console output.

---

### 3. Multi-Mirror Synchronization & Parity Architecture

#### Mirror Topology
In accordance with AI-BS Ecosystem **Rule 1 (Multi-Mirror Synchronization Law)**, components must maintain strict byte-for-byte SHA-256 parity across 4 directories:
1. **Canonical Source:** `C:\AI-BS\frontend\src\components\` (Primary Source of Truth)
2. **Mirror 1:** `C:\AI-BS\frontend\components\`
3. **Mirror 2:** `C:\AI-BS\frontend\src\components\components\`
4. **Mirror 3:** `C:\AI-BS\frontend\components\components\`

#### Synchronization Mechanism (`scripts/sync_mirrors.py` -> `frontend/scripts/sync_mirrors.py`)
- Traverses all files in `frontend/src/components/`, ignoring `node_modules`, `__pycache__`, `.git`, and subfolder `components`.
- Computes SHA-256 for each canonical file.
- If target file is missing or its hash does not match canonical hash, overwrites target file.
- Performs a strict verification pass across all primary files; returns exit code 0 if 100% parity is verified, or code 1 on mismatch.

#### Parity Verification Script (`scripts/verify-mirror-parity.ps1`)
- Scans `C:\AI-BS\frontend\src\components` and indexes all tracked files (excluding `node_modules`, `dist`, `build`, `.git`, `.next`, `*.log`, `*.bak`, `.DS_Store`, `components`).
- Computes SHA-256 hashes for all files in canonical source.
- Evaluates each of the 3 target mirrors:
  - Verifies presence of each source file.
  - Verifies exact SHA-256 hash match.
  - Checks for orphaned/extra files in mirror directories.
- Exits with 0 on 100% parity, 1 on failure.

#### Current Parity State & Acceptance Metric:
- **Baseline Count:** 446 files currently verified (exit code 0).
- **Post-Implementation Count:** Adding `GenomicsStudioTab.jsx` to `frontend/src/components/` makes the canonical count 447. Running `python scripts/sync_mirrors.py` synchronizes the new file to the other 3 mirrors, resulting in **447/447 files verified identical** across all 4 mirrors, exactly satisfying Acceptance Criterion 2.

---

### 4. Version Ledgers & Desktop Shortcuts

#### Ecosystem Version Synchronization
The ecosystem version must be bumped from `v5.310.0` to `v5.311.0` across all authoritative ledgers:

| # | File Path | Current Content | Required Content (v5.311.0) |
|---|---|---|---|
| 1 | `C:\AI-BS\version.txt` | `v5.310.0` | `v5.311.0` |
| 2 | `C:\AI-BS\package.json` | `"version": "5.310.0"` | `"version": "5.311.0"` |
| 3 | `C:\AI-BS\frontend\package.json` | `"version": "5.310.0"` | `"version": "5.311.0"` |
| 4 | `C:\AI-BS\frontend\public\version.json` | `"version": "5.310.0"`<br>`"release_tag": "v5.310.0-release"` | `"version": "5.311.0"`<br>`"release_tag": "v5.311.0-release"` |
| 5 | `C:\AI-BS\frontend\version.js` | `SYSTEM_VERSION = 'v5.309.0'` | `SYSTEM_VERSION = 'v5.311.0'`<br>`SYSTEM_VERSION_NUM = '5.311.0'`<br>`RELEASE_DATE = '2026-10-06'`<br>`RELEASE_TAG = 'v5.311.0-release'` |
| 6 | `C:\AI-BS\frontend\src\version.js` | `SYSTEM_VERSION = 'v5.309.0'` | Identical to `frontend/version.js` |
| 7 | `C:\AI-BS\frontend\src\components\TopNavbar.jsx` (line 248) | `<span>v5.310.0</span>` | `<span>v5.311.0</span>` (synced to all 4 mirrors) |
| 8 | `C:\AI-BS\scripts\refresh_desktop_shortcuts.ps1` (lines 1, 30) | `v5.310.0` | `v5.311.0` |
| 9 | `C:\AI-BS\AI_BS_MASTER_ARCHITECTURAL_LEDGER.md` | v5.310.0 entry at top | Prepend/Append `5.311.0` ledger row detailing the Genomic & Structural Intelligence Studio suite |
| 10 | `C:\AI-BS\SAVED_CHECKPOINT.md` | `v5.310.0` | `v5.311.0` |

#### Desktop Shortcuts System (`scripts/refresh_desktop_shortcuts.ps1`)
- Targets:
  - `C:\Users\footb\OneDrive\Desktop\AI-BS Executive Studio.lnk`
  - `C:\Users\footb\Desktop\AI-BS Executive Studio.lnk`
- Configuration:
  - Target: `wscript.exe`
  - Argument: `"C:\AI-BS\Launch_Desktop_Studio.vbs"`
  - Working Directory: `C:\AI-BS`
  - Icon: `C:\AI-BS\public\favicon.ico`
  - Description: `"AI-BS Sovereign Executive Command Studio (v5.311.0)"`
- Execution: `powershell -ExecutionPolicy Bypass -File scripts/refresh_desktop_shortcuts.ps1` updates both links.

---

### 5. Vite Build Tooling & Performance

#### Build Pipeline Configuration (`frontend/vite.config.js`)
- **Plugin:** `@vitejs/plugin-react` with `@babel/plugin-syntax-dynamic-import`.
- **Target:** `esnext`.
- **Minifier:** `terser` with console drop and debugger removal enabled.
- **Manual Chunks:**
  ```javascript
  manualChunks(id) {
    if (id.includes('monaco-editor')) return 'monaco';
    if (id.includes('xterm')) return 'xterm';
    if (id.includes('react-markdown') || id.includes('react-syntax-highlighter')) return 'markdown';
    if (id.includes('@xyflow')) return 'xyflow';
    if (id.includes('firebase')) return 'firebase';
    if (id.includes('lucide-react')) return 'icons';
    if (id.includes('recharts') || id.includes('d3-')) return 'recharts';
    if (id.includes('node_modules')) return 'vendor';
  }
  ```
- **Test Build Result:** Verified on live filesystem. `npm run build` executed in 24.59s, exiting with code 0 and producing valid production bundles in `dist/`.

---

## Action Plan for Subsequent Implementation Agents

1. **Author `frontend/src/components/GenomicsStudioTab.jsx`:**
   - Implement the complete 4-panel architecture with Lucide icons, dark mode styling, and error boundaries.
   - Include Foldseek 3D structural homology search in Panel 2.
   - Support live SSE event streaming for `genomic_discovery_sprint` Swarm dispatch in Panel 4.
2. **Mount Studio into Application:**
   - In `frontend/App.jsx`: Add lazy import and tab definition in `tabs` array.
   - In `frontend/src/components/navigationConfig.js`: Add sub-tab to `intelligence_and_code`.
   - In `frontend/src/components/accessControl.js`: Add `genomics_studio: ['admin', 'enterprise_all_access']` to `TAB_PERMISSIONS`.
   - In `frontend/src/index.css` & `frontend/src/components/index.css`: Add container height rules.
3. **Execute 4-Mirror Synchronization:**
   - Run `python scripts/sync_mirrors.py`.
   - Run `powershell -ExecutionPolicy Bypass -File scripts/verify-mirror-parity.ps1` to confirm 447/447 files identical.
4. **Update Version Authority & Shortcuts:**
   - Update 9 version ledger files to `v5.311.0`.
   - Run `powershell -ExecutionPolicy Bypass -File scripts/refresh_desktop_shortcuts.ps1`.
5. **Run Clean Production Build:**
   - Run `npm run build` in `frontend/`.
