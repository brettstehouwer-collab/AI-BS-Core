import asyncio
import httpx
from bs4 import BeautifulSoup
import re
import csv
import logging
import os
import random
import json
import sqlite3
import uuid
from datetime import datetime

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("LeadGenerator")


class WestMichiganLeadGen:
    def __init__(self):
        # Base list of local directories and resources for family businesses
        self.target_urls = [
            "https://fbagr.org/member-directory/",
            "https://www.westcoastchamber.org/list/",
        ]

        # Heuristics for viable leads
        self.family_keywords = [
            "family",
            "owned",
            "generation",
            "brothers",
            "sons",
            "daughters",
        ]
        self.email_regex = re.compile(r"[\w\.-]+@[\w\.-]+\.\w+")
        self.results = []

        self.db_path = os.path.join(os.path.dirname(__file__), "state.db")
        self.cache_file = os.path.join(os.path.dirname(__file__), "lead_gen_cache.json")
        self.visited_urls = self._load_cache()

    def _load_cache(self) -> set:
        if os.path.exists(self.cache_file):
            try:
                with open(self.cache_file, "r", encoding="utf-8") as f:
                    return set(json.load(f))
            except json.JSONDecodeError:
                return set()
        return set()

    def _save_cache(self):
        with open(self.cache_file, "w", encoding="utf-8") as f:
            json.dump(list(self.visited_urls), f)

    async def fetch_page(self, url: str):
        # 24/7 Server Safe: Humanized, highly conservative delays to prevent IP bans.
        delay = random.uniform(15.0, 45.0)
        logger.info(f"Sleeping for {delay:.2f} seconds before fetching...")
        await asyncio.sleep(delay)
        try:
            async with httpx.AsyncClient(timeout=15.0) as client:
                headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"}
                response = await client.get(url, headers=headers)
                response.raise_for_status()
                return response.text
        except Exception as e:
            logger.error(f"Failed to fetch {url}: {e}")
            return None

    def extract_emails(self, text: str) -> list:
        emails = self.email_regex.findall(text)
        # Filter out common false positives
        return list(
            set(
                [
                    e
                    for e in emails
                    if not e.endswith((".png", ".jpg", ".gif", "wixpress.com"))
                ]
            )
        )

    async def scan_url(self, url: str):
        if url in self.visited_urls:
            logger.info(f"Skipping cached URL: {url}")
            return

        logger.info(f"Scanning target: {url}")
        html = await self.fetch_page(url)
        if not html:
            return

        self.visited_urls.add(url)
        self._save_cache()

        soup = BeautifulSoup(html, "html.parser")
        page_text = soup.get_text(separator=" ", strip=True).lower()

        # Check if it triggers family-owned heuristics
        is_family = any(kw in page_text for kw in self.family_keywords)

        emails = self.extract_emails(html)

        if is_family:
            title = soup.title.string if soup.title else "Unknown Business"
            # If emails exist, add a record for each. If not, add a fallback prospect record.
            if emails:
                for email in emails:
                    self.results.append(
                        {
                            "business_name": title.strip(),
                            "url": url,
                            "email": email,
                            "heuristic_match": "Family Owned - Contact Available",
                        }
                    )
                    logger.info(f"Lead Acquired: {email} from {title}")
            else:
                self.results.append(
                    {
                        "business_name": title.strip(),
                        "url": url,
                        "email": "NO EMAIL - Prospect for Web Build",
                        "heuristic_match": "Family Owned - Zero Digital Presence",
                    }
                )
                logger.info(f"Prospect Acquired: No Email from {title}")

    async def run_sweep(self, custom_urls: list = None):
        urls_to_scan = custom_urls if custom_urls else self.target_urls
        logger.info(f"Initiating sweep on {len(urls_to_scan)} targets.")

        for url in urls_to_scan:
            await self.scan_url(url)

        self._export_to_db()
        return self.results

    def _export_to_db(self):
        if not self.results:
            logger.warning("No leads found to export to DB.")
            return

        try:
            conn = sqlite3.connect(self.db_path)
            try:
                conn.execute("PRAGMA journal_mode=WAL;")
                conn.execute("PRAGMA synchronous=NORMAL;")
            except Exception:
                pass
            cursor = conn.cursor()

            inserted_count = 0
            for row in self.results:
                record_id = str(uuid.uuid4())
                date_acq = datetime.utcnow().isoformat()

                # Use INSERT OR IGNORE in case email is a unique constraint later
                cursor.execute(
                    """
                    INSERT INTO advertising_leads (id, business_name, url, email, heuristic_match, date_acquired)
                    VALUES (?, ?, ?, ?, ?, ?)
                """,
                    (
                        record_id,
                        row["business_name"],
                        row["url"],
                        row["email"],
                        row["heuristic_match"],
                        date_acq,
                    ),
                )
                inserted_count += cursor.rowcount

            conn.commit()
            logger.info(f"Exported {inserted_count} new leads to state.db database.")
        except Exception as e:
            logger.error(f"Database insertion failed: {e}")
        finally:
            conn.close()


if __name__ == "__main__":
    # Real Run Execution
    gen = WestMichiganLeadGen()
    logger.info("Starting real web scraping sweep...")
    asyncio.run(gen.run_sweep(["https://fbagr.org/member-directory/"]))
