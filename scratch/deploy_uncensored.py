import subprocess
import os

def create_ollama_model(model_name, modelfile_path):
    print(f"Creating {model_name} from {modelfile_path}...")
    try:
        subprocess.run(["ollama", "create", model_name, "-f", modelfile_path], check=True)
        print(f"Successfully created {model_name}.")
    except subprocess.CalledProcessError as e:
        print(f"Error creating {model_name}: {e}")

if __name__ == "__main__":
    print("Setting up Uncensored Models for Stehouwer LLM...")
    
    # Assumes you have run `ollama pull` or downloaded the GGUFs.
    # If using local GGUFs downloaded via FDM, change the first line in the Modelfile 
    # to 'FROM ./path/to/model.gguf' before running this script!
    
    models = {
        "stehouwer_dolphin": "Modelfile.Dolphin",
        "stehouwer_qwen": "Modelfile.Qwen",
        "stehouwer_hermes": "Modelfile.Hermes"
    }
    
    for name, mfile in models.items():
        if os.path.exists(mfile):
            create_ollama_model(name, mfile)
        else:
            print(f"Modelfile {mfile} not found! Skipping.")
    
    print("\nSetup complete! You can now use the new /api/models/active endpoint to switch to these models.")
