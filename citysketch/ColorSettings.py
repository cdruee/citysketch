import wx
from typing import Dict, NamedTuple, Tuple


class ColorDefinition(NamedTuple):
    """Defines a color with name, default value and description"""
    name: str
    default: Tuple[int, int, int, int]  # RGBA tuple instead of wx.Colour
    description: str


class ColorSettings:
    """Centralized color management for the application"""

    # Define all application colors here using RGBA tuples
    COLOR_DEFINITIONS = {
        # Tile colors
        'COL_TILE_EMPTY': ColorDefinition(
            'COL_TILE_EMPTY',
            (200, 200, 200, 255),
            'Empty map tile background'
        ),
        'COL_TILE_EDGE': ColorDefinition(
            'COL_TILE_EDGE',
            (240, 240, 240, 255),
            'Map tile edge border'
        ),

        # Grid colors
        'COL_GRID': ColorDefinition(
            'COL_GRID',
            (220, 220, 220, 255),
            'Background grid lines'
        ),

        # Building preview colors
        'COL_FLOAT_IN': ColorDefinition(
            'COL_FLOAT_IN',
            (100, 255, 100, 100),
            'Building preview fill'
        ),
        'COL_FLOAT_OUT': ColorDefinition(
            'COL_FLOAT_OUT',
            (0, 200, 0, 255),
            'Building preview outline'
        ),

        # Building colors
        'COL_BLDG_IN': ColorDefinition(
            'COL_BLDG_IN',
            (200, 200, 200, 180),
            'Building interior fill'
        ),
        'COL_BLDG_OUT': ColorDefinition(
            'COL_BLDG_OUT',
            (100, 100, 100, 255),
            'Building outline border'
        ),
        'COL_BLDG_LBL': ColorDefinition(
            'COL_BLDG_LBL',
            (255, 255, 255, 255),
            'Building label text'
        ),

        # Selected building colors
        'COL_SEL_BLDG_IN': ColorDefinition(
            'COL_SEL_BLDG_IN',
            (150, 180, 255, 180),
            'Selected building interior fill'
        ),
        'COL_SEL_BLDG_OUT': ColorDefinition(
            'COL_SEL_BLDG_OUT',
            (0, 0, 255, 255),
            'Selected building outline border'
        ),

        # Handle colors
        'COL_HANDLE_IN': ColorDefinition(
            'COL_HANDLE_IN',
            (255, 255, 255, 255),
            'Selection handle interior'
        ),
        'COL_HANDLE_OUT': ColorDefinition(
            'COL_HANDLE_OUT',
            (0, 0, 255, 255),
            'Selection handle outline'
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

    def get_color(self, key: str) -> wx.Colour:
        """Get a color by key"""
        self._ensure_initialized()
        if key not in self._colors:
            raise KeyError(f"Color '{key}' not defined")
        return self._colors[key]

    def set_color(self, key: str, color: wx.Colour):
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
