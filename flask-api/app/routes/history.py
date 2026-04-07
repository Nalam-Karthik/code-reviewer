from flask import Blueprint,request,jsonify
from flask_jwt_extended import jwt_required, get_jwt_identity
from app.models import Review

history_bp = Blueprint("history", __name__)

@history_bp.route("/",methods = ["GET"])
@jwt_required()
def get_history():
    user_id = get_jwt_identity()
    language = request.args.get("language")
    limit = request.args.get("limit", 20, type=int)
    limit = min(limit, 100)

    query = Review.query.filter_by(user_id=user_id)
    if language:
        query = query.filter_by(language=language)

    reviews = query.order_by(Review.created_at.desc()).limit(limit).all()

    return jsonify({
        "reviews": [r.to_dict() for r in reviews],
        "total":   len(reviews)
    }), 200

