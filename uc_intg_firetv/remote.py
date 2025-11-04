"""
Fire TV Remote Entity Implementation.

:copyright: (c) 2025 by Meir Miyara.
:license: MIT, see LICENSE for more details.
"""

import logging
from typing import Any, Dict, List, Optional

from ucapi import StatusCodes
from ucapi.remote import Attributes, Features, Remote, States
from ucapi.ui import Buttons

from uc_intg_firetv.apps import FIRE_TV_TOP_APPS, get_app_package, validate_package_name

_LOG = logging.getLogger(__name__)


class FireTVRemote(Remote):

    def __init__(self, device_id: str, device_name: str):
        features = [Features.SEND_CMD, Features.ON_OFF, Features.TOGGLE]
        attributes = {Attributes.STATE: States.ON}
        
        simple_commands = self._build_simple_commands()
        button_mapping = self._create_button_mapping()
        ui_pages = self._create_ui_pages()
        
        super().__init__(
            identifier=f"{device_id}_remote",
            name=f"{device_name} Remote",
            features=features,
            attributes=attributes,
            simple_commands=simple_commands,
            button_mapping=button_mapping,
            ui_pages=ui_pages,
            cmd_handler=self._handle_command,
        )
        
        self._client = None
        self._api = None

    def set_client(self, client):
        """Set the Fire TV client."""
        self._client = client

    def set_api(self, api):
        """Set the integration API for state updates."""
        self._api = api

    def _build_simple_commands(self) -> List[str]:
        commands = [
            'DPAD_UP',
            'DPAD_DOWN',
            'DPAD_LEFT',
            'DPAD_RIGHT',
            'SELECT',
            'HOME',
            'BACK',
            'MENU',
            'PLAY_PAUSE',
            'FAST_FORWARD',
            'REWIND',
            'NEXT',
            'PREVIOUS',
            'LAUNCH_NETFLIX',
            'LAUNCH_PRIME_VIDEO',
            'LAUNCH_DISNEY_PLUS',
            'LAUNCH_PLEX',
            'LAUNCH_KODI',
        ]
        
        return commands

    def _create_button_mapping(self) -> List[Dict]:
        mappings = []
        
        button_configs = [
            (Buttons.DPAD_UP, 'DPAD_UP', None),
            (Buttons.DPAD_DOWN, 'DPAD_DOWN', None),
            (Buttons.DPAD_LEFT, 'DPAD_LEFT', None),
            (Buttons.DPAD_RIGHT, 'DPAD_RIGHT', None),
            (Buttons.DPAD_MIDDLE, 'SELECT', None),
            (Buttons.BACK, 'BACK', None),
            (Buttons.HOME, 'HOME', 'MENU'),
            (Buttons.PLAY, 'PLAY_PAUSE', None),
            (Buttons.CHANNEL_UP, 'NEXT', None),
            (Buttons.CHANNEL_DOWN, 'PREVIOUS', None),
            (Buttons.RED, 'LAUNCH_NETFLIX', None),
            (Buttons.GREEN, 'LAUNCH_PRIME_VIDEO', None),
            (Buttons.YELLOW, 'LAUNCH_DISNEY_PLUS', None),
            (Buttons.BLUE, 'LAUNCH_PLEX', None),
        ]
        
        for button, short_cmd, long_cmd in button_configs:
            mapping_dict = {
                'button': button.value,
                'short_press': {
                    'cmd_id': 'send_cmd',
                    'params': {'command': short_cmd}
                } if short_cmd else None,
                'long_press': {
                    'cmd_id': 'send_cmd',
                    'params': {'command': long_cmd}
                } if long_cmd else None,
            }
            mappings.append(mapping_dict)
        
        return mappings

    def _create_ui_pages(self) -> List[Dict[str, Any]]:
        return [
            self._create_navigation_page(),
            self._create_top_apps_page(),
            self._create_custom_apps_page(),
        ]

    def _create_navigation_page(self) -> Dict[str, Any]:
        return {
            'page_id': 'navigation',
            'name': 'Navigation',
            'grid': {'width': 4, 'height': 6},
            'items': [
                {'type': 'text', 'location': {'x': 1, 'y': 0}, 'text': 'UP',
                 'command': {'cmd_id': 'send_cmd', 'params': {'command': 'DPAD_UP'}}},
                {'type': 'text', 'location': {'x': 0, 'y': 1}, 'text': 'LEFT',
                 'command': {'cmd_id': 'send_cmd', 'params': {'command': 'DPAD_LEFT'}}},
                {'type': 'text', 'location': {'x': 1, 'y': 1}, 'text': 'OK',
                 'command': {'cmd_id': 'send_cmd', 'params': {'command': 'SELECT'}}},
                {'type': 'text', 'location': {'x': 2, 'y': 1}, 'text': 'RIGHT',
                 'command': {'cmd_id': 'send_cmd', 'params': {'command': 'DPAD_RIGHT'}}},
                {'type': 'text', 'location': {'x': 1, 'y': 2}, 'text': 'DOWN',
                 'command': {'cmd_id': 'send_cmd', 'params': {'command': 'DPAD_DOWN'}}},
                {'type': 'text', 'location': {'x': 3, 'y': 0}, 'text': 'HOME',
                 'command': {'cmd_id': 'send_cmd', 'params': {'command': 'HOME'}}},
                {'type': 'text', 'location': {'x': 3, 'y': 1}, 'text': 'BACK',
                 'command': {'cmd_id': 'send_cmd', 'params': {'command': 'BACK'}}},
                {'type': 'text', 'location': {'x': 3, 'y': 2}, 'text': 'MENU',
                 'command': {'cmd_id': 'send_cmd', 'params': {'command': 'MENU'}}},
                {'type': 'text', 'location': {'x': 0, 'y': 3}, 'text': 'PREV',
                 'command': {'cmd_id': 'send_cmd', 'params': {'command': 'PREVIOUS'}}},
                {'type': 'text', 'location': {'x': 1, 'y': 3}, 'text': 'PLAY',
                 'command': {'cmd_id': 'send_cmd', 'params': {'command': 'PLAY_PAUSE'}}},
                {'type': 'text', 'location': {'x': 2, 'y': 3}, 'text': 'NEXT',
                 'command': {'cmd_id': 'send_cmd', 'params': {'command': 'NEXT'}}},
                {'type': 'text', 'location': {'x': 0, 'y': 4}, 'text': 'REW',
                 'command': {'cmd_id': 'send_cmd', 'params': {'command': 'REWIND'}}},
                {'type': 'text', 'location': {'x': 2, 'y': 4}, 'text': 'FWD',
                 'command': {'cmd_id': 'send_cmd', 'params': {'command': 'FAST_FORWARD'}}},
            ]
        }

    def _create_top_apps_page(self) -> Dict[str, Any]:
        items = []
        
        top_apps = [
            ('netflix', 'Netflix', 0, 0),
            ('prime_video', 'Prime', 1, 0),
            ('disney_plus', 'Disney+', 2, 0),
            ('plex', 'Plex', 0, 1),
            ('kodi', 'Kodi', 1, 1),
        ]
        
        for app_id, label, col, row in top_apps:
            app_data = FIRE_TV_TOP_APPS.get(app_id)
            if app_data:
                cmd_name = app_data['name'].upper().replace(' ', '_').replace('+', 'PLUS')
                items.append({
                    'type': 'text',
                    'location': {'x': col, 'y': row},
                    'text': label,
                    'command': {'cmd_id': 'send_cmd', 'params': {'command': f'LAUNCH_{cmd_name}'}}
                })
        
        items.append({
            'type': 'text',
            'location': {'x': 0, 'y': 3},
            'size': {'width': 4, 'height': 1},
            'text': 'Custom Apps Page for more',
            'command': None
        })
        
        return {
            'page_id': 'top_apps',
            'name': 'Top Apps',
            'grid': {'width': 4, 'height': 6},
            'items': items
        }

    def _create_custom_apps_page(self) -> Dict[str, Any]:
        items = []
        
        items.append({
            'type': 'text',
            'location': {'x': 0, 'y': 0},
            'size': {'width': 4, 'height': 2},
            'text': 'Launch ANY app using:\ncustom_app:com.package.name',
            'command': None
        })
        
        examples = [
            ('Example:\nHulu', 'custom_app:com.hulu.plus', 0, 2),
            ('Example:\nYouTube', 'custom_app:com.amazon.firetv.youtube', 2, 2),
            ('Example:\nSpotify', 'custom_app:com.spotify.tv.android', 0, 3),
            ('Example:\nVLC', 'custom_app:org.videolan.vlc', 2, 3),
        ]
        
        for label, cmd, col, row in examples:
            items.append({
                'type': 'text',
                'location': {'x': col, 'y': row},
                'size': {'width': 2, 'height': 1},
                'text': label,
                'command': {'cmd_id': 'send_cmd', 'params': {'command': cmd}}
            })
        
        items.append({
            'type': 'text',
            'location': {'x': 0, 'y': 5},
            'size': {'width': 4, 'height': 1},
            'text': 'Find package names in app settings',
            'command': None
        })
        
        return {
            'page_id': 'custom_apps',
            'name': 'Custom Apps',
            'grid': {'width': 4, 'height': 6},
            'items': items
        }

    async def push_initial_state(self):
        if not self._api:
            _LOG.warning("API not set, cannot push state")
            return
        
        if not self._api.configured_entities.contains(self.id):
            _LOG.debug("Entity %s not subscribed yet, skipping state push", self.id)
            return
        
        _LOG.info("Pushing initial state for %s: ON", self.id)
        
        self._api.configured_entities.update_attributes(
            self.id,
            {Attributes.STATE: States.ON}
        )
        
        _LOG.info("âœ… Initial state pushed successfully")

    async def _handle_command(
        self,
        entity,
        cmd_id: str,
        params: Optional[Dict[str, Any]] = None
    ) -> StatusCodes:
        if not self._client:
            _LOG.error("Client not initialized")
            return StatusCodes.SERVER_ERROR
        
        try:
            _LOG.info("Handling command: %s with params: %s", cmd_id, params)
            
            if cmd_id == "send_cmd" and params and 'command' in params:
                command = params['command']
                await self._execute_command(command)
                
            elif cmd_id == "on":
                self.attributes[Attributes.STATE] = States.ON
                if self._api:
                    self._api.configured_entities.update_attributes(
                        self.id, {Attributes.STATE: States.ON}
                    )
                
            elif cmd_id == "off":
                self.attributes[Attributes.STATE] = States.OFF
                if self._api:
                    self._api.configured_entities.update_attributes(
                        self.id, {Attributes.STATE: States.OFF}
                    )
                
            elif cmd_id == "toggle":
                new_state = States.OFF if self.attributes[Attributes.STATE] == States.ON else States.ON
                self.attributes[Attributes.STATE] = new_state
                if self._api:
                    self._api.configured_entities.update_attributes(
                        self.id, {Attributes.STATE: new_state}
                    )
                
            else:
                _LOG.warning("Unhandled command: %s", cmd_id)
                return StatusCodes.NOT_IMPLEMENTED
            
            return StatusCodes.OK
            
        except Exception as e:
            _LOG.error("Error executing command: %s", e, exc_info=True)
            return StatusCodes.SERVER_ERROR

    async def _execute_command(self, command: str):
        _LOG.info("Executing command: %s", command)
        
        command_lower = command.lower()
        
        if command.startswith('custom_app:'):
            try:
                package = command.split(':', 1)[1].strip()
                
                if not validate_package_name(package):
                    _LOG.error("Invalid package name format: %s", package)
                    _LOG.error("Package must be in format: com.company.app")
                    return
                
                _LOG.info("Launching custom app with package: %s", package)
                success = await self._client.launch_app(package)
                
                if success:
                    _LOG.info("Successfully launched custom app: %s", package)
                else:
                    _LOG.warning("Failed to launch custom app: %s", package)
                    _LOG.warning("Check if app is installed on Fire TV")
                
                return
                
            except Exception as e:
                _LOG.error("Error launching custom app: %s", e)
                return
        
        nav_commands = {
            'dpad_up': self._client.dpad_up,
            'dpad_down': self._client.dpad_down,
            'dpad_left': self._client.dpad_left,
            'dpad_right': self._client.dpad_right,
            'select': self._client.select,
            'home': self._client.home,
            'back': self._client.back,
            'menu': self._client.menu,
        }
        
        if command_lower in nav_commands:
            await nav_commands[command_lower]()
            return
        
        media_commands = {
            'play_pause': self._client.play_pause,
            'fast_forward': self._client.fast_forward,
            'rewind': self._client.rewind,
            'next': self._client.next,
            'previous': self._client.previous,
        }
        
        if command_lower in media_commands:
            await media_commands[command_lower]()
            return
        
        if command.startswith('LAUNCH_'):
            app_name = command.replace('LAUNCH_', '').lower()
            
            package = None
            for app_id, app_data in FIRE_TV_TOP_APPS.items():
                if app_data['name'].upper().replace(' ', '_').replace('+', 'PLUS') == command.replace('LAUNCH_', ''):
                    package = app_data['package']
                    break
            
            if package:
                _LOG.info("Launching top app: %s (package: %s)", command, package)
                await self._client.launch_app(package)
            else:
                _LOG.warning("Unknown app command: %s", command)
            return
        
        _LOG.warning("Unhandled command: %s", command)