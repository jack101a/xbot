import uuid
from datetime import datetime
from enum import StrEnum
from typing import TYPE_CHECKING, Any

from sqlalchemy import JSON, DateTime, Enum, ForeignKey, String, Text, Uuid
from sqlalchemy.orm import Mapped, mapped_column, relationship

from xbot.models.base import Base

if TYPE_CHECKING:
    from xbot.models.profile import Profile


class ContentType(StrEnum):
    ORIGINAL = "original"
    TWEET = "original"
    REPLY = "reply"
    QUOTE = "quote"
    THREAD = "thread"
    POLL = "poll"


class ContentStatus(StrEnum):
    DRAFT = "draft"
    APPROVED = "approved"
    POSTED = "posted"
    FAILED = "failed"


class Content(Base):
    __tablename__ = "content"

    def __init__(self, *args: Any, text: str | None = None, **kwargs: Any) -> None:
        if text is not None and "body" not in kwargs:
            kwargs["body"] = text
        super().__init__(*args, **kwargs)

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    profile_id: Mapped[uuid.UUID] = mapped_column(
        Uuid, ForeignKey("profiles.id", ondelete="CASCADE"), index=True
    )
    content_type: Mapped[ContentType] = mapped_column(
        Enum(ContentType), default=ContentType.ORIGINAL, index=True
    )
    body: Mapped[str] = mapped_column(Text)
    status: Mapped[ContentStatus] = mapped_column(
        Enum(ContentStatus), default=ContentStatus.DRAFT, index=True
    )

    @property
    def text(self) -> str:
        return self.body

    @text.setter
    def text(self, value: str) -> None:
        self.body = value
    tweet_id: Mapped[str | None] = mapped_column(String(100), nullable=True, index=True)
    performance: Mapped[dict[str, Any] | None] = mapped_column(JSON, nullable=True)
    ai_metadata: Mapped[dict[str, Any] | None] = mapped_column(JSON, nullable=True)
    posted_at: Mapped[datetime | None] = mapped_column(
        DateTime, nullable=True, index=True
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow, index=True
    )

    # Relationships
    profile: Mapped["Profile"] = relationship("Profile", back_populates="content")
