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
    """
    Initialize entities with race condition protection - MANDATORY for reboot survival.
    
    This function MUST complete before any subscription attempts to avoid
    "entity unavailable" issues after system reboots.
    """
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
            token = config.get_token()
            
            _LOG.info("Host: %s", host)
            _LOG.info("Token: %s", token[:10] + "..." if token else "None")
            
            # Create client with saved token
            client = FireTVClient(host, token)
            
            # Test connection
            if not await client.test_connection():
                _LOG.error("Failed to connect to Fire TV at %s", host)
                await api.set_device_state(DeviceStates.ERROR)
                _entities_ready = False
                return
            
            _LOG.info("✅ Connected to Fire TV at %s", host)
            
            # Create remote entity
            device_id = f"firetv_{host.replace('.', '_').replace(':', '_')}"
            device_name = f"Fire TV ({host})"
            
            remote_entity = FireTVRemote(device_id, device_name)
            remote_entity.set_client(client)
            remote_entity.set_api(api)
            
            # Add entities atomically
            api.available_entities.clear()
            api.available_entities.add(remote_entity)
            
            _entities_ready = True
            
            _LOG.info("✅ Fire TV remote entity created: %s", remote_entity.id)
            _LOG.info("✅ Entities ready for subscription")
            _LOG.info("=" * 60)
            
            # Set connected state
            await api.set_device_state(DeviceStates.CONNECTED)
            
        except Exception as e:
            _LOG.error("Failed to initialize entities: %s", e, exc_info=True)
            _entities_ready = False
            await api.set_device_state(DeviceStates.ERROR)
            raise


async def setup_handler(msg: ucapi.SetupDriver) -> ucapi.SetupAction:
    global config, client
    
    _LOG.info("=" * 60)
    _LOG.info("SETUP HANDLER: %s", type(msg).__name__)
    _LOG.info("=" * 60)
    
    # Handle initial setup request with host
    if isinstance(msg, ucapi.DriverSetupRequest):
        _LOG.info("=== SETUP: Driver Setup Request ===")
        setup_data = msg.setup_data
        
        if 'host' in setup_data:
            host = setup_data.get('host')
            _LOG.info("Step 1: Testing connection to Fire TV at %s", host)
            
            # Test connection first
            test_client = FireTVClient(host)
            if not await test_client.test_connection():
                _LOG.error("Cannot reach Fire TV at %s", host)
                await test_client.close()
                return SetupError(IntegrationSetupError.CONNECTION_REFUSED)
            
            # Request PIN display
            _LOG.info("Step 2: Requesting PIN display on Fire TV")
            pin = await test_client.request_pin("UC Remote")
            await test_client.close()
            
            if not pin:
                _LOG.error("Failed to request PIN from Fire TV")
                return SetupError(IntegrationSetupError.OTHER)
            
            # Store host temporarily
            config.set('host', host)
            # Don't save yet - wait for PIN verification
            
            _LOG.info("Step 3: PIN displayed on TV, requesting user input")
            
            # Return user input request for PIN
            return ucapi.RequestUserInput(
                title={"en": "Enter PIN from Fire TV"},
                settings=[
                    {
                        "id": "pin",
                        "label": {"en": "4-Digit PIN"},
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
    
    # Handle user data response with PIN
    elif isinstance(msg, ucapi.UserDataResponse):
        _LOG.info("=== SETUP: User Data Response (PIN Entry) ===")
        
        pin = msg.input_values.get('pin')
        host = config.get_host()
        
        if not host:
            _LOG.error("No host in config - setup flow broken")
            return SetupError(IntegrationSetupError.OTHER)
        
        if not pin:
            _LOG.error("No PIN provided")
            return SetupError(IntegrationSetupError.OTHER)
        
        _LOG.info("Step 4: Verifying PIN '%s'", pin)
        
        # Verify PIN and get token
        verify_client = FireTVClient(host)
        token = await verify_client.verify_pin(pin)
        await verify_client.close()
        
        if not token:
            _LOG.error("PIN verification failed")
            return SetupError(IntegrationSetupError.AUTHORIZATION_ERROR)
        
        # Save configuration with token
        config.set('token', token)
        config.save()
        
        _LOG.info("✅ Configuration saved successfully")
        _LOG.info("Step 5: Setup complete - Initializing entities")
        
        # Initialize entities
        await _initialize_entities()
        
        return SetupComplete()
    
    # Handle user confirmation response (shouldn't happen, but handle gracefully)
    elif isinstance(msg, ucapi.UserConfirmationResponse):
        _LOG.warning("Unexpected UserConfirmationResponse in setup")
        return SetupComplete()
    
    # Handle abort
    elif isinstance(msg, ucapi.AbortDriverSetup):
        _LOG.warning("Setup aborted by user")
        return SetupError(IntegrationSetupError.OTHER)
    
    _LOG.error("Unknown setup message type: %s", type(msg))
    return SetupError(IntegrationSetupError.OTHER)


async def on_connect() -> None:
    global config, _entities_ready
    
    _LOG.info("=" * 60)
    _LOG.info("Remote Two/3 connected")
    _LOG.info("=" * 60)
    
    if not config:
        config = Config()
    
    config.reload_from_disk()
    
    # If configured but entities not ready, initialize them now
    if config.is_configured() and not _entities_ready:
        _LOG.info("Configuration found but entities missing, reinitializing...")
        try:
            await _initialize_entities()
        except Exception as e:
            _LOG.error("Failed to reinitialize entities: %s", e)
            await api.set_device_state(DeviceStates.ERROR)
            return
    
    # Set appropriate device state
    if config.is_configured() and _entities_ready:
        await api.set_device_state(DeviceStates.CONNECTED)
    elif not config.is_configured():
        await api.set_device_state(DeviceStates.DISCONNECTED)
    else:
        await api.set_device_state(DeviceStates.ERROR)


async def on_disconnect() -> None:
    """Handle Remote disconnection."""
    _LOG.info("Remote Two/3 disconnected")


async def on_subscribe_entities(entity_ids: List[str]):
    global remote_entity, _entities_ready
    
    _LOG.info("=" * 60)
    _LOG.info("✅ SUBSCRIPTION EVENT - Entities subscribed: %s", entity_ids)
    _LOG.info("=" * 60)
    
    # Guard against race condition
    if not _entities_ready:
        _LOG.error("RACE CONDITION: Subscription before entities ready! Attempting recovery...")
        if config and config.is_configured():
            await _initialize_entities()
        else:
            _LOG.error("Cannot recover - no configuration available")
            return
    
    for entity_id in entity_ids:
        if remote_entity and entity_id == remote_entity.id:
            _LOG.info("📡 Pushing initial state for remote entity: %s", entity_id)
            await remote_entity.push_initial_state()
            _LOG.info("✅ Remote entity initial state pushed")


async def on_unsubscribe_entities(entity_ids: List[str]):
    _LOG.info("Entities unsubscribed: %s", entity_ids)


async def main():
    global api, config
    
    _LOG.info("=" * 60)
    _LOG.info("🔥 FIRE TV INTEGRATION DRIVER STARTING")
    _LOG.info("=" * 60)
    
    try:
        loop = asyncio.get_running_loop()
        
        # Initialize config
        config = Config()
        config.load()
        
        # Initialize API
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
        
        # Initialize API
        await api.init(os.path.abspath(driver_path), setup_handler)
        
        # Set initial state
        if config.is_configured():
            await api.set_device_state(DeviceStates.CONNECTING)
        else:
            await api.set_device_state(DeviceStates.DISCONNECTED)
        
        _LOG.info("Fire TV driver initialized successfully")
        _LOG.info("=" * 60)
        
        # Run forever
        await asyncio.Future()
        
    except asyncio.CancelledError:
        _LOG.info("Driver task cancelled")
    except Exception as e:
        _LOG.error("Fatal error in main: %s", e, exc_info=True)
        raise


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except (KeyboardInterrupt, asyncio.CancelledError):
        _LOG.info("🔥 Fire TV driver stopped by user")
    except Exception as e:
        _LOG.error("🔥 Fire TV driver crashed: %s", e, exc_info=True)