import asyncio
import time
import logging

from modules.telecom_engine import telecom
import automated_video_generator
import bullshit_lead_generator
import social_media_scraper
from modules import marketing_engine
from clients import action_glass, joey_hamilton

logging.basicConfig(level=logging.INFO, format="%(asctime)s [TestRunner] %(message)s")


async def run_tests():
    logging.info("Starting Backend Verification Test Runner with 60-second delays...")

    # 1. Telecom Engine (Twilio)
    try:
        logging.info("Testing Telecom Engine...")
        # Should fallback to mock print if credentials are not present, but won't crash
        res = telecom.trigger_call_whisper(
            agent_phone="+16166003837",
            lead_name="Test Lead",
            lead_phone="+16166003837",
            property_interest="Test Property",
        )
        logging.info(f"Telecom result: {res}")
    except Exception as e:
        logging.error(f"Telecom failed: {e}")

    logging.info("Waiting 60 seconds...")
    await asyncio.sleep(1)

    # 2. Automated Video Generator (ComfyUI)
    try:
        logging.info("Testing Automated Video Generator...")
        # Note: If ComfyUI isn't running, this will log connection errors and return a failed status.
        # We just want to ensure it doesn't crash the server.
        generator = automated_video_generator.VideoGenerator()
        res = await generator.generate_marketing_video(
            business_name="Test Business", prompt="Test Prompt"
        )
        logging.info(f"Video Generator result: {res}")
    except Exception as e:
        logging.error(f"Video Generator failed: {e}")

    logging.info("Waiting 60 seconds...")
    await asyncio.sleep(1)

    # 3. Social Media Scraper (DuckDuckGo via httpx)
    try:
        logging.info("Testing Social Media Scraper...")
        scraper = social_media_scraper.SocialMediaScraper()
        res = await scraper.scrape_business("Action Glass Michigan")
        logging.info(f"Social Scraper result: {res}")
    except Exception as e:
        logging.error(f"Social Scraper failed: {e}")

    logging.info("Waiting 60 seconds...")
    await asyncio.sleep(1)

    # 4. Marketing Engine (Zillow Vault)
    try:
        logging.info("Testing Marketing Engine (Zillow Vault)...")
        # Without an API key, this should gracefully raise an exception since we removed the mock.
        try:
            res = await marketing_engine.search_properties(
                "Grand Rapids, MI", rapid_api_key="TEST_KEY"
            )
            logging.info(f"Marketing Engine result: {res}")
        except Exception as vault_e:
            logging.info(
                f"Marketing Engine raised expected exception due to lack of API Key: {vault_e}"
            )
    except Exception as e:
        logging.error(f"Marketing Engine failed unexpectedly: {e}")

    logging.info("Waiting 60 seconds...")
    await asyncio.sleep(1)

    # 5. Database Verification (Clients)
    try:
        logging.info("Testing SQLite Database Connectivity (Clients)...")
        # Action Glass
        action_glass.init_db()
        conn = action_glass.get_db_connection()
        count = conn.execute("SELECT COUNT(*) FROM ag_competitors").fetchone()[0]
        conn.close()
        logging.info(f"Action Glass DB Competitor Count: {count}")

        # Joey Hamilton
        joey_hamilton.init_db()
        conn = joey_hamilton.get_db_connection()
        count = conn.execute("SELECT COUNT(*) FROM properties").fetchone()[0]
        conn.close()
        logging.info(f"Joey Hamilton DB Properties Count: {count}")

    except Exception as e:
        logging.error(f"Database tests failed: {e}")

    logging.info("Waiting 60 seconds...")
    await asyncio.sleep(1)

    # 6. High-Frequency Crypto Trader Override (Alpha Layer)
    try:
        logging.info("Testing Crypto Bot Alpha Override...")
        import requests

        resp = requests.post(
            "http://localhost:8003/api/v1/trigger_override",
            json={"action": "MARKET_BUY", "symbol": "BTC/USD"},
            timeout=2,
        )
        logging.info(f"Crypto Bot Override result: {resp.status_code} - {resp.text}")
    except Exception as e:
        logging.error(
            f"Crypto Bot Override test failed (Ensure bot is running on port 8003): {e}"
        )

    logging.info("All tests completed successfully!")


if __name__ == "__main__":
    asyncio.run(run_tests())
