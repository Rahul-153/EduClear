"""Sign-in code delivery behind an interface (AGENT_MANUAL.md section 5). Only a mock exists until a provider key is chosen."""
import logging
from typing import List, Protocol, Tuple

from ..config import settings

log = logging.getLogger("educlear.mailer")


class Mailer(Protocol):
    real: bool

    def send_code(self, email: str, code: str) -> None: ...


class MockMailer:
    """Keeps codes in memory for tests and logs them in development. Never used as a real channel in production."""
    real = False

    def __init__(self) -> None:
        self.outbox: List[Tuple[str, str]] = []

    def send_code(self, email: str, code: str) -> None:
        self.outbox.append((email, code))
        if settings.env != "production":
            log.info("[mock mailer] sign-in code %s for %s", code, email)


_mailer = MockMailer()


def get_mailer() -> Mailer:
    return _mailer
