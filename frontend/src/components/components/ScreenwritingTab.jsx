import React, { useState, useEffect, useRef } from 'react';
import { createAuthenticatedEventSource } from '/src/utils/authenticatedEventSource.js';
import { createScreenplayDraftCoordinator } from '/src/utils/screenplayDraftCoordinator.js';
import { Fountain } from 'fountain-js';
const fountainParser = new Fountain();
import { useAppStore } from './useAppStore';
import CharacterVaultModal from './CharacterVaultModal';
import CoverageReportModal from './CoverageReportModal';
import ScreenplayEditor from './ScreenplayEditor';
import ScreenplayViewer from './ScreenplayViewer';
import AdaptationStatusBar from './AdaptationStatusBar';
import ScriptAssistantDrawer from './ScriptAssistantDrawer';
import ProjectAudioPlayer from './ProjectAudioPlayer';
import { parseFDX } from '/utils/FDXParser.js';
import { serializeFDX } from '/utils/FDXSerializer.js';
import { fountainToAST, astToFountain } from '/utils/FountainAdapter.js';
import { logTeamActivity } from './collaborationService';
import ScriptToBookNovelizerModal from './ScriptToBookNovelizerModal';
import ScreenplayTableReadModal from './ScreenplayTableReadModal';
import AnalyticsOverlay from './AnalyticsOverlay';
import ProductionBreakdownModal from './ProductionBreakdownModal';
import StagePlayBreakdownModal from './StagePlayBreakdownModal';
import ScriptTelemetryModal from './ScriptTelemetryModal';
import './StagePlayBreakdownModal.css';

const StoryboardModal = ({ isOpen, onClose, storyboards, backendUrl = '' }) => {
  if (!isOpen) return null;
  return (
    <div className="fixed inset-0 bg-black/80 flex items-center justify-center z-50 p-4">
      <div className="bg-gray-900 border border-gray-700 rounded-xl max-w-6xl w-full max-h-[90vh] overflow-y-auto p-6 text-white shadow-2xl">
        <div className="flex justify-between items-center mb-6">
          <h2 className="text-2xl font-bold text-transparent bg-clip-text bg-gradient-to-r from-purple-400 to-pink-500">
            🎬 AI Storyboard Generator
          </h2>
          <button onClick={onClose} className="text-gray-400 hover:text-white text-xl">&times;</button>
        </div>
        
        <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
          {storyboards.map((sb, idx) => (
            <div key={idx} className="bg-gray-800 rounded-lg p-4 border border-gray-700 shadow-lg">
              <div className="text-sm text-gray-300 mb-3 h-16 overflow-y-auto italic">"{sb.action}"</div>
              <img src={sb.image_url?.startsWith('http') || sb.image_url?.startsWith('data:') || sb.image_url?.startsWith('blob:') ? sb.image_url : `${backendUrl}${sb.image_url?.startsWith('/') ? '' : '/'}${sb.image_url}`} alt="Storyboard Panel" className="w-full h-auto rounded-lg shadow-md border border-gray-600" />
            </div>
          ))}
        </div>
        
        {storyboards.length === 0 && (
          <div className="text-center text-gray-500 py-10">
            No storyboards generated.
          </div>
        )}
      </div>
    </div>
  );
};

const GUIDE_DATA = [
  // Category 0: 8-Step Production Workflow
  { cat: 0, title: "Step 1: Project Initialization & Title Page Setup", badge: "Phase 1 • Setup", badgeColor: "#38bdf8", desc: "Begin your screenplay with proper metadata. Configure official title, author credits, revision status, WGA registration, and contact information.", steps: ["Click '+ New Project' on the Quick Action Bar to start fresh, or select an existing project from the dropdown.", "Switch to '🚀 Production & CMS' ribbon tab and click '📄 Title Page'.", "Enter your Title, Written by credit, Draft Date, and WGA / Contact details.", "Click '✨ Apply to Title Page' to prepend the standard Hollywood title page block directly into the manuscript."], tip: "Standard Hollywood title blocks sit above 'FADE IN:' and are excluded from the official script page count." },
  { cat: 0, title: "Step 2: Story Architecture & Visual Beat Board", badge: "Phase 2 • Outlining", badgeColor: "#facc15", desc: "Map your three-act structure and character arcs visually before writing prose. Scene cards dynamically reflect time-of-day emojis (🌙 Night, 🌅 Sunset, 🎬 Day) and estimated manuscript pages.", steps: ["Click 'Beat Board' in the Page Navigation bar or '🗂️ Beat Board' on the '👁️ Views & Split' ribbon.", "Click '+ Add Beat' to insert new scene cards with your desired location slugs (e.g. EXT. ROOFTOP - NIGHT).", "Click any beat card to jump instantly to that location in the manuscript editor.", "Click '🎬 Animate Scene' on any beat card to push that scene's prompt directly to the 3D Previs simulator."], tip: "Use the Left Sidebar 'Outlines' tabs ('Outline 1' vs 'Outline 2') to test alternate endings without modifying your primary draft." },
  { cat: 0, title: "Step 3: Screenplay Formatting & Element Keys", badge: "Phase 3 • Authoring", badgeColor: "#4ade80", desc: "Author your manuscript formatted in industry-standard Courier 11pt monospace with 55 lines per page and exact 1.5-inch left binding margins.", steps: ["Insert '🎬 Heading' (INT. or EXT. LOCATION - TIME) to establish scene boundaries.", "Add '📝 Action' lines in present tense describing visual beats and character movement.", "Insert '👤 Character' in all-caps, followed immediately by '💬 Dialogue'.", "Insert '🗣️ Parenthetical' (e.g. (wryly)) between Character and Dialogue for specific actor cues.", "Use '👥 Dual' for simultaneous dialogue and '⚡ Transition' (CUT TO:) for editorial scene cuts."], tip: "Smart Tab/Enter Flow: Press Tab on a blank line to insert a Character cue; press Tab from Character to insert a Parenthetical; press Enter from Character to begin Dialogue!" },
  { cat: 0, title: "Step 4: Lexical Polish, Spellcheck & AI Alt-Takes", badge: "Phase 4 • Dialogue Polish", badgeColor: "#c084fc", desc: "Refine dialogue and punch up action descriptions using the built-in lexicon, thesaurus, and AI-powered alternate takes.", steps: ["Highlight any dialogue line in the script editor and click '✨ Alt-Take' on the '✍️ Write' ribbon.", "Review 3 distinct alternate takes (Subtextual, Raw Emotional, or Pragmatic) generated by the Stehouwer LLM.", "Select your preferred take to instantly replace the highlighted text in the manuscript.", "Highlight individual words and click '📖 Thesaurus' for vivid synonyms, and run '📝 Spell' to catch typos."], tip: "Top screenwriters rely on subtext: let characters talk about simple physical objects to reveal deep emotional conflict." },
  { cat: 0, title: "Step 5: Scene Verification & Page Review Doctor", badge: "Phase 5 • Quality Control", badgeColor: "#e879f9", desc: "Proof your manuscript page by page using the side-by-side Page Format Doctor that automatically detects Hollywood formatting errors.", steps: ["Navigate to any page using the page pagination buttons or the jump-to-page input box.", "Click '🟣 Review Pg X' in the Page Navigation bar.", "Inspect the side-by-side comparison: the left editor highlights orphaned character cues, misaligned dialogue, missing slugline times, or hyphen errors.", "Click '✨ Apply Proof & Advance' to automatically patch the script and advance to the next page."], tip: "Keeping each page strictly under 55 lines maintains the Hollywood gold standard rule: 1 Page = 1 Minute of screen time." },
  { cat: 0, title: "Step 6: Multi-Voice Table Read Audition & MMCSS Pro Audio", badge: "Phase 6 • Audio Drama", badgeColor: "#fb923c", desc: "Audition your screenplay with fully synthesized character voices streamed in real time via a Windows MMCSS Priority 15 Pro Audio thread.", steps: ["Click '🎙️ Table Read Studio' on the Quick Action Bar or '🎧 Audio Drama' on the navigation strip.", "The studio parses all character cues and maps them across a 10-role voice cast matrix.", "In the Cast Matrix tab, customize voice timbre, pitch, and playback rate for each character.", "Click '▶️ Play / Resume' to begin playback; follow the dual teleprompter with live line tracking and stereo RMS VU meters.", "Click '💾 Export Table Read WAV' to render a broadcast-quality WAV master file to disk."], tip: "Hearing your script read aloud by distinct voices is the fastest way to expose unnatural rhythm, pacing lag, and exposition dumps." },
  { cat: 0, title: "Step 7: Production Breakdown, Stripboard & 50-State Tax Engine", badge: "Phase 7 • Budgeting", badgeColor: "#38bdf8", desc: "Transform your creative manuscript into a production-ready shoot plan with color-coded stripboard, departmental breakdowns, cast DOOD matrix, and tax incentives.", steps: ["Switch to the '🚀 Production & CMS' ribbon and click '🎬 Film Budget'.", "In Tab 1 ('Stripboard'), drag and group color-coded scene strips to optimize shoot days.", "In Tab 2 ('Script Breakdown'), review tagged assets (Props, Wardrobe, Vehicles, SFX) per scene.", "In Tab 3 ('Cast DOOD Matrix'), review actor Work (W), Hold (H), Drop (D), and Pickup (P) schedules.", "In Tab 4 ('Top Sheet Budget'), select your production state (e.g. Georgia 30%, California 35%, New Mexico 40%) to calculate net tax incentive savings."], tip: "Grouping exterior night scenes (blue strips) and interior night scenes (green strips) together eliminates costly night-to-day crew turnaround premiums." },
  { cat: 0, title: "Step 8: Multi-Format Export (.fdx, .pdf, .fountain) & CMS Publishing", badge: "Phase 8 • Release & Archival", badgeColor: "#34d399", desc: "Export industry-standard files for studio distribution, talent representation, and sovereign archival.", steps: ["Click '📄 Export FDX' on the Action Bar to save a Final Draft XML file, or select Fountain from the dropdown.", "Click '📑 Export PDF' to generate print-ready PDFs formatted with Hollywood title pages and page numbering.", "Select 'Export Call Sheet & Shooting Schedule PDF' to generate daily crew call sheets.", "Click '🚀 Publish to CMS' on the Production ribbon to archive the blue production draft directly in the Stehouwer Publications CMS Vault."], tip: "Always distribute PDFs with watermarked draft versions (e.g. 'Blue Production Draft') to prevent on-set script discrepancies." },

  // Category 1: Action Bar & Top Commands
  { cat: 1, title: "+ New Project", badge: "Action Bar • Row 2B", badgeColor: "#22c55e", desc: "Creates a brand new screenplay project with a fresh manuscript canvas, initialized title page, and reset scene hierarchy.", steps: ["Click '+ New Project' on the Quick Action Bar.", "Enter the project title in the input prompt (e.g. 'The Judge Made Him Go').", "The studio initializes a standard title header and centers the cursor on the drafting canvas."], tip: "Use the Project dropdown in Row 2A anytime to toggle between multiple active projects without losing draft state." },
  { cat: 1, title: "🧘 Zen Mode", badge: "Action Bar • Row 2B", badgeColor: "#a78bfa", desc: "Collapses the Left Sidebar (Projects, Outlines, Branches, Scenes list) to maximize horizontal writing space for distraction-free focus.", steps: ["Click '🧘 Zen Mode' to collapse the left navigation panel.", "Click '🧘 Zen Mode' again or press Escape to restore the full navigation panel."], tip: "Zen Mode is ideal for 15-minute writing sprints and continuous dialogue drafting sessions." },
  { cat: 1, title: "📖 Novelize to Book", badge: "Action Bar • Row 2B", badgeColor: "#a855f7", desc: "Transforms standard screenplay action blocks and dialogue into descriptive, chaptered literary novel prose using the Stehouwer LLM engine.", steps: ["Ensure your screenplay has active scene headings and dialogue cues.", "Click '📖 Novelize to Book'.", "The AI ingests character dynamics and scene context, then generates narrative prose formatted into book chapters."], tip: "Great for producing novelizations, companion fiction, or detailed treatment prose from an existing script." },
  { cat: 1, title: "🎙️ Table Read Studio", badge: "Action Bar • Row 2B", badgeColor: "#f59e0b", desc: "Launches the multi-voice AI Table Read Studio. Automatically parses character dialogue cues, assigns distinct voice profiles across a 10-role cast matrix, and streams real-time audio through a Windows MMCSS Priority 15 thread.", steps: ["Click '🎙️ Table Read Studio' on the Quick Action Bar.", "Inspect the Cast Matrix: customize voice, pitch, and speed for each character.", "Click '▶️ Play / Resume' to hear the script read aloud with live line highlighting in the teleprompter."], tip: "The MMCSS Priority 15 thread guarantees glitch-free, zero-buffer-underrun audio playback even under heavy system load." },
  { cat: 1, title: "⚡ Thoughts & Pages Telemetry", badge: "Action Bar • Row 2B", badgeColor: "#0284c7", desc: "Opens the comprehensive Script Telemetry & Analytics modal displaying estimated screen time, dialogue vs. action percentage, character lines, and three-act pacing curves.", steps: ["Click '⚡ Thoughts & Pages Telemetry'.", "Review the Dialogue/Action ratio meter (industry sweet spot is 30%-45% dialogue).", "Inspect character dialogue distribution and unique location counts."], tip: "Clicking this button also automatically reveals the '🎮 3D & Previs' pipeline ribbon deck in Row 3." },
  { cat: 1, title: "📥 Import", badge: "Action Bar • Row 2B", badgeColor: "#34d399", desc: "Imports existing screenplays from industry standard file formats with automatic scene slugline and character cue parsing.", steps: ["Click '📥 Import' to open the import dropdown menu.", "Select your file format: Final Draft (.fdx), Fountain (.fountain), Screenplay PDF (.pdf), or Plain Text (.txt).", "Choose your file in the file browser; the studio parses scenes and pagination instantly."], tip: "Fountain is an open, plain-text format that preserves all screenplay formatting across any operating system." },
  { cat: 1, title: "🔍 Find & Replace", badge: "Action Bar • Row 2B", badgeColor: "#a855f7", desc: "Toggles the inline search and replace bar located directly above the manuscript canvas.", steps: ["Click '🔍 Find & Replace' or press Ctrl+F.", "Enter search text in 'Find text...' and replacement text in 'Replace with...'.", "Click 'Find Next' to cycle through occurrences, or 'Replace All' to update the entire manuscript."], tip: "Press Escape or click the '✕' close button on the right to dismiss the inline search bar." },
  { cat: 1, title: "📄 Export FDX", badge: "Action Bar • Row 2B", badgeColor: "#38bdf8", desc: "Exports the manuscript into industry-standard Final Draft XML (.fdx) and Fountain (.fountain) file formats.", steps: ["Click '📄 Export FDX' to open the export format dropdown.", "Choose 'Export Final Draft (.fdx)' or 'Export Fountain Script (.fountain)'.", "Choose your save location; the file is saved with full scene, character, and dialogue XML tags intact."], tip: "Final Draft (.fdx) files exported here are 100% compatible with Final Draft 12/13, WriterDuet, and StudioBinder." },
  { cat: 1, title: "📑 Export PDF", badge: "Action Bar • Row 2B", badgeColor: "#f87171", desc: "Renders a print-ready, industry-standard formatted screenplay PDF complete with title page, page headers, numbers, and optional call sheets.", steps: ["Click '📑 Export PDF' to open the PDF export options.", "Select 'Export Screenplay PDF (.pdf)' for the full manuscript.", "Select 'Export Call Sheet & Shooting Schedule PDF' to generate daily production call sheets."], tip: "PDFs are generated using standard Courier 11pt font with exact 1-inch top/bottom/right margins and 1.5-inch left margins." },
  { cat: 1, title: "💾 Save / 🟢 Autosaved", badge: "Action Bar • Row 2B", badgeColor: "#22c55e", desc: "Real-time autosave status badge and manual commit button. Persists the current screenplay draft into both the local filesystem and the SQLite sovereign vault.", steps: ["The studio automatically saves edits in the background, updating the timestamp badge.", "Click '💾 Save' at any time to execute an immediate hard write and vault checkpoint."], tip: "Scripts are encrypted and archived in 'stehouwer_vault.db' under the 'screenplay_projects' table." },

  // Category 2: 5 Dynamic Ribbon Decks
  { cat: 2, title: "Deck 0: ✍️ Write Ribbon", badge: "Ribbon Deck 0 • Editing", badgeColor: "#facc15", desc: "Houses primary text formatting, lexical tools, clipboard operations, and AI dialogue revision tools.", steps: ["↶ Undo / ↷ Redo: Navigate backward and forward through text edit history (Ctrl+Z / Ctrl+Y).", "✂️ Cut / 📋 Copy / 📋 Paste: Standard clipboard operations.", "B / I / U: Toggle Bold (slugline emphasis), Italic (sound effects / vocal inflection), and Underline.", "📝 Spell: Scans the active screenplay against the Hollywood lexicon to flag spelling mistakes.", "📖 Thesaurus: Highlights synonyms for the selected word to enrich action descriptions.", "✨ Alt-Take: Generates 3 AI alternative takes (Subtextual, Raw Emotional, Pragmatic) for any selected dialogue line."], tip: "Use Bold on scene sluglines (e.g. **INT. WAREHOUSE - NIGHT**) for modern, punchy production readability." },
  { cat: 2, title: "Deck 1: 🧩 Elements & Insert Ribbon", badge: "Ribbon Deck 1 • Script Elements", badgeColor: "#38bdf8", desc: "Provides one-click insertion of all 10 standard Hollywood screenplay formatting elements.", steps: ["🎬 Heading: Inserts scene slugline (e.g. INT. LOCATION - DAY) setting camera and lighting setup.", "📝 Action: Inserts present-tense description of character actions and physical environment.", "👤 Character: Centers character cue in uppercase above spoken lines.", "💬 Dialogue: Spoken dialogue indented to standard 2.5-inch margins.", "🗣️ Parenthetical: Inserts actor delivery cue in parentheses (e.g. (whispering)).", "👥 Dual: Formats two characters speaking simultaneously side by side.", "⚡ Transition: Inserts right-aligned editorial cuts (e.g. CUT TO:, DISSOLVE TO:).", "🔖 Beat: Inserts a dramatic pause marker ([BEAT: Tension mounts]).", "📌 ScriptNote: Non-printing notes for director, cinematographer, or crew."], tip: "Never write character internal thoughts in Action lines—only describe what can be seen or heard by the camera!" },
  { cat: 2, title: "Deck 2: 👁️ Views & Split Ribbon", badge: "Ribbon Deck 2 • Layout & Panes", badgeColor: "#a78bfa", desc: "Controls screen layout, multi-pane split viewing, outline navigation, and the visual beat board.", steps: ["📝 Editor: Full-canvas standard script text editor.", "👁️ Scene View: Page-by-page viewing with realistic 8.5x11 paper margins and page numbers.", "🗂️ Beat Board: Visual story cards arranged horizontally with day/night badges.", "◀ Outline: Toggles the left outline panel visibility.", "🧭 Navigator: Toggles the scene hierarchy and quick-jump tree.", "None / Split V / Split H: Controls split-screen viewing between raw manuscript and formatted preview."], tip: "Split V (vertical split) allows you to type in the raw manuscript on the left while previewing formatted 8.5x11 pages on the right." },
  { cat: 2, title: "Deck 3: 🎮 3D & Previs Ribbon", badge: "Ribbon Deck 3 • Virtual Production", badgeColor: "#ec4899", desc: "Bridges the screenplay to virtual production, Unreal Engine 5, and AI video diffusion pipelines.", steps: ["🎥 Send to Video Studio: Transmits the active scene slug and action description directly to the RTX 4090 Wan2.1 video generation engine.", "🎮 Export CSV (Data Table): Generates an Unreal Engine 5 Data Table CSV containing all scene numbers, locations, and characters.", "🎮 Export Python (Sequencer): Exports a Python script to automatically assemble Unreal Engine 5 Level Sequence camera tracks.", "❇️ Chunk in ComfyUI: Calculates 130 words-per-minute scene pacing and queues prompt chunks into the ComfyUI GPU queue on Port 8189.", "🧊 3D Previs & Camera Blocking: Opens the 3D scene previewer and virtual camera staging simulator."], tip: "Automated 130 WPM ComfyUI chunking converts every 10 lines of action into timed 4-second video generation prompts." },
  { cat: 2, title: "Deck 4: 🚀 Production & CMS Ribbon", badge: "Ribbon Deck 4 • Production & Budget", badgeColor: "#4ade80", desc: "Professional film and theatrical production management, script coverage, budgeting, colored revisions, and CMS publishing.", steps: ["🎭 Character Vault: Cast roster displaying line counts, dialogue frequency, and actor assignments.", "📊 Script Coverage: AI Script Doctor analyzing premise, structure, character arcs, dialogue, and commercial viability.", "📈 Analytics: Telemetry graphs showing pacing, act breaks, dialogue vs. action, and location counts.", "🎬 Film Budget: 4-tab suite with 50-State Tax Credit calculator, stripboard, and DOOD matrix.", "🎭 Theatrical Budget: Stage play capitalization and weekly operating budget suite.", "⚪ Revision Mode & Colors: Industry revision tracking (Blue, Pink, Yellow, Green revision pages).", "📄 Title Page: Configures script title, author, draft date, and WGA contact info.", "🚀 Publish to CMS: Archives the verified draft directly in the Stehouwer Publications CMS Vault."], tip: "Always engage Revision Mode before starting second-draft rewrites to highlight altered scenes with industry standard revision colors." },

  // Category 3: Navigation, Sidebar & Layout
  { cat: 3, title: "View Mode Switchers (Editor, Page View, Split, Beat Board)", badge: "Row 4 • Navigation Strip", badgeColor: "#38bdf8", desc: "Four distinct view modes tailored for every stage of writing and reviewing.", steps: ["Editor: High-performance distraction-free typing in Courier 11pt with live scene highlighting.", "Page View: Paginated 8.5\" x 11\" paper view showing exact Hollywood page boundaries and page numbers.", "Split: Side-by-side split screen with manuscript editor on the left and live formatted page preview on the right.", "Beat Board: Story index card canvas displaying beats grouped with day/night badges and emotional arc icons."], tip: "Switch to Page View before exporting to ensure dialogue blocks do not awkwardly break across page bottoms." },
  { cat: 3, title: "Pagination Controls (First, Prev, Next, Last)", badge: "Row 4 • Navigation Strip", badgeColor: "#94a3b8", desc: "Instant page navigation and jump controls.", steps: ["⏮ First: Jump immediately to Page 1.", "◀ Prev: Go to previous page.", "Page X of Y: Dynamic label indicating active page and total script length.", "Next ▶: Go to next page.", "Last ⏭: Jump immediately to the final page of the manuscript."], tip: "You can also use the 'Jump to Page' box in the bottom telemetry strip to type any specific page number directly." },
  { cat: 3, title: "🟣 Review Pg X Format Doctor", badge: "Row 4 • Navigation Strip", badgeColor: "#a855f7", desc: "Intelligent side-by-side page proofing engine that audits the active 54-line page slice against standard Hollywood formatting rules.", steps: ["Click '🟣 Review Pg X' to open the Format Doctor for the active page.", "The engine checks 54-line height limits, orphaned cues, and improper sluglines.", "Click '✨ Apply Proof & Advance' to commit the clean formatted text and automatically advance to the next page."], tip: "Run Review Pg X across all pages before submitting to talent agencies, festivals, or production companies." },
  { cat: 3, title: "Scene Selector Dropdown", badge: "Row 4 • Navigation Strip", badgeColor: "#eab308", desc: "Dynamic dropdown menu listing every detected scene slugline in the screenplay along with its estimated page number.", steps: ["Click the 'Scene: Select Scene...' dropdown in Row 4.", "Select any scene header (e.g. '3. INT. SUBURBAN LIVING ROOM - DAY... (p.2)').", "The editor immediately scrolls and positions the cursor at that exact scene header."], tip: "Selecting a scene also updates the 8.5x11 page viewer to display that scene's page." },
  { cat: 3, title: "Left Sidebar (Scenes, Outlines, Projects, Branches, Writing Sprint)", badge: "Row 5 • Left Panel", badgeColor: "#22c55e", desc: "Hierarchical project navigator and writing productivity tools.", steps: ["Scenes List: Searchable list of all scenes in chronological order; clicking any scene jumps directly to it.", "Outlines 1 & 2: Toggle between parallel plot outlines without altering the manuscript.", "Projects Tree: Switch between project folders and import reference files.", "Branches: Version control branches (e.g. main vs alt-ending).", "15-Minute Writing Sprint: Built-in timer that tracks words written and words-per-minute (WPM) during timed writing sprints."], tip: "Click 'Start Sprint' to initiate a focused 15-minute drafting block. The timer automatically calculates your WPM upon completion." },
  { cat: 3, title: "Hollywood Monospace Layout Specifications", badge: "Core Typography & Geometry", badgeColor: "#f87171", desc: "Exact mathematical specifications of the Hollywood screenplay format standard.", steps: ["Font: Courier New, 11 point size, monospace (10 characters per inch).", "Line Height: 1.4 spacing, exactly 55 lines maximum per 8.5\" x 11\" page.", "Margins: Top 1.0\", Bottom 1.0\", Right 1.0\", Left 1.5\" (allows for standard 3-hole punch brass brad binding).", "Character Cues: Uppercase, indented 3.7 inches from left margin.", "Dialogue: Indented 2.5 inches from left margin, maximum 3.5 inches wide.", "Parentheticals: Indented 3.1 inches from left margin."], tip: "These strict rules guarantee that one page of screenplay translates to exactly one minute of screen time on set." },
  { cat: 3, title: "Bottom Script Telemetry Strip", badge: "Row 6 • Footer Strip", badgeColor: "#38bdf8", desc: "Live status telemetry displaying page count, screen time, dialogue-to-action ratio, role counts, scene counts, and zoom controls.", steps: ["Displays: 'SCRIPT TELEMETRY: 31 Pages (~31m screen time) • 28% Dialogue / 72% Action • 10 Roles • 136 Scenes'.", "Jump to Page: Input box to jump instantly to any page number.", "Zoom Slider: Adjusts canvas scaling between 75% and 150%."], tip: "The Dialogue vs. Action percentage alerts you if your script is becoming overly talky or lacking visual action." },

  // Category 4: Keyboard Shortcuts & Standards
  { cat: 4, title: "The Smart Tab & Enter Flow (Typing Cheat Sheet)", badge: "Industry Typing Standard", badgeColor: "#facc15", desc: "Streamlined keyboard transitions that eliminate the need to manually click element formatting buttons.", steps: ["From blank line: Press Tab -> Inserts centered CHARACTER cue in uppercase", "From Character line: Press Tab -> Inserts PARENTHETICAL cue (wryly)", "From Character line: Press Enter -> Moves to next line and indents for DIALOGUE", "From Parenthetical line: Press Enter -> Moves to next line and indents for DIALOGUE", "From Dialogue line: Press Enter -> Starts new dialogue line under same character", "From Dialogue line: Press Enter twice -> Exits dialogue and resets indentation to ACTION", "From Transition line: Press Enter twice -> Inserts two newlines ready for new SCENE HEADING"], tip: "Mastering the Tab/Enter flow enables you to write complete scenes without ever lifting your hands from the keyboard!" },
  { cat: 4, title: "Universal Keyboard Shortcuts Reference", badge: "Keyboard Hotkeys", badgeColor: "#38bdf8", desc: "Complete reference table for standard studio keyboard shortcuts.", steps: ["Ctrl + S: Save Script to SQLite vault and disk", "Ctrl + F: Open inline search and replace bar", "Ctrl + Z: Undo last edit", "Ctrl + Y / Ctrl+Shift+Z: Redo undone edit", "Ctrl + B: Bold selected text", "Ctrl + I: Italicize selected text", "Ctrl + U: Underline selected text", "F1 or Ctrl + H: Open this Hollywood Screenwriting Studio Master Guide", "Enter: Find next match (when in search box)", "Shift + Enter: Find previous match (when in search box)", "Escape: Dismiss search bar or modal dialogs"], tip: "Press F1 anytime in the Writing Studio to instantly bring up this reference guide." },

  // Category 5: Film Budget & Tax Engine
  { cat: 5, title: "Shooting Schedule & Production Stripboard (Tab 1)", badge: "Film Budget Suite • Tab 1", badgeColor: "#facc15", desc: "Recreates physical Hollywood production stripboards using color-coded scene strips. Groups scenes by location and lighting to minimize expensive crew company moves.", steps: ["🟡 Yellow Strips: Day Exterior (EXT. DAY) — Natural daylight filming.", "🔵 Blue Strips: Night Exterior (EXT. NIGHT) — Requires night lighting setups and generator trucks.", "⚪ White Strips: Day Interior (INT. DAY) — Studio or practical location day lighting.", "🟢 Green Strips: Night Interior (INT. NIGHT) — Studio or practical location night lighting.", "🟠 Orange Strips: Dawn, Sunset, Magic Hour, or Special Visual FX setups.", "Click and drag scene strips into Days to build shooting schedules."], tip: "Always schedule Day Interiors after Night Exteriors to provide mandatory 12-hour turnaround rest for crew." },
  { cat: 5, title: "Script Breakdown & Departmental Tagging (Tab 2)", badge: "Film Budget Suite • Tab 2", badgeColor: "#38bdf8", desc: "Categorizes all physical production requirements by department across every individual scene.", steps: ["Cast Members: Speaking roles required on set.", "Props: Action props handled by actors (e.g. key datapad, weapon, suitcase).", "Vehicles & Animals: Picture vehicles and wrangler-managed livestock.", "Wardrobe & Makeup: Special costumes, prosthetics, and makeup effects.", "Special FX: Squibs, explosions, practical rain, or stunt rigging."], tip: "Tagging props early prevents emergency on-set delays during filming days." },
  { cat: 5, title: "Cast Day-Out-of-Days (DOOD) Matrix (Tab 3)", badge: "Film Budget Suite • Tab 3", badgeColor: "#a855f7", desc: "Industry standard grid tracking daily work, hold, and drop statuses for every actor across the entire shooting schedule.", steps: ["W (Work): Actor is called to set and actively shooting.", "S (Start): The actor's first scheduled work day on the production.", "F (Finish): The actor's final scheduled work day on the production.", "H (Hold): Non-working day between work days where the actor is on paid retainer (cannot be booked elsewhere).", "D (Drop): Actor is released from production temporarily (unpaid hiatus).", "P (Pickup): Actor is called back to set after a drop period."], tip: "SAG-AFTRA rules require paying actors for Hold days unless a Drop/Pickup hiatus of at least 10 consecutive days is scheduled." },
  { cat: 5, title: "50-State & International Film Tax Credit Calculator (Tab 4)", badge: "Film Budget Suite • Tab 4", badgeColor: "#22c55e", desc: "Dynamic financial calculation engine covering all 50 US States, Puerto Rico, US Virgin Islands, UK, Canada, and Australia.", steps: ["Georgia: 20% base transferable tax credit + 10% Georgia Entertainment Promotion logo uplift (30% total). No annual cap.", "California: 35% base refundable credit (Program 4.0) + up to 45% outside the LA 30-mile zone.", "New Mexico: 25% base refundable credit + 5% TV series + 5% rural uplift zone + 5% QPF (up to 40% total).", "New York: 30% fully refundable base + 10% upstate wage credit ($800M annual program).", "New Jersey: 35% base north, 40% south + diversity inclusion bonuses.", "Select any state or country from the dropdown to automatically recalculate net qualified spend and tax savings."], tip: "Transferable credits in Georgia and New Jersey can be brokered on the secondary market for 88-92 cents on the dollar for immediate cash flow." },
  { cat: 5, title: "Theatrical Stage Play Capitalization & Operating Suite", badge: "Theatrical Budget Modal", badgeColor: "#ec4899", desc: "Comprehensive theatrical financial suite for Broadway, Off-Broadway, and regional stage productions.", steps: ["Capitalization: Physical production costs (Scenery, Costumes, Lighting, Sound) + rehearsal salaries and advance advertising.", "Weekly Operating Costs: Theater rent, actor/crew weekly salaries, royalties, and ongoing advertising.", "Recoupment Timeline: Interactive model calculating weeks to 100% investor payback based on weekly box office gross percentage."], tip: "Off-Broadway productions typically aim for recoupment within 18 to 26 weeks at 70% average box office capacity." }
];

const ScreenwritingHelpGuideModal = ({ isOpen, onClose }) => {
  const [activeCategory, setActiveCategory] = useState(0);
  const [searchQuery, setSearchQuery] = useState('');

  if (!isOpen) return null;

  const categories = [
    { id: 0, title: "🚀 8-Step Production Workflow", desc: "From blank page to production" },
    { id: 1, title: "🎛️ Action Bar & Top Commands", desc: "10 Primary Studio action tools" },
    { id: 2, title: "🧩 5 Dynamic Ribbon Decks", desc: "Write, Elements, Views, 3D, Production" },
    { id: 3, title: "🧭 Navigation, Sidebar & Layout", desc: "View modes, pagination, Review Pg X" },
    { id: 4, title: "⌨️ Keyboard Shortcuts & Standards", desc: "Smart Tab/Enter flow & hotkeys" },
    { id: 5, title: "🎬 Film Budget & Tax Engine", desc: "Stripboards, DOOD & 50-State credits" },
  ];

  const q = searchQuery.toLowerCase().trim();
  const filteredCards = GUIDE_DATA.filter(card => {
    if (q) {
      const matchText = `${card.title} ${card.badge} ${card.desc} ${(card.steps || []).join(' ')} ${card.tip || ''}`.toLowerCase();
      return matchText.includes(q);
    }
    return card.cat === activeCategory;
  });

  return (
    <div className="fixed inset-0 bg-black/85 flex items-center justify-center z-[9999] p-4 backdrop-blur-sm animate-fade-in">
      <div className="bg-[#080d1a] border border-[#1e293b] rounded-xl max-w-5xl w-full max-h-[90vh] flex flex-col text-white shadow-2xl overflow-hidden font-sans">
        
        {/* Header */}
        <div className="bg-[#0d1527] border-b border-[#1e293b] p-4 flex items-center justify-between gap-4">
          <div>
            <div className="inline-block bg-[#1e293b] text-[#38bdf8] text-[10px] font-bold px-2 py-0.5 rounded border border-[#0284c7] mb-1">
              HOLLYWOOD STUDIO REFERENCE MANUAL
            </div>
            <h2 className="text-lg font-bold text-white flex items-center gap-2">
              📖 Universal Screenwriting Studio — Master Tool & Workflow Guide
            </h2>
            <p className="text-xs text-gray-400">Step-by-step production roadmap, action button manual, dynamic ribbon index, and formatting cheat sheet.</p>
          </div>

          <div className="flex items-center gap-3">
            <input
              type="text"
              placeholder="🔍 Search any tool, button, or shortcut..."
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              className="bg-[#060a12] border border-[#334155] focus:border-[#38bdf8] text-sm text-gray-200 px-3 py-1.5 rounded-lg outline-none w-64"
            />
            <button onClick={onClose} className="text-gray-400 hover:text-white text-2xl font-bold px-2 py-1 leading-none">&times;</button>
          </div>
        </div>

        {/* Body Splitter */}
        <div className="flex flex-1 min-h-0">
          {/* Left Category Navigation */}
          <div className="w-64 bg-[#0a0f1d] border-r border-[#162032] p-3 flex flex-col gap-1 shrink-0 overflow-y-auto">
            <div className="text-[11px] font-bold text-[#38bdf8] uppercase tracking-wider px-2 py-1 mb-1">Guide Sections</div>
            {categories.map(cat => (
              <button
                key={cat.id}
                onClick={() => { setActiveCategory(cat.id); setSearchQuery(''); }}
                className={`text-left px-3 py-2.5 rounded-lg text-xs transition-all flex flex-col gap-0.5 ${activeCategory === cat.id && !searchQuery ? 'bg-[#1e293b] text-[#facc15] font-bold border-l-4 border-[#38bdf8]' : 'text-gray-300 hover:bg-[#162032] hover:text-[#38bdf8]'}`}
              >
                <span>{cat.title}</span>
                <span className="text-[10px] text-gray-400">{cat.desc}</span>
              </button>
            ))}

            <div className="mt-auto pt-4 border-t border-[#162032]">
              <div className="bg-[#0f172a] border border-[#1e293b] rounded-lg p-2.5 text-[11px] text-gray-300">
                <div className="text-[#facc15] font-bold mb-1">💡 Quick Tip</div>
                Press <kbd className="bg-[#1e293b] px-1.5 py-0.5 rounded text-[10px] font-mono text-cyan-400">Tab</kbd> on a blank line to insert a Character cue; press <kbd className="bg-[#1e293b] px-1.5 py-0.5 rounded text-[10px] font-mono text-cyan-400">Enter</kbd> to begin Dialogue.
              </div>
            </div>
          </div>

          {/* Right Scrollable Cards Area */}
          <div className="flex-1 p-4 overflow-y-auto bg-transparent space-y-3">
            {searchQuery && (
              <div className="text-xs text-[#38bdf8] font-bold mb-2">
                Found {filteredCards.length} tool(s) matching "{searchQuery}":
              </div>
            )}

            {filteredCards.map((card, idx) => (
              <div key={idx} className="bg-[#0c1222] border border-[#1e293b] hover:border-[#38bdf8] rounded-xl p-3.5 transition-all shadow-sm">
                <div className="flex items-center justify-between gap-2 mb-1.5">
                  <h3 className="text-sm font-bold text-white">{card.title}</h3>
                  <span className="text-[10px] font-semibold px-2 py-0.5 rounded border" style={{ backgroundColor: '#1e293b', color: card.badgeColor, borderColor: `${card.badgeColor}66` }}>
                    {card.badge}
                  </span>
                </div>
                <p className="text-xs text-gray-300 mb-2 leading-relaxed">{card.desc}</p>
                {card.steps && card.steps.length > 0 && (
                  <div className="bg-[#060a12] border border-[#162032] rounded-lg p-2.5 mb-2 space-y-1">
                    <div className="text-[10px] font-bold text-[#38bdf8] uppercase">How to Use:</div>
                    {card.steps.map((st, sIdx) => (
                      <div key={sIdx} className="text-xs text-gray-400 leading-snug">
                        <span className="text-[#facc15] font-bold mr-1.5">{sIdx + 1}.</span>
                        {st}
                      </div>
                    ))}
                  </div>
                )}
                {card.tip && (
                  <div className="text-[11px] text-[#a7f3d0] leading-snug flex items-start gap-1">
                    <span>💡</span>
                    <span><strong className="text-[#34d399]">Pro-Tip:</strong> {card.tip}</span>
                  </div>
                )}
              </div>
            ))}

            {filteredCards.length === 0 && (
              <div className="text-center py-12 text-gray-500 text-sm">
                No tools or guides found matching "{searchQuery}".
              </div>
            )}
          </div>
        </div>

        {/* Footer */}
        <div className="bg-[#0a0f1d] border-t border-[#1e293b] px-4 py-3 flex items-center justify-between">
          <div className="text-xs text-gray-400">
            AI-BS Sovereign Intelligence Ecosystem • Hollywood Screenwriting Studio
          </div>
          <button
            onClick={onClose}
            className="bg-[#2563eb] hover:bg-[#1d4ed8] text-white text-xs font-bold px-5 py-2 rounded-lg transition-colors cursor-pointer"
          >
            Close Guide
          </button>
        </div>

      </div>
    </div>
  );
};

import './ScreenwritingTab.css';

export default function ScreenwritingTab({ backendUrl, sharedContent, setSharedContent, sharedActiveDoc, onSendToVideoStudio }) {
  const storeBackendUrl = useAppStore(state => state.BACKEND_URL);
  const BACKEND_URL = backendUrl || storeBackendUrl || 'http://127.0.0.1:8000';

  // The loaded project's draft stays authoritative. A parent workspace changing
  // documents must not silently replace this editor and autosave into its project.
  const [localScreenplay, setLocalScreenplay] = useState(() => typeof sharedContent === 'string' ? sharedContent : '');
  const screenplay = localScreenplay;
  const sharedEchoRef = useRef(sharedContent);
  const screenplayRef = useRef(screenplay);
  const draftRevisionRef = useRef(0);
  if (screenplayRef.current !== screenplay) {
    screenplayRef.current = screenplay;
    draftRevisionRef.current += 1;
  }
  const setScreenplay = (content) => {
    screenplayRef.current = content;
    draftRevisionRef.current += 1;
    setLocalScreenplay(content);
    if (setSharedContent) {
      sharedEchoRef.current = content;
      setSharedContent(content);
    }
  };
  const [ast, setAst] = useState([]);
  const [isInternalChange, setIsInternalChange] = useState(false);
  const [parsed, setParsed] = useState(null);
  const [liveHtml, setLiveHtml] = useState('');
  const [projectMetadata, setProjectMetadata] = useState(null);
  const [animatingBeats, setAnimatingBeats] = useState({});
  
  // Layout State
  const [leftPanelVisible, setLeftPanelVisible] = useState(() => typeof window !== 'undefined' ? window.innerWidth >= 850 : true);
  const [navigatorVisible, setNavigatorVisible] = useState(false);
  const [outlineMode, setOutlineMode] = useState('outline1'); // outline1, outline2
  const [activeView, setActiveView] = useState('editor'); // editor, preview, beats
  const [splitMode, setSplitMode] = useState('none'); // none, vertical, horizontal
  const [zoomLevel, setZoomLevel] = useState(100);

  // Find & Replace State
  const [showFindReplace, setShowFindReplace] = useState(false);
  const [findText, setFindText] = useState('');
  const [replaceText, setReplaceText] = useState('');


  // Permanent Page Viewer Navigation State
  const viewerRef = useRef(null);
  const [viewerCurrentPage, setViewerCurrentPage] = useState(1);
  const [viewerSearch, setViewerSearch] = useState('');
  const calculateTotalPages = () => {
    if (!ast || ast.length === 0) return 1;
    let lines = 0;
    ast.forEach(b => {
      const len = (b.text || '').length;
      if (b.type === 'Scene Heading' || b.type === 'Action') lines += 1 + Math.ceil(Math.max(1, len) / 58);
      else if (b.type === 'Character') lines += 1 + Math.ceil(Math.max(1, len) / 38);
      else if (b.type === 'Parenthetical') lines += Math.ceil(Math.max(1, len) / 28);
      else if (b.type === 'Dialogue') lines += Math.ceil(Math.max(1, len) / 38);
      else if (b.type === 'Transition') lines += 1 + Math.ceil(Math.max(1, len) / 20);
      else lines += 1;
    });
    return Math.max(1, Math.ceil(lines / 54));
  };
  const totalScriptPages = calculateTotalPages();

  // Real-Time Hollywood Script Telemetry & Diagnostics
  const calculateScriptDiagnostics = () => {
    if (!ast || ast.length === 0) {
      return {
        pages: 1,
        runtimeStr: '1m',
        dialogueLines: 0,
        actionLines: 0,
        dialoguePct: 0,
        actionPct: 100,
        characterCount: 0,
        sceneCount: 0
      };
    }
    let dialogueLines = 0;
    let actionLines = 0;
    const uniqueChars = new Set();
    let sceneCount = 0;

    ast.forEach(b => {
      const len = (b.text || '').length;
      if (b.type === 'Dialogue' || b.type === 'Parenthetical') {
        dialogueLines += Math.ceil(Math.max(1, len) / 38);
      } else if (b.type === 'Character') {
        const clean = b.text.replace(/\s*\(.*?\)\s*/g, '').replace(/\s*\^/g, '').trim().toUpperCase();
        if (clean) uniqueChars.add(clean);
      } else if (b.type === 'Scene Heading') {
        sceneCount += 1;
        actionLines += 1 + Math.ceil(Math.max(1, len) / 58);
      } else if (b.type === 'Action' || b.type === 'Transition') {
        actionLines += 1 + Math.ceil(Math.max(1, len) / 58);
      }
    });

    const totalLines = dialogueLines + actionLines;
    const dialoguePct = totalLines > 0 ? Math.round((dialogueLines / totalLines) * 100) : 0;
    const actionPct = 100 - dialoguePct;

    const hours = Math.floor(totalScriptPages / 60);
    const mins = totalScriptPages % 60;
    const runtimeStr = hours > 0 ? `${hours}h ${mins}m` : `${mins}m`;

    return {
      pages: totalScriptPages,
      runtimeStr,
      dialogueLines,
      actionLines,
      dialoguePct,
      actionPct,
      characterCount: uniqueChars.size,
      sceneCount: sceneCount || parsed?.beats?.length || 0
    };
  };
  const scriptDiag = calculateScriptDiagnostics();

  // Undo / Redo Stack State
  const [history, setHistory] = useState([ast]);
  const [historyIndex, setHistoryIndex] = useState(0);

  const handleUndo = () => {
    if (historyIndex > 0) {
      const prevIdx = historyIndex - 1;
      setHistoryIndex(prevIdx);
      const prevAst = history[prevIdx];
      setAst(prevAst);
      setIsInternalChange(true);
      setScreenplay(astToFountain(prevAst));
    }
  };

  const handleRedo = () => {
    if (historyIndex < history.length - 1) {
      const nextIdx = historyIndex + 1;
      setHistoryIndex(nextIdx);
      const nextAst = history[nextIdx];
      setAst(nextAst);
      setIsInternalChange(true);
      setScreenplay(astToFountain(nextAst));
    }
  };

  // Branch & Sprint State
  const [branches, setBranches] = useState([]);
  const [currentBranch, setCurrentBranch] = useState('main');
  const [sprints, setSprints] = useState([]);
  const [activeSprint, setActiveSprint] = useState(null);
  const [sprintName, setSprintName] = useState('');
  const [newBranchName, setNewBranchName] = useState('');
  
  // Projects State
  const [projects, setProjects] = useState([]);
  const [currentProject, setCurrentProjectState] = useState('');
  const currentProjectRef = useRef('');
  const setCurrentProject = (project) => {
    currentProjectRef.current = project;
    setCurrentProjectState(project);
  };
  const [archivedProjects, setArchivedProjects] = useState([]);
  const [showArchivedProjects, setShowArchivedProjects] = useState(false);
  const fileInputRef = useRef(null);
  
  const [isLoading, setIsLoading] = useState(false);
  const [isReordering, setIsReordering] = useState(false);
  const reorderInFlightRef = useRef(false);
  const saveCoordinatorRef = useRef(null);
  const backendUrlRef = useRef(BACKEND_URL);
  backendUrlRef.current = BACKEND_URL;
  if (!saveCoordinatorRef.current) {
    saveCoordinatorRef.current = createScreenplayDraftCoordinator({ write: async payload => {
      const response = await fetch(`${backendUrlRef.current}/api/screenwriting/write`, {
        method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(payload),
      });
      const data = await response.json().catch(() => ({}));
      if (!response.ok) throw Object.assign(new Error(typeof data.detail === 'string' ? data.detail : 'Draft save failed.'), { status: response.status });
      return data;
    }});
  }
  const [saveProblem, setSaveProblem] = useState(null);
  const manualReviewRef = useRef(new Set());
  const [recoveryDrafts, setRecoveryDrafts] = useState([]);
  const [incomingWorkspaceDraft, setIncomingWorkspaceDraft] = useState(null);
  const transitionRef = useRef(false);
  const recoveryIdRef = useRef(`${Date.now()}-${Math.random().toString(36).slice(2)}`);
  const editorRef = useRef(null);
  const [draggedBeatIndex, setDraggedBeatIndex] = useState(null);
  const [isProofing, setIsProofing] = useState(false);

  // Navigation & Workspace State
  const [sceneSearch, setSceneSearch] = useState('');
  const [pageJumpInput, setPageJumpInput] = useState('');
  const [activeRibbonTab, setActiveRibbonTab] = useState('write'); // 'write' | 'elements' | 'views' | 'unreal' | 'production'
  const [zenMode, setZenMode] = useState(false);

  const handleJumpToScene = (beat) => {
    if (!beat) return;
    const cleanHeading = (beat.heading || '').trim().toUpperCase();
    const targetBlock = ast.find(b => b.type === 'Scene Heading' && cleanHeading && b.text.trim().toUpperCase().includes(cleanHeading.substring(0, 25)));
    
    // In viewer mode or split mode, forward to viewer ref
    if (viewerRef.current) {
      viewerRef.current.scrollToScene(beat);
    }
    
    if (targetBlock) {
      // In editor mode, safely scroll the editor container internally without displacing page headers
      const editorContainer = document.querySelector('.sw-paginated-container');
      const editorEl = document.getElementById(`sw-block-${targetBlock.id}`);
      if (editorContainer && editorEl) {
        const containerRect = editorContainer.getBoundingClientRect();
        const elRect = editorEl.getBoundingClientRect();
        const targetTop = editorContainer.scrollTop + (elRect.top - containerRect.top) - (containerRect.height / 2);
        editorContainer.scrollTo({ top: Math.max(0, targetTop), behavior: 'smooth' });
        editorEl.focus();
        editorEl.style.transition = 'background-color 0.4s ease, box-shadow 0.4s ease';
        editorEl.style.backgroundColor = 'rgba(250, 204, 21, 0.25)';
        editorEl.style.boxShadow = '0 0 16px rgba(250, 204, 21, 0.5)';
        setTimeout(() => { 
          editorEl.style.backgroundColor = 'transparent'; 
          editorEl.style.boxShadow = 'none';
        }, 1600);
      }
    } else if (beat.page) {
      handleJumpToPage(Math.floor(beat.page));
    }
  };

  const handleJumpToPage = (pageNum) => {
    if (!pageNum || isNaN(pageNum)) return;
    const validPage = Math.max(1, Math.min(pageNum, totalScriptPages));
    setViewerCurrentPage(validPage);
    
    // Jump in viewer
    if (viewerRef.current) {
      viewerRef.current.scrollToPage(validPage);
    }
    
    // Jump in editor
    const editorContainer = document.querySelector('.sw-paginated-container');
    const pageEl = document.getElementById(`sw-page-${validPage}`);
    if (editorContainer && pageEl) {
      const containerRect = editorContainer.getBoundingClientRect();
      const elRect = pageEl.getBoundingClientRect();
      const targetTop = editorContainer.scrollTop + (elRect.top - containerRect.top) - 20;
      editorContainer.scrollTo({ top: Math.max(0, targetTop), behavior: 'smooth' });
      pageEl.style.transition = 'box-shadow 0.4s ease';
      pageEl.style.boxShadow = '0 0 25px rgba(56, 189, 248, 0.7)';
      setTimeout(() => { pageEl.style.boxShadow = '0 4px 12px rgba(0,0,0,0.5)'; }, 1500);
    }
  };

  useEffect(() => {
    const handleGlobalKeyDown = (e) => {
      if (e.key === 'Escape' && zenMode) {
        setZenMode(false);
      }
      if (e.key === 'F1' || (e.ctrlKey && e.key.toLowerCase() === 'h')) {
        e.preventDefault();
        setShowHelpGuideModal(prev => !prev);
      }
    };
    window.addEventListener('keydown', handleGlobalKeyDown);
    return () => window.removeEventListener('keydown', handleGlobalKeyDown);
  }, [zenMode]);

  // Hollywood Help Guide & Tool Manual State
  const [showHelpGuideModal, setShowHelpGuideModal] = useState(false);

  // New Project State
  const [showNewProjectModal, setShowNewProjectModal] = useState(false);
  const [showNovelizerModal, setShowNovelizerModal] = useState(false);
  const [showTableReadModal, setShowTableReadModal] = useState(false);
  const [newProjectName, setNewProjectName] = useState('');
  const [newProjectTemplate, setNewProjectTemplate] = useState('feature');
  const [newProjectAuthor, setNewProjectAuthor] = useState('Screenwriter');

  // AI Adapter State
  const [showAdaptModal, setShowAdaptModal] = useState(false);
  const [adaptFile, setAdaptFile] = useState(null);
  const [adaptProjectName, setAdaptProjectName] = useState('');
  const [adaptType, setAdaptType] = useState('Feature Film');
  const [adaptProgress, setAdaptProgress] = useState(null);
  const [isAdapting, setIsAdapting] = useState(false);

  // AI Ghostwriter State
  const [isGhostwriting, setIsGhostwriting] = useState(false);
  const [showCoverage, setShowCoverage] = useState(false);
  const [showStoryboards, setShowStoryboards] = useState(false);
  const [storyboards, setStoryboards] = useState([]);
  const [generatingStoryboards, setGeneratingStoryboards] = useState(false);
  const [coverageData, setCoverageData] = useState(null);
  const [isGeneratingCoverage, setIsGeneratingCoverage] = useState(false);
  const [showCharacterVault, setShowCharacterVault] = useState(false);
  const [characters, setCharacters] = useState([]);

  // Professional Features State
  const [isRevisionMode, setIsRevisionMode] = useState(false);
  const [revisionColor, setRevisionColor] = useState('blue');
  const [showAnalyticsOverlay, setShowAnalyticsOverlay] = useState(false);
  const [showProductionBreakdown, setShowProductionBreakdown] = useState(false);
  const [showStagePlayBreakdown, setShowStagePlayBreakdown] = useState(false);
  const [showScriptTelemetryModal, setShowScriptTelemetryModal] = useState(false);

  // Page Review & !proof State
  const [showPageReviewModal, setShowPageReviewModal] = useState(false);
  const [reviewPageNum, setReviewPageNum] = useState(1);
  const [isReviewingPage, setIsReviewingPage] = useState(false);
  const [reviewOriginalFountain, setReviewOriginalFountain] = useState('');
  const [reviewSuggestedFountain, setReviewSuggestedFountain] = useState('');
  const [reviewPageIndices, setReviewPageIndices] = useState({ start: 0, end: 0 });
  const [reviewStatusMessage, setReviewStatusMessage] = useState('');

  // Dedicated Script & Memoir Assistant Drawer State
  const [showScriptAssistant, setShowScriptAssistant] = useState(false);

  // Dedicated Audio Adaptation Master Track State
  const [showAudioPlayer, setShowAudioPlayer] = useState(true);

  // New Project Creation Handlers
  const handleCreateNewProject = async () => {
    if (!newProjectName.trim()) {
      alert("Please enter a project name.");
      return;
    }
    if (transitionRef.current) return;
    transitionRef.current = true; setIsLoading(true);
    try {
      const departingDraft = await flushDraftForTransition();
      const res = await fetch(`${BACKEND_URL}/api/screenwriting/projects/create`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          project_name: newProjectName.trim(),
          template: newProjectTemplate,
          author: newProjectAuthor.trim() || 'Screenwriter'
        })
      });
      const data = await res.json();
      if (data.status === 'success') {
        setShowNewProjectModal(false);
        setNewProjectName('');
        await loadProjects();
        if (!draftStillCurrent(departingDraft)) throw new Error('Project created. Your newer edits remain open; select the new project when ready.');
        await loadScreenplay(data.current);
        await loadBranches();
        await loadSprints();
        await loadCharacters();
      } else {
        alert(`Failed to create project: ${data.detail || data.message || 'Unknown error'}`);
      }
    } catch (err) {
      alert(`Error creating project: ${err.message}`);
    } finally { transitionRef.current = false; setIsLoading(false); }
  };

  const handleDeleteCurrentProject = async () => {
    if (currentProject === 'Default Project') {
      alert("Cannot archive the Default Project.");
      return;
    }
    if (!currentProject || loadedProjectRef.current !== currentProject || isLoading) return;
    if (!confirm(`Archive "${currentProject}"? Its script, assets, and history will be preserved. Use Archived projects to restore it.`)) {
      return;
    }
    if (transitionRef.current) return;
    setIsLoading(true);
    if (autoSaveTimerRef.current) clearTimeout(autoSaveTimerRef.current);
    const projectToArchive = currentProject;
    transitionRef.current = true;
    try {
      const captured = await flushDraftForTransition();
      if (!draftStillCurrent(captured)) return;
      const res = await fetch(`${BACKEND_URL}/api/screenwriting/projects/archive`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ project_name: projectToArchive })
      });
      const data = await res.json();
      if (!res.ok) throw new Error(data.detail || 'Project could not be archived.');
      await loadProjects();
      if (!draftStillCurrent(captured)) {
        manualReviewRef.current.add(projectToArchive);
        preserveDraft(captureDraft());
        throw new Error('Project archived, but newer local edits remain open. Download them before loading another project.');
      }
      await loadScreenplay(data.current || 'Default Project');
      if (showArchivedProjects) await loadArchivedProjects();
    } catch (err) {
      setSaveProblem({ project: projectToArchive, message: err.message });
      alert(`Error archiving project: ${err.message}`);
    } finally {
      transitionRef.current = false;
      setIsLoading(false);
    }
  };

  const loadArchivedProjects = async () => {
    try {
      const res = await fetch(`${BACKEND_URL}/api/screenwriting/projects/archives`);
      const data = await res.json();
      if (!res.ok) throw new Error(data.detail || 'Could not load archived projects.');
      setArchivedProjects(data.archives || []);
    } catch (err) { alert(err.message); }
  };

  const handleRestoreProject = async (archiveId) => {
    if (transitionRef.current) return;
    transitionRef.current = true;
    setIsLoading(true);
    try {
      const departingDraft = await flushDraftForTransition();
      const res = await fetch(`${BACKEND_URL}/api/screenwriting/projects/restore`, {
        method: 'POST', headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ archive_id: archiveId })
      });
      const data = await res.json();
      if (!res.ok) throw new Error(data.detail || 'Could not restore project.');
      await loadProjects();
      if (!draftStillCurrent(departingDraft)) throw new Error('Project restored. Your newer edits remain open; select the restored project when ready.');
      await loadScreenplay(data.current);
      await loadArchivedProjects();
    } catch (err) {
      alert(err.message);
    }
    finally { transitionRef.current = false; setIsLoading(false); }
  };

  // Parse Screenplay helper
  const parseScreenplay = async (contentToParse) => {
    const sequence = screenplayLoadSequenceRef.current;
    const draft = contentToParse ?? screenplayRef.current;
    try {
      // Local real-time fountain-js parse for split-pane preview
      const htmlOutput = fountainParser.parse(draft);
      if (htmlOutput && htmlOutput.html && htmlOutput.html.script) {
        setLiveHtml(htmlOutput.html.script);
      }

      // Backend parse for Beat Board extraction, scene analysis, CMS
      const res = await fetch(`${BACKEND_URL}/api/screenwriting/parse`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ content: draft }),
      });
      const data = await res.json();
      if (sequence === screenplayLoadSequenceRef.current && draft === screenplayRef.current) setParsed(data);
    } catch (err) {
      console.error('Parse failed:', err);
    }
  };

  // Instantaneous parse effect
  useEffect(() => {
    if (!isInternalChange && screenplay) {
        setAst(fountainToAST(screenplay));
    }
    setIsInternalChange(false);
    
    const htmlOutput = fountainParser.parse(screenplay);
    if (htmlOutput && htmlOutput.html && htmlOutput.html.script) {
        setLiveHtml(htmlOutput.html.script);
    }
  }, [screenplay]);

  const handleAstChange = (newAst) => {
    setAst(newAst);
    setIsInternalChange(true);
    setScreenplay(astToFountain(newAst));
    setHistory(prev => {
      const upToCurrent = prev.slice(0, historyIndex + 1);
      const updated = [...upToCurrent, newAst];
      if (updated.length > 100) updated.shift();
      return updated;
    });
    setHistoryIndex(prev => Math.min(prev + 1, 99));
  };

  const loadProjects = async () => {
      try {
          const res = await fetch(`${BACKEND_URL}/api/screenwriting/projects`);
          const data = await res.json();
          setProjects(data.projects || []);
          if (!currentProjectRef.current) setCurrentProject(data.current || '');
      } catch (err) {
          console.error('Failed to load projects:', err);
      }
  };

  const loadedProjectRef = useRef('');
  const screenplayLoadSequenceRef = useRef(0);
  const loadScreenplay = async (targetProj, { reload = false } = {}) => {
    // Fetch first, then replace the visible draft only if no edit happened while
    // saving or loading. Failed reads leave the existing editor/project intact.
    if (reorderInFlightRef.current) return false;
    const sequence = ++screenplayLoadSequenceRef.current;
    try {
      const captured = reload ? captureDraft() : await flushDraftForTransition();
      const sharedProject = typeof sharedActiveDoc === 'string' ? sharedActiveDoc : '';
      const proj = targetProj || sharedProject || currentProjectRef.current;
      const hasSharedDraft = !loadedProjectRef.current && !targetProj && !!sharedProject && typeof sharedContent === 'string';
      const initialDraft = screenplayRef.current;
      const initialEdit = draftRevisionRef.current;
      const queryParam = proj ? `?project_name=${encodeURIComponent(proj)}` : '';
      const res = await fetch(`${BACKEND_URL}/api/screenwriting/read${queryParam}`);
      if (!res.ok) throw new Error(`Project load failed (${res.status})`);
      const data = await res.json();
      if (sequence !== screenplayLoadSequenceRef.current) return false;
      if ((captured && !draftStillCurrent(captured)) || draftRevisionRef.current !== initialEdit) {
        throw new Error('Your draft changed during loading. It is still open; retry the project change when ready.');
      }
      saveCoordinatorRef.current.load(data.project, data.content, data.revision);
      manualReviewRef.current.delete(data.project);
      loadedProjectRef.current = data.project;
      setCurrentProject(data.project);
      setSaveProblem(null);
      setCharacters([]);
      setShowCharacterVault(false);
      setDraggedBeatIndex(null);
      const content = hasSharedDraft ? initialDraft : data.content;
      setScreenplay(content);
      setAst(fountainToAST(content));
      setLastSavedTime(null);
      setAutoSaveStatus(content === data.content ? 'saved' : 'unsaved');
      // A shared-workspace draft has no historical disk baseline. Keep it visible,
      // but require an explicit review/save instead of autosaving on initial load.
      if (hasSharedDraft && content !== data.content) {
        manualReviewRef.current.add(data.project);
        setSaveProblem({ project: data.project, message: 'Workspace draft retained. Review it against the saved version before choosing Save.', reviewOnly: true });
        preserveDraft({ project: data.project, content, revision: data.revision });
      }
      refreshRecoveryDrafts(data.project);
      await parseScreenplay(content);
      if (sequence !== screenplayLoadSequenceRef.current) return true;
      setCurrentBranch(data.metadata?.current_branch || 'main');
      setProjectMetadata(data.metadata || {});
      await loadCharacters(data.project);
      return true;
    } catch (err) {
      setSaveProblem({ project: loadedProjectRef.current || targetProj, message: err.message });
      return false;
    }
  };

  const loadBranches = async () => {
    try {
      const res = await fetch(`${BACKEND_URL}/api/screenwriting/branches`);
      const data = await res.json();
      setBranches(data.branches || []);
      setCurrentBranch(data.current || 'main');
    } catch (err) {
      console.error('Failed to load branches:', err);
    }
  };


  const loadCharacters = async (targetProject = loadedProjectRef.current) => {
    const project = targetProject;
    const sequence = screenplayLoadSequenceRef.current;
    if (!project || loadedProjectRef.current !== project || currentProjectRef.current !== project) return;
    try {
      const res = await fetch(`${BACKEND_URL}/api/screenwriting/projects/characters?project_name=${encodeURIComponent(project)}`);
      const data = await res.json();
      if (sequence !== screenplayLoadSequenceRef.current || loadedProjectRef.current !== project || currentProjectRef.current !== project) return;
      if (res.ok && data.status === 'success') setCharacters(data.characters || []);
    } catch (err) {
      console.error('Failed to load characters:', err);
    }
  };

  const loadSprints = async () => {
    try {
      const res = await fetch(`${BACKEND_URL}/api/screenwriting/sprints`);
      const data = await res.json();
      setSprints(data.sprints || []);
    } catch (err) {
      console.error('Failed to load sprints:', err);
    }
  };

  // Initial Load
  useEffect(() => {
    loadProjects();
    loadScreenplay();
    loadBranches();
    loadSprints();
  }, []);

  const autoSaveTimerRef = useRef(null);
  const [autoSaveStatus, setAutoSaveStatus] = useState('saved');
  const [lastSavedTime, setLastSavedTime] = useState(null);

  const captureDraft = () => {
    const project = loadedProjectRef.current;
    if (!project || project !== currentProjectRef.current) return null;
    return { project, content: screenplayRef.current, edit: draftRevisionRef.current, branch: currentBranch,
      revision: saveCoordinatorRef.current.snapshot(project)?.revision };
  };
  const draftStillCurrent = draft => !draft || (loadedProjectRef.current === draft.project && currentProjectRef.current === draft.project &&
    screenplayRef.current === draft.content && draftRevisionRef.current === draft.edit);
  const preserveDraft = (draft, recoveryId = recoveryIdRef.current) => {
    if (!draft) return false;
    try {
      const key = `aibs_script_recovery_${encodeURIComponent(draft.project)}_${recoveryId}`;
      localStorage.setItem(key, JSON.stringify({ ...draft, savedAt: new Date().toISOString() }));
      return true;
    } catch {
      setSaveProblem({ project: draft.project, message: 'Browser recovery storage is unavailable. Download your local draft before leaving.' });
      return false;
    }
  };
  const refreshRecoveryDrafts = project => {
    try {
      const prefix = `aibs_script_recovery_${encodeURIComponent(project)}_`;
      const entries = Object.keys(localStorage).filter(key => key.startsWith(prefix)).map(key => {
        try { return { ...JSON.parse(localStorage.getItem(key)), key }; } catch { return null; }
      }).filter(item => item && typeof item.content === 'string');
      setRecoveryDrafts(entries.sort((a,b) => b.savedAt.localeCompare(a.savedAt)));
    } catch { setRecoveryDrafts([]); }
  };
  const downloadLocalDraft = (draft = captureDraft()) => {
    if (!draft) return;
    const url = URL.createObjectURL(new Blob([draft.content], { type: 'text/plain;charset=utf-8' }));
    const link = document.createElement('a');
    link.href = url;
    link.download = `${draft.project}-recovered-${Date.now()}.fountain`;
    document.body.appendChild(link); link.click(); link.remove();
    setTimeout(() => URL.revokeObjectURL(url), 1000);
  };
  const reportSaveFailure = (draft, error) => {
    if (draftStillCurrent(draft)) setAutoSaveStatus('error');
    preserveDraft(loadedProjectRef.current === draft?.project ? captureDraft() : draft);
    setSaveProblem({ project: draft?.project, conflict: error.status === 409,
      message: error.status === 409 ? 'Another tab or process changed this project. Your local draft is retained; saving has stopped to protect both versions.' : `${error.message} Your local draft is retained.` });
  };
  const saveCapturedDraft = async draft => {
    if (!draft) throw new Error('Wait for the project to load before saving.');
    if (saveCoordinatorRef.current.isDirty(draft.project, draft.content)) preserveDraft(draft);
    try {
      const result = await saveCoordinatorRef.current.save(draft.project, draft.content, draft.branch);
      if (draftStillCurrent(draft)) {
        setAutoSaveStatus('saved'); setSaveProblem(null);
        if (!result.unchanged) setLastSavedTime(new Date().toLocaleTimeString());
      }
      return result;
    } catch (error) { reportSaveFailure(draft, error); throw error; }
  };
  const flushDraftForTransition = async () => {
    if (autoSaveTimerRef.current) clearTimeout(autoSaveTimerRef.current);
    if (reorderInFlightRef.current) throw new Error('Wait for scene reordering to finish before changing projects.');
    const draft = captureDraft();
    if (!draft) return null;
    if (manualReviewRef.current.has(draft.project)) throw new Error('Review and save the local draft, or download it and reload the saved version first.');
    await saveCapturedDraft(draft);
    if (!draftStillCurrent(draft)) throw new Error('Your draft changed while saving. The project stays open; retry after your latest edits save.');
    return draft;
  };
  const reloadSavedVersion = async () => {
    const draft = captureDraft();
    if (!draft || transitionRef.current) return;
    if (!preserveDraft(draft)) { downloadLocalDraft(draft); return; }
    if (!confirm('Reload the saved version? Your current text will remain in browser recovery copies. Download it first if you want a separate file.')) return;
    // Retain this recovery snapshot even after the user edits the reloaded copy.
    recoveryIdRef.current = `${Date.now()}-${Math.random().toString(36).slice(2)}`;
    if (autoSaveTimerRef.current) clearTimeout(autoSaveTimerRef.current);
    transitionRef.current = true; setIsLoading(true);
    try {
      await saveCoordinatorRef.current.idle();
      if (draftStillCurrent(draft)) await loadScreenplay(draft.project, { reload: true });
    } finally { transitionRef.current = false; setIsLoading(false); }
  };

  useEffect(() => {
    if (typeof sharedContent !== 'string' || sharedContent === sharedEchoRef.current) return;
    sharedEchoRef.current = sharedContent;
    if (sharedContent === screenplayRef.current) return;
    const incoming = { project: typeof sharedActiveDoc === 'string' && sharedActiveDoc ? sharedActiveDoc : 'Workspace draft', content: sharedContent };
    preserveDraft(incoming, `workspace-${Date.now()}-${Math.random().toString(36).slice(2)}`);
    setIncomingWorkspaceDraft(incoming);
  }, [sharedContent, sharedActiveDoc]);

  useEffect(() => {
    const onUnload = event => {
      const draft = captureDraft();
      if (draft && (saveCoordinatorRef.current.isDirty(draft.project, draft.content) || saveCoordinatorRef.current.snapshot(draft.project)?.blocked)) {
        preserveDraft(draft); event.preventDefault(); event.returnValue = '';
      }
    };
    window.addEventListener('beforeunload', onUnload);
    return () => window.removeEventListener('beforeunload', onUnload);
  }, []);

  useEffect(() => {
    const draft = captureDraft();
    if (!draft) return;
    if (!saveCoordinatorRef.current.isDirty(draft.project, draft.content)) return;
    preserveDraft(draft);
    if (autoSaveTimerRef.current) clearTimeout(autoSaveTimerRef.current);
    if (isLoading || isReordering || transitionRef.current || reorderInFlightRef.current || saveCoordinatorRef.current.snapshot(draft.project)?.blocked || manualReviewRef.current.has(draft.project)) return;
    setAutoSaveStatus('unsaved');
    autoSaveTimerRef.current = setTimeout(async () => {
      if (!draftStillCurrent(draft) || transitionRef.current || reorderInFlightRef.current) return;
      setAutoSaveStatus('saving');
      try { await saveCapturedDraft(draft); } catch { /* The visible recovery notice retains the error. */ }
    }, 1500);
    return () => clearTimeout(autoSaveTimerRef.current);
  }, [screenplay, currentProject, currentBranch, BACKEND_URL, isLoading, isReordering, saveProblem?.reviewOnly]);

  const handleSaveScreenplay = async () => {
    if (transitionRef.current || reorderInFlightRef.current) return;
    const draft = captureDraft();
    if (autoSaveTimerRef.current) clearTimeout(autoSaveTimerRef.current);
    setIsLoading(true); setAutoSaveStatus('saving');
    try {
      await saveCapturedDraft(draft);
      manualReviewRef.current.delete(draft.project);
    }
    catch { /* Keep the local draft and visible recovery controls. */ }
    finally { setIsLoading(false); }
  };

  const handleExportFDX = () => {
    const xml = serializeFDX(ast);
    const blob = new Blob([xml], { type: "text/xml" });
    const url = URL.createObjectURL(blob);
    const link = document.createElement("a");
    link.href = url;
    link.download = `${currentProject || 'screenplay'}.fdx`;
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
    URL.revokeObjectURL(url);
  };

  const downloadScreenplayExport = async (format, watermark = '') => {
    if (!currentProject || loadedProjectRef.current !== currentProject || isLoading) {
      alert('Wait for the selected project to finish loading before exporting.');
      return;
    }
    const project = currentProject;
    const draft = captureDraft();
    if (autoSaveTimerRef.current) clearTimeout(autoSaveTimerRef.current);
    setIsLoading(true);
    try {
      if (manualReviewRef.current.has(project)) throw new Error('Review and save the local draft before exporting, or download it from the draft protection notice.');
      await saveCapturedDraft(draft);
      const query = new URLSearchParams({ project_name: project });
      if (watermark) query.set('watermark', watermark);
      const response = await fetch(`${BACKEND_URL}/api/screenwriting/export/${format}?${query}`);
      if (!response.ok) {
        const error = await response.json().catch(() => ({}));
        throw new Error(error.detail || `Export failed (HTTP ${response.status}).`);
      }
      const blob = await response.blob();
      if (format === 'pdf' && (await blob.slice(0, 5).text()) !== '%PDF-') {
        throw new Error('The export service did not return a PDF.');
      }
      const url = URL.createObjectURL(blob);
      const link = document.createElement('a');
      link.href = url;
      link.download = `${project}.${format}`;
      document.body.appendChild(link);
      link.click();
      link.remove();
      setTimeout(() => URL.revokeObjectURL(url), 1000);
    } catch (error) {
      alert(`Export failed: ${error.message}`);
    } finally {
      setIsLoading(false);
    }
  };

  const handleExportPDF = () => downloadScreenplayExport('pdf');

  const handleCreateBranch = async () => {
    if (!newBranchName.trim()) return;
    try {
      const res = await fetch(`${BACKEND_URL}/api/screenwriting/branch/create`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ branch_name: newBranchName }),
      });
      const data = await res.json();
      if (data.status === 'success') {
        await loadBranches();
        setNewBranchName('');
      }
    } catch (err) {
      console.error('Branch creation failed:', err);
    }
  };

  const handleStartSprint = async () => {
    if (!sprintName.trim()) return;
    try {
      const res = await fetch(`${BACKEND_URL}/api/screenwriting/sprint/start`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ name: sprintName, target_pages: 10 }),
      });
      const data = await res.json();
      if (data.sprint) {
        setActiveSprint(data.sprint);
        setSprintName('');
        await loadSprints();
      }
    } catch (err) {
      console.error('Sprint start failed:', err);
    }
  };

  const handleEndSprint = async () => {
    if (!activeSprint) return;
    try {
      const res = await fetch(`${BACKEND_URL}/api/screenwriting/sprint/end`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ sprint_id: activeSprint.id }),
      });
      const data = await res.json();
      if (data.status === 'success') {
        setActiveSprint(null);
        await loadSprints();
      }
    } catch (err) {
      console.error('Sprint end failed:', err);
    }
  };

  // Drag and Drop Beat Reordering
  const handleDragStart = (e, index) => {
    setDraggedBeatIndex(index);
    e.dataTransfer.effectAllowed = 'move';
  };

  const handleDragOver = (e) => {
    e.preventDefault();
  };

  const handleDrop = async (e, targetIndex) => {
    e.preventDefault();
    if (draggedBeatIndex === null || draggedBeatIndex === targetIndex) return;
    const project = loadedProjectRef.current;
    if (!project || currentProjectRef.current !== project || isLoading || reorderInFlightRef.current) return;
    const sequence = screenplayLoadSequenceRef.current;
    const draft = screenplayRef.current;
    const revision = draftRevisionRef.current;
    const isCurrent = () => sequence === screenplayLoadSequenceRef.current && loadedProjectRef.current === project && currentProjectRef.current === project;
    if (autoSaveTimerRef.current) clearTimeout(autoSaveTimerRef.current);
    reorderInFlightRef.current = true;
    setIsReordering(true);
    setIsLoading(true);
    try {
      const data = await saveCoordinatorRef.current.mutate(project, draft, async payload => {
        if (!isCurrent() || draftRevisionRef.current !== revision) throw new Error('The draft changed while waiting to reorder. Retry the move.');
        const res = await fetch(`${BACKEND_URL}/api/screenwriting/beats/reorder`, {
          method: 'POST', headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ ...payload, expected_revision: payload.expected_revision, source_index: draggedBeatIndex, target_index: targetIndex }),
        });
        const result = await res.json();
        if (!res.ok) throw Object.assign(new Error(typeof result.detail === 'string' ? result.detail : 'Beat reordering failed.'), { status: res.status });
        return result;
      });
      if (!isCurrent()) return;
      if (draftRevisionRef.current !== revision || screenplayRef.current !== draft) {
        // The remote order changed, while this editor has newer edits. Keep those
        // edits, block automatic saving, and require an explicit recovery decision.
        const state = saveCoordinatorRef.current.snapshot(project);
        manualReviewRef.current.add(project);
        setSaveProblem({ project, reviewOnly: true, message: 'Scene order was saved, but newer local edits are still open. Review them before saving or reload the saved order.' });
        preserveDraft({ project, content: screenplayRef.current, revision: state?.revision });
        return;
      }
      if (data.status === 'success' && typeof data.content === 'string') {
        setParsed(data.parsed);
        setScreenplay(data.content);
        setAst(fountainToAST(data.content));
        if (data.warning) alert(`Beat order saved. ${data.warning}`);
      }
    } catch (err) {
      reportSaveFailure({ project, content: screenplayRef.current, edit: draftRevisionRef.current }, err);
      if (isCurrent()) alert(err.message);
    } finally {
      reorderInFlightRef.current = false;
      setIsReordering(false);
      if (isCurrent()) {
        setIsLoading(false);
        setDraggedBeatIndex(null);
      }
    }
  };

  const handleSwitchProject = async (proj) => {
    if (!proj || transitionRef.current || reorderInFlightRef.current) return;
    transitionRef.current = true; setIsLoading(true);
    try {
      const departingDraft = await flushDraftForTransition();
      const response = await fetch(`${BACKEND_URL}/api/screenwriting/projects/switch`, {
        method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ project_name: proj }),
      });
      if (!response.ok) { const error = await response.json(); throw new Error(error.detail || 'Project switch failed.'); }
      await loadProjects();
      if (!draftStillCurrent(departingDraft)) throw new Error('Your draft changed during the switch. It remains open; retry when ready.');
      if (await loadScreenplay(proj)) { await loadBranches(); await loadSprints(); }
    } catch (error) { setSaveProblem({ project: currentProjectRef.current, message: error.message }); }
    finally { transitionRef.current = false; setIsLoading(false); }
  };

  const handleAnimateBeat = async (beat) => {
      const project = loadedProjectRef.current;
      if (!project || currentProjectRef.current !== project || isLoading) return;
      const sequence = screenplayLoadSequenceRef.current;
      const isCurrent = () => sequence === screenplayLoadSequenceRef.current && loadedProjectRef.current === project && currentProjectRef.current === project;
      setAnimatingBeats(prev => ({...prev, [beat.id]: true}));
      try {
          const prompt = beat.heading + " " + beat.summary;
          const res = await fetch(`${BACKEND_URL}/api/video/test_pipeline`, {
              method: 'POST',
              headers: {'Content-Type': 'application/json'},
              body: JSON.stringify({ prompt: prompt })
          });
          const data = await res.json();
          if (data.status === 'success') {
               // Hardcoded HLS stream for now as output from VLC transcoder
               const videoUrl = `${BACKEND_URL}/streams/test_output.m3u8`;
               
               const saved = await fetch(`${BACKEND_URL}/api/screenwriting/projects/scene_video`, {
                   method: 'POST',
                   headers: {'Content-Type': 'application/json'},
                   body: JSON.stringify({ project_name: project, beat_id: beat.id, video_url: videoUrl })
               });
               if (!saved.ok) throw new Error('Scene video could not be saved.');
               if (isCurrent()) setProjectMetadata(prev => ({...prev, beat_videos: {...prev?.beat_videos, [beat.id]: videoUrl}}));
          }
      } catch(err) {
          console.error(err);
      } finally {
          if (isCurrent()) setAnimatingBeats(prev => ({...prev, [beat.id]: false}));
      }
  };

  const convertFdxToFountain = (xmlString) => {
      const parser = new DOMParser();
      const xmlDoc = parser.parseFromString(xmlString, "text/xml");
      const paragraphs = xmlDoc.getElementsByTagName("Paragraph");
      let fountain = "";
      
      for (let i = 0; i < paragraphs.length; i++) {
          const p = paragraphs[i];
          const type = p.getAttribute("Type");
          const texts = p.getElementsByTagName("Text");
          let content = "";
          for (let j = 0; j < texts.length; j++) {
              content += texts[j].textContent;
          }
          
          if (!content.trim()) {
              fountain += "\n";
              continue;
          }
          
          if (type === "Scene Heading") {
              fountain += content.toUpperCase() + "\n\n";
          } else if (type === "Action") {
              fountain += content + "\n\n";
          } else if (type === "Character") {
              fountain += content.toUpperCase() + "\n";
          } else if (type === "Parenthetical") {
              if (content.startsWith('(') && content.endsWith(')')) {
                  fountain += content + "\n";
              } else {
                  fountain += "(" + content + ")\n";
              }
          } else if (type === "Dialogue") {
              fountain += content + "\n\n";
          } else if (type === "Transition") {
              fountain += "> " + content.toUpperCase() + "\n\n";
          } else {
              fountain += content + "\n\n";
          }
      }
      return fountain.trim();
  };

  const handleImportClick = () => {
      fileInputRef.current?.click();
  };

  const handleFileChange = async (e) => {
      const file = e.target.files?.[0];
      if (!file) return;
      const sequence = screenplayLoadSequenceRef.current;
      const initiatingProject = currentProjectRef.current;
      const isCurrent = () => sequence === screenplayLoadSequenceRef.current && currentProjectRef.current === initiatingProject;
      
      const fileName = file.name.toLowerCase();
      const validExts = ['.pdf', '.docx', '.doc', '.epub', '.txt', '.rtf', '.md', '.markdown', '.fountain', '.fdx'];
      if (!validExts.some(ext => fileName.endsWith(ext))) {
          alert("Unsupported file format. Please upload a .pdf, .docx, .epub, .txt, .rtf, .md, .fdx, or .fountain file.");
          e.target.value = '';
          return;
      }
      
      const defaultName = currentProject || "Default Project";
      
      // If it's a manuscript/book file, open the Hollywood Adaptation Modal
      if (fileName.endsWith('.pdf') || fileName.endsWith('.docx') || fileName.endsWith('.doc') || fileName.endsWith('.epub') || fileName.endsWith('.rtf') || fileName.endsWith('.txt') || fileName.endsWith('.md') || fileName.endsWith('.markdown')) {
          setAdaptFile(file);
          setAdaptProjectName(defaultName);
          setShowAdaptModal(true);
          e.target.value = '';
          return;
      }
      
      // Direct screenplay script import (.fdx or .fountain)
      const projName = prompt("Import screenplay as a new project (existing projects are preserved):", file.name.replace(/\.(fdx|fountain)$/i, ''));
      if (!projName) {
          e.target.value = '';
          return;
      }
      
      const reader = new FileReader();
      reader.onload = async (ev) => {
          let text = ev.target.result;
          
          if (file.name.toLowerCase().endsWith('.fdx')) {
              const newAst = parseFDX(text);
              text = astToFountain(newAst);
          }
          
          if (!isCurrent() || transitionRef.current) return;
          transitionRef.current = true;
          setIsLoading(true);
          try {
              const departingDraft = await flushDraftForTransition();
              const response = await fetch(`${BACKEND_URL}/api/screenwriting/projects/import`, {
                  method: 'POST',
                  headers: { 'Content-Type': 'application/json' },
                  body: JSON.stringify({ project_name: projName, content: text })
              });
              const data = await response.json();
              if (!response.ok) throw new Error(data.detail || 'The screenplay could not be imported.');
              const importedProject = data.project || data.current;
              if (!importedProject) throw new Error('Import did not return a project name.');
              if (!isCurrent()) return;
              await loadProjects();
              if (!isCurrent()) return;
              if (!draftStillCurrent(departingDraft)) throw new Error('Import created. Your newer edits remain open; select the imported project when ready.');
              await loadScreenplay(importedProject);
              await loadBranches();
              await loadSprints();
              if (currentProjectRef.current === importedProject) setIsLoading(false);
          } catch(err) {
              console.error(err);
              if (isCurrent()) {
                  alert(`Import failed: ${err.message}`);
                  setIsLoading(false);
              }
          } finally { transitionRef.current = false; setIsLoading(false); }
      };
      reader.readAsText(file);
      e.target.value = '';
  };

  const handleStartAdaptation = async (forceRestart = false) => {
      if (!adaptFile || !adaptProjectName) return;
      try { await flushDraftForTransition(); } catch (error) { alert(error.message); return; }
      setIsAdapting(true);
      setShowAdaptModal(false);
      setAdaptProgress({ status: 'processing', progress: 0, current_chunk: 0, total_chunks: 0 });
      
      const formData = new FormData();
      formData.append('file', adaptFile);
      formData.append('project_name', adaptProjectName);
      formData.append('adaptation_type', adaptType);
      if (forceRestart) {
        formData.append('force', 'true');
      }
      
      try {
          const res = await fetch(`${BACKEND_URL}/api/screenplay/adapt`, {
              method: 'POST',
              body: formData
          });
          const resData = await res.json();
          if (res.status === 409 || resData.status === 'processing') {
              const doForce = confirm(
                `An adaptation job is already in progress for "${adaptProjectName}".\n\n` +
                `• Click OK to FORCE RESTART from the beginning.\n` +
                `• Click Cancel to attach to the live stream.`
              );
              if (doForce) {
                handleStartAdaptation(true);
                return;
              }
          } else if (!res.ok || resData.status === 'error') {
              throw new Error(resData.message || `HTTP error! status: ${res.status}`);
          }
          startAdaptationStream(adaptProjectName);
      } catch (err) {
          console.error('Adaptation error:', err);
          setIsAdapting(false);
          setAdaptProgress(null);
          alert(`Adaptation note: ${err.message}`);
      }
  };

  const startAdaptationStream = (projName) => {
      const eventSource = createAuthenticatedEventSource(`${BACKEND_URL}/api/screenplay/adapt/stream?project_name=${encodeURIComponent(projName)}`);
      let lastProgress = -1;

      eventSource.onmessage = async (event) => {
          try {
              const data = JSON.parse(event.data);
              if (data.status && data.status !== 'not_found') {
                  setAdaptProgress(data);
                  
                  if (data.status === 'processing' && data.progress !== lastProgress) {
                      lastProgress = data.progress;
                      lastProgress = data.progress;
                      // Progress never replaces the active draft or steals project focus.
                  }

                  if (data.status === 'complete' || data.status === 'error') {
                      eventSource.close();
                      setIsAdapting(false);
                      setTimeout(() => setAdaptProgress(null), 3000);
                      
                      if (data.status === 'error') {
                          alert(`AI Adaptation Failed: ${data.error || 'Unknown error'}`);
                      }
                      
                      await loadProjects();
                      if (currentProjectRef.current === projName) {
                        manualReviewRef.current.add(projName);
                        setSaveProblem({ project: projName, reviewOnly: true, message: 'Adaptation finished. Download any local edits, then use Reload saved version to view the generated manuscript.' });
                      }
                  }
              }
          } catch(err) {
              console.error(err);
          }
      };

      eventSource.onerror = (err) => {
          console.error("SSE Error:", err);
          eventSource.close();
          setIsAdapting(false);
      };
  };

  const insertSyntax = (syntax) => {
    const { blockId } = getActiveEditorSelection();
    let insertIdx = ast.length;
    if (blockId) {
      const idx = ast.findIndex(b => String(b.id) === String(blockId));
      if (idx !== -1) insertIdx = idx + 1;
    }
    
    let type = 'Action';
    let cleanText = syntax.replace(/^\n+|\n+$/g, '');
    if (syntax.startsWith('INT.') || syntax.startsWith('EXT.')) {
      type = 'Scene Heading';
      cleanText = syntax.trim() || 'INT. LOCATION - DAY';
    } else if (syntax.includes('CHARACTER')) {
      type = 'Character';
      cleanText = 'CHARACTER';
    } else if (syntax.includes('Dialogue')) {
      type = 'Dialogue';
      cleanText = 'Dialogue text here.';
    } else if (syntax.includes('parenthetical')) {
      type = 'Parenthetical';
      cleanText = '(whispering)';
    } else if (syntax.includes('CUT TO:')) {
      type = 'Transition';
      cleanText = 'CUT TO:';
    }

    const newBlock = {
      id: crypto.randomUUID(),
      type,
      text: cleanText
    };
    const newAst = [...ast];
    newAst.splice(insertIdx, 0, newBlock);
    handleAstChange(newAst);
  };

  const exportFDX = () => downloadScreenplayExport('fdx');

  const exportPDF = () => {
    const watermark = prompt('Enter watermark text (or leave blank for none):', '');
    if (watermark !== null) return downloadScreenplayExport('pdf', watermark);
  };

  // Helper to extract selected text or active focused block in ScreenplayEditor
  const getActiveEditorSelection = () => {
    const selection = window.getSelection();
    let text = '';
    let blockId = null;
    let isSubSelection = false;

    if (selection && selection.toString().trim()) {
      text = selection.toString().trim();
      isSubSelection = true;
      let node = selection.anchorNode;
      if (node && node.nodeType === 3) node = node.parentElement;
      const blockEl = node?.closest('[id^="sw-block-"]');
      if (blockEl) {
        blockId = blockEl.id.replace('sw-block-', '');
      }
    } else {
      const activeEl = document.activeElement?.closest('[id^="sw-block-"]');
      if (activeEl) {
        blockId = activeEl.id.replace('sw-block-', '');
        text = activeEl.innerText.trim();
      }
    }
    return { text, blockId, isSubSelection };
  };

  const applyEditorReplacement = (blockId, oldText, newText, isSubSelection) => {
    if (!blockId && ast.length > 0) {
      blockId = ast[0].id;
    }
    if (!blockId) return;

    const newAst = ast.map(b => {
      if (String(b.id) === String(blockId)) {
        if (isSubSelection && oldText && b.text.includes(oldText)) {
          return { ...b, text: b.text.replace(oldText, newText) };
        }
        return { ...b, text: newText };
      }
      return b;
    });
    handleAstChange(newAst);
  };

  const handleClipboard = async (action) => {
    const { text, blockId, isSubSelection } = getActiveEditorSelection();
    if (action === 'copy') {
      if (text) {
        await navigator.clipboard.writeText(text);
      }
    } else if (action === 'cut') {
      if (text && blockId) {
        await navigator.clipboard.writeText(text);
        applyEditorReplacement(blockId, text, '', isSubSelection);
      }
    } else if (action === 'paste') {
      try {
        const pasteText = await navigator.clipboard.readText();
        if (blockId) {
          applyEditorReplacement(blockId, text, (text ? text + ' ' : '') + pasteText, isSubSelection);
        }
      } catch (err) {
        console.error("Paste failed", err);
      }
    }
  };

  const handleFormat = (type) => {
    const { text, blockId, isSubSelection } = getActiveEditorSelection();
    if (!text || !blockId) {
      alert("Please highlight text or click inside a block to format.");
      return;
    }
    let formatted = text;
    if (type === 'bold') formatted = `**${text.replace(/\*\*/g, '')}**`;
    else if (type === 'italic') formatted = `*${text.replace(/\*/g, '')}*`;
    else if (type === 'underline') formatted = `_${text.replace(/_/g, '')}_`;
    else if (type === 'dual') formatted = text.endsWith(' ^') ? text.slice(0, -2) : `${text} ^`;

    applyEditorReplacement(blockId, text, formatted, isSubSelection);
  };

  const handleProofing = async (mode) => {
    const { text, blockId, isSubSelection } = getActiveEditorSelection();
    if (!text || !blockId) {
      alert("Please highlight text or click inside a block to run proofing.");
      return;
    }
    setIsProofing(true);
    const prompt = mode === 'spell' 
        ? `Fix spelling and grammar for the following screenplay excerpt. Return ONLY the corrected text without introductory markdown:\n\n${text}`
        : `Suggest a better, more evocative phrasing/synonym for the following screenplay excerpt. Return ONLY the new text without introductory markdown:\n\n${text}`;
        
    try {
        const res = await fetch(`${BACKEND_URL}/api/chat`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ message: prompt, model: "stehouwer_dolphin:latest" }),
        });
        const data = await res.json();
        
        if (data.status === 'success' || data.choices || data.message) {
            const responseText = (data.choices?.[0]?.message?.content || data.message?.content || data.response || data.message || '').trim();
            if (responseText) {
                applyEditorReplacement(blockId, text, responseText, isSubSelection);
            }
        }
    } catch (err) {
        console.error(err);
        alert("Proofing failed: " + err.message);
    } finally {
        setIsProofing(false);
    }
  };


  const getCharacterContextString = () => {
      if (!characters || characters.length === 0) return "";
      let ctx = "\n\n--- CHARACTER LORE & SPEAKING STYLES ---\n";
      characters.forEach(c => {
          ctx += `Name: ${c.name}\n`;
          if (c.bio) ctx += `Bio: ${c.bio}\n`;
          if (c.speaking_style) ctx += `Speaking Style: ${c.speaking_style}\n`;
          ctx += "\n";
      });
      return ctx;
  };

  const handleGhostwriter = async (index) => {
      // Get context from the recent AST blocks
      const contextBlocks = ast.slice(Math.max(0, index - 10), index + 1);
      const textToCursor = astToFountain(contextBlocks);
      
      setIsGhostwriting(true);
      const charContext = getCharacterContextString();
      const prompt = `You are an expert Hollywood screenwriter. Continue the following screenplay excerpt. 
Provide exactly ONE logical next beat (either a short action paragraph or a character's dialogue).
If you write dialogue for an existing character, you MUST adopt their specified Speaking Style and lore.
Format it in Fountain. 
Rules:
1. ABSOLUTELY NO PREAMBLE, introductions, or conversational text.
2. ABSOLUTELY NO MARKDOWN formatting (Do NOT use ** or * for bold/italics).

${charContext}

--- SCRIPT SO FAR ---
${textToCursor}`;

      try {
          const res = await fetch(`${BACKEND_URL}/api/chat`, {
              method: 'POST',
              headers: { 'Content-Type': 'application/json' },
              body: JSON.stringify({ message: prompt, model: "llama3:latest" }),
          });
          const data = await res.json();
          
          if (data.status === 'success') {
              let responseText = data.message?.content || data.response || '';
              responseText = responseText.trim();
              
              if (responseText) {
                  const newBlocks = fountainToAST(responseText);
                  const newAst = [...ast];
                  newAst.splice(index + 1, 0, ...newBlocks);
                  handleAstChange(newAst);
              }
          }
      } catch (err) {
          console.error('Ghostwriter failed', err);
      } finally {
          setIsGhostwriting(false);
      }
  };


  
  const [isExporting, setIsExporting] = useState(false);

  const handleExportUnreal = async (type) => {
      if (!screenplay || screenplay.trim() === '') {
          alert("No script to export!");
          return;
      }
      setIsExporting(true);
      try {
          const endpoint = type === 'csv' ? '/api/screenwriting/export/unreal-csv' : '/api/screenwriting/export/unreal-python';
          const res = await fetch(`${BACKEND_URL}${endpoint}`, {
              method: 'POST',
              headers: { 'Content-Type': 'application/json' },
              body: JSON.stringify({ content: screenplay })
          });
          const data = await res.json();
          if (data.status === 'success') {
              const blob = new Blob([data.data], { type: 'text/plain' });
              const url = URL.createObjectURL(blob);
              const a = document.createElement('a');
              a.href = url;
              a.download = type === 'csv' ? 'Unreal_DataTable.csv' : 'build_scene.py';
              document.body.appendChild(a);
              a.click();
              document.body.removeChild(a);
              URL.revokeObjectURL(url);
          } else {
              alert("Export failed: " + data.message);
          }
      } catch (err) {
          console.error(err);
          alert("Export failed.");
      } finally {
          setIsExporting(false);
      }
  };

  const handleGenerateCoverage = async () => {
      if (!screenplay || screenplay.trim() === '') {
          alert("No script to analyze!");
          return;
      }
      setIsGeneratingCoverage(true);
      try {
          const res = await fetch(`${BACKEND_URL}/api/screenwriting/coverage`, {
              method: 'POST',
              headers: { 'Content-Type': 'application/json' },
              body: JSON.stringify({ content: screenplay })
          });
          const data = await res.json();
          if (data.status === 'success') {
              setCoverageData(data.coverage);
              setShowCoverage(true);
          } else {
              alert("Failed to generate coverage: " + data.message);
          }
      } catch (err) {
          console.error("Coverage failed", err);
          alert("Failed to generate coverage.");
      } finally {
          setIsGeneratingCoverage(false);
      }
  };

  const handleAltTake = async () => {
    const { text, blockId, isSubSelection } = getActiveEditorSelection();
    if (!text || !blockId) {
      alert("Please highlight dialogue or click inside a block to generate an Alt-Take.");
      return;
    }

    setIsProofing(true);
    const charContext = getCharacterContextString();
    const prompt = `EDITORIAL DIRECTIVE:
You are an expert Hollywood dramatic screenwriter. Rewrite the following excerpt from a screenplay to provide a single, strong "Alt-Take" that is punchier, more dramatic, or emotionally compelling.
Crucially, you MUST maintain the character's exact voice, using any speaking styles provided below.
Return ONLY the Fountain syntax for the rewritten text. Do not include introductory text or explanations.
Rules:
1. ABSOLUTELY NO PREAMBLE or conversational text.
2. ABSOLUTELY NO MARKDOWN formatting (Do NOT use ** or * for bold/italics).

${charContext}

--- ORIGINAL TEXT ---
${text}`;

    try {
      const res = await fetch(`${BACKEND_URL}/api/chat`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ message: prompt, model: "stehouwer_dolphin:latest" }),
      });
      const data = await res.json();

      if (data.status === 'success' || data.choices || data.message) {
        let responseText = (data.choices?.[0]?.message?.content || data.message?.content || data.response || data.message || '').trim();
        responseText = responseText.replace(/^```(?:fountain|markdown)?\s*\n/i, '').replace(/\n```\s*$/, '').trim();
        if (responseText) {
          applyEditorReplacement(blockId, text, responseText, isSubSelection);
        }
      }
    } catch (err) {
      console.error('Alt-Take failed', err);
      alert('Alt-Take failed: ' + err.message);
    } finally {
      setIsProofing(false);
    }
  };

  const handleTitlePage = () => {
    const hasTitle = ast.some(b => b.type === 'Title' || (b.text && b.text.startsWith('Title:')));
    if (!hasTitle) {
      const titleBlock = {
        id: crypto.randomUUID(),
        type: 'Title',
        text: `Title: ${currentProject || 'UNTITLED'}\nAuthor: Brett Stehouwer\nDraft date: ${new Date().toLocaleDateString()}`
      };
      handleAstChange([titleBlock, ...ast]);
    }
    handleJumpToPage(1);
  };

  const handleSendToVideo = () => {
    const { text, blockId } = getActiveEditorSelection();
    let targetText = text;
    if (!targetText && blockId) {
      const block = ast.find(b => String(b.id) === String(blockId));
      if (block) targetText = block.text;
    }
    
    if (!targetText || targetText.trim() === "") {
      alert("Please highlight the scene/text you want to send to Video Studio!");
      return;
    }
    
    if (onSendToVideoStudio) {
      onSendToVideoStudio(targetText);
    }
  };

  const getPageBlocks = (targetPageNum) => {
    if (!ast || ast.length === 0) return { blocks: [], startIndex: 0, endIndex: 0 };
    const pages = [];
    let currentBuildingPage = [];
    let currentLines = 0;
    const MAX_LINES = 54;

    const estimateLines = (block) => {
      const len = (block.text || '').length;
      switch (block.type) {
        case 'Scene Heading': return 2 + Math.ceil(Math.max(1, len) / 58);
        case 'Action': return 1 + Math.ceil(Math.max(1, len) / 58);
        case 'Character': return 1 + Math.ceil(Math.max(1, len) / 38);
        case 'Dialogue': return Math.ceil(Math.max(1, len) / 38);
        case 'Parenthetical': return Math.ceil(Math.max(1, len) / 28);
        case 'Transition': return 2 + Math.ceil(Math.max(1, len) / 20);
        default: return 1;
      }
    };

    let pageStartIndex = 0;
    for (let i = 0; i < ast.length; i++) {
      const block = ast[i];
      const lines = estimateLines(block);
      if (currentLines + lines > MAX_LINES && currentBuildingPage.length > 0) {
        pages.push({ blocks: currentBuildingPage, startIndex: pageStartIndex, endIndex: i });
        currentBuildingPage = [block];
        currentLines = lines;
        pageStartIndex = i;
      } else {
        currentBuildingPage.push(block);
        currentLines += lines;
      }
    }
    if (currentBuildingPage.length > 0) {
      pages.push({ blocks: currentBuildingPage, startIndex: pageStartIndex, endIndex: ast.length });
    }

    const pageIndex = Math.max(0, Math.min(targetPageNum - 1, pages.length - 1));
    return pages[pageIndex] || { blocks: [], startIndex: 0, endIndex: 0 };
  };

  const handleProofPage = async (targetPageNum = viewerCurrentPage) => {
    const validPage = Math.max(1, Math.min(targetPageNum, totalScriptPages));
    setReviewPageNum(validPage);
    const { blocks, startIndex, endIndex } = getPageBlocks(validPage);
    if (!blocks || blocks.length === 0) {
      alert(`No content found on Page ${validPage}.`);
      return;
    }

    const origFountain = astToFountain(blocks);
    setReviewOriginalFountain(origFountain);
    setReviewSuggestedFountain('');
    setReviewPageIndices({ start: startIndex, end: endIndex });
    setShowPageReviewModal(true);
    setIsReviewingPage(true);
    setReviewStatusMessage(`Analyzing and format-proofing Page ${validPage}...`);

    const charContext = getCharacterContextString();
    const prompt = `EDITORIAL DIRECTIVE:
You are an expert Hollywood Screenplay Doctor and Format Proofing Engine.
Review, format-proof, and polish the following screenplay excerpt from Page ${validPage}.

STRICT ANTI-HALLUCINATION & FACTUAL FIDELITY RULES:
1. STRICT GROUNDING: You are an editorial proofreader and format doctor, NOT a fiction author. You are strictly forbidden from inventing new characters, altering character names, changing plot events, or introducing fictional dialogue that changes the meaning of the true story.
2. FORMAT STANDARDIZATION: Standardize all SCENE HEADINGS (INT., EXT., INT./EXT. in ALL CAPS).
3. CHARACTER CUES: Ensure CHARACTER names are ALL CAPS on their own line preceding dialogue.
4. PARENTHETICALS: Place PARENTHETICALS on their own line enclosed in parentheses (e.g. "(whispering)").
5. ACTION & DIALOGUE SEPARATION: Separate combined action and dialogue paragraphs into clean, distinct blocks.
6. TRANSITIONS: Standardize TRANSITIONS (e.g., "CUT TO:", "FADE OUT." in ALL CAPS).
7. GRAMMAR & POLISH: Correct spelling, typos, grammar, and spacing while strictly preserving character dialogue voice, emotional tone, and non-fiction baseline facts.
8. ZERO PREAMBLE: Return ONLY the clean Fountain screenplay text. Do NOT include markdown code blocks, conversational greetings, or notes.

${charContext}

--- ORIGINAL PAGE ${validPage} CONTENT ---
${origFountain}`;

    try {
      const res = await fetch(`${BACKEND_URL}/api/chat`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ 
          message: prompt, 
          model: "stehouwer_dolphin:latest",
          temperature: 0.1,
          top_p: 0.85
        }),
      });
      const data = await res.json();
      if (data.status === 'success' || data.choices || data.message) {
        let suggested = (data.choices?.[0]?.message?.content || data.message?.content || data.response || data.message || '').trim();
        suggested = suggested.replace(/^```(?:fountain|markdown)?\s*\n/i, '').replace(/\n```\s*$/, '').trim();
        setReviewSuggestedFountain(suggested);
        setReviewStatusMessage(`Page ${validPage} proofing ready for review.`);
      }
    } catch (err) {
      console.error('Page proofing error:', err);
      setReviewStatusMessage(`Error analyzing page: ${err.message}`);
    } finally {
      setIsReviewingPage(false);
    }
  };

  const handleApplyPageProof = (advanceNext = false) => {
    if (!reviewSuggestedFountain) return;
    const newBlocks = fountainToAST(reviewSuggestedFountain);
    const newAst = [...ast];
    newAst.splice(reviewPageIndices.start, reviewPageIndices.end - reviewPageIndices.start, ...newBlocks);
    handleAstChange(newAst);
    
    if (advanceNext && reviewPageNum < totalScriptPages) {
      handleProofPage(reviewPageNum + 1);
    } else {
      setShowPageReviewModal(false);
    }
  };

  const handleInsertScriptAssistantText = (textToInsert) => {
    if (!textToInsert) return;
    const newBlocks = fountainToAST(textToInsert);
    const { blockId } = getActiveEditorSelection();
    if (blockId) {
      const idx = ast.findIndex(b => String(b.id) === String(blockId));
      if (idx !== -1) {
        const newAst = [...ast];
        newAst.splice(idx + 1, 0, ...newBlocks);
        handleAstChange(newAst);
        return;
      }
    }
    handleAstChange([...ast, ...newBlocks]);
  };

  const handleEditorWillMount = (monaco) => {
    monaco.languages.register({ id: 'fountain' });

    monaco.languages.setMonarchTokensProvider('fountain', {
        tokenizer: {
            root: [
                // Scene Headings
                [/^(INT|EXT|EST|INT\/EXT|I\/E|int|ext|est)[\.\s].*$/, 'scene-heading'],
                [/^\..*$/, 'scene-heading'],
                
                // Transitions
                [/^>.*$/, 'transition'],
                [/^[A-Z\s]+ TO:$/, 'transition'],
                
                // Forced Character
                [/^@[A-Z0-9\s\.\(\)\-]+$/, 'character'],
                
                // Character Names (Heuristic: All caps line, but let's avoid matching every all-cap line perfectly, we can just do A-Z with optional parens)
                [/^[A-Z0-9\s\.\-]+(\s\(.*?\))?$/, 'character'],
                
                // Parentheticals
                [/^\s*\([^)]*\)\s*$/, 'parenthetical'],
                
                // Emphasis
                [/\*\*.*?\*\*/, 'bold'],
                [/\*.*?\*/, 'italic'],
                [/_.*?_/, 'underline'],
                
                // Notes/Boneyard
                [/\[\[.*?\]\]/, 'note'],
                [/\/\*/, 'comment', '@boneyard']
            ],
            boneyard: [
                [/[^\/*]+/, 'comment'],
                [/\*\//, 'comment', '@pop'],
                [/[\/*]/, 'comment']
            ]
        }
    });

    monaco.editor.defineTheme('fountain-theme', {
        base: 'vs-dark',
        inherit: true,
        rules: [
            { token: 'scene-heading', foreground: '58a6ff', fontStyle: 'bold' },
            { token: 'transition', foreground: 'd2a8ff', fontStyle: 'italic' },
            { token: 'character', foreground: 'facc15', fontStyle: 'bold' },
            { token: 'parenthetical', foreground: '9ca3af', fontStyle: 'italic' },
            { token: 'note', foreground: 'ff7b72' },
            { token: 'comment', foreground: '6e7681', fontStyle: 'italic' },
            { token: 'bold', fontStyle: 'bold' },
            { token: 'italic', fontStyle: 'italic' },
            { token: 'underline', fontStyle: 'underline' }
        ],
        colors: {
            'editor.background': '#0d1117'
        }
    });
  };

  const handlePublishToCMS = async () => {
      if (!parsed || !parsed.html) {
          alert("No parsed HTML available to publish.");
          return;
      }
      
      const filename = prompt("Enter the filename for the CMS (e.g. script.html):", `${currentProject || 'draft'}.html`);
      if (!filename) return;

      setIsLoading(true);
      try {
          const res = await fetch(`${BACKEND_URL}/api/cms/page/save`, {
              method: 'POST',
              headers: { 'Content-Type': 'application/json' },
              body: JSON.stringify({
                  filename: filename,
                  content: `<div class="script-content" style="max-width: 800px; margin: 0 auto; font-family: 'Courier Prime', Courier, monospace; background: white; padding: 40px; box-shadow: 0 4px 10px rgba(0,0,0,0.1);">\n${parsed.html}\n</div>`
              })
          });
          const data = await res.json();
          if (data.status === 'success') {
              alert(`Successfully published ${filename} to CMS!`);
          } else {
              alert(`Error publishing to CMS: ${data.message || 'Unknown error'}`);
          }
      } catch (err) {
          console.error("Publish failed", err);
          alert("Failed to publish to CMS");
      } finally {
          setIsLoading(false);
      }
  };
  const filteredBeats = (parsed?.beats || []).filter(b => 
      !sceneSearch.trim() || 
      (b.heading && b.heading.toLowerCase().includes(sceneSearch.toLowerCase())) ||
      (b.summary && b.summary.toLowerCase().includes(sceneSearch.toLowerCase()))
  );

  return (
    <div className="screenwriting-container" style={{ display: 'flex', flexDirection: 'column', height: '100%', maxHeight: '100%', width: '100%', minHeight: 0, overflow: 'hidden', flexWrap: 'nowrap' }}>
      {/* Coverage Modal */}
      {showCoverage && (
        <CoverageReportModal 
          coverageData={coverageData}
          onClose={() => setShowCoverage(false)}
        />
      )}

      {/* Analytics Overlay */}
      {showAnalyticsOverlay && (
        <AnalyticsOverlay 
          ast={ast} 
          onClose={() => setShowAnalyticsOverlay(false)} 
        />
      )}

      {/* Production Breakdown Modal */}
      {showProductionBreakdown && (
        <ProductionBreakdownModal 
          scriptText={screenplay || ''} 
          onClose={() => setShowProductionBreakdown(false)} 
        />
      )}

      {/* Stage Play Breakdown Modal */}
      {showStagePlayBreakdown && (
        <StagePlayBreakdownModal 
          scriptText={screenplay || ''} 
          onClose={() => setShowStagePlayBreakdown(false)} 
        />
      )}

      {/* Character Vault Modal */}
      {incomingWorkspaceDraft && (
        <div role="status" style={{ padding: '12px', background: '#172033', color: '#e2e8f0' }}>
          Workspace text changed outside this editor. Your current project remains open. Download the incoming copy to review or import it separately.
          {' '}<button type="button" onClick={() => downloadLocalDraft(incomingWorkspaceDraft)}>Download workspace draft</button>
        </div>
      )}
      {saveProblem && (
        <div role="alert" style={{ padding: '12px', background: '#422006', color: '#fef3c7', border: '1px solid #d97706' }}>
          <strong>Draft protection — {saveProblem.project || 'Screenwriting Studio'}</strong>
          <p>{saveProblem.message}</p>
          <button type="button" onClick={() => downloadLocalDraft()}>Download local draft</button>{' '}
          <button type="button" disabled={isLoading || isReordering} onClick={reloadSavedVersion}>Reload saved version</button>
          <p>To keep both versions, download your draft and import it under a new project name. Reload never merges drafts automatically.</p>
        </div>
      )}
      {recoveryDrafts.length > 0 && (
        <details style={{ padding: '8px', background: '#172033', color: '#e2e8f0' }}>
          <summary>Browser recovery copies ({recoveryDrafts.length})</summary>
          {recoveryDrafts.map(draft => <button type="button" key={draft.key} onClick={() => downloadLocalDraft(draft)}>
            Download {draft.project} — {new Date(draft.savedAt).toLocaleString()}
          </button>)}
        </details>
      )}
      {showCharacterVault && currentProject && loadedProjectRef.current === currentProject && (
        <CharacterVaultModal 
          key={`${currentProject}:${screenplayLoadSequenceRef.current}`}
          projectName={currentProject}
          backendUrl={BACKEND_URL}
          onClose={() => setShowCharacterVault(false)}
          onCharactersUpdate={(chars, project) => {
             if (project === currentProjectRef.current && project === loadedProjectRef.current) setCharacters(chars);
          }}
        />
      )}

      {showAdaptModal && (
        <div style={{ position: 'fixed', top: 0, left: 0, right: 0, bottom: 0, background: 'rgba(0,0,0,0.85)', zIndex: 1000, display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
          <div style={{ background: '#1f2937', border: '1px solid #374151', padding: '24px', borderRadius: '10px', width: '500px', maxWidth: '90vw', boxShadow: '0 8px 32px rgba(0,0,0,0.6)' }}>
            <h3 style={{ color: '#facc15', marginTop: 0, display: 'flex', alignItems: 'center', gap: '8px' }}>
              🎬 Adapt Manuscript to Hollywood Screenplay
            </h3>
            <p style={{ color: '#9ca3af', fontSize: '0.85rem', lineHeight: '1.4', marginBottom: '16px' }}>
              The AI-BS Matrix extracts character arcs, visual actions, and subtext from your manuscript (PDF, Word, EPUB, RTF, TXT, MD), chunking and adapting it into a professional screenplay.
            </p>
            
            <div style={{ marginBottom: '12px' }}>
              <label style={{ color: '#d1d5db', display: 'block', fontSize: '0.85rem', marginBottom: '4px', fontWeight: 'bold' }}>Source File:</label>
              <div style={{ color: '#38bdf8', fontSize: '0.85rem', padding: '6px 10px', background: '#111827', borderRadius: '4px', border: '1px solid #374151' }}>
                📄 {adaptFile?.name || 'No file selected'}
              </div>
            </div>

            <label style={{ color: '#d1d5db', display: 'block', fontSize: '0.85rem', marginBottom: '4px', fontWeight: 'bold' }}>Project Name:</label>
            <input type="text" value={adaptProjectName} onChange={e => setAdaptProjectName(e.target.value)} className="sw-panel-input" style={{ width: '100%', marginBottom: '16px', boxSizing: 'border-box' }} />
            
            <label style={{ color: '#d1d5db', display: 'block', fontSize: '0.85rem', marginBottom: '4px', fontWeight: 'bold' }}>Hollywood & Director Format Target:</label>
            <select value={adaptType} onChange={e => setAdaptType(e.target.value)} className="sw-panel-input" style={{ width: '100%', marginBottom: '10px', boxSizing: 'border-box', background: '#111827', color: '#fff' }}>
              <option value="Feature Film (Spec Script)">🎬 Feature Film (3-Act Hollywood Spec Script)</option>
              <option value="TV Pilot (1-Hour Drama)">📺 TV Pilot (1-Hour Network/Streaming Drama)</option>
              <option value="TV Pilot (30-Minute Comedy/Sitcom)">🎭 TV Pilot (30-Minute Comedy / Sitcom)</option>
              <option value="Limited / Mini-Series Episode">🎞️ Limited / Mini-Series Episodic Script</option>
              <option value="Director's Shooting Script (Previs & Camera Cues)">🎥 Director's Shooting Script (Camera & Lighting Cues)</option>
              <option value="Theatrical Stage Play">🏛️ Theatrical Stage Play (Act/Scene & Stage Blocking)</option>
              <option value="Audio Drama / Scripted Podcast">🎙️ Audio Drama / Scripted Podcast (SFX & Spatial Audio)</option>
              <option value="Short Film">⚡ Short Film (10-15 Minute Condensed Arc)</option>
            </select>

            {/* Dynamic Format Guide Helper */}
            <div style={{ background: '#111827', border: '1px solid #374151', padding: '10px', borderRadius: '6px', fontSize: '0.75rem', color: '#9ca3af', marginBottom: '20px', lineHeight: '1.4' }}>
              {adaptType.includes("1-Hour") && "📌 Structures prose into Teaser + 5/6 Acts with broadcast commercial cliffhangers and uppercase character introductions."}
              {adaptType.includes("30-Minute") && "📌 Fast-paced comedic rhythm with Cold Open, Act 1, Act 2, Tag, and punchy physical delivery parentheticals."}
              {adaptType.includes("Director") && "📌 Adds [WIDE SHOT], [CLOSE-UP], [TRACKING] camera framing, lighting notes, and physical actor blocking for 3D Unreal Engine previs."}
              {adaptType.includes("Stage Play") && "📌 Formats with ACT I / SCENE I headers, stage directions [STAGE LEFT], and physical actor blocking."}
              {adaptType.includes("Audio Drama") && "📌 Injects spatial sound design cues [SFX: ...], musical underscores [MUSIC: ...], and voiceover transitions."}
              {adaptType.includes("Short Film") && "📌 Strips exposition for rapid inciting incidents, tight visual conflict, and a sharp thematic punchline."}
              {adaptType.includes("Limited") && "📌 Serialized storytelling interleaving A-plot and B-plot character arcs with atmospheric scene depth."}
              {(!adaptType.includes("1-Hour") && !adaptType.includes("30-Minute") && !adaptType.includes("Director") && !adaptType.includes("Stage Play") && !adaptType.includes("Audio Drama") && !adaptType.includes("Short Film") && !adaptType.includes("Limited")) && "📌 Industry-standard 3-Act studio screenplay converting internal prose into visual external actions and subtext dialogue."}
            </div>
            
            <div style={{ display: 'flex', justifyContent: 'flex-end', gap: '8px' }}>
              <button onClick={() => setShowAdaptModal(false)} style={{ background: 'transparent', border: '1px solid #555', color: '#fff', padding: '6px 14px', cursor: 'pointer', borderRadius: '4px' }}>Cancel</button>
              <button onClick={handleStartAdaptation} style={{ background: '#facc15', color: '#000', border: 'none', padding: '6px 14px', fontWeight: 'bold', cursor: 'pointer', borderRadius: '4px' }}>🚀 Start Adaptation</button>
            </div>
          </div>
        </div>
      )}

      {/* 1. Consolidated Studio Header & Breadcrumbs */}
      {zenMode ? (
        <div style={{ position: 'fixed', top: '12px', right: '16px', zIndex: 9999, display: 'flex', gap: '8px', background: 'rgba(17, 24, 39, 0.9)', padding: '6px 14px', borderRadius: '20px', border: '1px solid #374151', backdropFilter: 'blur(8px)', boxShadow: '0 4px 16px rgba(0,0,0,0.5)' }}>
          <span style={{ color: '#facc15', fontSize: '0.85rem', display: 'flex', alignItems: 'center', gap: '6px' }}>🧘 Zen Focus Mode Active</span>
          <button onClick={() => setZenMode(false)} style={{ background: '#374151', color: '#fff', border: 'none', padding: '2px 10px', borderRadius: '12px', fontSize: '0.75rem', cursor: 'pointer' }}>
            Exit (Esc)
          </button>
        </div>
      ) : (
        <div className="sw-consolidated-header" style={{ position: 'sticky', top: 0, zIndex: 110, flexShrink: 0, background: '#111827', borderBottom: '1px solid #1f2937', padding: '6px 16px', display: 'flex', alignItems: 'center', justifyContent: 'space-between', flexWrap: 'wrap', gap: '8px' }}>
          
          {/* Breadcrumb Navigation */}
          <div style={{ display: 'flex', alignItems: 'center', gap: '8px', fontSize: '0.85rem' }}>
            <span style={{ color: '#9ca3af' }}>🎬 Creation Suite</span>
            <span style={{ color: '#4b5563' }}>/</span>
            <span style={{ color: '#38bdf8', fontWeight: 'bold' }}>✍️ Writing Studio</span>
            <span style={{ color: '#4b5563' }}>/</span>
            <select 
              value={currentProject} 
              onChange={(e) => handleSwitchProject(e.target.value)} 
              style={{ background: '#1f2937', color: '#facc15', border: '1px solid #374151', borderRadius: '4px', padding: '2px 8px', fontSize: '0.85rem', fontWeight: 'bold', cursor: 'pointer' }}
            >
              {projects.map(p => <option key={p} value={p}>{p}</option>)}
            </select>
          </div>

          {/* Ribbon Category Switcher Tabs */}
          <div style={{ display: 'flex', gap: '2px', background: '#0a0a0a', padding: '3px', borderRadius: '6px', border: '1px solid #1f2937' }}>
            {[
              { id: 'write', label: '✍️ Write' },
              { id: 'elements', label: '🧩 Elements' },
              { id: 'views', label: '👁️ Views & Split' },
              { id: 'unreal', label: '🎮 3D & Previs' },
              { id: 'production', label: '🚀 Production & CMS' },
            ].map(tab => (
              <button
                key={tab.id}
                onClick={() => setActiveRibbonTab(tab.id)}
                style={{
                  background: activeRibbonTab === tab.id ? '#1f2937' : 'transparent',
                  color: activeRibbonTab === tab.id ? '#facc15' : '#9ca3af',
                  border: 'none',
                  borderRadius: '4px',
                  padding: '4px 10px',
                  fontSize: '0.8rem',
                  fontWeight: activeRibbonTab === tab.id ? 'bold' : 'normal',
                  cursor: 'pointer',
                  transition: 'all 0.2s ease'
                }}
              >
                {tab.label}
              </button>
            ))}
          </div>

          {/* Quick Action Group */}
          <div style={{ display: 'flex', gap: '6px', alignItems: 'center' }}>
            <button 
              onClick={() => setShowNewProjectModal(true)} 
              style={{ background: '#238636', color: '#fff', border: '1px solid #2ea043', borderRadius: '4px', padding: '4px 10px', fontSize: '0.8rem', fontWeight: 'bold', cursor: 'pointer', display: 'flex', alignItems: 'center', gap: '4px' }}
              title="Create a new Screenplay Project"
            >
              + New Project
            </button>
            <button 
              onClick={() => setZenMode(true)} 
              style={{ background: '#1f2937', color: '#a78bfa', border: '1px solid #374151', borderRadius: '4px', padding: '4px 10px', fontSize: '0.8rem', cursor: 'pointer', display: 'flex', alignItems: 'center', gap: '4px' }}
              title="Enter Distraction-Free Fullscreen Mode (Esc to exit)"
            >
              🧘 Zen Mode
            </button>
            <button 
              onClick={() => setShowNovelizerModal(true)} 
              style={{ background: 'linear-gradient(90deg, #7c3aed 0%, #6d28d9 100%)', color: '#fff', border: '1px solid #a78bfa', borderRadius: '4px', padding: '4px 10px', fontSize: '0.8rem', fontWeight: 'bold', cursor: 'pointer', display: 'flex', alignItems: 'center', gap: '4px', boxShadow: '0 2px 8px rgba(124, 58, 237, 0.4)' }}
              title="Convert this Screenplay into a full-length Book / Novel / Memoir"
            >
              📖 Novelize to Book
            </button>
            <button 
              onClick={() => setShowTableReadModal(true)} 
              style={{ background: 'linear-gradient(90deg, #d97706 0%, #b45309 100%)', color: '#fff', border: '1px solid #f59e0b', borderRadius: '4px', padding: '4px 10px', fontSize: '0.8rem', fontWeight: 'bold', cursor: 'pointer', display: 'flex', alignItems: 'center', gap: '4px', boxShadow: '0 2px 8px rgba(217, 119, 6, 0.4)' }}
              title="Launch Multi-Voice AI Audio Table Read Studio"
            >
              🎙️ Table Read Studio
            </button>
            <button 
              onClick={() => setShowScriptTelemetryModal(true)} 
              style={{ background: 'linear-gradient(90deg, #0284c7 0%, #0369a1 100%)', color: '#fff', border: '1px solid #38bdf8', borderRadius: '4px', padding: '4px 10px', fontSize: '0.8rem', fontWeight: 'bold', cursor: 'pointer', display: 'flex', alignItems: 'center', gap: '4px', boxShadow: '0 2px 8px rgba(2, 132, 199, 0.4)' }}
              title="Watch pages being written, AI thoughts & execution telemetry live"
            >
              ⚡ Thoughts & Pages Telemetry
            </button>
            <button onClick={handleImportClick} className="sw-ribbon-btn" style={{ background: 'transparent', border: '1px solid #34d399', color: '#34d399', padding: '4px 8px', fontSize: '0.8rem' }}>
              📥 Import
            </button>
            <button onClick={() => setShowFindReplace(!showFindReplace)} className="sw-ribbon-btn" style={{ background: showFindReplace ? 'rgba(168, 85, 247, 0.3)' : 'transparent', border: '1px solid #a855f7', color: '#a855f7', padding: '4px 8px', fontSize: '0.8rem' }}>
              🔍 Find & Replace
            </button>
            <button onClick={handleExportFDX} className="sw-ribbon-btn" style={{ background: 'transparent', border: '1px solid #38bdf8', color: '#38bdf8', padding: '4px 8px', fontSize: '0.8rem' }}>
              📄 Export FDX
            </button>
            <button onClick={handleExportPDF} className="sw-ribbon-btn" style={{ background: 'transparent', border: '1px solid #e11d48', color: '#e11d48', padding: '4px 8px', fontSize: '0.8rem' }}>
              📄 Export PDF
            </button>
            <button 
              onClick={() => setShowHelpGuideModal(true)} 
              className="sw-ribbon-btn" 
              style={{ background: 'rgba(56, 189, 248, 0.15)', border: '1px solid #0284c7', color: '#38bdf8', padding: '4px 10px', fontSize: '0.8rem', fontWeight: 'bold', display: 'flex', alignItems: 'center', gap: '4px', cursor: 'pointer' }}
              title="Complete Hollywood Screenwriting Studio Step-by-Step Guide & Tool Manual (F1)"
            >
              📖 Help Guide
            </button>
            <div style={{ display: 'flex', alignItems: 'center', gap: '6px', background: 'rgba(15, 23, 42, 0.9)', border: '1px solid #334155', padding: '3px 8px', borderRadius: '6px', fontSize: '0.75rem' }} title="Continuous background autosave for admins">
              <span style={{ fontSize: '0.65rem' }}>
                {autoSaveStatus === 'saving' || autoSaveStatus === 'unsaved' ? '🟡' : autoSaveStatus === 'error' ? '🔴' : '🟢'}
              </span>
              <span style={{ color: autoSaveStatus === 'error' ? '#f87171' : (autoSaveStatus === 'saving' ? '#fbbf24' : '#38bdf8'), fontWeight: 600 }}>
                {autoSaveStatus === 'saving' ? 'Saving...' : autoSaveStatus === 'unsaved' ? 'Unsaved changes' : autoSaveStatus === 'error' ? 'Save paused' : `Saved ${lastSavedTime || ''}`}
              </span>
            </div>
            <button onClick={handleSaveScreenplay} disabled={isLoading} className="sw-save-btn" style={{ padding: '4px 12px', fontSize: '0.8rem' }}>
              {isLoading ? 'Saving...' : '💾 Save'}
            </button>
          </div>
        </div>
      )}

      {/* Find & Replace Bar */}
      {showFindReplace && (
        <div style={{ background: '#1e293b', borderBottom: '1px solid #334155', padding: '8px 16px', display: 'flex', alignItems: 'center', gap: '12px' }}>
          <input 
            type="text" 
            placeholder="Find text..." 
            value={findText} 
            onChange={(e) => setFindText(e.target.value)} 
            style={{ background: '#0f172a', border: '1px solid #475569', color: '#fff', padding: '4px 8px', borderRadius: '4px', fontSize: '0.85rem', width: '200px' }}
          />
          <input 
            type="text" 
            placeholder="Replace with..." 
            value={replaceText} 
            onChange={(e) => setReplaceText(e.target.value)} 
            style={{ background: '#0f172a', border: '1px solid #475569', color: '#fff', padding: '4px 8px', borderRadius: '4px', fontSize: '0.85rem', width: '200px' }}
          />
          <button 
            onClick={() => {
              if (!findText) return;
              let occurrences = 0;
              const newAst = ast.map(b => {
                if (b.text && b.text.includes(findText)) {
                  occurrences += (b.text.split(findText).length - 1);
                  return { ...b, text: b.text.split(findText).join(replaceText) };
                }
                return b;
              });
              if (occurrences > 0) {
                handleAstChange(newAst);
                alert(`Replaced ${occurrences} occurrences of "${findText}".`);
              } else {
                alert(`No occurrences of "${findText}" found.`);
              }
            }}
            style={{ background: '#3b82f6', color: '#fff', border: 'none', padding: '4px 12px', borderRadius: '4px', fontSize: '0.85rem', cursor: 'pointer', fontWeight: 'bold' }}
          >
            Replace All
          </button>
          <button onClick={() => setShowFindReplace(false)} style={{ background: 'transparent', color: '#94a3b8', border: 'none', cursor: 'pointer', fontSize: '1rem' }}>
            &times;
          </button>
        </div>
      )}


      {/* 2. Dynamic Single-Deck Ribbon (Hidden in Zen Mode) */}
      {!zenMode && (
        <div className="sw-ribbon" style={{ position: 'sticky', top: 0, zIndex: 105, flexShrink: 0, padding: '6px 16px', minHeight: '42px', display: 'flex', alignItems: 'center', background: '#161e2e', borderBottom: '1px solid #1f2937', gap: '16px', overflowX: 'auto' }}>
          
          {/* TAB 1: WRITE */}
          {activeRibbonTab === 'write' && (
            <div style={{ display: 'flex', gap: '16px', alignItems: 'center' }}>
              <div style={{ display: 'flex', gap: '4px', alignItems: 'center', borderRight: '1px solid #374151', paddingRight: '12px' }}>
                <button className="sw-ribbon-btn" onClick={handleUndo} disabled={historyIndex <= 0} title="Undo (Ctrl+Z)" style={{ opacity: historyIndex <= 0 ? 0.4 : 1, fontWeight: 'bold' }}>↶ Undo</button>
                <button className="sw-ribbon-btn" onClick={handleRedo} disabled={historyIndex >= history.length - 1} title="Redo (Ctrl+Y)" style={{ opacity: historyIndex >= history.length - 1 ? 0.4 : 1, fontWeight: 'bold' }}>↷ Redo</button>
              </div>

              <div style={{ display: 'flex', gap: '4px', alignItems: 'center', borderRight: '1px solid #374151', paddingRight: '12px' }}>
                <button className="sw-ribbon-btn" onClick={() => handleClipboard('cut')}>✂️ Cut</button>
                <button className="sw-ribbon-btn" onClick={() => handleClipboard('copy')}>📋 Copy</button>
                <button className="sw-ribbon-btn" onClick={() => handleClipboard('paste')}>📋 Paste</button>
              </div>

              <div style={{ display: 'flex', gap: '4px', alignItems: 'center', borderRight: '1px solid #374151', paddingRight: '12px' }}>
                <button className="sw-ribbon-btn" style={{ fontWeight: 'bold' }} onClick={() => handleFormat('bold')}>B</button>
                <button className="sw-ribbon-btn" style={{ fontStyle: 'italic' }} onClick={() => handleFormat('italic')}>I</button>
                <button className="sw-ribbon-btn" style={{ textDecoration: 'underline' }} onClick={() => handleFormat('underline')}>U</button>
              </div>

              <div style={{ display: 'flex', gap: '4px', alignItems: 'center' }}>
                <button className="sw-ribbon-btn" onClick={() => handleProofing('spell')} disabled={isProofing}>{isProofing ? '⏳' : '📝'} Spell</button>
                <button className="sw-ribbon-btn" onClick={() => handleProofing('thesaurus')} disabled={isProofing}>{isProofing ? '⏳' : '📖'} Thesaurus</button>
                <button className="sw-ribbon-btn" onClick={handleAltTake} disabled={isProofing} style={{ color: '#facc15' }}>{isProofing ? '⏳' : '✨'} Alt-Take</button>
                <button className="sw-ribbon-btn" onClick={() => setShowHelpGuideModal(true)} style={{ color: '#38bdf8' }} title="Screenwriting Studio Master Help Guide & Tool Manual (F1)">❓ Help Guide</button>
              </div>
            </div>
          )}

          {/* TAB 2: ELEMENTS & INSERT */}
          {activeRibbonTab === 'elements' && (
            <div style={{ display: 'flex', gap: '8px', alignItems: 'center' }}>
              <button onClick={() => insertSyntax('INT. ')} className="sw-ribbon-btn">🎬 Heading</button>
              <button onClick={() => insertSyntax('\n\nAction text...\n')} className="sw-ribbon-btn">📝 Action</button>
              <button onClick={() => insertSyntax('\n\nCHARACTER\n')} className="sw-ribbon-btn">👤 Character</button>
              <button onClick={() => insertSyntax('Dialogue text\n')} className="sw-ribbon-btn">💬 Dialogue</button>
              <button onClick={() => insertSyntax('(parenthetical)\n')} className="sw-ribbon-btn">🗣️ Parenthetical</button>
              <button onClick={() => handleFormat('dual')} className="sw-ribbon-btn" style={{ color: '#38bdf8' }}>👥 Dual</button>
              <button onClick={() => insertSyntax('\n\nCUT TO:\n')} className="sw-ribbon-btn">⚡ Transition</button>
              <button onClick={() => { insertSyntax('\n[  ]\n'); editorRef.current?.focus(); }} className="sw-toolbar-btn">🔖 Beat</button>
              <button onClick={() => insertSyntax('[[Note: Your note here]]\n')} className="sw-ribbon-btn">📌 ScriptNote</button>
              <button onClick={() => insertSyntax('[[Image: path/to/img.png]]\n')} className="sw-ribbon-btn">🖼️ Image</button>
            </div>
          )}

          {/* TAB 3: VIEWS & SPLIT */}
          {activeRibbonTab === 'views' && (
            <div style={{ display: 'flex', gap: '16px', alignItems: 'center' }}>
              <div style={{ display: 'flex', gap: '4px', borderRight: '1px solid #374151', paddingRight: '12px' }}>
                <button className={`sw-ribbon-btn ${activeView === 'editor' ? 'sw-ribbon-btn-active' : ''}`} onClick={() => setActiveView('editor')}>📝 Editor</button>
                <button className={`sw-ribbon-btn ${activeView === 'preview' ? 'sw-ribbon-btn-active' : ''}`} onClick={() => setActiveView('preview')}>👁️ Scene View</button>
                <button className={`sw-ribbon-btn ${activeView === 'beats' ? 'sw-ribbon-btn-active' : ''}`} onClick={() => setActiveView('beats')}>🗂️ Beat Board</button>
              </div>

              <div style={{ display: 'flex', gap: '4px', alignItems: 'center', borderRight: '1px solid #374151', paddingRight: '12px' }}>
                <span style={{ fontSize: '0.8rem', color: '#9ca3af' }}>Panels:</span>
                <button className={`sw-ribbon-btn ${leftPanelVisible ? 'sw-ribbon-btn-active' : ''}`} onClick={() => setLeftPanelVisible(!leftPanelVisible)}>{leftPanelVisible ? '◀ Outline' : '▶ Outline'}</button>
                <button className={`sw-ribbon-btn ${navigatorVisible ? 'sw-ribbon-btn-active' : ''}`} onClick={() => setNavigatorVisible(!navigatorVisible)}>🧭 Navigator</button>
              </div>

              <div style={{ display: 'flex', gap: '4px', alignItems: 'center' }}>
                <span style={{ fontSize: '0.8rem', color: '#9ca3af' }}>Split:</span>
                <button className={`sw-ribbon-btn ${splitMode === 'none' ? 'sw-ribbon-btn-active' : ''}`} onClick={() => setSplitMode('none')}>None</button>
                <button className={`sw-ribbon-btn ${splitMode === 'vertical' ? 'sw-ribbon-btn-active' : ''}`} onClick={() => setSplitMode('vertical')}>Split V</button>
                <button className={`sw-ribbon-btn ${splitMode === 'horizontal' ? 'sw-ribbon-btn-active' : ''}`} onClick={() => setSplitMode('horizontal')}>Split H</button>
              </div>
            </div>
          )}

          {/* TAB 4: 3D & PREVIS */}
          {activeRibbonTab === 'unreal' && (
            <div style={{ display: 'flex', gap: '8px', alignItems: 'center' }}>
              <button onClick={handleSendToVideo} className="sw-toolbar-btn" style={{ background: '#2ea043', color: '#fff' }}>
                🎥 Send to Video Studio
              </button>
              <button className="sw-ribbon-btn" onClick={() => handleExportUnreal('csv')} disabled={isExporting} style={{ background: '#2563eb', color: '#fff' }}>
                🎮 Export CSV (Data Table)
              </button>
              <button className="sw-ribbon-btn" onClick={() => handleExportUnreal('python')} disabled={isExporting} style={{ background: '#047857', color: '#fff' }}>
                🎮 Export Python (Sequencer)
              </button>
            </div>
          )}

          {/* TAB 5: PRODUCTION & CMS */}
          {activeRibbonTab === 'production' && (
            <div style={{ display: 'flex', gap: '8px', alignItems: 'center' }}>
              <button className="sw-ribbon-btn" onClick={() => setShowCharacterVault(true)} style={{ color: '#facc15' }}>
                🎭 Character Vault
              </button>
              <button className="sw-ribbon-btn" onClick={handleGenerateCoverage} disabled={isGeneratingCoverage}>
                {isGeneratingCoverage ? '⏳ Analyzing...' : '📊 Script Coverage'}
              </button>
              <button className="sw-ribbon-btn" onClick={() => setShowAnalyticsOverlay(!showAnalyticsOverlay)} style={{ color: showAnalyticsOverlay ? '#facc15' : 'inherit' }}>
                📈 Analytics
              </button>
              <button className="sw-ribbon-btn" onClick={() => setShowProductionBreakdown(true)}>
                🎬 Film Budget
              </button>
              <button className="sw-ribbon-btn" onClick={() => setShowStagePlayBreakdown(true)}>
                🎭 Theatrical Budget
              </button>
              <div style={{ display: 'flex', alignItems: 'center', gap: '4px', borderLeft: '1px solid #374151', paddingLeft: '8px', marginLeft: '4px' }}>
                <button 
                  className="sw-ribbon-btn" 
                  onClick={() => setIsRevisionMode(!isRevisionMode)} 
                  style={{ background: isRevisionMode ? '#374151' : 'transparent', color: isRevisionMode ? '#f87171' : 'inherit', fontWeight: isRevisionMode ? 'bold' : 'normal' }}
                >
                  {isRevisionMode ? '🔴 Revision ON' : '⚪ Revision OFF'}
                </button>
                {isRevisionMode && (
                  <select 
                    value={revisionColor} 
                    onChange={e => setRevisionColor(e.target.value)} 
                    className="sw-panel-input" 
                    style={{ background: '#111827', color: '#fff', border: '1px solid #374151', padding: '2px 4px', fontSize: '0.8rem', borderRadius: '4px' }}
                  >
                    <option value="blue">Blue</option>
                    <option value="pink">Pink</option>
                    <option value="yellow">Yellow</option>
                    <option value="green">Green</option>
                  </select>
                )}
              </div>
              <button className="sw-ribbon-btn" onClick={handleTitlePage} style={{ borderLeft: '1px solid #374151', paddingLeft: '12px', marginLeft: '4px' }}>
                📄 Title Page
              </button>
              <button className="sw-ribbon-btn" onClick={exportFDX} style={{ color: '#38bdf8' }}>
                ⬇️ Export .fdx
              </button>
              <button className="sw-ribbon-btn" onClick={exportPDF} style={{ color: '#f87171' }}>
                📄 Export .pdf
              </button>
              <button className="sw-ribbon-btn" onClick={handlePublishToCMS} style={{ background: '#238636', color: 'white', border: 'none' }}>
                🚀 Publish to CMS
              </button>
            </div>
          )}
        </div>
      )}

      {/* 2.5 Live AI Adaptation Status & Progress Bar */}
      <div style={{ flexShrink: 0 }}>
        <AdaptationStatusBar 
          backendUrl={BACKEND_URL}
          onSwitchToProject={handleSwitchProject}
          onRefreshScreenplay={async (proj) => {
            if (proj === currentProject) {
              await loadScreenplay(proj);
            }
          }}
        />
      </div>

      {/* 2.6 Dedicated Project Audio Drama Adaptation Player */}
      <ProjectAudioPlayer 
        projectName={currentProject}
        backendUrl={BACKEND_URL}
        isOpen={showAudioPlayer}
        onClose={() => setShowAudioPlayer(false)}
      />

      {/* 2.8 PERMANENT HARDCODED PAGE NAVIGATION & VIEW DECK (ALWAYS VISIBLE AT TOP) */}
      <div className="sw-permanent-page-bar" style={{
        position: 'sticky',
        top: 0,
        zIndex: 100,
        flexShrink: 0,
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'space-between',
        padding: '5px 16px',
        background: '#0e1726',
        borderBottom: '1px solid #1f2937',
        color: '#e5e7eb',
        fontSize: '0.85rem',
        flexWrap: 'wrap',
        gap: '10px'
      }}>
        {/* Left: View Mode Quick Toggles */}
        <div style={{ display: 'flex', gap: '3px', background: '#0a0f1d', padding: '2px', borderRadius: '6px', border: '1px solid #1e293b' }}>
          <button 
            onClick={() => { setActiveView('editor'); setSplitMode('none'); }} 
            style={{
              background: activeView === 'editor' && splitMode === 'none' ? '#2563eb' : 'transparent',
              color: activeView === 'editor' && splitMode === 'none' ? '#fff' : '#94a3b8',
              border: 'none',
              padding: '3px 10px',
              borderRadius: '4px',
              fontSize: '0.8rem',
              fontWeight: activeView === 'editor' && splitMode === 'none' ? 'bold' : 'normal',
              cursor: 'pointer',
              display: 'flex',
              alignItems: 'center',
              gap: '4px'
            }}
            title="Interactive AST Screenplay Editor"
          >
            📝 Editor
          </button>
          <button 
            onClick={() => { setActiveView('preview'); setSplitMode('none'); }} 
            style={{
              background: activeView === 'preview' && splitMode === 'none' ? '#2563eb' : 'transparent',
              color: activeView === 'preview' && splitMode === 'none' ? '#fff' : '#94a3b8',
              border: 'none',
              padding: '3px 10px',
              borderRadius: '4px',
              fontSize: '0.8rem',
              fontWeight: activeView === 'preview' && splitMode === 'none' ? 'bold' : 'normal',
              cursor: 'pointer',
              display: 'flex',
              alignItems: 'center',
              gap: '4px'
            }}
            title="Paginated 8.5 x 11 Finished Script Page View"
          >
            📄 Page View
          </button>
          <button 
            onClick={() => { setSplitMode(splitMode === 'vertical' ? 'none' : 'vertical'); }} 
            style={{
              background: splitMode === 'vertical' ? '#3b82f6' : 'transparent',
              color: splitMode === 'vertical' ? '#fff' : '#94a3b8',
              border: 'none',
              padding: '3px 10px',
              borderRadius: '4px',
              fontSize: '0.8rem',
              fontWeight: splitMode === 'vertical' ? 'bold' : 'normal',
              cursor: 'pointer',
              display: 'flex',
              alignItems: 'center',
              gap: '4px'
            }}
            title="Toggle Split View (Side-by-Side Editor & Pages)"
          >
            🪟 Split
          </button>
          <button 
            onClick={() => { setActiveView('beats'); setSplitMode('none'); }} 
            style={{
              background: activeView === 'beats' && splitMode === 'none' ? '#2563eb' : 'transparent',
              color: activeView === 'beats' && splitMode === 'none' ? '#fff' : '#94a3b8',
              border: 'none',
              padding: '3px 10px',
              borderRadius: '4px',
              fontSize: '0.8rem',
              fontWeight: activeView === 'beats' && splitMode === 'none' ? 'bold' : 'normal',
              cursor: 'pointer',
              display: 'flex',
              alignItems: 'center',
              gap: '4px'
            }}
            title="Visual Story Beat Board"
          >
            🗂️ Beat Board
          </button>
        </div>

        {/* Center: HARDCODED PERMANENT PAGE NAVIGATION TOOLS */}
        <div style={{ display: 'flex', alignItems: 'center', gap: '6px', background: '#0a0f1d', padding: '3px 10px', borderRadius: '6px', border: '1px solid #1e293b' }}>
          <button 
            onClick={() => handleJumpToPage(1)} 
            disabled={viewerCurrentPage <= 1}
            style={{ background: '#1e293b', color: '#fff', border: '1px solid #334155', padding: '3px 8px', borderRadius: '4px', cursor: viewerCurrentPage <= 1 ? 'not-allowed' : 'pointer', fontSize: '0.8rem' }}
            title="First Page (Page 1)"
          >
            ⏮ First
          </button>
          <button 
            onClick={() => handleJumpToPage(viewerCurrentPage - 1)} 
            disabled={viewerCurrentPage <= 1}
            style={{ background: '#1e293b', color: '#fff', border: '1px solid #334155', padding: '3px 8px', borderRadius: '4px', cursor: viewerCurrentPage <= 1 ? 'not-allowed' : 'pointer', fontSize: '0.8rem' }}
            title="Previous Page"
          >
            ◀ Prev
          </button>
          
          <span style={{ color: '#94a3b8', fontSize: '0.8rem', fontWeight: '500' }}>Page</span>
          <input 
            type="number"
            min="1"
            max={totalScriptPages}
            value={viewerCurrentPage}
            onChange={(e) => {
              const val = parseInt(e.target.value);
              if (!isNaN(val)) {
                handleJumpToPage(val);
              }
            }}
            style={{ width: '44px', padding: '2px 4px', textAlign: 'center', background: '#020617', color: '#facc15', border: '1px solid #334155', borderRadius: '4px', fontWeight: 'bold', fontSize: '0.85rem' }}
          />
          <span style={{ color: '#94a3b8', fontSize: '0.8rem', fontWeight: '500' }}>of {totalScriptPages}</span>

          <button 
            onClick={() => handleJumpToPage(viewerCurrentPage + 1)} 
            disabled={viewerCurrentPage >= totalScriptPages}
            style={{ background: '#1e293b', color: '#fff', border: '1px solid #334155', padding: '3px 8px', borderRadius: '4px', cursor: viewerCurrentPage >= totalScriptPages ? 'not-allowed' : 'pointer', fontSize: '0.8rem' }}
            title="Next Page"
          >
            Next ▶
          </button>
          <button 
            onClick={() => handleJumpToPage(totalScriptPages)} 
            disabled={viewerCurrentPage >= totalScriptPages}
            style={{ background: '#1e293b', color: '#fff', border: '1px solid #334155', padding: '3px 8px', borderRadius: '4px', cursor: viewerCurrentPage >= totalScriptPages ? 'not-allowed' : 'pointer', fontSize: '0.8rem' }}
            title="Last Page"
          >
            Last ⏭
          </button>

          {/* Quick Page Doctor / Review Trigger */}
          <button 
            onClick={() => handleProofPage(viewerCurrentPage)} 
            disabled={isReviewingPage}
            style={{
              background: 'linear-gradient(135deg, #8b5cf6 0%, #6366f1 100%)',
              color: '#fff',
              border: '1px solid #a855f7',
              padding: '3px 10px',
              borderRadius: '4px',
              cursor: isReviewingPage ? 'wait' : 'pointer',
              fontSize: '0.8rem',
              fontWeight: 'bold',
              display: 'flex',
              alignItems: 'center',
              gap: '4px',
              boxShadow: '0 2px 8px rgba(139, 92, 246, 0.4)',
              marginLeft: '6px'
            }}
            title="Review and format-proof the current page with AI Script Doctor (or type !proof in editor)"
          >
            {isReviewingPage ? '⏳ Proofing...' : `🔍 Review Pg ${viewerCurrentPage}`}
          </button>
        </div>

        {/* Right: Scene Quick Jump Dropdown & Search */}
        <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: '4px' }}>
            <span style={{ color: '#94a3b8', fontSize: '0.8rem' }}>🎬 Scene:</span>
            <select 
              onChange={(e) => {
                const selectedIndex = parseInt(e.target.value);
                if (!isNaN(selectedIndex) && parsed?.beats?.[selectedIndex]) {
                  const beat = parsed.beats[selectedIndex];
                  if (viewerRef.current) {
                    viewerRef.current.scrollToScene(beat);
                  } else {
                    setActiveView('preview');
                    setTimeout(() => viewerRef.current?.scrollToScene(beat), 100);
                  }
                }
              }}
              defaultValue=""
              style={{ background: '#0a0f1d', color: '#38bdf8', border: '1px solid #1e293b', padding: '3px 8px', borderRadius: '4px', maxWidth: '180px', cursor: 'pointer', fontSize: '0.8rem' }}
            >
              <option value="" disabled>Select Scene...</option>
              {(parsed?.beats || []).map((b, idx) => (
                <option key={idx} value={idx}>
                  {idx + 1}. {b.heading.substring(0, 24)}... (p.{Math.floor(b.page)})
                </option>
              ))}
            </select>
          </div>

          {/* Search Script with Match Counter & Enter / Shift+Enter Navigation */}
          <div style={{ display: 'flex', alignItems: 'center', background: '#0a0f1d', borderRadius: '4px', border: '1px solid #1e293b', padding: '1px 6px', gap: '4px' }}>
            <span style={{ fontSize: '0.75rem', color: '#64748b' }}>🔍</span>
            <input 
              type="text" 
              value={viewerSearch} 
              onChange={(e) => setViewerSearch(e.target.value)} 
              onKeyDown={(e) => {
                if (e.key === 'Enter') {
                  e.preventDefault();
                  if (e.shiftKey) {
                    viewerRef.current?.handlePrevSearch();
                  } else {
                    viewerRef.current?.handleNextSearch();
                  }
                }
              }}
              placeholder="Search (Enter/Shift+Enter)..." 
              style={{ background: 'transparent', border: 'none', color: '#fff', fontSize: '0.8rem', width: '140px', outline: 'none' }}
            />
            {viewerRef.current?.matchedCount > 0 && (
              <span style={{ fontSize: '0.7rem', color: '#38bdf8', fontWeight: 'bold' }}>
                {viewerRef.current.activeMatchIndex || 1}/{viewerRef.current.matchedCount}
              </span>
            )}
            {viewerSearch && (
              <button onClick={() => setViewerSearch('')} style={{ background: 'none', border: 'none', color: '#94a3b8', cursor: 'pointer', padding: '0 2px' }}>&times;</button>
            )}
          </div>

          {/* Zoom Stepper */}
          <div style={{ display: 'flex', alignItems: 'center', gap: '2px', background: '#0a0f1d', padding: '2px 4px', borderRadius: '4px', border: '1px solid #1e293b' }}>
            <button 
              onClick={() => setZoomLevel(Math.max(50, zoomLevel - 10))} 
              style={{ background: 'transparent', color: '#94a3b8', border: 'none', padding: '1px 5px', cursor: 'pointer', fontSize: '0.8rem' }}
              title="Zoom Out"
            >-</button>
            <span style={{ fontSize: '0.75rem', color: '#e2e8f0', minWidth: '34px', textAlign: 'center' }}>{zoomLevel}%</span>
            <button 
              onClick={() => setZoomLevel(Math.min(175, zoomLevel + 10))} 
              style={{ background: 'transparent', color: '#94a3b8', border: 'none', padding: '1px 5px', cursor: 'pointer', fontSize: '0.8rem' }}
              title="Zoom In"
            >+</button>
          </div>

          {/* Audio Drama Toggle */}
          <button
            onClick={() => setShowAudioPlayer(!showAudioPlayer)}
            style={{
              background: showAudioPlayer ? '#1e3a8a' : '#1e293b',
              color: '#93c5fa',
              border: '1px solid #3b82f6',
              borderRadius: '4px',
              padding: '3px 10px',
              fontSize: '0.8rem',
              fontWeight: 'bold',
              cursor: 'pointer',
              display: 'flex',
              alignItems: 'center',
              gap: '4px'
            }}
            title="Toggle ElevenLabs Audio Drama Master Player"
          >
            🎙️ Audio Drama
          </button>

          {/* Dedicated Script & Memoir Co-Pilot Assistant Toggle */}
          <button
            onClick={() => setShowScriptAssistant(!showScriptAssistant)}
            style={{
              background: showScriptAssistant ? '#2563eb' : '#1e293b',
              color: '#38bdf8',
              border: '1px solid #38bdf8',
              borderRadius: '4px',
              padding: '3px 10px',
              fontSize: '0.8rem',
              fontWeight: 'bold',
              cursor: 'pointer',
              display: 'flex',
              alignItems: 'center',
              gap: '4px',
              boxShadow: showScriptAssistant ? '0 0 12px rgba(56, 189, 248, 0.4)' : 'none'
            }}
            title="Open dedicated Script & Memoir AI Assistant connected to this project's isolated Vector DB"
          >
            🤖 Script Co-Pilot
          </button>
        </div>
      </div>

      {/* 3. Main Workspace */}
      <div className="sw-workspace" style={{ flex: 1, width: '100%', height: 'calc(100% - 40px)', maxHeight: '100%', minHeight: 0, display: 'flex', flexDirection: 'row', flexWrap: 'nowrap', overflow: 'hidden' }}>
        
        {/* Outline Panel (Left) */}
        {leftPanelVisible && !zenMode && (
          <div className="sw-left-panel" style={{ width: '220px', minWidth: '220px', flexShrink: 0, background: '#111827', borderRight: '1px solid #1f2937', padding: '12px', display: 'flex', flexDirection: 'column', overflowY: 'auto' }}>
            <div style={{ display: 'flex', gap: '8px', marginBottom: '16px' }}>
              <button className="sw-ribbon-btn" onClick={() => setOutlineMode('outline1')} style={{ background: outlineMode === 'outline1' ? '#1f2937' : 'transparent', flex: 1, border: '1px solid #1f2937' }}>Outline 1</button>
              <button className="sw-ribbon-btn" onClick={() => setOutlineMode('outline2')} style={{ background: outlineMode === 'outline2' ? '#1f2937' : 'transparent', flex: 1, border: '1px solid #1f2937' }}>Outline 2</button>
            </div>

            {/* Projects */}
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '8px' }}>
              <h4 className="sw-panel-header" style={{ color: '#facc15', margin: 0 }}>📁 Projects</h4>
              <div style={{ display: 'flex', gap: '4px' }}>
                <button 
                  onClick={() => setShowNewProjectModal(true)} 
                  style={{ background: '#238636', color: '#fff', border: 'none', borderRadius: '4px', padding: '2px 8px', fontSize: '0.75rem', fontWeight: 'bold', cursor: 'pointer' }}
                  title="Create a new Screenplay Project"
                >
                  + New
                </button>
                <button 
                  onClick={() => setLeftPanelVisible(false)} 
                  style={{ background: '#374151', color: '#9ca3af', border: 'none', borderRadius: '4px', padding: '2px 6px', fontSize: '0.75rem', cursor: 'pointer' }}
                  title="Close Outline Drawer"
                >
                  ✕
                </button>
              </div>
            </div>

            <div style={{ marginBottom: '16px' }}>
              <div style={{ display: 'flex', gap: '4px', marginBottom: '6px' }}>
                <select value={currentProject} onChange={(e) => handleSwitchProject(e.target.value)} className="sw-panel-input" style={{ flex: 1 }}>
                  {projects.map(p => <option key={p} value={p}>{p}</option>)}
                </select>
                {currentProject !== 'Default Project' && (
                  <button 
                    onClick={handleDeleteCurrentProject} 
                    disabled={isLoading}
                    style={{ background: '#ef444422', border: '1px solid #ef444466', color: '#ef4444', padding: '0 6px', borderRadius: '4px', cursor: 'pointer', fontSize: '0.8rem' }}
                    title="Archive current project (recoverable)"
                    aria-label="Archive current project"
                  >
                    📦
                  </button>
                )}
              </div>
              <button type="button" aria-expanded={showArchivedProjects} onClick={async () => {
                if (!showArchivedProjects) await loadArchivedProjects();
                setShowArchivedProjects(!showArchivedProjects);
              }} style={{ width: '100%', marginBottom: '6px' }}>
                📦 Archived projects
              </button>
              {showArchivedProjects && (
                <div role="region" aria-label="Archived projects" style={{ marginBottom: '10px' }}>
                  {archivedProjects.length === 0 && <p>No archived projects.</p>}
                  {archivedProjects.map(item => (
                    <div key={item.archive_id} style={{ marginBottom: '6px' }}>
                      <span>{item.project_name}</span>{' '}
                      <button type="button" disabled={isLoading} onClick={() => handleRestoreProject(item.archive_id)}>
                        Restore
                      </button>
                    </div>
                  ))}
                </div>
              )}
              <button onClick={handleImportClick} style={{ width: '100%', background: 'transparent', border: '1px solid #facc15', color: '#facc15', padding: '4px', cursor: 'pointer', fontSize: '0.8rem', borderRadius: '4px' }}>
                + Import (.pdf, .docx, .epub, .fdx, etc.)
              </button>
              <input type="file" ref={fileInputRef} style={{ display: 'none' }} accept=".pdf,.docx,.doc,.epub,.txt,.rtf,.md,.markdown,.fountain,.fdx" onChange={handleFileChange} />
            </div>

            {/* Adaptation Progress */}
            {isAdapting && adaptProgress && (
              <div style={{ marginBottom: '16px', background: '#374151', padding: '12px', borderRadius: '6px' }}>
                <div style={{ color: '#facc15', fontSize: '0.8rem', fontWeight: 'bold', marginBottom: '4px' }}>AI ADAPTATION IN PROGRESS...</div>
                <div style={{ width: '100%', background: '#1f2937', height: '8px', borderRadius: '4px', overflow: 'hidden' }}>
                  <div style={{ width: `${adaptProgress.progress}%`, background: '#facc15', height: '100%', transition: 'width 0.5s' }} />
                </div>
                <div style={{ color: '#9ca3af', fontSize: '0.7rem', marginTop: '4px', display: 'flex', justifyContent: 'space-between' }}>
                  <span>Chunk {adaptProgress.current_chunk || 0} of {adaptProgress.total_chunks || 0}</span>
                  <span>{adaptProgress.progress || 0}%</span>
                </div>
              </div>
            )}

            {/* Git Branching */}
            <h4 className="sw-panel-header" style={{ color: '#4ade80', margin: '0 0 8px 0' }}>🌿 Branches</h4>
            <div style={{ marginBottom: '16px' }}>
              <select value={currentBranch} onChange={(e) => setCurrentBranch(e.target.value)} className="sw-panel-input" style={{ width: '100%', marginBottom: '8px' }}>
                {branches.map(b => <option key={b} value={b}>{b}</option>)}
              </select>
              <div style={{ display: 'flex', gap: '4px' }}>
                <input type="text" value={newBranchName} onChange={(e) => setNewBranchName(e.target.value)} placeholder="New branch..." className="sw-panel-input" style={{ flex: 1 }} />
                <button onClick={handleCreateBranch} style={{ background: '#38bdf8', color: '#000', border: 'none', padding: '0 8px', fontWeight: 'bold', cursor: 'pointer', borderRadius: '3px' }}>+</button>
              </div>
            </div>

            {/* Sprints */}
            <h4 className="sw-panel-header" style={{ color: '#38bdf8', margin: '0 0 8px 0' }}>⏱️ Sprints</h4>
            {!activeSprint ? (
              <div style={{ marginBottom: '16px' }}>
                <input type="text" value={sprintName} onChange={(e) => setSprintName(e.target.value)} placeholder="Sprint name..." className="sw-panel-input" style={{ width: '100%', marginBottom: '4px', boxSizing: 'border-box' }} />
                <button onClick={handleStartSprint} style={{ width: '100%', background: '#a78bfa', color: '#000', padding: '4px', border: 'none', cursor: 'pointer', fontSize: '0.8rem', fontWeight: 'bold', borderRadius: '3px' }}>Start Sprint</button>
              </div>
            ) : (
              <div className="sw-sprint-active" style={{ marginBottom: '16px' }}>
                <div style={{ color: '#a78bfa', fontSize: '0.8rem', marginBottom: '4px', fontWeight: 'bold' }}>▶️ {activeSprint.name}</div>
                <button onClick={handleEndSprint} style={{ width: '100%', background: 'transparent', border: '1px solid #a78bfa', color: '#a78bfa', padding: '4px', cursor: 'pointer', fontSize: '0.8rem', borderRadius: '3px' }}>End Sprint</button>
              </div>
            )}
            
            {/* Outline Scenes with Search & Direct Jump */}
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '6px' }}>
              <h4 className="sw-panel-header" style={{ color: '#9ca3af', margin: 0 }}>🎬 Scenes ({filteredBeats.length})</h4>
            </div>
            <input 
              type="text" 
              value={sceneSearch} 
              onChange={(e) => setSceneSearch(e.target.value)} 
              placeholder="🔍 Filter scenes..." 
              className="sw-panel-input" 
              style={{ width: '100%', marginBottom: '8px', boxSizing: 'border-box', fontSize: '0.75rem', padding: '4px 6px' }}
            />
            <div className="sw-scene-list" style={{ flex: 1, overflowY: 'auto' }}>
                {filteredBeats.map((b, i) => (
                    <div 
                      key={i} 
                      className="sw-scene-item" 
                      onClick={() => handleJumpToScene(b)}
                      style={{ cursor: 'pointer', padding: '4px 6px', display: 'flex', justifyContent: 'space-between', alignItems: 'center', fontSize: '0.8rem', borderBottom: '1px solid #1f2937', transition: 'background 0.2s ease' }}
                    >
                        <span style={{ overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap', maxWidth: '130px' }}>
                          {b.heading}
                        </span>
                        <span style={{ color: '#9ca3af', fontSize: '0.7rem' }}>p.{Math.floor(b.page)}</span>
                    </div>
                ))}
                {filteredBeats.length === 0 && (
                    <div style={{ color: '#6b7280', fontSize: '0.75rem', textAlign: 'center', padding: '8px' }}>
                      No matching scenes
                    </div>
                )}
            </div>
          </div>
        )}

        {/* Central Area (Supports Split) */}
        <div className="sw-central-area" style={{ flex: 1, flexShrink: 1, width: leftPanelVisible && !zenMode ? 'calc(100% - 220px)' : '100%', height: '100%', maxHeight: '100%', minHeight: 0, display: 'flex', overflow: 'hidden', flexWrap: 'nowrap', flexDirection: splitMode === 'horizontal' ? 'column' : 'row' }}>
            
            {/* Primary View (Editor) */}
            {(activeView === 'editor' || splitMode !== 'none') && (
                <div className="sw-editor-container" style={{ flex: 1, height: '100%', maxHeight: '100%', minHeight: 0, display: 'flex', overflow: 'hidden', borderRight: splitMode === 'vertical' ? '1px solid #1f2937' : 'none', borderBottom: splitMode === 'horizontal' ? '1px solid #1f2937' : 'none' }}>
                    <ScreenplayEditor
                        ast={ast}
                        onChange={handleAstChange}
                        zoomLevel={zoomLevel}
                        onGhostwriter={(index) => handleGhostwriter(index)}
                        characters={characters}
                        currentPage={viewerCurrentPage}
                        onPageChange={(p) => setViewerCurrentPage(p)}
                        onProofPage={(p) => handleProofPage(p)}
                        isRevisionMode={isRevisionMode}
                        revisionColor={revisionColor}
                    />
                </div>
            )}

            {/* Secondary View (Preview or Beats) */}
            {(activeView !== 'editor' || splitMode !== 'none') && (
                <div className="sw-preview-container" style={{ flex: 1, height: '100%', background: '#0a0a0a', overflow: 'hidden', display: 'flex', flexDirection: 'column' }}>
                    {(activeView === 'preview' || (splitMode !== 'none' && activeView !== 'beats')) ? (
                         <ScreenplayViewer
                             ref={viewerRef}
                             ast={ast}
                             beats={parsed?.beats || []}
                             zoomLevel={zoomLevel}
                             currentPage={viewerCurrentPage}
                             onPageChange={(p) => setViewerCurrentPage(p)}
                             searchQuery={viewerSearch}
                             showInternalHeader={false}
                             onSwitchToEditor={(blockId) => {
                                 setActiveView('editor');
                                 if (blockId) {
                                     setTimeout(() => {
                                         const el = document.getElementById(`sw-block-${blockId}`);
                                         if (el) {
                                             el.scrollIntoView({ behavior: 'smooth', block: 'center' });
                                             el.focus();
                                         }
                                     }, 100);
                                 }
                             }}
                         />
                    ) : (
                         <div className="sw-beat-board" style={{ padding: `${20 * (zoomLevel / 100)}px`, gap: `${20 * (zoomLevel / 100)}px` }}>
                            <div className="sw-beat-timeline" />
                            
                            {(parsed?.beats || []).map((beat, idx) => {
                                const scale = zoomLevel / 100;
                                const isDragging = draggedBeatIndex === idx;
                                return (
                                    <div 
                                        key={idx} 
                                        draggable
                                        onDragStart={(e) => handleDragStart(e, idx)}
                                        onDragOver={handleDragOver}
                                        onDrop={(e) => handleDrop(e, idx)}
                                        onClick={() => handleJumpToScene(beat)}
                                        className="sw-beat-card"
                                        style={{
                                            width: `${140 * scale}px`,
                                            height: `${110 * scale}px`,
                                            background: isDragging ? '#1a1a1a' : '#1e1e1e',
                                            border: `2px solid ${isDragging ? '#555' : 'rgba(56, 189, 248, 0.4)'}`,
                                            padding: `${10 * scale}px`,
                                            boxShadow: isDragging ? 'none' : '0 4px 12px rgba(56, 189, 248, 0.1)',
                                            opacity: isDragging ? 0.5 : 1,
                                            cursor: 'pointer'
                                        }}
                                    >
                                        <div className="sw-beat-index" style={{ top: `-${25 * scale}px`, fontSize: `${12 * scale}px` }}>
                                            {idx + 1}
                                        </div>
                                        <div style={{ fontSize: `${18 * scale}px`, marginBottom: `${4 * scale}px` }}>{beat.emoji || '🎬'}</div>
                                        <div className="sw-beat-heading" style={{ fontSize: `${11 * scale}px` }}>
                                            {beat.heading}
                                        </div>
                                        <div className="sw-beat-page" style={{ fontSize: `${10 * scale}px` }}>
                                            p.{Math.floor(beat.page)}
                                        </div>
                                        
                                        {/* Video Attachment Logic */}
                                        <div style={{ marginTop: 'auto', borderTop: '1px solid #333', paddingTop: '4px' }}>
                                            {projectMetadata?.beat_videos?.[beat.id] ? (
                                                <div style={{ fontSize: `${9 * scale}px`, color: '#4ade80', textAlign: 'center', background: '#112211', padding: '2px', borderRadius: '4px' }}>
                                                    ✅ Video Generated
                                                </div>
                                            ) : (
                                                <button 
                                                    onClick={(e) => { e.stopPropagation(); handleAnimateBeat(beat); }}
                                                    disabled={animatingBeats[beat.id]}
                                                    style={{ width: '100%', background: '#3b82f6', color: 'white', border: 'none', borderRadius: '4px', fontSize: `${9 * scale}px`, padding: '2px', cursor: animatingBeats[beat.id] ? 'not-allowed' : 'pointer' }}
                                                >
                                                    {animatingBeats[beat.id] ? '⏳ Generating...' : '🎥 Animate Scene'}
                                                </button>
                                            )}
                                        </div>
                                    </div>
                                );
                            })}
                         </div>
                    )}
                </div>
            )}

        </div>

        {/* Navigator Panel (Right) */}
        {navigatorVisible && !zenMode && (
          <div className="sw-left-panel" style={{ width: '240px', minWidth: '240px', background: '#111827', borderLeft: '1px solid #1f2937', borderRight: 'none', padding: '12px', display: 'flex', flexDirection: 'column', overflowY: 'auto' }}>
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '12px' }}>
              <h4 className="sw-panel-header" style={{ color: '#38bdf8', margin: 0 }}>🧭 Navigator ({filteredBeats.length})</h4>
              <button onClick={() => setNavigatorVisible(false)} style={{ background: 'transparent', border: 'none', color: '#9ca3af', cursor: 'pointer', fontSize: '1.2rem' }}>&times;</button>
            </div>

            <input 
              type="text" 
              value={sceneSearch} 
              onChange={(e) => setSceneSearch(e.target.value)} 
              placeholder="🔍 Search scenes & characters..." 
              className="sw-panel-input" 
              style={{ width: '100%', marginBottom: '12px', boxSizing: 'border-box', fontSize: '0.8rem', padding: '4px 8px' }}
            />

            <div className="sw-scene-list" style={{ flex: 1, overflowY: 'auto' }}>
                {filteredBeats.map((b, i) => (
                    <div 
                        key={i} 
                        className="sw-scene-item" 
                        style={{ cursor: 'pointer', padding: '8px', borderBottom: '1px solid #1f2937', display: 'flex', alignItems: 'center', gap: '8px', transition: 'background 0.2s ease', borderRadius: '4px' }}
                        onClick={() => handleJumpToScene(b)}
                    >
                        <span style={{ fontSize: '1.2rem' }}>{b.emoji || '🎬'}</span>
                        <div style={{ display: 'flex', flexDirection: 'column', flex: 1, overflow: 'hidden' }}>
                           <span style={{ fontWeight: 'bold', color: '#fff', fontSize: '0.85rem', overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>
                             {b.heading}
                           </span>
                           <span style={{ color: '#9ca3af', fontSize: '0.75rem' }}>Page {Math.floor(b.page)}</span>
                        </div>
                    </div>
                ))}
                {filteredBeats.length === 0 && (
                    <div style={{ color: '#6b7280', textAlign: 'center', marginTop: '20px', fontSize: '0.9rem' }}>
                        No scenes found.
                    </div>
                )}
            </div>
          </div>
        )}
      </div>

      {/* 4. Bottom Status & Diagnostics Telemetry Panel */}
      <div className="sw-bottom-panel" style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', padding: '6px 16px', background: '#111827', borderTop: '1px solid #1f2937', fontSize: '0.8rem', color: '#9ca3af' }}>
        <div style={{ display: 'flex', gap: '14px', alignItems: 'center', flexWrap: 'wrap' }}>
          <span style={{ color: '#fff', fontWeight: 'bold' }}>🎬 SCRIPT TELEMETRY:</span>
          <span style={{ color: '#38bdf8', fontWeight: 'bold' }}>📜 {scriptDiag.pages} Pages (~{scriptDiag.runtimeStr} screen time)</span>
          <span style={{ color: '#4ade80' }}>⚖️ {scriptDiag.dialoguePct}% Dialogue / {scriptDiag.actionPct}% Action</span>
          <span style={{ color: '#facc15' }}>🎭 {scriptDiag.characterCount} Roles</span>
          <span style={{ color: '#e2e8f0' }}>🎬 {scriptDiag.sceneCount} Scenes</span>
          <span style={{ color: '#a78bfa' }}>🌿 Branch: {currentBranch}</span>
          {isGhostwriting && <span style={{ color: '#facc15', fontStyle: 'italic' }}>🤖 Ghostwriter is thinking...</span>}
        </div>

        {/* Page Jump Control */}
        <div style={{ display: 'flex', alignItems: 'center', gap: '6px' }}>
          <span>Jump to Page:</span>
          <input 
            type="number" 
            min="1" 
            max={totalScriptPages}
            value={pageJumpInput} 
            onChange={(e) => setPageJumpInput(e.target.value)}
            onKeyDown={(e) => {
              if (e.key === 'Enter') {
                handleJumpToPage(parseInt(pageJumpInput));
              }
            }}
            placeholder="Pg #" 
            className="sw-panel-input" 
            style={{ width: '55px', padding: '2px 6px', textAlign: 'center', fontSize: '0.8rem', boxSizing: 'border-box' }}
          />
          <button 
            onClick={() => handleJumpToPage(parseInt(pageJumpInput))}
            style={{ background: '#38bdf8', color: '#000', border: 'none', borderRadius: '3px', padding: '2px 8px', fontSize: '0.75rem', fontWeight: 'bold', cursor: 'pointer' }}
          >
            Go
          </button>
        </div>

        <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
          <span>Zoom: {zoomLevel}%</span>
          <input 
            type="range" 
            min="50" max="200" step="10" 
            value={zoomLevel} 
            onChange={(e) => setZoomLevel(parseInt(e.target.value))} 
            style={{ width: '90px', cursor: 'pointer' }}
          />
        </div>
      </div>

      {/* ── Create New Screenplay Project Modal ── */}
      {showNewProjectModal && (
        <div style={{
          position: 'fixed', top: 0, left: 0, right: 0, bottom: 0,
          background: 'rgba(0,0,0,0.85)', zIndex: 3000,
          display: 'flex', alignItems: 'center', justifyContent: 'center',
          backdropFilter: 'blur(6px)'
        }}>
          <div style={{
            background: '#1f2937', border: '1px solid #374151', padding: '24px',
            borderRadius: '12px', width: '540px', maxWidth: '92vw',
            boxShadow: '0 16px 48px rgba(0,0,0,0.7)', color: '#fff'
          }}>
            <h3 style={{ color: '#facc15', marginTop: 0, display: 'flex', alignItems: 'center', gap: '8px', fontSize: '1.2rem' }}>
              🎬 Create New Screenplay Project
            </h3>
            
            <p style={{ color: '#9ca3af', fontSize: '0.85rem', lineHeight: '1.4', marginBottom: '16px' }}>
              Initialize a dedicated Hollywood screenplay workspace with professional 8.5" x 11" US Letter geometry, title page metadata, and industry-standard element formatting.
            </p>

            <div style={{ marginBottom: '12px' }}>
              <label style={{ color: '#d1d5db', display: 'block', fontSize: '0.85rem', marginBottom: '4px', fontWeight: 'bold' }}>
                Project / Script Title:
              </label>
              <input 
                type="text" 
                value={newProjectName} 
                onChange={(e) => setNewProjectName(e.target.value)} 
                placeholder="e.g. Neon Horizon, Untitled Feature"
                style={{ width: '100%', padding: '8px 10px', background: '#111827', border: '1px solid #374151', borderRadius: '6px', color: '#fff', fontSize: '0.9rem', boxSizing: 'border-box' }} 
                autoFocus
              />
            </div>

            <div style={{ marginBottom: '12px' }}>
              <label style={{ color: '#d1d5db', display: 'block', fontSize: '0.85rem', marginBottom: '4px', fontWeight: 'bold' }}>
                Screenwriter / Author:
              </label>
              <input 
                type="text" 
                value={newProjectAuthor} 
                onChange={(e) => setNewProjectAuthor(e.target.value)} 
                placeholder="Author Name"
                style={{ width: '100%', padding: '8px 10px', background: '#111827', border: '1px solid #374151', borderRadius: '6px', color: '#fff', fontSize: '0.9rem', boxSizing: 'border-box' }} 
              />
            </div>

            <div style={{ marginBottom: '16px' }}>
              <label style={{ color: '#d1d5db', display: 'block', fontSize: '0.85rem', marginBottom: '4px', fontWeight: 'bold' }}>
                Starting Format & Template:
              </label>
              <select 
                value={newProjectTemplate} 
                onChange={(e) => setNewProjectTemplate(e.target.value)} 
                style={{ width: '100%', padding: '8px 10px', background: '#111827', border: '1px solid #374151', borderRadius: '6px', color: '#38bdf8', fontSize: '0.9rem', boxSizing: 'border-box' }}
              >
                <option value="feature">🎬 Hollywood Feature Film (3-Act Spec Script)</option>
                <option value="tv_drama">📺 TV Pilot (1-Hour Drama with Act Breaks)</option>
                <option value="tv_comedy">🎭 TV Pilot (30-Minute Comedy / Sitcom)</option>
                <option value="stage_play">🏛️ Theatrical Stage Play (Acts & Scenes)</option>
                <option value="audio_drama">🎙️ Audio Drama / Scripted Podcast</option>
              </select>
            </div>

            <div style={{ display: 'flex', justifyContent: 'flex-end', gap: '10px' }}>
              <button 
                onClick={() => setShowNewProjectModal(false)} 
                style={{ background: 'transparent', border: '1px solid #555', color: '#fff', padding: '8px 16px', borderRadius: '6px', cursor: 'pointer' }}
              >
                Cancel
              </button>
              <button 
                onClick={handleCreateNewProject} 
                style={{ background: '#238636', color: '#fff', border: 'none', padding: '8px 20px', fontWeight: 'bold', borderRadius: '6px', cursor: 'pointer', display: 'flex', alignItems: 'center', gap: '6px' }}
              >
                ✨ Create Project
              </button>
            </div>
          </div>
        </div>
      )}

      {/* ── Page Review & Format Doctor Modal ── */}
      {showPageReviewModal && (
        <div style={{
          position: 'fixed', top: 0, left: 0, right: 0, bottom: 0,
          background: 'rgba(0,0,0,0.85)', zIndex: 3000,
          display: 'flex', alignItems: 'center', justifyContent: 'center',
          backdropFilter: 'blur(8px)'
        }}>
          <div style={{
            background: '#111827', border: '1px solid #374151', borderRadius: '12px',
            width: '90%', maxWidth: '1100px', maxHeight: '90vh',
            display: 'flex', flexDirection: 'column', overflow: 'hidden',
            boxShadow: '0 20px 60px rgba(0,0,0,0.8)'
          }}>
            {/* Header */}
            <div style={{ padding: '16px 24px', background: '#1e293b', borderBottom: '1px solid #334155', display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
              <div style={{ display: 'flex', alignItems: 'center', gap: '12px' }}>
                <span style={{ fontSize: '1.4rem' }}>📖</span>
                <div>
                  <h3 style={{ margin: 0, color: '#f8fafc', fontSize: '1.1rem', fontWeight: 'bold' }}>
                    AI Page Review & Format Doctor — Page {reviewPageNum} of {totalScriptPages}
                  </h3>
                  <div style={{ color: '#94a3b8', fontSize: '0.8rem', marginTop: '2px' }}>
                    Review, standardize Fountain formatting, capitalize character cues, and polish dialogue.
                  </div>
                </div>
              </div>

              {/* Page Stepper Navigation */}
              <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                <button
                  onClick={() => handleProofPage(Math.max(1, reviewPageNum - 1))}
                  disabled={reviewPageNum <= 1 || isReviewingPage}
                  style={{ background: '#334155', color: '#fff', border: 'none', borderRadius: '4px', padding: '4px 10px', fontSize: '0.8rem', cursor: reviewPageNum <= 1 ? 'not-allowed' : 'pointer' }}
                >
                  ◀ Prev Page
                </button>
                <span style={{ color: '#facc15', fontWeight: 'bold', fontSize: '0.85rem' }}>Page {reviewPageNum}</span>
                <button
                  onClick={() => handleProofPage(Math.min(totalScriptPages, reviewPageNum + 1))}
                  disabled={reviewPageNum >= totalScriptPages || isReviewingPage}
                  style={{ background: '#334155', color: '#fff', border: 'none', borderRadius: '4px', padding: '4px 10px', fontSize: '0.8rem', cursor: reviewPageNum >= totalScriptPages ? 'not-allowed' : 'pointer' }}
                >
                  Next Page ▶
                </button>
                <button
                  onClick={() => setShowPageReviewModal(false)}
                  style={{ background: 'transparent', border: 'none', color: '#94a3b8', fontSize: '1.2rem', cursor: 'pointer', marginLeft: '12px' }}
                >
                  ✕
                </button>
              </div>
            </div>

            {/* Status bar */}
            <div style={{ padding: '8px 24px', background: '#0f172a', borderBottom: '1px solid #1e293b', display: 'flex', justifyContent: 'space-between', alignItems: 'center', fontSize: '0.85rem' }}>
              <span style={{ color: isReviewingPage ? '#facc15' : '#4ade80' }}>
                {isReviewingPage ? `⏳ ${reviewStatusMessage}` : '✅ Page formatting analyzed and ready.'}
              </span>
              <span style={{ color: '#64748b' }}>Tip: Type <code>!proof</code> anywhere in a block to trigger this instantly</span>
            </div>

            {/* Main Side-by-Side Comparison Body */}
            <div style={{ flex: 1, display: 'flex', overflow: 'hidden', padding: '16px 24px', gap: '20px' }}>
              {/* Left: Original Page */}
              <div style={{ flex: 1, display: 'flex', flexDirection: 'column', background: '#090d16', border: '1px solid #1e293b', borderRadius: '8px', padding: '12px', overflow: 'hidden' }}>
                <div style={{ color: '#94a3b8', fontSize: '0.8rem', fontWeight: 'bold', marginBottom: '8px', textTransform: 'uppercase', letterSpacing: '0.05em' }}>
                  Original Page {reviewPageNum} Content
                </div>
                <textarea
                  readOnly
                  value={reviewOriginalFountain}
                  style={{
                    flex: 1, width: '100%', background: '#020617', color: '#cbd5e1',
                    border: '1px solid #1e293b', borderRadius: '4px', padding: '12px',
                    fontFamily: '"Courier Prime", Courier, monospace', fontSize: '13px',
                    lineHeight: '1.4', resize: 'none', outline: 'none'
                  }}
                />
              </div>

              {/* Right: Suggested Proof / Format Fix */}
              <div style={{ flex: 1, display: 'flex', flexDirection: 'column', background: '#090d16', border: '1px solid #3b82f6', borderRadius: '8px', padding: '12px', overflow: 'hidden' }}>
                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '8px' }}>
                  <span style={{ color: '#38bdf8', fontSize: '0.8rem', fontWeight: 'bold', textTransform: 'uppercase', letterSpacing: '0.05em' }}>
                    ✨ AI Proofed & Formatted Screenplay
                  </span>
                  <span style={{ color: '#4ade80', fontSize: '0.75rem' }}>Editable preview</span>
                </div>
                <textarea
                  value={reviewSuggestedFountain}
                  onChange={(e) => setReviewSuggestedFountain(e.target.value)}
                  placeholder={isReviewingPage ? "Generating Hollywood formatted draft..." : "Formatted screenplay will appear here..."}
                  style={{
                    flex: 1, width: '100%', background: '#020617', color: '#f8fafc',
                    border: '1px solid #334155', borderRadius: '4px', padding: '12px',
                    fontFamily: '"Courier Prime", Courier, monospace', fontSize: '13px',
                    lineHeight: '1.4', resize: 'none', outline: 'none'
                  }}
                />
              </div>
            </div>

            {/* Footer / Action Buttons */}
            <div style={{ padding: '16px 24px', background: '#1e293b', borderTop: '1px solid #334155', display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
              <button
                onClick={() => handleProofPage(reviewPageNum)}
                disabled={isReviewingPage}
                style={{ background: '#334155', color: '#cbd5e1', border: 'none', borderRadius: '6px', padding: '8px 16px', fontSize: '0.85rem', cursor: 'pointer', display: 'flex', alignItems: 'center', gap: '6px' }}
              >
                🔄 Re-Analyze Page
              </button>

              <div style={{ display: 'flex', gap: '12px' }}>
                <button
                  onClick={() => setShowPageReviewModal(false)}
                  style={{ background: 'transparent', color: '#94a3b8', border: '1px solid #475569', borderRadius: '6px', padding: '8px 16px', fontSize: '0.85rem', cursor: 'pointer' }}
                >
                  Cancel
                </button>
                <button
                  onClick={() => handleApplyPageProof(false)}
                  disabled={!reviewSuggestedFountain || isReviewingPage}
                  style={{ background: '#2563eb', color: '#fff', border: 'none', borderRadius: '6px', padding: '8px 16px', fontSize: '0.85rem', fontWeight: 'bold', cursor: (!reviewSuggestedFountain || isReviewingPage) ? 'not-allowed' : 'pointer' }}
                >
                  ✅ Apply to Page {reviewPageNum}
                </button>
                <button
                  onClick={() => handleApplyPageProof(true)}
                  disabled={!reviewSuggestedFountain || isReviewingPage || reviewPageNum >= totalScriptPages}
                  style={{ background: '#22c55e', color: '#000', border: 'none', borderRadius: '6px', padding: '8px 18px', fontSize: '0.85rem', fontWeight: 'bold', cursor: (!reviewSuggestedFountain || isReviewingPage || reviewPageNum >= totalScriptPages) ? 'not-allowed' : 'pointer' }}
                >
                  ⏭ Apply & Next Page ({reviewPageNum + 1})
                </button>
              </div>
            </div>
          </div>
        </div>
      )}

      {/* ── Dedicated Project Script & Memoir Assistant Drawer ── */}
      <ScriptAssistantDrawer
        projectName={currentProject}
        isOpen={showScriptAssistant}
        onClose={() => setShowScriptAssistant(false)}
        onInsertScript={handleInsertScriptAssistantText}
        backendUrl={BACKEND_URL}
      />

      {/* ── Screenplay-to-Book AI Novelizer Studio Modal ── */}
      <ScriptToBookNovelizerModal
        isOpen={showNovelizerModal}
        onClose={() => setShowNovelizerModal(false)}
        backendUrl={BACKEND_URL}
        currentProject={currentProject}
        activeScript={screenplay}
      />

      {/* ── Multi-Voice AI Audio Table Read Studio Modal ── */}
      <ScreenplayTableReadModal
        isOpen={showTableReadModal}
        onClose={() => setShowTableReadModal(false)}
        screenplayText={screenplay}
        projectName={currentProject?.name || currentProject || 'Active Script'}
      />

      {/* ── Live Writing & AI Thought Telemetry Modal ── */}
      <ScriptTelemetryModal
        isOpen={showScriptTelemetryModal}
        onClose={() => setShowScriptTelemetryModal(false)}
        projectName={currentProject?.name || currentProject || 'The Mafia'}
        screenplayText={screenplay}
        ast={ast}
        totalScriptPages={totalScriptPages}
        autoSaveStatus={autoSaveStatus}
        lastSavedTime={lastSavedTime}
        backendUrl={BACKEND_URL}
      />

      {/* ── Hollywood Screenwriting Studio Step-by-Step Help Guide & Tool Manual ── */}
      <ScreenwritingHelpGuideModal
        isOpen={showHelpGuideModal}
        onClose={() => setShowHelpGuideModal(false)}
      />

    </div>
  );
}
