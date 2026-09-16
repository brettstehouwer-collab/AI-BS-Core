import React, { useState } from 'react';
import { Eye, FileText, Database } from 'lucide-react';

export default function ComputerVisionSuiteTab() {
  const [activeModule, setActiveModule] = useState('mod1');

  return (
    <div className="h-full flex flex-col bg-slate-900 text-slate-200 p-6">
      <h2 className="text-2xl font-bold mb-4 flex items-center gap-2 text-indigo-400">
        <Eye className="w-6 h-6" /> Computer Vision Engineering OS
      </h2>
      
      <div className="flex gap-4 mb-6">
        <button 
          onClick={() => setActiveModule('mod1')}
          className={`px-4 py-2 rounded-lg font-medium ${activeModule === 'mod1' ? 'bg-indigo-600 text-white' : 'bg-slate-800 text-slate-400'}`}>
          <FileText className="inline w-4 h-4 mr-2" /> YOLO Dataset Gen
        </button>
        <button 
          onClick={() => setActiveModule('mod2')}
          className={`px-4 py-2 rounded-lg font-medium ${activeModule === 'mod2' ? 'bg-indigo-600 text-white' : 'bg-slate-800 text-slate-400'}`}>
          <Database className="inline w-4 h-4 mr-2" /> Edge Quantization Sim
        </button>
      </div>

      <div className="flex-1 border border-slate-700 bg-slate-800/50 rounded-xl p-4 flex flex-col items-center justify-center">
        {activeModule === 'mod1' ? (
          <div className="text-center">
            <h3 className="text-xl font-bold mb-2">YOLO Dataset Gen</h3>
            <p className="text-slate-400 max-w-md">Offline module processing. All heavy dependencies stored in E:\AI_BS_Resources.</p>
          </div>
        ) : (
          <div className="text-center">
            <h3 className="text-xl font-bold mb-2">Edge Quantization Sim</h3>
            <p className="text-slate-400 max-w-md">Local Stehouwer LLM / RAG execution. No cloud transit.</p>
          </div>
        )}
      </div>
    </div>
  );
}
