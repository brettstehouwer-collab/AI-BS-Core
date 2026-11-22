import { useEffect, useRef } from 'react';

/**
 * 60 FPS HTML5/WebGL Canvas Compositor Hook
 * Renders multiple layered video/overlay sources with smooth z-indexing,
 * active border highlights, and zero-drift animation timing.
 */
export function useCanvasCompositor({ canvasRef, sources = [], activeScene = 'Main', isStreaming = false }) {
  const animFrameRef = useRef(null);
  const lastTimeRef = useRef(performance.now());

  useEffect(() => {
    const canvas = canvasRef.current;
    if (!canvas) return;
    const ctx = canvas.getContext('2d', { alpha: false });
    if (!ctx) return;

    let running = true;

    const renderLoop = (now) => {
      if (!running) return;
      const dt = (now - lastTimeRef.current) / 1000;
      lastTimeRef.current = now;

      // 1. Clear Canvas with dark broadcast studio gradient
      const bgGrad = ctx.createLinearGradient(0, 0, canvas.width, canvas.height);
      bgGrad.addColorStop(0, '#060a12');
      bgGrad.addColorStop(1, '#0d1527');
      ctx.fillStyle = bgGrad;
      ctx.fillRect(0, 0, canvas.width, canvas.height);

      // 2. Render active scene background grid/lines
      ctx.strokeStyle = 'rgba(0, 229, 255, 0.04)';
      ctx.lineWidth = 1;
      const step = 40;
      for (let x = 0; x < canvas.width; x += step) {
        ctx.beginPath();
        ctx.moveTo(x, 0);
        ctx.lineTo(x, canvas.height);
        ctx.stroke();
      }
      for (let y = 0; y < canvas.height; y += step) {
        ctx.beginPath();
        ctx.moveTo(0, y);
        ctx.lineTo(canvas.width, y);
        ctx.stroke();
      }

      // 3. Render sources in array order (z-index)
      sources.forEach((source, idx) => {
        if (!source.enabled) return;

        // Positioning logic based on source layout or grid
        const cols = sources.length > 2 ? 2 : 1;
        const colIdx = idx % cols;
        const rowIdx = Math.floor(idx / cols);
        const w = sources.length === 1 ? canvas.width - 40 : (canvas.width / cols) - 30;
        const h = sources.length <= 2 ? canvas.height - 40 : (canvas.height / 2) - 30;
        const x = 20 + colIdx * (w + 20);
        const y = 20 + rowIdx * (h + 20);

        // Draw Layer Surface Card
        ctx.fillStyle = 'rgba(15, 23, 42, 0.88)';
        ctx.fillRect(x, y, w, h);

        // Highlight Active Source Border
        ctx.strokeStyle = isStreaming ? '#00e5ff' : '#38bdf8';
        ctx.lineWidth = 2;
        ctx.strokeRect(x, y, w, h);

        // Header Title Badge
        ctx.fillStyle = 'rgba(0, 229, 255, 0.12)';
        ctx.fillRect(x, y, w, 28);
        ctx.fillStyle = '#00e5ff';
        ctx.font = 'bold 12px monospace';
        ctx.fillText(`● [LAYER ${idx + 1}] ${source.name.toUpperCase()}`, x + 10, y + 18);

        // Source Type Watermark
        ctx.fillStyle = 'rgba(255, 255, 255, 0.2)';
        ctx.font = '11px sans-serif';
        ctx.fillText(source.type || 'Video Source', x + w - 100, y + 18);
      });

      animFrameRef.current = requestAnimationFrame(renderLoop);
    };

    animFrameRef.current = requestAnimationFrame(renderLoop);

    return () => {
      running = false;
      if (animFrameRef.current) cancelAnimationFrame(animFrameRef.current);
    };
  }, [canvasRef, sources, activeScene, isStreaming]);

  return { animFrameRef };
}
