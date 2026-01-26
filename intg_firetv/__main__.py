"""
Entry point for running as module: python -m intg_firetv

:copyright: (c) 2025 by Meir Miyara.
:license: MPL-2.0, see LICENSE for more details.
"""

import asyncio
from intg_firetv import main

if __name__ == "__main__":
    asyncio.run(main())
