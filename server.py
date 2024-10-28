import os
from dotenv import load_dotenv
from flask import Flask, request, jsonify, redirect, abort
from flask_sqlalchemy import SQLAlchemy
from flask_cors import CORS
import validators
import redis
from typing import Optional
from datetime import datetime, timedelta
import hashlib
import base64
from pydantic import BaseModel
from functools import wraps

load_dotenv()

app = Flask(__name__)
CORS(app)

# Database configuration
app.config['SQLALCHEMY_DATABASE_URI'] = os.getenv('DATABASE_URL', 'sqlite:///urls.db')
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
db = SQLAlchemy(app)

# Redis configuration
redis_client = redis.Redis(
    host=os.getenv('REDIS_HOST', 'localhost'),
    port=int(os.getenv('REDIS_PORT', 6379)),
    db=0,
    decode_responses=True
)

# Define URL model
class URL(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    original_url = db.Column(db.String, nullable=False)
    short_url = db.Column(db.String, unique=True, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    expires_at = db.Column(db.DateTime)
    access_count = db.Column(db.Integer, default=0)

with app.app_context():
    db.create_all()

# Rate Limiting Decorator
def rate_limit(limit, period):
    def decorator(f):
        timestamps = []
        
        @wraps(f)
        def wrapped(*args, **kwargs):
            nonlocal timestamps
            now = datetime.now()
            timestamps = [t for t in timestamps if t > now - timedelta(seconds=period)]
            if len(timestamps) >= limit:
                abort(429, description="Too Many Requests")
            timestamps.append(now)
            return f(*args, **kwargs)
        return wrapped
    return decorator

class URLRequest(BaseModel):
    url: str
    custom_slug: Optional[str] = None
    expiration_days: Optional[int] = None

class URLResponse(BaseModel):
    short_url: str

def generate_short_url(url: str, attempt: int = 0) -> str:
    input_string = f"{url}{attempt}{datetime.now().timestamp()}"
    hash_object = hashlib.sha256(input_string.encode())
    hash_bytes = hash_object.digest()
    short_url = base64.urlsafe_b64encode(hash_bytes)[:6].decode()
    return short_url

@app.route("/url/shorten", methods=["POST"])
@rate_limit(10, 60)  # Rate limit: 10 requests per minute
def shorten_url():
    data = request.get_json()
    url_request = URLRequest(**data)

    if not validators.url(url_request.url):
        abort(400, "Invalid URL")

    if url_request.custom_slug:
        if len(url_request.custom_slug) > 20:
            abort(400, "Custom slug too long")
        if URL.query.filter_by(short_url=url_request.custom_slug).first():
            abort(409, "Custom slug already exists")
        short_url = url_request.custom_slug
    else:
        attempt = 0
        while True:
            short_url = generate_short_url(url_request.url, attempt)
            if not URL.query.filter_by(short_url=short_url).first():
                break
            attempt += 1

    expiration_date = None
    if url_request.expiration_days:
        if url_request.expiration_days <= 0:
            abort(400, "Expiration days must be positive")
        expiration_date = datetime.utcnow() + timedelta(days=url_request.expiration_days)

    url_record = URL(
        original_url=url_request.url,
        short_url=short_url,
        created_at=datetime.utcnow(),
        expires_at=expiration_date
    )
    db.session.add(url_record)
    db.session.commit()

    if expiration_date:
        redis_client.setex(f"url:{short_url}", int(timedelta(days=url_request.expiration_days).total_seconds()), url_request.url)
    else:
        redis_client.set(f"url:{short_url}", url_request.url)

    base_url = os.getenv('BASE_URL', 'http://localhost:8000')
    return jsonify(URLResponse(short_url=f"{base_url}/r/{short_url}").dict()), 201

@app.route("/r/<short_url>")
def redirect_url(short_url):
    cached_url = redis_client.get(f"url:{short_url}")
    if cached_url:
        redis_client.incr(f"stats:{short_url}")
        return redirect(cached_url)

    url_record = URL.query.filter_by(short_url=short_url).first()
    if not url_record:
        abort(404, "URL not found")

    if url_record.expires_at and url_record.expires_at < datetime.utcnow():
        db.session.delete(url_record)
        db.session.commit()
        abort(404, "URL has expired")

    url_record.access_count += 1
    db.session.commit()

    if url_record.expires_at:
        ttl = int((url_record.expires_at - datetime.utcnow()).total_seconds())
        if ttl > 0:
            redis_client.setex(f"url:{short_url}", ttl, url_record.original_url)
    else:
        redis_client.set(f"url:{short_url}", url_record.original_url)

    return redirect(url_record.original_url)

@app.route("/stats/<short_url>")
def get_stats(short_url):
    url_record = URL.query.filter_by(short_url=short_url).first()
    if not url_record:
        abort(404, "URL not found")

    return jsonify({
        "short_url": short_url,
        "original_url": url_record.original_url,
        "created_at": url_record.created_at,
        "expires_at": url_record.expires_at,
        "access_count": url_record.access_count
    })

if __name__ == "__main__":
    app.run(debug=True, port=int(os.getenv('PORT', 8000)))
