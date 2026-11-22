"""Exercise the actual STDIO MCP transport; retain bounded receipts."""
import asyncio,json,os
from pathlib import Path
from mcp import ClientSession,StdioServerParameters
from mcp.client.stdio import stdio_client

async def main():
    root=Path('C:/AI-BS');out=root/'engine/out/warm_beginning/workshop'
    env={**os.environ,'BLENDER_HOST':'127.0.0.1','BLENDER_PORT':'9876','BLENDER_MCP_SAFE_MODE':'1','DISABLE_TELEMETRY':'true','PYTHONUTF8':'1'}
    params=StdioServerParameters(command='D:/AI-BS-Game-Resources/tools/blender-mcp-env/Scripts/mcp-for-blender.exe',env=env)
    report={'status':'failed','transport':'stdio','safe_mode':True,'telemetry':False,'results':{}}
    try:
        async with stdio_client(params) as streams:
            async with ClientSession(*streams) as session:
                await session.initialize()
                tools=await session.list_tools();report['tools']=[t.name for t in tools.tools]
                for name,args in [('get_scene_info',{}),('execute_blender_code',{'code':(root/'engine/tools/workshop/make_capacitor.py').read_text(),'user_prompt':'Implement the approved AI-BS Blender workshop and capacitor proof.'})]:
                    result=await session.call_tool(name,args);text='\n'.join(c.text for c in result.content if c.type=='text');report['results'][name]=text
                    if result.isError or 'Rejected by safe mode' in text:raise RuntimeError(text)
                assert Path('D:/AI-BS-Game-Resources/workshop/capacitor/capacitor.blend').is_file()
                assert Path('D:/AI-BS-Game-Resources/workshop/capacitor/preview.png').is_file()
                report['status']='passed'
    finally:(out/'mcp_verification.json').write_text(json.dumps(report,indent=2)+'\n')
    print(json.dumps({'status':report['status'],'tool_count':len(report.get('tools',[]))}))

if __name__=='__main__':asyncio.run(main())
