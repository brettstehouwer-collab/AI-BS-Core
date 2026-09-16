import os
import shutil
import zipfile
import mimetypes
import io
import time
from pathlib import Path
from typing import List, Optional, Dict, Any
from datetime import datetime
from fastapi import APIRouter, UploadFile, File, Form, Query, HTTPException, Request, Response
from fastapi.responses import JSONResponse, StreamingResponse, FileResponse
from pydantic import BaseModel

router = APIRouter(prefix="/api/drive", tags=["Admin Shared Cloud Drive"])

# Root drive storage location on host system
DRIVE_ROOT = Path(r"C:\AI-BS\shared_cloud_drive").resolve()

# Pre-seeded default enterprise folders
DEFAULT_FOLDERS = [
    "01_Screenplays_and_Scripts",
    "02_Media_and_Previs",
    "03_Audio_and_Voiceovers",
    "04_Hospitality_and_Banquets",
    "05_Corporate_and_Legal",
    "06_Marketing_and_Leads",
    "07_AI_Models_and_Backups",
]

def ensure_drive_initialized():
    """Initializes the shared cloud drive root and default folders if missing."""
    DRIVE_ROOT.mkdir(parents=True, exist_ok=True)
    for folder in DEFAULT_FOLDERS:
        (DRIVE_ROOT / folder).mkdir(parents=True, exist_ok=True)

ensure_drive_initialized()


ALLOWED_ROOTS = [
    DRIVE_ROOT,
    Path("E:/").resolve(),
    Path(r"E:\Cymatics").resolve(),
    Path(r"E:\Muse Hub").resolve(),
    Path(r"C:\Program Files\Common Files\VST3").resolve(),
    Path(r"C:\ProgramData\Cymatics").resolve(),
    Path(r"C:\Users\footb\AppData\Roaming\Cymatics").resolve(),
    Path(r"E:\.ollama").resolve(),
    Path(r"E:\AI_BS_Resources\Ollama").resolve(),
    Path(r"D:\huggingface_cache").resolve()
]

def resolve_safe_path(rel_path: str) -> Path:
    """
    Safely resolves a relative path against DRIVE_ROOT and authorized asset junctions,
    preventing arbitrary path traversal attacks while allowing linked music & AI directories.
    """
    cleaned = (rel_path or "").strip().replace("\\", "/").lstrip("/")
    target = (DRIVE_ROOT / cleaned)
    resolved_target = target.resolve()
    
    # Enforce containment inside DRIVE_ROOT or authorized junction roots
    is_allowed = any(str(resolved_target).lower().startswith(str(root).lower()) for root in ALLOWED_ROOTS)
    if not is_allowed:
        raise HTTPException(status_code=403, detail="Access denied: Path traversal attempted.")
    return target


def format_bytes(size: int) -> str:
    """Formats bytes into human readable string."""
    if size == 0:
        return "0 B"
    units = ["B", "KB", "MB", "GB", "TB"]
    i = 0
    s = float(size)
    while s >= 1024.0 and i < len(units) - 1:
        s /= 1024.0
        i += 1
    return f"{s:.1f} {units[i]}"


def get_file_category(filename: str, is_dir: bool) -> str:
    """Classifies file into an AI-BS category."""
    if is_dir:
        return "folder"
    ext = os.path.splitext(filename)[1].lower()
    
    if ext in [".fountain", ".fdx", ".screenplay", ".sp"]:
        return "screenplay"
    elif ext in [".png", ".jpg", ".jpeg", ".webp", ".svg", ".gif", ".bmp", ".tiff"]:
        return "image"
    elif ext in [".mp4", ".webm", ".mov", ".avi", ".mkv", ".m4v"]:
        return "video"
    elif ext in [".wav", ".mp3", ".ogg", ".flac", ".m4a", ".aac"]:
        return "audio"
    elif ext in [".pdf", ".doc", ".docx", ".txt", ".md", ".rtf", ".odt"]:
        return "document"
    elif ext in [".py", ".js", ".jsx", ".ts", ".tsx", ".json", ".html", ".css", ".sql", ".sh", ".bat", ".yaml", ".yml"]:
        return "code"
    elif ext in [".zip", ".tar", ".gz", ".7z", ".rar", ".bz2"]:
        return "archive"
    elif ext in [".safetensors", ".ckpt", ".pt", ".bin", ".onnx", ".gguf"]:
        return "model"
    elif ext in [".uasset", ".umap", ".fbx", ".obj", ".blend", ".gltf", ".glb"]:
        return "unreal"
    return "other"


def get_file_icon(category: str, ext: str) -> str:
    """Returns appropriate emoji icon for file category."""
    icons = {
        "folder": "📁",
        "screenplay": "🎬",
        "image": "🖼️",
        "video": "🎥",
        "audio": "🎙️",
        "document": "📄",
        "code": "💻",
        "archive": "📦",
        "model": "🧠",
        "unreal": "🎮",
        "other": "📎"
    }
    if ext == ".pdf":
        return "📕"
    if ext == ".json":
        return "📊"
    if ext == ".py":
        return "🐍"
    if ext in [".fountain", ".fdx"]:
        return "🎬"
    return icons.get(category, "📎")


# ==============================================================================
# SCHEMAS
# ==============================================================================

class CreateFolderRequest(BaseModel):
    current_path: str = "/"
    folder_name: str

class CreateDocumentRequest(BaseModel):
    current_path: str = "/"
    file_name: str
    content: str = ""
    doc_type: Optional[str] = "markdown"  # fountain, markdown, text, json, python

class SaveDocumentRequest(BaseModel):
    file_path: str
    content: str

class RenameItemRequest(BaseModel):
    item_path: str
    new_name: str

class MoveItemsRequest(BaseModel):
    source_paths: List[str]
    target_folder: str

class DeleteItemsRequest(BaseModel):
    item_paths: List[str]

class ZipDownloadRequest(BaseModel):
    paths: List[str]
    archive_name: Optional[str] = "shared_drive_export.zip"


# ==============================================================================
# 1. DIRECTORY LISTING & SEARCH
# ==============================================================================

@router.get("/files")
async def list_files(
    path: str = Query("/", description="Relative path inside shared cloud drive"),
    search: Optional[str] = Query(None, description="Search keyword filter"),
    category: Optional[str] = Query(None, description="Category filter (all, screenplay, image, video, audio, document, code, archive)"),
    sort_by: str = Query("name", description="name, modified, size, type"),
    sort_order: str = Query("asc", description="asc or desc")
):
    """
    Returns contents of specified folder or search results across the entire shared cloud drive.
    """
    ensure_drive_initialized()
    target_dir = resolve_safe_path(path)
    if not target_dir.exists() or not target_dir.is_dir():
        raise HTTPException(status_code=404, detail="Directory not found.")

    items = []
    
    # Calculate Breadcrumbs
    rel_path_str = str(target_dir.relative_to(DRIVE_ROOT)).replace("\\", "/")
    if rel_path_str == ".":
        rel_path_str = ""
    
    parts = rel_path_str.split("/") if rel_path_str else []
    breadcrumbs = [{"name": "Shared Cloud Drive", "path": "/"}]
    curr_accum = ""
    for part in parts:
        if part:
            curr_accum = f"{curr_accum}/{part}".lstrip("/")
            breadcrumbs.append({"name": part, "path": f"/{curr_accum}"})

    # If search keyword is active, perform recursive search
    if search and search.strip():
        search_term = search.strip().lower()
        for root, dirs, files in os.walk(DRIVE_ROOT):
            root_path = Path(root)
            for d in dirs:
                if search_term in d.lower():
                    dir_full = root_path / d
                    rel = str(dir_full.relative_to(DRIVE_ROOT)).replace("\\", "/")
                    stat = dir_full.stat()
                    items.append({
                        "id": rel,
                        "name": d,
                        "path": f"/{rel}",
                        "is_dir": True,
                        "extension": "",
                        "size_bytes": 0,
                        "size_formatted": "--",
                        "modified_ts": stat.st_mtime,
                        "modified_formatted": datetime.fromtimestamp(stat.st_mtime).strftime("%b %d, %Y %I:%M %p"),
                        "category": "folder",
                        "icon": "📁"
                    })
            for f in files:
                if search_term in f.lower():
                    file_full = root_path / f
                    rel = str(file_full.relative_to(DRIVE_ROOT)).replace("\\", "/")
                    stat = file_full.stat()
                    ext = os.path.splitext(f)[1].lower()
                    cat = get_file_category(f, False)
                    items.append({
                        "id": rel,
                        "name": f,
                        "path": f"/{rel}",
                        "is_dir": False,
                        "extension": ext,
                        "size_bytes": stat.st_size,
                        "size_formatted": format_bytes(stat.st_size),
                        "modified_ts": stat.st_mtime,
                        "modified_formatted": datetime.fromtimestamp(stat.st_mtime).strftime("%b %d, %Y %I:%M %p"),
                        "category": cat,
                        "icon": get_file_icon(cat, ext)
                    })
    else:
        # Standard folder listing
        for entry in target_dir.iterdir():
            rel = str(entry.relative_to(DRIVE_ROOT)).replace("\\", "/")
            stat = entry.stat()
            is_dir = entry.is_dir()
            ext = os.path.splitext(entry.name)[1].lower() if not is_dir else ""
            cat = get_file_category(entry.name, is_dir)
            
            # Apply category filter
            if category and category != "all" and cat != category and not is_dir:
                continue

            items.append({
                "id": rel,
                "name": entry.name,
                "path": f"/{rel}",
                "is_dir": is_dir,
                "extension": ext,
                "size_bytes": stat.st_size if not is_dir else 0,
                "size_formatted": format_bytes(stat.st_size) if not is_dir else "--",
                "modified_ts": stat.st_mtime,
                "modified_formatted": datetime.fromtimestamp(stat.st_mtime).strftime("%b %d, %Y %I:%M %p"),
                "category": cat,
                "icon": get_file_icon(cat, ext)
            })

    # Sort items: Folders always first, then files sorted by criteria
    reverse_order = (sort_order.lower() == "desc")
    
    def sort_key(x):
        if sort_by == "modified":
            return (0 if x["is_dir"] else 1, x["modified_ts"])
        elif sort_by == "size":
            return (0 if x["is_dir"] else 1, x["size_bytes"])
        elif sort_by == "type":
            return (0 if x["is_dir"] else 1, x["category"], x["name"].lower())
        else: # name
            return (0 if x["is_dir"] else 1, x["name"].lower())

    items.sort(key=sort_key, reverse=reverse_order)

    return {
        "current_path": f"/{rel_path_str}" if rel_path_str else "/",
        "breadcrumbs": breadcrumbs,
        "item_count": len(items),
        "items": items
    }


# ==============================================================================
# 2. FILE & FOLDER CREATION & UPLOAD (ANY FILE TYPE)
# ==============================================================================

@router.post("/upload")
async def upload_files(
    files: List[UploadFile] = File(...),
    target_path: str = Form("/")
):
    """
    Accepts and uploads ANY file type into the specified target folder.
    Preserves original filenames or resolves duplicate names with numbering.
    """
    target_dir = resolve_safe_path(target_path)
    target_dir.mkdir(parents=True, exist_ok=True)

    uploaded_results = []

    for file in files:
        original_name = os.path.basename(file.filename or "uploaded_file")
        dest_path = target_dir / original_name
        
        # Handle collision
        stem, ext = os.path.splitext(original_name)
        counter = 1
        while dest_path.exists():
            dest_path = target_dir / f"{stem} ({counter}){ext}"
            counter += 1

        with open(dest_path, "wb") as f:
            shutil.copyfileobj(file.file, f)

        stat = dest_path.stat()
        rel = str(dest_path.relative_to(DRIVE_ROOT)).replace("\\", "/")
        cat = get_file_category(dest_path.name, False)
        
        uploaded_results.append({
            "name": dest_path.name,
            "path": f"/{rel}",
            "size_bytes": stat.st_size,
            "size_formatted": format_bytes(stat.st_size),
            "category": cat
        })

    return {
        "status": "success",
        "message": f"Successfully uploaded {len(uploaded_results)} file(s).",
        "uploaded": uploaded_results
    }


@router.post("/create_folder")
async def create_folder(req: CreateFolderRequest):
    """Creates a new folder inside current directory."""
    parent_dir = resolve_safe_path(req.current_path)
    clean_name = os.path.basename(req.folder_name.strip())
    if not clean_name:
        raise HTTPException(status_code=400, detail="Invalid folder name.")

    new_folder = parent_dir / clean_name
    if new_folder.exists():
        raise HTTPException(status_code=409, detail="A folder with this name already exists.")

    new_folder.mkdir(parents=True, exist_ok=True)
    rel = str(new_folder.relative_to(DRIVE_ROOT)).replace("\\", "/")

    return {
        "status": "success",
        "message": f"Folder '{clean_name}' created.",
        "path": f"/{rel}"
    }


@router.post("/create_document")
async def create_document(req: CreateDocumentRequest):
    """
    Creates a new document file (Fountain, Markdown, Text, JSON, Python, etc.)
    directly in the specified folder with optional initial content.
    """
    parent_dir = resolve_safe_path(req.current_path)
    parent_dir.mkdir(parents=True, exist_ok=True)

    clean_name = os.path.basename(req.file_name.strip())
    if not clean_name:
        raise HTTPException(status_code=400, detail="Invalid file name.")

    # Automatically add extension if omitted based on doc_type
    stem, ext = os.path.splitext(clean_name)
    if not ext:
        ext_map = {
            "fountain": ".fountain",
            "markdown": ".md",
            "text": ".txt",
            "json": ".json",
            "python": ".py",
            "script": ".fountain"
        }
        clean_name = f"{stem}{ext_map.get(req.doc_type, '.md')}"

    target_file = parent_dir / clean_name
    if target_file.exists():
        raise HTTPException(status_code=409, detail="A file with this name already exists.")

    with open(target_file, "w", encoding="utf-8") as f:
        f.write(req.content or "")

    stat = target_file.stat()
    rel = str(target_file.relative_to(DRIVE_ROOT)).replace("\\", "/")
    cat = get_file_category(clean_name, False)

    return {
        "status": "success",
        "message": f"Document '{clean_name}' created.",
        "path": f"/{rel}",
        "category": cat,
        "size_formatted": format_bytes(stat.st_size)
    }


# ==============================================================================
# 3. DOCUMENT READ & LIVE SAVE
# ==============================================================================

@router.get("/read_document")
async def read_document(path: str = Query(..., description="Relative file path")):
    """Reads UTF-8 text/code/screenplay document content for the in-drive editor."""
    target_file = resolve_safe_path(path)
    if not target_file.exists() or target_file.is_dir():
        raise HTTPException(status_code=404, detail="File not found.")

    try:
        with open(target_file, "r", encoding="utf-8", errors="replace") as f:
            content = f.read()
        
        stat = target_file.stat()
        ext = os.path.splitext(target_file.name)[1].lower()
        cat = get_file_category(target_file.name, False)

        return {
            "path": path,
            "filename": target_file.name,
            "extension": ext,
            "category": cat,
            "content": content,
            "size_bytes": stat.st_size,
            "modified_formatted": datetime.fromtimestamp(stat.st_mtime).strftime("%b %d, %Y %I:%M %p")
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to read file: {str(e)}")


@router.post("/save_document")
async def save_document(req: SaveDocumentRequest):
    """Saves updated document content directly to disk."""
    target_file = resolve_safe_path(req.file_path)
    if not target_file.exists():
        raise HTTPException(status_code=404, detail="Target document not found.")

    try:
        with open(target_file, "w", encoding="utf-8") as f:
            f.write(req.content)

        stat = target_file.stat()
        return {
            "status": "success",
            "message": f"Saved '{target_file.name}'.",
            "size_bytes": stat.st_size,
            "size_formatted": format_bytes(stat.st_size),
            "modified_formatted": datetime.fromtimestamp(stat.st_mtime).strftime("%b %d, %Y %I:%M %p")
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to save document: {str(e)}")


# ==============================================================================
# 4. RENAME, MOVE & DELETE OPERATIONS
# ==============================================================================

@router.post("/rename")
async def rename_item(req: RenameItemRequest):
    """Renames a file or folder."""
    target = resolve_safe_path(req.item_path)
    if not target.exists():
        raise HTTPException(status_code=404, detail="Item not found.")

    new_name = os.path.basename(req.new_name.strip())
    if not new_name:
        raise HTTPException(status_code=400, detail="Invalid new name.")

    destination = target.parent / new_name
    if destination.exists():
        raise HTTPException(status_code=409, detail="An item with the new name already exists.")

    target.rename(destination)
    rel = str(destination.relative_to(DRIVE_ROOT)).replace("\\", "/")

    return {
        "status": "success",
        "message": f"Renamed to '{new_name}'.",
        "new_path": f"/{rel}"
    }


@router.post("/move")
async def move_items(req: MoveItemsRequest):
    """Moves files and/or folders into a destination directory."""
    target_dir = resolve_safe_path(req.target_folder)
    if not target_dir.exists() or not target_dir.is_dir():
        raise HTTPException(status_code=404, detail="Destination directory not found.")

    moved_count = 0
    for src_rel in req.source_paths:
        src = resolve_safe_path(src_rel)
        if src.exists() and src != target_dir:
            dest = target_dir / src.name
            if not dest.exists():
                shutil.move(str(src), str(dest))
                moved_count += 1

    return {
        "status": "success",
        "message": f"Successfully moved {moved_count} item(s)."
    }


@router.post("/delete")
async def delete_items(req: DeleteItemsRequest):
    """Deletes files or directories."""
    deleted_count = 0
    for item_rel in req.item_paths:
        item = resolve_safe_path(item_rel)
        if item.exists():
            if item.is_dir():
                shutil.rmtree(str(item))
            else:
                item.unlink()
            deleted_count += 1

    return {
        "status": "success",
        "message": f"Deleted {deleted_count} item(s)."
    }


# ==============================================================================
# 5. STREAMING DOWNLOAD & ZIP BUNDLING
# ==============================================================================

@router.get("/download")
async def download_file(path: str = Query(..., description="Relative file path")):
    """Streams a file for download with Content-Disposition."""
    target = resolve_safe_path(path)
    if not target.exists() or target.is_dir():
        raise HTTPException(status_code=404, detail="File not found.")

    mime_type, _ = mimetypes.guess_type(target.name)
    return FileResponse(
        path=str(target),
        filename=target.name,
        media_type=mime_type or "application/octet-stream"
    )


@router.post("/zip_download")
async def zip_download(req: ZipDownloadRequest):
    """Bundles multiple files/folders on-the-fly into a streaming ZIP download."""
    memory_zip = io.BytesIO()

    with zipfile.ZipFile(memory_zip, mode="w", compression=zipfile.ZIP_DEFLATED) as zf:
        for p_rel in req.paths:
            p = resolve_safe_path(p_rel)
            if p.exists():
                if p.is_dir():
                    for root, _, files in os.walk(p):
                        for file in files:
                            full_p = Path(root) / file
                            arcname = full_p.relative_to(p.parent)
                            zf.write(full_p, arcname=str(arcname))
                else:
                    zf.write(p, arcname=p.name)

    memory_zip.seek(0)
    archive_name = req.archive_name or "shared_drive_bundle.zip"
    if not archive_name.endswith(".zip"):
        archive_name += ".zip"

    return StreamingResponse(
        memory_zip,
        media_type="application/zip",
        headers={"Content-Disposition": f'attachment; filename="{archive_name}"'}
    )


@router.get("/preview")
async def preview_media(path: str = Query(..., description="Relative file path"), request: Request = None):
    """Streams binary media (images, audio, video with Range headers, PDF) for in-app preview."""
    target = resolve_safe_path(path)
    if not target.exists() or target.is_dir():
        raise HTTPException(status_code=404, detail="File not found.")

    mime_type, _ = mimetypes.guess_type(target.name)
    if not mime_type:
        mime_type = "application/octet-stream"

    return FileResponse(
        path=str(target),
        media_type=mime_type
    )


# ==============================================================================
# 6. STORAGE TELEMETRY & DISK STATS
# ==============================================================================

@router.get("/storage_stats")
async def get_storage_stats():
    """Calculates disk capacity, used space, and AI-BS file category distribution."""
    ensure_drive_initialized()
    total_b, used_b, free_b = shutil.disk_usage(DRIVE_ROOT)

    categories_count: Dict[str, int] = {
        "screenplay": 0,
        "image": 0,
        "video": 0,
        "audio": 0,
        "document": 0,
        "code": 0,
        "archive": 0,
        "model": 0,
        "unreal": 0,
        "other": 0
    }
    categories_bytes: Dict[str, int] = {k: 0 for k in categories_count}
    total_drive_files = 0
    total_drive_folders = 0
    total_drive_bytes = 0

    for root, dirs, files in os.walk(DRIVE_ROOT):
        total_drive_folders += len(dirs)
        for f in files:
            fp = Path(root) / f
            try:
                sz = fp.stat().st_size
                cat = get_file_category(f, False)
                categories_count[cat] = categories_count.get(cat, 0) + 1
                categories_bytes[cat] = categories_bytes.get(cat, 0) + sz
                total_drive_files += 1
                total_drive_bytes += sz
            except Exception:
                pass

    return {
        "root_path": str(DRIVE_ROOT),
        "disk_total_formatted": format_bytes(total_b),
        "disk_used_formatted": format_bytes(used_b),
        "disk_free_formatted": format_bytes(free_b),
        "disk_used_pct": round((used_b / total_b) * 100, 1) if total_b > 0 else 0,
        "drive_total_files": total_drive_files,
        "drive_total_folders": total_drive_folders,
        "drive_total_bytes": total_drive_bytes,
        "drive_total_formatted": format_bytes(total_drive_bytes),
        "categories_breakdown": [
            {
                "category": cat,
                "count": categories_count[cat],
                "bytes": categories_bytes[cat],
                "size_formatted": format_bytes(categories_bytes[cat]),
                "icon": get_file_icon(cat, "")
            }
            for cat in categories_count if categories_count[cat] > 0
        ]
    }
