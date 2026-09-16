import time
import logging
import requests
import json
import xml.etree.ElementTree as ET
import asyncio
from pathlib import Path
from html.parser import HTMLParser
from technical_indicators import CryptoTechnicals

# Setup logging
logging.basicConfig(level=logging.INFO, format="%(asctime)s [NewsFirehose] %(message)s")
logger = logging.getLogger("NewsFirehose")

# --- SHM Bridge Setup ---
try:
    from shm_bridge import ShmBridge, TOPIC_HEURISTICS_TELEMETRY, FLAG_HIGH_PRIORITY
except ImportError:

    class ShmBridge:
        def push_topic_event(self, topic, flags, data):
            return 0

    TOPIC_HEURISTICS_TELEMETRY = 0x0003
    FLAG_HIGH_PRIORITY = 0x02

bridge = ShmBridge()

# Setup config
WATCHER_SYMBOLS = ["SOL/USD", "BTC/USD", "ETH/USD"]
ENV_FILE = Path("../../.env")
if ENV_FILE.exists():
    with open(ENV_FILE, "r") as f:
        for line in f:
            if "=" in line and not line.startswith("#"):
                k, v = line.strip().split("=", 1)
                if k == "WATCHER_SYMBOLS":
                    WATCHER_SYMBOLS = [s.strip() for s in v.strip('"').split(",")]


class MLStripper(HTMLParser):
    def __init__(self):
        super().__init__()
        self.reset()
        self.strict = False
        self.convert_charrefs = True
        self.fed = []

    def handle_data(self, d):
        self.fed.append(d)

    def get_data(self):
        return "".join(self.fed)


def strip_tags(html):
    s = MLStripper()
    s.feed(html)
    return s.get_data()


def fetch_crypto_news():
    """Fetches real-time news from multiple RSS feeds."""
    logger.info("Fetching unified news streams from RSS feeds...")
    news_items = []

    rss_urls = [
        "https://cointelegraph.com/rss",
        "https://www.coindesk.com/arc/outboundfeeds/rss/",
        "https://cryptoslate.com/feed/",
        "https://bitcoinmagazine.com/.rss/full/",
        "https://decrypt.co/feed",
    ]

    headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AI-BS/1.0"}
    for rss_url in rss_urls:
        try:
            response = requests.get(rss_url, headers=headers, timeout=10)
            response.raise_for_status()
            root = ET.fromstring(response.content)

            for item in root.findall("./channel/item")[
                :3
            ]:  # Get latest 3 per feed to manage LLM load
                title = (
                    item.find("title").text if item.find("title") is not None else ""
                )
                desc_raw = (
                    item.find("description").text
                    if item.find("description") is not None
                    else ""
                )
                description = strip_tags(desc_raw)[:500]  # First 500 chars

                # Map to an asset if mentioned, else general
                target_asset = "General"
                title_upper = title.upper()
                if (
                    "SOLANA" in title_upper
                    or " SOL " in title_upper
                    or title_upper.startswith("SOL")
                ):
                    target_asset = "SOL/USD"
                elif (
                    "BITCOIN" in title_upper
                    or " BTC " in title_upper
                    or title_upper.startswith("BTC")
                ):
                    target_asset = "BTC/USD"
                elif (
                    "ETHEREUM" in title_upper
                    or " ETH " in title_upper
                    or title_upper.startswith("ETH")
                ):
                    target_asset = "ETH/USD"

                if target_asset == "General":
                    target_asset = WATCHER_SYMBOLS[0] if WATCHER_SYMBOLS else "SOL/USD"

                if target_asset in WATCHER_SYMBOLS:
                    news_items.append(
                        {
                            "title": title,
                            "description": description,
                            "asset": target_asset,
                        }
                    )
        except Exception as e:
            logger.error(f"Failed to fetch RSS from {rss_url}: {e}")
            continue

    return news_items


def call_stehouwer_llm(title, description, asset, technicals="None"):
    """Calls local Ollama API to evaluate sentiment"""
    prompt = f"""You are an expert cryptocurrency trading AI. Analyze the following news headline and short description.
Determine the sentiment specifically for {asset}.
Is this HIGH CONVICTION BULLISH, BEARISH, or NEUTRAL?
Consider the technical indicators provided below as confluence. If news is bullish but RSI is > 70 (Overbought), you might want to lower confidence. If RSI is < 30 (Oversold) and news is bullish, you can have very high confidence.
Respond in strict JSON format with keys "sentiment" (value must be one of: "bullish", "bearish", "neutral") and "confidence" (0-100 integer).
Do not output anything other than the JSON object.

Headline: {title}
Description: {description}
Technical Indicators: {technicals}
"""
    try:
        resp = requests.post(
            "http://127.0.0.1:11434/api/generate",
            json={
                "model": "stehouwer_llm",
                "prompt": prompt,
                "format": "json",
                "stream": False,
            },
            timeout=30,
        )
        resp.raise_for_status()
        data = resp.json()
        # Parse JSON
        result = json.loads(data.get("response", "{}"))
        return result.get("sentiment", "neutral").lower(), int(
            result.get("confidence", 0)
        )
    except Exception as e:
        logger.error(f"LLM API Call failed: {e}")
        return "neutral", 0


def evaluate_news_with_llm(news_items):
    """
    Pipes news to Stehouwer LLM.
    If HIGH CONVICTION (confidence >= 80) BULLISH, trigger Alpha Override.
    """
    tech_engine = CryptoTechnicals()

    for item in news_items:
        title = item["title"]
        asset = item["asset"]
        desc = item["description"]

        logger.info(f"Fetching technical confluence for {asset}...")
        try:
            signals = asyncio.run(tech_engine.get_all_signals(asset))
            tech_str = json.dumps(signals)
        except Exception as e:
            logger.error(f"Failed to fetch technicals: {e}")
            tech_str = "None"

        logger.info(
            f"Stehouwer LLM Evaluating: '{title}' for {asset} with technicals: {tech_str}"
        )

        sentiment, confidence = call_stehouwer_llm(title, desc, asset, tech_str)
        logger.info(f"LLM Result: {sentiment.upper()} (Confidence: {confidence}%)")

        if sentiment == "bullish" and confidence >= 80:
            logger.warning(
                f"HIGH CONVICTION BULLISH on {asset}. Triggering Market Buy Override!"
            )
            try:
                # Target port 8006 where Crypto Trader Bot is now running
                resp = requests.post(
                    "http://localhost:8006/api/v1/trigger_override",
                    json={"action": "MARKET_BUY", "symbol": asset},
                    timeout=5,
                )
                logger.info(f"Crypto Bot response: {resp.text}")
            except Exception as e:
                logger.error(f"Failed to trigger Crypto Bot API (Is it running?): {e}")

            # Broadcast the heuristics to the broader swarm via SHM
            payload = f"LLM_ALPHA|BULLISH_{asset}"
            bridge.push_topic_event(
                TOPIC_HEURISTICS_TELEMETRY,
                FLAG_HIGH_PRIORITY,
                payload.encode("utf-8")[:60],
            )

    # Cleanup engine resources after evaluating batch
    try:
        asyncio.run(tech_engine.close())
    except:
        pass


def run_firehose():
    logger.info("Starting Multi-Modal News Firehose Daemon...")
    while True:
        try:
            news = fetch_crypto_news()
            if news:
                evaluate_news_with_llm(news)
        except Exception as e:
            logger.error(f"Firehose error: {e}")

        # Obey rate limits (300 seconds for RSS)
        time.sleep(300)


if __name__ == "__main__":
    run_firehose()
