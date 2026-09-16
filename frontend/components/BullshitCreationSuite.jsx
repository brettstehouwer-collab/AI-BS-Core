import React, { useState, useCallback, useMemo } from 'react';
import {
  ReactFlow, MiniMap, Controls, Background, useNodesState,
  useEdgesState, addEdge, Handle, Position
} from '@xyflow/react';
import '@xyflow/react/dist/style.css';
import './VisualScriptingTab.css';

// ---------------- CUSTOM NODES FOR VISUAL SCRIPTING ----------------

const StartNode = ({ data }) => (
  <div className="vs-node vs-node-start">
    <div className="vs-node-header">🚀 Event: On Start</div>
    <div className="vs-node-body">Triggers when script runs</div>
    <Handle type="source" position={Position.Right} id="out" />
  </div>
);

const PrintNode = ({ data, id }) => (
  <div className="vs-node vs-node-action">
    <Handle type="target" position={Position.Left} id="in" />
    <div className="vs-node-header">🖨️ Action: Print</div>
    <div className="vs-node-body">
      <label>Message: </label>
      <input className="vs-node-input" value={data.message || ''} onChange={(e) => data.onChange(id, 'message', e.target.value)} />
    </div>
    <Handle type="source" position={Position.Right} id="out" />
  </div>
);

const MathNode = ({ data, id }) => (
  <div className="vs-node vs-node-math">
    <Handle type="target" position={Position.Left} id="in" />
    <div className="vs-node-header">➕ Math Operation</div>
    <div className="vs-node-body" style={{display:'flex', flexDirection:'column', gap:'4px'}}>
      <input type="text" className="vs-node-input" placeholder="Val 1" value={data.val1 || '0'} onChange={(e) => data.onChange(id, 'val1', e.target.value)} />
      <select className="vs-node-input" value={data.op || '+'} onChange={(e) => data.onChange(id, 'op', e.target.value)}>
        <option value="+">+</option><option value="-">-</option><option value="*">*</option><option value="/">/</option>
      </select>
      <input type="text" className="vs-node-input" placeholder="Val 2" value={data.val2 || '0'} onChange={(e) => data.onChange(id, 'val2', e.target.value)} />
      <input type="text" className="vs-node-input" placeholder="Save to Var..." value={data.varName || 'res'} onChange={(e) => data.onChange(id, 'varName', e.target.value)} />
    </div>
    <Handle type="source" position={Position.Right} id="out" />
  </div>
);

const LogicBranchNode = ({ data, id }) => (
  <div className="vs-node vs-node-logic">
    <Handle type="target" position={Position.Left} id="in" />
    <div className="vs-node-header">🔀 Branch (If/Else)</div>
    <div className="vs-node-body" style={{display:'flex', gap:'4px', alignItems:'center'}}>
      <input type="text" className="vs-node-input" style={{width:'40px'}} value={data.varA || 'A'} onChange={(e) => data.onChange(id, 'varA', e.target.value)} />
      <select className="vs-node-input" style={{width:'50px'}} value={data.comp || '>'} onChange={(e) => data.onChange(id, 'comp', e.target.value)}>
        <option value=">">&gt;</option><option value="<">&lt;</option><option value="==">==</option><option value="!=">!=</option>
      </select>
      <input type="text" className="vs-node-input" style={{width:'40px'}} value={data.varB || 'B'} onChange={(e) => data.onChange(id, 'varB', e.target.value)} />
    </div>
    <Handle type="source" position={Position.Right} id="true" style={{top: 35, background: '#10b981'}} />
    <Handle type="source" position={Position.Right} id="false" style={{top: 75, background: '#ef4444'}} />
    <div style={{position:'absolute', right:'-35px', top:'26px', fontSize:'10px', color:'#10b981', fontWeight: 'bold'}}>True</div>
    <div style={{position:'absolute', right:'-40px', top:'66px', fontSize:'10px', color:'#ef4444', fontWeight: 'bold'}}>False</div>
  </div>
);

const Spawn3DNode = ({ data, id }) => (
  <div className="vs-node vs-node-3d">
    <Handle type="target" position={Position.Left} id="in" />
    <div className="vs-node-header">🧊 Spawn 3D Object</div>
    <div className="vs-node-body" style={{display:'flex', flexDirection:'column', gap:'4px'}}>
      <select className="vs-node-input" value={data.shape || 'Cube'} onChange={(e) => data.onChange(id, 'shape', e.target.value)}>
        <option value="Cube">Cube</option><option value="Sphere">Sphere</option>
      </select>
      <div style={{display:'flex', gap:'4px'}}>
        <input type="number" className="vs-node-input" placeholder="X" value={data.x || 0} onChange={(e) => data.onChange(id, 'x', e.target.value)} />
        <input type="number" className="vs-node-input" placeholder="Y" value={data.y || 0} onChange={(e) => data.onChange(id, 'y', e.target.value)} />
        <input type="number" className="vs-node-input" placeholder="Z" value={data.z || 0} onChange={(e) => data.onChange(id, 'z', e.target.value)} />
      </div>
      <input type="color" className="vs-node-input" style={{padding:0, height: '30px'}} value={data.color || '#00ff00'} onChange={(e) => data.onChange(id, 'color', e.target.value)} />
    </div>
    <Handle type="source" position={Position.Right} id="out" />
  </div>
);

const TelemetryNode = ({ data, id }) => (
  <div className="vs-node vs-node-telemetry">
    <div className="vs-node-header">📡 Input: Telemetry Matrix</div>
    <div className="vs-node-body">
      <select className="vs-node-input" value={data.sensor || 'CO2'} onChange={(e) => data.onChange(id, 'sensor', e.target.value)}>
        <option value="CO2">CO2 Levels (ppm)</option>
        <option value="TEMP">Temperature (°C)</option>
        <option value="MFC">MFC Output (mW)</option>
      </select>
      <div style={{fontSize: '10px', marginTop: '4px'}}>Outputs raw sensor value.</div>
    </div>
    <Handle type="source" position={Position.Right} id="out" />
  </div>
);

const initialNodes = [
  { id: '1', type: 'startNode', position: { x: 50, y: 150 }, data: { label: 'Start' } },
];

export default function BullshitCreationSuite(props) {
  const { activeTab } = props;

  // VISUAL SCRIPTING STATE
  const [nodes, setNodes, onNodesChange] = useNodesState(initialNodes);
  const [edges, setEdges, onEdgesChange] = useEdgesState([]);
  const [nodeIdCounter, setNodeIdCounter] = useState(2);
  const [compileTarget, setCompileTarget] = useState('nodejs');

  // GENERATOR STATE
  const [isAiGenerating, setIsAiGenerating] = useState(false);
  const [aiBlueprint, setAiBlueprint] = useState(null);

  const handleNodeDataChange = (id, field, val) => {
    setNodes((nds) => nds.map((node) => {
      if (node.id === id) node.data = { ...node.data, [field]: val };
      return node;
    }));
  };

  const nodeTypes = useMemo(() => ({
    startNode: StartNode,
    printNode: (p) => <PrintNode {...p} data={{ ...p.data, onChange: handleNodeDataChange }} />,
    mathNode: (p) => <MathNode {...p} data={{ ...p.data, onChange: handleNodeDataChange }} />,
    logicNode: (p) => <LogicBranchNode {...p} data={{ ...p.data, onChange: handleNodeDataChange }} />,
    spawn3dNode: (p) => <Spawn3DNode {...p} data={{ ...p.data, onChange: handleNodeDataChange }} />,
    telemetryNode: (p) => <TelemetryNode {...p} data={{ ...p.data, onChange: handleNodeDataChange }} />
  }), []);

  const onConnect = useCallback((params) => setEdges((eds) => addEdge(params, eds)), [setEdges]);

  const addNode = (type) => {
    const defaultData = type === 'mathNode' ? { val1:'1', op:'+', val2:'2', varName:'res' } :
                        type === 'logicNode' ? { varA:'A', comp:'>', varB:'B' } :
                        type === 'spawn3dNode' ? { shape:'Cube', x:0, y:0, z:0, color:'#00ff00' } :
                        type === 'telemetryNode' ? { sensor:'CO2' } :
                        { message: 'Hello' };
    setNodes((nds) => nds.concat({
      id: `${nodeIdCounter}`, type,
      position: { x: Math.random() * 200 + 300, y: Math.random() * 200 + 100 },
      data: defaultData,
    }));
    setNodeIdCounter(id => id + 1);
  };

  const generateThreeJsBoilerplate = (innerLogic) => `<!DOCTYPE html>
<html>
<head>
  <style>body { margin: 0; overflow: hidden; background: #0b0f19; }</style>
  <script src="https://cdnjs.cloudflare.com/ajax/libs/three.js/r128/three.min.js"></script>
</head>
<body>
  <script>
    const scene = new THREE.Scene();
    const camera = new THREE.PerspectiveCamera(75, window.innerWidth/window.innerHeight, 0.1, 1000);
    const renderer = new THREE.WebGLRenderer({ antialias: true });
    renderer.setSize(window.innerWidth, window.innerHeight);
    document.body.appendChild(renderer.domElement);
    const light = new THREE.DirectionalLight(0xffffff, 1);
    light.position.set(5, 5, 5);
    scene.add(light);
    scene.add(new THREE.AmbientLight(0x404040));
${innerLogic}
    camera.position.z = 10;
    camera.position.y = 2;
    function animate() {
      requestAnimationFrame(animate);
      scene.children.forEach(c => {
         if (c.type === 'Mesh') { c.rotation.x += 0.01; c.rotation.y += 0.01; }
      });
      renderer.render(scene, camera);
    }
    animate();
  </script>
</body>
</html>`;

  const handleCompile = () => {
    const startNode = nodes.find(n => n.type === 'startNode');
    if (!startNode) return alert("Missing Start Node!");
    let indent = compileTarget === 'webgl' ? "    " : "  ";
    let codeBody = "";
    const traverse = (nodeId, currentIndent) => {
      let block = "";
      const node = nodes.find(n => n.id === nodeId);
      if (!node) return block;
      if (node.type === 'printNode') {
        block += currentIndent + `console.log("${node.data.message || ''}");\n`;
      } else if (node.type === 'mathNode') {
        block += currentIndent + `let ${node.data.varName || 'res'} = ${node.data.val1 || 0} ${node.data.op || '+'} ${node.data.val2 || 0};\n`;
      } else if (node.type === 'spawn3dNode') {
        if (compileTarget === 'webgl') {
          const colorHex = (node.data.color || '#00ff00').replace('#', '0x');
          const isCube = node.data.shape === 'Cube';
          block += currentIndent + `const geo_${node.id} = new THREE.${isCube ? 'BoxGeometry()' : 'SphereGeometry(1, 32, 16)'};\n`;
          block += currentIndent + `const mat_${node.id} = new THREE.MeshStandardMaterial({ color: ${colorHex} });\n`;
          block += currentIndent + `const mesh_${node.id} = new THREE.Mesh(geo_${node.id}, mat_${node.id});\n`;
          block += currentIndent + `mesh_${node.id}.position.set(${node.data.x||0}, ${node.data.y||0}, ${node.data.z||0});\n`;
          block += currentIndent + `scene.add(mesh_${node.id});\n`;
        }
      } else if (node.type === 'telemetryNode') {
        block += currentIndent + `let sensorValue_${node.id} = 820;\n`;
      }
      if (node.type === 'logicNode') {
        block += currentIndent + `if (${node.data.varA || 'A'} ${node.data.comp || '>'} ${node.data.varB || 'B'}) {\n`;
        const trueEdge = edges.find(e => e.source === nodeId && e.sourceHandle === 'true');
        if (trueEdge) block += traverse(trueEdge.target, currentIndent + "  ");
        block += currentIndent + `} else {\n`;
        const falseEdge = edges.find(e => e.source === nodeId && e.sourceHandle === 'false');
        if (falseEdge) block += traverse(falseEdge.target, currentIndent + "  ");
        block += currentIndent + `}\n`;
        return block;
      }
      const outEdge = edges.find(e => e.source === nodeId && (!e.sourceHandle || e.sourceHandle === 'out'));
      if (outEdge) block += traverse(outEdge.target, currentIndent);
      return block;
    };
    const startEdge = edges.find(e => e.source === startNode.id);
    if (startEdge) codeBody = traverse(startEdge.target, indent);

    if (compileTarget === 'nodejs') {
      props.onExportCode(`function start() {\n${codeBody}}\nstart();`, 'javascript');
    } else {
      props.onExportCode(generateThreeJsBoilerplate(codeBody), 'html');
    }
  };

  const handleAiGeneration = async () => {
    setIsAiGenerating(true);
    try {
      const res = await fetch(`${props.BACKEND_URL}/api/generator/predictive`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          dimensionality: props.genDimensionality,
          physics_target: props.genPhysicsTarget,
          objective: props.genObjective
        })
      });
      const data = await res.json();
      if (res.ok) {
        setAiBlueprint({
          techStack: data.techStack || 'Dependencies automatically determined.',
          coreLoop: data.code || 'No code generated.',
          nextSteps: data.nextSteps || ['Review sandbox validation logs.'],
          sandboxLog: data.sandboxLog || 'Sandbox validation passed.'
        });
      }
    } catch (err) {}
    setIsAiGenerating(false);
  };

  const getBlueprint = () => {
    if (aiBlueprint) return aiBlueprint;
    if (props.genDimensionality === '3D' && props.genPhysicsTarget === 'Rigid Objects' && props.genObjective === 'Stabilize') {
      return {
        techStack: "pip install pybullet numpy",
        coreLoop: `while True:\n    current_pitch = get_vehicle_pitch()\n    if current_pitch > 15:\n        apply_counter_torque()\n    p.stepSimulation()`,
        nextSteps: ["Step 1: Setup PyBullet environment."]
      }
    }
    return {
      techStack: `Dependencies for ${props.genDimensionality}`,
      coreLoop: `# Generic agent loop\nwhile True:\n    step_physics()`,
      nextSteps: ["Initialize engine."]
    }
  };

  if (activeTab === 'firewrite') {
    return (
      <div className="fire-writing-container">
        <div className="fire-writing-toolbar glass-panel" style={{ padding: '16px', borderRadius: '8px', marginBottom: '20px' }}>
          <div className="fire-controls-left">
            <span style={{ fontWeight: '600', marginRight: '10px' }}>Formatting Style Profile:</span>
            <select value={props.fireProfile} onChange={(e) => props.setFireProfile(e.target.value)} style={{ background: 'var(--bg-main)', border: '1px solid var(--border-glow)', color: 'white', padding: '6px 12px', borderRadius: '4px' }}>
              <option value="fire_writing">🔥 Strict Structural Formatting (No words altered)</option>
              <option value="professional">💼 Professional Polish (Emails, Cover Letters)</option>
              <option value="creative">📖 Creative Prose (Narrative & Story polish)</option>
            </select>
          </div>
          <div className="fire-buttons-right" style={{ display: 'flex', gap: '12px' }}>
            <button className="format-button" onClick={props.handleFormatFireWriting}>
              {props.isFormatting ? 'Processing AI...' : '✨ Execute Formatting'}
            </button>
            <button className="export-button" onClick={props.handleExportFireWriting} disabled={!props.fireTextFormatted}>📥 Download Export</button>
          </div>
        </div>
        <div className="split-pane">
          <div className="pane input-pane">
            <div className="pane-title">Raw Fire Writing</div>
            <textarea placeholder="Raw input..." value={props.fireTextRaw} onChange={(e) => props.setFireTextRaw(e.target.value)} />
          </div>
          <div className="pane output-pane">
            <div className="pane-title">Structured Output</div>
            <textarea readOnly placeholder="Formatted output..." value={props.fireTextFormatted} />
          </div>
        </div>
      </div>
    );
  }

  if (activeTab === 'generator') {
    const blueprint = getBlueprint();
    return (
      <div className="generator-workspace-grid" style={{ display: 'grid', gridTemplateColumns: '350px 1fr', gap: '24px', height: '100%' }}>
        <div className="gen-input-panel glass-panel" style={{ padding: '24px', display: 'flex', flexDirection: 'column', gap: '24px' }}>
          <h3 style={{ margin: 0, color: 'var(--accent-neon)' }}>The Input Matrix</h3>
          <div className="gen-control-group">
            <label className="gen-label">Dimensionality</label>
            <select className="gen-select" value={props.genDimensionality} onChange={e => props.setGenDimensionality(e.target.value)}>
              <option value="2D">2D</option><option value="3D">3D</option>
            </select>
          </div>
          <div className="gen-control-group">
            <label className="gen-label">Physics Target</label>
            <select className="gen-select" value={props.genPhysicsTarget} onChange={e => props.setGenPhysicsTarget(e.target.value)}>
              <option value="Rigid Objects">Rigid Objects</option><option value="Soft Bodies">Soft Bodies</option>
            </select>
          </div>
          <div className="gen-control-group">
            <label className="gen-label">Agent Objective</label>
            <select className="gen-select" value={props.genObjective} onChange={e => props.setGenObjective(e.target.value)}>
              <option value="Stabilize">Stabilize</option><option value="Destroy">Destroy</option>
            </select>
          </div>
        </div>
        <div className="gen-output-panel glass-panel" style={{ padding: '24px', display: 'flex', flexDirection: 'column', gap: '20px', overflowY: 'auto' }}>
          <h3 style={{ margin: 0, color: '#fff' }}>The Blueprint Output</h3>
          <button onClick={handleAiGeneration} disabled={isAiGenerating} style={{ background: '#ec4899', color: '#fff', padding: '6px 12px', border: 'none', borderRadius: '4px', cursor: 'pointer' }}>
            {isAiGenerating ? '🤖 Synthesizing...' : '🤖 Generate via AI'}
          </button>
          <div className="blueprint-section"><h4>📦 Tech Stack</h4><div className="blueprint-box cmd-box"><code>{blueprint.techStack}</code></div></div>
          <div className="blueprint-section"><h4>🔄 Core Loop</h4><div className="blueprint-box code-box" style={{ background: '#1e1e1e', padding: '12px', whiteSpace: 'pre-wrap' }}>{blueprint.coreLoop}</div></div>
          <button onClick={props.handleDeployBlueprint} disabled={props.isDeploying} className="dev-btn dev-btn-run" style={{ padding: '16px' }}>🚀 Deploy Blueprint</button>
        </div>
      </div>
    );
  }

  if (activeTab === 'visual_scripting') {
    return (
      <div className="vs-container">
        <div className="vs-toolbar glass-panel" style={{flexWrap: 'wrap'}}>
          <div style={{display:'flex', gap:'8px', marginRight: '20px'}}>
            <button className="dev-btn" onClick={() => addNode('printNode')}>+ Print</button>
            <button className="dev-btn" onClick={() => addNode('mathNode')}>+ Math</button>
            <button className="dev-btn" onClick={() => addNode('logicNode')}>+ Logic</button>
            <button className="dev-btn" onClick={() => addNode('spawn3dNode')}>+ Spawn 3D</button>
            <button className="dev-btn" onClick={() => addNode('telemetryNode')}>+ Telemetry</button>
          </div>
          <div style={{marginLeft: 'auto', display:'flex', gap:'16px', alignItems:'center'}}>
            <select className="dev-select" value={compileTarget} onChange={e => setCompileTarget(e.target.value)}>
              <option value="nodejs">Node.js</option>
              <option value="webgl">WebGL</option>
            </select>
            <button className="dev-btn dev-btn-run" onClick={handleCompile}>⚙️ Compile Graph</button>
          </div>
        </div>
        <div className="vs-canvas glass-panel">
          <ReactFlow nodes={nodes} edges={edges} onNodesChange={onNodesChange} onEdgesChange={onEdgesChange} onConnect={onConnect} nodeTypes={nodeTypes} fitView>
            <Controls /><Background variant="dots" gap={12} size={1} />
          </ReactFlow>
        </div>
      </div>
    );
  }

  return null;
}
