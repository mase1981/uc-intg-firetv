"""
Fire TV Remote Entity Implementation.

:copyright: (c) 2025 by Meir Miyara.
:license: MPL-2.0, see LICENSE for more details.
"""

import logging
from typing import Any, Dict, List, Optional

from ucapi import StatusCodes
from ucapi.remote import Attributes, Features, Remote, States
from ucapi.ui import Buttons

from intg_firetv.apps import FIRE_TV_TOP_APPS
from intg_firetv.config import FireTVConfig
from intg_firetv.device import FireTVDevice
from intg_firetv.client import TokenInvalidError

_LOG = logging.getLogger(__name__)


class FireTVRemote(Remote):
    """Fire TV Remote entity."""

    def __init__(self, device_config: FireTVConfig, device: FireTVDevice):
        self._device = device
        self._device_config = device_config

        entity_id = f"remote.{device_config.identifier}"

        features = [Features.SEND_CMD, Features.ON_OFF, Features.TOGGLE]
        attributes = {Attributes.STATE: States.ON}

        simple_commands = self._build_simple_commands()
        button_mapping = self._create_button_mapping()
        ui_pages = self._create_ui_pages()

        super().__init__(
            entity_id,
            device_config.name,
            features=features,
            attributes=attributes,
            simple_commands=simple_commands,
            button_mapping=button_mapping,
            ui_pages=ui_pages,
            cmd_handler=self._handle_command,
        )

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
            'EPG',
            'SETTINGS',
            'VOLUME_UP',
            'VOLUME_DOWN',
            'MUTE',
            'POWER',
            'SLEEP',
            'PLAY_PAUSE',
            'PAUSE',
            'FAST_FORWARD',
            'REWIND',
            'LAUNCH_NETFLIX',
            'LAUNCH_PRIME_VIDEO',
            'LAUNCH_DISNEY_PLUS',
            'LAUNCH_PLEX',
            'LAUNCH_KODI',
            '0',
            '1',
            '2',
            '3',
            '4',
            '5',
            '6',
            '7',
            '8',
            '9'
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
            (Buttons.HOME, 'HOME', None),
            (Buttons.MENU, 'MENU', None),
            (Buttons.PLAY, 'PLAY_PAUSE', None),
            (Buttons.PREV, 'REWIND', None),
            (Buttons.NEXT, 'FAST_FORWARD', None),
            (Buttons.VOLUME_UP, 'VOLUME_UP', None),
            (Buttons.VOLUME_DOWN, 'VOLUME_DOWN', None),
            (Buttons.MUTE, 'MUTE', None),
            (Buttons.POWER, 'POWER', None),
            (Buttons.RED, 'LAUNCH_NETFLIX', None),
            (Buttons.GREEN, 'LAUNCH_PRIME_VIDEO', None),
            (Buttons.YELLOW, 'LAUNCH_DISNEY_PLUS', None),
            (Buttons.BLUE, 'LAUNCH_PLEX', None),
        ]

        for button, short_cmd, long_cmd in button_configs:
            mapping_dict = {
                'button': button.value,
                'short_press': {
                    'cmd_id': short_cmd
                } if short_cmd else None,
                'long_press': {
                    'cmd_id': long_cmd
                } if long_cmd else None,
            }
            mappings.append(mapping_dict)

        return mappings

    def _create_ui_pages(self) -> List[Dict[str, Any]]:
        return [
            self._create_navigation_page(),
            self._create_top_apps_page(),
            self._create_number_page(),
            self._create_custom_apps_page(),
        ]

    def _create_navigation_page(self) -> Dict[str, Any]:
        return {
            'page_id': 'navigation',
            'name': 'Navigation',
            'grid': {'width': 4, 'height': 6},
            'items': [
                {'type': 'text', 'location': {'x': 1, 'y': 0}, 'text': 'UP',
                 'command': {'cmd_id': 'DPAD_UP'}},
                {'type': 'text', 'location': {'x': 0, 'y': 1}, 'text': 'LEFT',
                 'command': {'cmd_id': 'DPAD_LEFT'}},
                {'type': 'text', 'location': {'x': 1, 'y': 1}, 'text': 'OK',
                 'command': {'cmd_id': 'SELECT'}},
                {'type': 'text', 'location': {'x': 2, 'y': 1}, 'text': 'RIGHT',
                 'command': {'cmd_id': 'DPAD_RIGHT'}},
                {'type': 'text', 'location': {'x': 1, 'y': 2}, 'text': 'DOWN',
                 'command': {'cmd_id': 'DPAD_DOWN'}},
                {'type': 'text', 'location': {'x': 3, 'y': 0}, 'text': 'HOME',
                 'command': {'cmd_id': 'HOME'}},
                {'type': 'text', 'location': {'x': 3, 'y': 1}, 'text': 'BACK',
                 'command': {'cmd_id': 'BACK'}},
                {'type': 'text', 'location': {'x': 3, 'y': 2}, 'text': 'MENU',
                 'command': {'cmd_id': 'MENU'}},
                {'type': 'text', 'location': {'x': 3, 'y': 3}, 'text': 'SET',
                 'command': {'cmd_id': 'LAUNCH_SETTINGS'}},
                {'type': 'text', 'location': {'x': 0, 'y': 3}, 'text': 'VOL-',
                 'command': {'cmd_id': 'VOLUME_DOWN'}},
                {'type': 'text', 'location': {'x': 1, 'y': 3}, 'text': 'MUTE',
                 'command': {'cmd_id': 'MUTE'}},
                {'type': 'text', 'location': {'x': 2, 'y': 3}, 'text': 'VOL+',
                 'command': {'cmd_id': 'VOLUME_UP'}},
                {'type': 'text', 'location': {'x': 0, 'y': 4}, 'text': 'REW',
                 'command': {'cmd_id': 'REWIND'}},
                {'type': 'text', 'location': {'x': 1, 'y': 4}, 'text': 'PLAY',
                 'command': {'cmd_id': 'PLAY_PAUSE'}},
                {'type': 'text', 'location': {'x': 2, 'y': 4}, 'text': 'FWD',
                 'command': {'cmd_id': 'FAST_FORWARD'}},
                {'type': 'text', 'location': {'x': 0, 'y': 5}, 'text': 'POWER',
                 'command': {'cmd_id': 'POWER'}},
                {'type': 'text', 'location': {'x': 1, 'y': 5}, 'text': 'SLEEP',
                 'command': {'cmd_id': 'SLEEP'}},
                {'type': 'text', 'location': {'x': 2, 'y': 5}, 'text': 'EPG',
                 'command': {'cmd_id': 'EPG'}},
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
                    'command': {'cmd_id': f'LAUNCH_{cmd_name}'}
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

    def _create_number_page(self) -> Dict[str, Any]:
        return {
            'page_id': 'keypad',
            'name': 'Keypad',
            'grid': {'width': 3, 'height': 4},
            'items': [
                {'type': 'text', 'location': {'x': 0, 'y': 0}, 'text': '1', 'command': {'cmd_id': "text:1"}},
                {'type': 'text', 'location': {'x': 1, 'y': 0}, 'text': '2', 'command': {'cmd_id': "text:2"}},
                {'type': 'text', 'location': {'x': 2, 'y': 0}, 'text': '3', 'command': {'cmd_id': "text:3"}},
                {'type': 'text', 'location': {'x': 0, 'y': 1}, 'text': '4', 'command': {'cmd_id': "text:4"}},
                {'type': 'text', 'location': {'x': 1, 'y': 1}, 'text': '5', 'command': {'cmd_id': "text:5"}},
                {'type': 'text', 'location': {'x': 2, 'y': 1}, 'text': '6', 'command': {'cmd_id': "text:6"}},
                {'type': 'text', 'location': {'x': 0, 'y': 2}, 'text': '7', 'command': {'cmd_id': "text:7"}},
                {'type': 'text', 'location': {'x': 1, 'y': 2}, 'text': '8', 'command': {'cmd_id': "text:8"}},
                {'type': 'text', 'location': {'x': 2, 'y': 2}, 'text': '9', 'command': {'cmd_id': "text:9"}},
                {'type': 'text', 'location': {'x': 0, 'y': 3}, 'text': '<', 'command': {'cmd_id': "REWIND"}},
                {'type': 'text', 'location': {'x': 1, 'y': 3}, 'text': '0', 'command': {'cmd_id': "text:0"}},
                {'type': 'text', 'location': {'x': 2, 'y': 3}, 'text': '>', 'command': {'cmd_id': "FAST_FORWARD"}},
            ]
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
                'command': {'cmd_id': cmd}
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

    async def _handle_command(
        self,
        entity: Remote,
        cmd_id: str,
        params: Optional[Dict[str, Any]] = None
    ) -> StatusCodes:
        """Handle remote commands."""
        _LOG.info("[%s] Command: %s %s", self.id, cmd_id, params or "")

        try:
            if cmd_id == "send_cmd" and params and 'command' in params:
                command = params['command']
                success = await self._device.send_command(command)
                return StatusCodes.OK if success else StatusCodes.SERVER_ERROR

            elif cmd_id == "on":
                self.attributes[Attributes.STATE] = States.ON
                return StatusCodes.OK

            elif cmd_id == "off":
                self.attributes[Attributes.STATE] = States.OFF
                return StatusCodes.OK

            elif cmd_id == "toggle":
                new_state = States.OFF if self.attributes[Attributes.STATE] == States.ON else States.ON
                self.attributes[Attributes.STATE] = new_state
                return StatusCodes.OK

            else:
                _LOG.warning("[%s] Unhandled command: %s", self.id, cmd_id)
                return StatusCodes.NOT_IMPLEMENTED

        except TokenInvalidError as e:
            _LOG.error("[%s] AUTHENTICATION TOKEN INVALID: %s", self.id, e)
            _LOG.error("[%s] User must re-run setup to obtain new authentication token", self.id)
            return StatusCodes.UNAUTHORIZED

        except Exception as e:
            _LOG.error("[%s] Error executing command: %s", self.id, e, exc_info=True)
            return StatusCodes.SERVER_ERROR
