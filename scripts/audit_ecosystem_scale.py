import os, sys, re, json, glob

def analyze_aibs_scale():
    print("=== AI-BS SCALE & COMPONENT AUDIT ===")
    
    # 1. Count Tabs in App.jsx and navigationConfig.js
    app_jsx_path = r'C:\AI-BS\frontend\src\App.jsx'
    nav_cfg_path = r'C:\AI-BS\frontend\src\components\navigationConfig.js'
    tabs_app = set()
    if os.path.exists(app_jsx_path):
        with open(app_jsx_path, 'r', encoding='utf-8', errors='ignore') as f:
            c = f.read()
            tabs_app = set(re.findall(r'id:\s*[\'"]([^\'"]+)[\'"]', c))
            
    nav_tabs = set()
    if os.path.exists(nav_cfg_path):
        with open(nav_cfg_path, 'r', encoding='utf-8', errors='ignore') as f:
            c = f.read()
            nav_tabs = set(re.findall(r'id:\s*[\'"]([^\'"]+)[\'"]', c))
            
    all_tabs = tabs_app.union(nav_tabs)
    print(f"Total Unique UI Tabs: {len(all_tabs)} (App.jsx: {len(tabs_app)}, navigationConfig: {len(nav_tabs)})")

    # 2. Count Frontend Components
    comp_dir = r'C:\AI-BS\frontend\src\components'
    frontend_files = glob.glob(os.path.join(comp_dir, '**', '*.jsx'), recursive=True) + \
                     glob.glob(os.path.join(comp_dir, '**', '*.js'), recursive=True)
    # Deduplicate relative subpaths inside components
    rel_files = set([os.path.relpath(p, comp_dir) for p in frontend_files if 'components\\components' not in os.path.relpath(p, comp_dir)])
    print(f"Total Frontend UI Components/Modules: {len(rel_files)}")

    # 3. Count Backend Routers & Python Modules
    routers_dir = r'C:\AI-BS\backend\routers'
    backend_routers = glob.glob(os.path.join(routers_dir, '*.py'))
    backend_routers = [f for f in backend_routers if not os.path.basename(f).startswith('__')]
    print(f"Total Backend API Routers: {len(backend_routers)}")

    core_modules = glob.glob(r'C:\AI-BS\backend\core\*.py') + glob.glob(r'C:\AI-BS\backend\modules\*.py')
    core_modules = [f for f in core_modules if not os.path.basename(f).startswith('__')]
    print(f"Total Backend Core Subsystem Modules: {len(core_modules)}")

    # 4. Count Registered Tools in ToolRegistry
    try:
        sys.path.insert(0, r'C:\AI-BS\backend')
        from tools.tool_registry import ToolRegistry
        tr = ToolRegistry()
        if hasattr(tr, 'tools'):
            tool_count = len(tr.tools)
        elif hasattr(tr, 'get_all_tools'):
            tool_count = len(tr.get_all_tools())
        else:
            tool_count = len(dir(tr))
        print(f"Total Registered Cognitive AI Tools: {tool_count}")
    except Exception as e:
        print(f"Error querying ToolRegistry: {e}")

    # 5. Count Total Backend API Routes (FastAPI routes)
    try:
        from AI_BS_Backend import app
        total_routes = len(app.routes)
        print(f"Total FastAPI REST & WebSocket Endpoints: {total_routes}")
    except Exception as e:
        print(f"Error checking app.routes: {e}")

if __name__ == '__main__':
    analyze_aibs_scale()
