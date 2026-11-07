import { useEffect, useRef, useState } from "react";
import { captureBooking, cancelBooking, mockApprove, type BookingView, type PayConfig } from "../api";

interface Props { booking: BookingView; cfg: PayConfig; onChange: (b: BookingView | null) => void; payLaterHint?: string }

/* Mock mode simulates the buyer's action in the PayPal pop-up. Live-sandbox mode loads PayPal JS SDK v6 and uses the
   real <paypal-button> / <paypal-pay-later-button> components against the sandbox. */
export default function CheckoutPanel({ booking, cfg, onChange, payLaterHint }: Props) {
  const [msg, setMsg] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);
  const host = useRef<HTMLDivElement>(null);

  const run = async (fn: () => Promise<BookingView | void>) => {
    setBusy(true); setMsg(null);
    try { const r = await fn(); if (r) onChange(r); } catch (e) { setMsg((e as Error).message); } finally { setBusy(false); }
  };

  useEffect(() => {
    if (cfg.mode !== "live-sandbox" || !cfg.client_id || !host.current) return;
    let dead = false;
    (async () => {
      try {
        const { loadCoreSdkScript } = await import("@paypal/paypal-js/sdk-v6");
        const paypal = await loadCoreSdkScript({ environment: "sandbox" });
        if (!paypal || dead) return;
        const sdk = await paypal.createInstance({ clientId: cfg.client_id!, components: ["paypal-payments"], pageType: "checkout" });
        const eligible = await sdk.findEligibleMethods({ currencyCode: "USD" });
        const opts = { onApprove: async () => { await run(() => captureBooking(booking.id)); },
          onCancel: () => setMsg("Payment cancelled."), onError: () => setMsg("PayPal reported an error. Nothing was charged.") };
        const mount = (el: HTMLElement, start: () => void) => { el.addEventListener("click", start); host.current?.appendChild(el); };
        host.current!.innerHTML = "";
        if (eligible.isEligible("paypal")) {
          const s = sdk.createPayPalOneTimePaymentSession(opts);
          mount(document.createElement("paypal-button"), () => s.start({ presentationMode: "auto" }, Promise.resolve({ orderId: booking.paypal_order_id })));
        }
        if (eligible.isEligible("paylater")) {
          const d = eligible.getDetails("paylater") as { countryCode?: "US"; productCode?: "PAYLATER" | "PAY_LATER_SHORT_TERM" };
          const s = sdk.createPayLaterOneTimePaymentSession(opts);
          const el = document.createElement("paypal-pay-later-button");
          el.countryCode = d.countryCode; el.productCode = d.productCode;
          mount(el, () => s.start({ presentationMode: "auto" }, Promise.resolve({ orderId: booking.paypal_order_id })));
        }
      } catch { if (!dead) setMsg("PayPal sandbox could not be loaded."); }
    })();
    return () => { dead = true; };
  }, [booking.id, cfg.mode, cfg.client_id]);

  return (
    <div className="card" style={{ boxShadow: "none", marginTop: 12, background: "#f8fafc" }} aria-live="polite">
      <div className="label">Checkout — PayPal sandbox ({cfg.mode === "mock" ? "simulated" : "live sandbox"})</div>
      <div className="row"><span>{booking.title}</span><span className="num value">₹{booking.amount_inr.toLocaleString("en-IN")} ≈ ${booking.usd}</span></div>
      <p className="note">{cfg.currency_note}</p>
      {payLaterHint && <p className="note">{payLaterHint}</p>}
      {cfg.mode === "mock" ? (
        <div style={{ display: "flex", gap: 8, flexWrap: "wrap" }}>
          <button disabled={busy} className="capsule" style={{ padding: "8px 16px", background: "#FFC439", border: 0, fontWeight: 600 }}
            onClick={() => run(async () => { await mockApprove(booking.id, true); return captureBooking(booking.id); })}>Approve with PayPal (simulated)</button>
          <button disabled={busy} className="link" onClick={() => run(async () => { await mockApprove(booking.id, false); await captureBooking(booking.id); })}>Simulate decline</button>
          <button disabled={busy} className="link" onClick={() => run(async () => { const b = await cancelBooking(booking.id); onChange(null); return b; })}>Cancel</button>
        </div>
      ) : <div ref={host} style={{ display: "flex", gap: 8, flexWrap: "wrap", minHeight: 44 }} />}
      {msg && <p role="alert" className="note" style={{ color: "var(--amber)" }}>{msg}</p>}
    </div>
  );
}
