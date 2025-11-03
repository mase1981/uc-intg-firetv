"""
Fire TV REST API Client Implementation.

:copyright: (c) 2025 by Meir Miyara.
:license: MIT, see LICENSE for more details.
"""

import asyncio
import json
import logging
import ssl
from typing import Optional

import aiohttp
import certifi

_LOG = logging.getLogger(__name__)


class FireTVClient:
    def __init__(self, host: str, token: Optional[str] = None):
        self.host = host
        self.token = token
        self.api_key = "0987654321"  # Standard Fire TV API key
        self.session: Optional[aiohttp.ClientSession] = None
        if host.lower() in ['localhost', '127.0.0.1', '0.0.0.0']:
            protocol = "http"
            self._use_https = False
            _LOG.info("Using HTTP for simulator/localhost")
        else:
            protocol = "https"
            self._use_https = True
            _LOG.info("Using HTTPS for Fire TV device")
        
        self._base_url = f"{protocol}://{self.host}:8080"

    async def __aenter__(self):
        """Async context manager entry."""
        await self._ensure_session()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit."""
        await self.close()

    async def _ensure_session(self):
        """Ensure HTTP session is available."""
        if self.session is None or self.session.closed:
            if self._use_https:
                ssl_context = ssl.create_default_context(cafile=certifi.where())
                ssl_context.check_hostname = False
                ssl_context.verify_mode = ssl.CERT_NONE
                
                connector = aiohttp.TCPConnector(ssl=ssl_context)
                _LOG.debug("Created HTTPS connector with SSL verification disabled")
            else:
                connector = aiohttp.TCPConnector()
                _LOG.debug("Created HTTP connector")
            
            self.session = aiohttp.ClientSession(
                connector=connector,
                timeout=aiohttp.ClientTimeout(total=10)
            )
            _LOG.debug("HTTP session created for %s (%s)", self.host, 
                      "HTTPS" if self._use_https else "HTTP")

    async def close(self):
        """Close HTTP session."""
        if self.session and not self.session.closed:
            await self.session.close()
            _LOG.debug("HTTP session closed")

    def _get_headers(self, include_token: bool = True) -> dict:
        headers = {
            "X-Api-Key": self.api_key,
            "Content-Type": "application/json",
            "User-Agent": "okhttp/4.10.0",
        }
        
        if include_token and self.token:
            headers["X-Client-Token"] = self.token
        
        return headers

    async def request_pin(self, friendly_name: str = "UC Remote", max_retries: int = 4, retry_delay: float = 3.0) -> Optional[str]:
        """
        Request PIN display from Fire TV with retry logic.
        
        Fire TV Cube may return success (200) but PIN=None initially,
        then the PIN becomes available after a few seconds. We retry
        until we get a valid PIN or max retries exhausted.
        
        Args:
            friendly_name: Name to display on Fire TV
            max_retries: Number of PIN request attempts (default: 4)
            retry_delay: Seconds to wait between retries (default: 3.0)
        
        Returns:
            PIN string if successful, None otherwise
        """
        await self._ensure_session()
        
        url = f"{self._base_url}/v1/FireTV/pin/display"
        payload = {"friendlyName": friendly_name}
        
        _LOG.info("Requesting PIN display from Fire TV at %s", self.host)
        _LOG.info("Will retry up to %d times if PIN not immediately available", max_retries)
        
        for attempt in range(1, max_retries + 1):
            try:
                _LOG.info("PIN request attempt %d/%d...", attempt, max_retries)
                
                async with self.session.post(
                    url,
                    headers=self._get_headers(include_token=False),
                    json=payload,
                    timeout=aiohttp.ClientTimeout(total=15)
                ) as response:
                    if response.status == 200:
                        data = await response.json()
                        pin = data.get('pin')
                        
                        if pin and pin != "None" and pin.strip():
                            _LOG.info("✅ PIN received: %s (attempt %d)", pin, attempt)
                            return pin
                        else:
                            _LOG.warning("⚠️ API returned success but PIN is None/empty (attempt %d/%d)", 
                                       attempt, max_retries)
                            _LOG.info("This is normal for Fire TV Cube - PIN display has a delay")
                            
                    else:
                        _LOG.warning("⚠️ PIN request failed with status: %d (attempt %d/%d)", 
                                   response.status, attempt, max_retries)
                        
            except asyncio.TimeoutError:
                _LOG.warning("⏱️ PIN request timeout (attempt %d/%d)", attempt, max_retries)
                
            except Exception as e:
                _LOG.warning("⚠️ Error requesting PIN (attempt %d/%d): %s", 
                           attempt, max_retries, str(e))
            
            # If this wasn't the last attempt, wait before retrying
            if attempt < max_retries:
                _LOG.info("⏳ Waiting %.1f seconds for PIN to appear on TV...", retry_delay)
                await asyncio.sleep(retry_delay)
        
        # All retries exhausted
        _LOG.error("❌ Failed to get PIN after %d attempts", max_retries)
        _LOG.error("PIN may have appeared on TV but API never returned it")
        return None

    async def verify_pin(self, pin: str) -> Optional[str]:
        await self._ensure_session()
        
        url = f"{self._base_url}/v1/FireTV/pin/verify"
        payload = {"pin": pin}
        
        _LOG.info("Verifying PIN: %s", pin)
        
        try:
            async with self.session.post(
                url,
                headers=self._get_headers(include_token=False),
                json=payload,
                timeout=aiohttp.ClientTimeout(total=10)
            ) as response:
                if response.status == 200:
                    data = await response.json()
                    token = data.get('description')
                    self.token = token
                    _LOG.info("✅ PIN verified - Token obtained: %s", token)
                    return token
                else:
                    _LOG.error("PIN verification failed with status: %d", response.status)
                    return None
        except Exception as e:
            _LOG.error("Error verifying PIN: %s", e)
            return None

    async def test_connection(self, max_retries: int = 3, retry_delay: float = 3.0) -> bool:
        """
        Test connection to Fire TV with retry logic.
        
        Fire TV Cube devices may need time to wake up the REST API service,
        so we retry multiple times with delays.
        
        Args:
            max_retries: Number of connection attempts (default: 3)
            retry_delay: Seconds to wait between retries (default: 3.0)
        
        Returns:
            True if connection successful, False otherwise
        """
        await self._ensure_session()
        
        _LOG.info("Testing connection to %s (will retry up to %d times)", 
                 self._base_url, max_retries)
        
        for attempt in range(1, max_retries + 1):
            try:
                _LOG.info("Connection attempt %d/%d to %s...", 
                         attempt, max_retries, self.host)
                
                # Try to reach the base URL or status endpoint
                async with self.session.get(
                    f"{self._base_url}/",
                    timeout=aiohttp.ClientTimeout(total=12)  # Increased from 5 to 12
                ) as response:
                    # Any response means Fire TV is reachable
                    reachable = response.status in [200, 400, 401, 404, 405]
                    if reachable:
                        _LOG.info("✅ Fire TV is reachable at %s (attempt %d)", 
                                 self.host, attempt)
                        return True
                    else:
                        _LOG.warning("⚠️ Unexpected response status: %d (attempt %d)", 
                                   response.status, attempt)
                        
            except asyncio.TimeoutError:
                _LOG.warning("⏱️ Connection timeout to %s (attempt %d/%d)", 
                           self.host, attempt, max_retries)
                
            except aiohttp.ClientConnectorError as e:
                _LOG.warning("⚠️ Connection failed to %s (attempt %d/%d): %s", 
                           self.host, attempt, max_retries, str(e))
                
            except Exception as e:
                _LOG.warning("⚠️ Unexpected error (attempt %d/%d): %s", 
                           attempt, max_retries, str(e))
            
            # If this wasn't the last attempt, wait before retrying
            if attempt < max_retries:
                _LOG.info("⏳ Waiting %.1f seconds before retry...", retry_delay)
                await asyncio.sleep(retry_delay)
        
        # All retries exhausted
        _LOG.error("❌ Failed to connect to %s after %d attempts", 
                  self.host, max_retries)
        return False

    async def send_navigation_command(self, action: str) -> bool:
        await self._ensure_session()
        
        url = f"{self._base_url}/v1/FireTV?action={action}"
        
        _LOG.debug("Sending navigation command: %s", action)
        
        try:
            async with self.session.post(
                url,
                headers=self._get_headers(),
                timeout=aiohttp.ClientTimeout(total=5)
            ) as response:
                success = response.status == 200
                if success:
                    _LOG.debug("✅ Navigation command successful: %s", action)
                else:
                    _LOG.warning("❌ Navigation command failed: %s (status: %d)", 
                               action, response.status)
                return success
        except Exception as e:
            _LOG.error("Error sending navigation command %s: %s", action, e)
            return False

    async def send_media_command(
        self,
        action: str,
        direction: Optional[str] = None,
        key_action_type: str = "keyDown"
    ) -> bool:
        await self._ensure_session()
        
        url = f"{self._base_url}/v1/media?action={action}"
        
        payload = {}
        if action == 'scan' and direction:
            payload = {
                "direction": direction,
                "keyAction": {"keyActionType": key_action_type}
            }
        
        _LOG.debug("Sending media command: %s (payload: %s)", action, payload)
        
        try:
            async with self.session.post(
                url,
                headers=self._get_headers(),
                json=payload if payload else None,
                timeout=aiohttp.ClientTimeout(total=5)
            ) as response:
                success = response.status == 200
                if success:
                    _LOG.debug("✅ Media command successful: %s", action)
                else:
                    _LOG.warning("❌ Media command failed: %s (status: %d)", 
                               action, response.status)
                return success
        except Exception as e:
            _LOG.error("Error sending media command %s: %s", action, e)
            return False

    async def launch_app(self, package_name: str) -> bool:
        await self._ensure_session()
        
        url = f"{self._base_url}/v1/FireTV/app/{package_name}"
        
        _LOG.info("Launching app: %s", package_name)
        
        try:
            async with self.session.post(
                url,
                headers=self._get_headers(),
                timeout=aiohttp.ClientTimeout(total=5)
            ) as response:
                success = response.status == 200
                if success:
                    _LOG.info("✅ App launch successful: %s", package_name)
                else:
                    _LOG.warning("❌ App launch failed: %s (status: %d)", 
                               package_name, response.status)
                return success
        except Exception as e:
            _LOG.error("Error launching app %s: %s", package_name, e)
            return False

    # Convenience methods for common actions
    
    async def dpad_up(self) -> bool:
        """Send D-Pad UP command."""
        return await self.send_navigation_command("dpad_up")

    async def dpad_down(self) -> bool:
        """Send D-Pad DOWN command."""
        return await self.send_navigation_command("dpad_down")

    async def dpad_left(self) -> bool:
        """Send D-Pad LEFT command."""
        return await self.send_navigation_command("dpad_left")

    async def dpad_right(self) -> bool:
        """Send D-Pad RIGHT command."""
        return await self.send_navigation_command("dpad_right")

    async def select(self) -> bool:
        """Send SELECT command."""
        return await self.send_navigation_command("select")

    async def home(self) -> bool:
        """Send HOME command."""
        return await self.send_navigation_command("home")

    async def back(self) -> bool:
        """Send BACK command."""
        return await self.send_navigation_command("back")

    async def menu(self) -> bool:
        """Send MENU command."""
        return await self.send_navigation_command("menu")

    async def play_pause(self) -> bool:
        """Send PLAY/PAUSE toggle command."""
        return await self.send_media_command("play")

    async def fast_forward(self) -> bool:
        """Send FAST FORWARD command."""
        return await self.send_media_command("scan", direction="forward")

    async def rewind(self) -> bool:
        """Send REWIND command."""
        return await self.send_media_command("scan", direction="back")