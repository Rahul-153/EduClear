"""Manual PayPal SANDBOX walkthrough (needs sandbox keys in .env). Never touches live PayPal.

  python scripts/paypal_sandbox_smoke.py order            # create a $29.99 order, print the buyer approval URL
  python scripts/paypal_sandbox_smoke.py capture ORDER_ID # after approving with the sandbox Personal account
  python scripts/paypal_sandbox_smoke.py payout           # send $1.00 to PAYPAL_COUNSELLOR_PAYOUT_EMAIL
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
import httpx  # noqa: E402

from backend.app.config import settings  # noqa: E402
from backend.app.integrations.paypal import SANDBOX_BASE, HttpPayPal, assert_sandbox  # noqa: E402

assert_sandbox()
if not (settings.paypal_client_id and settings.paypal_client_secret):
    sys.exit("Set PAYPAL_CLIENT_ID and PAYPAL_CLIENT_SECRET (sandbox) in .env first.")
pp = HttpPayPal(settings.paypal_client_id, settings.paypal_client_secret, settings.paypal_webhook_id)
step = sys.argv[1] if len(sys.argv) > 1 else "order"
if step == "order":
    j = pp._call("POST", "/v2/checkout/orders", {"intent": "CAPTURE", "purchase_units": [{"reference_id": "smoke", "amount": {"currency_code": "USD", "value": "29.99"}}]})
    print("order", j["id"], j["status"])
    print("approve at:", next(l["href"] for l in j["links"] if l["rel"] in ("approve", "payer-action")))
elif step == "capture":
    print(pp.capture_order(sys.argv[2]))
elif step == "payout":
    if not settings.paypal_counsellor_payout_email:
        sys.exit("Set PAYPAL_COUNSELLOR_PAYOUT_EMAIL (a sandbox Personal account) in .env first.")
    print(pp.payout(settings.paypal_counsellor_payout_email, 100, "EduClear smoke payout", "smoke-" + str(abs(hash(sys.argv))) ))
else:
    sys.exit(__doc__)
print("base:", SANDBOX_BASE)
