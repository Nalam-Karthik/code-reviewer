
import pytest


class TestRegister:
    """Tests for POST /api/auth/register"""

    def test_register_success(self, client):
        """Valid registration returns 201 with user data."""
        res = client.post("/api/auth/register", json={
            "username": "newuser",
            "email":    "new@example.com",
            "password": "pass123"
        })
        assert res.status_code == 201
        data = res.get_json()
        assert data["user"]["username"] == "newuser"
        # Password must NEVER appear in any API response
        assert "password"      not in data["user"]
        assert "password_hash" not in data["user"]

    def test_register_duplicate_username(self, client):
        """Same username twice returns 400."""
        payload = {"username": "dup", "email": "dup@example.com", "password": "pass"}
        client.post("/api/auth/register", json=payload)
        res = client.post("/api/auth/register", json={
            "username": "dup",
            "email":    "different@example.com",
            "password": "pass"
        })
        assert res.status_code == 400
        assert "Username" in res.get_json()["error"]

    def test_register_duplicate_email(self, client):
        """Same email twice returns 400."""
        client.post("/api/auth/register", json={
            "username": "user1", "email": "same@example.com", "password": "pass"
        })
        res = client.post("/api/auth/register", json={
            "username": "user2", "email": "same@example.com", "password": "pass"
        })
        assert res.status_code == 400

    def test_register_missing_fields(self, client):
        """Missing required field returns 400."""
        res = client.post("/api/auth/register", json={
            "username": "incomplete"
            # missing email and password
        })
        assert res.status_code == 400


class TestLogin:
    """Tests for POST /api/auth/login"""

    def test_login_success(self, client, registered_user):
        """Valid credentials return access and refresh tokens."""
        res = client.post("/api/auth/login", json={
            "username": "karthik",
            "password": "securepass123"
        })
        assert res.status_code == 200
        data = res.get_json()
        assert "access_token"  in data
        assert "refresh_token" in data
        assert data["user"]["username"] == "karthik"

    def test_login_wrong_password(self, client, registered_user):
        """Wrong password returns 401."""
        res = client.post("/api/auth/login", json={
            "username": "karthik",
            "password": "wrongpassword"
        })
        assert res.status_code == 401

    def test_login_nonexistent_user(self, client):
        """Login for user that doesn't exist returns 401."""
        res = client.post("/api/auth/login", json={
            "username": "ghost",
            "password": "anything"
        })
        assert res.status_code == 401

    def test_token_refresh(self, client, registered_user):
        """Refresh token returns new access token."""
        login_res     = client.post("/api/auth/login", json={
            "username": "karthik", "password": "securepass123"
        })
        refresh_token = login_res.get_json()["refresh_token"]

        res = client.post("/api/auth/refresh", headers={
            "Authorization": f"Bearer {refresh_token}"
        })
        assert res.status_code == 200
        assert "access_token" in res.get_json()