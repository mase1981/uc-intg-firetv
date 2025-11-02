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

from uc_intg_firetv.apps import FIRE_TV_APPS, get_app_package

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
            # Navigation commands
            'DPAD_UP',
            'DPAD_DOWN',
            'DPAD_LEFT',
            'DPAD_RIGHT',
            'SELECT',
            'HOME',
            'BACK',
            'MENU',
            
            # Media commands
            'PLAY_PAUSE',
            'FAST_FORWARD',
            'REWIND',
        ]
        
        # Add app launch commands with readable names
        for app_id, app_data in FIRE_TV_APPS.items():
            app_name = app_data['name'].upper().replace(' ', '_').replace('+', 'PLUS')
            commands.append(f'LAUNCH_{app_name}')
        
        return commands

    def _create_button_mapping(self) -> List[Dict]:
        mappings = []
        
        # Core button mappings
        button_configs = [
            # D-Pad navigation
            (Buttons.DPAD_UP, 'DPAD_UP', None),
            (Buttons.DPAD_DOWN, 'DPAD_DOWN', None),
            (Buttons.DPAD_LEFT, 'DPAD_LEFT', None),
            (Buttons.DPAD_RIGHT, 'DPAD_RIGHT', None),
            (Buttons.DPAD_MIDDLE, 'SELECT', None),
            
            # Navigation buttons
            (Buttons.BACK, 'BACK', None),
            (Buttons.HOME, 'HOME', 'MENU'),
            
            # Media controls
            (Buttons.PLAY, 'PLAY_PAUSE', None),
            
            # Quick app launchers on color buttons
            (Buttons.RED, 'LAUNCH_NETFLIX', None),
            (Buttons.GREEN, 'LAUNCH_PRIME_VIDEO', None),
            (Buttons.YELLOW, 'LAUNCH_YOUTUBE', None),
            (Buttons.BLUE, 'LAUNCH_DISNEY_PLUS', None),
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
            self._create_streaming_apps_page(),
            self._create_music_apps_page(),
            self._create_utility_apps_page(),
        ]

    def _create_navigation_page(self) -> Dict[str, Any]:
        return {
            'page_id': 'navigation',
            'name': 'Navigation',
            'grid': {'width': 4, 'height': 6},
            'items': [
                # D-Pad layout (centered)
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
                
                # System buttons
                {'type': 'text', 'location': {'x': 3, 'y': 0}, 'text': 'HOME',
                 'command': {'cmd_id': 'send_cmd', 'params': {'command': 'HOME'}}},
                {'type': 'text', 'location': {'x': 3, 'y': 1}, 'text': 'BACK',
                 'command': {'cmd_id': 'send_cmd', 'params': {'command': 'BACK'}}},
                {'type': 'text', 'location': {'x': 3, 'y': 2}, 'text': 'MENU',
                 'command': {'cmd_id': 'send_cmd', 'params': {'command': 'MENU'}}},
                
                # Media controls - FIXED: Use text instead of symbols
                {'type': 'text', 'location': {'x': 0, 'y': 4}, 'text': 'REW',
                 'command': {'cmd_id': 'send_cmd', 'params': {'command': 'REWIND'}}},
                {'type': 'text', 'location': {'x': 1, 'y': 4}, 'text': 'PLAY',
                 'command': {'cmd_id': 'send_cmd', 'params': {'command': 'PLAY_PAUSE'}}},
                {'type': 'text', 'location': {'x': 2, 'y': 4}, 'text': 'FWD',
                 'command': {'cmd_id': 'send_cmd', 'params': {'command': 'FAST_FORWARD'}}},
            ]
        }

    def _create_streaming_apps_page(self) -> Dict[str, Any]:
        items = []
        
        # Get streaming apps
        streaming_apps = {
            app_id: app_data
            for app_id, app_data in FIRE_TV_APPS.items()
            if app_data.get('category') == 'streaming'
        }
        
        # Layout apps in grid (4 columns)
        row, col = 0, 0
        for app_id, app_data in list(streaming_apps.items())[:24]:  # Max 24 apps
            if row >= 6:
                break
            
            app_name = app_data['name']
            label = app_name[:8]  # Truncate for UI
            cmd_name = app_name.upper().replace(' ', '_').replace('+', 'PLUS')
            
            items.append({
                'type': 'text',
                'location': {'x': col, 'y': row},
                'text': label,
                'command': {'cmd_id': 'send_cmd', 'params': {'command': f'LAUNCH_{cmd_name}'}}
            })
            
            col += 1
            if col >= 4:
                col = 0
                row += 1
        
        return {
            'page_id': 'streaming',
            'name': 'Streaming',
            'grid': {'width': 4, 'height': 6},
            'items': items
        }

    def _create_music_apps_page(self) -> Dict[str, Any]:
        """
        Create music apps page.
        
        Returns:
            Music apps page dictionary
        """
        items = []
        
        # Get music apps
        music_apps = {
            app_id: app_data
            for app_id, app_data in FIRE_TV_APPS.items()
            if app_data.get('category') == 'music'
        }
        
        # Layout apps in grid
        row, col = 0, 0
        for app_id, app_data in music_apps.items():
            if row >= 5:  # Leave room for media controls at bottom
                break
            
            app_name = app_data['name']
            label = app_name[:10]
            cmd_name = app_name.upper().replace(' ', '_').replace('+', 'PLUS')
            
            items.append({
                'type': 'text',
                'location': {'x': col, 'y': row},
                'text': label,
                'command': {'cmd_id': 'send_cmd', 'params': {'command': f'LAUNCH_{cmd_name}'}}
            })
            
            col += 1
            if col >= 4:
                col = 0
                row += 1
        
        # Add media controls at bottom
        items.extend([
            {'type': 'text', 'location': {'x': 0, 'y': 5}, 'text': 'REW',
             'command': {'cmd_id': 'send_cmd', 'params': {'command': 'REWIND'}}},
            {'type': 'text', 'location': {'x': 1, 'y': 5}, 'text': 'PLAY',
             'command': {'cmd_id': 'send_cmd', 'params': {'command': 'PLAY_PAUSE'}}},
            {'type': 'text', 'location': {'x': 2, 'y': 5}, 'text': 'FWD',
             'command': {'cmd_id': 'send_cmd', 'params': {'command': 'FAST_FORWARD'}}},
        ])
        
        return {
            'page_id': 'music',
            'name': 'Music',
            'grid': {'width': 4, 'height': 6},
            'items': items
        }

    def _create_utility_apps_page(self) -> Dict[str, Any]:
        items = []
        
        # Get utility apps
        utility_apps = {
            app_id: app_data
            for app_id, app_data in FIRE_TV_APPS.items()
            if app_data.get('category') in ['utility', 'system', 'news', 'sports', 'live_tv']
        }
        
        # Layout apps in grid
        row, col = 0, 0
        for app_id, app_data in utility_apps.items():
            if row >= 6:
                break
            
            app_name = app_data['name']
            label = app_name[:10]
            cmd_name = app_name.upper().replace(' ', '_').replace('+', 'PLUS')
            
            items.append({
                'type': 'text',
                'location': {'x': col, 'y': row},
                'text': label,
                'command': {'cmd_id': 'send_cmd', 'params': {'command': f'LAUNCH_{cmd_name}'}}
            })
            
            col += 1
            if col >= 4:
                col = 0
                row += 1
        
        return {
            'page_id': 'utility',
            'name': 'Apps & Settings',
            'grid': {'width': 4, 'height': 6},
            'items': items
        }

    async def push_initial_state(self):
        if not self._api:
            _LOG.warning("API not set, cannot push state")
            return
        
        # Check if entity is in configured_entities (subscribed)
        if not self._api.configured_entities.contains(self.id):
            _LOG.debug("Entity %s not subscribed yet, skipping state push", self.id)
            return
        
        _LOG.info("Pushing initial state for %s: ON", self.id)
        
        # Update attributes to ON state
        self._api.configured_entities.update_attributes(
            self.id,
            {Attributes.STATE: States.ON}
        )
        
        _LOG.info("✅ Initial state pushed successfully")

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
        
        # Map uppercase commands to lowercase API calls
        command_lower = command.lower()
        
        # Navigation commands
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
        
        # Media commands
        if command_lower == 'play_pause':
            await self._client.play_pause()
        elif command_lower == 'fast_forward':
            await self._client.fast_forward()
        elif command_lower == 'rewind':
            await self._client.rewind()
        
        # App launch commands
        elif command.startswith('LAUNCH_'):
            # Convert LAUNCH_NETFLIX -> netflix
            app_name = command.replace('LAUNCH_', '').lower()
            
            # Find app by matching name
            package = None
            for app_id, app_data in FIRE_TV_APPS.items():
                if app_data['name'].upper().replace(' ', '_').replace('+', 'PLUS') == command.replace('LAUNCH_', ''):
                    package = app_data['package']
                    break
            
            if package:
                await self._client.launch_app(package)
            else:
                _LOG.warning("Unknown app command: %s", command)
        
        else:
            _LOG.warning("Unhandled command: %s", command)