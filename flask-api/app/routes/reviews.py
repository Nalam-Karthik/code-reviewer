# flask-api/app/routes/reviews.py

import time
from flask import Blueprint, request, jsonify
from flask_jwt_extended import jwt_required, get_jwt_identity

from app import db
from app.models import Review
from app.services.cache import (
    get_cached_review, set_cached_review,
    make_code_hash, get_cache_stats
)
from app.services.ai import get_code_review
from app.services.memory import store_review_embedding, get_similar_past_reviews
from app.services.kafka_producer import publish_review_event

reviews_bp = Blueprint("reviews", __name__)

SUPPORTED_LANGUAGES = [
    "python", "javascript", "java", "c", "cpp",
    "typescript", "go", "rust", "sql", "bash"
]


@reviews_bp.route("/submit", methods=["POST"])
@jwt_required()
def submit_review():
    """
    Full Day 2 flow:
    1. Validate input
    2. Check Redis cache → return immediately if hit
    3. Query ChromaDB for similar past reviews (memory)
    4. Call OpenRouter AI with memory context injected
    5. Store result in MySQL
    6. Store embedding in ChromaDB
    7. Publish event to Kafka
    8. Cache result in Redis
    9. Return structured JSON
    """
    data    = request.get_json()
    user_id = int(get_jwt_identity())

    # ── Validate ──────────────────────────────
    if not data or not data.get("code"):
        return jsonify({"error": "'code' is required"}), 400

    language = data.get("language", "python").lower()
    if language not in SUPPORTED_LANGUAGES:
        return jsonify({
            "error": f"Unsupported language. Supported: {SUPPORTED_LANGUAGES}"
        }), 400

    code = data["code"].strip()
    if len(code) < 10:
        return jsonify({"error": "Code too short to review"}), 400

    # ── Cache check ───────────────────────────
    start_ms = time.time() * 1000
    cached   = get_cached_review(language, code)

    if cached:
        return jsonify({
            **cached,
            "cached":      True,
            "response_ms": round(time.time() * 1000 - start_ms, 2)
        }), 200

    # ── ChromaDB: get past similar reviews ────
    # This is what makes the AI "remember" the user's patterns
    past_reviews = get_similar_past_reviews(
        user_id=user_id,
        language=language,
        code=code
    )
    has_memory = len(past_reviews) > 0

    # ── AI call with memory context ───────────
    result = get_code_review(language, code, past_reviews=past_reviews)

    if result["error"] and not result["review"]:
        return jsonify({"error": f"AI service error: {result['error']}"}), 502

    review_data = result["review"]
    tokens_used = result["tokens_used"]
    score       = review_data.get("score")

    # ── Store in MySQL ────────────────────────
    review = Review(
        user_id        = user_id,
        language       = language,
        code_snippet   = code,
        code_hash      = make_code_hash(language, code),
        ai_response    = review_data,
        tokens_used    = tokens_used,
        cached         = False,
        severity_score = score
    )
    db.session.add(review)
    db.session.commit()

    # ── Store embedding in ChromaDB ───────────
    store_review_embedding(
        review_id = review.id,
        user_id   = user_id,
        language  = language,
        code      = code,
        summary   = review_data.get("summary", ""),
        score     = score or 0
    )

    # ── Publish to Kafka ──────────────────────
    # Fire and forget — API doesn't wait for consumer
    publish_review_event(
        review_id = review.id,
        user_id   = user_id,
        language  = language,
        score     = score or 0
    )

    # ── Build response ─────────────────────────
    response = {
        "review_id":        review.id,
        "language":         language,
        "summary":          review_data.get("summary"),
        "score":            score,
        "issues":           review_data.get("issues", []),
        "strengths":        review_data.get("strengths", []),
        "recurring_issues": review_data.get("recurring_issues", []),
        "tokens_used":      tokens_used,
        "cached":           False,
        "memory_used":      has_memory,    # tells you if past reviews were used
        "past_reviews_found": len(past_reviews),
        "response_ms":      round(time.time() * 1000 - start_ms, 2)
    }

    # ── Cache for next identical submission ───
    set_cached_review(language, code, response)

    return jsonify(response), 200


@reviews_bp.route("/stats", methods=["GET"])
@jwt_required()
def cache_stats():
    """Live Redis cache performance metrics."""
    return jsonify(get_cache_stats()), 200