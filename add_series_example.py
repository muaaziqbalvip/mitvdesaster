#!/usr/bin/env python3
"""Example: add a series with episodes to Firestore"""

import firebase_admin
from firebase_admin import credentials, firestore

cred = credentials.Certificate("serviceAccountKey.json")
firebase_admin.initialize_app(cred)
db = firestore.client()

series_example = {
    "name": "Example Series",
    "poster_url": "https://your-server.com/posters/example.jpg",
    "category": "Drama",
    "active": True,
    "episodes": [
        {"season": 1, "episode": 1, "title": "Pilot", "stream_url": "https://your-server.com/s1e1.m3u8"},
        {"season": 1, "episode": 2, "title": "Episode 2", "stream_url": "https://your-server.com/s1e2.m3u8"},
    ],
}

db.collection("series").document("example-series").set(series_example)
print("✅ Series added")
