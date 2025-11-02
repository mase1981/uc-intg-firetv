"""
Configuration management for Fire TV Integration.

:copyright: (c) 2025 by Meir Miyara.
:license: MIT, see LICENSE for more details.
"""

import json
import logging
import os
from typing import Any, Dict, Optional

_LOG = logging.getLogger(__name__)


class Config:

    def __init__(self):
        self._config_dir = os.getenv("UC_CONFIG_HOME", os.path.join(os.getcwd(), "config"))
        self._config_file = os.path.join(self._config_dir, "config.json")
        self._config: Dict[str, Any] = {}
        os.makedirs(self._config_dir, exist_ok=True)
        _LOG.info("Configuration directory: %s", self._config_dir)

    def load(self):
        try:
            if os.path.exists(self._config_file):
                with open(self._config_file, 'r', encoding='utf-8') as f:
                    self._config = json.load(f)
                _LOG.info("Configuration loaded successfully")
                _LOG.debug("Config contents: %s", self._sanitize_log())
            else:
                _LOG.info("No configuration file found, using defaults")
                self._config = {}
        except Exception as e:
            _LOG.error("Error loading configuration: %s", e)
            self._config = {}

    def save(self):
        try:
            with open(self._config_file, 'w', encoding='utf-8') as f:
                json.dump(self._config, f, indent=2)
            _LOG.info("Configuration saved successfully")
            _LOG.debug("Saved config: %s", self._sanitize_log())
        except Exception as e:
            _LOG.error("Error saving configuration: %s", e)

    def reload_from_disk(self):
        _LOG.info("Reloading configuration from disk...")
        self.load()

    def get(self, key: str, default: Any = None) -> Any:
        return self._config.get(key, default)

    def set(self, key: str, value: Any):
        self._config[key] = value

    def update(self, values: Dict[str, Any]):
        self._config.update(values)

    def is_configured(self) -> bool:
        return bool(self._config.get("host") and self._config.get("token"))

    def get_host(self) -> Optional[str]:
        return self._config.get("host")

    def get_token(self) -> Optional[str]:
        return self._config.get("token")

    def save_token(self, token: str):
        self._config['token'] = token
        self.save()
        _LOG.info("Authentication token saved")

    def clear(self):
        self._config = {}
        if os.path.exists(self._config_file):
            os.remove(self._config_file)
        _LOG.info("Configuration cleared")

    def _sanitize_log(self) -> Dict[str, Any]:
        sanitized = self._config.copy()
        if 'token' in sanitized:
            sanitized['token'] = '***HIDDEN***'
        return sanitized