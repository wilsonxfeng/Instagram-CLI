import os
from pathlib import Path
from typing import Dict, List

from dotenv import load_dotenv
from flask import Flask, jsonify, request, send_from_directory
from instagrapi import Client
from instagrapi.exceptions import ClientError, ClientLoginRequired

SESSION_PATH = Path("session.json")
THREAD_MESSAGE_LIMIT = 1

app = Flask(__name__, static_folder="static", static_url_path="/")

_client: Client | None = None


def login_with_session(cl: Client, username: str, password: str) -> None:
    if SESSION_PATH.exists():
        cl.load_settings(SESSION_PATH)
    try:
        cl.login(username, password)
    except (ClientLoginRequired, ClientError):
        if SESSION_PATH.exists():
            SESSION_PATH.unlink()
        cl.login(username, password)
        cl.dump_settings(SESSION_PATH)


def get_client() -> Client:
    global _client
    if _client is None:
        load_dotenv()
        username = os.environ["USERNAME"]
        password = os.environ["PASSWORD"]
        cl = Client()
        login_with_session(cl, username, password)
        _client = cl
    return _client


def thread_title(thread) -> str:
    if thread.thread_title:
        return thread.thread_title
    return ", ".join(u.username for u in thread.users)


@app.get("/")
def index():
    return send_from_directory("static", "index.html")


@app.get("/api/inbox")
def api_inbox():
    amount = int(request.args.get("amount", "10"))
    cl = get_client()
    threads = cl.direct_threads(amount=amount, thread_message_limit=THREAD_MESSAGE_LIMIT)
    payload = []
    for t in threads:
        last = t.messages[0] if t.messages else None
        payload.append(
            {
                "id": t.id,
                "title": thread_title(t),
                "last_text": last.text if last and last.text else "",
                "last_ts": last.timestamp.isoformat() if last and last.timestamp else "",
                "users": [{"id": str(u.pk), "username": u.username} for u in t.users],
            }
        )
    return jsonify(payload)


@app.get("/api/me")
def api_me():
    cl = get_client()
    return jsonify({"user_id": str(cl.user_id)})


@app.get("/api/thread/<thread_id>")
def api_thread(thread_id: str):
    amount = int(request.args.get("amount", "20"))
    cl = get_client()
    messages = cl.direct_messages(thread_id, amount=amount)
    payload = [
        {
            "id": m.id,
            "user_id": str(m.user_id),
            "text": m.text or "",
            "timestamp": m.timestamp.isoformat(),
        }
        for m in sorted(messages, key=lambda x: x.timestamp)
    ]
    return jsonify(payload)


@app.post("/api/send")
def api_send():
    data = request.get_json(force=True)
    thread_id = data.get("thread_id")
    text = data.get("text", "").strip()
    if not thread_id or not text:
        return jsonify({"ok": False, "error": "thread_id and text required"}), 400
    cl = get_client()
    cl.direct_answer(thread_id, text)
    return jsonify({"ok": True})


if __name__ == "__main__":
    app.run(host="127.0.0.1", port=5000, debug=True)
