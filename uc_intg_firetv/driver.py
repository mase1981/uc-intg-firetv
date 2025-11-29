"""
Fire TV Integration Driver for Unfolded Circle Remote Two/3.

:copyright: (c) 2025 by Meir Miyara.
:license: MIT, see LICENSE for more details.
"""

import asyncio
import logging
import os
from typing import List, Optional

import ucapi
from ucapi import DeviceStates, Events, IntegrationSetupError, SetupComplete, SetupError

from uc_intg_firetv.client import FireTVClient
from uc_intg_firetv.config import Config
from uc_intg_firetv.remote import FireTVRemote

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
_LOG = logging.getLogger(__name__)

api: Optional[ucapi.IntegrationAPI] = None
config: Optional[Config] = None
client: Optional[FireTVClient] = None
remote_entity: Optional[FireTVRemote] = None
_entities_ready: bool = False
_initialization_lock: asyncio.Lock = asyncio.Lock()


async def _initialize_entities():
    global config, client, remote_entity, api, _entities_ready
    
    async with _initialization_lock:
        if _entities_ready:
            _LOG.debug("Entities already initialized, skipping")
            return
        
        if not config or not config.is_configured():
            _LOG.info("Integration not configured, skipping entity initialization")
            return
        
        _LOG.info("=" * 60)
        _LOG.info("Initializing Fire TV entities...")
        _LOG.info("=" * 60)
        
        try:
            host = config.get_host()
            port = config.get('port', 8080)
            token = config.get_token()
            
            _LOG.info(f"Host: {host}")
            _LOG.info(f"Port: {port}")
            _LOG.info(f"Token: {token[:10]}..." if token else "None")
            
            client = FireTVClient(host, port, token)
            
            if not await client.test_connection():
                _LOG.error(f"Failed to connect to Fire TV at {host}:{port}")
                await api.set_device_state(DeviceStates.ERROR)
                _entities_ready = False
                return
            
            _LOG.info(f"… Connected to Fire TV at {host}:{port}")
            
            device_id = f"firetv_{host.replace('.', '_')}_{port}"
            device_name = f"Fire TV ({host})"
            
            remote_entity = FireTVRemote(device_id, device_name)
            remote_entity.set_client(client)
            remote_entity.set_api(api)
            
            api.available_entities.clear()
            api.available_entities.add(remote_entity)
            
            _entities_ready = True
            
            _LOG.info(f"… Fire TV remote entity created: {remote_entity.id}")
            _LOG.info("… Entities ready for subscription")
            _LOG.info("=" * 60)
            
            await api.set_device_state(DeviceStates.CONNECTED)
            
        except Exception as e:
            _LOG.error(f"Failed to initialize entities: {e}", exc_info=True)
            _entities_ready = False
            await api.set_device_state(DeviceStates.ERROR)
            raise


async def setup_handler(msg: ucapi.SetupDriver) -> ucapi.SetupAction:
    global config, client
    
    _LOG.info("=" * 60)
    _LOG.info(f"SETUP HANDLER: {type(msg).__name__}")
    _LOG.info("=" * 60)
    
    if isinstance(msg, ucapi.DriverSetupRequest):
        _LOG.info("=== SETUP: Driver Setup Request ===")
        setup_data = msg.setup_data
        
        if 'host' in setup_data:
            host_input = setup_data.get('host')
            port_input = setup_data.get('port', '8080')
            
            try:
                port = int(port_input)
            except ValueError:
                _LOG.error(f"Invalid port number: {port_input}")
                port = 8080
            
            _LOG.info(f"Step 1: Testing connection to Fire TV at {host_input}:{port}")
            
            test_client = FireTVClient(host_input, port)
            
            _LOG.info("Step 1a: Sending wake-up command to Fire TV")
            await test_client.wake_up()
            
            _LOG.info("Step 1b: Waiting 3 seconds for Fire TV to wake up")
            await asyncio.sleep(3)
            
            _LOG.info("Step 1c: Testing connection after wake-up")
            connection_ok = await test_client.test_connection(max_retries=3, retry_delay=3.0)
            
            if not connection_ok:
                _LOG.error("=" * 60)
                _LOG.error(f"CANNOT REACH FIRE TV AT {host_input}:{port}")
                _LOG.error("=" * 60)
                _LOG.error("")
                _LOG.error("Troubleshooting:")
                _LOG.error("1. Fire TV is powered on")
                _LOG.error("2. Correct IP address")
                _LOG.error("3. Try different port (8080, 8009, 8443)")
                _LOG.error("4. Network/firewall allows connection")
                _LOG.error("=" * 60)
                
                await test_client.close()
                return SetupError(IntegrationSetupError.CONNECTION_REFUSED)
            
            _LOG.info("Connection successful to Fire TV")
            
            _LOG.info("Step 2: Requesting PIN display on Fire TV screen")
            
            pin_requested = await test_client.request_pin("UC Remote")
            await test_client.close()
            
            if not pin_requested:
                _LOG.error("=" * 60)
                _LOG.error(" FAILED TO REQUEST PIN DISPLAY")
                _LOG.error("=" * 60)
                return SetupError(IntegrationSetupError.OTHER)
            
            config.set('host', host_input)
            config.set('port', port)
            
            _LOG.info("… PIN display request successful")
            _LOG.info("Step 3: Showing PIN entry page to user")
            
            return ucapi.RequestUserInput(
                title={"en": "Enter PIN from Fire TV"},
                settings=[
                    {
                        "id": "pin",
                        "label": {"en": "4-Digit PIN (shown on TV screen)"},
                        "field": {
                            "text": {
                                "default": ""
                            }
                        }
                    }
                ]
            )
        else:
            _LOG.error("Invalid setup data: missing host")
            return SetupError(IntegrationSetupError.OTHER)
    
    elif isinstance(msg, ucapi.UserDataResponse):
        _LOG.info("=== SETUP: User Data Response (PIN Entry) ===")
        
        pin = msg.input_values.get('pin')
        host = config.get_host()
        port = config.get('port', 8080)
        
        if not host:
            _LOG.error("No host in config - setup flow broken")
            return SetupError(IntegrationSetupError.OTHER)
        
        if not pin:
            _LOG.error("No PIN provided by user")
            return SetupError(IntegrationSetupError.OTHER)
        
        _LOG.info(f"Step 4: Verifying PIN '{pin}' with Fire TV")
        
        verify_client = FireTVClient(host, port)
        token = await verify_client.verify_pin(pin)
        await verify_client.close()
        
        if not token:
            _LOG.error("=" * 60)
            _LOG.error("PIN VERIFICATION FAILED")
            _LOG.error("=" * 60)
            return SetupError(IntegrationSetupError.AUTHORIZATION_ERROR)
        
        config.set('token', token)
        config.save()
        
        _LOG.info("PIN verified successfully")
        _LOG.info("Authentication token obtained and saved")
        _LOG.info("Step 5: Setup complete - Initializing entities")
        
        await _initialize_entities()
        
        _LOG.info("… Setup completed successfully!")
        
        return SetupComplete()
        
    elif isinstance(msg, ucapi.UserConfirmationResponse):
        _LOG.warning("Unexpected UserConfirmationResponse in setup")
        return SetupComplete()
    
    elif isinstance(msg, ucapi.AbortDriverSetup):
        _LOG.warning("Setup aborted by user or system")
        return SetupError(IntegrationSetupError.OTHER)
    
    _LOG.error(f"Unknown setup message type: {type(msg)}")
    return SetupError(IntegrationSetupError.OTHER)


async def on_connect() -> None:
    global config, _entities_ready, client
    
    _LOG.info("=" * 60)
    _LOG.info("Remote Two/3 connected")
    _LOG.info("=" * 60)
    
    if not config:
        config = Config()
    
    config.reload_from_disk()
    
    if config.is_configured() and not _entities_ready:
        _LOG.info("Configuration found but entities missing, reinitializing...")
        try:
            await _initialize_entities()
        except Exception as e:
            _LOG.error(f"Failed to reinitialize entities: {e}")
            await api.set_device_state(DeviceStates.ERROR)
            return
    
    if config.is_configured() and _entities_ready:
        if client and client.session and not client.session.closed:
            _LOG.info("Fire TV client session active, connection maintained")
        await api.set_device_state(DeviceStates.CONNECTED)
    elif not config.is_configured():
        await api.set_device_state(DeviceStates.DISCONNECTED)
    else:
        await api.set_device_state(DeviceStates.ERROR)


async def on_disconnect() -> None:
    global client, _entities_ready
    
    _LOG.warning("=" * 60)
    _LOG.warning("Remote Two/3 disconnected - cleaning up")
    _LOG.warning("=" * 60)
    
    if client:
        try:
            _LOG.info("Closing Fire TV client session...")
            await client.close()
            _LOG.info("Fire TV client session closed")
        except Exception as e:
            _LOG.error(f"Error closing Fire TV client: {e}")
    
    _LOG.info("Disconnect cleanup complete - ready for reconnect")


async def on_subscribe_entities(entity_ids: List[str]):
    global remote_entity, _entities_ready
    
    _LOG.info("=" * 60)
    _LOG.info(f"… SUBSCRIPTION EVENT - Entities subscribed: {entity_ids}")
    _LOG.info("=" * 60)
    
    if not _entities_ready:
        _LOG.error("RACE CONDITION: Subscription before entities ready! Attempting recovery...")
        if config and config.is_configured():
            await _initialize_entities()
        else:
            _LOG.error("Cannot recover - no configuration available")
            return
    
    for entity_id in entity_ids:
        if remote_entity and entity_id == remote_entity.id:
            _LOG.info(f"Pushing initial state for remote entity: {entity_id}")
            await remote_entity.push_initial_state()
            _LOG.info("… Remote entity initial state pushed")


async def on_unsubscribe_entities(entity_ids: List[str]):
    _LOG.info(f"Entities unsubscribed: {entity_ids}")


async def main():
    global api, config
    
    _LOG.info("=" * 60)
    _LOG.info("FIRE TV INTEGRATION DRIVER STARTING")
    _LOG.info("=" * 60)
    
    try:
        loop = asyncio.get_running_loop()
        
        config = Config()
        config.load()
        
        driver_path = os.path.join(os.path.dirname(__file__), "..", "driver.json")
        api = ucapi.IntegrationAPI(loop)
        
        if config.is_configured():
            _LOG.info("Found existing configuration, pre-initializing entities for reboot survival")
            loop.create_task(_initialize_entities())
        else:
            _LOG.info("No configuration found, waiting for setup...")
        
        api.add_listener(Events.CONNECT, on_connect)
        api.add_listener(Events.DISCONNECT, on_disconnect)
        api.add_listener(Events.SUBSCRIBE_ENTITIES, on_subscribe_entities)
        api.add_listener(Events.UNSUBSCRIBE_ENTITIES, on_unsubscribe_entities)
        
        await api.init(os.path.abspath(driver_path), setup_handler)
        
        if config.is_configured():
            await api.set_device_state(DeviceStates.CONNECTING)
        else:
            await api.set_device_state(DeviceStates.DISCONNECTED)
        
        _LOG.info("Fire TV driver initialized successfully")
        _LOG.info("=" * 60)
        
        await asyncio.Future()
        
    except asyncio.CancelledError:
        _LOG.info("Driver task cancelled")
    except Exception as e:
        _LOG.error(f"Fatal error in main: {e}", exc_info=True)
        raise


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except (KeyboardInterrupt, asyncio.CancelledError):
        _LOG.info("Fire TV driver stopped by user")
    except Exception as e:
        _LOG.error(f"Fire TV driver crashed: {e}", exc_info=True)