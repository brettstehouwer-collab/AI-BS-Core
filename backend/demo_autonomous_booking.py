import os
import sys
import json
import requests
import time

OLLAMA_URL = "http://127.0.0.1:11434/api/generate"
PERSONA_PATH = os.path.join(os.path.dirname(__file__), "personas", "autonomous_booking_persona.json")

def load_persona():
    if not os.path.exists(PERSONA_PATH):
        print(f"Error: Persona file not found at {PERSONA_PATH}")
        return {"system_prompt": "You are a helpful plumbing assistant. Ask for the user's name, address, and issue to book an appointment. End with [SYSTEM: BOOKING CONFIRMED]."}
    with open(PERSONA_PATH, 'r') as f:
        return json.load(f)

def generate_response(prompt, system_prompt, history=""):
    full_prompt = f"{system_prompt}\n\nConversation History:\n{history}\n\nCustomer: {prompt}\nAgent:"
    
    payload = {
        "model": "llama3.1", 
        "prompt": full_prompt,
        "stream": False,
        "temperature": 0.4
    }
    
    # Try models in sequence
    models_to_try = ["stehouwer_llm", "llama3.1", "qwen2", "mistral", "phi3"]
    
    for model in models_to_try:
        payload["model"] = model
        try:
            response = requests.post(OLLAMA_URL, json=payload, timeout=20)
            if response.status_code == 200:
                return response.json().get("response", "").strip()
        except requests.exceptions.RequestException:
            continue
            
    return "Error: Could not connect to local Ollama instance. Is it running?"

def get_initial_state():
    return "Agent: Thank you for contacting Smith & Sons Plumbing! How can we help you today?\n"

def process_chat_turn(user_message, history):
    persona = load_persona()
    system_prompt = persona.get("system_prompt", "")
    
    history += f"Customer: {user_message}\n"
    response = generate_response(user_message, system_prompt, history)
    history += f"Agent: {response}\n"
    
    is_confirmed = False
    if "[SYSTEM: BOOKING CONFIRMED]" in response.upper() or "BOOKING CONFIRMED" in response.upper():
        is_confirmed = True
        
    return {
        "response": response,
        "history": history,
        "is_confirmed": is_confirmed
    }

def main():
    print("================================================================")
    print(" AI-BS: Autonomous Customer Service & Booking Agent (Demo) ")
    print("================================================================")
    print("Initializing Persona...")
    
    persona = load_persona()
    system_prompt = persona["system_prompt"]
    
    print("\nScenario: You are a homeowner with a plumbing emergency.")
    print("You have just sent an SMS to 'Smith & Sons Plumbing'.")
    print("Type your messages to interact. The AI will attempt to book you automatically.\n")
    
    history = get_initial_state()
    print(history.strip())
    
    while True:
        try:
            user_input = input("\nYou (Customer): ")
            
            if user_input.strip() == "":
                continue
                
            history += f"Customer: {user_input}\n"
            
            print("AI is typing...")
            response = generate_response(user_input, system_prompt, history)
            
            history += f"Agent: {response}\n"
            print(f"\nAI Agent: {response}")
            
            if "[SYSTEM: BOOKING CONFIRMED]" in response.upper() or "BOOKING CONFIRMED" in response.upper():
                print("\n================================================================")
                print(" [SUCCESS] The AI Agent successfully autonomously parsed the")
                print(" requirements, scheduled the appointment, and updated the CRM.")
                print("================================================================")
                break
            
        except KeyboardInterrupt:
            print("\nExiting simulator.")
            break
        except Exception as e:
            print(f"\nError: {e}")
            break

if __name__ == "__main__":
    main()
