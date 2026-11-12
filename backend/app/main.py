from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles

from .config import ROOT, settings

from .db import init_db
from .integrations.paypal import assert_sandbox
from .auth.deps import SESSION_COOKIE
from .routers.api import router
from .routers.auth import router as auth_router
from .routers.agent import router as agent_router
from .routers.payments import router as payments_router


@asynccontextmanager
async def lifespan(_: FastAPI):
    assert_sandbox()  # refuse to start unless PAYPAL_ENV=sandbox (NFR-05)
    if settings.env == "production" and not settings.auth_secret:
        raise RuntimeError("AUTH_SECRET must be set when ENV=production (it keys sign-in codes and invite codes).")
    init_db()
    yield


app = FastAPI(title="EduClear API", version="0.1.0", lifespan=lifespan)


@app.middleware("http")
async def csrf_guard(request: Request, call_next):
    """A cookie session needs the custom header on writes (a cross-site form cannot set it). Webhooks are signature-verified instead."""
    p = request.url.path
    if request.method in ("POST", "PUT", "PATCH", "DELETE") and p.startswith("/api/") and not p.startswith("/api/webhooks/") \
            and SESSION_COOKIE in request.cookies and request.headers.get("x-requested-with") != "educlear":
        return JSONResponse({"detail": "Missing X-Requested-With header."}, status_code=403)
    return await call_next(request)


app.include_router(router)
app.include_router(auth_router)
app.include_router(payments_router)
app.include_router(agent_router)



class WebFiles(StaticFiles):
    """Hashed bundles never change, so cache them hard; index.html must always be re-checked or a returning visitor keeps the old build."""
    async def get_response(self, path, scope):
        r = await super().get_response(path, scope)
        r.headers["Cache-Control"] = "public, max-age=31536000, immutable" if path.startswith("assets/") else "no-cache"
        return r


_dist = ROOT / "frontend" / "dist"
if _dist.exists():  # production / demo: serve the built React app from the same service
    app.mount("/", WebFiles(directory=_dist, html=True), name="web")
