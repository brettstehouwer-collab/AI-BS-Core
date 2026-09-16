from fastapi import APIRouter, HTTPException, BackgroundTasks
from fastapi.responses import FileResponse, JSONResponse
from pydantic import BaseModel
import os
import uuid
import lxml.etree as ET

router = APIRouter(prefix="/api/export", tags=["Pro Export"])

class ExportPayload(BaseModel):
    format: str # 'fcpxml' or 'aaf'
    mode: str = "raw" # 'raw' or 'baked'
    videoTracks: list
    audioTracks: list
    compositorNodes: list = []

@router.post("/timeline")
def export_timeline(payload: ExportPayload):
    try:
        export_dir = os.path.join("C:\\AI-BS\\saved_data", "exports")
        os.makedirs(export_dir, exist_ok=True)
        file_id = str(uuid.uuid4())[:8]
        
        if payload.format == 'fcpxml':
            # Generate FCPXML
            root = ET.Element("fcpxml", version="1.9")
            resources = ET.SubElement(root, "resources")
            
            # Simple Format Resource
            format_node = ET.SubElement(resources, "format", id="r1", name="FFVideoFormat1080p30", frameDuration="1001/30000s", width="1920", height="1080")
            
            library = ET.SubElement(root, "library")
            event = ET.SubElement(library, "event", name="AI-BS Export")
            project = ET.SubElement(event, "project", name=f"Project_{file_id}")
            sequence = ET.SubElement(project, "sequence", format="r1", duration="3600/30s")
            spine = ET.SubElement(sequence, "spine")
            
            # Very basic FCPXML translation loop
            for t in payload.videoTracks:
                if t.get('clips') and len(t['clips']) > 0:
                    for clip in t['clips']:
                        if payload.mode == 'baked':
                            # In baked mode, we theoretically link to the rendered proxy asset
                            # For now, we stub an asset reference
                            asset = ET.SubElement(resources, "asset", id=f"proxy_{file_id}", name="Baked Proxy", src=f"file:///proxy_{file_id}.mp4")
                            clip_node = ET.SubElement(spine, "asset-clip", ref=f"proxy_{file_id}", offset=f"{clip.get('bar', 0)}s", duration=f"{clip.get('length', 1)}s")
                        else:
                            # Create empty gap or generator clip as placeholder
                            clip_node = ET.SubElement(spine, "clip", name=clip.get('name', 'Clip'), offset=f"{clip.get('bar', 0)}s", duration=f"{clip.get('length', 1)}s")
                            # If raw mode, inject node graph as filters
                            if payload.mode == 'raw' and payload.compositorNodes:
                                for node in payload.compositorNodes:
                                    if node.get('type') == 'colorTransform':
                                        ET.SubElement(clip_node, "filter-video", ref="Color Board", name="Color Board")
                                    elif node.get('type') == 'blur':
                                        ET.SubElement(clip_node, "filter-video", ref="Gaussian", name="Gaussian Blur")
            
            tree = ET.ElementTree(root)
            file_path = os.path.join(export_dir, f"export_{file_id}.fcpxml")
            tree.write(file_path, pretty_print=True, xml_declaration=True, encoding="utf-8")
            
            return {"status": "success", "download_url": f"/api/export/download/{file_id}.fcpxml"}
            
        elif payload.format == 'aaf':
            # Generate AAF via pyaaf2
            import aaf2
            file_path = os.path.join(export_dir, f"export_{file_id}.aaf")
            
            # Minimal AAF creation (stub structure)
            with aaf2.open(file_path, 'w') as f:
                comp = f.create.CompositionMob(f"AI-BS_Export_{file_id}")
                f.content.mobs.append(comp)
                
                for t_idx, t in enumerate(payload.videoTracks):
                     timeline_slot = comp.create_timeline_slot(24) # 24 fps
                     timeline_slot.name = f"{t.get('name', 'Track')}_{payload.mode}"
                
            return {"status": "success", "download_url": f"/api/export/download/{file_id}.aaf"}
            
        else:
            raise HTTPException(status_code=400, detail="Unsupported format")
            
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/download/{filename}")
def download_export(filename: str):
    file_path = os.path.join("C:\\AI-BS\\saved_data", "exports", filename)
    if os.path.exists(file_path):
        return FileResponse(file_path, filename=filename)
    raise HTTPException(status_code=404, detail="File not found")
