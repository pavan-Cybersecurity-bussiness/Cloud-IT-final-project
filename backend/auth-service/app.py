"""
Auth service — owns the users table and issues JWTs.

Matches the original CampusSwap front-end demo on purpose: there is still
no password, logging in just records who you say you are and which role
you're acting as for the session (see login.html: "Front-end demo — no
password, just picking who you are for this session."). What changes is
that this identity now lives in a real database behind a REST API instead
of being invented client-side in localStorage.
"""
import os
import sqlite3
import time

from flask import Flask, request, jsonify

from jwt_utils import issue_token, get_current_user

DB_PATH = os.environ.get("AUTH_DB_PATH", "/data/auth.db")

app = Flask(__name__)


def get_db():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)
    conn = get_db()
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT UNIQUE COLLATE NOCASE NOT NULL,
            role TEXT NOT NULL,
            created_at TEXT NOT NULL
        )
        """
    )
    conn.commit()
    conn.close()


@app.route("/health")
def health():
    return jsonify({"status": "ok", "service": "auth"})


@app.route("/login", methods=["POST"])
def login():
    body = request.get_json(silent=True) or {}
    name = (body.get("name") or "").strip()
    role = body.get("role") or "Member"

    if len(name) < 2:
        return jsonify({"error": "Enter a name."}), 400
    if role not in ("Member", "Moderator"):
        return jsonify({"error": "Invalid role."}), 400

    conn = get_db()
    row = conn.execute("SELECT * FROM users WHERE name = ?", (name,)).fetchone()
    if row is None:
        cur = conn.execute(
            "INSERT INTO users (name, role, created_at) VALUES (?, ?, ?)",
            (name, role, time.strftime("%Y-%m-%d")),
        )
        conn.commit()
        user_id, stored_role = cur.lastrowid, role
    else:
        # Same relaxed semantics as the original front-end: logging in again
        # under the same name just updates which role you're acting as.
        conn.execute("UPDATE users SET role = ? WHERE id = ?", (role, row["id"]))
        conn.commit()
        user_id, stored_role = row["id"], role
    conn.close()

    token = issue_token(user_id, name, stored_role)
    return jsonify({"token": token, "user": {"id": user_id, "name": name, "role": stored_role}})


@app.route("/me")
def me():
    user = get_current_user()
    if user is None:
        return jsonify({"error": "Not authenticated."}), 401
    return jsonify({"id": user["sub"], "name": user["name"], "role": user["role"]})


init_db()

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5001)
