import React, { useState, useEffect } from 'react';

export default function ComfyUIWorkflowTrigger() {
  const [workflows, setWorkflows] = useState<string[]>([]);
  const [selectedWorkflow, setSelectedWorkflow] = useState<string>('');
  const [prompt, setPrompt] = useState('Futuristic cybernetic workstation, RTX 4090 neon lighting, ultra detailed 8k');
  const [isTriggering, setIsTriggering] = useState(false);
  const [lastStatus, setLastStatus] = useState<any>(null);
  const [generatedMedia, setGeneratedMedia] = useState<string | null>(null);
  const [baseImage, setBaseImage] = useState<File | null>(null);

  const backendUrl = '';

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
  }, []);

  const handleTrigger = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!prompt.trim() || !selectedWorkflow) return;
    setIsTriggering(true);
    setLastStatus({ status: 'Uploading / Queuing...', vram_allocation_mb: 'Auto' });
    setGeneratedMedia(null);

    try {
      let baseImageFilename = null;
      if (baseImage) {
        const formData = new FormData();
        formData.append('image', baseImage);
        const uploadRes = await fetch(`${backendUrl}/api/comfyui/upload`, {
          method: 'POST',
          body: formData
        });
        if (uploadRes.ok) {
          const uploadData = await uploadRes.json();
          baseImageFilename = uploadData.name;
        }
      }

      const reqBody: any = { 
        workflow_filename: selectedWorkflow, 
        prompt_text: prompt 
      };
      if (baseImageFilename) reqBody.base_image = baseImageFilename;

      const res = await fetch(`${backendUrl}/api/comfyui/generate`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(reqBody)
      });
      
      if (res.ok) {
        const data = await res.json();
        setLastStatus({ status: 'Queued', prompt_id: data.prompt_id, vram_allocation_mb: 'Auto' });
        pollStatus(data.prompt_id);
      } else {
        throw new Error("Generation failed");
      }
    } catch (err) {
      console.warn('Backend ComfyUI workflow trigger failed.', err);
      setLastStatus({ status: 'FAILED' });
      setIsTriggering(false);
    }
  };

  const pollStatus = (promptId: string) => {
    setLastStatus({ status: 'Rendering on GPU... (Please wait)', vram_allocation_mb: 'Auto' });
    const interval = setInterval(async () => {
      try {
        const res = await fetch(`${backendUrl}/api/comfyui/status/${promptId}`);
        const data = await res.json();
        
        if (data.status === 'completed' && data.outputs && data.outputs.length > 0) {
          clearInterval(interval);
          setLastStatus({ status: 'Complete ✅', vram_allocation_mb: 'Auto' });
          setIsTriggering(false);
          const output = data.outputs[0];
          setGeneratedMedia(`${backendUrl}/api/comfyui/view?filename=${output.filename}&subfolder=${output.subfolder}&folder_type=${output.type}`);
        } else if (data.status === 'error') {
          clearInterval(interval);
          setLastStatus({ status: `Failed: ${data.error}` });
          setIsTriggering(false);
        }
      } catch (err) {
        console.error('Polling error', err);
      }
    }, 3000);
  };

  return (
    <div style={{
      backgroundColor: '#0d1117',
      border: '1px solid #30363d',
      borderRadius: '8px',
      padding: '16px',
      color: '#c9d1d9',
      marginTop: '12px'
    }}>
      <div style={{ display: 'flex', flexDirection: 'column', gap: '12px', marginBottom: '12px' }}>
        <h4 style={{ margin: 0, color: '#e040fb', fontSize: '14px', display: 'flex', alignItems: 'center', gap: '8px' }}>
          <span>🎨</span> ComfyUI Dynamic Workflow Pipeline
        </h4>
        <div style={{ display: 'flex', gap: '8px', flexWrap: 'wrap' }}>
          {workflows.map(wf => (
             <button
              key={wf}
              type="button"
              onClick={() => setSelectedWorkflow(wf)}
              style={{
                backgroundColor: selectedWorkflow === wf ? '#e040fb' : '#161b22',
                color: selectedWorkflow === wf ? '#fff' : '#8b949e',
                border: '1px solid #30363d',
                borderRadius: '4px',
                padding: '6px 12px',
                fontSize: '11px',
                cursor: 'pointer',
                fontWeight: selectedWorkflow === wf ? 'bold' : 'normal'
              }}
            >
              🎬 {wf.replace('.json', '').replace('_api', '')}
            </button>
          ))}
          {workflows.length === 0 && <span style={{ fontSize: '11px', color: '#8b949e' }}>Loading available workflows...</span>}
        </div>
      </div>

      <form onSubmit={handleTrigger} style={{ display: 'flex', flexDirection: 'column', gap: '10px' }}>
        <textarea
          value={prompt}
          onChange={(e) => setPrompt(e.target.value)}
          placeholder="Enter prompt for ComfyUI GPU generation..."
          rows={3}
          style={{
            backgroundColor: '#161b22',
            border: '1px solid #30363d',
            borderRadius: '4px',
            color: '#f0f6fc',
            padding: '8px 12px',
            fontSize: '12px',
            resize: 'vertical'
          }}
        />

        <div style={{ display: 'grid', gridTemplateColumns: '1fr auto', gap: '8px', alignItems: 'center' }}>
          <input 
            type="file" 
            accept="image/*"
            onChange={(e) => setBaseImage(e.target.files ? e.target.files[0] : null)}
            style={{
              fontSize: '11px',
              color: '#8b949e',
              backgroundColor: '#161b22',
              border: '1px solid #30363d',
              padding: '6px',
              borderRadius: '4px'
            }}
          />
          <button
            type="submit"
            disabled={isTriggering || !selectedWorkflow}
            style={{
              backgroundColor: isTriggering ? '#555' : '#a855f7',
              border: 'none',
              borderRadius: '4px',
              color: '#fff',
              padding: '8px 16px',
              fontSize: '12px',
              fontWeight: 600,
              cursor: isTriggering ? 'not-allowed' : 'pointer'
            }}
          >
            {isTriggering ? 'Queuing...' : '⚡ Render GPU'}
          </button>
        </div>
      </form>

      {lastStatus && (
        <div style={{
          marginTop: '10px',
          backgroundColor: '#161b22',
          border: '1px solid #238636',
          borderRadius: '4px',
          padding: '8px 12px',
          fontSize: '11px',
          color: lastStatus.status.includes('Failed') ? '#f85149' : '#7ee787'
        }}>
          Status: {lastStatus.status} {lastStatus.vram_allocation_mb && `| VRAM: ${lastStatus.vram_allocation_mb}`}
        </div>
      )}

      {generatedMedia && (
        <div style={{ marginTop: '15px' }}>
          {generatedMedia.endsWith('.mp4') || generatedMedia.endsWith('.webm') ? (
             <video src={generatedMedia.startsWith('http') ? generatedMedia : `${backendUrl}${generatedMedia.startsWith('/') ? '' : '/'}${generatedMedia}`} controls autoPlay loop style={{ width: '100%', borderRadius: '4px', border: '1px solid #30363d' }} />
          ) : (
             <img src={generatedMedia.startsWith('http') ? generatedMedia : `${backendUrl}${generatedMedia.startsWith('/') ? '' : '/'}${generatedMedia}`} alt="Generated" style={{ width: '100%', borderRadius: '4px', border: '1px solid #30363d' }} />
          )}
        </div>
      )}
    </div>
  );
}
