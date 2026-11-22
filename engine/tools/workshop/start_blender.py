"""Start the installed pinned addon in a new authoring session."""
import bpy
import addon_utils
addon_utils.enable('blender_mcp',default_set=True,persistent=True)
scene=bpy.context.scene
for name in ('polyhaven','hyper3d','hunyuan3d','sketchfab','tripo','meshy','polypizza'):
    key='blendermcp_use_'+name
    if hasattr(scene,key):setattr(scene,key,False)
addon=bpy.context.preferences.addons.get('blender_mcp')
if addon and hasattr(addon.preferences,'telemetry_consent'):addon.preferences.telemetry_consent=False
bpy.ops.wm.save_userpref()
if not getattr(bpy.types,'blendermcp_server',None):bpy.ops.blendermcp.start_server()
