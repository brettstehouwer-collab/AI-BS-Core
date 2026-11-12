import { useState } from 'react';
import { Cpu, Play, ExternalLink, CheckCircle2, X } from 'lucide-react';
import './BSGameHubTab.css';

const verifiedMilestones = [
  ['A native view of the world', 'The Windows DirectX 12 prototype renders motherboard geometry with a movable camera.'],
  ['Engine & world identity', 'The custom PC engine has an installable SDK and stable world/object identities across restart.'],
  ['World & Adam continuity', 'Local checkpoints preserve edits, recorded history, undo/redo and accepted commands together.'],
];

export default function BSGameHubTab() {
  const [playing, setPlaying] = useState(false);

  return (
    <section className="bs-game-hub" aria-labelledby="bs-game-title">
      <header className="bs-game-hero">
        <div className="bs-game-kicker"><Cpu size={16} aria-hidden="true" /> AI-BS / FIRST BOOT</div>
        <h1 id="bs-game-title">Build a world.<br /><span>Bring the lights back.</span></h1>
        <p className="bs-game-memoir">Adam&apos;s Infinite-Brett Stehouwer Living Learning Memoir</p>
        <p className="bs-game-intro">Explore a motherboard world, reclaim its systems, and build a place that remembers your journey. Adam&apos;s memory guides BS through it.</p>
        <div className="bs-game-actions">
          <button className="bs-game-primary" onClick={() => setPlaying(true)}><Play size={17} aria-hidden="true" /> Play concept in the hub</button>
          <a className="bs-game-secondary" href="/bs-game/index.html" target="_blank" rel="noopener noreferrer">Open full window <ExternalLink size={16} aria-hidden="true" /></a>
        </div>
        <p className="bs-game-note">Browser concept playground · simulated values · resets when reloaded</p>
      </header>

      {playing && (
        <section className="bs-game-play" aria-label="First Boot concept playground">
          <div className="bs-game-play-heading"><span>First Boot — Concept Playground</span><button onClick={() => setPlaying(false)} aria-label="Close concept playground"><X size={18} /></button></div>
          <iframe src="/bs-game/index.html" title="AI-BS First Boot playable concept" sandbox="allow-scripts allow-pointer-lock" allowFullScreen />
          <p>Click the scene to focus. Move with W/A/S/D; right-drag or use arrow keys to look around; scroll to zoom. Point at Core Node 01 and press E or left click to repair it, then explore the garage, archive and gate. Shift boosts a selected vehicle. Esc closes a catalog.</p>
        </section>
      )}

      <figure className="bs-game-native-preview">
        <div className="bs-game-preview-heading"><span className="bs-game-step">FIRST NATIVE FRAME</span><span>Windows PC · DirectX 12</span></div>
        <img src="/assets/bs-game-native-preview.png" alt="A frame from the native AI-BS DirectX 12 prototype: a motherboard with a CPU socket, memory banks, glowing traces and a large GPU landmark." width="960" height="640" loading="lazy" />
        <figcaption><strong>The motherboard world is becoming visible.</strong><span>This frame comes from the custom PC engine running locally on an RTX 4090. It is an early geometry prototype; world-building interactions and the full game are still ahead.</span></figcaption>
      </figure>

      <div className="bs-game-section-heading"><h2>The custom PC game is taking shape</h2><span>Published snapshot · 2026-11-01 · SDK 0.3</span></div>
      <div className="bs-game-milestones">
        {verifiedMilestones.map(([title, detail]) => (
          <article key={title}><CheckCircle2 size={19} aria-hidden="true" /><h3>{title}</h3><p>{detail}</p><span className="bs-game-status">Verified locally</span></article>
        ))}
      </div>
      <div className="bs-game-roadmap">
        <div><span className="bs-game-step">NEXT BUILD</span><h3>Give the visible world lasting changes</h3><p>Connect the scene to saved world edits, then develop interactions, construction and physics so the places BS builds can become part of the journey.</p></div>
        <div><span className="bs-game-step">ON THE HORIZON</span><h3>Adam alongside the journey</h3><p>A simultaneous phone companion is planned to follow the active PC game&apos;s progression, discoveries and guidance.</p></div>
      </div>
      <footer className="bs-game-footnote">The browser sketch is a separate creative playground. It does not use native saves or live PC hardware readings. The native PC renderer and checkpoint system are verified foundations; their integration into the full game and the Adam companion is still being developed. This published summary and image are a development snapshot, not a live connection to the development computer.</footer>
    </section>
  );
}
