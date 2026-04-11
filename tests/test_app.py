"""Tests for the education-calculator web application."""
import base64
from unittest.mock import patch

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app import auth as auth_module
from app.database import get_db
from app.main import create_app
from app.models import Base, Child
from app.sanitize import sanitize_name, sanitize_notes


@pytest.fixture(scope="module")
def _db_session_factory():
    """Return an in-memory SQLite session factory shared across tests."""
    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(bind=engine)
    factory = sessionmaker(autocommit=False, autoflush=False, bind=engine)

    db = factory()
    db.add(Child(name="Alice"))
    db.add(Child(name="Child 1"))
    db.commit()
    db.close()

    return factory


@pytest.fixture(scope="module")
def client(_db_session_factory):
    """Return a localhost client with local-dev auth bypass enabled."""
    application = create_app()

    def _override():
        db = _db_session_factory()
        try:
            yield db
        finally:
            db.close()

    application.dependency_overrides[get_db] = _override

    with TestClient(application, base_url="http://localhost") as test_client:
        yield test_client


@pytest.fixture(scope="module")
def readonly_client(_db_session_factory):
    """Return a localhost client for non-editor route checks."""
    application = create_app()

    def _override():
        db = _db_session_factory()
        try:
            yield db
        finally:
            db.close()

    application.dependency_overrides[get_db] = _override

    with TestClient(application, base_url="http://localhost") as test_client:
        yield test_client


@pytest.fixture
def remote_client(_db_session_factory):
    """Return a non-local client so authentication middleware is fully enforced."""
    application = create_app()

    def _override():
        db = _db_session_factory()
        try:
            yield db
        finally:
            db.close()

    application.dependency_overrides[get_db] = _override

    with TestClient(application, base_url="http://example.com") as test_client:
        yield test_client


def _basic_auth(username: str, password: str) -> dict[str, str]:
    token = base64.b64encode(f"{username}:{password}".encode("utf-8")).decode("ascii")
    return {"Authorization": f"Basic {token}"}


class TestSanitizeName:
    def test_valid_name(self):
        assert sanitize_name("Alice") == "Alice"

    def test_allows_hyphen_and_apostrophe(self):
        assert sanitize_name("Mary-Jane") == "Mary-Jane"
        assert sanitize_name("O'Connor") == "O'Connor"

    def test_strips_whitespace(self):
        assert sanitize_name("  Bob  ") == "Bob"

    def test_rejects_empty(self):
        with pytest.raises(ValueError, match="empty"):
            sanitize_name("")

    def test_rejects_whitespace_only(self):
        with pytest.raises(ValueError, match="empty"):
            sanitize_name("   ")

    def test_rejects_script_tag(self):
        with pytest.raises(ValueError, match="invalid characters"):
            sanitize_name("<script>alert(1)</script>")

    def test_rejects_sql_injection(self):
        with pytest.raises(ValueError, match="invalid characters"):
            sanitize_name("'; DROP TABLE children; --")

    def test_length_cap(self):
        with pytest.raises(ValueError, match="characters or fewer"):
            sanitize_name("A" * 51)


class TestSanitizeNotes:
    def test_none_passthrough(self):
        assert sanitize_notes(None) is None

    def test_strips_and_escapes(self):
        result = sanitize_notes('  <script>alert("xss")</script>  ')
        assert "<script>" not in result
        assert "&lt;script&gt;" in result

    def test_ampersand_escaped(self):
        assert "&amp;" in sanitize_notes("A & B")

    def test_truncates(self):
        long_text = "x" * 600
        result = sanitize_notes(long_text, max_length=500)
        assert len(result) == 500

    def test_empty_returns_none(self):
        assert sanitize_notes("   ") is None


class TestBalanceRoutes:
    def test_create_balance(self, client):
        response = client.post(
            "/api/balances/Alice",
            json={"year": 2026, "balance": 15000.0, "notes": "birthday deposit"},
        )
        assert response.status_code == 201
        data = response.json()
        assert data["year"] == 2026
        assert data["balance"] == 15000.0
        assert data["notes"] == "birthday deposit"

    def test_get_balances(self, client):
        response = client.get("/api/balances/Alice")
        assert response.status_code == 200
        items = response.json()
        assert isinstance(items, list)
        assert len(items) >= 1

    def test_get_balances_unknown_child_returns_empty(self, client):
        response = client.get("/api/balances/NobodyHere")
        assert response.status_code == 200
        assert response.json() == []

    def test_update_balance(self, client):
        balances = client.get("/api/balances/Alice").json()
        balance_id = balances[0]["id"]
        response = client.put(f"/api/balances/{balance_id}", json={"balance": 16000.0})
        assert response.status_code == 200
        assert response.json()["balance"] == 16000.0

    def test_delete_balance(self, client):
        create_response = client.post(
            "/api/balances/Alice",
            json={"year": 2025, "balance": 500.0},
        )
        balance_id = create_response.json()["id"]
        response = client.delete(f"/api/balances/{balance_id}")
        assert response.status_code == 204

    def test_duplicate_year_returns_409(self, client):
        response = client.post(
            "/api/balances/Alice",
            json={"year": 2026, "balance": 99999.0},
        )
        assert response.status_code == 409

    def test_xss_in_notes_is_escaped(self, client):
        response = client.post(
            "/api/balances/Alice",
            json={
                "year": 2027,
                "balance": 2000.0,
                "notes": '<img src=x onerror=alert(1)>',
            },
        )
        assert response.status_code == 201
        notes = response.json()["notes"]
        assert "<img" not in notes
        assert "&lt;img" in notes

    def test_update_nonexistent_returns_404(self, client):
        response = client.put("/api/balances/999999", json={"balance": 1.0})
        assert response.status_code == 404

    def test_delete_nonexistent_returns_404(self, client):
        response = client.delete("/api/balances/999999")
        assert response.status_code == 404


class TestSchemaValidation:
    def test_negative_balance_rejected(self, client):
        response = client.post(
            "/api/balances/Alice",
            json={"year": 2080, "balance": -100.0},
        )
        assert response.status_code == 422

    def test_year_below_range_rejected(self, client):
        response = client.post(
            "/api/balances/Alice",
            json={"year": 1999, "balance": 100.0},
        )
        assert response.status_code == 422

    def test_year_above_range_rejected(self, client):
        response = client.post(
            "/api/balances/Alice",
            json={"year": 2101, "balance": 100.0},
        )
        assert response.status_code == 422

    def test_missing_required_fields_rejected(self, client):
        response = client.post("/api/balances/Alice", json={})
        assert response.status_code == 422


class TestAuthEnforcement:
    def test_create_blocked_for_non_editor(self, readonly_client):
        with patch("app.routes.balances.is_editor", return_value=False):
            response = readonly_client.post(
                "/api/balances/Alice",
                json={"year": 2090, "balance": 100.0},
            )
        assert response.status_code == 403

    def test_update_blocked_for_non_editor(self, readonly_client):
        with patch("app.routes.balances.is_editor", return_value=False):
            response = readonly_client.put("/api/balances/1", json={"balance": 1.0})
        assert response.status_code == 403

    def test_delete_blocked_for_non_editor(self, readonly_client):
        with patch("app.routes.balances.is_editor", return_value=False):
            response = readonly_client.delete("/api/balances/1")
        assert response.status_code == 403

    def test_read_allowed_for_non_editor(self, readonly_client):
        with patch("app.routes.balances.is_editor", return_value=False):
            response = readonly_client.get("/api/balances/Alice")
        assert response.status_code == 200


class TestAuthHardening:
    def test_lockout_after_repeated_failed_attempts(self, remote_client, monkeypatch):
        monkeypatch.setitem(auth_module._USERS, "steven", "correct-password")
        monkeypatch.setitem(auth_module._USERS, "alyssa", "")
        monkeypatch.setitem(auth_module._USERS, "guest", "")
        monkeypatch.setattr(auth_module, "_MAX_FAILED_ATTEMPTS", 2)
        monkeypatch.setattr(auth_module, "_FAILED_WINDOW_SECONDS", 300)
        monkeypatch.setattr(auth_module, "_LOCKOUT_SECONDS", 60)
        auth_module._FAILED_ATTEMPTS_BY_IP.clear()
        auth_module._LOCKED_UNTIL_BY_IP.clear()

        bad_headers = _basic_auth("steven", "wrong-password")

        first = remote_client.get("/api/balances/Alice", headers=bad_headers)
        second = remote_client.get("/api/balances/Alice", headers=bad_headers)
        third = remote_client.get("/api/balances/Alice", headers=bad_headers)

        assert first.status_code == 401
        assert second.status_code == 401
        assert third.status_code == 429
        assert third.headers.get("Retry-After") is not None

    def test_successful_login_clears_failure_state(self, remote_client, monkeypatch):
        monkeypatch.setitem(auth_module._USERS, "steven", "correct-password")
        monkeypatch.setitem(auth_module._USERS, "alyssa", "")
        monkeypatch.setitem(auth_module._USERS, "guest", "")
        monkeypatch.setattr(auth_module, "_MAX_FAILED_ATTEMPTS", 3)
        monkeypatch.setattr(auth_module, "_FAILED_WINDOW_SECONDS", 300)
        monkeypatch.setattr(auth_module, "_LOCKOUT_SECONDS", 60)
        auth_module._FAILED_ATTEMPTS_BY_IP.clear()
        auth_module._LOCKED_UNTIL_BY_IP.clear()

        bad_headers = _basic_auth("steven", "wrong-password")
        good_headers = _basic_auth("steven", "correct-password")

        bad = remote_client.get("/api/balances/Alice", headers=bad_headers)
        good = remote_client.get("/api/balances/Alice", headers=good_headers)
        bad_again = remote_client.get("/api/balances/Alice", headers=bad_headers)

        assert bad.status_code == 401
        assert good.status_code == 200
        assert bad_again.status_code == 401
        assert not auth_module._LOCKED_UNTIL_BY_IP


class TestEducationStressTestRoutes:
    def test_get_stress_test_empty(self, client):
        response = client.get("/api/stress-test/Child%201")
        assert response.status_code == 200
        assert response.json() == {"result": None}

    def test_recalculate_stress_test(self, client):
        response = client.post(
            "/api/stress-test/Child%201/recalculate",
            json={"simulation_count": 5000, "random_seed": 42},
        )
        assert response.status_code == 200
        payload = response.json()
        assert payload.get("result") is not None

        result = payload["result"]
        assert result["child_name"] == "Child 1"
        assert result["simulation_count"] == 5000
        assert 0.0 <= float(result["success_probability_pct"]) <= 100.0
        assert result["rating_grade"] in {"A", "B", "C", "D", "F"}

    def test_get_stress_test_after_recalc(self, client):
        response = client.get("/api/stress-test/Child%201")
        assert response.status_code == 200
        result = response.json().get("result")
        assert result is not None
        assert result["child_name"] == "Child 1"


class TestSecurityHeaders:
    def test_csp_present(self, client):
        response = client.get("/health")
        csp = response.headers.get("Content-Security-Policy", "")
        assert "default-src 'self'" in csp
        assert "frame-ancestors 'none'" in csp

    def test_x_frame_options(self, client):
        assert client.get("/health").headers.get("X-Frame-Options") == "DENY"

    def test_nosniff(self, client):
        assert client.get("/health").headers.get("X-Content-Type-Options") == "nosniff"

    def test_hsts(self, client):
        hsts = client.get("/health").headers.get("Strict-Transport-Security", "")
        assert "max-age=" in hsts

    def test_referrer_policy(self, client):
        referrer_policy = client.get("/health").headers.get("Referrer-Policy", "")
        assert "strict-origin" in referrer_policy

    def test_permissions_policy(self, client):
        permissions_policy = client.get("/health").headers.get("Permissions-Policy", "")
        assert "camera=()" in permissions_policy


def test_health_check(client):
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}
