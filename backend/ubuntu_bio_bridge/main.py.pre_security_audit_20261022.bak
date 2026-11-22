from fastapi import FastAPI, HTTPException
import subprocess
import os

app = FastAPI(title="Ubuntu-Bio Bridge", description="Offline AI-BS Bioinformatics & Emulation RPC Daemon")

@app.get("/ping")
async def ping():
    return {"status": "ok", "message": "Ubuntu-Bio Bridge is active"}

@app.get("/mount_check")
async def check_mount():
    """Verify if E:\\WLS2BKUP is properly mounted."""
    mount_path = "/mnt/e/WLS2BKUP"
    if os.path.exists(mount_path):
        return {"status": "mounted", "path": mount_path}
    else:
        raise HTTPException(status_code=404, detail="E: drive is not mounted at /mnt/e/WLS2BKUP")

@app.post("/execute_tool/{tool_name}")
async def execute_tool(tool_name: str, args: list[str]):
    """
    Executes an offline bioinformatics or emulation tool.
    Supported tools: foldseek, mmseqs, clustalo, pymol (cli), wrangler, firebase
    """
    allowed_tools = ["foldseek", "mmseqs", "clustalo", "wrangler", "firebase", "node", "python3"]
    if tool_name not in allowed_tools:
        raise HTTPException(status_code=400, detail=f"Tool {tool_name} not authorized or recognized.")
    
    # Prefix tools with path if they are in /opt/bio_tools/bin
    if tool_name in ["foldseek", "mmseqs"]:
        bin_path = f"/opt/bio_tools/{tool_name}/bin/{tool_name}"
    else:
        bin_path = tool_name

    cmd = [bin_path] + args
    
    try:
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=300)
        return {
            "status": "success" if result.returncode == 0 else "error",
            "return_code": result.returncode,
            "stdout": result.stdout,
            "stderr": result.stderr
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=8085, reload=False)
