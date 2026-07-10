#!/usr/bin/env python3
"""
Bulk add channels to MITV Firestore panel
Run this locally or on your dev machine
"""

import firebase_admin
from firebase_admin import credentials, firestore
import json

# Initialize Firebase (use your service account JSON)
cred = credentials.Certificate("path/to/serviceAccountKey.json")
firebase_admin.initialize_app(cred)
db = firestore.client()

# Channel data (update with your actual streams)
CHANNELS = [
    {
        "id": "ptv-sports",
        "name": "PTV Sports",
        "stream_url": "https://example.com/stream/ptv-sports.m3u8",
        "category": "Sports",
        "logo_url": "https://example.com/logos/ptv-sports.png",
        "active": True,
    },
    {
        "id": "geo-news",
        "name": "Geo News",
        "stream_url": "https://example.com/stream/geo-news.m3u8",
        "category": "News",
        "logo_url": "https://example.com/logos/geo-news.png",
        "active": True,
    },
    {
        "id": "quran-24-7",
        "name": "Quran 24/7 (Live Recitation)",
        "stream_url": "https://your-server.com/quran-stream.m3u8",
        "category": "Islamic",
        "logo_url": "https://your-server.com/quran-logo.png",
        "active": True,
    },
    {
        "id": "ary-news",
        "name": "ARY News",
        "stream_url": "https://example.com/stream/ary-news.m3u8",
        "category": "News",
        "logo_url": "https://example.com/logos/ary-news.png",
        "active": True,
    },
]

def add_channels_to_firestore():
    batch = db.batch()
    for channel in CHANNELS:
        doc_ref = db.collection("channels").document(channel["id"])
        batch.set(doc_ref, channel)
    
    batch.commit()
    print(f"✅ Added {len(CHANNELS)} channels to Firestore")

if __name__ == "__main__":
    add_channels_to_firestore()
