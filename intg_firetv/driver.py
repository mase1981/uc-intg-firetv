"""
Fire TV driver for Unfolded Circle Remote.

:copyright: (c) 2025 by Meir Miyara.
:license: MPL-2.0, see LICENSE for more details.
"""

import logging
from ucapi_framework import BaseIntegrationDriver
from intg_firetv.config import FireTVConfig
from intg_firetv.device import FireTVDevice
from intg_firetv.remote import FireTVRemote

_LOG = logging.getLogger(__name__)


class FireTVDriver(BaseIntegrationDriver[FireTVDevice, FireTVConfig]):
    """Fire TV integration driver."""

    def __init__(self):
        super().__init__(
            device_class=FireTVDevice,
            entity_classes=[FireTVRemote],
            driver_id="firetv",
        )
