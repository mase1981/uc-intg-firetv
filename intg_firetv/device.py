"""
Fire TV device implementation for Unfolded Circle integration.

:copyright: (c) 2025 by Meir Miyara.
:license: MPL-2.0, see LICENSE for more details.
"""

import asyncio
import logging
import time

from ucapi_framework import PollingDevice

from intg_firetv.client import FireTVClient
from intg_firetv.commandcontext import get_context
from intg_firetv.config import FireTVConfig
from intg_firetv.helper import get_my_name

_LOG = logging.getLogger(__name__)

WAKE_THROTTLE_SEC = 60.0


class FireTVDevice(PollingDevice):
    """Fire TV implementation using PollingDevice for automatic reboot survival."""

    def __init__(self, device_config: FireTVConfig, **kwargs):
        super().__init__(device_config, poll_interval=30, **kwargs)
        self._device_config = device_config
        self._client: FireTVClient | None = None
        self._connect_lock: asyncio.Lock = asyncio.Lock()
        self._state: str = "UNKNOWN"
        self._last_wake_attempt: float = 0.0

    @property
    def identifier(self) -> str:
        return self._device_config.identifier

    @property
    def name(self) -> str:
        return self._device_config.name

    @property
    def address(self) -> str:
        return self._device_config.host

    @property
    def log_id(self) -> str:
        return f"{self.name} ({self.address})"

    @property
    def state(self) -> str:
        return self._state

    @property
    def client(self) -> FireTVClient | None:
        return self._client

    def _create_client(self) -> FireTVClient:
        return FireTVClient(
            host=self._device_config.host,
            port=self._device_config.port,
            token=self._device_config.token,
            long_press_timeout=self._device_config.long_press_timeout,
        )

    async def _get_client(self) -> FireTVClient:
        """Return the single shared client, creating it once if needed (rule 9/10)."""
        async with self._connect_lock:
            if self._client is None:
                self._client = self._create_client()
            return self._client

    async def _probe(self, client: FireTVClient, wake: bool) -> bool:
        """
        Test connectivity. If unreachable and ``wake`` is allowed, send a DIAL
        wake-up (port 8009) to start the Fire TV REST service and re-test.

        The wake-up is the key to recovering after a power-off/power-on cycle:
        a freshly powered Fire TV may have the port 8080 REST service stopped
        until kicked via DIAL.
        """
        if await client.test_connection(max_retries=1, retry_delay=1.0):
            return True

        if not wake:
            return False

        now = time.monotonic()
        if now - self._last_wake_attempt < WAKE_THROTTLE_SEC:
            return False

        self._last_wake_attempt = now
        _LOG.info("[%s] Unreachable, sending wake-up via DIAL (port 8009)", self.log_id)
        await client.wake_up()
        await asyncio.sleep(3)
        return await client.test_connection(max_retries=2, retry_delay=2.0)

    async def establish_connection(self) -> FireTVClient:
        """
        Establish connection to Fire TV - called by framework on startup.

        Follows the TV-off pattern: a Fire TV the user has powered off is not a
        failure. We never raise here (that would mark the device unavailable and
        prevent power-on); instead we report OFF and let polling recover.
        """
        _LOG.info("[%s] Establishing connection to Fire TV", self.log_id)
        client = await self._get_client()

        if await self._probe(client, wake=True):
            self._state = "ON"
            _LOG.info("[%s] Successfully connected to Fire TV", self.log_id)
        else:
            self._state = "OFF"
            _LOG.info("[%s] Fire TV not reachable (assuming powered off)", self.log_id)

        return client

    async def poll_device(self) -> None:
        """
        Poll Fire TV connectivity every 30 seconds, reusing the shared client.

        On every failed probe a DIAL wake-up is attempted (throttled) regardless
        of the previous poll result, so the integration recovers after the device
        is powered back on. State is reported as ON/OFF and pushed to entities;
        we never emit DISCONNECTED (TV-off pattern) so entities stay available and
        the user can power the device back on.
        """
        client = await self._get_client()

        try:
            connected = await self._probe(client, wake=True)
        except Exception as err:
            _LOG.debug(f"[{self.log_id},{get_my_name()}] Poll error: {err}")
            connected = False

        if connected:
            client.keep_alive()
            if self._state != "ON":
                _LOG.info(f"[{self.log_id},{get_my_name()}] Device is now reachable")
                self._state = "ON"
                self.push_update()
        else:
            if self._state != "OFF":
                _LOG.info(f"[{self.log_id},{get_my_name()}] Device is now powered off / unreachable")
                self._state = "OFF"
                self.push_update()

    async def power_on(self) -> bool:
        """Wake the Fire TV via DIAL - always works regardless of connection state."""
        client = await self._get_client()
        self._last_wake_attempt = time.monotonic()
        await client.wake_up()
        return True

    async def power_off(self) -> bool:
        """Put the Fire TV to sleep."""
        client = await self._get_client()
        return await client.send_navigation_command("sleep")

    async def disconnect(self) -> None:
        async with self._connect_lock:
            if self._client:
                await self._client.close()
                self._client = None
        self._state = "UNAVAILABLE"
        await super().disconnect()

    async def send_command(self, command: str) -> bool:
        """
        Send a command to Fire TV remote.

        Args:
            command: Command name (e.g., 'DPAD_UP', 'HOME', etc.)

        Returns:
            True if successful
        """
        client = await self._get_client()

        try:
            _LOG.debug(f"[{self.log_id},{get_my_name()}] Sending command: {command}")

            command_lower = command.lower()

            if command_lower in ("power_on", "on"):
                return await self.power_on()
            if command_lower in ("power_off", "off"):
                return await self.power_off()

            nav_commands = ['dpad_up','dpad_down','dpad_left','dpad_right','select','home','back','backspace','menu','epg','volume_up','volume_down','mute','power','sleep']

            if command_lower in nav_commands:
                return await client.send_navigation_command(command_lower)

            if command_lower == "settings":
                # settings key is just an alias for holding the home button longer
                command_ctx = get_context()
                command_ctx.hold = 400
                return await client.send_navigation_command('home')

            media_commands = {
                'play_pause': client.play_pause,
                'pause': client.pause,
                'fast_forward': client.fast_forward,
                'rewind': client.rewind,
            }

            if command_lower in media_commands:
                return await media_commands[command_lower]()

            if command.startswith('LAUNCH_'):
                from intg_firetv.apps import FIRE_TV_TOP_APPS

                for app_id, app_data in FIRE_TV_TOP_APPS.items():
                    normalized_name = app_data['name'].upper().replace(' ', '_').replace('+', 'PLUS')
                    if normalized_name == command.replace('LAUNCH_', ''):
                        package = app_data['package']
                        package_name = app_data['name']
                        _LOG.info(f"[{self.log_id},{get_my_name()}] Launching app: {package_name} (package: {package})")
                        return await client.launch_app(package)

                _LOG.warning(f"[{self.log_id},{get_my_name()}] Unknown app launch command: {command}")
                return False

            number_commands = ["1","2","3","4","5","6","7","8","9","0"]

            if command.startswith('text:') or command in number_commands:
                if command in number_commands:
                    send_text = command
                else:
                    send_text = command.split(':', 1)[1].strip()
                _LOG.info(f"[{self.log_id},{get_my_name()}] Sending text: {send_text}")
                return await client.send_text(send_text)

            if command.startswith('custom_app:'):
                from intg_firetv.apps import validate_package_name

                package = command.split(':', 1)[1].strip()

                if not validate_package_name(package):
                    _LOG.error(f"[{self.log_id},{get_my_name()}] Invalid package name: {package}")
                    return False

                _LOG.info(f"[{self.log_id},{get_my_name()}] Launching custom app: {package}")
                return await client.launch_app(package)

            if command.startswith('custom_cmd:'):
                custom_command = command.split(':', 1)[1].strip().lower()
                _LOG.info(f"[{self.log_id},{get_my_name()}] Launching custom command: {command}")
                return await client.send_navigation_command(custom_command)

            _LOG.warning(f"[{self.log_id},{get_my_name()}] Unknown command: {command}")
            return False

        except Exception as err:
            _LOG.error(f"[{self.log_id},{get_my_name()}] Error sending command {command}: {err}")
            return False
