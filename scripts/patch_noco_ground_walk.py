"""
Patch Noco3DCampusWalkthrough.jsx to add First-Person Ground Walk mode:
- State & refs: isGroundWalk, yaw, pitch, keys, drag-look
- Pointer events: drag to look with yaw & pitch
- Keyboard events: WASD & Arrow keys with Shift sprint
- Terrain collision / ground elevation clamping at 1.8m eye level
- Onscreen D-Pad overlay and Top HUD banner
- Toolbar toggle button
"""

import os

comp_path = r"C:\AI-BS\frontend\src\components\Noco3DCampusWalkthrough.jsx"
with open(comp_path, 'r', encoding='utf-8') as f:
    code = f.read()

# 1. State additions
state_target = """  const [isAutoTouring, setIsAutoTouring] = useState(false);
  const [tourIndex, setTourIndex] = useState(0);"""

state_repl = """  const [isAutoTouring, setIsAutoTouring] = useState(false);
  const [tourIndex, setTourIndex] = useState(0);
  const [isGroundWalk, setIsGroundWalk] = useState(false);"""

# 2. sceneRefs additions
refs_target = """    animFrameId: null,
    orbitAngle: 0,
    targetCamPos: new THREE.Vector3(0, 45, 110),
    targetLookAt: new THREE.Vector3(0, 5, 0)
  });"""

refs_repl = """    animFrameId: null,
    orbitAngle: 0,
    targetCamPos: new THREE.Vector3(0, 45, 110),
    targetLookAt: new THREE.Vector3(0, 5, 0),
    isGroundWalk: false,
    activeCamView: 'drone_orbit',
    yaw: 0,
    pitch: 0.05,
    keys: { forward: false, backward: false, left: false, right: false, sprint: false },
    isDragging: false,
    lastMouseX: 0,
    lastMouseY: 0
  });"""

# 3. Raycaster & Pointer Down / Move / Up handlers in useEffect
pointer_target = """    // 6. Raycaster for Interactive Hotspot Clicks
    const raycaster = new THREE.Raycaster();
    const mouse = new THREE.Vector2();

    const onPointerDown = (event) => {
      const rect = renderer.domElement.getBoundingClientRect();
      mouse.x = ((event.clientX - rect.left) / rect.width) * 2 - 1;
      mouse.y = -((event.clientY - rect.top) / rect.height) * 2 + 1;

      raycaster.setFromCamera(mouse, camera);
      const intersects = raycaster.intersectObjects(structures, true);
      if (intersects.length > 0) {
        let hit = intersects[0].object;
        while (hit.parent && !hit.userData?.id && hit.parent !== scene) {
          hit = hit.parent;
        }
        if (hit.userData?.id) {
          flyToWaypoint(hit.userData.id);
        }
      }
    };
    renderer.domElement.addEventListener('pointerdown', onPointerDown);"""

pointer_repl = """    // 6. Raycaster & Pointer Interaction (Hotspots + First-Person Drag Look)
    const raycaster = new THREE.Raycaster();
    const mouse = new THREE.Vector2();

    const onPointerDown = (event) => {
      const state = sceneRefs.current;
      state.isDragging = true;
      state.lastMouseX = event.clientX;
      state.lastMouseY = event.clientY;

      if (!state.isGroundWalk) {
        const rect = renderer.domElement.getBoundingClientRect();
        mouse.x = ((event.clientX - rect.left) / rect.width) * 2 - 1;
        mouse.y = -((event.clientY - rect.top) / rect.height) * 2 + 1;

        raycaster.setFromCamera(mouse, camera);
        const intersects = raycaster.intersectObjects(structures, true);
        if (intersects.length > 0) {
          let hit = intersects[0].object;
          while (hit.parent && !hit.userData?.id && hit.parent !== scene) {
            hit = hit.parent;
          }
          if (hit.userData?.id) {
            flyToWaypoint(hit.userData.id);
          }
        }
      }
    };

    const onPointerMove = (event) => {
      const state = sceneRefs.current;
      if (state.isGroundWalk && state.isDragging) {
        const dx = event.clientX - state.lastMouseX;
        const dy = event.clientY - state.lastMouseY;
        state.yaw += dx * 0.004;
        state.pitch = Math.max(-Math.PI * 0.35, Math.min(Math.PI * 0.35, state.pitch - dy * 0.004));
        state.lastMouseX = event.clientX;
        state.lastMouseY = event.clientY;
      }
    };

    const onPointerUp = () => {
      sceneRefs.current.isDragging = false;
    };

    renderer.domElement.addEventListener('pointerdown', onPointerDown);
    window.addEventListener('pointermove', onPointerMove);
    window.addEventListener('pointerup', onPointerUp);

    // Keyboard handlers for Ground Walk WASD
    const onKeyDown = (e) => {
      const state = sceneRefs.current;
      if (!state.isGroundWalk) return;
      if (['KeyW', 'ArrowUp'].includes(e.code)) state.keys.forward = true;
      if (['KeyS', 'ArrowDown'].includes(e.code)) state.keys.backward = true;
      if (['KeyA', 'ArrowLeft'].includes(e.code)) state.keys.left = true;
      if (['KeyD', 'ArrowRight'].includes(e.code)) state.keys.right = true;
      if (['ShiftLeft', 'ShiftRight'].includes(e.code)) state.keys.sprint = true;
    };

    const onKeyUp = (e) => {
      const state = sceneRefs.current;
      if (!state.isGroundWalk) return;
      if (['KeyW', 'ArrowUp'].includes(e.code)) state.keys.forward = false;
      if (['KeyS', 'ArrowDown'].includes(e.code)) state.keys.backward = false;
      if (['KeyA', 'ArrowLeft'].includes(e.code)) state.keys.left = false;
      if (['KeyD', 'ArrowRight'].includes(e.code)) state.keys.right = false;
      if (['ShiftLeft', 'ShiftRight'].includes(e.code)) state.keys.sprint = false;
    };

    window.addEventListener('keydown', onKeyDown);
    window.addEventListener('keyup', onKeyUp);"""

# 4. Animation loop update
anim_target = """      // Smooth camera interpolation towards target
      if (activeCamView === 'drone_orbit') {
        state.orbitAngle += delta * 0.12;
        const orbitRadius = 115;
        state.camera.position.x = Math.sin(state.orbitAngle) * orbitRadius;
        state.camera.position.z = Math.cos(state.orbitAngle) * orbitRadius;
        state.camera.position.y = 55 + Math.sin(state.orbitAngle * 0.5) * 8;
        state.camera.lookAt(0, 4, 0);
      } else {
        state.camera.position.lerp(state.targetCamPos, 0.05);
        state.camera.lookAt(state.targetLookAt);
      }"""

anim_repl = """      // Camera Control: Ground Walk Mode vs Orbit vs Focused Waypoint
      if (state.isGroundWalk) {
        const speed = (state.keys.sprint ? 28 : 14) * delta;
        const forward = new THREE.Vector3(Math.sin(state.yaw), 0, Math.cos(state.yaw));
        const right = new THREE.Vector3(Math.cos(state.yaw), 0, -Math.sin(state.yaw));

        const move = new THREE.Vector3();
        if (state.keys.forward) move.sub(forward);
        if (state.keys.backward) move.add(forward);
        if (state.keys.left) move.sub(right);
        if (state.keys.right) move.add(right);

        if (move.lengthSq() > 0) {
          move.normalize();
          state.camera.position.addScaledVector(move, speed);
          state.camera.position.x = Math.max(-110, Math.min(110, state.camera.position.x));
          state.camera.position.z = Math.max(-110, Math.min(110, state.camera.position.z));
        }

        // Adaptive natural rolling terrain height: central bowl with outer slope
        const r = Math.sqrt(state.camera.position.x ** 2 + state.camera.position.z ** 2);
        const groundY = Math.sin(state.camera.position.x * 0.04) * 1.5 + Math.cos(state.camera.position.z * 0.04) * 1.2 + (r > 35 ? (r - 35) * 0.08 : 0);
        state.camera.position.y = THREE.MathUtils.lerp(state.camera.position.y, groundY + 1.8, 0.2);

        // First-person look direction from yaw & pitch
        const lookTarget = new THREE.Vector3(
          state.camera.position.x - Math.sin(state.yaw) * Math.cos(state.pitch) * 10,
          state.camera.position.y + Math.sin(state.pitch) * 10,
          state.camera.position.z - Math.cos(state.yaw) * Math.cos(state.pitch) * 10
        );
        state.camera.lookAt(lookTarget);
      } else if (state.activeCamView === 'drone_orbit') {
        state.orbitAngle += delta * 0.12;
        const orbitRadius = 115;
        state.camera.position.x = Math.sin(state.orbitAngle) * orbitRadius;
        state.camera.position.z = Math.cos(state.orbitAngle) * orbitRadius;
        state.camera.position.y = 55 + Math.sin(state.orbitAngle * 0.5) * 8;
        state.camera.lookAt(0, 4, 0);
      } else {
        state.camera.position.lerp(state.targetCamPos, 0.05);
        state.camera.lookAt(state.targetLookAt);
      }"""

# 5. Cleanup in useEffect
clean_target = """    return () => {
      window.removeEventListener('resize', onResize);
      renderer.domElement.removeEventListener('pointerdown', onPointerDown);
      if (sceneRefs.current.animFrameId) {
        cancelAnimationFrame(sceneRefs.current.animFrameId);
      }
      renderer.dispose();
      container.innerHTML = '';
    };"""

clean_repl = """    return () => {
      window.removeEventListener('resize', onResize);
      renderer.domElement.removeEventListener('pointerdown', onPointerDown);
      window.removeEventListener('pointermove', onPointerMove);
      window.removeEventListener('pointerup', onPointerUp);
      window.removeEventListener('keydown', onKeyDown);
      window.removeEventListener('keyup', onKeyUp);
      if (sceneRefs.current.animFrameId) {
        cancelAnimationFrame(sceneRefs.current.animFrameId);
      }
      renderer.dispose();
      container.innerHTML = '';
    };"""

# 6. flyToWaypoint helper update to sync sceneRefs.current.activeCamView
fly_target = """  const flyToWaypoint = (wpId) => {
    setActiveCamView(wpId);
    const wp = waypoints.find(w => w.id === wpId) || waypoints[0];
    setSelectedHotspot(wp);

    if (sceneRefs.current.camera) {
      sceneRefs.current.targetCamPos = wp.pos.clone();
      sceneRefs.current.targetLookAt = wp.lookAt.clone();
    }
  };"""

fly_repl = """  const flyToWaypoint = (wpId) => {
    setActiveCamView(wpId);
    setIsGroundWalk(false);
    sceneRefs.current.isGroundWalk = false;
    sceneRefs.current.activeCamView = wpId;
    const wp = waypoints.find(w => w.id === wpId) || waypoints[0];
    setSelectedHotspot(wp);

    if (sceneRefs.current.camera) {
      sceneRefs.current.targetCamPos = wp.pos.clone();
      sceneRefs.current.targetLookAt = wp.lookAt.clone();
    }
  };

  const toggleGroundWalk = (enable) => {
    const nextVal = typeof enable === 'boolean' ? enable : !isGroundWalk;
    setIsGroundWalk(nextVal);
    setIsAutoTouring(false);
    sceneRefs.current.isGroundWalk = nextVal;
    if (nextVal) {
      if (sceneRefs.current.camera) {
        sceneRefs.current.camera.position.set(0, 2.5, 30);
        sceneRefs.current.yaw = 0;
        sceneRefs.current.pitch = 0.05;
      }
    } else {
      flyToWaypoint(activeCamView || 'drone_orbit');
    }
  };

  const setMoveKey = (key, val) => {
    if (sceneRefs.current.keys) {
      sceneRefs.current.keys[key] = val;
    }
  };"""

# 7. Toolbar button for Ground Walk
btn_target = """          {/* 3D Splat Cloud Toggle */}
          <button
            onClick={() => setShowSplatCloud(!showSplatCloud)}"""

btn_repl = """          {/* First-Person Ground Walk Mode Toggle */}
          <button
            onClick={() => toggleGroundWalk()}
            style={{
              background: isGroundWalk ? 'linear-gradient(135deg, rgba(16, 185, 129, 0.35), rgba(0, 255, 255, 0.35))' : 'rgba(255, 255, 255, 0.05)',
              border: isGroundWalk ? '1px solid #10b981' : '1px solid rgba(255, 255, 255, 0.15)',
              color: isGroundWalk ? '#ffffff' : '#94a3b8',
              padding: '6px 14px',
              borderRadius: '8px',
              cursor: 'pointer',
              fontWeight: 800,
              fontSize: '0.78rem',
              boxShadow: isGroundWalk ? '0 0 14px rgba(16, 185, 129, 0.4)' : 'none',
              display: 'flex',
              alignItems: 'center',
              gap: '6px'
            }}
          >
            🚶 First-Person Walk: {isGroundWalk ? 'ON (1.8m)' : 'OFF'}
          </button>

          {/* 3D Splat Cloud Toggle */}
          <button
            onClick={() => setShowSplatCloud(!showSplatCloud)}"""

# 8. 3D Canvas wrapper with Onscreen D-Pad and Top Telemetry HUD
canvas_target = """      {/* 3D WebGL Canvas Container */}
      <div
        ref={mountRef}
        style={{
          width: '100%',
          height: '520px',
          borderRadius: '10px',
          overflow: 'hidden',
          position: 'relative',
          cursor: 'grab',
          boxShadow: 'inset 0 0 25px rgba(0,0,0,0.8)',
          border: '1px solid rgba(0, 255, 255, 0.3)'
        }}
      />"""

canvas_repl = """      {/* 3D WebGL Canvas Container with First-Person Overlays */}
      <div style={{ position: 'relative', width: '100%', borderRadius: '10px', overflow: 'hidden' }}>
        <div
          ref={mountRef}
          style={{
            width: '100%',
            height: '520px',
            borderRadius: '10px',
            overflow: 'hidden',
            position: 'relative',
            cursor: isGroundWalk ? 'crosshair' : 'grab',
            boxShadow: 'inset 0 0 25px rgba(0,0,0,0.8)',
            border: isGroundWalk ? '1px solid #10b981' : '1px solid rgba(0, 255, 255, 0.3)'
          }}
        />

        {/* First-Person HUD Guidance Banner */}
        {isGroundWalk && (
          <div style={{
            position: 'absolute',
            top: '16px',
            left: '16px',
            background: 'rgba(13, 17, 23, 0.88)',
            border: '1px solid rgba(16, 185, 129, 0.6)',
            borderRadius: '8px',
            padding: '10px 16px',
            zIndex: 10,
            backdropFilter: 'blur(8px)',
            boxShadow: '0 4px 20px rgba(0,0,0,0.6)',
            fontSize: '0.78rem',
            color: '#ffffff'
          }}>
            <div style={{ color: '#10b981', fontWeight: 800, marginBottom: '4px', display: 'flex', alignItems: 'center', gap: '8px' }}>
              <span>🚶 FIRST-PERSON GROUND WALK MODE ACTIVE</span>
              <span style={{ fontSize: '0.68rem', background: 'rgba(16, 185, 129, 0.25)', color: '#34d399', padding: '1px 6px', borderRadius: '4px' }}>
                EYE LEVEL: 1.8m
              </span>
            </div>
            <div style={{ color: '#cbd5e1', fontSize: '0.72rem', lineHeight: 1.4 }}>
              ⌨️ <b style={{ color: '#ffffff' }}>[W, A, S, D]</b> or <b style={{ color: '#ffffff' }}>[Arrow Keys]</b> to walk • <b style={{ color: '#ffffff' }}>Drag mouse / touch</b> to look • <b style={{ color: '#ffffff' }}>[Shift]</b> Sprint
            </div>
          </div>
        )}

        {/* On-screen Directional D-Pad for Touch / Mobile & Mouse Walkers */}
        {isGroundWalk && (
          <div style={{
            position: 'absolute',
            bottom: '20px',
            right: '20px',
            background: 'rgba(13, 17, 23, 0.9)',
            border: '1px solid rgba(16, 185, 129, 0.5)',
            borderRadius: '12px',
            padding: '12px',
            display: 'flex',
            flexDirection: 'column',
            alignItems: 'center',
            gap: '8px',
            zIndex: 10,
            backdropFilter: 'blur(8px)',
            boxShadow: '0 4px 24px rgba(0,0,0,0.7)'
          }}>
            <div style={{ fontSize: '0.68rem', color: '#10b981', fontWeight: 800, letterSpacing: '0.5px' }}>
              GROUND D-PAD
            </div>
            <div style={{ display: 'grid', gridTemplateColumns: 'repeat(3, 38px)', gap: '4px' }}>
              <div />
              <button
                onPointerDown={() => setMoveKey('forward', true)}
                onPointerUp={() => setMoveKey('forward', false)}
                onPointerLeave={() => setMoveKey('forward', false)}
                style={{
                  background: 'rgba(16, 185, 129, 0.25)',
                  border: '1px solid #10b981',
                  color: '#ffffff',
                  borderRadius: '6px',
                  height: '38px',
                  fontSize: '1rem',
                  cursor: 'pointer',
                  fontWeight: 800
                }}
                title="Walk Forward (W / Up Arrow)"
              >
                ▲
              </button>
              <div />
              <button
                onPointerDown={() => setMoveKey('left', true)}
                onPointerUp={() => setMoveKey('left', false)}
                onPointerLeave={() => setMoveKey('left', false)}
                style={{
                  background: 'rgba(16, 185, 129, 0.25)',
                  border: '1px solid #10b981',
                  color: '#ffffff',
                  borderRadius: '6px',
                  height: '38px',
                  fontSize: '1rem',
                  cursor: 'pointer',
                  fontWeight: 800
                }}
                title="Strafe Left (A / Left Arrow)"
              >
                ◀
              </button>
              <button
                onPointerDown={() => setMoveKey('backward', true)}
                onPointerUp={() => setMoveKey('backward', false)}
                onPointerLeave={() => setMoveKey('backward', false)}
                style={{
                  background: 'rgba(16, 185, 129, 0.25)',
                  border: '1px solid #10b981',
                  color: '#ffffff',
                  borderRadius: '6px',
                  height: '38px',
                  fontSize: '1rem',
                  cursor: 'pointer',
                  fontWeight: 800
                }}
                title="Walk Backward (S / Down Arrow)"
              >
                ▼
              </button>
              <button
                onPointerDown={() => setMoveKey('right', true)}
                onPointerUp={() => setMoveKey('right', false)}
                onPointerLeave={() => setMoveKey('right', false)}
                style={{
                  background: 'rgba(16, 185, 129, 0.25)',
                  border: '1px solid #10b981',
                  color: '#ffffff',
                  borderRadius: '6px',
                  height: '38px',
                  fontSize: '1rem',
                  cursor: 'pointer',
                  fontWeight: 800
                }}
                title="Strafe Right (D / Right Arrow)"
              >
                ▶
              </button>
            </div>
            <div style={{ display: 'flex', gap: '6px', width: '100%' }}>
              <button
                onClick={() => {
                  const s = sceneRefs.current;
                  if (s.keys) s.keys.sprint = !s.keys.sprint;
                }}
                style={{
                  flex: 1,
                  background: 'rgba(0, 255, 255, 0.2)',
                  border: '1px solid #00FFFF',
                  color: '#00FFFF',
                  borderRadius: '6px',
                  padding: '4px 6px',
                  fontSize: '0.65rem',
                  fontWeight: 800,
                  cursor: 'pointer'
                }}
              >
                ⚡ Sprint
              </button>
              <button
                onClick={() => toggleGroundWalk(false)}
                style={{
                  flex: 1,
                  background: 'rgba(239, 68, 68, 0.25)',
                  border: '1px solid #ef4444',
                  color: '#f87171',
                  borderRadius: '6px',
                  padding: '4px 6px',
                  fontSize: '0.65rem',
                  fontWeight: 800,
                  cursor: 'pointer'
                }}
              >
                ✕ Exit
              </button>
            </div>
          </div>
        )}
      </div>"""

# Perform replacements safely
replacements = [
    (state_target, state_repl, "1: State"),
    (refs_target, refs_repl, "2: Refs"),
    (pointer_target, pointer_repl, "3: Pointer & Keyboard"),
    (anim_target, anim_repl, "4: Animation loop"),
    (clean_target, clean_repl, "5: Cleanup"),
    (fly_target, fly_repl, "6: FlyToWaypoint"),
    (btn_target, btn_repl, "7: Toolbar button"),
    (canvas_target, canvas_repl, "8: Canvas wrapper")
]

for target, repl, label in replacements:
    if target in code:
        code = code.replace(target, repl, 1)
        print(f"✔ Patched {label} (LF)")
    elif target.replace('\n', '\r\n') in code:
        code = code.replace(target.replace('\n', '\r\n'), repl.replace('\n', '\r\n'), 1)
        print(f"✔ Patched {label} (CRLF)")
    else:
        print(f"❌ Failed to find target for {label}")

with open(comp_path, 'w', encoding='utf-8') as f:
    f.write(code)

print("\nNoco3DCampusWalkthrough.jsx patched successfully!")
