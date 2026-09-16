import React from 'react';

export default function BullshitEvolutionHistory() {
  const milestones = [
    {
      version: "Phase 1: Genesis",
      title: "The AI-BS Matrix",
      date: "Early Architecture",
      description: "The project began as 'AI-BS Matrix', an ambitious attempt to create a localized Agentic Desktop Environment. Initial execution relied on raw VBScript and batch files to stitch together python scripts across the S: and G: drives.",
      icon: "🌌"
    },
    {
      version: "Phase 4: Consolidation",
      title: "The Great Rebranding",
      date: "Mid-Architecture",
      description: "The 'Matrix' moniker was dropped in favor of the sleeker 'AI-BS'. The chaotic VBScripts were replaced by a robust PyInstaller-compiled 'brain_backend.exe'. The UI started leveraging Electron for a unified application experience.",
      icon: "🔄"
    },
    {
      version: "Phase 7: Sovereignty",
      title: "Zero Cloud Dependency",
      date: "Security Milestone",
      description: "The 'Sovereignty Audit' was introduced. All external cloud APIs (OpenAI, AWS) were explicitly banned. The system shifted to a 100% local architecture using Ollama (stehouwer_llm) and PyTorch diffusers on the RTX 4090.",
      icon: "🛡️"
    },
    {
      version: "Phase 10: Living Memory",
      title: "ChromaDB & The Infinite Loop",
      date: "Cognitive Milestone",
      description: "AI-BS gained long-term memory. The 'infinite_learning_loop.py' daemon was created to tail chat logs, parse heuristics, and permanently store successful code blocks into the 'master_memory_dump.json' vector vault.",
      icon: "🧠"
    },
    {
      version: "Phase 14: Production",
      title: "Stehouwer Reality Standard v1.6.1",
      date: "Present Day",
      description: "Culmination of 1,000+ hours of iteration. Featuring a glassmorphism React frontend, 7-pass execution sandbox, polyglot background scavengers, and deep multi-drive (C:\\, G:\\, S:\\) telemetry tracking.",
      icon: "⚡"
    }
  ];

  const driveStats = [
    { name: "C:\\ Drive", role: "Primary Execution (Node/Vite, AppData Config)" },
    { name: "G:\\ Drive", role: "Deep Storage (Stehouwer_Server, Old Matrix DBs)" },
    { name: "S:\\ Drive", role: "Agent Sandboxes (.securecoder, .gemini, .chia)" },
  ];

  const releaseLogs = [
    { date: "July 22, 2026", version: "v1.2.0", focus: "Tool calling, Ollama Modelfile, 200GB SQLite mmap", docs: "Stehouwer_LLM_Upgrade_Study_Guide.md" },
    { date: "Aug 6, 2026", version: "Phase 2–10", focus: "Banquet Architect, NLP expansion, Gemini MCP Server", docs: "Agent_Implementation_Plans_History/" },
    { date: "Aug 7, 2026", version: "Phase 12", focus: "70-Vertical Infrastructure & Ubuntu-Bio Bridge", docs: "2026-08-07_Ubuntu_Bio_plan.md" },
    { date: "Aug 9, 2026", version: "Phase 14", focus: "Unreal Engine 3D Environment Integration & Web Remote Control", docs: "Unreal_Engine_Integration_Plan_20260809.md" },
    { date: "Aug 11, 2026", version: "Phase 50", focus: "ComfyUI Headless Generator & The Bad Side Upside Down", docs: "AI_BS_MASTER_ECOSYSTEM_MANUAL.md" },
    { date: "Aug 12, 2026", version: "v5.18.37", focus: "System-wide audit (6,403 Vite modules, 4,510 Python files verified)", docs: "AI_BS_MASTER_ARCHITECTURAL_LEDGER.md" },
    { date: "Aug 13, 2026", version: "v5.21.0", focus: "Draggable Grid Workspace migration (24-column layout)", docs: "AI_BS_MASTER_ARCHITECTURAL_LEDGER.md" },
    { date: "Aug 13, 2026", version: "v5.22.0", focus: "Final Draft Screenplay Editor Pagination & Nemotron Hybrid", docs: "AI_BS_MASTER_ARCHITECTURAL_LEDGER.md" },
    { date: "Aug 14, 2026", version: "v5.22.2", focus: "FLUX 3 Image-to-Video Workflow UI & Genie 3 Fallback", docs: "AI_BS_MASTER_ARCHITECTURAL_LEDGER.md" },
    { date: "Aug 14, 2026", version: "v5.22.4", focus: "Creation Suite: SSE Streaming, Dual-Dialogue & Character Autocomplete", docs: "AI_BS_MASTER_ARCHITECTURAL_LEDGER.md" },
    { date: "Aug 14, 2026", version: "v5.22.5", focus: "Universal Manuscript Ingestion & Hollywood Adaptation Matrix", docs: "AI_BS_MASTER_ARCHITECTURAL_LEDGER.md" },
    { date: "Aug 18, 2026", version: "v5.24.0", focus: "Multi-User Enterprise Matrix: MOM Version, Live Chat, 5-Pillar Mode", docs: "AI_BS_MASTER_ARCHITECTURAL_LEDGER.md" }
  ];

  return (
    <div className="p-8 text-white min-h-screen bg-gray-900 rounded-xl overflow-y-auto">
      <div className="mb-8 border-b border-gray-700 pb-4">
        <h1 className="text-4xl font-extrabold tracking-tight bg-clip-text text-transparent bg-gradient-to-r from-purple-400 via-pink-500 to-red-500">
          The Evolution of AI-BS
        </h1>
        <p className="mt-2 text-gray-400 text-lg">
          A historical archive of the 1,000+ hour journey from the AI-BS Matrix to a Sovereign Desktop OS.
        </p>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-8">
        
        {/* Left Column: Timeline */}
        <div className="lg:col-span-2 space-y-6">
          <h2 className="text-2xl font-bold text-green-400 mb-4">Architectural Timeline</h2>
          <div className="relative border-l border-gray-700 ml-4 space-y-8">
            {milestones.map((item, idx) => (
              <div key={idx} className="ml-8 relative">
                <div className="absolute -left-12 top-1 w-8 h-8 bg-gray-800 border-2 border-green-500 rounded-full flex items-center justify-center text-sm shadow-[0_0_10px_rgba(34,197,94,0.5)]">
                  {item.icon}
                </div>
                <div className="bg-gray-800/50 backdrop-blur-md p-5 rounded-lg border border-gray-700 shadow-xl hover:border-green-400 transition-colors">
                  <div className="flex justify-between items-center mb-2">
                    <span className="text-xs font-mono text-pink-400 px-2 py-1 bg-pink-400/10 rounded-full">{item.version}</span>
                    <span className="text-xs text-gray-500 font-mono">{item.date}</span>
                  </div>
                  <h3 className="text-xl font-bold text-white mb-2">{item.title}</h3>
                  <p className="text-gray-300 text-sm leading-relaxed">{item.description}</p>
                </div>
              </div>
            ))}
          </div>
        </div>

        {/* Right Column: Lore & Stats */}
        <div className="space-y-6">
          
          <div className="bg-gray-800/50 backdrop-blur-md p-6 rounded-lg border border-purple-500/30 shadow-[0_0_15px_rgba(168,85,247,0.15)]">
            <h3 className="text-lg font-bold text-purple-400 mb-3 border-b border-gray-700 pb-2">The Multi-Drive Ecosystem</h3>
            <p className="text-xs text-gray-400 mb-4">
              AI-BS does not live in a single folder. It aggressively expanded its tendrils across the host machine's drives, mapping out memory vaults, logging directories, and sandboxes.
            </p>
            <ul className="space-y-3">
              {driveStats.map((drive, idx) => (
                <li key={idx} className="bg-gray-900/80 p-3 rounded border border-gray-700">
                  <span className="text-green-400 font-mono text-sm block mb-1">{drive.name}</span>
                  <span className="text-gray-400 text-xs">{drive.role}</span>
                </li>
              ))}
            </ul>
          </div>

          <div className="bg-gradient-to-br from-gray-800 to-gray-900 p-6 rounded-lg border border-gray-700">
            <h3 className="text-lg font-bold text-white mb-3">Install Packaging Lore</h3>
            <p className="text-sm text-gray-300 mb-3">
              The deployment mechanics of AI-BS have seen numerous overhauls:
            </p>
            <ul className="list-disc list-inside text-xs text-gray-400 space-y-2">
              <li><strong>Era 1:</strong> Start_server.bat & VBScript hidden tasks.</li>
              <li><strong>Era 2:</strong> PyInstaller compilation of <code>brain_backend.exe</code> causing fork bombs.</li>
              <li><strong>Era 3:</strong> Electron-Builder wrapping the Python API inside a massive universal Windows Installer.</li>
              <li><strong>Era 4:</strong> Vite + React + FastAPI direct execution via unified architecture.</li>
            </ul>
          </div>

          <div className="bg-green-900/20 p-6 rounded-lg border border-green-500/30 text-center">
            <h3 className="text-3xl font-black text-green-400 mb-1">1,000+</h3>
            <p className="text-sm text-green-300 font-medium">Hours of Iteration</p>
            <p className="text-xs text-gray-400 mt-2">Zero compromises on data sovereignty.</p>
          </div>

        </div>
      </div>

      {/* Full Width Bottom Section: Detailed Release Log */}
      <div className="mt-12">
        <h2 className="text-2xl font-bold text-blue-400 mb-6 border-b border-gray-700 pb-2">Master Release Log</h2>
        <div className="bg-gray-800/50 backdrop-blur-md rounded-lg border border-gray-700 overflow-hidden shadow-2xl">
          <div className="overflow-x-auto overflow-y-auto max-h-96 scroll-smooth custom-scrollbar">
            <table className="w-full text-left border-collapse">
              <thead className="bg-gray-900 sticky top-0 z-10 shadow-md">
                <tr>
                  <th className="p-4 font-bold text-gray-300 border-b border-gray-700 text-sm tracking-wider">Milestone / Date</th>
                  <th className="p-4 font-bold text-gray-300 border-b border-gray-700 text-sm tracking-wider">Version</th>
                  <th className="p-4 font-bold text-gray-300 border-b border-gray-700 text-sm tracking-wider">Primary Focus</th>
                  <th className="p-4 font-bold text-gray-300 border-b border-gray-700 text-sm tracking-wider">Key Documentation</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-gray-700/50">
                {releaseLogs.map((log, idx) => (
                  <tr key={idx} className="hover:bg-gray-700/30 transition-colors">
                    <td className="p-4 text-sm text-gray-400 whitespace-nowrap">{log.date}</td>
                    <td className="p-4 text-sm font-mono text-pink-400 whitespace-nowrap">
                      <span className="bg-pink-400/10 px-2 py-1 rounded-md">{log.version}</span>
                    </td>
                    <td className="p-4 text-sm text-gray-200">{log.focus}</td>
                    <td className="p-4 text-xs font-mono text-blue-300 break-all">{log.docs}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      </div>
      
    </div>
  );
}
