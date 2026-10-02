import React, { useState } from 'react';
import {
  Gamepad2,
  Users,
  Cpu,
  ExternalLink,
  Share2,
  RefreshCw,
  Globe,
  Smartphone,
  Layers,
  Sparkles,
  Maximize2
} from 'lucide-react';
import SteamGamingHubTab from './SteamGamingHubTab.jsx';
import ProcessMemoryLabTab from './ProcessMemoryLabTab.jsx';

export default function CentralGamingHubTab({ backendUrl = 'http://localhost:8080' }) {
  const [activeSection, setActiveSection] = useState('dyadic'); // 'dyadic' | 'steam' | 'trainer'
  const [dyadicSource, setDyadicSource] = useState('local'); // 'local' | 'cloud'
  const [iframeKey, setIframeKey] = useState(0);

  const localDyadicUrl = '/dyadic/index.html';
  const cloudDyadicUrl = 'https://dyadic-hub.web.app';
  const activeDyadicUrl = dyadicSource === 'cloud' ? cloudDyadicUrl : localDyadicUrl;

  const copyCloudLink = () => {
    navigator.clipboard.writeText(cloudDyadicUrl);
    alert('Invite link copied: ' + cloudDyadicUrl);
  };

  return (
    <div className="flex flex-col h-full w-full bg-[#09090b] text-[#fafafa] overflow-hidden">
      {/* Top Gaming Hub Navigation Header */}
      <div className="flex flex-wrap items-center justify-between gap-3 px-4 py-3 bg-[#121215] border-b border-[#27272a] select-none">
        <div className="flex items-center gap-3">
          <div className="w-10 h-10 rounded-xl bg-gradient-to-br from-indigo-500/20 to-purple-600/30 border border-indigo-500/30 flex items-center justify-center text-indigo-400">
            <Gamepad2 className="w-5 h-5" />
          </div>
          <div>
            <h1 className="text-base font-bold tracking-tight text-white flex items-center gap-2">
              Central Gaming Hub
              <span className="text-[10px] font-semibold px-2 py-0.5 rounded-full bg-indigo-500/20 text-indigo-300 border border-indigo-500/30 uppercase tracking-wider">
                Unified Suite
              </span>
            </h1>
            <p className="text-xs text-zinc-400 hidden sm:block">
              2-Player P2P Dyadic Ludic Hub • Steam Library Launcher • Win32 Memory Trainer
            </p>
          </div>
        </div>

        {/* Section Switcher Tabs */}
        <div className="flex items-center gap-1.5 bg-[#18181b] p-1 rounded-xl border border-[#27272a]">
          <button
            onClick={() => setActiveSection('dyadic')}
            className={`flex items-center gap-2 px-3.5 py-1.5 rounded-lg text-xs font-semibold transition-all ${
              activeSection === 'dyadic'
                ? 'bg-indigo-600 text-white shadow-sm shadow-indigo-600/30'
                : 'text-zinc-400 hover:text-zinc-200 hover:bg-[#27272a]/50'
            }`}
          >
            <Users className="w-3.5 h-3.5" />
            <span>2P Dyadic Hub</span>
            <span className="w-1.5 h-1.5 rounded-full bg-emerald-400 animate-pulse hidden sm:inline-block"></span>
          </button>

          <button
            onClick={() => setActiveSection('steam')}
            className={`flex items-center gap-2 px-3.5 py-1.5 rounded-lg text-xs font-semibold transition-all ${
              activeSection === 'steam'
                ? 'bg-indigo-600 text-white shadow-sm shadow-indigo-600/30'
                : 'text-zinc-400 hover:text-zinc-200 hover:bg-[#27272a]/50'
            }`}
          >
            <Gamepad2 className="w-3.5 h-3.5" />
            <span>Steam Launcher</span>
          </button>

          <button
            onClick={() => setActiveSection('trainer')}
            className={`flex items-center gap-2 px-3.5 py-1.5 rounded-lg text-xs font-semibold transition-all ${
              activeSection === 'trainer'
                ? 'bg-indigo-600 text-white shadow-sm shadow-indigo-600/30'
                : 'text-zinc-400 hover:text-zinc-200 hover:bg-[#27272a]/50'
            }`}
          >
            <Cpu className="w-3.5 h-3.5" />
            <span>Memory Trainer</span>
          </button>
        </div>
      </div>

      {/* Main Tab Viewport */}
      <div className="flex-1 overflow-auto">
        {/* SUBTAB 1: DYADIC LUDIC HUB */}
        {activeSection === 'dyadic' && (
          <div className="flex flex-col h-full w-full">
            {/* Quick Action Sub-bar for Dyadic Hub */}
            <div className="flex flex-wrap items-center justify-between gap-2 px-4 py-2 bg-[#18181b]/80 border-b border-[#27272a] text-xs">
              <div className="flex items-center gap-2">
                <span className="text-zinc-400 font-medium">Source:</span>
                <div className="flex items-center bg-[#09090b] rounded-md p-0.5 border border-[#27272a]">
                  <button
                    onClick={() => setDyadicSource('local')}
                    className={`px-2.5 py-1 rounded text-[11px] font-medium transition ${
                      dyadicSource === 'local'
                        ? 'bg-indigo-600 text-white'
                        : 'text-zinc-400 hover:text-white'
                    }`}
                  >
                    Local Offline
                  </button>
                  <button
                    onClick={() => setDyadicSource('cloud')}
                    className={`px-2.5 py-1 rounded text-[11px] font-medium transition ${
                      dyadicSource === 'cloud'
                        ? 'bg-indigo-600 text-white'
                        : 'text-zinc-400 hover:text-white'
                    }`}
                  >
                    Firebase Cloud (Live P2P)
                  </button>
                </div>

                <span className="text-zinc-500 hidden md:inline">•</span>
                <span className="text-zinc-400 hidden md:inline">
                  7 Games: 20Q, Word Assoc, 5-Second, 2T1L, WYR, NHIE, One-Sentence Story
                </span>
              </div>

              <div className="flex items-center gap-2">
                <button
                  onClick={copyCloudLink}
                  title="Copy iPhone Invitation Link"
                  className="flex items-center gap-1.5 px-2.5 py-1 rounded-md bg-[#27272a] hover:bg-[#3f3f46] text-zinc-200 text-xs font-medium transition"
                >
                  <Share2 className="w-3.5 h-3.5 text-indigo-400" />
                  <span>Copy iPhone Link</span>
                </button>

                <button
                  onClick={() => setIframeKey(k => k + 1)}
                  title="Reload Game Hub"
                  className="p-1.5 rounded-md bg-[#27272a] hover:bg-[#3f3f46] text-zinc-300 transition"
                >
                  <RefreshCw className="w-3.5 h-3.5" />
                </button>

                <a
                  href={cloudDyadicUrl}
                  target="_blank"
                  rel="noopener noreferrer"
                  className="flex items-center gap-1 px-2.5 py-1 rounded-md bg-emerald-600/20 text-emerald-300 hover:bg-emerald-600/30 border border-emerald-500/30 text-xs font-medium transition"
                >
                  <ExternalLink className="w-3.5 h-3.5" />
                  <span>Open Fullscreen</span>
                </a>
              </div>
            </div>

            {/* Embedded Responsive Container */}
            <div className="flex-1 w-full bg-[#09090b] relative flex items-center justify-center p-0 md:p-2">
              <div className="w-full h-full max-w-2xl bg-[#09090b] md:rounded-2xl md:border md:border-[#27272a] overflow-hidden shadow-2xl relative flex flex-col">
                <iframe
                  key={iframeKey}
                  src={activeDyadicUrl}
                  title="Dyadic Ludic Hub"
                  className="w-full h-full flex-1 border-0"
                  allow="autoplay; clipboard-write; vibrate"
                />
              </div>
            </div>
          </div>
        )}

        {/* SUBTAB 2: STEAM GAMING HUB */}
        {activeSection === 'steam' && (
          <div className="h-full w-full">
            <SteamGamingHubTab backendUrl={backendUrl} />
          </div>
        )}

        {/* SUBTAB 3: PROCESS MEMORY LAB & TRAINER */}
        {activeSection === 'trainer' && (
          <div className="h-full w-full">
            <ProcessMemoryLabTab backendUrl={backendUrl} />
          </div>
        )}
      </div>
    </div>
  );
}
