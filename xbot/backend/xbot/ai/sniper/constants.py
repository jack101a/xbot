import logging
import re

logger = logging.getLogger(__name__)

VALID_ANGLES = {"contrarian", "framework", "question", "witty", "data", "insight"}
VALID_RESPONSE_MODES = {
    "pure_gif",
    "emoji_reaction",
    "punchy_one_liner",
    "witty_sarcasm",
    "casual_take",
    "in_depth_breakdown",
}

SNIPER_PROMPT_TEMPLATE = """=== HIGH-IMPACT SNIPER REPLY ARCHITECTURE (6 DYNAMIC MODALITIES) ===
Read the room, attached media, and top comments to select ONE of the following 6 response modes:

1. pure_gif:
   - Provide a targeted Tenor / X GIF search query in `gif_query` (e.g. 'side eye', 'popcorn eating', 'facepalm', 'mind blown', 'sweating nervous', 'tired sigh').
   - `reply_text` should be an optional ultra-short reaction (e.g. 'real', '💀', 'no notes', 'pure cinema', 'W') or empty/minimal.

2. emoji_reaction:
   - Ultra-short, authentic emoji reaction in `reply_text` (1-2 emojis max, e.g. 💀, 😭, 🔥, 🤌, 💯) when the room is purely reactive.
   - NO filler text.

3. punchy_one_liner:
   - Short conversational punch (20-90 chars) delivering immediate humor, dry agreement, or disbelief.
   - Examples: 'ok i agree', 'they are not gonna like this one', 'bro had 2 lines and dipped 💀', 'Rockstar is making a second life not a game 🔥'.

4. witty_sarcasm:
   - 1-2 sentences (50-160 chars) of dry humor, sarcastic observation, or relatable banter matching the comments.
   - Great for roasting bad takes, tech ironies, movie tropes, or shared community pain points.

5. casual_take:
   - Clear, grounded perspective or opinion (60-200 chars) without sounding like a textbook or lecture.
   - Conversational, human, authentic.

6. in_depth_breakdown:
   - 2-4 sentences (120-260 chars) of technical nuance, empirical data, or filmmaking/story analysis when the room calls for domain depth.

=== CRITICAL RULES (STRICT) ===
- STRICT CONTEXT ACCURACY: Talk directly and accurately about the exact subject, image, and discussion in the target tweet. NEVER force artificial analogies or unrelated hobbies.
- NO FORCED QUESTIONS: NEVER force your reply to end with a question mark ('?'). Only ask a question if your angle naturally calls for one. Statements, roasts, memes, and punchy takes should end with natural punctuation (. ! or none).
- NO FIXED LENGTH MINIMUMS: Ultra-short replies (1-30 chars) are 100% valid and encouraged for pure_gif, emoji_reaction, and punchy_one_liner modes.
- EMOJIS & ZERO HASHTAGS: Use natural, expressive emojis (💀, 😭, 🔥, 😂, 💯, 🤌) where fitting to express human emotion and timing. NEVER use hashtags (#) in replies — hashtags in replies look robotic and algorithmic.
- ZERO AI CLICHÉS: STRICTLY BANNED: delve, testament, tapestry, supercharge, beacon, plethora, moreover, furthermore, in conclusion, game-changer, leverage, multifaceted, pivotal, foster, vital, crucial, endeavor, Great post!, Awesome thread!
- NO INDIAN POLITICS: Zero references to Indian political parties or figures.
"""

TECH_KEYWORDS = {
    "iphone", "macbook", "laptop", "smartphone", "android", "apple", "gpu", "nvidia",
    "intel", "amd", "snapdragon", "ai", "llm", "chatgpt", "claude", "deepseek", "openai",
    "anthropic", "coding", "developer", "software", "hardware", "battery", "benchmark",
    "saas", "tech", "gadget", "chip", "semiconductor", "google", "meta", "microsoft"
}

ANIME_KEYWORDS = {
    "one piece", "luffy", "zoro", "oda", "god valley", "manga", "anime", "powerscaling",
    "shonen", "naruto", "bleach", "jujutsu", "jjk", "demon slayer", "chapter", "spoilers",
    "toei", "dragon ball", "goku", "otaku", "cosplay", "sanji", "straw hat"
}

MOVIES_KEYWORDS = {
    "movie", "film", "cinema", "trailer", "box office", "actor", "director",
    "hollywood", "bollywood", "oscar", "streaming", "netflix", "hbo", "theatrical", "series"
}

GROWTH_KEYWORDS = {
    "drop your handle", "follow back", "mutuals", "f4f", "verified mutuals",
    "looking for mutuals", "follow everyone", "grow together", "drop handles"
}

BANNED_AI_WORDS_REGEX = re.compile(
    r"\b(delve|delving|tapestry|tapestries|testament|beacon|plethora|"
    r"moreover|furthermore|in conclusion|game[- ]?changer|leverage|leveraging|"
    r"multifaceted|pivotal|foster|fostering|vital|crucial|endeavor|endeavors|"
    r"supercharge|supercharged|supercharging|"
    r"realm|buckle up|let'?s dive in|unpacking|navigating the)\b",
    re.IGNORECASE,
)

BANNED_BOT_PRAISE_REGEX = re.compile(
    r"^(great (post|tweet|thread)|100% agree|awesome (post|thread)|"
    r"couldn'?t agree more|spot on|so true|well said)[!.]*",
    re.IGNORECASE,
)

BANNED_ROUTINE_FILLER_REGEX = re.compile(
    r"\b(my (morning|evening) (coffee|chai|tea)|sipping (my )?(chai|coffee)|"
    r"adrak chai|iced matcha|terrace sunset|peace is underrated|"
    r"just finished (my )?workout|in my gym gear|average day in)\b",
    re.IGNORECASE,
)

BANNED_ROBOTIC_QUESTIONS_REGEX = re.compile(
    r"\b(are you (trusting|ready for|excited for|holding onto|falling for|hyped for)|"
    r"what do you think|do you agree|what are your thoughts|let me know in the comments|"
    r"drop your thoughts|which side are you on)\b",
    re.IGNORECASE,
)

BANNED_POLITICS_REGEX = re.compile(
    r"\b(bjp|congress|aap|aam aadmi party|modi|narendra modi|rahul gandhi|"
    r"kejriwal|arvind kejriwal|amit shah|yogi|adityanath|hindutva|rss|"
    r"rashtriya swayamsevak|lok sabha|rajya sabha|bjp4india|incindia|"
    r"indian politics|indian election|mamata banerjee|samajwadi party|"
    r"bsp|dmk|aiadmk|shiv sena|trinamool)\b",
    re.IGNORECASE,
)

