import React, { useState, useEffect } from 'react';
import VLCPreviewMonitor from './VLCPreviewMonitor';

export default function VideoStudioTab({ BACKEND_URL, backendUrl, sharedVideoPrompt, setSharedVideoPrompt }) {
    const activeBackend = backendUrl || BACKEND_URL || 'http://localhost:8080';
    const [videoPath, setVideoPath] = useState('C:\\AI-BS\\screenplay_projects\\Echoes_Within\\generated_scene_research_complex.mp4');
    const [streamUrl, setStreamUrl] = useState('');
    const [isStreaming, setIsStreaming] = useState(false);
    
    // Scene Generation State
    const [scenePrompt, setScenePrompt] = useState(
        "INT. SUB-LEVEL 4 RESEARCH COMPLEX - DAY\nThe emergency alarms pierce the air, echoing off the metallic walls. Dr. Aris Vance bursts through the heavy blast doors, clutching an encrypted datapad to his chest.\nMAYA (O.S.)\nThey're inside the mainframe!\nAris rushes towards Maya, who frantically works on the quantum console.\nARIS (urgently)\nHow much time do we have?\nMAYA (glancing at the console)\nTwo minutes before the automated defense turrets activate.\nAris inserts an override key into a nearby console. Sparks erupt from the overhead conduit as the elevator cable snaps with a deafening CRACK."
    );
    const [isGenerating, setIsGenerating] = useState(false);
    const [generationLogs, setGenerationLogs] = useState([]);
    const [generationEngine, setGenerationEngine] = useState("comfyui"); // "comfyui", "diffusers", "unreal"
    const [videoStyle, setVideoStyle] = useState("cinematic");
    const [isBatchMode, setIsBatchMode] = useState(false);
    const [activeJobId, setActiveJobId] = useState(null);

    // Recent generated scenes list
    const [recentClips, setRecentClips] = useState([
        {
            title: "Dr. Aris Vance Sub-Level 4 Research Complex",
            path: "C:\\AI-BS\\screenplay_projects\\Echoes_Within\\generated_scene_research_complex.mp4",
            style: "Cinematic 8K",
            engine: "Wan2.1"
        },
        {
            title: "🎮 Unreal Engine 5 Scene Constructor Script",
            path: "C:\\AI-BS\\AI-BS_Modual_Video_Editing\\Screen Recordings\\generated_unreal_467d7dff.py",
            style: "Python Level Script",
            engine: "UE5 Bridge"
        },
        {
            title: "Heaven & Hell Contrast Scene (Candy Store & Furnace)",
            path: "C:\\AI-BS\\screenplay_projects\\Echoes_Within\\generated_scene_heaven_hell.mp4",
            style: "Cinematic 8K",
            engine: "Wan2.1"
        },
        {
            title: "Weebles Wobble Candy Store (Fredy, Satin & Jesus)",
            path: "C:\\AI-BS\\screenplay_projects\\Echoes_Within\\generated_scene_candy_store.mp4",
            style: "Cinematic 8K",
            engine: "Wan2.1"
        },
        {
            title: "Young Brett & Mike Patrick Kitchen Scene",
            path: "C:\\AI-BS\\screenplay_projects\\Echoes_Within\\generated_scene_kitchen.mp4",
            style: "Cinematic 8K",
            engine: "Wan2.1"
        }
    ]);

    const STYLE_MODIFIERS = {
        "none": "",
        "cinematic": "Hyper-realistic cinematic film, 8k resolution, photorealistic, shot on ARRI Alexa, cinematic lighting. ",
        "3d": "High quality 3D animation, Pixar style, Unreal Engine 5 render, vibrant colors, soft lighting. ",
        "anime": "Studio Ghibli style, 2D anime animation, flat shading, beautifully hand-drawn. ",
        "claymation": "Aardman style claymation, stop-motion animation, tactile clay textures, studio miniature lighting. ",
        "vintage": "1970s vintage film aesthetic, 35mm film grain, slightly desaturated, light leaks. "
    };

    useEffect(() => {
        if (sharedVideoPrompt) {
            setScenePrompt(sharedVideoPrompt);
        }
    }, [sharedVideoPrompt]);

    const handleStartStream = async () => {
        if (!videoPath) {
            alert("Please provide a video path.");
            return;
        }
        setIsStreaming(true);
        try {
            const res = await fetch(`${activeBackend}/api/video/start_stream`, {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({ video_path: videoPath })
            });
            const data = await res.json();
            if (data.status === "success") {
                setStreamUrl(`${activeBackend}${data.stream_url}`);
            } else {
                alert(`Error starting stream: ${data.detail || data.message}`);
                setIsStreaming(false);
            }
        } catch (e) {
            console.error("Direct play fallback:", e);
            setStreamUrl(`${activeBackend}/api/video/stream?path=${encodeURIComponent(videoPath)}`);
        } finally {
            setIsStreaming(false);
        }
    };

    // Polling effect for batch mode
    useEffect(() => {
        let interval;
        if (activeJobId && isGenerating) {
            interval = setInterval(async () => {
                try {
                    const res = await fetch(`${activeBackend}/api/video/batch_status/${activeJobId}`);
                    if (res.ok) {
                        const data = await res.json();
                        setGenerationLogs(prev => {
                            const last = prev[prev.length - 1];
                            const msg = `[BATCH STATUS] ${data.message} (${data.current}/${data.total})`;
                            if (last === msg) return prev;
                            return [...prev, msg];
                        });
                        
                        if (data.status === "done") {
                            setIsGenerating(false);
                            setActiveJobId(null);
                            if (data.final_path) {
                                setVideoPath(data.final_path);
                                setStreamUrl(`${activeBackend}/api/video/stream?path=${encodeURIComponent(data.final_path)}`);
                                setRecentClips(prev => [{ title: `Batch Output (${data.final_path.split('\\').pop()})`, path: data.final_path, style: videoStyle, engine: generationEngine }, ...prev]);
                            }
                        } else if (data.status === "error") {
                            setIsGenerating(false);
                            setActiveJobId(null);
                            setGenerationLogs(prev => [...prev, "❌ [SYSTEM] Batch processing encountered an error."]);
                        }
                    }
                } catch (e) {
                    console.error("Polling error:", e);
                }
            }, 4000);
        }
        return () => clearInterval(interval);
    }, [activeJobId, isGenerating, activeBackend]);

    const handleGenerateScene = async () => {
        if (!scenePrompt) return;
        setIsGenerating(true);
        
        const finalPrompt = STYLE_MODIFIERS[videoStyle] + scenePrompt;
        setGenerationLogs([
            `[INIT] Starting scene generation for: "${finalPrompt}"`,
            `[GPU] Allocating NVIDIA GeForce RTX 4090 with Wan2.1 diffusion model...`
        ]);
        
        try {
            if (isBatchMode) {
                setGenerationLogs(prev => [...prev, `[SYSTEM] Submitting Batch Job via ${generationEngine}...`]);
                const response = await fetch(`${activeBackend}/api/video/batch_pipeline`, {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ prompt: finalPrompt, engine: generationEngine })
                });
                
                const data = await response.json();
                if (data.status === "accepted") {
                    setActiveJobId(data.job_id);
                    setGenerationLogs(prev => [...prev, `[SYSTEM] Batch Job Accepted. ID: ${data.job_id}. Processing in background...`]);
                } else {
                    throw new Error("Failed to start batch job.");
                }
                
            } else {
                setGenerationLogs(prev => [...prev, `[SYSTEM] Dispatching job to ComfyUI Wan2.1 engine on port 8189...`]);
                const response = await fetch(`${activeBackend}/api/video/test_pipeline`, {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ prompt: finalPrompt, engine: generationEngine })
                });

                const data = await response.json();
                
                if (response.ok && data.status === "success") {
                    const newLogs = data.output ? data.output.split('\n') : ["✅ Scene generation completed successfully!"];
                    setGenerationLogs(prev => [...prev, ...newLogs]);
                    
                    if (data.video_path) {
                        setVideoPath(data.video_path);
                        setStreamUrl(`${activeBackend}${data.stream_url}`);
                        setRecentClips(prev => [{ title: `Scene: ${scenePrompt.slice(0, 35)}...`, path: data.video_path, style: videoStyle, engine: generationEngine }, ...prev]);
                    }
                } else {
                    setGenerationLogs(prev => [...prev, `❌ [ERROR] Pipeline execution failed:\n${data.message || data.error || 'Unknown error'}`]);
                }
            }
        } catch (error) {
            setGenerationLogs(prev => [...prev, `❌ [ERROR] Connection failed: ${error.message}`]);
        } finally {
            setIsGenerating(false);
        }
    };

    return (
        <div className="video-studio-container" style={{ display: 'flex', flexDirection: 'column', gap: '20px', padding: '20px', color: '#e0e0e0', height: '100%', overflowY: 'auto' }}>
            {/* Header */}
            <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', borderBottom: '1px solid #1e293b', paddingBottom: '12px' }}>
                <h2 style={{ margin: 0, color: '#38bdf8', display: 'flex', alignItems: 'center', gap: '8px' }}>
                    <span>🎥</span> AI-BS Video Studio & Wan2.1 Cinematic Renderer
                </h2>
                <div style={{ display: 'flex', gap: '10px', alignItems: 'center' }}>
                    <span style={{ fontSize: '0.8rem', background: '#065f46', color: '#6ee7b7', padding: '3px 10px', borderRadius: '4px', border: '1px solid #059669' }}>
                        ⚡ RTX 4090 (24GB VRAM)
                    </span>
                    <span style={{ fontSize: '0.8rem', background: '#1e3a8a', color: '#93c5fd', padding: '3px 10px', borderRadius: '4px', border: '1px solid #3b82f6' }}>
                        ComfyUI Port 8189 (Online)
                    </span>
                </div>
            </div>
            
            <div style={{ display: 'flex', gap: '20px', flex: 1, minHeight: 0, flexWrap: 'wrap' }}>
                {/* Left Column: Controls & Generation */}
                <div style={{ flex: 1, minWidth: '380px', display: 'flex', flexDirection: 'column', gap: '16px', backgroundColor: '#0f172a', padding: '20px', borderRadius: '12px', border: '1px solid #1e293b' }}>
                    
                    {/* Scene Generator */}
                    <div className="control-group" style={{ display: 'flex', flexDirection: 'column', gap: '10px' }}>
                        <h3 style={{ margin: 0, color: '#f8fafc', fontSize: '1rem', display: 'flex', alignItems: 'center', gap: '6px' }}>
                            <span>🎬</span> AI Scene Prompt
                        </h3>
                        <textarea 
                            placeholder="Describe the scene you want to generate (e.g. 'Young Brett is sitting at the kitchen table...')..."
                            value={scenePrompt}
                            onChange={(e) => {
                                setScenePrompt(e.target.value);
                                if (setSharedVideoPrompt) setSharedVideoPrompt(e.target.value);
                            }}
                            rows={5}
                            style={{
                                width: '100%',
                                padding: '12px',
                                backgroundColor: '#070b14',
                                border: '1px solid #334155',
                                color: '#f1f5f9',
                                borderRadius: '6px',
                                resize: 'vertical',
                                fontSize: '0.85rem',
                                lineHeight: 1.5
                            }}
                        />
                        
                        <div style={{ display: 'flex', gap: '10px', alignItems: 'center' }}>
                            <select 
                                value={generationEngine} 
                                onChange={(e) => setGenerationEngine(e.target.value)}
                                style={{ flex: 1, backgroundColor: '#070b14', border: '1px solid #334155', color: '#38bdf8', borderRadius: '6px', padding: '8px 10px', fontSize: '0.8rem' }}
                            >
                                <option value="comfyui">Engine: ComfyUI (Wan 2.2 / 2.1 Local RTX 4090)</option>
                                <option value="wan_dancer">Engine: Wan-Dancer-14B (Audio-to-Motion)</option>
                                <option value="wansong">Engine: WanSong (Audio & Music Sync)</option>
                                <option value="wan_streamer">Engine: Wan-Streamer (Real-Time Interactive)</option>
                                <option value="wan3_spec">Engine: Wan 3.0 Multimodal (30s 1080p Doc Ingest)</option>
                                <option value="diffusers">Engine: Diffusers (CogVideoX Script)</option>
                                <option value="unreal">Engine: Unreal Engine (Python Script)</option>
                            </select>

                            <select 
                                value={videoStyle} 
                                onChange={(e) => setVideoStyle(e.target.value)}
                                style={{ flex: 1, backgroundColor: '#070b14', border: '1px solid #334155', color: '#a78bfa', borderRadius: '6px', padding: '8px 10px', fontSize: '0.8rem' }}
                            >
                                <option value="none">Style: None (Raw Prompt)</option>
                                <option value="cinematic">Style: Cinematic / Hyper-Realistic</option>
                                <option value="3d">Style: 3D Animation (Pixar/Disney)</option>
                                <option value="anime">Style: 2D Anime (Studio Ghibli)</option>
                                <option value="claymation">Style: Claymation / Stop-Motion</option>
                                <option value="vintage">Style: Vintage 70s Film</option>
                            </select>
                        </div>

                        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginTop: '4px' }}>
                            <label style={{ display: 'flex', alignItems: 'center', gap: '8px', color: '#94a3b8', fontSize: '0.85rem', cursor: 'pointer' }}>
                                <input 
                                    type="checkbox" 
                                    checked={isBatchMode} 
                                    onChange={(e) => setIsBatchMode(e.target.checked)} 
                                />
                                Auto-Batch Multi-Scene Script
                            </label>
                            
                            <button 
                                onClick={handleGenerateScene}
                                disabled={isGenerating || !scenePrompt.trim()}
                                style={{
                                    padding: '10px 20px',
                                    backgroundColor: isGenerating ? '#312e81' : '#2563eb',
                                    color: '#fff',
                                    border: 'none',
                                    borderRadius: '6px',
                                    cursor: isGenerating ? 'not-allowed' : 'pointer',
                                    fontWeight: 'bold',
                                    fontSize: '0.85rem',
                                    display: 'flex',
                                    alignItems: 'center',
                                    gap: '8px',
                                    boxShadow: '0 2px 10px rgba(37, 99, 235, 0.4)'
                                }}
                            >
                                {isGenerating ? (
                                    <>
                                        <span style={{ animation: 'spin 1s linear infinite' }}>⏳</span>
                                        <span>Generating with Wan2.1...</span>
                                    </>
                                ) : (
                                    <>
                                        <span>🚀</span>
                                        <span>{isBatchMode ? "Start Batch Processing" : "Generate Scene"}</span>
                                    </>
                                )}
                            </button>
                        </div>

                        {/* Generation Logs Console */}
                        <div style={{ marginTop: '10px' }}>
                            <div style={{ fontSize: '0.75rem', color: '#64748b', marginBottom: '4px', fontWeight: 'bold' }}>
                                💻 EXECUTION TELEMETRY LOGS
                            </div>
                            <div style={{
                                padding: '12px',
                                backgroundColor: '#070b14',
                                border: '1px solid #1e293b',
                                borderRadius: '6px',
                                minHeight: '140px',
                                maxHeight: '200px',
                                overflowY: 'auto',
                                fontFamily: 'monospace',
                                fontSize: '0.8rem'
                            }}>
                                {generationLogs.length === 0 && (
                                    <div style={{ color: '#475569' }}>
                                        Ready. Click "Generate Scene" to dispatch this scene to the Wan2.1 GPU pipeline.
                                    </div>
                                )}
                                {generationLogs.map((log, i) => (
                                    <div 
                                        key={i} 
                                        style={{ 
                                            color: log.includes('❌') || log.includes('[ERROR]') ? '#f87171' : log.includes('✅') || log.includes('[SUCCESS]') ? '#4ade80' : log.includes('🚀') || log.includes('[GPU]') ? '#38bdf8' : '#94a3b8',
                                            marginBottom: '3px',
                                            whiteSpace: 'pre-wrap'
                                        }}
                                    >
                                        {log}
                                    </div>
                                ))}
                            </div>
                        </div>
                    </div>

                    <hr style={{ borderColor: '#1e293b', margin: '6px 0' }} />

                    {/* Stream Controller */}
                    <div className="control-group">
                        <h4 style={{ margin: '0 0 6px 0', color: '#94a3b8', fontSize: '0.85rem' }}>
                            📁 Manual Video File Stream Path
                        </h4>
                        <div style={{ display: 'flex', gap: '8px' }}>
                            <input 
                                type="text" 
                                placeholder="C:\AI-BS\screenplay_projects\Echoes_Within\video.mp4" 
                                value={videoPath} 
                                onChange={(e) => setVideoPath(e.target.value)}
                                style={{ flex: 1, padding: '8px 10px', backgroundColor: '#070b14', border: '1px solid #334155', color: '#fff', borderRadius: '4px', fontSize: '0.8rem' }}
                            />
                            <button 
                                onClick={handleStartStream}
                                disabled={isStreaming}
                                style={{ padding: '8px 14px', backgroundColor: '#047857', color: '#fff', border: 'none', borderRadius: '4px', cursor: 'pointer', fontWeight: 'bold', fontSize: '0.8rem' }}
                            >
                                {isStreaming ? "Loading..." : "Load & Play"}
                            </button>
                        </div>
                    </div>
                </div>

                {/* Right Column: Preview Monitor & Recent Clips */}
                <div style={{ flex: 1.4, minWidth: '400px', display: 'flex', flexDirection: 'column', gap: '16px' }}>
                    <VLCPreviewMonitor 
                        videoPath={videoPath} 
                        streamUrl={streamUrl}
                        backendUrl={activeBackend}
                        title={recentClips.length > 0 ? recentClips[0].title : "AI-BS Cinematic Video Preview"}
                    />

                    {/* Recent Generated Scenes Shelf */}
                    <div style={{
                        background: '#0f172a',
                        border: '1px solid #1e293b',
                        borderRadius: '10px',
                        padding: '14px 18px'
                    }}>
                        <h4 style={{ margin: '0 0 10px 0', fontSize: '0.85rem', color: '#94a3b8', display: 'flex', alignItems: 'center', gap: '6px' }}>
                            <span>🎞️</span> Generated Scene Clips
                        </h4>
                        <div style={{ display: 'flex', flexDirection: 'column', gap: '8px' }}>
                            {recentClips.map((clip, idx) => (
                                <div 
                                    key={idx}
                                    style={{
                                        display: 'flex',
                                        alignItems: 'center',
                                        justifyContent: 'space-between',
                                        background: '#070b14',
                                        border: '1px solid #1e293b',
                                        borderRadius: '6px',
                                        padding: '8px 12px'
                                    }}
                                >
                                    <div style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
                                        <span style={{ fontSize: '1.2rem' }}>🎥</span>
                                        <div>
                                            <div style={{ fontWeight: 'bold', fontSize: '0.8rem', color: '#e2e8f0' }}>{clip.title}</div>
                                            <div style={{ fontSize: '0.7rem', color: '#64748b' }}>{clip.engine} • {clip.style}</div>
                                        </div>
                                    </div>
                                    <button
                                        onClick={() => {
                                            setVideoPath(clip.path);
                                            setStreamUrl(`${activeBackend}/api/video/stream?path=${encodeURIComponent(clip.path)}`);
                                        }}
                                        style={{
                                            background: '#2563eb',
                                            color: '#fff',
                                            border: 'none',
                                            borderRadius: '4px',
                                            padding: '4px 10px',
                                            fontSize: '0.75rem',
                                            cursor: 'pointer'
                                        }}
                                    >
                                        ▶ Load into Monitor
                                    </button>
                                </div>
                            ))}
                        </div>
                    </div>
                </div>
            </div>
        </div>
    );
}
