import os
import json

def generate_unreal_project():
    project_dir = r"C:\AI-BS\UnrealHub"
    os.makedirs(project_dir, exist_ok=True)
    
    uproject_path = os.path.join(project_dir, "AI_BS_Hub.uproject")
    
    project_data = {
        "FileVersion": 3,
        "EngineAssociation": "5.8",
        "Category": "",
        "Description": "AI-BS Pixel Streaming Hub - Master Project for 3D Viewports",
        "Plugins": [
            {
                "Name": "PixelStreaming",
                "Enabled": True
            }
        ]
    }
    
    with open(uproject_path, "w") as f:
        json.dump(project_data, f, indent=4)
        
    print(f"✅ Successfully created Unreal Engine Project at: {uproject_path}")
    print("\n--- NEXT STEPS FOR BRETT ---")
    print("1. Navigate to C:\\AI-BS\\UnrealHub")
    print("2. Right-click AI_BS_Hub.uproject and 'Generate Visual Studio project files' (optional if no C++)")
    print("3. Double-click AI_BS_Hub.uproject to open the Unreal Editor.")
    print("4. Inside the Editor, build the 'Banquet Room' map.")
    print("5. Once finished, click 'File > Package Project > Windows' to compile the .exe")

if __name__ == "__main__":
    generate_unreal_project()
