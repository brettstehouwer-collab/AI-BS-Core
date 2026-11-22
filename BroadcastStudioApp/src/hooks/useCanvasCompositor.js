import { useState, useEffect, useRef } from 'react';
import { WebGLCompositor } from '../core/WebGLCompositor';

export function useCanvasCompositor(sources) {
  const canvasRef = useRef(null);
  const compositorRef = useRef(null);
  const animFrameIdRef = useRef(null);

  useEffect(() => {
    if (canvasRef.current && !compositorRef.current) {
      compositorRef.current = new WebGLCompositor(canvasRef.current);
    }
  }, [canvasRef]);

  useEffect(() => {
    const renderLoop = () => {
      if (compositorRef.current) {
        compositorRef.current.renderFrame(sources);
      }
      animFrameIdRef.current = requestAnimationFrame(renderLoop);
    };

    animFrameIdRef.current = requestAnimationFrame(renderLoop);

    return () => {
      if (animFrameIdRef.current) {
        cancelAnimationFrame(animFrameIdRef.current);
      }
    };
  }, [sources]);

  return { canvasRef };
}
