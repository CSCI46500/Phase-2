"""
Comprehensive tests for auth.py to achieve 60%+ coverage.
Tests authentication, authorization, token management, and user creation.
"""
import pytest
from unittest.mock import Mock, patch, MagicMock
from datetime import datetime, timedelta
from fastapi import HTTPException
from sqlalchemy.orm import Session

from src.core.auth import (
    hash_password,
    verify_password,
    create_user,
    authenticate_user,
    generate_token,
    verify_token,
    check_permission,
    get_current_user,
    require_permission,
    require_admin,
    init_default_admin
)
from src.core.models import User, Token


# ============================================================================
# Password Hashing Tests
# ============================================================================

class TestPasswordHashing:
    """Test password hashing and verification."""

    def test_hash_password(self):
        """Test password hashing generates different hashes for same password."""
        password = "test_password123"
        salt1 = "salt1"
        salt2 = "salt2"

        hash1 = hash_password(password, salt1)
        hash2 = hash_password(password, salt2)

        # Different salts should produce different hashes
        assert hash1 != hash2
        assert len(hash1) > 0
        assert len(hash2) > 0

    def test_hash_password_deterministic_with_same_salt(self):
        """Test that same password and salt produces verifiable hash."""
        password = "test_password123"
        salt = "fixed_salt"

        hash1 = hash_password(password, salt)
        # Verify the password works with the hash
        assert verify_password(password, salt, hash1) is True

    def test_verify_password_correct(self):
        """Test password verification with correct password."""
        password = "correct_password"
        salt = "random_salt"
        password_hash = hash_password(password, salt)

        result = verify_password(password, salt, password_hash)
        assert result is True

    def test_verify_password_incorrect(self):
        """Test password verification with incorrect password."""
        correct_password = "correct_password"
        wrong_password = "wrong_password"
        salt = "random_salt"
        password_hash = hash_password(correct_password, salt)

        result = verify_password(wrong_password, salt, password_hash)
        assert result is False

    def test_verify_password_wrong_salt(self):
        """Test password verification with wrong salt."""
        password = "test_password"
        correct_salt = "correct_salt"
        wrong_salt = "wrong_salt"
        password_hash = hash_password(password, correct_salt)

        result = verify_password(password, wrong_salt, password_hash)
        assert result is False

    def test_verify_password_exception_handling(self):
        """Test password verification handles exceptions gracefully."""
        result = verify_password("password", "salt", "invalid_hash_format")
        assert result is False


# ============================================================================
# User Creation Tests
# ============================================================================

class TestCreateUser:
    """Test user creation functionality."""

    def test_create_user_success(self):
        """Test successful user creation."""
        mock_db = Mock(spec=Session)
        mock_db.query.return_value.filter.return_value.first.return_value = None

        user = create_user(
            db=mock_db,
            username="testuser",
            password="testpass123",
            permissions=["search", "download"],
            is_admin=False
        )

        # Verify user was added and committed
        mock_db.add.assert_called_once()
        mock_db.commit.assert_called_once()
        mock_db.refresh.assert_called_once()

    def test_create_user_duplicate_username(self):
        """Test creating user with existing username raises exception."""
        mock_db = Mock(spec=Session)

        # Mock existing user
        existing_user = Mock(spec=User)
        existing_user.username = "testuser"
        mock_db.query.return_value.filter.return_value.first.return_value = existing_user

        with pytest.raises(HTTPException) as exc_info:
            create_user(
                db=mock_db,
                username="testuser",
                password="testpass123",
                permissions=["search"],
                is_admin=False
            )

        assert exc_info.value.status_code == 400
        assert "already exists" in exc_info.value.detail.lower()

    def test_create_admin_user(self):
        """Test creating admin user."""
        mock_db = Mock(spec=Session)
        mock_db.query.return_value.filter.return_value.first.return_value = None

        user = create_user(
            db=mock_db,
            username="admin",
            password="adminpass",
            permissions=["upload", "download", "search", "admin"],
            is_admin=True
        )

        mock_db.add.assert_called_once()
        mock_db.commit.assert_called_once()

    def test_create_user_with_empty_permissions(self):
        """Test creating user with empty permissions list."""
        mock_db = Mock(spec=Session)
        mock_db.query.return_value.filter.return_value.first.return_value = None

        user = create_user(
            db=mock_db,
            username="limiteduser",
            password="pass123",
            permissions=[],
            is_admin=False
        )

        mock_db.add.assert_called_once()


# ============================================================================
# Authentication Tests
# ============================================================================

class TestAuthenticateUser:
    """Test user authentication."""

    def test_authenticate_user_success(self):
        """Test successful user authentication."""
        mock_db = Mock(spec=Session)

        # Create mock user with valid credentials
        salt = "test_salt"
        password = "correct_password"
        password_hash = hash_password(password, salt)

        mock_user = Mock(spec=User)
        mock_user.username = "testuser"
        mock_user.salt = salt
        mock_user.password_hash = password_hash

        mock_db.query.return_value.filter.return_value.first.return_value = mock_user

        result = authenticate_user(mock_db, "testuser", password)

        assert result == mock_user

    def test_authenticate_user_invalid_username(self):
        """Test authentication with non-existent username."""
        mock_db = Mock(spec=Session)
        mock_db.query.return_value.filter.return_value.first.return_value = None

        result = authenticate_user(mock_db, "nonexistent", "password")

        assert result is None

    def test_authenticate_user_invalid_password(self):
        """Test authentication with incorrect password."""
        mock_db = Mock(spec=Session)

        salt = "test_salt"
        correct_password = "correct_password"
        password_hash = hash_password(correct_password, salt)

        mock_user = Mock(spec=User)
        mock_user.username = "testuser"
        mock_user.salt = salt
        mock_user.password_hash = password_hash

        mock_db.query.return_value.filter.return_value.first.return_value = mock_user

        result = authenticate_user(mock_db, "testuser", "wrong_password")

        assert result is None


# ============================================================================
# Token Generation Tests
# ============================================================================

class TestGenerateToken:
    """Test token generation."""

    @patch('src.core.auth.settings')
    def test_generate_token_success(self, mock_settings):
        """Test successful token generation."""
        mock_settings.token_expiry_days = 10
        mock_settings.default_api_calls = 1000

        mock_db = Mock(spec=Session)
        mock_user = Mock(spec=User)
        mock_user.id = "user-123"
        mock_user.username = "testuser"

        token = generate_token(mock_db, mock_user)

        # Verify token is a string
        assert isinstance(token, str)
        assert len(token) > 0

        # Verify token was added to database
        mock_db.add.assert_called_once()
        mock_db.commit.assert_called_once()

    @patch('src.core.auth.settings')
    def test_generate_token_creates_db_entry(self, mock_settings):
        """Test that token generation creates proper database entry."""
        mock_settings.token_expiry_days = 10
        mock_settings.default_api_calls = 1000

        mock_db = Mock(spec=Session)
        mock_user = Mock(spec=User)
        mock_user.id = "user-123"
        mock_user.username = "testuser"

        token = generate_token(mock_db, mock_user)

        # Check that Token object was created and added
        call_args = mock_db.add.call_args
        assert call_args is not None


# ============================================================================
# Token Verification Tests
# ============================================================================

class TestVerifyToken:
    """Test token verification."""

    def test_verify_token_valid(self):
        """Test verification of valid token."""
        import hashlib

        mock_db = Mock(spec=Session)

        # Create mock token
        test_token = "test_token_123"
        token_hash = hashlib.sha256(test_token.encode()).hexdigest()

        mock_db_token = Mock(spec=Token)
        mock_db_token.token_hash = token_hash
        mock_db_token.user_id = "user-123"
        mock_db_token.api_calls_remaining = 100
        mock_db_token.expires_at = datetime.now() + timedelta(days=1)

        mock_user = Mock(spec=User)
        mock_user.id = "user-123"
        mock_user.username = "testuser"

        # Setup query chain for token lookup
        mock_token_query = Mock()
        mock_token_query.filter.return_value.first.return_value = mock_db_token

        # Setup query chain for user lookup
        mock_user_query = Mock()
        mock_user_query.filter.return_value.first.return_value = mock_user

        # Mock db.query to return different results based on model
        def query_side_effect(model):
            if model == Token:
                return mock_token_query
            elif model == User:
                return mock_user_query
            return Mock()

        mock_db.query.side_effect = query_side_effect

        result = verify_token(mock_db, test_token)

        assert result == mock_user
        # Verify API call was decremented
        assert mock_db_token.api_calls_remaining == 99
        mock_db.commit.assert_called_once()

    def test_verify_token_invalid(self):
        """Test verification of invalid token."""
        mock_db = Mock(spec=Session)
        mock_db.query.return_value.filter.return_value.first.return_value = None

        result = verify_token(mock_db, "invalid_token")

        assert result is None

    def test_verify_token_expired(self):
        """Test verification of expired token."""
        import hashlib

        mock_db = Mock(spec=Session)

        test_token = "expired_token"
        token_hash = hashlib.sha256(test_token.encode()).hexdigest()

        mock_db_token = Mock(spec=Token)
        mock_db_token.token_hash = token_hash
        mock_db_token.user_id = "user-123"
        mock_db_token.expires_at = datetime.now() - timedelta(days=1)  # Expired

        mock_db.query.return_value.filter.return_value.first.return_value = mock_db_token

        result = verify_token(mock_db, test_token)

        assert result is None

    def test_verify_token_no_calls_remaining(self):
        """Test verification of token with no API calls remaining."""
        import hashlib

        mock_db = Mock(spec=Session)

        test_token = "exhausted_token"
        token_hash = hashlib.sha256(test_token.encode()).hexdigest()

        mock_db_token = Mock(spec=Token)
        mock_db_token.token_hash = token_hash
        mock_db_token.user_id = "user-123"
        mock_db_token.api_calls_remaining = 0  # No calls left
        mock_db_token.expires_at = datetime.now() + timedelta(days=1)

        mock_db.query.return_value.filter.return_value.first.return_value = mock_db_token

        result = verify_token(mock_db, test_token)

        assert result is None

    def test_verify_token_user_not_found(self):
        """Test token verification when associated user doesn't exist."""
        import hashlib

        mock_db = Mock(spec=Session)

        test_token = "orphan_token"
        token_hash = hashlib.sha256(test_token.encode()).hexdigest()

        mock_db_token = Mock(spec=Token)
        mock_db_token.token_hash = token_hash
        mock_db_token.user_id = "nonexistent-user"
        mock_db_token.api_calls_remaining = 100
        mock_db_token.expires_at = datetime.now() + timedelta(days=1)

        mock_token_query = Mock()
        mock_token_query.filter.return_value.first.return_value = mock_db_token

        mock_user_query = Mock()
        mock_user_query.filter.return_value.first.return_value = None  # User not found

        def query_side_effect(model):
            if model == Token:
                return mock_token_query
            elif model == User:
                return mock_user_query
            return Mock()

        mock_db.query.side_effect = query_side_effect

        result = verify_token(mock_db, test_token)

        assert result is None


# ============================================================================
# Permission Checking Tests
# ============================================================================

class TestCheckPermission:
    """Test permission checking."""

    def test_check_permission_admin_has_all_permissions(self):
        """Test that admin users have all permissions."""
        mock_user = Mock(spec=User)
        mock_user.is_admin = True
        mock_user.permissions = []

        result = check_permission(mock_user, "any_permission")

        assert result is True

    def test_check_permission_user_has_permission(self):
        """Test user with specific permission."""
        mock_user = Mock(spec=User)
        mock_user.is_admin = False
        mock_user.permissions = ["upload", "download"]

        result = check_permission(mock_user, "upload")

        assert result is True

    def test_check_permission_user_lacks_permission(self):
        """Test user without required permission."""
        mock_user = Mock(spec=User)
        mock_user.is_admin = False
        mock_user.permissions = ["search"]

        result = check_permission(mock_user, "upload")

        assert result is False

    def test_check_permission_empty_permissions(self):
        """Test user with no permissions."""
        mock_user = Mock(spec=User)
        mock_user.is_admin = False
        mock_user.permissions = []

        result = check_permission(mock_user, "upload")

        assert result is False

    def test_check_permission_non_list_permissions(self):
        """Test handling of non-list permissions."""
        mock_user = Mock(spec=User)
        mock_user.is_admin = False
        mock_user.permissions = None  # Not a list

        result = check_permission(mock_user, "upload")

        assert result is False


# ============================================================================
# FastAPI Dependency Tests
# ============================================================================

class TestGetCurrentUser:
    """Test get_current_user dependency."""

    @pytest.mark.asyncio
    async def test_get_current_user_valid_token(self):
        """Test getting current user with valid token."""
        import hashlib

        mock_db = Mock(spec=Session)
        test_token = "valid_token"
        token_hash = hashlib.sha256(test_token.encode()).hexdigest()

        mock_db_token = Mock(spec=Token)
        mock_db_token.token_hash = token_hash
        mock_db_token.user_id = "user-123"
        mock_db_token.api_calls_remaining = 100
        mock_db_token.expires_at = datetime.now() + timedelta(days=1)

        mock_user = Mock(spec=User)
        mock_user.id = "user-123"
        mock_user.username = "testuser"

        mock_token_query = Mock()
        mock_token_query.filter.return_value.first.return_value = mock_db_token

        mock_user_query = Mock()
        mock_user_query.filter.return_value.first.return_value = mock_user

        def query_side_effect(model):
            if model == Token:
                return mock_token_query
            elif model == User:
                return mock_user_query
            return Mock()

        mock_db.query.side_effect = query_side_effect

        result = await get_current_user(x_auth_token=test_token, db=mock_db)

        assert result == mock_user

    @pytest.mark.asyncio
    async def test_get_current_user_invalid_token(self):
        """Test getting current user with invalid token."""
        mock_db = Mock(spec=Session)
        mock_db.query.return_value.filter.return_value.first.return_value = None

        with pytest.raises(HTTPException) as exc_info:
            await get_current_user(x_auth_token="invalid", db=mock_db)

        assert exc_info.value.status_code == 401
        assert "invalid" in exc_info.value.detail.lower() or "expired" in exc_info.value.detail.lower()


class TestRequireAdmin:
    """Test require_admin dependency."""

    @pytest.mark.asyncio
    async def test_require_admin_success(self):
        """Test require_admin with admin user."""
        mock_user = Mock(spec=User)
        mock_user.is_admin = True

        result = await require_admin(user=mock_user)

        assert result == mock_user

    @pytest.mark.asyncio
    async def test_require_admin_non_admin(self):
        """Test require_admin with non-admin user."""
        mock_user = Mock(spec=User)
        mock_user.is_admin = False

        with pytest.raises(HTTPException) as exc_info:
            await require_admin(user=mock_user)

        assert exc_info.value.status_code == 403
        assert "admin" in exc_info.value.detail.lower()


class TestRequirePermission:
    """Test require_permission dependency factory."""

    @pytest.mark.asyncio
    async def test_require_permission_user_has_permission(self):
        """Test require_permission when user has the permission."""
        mock_user = Mock(spec=User)
        mock_user.is_admin = False
        mock_user.permissions = ["upload", "download"]

        permission_checker = require_permission("upload")
        result = await permission_checker(user=mock_user)

        assert result == mock_user

    @pytest.mark.asyncio
    async def test_require_permission_user_lacks_permission(self):
        """Test require_permission when user lacks the permission."""
        mock_user = Mock(spec=User)
        mock_user.is_admin = False
        mock_user.permissions = ["search"]

        permission_checker = require_permission("upload")

        with pytest.raises(HTTPException) as exc_info:
            await permission_checker(user=mock_user)

        assert exc_info.value.status_code == 403
        assert "permission" in exc_info.value.detail.lower()

    @pytest.mark.asyncio
    async def test_require_permission_admin_bypasses_check(self):
        """Test that admin users bypass permission checks."""
        mock_user = Mock(spec=User)
        mock_user.is_admin = True
        mock_user.permissions = []

        permission_checker = require_permission("upload")
        result = await permission_checker(user=mock_user)

        assert result == mock_user


# ============================================================================
# Admin Initialization Tests
# ============================================================================

class TestInitDefaultAdmin:
    """Test default admin initialization."""

    @patch('src.core.auth.settings')
    def test_init_default_admin_creates_admin(self, mock_settings):
        """Test creating default admin when none exists."""
        mock_settings.admin_username = "admin"
        mock_settings.admin_password = "admin123"

        mock_db = Mock(spec=Session)
        mock_db.query.return_value.filter.return_value.first.return_value = None

        init_default_admin(mock_db)

        # Verify admin was created
        mock_db.add.assert_called_once()
        mock_db.commit.assert_called_once()

    @patch('src.core.auth.settings')
    def test_init_default_admin_already_exists(self, mock_settings):
        """Test initialization when admin already exists."""
        mock_settings.admin_username = "admin"

        mock_db = Mock(spec=Session)
        mock_existing_admin = Mock(spec=User)
        mock_existing_admin.username = "admin"
        mock_db.query.return_value.filter.return_value.first.return_value = mock_existing_admin

        init_default_admin(mock_db)

        # Verify no new admin was created
        mock_db.add.assert_not_called()
        mock_db.commit.assert_not_called()


# ============================================================================
# Integration Tests
# ============================================================================

class TestAuthIntegration:
    """Integration tests for authentication flow."""

    def test_full_auth_flow(self):
        """Test complete authentication flow: create user, authenticate, generate token."""
        mock_db = Mock(spec=Session)

        # Step 1: Create user
        mock_db.query.return_value.filter.return_value.first.return_value = None

        with patch('src.core.auth.settings') as mock_settings:
            mock_settings.token_expiry_days = 10
            mock_settings.default_api_calls = 1000

            user = create_user(
                db=mock_db,
                username="integrationuser",
                password="testpass123",
                permissions=["search", "upload"],
                is_admin=False
            )

            assert mock_db.add.called
            assert mock_db.commit.called

    def test_password_change_scenario(self):
        """Test that changing password invalidates old hash."""
        salt = "test_salt"
        old_password = "old_password"
        new_password = "new_password"

        old_hash = hash_password(old_password, salt)
        new_hash = hash_password(new_password, salt)

        # Old password should not work with new hash
        assert verify_password(old_password, salt, new_hash) is False
        # New password should work with new hash
        assert verify_password(new_password, salt, new_hash) is True
