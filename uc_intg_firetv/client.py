"""
Fire TV REST API Client Implementation.

:copyright: (c) 2025 by Meir Miyara.
:license: MIT, see LICENSE for more details.
"""

import asyncio
import logging
import ssl
from typing import Optional

import aiohttp
from aiohttp import ClientResponseError
import certifi

_LOG = logging.getLogger(__name__)


class FireTVClient:
    def __init__(self, host: str, port: int = 8080, token: Optional[str] = None):
        self.host = host
        self.port = port  # This is the HTTPS control port (8080)
        self.token = token
        self.api_key = "0987654321"
        self.session: Optional[aiohttp.ClientSession] = None
        self._last_command_time: float = 0
        self._wake_timeout: float = 25 * 60  # 25 minutes - wake if idle this long
        
        # Determine if localhost (simulator)
        if host.lower() in ['localhost', '127.0.0.1', '0.0.0.0']:
            self._use_https = False
            self._base_url = f"http://{self.host}:{self.port}"
            self._wake_url = f"http://{self.host}:{self.port}/apps/FireTVRemote"
            _LOG.info("Using HTTP for simulator/localhost")
        else:
            self._use_https = True
            # CRITICAL: Control API uses HTTPS on configured port (typically 8080)
            self._base_url = f"https://{self.host}:{self.port}"
            # CRITICAL: Wake-up ALWAYS uses HTTP on port 8009 (DIAL protocol)
            self._wake_url = f"http://{self.host}:8009/apps/FireTVRemote"
            _LOG.info(f"Using HTTPS for Fire TV device (control: {self.port}, wake: 8009)")

    async def __aenter__(self):
        await self._ensure_session()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        await self.close()

    async def _ensure_session(self):
        """Ensure we have a valid aiohttp session, recreating if needed."""
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
            _LOG.debug(f"HTTP session created for {self.host}:{self.port}")

    async def _recreate_session(self):
        """Force recreate the session - useful after connection errors."""
        _LOG.debug("Recreating HTTP session...")
        if self.session and not self.session.closed:
            await self.session.close()
        self.session = None
        await self._ensure_session()

    async def close(self):
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

    def _should_wake_device(self) -> bool:
        """Determine if device should be woken based on inactivity time."""
        import time
        current_time = time.time()
        time_since_last_command = current_time - self._last_command_time
        
        # Wake if never commanded or idle for more than threshold
        should_wake = (self._last_command_time == 0 or 
                      time_since_last_command > self._wake_timeout)
        
        if should_wake:
            _LOG.info(f"Device idle for {time_since_last_command:.0f}s - waking before command")
        
        return should_wake

    def _update_command_time(self):
        """Update last successful command time."""
        import time
        self._last_command_time = time.time()

    async def wake_up(self) -> bool:
        """
        Wake up Fire TV using DIAL protocol.
        
        CRITICAL: This MUST use HTTP on port 8009, NOT HTTPS on port 8080!
        This is the DIAL protocol wake-up endpoint that works on ALL Fire TV models.
        
        Returns:
            True if wake-up successful or device already awake
        """
        await self._ensure_session()
        
        _LOG.info(f"Sending wake-up POST to Fire TV")
        _LOG.debug(f"Wake-up URL: {self._wake_url}")
        
        try:
            async with self.session.post(
                self._wake_url,
                # Note: wake-up doesn't need API key or token headers
                headers={
                    "User-Agent": "okhttp/4.10.0",
                    "Content-Type": "text/plain; charset=utf-8",
                    "Content-Length": "0"
                },
                timeout=aiohttp.ClientTimeout(total=5)
            ) as response:
                if response.status in [200, 201, 204]:
                    _LOG.info(f"✅ Wake-up successful: {response.status}")
                    return True
                else:
                    _LOG.debug(f"Wake-up returned status: {response.status} (device may already be awake)")
                    return True  # Device may already be awake
                    
        except asyncio.TimeoutError:
            _LOG.debug("Wake-up timeout (device may already be awake)")
            return True
            
        except Exception as e:
            _LOG.debug(f"Wake-up error (device may already be awake): {e}")
            return True

    async def request_pin(self, friendly_name: str = "UC Remote") -> bool:
        """
        Request PIN display on Fire TV.
        
        Uses HTTPS on configured port (typically 8080).
        Device must be awake before calling this.
        """
        await self._ensure_session()
        
        url = f"{self._base_url}/v1/FireTV/pin/display"
        payload = {"friendlyName": friendly_name}
        
        _LOG.info(f"Requesting PIN display on Fire TV at {self.host}:{self.port}")
        _LOG.info("User should see PIN on TV screen within 5-10 seconds")
        
        try:
            async with self.session.post(
                url,
                headers=self._get_headers(include_token=False),
                json=payload,
                timeout=aiohttp.ClientTimeout(total=15)
            ) as response:
                if response.status == 200:
                    _LOG.info("✅ PIN display request successful")
                    _LOG.info("PIN should now be visible on Fire TV screen")
                    return True
                else:
                    _LOG.error(f"❌ PIN display request failed with status: {response.status}")
                    return False
                    
        except asyncio.TimeoutError:
            _LOG.error("⏱️ PIN display request timeout")
            return False
            
        except Exception as e:
            _LOG.error(f"❌️ Error requesting PIN display: {str(e)}")
            return False

    async def verify_pin(self, pin: str) -> Optional[str]:
        """
        Verify PIN and get authentication token.
        
        Uses HTTPS on configured port (typically 8080).
        """
        await self._ensure_session()
        
        url = f"{self._base_url}/v1/FireTV/pin/verify"
        payload = {"pin": pin}
        
        _LOG.info(f"Verifying PIN: {pin}")
        
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
                    _LOG.info(f"✅ PIN verified - Token obtained: {token}")
                    self._update_command_time()  # Mark as active after auth
                    return token
                else:
                    _LOG.error(f"PIN verification failed with status: {response.status}")
                    return None
        except Exception as e:
            _LOG.error(f"Error verifying PIN: {e}")
            return None

    async def test_connection(self, max_retries: int = 3, retry_delay: float = 3.0) -> bool:
        """
        Test connection to Fire TV REST API.
        
        CRITICAL: This tests the HTTPS REST API on configured port (8080),
        NOT the wake-up endpoint on port 8009.
        
        Tests actual API endpoint for Fire TV Stick compatibility.
        """
        await self._ensure_session()
        
        # Test actual API endpoint instead of root (Fire TV Stick compatibility)
        test_url = f"{self._base_url}/v1/FireTV/pin/display"
        
        _LOG.info(f"Testing connection to {self._base_url} (will retry up to {max_retries} times)")
        _LOG.info("IMPORTANT: Testing actual API endpoint, not root (Stick compatibility)")
        
        for attempt in range(1, max_retries + 1):
            try:
                _LOG.info(f"Connection attempt {attempt}/{max_retries} to {self.host}:{self.port}...")
                
                # Use POST to actual API endpoint (more reliable for Fire TV Stick)
                async with self.session.post(
                    test_url,
                    headers=self._get_headers(include_token=False),
                    json={"friendlyName": "UC Remote"},
                    timeout=aiohttp.ClientTimeout(total=12)
                ) as response:
                    if response.status in [200, 400, 401, 404, 405]:
                        _LOG.info(f"✅ Fire TV REST API is reachable at {self.host}:{self.port} (status: {response.status})")
                        _LOG.info(f"API endpoint test successful on attempt {attempt}")
                        return True
                    else:
                        _LOG.warning(f"❌️ Unexpected response status: {response.status} (attempt {attempt})")
                        
            except asyncio.TimeoutError:
                _LOG.warning(f"⏱️ Connection timeout to {self.host}:{self.port} (attempt {attempt}/{max_retries})")
                
            except aiohttp.ClientConnectorError as e:
                _LOG.warning(f"❌️ Connection failed to {self.host}:{self.port} (attempt {attempt}/{max_retries}): {str(e)}")
                
            except Exception as e:
                _LOG.warning(f"❌️ Unexpected error (attempt {attempt}/{max_retries}): {str(e)}")
            
            if attempt < max_retries:
                _LOG.info(f"⏳ Waiting {retry_delay} seconds before retry...")
                await asyncio.sleep(retry_delay)
        
        _LOG.error(f"❌ Failed to connect to {self.host}:{self.port} after {max_retries} attempts")
        return False

    async def _send_command_with_retry(self, command_func, command_name: str, max_retries: int = 2):
        """
        Send command with automatic wake-up and retry logic.
        
        Args:
            command_func: Async function that sends the actual command
            command_name: Name of command for logging
            max_retries: Number of retry attempts after wake-up
            
        Returns:
            Result from command_func
            
        Raises:
            TokenInvalidError: If authentication token is invalid/expired
        """
        # Wake device if it's been idle
        if self._should_wake_device():
            await self.wake_up()
            await asyncio.sleep(2)  # Give device time to wake up
            
            # Recreate session after wake (session might be stale)
            await self._recreate_session()
        
        # Try command with retries
        for attempt in range(1, max_retries + 1):
            try:
                result = await command_func()
                self._update_command_time()  # Mark successful command time
                return result
                
            except aiohttp.ClientResponseError as e:
                # Check for authentication errors
                if e.status in [401, 403]:
                    _LOG.error(f"❌ AUTHENTICATION FAILED: Token is invalid or expired")
                    _LOG.error(f"❌ Status {e.status}: {e.message}")
                    _LOG.error(f"❌ SOLUTION: Re-run setup to obtain new authentication token")
                    _LOG.error(f"❌ This typically happens if pairing was removed from Fire TV settings")
                    raise TokenInvalidError(
                        f"Authentication token invalid (HTTP {e.status}). "
                        "Please re-run setup to re-authenticate."
                    )
                else:
                    _LOG.error(f"HTTP error {e.status} on {command_name}: {e.message}")
                    raise
                
            except (aiohttp.ClientConnectorError, aiohttp.ServerDisconnectedError) as e:
                _LOG.warning(f"Connection error on {command_name} (attempt {attempt}/{max_retries}): {e}")
                
                if attempt < max_retries:
                    _LOG.info(f"Attempting wake and retry for {command_name}...")
                    await self.wake_up()
                    await asyncio.sleep(2)
                    await self._recreate_session()
                else:
                    _LOG.error(f"❌ {command_name} failed after {max_retries} attempts")
                    raise
                    
            except Exception as e:
                _LOG.error(f"Unexpected error in {command_name}: {e}")
                raise


class TokenInvalidError(Exception):
    """Raised when the authentication token is invalid or expired."""
    pass

    async def send_navigation_command(self, action: str) -> bool:
        """Send navigation command using HTTPS REST API with auto-wake."""
        
        async def _send():
            await self._ensure_session()
            url = f"{self._base_url}/v1/FireTV?action={action}"
            
            _LOG.debug(f"Sending navigation command: {action}")
            
            async with self.session.post(
                url,
                headers=self._get_headers(),
                timeout=aiohttp.ClientTimeout(total=5)
            ) as response:
                # Raise for HTTP errors (including 401/403)
                response.raise_for_status()
                
                success = response.status == 200
                if success:
                    _LOG.debug(f"✅ Navigation command successful: {action}")
                else:
                    _LOG.warning(f"❌ Navigation command failed: {action} (status: {response.status})")
                return success
        
        try:
            return await self._send_command_with_retry(_send, f"navigation:{action}")
        except TokenInvalidError:
            raise  # Re-raise token errors
        except Exception as e:
            _LOG.error(f"Error sending navigation command {action}: {e}")
            return False

    async def send_media_command(
        self,
        action: str,
        direction: Optional[str] = None,
        key_action_type: str = "keyDown"
    ) -> bool:
        """Send media command using HTTPS REST API with auto-wake."""
        
        async def _send():
            await self._ensure_session()
            url = f"{self._base_url}/v1/media?action={action}"
            
            payload = {}
            if action == 'scan' and direction:
                payload = {
                    "direction": direction,
                    "keyAction": {"keyActionType": key_action_type}
                }
            
            _LOG.debug(f"Sending media command: {action} (payload: {payload})")
            
            async with self.session.post(
                url,
                headers=self._get_headers(),
                json=payload if payload else None,
                timeout=aiohttp.ClientTimeout(total=5)
            ) as response:
                # Raise for HTTP errors (including 401/403)
                response.raise_for_status()
                
                success = response.status == 200
                if success:
                    _LOG.debug(f"✅ Media command successful: {action}")
                else:
                    _LOG.warning(f"❌ Media command failed: {action} (status: {response.status})")
                return success
        
        try:
            return await self._send_command_with_retry(_send, f"media:{action}")
        except TokenInvalidError:
            raise  # Re-raise token errors
        except Exception as e:
            _LOG.error(f"Error sending media command {action}: {e}")
            return False

    async def launch_app(self, package_name: str) -> bool:
        """Launch app using HTTPS REST API with auto-wake."""
        
        async def _send():
            await self._ensure_session()
            url = f"{self._base_url}/v1/FireTV/app/{package_name}"
            
            _LOG.info(f"Launching app: {package_name}")
            
            async with self.session.post(
                url,
                headers=self._get_headers(),
                timeout=aiohttp.ClientTimeout(total=5)
            ) as response:
                # Raise for HTTP errors (including 401/403)
                response.raise_for_status()
                
                success = response.status == 200
                if success:
                    _LOG.info(f"✅ App launch successful: {package_name}")
                else:
                    _LOG.warning(f"❌ App launch failed: {package_name} (status: {response.status})")
                return success
        
        try:
            return await self._send_command_with_retry(_send, f"app:{package_name}")
        except TokenInvalidError:
            raise  # Re-raise token errors
        except Exception as e:
            _LOG.error(f"Error launching app {package_name}: {e}")
            return False

    async def dpad_up(self) -> bool:
        return await self.send_navigation_command("dpad_up")

    async def dpad_down(self) -> bool:
        return await self.send_navigation_command("dpad_down")

    async def dpad_left(self) -> bool:
        return await self.send_navigation_command("dpad_left")

    async def dpad_right(self) -> bool:
        return await self.send_navigation_command("dpad_right")

    async def select(self) -> bool:
        return await self.send_navigation_command("select")

    async def home(self) -> bool:
        return await self.send_navigation_command("home")

    async def back(self) -> bool:
        return await self.send_navigation_command("back")

    async def menu(self) -> bool:
        return await self.send_navigation_command("menu")

    async def play_pause(self) -> bool:
        return await self.send_media_command("play")

    async def fast_forward(self) -> bool:
        return await self.send_media_command("scan", direction="forward")

    async def rewind(self) -> bool:
        return await self.send_media_command("scan", direction="back")

    async def next(self) -> bool:
        return await self.send_media_command("skip_forward")

    async def previous(self) -> bool:
        return await self.send_media_command("skip_back")