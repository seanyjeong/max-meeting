"""Contact model for meeting attendees."""

from typing import TYPE_CHECKING

from sqlalchemy import Index, Integer, LargeBinary, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, SoftDeleteMixin, TimestampMixin

if TYPE_CHECKING:
    from app.models.meeting import MeetingAttendee
    from app.models.result import ActionItem


class Contact(Base, TimestampMixin, SoftDeleteMixin):
    """Contact model for storing attendee information with PII encryption."""

    __tablename__ = "contacts"
    __table_args__ = (
        Index(
            "idx_contacts_name",
            "name",
            postgresql_where="deleted_at IS NULL",
        ),
        Index(
            "idx_contacts_name_trgm",
            "name",
            postgresql_using="gin",
            postgresql_ops={"name": "gin_trgm_ops"},
        ),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    role: Mapped[str | None] = mapped_column(String(50), nullable=True)
    organization: Mapped[str | None] = mapped_column(String(100), nullable=True)
    # PII encrypted columns (using pgcrypto)
    phone_encrypted: Mapped[bytes | None] = mapped_column(LargeBinary, nullable=True)
    email_encrypted: Mapped[bytes | None] = mapped_column(LargeBinary, nullable=True)

    # Relationships
    meeting_attendees: Mapped[list["MeetingAttendee"]] = relationship(
        "MeetingAttendee",
        back_populates="contact",
        lazy="selectin",
    )
    assigned_action_items: Mapped[list["ActionItem"]] = relationship(
        "ActionItem",
        back_populates="assignee",
        lazy="selectin",
    )

    def __repr__(self) -> str:
        return f"<Contact(id={self.id}, name='{self.name}')>"
