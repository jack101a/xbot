import asyncio
import os
import uuid
import sys
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

# Ensure backend is in python path
sys.path.append(os.path.join(os.path.dirname(__file__), "..", "backend"))

from xbot.database import engine, AsyncSessionLocal
from xbot.models.base import Base
from xbot.models.profile import Profile, ProfileStatus
from xbot.ai.generator import ContentGenerator

async def run_e2e_test():
    print("🚀 Starting E2E Test...")
    
    # Ensure tables exist
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
        
    async with AsyncSessionLocal() as db:
        # Create a test profile if it doesn't exist
        stmt = select(Profile).where(Profile.profile_slug == "test_e2e_bot")
        res = await db.execute(stmt)
        profile = res.scalar_one_or_none()
        
        if not profile:
            profile = Profile(
                profile_slug="test_e2e_bot",
                x_handle="@test_e2e",
                display_name="E2E Test Bot",
                status=ProfileStatus.ACTIVE
            )
            db.add(profile)
            await db.commit()
            await db.refresh(profile)
            print(f"✅ Created test profile: {profile.id}")
        else:
            print(f"✅ Found test profile: {profile.id}")
            
        # Ensure the test persona config exists
        os.makedirs(f"../data/profiles/test_e2e_bot", exist_ok=True)
        with open(f"../data/profiles/test_e2e_bot/persona.yaml", "w") as f:
            f.write("""
id: "test-bot-01"
display_name: "E2E Tester"
x_handle: "@test_e2e"
identity:
  background: "An automated testing agent built to verify AI pipelines."
personality:
  traits: ["Analytical", "Hype"]
  values: ["Code Quality", "Speed"]
  communication_style: "Direct and technical."
interests:
  primary: ["Software", "AI"]
  secondary: ["Testing"]
  will_not_discuss: ["Politics"]
writing_style:
  tone: "Concise"
  typical_length: "Short"
  formatting: []
  examples: []
goals:
  short_term: ["Run tests perfectly"]
  long_term: ["Automate everything"]
  content_pillars: ["DevOps", "AI"]
rules:
  always: ["End with a rocket emoji"]
  never: ["Apologize"]
""")
        print("✅ Created test persona config.")
            
        print("🤖 Triggering AI Ghostwriter endpoint via ContentGenerator directly...")
        
        generator = ContentGenerator()
        
        try:
            # We must set LITELLM API keys if not present. Let's use a mock or fake if needed,
            # or rely on the system's local liteLLM proxy if it's running.
            # Assuming LiteLLM uses some mock model or groq/openai with available keys.
            # We'll use a fast mock model just for test if no keys are provided.
            os.environ["LITELLM_PRIMARY_MODEL"] = "gemini/gemini-2.5-flash"
            
            result = await generator.generate_content(
                db=db,
                profile_slug=profile.profile_slug,
                context_prompt="Write a 1-sentence test tweet about AI automation."
            )
            
            print("\\n🎉 GENERATION SUCCESS:")
            print(f"Primary Text: {result.primary_text}")
            print(f"Alternatives: {result.alternatives}")
            print(f"Hashtags: {result.suggested_hashtags}")
            
        except Exception as e:
            print(f"❌ AI Generation Failed: {e}")
            import traceback
            traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(run_e2e_test())
