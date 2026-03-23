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
from intg_firetv.helper import get_my_name

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
            token=self._device_config.token,
            long_press_timeout=self._device_config.long_press_timeout
        )

        connected = await self._client.test_connection(max_retries=3, retry_delay=2.0)

        if not connected:
            _LOG.error("[%s] Failed to establish connection to Fire TV", self.log_id)
            raise ConnectionError(f"Failed to connect to Fire TV at {self.address}")

        _LOG.info("[%s] Successfully connected to Fire TV", self.log_id)
        self._state = "ON"
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
            _LOG.debug(f"[{self.log_id},{get_my_name()}] No client, skipping poll")
            return

        try:
            _LOG.debug(f"[{self.log_id},{get_my_name()}] Polling device connectivity")

            test_client = FireTVClient(
                host=self._device_config.host,
                port=self._device_config.port,
                token=self._device_config.token,
                long_press_timeout=self._device_config.long_press_timeout
            )

            connected = await test_client.test_connection(max_retries=1, retry_delay=1.0)

            if not connected and self._last_poll_succeeded:
                _LOG.info(f"[{self.log_id},{get_my_name()}] Connection failed, attempting wake-up via DIAL (port 8009)")
                await test_client.wake_up()
                await asyncio.sleep(3)

                _LOG.info(f"[{self.log_id},{get_my_name()}] Retrying connection after wake-up")
                connected = await test_client.test_connection(max_retries=1, retry_delay=1.0)

            await test_client.close()

            if connected:
                if self._client:
                    self._client.keep_alive()
                if not self._last_poll_succeeded:
                    _LOG.info(f"[{self.log_id},{get_my_name()}] Device is now reachable")
                    self._last_poll_succeeded = True
                    self.events.emit(DeviceEvents.CONNECTED, self.identifier)
            else:
                if self._last_poll_succeeded:
                    _LOG.warning(f"[{self.log_id},{get_my_name()}] Device is now unreachable (even after wake-up attempt)")
                    self._last_poll_succeeded = False
                    self.events.emit(DeviceEvents.DISCONNECTED, self.identifier)

        except Exception as err:
            _LOG.debug(f"[{self.log_id},{get_my_name()}] Poll error (device likely offline): {err}")
            if self._last_poll_succeeded:
                _LOG.warning("[%s] Device is now unreachable", self.log_id)
                self._last_poll_succeeded = False
                self.events.emit(DeviceEvents.DISCONNECTED, self.identifier)

    async def send_command(self, command: str, long_key_press: bool = False) -> bool:
        """
        Send a command to Fire TV remote.

        Args:
            command: Command name (e.g., 'DPAD_UP', 'HOME', etc.)

        Returns:
            True if successful
        """
        if not self._client:
            _LOG.error(f"[{self.log_id},{get_my_name()}] Client not connected")
            return False

        try:
            _LOG.debug(f"[{self.log_id},{get_my_name()}] Sending command: {command}")

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
                'backspace': self._client.backspace,
                'menu': self._client.menu,
                'epg': self._client.epg,
                'volume_up': self._client.volume_up,
                'volume_down': self._client.volume_down,
                'mute': self._client.mute,
                'power': self._client.power,
                'sleep': self._client.sleep,
            }

            if command_lower in nav_commands:
                return await nav_commands[command_lower](long_key_press)

            media_commands = {
                'play_pause': self._client.play_pause,
                'pause': self._client.pause,
                'fast_forward': self._client.fast_forward,
                'rewind': self._client.rewind,
            }

            if command_lower in media_commands:
                return await media_commands[command_lower](long_key_press)

            if command.startswith('LAUNCH_') or command == "SETTINGS":
                from intg_firetv.apps import FIRE_TV_TOP_APPS

                app_name = command.replace('LAUNCH_', '').lower()

                for app_id, app_data in FIRE_TV_TOP_APPS.items():
                    normalized_name = app_data['name'].upper().replace(' ', '_').replace('+', 'PLUS')
                    if normalized_name == command.replace('LAUNCH_', ''):
                        package = app_data['package']
                        package_name = app_data['name']
                        _LOG.info(f"[{self.log_id},{get_my_name()}] Launching app: {package_name} (package: {package})")
                        return await self._client.launch_app(package)

                _LOG.warning(f"[{self.log_id},{get_my_name()}] Unknown app launch command: {command}")
                return False

            number_commands = ["1","2","3","4","5","6","7","8","9","0"]

            if command.startswith('text:') or command in number_commands:
                if command in number_commands:
                    send_text = command
                else:
                    send_text = command.split(':', 1)[1].strip()
                _LOG.info(f"[{self.log_id},{get_my_name()}] Sending text: {send_text}")
                return await self._client.send_text(send_text)

            if command.startswith('custom_app:'):
                from intg_firetv.apps import validate_package_name

                package = command.split(':', 1)[1].strip()

                if not validate_package_name(package):
                    _LOG.error(f"[{self.log_id},{get_my_name()}] Invalid package name: {package}")
                    return False

                _LOG.info(f"[{self.log_id},{get_my_name()}] Launching custom app: {package}")
                return await self._client.launch_app(package)

            if command.startswith('custom_cmd:'):
                custom_command = command.split(':', 1)[1].strip().lower()
                _LOG.info(f"[{self.log_id},{get_my_name()}] Launching custom command: {command}")
                return await self._client.send_navigation_command(custom_command,long_key_press)

            _LOG.warning(f"[{self.log_id},{get_my_name()}] Unknown command: {command}")
            return False

        except Exception as err:
            _LOG.error(f"[{self.log_id},{get_my_name()}] Error sending command {command}: {err}")
            return False
