import React, { useState, useCallback, useRef } from 'react';
import {
  ReactFlow,
  Controls,
  Background,
  applyNodeChanges,
  applyEdgeChanges,
  addEdge,
} from '@xyflow/react';
import '@xyflow/react/dist/style.css';
import { theme } from '../../styles/theme';
import { Network, Plus, Video, PaintBucket, Sparkles, Droplets } from 'lucide-react';
import { VideoSourceNode, ColorTransformNode, BlurNode, AIGenerativeFillNode, MasterOutNode } from './CompositorNodes';
import { useDawStore } from './dawStore';

const nodeTypes = {
  videoSource: VideoSourceNode,
  colorTransform: ColorTransformNode,
  blur: BlurNode,
  aiGenFill: AIGenerativeFillNode,
  masterOut: MasterOutNode,
};

// initial state removed, now in dawStore

let id = 4;
const getId = () => `${id++}`;

const NodeCompositor = () => {
  const nodes = useDawStore(state => state.compositorNodes);
  const edges = useDawStore(state => state.compositorEdges);
  const setNodes = useDawStore(state => state.setCompositorNodes);
  const setEdges = useDawStore(state => state.setCompositorEdges);
  const reactFlowWrapper = useRef(null);

  const onNodesChange = useCallback(
    (changes) => setNodes((nds) => applyNodeChanges(changes, nds)),
    []
  );

  const onEdgesChange = useCallback(
    (changes) => setEdges((eds) => applyEdgeChanges(changes, eds)),
    []
  );

  const onConnect = useCallback(
    (params) => setEdges((eds) => addEdge({ ...params, animated: true, style: { stroke: theme.colors.accent } }, eds)),
    []
  );

  const addNode = (type, data = {}) => {
    const newNode = {
      id: getId(),
      type,
      position: {
        x: Math.random() * 200 + 100,
        y: Math.random() * 200 + 100,
      },
      data,
    };
    setNodes((nds) => nds.concat(newNode));
  };

  return (
    <div style={{
      background: 'rgba(12, 15, 20, 0.98)',
      height: '100%',
      display: 'flex',
      flexDirection: 'column',
      borderRadius: '8px',
      overflow: 'hidden'
    }}>
      {/* Top Header */}
      <div style={{
        padding: '12px 16px',
        borderBottom: `1px solid ${theme.colors.border}`,
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'space-between',
        background: 'rgba(20, 24, 30, 0.8)'
      }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
          <Network size={18} color={theme.colors.accent} />
          <h3 style={{ margin: 0, fontSize: '14px', color: '#fff', fontWeight: 'bold' }}>
            NODE-BASED VIDEO COMPOSITOR
          </h3>
        </div>
        <div style={{ display: 'flex', gap: '8px' }}>
          <button onClick={() => addNode('videoSource')} style={btnStyle}><Video size={12}/> + Source</button>
          <button onClick={() => addNode('colorTransform')} style={btnStyle}><PaintBucket size={12}/> + Color</button>
          <button onClick={() => addNode('blur')} style={btnStyle}><Droplets size={12}/> + Blur</button>
          <button onClick={() => addNode('aiGenFill')} style={btnStyle}><Sparkles size={12}/> + AI Fill</button>
        </div>
      </div>

      <div style={{ flex: 1, position: 'relative' }} ref={reactFlowWrapper}>
        <ReactFlow
          nodes={nodes}
          edges={edges}
          onNodesChange={onNodesChange}
          onEdgesChange={onEdgesChange}
          onConnect={onConnect}
          nodeTypes={nodeTypes}
          fitView
          theme="dark"
        >
          <Background color="#30363d" gap={24} size={2} />
          <Controls style={{ fill: '#fff' }} />
        </ReactFlow>
      </div>
    </div>
  );
};

const btnStyle = {
  background: 'rgba(255, 255, 255, 0.05)',
  border: '1px solid rgba(255, 255, 255, 0.1)',
  color: '#fff',
  fontSize: '11px',
  padding: '6px 10px',
  borderRadius: '4px',
  cursor: 'pointer',
  display: 'flex',
  alignItems: 'center',
  gap: '6px'
};

export default NodeCompositor;
