import httpx
import asyncio
import json


async def test_platform_post_generator():
    system_prompt = """You are an expert platform-native content strategist and local SEO specialist for West Michigan businesses. Your posts must be engineered to be indexed and ranked FAST by each platform's algorithm — not generic, not templated, algorithmically precise.

Business: "Action Glass Michigan" | Industry: "Glass Repair" | County: "Kent County"
Promotion: "something you have not heard in a minute.  \"GO TEAM!\" Have a great day its going to be the best day ever. each day has opportunity to be the best day ever. 
 Is today gonna be your day?"

CRITICAL ALGORITHM RULES PER PLATFORM (follow exactly):

ALL PLATFORMS: You MUST include the specific Promotion/Offer provided above in every single post naturally. Do not ignore the promo.

GOOGLE: Front-load geo-intent keywords (people search "near me" or "[city] [service]"). NAP-consistent phrasing. schema_title must be under 60 chars and include the county name. meta_description must be under 155 chars, include a local intent phrase, and end with a micro-CTA. local_keywords must be long-tail geo-modified phrases someone in Kent County would actually type (not brand names).

FACEBOOK: The entire headline + first sentence of body must be under 90 characters (this is what shows before "See More" — the algo rewards early engagement on visible text). Body is 2-3 sentences, conversational, no jargon. CTA drives a comment or message (comments boost reach 3x). Include 3-5 highly targeted, algorithmically optimized hashtags (mix of local, industry, and niche tags) to maximize organic outreach.

INSTAGRAM: caption_hook must be under 125 characters (this is the preview before "more" tap — the algo scores retention here). Body is 2-4 lines max. hashtags: use EXACTLY 3-5 highly targeted hashtags (2024 Instagram algo penalizes hashtag spam; 3-5 niche tags outperform 20+ generic ones). Mix one local tag, one industry tag, one niche tag.

TIKTOK: hook_text is the FIRST 1-3 SECONDS spoken aloud — TikTok transcribes audio and indexes it for search, so include the primary keyword in the spoken hook. script is a 30-45 second natural spoken script (TikTok rewards watch time and loop completion). caption_keywords: write 3-5 words as a search-optimized caption — TikTok's search engine indexes captions exactly like Google, so use phrases people search for (e.g. "Ottawa County marketing tips").

TWITTER / X: tweet must be under 220 characters. Zero external links (the X algorithm heavily suppresses tweets with external links). Use reply-bait wording to drive 30-min engagement velocity. card_title under 50 chars, card_description under 100 chars.

PINTEREST: pin_title must be keyword front-loaded. pin_description 2-3 sentences, search-intent driven, zero fluff.

YELP: Category-exact language. Business description 100-150 words. Mention the county name 2-3x naturally. Highlight special offer in Check-In Offer format.

Respond ONLY with a single, raw, valid JSON object with NO markdown, NO code block ticks, NO intro text, matching this exact shape:
{
  "_thought_process": "Verify promo inclusion, Facebook <90 chars, Instagram exactly 3-5 tags, Yelp 100+ words...",
  "google": { "schema_title": "...", "meta_description": "...", "local_keywords": ["...", "...", "..."] },
  "facebook": { "headline": "...", "body": "...", "cta": "...", "hashtags": "..." },
  "instagram": { "caption_hook": "...", "body": "...", "hashtags": "..." },
  "tiktok": { "hook_text": "...", "script": "...", "caption_keywords": "..." },
  "twitter": { "tweet": "..." , "card_title": "...", "card_description": "..." },
  "pinterest": { "pin_title": "...", "pin_description": "..." },
  "yelp": { "business_description": "...", "category_tags": ["...", "..."], "special_offer": "..." }
}"""

    payload = {
        "messages": [{"role": "user", "content": system_prompt}],
        "use_rag": False,
        "use_web_search": False,
        "model": "gemini-1.5-flash",
    }

    print("Sending live test request to AI-BS Central Cognitive Engine...")
    async with httpx.AsyncClient(timeout=120.0) as client:
        try:
            res = await client.post("http://127.0.0.1:8000/api/chat", json=payload)
            print(f"Status Code: {res.status_code}")

            data = res.json()
            content = data.get("response") or data.get("message")
            if isinstance(content, dict) and "content" in content:
                content = content["content"]

            print("\n=== AI GENERATED PAYLOAD ===")
            print(content)
            print("============================\n")

        except Exception as e:
            print(f"Error during API call: {e}")


if __name__ == "__main__":
    asyncio.run(test_platform_post_generator())
