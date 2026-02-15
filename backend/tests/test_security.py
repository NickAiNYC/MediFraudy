"""Tests for RBAC and security modules."""

import pytest
from core.rbac import Role, PERMISSIONS, has_permission
from core.security import create_access_token, decode_token, ROLE_HIERARCHY


class TestRBAC:
    """Test Role-Based Access Control."""

    def test_partner_has_all_permissions(self):
        """Partner role should have the most permissions."""
        partner_perms = PERMISSIONS[Role.PARTNER]
        assert "read:providers" in partner_perms
        assert "write:cases" in partner_perms
        assert "export:evidence" in partner_perms
        assert "manage:users" in partner_perms

    def test_auditor_is_read_only(self):
        """Auditor role should only have read permissions."""
        auditor_perms = PERMISSIONS[Role.AUDITOR]
        assert "read:providers" in auditor_perms
        assert "read:cases" in auditor_perms
        assert "write:cases" not in auditor_perms
        assert "export:evidence" not in auditor_perms
        assert "manage:users" not in auditor_perms

    def test_role_hierarchy(self):
        """Partner > Associate > Investigator > Auditor."""
        assert ROLE_HIERARCHY["partner"] > ROLE_HIERARCHY["associate"]
        assert ROLE_HIERARCHY["associate"] > ROLE_HIERARCHY["investigator"]
        assert ROLE_HIERARCHY["investigator"] > ROLE_HIERARCHY["auditor"]

    def test_has_permission_valid(self):
        """has_permission should return True for valid role/permission."""
        assert has_permission("partner", "manage:users") is True
        assert has_permission("auditor", "read:providers") is True

    def test_has_permission_invalid(self):
        """has_permission should return False for unauthorized actions."""
        assert has_permission("auditor", "manage:users") is False
        assert has_permission("investigator", "write:cases") is False

    def test_has_permission_unknown_role(self):
        """Unknown roles should have no permissions."""
        assert has_permission("hacker", "read:providers") is False


class TestJWT:
    """Test JWT token creation and decoding."""

    def test_create_and_decode_token(self):
        """Should create a valid JWT that decodes correctly."""
        token = create_access_token({"sub": "testuser", "role": "partner"})
        decoded = decode_token(token)
        assert decoded.sub == "testuser"
        assert decoded.role == "partner"

    def test_decode_invalid_token(self):
        """Should raise HTTPException for invalid tokens."""
        from fastapi import HTTPException
        with pytest.raises(HTTPException):
            decode_token("invalid.token.here")

    def test_token_contains_role(self):
        """Token should encode the user's role."""
        token = create_access_token({"sub": "analyst", "role": "investigator"})
        decoded = decode_token(token)
        assert decoded.role == "investigator"
