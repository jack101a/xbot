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
    POST = "original"
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
    DELETED = "deleted"


from sqlalchemy.types import TypeDecorator


class SafeContentType(TypeDecorator):
    impl = String
    cache_ok = True

    def process_bind_param(self, value: Any, dialect: Any) -> str | None:
        if value is None:
            return None
        if isinstance(value, ContentType):
            return value.value
        return str(value).lower()

    def process_result_value(self, value: Any, dialect: Any) -> ContentType | None:
        if value is None:
            return None
        val_str = str(value).lower()
        for member in ContentType:
            if member.value == val_str:
                return member
        return ContentType.ORIGINAL


class SafeContentStatus(TypeDecorator):
    impl = String
    cache_ok = True

    def process_bind_param(self, value: Any, dialect: Any) -> str | None:
        if value is None:
            return None
        if isinstance(value, ContentStatus):
            return value.value
        return str(value).lower()

    def process_result_value(self, value: Any, dialect: Any) -> ContentStatus | None:
        if value is None:
            return None
        val_str = str(value).lower()
        for member in ContentStatus:
            if member.value == val_str:
                return member
        return ContentStatus.DRAFT


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
        SafeContentType, default=ContentType.ORIGINAL, index=True
    )
    body: Mapped[str] = mapped_column(Text)
    status: Mapped[ContentStatus] = mapped_column(
        SafeContentStatus, default=ContentStatus.DRAFT, index=True
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
    thread_items: Mapped[list["ThreadItem"]] = relationship(
        "ThreadItem",
        back_populates="content",
        cascade="all, delete-orphan",
        order_by="ThreadItem.position",
        lazy="selectin",
    )


class ThreadItem(Base):
    __tablename__ = "thread_items"

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    content_id: Mapped[uuid.UUID] = mapped_column(
        Uuid, ForeignKey("content.id", ondelete="CASCADE"), index=True
    )
    position: Mapped[int] = mapped_column(default=0, index=True)  # 0, 1, 2, ...
    item_type: Mapped[str] = mapped_column(String(30), default="body")  # "hook", "body", "closer"
    text: Mapped[str] = mapped_column(Text)
    media_url: Mapped[str | None] = mapped_column(String(500), nullable=True)
    tweet_id: Mapped[str | None] = mapped_column(String(100), nullable=True)
    performance: Mapped[dict[str, Any] | None] = mapped_column(JSON, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    # Relationships
    content: Mapped["Content"] = relationship("Content", back_populates="thread_items")

