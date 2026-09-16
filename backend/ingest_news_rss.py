import asyncio
import feedparser
import httpx

BROKER_URL = "http://127.0.0.1:8085/publish"
# TechCrunch or BBC Tech News
RSS_URL = "https://feeds.bbci.co.uk/news/technology/rss.xml"

async def ingest_news():
    print("[News Ingestor] Starting live RSS feed...")
    async with httpx.AsyncClient() as client:
        while True:
            try:
                # feedparser parses synchronously, which is fine for this lightweight script
                feed = feedparser.parse(RSS_URL)
                
                # Grab top 5 articles
                articles = []
                for entry in feed.entries[:5]:
                    articles.append({
                        "title": entry.title,
                        "link": entry.link,
                        "published": entry.get("published", "")
                    })
                
                if articles:
                    payload = {
                        "topic": "news_feed",
                        "payload": {"source": "BBC Technology", "articles": articles}
                    }
                    
                    broker_res = await client.post(BROKER_URL, json=payload, timeout=5.0)
                    if broker_res.status_code == 200:
                        print(f"[News Ingestor] Successfully pushed {len(articles)} headlines.")
                    else:
                        print(f"[News Ingestor] Broker error: {broker_res.text}")
                        
            except Exception as e:
                print(f"[News Ingestor] Exception: {e}")
                
            await asyncio.sleep(120) # Poll every 2 minutes

if __name__ == "__main__":
    try:
        asyncio.run(ingest_news())
    except KeyboardInterrupt:
        print("[News Ingestor] Shutting down.")
