import json
import logging
import asyncio
import httpx
from bs4 import BeautifulSoup
from typing import Dict

logging.basicConfig(
    level=logging.INFO, format="%(asctime)s [SocialScraper] %(message)s"
)


class SocialMediaScraper:
    def __init__(self):
        # We will use direct HTTP requests with standard headers
        self.headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
        }

    async def _search_platform(self, business_name: str, platform: str) -> dict:
        """Searches for the business on a specific platform via public search engines."""
        search_query = f"{business_name} {platform}"
        url = f"https://html.duckduckgo.com/html/?q={search_query}"

        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                res = await client.get(url, headers=self.headers)
                if res.status_code == 200:
                    soup = BeautifulSoup(res.text, "html.parser")
                    results = soup.find_all("a", class_="result__url")

                    # Check if the first few results are actually on the platform
                    platform_url = f"{platform}.com"
                    found = False
                    for link in results[:3]:
                        if platform_url in link.text.lower():
                            found = True
                            break

                    return {"presence_detected": found, "status": "scanned"}
        except Exception as e:
            logging.error(f"Failed to scrape {platform} for {business_name}: {e}")

        return {"presence_detected": False, "status": "error"}

    async def scrape_business(self, business_name: str) -> Dict:
        """Performs real web scraping to audit social media presence."""
        logging.info(
            f"🔍 Initiating physical social media web scrape for: '{business_name}'..."
        )

        platforms = ["facebook", "instagram", "linkedin"]
        profile_data = {}
        deficits = []

        for platform in platforms:
            logging.info(f"Scraping presence for {platform}...")
            result = await self._search_platform(business_name, platform)
            profile_data[platform] = result

            if not result.get("presence_detected"):
                deficits.append(
                    f"{platform.capitalize()} presence could not be detected or is ranking poorly in public search."
                )
            else:
                # We assume if it ranks well, it's somewhat active, but still flag for videos
                deficits.append(
                    f"Consider auditing {platform.capitalize()} for short-form video content (Reels/TikToks) manually."
                )

        # Calculate visibility score
        score = max(10, 100 - (len(deficits) * 15))

        audit_report = {
            "business_name": business_name,
            "social_profiles": profile_data,
            "visibility_deficits": list(set(deficits)),
            "visibility_score": score,
            "status": "success",
        }

        logging.info(
            f"✅ Physical audit complete for '{business_name}'. Visibility Score: {score}/100."
        )
        return audit_report


if __name__ == "__main__":
    scraper = SocialMediaScraper()
    result = asyncio.run(scraper.scrape_business("Action Glass Michigan"))
    print(json.dumps(result, indent=2))
