# flask-api/app/models.py

from datetime import datetime
from app import db   


class User(db.Model):
    """
    Stores registered users.
    password_hash stores bcrypt hash — never store plain text.
    """
    __tablename__ = "users"

    id            = db.Column(db.Integer, primary_key=True)
    username      = db.Column(db.String(80),  nullable=False, unique=True)
    email         = db.Column(db.String(120), nullable=False, unique=True)
    password_hash = db.Column(db.String(255), nullable=False)
    created_at    = db.Column(db.DateTime, default=datetime.utcnow)

    # One user → many reviews (backref lets you do review.author)
    reviews = db.relationship("Review", backref="author", lazy=True)

    def to_dict(self):
        return {
            "id":         self.id,
            "username":   self.username,
            "email":      self.email,
            "created_at": self.created_at.isoformat()
        }


class Review(db.Model):
    """
    One AI review of one code submission.
    ai_response stores the full structured JSON from OpenRouter as TEXT.
    severity_score is 0-100, added via Alembic migration mid-Day-1.
    """
    __tablename__ = "reviews"

    id             = db.Column(db.Integer, primary_key=True)
    user_id        = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)
    language       = db.Column(db.String(50),  nullable=False)
    code_snippet   = db.Column(db.Text,         nullable=False)
    code_hash      = db.Column(db.String(64),   nullable=False)  # MD5 — used for cache key
    ai_response    = db.Column(db.JSON,          nullable=True)   # full structured response
    tokens_used    = db.Column(db.Integer,       default=0)
    cached         = db.Column(db.Boolean,       default=False)   # True if served from Redis
    severity_score = db.Column(db.Integer,       nullable=True)   # added via Alembic later
    created_at     = db.Column(db.DateTime, default=datetime.utcnow)

    def to_dict(self):
        return {
            "review_id":      self.id,
            "language":       self.language,
            "ai_response":    self.ai_response,
            "tokens_used":    self.tokens_used,
            "cached":         self.cached,
            "severity_score": self.severity_score,
            "created_at":     self.created_at.isoformat()
        }


class RefreshToken(db.Model):
    """
    Stores hashed refresh tokens.
    This is what makes proper JWT auth — access tokens expire in 15 min,
    refresh tokens let users get a new access token without logging in again.
    revoked=True means the token has been logged out.
    """
    __tablename__ = "refresh_tokens"

    id         = db.Column(db.Integer, primary_key=True)
    user_id    = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)
    token_hash = db.Column(db.String(255), nullable=False, unique=True)
    expires_at = db.Column(db.DateTime,   nullable=False)
    revoked    = db.Column(db.Boolean,    default=False)
    created_at = db.Column(db.DateTime,   default=datetime.utcnow)