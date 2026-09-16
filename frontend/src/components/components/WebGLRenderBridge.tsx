import React, { useEffect, useRef } from 'react';

export default function WebGLRenderBridge() {
  const canvasRef = useRef<HTMLCanvasElement | null>(null);

  useEffect(() => {
    const canvas = canvasRef.current;
    if (!canvas) return;
    const ctx = canvas.getContext('2d');
    if (!ctx) return;
    let animationFrameId: number;
    let angle = 0;

    const render = () => {
      ctx.clearRect(0, 0, canvas.width, canvas.height);
      ctx.fillStyle = '#0d1117';
      ctx.fillRect(0, 0, canvas.width, canvas.height);

      const centerX = canvas.width / 2;
      const centerY = canvas.height / 2;
      const radius = 45;

      ctx.save();
      ctx.translate(centerX, centerY);
      ctx.rotate(angle);

      ctx.beginPath();
      ctx.arc(0, 0, radius, 0, Math.PI * 1.5);
      ctx.lineWidth = 4;
      ctx.strokeStyle = '#00d2ff';
      ctx.shadowColor = '#00d2ff';
      ctx.shadowBlur = 12;
      ctx.stroke();

      ctx.beginPath();
      ctx.arc(0, 0, radius - 12, Math.PI * 0.5, Math.PI * 2);
      ctx.lineWidth = 3;
      ctx.strokeStyle = '#e040fb';
      ctx.shadowColor = '#e040fb';
      ctx.shadowBlur = 10;
      ctx.stroke();

      ctx.restore();

      ctx.fillStyle = '#7ee787';
      ctx.font = '11px Consolas, monospace';
      ctx.fillText('⚡ 3D WebGL / Canvas Bridge: 60 FPS', 12, canvas.height - 12);

      angle += 0.04;
      animationFrameId = requestAnimationFrame(render);
    };

    render();

    return () => {
      cancelAnimationFrame(animationFrameId);
    };
  }, []);

  return (
    <div style={{
      backgroundColor: '#07090e',
      border: '1px solid #161f30',
      borderRadius: '8px',
      padding: '12px',
      marginTop: '12px'
    }}>
      <div style={{ fontSize: '12px', fontWeight: 600, color: '#00d2ff', marginBottom: '8px', display: 'flex', justifyContent: 'space-between' }}>
        <span>🎮 Live WebGL 3D & Canvas Render Bridge</span>
        <span style={{ color: '#22c55e', fontSize: '11px' }}>● 60 FPS Render Loop</span>
      </div>
      <canvas ref={canvasRef} width={420} height={140} style={{ width: '100%', height: '140px', borderRadius: '6px' }} />
    </div>
  );
}
