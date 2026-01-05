"""
Application Settings Module
===========================

Handles persistent storage and retrieval of application settings.
Settings are stored in an INI config file in the user's config directory.

Config file location:
- Linux: ~/.config/citysketch/settings.ini
- Windows: %APPDATA%/citysketch/settings.ini
- macOS: ~/Library/Application Support/citysketch/settings.ini
"""

import ast
import configparser
import os
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, Optional

import wx


# =============================================================================
# Configuration File Handling
# =============================================================================

def get_config_dir() -> Path:
    """
    Get the platform-specific configuration directory.
    
    Returns:
        Path to the configuration directory.
    """
    if sys.platform == 'win32':
        base = Path(os.environ.get('APPDATA', Path.home()))
    elif sys.platform == 'darwin':
        base = Path.home() / 'Library' / 'Application Support'
    else:
        # Linux and other Unix-like systems
        base = Path(os.environ.get('XDG_CONFIG_HOME', Path.home() / '.config'))
    
    config_dir = base / 'citysketch'
    return config_dir


def get_config_file() -> Path:
    """
    Get the path to the settings configuration file.
    
    Returns:
        Path to the settings.ini file.
    """
    return get_config_dir() / 'settings.ini'


def ensure_config_dir():
    """Create the configuration directory if it doesn't exist."""
    config_dir = get_config_dir()
    config_dir.mkdir(parents=True, exist_ok=True)


# =============================================================================
# Settings Classes
# =============================================================================

@dataclass
class Definition:
    """Definition of a setting with value and description."""
    value: Any
    description: str


class Definitions(dict):
    """Dictionary of setting definitions."""
    def __init__(self, values: Optional[Dict[str, Definition]] = None):
        super().__init__()
        if values:
            self.update(values)


class Settings:
    """
    Centralized settings manager for the application.
    
    Handles loading, saving, and accessing settings with type checking
    and default value management.
    """
    _defaults = Definitions()
    _values = Definitions()

    def __init__(self, defaults: Definitions, section: str = 'general'):
        """
        Initialize settings with default definitions.
        
        Args:
            defaults: Dictionary of default setting definitions.
            section: Section name for this settings group in the config file.
        """
        self._defaults = defaults
        self._section = section
        self._initialized = False

    def _ensure_initialized(self):
        """Ensure params are initialized (called on first access)."""
        if not self._initialized:
            self._load_defaults()
            self._initialized = True

    def _load_defaults(self):
        """Load default values."""
        for key, definition in self._defaults.items():
            self._values[key] = Definition(definition.value,
                                           definition.description)

    def get(self, key: str) -> Any:
        """Get setting value by key."""
        self._ensure_initialized()
        if key not in self._values:
            raise KeyError(f"Parameter '{key}' not defined")
        return self._values[key].value

    def get_default(self, key: str) -> Any:
        """Get default value by key."""
        if key not in self._defaults:
            raise KeyError(f"Parameter '{key}' not defined")
        return self._defaults[key].value

    def set(self, key: str, value: Any):
        """Set setting value by key with type checking."""
        self._ensure_initialized()
        if key not in self._defaults:
            raise KeyError(f"Parameter '{key}' not defined")
        
        default_value = self._defaults[key].value
        default_type = type(default_value)
        
        # Handle wx.Colour specially
        if isinstance(default_value, wx.Colour):
            if isinstance(value, wx.Colour):
                self._values[key].value = value
            elif isinstance(value, (tuple, list)) and len(value) >= 3:
                self._values[key].value = wx.Colour(*value)
            else:
                raise TypeError(f"Parameter '{key}' must be a wx.Colour or tuple")
        elif not isinstance(value, default_type):
            # Try to cast to the correct type
            try:
                value = default_type(value)
            except (ValueError, TypeError):
                raise TypeError(f"Parameter '{key}' must be of type {default_type}")
        
        self._values[key].value = value

    def get_description(self, key: str) -> str:
        """Get description for a setting."""
        if key not in self._defaults:
            raise KeyError(f"Parameter '{key}' not defined")
        return self._defaults[key].description

    def get_all_keys(self):
        """Get all available setting keys."""
        self._ensure_initialized()
        return list(self._defaults.keys())

    def reset_to_defaults(self):
        """Reset all settings to default values."""
        for key in self._defaults.keys():
            self.reset_param_to_default(key)

    def reset_param_to_default(self, key: str):
        """Reset a specific setting to its default value."""
        if key not in self._defaults:
            raise KeyError(f"Parameter '{key}' not defined")
        self._ensure_initialized()
        self._values[key].value = self._defaults[key].value

    def from_dict(self, dictionary: Dict):
        """Load settings from a dictionary (case-insensitive key matching)."""
        self._ensure_initialized()
        
        # Build a case-insensitive lookup map: lowercase -> original key
        key_map = {k.lower(): k for k in self._defaults.keys()}
        
        for k, v in dictionary.items():
            # Look up the original key using case-insensitive match
            original_key = key_map.get(k.lower())
            if original_key is None:
                # Skip unknown keys (for forward compatibility)
                continue
            try:
                default_value = self._defaults[original_key].value
                
                # Handle wx.Colour specially
                if isinstance(default_value, wx.Colour):
                    if isinstance(v, (list, tuple)) and len(v) >= 3:
                        self._values[original_key].value = wx.Colour(*v)
                    elif isinstance(v, str):
                        # Parse string representation like "200, 200, 200, 255"
                        parts = [int(x.strip()) for x in v.split(',')]
                        if len(parts) >= 3:
                            self._values[original_key].value = wx.Colour(*parts)
                else:
                    # For other types, interpret from string if needed
                    if isinstance(v, str):
                        # Handle boolean specially
                        if isinstance(default_value, bool):
                            value = v.lower() in ('true', 'yes', '1', 'on')
                        # Handle empty strings for string types
                        elif isinstance(default_value, str):
                            value = v
                        else:
                            value = ast.literal_eval(v)
                    else:
                        value = v
                    self._values[original_key].value = type(default_value)(value)
            except (ValueError, TypeError, SyntaxError):
                # Keep default on parse error
                pass
        return True

    def to_dict(self) -> Dict:
        """Export settings to a dictionary suitable for INI serialization."""
        self._ensure_initialized()
        result = {}
        for key in self.get_all_keys():
            value = self.get(key)
            # Handle wx.Colour specially - format as "R, G, B, A"
            if isinstance(value, wx.Colour):
                result[key] = f"{value.Red()}, {value.Green()}, {value.Blue()}, {value.Alpha()}"
            else:
                result[key] = str(value)
        return result


# =============================================================================
# Persistent Settings Manager
# =============================================================================

class SettingsManager:
    """
    Manages multiple Settings instances and handles persistent storage.
    Uses INI format for human-readable config files.
    """
    
    def __init__(self):
        self._settings_groups: Dict[str, Settings] = {}
    
    def register(self, name: str, settings: Settings):
        """Register a settings group."""
        self._settings_groups[name] = settings
    
    def load_from_file(self) -> bool:
        """
        Load all settings from the config file.
        
        Returns:
            True if settings were loaded successfully, False otherwise.
        """
        config_file = get_config_file()
        if not config_file.exists():
            return False
        
        try:
            config = configparser.ConfigParser()
            config.read(config_file, encoding='utf-8')
            
            for name, settings_obj in self._settings_groups.items():
                if config.has_section(name):
                    section_dict = dict(config.items(name))
                    settings_obj.from_dict(section_dict)
            
            return True
        except (configparser.Error, IOError, OSError) as e:
            print(f"Warning: Could not load settings: {e}")
            return False
    
    def save_to_file(self) -> bool:
        """
        Save all settings to the config file.
        
        Returns:
            True if settings were saved successfully, False otherwise.
        """
        try:
            ensure_config_dir()
            config_file = get_config_file()
            
            config = configparser.ConfigParser()
            
            for name, settings_obj in self._settings_groups.items():
                config[name] = settings_obj.to_dict()
            
            with open(config_file, 'w', encoding='utf-8') as f:
                # Write a header comment
                f.write("# CitySketch Settings\n")
                f.write("# This file is auto-generated. Edit with care.\n\n")
                config.write(f)
            
            return True
        except (IOError, OSError) as e:
            print(f"Warning: Could not save settings: {e}")
            return False
    
    def get_config_file_path(self) -> str:
        """Get the path to the config file as a string."""
        return str(get_config_file())


# =============================================================================
# Setting Definitions
# =============================================================================

PARAMETER_DEFINITIONS = Definitions({
    # UI Settings
    'ZOOM_STEP_PERCENT': Definition(
        20, 'Zoom step percentage'
    ),
    'CIRCLE_CORNERS': Definition(
        12, 'Corners of a polygon representing circle'
    ),
    
    # Paths
    'GBA_DIRECTORY': Definition(
        '', 'Global Building Atlas directory path'
    ),
    
    # GeoJSON Import Settings
    'HEIGHT_TOLERANCE': Definition(
        0.10, 'Height tolerance for merging buildings (ratio, e.g., 0.10 = 10%)'
    ),
    'ANGLE_TOLERANCE': Definition(
        15.0, 'Angle tolerance for rectangle detection (degrees)'
    ),
    'DISTANCE_TOLERANCE': Definition(
        2.0, 'Distance tolerance for shape simplification (meters)'
    ),
    'MAX_NON_OVERLAP_RATIO': Definition(
        0.20, 'Maximum non-overlap ratio for rectangle fitting (ratio, e.g., 0.20 = 20%)'
    ),
    'MAX_CENTER_DISTANCE': Definition(
        10.0, 'Maximum center distance for AUSTAL import (meters)'
    ),
})


COLOR_DEFINITIONS = Definitions({
    # Tile colors
    'COL_TILE_EMPTY': Definition(
        wx.Colour(200, 200, 200, 255), 'Empty map tile background'
    ),
    'COL_TILE_EDGE': Definition(
        wx.Colour(240, 240, 240, 255), 'Map tile edge border'
    ),

    # Grid colors
    'COL_GRID': Definition(
        wx.Colour(220, 220, 220, 255), 'Background grid lines'
    ),

    # Building preview colors
    'COL_FLOAT_IN': Definition(
        wx.Colour(100, 255, 100, 100), 'Building preview fill'
    ),
    'COL_FLOAT_OUT': Definition(
        wx.Colour(0, 200, 0, 255), 'Building preview outline'
    ),

    # Building colors
    'COL_BLDG_IN': Definition(
        wx.Colour(200, 200, 200, 180), 'Building interior fill'
    ),
    'COL_BLDG_OUT': Definition(
        wx.Colour(100, 100, 100, 255), 'Building outline border'
    ),
    'COL_BLDG_LBL': Definition(
        wx.Colour(255, 255, 255, 255), 'Building label text'
    ),

    # Selected building colors
    'COL_SEL_BLDG_IN': Definition(
        wx.Colour(150, 180, 255, 180), 'Selected building interior fill'
    ),
    'COL_SEL_BLDG_OUT': Definition(
        wx.Colour(0, 0, 255, 255), 'Selected building outline border'
    ),

    # Handle colors
    'COL_HANDLE_IN': Definition(
        wx.Colour(255, 255, 255, 255), 'Selection handle interior'
    ),
    'COL_HANDLE_OUT': Definition(
        wx.Colour(0, 0, 255, 255), 'Selection handle outline'
    ),
})


# =============================================================================
# Global Instances
# =============================================================================

# Create settings instances
colorset = Settings(COLOR_DEFINITIONS, section='colors')
settings = Settings(PARAMETER_DEFINITIONS, section='settings')

# Create and configure the settings manager
settings_manager = SettingsManager()
settings_manager.register('colors', colorset)
settings_manager.register('settings', settings)


def load_settings():
    """Load settings from the config file at application startup."""
    return settings_manager.load_from_file()


def save_settings():
    """Save settings to the config file."""
    return settings_manager.save_to_file()


def get_settings_file_path() -> str:
    """Get the path to the settings file."""
    return settings_manager.get_config_file_path()
