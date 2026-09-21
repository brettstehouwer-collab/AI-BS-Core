import React, { useState, Suspense, lazy } from 'react';

// Lazy load the inner tools
const VisualScriptingTab = lazy(() => import('./VisualScriptingTab.jsx'));
const StudioWorkspaceTab = lazy(() => import('./StudioWorkspaceTab.jsx'));
const PlaywrightTab = lazy(() => import('./PlaywrightTab.jsx'));
const VideoStudioTab = lazy(() => import('./VideoStudioTab.jsx'));
const ComfyUIStudio = lazy(() => import('../src/components/ComfyUIStudio.jsx'));

const AUTHORIZED_EMAILS = [
    'brettstehouwer@gmail.com',
    'footballstar0325@gmail.com',
    'stehouwerjulie@gmail.com',
    'julie.a.stehouwer@gmail.com',
    'julieannstehouwer@gmail.com',
    'juliestehouwer@gmail.com',
    'stehouwer.julie@gmail.com',
    'julie@stehouwer-publishing.com'
];

const JULIE_EMAILS = [
    'stehouwerjulie@gmail.com',
    'julie.a.stehouwer@gmail.com',
    'julieannstehouwer@gmail.com',
    'juliestehouwer@gmail.com',
    'stehouwer.julie@gmail.com',
    'julie@stehouwer-publishing.com'
];

export default function UniversalCreationSuite(props) {
    const { currentUser } = props;

    // Determine if running locally or on local home network (LAN)
    const isLocalDev = typeof window !== 'undefined' && (
        window.location.hostname === 'localhost' ||
        window.location.hostname === '127.0.0.1' ||
        window.location.hostname.startsWith('192.168.') ||
        window.location.hostname.startsWith('10.') ||
        /^172\.(1[6-9]|2[0-9]|3[0-1])\./.test(window.location.hostname) ||
        window.location.protocol === 'file:'
    );

    // Determine current active user email
    const userEmail = (currentUser?.email || '').toLowerCase().trim();

    // Julie Stehouwer has full unrestricted access without any password requirement
    const isJulie = JULIE_EMAILS.includes(userEmail) || userEmail.includes('julie');

    // Allowed operators: Julie, Brett, LocalDev, footballstar0325
    const isAuthorizedOperator = isLocalDev || isJulie || AUTHORIZED_EMAILS.includes(userEmail);

    // Check persistent authorization or session unlock (Julie is ALWAYS unlocked with zero password prompt)
    const [isUnlocked, setIsUnlocked] = useState(() => {
        if (isJulie) return true;
        if (typeof window !== 'undefined') {
            return sessionStorage.getItem('aibs_universal_creation_unlocked') === 'true';
        }
        return false;
    });

    const [enteredPassword, setEnteredPassword] = useState('');
    const [passwordError, setPasswordError] = useState('');

    const handlePasswordUnlock = (e) => {
        e?.preventDefault();
        setPasswordError('');
        if (!enteredPassword.trim()) {
            setPasswordError('Please enter the creation suite security password.');
            return;
        }

        if (enteredPassword.trim() === 'jssdbdAS2631') {
            setIsUnlocked(true);
            if (typeof window !== 'undefined') {
                sessionStorage.setItem('aibs_universal_creation_unlocked', 'true');
            }
        } else {
            setPasswordError('Invalid security password. Access denied.');
        }
    };

    const handleLockVault = () => {
        setIsUnlocked(false);
        setEnteredPassword('');
        setPasswordError('');
        if (typeof window !== 'undefined') {
            sessionStorage.removeItem('aibs_universal_creation_unlocked');
        }
    };

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

    // Security Barrier 1: Email / LocalDev Identity Enforcement
    if (!isAuthorizedOperator) {
        return (
            <div style={{
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'center',
                minHeight: '80vh',
                padding: '32px 16px',
                background: '#0d1117',
                fontFamily: 'Inter, system-ui, sans-serif'
            }}>
                <div style={{
                    background: '#161b22',
                    border: '1px solid rgba(239, 68, 68, 0.4)',
                    borderRadius: '16px',
                    padding: '40px 32px',
                    maxWidth: '520px',
                    width: '100%',
                    textAlign: 'center',
                    boxShadow: '0 20px 45px rgba(0,0,0,0.7)'
                }}>
                    <div style={{ fontSize: '48px', marginBottom: '16px' }}>🔒</div>
                    <h2 style={{ color: '#ef4444', fontSize: '24px', fontWeight: '800', margin: '0 0 12px 0' }}>
                        Restricted Studio Access
                    </h2>
                    <p style={{ color: '#8b949e', fontSize: '14px', lineHeight: '1.6', margin: '0 0 24px 0' }}>
                        The Universal Creation & Screenwriting Studio is strictly restricted to authorized operators:
                    </p>
                    <div style={{ display: 'flex', flexDirection: 'column', gap: '8px', marginBottom: '24px' }}>
                        <span style={{ background: '#0d1117', border: '1px solid #30363d', borderRadius: '8px', padding: '8px 14px', fontSize: '13px', color: '#c9d1d9', fontWeight: '600' }}>
                            👤 Brettstehouwer@gmail.com
                        </span>
                        <span style={{ background: '#0d1117', border: '1px solid #30363d', borderRadius: '8px', padding: '8px 14px', fontSize: '13px', color: '#38bdf8', fontWeight: '600' }}>
                            ⚡ LocalDev (localhost / 127.0.0.1)
                        </span>
                        <span style={{ background: '#0d1117', border: '1px solid #30363d', borderRadius: '8px', padding: '8px 14px', fontSize: '13px', color: '#c9d1d9', fontWeight: '600' }}>
                            👤 footballstar0325@gmail.com
                        </span>
                    </div>
                    <div style={{ background: 'rgba(239, 68, 68, 0.1)', border: '1px solid rgba(239, 68, 68, 0.3)', borderRadius: '8px', padding: '10px 14px', fontSize: '12px', color: '#fca5a5' }}>
                        Current Operator Identity: <strong>{userEmail || 'Unauthenticated Guest'}</strong>
                    </div>
                </div>
            </div>
        );
    }

    // Security Barrier 2: Password Challenge
    if (!isUnlocked) {
        return (
            <div style={{
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'center',
                minHeight: '80vh',
                padding: '32px 16px',
                background: '#0d1117',
                fontFamily: 'Inter, system-ui, sans-serif'
            }}>
                <div style={{
                    background: '#161b22',
                    border: '1px solid rgba(56, 189, 248, 0.35)',
                    borderRadius: '16px',
                    padding: '40px 32px',
                    maxWidth: '520px',
                    width: '100%',
                    textAlign: 'center',
                    boxShadow: '0 20px 45px rgba(0,0,0,0.7)'
                }}>
                    <div style={{ fontSize: '48px', marginBottom: '16px' }}>🔐</div>
                    <h2 style={{ color: '#38bdf8', fontSize: '24px', fontWeight: '800', margin: '0 0 12px 0' }}>
                        Universal Creation Suite — Password Required
                    </h2>
                    <p style={{ color: '#8b949e', fontSize: '14px', lineHeight: '1.6', margin: '0 0 24px 0' }}>
                        Identity Verified: <span style={{ color: '#38bdf8', fontWeight: '700' }}>{isLocalDev ? 'LocalDev' : userEmail}</span>. Enter the master security password to unlock the studio workspace.
                    </p>
                    <form onSubmit={handlePasswordUnlock} style={{ display: 'flex', flexDirection: 'column', gap: '14px' }}>
                        <div style={{ display: 'flex', gap: '8px' }}>
                            <input
                                type="password"
                                placeholder="Enter Vault Password"
                                value={enteredPassword}
                                onChange={(e) => setEnteredPassword(e.target.value)}
                                autoFocus
                                style={{
                                    flex: 1,
                                    background: '#0d1117',
                                    border: '1px solid #30363d',
                                    borderRadius: '8px',
                                    padding: '12px 16px',
                                    color: '#fff',
                                    fontSize: '14px',
                                    outline: 'none'
                                }}
                            />
                            <button
                                type="submit"
                                style={{
                                    background: 'linear-gradient(135deg, #1f6feb 0%, #38bdf8 100%)',
                                    color: '#fff',
                                    border: 'none',
                                    borderRadius: '8px',
                                    padding: '12px 20px',
                                    fontWeight: '700',
                                    fontSize: '14px',
                                    cursor: 'pointer',
                                    whiteSpace: 'nowrap'
                                }}
                            >
                                Unlock Studio 🔓
                            </button>
                        </div>
                        {passwordError && (
                            <div style={{ background: 'rgba(239, 68, 68, 0.15)', border: '1px solid rgba(239, 68, 68, 0.4)', borderRadius: '8px', padding: '10px 14px', fontSize: '13px', color: '#f87171', textAlign: 'left' }}>
                                ⚠️ {passwordError}
                            </div>
                        )}
                    </form>
                </div>
            </div>
        );
    }

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

                    <button
                        onClick={handleLockVault}
                        title="Lock Studio (Requires password to re-enter)"
                        style={{
                            background: '#21262d',
                            color: '#f85149',
                            border: '1px solid rgba(248, 81, 73, 0.4)',
                            padding: '4px 10px',
                            borderRadius: '6px',
                            cursor: 'pointer',
                            fontSize: '0.75rem',
                            fontWeight: '600',
                            display: 'flex',
                            alignItems: 'center',
                            gap: '4px'
                        }}
                    >
                        <span>🔒 Lock Studio</span>
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
