"""
Fire TV setup flow for Unfolded Circle integration.

:copyright: (c) 2025 by Meir Miyara.
:license: MPL-2.0, see LICENSE for more details.
"""

import asyncio
import logging
from typing import Any
from ucapi import RequestUserInput, IntegrationSetupError
from ucapi_framework import BaseSetupFlow
from intg_firetv.config import FireTVConfig
from intg_firetv.client import FireTVClient

_LOG = logging.getLogger(__name__)


class FireTVSetupFlow(BaseSetupFlow[FireTVConfig]):
    """Setup flow for Fire TV integration with PIN authentication."""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._temp_host: str | None = None
        self._temp_port: int = 8080

    def get_manual_entry_form(self) -> RequestUserInput:
        """Define manual entry fields for Fire TV setup."""
        return RequestUserInput(
            {"en": "Fire TV Setup"},
            [
                {
                    "id": "name",
                    "label": {"en": "Device Name"},
                    "field": {"text": {"value": "Fire TV"}},
                },
                {
                    "id": "host",
                    "label": {"en": "IP Address"},
                    "field": {"text": {"value": ""}},
                },
                {
                    "id": "port",
                    "label": {"en": "Port (default: 8080)"},
                    "field": {"text": {"value": "8080"}},
                },
            ]
        )

    async def query_device(
        self, input_values: dict[str, Any]
    ) -> FireTVConfig | RequestUserInput:
        """
        Step 1: Validate connection and request PIN from Fire TV.
        Step 2: Verify PIN and create config.
        """
        # Check if this is the PIN verification step
        if "pin" in input_values and self._temp_host:
            return await self._verify_pin_step(input_values)

        # This is the initial connection step
        return await self._initial_connection_step(input_values)

    async def _initial_connection_step(
        self, input_values: dict[str, Any]
    ) -> RequestUserInput:
        """
        Step 1: Test connection and request PIN display on Fire TV screen.
        """
        host = input_values.get("host", "").strip()
        if not host:
            raise ValueError("IP address is required")

        try:
            port = int(input_values.get("port", 8080))
        except ValueError:
            raise ValueError("Port must be a number") from None

        # Store temporarily for next step
        self._temp_host = host
        self._temp_port = port

        _LOG.info("Step 1: Testing connection to Fire TV at %s:%d", host, port)

        # Create temporary client for setup
        client = FireTVClient(host, port)

        try:
            # Wake up device first
            _LOG.info("Sending wake-up command to Fire TV")
            await client.wake_up()
            await asyncio.sleep(3)

            # Test connection
            _LOG.info("Testing connection to Fire TV")
            connected = await client.test_connection(max_retries=3, retry_delay=3.0)

            if not connected:
                await client.close()
                raise ValueError(
                    f"Cannot reach Fire TV at {host}:{port}\n\n"
                    "Troubleshooting:\n"
                    "1. Ensure Fire TV is powered on\n"
                    "2. Verify IP address is correct\n"
                    "3. Try different port (8080, 8009, 8443)\n"
                    "4. Check network/firewall allows connection"
                )

            _LOG.info("Connection successful to Fire TV")

            # Request PIN display on TV screen
            _LOG.info("Step 2: Requesting PIN display on Fire TV screen")
            pin_requested = await client.request_pin("UC Remote")

            await client.close()

            if not pin_requested:
                raise ValueError(
                    "Failed to request PIN display on Fire TV.\n"
                    "Please ensure Fire TV is powered on and accessible."
                )

            _LOG.info("PIN display request successful")

            # Return PIN entry form
            return RequestUserInput(
                {"en": "Enter PIN from Fire TV"},
                [
                    {
                        "id": "pin",
                        "label": {"en": "4-Digit PIN (shown on TV screen)"},
                        "field": {
                            "text": {
                                "value": ""
                            }
                        }
                    }
                ]
            )

        except Exception as err:
            await client.close()
            self._temp_host = None
            self._temp_port = 8080
            raise ValueError(f"Setup failed: {err}") from err

    async def _verify_pin_step(
        self, input_values: dict[str, Any]
    ) -> FireTVConfig:
        """
        Step 2: Verify PIN and obtain authentication token.
        """
        pin = input_values.get("pin", "").strip()

        if not pin:
            raise ValueError("PIN is required")

        if not self._temp_host:
            raise ValueError("Setup flow error: no host stored from previous step")

        host = self._temp_host
        port = self._temp_port
        name = input_values.get("name", f"Fire TV ({host})").strip()

        _LOG.info("Step 3: Verifying PIN '%s' with Fire TV", pin)

        # Create temporary client for PIN verification
        client = FireTVClient(host, port)

        try:
            # Verify PIN and get token
            token = await client.verify_pin(pin)

            await client.close()

            if not token:
                raise ValueError(
                    "PIN verification failed.\n"
                    "Please check the PIN on your TV screen and try again."
                )

            _LOG.info("PIN verified successfully, token obtained")

            # Clear temporary data
            self._temp_host = None
            self._temp_port = 8080

            # Create configuration
            config = FireTVConfig(
                identifier=f"firetv_{host.replace('.', '_')}_{port}",
                name=name,
                host=host,
                port=port,
                token=token
            )

            _LOG.info("Setup completed successfully for %s", name)

            return config

        except Exception as err:
            await client.close()
            self._temp_host = None
            self._temp_port = 8080
            raise ValueError(f"PIN verification failed: {err}") from err
