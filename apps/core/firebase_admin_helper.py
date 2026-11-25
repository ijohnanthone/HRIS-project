import json
import logging
import os

import firebase_admin
from firebase_admin import credentials, db

logger = logging.getLogger(__name__)

DEFAULT_DATABASE_URL = 'https://hr-request-7c711-default-rtdb.asia-southeast1.firebasedatabase.app'


def init_firebase_admin():
    """
    Lazily and safely initializes the Firebase Admin SDK for server-side
    Realtime Database operations.

    Supports both:
    - FIREBASE_CREDENTIALS_JSON: raw JSON string (recommended for Vercel env vars)
    - FIREBASE_CREDENTIALS_PATH: path to local service account JSON file

    Returns the initialized Firebase App, or None if credentials are not configured.
    """
    if firebase_admin._apps:
        return firebase_admin.get_app()

    database_url = os.getenv('FIREBASE_DATABASE_URL', DEFAULT_DATABASE_URL).strip() or DEFAULT_DATABASE_URL
    cred_json = os.getenv('FIREBASE_CREDENTIALS_JSON', '').strip()
    cred_path = os.getenv('FIREBASE_CREDENTIALS_PATH', '').strip()

    try:
        cred = None
        if cred_json:
            cred = credentials.Certificate(json.loads(cred_json))
        elif cred_path and os.path.exists(cred_path):
            cred = credentials.Certificate(cred_path)
        else:
            return None

        return firebase_admin.initialize_app(cred, {
            'databaseURL': database_url,
        })
    except Exception as exc:
        logger.warning('Firebase Admin initialization skipped or failed: %s', exc)
        return None


def push_realtime_event(reference_path: str, payload: dict):
    """
    Pushes a new child record to Firebase Realtime Database under `reference_path`.
    No-ops safely if Firebase Admin credentials are not configured.
    """
    if not init_firebase_admin():
        return None

    try:
        ref = db.reference(reference_path)
        created = ref.push(payload)
        return created.key
    except Exception as exc:
        logger.warning('Firebase RTDB push failed on %s: %s', reference_path, exc)
        return None


def set_realtime_value(reference_path: str, payload: dict) -> bool:
    """
    Sets/updates a record at `reference_path` in Firebase Realtime Database.
    No-ops safely if Firebase Admin credentials are not configured.
    """
    if not init_firebase_admin():
        return False

    try:
        ref = db.reference(reference_path)
        ref.set(payload)
        return True
    except Exception as exc:
        logger.warning('Firebase RTDB set failed on %s: %s', reference_path, exc)
        return False
