import math
import statistics
from dataclasses import dataclass
from typing import Optional, List, Tuple

from .AppSettings import settings

# =========================================================================

@dataclass
class Building:
    """
    Represents a building with its geometric properties.
    
    Coordinates are in Web Mercator (EPSG:3857) meters, relative to
    the application's center position.
    
    :param id: Unique identifier for the building
    :param x1: X-coordinate of anchor corner (corner #0) in Web Mercator meters
    :param y1: Y-coordinate of anchor corner (corner #0) in Web Mercator meters  
    :param a: Width along the building's local X-axis (when rotation=0), 
        or 0 for cylindrical buildings
    :param b: Height along the building's local Y-axis (when rotation=0),
        or radius for cylindrical buildings
    :param height: Building height in meters (default 10.0)
    :param storeys: Number of storeys (default 3)
    :param rotation: Rotation angle in radians, counter-clockwise from 
        positive X-axis (default 0.0)
    """
    id: str
    x1: float  # corner #0
    y1: float  # corner #0
    a: float  # extent along x axis (when rotation is 0) or  0 (cylindrical)
    b: float  # extent along y axis (when rotation is 0) or diameter
    height: float = 10.0  # meters
    storeys: int = 3
    # selected: bool = False
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
        if self.a <= 0:
            # cylidrical building
            nc = settings.get('CIRCLE_CORNERS') + 1
            dr = 2 * math.pi / nc
            corners = [
                (self.b * math.cos(i * dr),
                 self.b * math.sin(i * dr)) for i in range(nc)
            ]
        else:
            # block building
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

    def get_llur(self) -> Tuple[float, float,float, float]:
        """Get lower left and upper right of surrounding rectangle"""
        corners = self.get_corners()

        le = min(c[0] for c in corners)
        ri = max(c[0] for c in corners)
        lo = min(c[1] for c in corners)
        up = max(c[1] for c in corners)

        return le, lo, ri, up


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
        old_x, old_y = self.get_corners()[corner_index]
        a_old, b_old = self.word_to_building(old_x, old_y)
        a_new, b_new = self.word_to_building(new_x, new_y)

        a_stretch = a_old / a_new
        b_stretch = b_old / b_new
        if corner_index != 0:
            if corner_index in [1, 2]:
                self.a = self.a * a_stretch
            if corner_index in [2, 3]:
                self.b = self.b * b_stretch
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
        # # Get rotated corners for the base
        # rotated_corners = self.get_corners()
        #
        # # Create vertices for the building (8 points for a box)
        # vertices = []
        # # Bottom face
        # for cx, cy in rotated_corners:
        #     vertices.append([cx, cy, 0.0])
        # # Top face
        # for cx, cy in rotated_corners:
        #     vertices.append([cx, cy, self.height])
        #
        # # Define faces (indices into vertices array)
        # boundaries = [
        #     [[0, 1, 2, 3]],  # bottom
        #     [[4, 7, 6, 5]],  # top
        #     [[0, 4, 5, 1]],  # front
        #     [[2, 6, 7, 3]],  # back
        #     [[0, 3, 7, 4]],  # left
        #     [[1, 5, 6, 2]],  # right
        # ]
        #
        # return vertices, boundaries

# =========================================================================

class BuildingGroup:
    buildings: List[Building]

    _x1: float | None = None  # lower left coner x, y
    _y1: float | None = None
    _a: float | None = None  # surrounding rectangle size along x, y axes
    _b: float | None = None
    _xr: float | None = None # rotation vertex x, y
    _yr: float | None = None
    _rotation: float | None = None

    def __init__(self, buildings: List[Building]):
        self.buildings = buildings
        # implicit call of self.update_buildings()

    def __setattr__(self, attr, value):
        super().__setattr__(attr, value)
        if attr == "buildings":
            self.update_buildings()

    def __len__(self):
        return len(self.buildings)

    def __contains__(self, item):
        return item in self.buildings

    def __iter__(self):
        return iter(self.buildings)

    @property
    def x1(self):
        return self._x1

    @property
    def y1(self):
        return self._y1

    @property
    def a(self):
        return self._a

    @property
    def b(self):
        return self._b

    @property
    def rotation(self):
        return self._rotation


    def update_buildings(self):
        if len(self.buildings) == 0:
            self._x1 = self._y1 = None
            self._a = self._b = None
            self._xr = self._yr = None
            self._rotation = None
            return
        elif len(self.buildings) == 1:
            self._rotation = self.buildings[0].rotation
        else:
            meds=[]
            rots = [b.rotation for b in self.buildings]
            for dr in [float(x) * math.pi / 2. for x in range(4)]:
                meds.append(
                    statistics.median(
                        [(x + dr) % (2 * math.pi) for x in rots]
                    ) - dr
                )
            self._rotation = statistics.median(meds)

        all_corners = [y for x in self.buildings for y in x.get_corners()]
        # preliminary anchor coordinate
        self._x1 = min(x[0] for x in all_corners)
        self._y1 = min(x[1] for x in all_corners)
        # find rotated circumferring rectangle
        all_corners_rot = [word_to_building(self, x, y)
                           for x, y in all_corners]
        le_rot = min(x[0] for x in all_corners_rot)
        lo_rot = min(x[1] for x in all_corners_rot)
        ri_rot = max(x[0] for x in all_corners_rot)
        up_rot = max(x[1] for x in all_corners_rot)
        # anchor coordinate and size
        le, lo = building_to_world(self, le_rot, lo_rot)
        self._x1 = le
        self._y1 = lo
        self._a = ri_rot - le_rot
        self._b = up_rot - lo_rot

        # rotation center is anchor
        self._rx = self._x1
        self._ry = self._y1

    def add(self, building: Building):
        """Add a building to the group,
        do nothing if building already in list"""
        if not building in self.buildings:
            self.buildings.append(building)
        self.update_buildings()

    def get(self, index: int):
        """Get building number index"""
        if not 0 <= index < len(self.buildings):
            raise ValueError(f"{self.__class__.__name__} "
                             f"list index out of range")
        else:
            return self.buildings[index]

    def remove(self, building: Building):
        """Remove a building from the group,
        do nothing if building not in list"""
        if building in self.buildings:
            self.buildings.remove(building)
        self.update_buildings()

    def get_corners(self) -> List[Tuple[float, float]]:
        if self._x1 is None or self._y1 is None:
            return []
        corners = [(0., 0.),
                   (self._a, 0.),
                   (self._a, self._b),
                   (0., self._b)]
        rotated = []
        for px, py in corners:
            rotated.append(building_to_world(self, px, py))
        return rotated

    def get_llur(self) -> Tuple[float, float, float, float]| None:
        if self._x1 is None or self._y1 is None:
            return None
        corners = self.get_corners()

        le = min(c[0] for c in corners)
        ri = max(c[0] for c in corners)
        lo = min(c[1] for c in corners)
        up = max(c[1] for c in corners)

        return le, lo, ri, up

    def contains_point(self, x: float, y: float) -> bool:
        """Check if a point is inside the surrounding rectangle"""
        return _contains_point(self, x, y)

    def buildings_contains_point(self, x: float, y: float) -> bool:
        """Check if a point is inside one of the buildings"""
        return any([_contains_point(b, x, y) for b in self.buildings])

    def get_corner_index(self, x: float, y: float,
                         threshold : float) -> Optional[int]:
        """Get which corner is near the point (0-3), None if no corner"""
        return _get_corner_index(self, x, y, threshold=threshold)

    def rotate_to_corner(self, corner_index: int, new_x: float,
                         new_y: float):
        """Rotate the building so that the specified corner moves to target point"""
        if corner_index != 0:
            old_x, old_y = self.get_corners()[corner_index]
            old_angle = math.atan2(old_y - self.y1, old_x - self.x1)
            old_dist = math.sqrt((old_x - self.x1) ** 2 +
                                 (old_y - self.y1) ** 2)
            new_angle = math.atan2(new_y - self.y1, new_x - self.x1)
            new_dist = math.sqrt((new_x - self.x1) ** 2 +
                                 (new_y - self.y1) ** 2)
            dr = new_angle - old_angle
            scale = new_dist / old_dist

            for b in self.buildings:
                # rotate building
                b.rotation = b.rotation + dr
                # scale building
                b.a = b.a * scale
                b.b = b.b * scale
                # transform distance to vertex
                x_old_grp, y_old_grp = word_to_building(self, b.x1, b.y1)
                x_new_grp = scale * (math.cos(dr) * x_old_grp -
                                     math.sin(dr) * y_old_grp)
                y_new_grp = scale * (math.sin(dr) * x_old_grp +
                                     math.cos(dr) * y_old_grp)
                b.x1, b.y1 = building_to_world(self, x_new_grp, y_new_grp)
            self.update_buildings()
        else:
            pass



    def scale_to_corner(self, corner_index: int, new_x: float,
                        new_y: float):
        """Move a specific corner (for scaling / rotation)"""
        am, bm = word_to_building(self, new_x, new_y)
        if corner_index != 0:
            scale_a = 1.
            scale_b = 1.
            if corner_index in [1, 2]:
                scale_a = am / self._a
            if corner_index in [2, 3]:
                scale_b = bm / self._b
            for b in self.buildings:
                # scale building size
                b.a = b.a * scale_a
                b.b = b.b * scale_b
                # scale distance to vertex
                x_old_grp, y_old_grp = word_to_building(self, b.x1, b.y1)
                x_new_grp = x_old_grp * scale_a
                y_new_grp = y_old_grp * scale_b
                b.x1, b.y1 = building_to_world(self, x_new_grp, y_new_grp)
            # # save new group size
            # self._a *= scale_a
            # self._b *= scale_b
            self.update_buildings()
        else:
            self.translate(new_x, new_y)

    def translate(self, new_x: float, new_y: float):
        """Move the building to the new position"""
        dx = new_x - self._x1
        dy = new_y - self._y1
        self.shift(dx, dy)

    def shift(self, dx: float, dy: float):
        for b in self.buildings:
            b.shift(dx, dy)
        self.update_buildings()

    def rotate(self, dr: float):
        for b in self.buildings:
            b.rotation += dr
            x1, y1 = b.x1, b.y1
            new_x = math.cos(dr) * x1 - math.sin(dr) * y1
            new_y = math.sin(dr) * x1 + math.cos(dr) * y1
            b.x1 = new_x
            b.y1 = new_y
        self.update_buildings()

# =========================================================================
# static methods

def _contains_point(obj, x: float, y: float) -> bool:
    """Check if a point is inside the building (considering rotation)"""
    corners = obj.get_corners()
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

# -------------------------------------------------------------------------

def _get_corner_index(obj, x: float, y: float,
                     threshold: float = 10) -> Optional[int]:
    """Get which corner is near the point (0-3), None if no corner"""
    corners = obj.get_corners()
    for i, (cx, cy) in enumerate(corners):
        if math.sqrt((x - cx) ** 2 + (y - cy) ** 2) < threshold:
            return i
    return None

# -------------------------------------------------------------------------

def word_to_building(obj, x: float, y: float
                     ) -> tuple[float, float]:
    dx = x - obj.x1
    dy = y - obj.y1
    a = + math.cos(obj.rotation) * dx + math.sin(obj.rotation) * dy
    b = - math.sin(obj.rotation) * dx + math.cos(obj.rotation) * dy
    return a, b

# -------------------------------------------------------------------------

def building_to_world(obj, a: float, b: float
                      ) -> tuple[float, float]:
    dx = + math.cos(obj.rotation) * a - math.sin(obj.rotation) * b
    dy = + math.sin(obj.rotation) * a + math.cos(obj.rotation) * b
    x = dx + obj.x1
    y = dy + obj.y1
    return x, y
