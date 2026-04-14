# flask-api/tests/test_reviews.py

import pytest
from unittest.mock import patch, MagicMock


# ── Mock the external services so tests don't need OpenRouter/Redis/ChromaDB ──
# patch() replaces the real function with a fake one during the test
# This is standard practice — unit tests shouldn't call real external APIs

MOCK_AI_RESPONSE = {
    "review": {
        "summary":          "Code has a SQL injection vulnerability",
        "score":            25,
        "issues":           [{"line": 2, "severity": "error",
                              "message": "SQL injection risk", "fix": "Use parameterized queries"}],
        "strengths":        ["Simple function structure"],
        "recurring_issues": [],
        "language_detected": "python"
    },
    "tokens_used": 150,
    "error": None
}


class TestReviewSubmit:
    """Tests for POST /api/reviews/submit"""

    @patch("app.routes.reviews.get_cached_review", return_value=None)
    @patch("app.routes.reviews.get_similar_past_reviews", return_value=[])
    @patch("app.routes.reviews.get_code_review", return_value=MOCK_AI_RESPONSE)
    @patch("app.routes.reviews.store_review_embedding", return_value=None)
    @patch("app.routes.reviews.publish_review_event", return_value=True)
    @patch("app.routes.reviews.set_cached_review", return_value=None)
    def test_submit_success(self, mock_cache_set, mock_kafka,
                            mock_chroma, mock_ai, mock_memory,
                            mock_cache_get, client, auth_headers):
        """Valid code submission returns structured review."""
        res = client.post("/api/reviews/submit",
            headers=auth_headers,
            json={"language": "python", "code": "def get_user(id):\n    return db.execute('SELECT * FROM users WHERE id='+str(id))"}
        )
        assert res.status_code == 200
        data = res.get_json()
        assert "review_id"   in data
        assert "score"       in data
        assert "issues"      in data
        assert "cached"      in data
        assert data["cached"] is False
        assert data["score"]  == 25

    @patch("app.routes.reviews.get_cached_review", return_value=None)
    @patch("app.routes.reviews.get_similar_past_reviews", return_value=[])
    @patch("app.routes.reviews.get_code_review", return_value=MOCK_AI_RESPONSE)
    @patch("app.routes.reviews.store_review_embedding", return_value=None)
    @patch("app.routes.reviews.publish_review_event", return_value=True)
    @patch("app.routes.reviews.set_cached_review", return_value=None)
    def test_submit_stores_in_db(self, mock_cache_set, mock_kafka,
                                  mock_chroma, mock_ai, mock_memory,
                                  mock_cache_get, client, auth_headers, db):
        """Submitted review is saved to the database."""
        from app.models import Review
        client.post("/api/reviews/submit",
            headers=auth_headers,
            json={"language": "python", "code": "def foo():\n    pass\n    return 1"}
        )
        reviews = Review.query.all()
        assert len(reviews) == 1
        assert reviews[0].language == "python"

    def test_submit_no_token(self, client):
        """Request without JWT returns 401."""
        res = client.post("/api/reviews/submit",
            json={"language": "python", "code": "def foo(): pass"}
        )
        assert res.status_code == 401

    def test_submit_missing_code(self, client, auth_headers):
        """Request without code field returns 400."""
        res = client.post("/api/reviews/submit",
            headers=auth_headers,
            json={"language": "python"}
        )
        assert res.status_code == 400
        assert "error" in res.get_json()

    def test_submit_unsupported_language(self, client, auth_headers):
        """Unsupported language returns 400."""
        res = client.post("/api/reviews/submit",
            headers=auth_headers,
            json={"language": "cobol", "code": "IDENTIFICATION DIVISION."}
        )
        assert res.status_code == 400

    def test_submit_code_too_short(self, client, auth_headers):
        """Code under 10 chars returns 400."""
        res = client.post("/api/reviews/submit",
            headers=auth_headers,
            json={"language": "python", "code": "x=1"}
        )
        assert res.status_code == 400

    @patch("app.routes.reviews.get_cached_review")
    def test_cache_hit_returns_instantly(self, mock_cache_get, client, auth_headers):
        """When Redis has the result, AI is never called."""
        cached_data = {
            "review_id": 99, "language": "python",
            "summary": "Cached review", "score": 80,
            "issues": [], "strengths": [],
            "tokens_used": 0, "cached": True
        }
        mock_cache_get.return_value = cached_data

        res = client.post("/api/reviews/submit",
            headers=auth_headers,
            json={"language": "python", "code": "def add(a,b):\n    return a + b"}
        )
        assert res.status_code == 200
        assert res.get_json()["cached"] is True


class TestReviewHistory:
    """Tests for GET /api/history/"""

    def test_history_empty(self, client, auth_headers):
        """New user has no history."""
        res = client.get("/api/history/", headers=auth_headers)
        assert res.status_code == 200
        assert res.get_json()["total"] == 0

    def test_history_requires_auth(self, client):
        """History endpoint without token returns 401."""
        res = client.get("/api/history/")
        assert res.status_code == 401

    @patch("app.routes.reviews.get_cached_review", return_value=None)
    @patch("app.routes.reviews.get_similar_past_reviews", return_value=[])
    @patch("app.routes.reviews.get_code_review", return_value=MOCK_AI_RESPONSE)
    @patch("app.routes.reviews.store_review_embedding", return_value=None)
    @patch("app.routes.reviews.publish_review_event", return_value=True)
    @patch("app.routes.reviews.set_cached_review", return_value=None)
    def test_history_shows_past_reviews(self, mock_cache_set, mock_kafka,
                                         mock_chroma, mock_ai, mock_memory,
                                         mock_cache_get, client, auth_headers):
        """After submitting, history shows that review."""
        client.post("/api/reviews/submit",
            headers=auth_headers,
            json={"language": "python", "code": "def hello():\n    print('hello world')"}
        )
        res = client.get("/api/history/", headers=auth_headers)
        assert res.status_code == 200
        assert res.get_json()["total"] == 1