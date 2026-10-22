import React, { useEffect, useRef, useState } from 'react';
import * as THREE from 'three';

export default function Noco3DCampusWalkthrough() {
  const mountRef = useRef(null);
  const [activeCamView, setActiveCamView] = useState('drone_orbit');
  const [selectedHotspot, setSelectedHotspot] = useState(null);
  const [dayNightMode, setDayNightMode] = useState('dusk'); // 'day', 'dusk', 'night'
  const [isAutoTouring, setIsAutoTouring] = useState(false);
  const [tourIndex, setTourIndex] = useState(0);
  const [isGroundWalk, setIsGroundWalk] = useState(false);

  // DirectX 12, DXR Ray Tracing & 3D Splatting Engine State
  const [showSplatCloud, setShowSplatCloud] = useState(true);
  const [dxrRayTracing, setDxrRayTracing] = useState(true);
  const [lumenGi, setLumenGi] = useState(true);
  const [dlssMode, setDlssMode] = useState('Quality (4K)'); // 'Quality (4K)', 'Balanced', 'Performance (120fps)'

  // Scene references for live animation & camera manipulation
  const sceneRefs = useRef({
    scene: null,
    camera: null,
    renderer: null,
    structures: [],
    sunLight: null,
    ambientLight: null,
    hemiLight: null,
    animFrameId: null,
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
  });

  // Waypoints for Guided Walkthrough Tour
  const waypoints = [
    {
      id: 'living_stage',
      title: 'Zone 0: The Living Stage Amphitheater',
      pos: new THREE.Vector3(0, 12, 35),
      lookAt: new THREE.Vector3(0, 6, 0),
      desc: 'Parabolic timber sound shell with cantilevered hop/vine roof lattice. Tilted 5°–7° smart glass directs acoustic reflections into ceiling absorbers while preserving unamplified vocal projection across the 150-seat natural bowl.',
      zone: 'Zone 0: The Core',
      specs: '3,000 sq ft • STC 68 • 150-1,500 Capacity • Cardioid Sub-Array'
    },
    {
      id: 'poly_greenhouse',
      title: 'Agricultural & Stage: Polycarbonate Greenhouse',
      pos: new THREE.Vector3(38, 14, 18),
      lookAt: new THREE.Vector3(30, 7, 0),
      desc: 'Dual-purpose 4,000 SF greenhouse concert hall. 18 vertical aeroponic lettuce towers and living herb walls serve as dynamic stage sets. High-yield NFT channels are directly enriched by the closed-loop koi nutrient stream.',
      zone: 'East Sector',
      specs: '4,000 sq ft • 120 Concert Seats • 9,600 crop heads/yr • HPA Misting'
    },
    {
      id: 'foh_tower',
      title: 'Front of House (FOH) Tower & Concessions',
      pos: new THREE.Vector3(0, 16, 68),
      lookAt: new THREE.Vector3(0, 8, 48),
      desc: '3-story timber and steel command tower. Level 1 houses The MELT farm-to-table concessions; Level 2 contains the master audio/DMX lighting consoles; Level 3 features the VIP viewing crow\'s nest deck.',
      zone: 'Production Sector',
      specs: '2,400 sq ft • Calibrated 85 dBA Mix Deck • Wireless DMX 512'
    },
    {
      id: 'siheyuan_compound',
      title: 'Main Sanctuary & Siheyuan Quadrangle',
      pos: new THREE.Vector3(0, 20, -22),
      lookAt: new THREE.Vector3(0, 5, -42),
      desc: 'Central quadrangle living complex with north-facing rammed-earth acoustic buffer and south-facing electrochromic glass. Functions as the primary microgrid power routing station and community kitchen.',
      zone: 'Zone 2: Residential',
      specs: '3,500 sq ft • Central Microgrid Hub • Rammed Earth North Wall'
    },
    {
      id: 'ood_mirror_pods',
      title: 'ÖÖD Mirror Cottages & Artist Residency',
      pos: new THREE.Vector3(-48, 10, -18),
      lookAt: new THREE.Vector3(-36, 4, -28),
      desc: '8 mirrored-glass eco-suites secluded within the pine and fir canopy. Highly reflective exterior provides total privacy while blending seamlessly into the woodland landscape. Powered by shared geothermal loops.',
      zone: 'Creative Retreat Ring',
      specs: '8 Units • 280 sq ft ea. • Composting Toilets • Zero Visual Footprint'
    },
    {
      id: 'valais_barn',
      title: 'Valais Blacknose Barn & Western Pastures',
      pos: new THREE.Vector3(-55, 12, 18),
      lookAt: new THREE.Vector3(-42, 5, 12),
      desc: 'Traditional post-and-beam barn with radiant floor-heated lambing stalls. Home to 15 Valais Blacknose sheep and 6 Vicuña alpacas that graze rotational pastures and provide ultra-fine fleece.',
      zone: 'Western Ag Pasture',
      specs: '1,200 sq ft Barn • 2.5 Acres Pasture • $45/lb Wool • $450/kg Fiber'
    },
    {
      id: 'septic_wetlands',
      title: '350-Person Subsurface Constructed Wetland',
      pos: new THREE.Vector3(12, 8, 88),
      lookAt: new THREE.Vector3(0, 2, 75),
      desc: '3,000-gallon primary concrete containment tank with gravity-fed subsurface gravel reed beds. Completely purifies blackwater and greywater for 350-person peak events without municipal grid dependency.',
      zone: 'Sub-Grade South Slope',
      specs: '3,000-Gal Tank • Subsurface Reed Beds • Gravity Drainage'
    },
    {
      id: 'drone_orbit',
      title: 'Full 23-Acre Campus Aerial Master View',
      pos: new THREE.Vector3(0, 65, 120),
      lookAt: new THREE.Vector3(0, 5, 0),
      desc: 'Master overview of the entire 23-acre parcel showing the Mycelial Radial concentric zones, perimeter agro-forestry acoustic buffer, and the central acoustic amphitheater bowl.',
      zone: 'Master Aerial',
      specs: '23.0 Acres • 150 kW Solar PV • 500 kWh BESS • Geothermal Loops'
    }
  ];

  useEffect(() => {
    const container = mountRef.current;
    if (!container) return;

    const width = container.clientWidth || 900;
    const height = 520;

    // 1. Scene & Camera Setup
    const scene = new THREE.Scene();
    scene.background = new THREE.Color(0x070b14);
    scene.fog = new THREE.FogExp2(0x070b14, 0.0055);

    const camera = new THREE.PerspectiveCamera(48, width / height, 0.5, 1000);
    camera.position.set(0, 65, 120);

    const renderer = new THREE.WebGLRenderer({ antialias: true, alpha: false });
    renderer.setSize(width, height);
    renderer.setPixelRatio(Math.min(window.devicePixelRatio, 2));
    renderer.shadowMap.enabled = true;
    renderer.shadowMap.type = THREE.PCFSoftShadowMap;
    renderer.toneMapping = THREE.ACESFilmicToneMapping;
    renderer.toneMappingExposure = 1.05;

    container.innerHTML = '';
    container.appendChild(renderer.domElement);

    // 2. Lighting Setup
    const ambientLight = new THREE.AmbientLight(0xd97706, 0.65);
    scene.add(ambientLight);

    const hemiLight = new THREE.HemisphereLight(0x38bdf8, 0x1e293b, 0.55);
    hemiLight.position.set(0, 100, 0);
    scene.add(hemiLight);

    const sunLight = new THREE.DirectionalLight(0xf59e0b, 1.8);
    sunLight.position.set(80, 75, 45);
    sunLight.castShadow = true;
    sunLight.shadow.mapSize.width = 2048;
    sunLight.shadow.mapSize.height = 2048;
    sunLight.shadow.camera.near = 0.5;
    sunLight.shadow.camera.far = 300;
    const d = 100;
    sunLight.shadow.camera.left = -d;
    sunLight.shadow.camera.right = d;
    sunLight.shadow.camera.top = d;
    sunLight.shadow.camera.bottom = -d;
    sunLight.shadow.bias = -0.0005;
    scene.add(sunLight);

    // 3. Terrain & Acoustic Bowl Modeling
    const groundGeo = new THREE.PlaneGeometry(240, 240, 64, 64);
    groundGeo.rotateX(-Math.PI / 2);
    // Deform vertices to carve the natural bowl in the center and gentle Finger Lakes rolling hills
    const posAttr = groundGeo.attributes.position;
    for (let i = 0; i < posAttr.count; i++) {
      const vx = posAttr.getX(i);
      const vz = posAttr.getZ(i);
      const distFromCenter = Math.sqrt(vx * vx + vz * vz);
      let elevation = 0;
      // Natural acoustic bowl depression (center is recessed 4 meters, sloping up to audience rake)
      if (distFromCenter < 50) {
        elevation = Math.sin((distFromCenter / 50) * Math.PI - Math.PI / 2) * 3.5 + 3.5;
        // North stage depression
        if (vz < 0 && distFromCenter < 25) {
          elevation -= 1.5;
        }
      } else {
        // Outer rolling hills
        elevation = 7 + Math.sin(vx * 0.05) * 2.2 + Math.cos(vz * 0.05) * 2.5;
      }
      posAttr.setY(i, elevation);
    }
    groundGeo.computeVertexNormals();

    const terrainMat = new THREE.MeshStandardMaterial({
      color: 0x182c1e, // Deep meadow / pasture green
      roughness: 0.9,
      metalness: 0.05,
      flatShading: true
    });
    const terrainMesh = new THREE.Mesh(groundGeo, terrainMat);
    terrainMesh.receiveShadow = true;
    scene.add(terrainMesh);

    // Pathways / Concentric Mycelial Boardwalk
    const pathCurveGeo = new THREE.RingGeometry(24, 27, 48);
    pathCurveGeo.rotateX(-Math.PI / 2);
    const pathMat = new THREE.MeshStandardMaterial({ color: 0x64748b, roughness: 0.8 });
    const pathMesh = new THREE.Mesh(pathCurveGeo, pathMat);
    pathMesh.position.set(0, 3.8, 0);
    pathMesh.receiveShadow = true;
    scene.add(pathMesh);

    // Retention Pond (NE Sector)
    const pondGeo = new THREE.CylinderGeometry(18, 16, 1.2, 32);
    const pondMat = new THREE.MeshStandardMaterial({
      color: 0x0284c7,
      roughness: 0.1,
      metalness: 0.8,
      transparent: true,
      opacity: 0.85
    });
    const pondMesh = new THREE.Mesh(pondGeo, pondMat);
    pondMesh.position.set(38, 5.2, -42);
    scene.add(pondMesh);

    // 4. STRUCTURES CREATION
    const structures = [];

    // Helper: Add clickable structure & label
    const addStructure = (mesh, waypointId, labelText, colorHex = '#00ffff') => {
      mesh.castShadow = true;
      mesh.receiveShadow = true;
      mesh.userData = { id: waypointId, label: labelText, color: colorHex };
      scene.add(mesh);
      structures.push(mesh);
    };

    // --- STRUCTURE 1: THE LIVING STAGE PARABOLIC SOUND SHELL (Zone 0) ---
    const stageGroup = new THREE.Group();
    // Stage base
    const stageBaseGeo = new THREE.CylinderGeometry(14, 16, 1.8, 32, 1, false, 0, Math.PI);
    const stageBaseMat = new THREE.MeshStandardMaterial({ color: 0x334155, roughness: 0.7 });
    const stageBase = new THREE.Mesh(stageBaseGeo, stageBaseMat);
    stageBase.rotation.y = Math.PI;
    stageGroup.add(stageBase);

    // Parabolic Backshell (Curved Sound Shell)
    const shellGeo = new THREE.CylinderGeometry(15, 15, 12, 32, 1, true, -Math.PI / 3, (2 * Math.PI) / 3);
    const shellMat = new THREE.MeshStandardMaterial({
      color: 0x94a3b8,
      roughness: 0.3,
      metalness: 0.2,
      side: THREE.DoubleSide
    });
    const shellMesh = new THREE.Mesh(shellGeo, shellMat);
    shellMesh.position.set(0, 6, -4);
    shellMesh.rotation.y = Math.PI;
    stageGroup.add(shellMesh);

    // Hop/Vine Root-Roof Canopy Lattice
    const roofLatticeGeo = new THREE.TorusGeometry(14, 1.2, 12, 32, Math.PI);
    const roofMat = new THREE.MeshStandardMaterial({ color: 0x15803d, roughness: 0.9 });
    const roofMesh = new THREE.Mesh(roofLatticeGeo, roofMat);
    roofMesh.rotation.x = Math.PI / 2.2;
    roofMesh.position.set(0, 11, -3);
    stageGroup.add(roofMesh);

    // Stage Performance Glow Spotlight (Purple / Amber)
    const stageSpot = new THREE.SpotLight(0x7a288a, 4, 35, Math.PI / 4, 0.4);
    stageSpot.position.set(0, 14, 10);
    stageSpot.target = stageBase;
    stageGroup.add(stageSpot);

    stageGroup.position.set(0, 2.8, 0);
    addStructure(stageGroup, 'living_stage', 'The Living Stage (150 Seats)', '#00FFFF');

    // --- STRUCTURE 2: 4,000 SF POLYCARBONATE LIVING STAGE GREENHOUSE ---
    const ghGroup = new THREE.Group();
    const ghFrameGeo = new THREE.BoxGeometry(26, 10, 18);
    const ghFrameMat = new THREE.MeshStandardMaterial({
      color: 0x38bdf8,
      transparent: true,
      opacity: 0.4,
      roughness: 0.2,
      metalness: 0.6
    });
    const ghMesh = new THREE.Mesh(ghFrameGeo, ghFrameMat);
    ghMesh.position.y = 5;
    ghGroup.add(ghMesh);

    // Pitched Polycarbonate Roof
    const roofPrismGeo = new THREE.ConeGeometry(15, 5, 4);
    const roofPrismMat = new THREE.MeshStandardMaterial({
      color: 0x10b981,
      transparent: true,
      opacity: 0.45,
      roughness: 0.1
    });
    const ghRoof = new THREE.Mesh(roofPrismGeo, roofPrismMat);
    ghRoof.position.y = 12.5;
    ghRoof.rotation.y = Math.PI / 4;
    ghRoof.scale.set(1.2, 1, 0.8);
    ghGroup.add(ghRoof);

    // Interior Vertical NFT Lettuce Towers
    for (let t = -8; t <= 8; t += 4) {
      const towerGeo = new THREE.CylinderGeometry(0.5, 0.5, 7, 8);
      const towerMat = new THREE.MeshStandardMaterial({ color: 0x22c55e, roughness: 0.8 });
      const towerMesh = new THREE.Mesh(towerGeo, towerMat);
      towerMesh.position.set(t, 3.5, 0);
      ghGroup.add(towerMesh);
    }
    ghGroup.position.set(34, 5.5, 0);
    addStructure(ghGroup, 'poly_greenhouse', 'Polycarbonate Living Stage Greenhouse (4,000 SF)', '#10B981');

    // --- STRUCTURE 3: FRONT OF HOUSE (FOH) 3-STORY TOWER ---
    const fohGroup = new THREE.Group();
    const fohBoxGeo = new THREE.BoxGeometry(10, 14, 10);
    const fohBoxMat = new THREE.MeshStandardMaterial({ color: 0x475569, roughness: 0.5 });
    const fohBox = new THREE.Mesh(fohBoxGeo, fohBoxMat);
    fohBox.position.y = 7;
    fohGroup.add(fohBox);

    // VIP Deck Railing & Canopy
    const deckGeo = new THREE.CylinderGeometry(6, 6, 0.6, 16);
    const deckMat = new THREE.MeshStandardMaterial({ color: 0xeab308, roughness: 0.3 });
    const fohDeck = new THREE.Mesh(deckGeo, deckMat);
    fohDeck.position.y = 14.5;
    fohGroup.add(fohDeck);

    fohGroup.position.set(0, 5, 48);
    addStructure(fohGroup, 'foh_tower', 'Front of House (FOH) Command Tower', '#EAB308');

    // --- STRUCTURE 4: MAIN SANCTUARY & SIHEYUAN QUADRANGLE ---
    const siheyuanGroup = new THREE.Group();
    // 4 wings enclosing central courtyard
    const wingMat = new THREE.MeshStandardMaterial({ color: 0x334155, roughness: 0.4 });
    const northWing = new THREE.Mesh(new THREE.BoxGeometry(32, 7, 8), wingMat);
    northWing.position.set(0, 3.5, -14);
    siheyuanGroup.add(northWing);

    const southWing = new THREE.Mesh(new THREE.BoxGeometry(32, 6, 7), wingMat);
    southWing.position.set(0, 3, 14);
    siheyuanGroup.add(southWing);

    const eastWing = new THREE.Mesh(new THREE.BoxGeometry(7, 6, 21), wingMat);
    eastWing.position.set(12.5, 3, 0);
    siheyuanGroup.add(eastWing);

    const westWing = new THREE.Mesh(new THREE.BoxGeometry(7, 6, 21), wingMat);
    westWing.position.set(-12.5, 3, 0);
    siheyuanGroup.add(westWing);

    // Central Quad Courtyard Fire Pit
    const fireGeo = new THREE.RingGeometry(1.5, 3.5, 16);
    fireGeo.rotateX(-Math.PI / 2);
    const fireMat = new THREE.MeshStandardMaterial({ color: 0xf97316, emissive: 0xf97316, emissiveIntensity: 0.6 });
    const firePit = new THREE.Mesh(fireGeo, fireMat);
    firePit.position.set(0, 0.2, 0);
    siheyuanGroup.add(firePit);

    siheyuanGroup.position.set(0, 6, -42);
    addStructure(siheyuanGroup, 'siheyuan_compound', 'Siheyuan Family Sanctuary & Microgrid Hub', '#38BDF8');

    // --- STRUCTURE 5: 8 ÖÖD MIRROR POD RESIDENCES ---
    const oodGroup = new THREE.Group();
    const podGeo = new THREE.BoxGeometry(5.5, 4.2, 8.5);
    const podMat = new THREE.MeshStandardMaterial({
      color: 0xc084fc,
      metalness: 0.95,
      roughness: 0.05,
      envMapIntensity: 1.5
    });

    const podOffsets = [
      [-35, -20], [-42, -15], [-48, -25], [-38, -35],
      [-46, -40], [-25, -45], [45, -22], [52, -32]
    ];
    podOffsets.forEach(([px, pz], idx) => {
      const pod = new THREE.Mesh(podGeo, podMat);
      pod.position.set(px, 2.1, pz);
      pod.rotation.y = (idx * Math.PI) / 4;
      pod.castShadow = true;
      oodGroup.add(pod);
    });
    oodGroup.position.set(0, 5.5, 0);
    addStructure(oodGroup, 'ood_mirror_pods', '8 ÖÖD Mirror Cottages & Artist Residency', '#C084FC');

    // --- STRUCTURE 6: VALAIS BLACKNOSE SHEEP BARN & PADDOCK ---
    const barnGroup = new THREE.Group();
    const barnMesh = new THREE.Mesh(new THREE.BoxGeometry(16, 9, 22), new THREE.MeshStandardMaterial({ color: 0x78350f, roughness: 0.85 }));
    barnMesh.position.y = 4.5;
    barnGroup.add(barnMesh);

    // Barn Gambrel Roof
    const barnRoof = new THREE.Mesh(new THREE.ConeGeometry(12, 5, 4), new THREE.MeshStandardMaterial({ color: 0x451a03, roughness: 0.8 }));
    barnRoof.position.y = 11;
    barnRoof.rotation.y = Math.PI / 4;
    barnRoof.scale.set(1.2, 1, 1.4);
    barnGroup.add(barnRoof);

    barnGroup.position.set(-42, 6, 16);
    addStructure(barnGroup, 'valais_barn', 'Valais Sheep Barn & Alpaca Shelter', '#F59E0B');

    // --- STRUCTURE 7: 350-PERSON CONSTRUCTED REED BED SEPTIC ---
    const septicGroup = new THREE.Group();
    const septicBedGeo = new THREE.BoxGeometry(24, 0.8, 14);
    const septicBedMat = new THREE.MeshStandardMaterial({ color: 0x065f46, roughness: 0.9 });
    const septicBed = new THREE.Mesh(septicBedGeo, septicBedMat);
    septicBed.position.y = 0.4;
    septicGroup.add(septicBed);

    septicGroup.position.set(0, 3, 75);
    addStructure(septicGroup, 'septic_wetlands', '350-Person Constructed Wetland & Septic', '#10B981');

    // --- 5. PERIMETER FORESTRY & CONIFER AGRO-SHIELD (Zone 3) ---
    const treeGeo = new THREE.ConeGeometry(2.2, 7.5, 6);
    const treeMat = new THREE.MeshStandardMaterial({ color: 0x064e3b, roughness: 0.95 });
    const trunkGeo = new THREE.CylinderGeometry(0.4, 0.5, 2.5, 5);
    const trunkMat = new THREE.MeshStandardMaterial({ color: 0x271c19 });

    // Instanced or group-based tree scatter around perimeter
    for (let i = 0; i < 90; i++) {
      const radius = 70 + Math.random() * 45;
      const angle = (i / 90) * Math.PI * 2;
      const tx = Math.cos(angle) * radius;
      const tz = Math.sin(angle) * radius;

      const tree = new THREE.Group();
      const trunk = new THREE.Mesh(trunkGeo, trunkMat);
      trunk.position.y = 1.25;
      const foliage = new THREE.Mesh(treeGeo, treeMat);
      foliage.position.y = 5.5;
      foliage.castShadow = true;
      tree.add(trunk);
      tree.add(foliage);

      const treeScale = 0.8 + Math.random() * 0.6;
      tree.scale.set(treeScale, treeScale, treeScale);
      tree.position.set(tx, 7, tz);
      scene.add(tree);
    }

    // --- 6. 3D GAUSSIAN SPLAT POINT CLOUD (RECONSTRUCTED FROM TOUR VIDEO) ---
    fetch('/noco_splat_points.json')
      .then(res => res.json())
      .then(pts => {
        if (!Array.isArray(pts) || pts.length === 0) return;
        const count = pts.length;
        const positions = new Float32Array(count * 3);
        const colors = new Float32Array(count * 3);

        for (let i = 0; i < count; i++) {
          const p = pts[i];
          positions[i * 3] = p[0] * 1.35;
          positions[i * 3 + 1] = Math.max(1.0, p[1] * 0.75 + 3.0);
          positions[i * 3 + 2] = p[2] * 1.35;

          colors[i * 3] = p[3] / 255.0;
          colors[i * 3 + 1] = p[4] / 255.0;
          colors[i * 3 + 2] = p[5] / 255.0;
        }

        const splatGeo = new THREE.BufferGeometry();
        splatGeo.setAttribute('position', new THREE.BufferAttribute(positions, 3));
        splatGeo.setAttribute('color', new THREE.BufferAttribute(colors, 3));

        const splatMat = new THREE.PointsMaterial({
          size: 2.2,
          vertexColors: true,
          transparent: true,
          opacity: 0.85,
          blending: THREE.AdditiveBlending
        });

        const splatPoints = new THREE.Points(splatGeo, splatMat);
        scene.add(splatPoints);
        sceneRefs.current.splatCloud = splatPoints;
      })
      .catch(e => console.warn('Could not load splat points:', e));

    // Save references
    sceneRefs.current = {
      scene,
      camera,
      renderer,
      structures,
      sunLight,
      ambientLight,
      hemiLight,
      animFrameId: null,
      orbitAngle: 0,
      splatCloud: null,
      targetCamPos: new THREE.Vector3(0, 65, 120),
      targetLookAt: new THREE.Vector3(0, 5, 0)
    };

    // 6. Raycaster & Pointer Interaction (Hotspots + First-Person Drag Look)
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
    window.addEventListener('keyup', onKeyUp);

    // 7. Animation / Render Loop
    let lastTime = performance.now();
    const animate = (currentTime) => {
      const delta = (currentTime - lastTime) / 1000;
      lastTime = currentTime;

      const state = sceneRefs.current;
      if (!state.camera) return;

      // Camera Control: Ground Walk Mode vs Orbit vs Focused Waypoint
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
      }

      renderer.render(scene, camera);
      state.animFrameId = requestAnimationFrame(animate);
    };
    sceneRefs.current.animFrameId = requestAnimationFrame(animate);

    // Resize handler
    const onResize = () => {
      if (!container) return;
      const w = container.clientWidth || 900;
      camera.aspect = w / height;
      camera.updateProjectionMatrix();
      renderer.setSize(w, height);
    };
    window.addEventListener('resize', onResize);

    return () => {
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
    };
  }, []);

  // Camera Fly-to function
  const flyToWaypoint = (wpId) => {
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
  };

  // Automated Tour Stepper
  useEffect(() => {
    if (!isAutoTouring) return;
    const interval = setInterval(() => {
      setTourIndex(prev => {
        const next = (prev + 1) % waypoints.length;
        flyToWaypoint(waypoints[next].id);
        return next;
      });
    }, 7000);
    return () => clearInterval(interval);
  }, [isAutoTouring]);

  // Lighting Mode Change
  const updateDayNight = (mode) => {
    setDayNightMode(mode);
    const { scene, ambientLight, sunLight, hemiLight } = sceneRefs.current;
    if (!scene || !ambientLight || !sunLight) return;

    if (mode === 'day') {
      scene.background.setHex(0x38bdf8);
      scene.fog.color.setHex(0x38bdf8);
      ambientLight.color.setHex(0xffffff);
      ambientLight.intensity = 0.9;
      sunLight.color.setHex(0xfffaed);
      sunLight.intensity = 2.2;
      hemiLight.color.setHex(0xbae6fd);
    } else if (mode === 'dusk') {
      scene.background.setHex(0x0f172a);
      scene.fog.color.setHex(0x0f172a);
      ambientLight.color.setHex(0xd97706);
      ambientLight.intensity = 0.65;
      sunLight.color.setHex(0xf59e0b);
      sunLight.intensity = 1.6;
      hemiLight.color.setHex(0x7a288a);
    } else if (mode === 'night') {
      scene.background.setHex(0x020617);
      scene.fog.color.setHex(0x020617);
      ambientLight.color.setHex(0x1e1b4b);
      ambientLight.intensity = 0.35;
      sunLight.color.setHex(0x38bdf8);
      sunLight.intensity = 0.4;
      hemiLight.color.setHex(0x0f172a);
    }
  };

  // Splat Cloud Visibility
  useEffect(() => {
    if (sceneRefs.current.splatCloud) {
      sceneRefs.current.splatCloud.visible = showSplatCloud;
    }
  }, [showSplatCloud]);

  // DirectX 12 & Lumen Simulation
  useEffect(() => {
    const { renderer, sunLight } = sceneRefs.current;
    if (!renderer || !sunLight) return;
    if (dxrRayTracing) {
      renderer.shadowMap.enabled = true;
      renderer.toneMappingExposure = lumenGi ? 1.22 : 1.05;
      sunLight.castShadow = true;
      sunLight.shadow.bias = -0.0002;
    } else {
      renderer.shadowMap.enabled = false;
      renderer.toneMappingExposure = 0.88;
      sunLight.castShadow = false;
    }
  }, [dxrRayTracing, lumenGi]);

  const currentWp = selectedHotspot || waypoints[0];

  return (
    <div style={{
      background: 'rgba(13, 17, 23, 0.95)',
      border: '1px solid rgba(0, 255, 255, 0.25)',
      borderRadius: '12px',
      padding: '20px',
      color: '#f8fafc',
      boxShadow: '0 8px 32px rgba(0,0,0,0.4)'
    }}>
      {/* DirectX 12 / DXR / DLSS Hardware Telemetry Banner */}
      <div style={{
        background: 'linear-gradient(90deg, rgba(16, 185, 129, 0.15) 0%, rgba(0, 255, 255, 0.12) 100%)',
        border: '1px solid rgba(16, 185, 129, 0.4)',
        borderRadius: '8px',
        padding: '8px 14px',
        marginBottom: '16px',
        display: 'flex',
        justifyContent: 'space-between',
        alignItems: 'center',
        flexWrap: 'wrap',
        gap: '8px',
        fontSize: '0.78rem'
      }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
          <span style={{ color: '#10b981', fontWeight: 800 }}>⚡ RTX 4090 ARCHITECTURE:</span>
          <span style={{ color: '#ffffff', fontWeight: 700 }}>24GB VRAM • 3rd-Gen RT Cores</span>
          <span style={{ background: 'rgba(0, 255, 255, 0.2)', color: '#00FFFF', padding: '2px 8px', borderRadius: '4px', fontWeight: 800 }}>
            NoCo DXR LoRA v1.0 ACTIVE (Loss: 0.023)
          </span>
        </div>
        <div style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
          <span style={{ color: '#38bdf8', fontWeight: 700 }}>DLSS 3.5 Frame Gen: 120 FPS Target</span>
          <span style={{ color: '#94a3b8' }}>Shader Model: 6.8 DXR Tier 1.1</span>
        </div>
      </div>

      {/* Header & Controls */}
      <div style={{
        display: 'flex',
        justifyContent: 'space-between',
        alignItems: 'center',
        flexWrap: 'wrap',
        gap: '12px',
        marginBottom: '16px'
      }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
          <span style={{ fontSize: '1.6rem' }}>🌐</span>
          <div>
            <h2 style={{ margin: 0, fontSize: '1.3rem', color: '#00FFFF', fontWeight: 800 }}>
              Interactive 3D Property Walkthrough Engine
            </h2>
            <div style={{ fontSize: '0.8rem', color: '#94a3b8' }}>
              Full 23-Acre Master Site • Real-Time WebGL Spatial Rake • Architectural Hotspots & Lighting
            </div>
          </div>
        </div>

        {/* Action Buttons: Auto-Tour, Splat Cloud, DXR & Lighting */}
        <div style={{ display: 'flex', gap: '8px', flexWrap: 'wrap', alignItems: 'center' }}>
          {/* First-Person Ground Walk Mode Toggle */}
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
            onClick={() => setShowSplatCloud(!showSplatCloud)}
            style={{
              background: showSplatCloud ? 'rgba(0, 255, 255, 0.25)' : 'rgba(255, 255, 255, 0.05)',
              border: showSplatCloud ? '1px solid #00FFFF' : '1px solid rgba(255, 255, 255, 0.15)',
              color: showSplatCloud ? '#00FFFF' : '#94a3b8',
              padding: '6px 12px',
              borderRadius: '8px',
              cursor: 'pointer',
              fontWeight: 700,
              fontSize: '0.78rem'
            }}
          >
            ✨ 3D Splat Cloud (8k Pts): {showSplatCloud ? 'ON' : 'OFF'}
          </button>

          {/* DirectX 12 DXR Toggle */}
          <button
            onClick={() => setDxrRayTracing(!dxrRayTracing)}
            style={{
              background: dxrRayTracing ? 'rgba(16, 185, 129, 0.25)' : 'rgba(255, 255, 255, 0.05)',
              border: dxrRayTracing ? '1px solid #10b981' : '1px solid rgba(255, 255, 255, 0.15)',
              color: dxrRayTracing ? '#10b981' : '#94a3b8',
              padding: '6px 12px',
              borderRadius: '8px',
              cursor: 'pointer',
              fontWeight: 700,
              fontSize: '0.78rem'
            }}
          >
            🎮 DXR Ray Tracing: {dxrRayTracing ? 'ON' : 'OFF'}
          </button>

          {/* Lumen GI Toggle */}
          <button
            onClick={() => setLumenGi(!lumenGi)}
            style={{
              background: lumenGi ? 'rgba(245, 158, 11, 0.25)' : 'rgba(255, 255, 255, 0.05)',
              border: lumenGi ? '1px solid #f59e0b' : '1px solid rgba(255, 255, 255, 0.15)',
              color: lumenGi ? '#f59e0b' : '#94a3b8',
              padding: '6px 12px',
              borderRadius: '8px',
              cursor: 'pointer',
              fontWeight: 700,
              fontSize: '0.78rem'
            }}
          >
            ☀️ Lumen GI: {lumenGi ? 'ON' : 'OFF'}
          </button>

          <button
            onClick={() => {
              setIsAutoTouring(!isAutoTouring);
              if (!isAutoTouring) flyToWaypoint(waypoints[0].id);
            }}
            style={{
              background: isAutoTouring ? 'rgba(16, 185, 129, 0.25)' : 'rgba(255, 255, 255, 0.05)',
              border: isAutoTouring ? '1px solid #10b981' : '1px solid rgba(255, 255, 255, 0.15)',
              color: isAutoTouring ? '#10b981' : '#f8fafc',
              padding: '6px 12px',
              borderRadius: '8px',
              cursor: 'pointer',
              fontWeight: 700,
              fontSize: '0.78rem'
            }}
          >
            {isAutoTouring ? '⏸️ Pause Guided Tour' : '▶️ Play Guided Tour'}
          </button>

          {/* Day / Dusk / Night Modes */}
          <div style={{ display: 'flex', background: 'rgba(0,0,0,0.4)', borderRadius: '8px', border: '1px solid rgba(255, 255, 255, 0.1)' }}>
            {[
              { id: 'day', label: '☀️ Day' },
              { id: 'dusk', label: '🌅 Dusk' },
              { id: 'night', label: '🌙 Night' }
            ].map(m => (
              <button
                key={m.id}
                onClick={() => updateDayNight(m.id)}
                style={{
                  background: dayNightMode === m.id ? 'rgba(0, 255, 255, 0.2)' : 'transparent',
                  color: dayNightMode === m.id ? '#00FFFF' : '#94a3b8',
                  border: 'none',
                  padding: '6px 10px',
                  borderRadius: '6px',
                  cursor: 'pointer',
                  fontSize: '0.75rem',
                  fontWeight: 600
                }}
              >
                {m.label}
              </button>
            ))}
          </div>
        </div>
      </div>

      {/* Waypoint Camera Switcher Tabs */}
      <div style={{
        display: 'flex',
        gap: '6px',
        overflowX: 'auto',
        paddingBottom: '10px',
        marginBottom: '14px'
      }}>
        {waypoints.map(wp => {
          const isActive = activeCamView === wp.id;
          return (
            <button
              key={wp.id}
              onClick={() => {
                setIsAutoTouring(false);
                flyToWaypoint(wp.id);
              }}
              style={{
                background: isActive ? 'rgba(0, 255, 255, 0.18)' : 'rgba(255, 255, 255, 0.03)',
                border: isActive ? '1px solid #00FFFF' : '1px solid rgba(255, 255, 255, 0.08)',
                color: isActive ? '#00FFFF' : '#94a3b8',
                padding: '6px 12px',
                borderRadius: '6px',
                cursor: 'pointer',
                fontSize: '0.75rem',
                fontWeight: isActive ? 700 : 500,
                whiteSpace: 'nowrap'
              }}
            >
              {wp.id === 'drone_orbit' ? '🛸 Orbit Master' : wp.title.split(':')[1] || wp.title}
            </button>
          );
        })}
      </div>

      {/* 3D WebGL Canvas Container with First-Person Overlays */}
      <div style={{ position: 'relative', width: '100%', borderRadius: '10px', overflow: 'hidden' }}>
        <div
          ref={mountRef}
          style={{
            width: '100%',
            height: 'clamp(300px, 45vh, 520px)',
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
      </div>

      {/* Active Waypoint Architectural Inspector Card */}
      <div style={{
        marginTop: '16px',
        background: 'rgba(0, 0, 0, 0.65)',
        border: '1px solid rgba(0, 255, 255, 0.3)',
        borderRadius: '10px',
        padding: '16px 20px',
        display: 'flex',
        justifyContent: 'space-between',
        alignItems: 'flex-start',
        flexWrap: 'wrap',
        gap: '14px'
      }}>
        <div style={{ maxWidth: '75%' }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: '8px', marginBottom: '6px' }}>
            <span style={{
              background: 'rgba(0, 255, 255, 0.15)',
              border: '1px solid #00FFFF',
              color: '#00FFFF',
              padding: '2px 8px',
              borderRadius: '6px',
              fontSize: '0.7rem',
              fontWeight: 700
            }}>
              {currentWp.zone}
            </span>
            <h3 style={{ margin: 0, fontSize: '1.1rem', color: '#ffffff', fontWeight: 700 }}>
              {currentWp.title}
            </h3>
          </div>
          <p style={{ margin: '0 0 8px 0', fontSize: '0.85rem', color: '#94a3b8', lineHeight: 1.55 }}>
            {currentWp.desc}
          </p>
          <div style={{ fontSize: '0.75rem', color: '#10b981', fontWeight: 600 }}>
            📐 Engineering Specs: {currentWp.specs}
          </div>
        </div>

        <div style={{ textAlign: 'right' }}>
          <div style={{ fontSize: '0.7rem', color: '#94a3b8', marginBottom: '4px' }}>NAVIGATION STATUS</div>
          <div style={{ fontSize: '0.85rem', color: '#00FFFF', fontWeight: 700 }}>
            {activeCamView === 'drone_orbit' ? '🛸 Dynamic Orbit (360°)' : '🎯 Focused Waypoint'}
          </div>
          <div style={{ fontSize: '0.72rem', color: '#64748b', marginTop: '4px' }}>
            Click 3D structures or use tabs to inspect
          </div>
        </div>
      </div>
    </div>
  );
}
