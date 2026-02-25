"""
SAFE Framework Integration — NASA Archive Explorer
===================================================
Session hooks and consent management.
"""

from typing import Dict
from datetime import datetime


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
