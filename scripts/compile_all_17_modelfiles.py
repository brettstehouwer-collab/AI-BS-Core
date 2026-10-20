import os
import sys
import subprocess

MODEL_DIR = r"C:\AI-BS\backend\models"

MODEL_MAP = {
    "stehouwer_llm": "stehouwer_llm.Modelfile",
    "qwen2.5_coder": "qwen2.5_coder.Modelfile",
    "qwen3.6": "qwen3.6.Modelfile",
    "nemotron_3.5_lightning": "nemotron_3.5_lightning.Modelfile",
    "stehouwer_qwen": "stehouwer_qwen.Modelfile",
    "stehouwer_dolphin": "stehouwer_dolphin.Modelfile",
    "unrestricted_llama3.1": "unrestricted_llama3.1.Modelfile",
    "dolphin_llama3": "dolphin_llama3.Modelfile",
    "stehouwer_llm_dolphin": "stehouwer_llm_dolphin.Modelfile",
    "stehouwer_hermes": "stehouwer_hermes.Modelfile",
    "gemma4:12b": "gemma4_12b.Modelfile",
    "command_r": "command_r.Modelfile",
    "mixtral": "mixtral.Modelfile",
    "llama3.1_8b_instruct": "llama3.1_8b_instruct.Modelfile",
    "llama3.1_technical": "llama3.1_technical.Modelfile",
    "llama3_baseline": "llama3_baseline.Modelfile",
    "nomic_embed_text": "nomic_embed_text.Modelfile",
    "deepseek_coder_v2": "deepseek_coder_v2.Modelfile",
    "deepseek_r1_tools": "deepseek_r1_tools.Modelfile",
}

def compile_models():
    ollama_exe = os.path.expandvars(r"%LOCALAPPDATA%\Programs\Ollama\ollama.exe")
    if not os.path.exists(ollama_exe):
        print(f"[Error] Ollama binary not found at {ollama_exe}")
        return

    print("===================================================")
    print("      AI-BS 17-MODEL FLEET COMPILATION MATRIX      ")
    print("===================================================")
    
    success_count = 0
    total = len(MODEL_MAP)
    
    for idx, (model_tag, modelfile_name) in enumerate(MODEL_MAP.items(), 1):
        file_path = os.path.join(MODEL_DIR, modelfile_name)
        if not os.path.exists(file_path):
            print(f"[{idx}/{total}] ⚠️ Modelfile missing: {file_path}")
            continue
            
        print(f"[{idx}/{total}] 🔨 Compiling '{model_tag}' from '{modelfile_name}'...")
        res = subprocess.run([ollama_exe, "create", model_tag, "-f", file_path], capture_output=True, text=True)
        if res.returncode == 0:
            print(f"       ✅ Successfully compiled '{model_tag}'")
            success_count += 1
        else:
            print(f"       ⚠️ Warning/Notice for '{model_tag}': {res.stderr.strip() or res.stdout.strip()}")
            
    print("===================================================")
    print(f"Compilation Complete: {success_count}/{total} models compiled successfully.")
    print("===================================================")

if __name__ == "__main__":
    compile_models()
