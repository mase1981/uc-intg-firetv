"""
Fire TV simulator for testing without actual hardware.
This file remains local only - not pushed to repository.

:copyright: (c) 2025 by Meir Miyara.
:license: MPL-2.0, see LICENSE for more details.
"""

import asyncio
import logging
from aiohttp import web
import secrets

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s | %(levelname)-8s | %(message)s'
)
_LOG = logging.getLogger(__name__)

# Simulator state
STATE = {
    "pin_request_active": False,
    "current_pin": None,
    "authenticated_tokens": {},
}


async def handle_root(request):
    """Handle root endpoint."""
    return web.Response(text="Fire TV Simulator", status=200)


async def handle_wake(request):
    """Handle wake-up endpoint."""
    _LOG.info("Wake-up request received")
    return web.Response(status=200)


async def handle_pin_display(request):
    """Handle PIN display request."""
    try:
        data = await request.json()
        friendly_name = data.get("friendlyName", "Unknown")

        # Generate 4-digit PIN
        pin = f"{secrets.randbelow(10000):04d}"
        STATE["current_pin"] = pin
        STATE["pin_request_active"] = True

        _LOG.info("=" * 60)
        _LOG.info("PIN DISPLAY REQUEST")
        _LOG.info(f"From: {friendly_name}")
        _LOG.info(f"PIN: {pin}")
        _LOG.info("=" * 60)

        return web.json_response({"status": "success"}, status=200)

    except Exception as e:
        _LOG.error(f"Error in PIN display: {e}")
        return web.Response(status=500)


async def handle_pin_verify(request):
    """Handle PIN verification."""
    try:
        data = await request.json()
        pin = data.get("pin")

        if not STATE["pin_request_active"]:
            _LOG.error("No active PIN request")
            return web.Response(status=400)

        if pin != STATE["current_pin"]:
            _LOG.error(f"Invalid PIN: {pin} (expected: {STATE['current_pin']})")
            return web.Response(status=403)

        # Generate authentication token
        token = secrets.token_hex(32)
        STATE["authenticated_tokens"][token] = True
        STATE["pin_request_active"] = False

        _LOG.info("=" * 60)
        _LOG.info("PIN VERIFIED SUCCESSFULLY")
        _LOG.info(f"Token: {token}")
        _LOG.info("=" * 60)

        return web.json_response({"description": token}, status=200)

    except Exception as e:
        _LOG.error(f"Error in PIN verify: {e}")
        return web.Response(status=500)


async def handle_navigation_command(request):
    """Handle navigation command."""
    action = request.query.get("action", "unknown")

    # Verify token
    token = request.headers.get("X-Client-Token")
    if not token or token not in STATE["authenticated_tokens"]:
        _LOG.error(f"Unauthorized command: {action}")
        return web.Response(status=401)

    _LOG.info(f"Navigation command: {action}")
    return web.Response(status=200)


async def handle_media_command(request):
    """Handle media command."""
    action = request.query.get("action", "unknown")

    # Verify token
    token = request.headers.get("X-Client-Token")
    if not token or token not in STATE["authenticated_tokens"]:
        _LOG.error(f"Unauthorized command: {action}")
        return web.Response(status=401)

    _LOG.info(f"Media command: {action}")
    return web.Response(status=200)


async def handle_app_launch(request):
    """Handle app launch."""
    package = request.match_info.get("package", "unknown")

    # Verify token
    token = request.headers.get("X-Client-Token")
    if not token or token not in STATE["authenticated_tokens"]:
        _LOG.error(f"Unauthorized app launch: {package}")
        return web.Response(status=401)

    _LOG.info(f"Launching app: {package}")
    return web.Response(status=200)


async def main():
    """Start the Fire TV simulator."""
    app = web.Application()

    # Routes
    app.router.add_get("/", handle_root)
    app.router.add_post("/apps/FireTVRemote", handle_wake)
    app.router.add_post("/v1/FireTV/pin/display", handle_pin_display)
    app.router.add_post("/v1/FireTV/pin/verify", handle_pin_verify)
    app.router.add_post("/v1/FireTV", handle_navigation_command)
    app.router.add_post("/v1/media", handle_media_command)
    app.router.add_post("/v1/FireTV/app/{package:.*}", handle_app_launch)

    _LOG.info("=" * 60)
    _LOG.info("FIRE TV SIMULATOR STARTING")
    _LOG.info("Listening on all network interfaces (0.0.0.0:8080)")
    _LOG.info("Access from network: http://10.2.9.118:8080")
    _LOG.info("Access from localhost: http://localhost:8080")
    _LOG.info("=" * 60)

    runner = web.AppRunner(app)
    await runner.setup()
    site = web.TCPSite(runner, '0.0.0.0', 8080)
    await site.start()

    _LOG.info("Simulator ready for connections from Remote")
    _LOG.info("Configure integration with IP: 10.2.9.118, Port: 8080")

    # Keep running
    await asyncio.Future()


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        _LOG.info("Simulator stopped by user")
