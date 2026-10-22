import re

path = r"C:\AI-BS\frontend\src\components\ProjectNoCoStudioTab.jsx"
with open(path, "r", encoding="utf-8") as f:
    content = f.read()

# 1. Add import
old_import = "import NocoAgritourismCrm from './NocoAgritourismCrm.jsx';"
new_import = """import NocoAgritourismCrm from './NocoAgritourismCrm.jsx';
import NocoPropertiesTracker from './NocoPropertiesTracker.jsx';"""

if old_import in content:
    content = content.replace(old_import, new_import, 1)
    print("Added NocoPropertiesTracker import.")
else:
    print("Could not find old_import.")

# 2. Update initial activeSubTab
old_state = "const [activeSubTab, setActiveSubTab] = useState('campus_map');"
new_state = """const [activeSubTab, setActiveSubTab] = useState(() => {
    try {
      const params = new URLSearchParams(window.location.search);
      if (params.get('subtab') === 'properties' || params.get('tab') === 'noco_properties') {
        return 'properties_tracker';
      }
    } catch (e) {}
    return 'campus_map';
  });"""

if old_state in content:
    content = content.replace(old_state, new_state, 1)
    print("Updated activeSubTab initial state.")
else:
    print("Could not find old_state.")

# 3. Add to sub-tab list
old_first_tab = "{ id: 'campus_map',"
new_first_tab = """{ id: 'properties_tracker', label: '🏡 Nationwide Land Tracker & 112 Questionnaire' },
          { id: 'campus_map',"""

if old_first_tab in content:
    content = content.replace(old_first_tab, new_first_tab, 1)
    print("Added properties_tracker to sub-tabs array.")
else:
    print("Could not find old_first_tab.")

# 4. Render component
old_render = "{/* 1. INTERACTIVE 2D CAMPUS MASTER PLAN & SPATIAL ZONES */}\n      {activeSubTab === 'campus_map' && <NocoSpatialCampusMap />}"
# Also handle \r\n
old_render_crlf = "{/* 1. INTERACTIVE 2D CAMPUS MASTER PLAN & SPATIAL ZONES */}\r\n      {activeSubTab === 'campus_map' && <NocoSpatialCampusMap />}"

new_render = """{/* 0. NATIONWIDE LAND TRACKER & 112 DUE DILIGENCE AUDIT HUB */}
      {activeSubTab === 'properties_tracker' && <NocoPropertiesTracker />}

      {/* 1. INTERACTIVE 2D CAMPUS MASTER PLAN & SPATIAL ZONES */}
      {activeSubTab === 'campus_map' && <NocoSpatialCampusMap />}"""

if old_render in content:
    content = content.replace(old_render, new_render, 1)
    print("Added NocoPropertiesTracker render block (LF).")
elif old_render_crlf in content:
    content = content.replace(old_render_crlf, new_render, 1)
    print("Added NocoPropertiesTracker render block (CRLF).")
else:
    # Regex fallback
    pattern = r"(\{/\*\s*1\.\s*INTERACTIVE 2D CAMPUS MASTER PLAN[^\}]*\}\s*\{activeSubTab === 'campus_map' && <NocoSpatialCampusMap />\})"
    if re.search(pattern, content):
        content = re.sub(pattern, new_render, content, count=1)
        print("Added NocoPropertiesTracker render block via regex.")
    else:
        print("Could not find render point.")

with open(path, "w", encoding="utf-8") as f:
    f.write(content)
print("Saved modified ProjectNoCoStudioTab.jsx.")
