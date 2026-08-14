"""
Listings service — owns the listings and favorites tables.

Routes are root-relative (no "/listings" prefix) because the API gateway
adds that prefix when it routes /api/listings/* here. See backend/gateway.
"""
import json
import os
import sqlite3
import time

from flask import Flask, request, jsonify, send_from_directory

from jwt_utils import require_auth, require_role
from image_storage import save_image, LOCAL_UPLOAD_DIR

DB_PATH = os.environ.get("LISTINGS_DB_PATH", "/data/listings.db")
SEED_PATH = os.path.join(os.path.dirname(__file__), "seed_data.json")

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
        CREATE TABLE IF NOT EXISTS listings (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            title TEXT NOT NULL,
            description TEXT NOT NULL,
            category TEXT NOT NULL,
            price REAL NOT NULL,
            condition TEXT NOT NULL,
            seller_id INTEGER,
            seller_name TEXT NOT NULL,
            date_posted TEXT NOT NULL,
            status TEXT NOT NULL DEFAULT 'active',
            reported INTEGER NOT NULL DEFAULT 0,
            report_reason TEXT NOT NULL DEFAULT '',
            image_url TEXT
        )
        """
    )
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS favorites (
            user_id INTEGER NOT NULL,
            listing_id INTEGER NOT NULL,
            PRIMARY KEY (user_id, listing_id)
        )
        """
    )
    conn.commit()

    count = conn.execute("SELECT COUNT(*) AS c FROM listings").fetchone()["c"]
    if count == 0 and os.path.exists(SEED_PATH):
        with open(SEED_PATH) as f:
            seed = json.load(f)
        for item in seed:
            conn.execute(
                """INSERT INTO listings
                   (title, description, category, price, condition, seller_id,
                    seller_name, date_posted, status, reported, report_reason, image_url)
                   VALUES (?, ?, ?, ?, ?, NULL, ?, ?, ?, 0, '', ?)""",
                (
                    item["title"], item["description"], item["category"], item["price"],
                    item["condition"], item["sellerName"], item["datePosted"],
                    item.get("status", "active"), item.get("imageUrl"),
                ),
            )
        conn.commit()
    conn.close()


def row_to_listing(row):
    return {
        "id": str(row["id"]),
        "title": row["title"],
        "description": row["description"],
        "category": row["category"],
        "price": row["price"],
        "condition": row["condition"],
        "sellerName": row["seller_name"],
        "datePosted": row["date_posted"],
        "status": row["status"],
        "reported": bool(row["reported"]),
        "reportReason": row["report_reason"],
        "imageUrl": row["image_url"] or "assets/img/placeholder.png",
    }


def _validate_fields(form):
    errors = {}
    title = (form.get("title") or "").strip()
    category = form.get("category") or ""
    price = form.get("price") or ""
    condition = form.get("condition") or ""
    description = (form.get("description") or "").strip()

    if len(title) < 3:
        errors["title"] = "Title must be at least 3 characters."
    if not category:
        errors["category"] = "Choose a category."
    try:
        if float(price) < 0:
            raise ValueError
    except ValueError:
        errors["price"] = "Enter a valid, non-negative price."
    if not condition:
        errors["condition"] = "Choose a condition."
    if len(description) < 10:
        errors["description"] = "Add at least a short description."
    return errors


@app.route("/health")
def health():
    return jsonify({"status": "ok", "service": "listings"})


@app.route("/uploads/<path:filename>")
def uploaded_file(filename):
    return send_from_directory(LOCAL_UPLOAD_DIR, filename)


@app.route("/mine", methods=["GET"])
@require_auth
def my_listings():
    conn = get_db()
    rows = conn.execute(
        "SELECT * FROM listings WHERE seller_id = ? AND status = 'active' ORDER BY id DESC",
        (request.user["sub"],),
    ).fetchall()
    conn.close()
    return jsonify([row_to_listing(r) for r in rows])


@app.route("/moderation-queue", methods=["GET"])
@require_role("Moderator")
def moderation_queue():
    conn = get_db()
    rows = conn.execute(
        "SELECT * FROM listings WHERE status = 'active' AND reported = 1 ORDER BY id DESC"
    ).fetchall()
    conn.close()
    return jsonify([row_to_listing(r) for r in rows])


@app.route("/favorites", methods=["GET"])
@require_auth
def favorites():
    conn = get_db()
    rows = conn.execute(
        """SELECT l.* FROM listings l
           JOIN favorites f ON f.listing_id = l.id
           WHERE f.user_id = ? AND l.status = 'active'
           ORDER BY l.id DESC""",
        (request.user["sub"],),
    ).fetchall()
    conn.close()
    return jsonify([row_to_listing(r) for r in rows])


@app.route("/", methods=["GET"])
def list_listings():
    category = request.args.get("category")
    q = (request.args.get("q") or "").strip().lower()

    conn = get_db()
    rows = conn.execute(
        "SELECT * FROM listings WHERE status = 'active' ORDER BY id DESC"
    ).fetchall()
    conn.close()

    results = []
    for row in rows:
        if category and category != "all" and row["category"] != category:
            continue
        if q and q not in row["title"].lower() and q not in row["description"].lower():
            continue
        results.append(row_to_listing(row))
    return jsonify(results)


@app.route("/", methods=["POST"])
@require_role("Member")
def create_listing():
    errors = _validate_fields(request.form)
    if errors:
        return jsonify({"errors": errors}), 400

    image_url = save_image(request.files.get("image"))

    conn = get_db()
    cur = conn.execute(
        """INSERT INTO listings
           (title, description, category, price, condition, seller_id, seller_name,
            date_posted, status, reported, report_reason, image_url)
           VALUES (?, ?, ?, ?, ?, ?, ?, ?, 'active', 0, '', ?)""",
        (
            request.form["title"].strip(), request.form["description"].strip(),
            request.form["category"], float(request.form["price"]), request.form["condition"],
            request.user["sub"], request.user["name"], time.strftime("%Y-%m-%d"), image_url,
        ),
    )
    conn.commit()
    new_id = cur.lastrowid
    row = conn.execute("SELECT * FROM listings WHERE id = ?", (new_id,)).fetchone()
    conn.close()
    return jsonify(row_to_listing(row)), 201


@app.route("/<int:listing_id>", methods=["GET"])
def get_listing(listing_id):
    conn = get_db()
    row = conn.execute("SELECT * FROM listings WHERE id = ?", (listing_id,)).fetchone()
    conn.close()
    if row is None:
        return jsonify({"error": "Listing not found."}), 404
    return jsonify(row_to_listing(row))


@app.route("/<int:listing_id>", methods=["PUT"])
@require_auth
def update_listing(listing_id):
    conn = get_db()
    row = conn.execute("SELECT * FROM listings WHERE id = ?", (listing_id,)).fetchone()
    if row is None:
        conn.close()
        return jsonify({"error": "Listing not found."}), 404
    if row["seller_id"] != request.user["sub"]:
        conn.close()
        return jsonify({"error": "You can only edit your own listings."}), 403

    errors = _validate_fields(request.form)
    if errors:
        conn.close()
        return jsonify({"errors": errors}), 400

    image_url = row["image_url"]
    new_image = save_image(request.files.get("image"))
    if new_image:
        image_url = new_image

    conn.execute(
        """UPDATE listings SET title=?, description=?, category=?, price=?,
           condition=?, image_url=? WHERE id=?""",
        (
            request.form["title"].strip(), request.form["description"].strip(),
            request.form["category"], float(request.form["price"]), request.form["condition"],
            image_url, listing_id,
        ),
    )
    conn.commit()
    row = conn.execute("SELECT * FROM listings WHERE id = ?", (listing_id,)).fetchone()
    conn.close()
    return jsonify(row_to_listing(row))


@app.route("/<int:listing_id>", methods=["DELETE"])
@require_auth
def delete_listing(listing_id):
    conn = get_db()
    row = conn.execute("SELECT * FROM listings WHERE id = ?", (listing_id,)).fetchone()
    if row is None:
        conn.close()
        return jsonify({"error": "Listing not found."}), 404

    is_owner = row["seller_id"] == request.user["sub"]
    is_moderator = request.user["role"] == "Moderator"
    if not (is_owner or is_moderator):
        conn.close()
        return jsonify({"error": "Not permitted."}), 403

    conn.execute("UPDATE listings SET status = 'removed' WHERE id = ?", (listing_id,))
    conn.commit()
    conn.close()
    return jsonify({"ok": True})


@app.route("/<int:listing_id>/report", methods=["POST"])
def report_listing(listing_id):
    body = request.get_json(silent=True) or {}
    reason = body.get("reason")
    if not reason:
        return jsonify({"error": "A reason is required."}), 400

    conn = get_db()
    row = conn.execute("SELECT id FROM listings WHERE id = ?", (listing_id,)).fetchone()
    if row is None:
        conn.close()
        return jsonify({"error": "Listing not found."}), 404

    conn.execute(
        "UPDATE listings SET reported = 1, report_reason = ? WHERE id = ?",
        (reason, listing_id),
    )
    conn.commit()
    conn.close()
    return jsonify({"ok": True})


@app.route("/<int:listing_id>/favorite", methods=["POST"])
@require_auth
def toggle_favorite(listing_id):
    conn = get_db()
    existing = conn.execute(
        "SELECT 1 FROM favorites WHERE user_id = ? AND listing_id = ?",
        (request.user["sub"], listing_id),
    ).fetchone()

    if existing:
        conn.execute(
            "DELETE FROM favorites WHERE user_id = ? AND listing_id = ?",
            (request.user["sub"], listing_id),
        )
        favorited = False
    else:
        conn.execute(
            "INSERT INTO favorites (user_id, listing_id) VALUES (?, ?)",
            (request.user["sub"], listing_id),
        )
        favorited = True

    conn.commit()
    conn.close()
    return jsonify({"favorited": favorited})


init_db()

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5002)
