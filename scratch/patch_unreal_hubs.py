import os

HUBS = [
    ("RealEstateArchitectureHub.jsx", "Unreal Engine Digital Twin: Property Walkthrough"),
    ("DataCenterOperationsHub.jsx", "Unreal Engine Digital Twin: Data Center Thermals"),
    ("GameEngineArchitectureHub.jsx", "Unreal Engine: Level Architect & Playtest")
]

BASE_DIR = "C:\\AI-BS\\frontend\\components\\industry_hubs"

for hub_name, title in HUBS:
    filepath = os.path.join(BASE_DIR, hub_name)
    with open(filepath, 'r', encoding='utf-8') as f:
        content = f.read()

    # Add import
    if "import UnrealPixelStreamBridge" not in content:
        content = content.replace(
            "import { Play, Activity, Shield, Zap } from 'lucide-react';",
            "import { Play, Activity, Shield, Zap } from 'lucide-react';\nimport UnrealPixelStreamBridge from '../UnrealPixelStreamBridge';"
        )

    # Add component
    if "<UnrealPixelStreamBridge" not in content:
        bridge_code = f"""      <div className="mb-6">
        <UnrealPixelStreamBridge title="{title}" />
      </div>\n      <div className="grid grid-cols-1"""
        content = content.replace("      <div className=\"grid grid-cols-1", bridge_code)

    with open(filepath, 'w', encoding='utf-8') as f:
        f.write(content)
    print(f"Patched {hub_name}")
