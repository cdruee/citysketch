import ast
from dataclasses import dataclass
from typing import Any, Dict, NamedTuple, Optional, Tuple, Type

import wx

@dataclass
class Definition:
    value: Any
    description: str

class Definitions(dict):
    def __init__(self, values: Optional[Dict[str, Definition]] = None):
        super().__init__()
        if values:
            self.update(values)

class Settings():
    """Centralized view params for the application"""
    _defaults = Definitions()
    _values = Definitions()

    def __init__(self, defaults: Definitions):
        self._defaults = defaults
        self._initialized = False

    def _ensure_initialized(self):
        """Ensure params are initialized (called on first access)"""
        if not self._initialized:
            self._load_defaults()
            self._initialized = True

    def _load_defaults(self):
        """Load default color values"""
        for key, definition in self._defaults.items():
            self._values[key] = Definition(definition.value,
                                           definition.description)

    def get(self, key: str) -> Any:
        """Get params by key"""
        self._ensure_initialized()
        if key not in self._values:
            raise KeyError(f"Parameter '{key}' not defined")
        return self._values[key].value

    def get_default(self, key: str) -> Any:
        """Get default definition by key"""
        if key not in self._values:
            raise KeyError(f"Parameter '{key}' not defined")
        return self._defaults[key].value

    def set(self, key: str, value: Any):
        """Set params by key"""
        self._ensure_initialized()
        if key not in self._defaults:
            raise KeyError(f"Parameter '{key}' not defined")
        if not isinstance(value, type(self._defaults[key].value)):
            raise TypeError(f"Parameter '{key}' must be of "
                            f"type {type(self._defaults[key].value)}")
        self._values[key].value = value

    def get_description(self, key: str) -> Definition:
        """Get color definition by key"""
        if key not in self._values:
            raise KeyError(f"Parameter '{key}' not defined")
        return self._values[key].description

    def get_all_keys(self):
        """Get all available color keys"""
        return list(self._defaults.keys())

    def reset_to_defaults(self):
        """Reset all params to default params"""
        for key in self._defaults.keys():
            self.reset_param_to_default(key)

    def reset_param_to_default(self, key: str):
        """Reset a specific color to its default param"""
        if key not in self._defaults:
            raise KeyError(f"Parameter '{key}' not defined")
        self.set(key, self._defaults[key].value)

    def from_dict(self, dictionary: Dict):
        for k, v in dictionary.items():
            if k not in self._defaults.keys():
                raise KeyError(f"Color '{k}' not defined")
            # interpret type from string
            value = ast.literal_eval(v)
            # cast to actual type
            self.set(k, type(self._defaults[k].value)(value))
        return True

    def to_dict(self):
        return {x: str(self.get(x)) for x in self.get_all_keys()}


PARAMETER_DEFINITIONS = Definitions({
    'ZOOM_STEP_PERCENT': Definition (
        20, 'Zoom step percentage'
    ),
    'CIRCLE_CORNERS': Definition(
        12, 'Corners of a polygon representing circle'
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

# Global color settings instance
colorset = Settings(COLOR_DEFINITIONS)
settings = Settings(PARAMETER_DEFINITIONS)
