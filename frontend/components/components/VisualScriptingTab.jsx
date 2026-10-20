import React, { useState, useCallback, useMemo } from 'react';
import {
  ReactFlow, MiniMap, Controls, Background, useNodesState,
  useEdgesState, addEdge, Handle, Position
} from '@xyflow/react';
import '@xyflow/react/dist/style.css';
import './VisualScriptingTab.css';

// ---------------- CUSTOM NODES ----------------

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
    <div className="vs-node-body vs-node-math-inputs">
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
    <div className="vs-node-body vs-node-logic-inputs">
      <input type="text" className="vs-node-input vs-node-logic-var" value={data.varA || 'A'} onChange={(e) => data.onChange(id, 'varA', e.target.value)} />
      <select className="vs-node-input vs-node-logic-comp" value={data.comp || '>'} onChange={(e) => data.onChange(id, 'comp', e.target.value)}>
        <option value=">">&gt;</option><option value="<">&lt;</option><option value="==">==</option><option value="!=">!=</option>
      </select>
      <input type="text" className="vs-node-input vs-node-logic-var" value={data.varB || 'B'} onChange={(e) => data.onChange(id, 'varB', e.target.value)} />
    </div>
    <Handle type="source" position={Position.Right} id="true" style={{top: 35, background: '#10b981'}} />
    <Handle type="source" position={Position.Right} id="false" style={{top: 75, background: '#ef4444'}} />
    <div className="vs-node-logic-true">True</div>
    <div className="vs-node-logic-false">False</div>
  </div>
);

const Spawn3DNode = ({ data, id }) => (
  <div className="vs-node vs-node-3d">
    <Handle type="target" position={Position.Left} id="in" />
    <div className="vs-node-header">🧊 Spawn 3D Object</div>
    <div className="vs-node-body vs-node-3d-inputs">
      <select className="vs-node-input" value={data.shape || 'Cube'} onChange={(e) => data.onChange(id, 'shape', e.target.value)}>
        <option value="Cube">Cube</option><option value="Sphere">Sphere</option>
      </select>
      <div className="vs-node-3d-coords">
        <input type="number" className="vs-node-input" placeholder="X" value={data.x || 0} onChange={(e) => data.onChange(id, 'x', e.target.value)} />
        <input type="number" className="vs-node-input" placeholder="Y" value={data.y || 0} onChange={(e) => data.onChange(id, 'y', e.target.value)} />
        <input type="number" className="vs-node-input" placeholder="Z" value={data.z || 0} onChange={(e) => data.onChange(id, 'z', e.target.value)} />
      </div>
      <input type="color" className="vs-node-input vs-node-3d-color" value={data.color || '#00ff00'} onChange={(e) => data.onChange(id, 'color', e.target.value)} />
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
      <div className="vs-node-telemetry-desc">Outputs raw sensor value.</div>
    </div>
    <Handle type="source" position={Position.Right} id="out" />
  </div>
);

// ---------------- INITIAL GRAPH ----------------

const initialNodes = [
  { id: '1', type: 'startNode', position: { x: 50, y: 150 }, data: { label: 'Start' } },
];

export default function VisualScriptingTab({ onExportCode }) {
  const [nodes, setNodes, onNodesChange] = useNodesState(initialNodes);
  const [edges, setEdges, onEdgesChange] = useEdgesState([]);
  const [nodeIdCounter, setNodeIdCounter] = useState(2);
  const [compileTarget, setCompileTarget] = useState('nodejs');

  const handleNodeDataChange = (id, field, val) => {
    setNodes((nds) => nds.map((node) => {
      if (node.id === id) node.data = { ...node.data, [field]: val };
      return node;
    }));
  };

  const nodeTypes = useMemo(() => ({
    startNode: StartNode,
    printNode: (props) => <PrintNode {...props} data={{ ...props.data, onChange: handleNodeDataChange }} />,
    mathNode: (props) => <MathNode {...props} data={{ ...props.data, onChange: handleNodeDataChange }} />,
    logicNode: (props) => <LogicBranchNode {...props} data={{ ...props.data, onChange: handleNodeDataChange }} />,
    spawn3dNode: (props) => <Spawn3DNode {...props} data={{ ...props.data, onChange: handleNodeDataChange }} />,
    telemetryNode: (props) => <TelemetryNode {...props} data={{ ...props.data, onChange: handleNodeDataChange }} />
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
    
    // Lighting
    const light = new THREE.DirectionalLight(0xffffff, 1);
    light.position.set(5, 5, 5);
    scene.add(light);
    scene.add(new THREE.AmbientLight(0x404040));
    
    // Virtual Graph Logic Injection
${innerLogic}
    
    camera.position.z = 10;
    camera.position.y = 2;
    
    async function animate() {
      requestAnimationFrame(animate);
      // Optional: Auto-rotate meshes spawned by the graph
      scene.children.forEach(c => {
         if (c.type === 'Mesh') { c.rotation.x += 0.01; c.rotation.y += 0.01; }
      });
      renderer.render(scene, camera);
    }
    
    // Wrap logic in an async IIFE to support top-level await from Telemetry Nodes
    (async () => {
${innerLogic}
      animate();
    })();
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
        } else {
          block += currentIndent + `console.log("3D Spawner (Cube at ${node.data.x||0},${node.data.y||0},${node.data.z||0}) ignored in Node.js compile target.");\n`;
        }
      } else if (node.type === 'telemetryNode') {
        block += currentIndent + `let sensorData_${node.id} = await fetch('/api/telemetry/matrix').then(r => r.json());\n`;
        block += currentIndent + `let sensorValue_${node.id} = sensorData_${node.id}.matrix.sensors["${node.data.sensor}"] || 0;\n`;
        block += currentIndent + `console.log("Telemetry ${node.data.sensor}:", sensorValue_${node.id});\n`;
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
      if (outEdge) {
        block += traverse(outEdge.target, currentIndent);
      }
      return block;
    };

    const startEdge = edges.find(e => e.source === startNode.id);
    if (startEdge) {
      codeBody = traverse(startEdge.target, indent);
    }

    if (compileTarget === 'nodejs') {
      let finalCode = "// Generated from Visual Scripting AST Compiler\nasync function start() {\n";
      finalCode += codeBody;
      finalCode += "}\nstart();";
      onExportCode(finalCode, 'javascript');
    } else {
      onExportCode(generateThreeJsBoilerplate(codeBody), 'html');
    }
  };

  return (
    <div className="vs-container">
      <div className="vs-toolbar">
        <div className="vs-toolbar-group">
          <button className="dev-btn" onClick={() => addNode('printNode')}>+ Print</button>
          <button className="dev-btn" onClick={() => addNode('mathNode')} style={{borderBottom: '2px solid #f59e0b'}}>+ Math</button>
          <button className="dev-btn" onClick={() => addNode('logicNode')} style={{borderBottom: '2px solid #eab308'}}>+ Logic</button>
          <button className="dev-btn" onClick={() => addNode('spawn3dNode')} style={{borderBottom: '2px solid #a855f7'}}>+ Spawn 3D</button>
          <button className="dev-btn" onClick={() => addNode('telemetryNode')} style={{borderBottom: '2px solid #4cc9f0'}}>+ Telemetry</button>
        </div>
        
        <div className="vs-toolbar-actions">
          <select 
            className={`vs-select ${compileTarget === 'webgl' ? 'vs-select-webgl' : 'vs-select-nodejs'}`}
            value={compileTarget} 
            onChange={e => setCompileTarget(e.target.value)}
          >
            <option value="nodejs">Target: Node.js (Console)</option>
            <option value="webgl">Target: Live 3D WebGL (Browser)</option>
          </select>
          <button className="dev-btn dev-btn-run" onClick={handleCompile}>⚙️ Compile Graph</button>
        </div>
      </div>
      <div className="vs-canvas">
        <ReactFlow nodes={nodes} edges={edges} onNodesChange={onNodesChange} onEdgesChange={onEdgesChange} onConnect={onConnect} nodeTypes={nodeTypes} fitView>
          <Controls />
          <Background variant="dots" gap={12} size={1} />
        </ReactFlow>
      </div>
    </div>
  );
}
