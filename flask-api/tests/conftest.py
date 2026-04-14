
import pytest
from app import create_app, db as _db


@pytest.fixture(scope="session")
def app():
    """
    Create a Flask app configured for testing.
    Uses SQLite in-memory so tests run without MySQL.
    scope="session" means one app instance for the whole test run.
    """
    test_app = create_app()
    test_app.config.update({
        "TESTING":                  True,
        "SQLALCHEMY_DATABASE_URI":  "sqlite:///:memory:",
        "JWT_SECRET_KEY":           "test-secret-key",
        "WTF_CSRF_ENABLED":         False,
    })
    return test_app


@pytest.fixture(scope="function")
def db(app):
    """
    Fresh database for every test function.
    Creates all tables before the test, drops them after.
    scope="function" means each test gets a clean slate.
    """
    with app.app_context():
        _db.create_all()
        yield _db
        _db.session.remove()
        _db.drop_all()


@pytest.fixture(scope="function")
def client(app, db):
    """HTTP test client — use this to make requests in tests."""
    return app.test_client()


@pytest.fixture(scope="function")
def auth_headers(client):
    """
    Register + login a test user, return JWT auth headers.
    Use this fixture in any test that needs authentication.

    Usage:
        def test_something(client, auth_headers):
            res = client.get("/api/history/", headers=auth_headers)
    """
    # Register
    client.post("/api/auth/register", json={
        "username": "testuser",
        "email":    "test@example.com",
        "password": "testpass123"
    })

    # Login
    res   = client.post("/api/auth/login", json={
        "username": "testuser",
        "password": "testpass123"
    })
    token = res.get_json()["access_token"]
    return {"Authorization": f"Bearer {token}"}


@pytest.fixture(scope="function")
def registered_user(client):
    """Create and return a test user dict."""
    res = client.post("/api/auth/register", json={
        "username": "karthik",
        "email":    "karthik@example.com",
        "password": "securepass123"
    })
    return res.get_json()["user"]