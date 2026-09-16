import React, { useRef, useEffect } from 'react';
import { theme } from '../../styles/theme';

const ColorGrading = () => {
  const canvasRef = useRef(null);

  // Draw some placeholder scopes using Canvas
  useEffect(() => {
    const canvas = canvasRef.current;
    if (!canvas) return;
    const ctx = canvas.getContext('2d');
    
    let frameId;
    const drawScope = () => {
      ctx.fillStyle = '#0a0d12';
      ctx.fillRect(0, 0, canvas.width, canvas.height);
      
      // Draw grid
      ctx.strokeStyle = '#30363d';
      ctx.lineWidth = 1;
      for (let i = 0; i < canvas.width; i += 40) {
        ctx.beginPath(); ctx.moveTo(i, 0); ctx.lineTo(i, canvas.height); ctx.stroke();
      }
      for (let i = 0; i < canvas.height; i += 40) {
        ctx.beginPath(); ctx.moveTo(0, i); ctx.lineTo(canvas.width, i); ctx.stroke();
      }

      // Draw fake RGB parade
      const t = Date.now() / 1000;
      
      const drawParade = (offset, color) => {
        ctx.strokeStyle = color;
        ctx.lineWidth = 2;
        ctx.beginPath();
        for (let i = 0; i < 100; i++) {
          const x = offset + i;
          const y = canvas.height - (Math.sin(i * 0.1 + t) * 30 + Math.random() * 20 + 50);
          if (i === 0) ctx.moveTo(x, y);
          else ctx.lineTo(x, y);
        }
        ctx.stroke();
      };
      
      drawParade(10, 'rgba(255, 0, 0, 0.8)');
      drawParade(120, 'rgba(0, 255, 0, 0.8)');
      drawParade(230, 'rgba(0, 0, 255, 0.8)');
      
      frameId = requestAnimationFrame(drawScope);
    };
    
    drawScope();
    return () => cancelAnimationFrame(frameId);
  }, []);

  const renderColorWheel = (title) => (
    <div style={{ display: 'flex', flexDirection: 'column', alignItems: 'center', gap: '10px' }}>
      <div style={{ fontSize: '12px', fontWeight: 'bold', color: '#888' }}>{title}</div>
      <div style={{
        width: '120px', height: '120px', borderRadius: '50%',
        background: 'conic-gradient(red, yellow, lime, aqua, blue, magenta, red)',
        position: 'relative',
        boxShadow: 'inset 0 0 20px rgba(0,0,0,0.8), 0 0 10px rgba(0,0,0,0.5)'
      }}>
        <div style={{
          width: '12px', height: '12px', borderRadius: '50%',
          border: '2px solid white', background: 'rgba(0,0,0,0.5)',
          position: 'absolute', top: '50%', left: '50%', transform: 'translate(-50%, -50%)',
          cursor: 'pointer'
        }} />
      </div>
      <div style={{ display: 'flex', gap: '5px' }}>
        <input type="range" min="-100" max="100" defaultValue="0" style={{ width: '100px', accentColor: theme.colors.accent }} />
      </div>
    </div>
  );

  return (
    <div style={{ width: '100%', height: '100%', display: 'flex', flexDirection: 'column', background: '#0d1117', color: '#fff' }}>
      <div style={{ padding: '8px 16px', background: 'rgba(255,255,255,0.05)', borderBottom: '1px solid #30363d', fontSize: '13px', fontWeight: 'bold' }}>
        🎨 Professional Color Grading & Scopes
      </div>
      <div style={{ display: 'flex', flex: 1, overflow: 'hidden' }}>
        
        {/* Scopes Panel */}
        <div style={{ flex: '0 0 400px', borderRight: '1px solid #30363d', padding: '16px', display: 'flex', flexDirection: 'column', gap: '16px' }}>
          <div style={{ fontSize: '11px', color: '#888', fontWeight: 'bold' }}>RGB PARADE (WAVEFORM)</div>
          <canvas ref={canvasRef} width="360" height="200" style={{ background: '#0a0d12', border: '1px solid #30363d', borderRadius: '4px' }} />
          
          <div style={{ fontSize: '11px', color: '#888', fontWeight: 'bold', marginTop: '16px' }}>VECTORSCOPE</div>
          <div style={{ width: '100%', height: '200px', background: '#0a0d12', border: '1px solid #30363d', borderRadius: '4px', position: 'relative' }}>
             {/* Fake Vectorscope Graticule */}
             <div style={{ position: 'absolute', top: '50%', left: '0', right: '0', height: '1px', background: '#30363d' }} />
             <div style={{ position: 'absolute', top: '0', bottom: '0', left: '50%', width: '1px', background: '#30363d' }} />
             <div style={{ position: 'absolute', top: '50%', left: '50%', width: '100px', height: '100px', borderRadius: '50%', border: '1px dashed #30363d', transform: 'translate(-50%, -50%)' }} />
             {/* Fake signal cluster */}
             <div style={{ position: 'absolute', top: '50%', left: '50%', width: '40px', height: '40px', background: 'radial-gradient(circle, rgba(0,255,100,0.8) 0%, rgba(0,255,100,0) 70%)', transform: 'translate(-30%, -20%)' }} />
          </div>
        </div>

        {/* Color Wheels Panel */}
        <div style={{ flex: 1, padding: '24px', display: 'flex', flexDirection: 'column', alignItems: 'center', justifyContent: 'center', gap: '40px' }}>
          <div style={{ display: 'flex', gap: '40px', justifyContent: 'center' }}>
            {renderColorWheel('LIFT (Shadows)')}
            {renderColorWheel('GAMMA (Midtones)')}
            {renderColorWheel('GAIN (Highlights)')}
          </div>
          
          <div style={{ display: 'flex', gap: '20px', background: '#0a0d12', padding: '16px', borderRadius: '8px', border: '1px solid #30363d' }}>
             <div style={{ display: 'flex', flexDirection: 'column', alignItems: 'center' }}>
                <span style={{ fontSize: '10px', color: '#888' }}>Temperature</span>
                <input type="range" min="-100" max="100" defaultValue="0" style={{ accentColor: '#ffaa00' }} />
             </div>
             <div style={{ display: 'flex', flexDirection: 'column', alignItems: 'center' }}>
                <span style={{ fontSize: '10px', color: '#888' }}>Tint</span>
                <input type="range" min="-100" max="100" defaultValue="0" style={{ accentColor: '#ff00ff' }} />
             </div>
             <div style={{ display: 'flex', flexDirection: 'column', alignItems: 'center' }}>
                <span style={{ fontSize: '10px', color: '#888' }}>Saturation</span>
                <input type="range" min="0" max="200" defaultValue="100" style={{ accentColor: theme.colors.accent }} />
             </div>
             <div style={{ display: 'flex', flexDirection: 'column', alignItems: 'center' }}>
                <span style={{ fontSize: '10px', color: '#888' }}>Contrast</span>
                <input type="range" min="0" max="200" defaultValue="100" style={{ accentColor: theme.colors.accent }} />
             </div>
          </div>
        </div>
      </div>
    </div>
  );
};

export default ColorGrading;
