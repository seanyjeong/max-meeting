"""Unit tests for contacts router."""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from datetime import datetime, timezone


class TestContactsRouter:
    """Test contacts API endpoints."""

    @pytest.fixture
    def mock_current_user(self):
        """Mock authenticated user."""
        return {"sub": "1", "type": "access"}

    @pytest.fixture
    def mock_db_session(self):
        """Mock database session."""
        return AsyncMock()

    @pytest.fixture
    def sample_contact_data(self):
        """Sample contact data for tests."""
        return {
            "id": 1,
            "name": "John Doe",
            "phone": "010-1234-5678",
            "email": "john@example.com",
            "organization": "ACME Corp",
            "role": "Manager",
            "notes": None,
            "created_at": datetime.now(timezone.utc),
            "updated_at": datetime.now(timezone.utc),
        }

    def test_contact_create_schema_validation(self):
        """Test ContactCreate schema validation."""
        from app.schemas.contact import ContactCreate

        # Valid contact
        contact = ContactCreate(
            name="Test User",
            phone="010-1234-5678",
            email="test@example.com",
            organization="Test Org",
        )
        assert contact.name == "Test User"
        assert contact.phone == "010-1234-5678"
        assert contact.email == "test@example.com"

    def test_contact_create_schema_requires_name(self):
        """Test that name is required."""
        from app.schemas.contact import ContactCreate
        from pydantic import ValidationError

        with pytest.raises(ValidationError) as exc_info:
            ContactCreate(phone="010-1234-5678")

        errors = exc_info.value.errors()
        assert any(e["loc"] == ("name",) for e in errors)

    def test_contact_create_schema_name_length(self):
        """Test name length validation."""
        from app.schemas.contact import ContactCreate
        from pydantic import ValidationError

        # Empty name should fail
        with pytest.raises(ValidationError):
            ContactCreate(name="")

        # Name too long should fail (>100 chars)
        with pytest.raises(ValidationError):
            ContactCreate(name="a" * 101)

    def test_contact_create_schema_email_validation(self):
        """Test email validation."""
        from app.schemas.contact import ContactCreate
        from pydantic import ValidationError

        # Invalid email should fail
        with pytest.raises(ValidationError):
            ContactCreate(name="Test", email="not-an-email")

        # Valid email should pass
        contact = ContactCreate(name="Test", email="valid@example.com")
        assert contact.email == "valid@example.com"

    def test_contact_update_schema_all_optional(self):
        """Test that ContactUpdate has all optional fields."""
        from app.schemas.contact import ContactUpdate

        # Empty update should be valid
        update = ContactUpdate()
        assert update.model_dump(exclude_unset=True) == {}

        # Partial update should be valid
        update = ContactUpdate(name="New Name")
        assert update.name == "New Name"
        assert update.phone is None

    def test_contact_response_schema_from_attributes(self):
        """Test ContactResponse with from_attributes."""
        from app.schemas.contact import ContactResponse

        class MockContact:
            id = 1
            name = "Test User"
            phone = "010-1234-5678"
            email = "test@example.com"
            organization = "Test Org"
            role = "Manager"
            notes = None
            created_at = datetime.now(timezone.utc)
            updated_at = datetime.now(timezone.utc)

        # This tests from_attributes mode
        response = ContactResponse(
            id=MockContact.id,
            name=MockContact.name,
            phone=MockContact.phone,
            email=MockContact.email,
            organization=MockContact.organization,
            position=MockContact.role,
            notes=MockContact.notes,
            created_at=MockContact.created_at,
            updated_at=MockContact.updated_at,
        )

        assert response.id == 1
        assert response.name == "Test User"

    def test_contact_list_response_schema(self):
        """Test ContactListResponse schema."""
        from app.schemas.contact import ContactListResponse, ContactListMeta, ContactResponse

        now = datetime.now(timezone.utc)
        response = ContactListResponse(
            data=[
                ContactResponse(
                    id=1,
                    name="User 1",
                    phone="010-1234-5678",
                    email="user1@example.com",
                    organization=None,
                    position=None,
                    notes=None,
                    created_at=now,
                    updated_at=now,
                ),
            ],
            meta=ContactListMeta(total=100, limit=20, offset=0),
        )

        assert len(response.data) == 1
        assert response.meta.total == 100
        assert response.meta.limit == 20
        assert response.meta.offset == 0


class TestContactService:
    """Test ContactService."""

    @pytest.fixture
    def mock_db(self):
        """Create mock database session."""
        return AsyncMock()

    @pytest.mark.asyncio
    async def test_service_get_list_basic(self, mock_db):
        """Test basic list retrieval."""
        from app.services.contact import ContactService

        # Mock the database response
        mock_contact = MagicMock()
        mock_contact.id = 1
        mock_contact.name = "Test User"
        mock_contact.deleted_at = None

        mock_result = MagicMock()
        mock_result.scalars.return_value.all.return_value = [mock_contact]
        mock_count_result = MagicMock()
        mock_count_result.scalar_one.return_value = 1

        mock_db.execute = AsyncMock(side_effect=[mock_count_result, mock_result])

        service = ContactService(mock_db)
        contacts, total = await service.get_list()

        assert total == 1
        assert len(contacts) == 1
        assert mock_db.execute.call_count == 2

    @pytest.mark.asyncio
    async def test_service_get_by_id(self, mock_db):
        """Test getting contact by ID."""
        from app.services.contact import ContactService

        mock_contact = MagicMock()
        mock_contact.id = 1
        mock_contact.name = "Test User"

        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = mock_contact
        mock_db.execute = AsyncMock(return_value=mock_result)

        service = ContactService(mock_db)
        contact = await service.get_by_id(1)

        assert contact is not None
        assert contact.id == 1

    @pytest.mark.asyncio
    async def test_service_get_by_id_not_found(self, mock_db):
        """Test getting non-existent contact."""
        from app.services.contact import ContactService

        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = None
        mock_db.execute = AsyncMock(return_value=mock_result)

        service = ContactService(mock_db)
        contact = await service.get_by_id(999)

        assert contact is None

    @pytest.mark.asyncio
    async def test_service_create_with_encryption(self, mock_db):
        """Test contact creation with PII encryption."""
        from app.services.contact import ContactService
        from app.schemas.contact import ContactCreate

        data = ContactCreate(
            name="Test User",
            phone="010-1234-5678",
            email="test@example.com",
        )

        # Mock the add, flush, and refresh operations
        mock_db.add = MagicMock()
        mock_db.flush = AsyncMock()
        mock_db.refresh = AsyncMock()

        with patch('app.services.contact.encrypt_pii') as mock_encrypt:
            mock_encrypt.return_value = b'encrypted_data'

            service = ContactService(mock_db)
            contact = await service.create(data)

            # Verify encryption was called for phone and email
            assert mock_encrypt.call_count == 2

    @pytest.mark.asyncio
    async def test_service_soft_delete(self, mock_db):
        """Test soft delete."""
        from app.services.contact import ContactService

        mock_contact = MagicMock()
        mock_contact.soft_delete = MagicMock()

        mock_db.flush = AsyncMock()

        service = ContactService(mock_db)
        await service.delete(mock_contact)

        mock_contact.soft_delete.assert_called_once()
        mock_db.flush.assert_called_once()


class TestEncryptionService:
    """Test encryption service."""

    @pytest.fixture
    def valid_key(self):
        """Generate a valid Fernet key for testing."""
        from cryptography.fernet import Fernet
        return Fernet.generate_key().decode()

    def test_encryption_roundtrip(self, valid_key):
        """Test that encryption and decryption work correctly."""
        from app.services.encryption import EncryptionService

        service = EncryptionService(key=valid_key)
        plaintext = "010-1234-5678"

        encrypted = service.encrypt(plaintext)
        decrypted = service.decrypt(encrypted)

        assert encrypted != plaintext.encode()  # Should be different
        assert decrypted == plaintext  # Should match original

    def test_encryption_empty_string(self, valid_key):
        """Test encryption of empty string."""
        from app.services.encryption import EncryptionService

        service = EncryptionService(key=valid_key)

        encrypted = service.encrypt("")
        decrypted = service.decrypt(encrypted)

        assert encrypted == b""
        assert decrypted == ""

    def test_encryption_unicode(self, valid_key):
        """Test encryption of unicode characters."""
        from app.services.encryption import EncryptionService

        service = EncryptionService(key=valid_key)
        plaintext = "한글 테스트 데이터"

        encrypted = service.encrypt(plaintext)
        decrypted = service.decrypt(encrypted)

        assert decrypted == plaintext

    def test_encryption_invalid_key(self):
        """Test that invalid key raises error."""
        from app.services.encryption import EncryptionService, EncryptionError

        with pytest.raises(EncryptionError):
            EncryptionService(key="invalid-key")

    def test_decryption_invalid_data(self, valid_key):
        """Test that invalid ciphertext raises error."""
        from app.services.encryption import EncryptionService, EncryptionError

        service = EncryptionService(key=valid_key)

        with pytest.raises(EncryptionError):
            service.decrypt(b"invalid_ciphertext")

    def test_encryption_service_missing_key(self):
        """Test that missing key raises error."""
        from app.services.encryption import EncryptionService, EncryptionError

        # Mock get_settings to return empty key
        with patch('app.services.encryption.get_settings') as mock_settings:
            mock_settings.return_value.PII_ENCRYPTION_KEY = ""

            with pytest.raises(EncryptionError) as exc_info:
                EncryptionService()

            assert "PII_ENCRYPTION_KEY is not configured" in str(exc_info.value)

    def test_generate_key(self):
        """Test key generation."""
        from app.services.encryption import generate_key, EncryptionService

        key = generate_key()

        # Key should be valid for Fernet
        assert isinstance(key, str)
        assert len(key) == 44  # Base64-encoded 32 bytes

        # Should be usable
        service = EncryptionService(key=key)
        encrypted = service.encrypt("test")
        assert service.decrypt(encrypted) == "test"

    def test_helper_functions(self, valid_key):
        """Test encrypt_pii and decrypt_pii helper functions."""
        from app.services.encryption import encrypt_pii, decrypt_pii, _get_encryption_service

        # Clear cache
        _get_encryption_service.cache_clear()

        with patch('app.services.encryption.get_settings') as mock_settings:
            mock_settings.return_value.PII_ENCRYPTION_KEY = valid_key

            plaintext = "sensitive-data"
            encrypted = encrypt_pii(plaintext)
            decrypted = decrypt_pii(encrypted)

            assert decrypted == plaintext

        # Clear cache after test
        _get_encryption_service.cache_clear()

    def test_helper_functions_empty_values(self, valid_key):
        """Test helper functions with empty values."""
        from app.services.encryption import encrypt_pii, decrypt_pii, _get_encryption_service

        # Clear cache
        _get_encryption_service.cache_clear()

        with patch('app.services.encryption.get_settings') as mock_settings:
            mock_settings.return_value.PII_ENCRYPTION_KEY = valid_key

            assert encrypt_pii("") == b""
            assert encrypt_pii(None) == b""
            assert decrypt_pii(b"") == ""
            assert decrypt_pii(None) == ""

        # Clear cache after test
        _get_encryption_service.cache_clear()


class TestContactToResponseDict:
    """Test contact_to_response_dict function."""

    def test_contact_to_response_dict_with_encrypted_pii(self):
        """Test conversion with encrypted PII."""
        from app.services.contact import contact_to_response_dict
        from datetime import datetime, timezone

        mock_contact = MagicMock()
        mock_contact.id = 1
        mock_contact.name = "Test User"
        mock_contact.phone_encrypted = b"encrypted_phone"
        mock_contact.email_encrypted = b"encrypted_email"
        mock_contact.organization = "Test Org"
        mock_contact.role = "Manager"
        mock_contact.created_at = datetime.now(timezone.utc)
        mock_contact.updated_at = datetime.now(timezone.utc)

        with patch('app.services.contact.decrypt_pii') as mock_decrypt:
            mock_decrypt.side_effect = ["010-1234-5678", "test@example.com"]

            result = contact_to_response_dict(mock_contact)

            assert result["id"] == 1
            assert result["name"] == "Test User"
            assert result["phone"] == "010-1234-5678"
            assert result["email"] == "test@example.com"
            assert mock_decrypt.call_count == 2

    def test_contact_to_response_dict_without_pii(self):
        """Test conversion without encrypted PII."""
        from app.services.contact import contact_to_response_dict
        from datetime import datetime, timezone

        mock_contact = MagicMock()
        mock_contact.id = 1
        mock_contact.name = "Test User"
        mock_contact.phone_encrypted = None
        mock_contact.email_encrypted = None
        mock_contact.organization = None
        mock_contact.role = None
        mock_contact.created_at = datetime.now(timezone.utc)
        mock_contact.updated_at = datetime.now(timezone.utc)

        result = contact_to_response_dict(mock_contact)

        assert result["id"] == 1
        assert result["name"] == "Test User"
        assert result["phone"] is None
        assert result["email"] is None
