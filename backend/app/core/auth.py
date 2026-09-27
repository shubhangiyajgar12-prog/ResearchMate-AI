from __future__ import annotations

import base64
import hashlib
import hmac
import os
import secrets
import time
from typing import Optional

DEFAULT_TOKEN_TTL_SECONDS = 7 * 24 * 60 * 60
PASSWORD_ITERATIONS = 310_000


def _secret() -> bytes:
    value = os.getenv("AUTH_SECRET", "").strip()
    if not value or value == "PASTE_A_LONG_RANDOM_SECRET_HERE":
        raise RuntimeError(
            "AUTH_SECRET is not configured. Set a strong random AUTH_SECRET in backend/.env."
        )
    return value.encode("utf-8")


def hash_password(password: str) -> str:
    if not isinstance(password, str) or not password:
        raise ValueError("Password cannot be empty.")

    salt = secrets.token_bytes(16)
    digest = hashlib.pbkdf2_hmac(
        "sha256",
        password.encode("utf-8"),
        salt,
        PASSWORD_ITERATIONS,
    )

    return (
        f"pbkdf2_sha256${PASSWORD_ITERATIONS}$"
        f"{base64.urlsafe_b64encode(salt).decode('ascii')}$"
        f"{base64.urlsafe_b64encode(digest).decode('ascii')}"
    )


def verify_password(password: str, stored_hash: str) -> bool:
    try:
        algorithm, iterations_text, salt_text, digest_text = stored_hash.split("$", 3)

        if algorithm != "pbkdf2_sha256":
            return False

        iterations = int(iterations_text)
        salt = base64.urlsafe_b64decode(salt_text.encode("ascii"))
        expected = base64.urlsafe_b64decode(digest_text.encode("ascii"))

        actual = hashlib.pbkdf2_hmac(
            "sha256",
            password.encode("utf-8"),
            salt,
            iterations,
        )

        return hmac.compare_digest(actual, expected)
    except (ValueError, TypeError, UnicodeError):
        return False


def _b64(value: bytes) -> str:
    return base64.urlsafe_b64encode(value).decode("ascii").rstrip("=")


def _unb64(value: str) -> bytes:
    padding = "=" * (-len(value) % 4)
    return base64.urlsafe_b64decode((value + padding).encode("ascii"))


def create_access_token(user_id: int, ttl_seconds: Optional[int] = None) -> str:
    try:
        user_id = int(user_id)
    except (TypeError, ValueError) as exc:
        raise ValueError("Invalid user id.") from exc

    if user_id <= 0:
        raise ValueError("Invalid user id.")

    if ttl_seconds is None:
        raw_ttl = os.getenv("AUTH_TOKEN_TTL_SECONDS", "").strip()
        try:
            ttl_seconds = int(raw_ttl) if raw_ttl else DEFAULT_TOKEN_TTL_SECONDS
        except ValueError:
            ttl_seconds = DEFAULT_TOKEN_TTL_SECONDS

    ttl_seconds = max(300, min(ttl_seconds, 60 * 60 * 24 * 30))
    expires_at = int(time.time()) + ttl_seconds

    payload = f"rm1.{user_id}.{expires_at}".encode("utf-8")
    signature = hmac.new(_secret(), payload, hashlib.sha256).digest()

    return f"rm1.{user_id}.{expires_at}.{_b64(signature)}"


def decode_access_token(token: str) -> Optional[int]:
    if not token or not isinstance(token, str):
        return None

    try:
        version, user_id_text, expires_text, signature_text = token.strip().split(
            ".", 3
        )

        if version != "rm1":
            return None

        user_id = int(user_id_text)
        expires_at = int(expires_text)

        if user_id <= 0 or expires_at <= int(time.time()):
            return None

        payload = f"{version}.{user_id}.{expires_at}".encode("utf-8")
        expected_signature = hmac.new(
            _secret(),
            payload,
            hashlib.sha256,
        ).digest()
        supplied_signature = _unb64(signature_text)

        if not hmac.compare_digest(expected_signature, supplied_signature):
            return None

        return user_id

    except (ValueError, TypeError, UnicodeError):
        return None
