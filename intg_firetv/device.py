"""
Fire TV device implementation for Unfolded Circle integration.

:copyright: (c) 2025 by Meir Miyara.
:license: MPL-2.0, see LICENSE for more details.
"""

import logging
from ucapi_framework import ExternalClientDevice, DeviceEvents
from intg_firetv.config import FireTVConfig
from intg_firetv.client import FireTVClient

_LOG = logging.getLogger(__name__)


class FireTVDevice(ExternalClientDevice):
    """Fire TV implementation using ExternalClientDevice."""

    def __init__(self, device_config: FireTVConfig, **kwargs):
        super().__init__(device_config, **kwargs)
        self._device_config = device_config
        self._client: FireTVClient | None = None

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

    async def create_client(self) -> FireTVClient:
        """
        Create Fire TV client instance - called by framework.

        Returns:
            FireTVClient instance
        """
        _LOG.info("[%s] Creating Fire TV client", self.log_id)

        self._client = FireTVClient(
            host=self._device_config.host,
            port=self._device_config.port,
            token=self._device_config.token
        )

        return self._client

    async def connect_client(self) -> None:
        """
        Connect to Fire TV device - called by framework after create_client.
        """
        if not self._client:
            raise RuntimeError("Client not created. Call create_client() first.")

        _LOG.info("[%s] Testing connection to Fire TV", self.log_id)
        connected = await self._client.test_connection(max_retries=3, retry_delay=2.0)

        if not connected:
            _LOG.error("[%s] Failed to connect to Fire TV", self.log_id)
            raise ConnectionError(f"Failed to connect to Fire TV at {self.address}")

        _LOG.info("[%s] Successfully connected to Fire TV", self.log_id)
        self.events.emit(DeviceEvents.CONNECTED, self.identifier)

    async def disconnect_client(self) -> None:
        """
        Disconnect from Fire TV - called by framework.
        """
        _LOG.info("[%s] Disconnecting Fire TV client", self.log_id)

        if self._client:
            try:
                await self._client.close()
            except Exception as err:
                _LOG.warning("[%s] Error closing client: %s", self.log_id, err)
            finally:
                self._client = None

        self.events.emit(DeviceEvents.DISCONNECTED, self.identifier)

    def check_client_connected(self) -> bool:
        """
        Check if Fire TV client is connected and responsive.

        Called by ExternalClientDevice watchdog to monitor connection health.
        This enables automatic reconnection if the Fire TV device reboots or
        becomes unreachable.

        Returns:
            True if client exists and session is open, False otherwise
        """
        if not self._client:
            _LOG.debug("[%s] Client is None", self.log_id)
            return False

        if not self._client.session or self._client.session.closed:
            _LOG.debug("[%s] Client session is closed or None", self.log_id)
            return False

        _LOG.debug("[%s] Client is connected", self.log_id)
        return True

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
                        _LOG.info("[%s] Launching app: %s (package: %s)", self.log_id, app_data['name'], package)
                        return await self._client.launch_app(package)

                _LOG.warning("[%s] Unknown app launch command: %s", self.log_id, command)
                return False

            if command.startswith('custom_app:'):
                from intg_firetv.apps import validate_package_name

                package = command.split(':', 1)[1].strip()

                if not validate_package_name(package):
                    _LOG.error("[%s] Invalid package name: %s", self.log_id, package)
                    return False

                _LOG.info("[%s] Launching custom app: %s", self.log_id, package)
                return await self._client.launch_app(package)

            _LOG.warning("[%s] Unknown command: %s", self.log_id, command)
            return False

        except Exception as err:
            _LOG.error("[%s] Error sending command %s: %s", self.log_id, command, err)
            return False
