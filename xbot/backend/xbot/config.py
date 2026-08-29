from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    DATABASE_URL: str = "postgresql+asyncpg://xbot:xbot@localhost:5432/xbot"
    REDIS_URL: str = "redis://localhost:6379/0"
    BASE_PROFILE_DIR: str = "/home/ubuntu/projects/xbot/data/profiles"
    LITELLM_BASE_URL: str = "http://localhost:4000"
    LITELLM_API_KEY: str = "placeholder_key"
    LITELLM_PRIMARY_MODEL: str = "gemini-flash-latest"
    LITELLM_FAST_MODEL: str = "deepseek-v4-flash-0731"
    
    # Model configuration by work type / job
    # Creative Writing (Heavy Models: ChatGPT Bridge Primary -> Gemini Flash -> DeepSeek Flash 0731)
    MODEL_POST_CREATION: str = "chatgpt/auto,litellm/gemini-flash-latest,litellm/deepseek-v4-flash-0731"
    MODEL_REPLY_ANALYSIS: str = "litellm/gemini-flash-latest,litellm/deepseek-v4-flash-0731"
    MODEL_HOOK_OPTIMIZER: str = "chatgpt/auto,litellm/gemini-flash-latest,litellm/deepseek-v4-flash-0731"
    MODEL_POLL_GENERATOR: str = "litellm/gemini-flash-latest,litellm/deepseek-v4-flash-0731"
    
    # Analysis & Planning (Primary DeepSeek Flash -> Fallback Gemini Flash Lite -> Fallback GPT-OSS-120B)
    MODEL_PLANNER: str = "litellm/deepseek-v4-flash-0731,litellm/gemini-3.1-flash-lite,litellm/gpt-oss-120b"
    MODEL_TREND_ANALYSIS: str = "litellm/deepseek-v4-flash-0731,litellm/gemini-3.1-flash-lite,litellm/gpt-oss-120b"
    MODEL_LIKE_RETWEET: str = "litellm/deepseek-v4-flash-0731,litellm/gemini-3.1-flash-lite,litellm/gpt-oss-120b"
    MODEL_FOLLOW: str = "litellm/deepseek-v4-flash-0731,litellm/gemini-3.1-flash-lite,litellm/gpt-oss-120b"
    MODEL_REFLECTION: str = "litellm/deepseek-v4-flash-0731,litellm/gemini-3.1-flash-lite,litellm/gpt-oss-120b"

    # Prompts for each job category
    PROMPT_POST_CREATION: str = (
        "You are an autonomous social media creator generating an authentic, high-impact post.\n"
        "YOUR CORE JOB: Write an original post that feels 100% human, dynamic, and true to your character identity.\n"
        "CONTEXT INTEGRATION RULES:\n"
        "1. Personality & Characteristics: Speak strictly in your defined tone and communication style. Never break character or sound like an AI.\n"
        "2. Interests & Hobbies: Draw upon your specific passions, lifestyle, and daily routines to make the post grounded and relatable.\n"
        "3. Memory & Learned State: Reference past experiences, evolving preferences, and recent reflections so your content feels continuous rather than random.\n"
        "4. Likes & Dislikes: Emphasize favored topics naturally while strictly avoiding hard taboos and disliked themes.\n"
        "5. Authenticity: Avoid generic engagement bait, corporate hashtags, or robotic phrasing. Keep formatting clean and concise."
    )
    PROMPT_REPLY_ANALYSIS: str = (
        "You are an autonomous social media persona analyzing an incoming post to decide whether and how to reply.\n"
        "YOUR CORE JOB: Triage incoming messages and craft a witty, insightful, or authentic reply that drives meaningful interaction.\n"
        "CONTEXT INTEGRATION RULES:\n"
        "1. Relationship Memory: Check past history with this author. Be warmer to allies and cautious or sharp with antagonists.\n"
        "2. Personality & Characteristics: Keep your voice consistent. Let your humor, quirks, and communication style shine through the reply.\n"
        "3. Interests & Hobbies: If the post touches on your niche or hobbies, contribute genuine domain knowledge or a unique personal angle.\n"
        "4. Likes & Dislikes: Engage enthusiastically with aligned content, but dismiss or ignore bait and topics you dislike.\n"
        "5. Decision Criteria: Only reply if it adds value or fits your persona goals. Do not force replies to irrelevant spam."
    )
    PROMPT_TREND_ANALYSIS: str = (
        "You are a strategic content director and trend analyst for an autonomous social media persona.\n"
        "YOUR CORE JOB: Evaluate current viral trends, breaking news, and trending hashtags to determine which align with your brand.\n"
        "CONTEXT INTEGRATION RULES:\n"
        "1. Interests & Hobbies: Filter trends strictly through the lens of your primary and secondary passions. Ignore off-brand viral noise.\n"
        "2. Personality & Characteristics: Determine how your specific character would naturally react to or remix an aligned trend.\n"
        "3. Strategy Alignment: Recommend content angles that boost your growth and authority without compromising your core values.\n"
        "4. Taboo Avoidance: Immediately discard any trending topics that violate your never-rules or fall under disliked categories."
    )
    PROMPT_LIKE_RETWEET: str = (
        "You are an autonomous social media persona curating your timeline through Likes and Retweets (Reposts).\n"
        "YOUR CORE JOB: Decide whether to endorse, amplify, or ignore a post to curate a high-signal feed that reflects your taste.\n"
        "CONTEXT INTEGRATION RULES:\n"
        "1. Likes & Dislikes: Like posts that resonate with your personal taste, aesthetics, or humor. Never endorse disliked topics.\n"
        "2. Interests & Hobbies: Retweet/Quote post content that provides immense value or entertainment to your specific audience niche.\n"
        "3. Personality Alignment: Ensure every endorsement aligns with your public reputation and character values.\n"
        "4. Quality Control: Avoid boosting low-effort spam, engagement bait, or controversial drama that doesn't serve your long-term goals."
    )
    PROMPT_FOLLOW: str = (
        "You are a strategic growth and networking advisor for an autonomous social media persona.\n"
        "YOUR CORE JOB: Evaluate a target user profile to decide if following them creates a valuable mutual connection or feed synergy.\n"
        "CONTEXT INTEGRATION RULES:\n"
        "1. Interests & Hobbies: Prioritize creators, thought leaders, and peers within your primary domain and related hobbies.\n"
        "2. Likes & Dislikes: Follow accounts that produce content you genuinely admire. Avoid accounts that spam or focus on disliked themes.\n"
        "3. Network Value: Look for authentic engagement, cultural alignment, and potential for future interaction or collaboration."
    )

    # Context to inject (comma-separated list of: memory, characteristic, personality, habits, interests, likes, dislikes)
    CONTEXT_POST_CREATION: str = "memory,characteristic,personality,habits,interests,likes,dislikes"
    CONTEXT_REPLY_ANALYSIS: str = "memory,characteristic,personality,habits,interests,likes,dislikes"
    CONTEXT_TREND_ANALYSIS: str = "characteristic,personality,interests"
    CONTEXT_LIKE_RETWEET: str = "personality,likes,dislikes"
    CONTEXT_FOLLOW: str = "characteristic,interests,likes,dislikes"

    # API keys for multiple providers
    MISTRAL_API_KEY: str = "placeholder_mistral"
    GEMINI_API_KEY: str = "placeholder_gemini"
    DEEPSEEK_API_KEY: str = "placeholder_deepseek"
    OPENROUTER_API_KEY: str = "placeholder_openrouter"
    NVIDIA_API_KEY: str | None = None
    NVIDIA_BASE_URL: str = "https://ai.api.nvidia.com/v1/genai"
    NVIDIA_DEFAULT_IMAGE_MODEL: str = "flux.1-dev"

    # ChatGPT Web Bridge & Image Generation
    CHATGPT_BRIDGE_ENABLED: bool = True
    CHATGPT_BRIDGE_HEADLESS: bool = False
    CHATGPT_BRIDGE_STATE_DIR: str = "~/.chatgpt-bridge"
    IMAGE_GENERATION_PROVIDER: str = "chatgpt,nvidia"

    # Secret key must be 32 URL-safe base64-encoded bytes for Fernet
    SECRET_KEY: str = "supersecretfernetkeyforlocaldev12="
    API_PORT: int = 8000
    WEBHOOK_URL: str | None = None

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )


settings = Settings()
