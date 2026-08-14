"""
jwt_utils.py — shared JWT helper.

This file is intentionally duplicated (not imported as a shared package)
across auth-service, listings-service, and messaging-service. Each
microservice owns a copy so it can be built, tested, and deployed on its
own, without a shared internal library coupling the three together.
"""
import os
import time
from functools import wraps

import jwt
from flask import request, jsonify

JWT_SECRET = os.environ.get("JWT_SECRET", "dev-secret-change-me")
JWT_ALGO = "HS256"
JWT_EXPIRY_SECONDS = 60 * 60 * 12  # 12 hours


def issue_token(user_id, name, role):
    payload = {
        "sub": user_id,
        "name": name,
        "role": role,
        "iat": int(time.time()),
        "exp": int(time.time()) + JWT_EXPIRY_SECONDS,
    }
    return jwt.encode(payload, JWT_SECRET, algorithm=JWT_ALGO)


def decode_token(token):
    return jwt.decode(token, JWT_SECRET, algorithms=[JWT_ALGO])


def get_current_user():
    """Returns the decoded token claims for the current request, or None."""
    auth_header = request.headers.get("Authorization", "")
    if not auth_header.startswith("Bearer "):
        return None
    token = auth_header.split(" ", 1)[1]
    try:
        return decode_token(token)
    except jwt.PyJWTError:
        return None


def require_auth(fn):
    @wraps(fn)
    def wrapper(*args, **kwargs):
        user = get_current_user()
        if user is None:
            return jsonify({"error": "Authentication required."}), 401
        request.user = user
        return fn(*args, **kwargs)
    return wrapper


def require_role(*roles):
    def decorator(fn):
        @wraps(fn)
        def wrapper(*args, **kwargs):
            user = get_current_user()
            if user is None:
                return jsonify({"error": "Authentication required."}), 401
            if user["role"] not in roles:
                return jsonify({"error": "Not permitted for this role."}), 403
            request.user = user
            return fn(*args, **kwargs)
        return wrapper
    return decorator
