import json
import time
import os

vault_path = r"C:\AI-BS\backend\AI-BS_Knowledge_Vaults\api_code_snippets_vault.json"
dataset_path = r"C:\AI-BS\backend\AI-BS_Knowledge_Vaults\llm_training_dataset.jsonl"

with open(vault_path, "r", encoding="utf-8") as f:
    vault = json.load(f)

code_snippet = """package main

import (
	"fmt"
	"strings"
	"net/http"
	"io"
)

func main() {

	url := "https://leadengine-ai.p.rapidapi.com/api/config/rosie_lawn"

	payload := strings.NewReader("{\\"businessName\\":\\"Rosie's Lawn Care\\",\\"businessType\\":\\"landscaping\\",\\"phone\\":\\"(555) 987-6543\\",\\"email\\":\\"rosie@rosielawncare.com\\",\\"services\\":[\\"Lawn mowing\\",\\"Hedge trimming\\",\\"Leaf cleanup\\",\\"Garden design\\"],\\"serviceArea\\":{\\"country\\":\\"United States\\",\\"state\\":\\"Texas\\",\\"cities\\":[\\"Austin\\",\\"Round Rock\\",\\"Cedar Park\\",\\"Georgetown\\"],\\"zipCodes\\":[\\"78701\\",\\"78702\\",\\"78703\\",\\"78704\\"],\\"radius\\":\\"30 miles from downtown Austin\\"},\\"branding\\":{\\"widgetColor\\":\\"#16a34a\\",\\"headerColor\\":\\"#14532d\\",\\"botName\\":\\"Rosie\\",\\"headerSubtitle\\":\\"Your lawn care assistant\\",\\"welcomeMessage\\":\\"Hi! Need help with your lawn? I can get you a free estimate.\\",\\"showPoweredBy\\":false,\\"quickReplies\\":[\\"Get a Quote\\",\\"Book Service\\",\\"Emergency Cleanup\\"]}}")

	req, _ := http.NewRequest("POST", url, payload)

	req.Header.Add("x-rapidapi-key", "715331f921msh08fd118bc6cfcdbp1fd3bfjsn995142bec639")
	req.Header.Add("x-rapidapi-host", "leadengine-ai.p.rapidapi.com")
	req.Header.Add("Content-Type", "application/json")

	res, _ := http.DefaultClient.Do(req)

	defer res.Body.Close()
	body, _ := io.ReadAll(res.Body)

	fmt.Println(res)
	fmt.Println(string(body))

}"""

sample_payload = {
    "businessName": "Rosie's Lawn Care",
    "businessType": "landscaping",
    "phone": "(555) 987-6543",
    "email": "rosie@rosielawncare.com",
    "services": ["Lawn mowing", "Hedge trimming", "Leaf cleanup", "Garden design"],
    "serviceArea": {
        "country": "United States",
        "state": "Texas",
        "cities": ["Austin", "Round Rock", "Cedar Park", "Georgetown"],
        "zipCodes": ["78701", "78702", "78703", "78704"],
        "radius": "30 miles from downtown Austin"
    },
    "branding": {
        "widgetColor": "#16a34a",
        "headerColor": "#14532d",
        "botName": "Rosie",
        "headerSubtitle": "Your lawn care assistant",
        "welcomeMessage": "Hi! Need help with your lawn? I can get you a free estimate.",
        "showPoweredBy": False,
        "quickReplies": ["Get a Quote", "Book Service", "Emergency Cleanup"]
    }
}

new_entry = {
    "id": f"snippet_{int(time.time())}_leadengine",
    "title": "LeadEngine AI Chatbot & Lead Generation Widget Config",
    "language": "go",
    "host": "leadengine-ai.p.rapidapi.com",
    "endpoint": "/api/config/rosie_lawn",
    "category": "Lead Generation & AI Chatbot",
    "code_snippet": code_snippet,
    "sample_payload": sample_payload,
    "timestamp": time.time()
}

if not any(item.get("endpoint") == new_entry["endpoint"] for item in vault):
    vault.append(new_entry)
    with open(vault_path, "w", encoding="utf-8") as f:
        json.dump(vault, f, indent=2)

    dataset_line = {
        "instruction": "Generate a Go request snippet for the RapidAPI host leadengine-ai.p.rapidapi.com endpoint /api/config/rosie_lawn.",
        "input": "Configure LeadEngine AI Chatbot Widget for Rosie's Lawn Care",
        "output": new_entry["code_snippet"]
    }
    with open(dataset_path, "a", encoding="utf-8") as f:
        f.write(json.dumps(dataset_line) + "\n")
    print(f"Successfully vaulted 12th endpoint: {new_entry['title']}")
else:
    print("Endpoint already exists in vault.")
