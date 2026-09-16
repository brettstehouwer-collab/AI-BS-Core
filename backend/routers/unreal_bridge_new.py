import os
import subprocess
import aiohttp
from fastapi import APIRouter
from pydantic import BaseModel
import logging
import sys

sys.path.append("C:\\AI-BS")
try:
    from discord_notifier import send_discord_update
except ImportError:
    def send_discord_update(msg): print(msg)

router = APIRouter(prefix="/unreal", tags=["Unreal Engine Automation"])

UNREAL_SCRIPTS_DIR = "C:\\AI-BS\\UnrealHub\\Assets"
UNREAL_RC_URL = "http://127.0.0.1:30010/remote/object/call"

class UnrealTask(BaseModel):
    tool_id: str
    parameters: dict = {}

class SpawnAssetRequest(BaseModel):
    package_path: str
    location: dict = {"X": 0.0, "Y": 0.0, "Z": 0.0}
    rotation: dict = {"Pitch": 0.0, "Yaw": 0.0, "Roll": 0.0}
    object_path: str = "/Game/Maps/BanquetHall.BanquetHall:PersistentLevel.SceneController_2"

class EnvironmentRequest(BaseModel):
    lighting_preset: str = "Daylight"
    object_path: str = "/Game/Maps/BanquetHall.BanquetHall:PersistentLevel.SceneController_2"

async def _send_unreal_rc(command: str, payload: dict, object_path: str):
    unreal_payload = {
        "objectPath": object_path,
        "functionName": command,
        "parameters": payload,
        "generateTransaction": True
    }
    try:
        connector = aiohttp.TCPConnector(ssl=False)
        async with aiohttp.ClientSession(connector=connector) as session:
            async with session.put(UNREAL_RC_URL, json=unreal_payload, timeout=3.0) as response:
                if response.status == 200:
                    return {"status": "success", "data": await response.json()}
                else:
                    return {"status": "error", "message": f"Unreal Engine returned HTTP {response.status}"}
    except Exception as e:
        return {"status": "error", "message": str(e)}

class RemoteControlRequest(BaseModel):
    objectPath: str = "/Game/Maps/BanquetHall.BanquetHall:PersistentLevel.SceneController_2"
    functionName: str = "UpdateSceneParams"
    parameters: dict = {}

@router.post("/remote-control")
async def unreal_remote_control(req: RemoteControlRequest):
    return await _send_unreal_rc(req.functionName, req.parameters, req.objectPath)

@router.post("/spawn_asset")
async def spawn_asset(req: SpawnAssetRequest):
    return await _send_unreal_rc("SpawnAsset", req.dict(exclude={"object_path"}), req.object_path)

@router.post("/set_environment")
async def set_environment(req: EnvironmentRequest):
    return await _send_unreal_rc("SetEnvironment", req.dict(exclude={"object_path"}), req.object_path)

@router.post("/execute")
def execute_unreal_script(task: UnrealTask):
    # Mapping of tool IDs to the generated scripts
    script_map = {
        "level": "01_Level_Editor/spawn_actors.py",
        "blueprint": "02_Blueprint_Editor/create_blueprint.py",
        "material": "03_Material_Editor/create_material.py",
        "niagara": "04_Niagara_Editor/create_niagara_system.py",
        "umg": "05_UMG_UI_Editor/create_widget.py",
        "control_rig": "06_Control_Rig/setup_control_rig.py",
        "modeling": "07_Modeling_Mode/process_meshes.py",
        "behavior": "08_Behavior_Tree/setup_behavior_tree.py",
        "physics": "09_Physics_Asset/setup_physics.py",
        "audio": "10_Audio_MetaSounds/create_metasound.py"
    }

    if task.tool_id not in script_map:
        return {"status": "error", "message": f"Unknown tool ID: {task.tool_id}"}
        
    script_path = os.path.join(UNREAL_SCRIPTS_DIR, script_map[task.tool_id].replace("/", "\\"))
    
    if not os.path.exists(script_path):
        return {"status": "error", "message": f"Script not found at {script_path}"}
        
    try:
        # We would typically use unreal.exe here, but for simulation we just call the python script
        result = subprocess.run(
            [sys.executable, script_path], 
            capture_output=True, 
            text=True, 
            timeout=10
        )
        return {
            "status": "success", 
            "stdout": result.stdout,
            "stderr": result.stderr
        }
    except Exception as e:
        return {"status": "error", "message": str(e)}

class ScreenplayTask(BaseModel):
    project_name: str
    script_name: str

@router.post("/execute_screenplay")
def execute_screenplay_script(task: ScreenplayTask):
    script_path = os.path.join("C:\\AI-BS\\screenplay_projects", task.project_name, task.script_name)
    
    if not os.path.exists(script_path):
        return {"status": "error", "message": f"Script not found at {script_path}"}
        
    try:
        result = subprocess.run(
            [sys.executable, script_path], 
            capture_output=True, 
            text=True, 
            timeout=15
        )
        return {
            "status": "success", 
            "stdout": result.stdout,
            "stderr": result.stderr
        }
    except Exception as e:
        return {"status": "error", "message": str(e)}

try:
    from aibs_opencv_tracker import tracker_instance
except ImportError:
    tracker_instance = None

@router.post("/tracker/start")
def start_opencv_tracker():
    if not tracker_instance:
        return {"status": "error", "message": "OpenCV Tracker module unavailable."}
    tracker_instance.start()
    return {"status": "success", "message": "OpenCV Face & Head Tracker started."}

@router.post("/tracker/stop")
def stop_opencv_tracker():
    if not tracker_instance:
        return {"status": "error", "message": "OpenCV Tracker module unavailable."}
    tracker_instance.stop()
    return {"status": "success", "message": "OpenCV Face & Head Tracker stopped."}

@router.get("/tracker/status")
def tracker_status():
    is_running = tracker_instance.is_running if tracker_instance else False
    return {"status": "success", "running": is_running}

@router.post("/launch_streamer")
def launch_unreal_streamer():
    """
    Launches Unreal Engine 5.8 in Pixel Streaming mode on port 8888.
    """
    bat_path = r"C:\AI-BS\Launch_Unreal_OnDemand.bat"
    try:
        subprocess.Popen(["cmd.exe", "/c", bat_path], cwd=r"C:\AI-BS")
        return {
            "status": "success",
            "message": "🎮 Unreal Engine 5.8 Pixel Streaming engine launching in background on ws://127.0.0.1:8888..."
        }
    except Exception as e:
        return {"status": "error", "message": str(e)}

@router.post("/kill_streamer")
def kill_unreal_streamer():
    """
    Terminates running Unreal Engine processes.
    """
    try:
        subprocess.run(["taskkill", "/F", "/IM", "UnrealEditor.exe"], capture_output=True)
        return {"status": "success", "message": "Unreal Engine process terminated."}
    except Exception as e:
        return {"status": "error", "message": str(e)}

@router.get("/status")
def unreal_status():
    return {"status": "Unreal Engine Automation Bridge is Online."}

# Notify Discord on module load
send_discord_update("Phase 13 Complete: Unreal Engine Bridge API initialized and ready for execution.")
