"""
Fire TV Application Database - Top Apps Only.

Users can launch any other app using the custom_app command:
Example: custom_app:com.package.name

:copyright: (c) 2025 by Meir Miyara.
:license: MIT, see LICENSE for more details.
"""

from typing import Dict, Any

# Top 5 most common Fire TV apps with verified package names
FIRE_TV_TOP_APPS: Dict[str, Dict[str, Any]] = {
    'netflix': {
        'name': 'Netflix',
        'package': 'com.netflix.ninja',
        'category': 'streaming',
        'icon': 'uc:netflix',
    },
    'prime_video': {
        'name': 'Prime Video',
        'package': 'com.amazon.avod',
        'category': 'streaming',
        'icon': 'uc:amazon',
    },
    'disney_plus': {
        'name': 'Disney+',
        'package': 'com.disney.disneyplus',
        'category': 'streaming',
        'icon': 'uc:disney',
    },
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
}


def get_app_by_id(app_id: str) -> Dict[str, Any]:
    """Get app information by ID."""
    return FIRE_TV_TOP_APPS.get(app_id, {})


def get_app_package(app_id: str) -> str:
    """Get app package name by ID."""
    app = FIRE_TV_TOP_APPS.get(app_id, {})
    return app.get('package', '')


def get_all_app_ids() -> list:
    """Get list of all pre-configured app IDs."""
    return list(FIRE_TV_TOP_APPS.keys())


def get_app_names_and_packages() -> Dict[str, str]:
    """
    Get mapping of app names to package names for display.
    
    Returns:
        Dictionary mapping friendly names to package names
    """
    return {
        app_data['name']: app_data['package']
        for app_data in FIRE_TV_TOP_APPS.values()
    }


def validate_package_name(package: str) -> bool:
    """
    Validate that a package name follows Android package naming conventions.
    
    Args:
        package: Package name to validate (e.g., com.example.app)
    
    Returns:
        True if valid package name format
    """
    if not package:
        return False
    
    # Basic validation: must have at least one dot and only alphanumeric/dots
    if '.' not in package:
        return False
    
    parts = package.split('.')
    if len(parts) < 2:
        return False
    
    # Each part should be non-empty and contain only alphanumeric and underscores
    for part in parts:
        if not part:
            return False
        if not all(c.isalnum() or c == '_' for c in part):
            return False
    
    return True


# Common package name patterns for reference
COMMON_PACKAGE_PATTERNS = {
    'YouTube': 'com.amazon.firetv.youtube',
    'Hulu': 'com.hulu.plus',
    'HBO Max': 'com.wbd.stream',
    'Apple TV+': 'com.apple.atve.amazon.appletv',
    'Spotify': 'com.spotify.tv.android',
    'VLC': 'org.videolan.vlc',
    'Silk Browser': 'com.amazon.cloud9.silkbrowser',
    'Settings': 'com.amazon.tv.settings',
}


def get_package_name_examples() -> Dict[str, str]:
    """
    Get examples of common package names for user reference.
    
    Returns:
        Dictionary of app names and their package names
    """
    examples = COMMON_PACKAGE_PATTERNS.copy()
    
    # Add top 5 apps to examples
    for app_data in FIRE_TV_TOP_APPS.values():
        examples[app_data['name']] = app_data['package']
    
    return examples