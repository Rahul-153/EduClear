"""Live PayPal SANDBOX tests. Run with: .venv/bin/python -m pytest -m paypal_sandbox backend/tests/paypal -v
Needs PAYPAL_CLIENT_ID / PAYPAL_CLIENT_SECRET (sandbox app) in .env. Buyer approval needs a browser, so capture and payout
are covered by scripts/paypal_sandbox_smoke.py steps."""
import pytest

from backend.app.config import settings
from backend.app.integrations.paypal import SANDBOX_BASE, HttpPayPal

pytestmark = pytest.mark.paypal_sandbox
if not (settings.paypal_client_id and settings.paypal_client_secret):
    pytest.skip("sandbox credentials not set", allow_module_level=True)


@pytest.fixture(scope="module")
def pp():
    return HttpPayPal(settings.paypal_client_id, settings.paypal_client_secret, settings.paypal_webhook_id)


def test_base_url_is_sandbox():
    assert SANDBOX_BASE.endswith("sandbox.paypal.com")


def test_auth_token(pp):
    assert pp._auth()


def test_create_order_usd(pp):
    o = pp.create_order(2999, "live-test-1", "EduClear sandbox smoke test")
    assert o["id"] and o["status"] in ("CREATED", "PAYER_ACTION_REQUIRED")


def test_capture_of_unapproved_order_is_rejected(pp):
    from backend.app.integrations.paypal import PayPalError
    o = pp.create_order(2999, "live-test-2", "EduClear sandbox smoke test")
    with pytest.raises(PayPalError):
        pp.capture_order(o["id"])


def test_webhook_with_bad_signature_is_rejected(pp):
    assert pp.verify_webhook({"paypal-auth-algo": "x", "paypal-cert-url": "https://example.test", "paypal-transmission-id": "x",
                              "paypal-transmission-sig": "x", "paypal-transmission-time": "2026-01-01T00:00:00Z"}, {"id": "WH-X"}) is False
