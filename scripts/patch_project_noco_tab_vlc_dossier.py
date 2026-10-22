import os

tab_path = r"C:\AI-BS\frontend\src\components\ProjectNoCoStudioTab.jsx"
with open(tab_path, 'r', encoding='utf-8') as f:
    content = f.read()

# 1. Add Executive Dossier button in header
header_target = """        <div style={{ display: 'flex', gap: '12px' }}>
          <div style={{
            background: 'rgba(16, 185, 129, 0.15)',"""

header_replacement = """        <div style={{ display: 'flex', gap: '12px', alignItems: 'center', flexWrap: 'wrap' }}>
          <a
            href="/NoCo_Executive_Due_Diligence_Dossier_2026.pdf"
            target="_blank"
            rel="noreferrer"
            download="NoCo_Executive_Due_Diligence_Dossier_2026.pdf"
            style={{
              background: 'linear-gradient(135deg, rgba(239, 68, 68, 0.25), rgba(122, 40, 138, 0.45))',
              border: '1px solid #ef4444',
              borderRadius: '8px',
              padding: '8px 14px',
              textAlign: 'center',
              textDecoration: 'none',
              display: 'flex',
              flexDirection: 'column',
              justifyContent: 'center',
              cursor: 'pointer',
              boxShadow: '0 0 14px rgba(239, 68, 68, 0.3)',
              transition: 'all 0.2s ease'
            }}
          >
            <div style={{ fontSize: '0.68rem', color: '#f87171', fontWeight: 800, letterSpacing: '0.5px' }}>
              📄 EXECUTIVE DOSSIER
            </div>
            <div style={{ fontSize: '0.85rem', color: '#ffffff', fontWeight: 800 }}>
              DOWNLOAD PDF (9.2 KB)
            </div>
          </a>

          <div style={{
            background: 'rgba(16, 185, 129, 0.15)',"""

# 2. Update Playlist to 4 video perspectives
playlist_target = """                playlist={[
                  {
                    id: 'flythrough_60fps',
                    title: '✨ AI-BS Remastered 60 FPS Cinema Flythrough',
                    src: '/noco_flythrough_60fps.mp4?v=vlc_fs2',
                    badge: '60 FPS • UNBLURRED',
                    desc: 'Interpolated to 60 FPS motion compensation with enhanced micro-contrast, atmospheric color grading, and edge sharpening highlighting solar roof arrays and reflecting ponds.'
                  },
                  {
                    id: 'source_uploaded',
                    title: '📹 Uploaded Master Property Tour',
                    src: '/noco_property_tour_uploaded.mp4?v=vlc_fs2',
                    badge: 'SOURCE 24 FPS',
                    desc: 'Direct reference video with natural architectural overlay showing the central quadrangle, amphitheater rake, pond saunas, and surrounding conifer forest.'
                  }
                ]}"""

playlist_replacement = """                playlist={[
                  {
                    id: 'flythrough_60fps',
                    title: '✨ AI-BS Remastered 60 FPS Cinema Flythrough',
                    src: '/noco_flythrough_60fps.mp4?v=vlc_fs2',
                    badge: '60 FPS • UNBLURRED',
                    desc: 'Interpolated to 60 FPS motion compensation with enhanced micro-contrast, atmospheric color grading, and edge sharpening highlighting solar roof arrays and reflecting ponds.'
                  },
                  {
                    id: 'source_uploaded',
                    title: '📹 Uploaded Master Property Tour',
                    src: '/noco_property_tour_uploaded.mp4?v=vlc_fs2',
                    badge: 'SOURCE 24 FPS',
                    desc: 'Direct reference video with natural architectural overlay showing the central quadrangle, amphitheater rake, pond saunas, and surrounding conifer forest.'
                  },
                  {
                    id: 'dxr_greenhouse',
                    title: '🌿 RTX 4090 DXR: CEA Hydroponics & Koi Biome',
                    src: '/noco_dxr_greenhouse_tour.mp4?v=lora_dxr_v1',
                    badge: 'DXR RAY-TRACED • 60 FPS',
                    desc: 'Interior CEA greenhouse sweep showing purple-spectrum LED grow arrays, automated misting nozzles, vertical hydroponic towers, and circulating koi bio-filter canal.'
                  },
                  {
                    id: 'dxr_winter',
                    title: '❄️ RTX 4090 DXR: Winter Dusk ÖÖD Cabins & Stage',
                    src: '/noco_dxr_winter_dusk.mp4?v=lora_dxr_v1',
                    badge: 'LUMEN GI • DLSS 3.5',
                    desc: 'Cinematic winter dusk perspective showcasing mirror-glass ÖÖD guest cabins reflecting snow-dusted conifer forests, amber timber uplighting, and glowing geodesic living domes.'
                  }
                ]}"""

# Patch 1
if header_target in content:
    content = content.replace(header_target, header_replacement, 1)
    print("Header Patched LF")
elif header_target.replace('\n', '\r\n') in content:
    content = content.replace(header_target.replace('\n', '\r\n'), header_replacement.replace('\n', '\r\n'), 1)
    print("Header Patched CRLF")
else:
    print("Header Target Not Found")

# Patch 2
if playlist_target in content:
    content = content.replace(playlist_target, playlist_replacement, 1)
    print("Playlist Patched LF")
elif playlist_target.replace('\n', '\r\n') in content:
    content = content.replace(playlist_target.replace('\n', '\r\n'), playlist_replacement.replace('\n', '\r\n'), 1)
    print("Playlist Patched CRLF")
else:
    print("Playlist Target Not Found")

with open(tab_path, 'w', encoding='utf-8') as f:
    f.write(content)
print("ProjectNoCoStudioTab.jsx Updated Successfully!")
