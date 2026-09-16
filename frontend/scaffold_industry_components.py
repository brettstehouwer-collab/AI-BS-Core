import os

components = [
    ("EdgeIoTSuiteTab", "Cpu", "Edge AI & IoT OS", "Firmware Tracker", "Telemetry Dashboard"),
    ("ObservabilitySuiteTab", "Activity", "Telemetry & Observability OS", "Tracing Analyzer", "Alert Fatigue Reducer"),
    ("EmbeddedSuiteTab", "Cpu", "Embedded Systems OS", "Binary Analyzer", "RTOS RAG"),
    ("GameArchitectureSuiteTab", "Gamepad", "Game Engine Architecture OS", "Shader Optimizer", "C++ Leak Hunter"),
    ("PenTestingSuiteTab", "ShieldAlert", "Network Security & Pen Testing OS", "Red-Team Vector Gen", "PCAP Analyzer"),
    ("AutonomousVehiclesSuiteTab", "Car", "Autonomous Vehicles OS", "LiDAR Renderer", "Sensor Fusion Anomaly"),
    ("ARDevSuiteTab", "Glasses", "Augmented Reality Development OS", "Spatial Debugger", "Anchor Tracker"),
    ("SemiconductorsSuiteTab", "Cpu", "Semiconductors & VLSI OS", "Chip Defect Vision", "Cleanroom Compliance"),
    ("NanotechSuiteTab", "Atom", "Nanotechnology OS", "Synthesis RAG", "Molecule Dynamics Sim"),
    ("DeepSpaceSuiteTab", "Satellite", "Deep Space Communications OS", "Telemetry Decoder", "Latency Router")
]

template = """import React, { useState } from 'react';
import { {icon}, FileText, Database } from 'lucide-react';

export default function {name}() {
  const [activeModule, setActiveModule] = useState('mod1');

  return (
    <div className="h-full flex flex-col bg-slate-900 text-slate-200 p-6">
      <h2 className="text-2xl font-bold mb-4 flex items-center gap-2 text-indigo-400">
        <{icon} className="w-6 h-6" /> {title}
      </h2>
      
      <div className="flex gap-4 mb-6">
        <button 
          onClick={() => setActiveModule('mod1')}
          className={`px-4 py-2 rounded-lg font-medium ${activeModule === 'mod1' ? 'bg-indigo-600 text-white' : 'bg-slate-800 text-slate-400'}`}>
          <FileText className="inline w-4 h-4 mr-2" /> {mod1}
        </button>
        <button 
          onClick={() => setActiveModule('mod2')}
          className={`px-4 py-2 rounded-lg font-medium ${activeModule === 'mod2' ? 'bg-indigo-600 text-white' : 'bg-slate-800 text-slate-400'}`}>
          <Database className="inline w-4 h-4 mr-2" /> {mod2}
        </button>
      </div>

      <div className="flex-1 border border-slate-700 bg-slate-800/50 rounded-xl p-4 flex flex-col items-center justify-center">
        {activeModule === 'mod1' ? (
          <div className="text-center">
            <h3 className="text-xl font-bold mb-2">{mod1}</h3>
            <p className="text-slate-400 max-w-md">Offline module processing. All heavy dependencies stored in E:\\AI_BS_Resources.</p>
          </div>
        ) : (
          <div className="text-center">
            <h3 className="text-xl font-bold mb-2">{mod2}</h3>
            <p className="text-slate-400 max-w-md">Local Stehouwer LLM / RAG execution. No cloud transit.</p>
          </div>
        )}
      </div>
    </div>
  );
}
"""

for name, icon, title, mod1, mod2 in components:
    # lucide icon aliases
    if icon == "Glasses": icon = "Eye"
    if icon == "Satellite": icon = "Radio"
    
    rendered = template.replace("{name}", name).replace("{icon}", icon).replace("{title}", title).replace("{mod1}", mod1).replace("{mod2}", mod2)
    rendered = rendered.replace("${activeModule", "${activeModule")
    with open(f"C:/AI-BS/frontend/components/industry_suites/{name}.jsx", "w") as f:
        f.write(rendered)

print("Scaffolded Phase 8 components.")
