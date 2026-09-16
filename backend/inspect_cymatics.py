import asyncio
import json
from playwright.async_api import async_playwright

async def inspect():
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        page = await browser.new_page()
        print("Navigating to https://cymatics.fm/pages/cymatics-c86v...")
        await page.goto("https://cymatics.fm/pages/cymatics-c86v", wait_until="domcontentloaded", timeout=30000)
        await page.wait_for_timeout(3000)
        
        # Query all dl-cards and images
        cards = await page.query_selector_all(".dl-card, [class*='dl-card']")
        print(f"Total dl-card elements found: {len(cards)}")
        
        results = []
        for i, card in enumerate(cards):
            text = (await card.inner_text()).strip()
            html = await card.inner_html()
            
            # Find img src and data-real-img
            img = await card.query_selector("img")
            img_src = await img.get_attribute("src") if img else None
            data_real = await img.get_attribute("data-real-img") if img else None
            alt = await img.get_attribute("alt") if img else None
            
            # Find any buttons or links
            btn = await card.query_selector("button, a")
            btn_text = (await btn.inner_text()).strip() if btn else None
            btn_href = await btn.get_attribute("href") if btn else None
            
            results.append({
                "index": i + 1,
                "text": text,
                "alt": alt,
                "img_src": img_src,
                "data_real_img": data_real,
                "btn_text": btn_text,
                "btn_href": btn_href,
                "html_snippet": html[:300]
            })
            
        with open("C:/AI-BS/saved_data/cymatics_cards_inspection.json", "w", encoding="utf-8") as f:
            json.dump(results, f, indent=2)
            
        print(f"Inspection complete. Saved {len(results)} items to C:/AI-BS/saved_data/cymatics_cards_inspection.json")
        for r in results:
            print(f"Card #{r['index']}: {r['alt']} | Btn: {r['btn_text']} | Href: {r['btn_href']}")

        await browser.close()

if __name__ == "__main__":
    asyncio.run(inspect())
