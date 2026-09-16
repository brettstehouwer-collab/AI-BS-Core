import React, { useState, useEffect } from 'react';

export default function ComfyUIStudio({ backendUrl = 'http://127.0.0.1:8000' }) {
  const [workflows, setWorkflows] = useState([]);
  const [selectedWorkflow, setSelectedWorkflow] = useState('');
  
  // Script / Scenes state
  const [scenes, setScenes] = useState([
    { prompt: 'Futuristic Weeble Wobble, 8k ultra detailed', duration: 5 }
  ]);
  
  const [baseImage, setBaseImage] = useState(null);
  const [isGenerating, setIsGenerating] = useState(false);
  const [status, setStatus] = useState('Idle');
  const [generatedMedia, setGeneratedMedia] = useState(null);
  
  // Global Chunk Duration
  const [chunkDuration, setChunkDuration] = useState(5);

  // Fetch available workflows on load
  useEffect(() => {
    fetch(`${backendUrl}/api/comfyui/workflows`)
      .then(res => res.json())
      .then(data => {
        if (data.workflows && data.workflows.length > 0) {
          setWorkflows(data.workflows);
          setSelectedWorkflow(data.workflows[0]);
        }
      })
      .catch(err => console.error('Failed to fetch workflows', err));
  }, [backendUrl]);

  const addScene = () => {
    setScenes([...scenes, { prompt: '', duration: 5 }]);
  };

  const removeScene = (index) => {
    if (scenes.length <= 1) return;
    const newScenes = [...scenes];
    newScenes.splice(index, 1);
    setScenes(newScenes);
  };

  const updateScene = (index, field, value) => {
    const newScenes = [...scenes];
    newScenes[index][field] = value;
    setScenes(newScenes);
  };

  const handleScriptUpload = (e) => {
    const file = e.target.files[0];
    if (!file) return;

    const reader = new FileReader();
    reader.onload = (event) => {
      const text = event.target.result;
      const lines = text.split('\n');
      
      const hollywoodKeywords = /^(INT\.|EXT\.|CUT TO:|FADE TO:|FADE IN:|TRANSITION TO:|DISSOLVE TO:)/i;
      
      const calculateDuration = (text) => {
        const wordCount = text.trim().split(/\s+/).filter(w => w.length > 0).length;
        // Industry standard: 130 words = 60 seconds
        let seconds = Math.round((wordCount / 130) * 60);
        if (seconds < 2) seconds = 2; // Minimum 2 seconds
        if (seconds > 60) seconds = 60;
        return seconds;
      };

      const parsedScenes = [];
      let currentSceneText = "";

      for (let line of lines) {
        if (hollywoodKeywords.test(line.trim())) {
          if (currentSceneText.trim()) {
            parsedScenes.push({ prompt: currentSceneText.trim(), duration: calculateDuration(currentSceneText) });
          }
          currentSceneText = line + "\n";
        } else {
          currentSceneText += line + "\n";
        }
      }
      if (currentSceneText.trim()) {
        parsedScenes.push({ prompt: currentSceneText.trim(), duration: calculateDuration(currentSceneText) });
      }

      if (parsedScenes.length > 0) {
        setScenes(parsedScenes);
        setStatus(`Successfully parsed ${parsedScenes.length} scenes from script.`);
      } else {
        setStatus(`Could not find any Hollywood standard scene keywords (INT., EXT., CUT TO:, etc) in script.`);
      }
    };
    reader.readAsText(file);
    e.target.value = null; // reset input
  };


  const handleGenerate = async (e) => {
    e.preventDefault();
    if (!selectedWorkflow || scenes.some(s => !s.prompt.trim())) return;
    
    setIsGenerating(true);
    setStatus('Queuing to ComfyUI GPU...');
    setGeneratedMedia(null);

    try {
      let baseImageFilename = null;
      if (baseImage) {
        setStatus('Uploading Reference Image...');
        const formData = new FormData();
        formData.append('image', baseImage);
        
        const uploadRes = await fetch(`${backendUrl}/api/comfyui/upload`, {
          method: 'POST',
          body: formData
        });
        
        if (!uploadRes.ok) throw new Error('Failed to upload reference image');
        const uploadData = await uploadRes.json();
        baseImageFilename = uploadData.name;
      }

      setStatus('Queuing script workflow to ComfyUI GPU...');
      
      const reqBody = { 
        workflow_filename: selectedWorkflow, 
        scenes: scenes.map(s => ({
            prompt_text: s.prompt,
            target_duration_sec: parseFloat(s.duration)
        })),
        chunk_duration_sec: parseFloat(chunkDuration)
      };
      if (baseImageFilename) reqBody.base_image = baseImageFilename;

      const endpoint = '/api/comfyui/generate_script';

      const res = await fetch(`${backendUrl}${endpoint}`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(reqBody)
      });
      
      if (!res.ok) throw new Error('Failed to queue script workflow');
      
      const data = await res.json();
      const promptId = data.prompt_id;
      
      // Poll for completion
      pollStatus(promptId);
    } catch (err) {
      console.error(err);
      setStatus('Error connecting to backend');
      setIsGenerating(false);
    }
  };

  const pollStatus = (promptId) => {
    setStatus('Rendering on GPU... (This may take a while)');
    const interval = setInterval(async () => {
      try {
        const res = await fetch(`${backendUrl}/api/comfyui/status/${promptId}`);
        const data = await res.json();
        
        if (data.status === 'completed' && data.outputs && data.outputs.length > 0) {
          clearInterval(interval);
          setStatus('Generation Complete! ✅');
          setIsGenerating(false);
          // Assuming the first output is what we want
          const output = data.outputs[0];
          setGeneratedMedia(`${backendUrl}/api/comfyui/view?filename=${output.filename}&subfolder=${output.subfolder}&folder_type=${output.type}`);
        } else if (data.status === 'error') {
          clearInterval(interval);
          setStatus(`Generation Failed: ${data.error || 'Unknown error'}`);
          setIsGenerating(false);
        }
      } catch (err) {
        console.error('Polling error', err);
      }
    }, 3000);
  };

  const totalDuration = scenes.reduce((sum, s) => sum + parseFloat(s.duration || 0), 0);

  return (
    <div style={{
      backgroundColor: '#0d1117',
      border: '1px solid #30363d',
      borderRadius: '8px',
      padding: '20px',
      color: '#c9d1d9',
      fontFamily: 'Inter, sans-serif'
    }}>
      <h2 style={{ color: '#e040fb', marginTop: 0 }}>🎨 Script to Video Studio</h2>
      <p style={{ color: '#8b949e', fontSize: '14px', marginBottom: '20px' }}>
        Chain multiple prompts sequentially to generate complete video scripts.
      </p>

      <form onSubmit={handleGenerate} style={{ display: 'flex', flexDirection: 'column', gap: '15px' }}>
        <div>
          <label style={{ display: 'block', marginBottom: '5px', fontSize: '13px' }}>Select Workflow Architecture:</label>
          <select 
            value={selectedWorkflow} 
            onChange={(e) => setSelectedWorkflow(e.target.value)}
            style={{
              width: '100%',
              backgroundColor: '#161b22',
              border: '1px solid #30363d',
              color: '#fff',
              padding: '10px',
              borderRadius: '4px'
            }}
          >
            {workflows.map(wf => (
              <option key={wf} value={wf}>{wf}</option>
            ))}
            {workflows.length === 0 && <option value="">No workflows found in backend/comfyui_workflows</option>}
          </select>
        </div>

        <div>
          <label style={{ display: 'block', marginBottom: '5px', fontSize: '13px' }}>Base Reference Image (Optional):</label>
          <input 
            type="file" 
            accept="image/*"
            onChange={(e) => setBaseImage(e.target.files[0])}
            style={{
              width: '100%',
              backgroundColor: '#161b22',
              border: '1px solid #30363d',
              color: '#fff',
              padding: '10px',
              borderRadius: '4px'
            }}
          />
        </div>

        <div style={{ borderTop: '1px solid #30363d', paddingTop: '15px' }}>
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '10px' }}>
            <h3 style={{ fontSize: '15px', color: '#fff', margin: 0 }}>Scenes</h3>
            <div>
                <input 
                    type="file" 
                    accept=".md,.txt,.fdx" 
                    onChange={handleScriptUpload} 
                    id="scriptUpload"
                    style={{ display: 'none' }}
                />
                <label 
                    htmlFor="scriptUpload" 
                    style={{
                        backgroundColor: '#238636',
                        color: '#fff',
                        padding: '6px 12px',
                        borderRadius: '4px',
                        cursor: 'pointer',
                        fontSize: '13px',
                        fontWeight: 'bold',
                        border: '1px solid rgba(240, 246, 252, 0.1)'
                    }}
                >
                    m Upload Markdown/FDX Script
                </label>
            </div>
          </div>
          
          {scenes.map((scene, index) => (
            <div key={index} style={{
                backgroundColor: '#161b22',
                border: '1px solid #30363d',
                borderRadius: '6px',
                padding: '15px',
                marginBottom: '15px',
                position: 'relative'
            }}>
                <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: '10px' }}>
                    <span style={{ fontWeight: 'bold', color: '#a855f7' }}>Scene {index + 1}</span>
                    {scenes.length > 1 && (
                        <button 
                            type="button" 
                            onClick={() => removeScene(index)}
                            style={{ background: 'transparent', border: 'none', color: '#f85149', cursor: 'pointer' }}
                        >
                            ✖ Remove
                        </button>
                    )}
                </div>

                <label style={{ display: 'block', marginBottom: '5px', fontSize: '13px' }}>Scene Prompt:</label>
                <textarea
                    value={scene.prompt}
                    onChange={(e) => updateScene(index, 'prompt', e.target.value)}
                    rows={3}
                    style={{
                    width: '100%',
                    backgroundColor: '#0d1117',
                    border: '1px solid #30363d',
                    color: '#fff',
                    padding: '10px',
                    borderRadius: '4px',
                    resize: 'vertical',
                    marginBottom: '10px'
                    }}
                />

                <label style={{ display: 'block', marginBottom: '5px', fontSize: '13px' }}>Scene Duration (Seconds): {scene.duration}s</label>
                <input
                    type="range"
                    min="1"
                    max="60"
                    value={scene.duration}
                    onChange={(e) => updateScene(index, 'duration', e.target.value)}
                    style={{ width: '100%', accentColor: '#a855f7' }}
                />
            </div>
          ))}

          <button 
            type="button" 
            onClick={addScene}
            style={{
                backgroundColor: 'transparent',
                color: '#58a6ff',
                border: '1px dashed #58a6ff',
                padding: '10px',
                borderRadius: '4px',
                cursor: 'pointer',
                width: '100%',
                fontWeight: 'bold'
            }}
          >
            + Add New Scene
          </button>
        </div>

        <div>
          <label style={{ display: 'block', marginBottom: '5px', fontSize: '13px' }}>Global Chunk Render Duration (Seconds): {chunkDuration}s</label>
          <input
            type="range"
            min="1"
            max="20"
            value={chunkDuration}
            onChange={(e) => setChunkDuration(e.target.value)}
            style={{ width: '100%', accentColor: '#a855f7' }}
          />
        </div>

        <div style={{ padding: '10px', backgroundColor: '#161b22', borderRadius: '4px', border: '1px solid #30363d', textAlign: 'center' }}>
            <strong>Total Script Runtime: </strong> {totalDuration} Seconds
        </div>

        <button
          type="submit"
          disabled={isGenerating || workflows.length === 0}
          style={{
            backgroundColor: isGenerating ? '#555' : '#a855f7',
            color: '#fff',
            border: 'none',
            padding: '15px',
            borderRadius: '4px',
            fontWeight: 'bold',
            fontSize: '15px',
            cursor: isGenerating ? 'not-allowed' : 'pointer',
            marginTop: '10px'
          }}
        >
          {isGenerating ? '⚡ Generating Script...' : '🎬 Generate Full Script!'}
        </button>
      </form>

      <div style={{ marginTop: '15px', fontSize: '13px', color: status.includes('Failed') ? '#f85149' : '#7ee787' }}>
        Status: {status}
      </div>

      {generatedMedia && (
        <div style={{ marginTop: '20px', borderTop: '1px solid #30363d', paddingTop: '20px' }}>
          <h3 style={{ color: '#fff', fontSize: '16px' }}>Final Script Output:</h3>
          <video 
            src={generatedMedia?.startsWith('http') || generatedMedia?.startsWith('data:') || generatedMedia?.startsWith('blob:') ? generatedMedia : `${backendUrl}${generatedMedia?.startsWith('/') ? '' : '/'}${generatedMedia}`} 
            controls 
            autoPlay 
            loop 
            style={{ maxWidth: '100%', borderRadius: '8px', border: '1px solid #30363d' }} 
          />
        </div>
      )}
    </div>
  );
}
