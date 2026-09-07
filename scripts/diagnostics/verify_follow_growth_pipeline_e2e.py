import asyncio
import os
from sqlalchemy import select
from xbot.database import AsyncSessionLocal
from xbot.models.profile import Profile, ProfileStatus
from xbot.models.content import Content
from xbot.models.pipeline import PipelineRun
from xbot.pipelines.central_guard import CentralGuard
from xbot.browser.manager import BrowserManager
from xbot.pipelines.follow_growth_post_pipeline import run_follow_growth_post_for_profile

async def main():
    print("=== STARTING E2E VERIFICATION OF FOLLOW GROWTH POST PIPELINE ===")
    async with AsyncSessionLocal() as db:
        stmt = select(Profile).where(Profile.profile_slug == "test_profile1")
        profile = (await db.execute(stmt)).scalar_one_or_none()
        if not profile:
            print("ERROR: test_profile1 not found!")
            return

        print(f"Testing for profile: {profile.display_name} (@{profile.x_handle})")
        guard = CentralGuard()
        manager = BrowserManager()
        await manager.start()

        try:
            print("\n[Step 1] Executing run_follow_growth_post_for_profile...")
            res = await run_follow_growth_post_for_profile(
                db=db,
                profile=profile,
                guard=guard,
                manager=manager,
            )
            print(f"\n[Result] Pipeline executed with status: {res}")

            # Verify Database
            if res.get("post_id"):
                import uuid
                c_stmt = select(Content).where(Content.id == uuid.UUID(str(res["post_id"])))
                content = (await db.execute(c_stmt)).scalar_one_or_none()
                if content:
                    print("\n[Database Check - Content]")
                    print(f"- Content ID: {content.id}")
                    print(f"- Status: {content.status}")
                    print(f"- Tweet Body:\n{content.body}")
                    print(f"- Media: {content.ai_metadata.get('media_urls')}")
                    
                    img_path = content.ai_metadata.get('image_path')
                    if img_path and os.path.exists(img_path):
                        print(f"- Image verified on disk: {img_path} ({os.path.getsize(img_path)} bytes)")
                    else:
                        print(f"- WARNING: Image file not found at {img_path}")

        finally:
            await manager.stop()
            print("\n=== E2E VERIFICATION COMPLETE ===")

if __name__ == "__main__":
    asyncio.run(main())
