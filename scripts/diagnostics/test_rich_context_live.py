import asyncio
import json
import re
from pathlib import Path
from playwright.async_api import async_playwright
from xbot.ai.client import get_ai_client
from xbot.config import settings

async def main():
    profile_dir = Path("/home/ubuntu/projects/xbot/data/profiles/test_profile1")
    
    test_urls = [
        "https://x.com/DiscussingFilm/status/2093059147700764805",
        "https://x.com/DiscussingFilm/status/2093002605375152140",
        "https://x.com/BSCNews/status/2093233583574110626",
    ]
    
    test_cases = []
    
    async with async_playwright() as p:
        context = await p.chromium.launch_persistent_context(
            user_data_dir=str(profile_dir / "browser_data"),
            headless=True,
            args=["--no-sandbox", "--disable-dev-shm-usage"]
        )
        page = await context.new_page()
        page.set_default_timeout(30000)
        
        for url in test_urls:
            print(f"\n=================== SCRAPING TWEET PERMALINK: {url} ===================")
            try:
                await page.goto(url, wait_until="domcontentloaded", timeout=25000)
                await page.wait_for_selector("[data-testid='tweet']", timeout=15000)
                await asyncio.sleep(3)
                
                # Extract root tweet, images, and scroll to collect comments
                root_el = (await page.query_selector_all("[data-testid='tweet']"))[0]
                user_el = await root_el.query_selector("[data-testid='User-Name']")
                author = (await user_el.inner_text()).replace('\n', ' | ') if user_el else "DiscussingFilm"
                
                text_el = await root_el.query_selector("[data-testid='tweetText']")
                text = (await text_el.inner_text()).strip() if text_el else ""
                
                # Attached media & alt descriptions
                img_els = await root_el.query_selector_all("img")
                media_alts = []
                for img in img_els:
                    src = await img.get_attribute("src") or ""
                    alt = await img.get_attribute("alt") or ""
                    if src.startswith("http") and not any(x in src for x in ("profile_images", "emoji", "twemoji", "avatar", "svg")):
                        if alt and alt.lower() not in ("image", "photo", "embedded video") and alt not in media_alts:
                            media_alts.append(alt)
                
                # Scroll down to load 15-20 comment replies
                collected_comments = []
                seen_c = set()
                
                for scroll_step in range(4):
                    articles = await page.query_selector_all("[data-testid='tweet']")
                    for art in articles[1:]:
                        c_text_el = await art.query_selector("[data-testid='tweetText']")
                        if not c_text_el:
                            continue
                        c_text = (await c_text_el.inner_text()).strip()
                        if not c_text or c_text in seen_c or c_text == text:
                            continue
                        seen_c.add(c_text)
                        
                        c_user_el = await art.query_selector("[data-testid='User-Name']")
                        c_author = (await c_user_el.inner_text()).split('\n')[0] if c_user_el else "user"
                        
                        like_el = await art.query_selector("[data-testid='like'], button[aria-label*='Like']")
                        like_val = 0
                        if like_el:
                            aria = await like_el.get_attribute("aria-label") or ""
                            inner = await like_el.inner_text() or ""
                            # Parse metric
                            m = re.search(r'([\d\.]+)\s*([KkMm]?)', aria + " " + inner)
                            if m:
                                num = float(m.group(1))
                                unit = m.group(2).upper()
                                like_val = int(num * 1000) if unit == 'K' else int(num * 1000000) if unit == 'M' else int(num)
                        
                        collected_comments.append({
                            "author": c_author,
                            "text": c_text,
                            "likes": like_val
                        })
                    
                    await page.evaluate("window.scrollBy(0, 800)")
                    await asyncio.sleep(2)
                    
                # Sort comments descending by likes (most popular first)
                collected_comments.sort(key=lambda c: c["likes"], reverse=True)
                top_comments = collected_comments[:10]
                
                test_cases.append({
                    "url": url,
                    "author": author,
                    "text": text,
                    "media_alts": media_alts,
                    "top_comments": top_comments
                })
                print(f"Scraped '{text[:60]}...' | Media: {media_alts} | Top Comments: {len(top_comments)}")
                
            except Exception as e:
                print(f"Error scraping {url}: {e}")
                
        await context.close()
        
    print(f"\n=================== RUNNING AI RICH CONTEXT GENERATION ({len(test_cases)} CASES) ===================")
    ai_client = get_ai_client()
    
    for idx, tc in enumerate(test_cases, 1):
        print("\n" + "="*85)
        print(f"🔥 TEST CASE {idx}: Tweet by {tc['author']}")
        print(f"URL: {tc['url']}")
        print(f"POST CONTENT:\n\"{tc['text']}\"")
        if tc["media_alts"]:
            print(f"ATTACHED MEDIA DESCRIPTIONS: {tc['media_alts']}")
        else:
            print("ATTACHED MEDIA: Embedded screenshot / media")
            
        print("\nTOP COMMENTS IN ROOM (Ranked by most likes):")
        for ci, c in enumerate(tc["top_comments"][:6], 1):
            print(f"  {ci}. {c['author']}: \"{c['text']}\" [{c['likes']:,} likes]")
            
        comments_formatted = ""
        for ci, c in enumerate(tc["top_comments"][:10], 1):
            comments_formatted += f"{ci}. {c['author']}: \"{c['text']}\" ({c['likes']:,} likes)\n"

        prompt = f"""You are an authentic, culturally savvy creator on X (Twitter).
You are analyzing this real live post to generate:
1. A sharp, high-retention Sniper Reply (direct reply in thread)
2. A viral Quote Tweet (standalone perspective take)

=== TARGET TWEET ===
Author: {tc['author']}
Content: "{tc['text']}"
Attached Media / Visual Details: {tc['media_alts'] if tc['media_alts'] else 'Embedded image/video'}

=== TOP 10 COMMENTS IN THE ROOM (VIBE, SENTIMENT & DEBATE) ===
{comments_formatted if comments_formatted else 'No comments yet'}

=== GENERATION RULES ===
1. 100% CONTEXT ACCURACY: Understand what the post, image, and comments are actually talking about. Talk directly about the subject. Never force bizarre analogies or unrelated topics.
2. NATURAL HUMAN VOICE: Sound witty, observant, conversational, and authentic. 
3. EMOJIS & HASHTAGS: Use natural emojis where fitting (e.g. 💀, 😭, 🔥, 😂, 💯). Include 1-2 relevant hashtags if natural (e.g. #GTA6, #Cinema, #DCU, #Crypto).
4. GIF ATTACHMENT: Provide a 1-3 word Tenor search query in `gif_query` if a reaction GIF adds comedic timing or punch; otherwise null.

Return ONLY a JSON object:
{{
  "topic_understanding": "1-2 sentences explaining what this post, image, and comment section are actually discussing",
  "sniper_reply": "Your contextual reply text",
  "reply_gif_query": "Tenor search query or null",
  "quote_tweet": "Your quote tweet take",
  "quote_gif_query": "Tenor search query or null"
}}
"""
        try:
            resp = await ai_client.chat.completions.create(
                model=settings.MODEL_REPLY_ANALYSIS,
                messages=[
                    {"role": "system", "content": "You are a world-class social media strategist and authentic creator on X."},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.75,
                max_tokens=600
            )
            raw = resp.choices[0].message.content.strip()
            if raw.startswith("```json"):
                raw = raw[7:]
            if raw.startswith("```"):
                raw = raw[3:]
            if raw.endswith("```"):
                raw = raw[:-3]
            out = json.loads(raw.strip())
            
            print("\n------------------- 🤖 AI GENERATED OUTPUT -------------------")
            print(f"📌 TOPIC UNDERSTANDING:\n{out.get('topic_understanding')}")
            print(f"\n💬 SNIPER REPLY:\n\"{out.get('sniper_reply')}\"")
            if out.get("reply_gif_query"):
                print(f"   🎬 [Attached Tenor GIF Query: '{out.get('reply_gif_query')}']")
            print(f"\n🔄 QUOTE TWEET:\n\"{out.get('quote_tweet')}\"")
            if out.get("quote_gif_query"):
                print(f"   🎬 [Attached Tenor GIF Query: '{out.get('quote_gif_query')}']")
            print("="*85)
        except Exception as e:
            print(f"Generation error: {e}")

if __name__ == "__main__":
    asyncio.run(main())
