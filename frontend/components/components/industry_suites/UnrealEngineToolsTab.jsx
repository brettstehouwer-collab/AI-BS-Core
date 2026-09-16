import React, { useState } from 'react';
import { Gamepad2, Layers, Cpu, Wrench, FileCode, PlayCircle, Settings, Music, Box, Activity } from 'lucide-react';

export default function UnrealEngineToolsTab() {
  const [activeTool, setActiveTool] = useState(null);

  const tools = [
    { id: 'level', name: 'Level Editor Tools', icon: Layers, script: '01_Level_Editor/spawn_actors.py', desc: 'Scene assembly, actor placement, world composition.' },
    { id: 'blueprint', name: 'Blueprint Editor Tools', icon: FileCode, script: '02_Blueprint_Editor/create_blueprint.py', desc: 'Node-based visual scripting, gameplay logic.' },
    { id: 'material', name: 'Material Editor Tools', icon: Settings, script: '03_Material_Editor/create_material.py', desc: 'Shader authoring, surface properties.' },
    { id: 'niagara', name: 'Niagara Editor Tools', icon: PlayCircle, script: '04_Niagara_Editor/create_niagara_system.py', desc: 'Particle systems, VFX, simulations.' },
    { id: 'umg', name: 'UMG UI Editor Tools', icon: Cpu, script: '05_UMG_UI_Editor/create_widget.py', desc: 'HUDs, menus, screen layouts.' },
    { id: 'control_rig', name: 'Control Rig Tools', icon: Wrench, script: '06_Control_Rig/setup_control_rig.py', desc: 'Skeletal retargeting, cinematics.' },
    { id: 'modeling', name: 'Modeling Mode Tools', icon: Box, script: '07_Modeling_Mode/process_meshes.py', desc: 'Mesh creation, sculpting, booleans.' },
    { id: 'behavior', name: 'Behavior Tree Tools', icon: Activity, script: '08_Behavior_Tree/setup_behavior_tree.py', desc: 'AI decision hierarchies, NPC logic.' },
    { id: 'physics', name: 'Physics Asset Tools', icon: Settings, script: '09_Physics_Asset/setup_physics.py', desc: 'Chaos solvers, rigid bodies, cloth.' },
    { id: 'audio', name: 'MetaSounds Tools', icon: Music, script: '10_Audio_MetaSounds/create_metasound.py', desc: 'Procedural sound design.' }
  ];

  return (
    <div className="h-full flex flex-col bg-slate-900 text-slate-200 p-6">
      <h2 className="text-2xl font-bold mb-6 flex items-center gap-2 text-indigo-400">
        <Gamepad2 className="w-8 h-8" /> Unreal Engine Creation Tools Matrix
      </h2>
      
      <div className="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-3 gap-4 mb-6">
        {tools.map(tool => (
          <button 
            key={tool.id}
            onClick={() => setActiveTool(tool)}
            className={`p-4 rounded-xl border text-left transition-all flex items-start gap-4 ${
              activeTool?.id === tool.id 
                ? 'bg-indigo-900/40 border-indigo-500 shadow-lg shadow-indigo-900/20' 
                : 'bg-slate-800 border-slate-700 hover:border-slate-500'
            }`}
          >
            <div className={`p-3 rounded-lg ${activeTool?.id === tool.id ? 'bg-indigo-600' : 'bg-slate-700'}`}>
              <tool.icon className="w-6 h-6 text-white" />
            </div>
            <div>
              <h3 className="font-bold text-white mb-1">{tool.name}</h3>
              <p className="text-xs text-slate-400 font-mono mb-2">{tool.script}</p>
              <p className="text-sm text-slate-300">{tool.desc}</p>
            </div>
          </button>
        ))}
      </div>

      <div className="flex-1 border border-slate-700 bg-slate-800/50 rounded-xl p-6">
        {activeTool ? (
          <div>
            <h3 className="text-xl font-bold mb-4 text-white">Directive Details: {activeTool.name}</h3>
            <div className="bg-black/50 p-4 rounded-lg font-mono text-sm text-green-400 mb-4">
              Path: E:\AI_BS_Resources\Unreal_Scripts\{activeTool.script}
            </div>
            <p className="text-slate-300">
              This module triggers local Python execution mapped directly to the Unreal Engine Python API. 
              The scripts are designed to automate {activeTool.desc.toLowerCase()}
            </p>
          </div>
        ) : (
          <div className="h-full flex flex-col items-center justify-center text-slate-500">
            <Gamepad2 className="w-12 h-12 mb-4 opacity-50" />
            <p>Select an Unreal Engine Tool Directive to view execution details.</p>
            <p className="text-xs mt-2">All scripts are safely stored in E:\AI_BS_Resources\Unreal_Scripts</p>
          </div>
        )}
      </div>
    </div>
  );
}
