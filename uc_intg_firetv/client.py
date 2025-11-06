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
import certifi

_LOG = logging.getLogger(__name__)


class FireTVClient:
    def __init__(self, host: str, port: int = 8080, token: Optional[str] = None):
        self.host = host
        self.port = port  # This is the HTTPS control port (8080)
        self.token = token
        self.api_key = "0987654321"
        self.session: Optional[aiohttp.ClientSession] = None
        
        # Determine if localhost (simulator)
        if host.lower() in ['localhost', '127.0.0.1', '0.0.0.0']:
            self._use_https = False
            self._base_url = f"http://{self.host}:{self.port}"
            self._wake_url = f"http://{self.host}:{self.port}/apps/FireTVRemote"
            _LOG.info("Using HTTP for simulator/localhost")
        else:
            self._use_https = True
            self._base_url = f"https://{self.host}:{self.port}"
            self._wake_url = f"http://{self.host}:8009/apps/FireTVRemote"
            _LOG.info(f"Using HTTPS for Fire TV device (control: {self.port}, wake: 8009)")

    async def __aenter__(self):
        await self._ensure_session()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        await self.close()

    async def _ensure_session(self):
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

    async def wake_up(self) -> bool:
        await self._ensure_session()
        
        _LOG.info(f"Sending wake-up POST to Fire TV")
        _LOG.info(f"Wake-up URL: {self._wake_url}")
        
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
                    _LOG.warning(f"Wake-up returned status: {response.status}")
                    return True  # Device may already be awake
                    
        except asyncio.TimeoutError:
            _LOG.warning("Wake-up timeout (device may already be awake)")
            return True
            
        except Exception as e:
            _LOG.warning(f"Wake-up error (device may already be awake): {e}")
            return True

    async def test_connection(self, max_retries: int = 3, retry_delay: float = 3.0) -> bool:
        await self._ensure_session()
        
        _LOG.info(f"Testing connection to {self._base_url} (will retry up to {max_retries} times)")
        _LOG.info("IMPORTANT: Testing actual API endpoint, not root (Stick compatibility)")
        
        for attempt in range(1, max_retries + 1):
            try:
                _LOG.info(f"Connection attempt {attempt}/{max_retries} to {self.host}:{self.port}...")
                test_url = f"{self._base_url}/v1/FireTV/pin/display"
                async with self.session.post(
                    test_url,
                    headers=self._get_headers(include_token=False),
                    json={"friendlyName": "UC Remote Connection Test"},
                    timeout=aiohttp.ClientTimeout(total=12)
                ) as response:
                    reachable = response.status in [200, 400, 401, 404, 405]
                    
                    if reachable:
                        _LOG.info(f"✅ Fire TV REST API is reachable at {self.host}:{self.port} (status: {response.status})")
                        _LOG.info(f"API endpoint test successful on attempt {attempt}")
                        return True
                    elif response.status == 403:
                        _LOG.warning(f"⚠️  API endpoint returned 403 (attempt {attempt})")
                        _LOG.warning("This may indicate authentication or security restrictions")
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

    async def request_pin(self, friendly_name: str = "UC Remote") -> bool:
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
                    return token
                else:
                    _LOG.error(f"PIN verification failed with status: {response.status}")
                    return None
        except Exception as e:
            _LOG.error(f"Error verifying PIN: {e}")
            return None

    async def send_navigation_command(self, action: str) -> bool:
        await self._ensure_session()
        
        url = f"{self._base_url}/v1/FireTV?action={action}"
        
        _LOG.debug(f"Sending navigation command: {action}")
        
        try:
            async with self.session.post(
                url,
                headers=self._get_headers(),
                timeout=aiohttp.ClientTimeout(total=5)
            ) as response:
                success = response.status == 200
                if success:
                    _LOG.debug(f"✅ Navigation command successful: {action}")
                else:
                    _LOG.warning(f"❌ Navigation command failed: {action} (status: {response.status})")
                return success
        except Exception as e:
            _LOG.error(f"Error sending navigation command {action}: {e}")
            return False

    async def send_media_command(
        self,
        action: str,
        direction: Optional[str] = None,
        key_action_type: str = "keyDown"
    ) -> bool:
        """Send media command using HTTPS REST API."""
        await self._ensure_session()
        
        url = f"{self._base_url}/v1/media?action={action}"
        
        payload = {}
        if action == 'scan' and direction:
            payload = {
                "direction": direction,
                "keyAction": {"keyActionType": key_action_type}
            }
        
        _LOG.debug(f"Sending media command: {action} (payload: {payload})")
        
        try:
            async with self.session.post(
                url,
                headers=self._get_headers(),
                json=payload if payload else None,
                timeout=aiohttp.ClientTimeout(total=5)
            ) as response:
                success = response.status == 200
                if success:
                    _LOG.debug(f"✅ Media command successful: {action}")
                else:
                    _LOG.warning(f"❌ Media command failed: {action} (status: {response.status})")
                return success
        except Exception as e:
            _LOG.error(f"Error sending media command {action}: {e}")
            return False

    async def launch_app(self, package_name: str) -> bool:
        """Launch app using HTTPS REST API."""
        await self._ensure_session()
        
        url = f"{self._base_url}/v1/FireTV/app/{package_name}"
        
        _LOG.info(f"Launching app: {package_name}")
        
        try:
            async with self.session.post(
                url,
                headers=self._get_headers(),
                timeout=aiohttp.ClientTimeout(total=5)
            ) as response:
                success = response.status == 200
                if success:
                    _LOG.info(f"✅ App launch successful: {package_name}")
                else:
                    _LOG.warning(f"❌ App launch failed: {package_name} (status: {response.status})")
                return success
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