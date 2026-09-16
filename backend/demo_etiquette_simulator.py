import os
import sys
import json
import requests
import time

OLLAMA_URL = "http://127.0.0.1:11434/api/generate"
PERSONA_PATH = os.path.join(os.path.dirname(__file__), "personas", "notos_hospitality_persona.json")

def load_persona():
    if not os.path.exists(PERSONA_PATH):
        print(f"Error: Persona file not found at {PERSONA_PATH}")
        sys.exit(1)
    with open(PERSONA_PATH, 'r') as f:
        return json.load(f)

def generate_response(prompt, system_prompt, history=""):
    full_prompt = f"{system_prompt}\n\nConversation History:\n{history}\n\nServer: {prompt}\nCustomer:"
    
    payload = {
        "model": "llama3.1", # Or whichever model is active, using generic default
        "prompt": full_prompt,
        "stream": False,
        "temperature": 0.7
    }
    
    # Try different models if one fails
    models_to_try = ["llama3.1", "qwen2", "mistral", "phi3"]
    
    for model in models_to_try:
        payload["model"] = model
        try:
            response = requests.post(OLLAMA_URL, json=payload, timeout=10)
            if response.status_code == 200:
                return response.json().get("response", "").strip()
        except requests.exceptions.RequestException:
            continue
            
    return "Error: Could not connect to local Ollama instance. Is it running?"

def main():
    print("=========================================================")
    print(" AI-BS: Tony Noto Etiquette Simulator (Terminal Edition) ")
    print("=========================================================")
    print("Initializing Persona...")
    
    persona = load_persona()
    system_prompt = persona["system_prompt"]
    
    print("\nScenario: You are a new server at Noto's Old World Italian Dining.")
    print("A customer has just been seated in your section.")
    print("Type your response to interact. Type '/evaluate' to end the session and receive your score.\n")
    
    history = "Customer: *Sits down and looks at the wine list with a slightly confused expression.*\n"
    print(history.strip())
    
    while True:
        try:
            user_input = input("\nYou (Server): ")
            
            if user_input.strip() == "":
                continue
                
            if user_input.strip() == "/evaluate":
                print("\n[AI-BS] Generating Evaluation based on Tony Noto's Etiquette Curriculum...")
                eval_prompt = "The training session has ended. Based on the conversation history, evaluate the server out of 100 on Empathy, Tone of Voice, Menu Knowledge, and Politeness. Provide constructive feedback."
                response = generate_response(eval_prompt, system_prompt, history)
                print(f"\n================ EVALUATION ================\n{response}\n============================================")
                break
                
            history += f"Server: {user_input}\n"
            
            print("Customer is thinking...")
            response = generate_response(user_input, system_prompt, history)
            
            history += f"Customer: {response}\n"
            print(f"\nCustomer: {response}")
            
        except KeyboardInterrupt:
            print("\nExiting simulator.")
            break
        except Exception as e:
            print(f"\nError: {e}")
            break

if __name__ == "__main__":
    main()
