"""
Fire TV configuration for Unfolded Circle integration.

:copyright: (c) 2025 by Meir Miyara.
:license: MPL-2.0, see LICENSE for more details.
"""

from dataclasses import dataclass
from ucapi_framework import BaseConfigManager


@dataclass
class FireTVConfig:
    """Fire TV configuration."""

    identifier: str
    name: str
    host: str
    port: int = 8080
    token: str = ""


class FireTVConfigManager(BaseConfigManager[FireTVConfig]):
    """Configuration manager with automatic JSON persistence."""

    pass
