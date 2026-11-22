
import os
from datetime import datetime, timezone

import psycopg
from flask import Flask, request, jsonify

app = Flask(__name__)

DATABASE_URL = os.environ["DATABASE_URL"]
ADMIN_KEY = os.environ["ADMIN_KEY"]


def get_db():
    return psycopg.connect(DATABASE_URL)


def init_db():
    with get_db() as con:
        con.execute("""
            CREATE TABLE IF NOT EXISTS connections (
                id BIGSERIAL PRIMARY KEY,
                device_id VARCHAR(64) NOT NULL,
                connected_at TIMESTAMPTZ NOT NULL
            )
        """)


@app.get("/")
def home():
    return jsonify({
        "app": "IPMONITOR",
        "status": "ONLINE"
    })


@app.post("/connect")
def connect_device():
    data = request.get_json(silent=True) or {}

    if data.get("consent") is not True:
        return jsonify({"error": "Consent required"}), 403

    device_id = data.get("device_id")

    if not isinstance(device_id, str) or not device_id.strip() or len(device_id) > 64:
        return jsonify({"error": "Invalid device ID"}), 400

    now = datetime.now(timezone.utc)

    with get_db() as con:
        con.execute(
            """
            INSERT INTO connections (device_id, connected_at)
            VALUES (%s, %s)
            """,
            (device_id, now)
        )

    return jsonify({"status": "registered"})


@app.get("/connections")
def get_connections():
    if request.headers.get("X-Admin-Key") != ADMIN_KEY:
        return jsonify({"error": "Unauthorized"}), 401

    with get_db() as con:
        rows = con.execute("""
            SELECT id, device_id, connected_at
            FROM connections
            ORDER BY id DESC
            LIMIT 500
        """).fetchall()

    return jsonify([
        {
            "id": row[0],
            "device": row[1],
            "date": row[2].isoformat()
        }
        for row in rows
    ])


init_db()
