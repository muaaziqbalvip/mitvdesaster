# MITV Panel — Setup Guide

## What this is
An Xtream-style panel (`get.php` compatible) backed by Firebase Firestore,
deployable on Vercel. Supports:
- Live TV channels
- Movies (VOD)
- Series with episodes
- Per-user device limit (device_id + IP tracked)
- Auto-expiry: when subscription lapses, ALL channels redirect to your
  payment-reminder video instead of real streams
- Device-limit-exceeded: redirects to a separate warning video
- Session logs (who watched what, from where, when)

## 1. Firebase setup
1. Go to Firebase Console → Project Settings → Service Accounts
2. Generate new private key → download the JSON
3. Keep this file SECRET — never commit it, never put it in client-side code
4. **Rotate your existing web apiKey/config** if it was ever shared publicly —
   while the apiKey itself is meant to be public in client apps, it's good
   practice to review your Firestore rules (see firestore.rules) since that's
   what actually protects your data, not the apiKey.

## 2. Deploy Firestore rules
```bash
firebase deploy --only firestore:rules
```
This locks down `users`, `channels`, `movies`, `series`, and `sessions` so only
your server (using the Admin SDK) can touch them — no client can read/write directly.

## 3. Set environment variables on Vercel
In your Vercel project settings → Environment Variables:
- `FIREBASE_SERVICE_ACCOUNT` → paste the full service account JSON as one line
- `EXPIRED_VIDEO_URL` → URL of your "please renew" video
- `DEVICE_LIMIT_VIDEO_URL` → URL of your "device limit reached" video

## 4. Deploy
```bash
cd mitv-panel
vercel deploy --prod
```

## 5. Add channels / movies / series
```bash
pip install firebase-admin bcrypt
python add_channels.py
python add_series_example.py
```

## 6. Add subscribers
```bash
python manage_users.py
```
Edit the `add_user(...)` call at the bottom with real usernames/passwords,
subscription length, and device limit before running.

## 7. Test the playlist
```
https://your-app.vercel.app/get.php?username=customer001&password=StrongPass123!&type=m3u_plus&output=m3u8&device_id=test-device-1
```
Try it in VLC, then try again with a different `device_id` beyond your
`max_devices` limit — you should see the device-limit warning video instead.

## 8. Renewing a subscriber
```python
from manage_users import renew_user
renew_user("customer001", extra_days=30)
```

## Notes
- `device_id` should be a stable per-install identifier your Android app
  generates once and reuses (e.g. `Settings.Secure.ANDROID_ID` or a UUID
  stored in SharedPreferences) — NOT something that changes every request.
- IP is captured server-side automatically via the `x-forwarded-for` header.
- All of this only governs YOUR own subscribers and YOUR own licensed content.
  Make sure `stream_url` values point to content you have rights to distribute.
