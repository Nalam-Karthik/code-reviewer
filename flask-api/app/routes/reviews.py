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

reviews_bp = Blueprint("reviews", __name__)

SUPPORTED_LANGUAGES = [
    "python", "javascript", "java", "c", "cpp",
    "typescript", "go", "rust", "sql", "bash"
]


@reviews_bp.route("/submit", methods=["POST"])
@jwt_required()
def submit_review():
    
    data    = request.get_json()
    user_id = get_jwt_identity()

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

    
    start_ms = time.time() * 1000
    cached   = get_cached_review(language, code)

    if cached:
        
        return jsonify({
            **cached,
            "cached":       True,
            "response_ms":  round(time.time() * 1000 - start_ms, 2)
        }), 200

    
    result = get_code_review(language, code)

    if result["error"] and not result["review"]:
        return jsonify({"error": f"AI service error: {result['error']}"}), 502

    review_data = result["review"]
    tokens_used = result["tokens_used"]

    
    review = Review(
        user_id      = user_id,
        language     = language,
        code_snippet = code,
        code_hash    = make_code_hash(language, code),
        ai_response  = review_data,
        tokens_used  = tokens_used,
        cached       = False,
        severity_score = review_data.get("score")
    )
    db.session.add(review)
    db.session.commit()

    # ── Build response ─────────────────────────
    # This is the JSON contract — shape never changes without versioning
    response = {
        "review_id":   review.id,
        "language":    language,
        "summary":     review_data.get("summary"),
        "score":       review_data.get("score"),
        "issues":      review_data.get("issues", []),
        "strengths":   review_data.get("strengths", []),
        "tokens_used": tokens_used,
        "cached":      False,
        "response_ms": round(time.time() * 1000 - start_ms, 2)
    }

    # ── Store in Redis for next identical submission ──
    set_cached_review(language, code, response)

    return jsonify(response), 200


@reviews_bp.route("/stats", methods=["GET"])
@jwt_required()
def cache_stats():
    """Live Redis cache performance — your resume's performance story."""
    return jsonify(get_cache_stats()), 200