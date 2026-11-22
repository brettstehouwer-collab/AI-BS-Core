import os
import re

components_dir = r"C:\AI-BS\frontend\components"
files_to_check = [
    "AutomatedClientSchedulerTab.jsx", "BetaAnalyticsTab.jsx", "BrettDataTab.jsx",
    "ComfyUIWorkflowTrigger.jsx", "DeepLearningStudioTab.jsx", "DocumentsTab.jsx",
    "GpuNetworkTab.jsx", "LearningMaterialHub.jsx", "MoneyTrackTab.jsx",
    "PublicPlaygroundTab.jsx", "RapidApiReconTab.jsx", "ReasoningAttentionTab.jsx",
    "TheatricalStageSwitch.jsx", "VectorVaultManager.jsx"
]

injection = "  const backendUrl = import.meta.env.VITE_BACKEND_URL || (import.meta.env.DEV ? 'http://localhost:8000' : '');\n"

for filename in files_to_check:
    filepath = os.path.join(components_dir, filename)
    if not os.path.exists(filepath):
        continue
        
    with open(filepath, 'r', encoding='utf-8') as f:
        content = f.read()
        
    # Check if backendUrl is defined as a prop or variable
    if 'backendUrl' in content:
        # It uses backendUrl. Is it defined?
        # A rough heuristic: if we see 'backendUrl =' or '{ backendUrl' or '{backendUrl'
        if not re.search(r'(const|let|var)\s+backendUrl\s*=', content) and not re.search(r'\{\s*backendUrl[^\}]*\}\s*\)', content) and not re.search(r'function\s+\w+\s*\([^)]*backendUrl[^)]*\)', content):
            # Not defined! Inject it right after the component declaration
            # Find the component declaration
            match = re.search(r'export default function (\w+)\s*\([^)]*\)\s*\{', content)
            if match:
                insert_pos = match.end()
                new_content = content[:insert_pos] + "\n" + injection + content[insert_pos:]
                with open(filepath, 'w', encoding='utf-8') as f:
                    f.write(new_content)
                print(f"Injected backendUrl into {filename}")
            else:
                match = re.search(r'const (\w+)\s*=\s*(?:function)?\s*\([^)]*\)\s*=>\s*\{', content)
                if match:
                    insert_pos = match.end()
                    new_content = content[:insert_pos] + "\n" + injection + content[insert_pos:]
                    with open(filepath, 'w', encoding='utf-8') as f:
                        f.write(new_content)
                    print(f"Injected backendUrl into {filename}")
                else:
                    print(f"Could not find function declaration in {filename}")

print("Done scanning for backendUrl injections.")
