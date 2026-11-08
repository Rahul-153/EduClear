"""Orders created through PayPal's official MCP server (@paypal/mcp, built on the PayPal Agent Toolkit), D-37.

The agent proposes a booking, the user confirms, and only then does this module ask the MCP server's `create_order` tool for a
sandbox order. Capture and payouts still go through our own PayPal client, so the ledger rules do not change. Returns None
when the server is not available (no Node, no package, tool error) so the caller falls back to the direct REST call."""
import asyncio
import json
import os
import shutil
from pathlib import Path
from typing import List, Optional

from ..config import settings
from .paypal import HttpPayPal

BUNDLED = Path("/opt/mcp/node_modules/@paypal/mcp/dist/index.js")  # installed by the Dockerfile
TOOLS = "orders.create"


def _command() -> Optional[List[str]]:
    node = shutil.which("node")
    if node and BUNDLED.exists():
        return [node, str(BUNDLED), f"--tools={TOOLS}"]
    npx = shutil.which("npx")
    return [npx, "-y", "@paypal/mcp", f"--tools={TOOLS}"] if npx else None


async def _create(cmd: List[str], token: str, usd: str, name: str, return_url: str) -> str:
    from mcp import ClientSession, StdioServerParameters
    from mcp.client.stdio import stdio_client

    env = {**os.environ, "PAYPAL_ACCESS_TOKEN": token, "PAYPAL_ENVIRONMENT": "SANDBOX"}
    async with stdio_client(StdioServerParameters(command=cmd[0], args=cmd[1:], env=env)) as (r, w):
        async with ClientSession(r, w) as session:
            await session.initialize()
            res = await asyncio.wait_for(session.call_tool("create_order", {
                "currencyCode": "USD", "returnUrl": return_url, "cancelUrl": return_url,
                "items": [{"name": name[:120], "quantity": 1, "itemCost": float(usd), "itemTotal": float(usd)}]}), 30)
    if res.is_error:
        raise RuntimeError("MCP create_order returned an error")
    order = json.loads(res.content[0].text)
    return order["id"]


def create_order(pp: object, usd_cents: int, description: str, return_url: str) -> Optional[str]:
    if not settings.paypal_mcp_enabled or not isinstance(pp, HttpPayPal):
        return None  # mock mode has no PayPal account to act on
    cmd = _command()
    if not cmd:
        return None
    try:
        return asyncio.run(_create(cmd, pp._auth(), f"{usd_cents / 100:.2f}", description, return_url))
    except Exception:  # noqa: BLE001 - any MCP failure falls back to the REST client (NFR-04)
        return None
