"""Hashing and token helpers. Codes, invite codes and session ids are stored hashed and compared in constant time."""
import hashlib
import hmac
import secrets

from ..config import settings

_DEV_SECRET = secrets.token_bytes(32)  # used only when AUTH_SECRET is unset (development, tests)
_INVITE_ALPHABET = "ABCDEFGHJKLMNPQRSTUVWXYZ23456789"  # no 0, O, 1, I


def _key() -> bytes:
    return settings.auth_secret.encode() if settings.auth_secret else _DEV_SECRET


def mac(*parts: str) -> str:
    return hmac.new(_key(), ":".join(parts).encode(), hashlib.sha256).hexdigest()


def new_code() -> str:
    return f"{secrets.randbelow(10**6):06d}"


def new_invite_code() -> str:
    return "".join(secrets.choice(_INVITE_ALPHABET) for _ in range(8))


def new_session_token() -> str:
    return secrets.token_urlsafe(32)


def sha256(token: str) -> str:
    return hashlib.sha256(token.encode()).hexdigest()


def same(a: str, b: str) -> bool:
    return hmac.compare_digest(a, b)
