import math
from dataclasses import dataclass
from typing import Optional, List, Tuple


@dataclass
class Building:
    """Represents a building with its properties"""
    id: str
    x1: float  # corner #0
    y1: float  # corner #0
    a: float  # extent along x axis (when rotation is 0)
    b: float  # extent along y axis (when rotation is 0)
    height: float = 10.0  # meters
    storeys: int = 3
    selected: bool = False
    rotation: float = 0.0  # rotation angle in radians (math definition)

    def contains_point(self, x: float, y: float) -> bool:
        """Check if a point is inside the building (considering rotation)"""
        corners = self.get_corners()
        # Use ray casting algorithm for point in polygon
        n = len(corners)
        inside = False
        j = n - 1
        for i in range(n):
            xi, yi = corners[i]
            xj, yj = corners[j]
            if ((yi > y) != (yj > y)) and (
                    x < (xj - xi) * (y - yi) / (yj - yi) + xi):
                inside = not inside
            j = i
        return inside

    def get_corner_index(self, x: float, y: float,
                         threshold: float = 10) -> Optional[int]:
        """Get which corner is near the point (0-3), None if no corner"""
        corners = self.get_corners()
        for i, (cx, cy) in enumerate(corners):
            if math.sqrt((x - cx) ** 2 + (y - cy) ** 2) < threshold:
                return i
        return None

    def get_corners(self) -> List[Tuple[float, float]]:
        """Get all four corners after rotation"""
        corners = [
            (0., 0.),  # 0: bottom-left
            (self.a, 0.),  # 1: bottom-right
            (self.a, self.b),  # 2: top-right
            (0., self.b),  # 3: top-left
        ]

        rotated = []
        for px, py in corners:
            rotated.append(self.building_to_world(px, py))

        return rotated

    def word_to_building(self, x: float, y: float
                         ) -> tuple[float, float]:
        dx = x - self.x1
        dy = y - self.y1
        a = + math.cos(self.rotation) * dx + math.sin(self.rotation) * dy
        b = - math.sin(self.rotation) * dx + math.cos(self.rotation) * dy
        return a, b

    def building_to_world(self, a: float, b: float
                          ) -> tuple[float, float]:
        dx = + math.cos(self.rotation) * a - math.sin(self.rotation) * b
        dy = + math.sin(self.rotation) * a + math.cos(self.rotation) * b
        x = dx + self.x1
        y = dy + self.y1
        return x, y

    def rotate_to_corner(self, corner_index: int, new_x: float,
                         new_y: float):
        """Rotate the building so that the specified corner moves to target point"""
        old_x, old_y = self.get_corners()[corner_index]
        old_angle = math.atan2(old_y - self.y1, old_x - self.x1)
        old_dist = math.sqrt((old_x - self.x1) ** 2 +
                             (old_y - self.y1) ** 2)
        new_angle = math.atan2(new_y - self.y1, new_x - self.x1)
        new_dist = math.sqrt((new_x - self.x1) ** 2 +
                             (new_y - self.y1) ** 2)
        self.rotation += new_angle - old_angle
        self.a *= new_dist / old_dist
        self.b *= new_dist / old_dist

    def scale_to_corner(self, corner_index: int, new_x: float,
                        new_y: float):
        """Move a specific corner (for scaling / rotation)"""
        a_new, b_new = self.word_to_building(new_x, new_y)
        if corner_index != 0:
            if corner_index in [1, 2]:
                self.a = a_new
            if corner_index in [2, 3]:
                self.b = b_new
        else:
            self.translate(new_x, new_y)

    def translate(self, new_x: float, new_y: float):
        """Move the entire building to new position"""
        self.x1 = new_x
        self.y1 = new_y

    def shift(self, dx: float, dy: float):
        """Move the entire building by incremental distance"""
        self.translate(self.x1 + dx, self.y1 + dy)

    def to_cityjson_geometry(self) -> dict:
        """Convert to CityJSON geometry format"""
        # Get rotated corners for the base
        rotated_corners = self.get_corners()

        # Create vertices for the building (8 points for a box)
        vertices = []
        # Bottom face
        for cx, cy in rotated_corners:
            vertices.append([cx, cy, 0.0])
        # Top face
        for cx, cy in rotated_corners:
            vertices.append([cx, cy, self.height])

        # Define faces (indices into vertices array)
        boundaries = [
            [[0, 1, 2, 3]],  # bottom
            [[4, 7, 6, 5]],  # top
            [[0, 4, 5, 1]],  # front
            [[2, 6, 7, 3]],  # back
            [[0, 3, 7, 4]],  # left
            [[1, 5, 6, 2]],  # right
        ]

        return vertices, boundaries
