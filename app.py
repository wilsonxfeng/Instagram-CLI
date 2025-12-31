import os
from pathlib import Path
from typing import Dict, List, Optional

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


def best_image_url(image_versions) -> Optional[str]:
    if not image_versions or not image_versions.candidates:
        return None
    best = max(image_versions.candidates, key=lambda c: c.width * c.height)
    return best.url


def animated_media_url(animated: dict) -> Optional[str]:
    if not isinstance(animated, dict):
        return None
    images = animated.get("images", {})
    for key in ("fixed_height", "fixed_width", "original"):
        if key in images and images[key].get("url"):
            return images[key]["url"]
    return animated.get("url")


def extract_attachments(message) -> List[Dict[str, str]]:
    attachments: List[Dict[str, str]] = []

    if message.animated_media:
        url = animated_media_url(message.animated_media)
        if url:
            attachments.append({"kind": "gif", "url": url, "label": "gif"})

    if message.media:
        if message.media.thumbnail_url:
            attachments.append(
                {
                    "kind": "image",
                    "url": str(message.media.thumbnail_url),
                    "label": "image",
                }
            )
        elif message.media.video_url:
            attachments.append({"kind": "video", "label": "video"})
        elif message.media.audio_url:
            attachments.append({"kind": "audio", "label": "audio"})

    if message.visual_media and message.visual_media.media:
        media = message.visual_media.media
        if media.media_type == 1:
            url = best_image_url(media.image_versions2)
            if url:
                attachments.append({"kind": "image", "url": url, "label": "image"})
            else:
                attachments.append({"kind": "image", "label": "image"})
        elif media.media_type == 2:
            attachments.append({"kind": "video", "label": "video"})

    if message.story_share:
        attachments.append({"kind": "story", "label": "story"})
    if message.reel_share:
        attachments.append({"kind": "reel", "label": "reel"})
    if message.media_share:
        attachments.append({"kind": "post", "label": "post"})
    if message.clip:
        attachments.append({"kind": "clip", "label": "clip"})

    return attachments


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
    payload = []
    for m in sorted(messages, key=lambda x: x.timestamp):
        payload.append(
            {
                "id": m.id,
                "user_id": str(m.user_id),
                "text": m.text or "",
                "timestamp": m.timestamp.isoformat(),
                "attachments": extract_attachments(m),
            }
        )
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
