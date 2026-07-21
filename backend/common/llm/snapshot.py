from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass, field
from datetime import datetime, timezone


@dataclass(frozen=True)
class ProviderSnapshot:
    provider_id: str
    provider_name: str
    provider_type: str
    api_url: str
    model: str
    enabled: bool
    timeout: int
    api_key: str | None = field(default=None, repr=False)
    captured_at: str = field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat()
    )

    @property
    def fingerprint(self) -> str:
        key_digest = hashlib.sha256(
            (self.api_key or "").encode("utf-8")
        ).hexdigest()
        payload = {
            "provider_id": self.provider_id,
            "provider_type": self.provider_type,
            "api_url": self.api_url.rstrip("/"),
            "model": self.model,
            "enabled": self.enabled,
            "timeout": self.timeout,
            "api_key_digest": key_digest,
        }
        encoded = json.dumps(payload, sort_keys=True, separators=(",", ":"))
        return hashlib.sha256(encoded.encode("utf-8")).hexdigest()

    def sanitized(self) -> dict[str, object]:
        return {
            "provider_id": self.provider_id,
            "provider_name": self.provider_name,
            "provider_type": self.provider_type,
            "api_url": self.api_url,
            "model": self.model,
            "enabled": self.enabled,
            "timeout": self.timeout,
            "api_key_configured": bool((self.api_key or "").strip()),
            "fingerprint": self.fingerprint,
            "captured_at": self.captured_at,
        }
