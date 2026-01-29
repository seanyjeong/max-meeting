"""Tests for base model classes and mixins."""

from datetime import datetime

from sqlalchemy import DateTime
from sqlalchemy.orm import DeclarativeBase

from app.models.base import Base, TimestampMixin, SoftDeleteMixin


class TestBase:
    """Tests for the Base declarative class."""

    def test_base_is_declarative_base(self):
        """Base should be a valid SQLAlchemy DeclarativeBase."""
        assert issubclass(Base, DeclarativeBase)

    def test_base_has_datetime_type_annotation_map(self):
        """Base should map datetime to DateTime with timezone."""
        assert datetime in Base.type_annotation_map
        mapped_type = Base.type_annotation_map[datetime]
        assert isinstance(mapped_type, DateTime)
        assert mapped_type.timezone is True


class TestTimestampMixin:
    """Tests for the TimestampMixin."""

    def test_timestamp_mixin_has_created_at(self):
        """TimestampMixin should have created_at attribute."""
        assert hasattr(TimestampMixin, "created_at")

    def test_timestamp_mixin_has_updated_at(self):
        """TimestampMixin should have updated_at attribute."""
        assert hasattr(TimestampMixin, "updated_at")


class TestSoftDeleteMixin:
    """Tests for the SoftDeleteMixin."""

    def test_soft_delete_mixin_has_deleted_at(self):
        """SoftDeleteMixin should have deleted_at attribute."""
        assert hasattr(SoftDeleteMixin, "deleted_at")

    def test_soft_delete_mixin_has_is_deleted_property(self):
        """SoftDeleteMixin should have is_deleted property."""
        assert hasattr(SoftDeleteMixin, "is_deleted")
