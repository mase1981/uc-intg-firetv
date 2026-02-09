"""
Fire TV device implementation for Unfolded Circle integration.

:copyright: (c) 2025 by Meir Miyara.
:license: MPL-2.0, see LICENSE for more details.
"""

import asyncio
import logging
from ucapi_framework import PollingDevice, DeviceEvents
from intg_firetv.config import FireTVConfig
from intg_firetv.client import FireTVClient

_LOG = logging.getLogger(__name__)


class FireTVDevice(PollingDevice):
    """Fire TV implementation using PollingDevice for automatic reboot survival."""

    def __init__(self, device_config: FireTVConfig, **kwargs):
        super().__init__(device_config, poll_interval=30, **kwargs)
        self._device_config = device_config
        self._client: FireTVClient | None = None
        self._last_poll_succeeded: bool = False

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
    def client(self) -> FireTVClient | None:
        """Get the Fire TV client."""
        return self._client

    async def establish_connection(self) -> FireTVClient:
        """
        Establish connection to Fire TV device - called by framework on startup.

        Returns:
            FireTVClient instance

        Raises:
            ConnectionError: If connection fails after retries
        """
        _LOG.info("[%s] Establishing connection to Fire TV", self.log_id)

        self._client = FireTVClient(
            host=self._device_config.host,
            port=self._device_config.port,
            token=self._device_config.token
        )

        connected = await self._client.test_connection(max_retries=3, retry_delay=2.0)

        if not connected:
            _LOG.error("[%s] Failed to establish connection to Fire TV", self.log_id)
            raise ConnectionError(f"Failed to connect to Fire TV at {self.address}")

        _LOG.info("[%s] Successfully connected to Fire TV", self.log_id)
        self._state = "connected"
        return self._client

    async def poll_device(self) -> None:
        """
        Poll Fire TV device to test connectivity - called every 30 seconds by framework.

        Creates a new test connection to verify device is reachable.
        If device is offline/rebooted, framework will automatically attempt reconnection.

        After Fire TV reboot, port 8080 service may not be running. We send a wake-up
        command via DIAL protocol (port 8009) to start the service before giving up.
        """
        if not self._client:
            _LOG.debug("[%s] No client, skipping poll", self.log_id)
            return

        try:
            _LOG.debug("[%s] Polling device connectivity", self.log_id)

            test_client = FireTVClient(
                host=self._device_config.host,
                port=self._device_config.port,
                token=self._device_config.token
            )

            connected = await test_client.test_connection(max_retries=1, retry_delay=1.0)

            if not connected and self._last_poll_succeeded:
                _LOG.info("[%s] Connection failed, attempting wake-up via DIAL (port 8009)", self.log_id)
                await test_client.wake_up()
                await asyncio.sleep(3)

                _LOG.info("[%s] Retrying connection after wake-up", self.log_id)
                connected = await test_client.test_connection(max_retries=1, retry_delay=1.0)

            await test_client.close()

            if connected:
                if not self._last_poll_succeeded:
                    _LOG.info("[%s] Device is now reachable", self.log_id)
                    self._last_poll_succeeded = True
                    self.events.emit(DeviceEvents.CONNECTED, self.identifier)
            else:
                if self._last_poll_succeeded:
                    _LOG.warning("[%s] Device is now unreachable (even after wake-up attempt)", self.log_id)
                    self._last_poll_succeeded = False
                    self.events.emit(DeviceEvents.DISCONNECTED, self.identifier)

        except Exception as err:
            _LOG.debug("[%s] Poll error (device likely offline): %s", self.log_id, err)
            if self._last_poll_succeeded:
                _LOG.warning("[%s] Device is now unreachable", self.log_id)
                self._last_poll_succeeded = False
                self.events.emit(DeviceEvents.DISCONNECTED, self.identifier)

    async def send_command(self, command: str) -> bool:
        """
        Send a command to Fire TV remote.

        Args:
            command: Command name (e.g., 'DPAD_UP', 'HOME', etc.)

        Returns:
            True if successful
        """
        if not self._client:
            _LOG.error("[%s] Client not connected", self.log_id)
            return False

        try:
            _LOG.debug("[%s] Sending command: %s", self.log_id, command)

            command_lower = command.lower()
            command_upper = command.upper()

            nav_commands = {
                'dpad_up': self._client.dpad_up,
                'dpad_down': self._client.dpad_down,
                'dpad_left': self._client.dpad_left,
                'dpad_right': self._client.dpad_right,
                'select': self._client.select,
                'home': self._client.home,
                'back': self._client.back,
                'menu': self._client.menu,
                'epg': self._client.epg,
                'volume_up': self._client.volume_up,
                'volume_down': self._client.volume_down,
                'mute': self._client.mute,
                'power': self._client.power,
                'sleep': self._client.sleep,
            }

            if command_lower in nav_commands:
                return await nav_commands[command_lower]()

            media_commands = {
                'play_pause': self._client.play_pause,
                'pause': self._client.pause,
                'fast_forward': self._client.fast_forward,
                'rewind': self._client.rewind,
            }

            if command_lower in media_commands:
                return await media_commands[command_lower]()

            if command.startswith('LAUNCH_'):
                from intg_firetv.apps import FIRE_TV_TOP_APPS

                app_name = command.replace('LAUNCH_', '').lower()

                for app_id, app_data in FIRE_TV_TOP_APPS.items():
                    normalized_name = app_data['name'].upper().replace(' ', '_').replace('+', 'PLUS')
                    if normalized_name == command.replace('LAUNCH_', ''):
                        package = app_data['package']
                        package_name = app_data['name']
                        _LOG.info("[%s] Launching app: %s (package: %s)", self.log_id, package_name, package)
                        return await self._client.launch_app(package)

                _LOG.warning("[%s] Unknown app launch command: %s", self.log_id, command)
                return False

            if command.startswith('text:'):
                send_text = command.split(':', 1)[1].strip()
                _LOG.info("[%s] Sending text: %s", self.log_id, send_text)
                return await self._client.send_keycode(send_text)

            if command.startswith('custom_app:'):
                from intg_firetv.apps import validate_package_name

                package = command.split(':', 1)[1].strip()

                if not validate_package_name(package):
                    _LOG.error("[%s] Invalid package name: %s", self.log_id, package)
                    return False

                _LOG.info("[%s] Launching custom app: %s", self.log_id, package)
                return await self._client.launch_app(package)

            if command.startswith('custom_cmd:'):
                custom_command = command.split(':', 1)[1].strip().lower()
                _LOG.info("[%s] Launching custom command: %s", self.log_id, custom_command)
                return await self._client.send_navigation_command(custom_command)

            _LOG.warning("[%s] Unknown command: %s", self.log_id, command)
            return False

        except Exception as err:
            _LOG.error("[%s] Error sending command %s: %s", self.log_id, command, err)
            return False
