"""Small in-memory per-IP limiter for the model-backed endpoints (T-15.08). One process only; the auth limiter counts database rows
and cannot be reused here."""
import time
from collections import defaultdict, deque

from fastapi import HTTPException, Request

from ..config import settings

_hits: dict = defaultdict(deque)


def reset() -> None:
    _hits.clear()


def limit_ai(request: Request) -> None:
    ip = request.client.host if request.client else "unknown"
    q, now = _hits[ip], time.time()
    while q and now - q[0] > 60:
        q.popleft()
    if len(q) >= settings.agent_per_minute:
        raise HTTPException(429, "Too many requests. Please wait a minute.")
    q.append(now)
