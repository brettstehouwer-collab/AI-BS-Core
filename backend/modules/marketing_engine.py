import subprocess
import json
import httpx
import re


class ZillowAPIProvider:
    """Base class for Zillow RapidAPI providers to standardize messy data."""

    def __init__(self, host: str, rapid_api_key: str):
        self.host = host
        self.api_key = rapid_api_key

    async def fetch_property(self, zillow_url: str):
        raise NotImplementedError()

    async def search_properties(self, location: str, status_type: str = "ForSale"):
        raise NotImplementedError()


class ZillowCom1Provider(ZillowAPIProvider):
    """Original Zillow-com1 provider implementation."""

    def __init__(self, rapid_api_key: str):
        super().__init__("zillow-com1.p.rapidapi.com", rapid_api_key)

    async def fetch_property(self, zillow_url: str):
        url = f"https://{self.host}/property"
        querystring = {"property_url": zillow_url}
        headers = {"x-rapidapi-key": self.api_key, "x-rapidapi-host": self.host}
        async with httpx.AsyncClient() as client:
            response = await client.get(
                url, headers=headers, params=querystring, timeout=15.0
            )
            if response.status_code != 200:
                raise Exception(
                    f"{self.host} returned {response.status_code}: {response.text}"
                )

            data = response.json()
            return {
                "address": data.get("address", {}).get(
                    "streetAddress", "Unknown Address"
                ),
                "city": data.get("address", {}).get("city", ""),
                "state": data.get("address", {}).get("state", ""),
                "zip": data.get("address", {}).get("zipcode", ""),
                "price": data.get("price", "Unknown Price"),
                "bedrooms": data.get("bedrooms", "Unknown"),
                "bathrooms": data.get("bathrooms", "Unknown"),
                "sqft": data.get("livingArea", "Unknown"),
                "yearBuilt": data.get("yearBuilt", "Unknown"),
                "description": data.get("description", "No description available."),
            }

    async def search_properties(self, location: str, status_type: str = "ForSale"):
        url = f"https://{self.host}/propertyExtendedSearch"
        querystring = {"location": location, "status_type": status_type}
        headers = {"x-rapidapi-key": self.api_key, "x-rapidapi-host": self.host}
        async with httpx.AsyncClient() as client:
            response = await client.get(
                url, headers=headers, params=querystring, timeout=15.0
            )
            if response.status_code != 200:
                raise Exception(
                    f"{self.host} returned {response.status_code}: {response.text}"
                )

            data = response.json()
            properties = []
            for prop in data.get("props", []):
                properties.append(
                    {
                        "zpid": prop.get("zpid"),
                        "address": prop.get("address", "Unknown"),
                        "price": prop.get("price", 0),
                        "bedrooms": prop.get("bedrooms", 0),
                        "bathrooms": prop.get("bathrooms", 0),
                        "livingArea": prop.get("livingArea", 0),
                        "propertyType": prop.get("propertyType", "Unknown"),
                        "listingStatus": prop.get("listingStatus", "Unknown"),
                        "daysOnZillow": prop.get("daysOnZillow", 0),
                        "agentName": (
                            prop.get("listingAgent", {}).get(
                                "agentName", "Unknown Agent"
                            )
                            if prop.get("listingAgent")
                            else "Unknown"
                        ),
                        "zillowUrl": (
                            f"https://www.zillow.com/homedetails/{prop.get('zpid')}_zpid/"
                            if prop.get("zpid")
                            else ""
                        ),
                    }
                )
            return properties


class USHousingMarketData1Provider(ZillowAPIProvider):
    """Implementation for US Housing Market Data API (Clone of zillow-com1)"""

    def __init__(self, rapid_api_key: str):
        super().__init__("us-housing-market-data1.p.rapidapi.com", rapid_api_key)

    async def fetch_property(self, zillow_url: str):
        url = f"https://{self.host}/property"
        querystring = {"property_url": zillow_url}
        headers = {"x-rapidapi-key": self.api_key, "x-rapidapi-host": self.host}
        async with httpx.AsyncClient() as client:
            response = await client.get(
                url, headers=headers, params=querystring, timeout=15.0
            )
            if response.status_code != 200:
                raise Exception(
                    f"{self.host} returned {response.status_code}: {response.text}"
                )

            data = response.json()
            return {
                "address": data.get("address", {}).get(
                    "streetAddress", "Unknown Address"
                ),
                "city": data.get("address", {}).get("city", ""),
                "state": data.get("address", {}).get("state", ""),
                "zip": data.get("address", {}).get("zipcode", ""),
                "price": data.get("price", "Unknown Price"),
                "bedrooms": data.get("bedrooms", "Unknown"),
                "bathrooms": data.get("bathrooms", "Unknown"),
                "sqft": data.get("livingArea", "Unknown"),
                "yearBuilt": data.get("yearBuilt", "Unknown"),
                "description": data.get("description", "No description available."),
            }

    async def search_properties(self, location: str, status_type: str = "ForSale"):
        url = f"https://{self.host}/propertyExtendedSearch"
        querystring = {"location": location, "status_type": status_type}
        headers = {"x-rapidapi-key": self.api_key, "x-rapidapi-host": self.host}
        async with httpx.AsyncClient() as client:
            response = await client.get(
                url, headers=headers, params=querystring, timeout=15.0
            )
            if response.status_code != 200:
                raise Exception(
                    f"{self.host} returned {response.status_code}: {response.text}"
                )

            data = response.json()
            properties = []
            for prop in data.get("props", []):
                properties.append(
                    {
                        "zpid": prop.get("zpid"),
                        "address": prop.get("address", "Unknown"),
                        "price": prop.get("price", 0),
                        "bedrooms": prop.get("bedrooms", 0),
                        "bathrooms": prop.get("bathrooms", 0),
                        "livingArea": prop.get("livingArea", 0),
                        "propertyType": prop.get("propertyType", "Unknown"),
                        "listingStatus": prop.get("listingStatus", "Unknown"),
                        "daysOnZillow": prop.get("daysOnZillow", 0),
                        "agentName": (
                            prop.get("listingAgent", {}).get(
                                "agentName", "Unknown Agent"
                            )
                            if prop.get("listingAgent")
                            else "Unknown"
                        ),
                        "zillowUrl": (
                            f"https://www.zillow.com/homedetails/{prop.get('zpid')}_zpid/"
                            if prop.get("zpid")
                            else ""
                        ),
                    }
                )
            return properties


class USPropertyDataProvider(ZillowAPIProvider):
    """Implementation for US Property Data by Jay Shree Ram / PropertyData"""

    def __init__(self, rapid_api_key: str):
        super().__init__("us-property-data.p.rapidapi.com", rapid_api_key)

    async def fetch_property(self, zillow_url: str):
        # Extract zpid from the URL
        match = re.search(r"(\d+)_zpid", zillow_url)
        if not match:
            raise Exception("Could not extract zpid from Zillow URL")
        zpid = match.group(1)

        url = f"https://{self.host}/api/v1/property/detail"
        querystring = {"zpid": zpid}
        headers = {"x-rapidapi-key": self.api_key, "x-rapidapi-host": self.host}

        async with httpx.AsyncClient() as client:
            response = await client.get(
                url, headers=headers, params=querystring, timeout=15.0
            )
            if response.status_code != 200:
                raise Exception(
                    f"{self.host} returned {response.status_code}: {response.text}"
                )

            resp_json = response.json()
            data = resp_json.get("data", {})

            return {
                "address": data.get("address", {}).get(
                    "streetAddress", "Unknown Address"
                ),
                "city": data.get("address", {}).get("city", ""),
                "state": data.get("address", {}).get("state", ""),
                "zip": data.get("address", {}).get("zipcode", ""),
                "price": data.get("price", "Unknown Price"),
                "bedrooms": data.get("bedrooms", "Unknown"),
                "bathrooms": data.get("bathrooms", "Unknown"),
                "sqft": data.get("livingArea", "Unknown"),
                "yearBuilt": data.get("resoFacts", {}).get("yearBuilt", "Unknown"),
                "description": data.get("description", "No description available."),
            }

    async def search_properties(self, location: str, status_type: str = "ForSale"):
        raise Exception(f"{self.host} search properties endpoint not yet configured.")


class ZHomesRealtyUSProvider(ZillowAPIProvider):
    """Implementation for ZHomes Realty US"""

    def __init__(self, rapid_api_key: str):
        super().__init__("zhomes-realty-us.p.rapidapi.com", rapid_api_key)

    async def fetch_property(self, zillow_url: str):
        # Extract zpid from the URL
        match = re.search(r"(\d+)_zpid", zillow_url)
        if not match:
            raise Exception("Could not extract zpid from Zillow URL")
        zpid = match.group(1)

        url = f"https://{self.host}/v2/properties/detail"
        querystring = {"zpid": zpid}
        headers = {"x-rapidapi-key": self.api_key, "x-rapidapi-host": self.host}

        async with httpx.AsyncClient() as client:
            response = await client.get(
                url, headers=headers, params=querystring, timeout=15.0
            )
            if response.status_code != 200:
                raise Exception(
                    f"{self.host} returned {response.status_code}: {response.text}"
                )

            resp_json = response.json()
            data = resp_json.get("data", {})
            reso = data.get("resoFacts", {})

            return {
                "address": data.get("address", {}).get(
                    "streetAddress", "Unknown Address"
                ),
                "city": data.get("address", {}).get("city", ""),
                "state": data.get("address", {}).get("state", ""),
                "zip": data.get("address", {}).get("zipcode", ""),
                "price": data.get("price", "Unknown Price"),
                "bedrooms": data.get("bedrooms", reso.get("bedrooms", "Unknown")),
                "bathrooms": data.get("bathrooms", reso.get("bathrooms", "Unknown")),
                "sqft": data.get("livingArea", "Unknown"),
                "yearBuilt": data.get("yearBuilt", reso.get("yearBuilt", "Unknown")),
                "description": data.get("description", "No description available."),
            }

    async def search_properties(self, location: str, status_type: str = "ForSale"):
        raise Exception(f"{self.host} search properties endpoint not yet configured.")


# --- The Vault Logic ---


def get_vault_providers(rapid_api_key: str):
    """Returns the ordered list of RapidAPI providers to try."""
    return [
        USHousingMarketData1Provider(rapid_api_key),
        ZillowCom1Provider(rapid_api_key),
        USPropertyDataProvider(rapid_api_key),
        ZHomesRealtyUSProvider(rapid_api_key),
    ]


async def fetch_zillow_data(zillow_url: str, rapid_api_key: str):
    """Vault wrapper: Loops through RapidAPI providers until one succeeds."""
    providers = get_vault_providers(rapid_api_key)

    for provider in providers:
        try:
            return await provider.fetch_property(zillow_url)
        except Exception as e:
            print(f"Vault Warning: Provider {provider.host} failed. Reason: {e}")
            continue  # Try next provider

    raise Exception("All vault providers failed, including the fallback mock.")


async def search_properties(
    location: str, rapid_api_key: str, status_type: str = "ForSale"
):
    """Vault wrapper: Loops through RapidAPI providers until one succeeds."""
    providers = get_vault_providers(rapid_api_key)

    for provider in providers:
        try:
            return await provider.search_properties(location, status_type)
        except Exception as e:
            print(f"Vault Warning: Provider {provider.host} failed. Reason: {e}")
            continue  # Try next provider

    raise Exception("All vault providers failed, including the fallback mock.")


# --- Ollama Generation Logic (Unchanged) ---


async def generate_marketing_copy(
    zillow_url: str, rapid_api_key: str, brand_style: str = "Five Star Real Estate"
):
    """
    Fetches real data from Zillow via RapidAPI Vault, then generates Zillow, FB, and LinkedIn copy.
    """

    # 1. Fetch Zillow Data via Vault
    try:
        prop_data = await fetch_zillow_data(zillow_url, rapid_api_key)
    except Exception as e:
        return {
            "zillow": f"Failed to fetch data from Zillow API Vault: {e}",
            "facebook": "N/A",
            "linkedin": "N/A",
        }

    # 2. Format the AI Prompt
    prompt = f"""
    You are an expert real estate copywriter working for {brand_style}.
    I will provide real property data sourced from Zillow.
    You must return a strict JSON object with exactly three keys: "zillow", "facebook", and "linkedin".
    
    Guidelines for each:
    - "zillow": SEO optimized, professional, descriptive, 2 paragraphs. Do NOT just copy the existing description, rewrite it to be better.
    - "facebook": Short, punchy, uses emojis, calls to action to message or call.
    - "linkedin": Geared towards commercial investors, ROI focused, professional tone.
    
    Property Data:
    Address: {prop_data.get('address')}, {prop_data.get('city')}, {prop_data.get('state')} {prop_data.get('zip')}
    Price: ${prop_data.get('price')}
    Bedrooms: {prop_data.get('bedrooms')}
    Bathrooms: {prop_data.get('bathrooms')}
    SqFt: {prop_data.get('sqft')}
    Year Built: {prop_data.get('yearBuilt')}
    
    Original Agent Description (for context):
    {prop_data.get('description', '')[:1000]} # Trimmed to save context
    
    Output ONLY valid JSON.
    """

    # 3. Call Ollama (We use subprocess for Ollama local inference)
    try:
        result = subprocess.run(
            ["ollama", "run", "llama3", prompt],
            capture_output=True,
            text=True,
            encoding="utf-8",
            timeout=120,
        )

        output = result.stdout.strip()

        if output.startswith("```json"):
            output = output[7:]
        if output.startswith("```"):
            output = output[3:]
        if output.endswith("```"):
            output = output[:-3]

        output = output.strip()
        parsed = json.loads(output)
        return parsed
    except json.JSONDecodeError as e:
        print(f"Failed to parse JSON from Ollama: {e}")
        return {
            "zillow": "Failed to parse generated Zillow description. Output was:\n"
            + output,
            "facebook": "Failed to parse generated FB ad.",
            "linkedin": "Failed to parse generated LinkedIn post.",
        }
    except Exception as e:
        print(f"Marketing Engine Error: {e}")
        return {
            "zillow": f"Error: {e}",
            "facebook": f"Error: {e}",
            "linkedin": f"Error: {e}",
        }
