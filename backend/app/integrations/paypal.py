"""PayPal sandbox integration (INT-01). SANDBOX ONLY: the base URL is pinned and the app refuses any other environment.

Two implementations share one interface: HttpPayPal (real sandbox REST calls) and MockPayPal (offline, deterministic) so
the demo never breaks (NFR-04). get_paypal() picks HttpPayPal only when sandbox credentials are present.
"""
import base64
import itertools
import uuid
import time
from typing import Dict, Optional, Protocol

import httpx

from ..config import settings

SANDBOX_BASE = "https://api-m.sandbox.paypal.com"  # pinned; never configurable (NFR-05)


class PayPalError(Exception):
    def __init__(self, message: str, status: int = 502):
        super().__init__(message)
        self.status = status


def assert_sandbox() -> None:
    if settings.paypal_env != "sandbox":
        raise RuntimeError("PAYPAL_ENV must be 'sandbox'. Live PayPal is never used by this project.")


def inr_to_usd_cents(inr: int) -> int:
    return round(inr * settings.inr_to_usd_rate * 100)


class PayPal(Protocol):
    mode: str

    def create_order(self, usd_cents: int, reference: str, description: str) -> dict: ...
    def capture_order(self, order_id: str) -> dict: ...
    def payout(self, receiver_email: str, usd_cents: int, note: str, batch_id: str) -> dict: ...
    def verify_webhook(self, headers: Dict[str, str], event: dict) -> bool: ...


def _usd(cents: int) -> str:
    return f"{cents / 100:.2f}"


class HttpPayPal:
    mode = "live-sandbox"

    def __init__(self, client_id: str, secret: str, webhook_id: str):
        assert_sandbox()
        self.client_id, self.secret, self.webhook_id = client_id, secret, webhook_id
        self._token: Optional[str] = None
        self._exp = 0.0

    def _auth(self) -> str:
        if self._token and time.time() < self._exp - 30:
            return self._token
        basic = base64.b64encode(f"{self.client_id}:{self.secret}".encode()).decode()
        r = httpx.post(f"{SANDBOX_BASE}/v1/oauth2/token", headers={"Authorization": f"Basic {basic}"},
                       data={"grant_type": "client_credentials"}, timeout=20)
        if r.status_code != 200:
            raise PayPalError(f"PayPal sandbox authentication failed ({r.status_code})")
        j = r.json()
        self._token, self._exp = j["access_token"], time.time() + int(j.get("expires_in", 300))
        return self._token

    def _call(self, method: str, path: str, body: Optional[dict] = None, headers: Optional[dict] = None) -> dict:
        h = {"Authorization": f"Bearer {self._auth()}", "Content-Type": "application/json", **(headers or {})}
        try:
            r = httpx.request(method, f"{SANDBOX_BASE}{path}", json=body, headers=h, timeout=30)
        except httpx.HTTPError as e:
            raise PayPalError(f"PayPal sandbox unreachable: {type(e).__name__}", 504)
        if r.status_code >= 400:
            raise PayPalError(f"PayPal sandbox error {r.status_code}: {r.text[:300]}", 402 if r.status_code in (400, 422) else 502)
        return r.json() if r.content else {}

    def create_order(self, usd_cents: int, reference: str, description: str) -> dict:
        j = self._call("POST", "/v2/checkout/orders", {"intent": "CAPTURE", "purchase_units": [{
            "reference_id": reference, "description": description[:120],
            "amount": {"currency_code": "USD", "value": _usd(usd_cents)}}]},
            headers={"PayPal-Request-Id": f"educlear-{reference}"})
        return {"id": j["id"], "status": j["status"]}

    def capture_order(self, order_id: str) -> dict:
        j = self._call("POST", f"/v2/checkout/orders/{order_id}/capture", {}, headers={"PayPal-Request-Id": f"capture-{order_id}"})
        cap = j["purchase_units"][0]["payments"]["captures"][0]
        return {"status": j["status"], "capture_id": cap["id"],
                "usd_cents": round(float(cap["amount"]["value"]) * 100), "capture_status": cap["status"]}

    def payout(self, receiver_email: str, usd_cents: int, note: str, batch_id: str) -> dict:
        j = self._call("POST", "/v1/payments/payouts", {
            "sender_batch_header": {"sender_batch_id": batch_id, "email_subject": "EduClear session payout"},
            "items": [{"recipient_type": "EMAIL", "receiver": receiver_email, "sender_item_id": batch_id, "note": note[:100],
                       "amount": {"value": _usd(usd_cents), "currency": "USD"}}]})
        return {"batch_id": j["batch_header"]["payout_batch_id"], "status": j["batch_header"]["batch_status"]}

    def verify_webhook(self, headers: Dict[str, str], event: dict) -> bool:
        h = {k.lower(): v for k, v in headers.items()}
        try:
            j = self._call("POST", "/v1/notifications/verify-webhook-signature", {
                "auth_algo": h["paypal-auth-algo"], "cert_url": h["paypal-cert-url"], "transmission_id": h["paypal-transmission-id"],
                "transmission_sig": h["paypal-transmission-sig"], "transmission_time": h["paypal-transmission-time"],
                "webhook_id": self.webhook_id, "webhook_event": event})
        except (KeyError, PayPalError):
            return False
        return j.get("verification_status") == "SUCCESS"


class MockPayPal:
    """Offline stand-in that follows the same state machine as the sandbox (create -> approve -> capture -> payout)."""
    mode = "mock"
    _ids = itertools.count(1)

    def __init__(self, fail_payout: bool = False):
        self.orders: Dict[str, dict] = {}
        self.fail_payout = fail_payout

    def create_order(self, usd_cents: int, reference: str, description: str) -> dict:
        oid = f"MOCK-ORDER-{uuid.uuid4().hex[:10]}"  # unique across restarts: the DB outlives the in-memory mock
        self.orders[oid] = {"usd_cents": usd_cents, "state": "CREATED"}
        return {"id": oid, "status": "CREATED"}

    def approve(self, order_id: str, approve: bool = True) -> None:  # the buyer's action in the PayPal pop-up
        if order_id not in self.orders:
            raise PayPalError("unknown order", 404)
        self.orders[order_id]["state"] = "APPROVED" if approve else "DECLINED"

    def capture_order(self, order_id: str) -> dict:
        o = self.orders.get(order_id)
        if not o:
            raise PayPalError("unknown order", 404)
        if o["state"] == "COMPLETED":
            return {"status": "COMPLETED", "capture_id": o["capture_id"], "usd_cents": o["usd_cents"], "capture_status": "COMPLETED"}
        if o["state"] != "APPROVED":
            raise PayPalError(f"order is {o['state']}; the buyer has not approved it", 402)
        o["state"], o["capture_id"] = "COMPLETED", f"MOCK-CAP-{uuid.uuid4().hex[:10]}"
        return {"status": "COMPLETED", "capture_id": o["capture_id"], "usd_cents": o["usd_cents"], "capture_status": "COMPLETED"}

    def payout(self, receiver_email: str, usd_cents: int, note: str, batch_id: str) -> dict:
        if self.fail_payout:
            raise PayPalError("simulated payout failure", 502)
        return {"batch_id": f"MOCK-PAYOUT-{batch_id}", "status": "SUCCESS"}

    def verify_webhook(self, headers: Dict[str, str], event: dict) -> bool:
        return {k.lower(): v for k, v in headers.items()}.get("x-mock-signature") == "valid"


_mock = MockPayPal()
_http: Optional[HttpPayPal] = None


def get_paypal() -> PayPal:
    global _http
    assert_sandbox()
    if settings.paypal_client_id and settings.paypal_client_secret:
        if _http is None:
            _http = HttpPayPal(settings.paypal_client_id, settings.paypal_client_secret, settings.paypal_webhook_id)
        return _http
    return _mock
