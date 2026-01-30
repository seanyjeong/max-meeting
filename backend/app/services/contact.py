"""Contact service with CRUD operations and PII encryption."""

from typing import Optional

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import Contact
from app.schemas.contact import ContactCreate, ContactUpdate
from app.services.encryption import encrypt_pii, decrypt_pii


def escape_like(value: str) -> str:
    """Escape special characters for LIKE pattern to prevent SQL injection.

    Args:
        value: The search string to escape.

    Returns:
        Escaped string safe for use in LIKE patterns.
    """
    return value.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")


class ContactService:
    """Service for managing contacts with PII encryption."""

    def __init__(self, db: AsyncSession):
        """Initialize the contact service.

        Args:
            db: Async database session.
        """
        self.db = db

    async def get_list(
        self,
        q: Optional[str] = None,
        limit: int = 20,
        offset: int = 0,
    ) -> tuple[list[Contact], int]:
        """
        Get paginated list of contacts with optional search.

        Args:
            q: Search query (searches by name using pg_trgm).
            limit: Maximum number of contacts to return.
            offset: Number of contacts to skip.

        Returns:
            Tuple of (list of contacts, total count).
        """
        # Build base query with soft-delete filter
        base_query = select(Contact).where(Contact.deleted_at.is_(None))

        # Add search filter if query provided
        if q:
            # Use pg_trgm similarity search with escaped LIKE pattern
            # The index idx_contacts_name_trgm enables efficient trigram search
            escaped_q = escape_like(q)
            search_filter = Contact.name.ilike(f"%{escaped_q}%", escape="\\")
            base_query = base_query.where(search_filter)

        # Get total count
        count_query = select(func.count()).select_from(base_query.subquery())
        total_result = await self.db.execute(count_query)
        total = total_result.scalar_one()

        # Get paginated results
        query = (
            base_query
            .order_by(Contact.name.asc())
            .limit(limit)
            .offset(offset)
        )
        result = await self.db.execute(query)
        contacts = list(result.scalars().all())

        return contacts, total

    async def get_by_id(self, contact_id: int) -> Optional[Contact]:
        """
        Get a single contact by ID.

        Args:
            contact_id: The contact's ID.

        Returns:
            The contact if found and not deleted, None otherwise.
        """
        query = (
            select(Contact)
            .where(Contact.id == contact_id)
            .where(Contact.deleted_at.is_(None))
        )
        result = await self.db.execute(query)
        return result.scalar_one_or_none()

    async def create(self, data: ContactCreate) -> Contact:
        """
        Create a new contact with encrypted PII.

        Args:
            data: The contact data.

        Returns:
            The created contact.
        """
        # Encrypt PII fields
        phone_encrypted = encrypt_pii(data.phone) if data.phone else None
        email_encrypted = encrypt_pii(data.email) if data.email else None

        contact = Contact(
            name=data.name,
            position=data.role,
            organization=data.organization,
            phone_encrypted=phone_encrypted,
            email_encrypted=email_encrypted,
            notes=data.notes,
        )

        self.db.add(contact)
        await self.db.flush()
        await self.db.refresh(contact)

        return contact

    async def update(
        self,
        contact: Contact,
        data: ContactUpdate,
    ) -> Contact:
        """
        Update an existing contact.

        Args:
            contact: The contact to update.
            data: The update data (only provided fields are updated).

        Returns:
            The updated contact.
        """
        update_data = data.model_dump(exclude_unset=True)

        # Handle PII encryption for phone and email
        if "phone" in update_data:
            phone = update_data.pop("phone")
            contact.phone_encrypted = encrypt_pii(phone) if phone else None

        if "email" in update_data:
            email = update_data.pop("email")
            contact.email_encrypted = encrypt_pii(email) if email else None

        # Map role -> position for DB field
        if "role" in update_data:
            role_value = update_data.pop("role")
            contact.position = role_value

        # Update remaining fields
        for field, value in update_data.items():
            if hasattr(contact, field):
                setattr(contact, field, value)

        await self.db.flush()
        await self.db.refresh(contact)

        return contact

    async def delete(self, contact: Contact) -> None:
        """
        Soft delete a contact.

        Args:
            contact: The contact to delete.
        """
        contact.soft_delete()
        await self.db.flush()


def contact_to_response_dict(contact: Contact) -> dict:
    """
    Convert a Contact model to a response dictionary with decrypted PII.

    Args:
        contact: The contact model instance.

    Returns:
        Dictionary with decrypted phone and email fields.
    """
    return {
        "id": contact.id,
        "name": contact.name,
        "phone": decrypt_pii(contact.phone_encrypted) if contact.phone_encrypted else None,
        "email": decrypt_pii(contact.email_encrypted) if contact.email_encrypted else None,
        "organization": contact.organization,
        "role": contact.position,  # DB column is 'position', API returns 'role'
        "notes": contact.notes,
        "created_at": contact.created_at,
        "updated_at": contact.updated_at,
    }
