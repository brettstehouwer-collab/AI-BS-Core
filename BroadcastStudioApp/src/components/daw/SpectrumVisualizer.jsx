import React, { useEffect, useRef } from 'react';
import { masterAnalyser, useDawStore } from './dawStore';
import { theme } from '../../styles/theme';

const SpectrumVisualizer = ({ width = 120, height = 24 }) => {
  const canvasRef = useRef(null);
  const requestRef = useRef();

  useEffect(() => {
    const canvas = canvasRef.current;
    if (!canvas) return;
    const ctx = canvas.getContext('2d');

    const draw = () => {
      // Clear canvas
      ctx.clearRect(0, 0, width, height);

      // Only draw if engine is started
      if (useDawStore.getState().isEngineStarted) {
        const values = masterAnalyser.getValue();
        // values is a Float32Array of decibels usually from -100 to 0

        const barWidth = width / values.length;
        
        // Cyberpunk cyan/violet gradient
        const gradient = ctx.createLinearGradient(0, height, 0, 0);
        gradient.addColorStop(0, '#00f0ff');
        gradient.addColorStop(1, '#ff007f');
        ctx.fillStyle = gradient;

        for (let i = 0; i < values.length; i++) {
          // Normalize db value (approx -100 to 0) to 0-1
          let val = (values[i] + 100) / 100;
          if (val < 0) val = 0;
          if (val > 1) val = 1;

          const barHeight = val * height;
          
          ctx.fillRect(
            i * barWidth, 
            height - barHeight, 
            barWidth - 1, 
            barHeight
          );
        }
      }

      requestRef.current = requestAnimationFrame(draw);
    };

    requestRef.current = requestAnimationFrame(draw);

    return () => cancelAnimationFrame(requestRef.current);
  }, [width, height]);

  return (
    <canvas 
      ref={canvasRef} 
      width={width} 
      height={height} 
      style={{ 
        width: `${width}px`, 
        height: `${height}px`,
        background: 'rgba(0,0,0,0.5)',
        borderRadius: '2px',
        border: '1px solid #30363d',
        boxShadow: '0 0 10px rgba(0, 240, 255, 0.2)'
      }} 
    />
  );
};

export default SpectrumVisualizer;
