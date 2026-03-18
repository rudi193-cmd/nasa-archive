"""
SAFE Framework Integration — NASA Archive Explorer
===================================================
Session hooks, consent management, and Pigeon bus helpers.

Drop point: POST /api/pigeon/drop
Topics: ask, query, contribute, connect, status
"""

import os
import uuid
import requests as _requests
from typing import Dict, Optional
from datetime import datetime

# ── Pigeon Bus Helpers ────────────────────────────────────────────────────────

WILLOW_URL = os.environ.get("WILLOW_URL", "http://localhost:8420")
PIGEON_URL = f"{WILLOW_URL}/api/pigeon/drop"
APP_ID = "safe-app-nasa-archive"

_session_id = str(uuid.uuid4())


def ask(prompt: str, persona: Optional[str] = None, tier: str = "free") -> str:
    """Ask Willow a question. Returns the LLM response as a string."""
    result = _drop("ask", {"prompt": prompt, "persona": persona, "tier": tier})
    if result.get("ok"):
        return result.get("result", "")
    return f"[Error: {result.get('error', 'unknown')}]"


def query(q: str, limit: int = 5) -> list:
    """Query Willow's knowledge graph. Returns a list of matching atoms."""
    result = _drop("query", {"q": q, "limit": limit})
    if result.get("ok"):
        return result.get("result", [])
    return []


def contribute(content: str, category: str = "note", metadata: Optional[dict] = None) -> dict:
    """Contribute content to Willow's knowledge graph."""
    return _drop("contribute", {
        "content": content,
        "category": category,
        "metadata": metadata or {},
    })


def status() -> dict:
    """Check if Willow bus is reachable."""
    return _drop("status", {})


def _drop(topic: str, payload: dict) -> dict:
    """Internal: drop a message onto the Pigeon bus."""
    try:
        r = _requests.post(PIGEON_URL, json={
            "topic": topic,
            "app_id": APP_ID,
            "session_id": _session_id,
            "payload": payload,
        }, timeout=30)
        return r.json() if r.ok else {"ok": False, "error": r.text}
    except _requests.ConnectionError:
        return {
            "ok": False,
            "guest_mode": True,
            "error": f"Willow not reachable at {WILLOW_URL}. "
                     "Set WILLOW_URL env var or run Willow locally."
        }
    except Exception as e:
        return {"ok": False, "error": str(e)}


# ── SAFE Session ──────────────────────────────────────────────────────────────

APP_STREAMS = [
    {
        "stream_id": "query_history",
        "purpose": "Remember searches you ran this session",
        "retention": "session",
        "required": False,
        "prompt": "May I remember your searches this session for quick re-run?"
    },
    {
        "stream_id": "saved_discoveries",
        "purpose": "Store datasets and images you explicitly save",
        "retention": "permanent",
        "required": False,
        "prompt": "May I save datasets and images you choose to keep?"
    }
]


class SAFESession:
    """Manages SAFE session lifecycle and consent."""

    def __init__(self, session_id: str):
        self.session_id = session_id
        self.started_at = datetime.now()
        self.consents = {}
        self.active = True

    def on_session_start(self) -> Dict:
        return {
            "session_id": self.session_id,
            "authorization_requests": APP_STREAMS
        }

    def on_consent_granted(self, stream_id: str, granted: bool) -> Dict:
        self.consents[stream_id] = {
            "granted": granted,
            "timestamp": datetime.now().isoformat()
        }
        return {"status": "ok"}

    def can_access_stream(self, stream_id: str) -> bool:
        return self.consents.get(stream_id, {}).get("granted", False)

    def on_session_end(self) -> Dict:
        self.active = False
        actions = []
        if self.can_access_stream("query_history"):
            actions.append({"action": "delete", "stream": "query_history", "reason": "session_ended"})
        if self.can_access_stream("saved_discoveries"):
            actions.append({"action": "retain", "stream": "saved_discoveries", "reason": "permanent_consent"})
        return {
            "session_id": self.session_id,
            "ended_at": datetime.now().isoformat(),
            "duration_seconds": (datetime.now() - self.started_at).total_seconds(),
            "cleanup_actions": actions
        }

    def on_revoke(self, stream_id: str) -> Dict:
        if stream_id in self.consents:
            self.consents[stream_id]["granted"] = False
            self.consents[stream_id]["revoked_at"] = datetime.now().isoformat()
        return {"status": "revoked", "stream": stream_id, "action": "data_deleted"}


# ── Willow Consent Helpers ────────────────────────────────────────────────────

def get_consent_status(token=None):
    """Check if this app has consent to contribute to the user's Willow."""
    try:
        import requests as _r
        headers = {"Authorization": f"Bearer {token}"} if token else {}
        resp = _r.get(f"{WILLOW_URL}/api/apps", headers=headers, timeout=10)
        apps = resp.json().get("apps", [])
        return next((a["consented"] for a in apps if a["app_id"] == APP_ID), False)
    except Exception:
        return False


def request_consent_url():
    """Return the Willow URL where the user can grant consent to this app."""
    return f"{WILLOW_URL}/apps?highlight={APP_ID}"



def send(to_app, subject, body, thread_id=None):
    """Send a message to another app's Pigeon inbox."""
    return _drop("send", {"to": to_app, "subject": subject, "body": body, "thread_id": thread_id})


def check_inbox(unread_only=True):
    """Fetch this app's Pigeon inbox from Willow."""
    try:
        import requests as _r
        r = _r.get(
            f"{WILLOW_URL}/api/pigeon/inbox",
            params={"app_id": APP_ID, "unread_only": str(unread_only).lower()},
            timeout=10
        )
        return r.json().get("messages", []) if r.ok else []
    except Exception:
        return []

