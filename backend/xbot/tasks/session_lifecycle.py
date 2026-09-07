async def setup_session_record(db, profile_id):
    from sqlalchemy import select
    from xbot.models.profile import Profile, ProfileStatus
    from xbot.models.session import Session, SessionStatus
    import datetime
    from .common import broadcast_session_log
    
    stmt = select(Profile).where(Profile.id == profile_id)
    res = await db.execute(stmt)
    profile = res.scalar_one_or_none()
    if not profile:
        return None, {"status": "failed", "error": "Profile not found."}

    if profile.status in (ProfileStatus.PAUSED, ProfileStatus.LOCKED, ProfileStatus.SUSPENDED):
        return None, {"status": "ignored", "reason": f"Profile status is {profile.status}."}

    session = Session(
        profile_id=profile_id,
        status=SessionStatus.RUNNING,
        started_at=datetime.datetime.utcnow(),
    )
    db.add(session)
    await db.commit()
    await db.refresh(session)
    broadcast_session_log(session.id, "session_start", {"profile_slug": profile.profile_slug})
    return profile, session

async def complete_session_record(db, session_obj, error_log=None):
    import datetime
    from xbot.models.session import SessionStatus
    if error_log:
        session_obj.status = SessionStatus.FAILED
        session_obj.error_log = error_log
    else:
        session_obj.status = SessionStatus.COMPLETED
    session_obj.ended_at = datetime.datetime.utcnow()
    await db.commit()
