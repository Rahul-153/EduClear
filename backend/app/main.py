from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles

from .config import ROOT

from .db import init_db
from .integrations.paypal import assert_sandbox
from .routers.api import router
from .routers.agent import router as agent_router
from .routers.payments import router as payments_router


@asynccontextmanager
async def lifespan(_: FastAPI):
    assert_sandbox()  # refuse to start unless PAYPAL_ENV=sandbox (NFR-05)
    init_db()
    yield


app = FastAPI(title="EduClear API", version="0.1.0", lifespan=lifespan)
app.include_router(router)
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
