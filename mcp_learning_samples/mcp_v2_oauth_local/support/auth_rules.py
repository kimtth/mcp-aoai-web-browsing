"""Small, SDK-independent teaching helpers; not a general OAuth implementation."""

import base64
import hashlib
import secrets
from urllib.parse import parse_qs, urlsplit

ISSUER = "http://127.0.0.1:8020"
RESOURCE = "http://127.0.0.1:8021/mcp"
REDIRECT = "http://127.0.0.1:8022/callback"
SCOPE = "browser:read"


def challenge(verifier: str) -> str:
    """RFC 7636 S256: SHA-256 then unpadded URL-safe base64."""
    return base64.urlsafe_b64encode(hashlib.sha256(verifier.encode("ascii")).digest()).decode().rstrip("=")


def new_pkce() -> tuple[str, str]:
    verifier = secrets.token_urlsafe(48)
    return verifier, challenge(verifier)


def callback_values(url: str) -> dict[str, str]:
    """Decode once and reject duplicate parameters rather than silently picking one."""
    parts = urlsplit(url)
    if parts._replace(query="").geturl() != REDIRECT:
        raise ValueError("Unexpected callback destination")
    values = parse_qs(parts.query, keep_blank_values=True)
    if any(len(value) != 1 for value in values.values()):
        raise ValueError("Duplicate callback parameter")
    return {key: value[0] for key, value in values.items()}


def validate_callback(values: dict[str, str], expected_state: str,
                      expected_issuer: str, iss_required: bool) -> None:
    """2026-07-28 rule matrix; call BEFORE exchanging a code or using error text."""
    issuer = values.get("iss")
    if issuer is None:
        if iss_required:
            raise ValueError("Missing authorization response issuer")
    elif issuer != expected_issuer:
        # Deliberately no URL normalization: trailing slashes and case matter.
        raise ValueError("Authorization response issuer mismatch")
    if not secrets.compare_digest(values.get("state", ""), expected_state):
        raise ValueError("Authorization state mismatch")
    if "error" in values:
        raise ValueError("Authorization was denied")
    if not values.get("code"):
        raise ValueError("Missing authorization code")