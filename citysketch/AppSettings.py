from typing import Any, Dict, NamedTuple, Optional, Tuple, Type

import wx


class ColorDefinition(NamedTuple):
    """Defines a color with default value and description"""
    default: Tuple[int, int, int, int]  # RGBA tuple instead of wx.Colour
    description: str

class ParameterDefinition(NamedTuple):
    """Defines a view setting, default value and description"""
    default: Optional[Any]
    type: Type
    description: str

class ParameterSettings:
    """Centralized view params for the application"""

    PARAMETER_DEFINITIONS = {
        'ZOOM_STEP_PERCENT': ParameterDefinition (
            20, int, 'Zoom step percentage'
        )
    }

    def __init__(self):
        self._parameters: Dict[str, Any] = {}
        self._initialized = False

    def _ensure_initialized(self):
        """Ensure params are initialized (called on first access)"""
        if not self._initialized:
            self._load_defaults()
            self._initialized = True

    def _load_defaults(self):
        """Load default color values"""
        for key, definition in self.PARAMETER_DEFINITIONS.items():
            self._parameters[key] = definition.default

    def get(self, key: str) -> wx.Colour:
        """Get params by key"""
        self._ensure_initialized()
        if key not in self._parameters:
            raise KeyError(f"Parameter '{key}' not defined")
        return self._parameters[key]

    def set(self, key: str, value: Any):
        """Set params by key"""
        self._ensure_initialized()
        if key not in self.PARAMETER_DEFINITIONS:
            raise KeyError(f"Parameter '{key}' not defined")
        if not isinstance(value, self._parameters[key]):
            try:
                value = self._parameters[key].type(value)
            except TypeError:
                raise TypeError(f"Parameter '{key}' must "
                                f"be of type {type(value)}")
        self._parameters[key] = value

    def get_definition(self, key: str) -> ParameterDefinition:
        """Get color definition by key"""
        if key not in self.PARAMETER_DEFINITIONS:
            raise KeyError(f"Parameter '{key}' not defined")
        return self.PARAMETER_DEFINITIONS[key]

    def get_all_keys(self):
        """Get all available color keys"""
        return list(self.PARAMETER_DEFINITIONS.keys())

    def reset_to_defaults(self):
        """Reset all params to default params"""
        self._parameters.clear()
        self._initialized = False
        self._ensure_initialized()

    def reset_param_to_default(self, key: str):
        """Reset a specific color to its default param"""
        if key not in self.PARAMETER_DEFINITIONS:
            raise KeyError(f"Parameter '{key}' not defined")
        self._parameters[key] = self.PARAMETER_DEFINITIONS[key].default


class ColorSettings:
    """Centralized color management for the application"""

    # Define all application colors here using RGBA tuples
    COLOR_DEFINITIONS = {
        # Tile colors
        'COL_TILE_EMPTY': ColorDefinition(
            (200, 200, 200, 255), 'Empty map tile background'
        ),
        'COL_TILE_EDGE': ColorDefinition(
            (240, 240, 240, 255), 'Map tile edge border'
        ),

        # Grid colors
        'COL_GRID': ColorDefinition(
            (220, 220, 220, 255), 'Background grid lines'
        ),

        # Building preview colors
        'COL_FLOAT_IN': ColorDefinition(
            (100, 255, 100, 100), 'Building preview fill'
        ),
        'COL_FLOAT_OUT': ColorDefinition(
            (0, 200, 0, 255), 'Building preview outline'
        ),

        # Building colors
        'COL_BLDG_IN': ColorDefinition(
            (200, 200, 200, 180), 'Building interior fill'
        ),
        'COL_BLDG_OUT': ColorDefinition(
            (100, 100, 100, 255), 'Building outline border'
        ),
        'COL_BLDG_LBL': ColorDefinition(
            (255, 255, 255, 255), 'Building label text'
        ),

        # Selected building colors
        'COL_SEL_BLDG_IN': ColorDefinition(
            (150, 180, 255, 180), 'Selected building interior fill'
        ),
        'COL_SEL_BLDG_OUT': ColorDefinition(
            (0, 0, 255, 255), 'Selected building outline border'
        ),

        # Handle colors
        'COL_HANDLE_IN': ColorDefinition(
            (255, 255, 255, 255), 'Selection handle interior'
        ),
        'COL_HANDLE_OUT': ColorDefinition(
            (0, 0, 255, 255), 'Selection handle outline'
        ),
    }

    def __init__(self):
        self._colors: Dict[str, wx.Colour] = {}
        self._initialized = False

    def _ensure_initialized(self):
        """Ensure colors are initialized (called on first access)"""
        if not self._initialized:
            self._load_defaults()
            self._initialized = True

    def _load_defaults(self):
        """Load default color values"""
        for key, definition in self.COLOR_DEFINITIONS.items():
            r, g, b, a = definition.default
            self._colors[key] = wx.Colour(r, g, b, a)

    def get(self, key: str) -> wx.Colour:
        """Get a color by key"""
        self._ensure_initialized()
        if key not in self._colors:
            raise KeyError(f"Color '{key}' not defined")
        return self._colors[key]

    def set(self, key: str, color: wx.Colour):
        """Set a color by key"""
        self._ensure_initialized()
        if key not in self.COLOR_DEFINITIONS:
            raise KeyError(f"Color '{key}' not defined")
        self._colors[key] = wx.Colour(color)

    def get_definition(self, key: str) -> ColorDefinition:
        """Get color definition by key"""
        if key not in self.COLOR_DEFINITIONS:
            raise KeyError(f"Color '{key}' not defined")
        return self.COLOR_DEFINITIONS[key]

    def get_all_keys(self):
        """Get all available color keys"""
        return list(self.COLOR_DEFINITIONS.keys())

    def reset_to_defaults(self):
        """Reset all colors to default values"""
        self._colors.clear()
        self._initialized = False
        self._ensure_initialized()

    def reset_color_to_default(self, key: str):
        """Reset a specific color to its default value"""
        if key not in self.COLOR_DEFINITIONS:
            raise KeyError(f"Color '{key}' not defined")
        r, g, b, a = self.COLOR_DEFINITIONS[key].default
        self._colors[key] = wx.Colour(r, g, b, a)


# Global color settings instance
colorset = ColorSettings()
settings = ParameterSettings()
