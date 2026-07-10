"""
MITV Panel - Full Xtream-style endpoint
- Live TV + Movies + Series
- Device limit tracking (device_id + IP)
- Expiry / device-limit -> redirects ALL channels to a warning video
- Session logging (who watched what, from where, when)
"""

import os
import json
import time
import bcrypt
from datetime import datetime, timezone
from fastapi import FastAPI, Query, Request, Response
import firebase_admin
from firebase_admin import credentials, firestore

app = FastAPI()

if not firebase_admin._apps:
    cred_json = json.loads(os.environ["FIREBASE_SERVICE_ACCOUNT"])
    cred = credentials.Certificate(cred_json)
    firebase_admin.initialize_app(cred)

db = firestore.client()

EXPIRED_VIDEO_URL = os.environ.get("EXPIRED_VIDEO_URL", "https://your-server.com/expired-payment.mp4")
DEVICE_LIMIT_VIDEO_URL = os.environ.get("DEVICE_LIMIT_VIDEO_URL", "https://your-server.com/device-limit.mp4")

_attempts = {}
MAX_ATTEMPTS = 5
WINDOW_SECONDS = 60


def is_rate_limited(ip: str) -> bool:
    now = time.time()
    window = [t for t in _attempts.get(ip, []) if now - t < WINDOW_SECONDS]
    window.append(now)
    _attempts[ip] = window
    return len(window) > MAX_ATTEMPTS


def verify_password(plain: str, hashed: str) -> bool:
    try:
        return bcrypt.checkpw(plain.encode(), hashed.encode())
    except Exception:
        return False


def get_client_ip(request: Request) -> str:
    fwd = request.headers.get("x-forwarded-for")
    if fwd:
        return fwd.split(",")[0].strip()
    return request.client.host if request.client else "unknown"


def check_device_limit(user_ref, user: dict, device_id: str, ip: str) -> bool:
    devices = user.get("registered_devices", [])
    max_devices = user.get("max_devices", 1)

    existing = next((d for d in devices if d["device_id"] == device_id), None)
    if existing:
        existing["last_seen"] = datetime.now(timezone.utc).isoformat()
        existing["last_ip"] = ip
        user_ref.update({"registered_devices": devices})
        return True

    if len(devices) >= max_devices:
        return False

    devices.append({
        "device_id": device_id,
        "first_seen": datetime.now(timezone.utc).isoformat(),
        "last_seen": datetime.now(timezone.utc).isoformat(),
        "last_ip": ip,
    })
    user_ref.update({"registered_devices": devices})
    return True


def log_session(username: str, ip: str, device_id: str, note: str):
    db.collection("sessions").add({
        "username": username,
        "ip": ip,
        "device_id": device_id,
        "note": note,
        "timestamp": datetime.now(timezone.utc),
    })


BUY_PRO_VIDEO_URL = os.environ.get("BUY_PRO_VIDEO_URL", "https://your-server.com/buy-pro-promo.mp4")


def build_m3u(items: list, warning: bool = False, user_tier: str = "pro") -> str:
    lines = ["#EXTM3U"]
    for item in items:
        name = item.get("name", "Unknown")
        logo = item.get("logo_url") or item.get("poster_url", "")
        category = item.get("category", "General")
        item_tier = item.get("tier", "free")

        if warning:
            url = EXPIRED_VIDEO_URL
        elif user_tier == "free" and item_tier == "pro":
            url = BUY_PRO_VIDEO_URL
            name = f"LOCKED {name} (PRO - Buy to unlock)"
        else:
            url = item.get("stream_url", "")

        lines.append(f'#EXTINF:-1 tvg-logo="{logo}" group-title="{category}",{name}')
        lines.append(url)
    return "\n".join(lines)


def authenticate(username: str, password: str, ip: str, device_id: str):
    user_ref = db.collection("users").document(username)
    user_doc = user_ref.get()
    if not user_doc.exists:
        return "invalid", None, None

    user = user_doc.to_dict()
    if not verify_password(password, user.get("password_hash", "")):
        return "invalid", None, None

    if not user.get("active", False):
        return "expired", user, user_ref

    expiry = user.get("expiry")
    if expiry and expiry.replace(tzinfo=timezone.utc) < datetime.now(timezone.utc):
        return "expired", user, user_ref

    if not check_device_limit(user_ref, user, device_id, ip):
        return "device_limit", user, user_ref

    return "ok", user, user_ref


@app.get("/")
@app.get("/get")
def get_playlist(
    request: Request,
    username: str = Query(...),
    password: str = Query(...),
    type: str = Query("m3u_plus"),
    output: str = Query("m3u8"),
    device_id: str = Query("unknown-device"),
):
    ip = get_client_ip(request)

    if is_rate_limited(ip):
        return Response(content="Too many attempts, try later", status_code=429)

    status, user, user_ref = authenticate(username, password, ip, device_id)

    if status == "invalid":
        return Response(content="Invalid credentials", status_code=401)

    channels = [c.to_dict() for c in db.collection("channels").where("active", "==", True).stream()]
    movies = [m.to_dict() for m in db.collection("movies").where("active", "==", True).stream()]

    all_items = channels + movies
    user_tier = (user or {}).get("tier", "free")

    if status == "expired":
        log_session(username, ip, device_id, "BLOCKED_EXPIRED")
        playlist = build_m3u(all_items, warning=True)
        return Response(content=playlist, media_type="application/vnd.apple.mpegurl")

    if status == "device_limit":
        log_session(username, ip, device_id, "BLOCKED_DEVICE_LIMIT")
        for item in all_items:
            item["stream_url"] = DEVICE_LIMIT_VIDEO_URL
        playlist = build_m3u(all_items, warning=False)
        return Response(content=playlist, media_type="application/vnd.apple.mpegurl")

    log_session(username, ip, device_id, "PLAYLIST_SERVED")
    playlist = build_m3u(all_items, user_tier=user_tier)
    return Response(
        content=playlist,
        media_type="application/vnd.apple.mpegurl",
        headers={"Content-Disposition": "inline; filename=playlist.m3u8"},
    )


@app.get("/api/series")
def get_series(
    request: Request,
    username: str = Query(...),
    password: str = Query(...),
    device_id: str = Query("unknown-device"),
):
    ip = get_client_ip(request)
    status, user, user_ref = authenticate(username, password, ip, device_id)

    if status != "ok":
        return Response(content=json.dumps({"error": status}), status_code=403, media_type="application/json")

    series_docs = db.collection("series").where("active", "==", True).stream()
    series_list = [s.to_dict() for s in series_docs]

    log_session(username, ip, device_id, "SERIES_LIST_SERVED")
    return Response(content=json.dumps(series_list), media_type="application/json")
