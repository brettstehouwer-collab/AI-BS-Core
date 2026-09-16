import pandas as pd
import io
import subprocess
import json
import re


async def parse_and_generate_campaign(csv_content: str):
    """
    Parses a CSV of past clients, identifies targets (e.g. bought 5+ years ago),
    and uses Ollama (llama3) to generate personalized SMS texts.
    Expected CSV columns: Name, Phone, Email, PurchaseDate, PurchasePrice
    """
    try:
        # Read the CSV from string
        df = pd.read_csv(io.StringIO(csv_content))
    except Exception as e:
        raise Exception(f"Failed to parse CSV: {e}")

    # Ensure required columns are present (case-insensitive check)
    cols = [c.lower().strip() for c in df.columns]
    expected = ["name", "phone", "purchasedate"]
    for ex in expected:
        if not any(ex in c for c in cols):
            raise Exception(f"CSV missing required column containing '{ex}'")

    results = []

    for index, row in df.iterrows():
        # Clean up row data
        row_dict = {str(k).lower().strip(): v for k, v in row.items()}

        # Extract fields robustly
        name = None
        phone = None
        purchase_date = None
        purchase_price = "Unknown"

        for k, v in row_dict.items():
            if "name" in k and not name:
                name = str(v)
            if "phone" in k and not phone:
                phone = str(v)
            if "date" in k and not purchase_date:
                purchase_date = str(v)
            if "price" in k and purchase_price == "Unknown":
                purchase_price = str(v)

        if not name or not phone or pd.isna(name) or pd.isna(phone):
            continue

        # Build prompt for LLM
        prompt = f"""
        You are Joey Hamilton, a friendly, highly respected 33-year veteran real estate agent in Grandville, Michigan.
        Write a short, highly personalized SMS text message (under 300 characters) to your past client.
        
        Client Details:
        Name: {name}
        Original Purchase Date: {purchase_date}
        Original Price: {purchase_price}
        
        Goal: Wish them a happy "home anniversary" and gently mention that the West Michigan market has shifted and their equity has likely spiked. Ask if they want an updated valuation.
        Tone: Friendly, old-school relationship-focused, NOT pushy. Do not sound like a robot.
        
        Output ONLY the text message content, nothing else.
        """

        # Call Ollama
        try:
            result = subprocess.run(
                ["ollama", "run", "llama3", prompt],
                capture_output=True,
                text=True,
                encoding="utf-8",
                timeout=60,
            )
            sms_text = result.stdout.strip()
            # Clean up potential markdown formatting from LLM
            sms_text = sms_text.replace('"', "").replace("`", "")

            # Clean up ANSI escape sequences (terminal control characters)
            ansi_escape = re.compile(r"\x1B(?:[@-Z\\-_]|\[[0-?]*[ -/]*[@-~])")
            sms_text = ansi_escape.sub("", sms_text)

            # Additional cleanup for hidden backspaces or weird characters from Ollama
            sms_text = re.sub(
                r"\[\d*[A-Za-z]", "", sms_text
            )  # Catch things like [5D or [K

            results.append(
                {
                    "name": name,
                    "phone": phone,
                    "purchase_date": purchase_date,
                    "sms_generated": sms_text,
                }
            )
        except FileNotFoundError:
            print(f"Ollama is not installed or not in PATH.")
            results.append(
                {
                    "name": name,
                    "phone": phone,
                    "purchase_date": purchase_date,
                    "sms_generated": "Error: Ollama not found. Please install it to generate messages.",
                }
            )
        except Exception as e:
            print(f"Failed to generate SMS for {name}: {e}")
            results.append(
                {
                    "name": name,
                    "phone": phone,
                    "purchase_date": purchase_date,
                    "sms_generated": "Error generating message.",
                }
            )

    return results
