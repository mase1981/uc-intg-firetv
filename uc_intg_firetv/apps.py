"""
Fire TV Application Database.

:copyright: (c) 2025 by Meir Miyara.
:license: MIT, see LICENSE for more details.
"""

from typing import Dict, Any

# Comprehensive Fire TV application database
FIRE_TV_APPS: Dict[str, Dict[str, Any]] = {
    # Streaming Services - Major
    'netflix': {
        'name': 'Netflix',
        'package': 'com.netflix.ninja',
        'category': 'streaming',
        'icon': 'uc:netflix',
    },
    'prime_video': {
        'name': 'Prime Video',
        'package': 'com.amazon.cloud9',
        'category': 'streaming',
        'icon': 'uc:amazon',
    },
    'youtube': {
        'name': 'YouTube',
        'package': 'com.amazon.firetv.youtube',
        'category': 'streaming',
        'icon': 'uc:youtube',
    },
    'disney_plus': {
        'name': 'Disney+',
        'package': 'com.disney.disneyplus',
        'category': 'streaming',
        'icon': 'uc:disney',
    },
    'hulu': {
        'name': 'Hulu',
        'package': 'com.hulu.plus',
        'category': 'streaming',
        'icon': 'uc:hulu',
    },
    'apple_tv': {
        'name': 'Apple TV+',
        'package': 'com.apple.atve.amazon.appletv',
        'category': 'streaming',
        'icon': 'uc:apple',
    },
    'max': {
        'name': 'Max',
        'package': 'com.wbd.stream',
        'category': 'streaming',
        'icon': 'uc:hbo',
    },
    'paramount_plus': {
        'name': 'Paramount+',
        'package': 'com.cbs.ott',
        'category': 'streaming',
        'icon': 'uc:paramount',
    },
    'peacock': {
        'name': 'Peacock',
        'package': 'com.peacocktv.peacockandroid',
        'category': 'streaming',
        'icon': 'uc:peacock',
    },
    
    # Streaming Services - Regional/International
    'bbc_iplayer': {
        'name': 'BBC iPlayer',
        'package': 'uk.co.bbc.iplayer',
        'category': 'streaming',
        'icon': 'uc:bbc',
    },
    'itv': {
        'name': 'ITV Hub',
        'package': 'air.ITVMobilePlayer',
        'category': 'streaming',
        'icon': 'uc:itv',
    },
    'channel_4': {
        'name': 'Channel 4',
        'package': 'com.channel4.ondemand',
        'category': 'streaming',
        'icon': 'uc:channel4',
    },
    'demand_5': {
        'name': 'My5',
        'package': 'com.mobileiq.demand5',
        'category': 'streaming',
        'icon': 'uc:five',
    },
    'now_tv': {
        'name': 'NOW TV',
        'package': 'com.bskyb.nowtv.beta',
        'category': 'streaming',
        'icon': 'uc:now',
    },
    'sky_news': {
        'name': 'Sky News',
        'package': 'com.onemainstream.skynews.android',
        'category': 'news',
        'icon': 'uc:news',
    },
    
    # Music Services
    'amazon_music': {
        'name': 'Amazon Music',
        'package': 'com.amazon.bueller.music',
        'category': 'music',
        'icon': 'uc:music',
    },
    'spotify': {
        'name': 'Spotify',
        'package': 'com.spotify.tv.android',
        'category': 'music',
        'icon': 'uc:spotify',
    },
    'pandora': {
        'name': 'Pandora',
        'package': 'com.pandora.android.gtv',
        'category': 'music',
        'icon': 'uc:pandora',
    },
    'tidal': {
        'name': 'TIDAL',
        'package': 'com.aspiro.tidal',
        'category': 'music',
        'icon': 'uc:tidal',
    },
    
    # Live TV & Sports
    'pluto_tv': {
        'name': 'Pluto TV',
        'package': 'tv.pluto.android',
        'category': 'live_tv',
        'icon': 'uc:tv',
    },
    'espn': {
        'name': 'ESPN',
        'package': 'com.espn.score_center',
        'category': 'sports',
        'icon': 'uc:espn',
    },
    'nfl': {
        'name': 'NFL',
        'package': 'com.nfl.mobile.android.tv',
        'category': 'sports',
        'icon': 'uc:football',
    },
    
    # Utility & System
    'plex': {
        'name': 'Plex',
        'package': 'com.plexapp.android',
        'category': 'utility',
        'icon': 'uc:plex',
    },
    'kodi': {
        'name': 'Kodi',
        'package': 'org.xbmc.kodi',
        'category': 'utility',
        'icon': 'uc:kodi',
    },
    'vlc': {
        'name': 'VLC',
        'package': 'org.videolan.vlc',
        'category': 'utility',
        'icon': 'uc:video',
    },
    'browser': {
        'name': 'Silk Browser',
        'package': 'com.amazon.cloud9.silkbrowser',
        'category': 'utility',
        'icon': 'uc:browser',
    },
    'settings': {
        'name': 'Settings',
        'package': 'com.amazon.tv.settings',
        'category': 'system',
        'icon': 'uc:settings',
    },
}


def get_app_by_id(app_id: str) -> Dict[str, Any]:
    """Get app information by ID."""
    return FIRE_TV_APPS.get(app_id, {})


def get_app_package(app_id: str) -> str:
    """Get app package name by ID."""
    app = FIRE_TV_APPS.get(app_id, {})
    return app.get('package', '')


def get_apps_by_category(category: str) -> Dict[str, Dict[str, Any]]:
    """Get all apps in a specific category."""
    return {
        app_id: app_data
        for app_id, app_data in FIRE_TV_APPS.items()
        if app_data.get('category') == category
    }


def get_all_app_ids() -> list:
    """Get list of all app IDs."""
    return list(FIRE_TV_APPS.keys())


def get_streaming_apps() -> Dict[str, Dict[str, Any]]:
    """Get all streaming service apps."""
    return get_apps_by_category('streaming')


def get_music_apps() -> Dict[str, Dict[str, Any]]:
    """Get all music service apps."""
    return get_apps_by_category('music')