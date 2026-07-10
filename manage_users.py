#!/usr/bin/env python3
"""
Add or update a subscriber in the MITV panel.
Run locally: python manage_users.py
"""

import bcrypt
import firebase_admin
from firebase_admin import credentials, firestore
from datetime import datetime, timedelta, timezone

cred = credentials.Certificate("serviceAccountKey.json")
firebase_admin.initialize_app(cred)
db = firestore.client()


def add_user(username: str, plain_password: str, days_valid: int = 30, max_devices: int = 1):
    password_hash = bcrypt.hashpw(plain_password.encode(), bcrypt.gensalt()).decode()
    expiry = datetime.now(timezone.utc) + timedelta(days=days_valid)

    db.collection("users").document(username).set({
        "password_hash": password_hash,
        "expiry": expiry,
        "active": True,
        "max_devices": max_devices,
        "registered_devices": [],  # reset devices on (re)subscription
        "created_at": datetime.now(timezone.utc),
    })
    print(f"✅ User '{username}' added/updated. Expires: {expiry.date()}, max_devices={max_devices}")


def renew_user(username: str, extra_days: int = 30):
    """Extend expiry and clear device list so they can re-bind fresh devices if desired."""
    ref = db.collection("users").document(username)
    doc = ref.get()
    if not doc.exists:
        print("User not found")
        return
    current = doc.to_dict()
    current_expiry = current.get("expiry")
    base = current_expiry.replace(tzinfo=timezone.utc) if current_expiry else datetime.now(timezone.utc)
    if base < datetime.now(timezone.utc):
        base = datetime.now(timezone.utc)
    new_expiry = base + timedelta(days=extra_days)
    ref.update({"expiry": new_expiry, "active": True})
    print(f"✅ '{username}' renewed until {new_expiry.date()}")


def disable_user(username: str):
    db.collection("users").document(username).update({"active": False})
    print(f"🚫 '{username}' disabled")


if __name__ == "__main__":
    # Examples — edit and run as needed:
    add_user("customer001", "StrongPass123!", days_valid=30, max_devices=2)
    # renew_user("customer001", extra_days=30)
    # disable_user("customer001")
