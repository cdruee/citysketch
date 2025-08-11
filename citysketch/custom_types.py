import math
from dataclasses import dataclass
from enum import Enum
from typing import Optional, List, Tuple


class SelectionMode(Enum):
    NORMAL = "normal"
    ADD_BUILDING = "add_building"
    RECTANGLE_SELECT = "rectangle_select"


class MapProvider(Enum):
    NONE = "None"
    OSM = "OpenStreetMap"
    SATELLITE = "Satellite"
    TERRAIN = "Terrain"


@dataclass
class Building:
    """Represents a building with its properties"""
    id: str
    x1: float
    y1: float
    x2: float
    y2: float
    height: float = 10.0  # meters
    stories: int = 3
    selected: bool = False

    def __post_init__(self):
        # Ensure x1,y1 is bottom-left and x2,y2 is top-right
        if self.x1 > self.x2:
            self.x1, self.x2 = self.x2, self.x1
        if self.y1 > self.y2:
            self.y1, self.y2 = self.y2, self.y1

    def contains_point(self, x: float, y: float) -> bool:
        """Check if a point is inside the building"""
        return self.x1 <= x <= self.x2 and self.y1 <= y <= self.y2

    def get_corner_index(self, x: float, y: float,
                         threshold: float = 10) -> Optional[int]:
        """Get which corner is near the point (0-3), None if no corner"""
        corners = self.get_corners()
        for i, (cx, cy) in enumerate(corners):
            if math.sqrt((x - cx) ** 2 + (y - cy) ** 2) < threshold:
                return i
        return None

    def get_corners(self) -> List[Tuple[float, float]]:
        """Get all four corners"""
        return [
            (self.x1, self.y1),  # 0: bottom-left
            (self.x2, self.y1),  # 1: bottom-right
            (self.x2, self.y2),  # 2: top-right
            (self.x1, self.y2),  # 3: top-left
        ]

    def move_corner(self, corner_index: int, new_x: float, new_y: float):
        """Move a specific corner"""
        if corner_index == 0:  # bottom-left
            self.x1, self.y1 = new_x, new_y
        elif corner_index == 1:  # bottom-right
            self.x2, self.y1 = new_x, new_y
        elif corner_index == 2:  # top-right
            self.x2, self.y2 = new_x, new_y
        elif corner_index == 3:  # top-left
            self.x1, self.y2 = new_x, new_y
        self.__post_init__()  # Normalize coordinates

    def translate(self, dx: float, dy: float):
        """Move the entire building"""
        self.x1 += dx
        self.x2 += dx
        self.y1 += dy
        self.y2 += dy

    def to_cityjson_geometry(self) -> dict:
        """Convert to CityJSON geometry format"""
        # Create vertices for the building (8 points for a box)
        vertices = [
            [self.x1, self.y1, 0.0],
            [self.x2, self.y1, 0.0],
            [self.x2, self.y2, 0.0],
            [self.x1, self.y2, 0.0],
            [self.x1, self.y1, self.height],
            [self.x2, self.y1, self.height],
            [self.x2, self.y2, self.height],
            [self.x1, self.y2, self.height],
        ]

        # Define faces (indices into vertices array)
        boundaries = [
            [[0, 1, 2, 3]],  # bottom
            [[4, 7, 6, 5]],  # top
            [[0, 4, 5, 1]],  # front
            [[0, 4, 5, 1]],  # front
            [[2, 6, 7, 3]],  # back
            [[0, 3, 7, 4]],  # left
            [[1, 5, 6, 2]],  # right
        ]

        return vertices, boundaries
