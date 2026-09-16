import React, { useState, useEffect } from 'react';
import { 
  LayoutDashboard, 
  Film, 
  Cloud, 
  Droplets, 
  Calculator, 
  Cpu, 
  Search, 
  Eye, 
  Radio, 
  Settings,
  ChevronLeft,
  ChevronRight,
  Sparkles
} from 'lucide-react';

const NAVIGATION_ITEMS = [
  {
    category: "Core Engine",
    items: [
      { id: "command_center", label: "Command Center", icon: LayoutDashboard },
      { id: "shared_cloud_drive", label: "Shared Drive", icon: Cloud },
      { id: "blueprint_roi", label: "Systems & ROI Blueprint", icon: Calculator },
    ]
  },
  {
    category: "Specialized Hubs",
    items: [
      { id: "screenplay_studio", label: "Hollywood Creation", icon: Film },
      { id: "prestige_mobile_wash", label: "Prestige Wash OS", icon: Droplets },
      { id: "neural_intelligence", label: "Neural IDE & Local LLM", icon: Cpu },
    ]
  }
];

export function ModuleCard({ title, description, badge, onClick }) {
  return (
    <div 
      onClick={onClick}
      className="group relative cursor-pointer rounded-lg border border-border-subtle bg-surface p-5 transition-all duration-200 hover:bg-surface-elevated hover:border-border-active hover:shadow-lg"
    >
      <div className="flex items-start justify-between">
        <h3 className="text-sm font-semibold text-slate-100 group-hover:text-accent-primary transition-colors">
          {title}
        </h3>
        {badge && (
          <span className="font-mono text-[10px] px-2 py-0.5 rounded bg-surface-elevated border border-border-subtle text-slate-400">
            {badge}
          </span>
        )}
      </div>
      <p className="mt-2 text-xs text-slate-400 leading-relaxed">
        {description}
      </p>
    </div>
  );
}

export default function DashboardLayout({ activeTab, setActiveTab, children }) {
  const [sidebarCollapsed, setSidebarCollapsed] = useState(false);
  const [highLegibility, setHighLegibility] = useState(false);

  useEffect(() => {
    if (highLegibility) {
      document.body.classList.add('high-legibility');
    } else {
      document.body.classList.remove('high-legibility');
    }
  }, [highLegibility]);

  return (
    <div className="flex h-screen w-screen overflow-hidden bg-background text-slate-200">
      {/* Left Navigation Sidebar */}
      <aside 
        className={`relative flex flex-col border-r border-border-subtle bg-background-secondary transition-all duration-300 ${
          sidebarCollapsed ? 'w-16' : 'w-64'
        }`}
      >
        {/* Workspace Brand Indicator */}
        <div className="flex h-14 items-center justify-between border-b border-border-subtle px-4">
          {!sidebarCollapsed && (
            <div className="flex items-center gap-2">
              <span className="h-2 w-2 rounded-full bg-accent-primary animate-pulse" />
              <span className="font-semibold tracking-tight text-sm text-slate-100 uppercase">
                AI-BS Matrix
              </span>
            </div>
          )}
          <button 
            onClick={() => setSidebarCollapsed(!sidebarCollapsed)}
            className="p-1 rounded-md text-slate-400 hover:text-slate-100 hover:bg-surface-elevated ml-auto"
            aria-label="Toggle Sidebar"
          >
            {sidebarCollapsed ? <ChevronRight size={16} /> : <ChevronLeft size={16} />}
          </button>
        </div>

        {/* Navigation Groups */}
        <div className="flex-1 overflow-y-auto px-2 py-4 space-y-6">
          {NAVIGATION_ITEMS.map((group, idx) => (
            <div key={idx} className="space-y-1">
              {!sidebarCollapsed && (
                <div className="px-3 pb-1 text-[10px] font-semibold uppercase tracking-wider text-slate-400">
                  {group.category}
                </div>
              )}
              {group.items.map((item) => {
                const Icon = item.icon;
                const isActive = activeTab === item.id;
                return (
                  <button
                    key={item.id}
                    onClick={() => setActiveTab(item.id)}
                    className={`flex w-full items-center gap-3 px-3 py-2 rounded-md text-xs font-medium transition-colors ${
                      isActive 
                        ? 'bg-surface-elevated text-slate-100 border border-border-active' 
                        : 'text-slate-400 hover:text-slate-200 hover:bg-surface'
                    }`}
                    title={sidebarCollapsed ? item.label : undefined}
                  >
                    <Icon size={16} className={isActive ? 'text-accent-primary' : 'text-slate-400'} />
                    {!sidebarCollapsed && <span className="truncate">{item.label}</span>}
                  </button>
                );
              })}
            </div>
          ))}
        </div>

        {/* Sidebar Footer / Telemetry */}
        <div className="border-t border-border-subtle p-3">
          <div className="flex items-center gap-2 rounded-md bg-surface px-2.5 py-1.5 text-[11px] text-slate-400 border border-border-subtle">
            <Radio size={14} className="text-accent-success" />
            {!sidebarCollapsed && (
              <div className="flex flex-col">
                <span className="font-mono text-slate-200">RTX 4090</span>
                <span className="text-[9px] text-slate-400">CUDA Engine Ready</span>
              </div>
            )}
          </div>
        </div>
      </aside>

      {/* Main Execution Viewport */}
      <div className="flex flex-1 flex-col overflow-hidden">
        {/* Top App Bar */}
        <header className="flex h-14 items-center justify-between border-b border-border-subtle px-6 bg-background">
          {/* Command Search Bar Trigger */}
          <div className="flex items-center gap-4 w-1/3">
            <button className="flex w-full items-center justify-between rounded-md border border-border-subtle bg-surface px-3 py-1.5 text-xs text-slate-400 hover:border-border-active">
              <span className="flex items-center gap-2">
                <Search size={14} />
                <span>Search system or execute command...</span>
              </span>
              <kbd className="font-mono text-[10px] bg-surface-elevated px-1.5 py-0.5 rounded border border-border-subtle">
                Ctrl+K
              </kbd>
            </button>
          </div>

          {/* Utility Tools & Mode Switching */}
          <div className="flex items-center gap-3">
            {/* Integrated Accessible / High Legibility Toggle */}
            <button
              onClick={() => setHighLegibility(!highLegibility)}
              className={`flex items-center gap-1.5 px-3 py-1.5 rounded-md text-xs font-medium border transition-colors ${
                highLegibility 
                  ? 'bg-amber-500/10 text-amber-300 border-amber-500/30' 
                  : 'bg-surface text-slate-400 border-border-subtle hover:text-slate-200'
              }`}
            >
              <Eye size={14} />
              <span>Easy View (Mom Mode)</span>
            </button>

            <div className="h-4 w-[1px] bg-border-subtle" />

            {/* User Credentials */}
            <div className="flex items-center gap-2">
              <div className="h-7 w-7 rounded-full bg-surface-elevated border border-border-subtle flex items-center justify-center text-xs font-mono font-medium text-slate-300">
                BA
              </div>
              <span className="text-xs font-medium text-slate-300">Local Admin</span>
            </div>
          </div>
        </header>

        {/* Viewport Content */}
        <main className="flex-1 overflow-y-auto p-6 bg-background">
          <div className="mx-auto max-w-7xl">
            {children}
          </div>
        </main>
      </div>
    </div>
  );
}
