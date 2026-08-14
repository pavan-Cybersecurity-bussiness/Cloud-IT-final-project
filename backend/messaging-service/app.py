"""
Messaging service — owns the inquiries table.

Deliberately denormalized: listingTitle and sellerName are stored on the
inquiry itself at creation time (the frontend already has both when the
buyer submits the contact form on the listing detail page) rather than
this service calling back into listings-service to look them up. That
keeps the two services independent — messaging-service works even if
listings-service is temporarily down — at the cost of a stale title if a
listing is later renamed. A reasonable trade-off for this project's scale.

Routes are root-relative; the gateway adds the /api/inquiries prefix.
"""
import os
import sqlite3
import time

from flask import Flask, request, jsonify

from jwt_utils import require_auth

DB_PATH = os.environ.get("MESSAGING_DB_PATH", "/data/messaging.db")

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
        CREATE TABLE IF NOT EXISTS inquiries (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            listing_id TEXT NOT NULL,
            listing_title TEXT NOT NULL,
            seller_name TEXT NOT NULL,
            from_name TEXT NOT NULL,
            message TEXT NOT NULL,
            date_posted TEXT NOT NULL
        )
        """
    )
    conn.commit()
    conn.close()


def row_to_inquiry(row):
    return {
        "id": str(row["id"]),
        "listingId": row["listing_id"],
        "listingTitle": row["listing_title"],
        "sellerName": row["seller_name"],
        "fromName": row["from_name"],
        "message": row["message"],
        "datePosted": row["date_posted"],
    }


@app.route("/health")
def health():
    return jsonify({"status": "ok", "service": "messaging"})


@app.route("/", methods=["POST"])
def create_inquiry():
    body = request.get_json(silent=True) or {}
    listing_id = body.get("listingId")
    listing_title = body.get("listingTitle") or "a listing"
    seller_name = body.get("sellerName")
    from_name = (body.get("fromName") or "").strip()
    message = (body.get("message") or "").strip()

    if not listing_id or not seller_name:
        return jsonify({"error": "Missing listing reference."}), 400
    if len(from_name) < 2:
        return jsonify({"error": "Enter a name."}), 400
    if len(message) < 5:
        return jsonify({"error": "Write a short message before sending."}), 400

    conn = get_db()
    conn.execute(
        """INSERT INTO inquiries
           (listing_id, listing_title, seller_name, from_name, message, date_posted)
           VALUES (?, ?, ?, ?, ?, ?)""",
        (str(listing_id), listing_title, seller_name, from_name, message, time.strftime("%Y-%m-%d")),
    )
    conn.commit()
    conn.close()
    return jsonify({"ok": True}), 201


@app.route("/mine", methods=["GET"])
@require_auth
def my_inquiries():
    conn = get_db()
    rows = conn.execute(
        "SELECT * FROM inquiries WHERE seller_name = ? COLLATE NOCASE ORDER BY id DESC",
        (request.user["name"],),
    ).fetchall()
    conn.close()
    return jsonify([row_to_inquiry(r) for r in rows])


@app.route("/<int:inquiry_id>", methods=["DELETE"])
@require_auth
def dismiss_inquiry(inquiry_id):
    conn = get_db()
    row = conn.execute("SELECT * FROM inquiries WHERE id = ?", (inquiry_id,)).fetchone()
    if row is None:
        conn.close()
        return jsonify({"error": "Not found."}), 404
    if row["seller_name"].lower() != request.user["name"].lower():
        conn.close()
        return jsonify({"error": "Not permitted."}), 403
    conn.execute("DELETE FROM inquiries WHERE id = ?", (inquiry_id,))
    conn.commit()
    conn.close()
    return jsonify({"ok": True})


init_db()

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5003)
