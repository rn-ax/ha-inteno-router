"""Thin async client for the router's ubus-over-websocket API.

The router (Inteno/IOPSYS, JUCI web UI) exposes ubus over a websocket at
`/ubus` using the `ubus-json` subprotocol (found in the JUCI frontend's
`01-juci.js`: `new WebSocket(host, "ubus-json")`) — there is no plain HTTP
JSON-RPC fallback. See the `inteno-router` skill for the full confirmed
ACL and example responses this was validated against.
"""

from __future__ import annotations

import json
from typing import Any

import websockets

# ubus's convention for "no session yet" on the initial login call.
_NULL_SESSION = "0" * 32


class UbusAuthError(Exception):
    """Raised when login fails (wrong credentials, or ubus returned an error code)."""


class UbusClient:
    """One-shot ubus client: connect, log in, make calls, disconnect.

    ubus sessions expire in ~300s server-side, so this intentionally
    doesn't try to keep a session alive across calls spanning a long
    period — construct a fresh client (or call `login` again) each poll
    cycle instead of assuming a session persists.
    """

    def __init__(self, host: str, username: str, password: str) -> None:
        self._uri = f"ws://{host}/ubus"
        self._username = username
        self._password = password
        self._session: str | None = None

    async def _call(self, ws, obj: str, method: str, args: dict | None = None) -> Any:
        session = self._session or _NULL_SESSION
        request = {
            "jsonrpc": "2.0",
            "id": 1,
            "method": "call",
            "params": [session, obj, method, args or {}],
        }
        await ws.send(json.dumps(request))
        raw = await ws.recv()
        response = json.loads(raw)
        if "error" in response:
            raise UbusAuthError(f"ubus error calling {obj}.{method}: {response['error']}")
        result = response["result"]
        # ubus wraps every result as [status_code, payload]; 0 is success.
        status, payload = result[0], (result[1] if len(result) > 1 else {})
        if status != 0:
            raise UbusAuthError(f"ubus {obj}.{method} returned status {status}")
        return payload

    async def login(self, ws) -> None:
        """Authenticate and store the session token for subsequent calls on this ws."""
        payload = await self._call(
            ws, "session", "login",
            {"username": self._username, "password": self._password},
        )
        self._session = payload["ubus_rpc_session"]

    async def fetch(self, calls: list[tuple[str, str]]) -> dict[tuple[str, str], Any]:
        """Open one websocket, log in, and make several calls in one round trip.

        `calls` is a list of (object, method) pairs with no arguments — the
        common case for this integration's polling. Returns a dict keyed by
        the same (object, method) pairs.
        """
        results: dict[tuple[str, str], Any] = {}
        async with websockets.connect(self._uri, subprotocols=["ubus-json"]) as ws:
            await self.login(ws)
            for obj, method in calls:
                results[(obj, method)] = await self._call(ws, obj, method)
        return results

    async def call(self, obj: str, method: str, args: dict | None = None) -> Any:
        """Open one websocket, log in, and make a single call — for actions
        (reboot, etc.) rather than the batched reads `fetch` is for.
        """
        async with websockets.connect(self._uri, subprotocols=["ubus-json"]) as ws:
            await self.login(ws)
            return await self._call(ws, obj, method, args)
