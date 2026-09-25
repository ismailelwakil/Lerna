"""Security primitives: uploads (magic bytes, sanitization), signed URLs,
prompt-injection-resistant context wrapping, rate limiting."""
from __future__ import annotations

import hashlib
import hmac
import re
import secrets
import time
import uuid
from collections import defaultdict, deque

from .config import get_settings
from .exceptions import FileTooLargeError, RateLimitedError, UnsupportedFileError

# ------------------------------------------------------------------ uploads
ALLOWED_EXTENSIONS = {
    ".pdf": "application/pdf",
    ".docx": "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
    ".pptx": "application/vnd.openxmlformats-officedocument.presentationml.presentation",
    ".txt": "text/plain",
    ".png": "image/png", ".jpg": "image/jpeg", ".jpeg": "image/jpeg", ".webp": "image/webp",
    ".mp3": "audio/mpeg", ".wav": "audio/wav", ".mp4": "video/mp4",  # voice/video future
}

# magic-byte signatures (never trust client MIME or extension alone)
_MAGIC = [
    (b"%PDF-", {".pdf"}),
    (b"PK\x03\x04", {".docx", ".pptx"}),
    (b"\x89PNG\r\n\x1a\n", {".png"}),
    (b"\xff\xd8\xff", {".jpg", ".jpeg"}),
    (b"RIFF", {".wav", ".webp"}),
    (b"\x00\x00\x00\x20ftypisom", {".mp4"}),
    (b"\xff\xfb", {".mp3"}),
    (b"\xff\xf3", {".mp3"}),
    (b"ID3", {".mp3"}),
]


def validate_upload(filename: str, content: bytes, client_mime: str = "") -> tuple[str, str]:
    """Validate size, extension AND magic bytes. Returns (safe_stem, ext)."""
    settings = get_settings()
    max_bytes = settings.max_upload_mb * 1024 * 1024
    if not content:
        raise UnsupportedFileError("The uploaded file is empty.")
    if len(content) > max_bytes:
        raise FileTooLargeError(
            f"File exceeds the {settings.max_upload_mb} MB limit.")

    import pathlib
    raw = pathlib.Path(filename or "file").name  # strip any path components
    ext = pathlib.Path(raw).suffix.lower()
    if ext not in ALLOWED_EXTENSIONS:
        raise UnsupportedFileError(
            f"Unsupported file type '{ext or '(none)'}'. Supported: "
            + ", ".join(sorted(ALLOWED_EXTENSIONS)))

    ok_exts = None
    for signature, exts in _MAGIC:
        if content.startswith(signature):
            ok_exts = exts
            break
    if ok_exts is None and ext not in {".txt", ".md", ".csv"}:
        # text files have no signature; everything else must match magic bytes
        raise UnsupportedFileError(
            "File content does not match its extension (rejected for safety).")
    if ok_exts is not None and ext not in ok_exts and not (ext == ".webp" and b"RIFF" in content[:4]):
        raise UnsupportedFileError(
            "File content does not match its extension (rejected for safety).")

    stem = re.sub(r"[^A-Za-z0-9._-]", "_", raw[: -len(ext)] if ext else raw)[:120] or "file"
    stem = stem.replace("..", "_").strip("._-") or "file"
    return stem, ext


def safe_storage_key(student_id: str, ext: str) -> str:
    """Collision-free, traversal-proof storage key (no user-controlled parts)."""
    return f"{re.sub(r'[^a-zA-Z0-9_-]', '', student_id)[:32]}/{uuid.uuid4().hex}{ext}"


# ------------------------------------------------------------- signed URLs
def sign_key(key: str, expires_at: int) -> str:
    settings = get_settings()
    return hmac.new(settings.signing_secret.encode(),
                    f"{key}:{expires_at}".encode(), hashlib.sha256).hexdigest()


def make_signed_url(key: str, base_path: str = "/api/v1/content/assets") -> str:
    settings = get_settings()
    expires = int(time.time()) + settings.signed_url_ttl * 60
    return f"{base_path}/{key}?exp={expires}&sig={sign_key(key, expires)}"


def verify_signed(key: str, exp: str | int, sig: str) -> bool:
    try:
        expires = int(exp)
    except (TypeError, ValueError):
        return False
    if expires < int(time.time()):
        return False
    return hmac.compare_digest(sign_key(key, expires), sig)


# ------------------------------------------------- untrusted context wrap
_ROLE_MARKERS = re.compile(r"</?\s*(system|developer|assistant|source_context)\s*>", re.I)
_INJECTION = re.compile(
    r"(ignore.{0,24}(instructions|rules|prompt)|disregard.{0,24}(instructions|rules)|"
    r"you are now (a|an)\b|new system prompt|reveal (your|the) (system )?prompt|"
    r"print (your|the) (system )?prompt|repeat everything above)", re.I)


def wrap_untrusted(content: str, label: str = "source") -> str:
    """Neutralize role markers and instruction spikes, then wrap as DATA."""
    sanitized = _ROLE_MARKERS.sub("[filtered-tag]", content or "")
    sanitized = _INJECTION.sub("[filtered-instruction]", sanitized)
    return f"<{label}_context untrusted=\"true\">\n{sanitized}\n</{label}_context>"


def new_id() -> str:
    return uuid.uuid4().hex


def otp_like_secret() -> str:
    return secrets.token_urlsafe(32)


# ------------------------------------------------------------- rate limiter
class MemoryRateLimiter:
    def __init__(self) -> None:
        self._hits: dict[str, deque] = defaultdict(deque)

    def hit(self, key: str, limit: int, window: int) -> bool:
        now = time.time()
        bucket = self._hits[key]
        while bucket and now - bucket[0] > window:
            bucket.popleft()
        if len(bucket) >= limit:
            return False
        bucket.append(now)
        return True


_limiter = MemoryRateLimiter()


def enforce_rate(kind: str, identity: str) -> None:
    limit, window = get_settings().rate_limit(kind)
    if not _limiter.hit(f"{kind}:{identity}", limit, window):
        raise RateLimitedError()