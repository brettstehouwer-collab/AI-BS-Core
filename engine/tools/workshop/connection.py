"""Pinned local Blender workshop configuration; no import-time side effects."""
def configuration():
    return {'command':'D:/AI-BS-Game-Resources/tools/blender-mcp-env/Scripts/mcp-for-blender.exe',
        'env':{'BLENDER_HOST':'127.0.0.1','BLENDER_PORT':'9876',
               'BLENDER_MCP_SAFE_MODE':'1','DISABLE_TELEMETRY':'true','PYTHONUTF8':'1'},
        'startup_timeout_sec':30,'tool_timeout_sec':120,'required':False}
