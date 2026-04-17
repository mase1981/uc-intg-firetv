"""
Fire TV REST API Client Implementation.

:copyright: (c) 2025 by Meir Miyara.
:license: MPL-2.0, see LICENSE for more details.
"""

import asyncio
import logging
import ssl
from typing import Optional

import aiohttp
from aiohttp import ClientResponseError, ClientOSError
from aiohttp.client_exceptions import ServerTimeoutError, ClientConnectionError
import certifi
from intg_firetv.helper import AsyncDebounceTimer
from intg_firetv.commandcontext import get_context

_LOG = logging.getLogger(__name__)

ERROR_OS_WAIT = 0.5


class TokenInvalidError(Exception):
    pass


class FireTVClient:
    def __init__(self, host: str, port: int = 8080, token: Optional[str] = None, long_press_timeout: Optional[int] = 300):
        self.host = host
        self.port = port
        self.token = token
        self.api_key = "0987654321"
        self.session: Optional[aiohttp.ClientSession] = None
        self._last_command_time: float = 0
        self._wake_timeout: float = 5 * 60
        self._device_address = f"{host}:{port}"
        self._long_press_timeout: float = long_press_timeout/1000
        self._long_press_timer = AsyncDebounceTimer(self._long_press_timeout)

        # Use HTTP only for localhost/simulator testing
        # Real Fire TV devices always use HTTPS on port 8080
        if host.lower() in ['localhost', '127.0.0.1', '0.0.0.0']:
            self._use_https = False
            self._base_url = f"http://{self.host}:{self.port}"
            self._wake_url = f"http://{self.host}:{self.port}/apps/FireTVRemote"
        else:
            self._use_https = True
            self._base_url = f"https://{self.host}:{self.port}"
            self._wake_url = f"http://{self.host}:8009/apps/FireTVRemote"

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

    async def _recreate_session(self):
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
        import time
        current_time = time.time()
        time_since_last_command = current_time - self._last_command_time

        should_wake = (self._last_command_time == 0 or
                      time_since_last_command > self._wake_timeout)

        if should_wake:
            _LOG.info(f"Device idle for {time_since_last_command:.0f}s - waking before command")

        return should_wake

    def _update_command_time(self):
        import time
        self._last_command_time = time.time()

    def keep_alive(self):
        """Update command time to prevent wake timeout during active polling."""
        self._update_command_time()

    async def wake_up(self) -> bool:
        await self._ensure_session()

        _LOG.info(f"Sending wake-up POST to Fire TV")
        _LOG.debug(f"Wake-up URL: {self._wake_url}")

        try:
            async with self.session.post(
                self._wake_url,
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
                    return True

        except ClientOSError as ex:
            _LOG.warning("[%s] OS error during wake-up (WiFi not ready), waiting %ss", self._device_address, ERROR_OS_WAIT)
            try:
                await asyncio.sleep(ERROR_OS_WAIT)
                _LOG.info("[%s] Retrying wake-up after WiFi stabilization", self._device_address)
                async with self.session.post(
                    self._wake_url,
                    headers={
                        "User-Agent": "okhttp/4.10.0",
                        "Content-Type": "text/plain; charset=utf-8",
                        "Content-Length": "0"
                    },
                    timeout=aiohttp.ClientTimeout(total=5)
                ) as response:
                    return response.status in [200, 201, 204]
            except Exception as retry_ex:
                _LOG.debug(f"Wake-up retry failed (device may already be awake): {retry_ex}")
                return True

        except asyncio.TimeoutError:
            _LOG.debug("Wake-up timeout (device may already be awake)")
            return True

        except Exception as e:
            _LOG.debug(f"Wake-up error (device may already be awake): {e}")
            return True

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

    async def test_connection(self, max_retries: int = 3, retry_delay: float = 3.0) -> bool:
        for attempt in range(1, max_retries + 1):
            try:
                await self._ensure_session()

                async with self.session.get(
                    f"{self._base_url}/",
                    timeout=aiohttp.ClientTimeout(total=12)
                ) as response:
                    reachable = response.status in [200, 400, 401, 403, 404, 405]
                    if reachable:
                        return True
                    else:
                        _LOG.warning(f"❌️ Unexpected response to Connection attempt {attempt}/{max_retries}. status: {response.status} (attempt {attempt})")

            except asyncio.TimeoutError:
                _LOG.warning(f"⏱️ Connection timeout to {self.host}:{self.port} (attempt {attempt}/{max_retries})")
                await self._recreate_session()

            except (aiohttp.ClientConnectorError, aiohttp.ServerDisconnectedError) as e:
                _LOG.warning(f"❌️ Connection failed to {self.host}:{self.port} (attempt {attempt}/{max_retries}): {str(e)}")
                await self._recreate_session()

            except Exception as e:
                _LOG.warning(f"❌️ Unexpected error (attempt {attempt}/{max_retries}): {str(e)}")
                await self._recreate_session()

            if attempt == max_retries-1:
                _LOG.info(f"Attempting wake and retry for connection test (attempt {attempt+1}/{max_retries})...")
                await self.wake_up()

            if attempt < max_retries:
                _LOG.info(f"⏳ Waiting {retry_delay} seconds before retry...")
                await asyncio.sleep(retry_delay)

        _LOG.error(f"❌ Failed to connect to {self.host}:{self.port} after {max_retries} attempts")
        return False

    async def _key_up(self, **send_params):
        command_ctx = get_context()
        await self._send_command_with_retry(self._send_command, command_ctx.command, **send_params)

    async def _send_command_with_retry(self, command_func, command_name: str, max_retries: int = 2, **send_params):
        if self._should_wake_device():
            await self.wake_up()
            await asyncio.sleep(0.5)
            await self._recreate_session()

        for attempt in range(1, max_retries + 1):
            try:
                _LOG.debug(f"Sending command {command_name}, attempt {attempt}, params {send_params}")
                result = await command_func( **send_params )
                self._update_command_time()
                return result

            except ClientOSError as ex:
                _LOG.warning(
                    "[%s] OS error detected (WiFi not ready after wake), waiting %ss before retry",
                    self._device_address,
                    ERROR_OS_WAIT
                )

                try:
                    await asyncio.sleep(ERROR_OS_WAIT)
                    _LOG.info("[%s] Retrying command after WiFi stabilization", self._device_address)
                    result = await command_func()
                    self._update_command_time()
                    return result

                except Exception as retry_ex:
                    _LOG.error(
                        "[%s] Command failed even after WiFi wait period: %s",
                        self._device_address,
                        retry_ex
                    )
                    raise

            except aiohttp.ClientResponseError as e:
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

            except (ServerTimeoutError, ClientConnectionError) as ex:
                _LOG.error("[%s] Network error during command: %s", self._device_address, ex)
                raise

            except Exception as e:
                _LOG.error(f"Unexpected error in {command_name}: {e}")
                raise

    async def _send_command(self, **send_params):

        await self._ensure_session()

        command_ctx = get_context()

        cmd_name = send_params['cmd_name']
        url = f"{self._base_url}{send_params['url']}"
        action = send_params['action']
        add_key_action_type = send_params['add_key_action_type']

        long_key_press = (command_ctx.hold > 0)
        only_release_key = command_ctx.key_down

        if add_key_action_type:
            if only_release_key:
                key_action_type = "keyUp"
                long_key_press = False
            else:
                if long_key_press:
                    key_action_type = "keyDown"
                else:
                    key_action_type = "keyDownUp"

        found_key_action = False
        payload = None

        if "payload" in send_params:
            payload = send_params['payload']
            _LOG.debug(f"[{cmd_name}]: Payload found: {payload}")
            if add_key_action_type:
                if "keyActionType" in payload:
                    payload["keyActionType"] = key_action_type
                    found_key_action = True
                    _LOG.debug(f"[{cmd_name}]: keyActionType set to: {key_action_type}")
                elif "keyAction" in payload:
                    _LOG.debug(f"[{cmd_name}]: keyAction found")
                    if "keyActionType" in payload["keyAction"]:
                        payload["keyAction"]["keyActionType"] = key_action_type
                        found_key_action = True
                        _LOG.debug(f"[{cmd_name}]: keyAction/keyActionType set to: {key_action_type}")
                if not found_key_action:
                    payload["keyActionType"] = key_action_type
        elif add_key_action_type:
            payload = {"keyActionType": key_action_type}
            _LOG.debug(f"[{cmd_name}]: Default keyActionType added: {key_action_type}")

        json_payload = payload

        if "info_text" in send_params:
            _LOG.info(send_params['info_text'])
        _LOG.debug(f"[{cmd_name}]: Sending command {action} (payload: {json_payload}) to url {url}")

        async with self.session.post(
            url,
            headers=self._get_headers(),
            json=json_payload,
            timeout=aiohttp.ClientTimeout(total=5)
        ) as response:
            success = response.status in [200,500]
            if success:
                _LOG.debug(f"✅ [{cmd_name}]: command successful")
                if response.status == 500:
                    _LOG.debug(f"[{cmd_name}]: Got 500 response (treated as success for older FireTV devices)")
                if long_key_press:
                    command_ctx.key_down = True
                    self._long_press_timer.setDelayMS(command_ctx.hold)
                    self._long_press_timer.trigger(self._key_up,**send_params)
                    _LOG.info(f"🕛 Long key press: timer started for keyUp for command {cmd_name} in {self._long_press_timer.delay*1000}ms")
                else:
                    if (command_ctx.repeat > 1):
                        command_ctx.repeat -= 1
                        command_ctx.key_down = False
                        if command_ctx.delay > 0:
                            self._long_press_timer.setDelayMS(command_ctx.delay)
                            self._long_press_timer.trigger(self._send_command,**send_params)
                            _LOG.info(f"🕛 Repeated key press: timer started for next press {cmd_name} in {self._long_press_timer.delay*1000}ms")
                        else:
                            await self._send_command(**send_params)
            else:
                _LOG.warning(f"❌ [{cmd_name}]: command failed (status: {response.status})")
            return success

    async def send_navigation_command(self, action: str, long_key_press: bool = False) -> bool:
        cmd_name = f"navigation:{action}"
        url = f"/v1/FireTV?action={action}"

        send_args = {
            "cmd_name": cmd_name,
            "action": action,
            "add_key_action_type": True,
            "url": url,
            "long_key_press": long_key_press
        }

        try:
            return await self._send_command_with_retry(self._send_command, cmd_name, **send_args)
        except TokenInvalidError:
            raise
        except Exception as e:
            _LOG.error(f"Error sending command {cmd_name}: {e}")
            return False

    async def send_media_command(
        self,
        action: str,
        direction: Optional[str] = None,
        long_key_press: Optional[bool] = False
    ) -> bool:
        cmd_name = f"media:{action}"
        url = f"/v1/media?action={action}"
        add_key_action_type = False
        if action == 'scan' and direction:
                payload = {
                    "direction": direction,
                    "keyAction": {"keyActionType": "keyDownUp"}
                }
                add_key_action_type = True
        else:
            payload = None
        send_args = {
            "cmd_name": cmd_name,
            "action": action,
            "add_key_action_type": add_key_action_type,
            "url": url,
            "payload": payload,
            "long_key_press": long_key_press
        }

        try:
            return await self._send_command_with_retry(self._send_command, cmd_name, **send_args)
        except TokenInvalidError:
            raise
        except Exception as e:
            _LOG.error(f"Error sending command {cmd_name}: {e}")
            return False

    async def launch_app(self, package_name: str) -> bool:
        cmd_name = f"app:{package_name}"
        url = f"/v1/FireTV/app/{package_name}"

        send_args = {
            "cmd_name": cmd_name,
            "action": package_name,
            "add_key_action_type": False,
            "url": url,
            "info_text": f"Launching app: {package_name}"
        }
        try:
            return await self._send_command_with_retry(self._send_command, cmd_name, **send_args)
        except TokenInvalidError:
            raise
        except Exception as e:
            _LOG.error(f"Error launching app {package_name}: {e}")
            return False

    async def send_text(self, text: int) -> bool:
        cmd_name = f"text:{text}"
        url = "/v1/FireTV/text"
        json_payload = {"text": text}

        send_args = {
            "cmd_name": cmd_name,
            "action": text,
            "add_key_action_type": False,
            "url": url,
            "info_text": f"Sending text: {text}, {json_payload}",
            "payload": json_payload
        }

        try:
            return await self._send_command_with_retry(self._send_command, cmd_name, **send_args)
        except TokenInvalidError:
            raise
        except Exception as e:
            _LOG.error(f"Error sending keycode {text}: {e}")
            return False

    async def play_pause(self, long_key_press:bool = False) -> bool:
        return await self.send_media_command("play")

    async def pause(self, long_key_press:bool = False) -> bool:
        return await self.send_media_command("pause")

    async def fast_forward(self, long_key_press:bool = False) -> bool:
        return await self.send_media_command("scan", direction="forward")

    async def rewind(self, long_key_press:bool = False) -> bool:
        return await self.send_media_command("scan", direction="back")
