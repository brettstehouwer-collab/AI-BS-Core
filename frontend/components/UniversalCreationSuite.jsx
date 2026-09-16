import React, { useState, Suspense, lazy } from 'react';

// Lazy load the inner tools
const VisualScriptingTab = lazy(() => import('./VisualScriptingTab.jsx'));
const StudioWorkspaceTab = lazy(() => import('./StudioWorkspaceTab.jsx'));
const PlaywrightTab = lazy(() => import('./PlaywrightTab.jsx'));
const VideoStudioTab = lazy(() => import('./VideoStudioTab.jsx'));
const ComfyUIStudio = lazy(() => import('../src/components/ComfyUIStudio.jsx'));

export default function UniversalCreationSuite(props) {
    const [activeTool, setActiveTool] = useState(() => {
        if (typeof window !== 'undefined') {
            const params = new URLSearchParams(window.location.search);
            const sub = params.get('subtab');
            if (['playwright', 'video', 'comfyui', 'visual'].includes(sub)) return sub;
        }
        return 'playwright';
    });
    const [showTips, setShowTips] = useState(false);
    const [copiedToolUrl, setCopiedToolUrl] = useState(false);
    
    // Shared state for Video Studio Prompt
    const [sharedVideoPrompt, setSharedVideoPrompt] = useState('');

    const handleSelectTool = (toolKey) => {
        setActiveTool(toolKey);
        if (typeof window !== 'undefined') {
            const url = new URL(window.location.href);
            url.searchParams.set('subtab', toolKey);
            window.history.replaceState({}, '', url.toString());
        }
    };

    const handleCopyShareUrl = () => {
        const url = `${window.location.origin}${window.location.pathname}?tab=unified_creation&subtab=${activeTool}`;
        navigator.clipboard.writeText(url).then(() => {
            setCopiedToolUrl(true);
            setTimeout(() => setCopiedToolUrl(false), 2500);
        });
    };

    const handleSendToVideoStudio = (text) => {
        setSharedVideoPrompt(text);
        handleSelectTool('video');
    };

    const renderTool = () => {
        switch(activeTool) {
            case 'playwright':
                return <PlaywrightTab {...props} onSendToVideoStudio={handleSendToVideoStudio} />;
            case 'video':
                return <VideoStudioTab {...props} sharedVideoPrompt={sharedVideoPrompt} setSharedVideoPrompt={setSharedVideoPrompt} />;
            case 'visual':
                return <VisualScriptingTab {...props} />;
            case 'comfyui':
                return <ComfyUIStudio {...props} />;
            default:
                return <PlaywrightTab {...props} />;
        }
    };

    return (
        <div style={{ display: 'flex', flexDirection: 'column', height: '100%', width: '100%', background: '#0d1117', flexWrap: 'nowrap', overflow: 'hidden' }}>
            {/* Top Ribbon Navigation for the Suite */}
            {typeof window !== 'undefined' && !window.location.search.includes('standalone_writer=true') && (
            <div style={{
                display: 'flex',
                flexShrink: 0,
                width: '100%',
                boxSizing: 'border-box',
                background: '#161b22',
                borderBottom: '1px solid #30363d',
                padding: '0 20px',
                alignItems: 'center',
                justifyContent: 'space-between',
                height: '50px'
            }}>
                <div style={{ display: 'flex', alignItems: 'center', height: '100%' }}>
                    <div style={{ fontWeight: 'bold', color: '#c9d1d9', marginRight: '24px', fontSize: '1.05rem', letterSpacing: '1px' }}>
                        🌌 CREATION SUITE
                    </div>
                    
                    <div style={{ display: 'flex', gap: '10px', height: '100%' }}>
                        <button 
                            onClick={() => handleSelectTool('playwright')}
                            style={{
                                background: 'transparent',
                                border: 'none',
                                color: activeTool === 'playwright' ? '#58a6ff' : '#8b949e',
                                borderBottom: activeTool === 'playwright' ? '3px solid #58a6ff' : '3px solid transparent',
                                cursor: 'pointer',
                                padding: '0 15px',
                                fontWeight: activeTool === 'playwright' ? 'bold' : 'normal',
                                transition: 'all 0.2s',
                                display: 'flex',
                                alignItems: 'center',
                                gap: '8px'
                            }}>
                            ✍️ Writing Studio
                        </button>
                        
                        <button 
                            onClick={() => handleSelectTool('video')}
                            style={{
                                background: 'transparent',
                                border: 'none',
                                color: activeTool === 'video' ? '#58a6ff' : '#8b949e',
                                borderBottom: activeTool === 'video' ? '3px solid #58a6ff' : '3px solid transparent',
                                cursor: 'pointer',
                                padding: '0 15px',
                                fontWeight: activeTool === 'video' ? 'bold' : 'normal',
                                transition: 'all 0.2s',
                                display: 'flex',
                                alignItems: 'center',
                                gap: '8px'
                            }}>
                            🎥 Video Studio
                        </button>
                        
                        <button 
                            onClick={() => handleSelectTool('comfyui')}
                            style={{
                                background: 'transparent',
                                border: 'none',
                                color: activeTool === 'comfyui' ? '#e040fb' : '#8b949e',
                                borderBottom: activeTool === 'comfyui' ? '3px solid #e040fb' : '3px solid transparent',
                                cursor: 'pointer',
                                padding: '0 15px',
                                fontWeight: activeTool === 'comfyui' ? 'bold' : 'normal',
                                transition: 'all 0.2s',
                                display: 'flex',
                                alignItems: 'center',
                                gap: '8px'
                            }}>
                            🎨 ComfyUI Studio
                        </button>
                        
                        <button 
                            onClick={() => handleSelectTool('visual')}
                            style={{
                                background: 'transparent',
                                border: 'none',
                                color: activeTool === 'visual' ? '#58a6ff' : '#8b949e',
                                borderBottom: activeTool === 'visual' ? '3px solid #58a6ff' : '3px solid transparent',
                                cursor: 'pointer',
                                padding: '0 15px',
                                fontWeight: activeTool === 'visual' ? 'bold' : 'normal',
                                transition: 'all 0.2s',
                                display: 'flex',
                                alignItems: 'center',
                                gap: '8px'
                            }}>
                            👁️ Visual Scripting
                        </button>
                    </div>
                </div>

                {/* Right Guide & Share Actions */}
                <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                    <button
                        onClick={handleCopyShareUrl}
                        title="Copy direct shareable link for this creation sub-tool"
                        style={{
                            background: copiedToolUrl ? '#10b981' : 'rgba(56, 189, 248, 0.12)',
                            color: copiedToolUrl ? '#ffffff' : '#38bdf8',
                            border: `1px solid ${copiedToolUrl ? '#34d399' : '#38bdf8'}`,
                            padding: '4px 10px',
                            borderRadius: '6px',
                            cursor: 'pointer',
                            fontSize: '0.75rem',
                            fontWeight: '700'
                        }}
                    >
                        <span>🔗 {copiedToolUrl ? 'Copied!' : 'Share Sub-Tool'}</span>
                    </button>

                    <button
                        onClick={() => setShowTips(!showTips)}
                        title="Toggle Studio Operating Guide & Keyboard Shortcuts"
                        style={{
                            background: '#21262d',
                            color: '#c9d1d9',
                            border: '1px solid #30363d',
                            padding: '4px 10px',
                            borderRadius: '6px',
                            cursor: 'pointer',
                            fontSize: '0.75rem',
                            fontWeight: '600'
                        }}
                    >
                        <span>💡 {showTips ? 'Hide Tips' : 'Studio Guide'}</span>
                    </button>
                </div>
            </div>
            )}

            {/* In-Tab Guidance Accordion */}
            {showTips && (
                <div style={{
                    background: 'linear-gradient(135deg, rgba(15, 23, 42, 0.98) 0%, rgba(30, 41, 59, 0.95) 100%)',
                    borderBottom: '1px solid rgba(56, 189, 248, 0.35)',
                    borderLeft: '4px solid #38bdf8',
                    padding: '12px 20px',
                    color: '#cbd5e1',
                    fontSize: '0.8rem',
                    display: 'grid',
                    gridTemplateColumns: 'repeat(auto-fit, minmax(240px, 1fr))',
                    gap: '12px'
                }}>
                    <div style={{ background: '#0f172a', padding: '10px 14px', borderRadius: '8px', border: '1px solid #334155' }}>
                        <strong style={{ color: '#f8fafc', display: 'block', marginBottom: '4px' }}>⌨️ Screenplay AST Hotkeys:</strong>
                        <span style={{ color: '#94a3b8' }}>Ctrl+1 (Scene Heading), Ctrl+2 (Action), Ctrl+3 (Character), Ctrl+4 (Dialogue), Ctrl+5 (Parenthetical), Ctrl+6 (Transition).</span>
                    </div>
                    <div style={{ background: '#0f172a', padding: '10px 14px', borderRadius: '8px', border: '1px solid #334155' }}>
                        <strong style={{ color: '#f8fafc', display: 'block', marginBottom: '4px' }}>🔍 AI Page Doctor & !proof:</strong>
                        <span style={{ color: '#94a3b8' }}>Click "Review Pg X" or type "!proof" to run continuous automated formatting correction and character name capitalization.</span>
                    </div>
                    <div style={{ background: '#0f172a', padding: '10px 14px', borderRadius: '8px', border: '1px solid #334155' }}>
                        <strong style={{ color: '#f8fafc', display: 'block', marginBottom: '4px' }}>🎙️ 2h 39m Master Audio:</strong>
                        <span style={{ color: '#94a3b8' }}>Toggle "Audio Drama" to stream Brett Stehouwer's full voice adaptation with synchronized scene timecodes.</span>
                    </div>
                    <div style={{ background: '#0f172a', padding: '10px 14px', borderRadius: '8px', border: '1px solid #334155' }}>
                        <strong style={{ color: '#f8fafc', display: 'block', marginBottom: '4px' }}>🎮 Unreal & Wan2.1 Render:</strong>
                        <span style={{ color: '#94a3b8' }}>Click "Open in Video Studio" to dispatch scene prompts into local RTX 4090 ComfyUI diffusion or Unreal Engine 5.8 3D worlds.</span>
                    </div>
                </div>
            )}

            {/* Main Content Area */}
            <div style={{ flex: 1, width: '100%', minHeight: 0, minWidth: 0, display: 'flex', flexDirection: 'column', overflow: 'hidden', position: 'relative' }}>
                <Suspense fallback={
                    <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'center', height: '100%', color: '#888' }}>
                        Loading Tool...
                    </div>
                }>
                    {renderTool()}
                </Suspense>
            </div>
        </div>
    );
}
