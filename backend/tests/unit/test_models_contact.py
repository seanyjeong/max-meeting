"""Tests for Contact model."""

from app.models.contact import Contact
from app.models.base import Base


class TestContact:
    """Tests for the Contact model."""

    def test_contact_inherits_base(self):
        """Contact should inherit from Base."""
        assert issubclass(Contact, Base)
