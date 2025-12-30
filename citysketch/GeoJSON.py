"""
GeoJSON module for CityJSON Creator
Handles import/export and conversion between GeoJSON and CitySketch buildings
"""

import json
import math
import uuid
from typing import List, Tuple, Optional, Set
from dataclasses import dataclass
import numpy as np

from .Building import Building

# Module constants
HEIGHT_TOLERANCE = 0.10  # 10% tolerance for height matching
ANGLE_TOLERANCE = 15.0  # degrees for rectangle detection
DISTANCE_TOLERANCE = 2.0  # meters for shape simplification


@dataclass
class GeoJsonBuilding:
    """Temporary building from GeoJSON for preview"""
    coordinates: List[Tuple[float, float]]  # List of (x, y) tuples
    height: float
    feature_id: str
    selected: bool = False  # Green when True, red when False
    imported: bool = False
    # Optional properties that may be set from GeoJSON
    height_variance: Optional[float] = None
    region: Optional[str] = None
    source: Optional[str] = None

    def contains_point(self, x: float, y: float) -> bool:
        """Check if a point is inside the polygon using ray casting"""
        n = len(self.coordinates)
        inside = False
        j = n - 1
        for i in range(n):
            xi, yi = self.coordinates[i]
            xj, yj = self.coordinates[j]
            if ((yi > y) != (yj > y)) and (
                    x < (xj - xi) * (y - yi) / (yj - yi) + xi):
                inside = not inside
            j = i
        return inside

    def intersects_rect(self, x1, y1, x2, y2):
        """Check if polygon intersects with rectangle"""
        # Check if any vertex is inside rect
        for x, y in self.coordinates:
            if x1 <= x <= x2 and y1 <= y <= y2:
                return True
        # Check if rect center is inside polygon
        cx, cy = (x1 + x2) / 2, (y1 + y2) / 2
        return self.contains_point(cx, cy)

    def to_buildings(self, storey_height: float = 3.3):
        """Convert to one or more regular Building objects by fitting rectangles"""


        buildings = []
        rectangles = RectangleFitter.fit_multiple_rectangles(
            self.coordinates)

        for i, rect_coords in enumerate(rectangles):
            xs = [c[0] for c in rect_coords]
            ys = [c[1] for c in rect_coords]

            cx = sum(xs) / 4
            cy = sum(ys) / 4

            # Calculate rotation from first edge
            dx = rect_coords[1][0] - rect_coords[0][0]
            dy = rect_coords[1][1] - rect_coords[0][1]
            rotation = math.atan2(dy, dx)

            # Calculate dimensions
            width = math.sqrt(dx ** 2 + dy ** 2)
            side2_dx = rect_coords[3][0] - rect_coords[0][0]
            side2_dy = rect_coords[3][1] - rect_coords[0][1]
            height_2d = math.sqrt(side2_dx ** 2 + side2_dy ** 2)

            building = Building(
                id=f"geojson_{self.feature_id}_{i}" if i > 0 else f"geojson_{self.feature_id}",
                x1=cx - width / 2,
                y1=cy - height_2d / 2,
                x2=cx + width / 2,
                y2=cy + height_2d / 2,
                height=self.height,
                stories=max(1, round(self.height / storey_height))
            )

            building.rotation = rotation
            building.rotation_center = (cx, cy)

            if i == 0:
                building.polygon_coords = self.coordinates

            buildings.append(building)

        return buildings

    def to_building(self, storey_height: float = 3.3):
        """Convert to a single Building object (returns first fitted rectangle).
        
        This is a convenience method for cases where only one building is needed.
        For complex polygons that may decompose into multiple buildings, use to_buildings().
        
        Returns:
            Building: The first building from the fitted rectangles, or None if fitting fails.
        """
        buildings = self.to_buildings(storey_height)
        return buildings[0] if buildings else None


class RectangleFitter:
    """Fit irregular polygons with rectangles"""

    @staticmethod
    def fit_single_rectangle(coordinates: List[Tuple[float, float]]) -> \
    Tuple[float, float, float, float, float]:
        """
        Fit a single rectangle to polygon using PCA for orientation.
        Returns: (cx, cy, width, height, angle)
        """
        points = np.array(coordinates)
        centroid = np.mean(points, axis=0)
        centered = points - centroid

        # Compute covariance matrix for PCA without sklearn
        cov_matrix = np.cov(centered.T)
        eigenvalues, eigenvectors = np.linalg.eig(cov_matrix)

        # Sort eigenvectors by eigenvalues
        idx = eigenvalues.argsort()[::-1]
        eigenvectors = eigenvectors[:, idx]

        # Transform points to principal component space
        transformed = centered @ eigenvectors

        # Get bounding box in transformed space
        min_x, min_y = np.min(transformed, axis=0)
        max_x, max_y = np.max(transformed, axis=0)

        width = max_x - min_x
        height = max_y - min_y

        # Get rotation angle from first principal component
        angle = np.arctan2(eigenvectors[1, 0], eigenvectors[0, 0])

        # Get center in original space
        center_transformed = np.array(
            [(min_x + max_x) / 2, (min_y + max_y) / 2])
        center_original = center_transformed @ eigenvectors.T + centroid

        return center_original[0], center_original[1], width, height, angle

    @staticmethod
    def is_approximately_rectangular(
            coordinates: List[Tuple[float, float]]) -> bool:
        """Check if polygon is approximately rectangular"""
        if len(coordinates) < 4 or len(coordinates) > 8:
            return len(coordinates) <= 6

        angles = []
        for i in range(len(coordinates)):
            p1 = coordinates[i]
            p2 = coordinates[(i + 1) % len(coordinates)]
            p3 = coordinates[(i + 2) % len(coordinates)]

            v1 = (p2[0] - p1[0], p2[1] - p1[1])
            v2 = (p3[0] - p2[0], p3[1] - p2[1])

            angle = math.atan2(v2[1], v2[0]) - math.atan2(v1[1], v1[0])
            angle = math.degrees(angle) % 360
            if angle > 180:
                angle = 360 - angle
            angles.append(angle)

        right_angles = sum(
            1 for a in angles if abs(a - 90) < ANGLE_TOLERANCE)
        return right_angles >= len(coordinates) - 2

    @staticmethod
    def simplify_to_rectangle(coordinates: List[Tuple[float, float]]) -> \
    List[Tuple[float, float]]:
        """Simplify an approximately rectangular polygon to 4 corners"""
        cx, cy, width, height, angle = RectangleFitter.fit_single_rectangle(
            coordinates)

        cos_a = math.cos(angle)
        sin_a = math.sin(angle)
        hw = width / 2
        hh = height / 2

        corners = [(-hw, -hh), (hw, -hh), (hw, hh), (-hw, hh)]

        result = []
        for lx, ly in corners:
            rx = lx * cos_a - ly * sin_a
            ry = lx * sin_a + ly * cos_a
            result.append((cx + rx, cy + ry))

        return result

    @staticmethod
    def fit_multiple_rectangles(coordinates: List[Tuple[float, float]],
                                max_rectangles: int = 3) -> List[
        List[Tuple[float, float]]]:
        """Fit polygon with multiple rectangles if it's L-shaped, T-shaped, etc."""
        if RectangleFitter.is_approximately_rectangular(coordinates):
            return [RectangleFitter.simplify_to_rectangle(coordinates)]

        # For complex shapes, return single best-fit rectangle for now
        # TODO: Implement polygon decomposition for L-shaped, T-shaped buildings
        return [RectangleFitter.simplify_to_rectangle(coordinates)]


class BuildingMerger:
    """Merge CitySketch buildings into GeoJSON buildings"""

    @staticmethod
    def buildings_share_wall(b1, b2, tolerance: float = 0.5) -> bool:
        """Check if two buildings share at least one wall"""
        # Get corners of both buildings (considering rotation)
        corners1 = b1.get_rotated_corners() if hasattr(b1,
                                                       'get_rotated_corners') else b1.get_corners()
        corners2 = b2.get_rotated_corners() if hasattr(b2,
                                                       'get_rotated_corners') else b2.get_corners()

        # Check each edge pair
        for i in range(4):
            edge1_start = corners1[i]
            edge1_end = corners1[(i + 1) % 4]

            for j in range(4):
                edge2_start = corners2[j]
                edge2_end = corners2[(j + 1) % 4]

                # Check if edges are parallel and overlapping
                if BuildingMerger._edges_share_wall(
                        edge1_start, edge1_end, edge2_start, edge2_end,
                        tolerance):
                    return True

        return False

    @staticmethod
    def _edges_share_wall(e1_start, e1_end, e2_start, e2_end,
                          tolerance: float) -> bool:
        """Check if two edges form a shared wall"""
        # Calculate edge vectors
        v1 = (e1_end[0] - e1_start[0], e1_end[1] - e1_start[1])
        v2 = (e2_end[0] - e2_start[0], e2_end[1] - e2_start[1])

        # Check if parallel (opposite direction for shared wall)
        len1 = math.sqrt(v1[0] ** 2 + v1[1] ** 2)
        len2 = math.sqrt(v2[0] ** 2 + v2[1] ** 2)

        if len1 < 0.001 or len2 < 0.001:
            return False

        # Normalize vectors
        v1_norm = (v1[0] / len1, v1[1] / len1)
        v2_norm = (v2[0] / len2, v2[1] / len2)

        # Check if parallel (dot product close to -1 for opposite direction)
        dot = v1_norm[0] * v2_norm[0] + v1_norm[1] * v2_norm[1]
        if abs(dot + 1) > 0.1:  # Not opposite direction
            return False

        # Check if edges are close and overlapping
        # Project points onto the line
        dist1 = BuildingMerger._point_to_line_distance(e2_start, e1_start,
                                                       e1_end)
        dist2 = BuildingMerger._point_to_line_distance(e2_end, e1_start,
                                                       e1_end)

        if max(dist1, dist2) > tolerance:
            return False

        # Check overlap
        t1_s = BuildingMerger._project_point_on_line(e2_start, e1_start,
                                                     e1_end)
        t1_e = BuildingMerger._project_point_on_line(e2_end, e1_start,
                                                     e1_end)

        # Check if projections overlap with [0, 1] interval
        return not (max(t1_s, t1_e) < 0 or min(t1_s, t1_e) > 1)

    @staticmethod
    def _point_to_line_distance(point, line_start, line_end):
        """Calculate distance from point to line segment"""
        x0, y0 = point
        x1, y1 = line_start
        x2, y2 = line_end

        dx = x2 - x1
        dy = y2 - y1

        if dx == 0 and dy == 0:
            return math.sqrt((x0 - x1) ** 2 + (y0 - y1) ** 2)

        t = ((x0 - x1) * dx + (y0 - y1) * dy) / (dx ** 2 + dy ** 2)
        t = max(0, min(1, t))

        closest_x = x1 + t * dx
        closest_y = y1 + t * dy

        return math.sqrt((x0 - closest_x) ** 2 + (y0 - closest_y) ** 2)

    @staticmethod
    def _project_point_on_line(point, line_start, line_end):
        """Project point onto line and return parameter t"""
        x0, y0 = point
        x1, y1 = line_start
        x2, y2 = line_end

        dx = x2 - x1
        dy = y2 - y1

        if dx == 0 and dy == 0:
            return 0

        return ((x0 - x1) * dx + (y0 - y1) * dy) / (dx ** 2 + dy ** 2)

    @staticmethod
    def buildings_intersect(b1, b2) -> bool:
        """Check if two buildings' outlines intersect"""
        corners1 = b1.get_rotated_corners() if hasattr(b1,
                                                       'get_rotated_corners') else b1.get_corners()
        corners2 = b2.get_rotated_corners() if hasattr(b2,
                                                       'get_rotated_corners') else b2.get_corners()

        # Check if any corner of b1 is inside b2 or vice versa
        for corner in corners1:
            if BuildingMerger._point_in_polygon(corner, corners2):
                return True

        for corner in corners2:
            if BuildingMerger._point_in_polygon(corner, corners1):
                return True

        # Check edge intersections
        for i in range(4):
            for j in range(4):
                if BuildingMerger._edges_intersect(
                        corners1[i], corners1[(i + 1) % 4],
                        corners2[j], corners2[(j + 1) % 4]):
                    return True

        return False

    @staticmethod
    def _point_in_polygon(point, polygon):
        """Check if point is inside polygon using ray casting"""
        x, y = point
        n = len(polygon)
        inside = False
        j = n - 1

        for i in range(n):
            xi, yi = polygon[i]
            xj, yj = polygon[j]
            if ((yi > y) != (yj > y)) and (
                    x < (xj - xi) * (y - yi) / (yj - yi) + xi):
                inside = not inside
            j = i

        return inside

    @staticmethod
    def _edges_intersect(p1, p2, p3, p4):
        """Check if line segments p1-p2 and p3-p4 intersect"""

        def ccw(A, B, C):
            return (C[1] - A[1]) * (B[0] - A[0]) > (B[1] - A[1]) * (
                        C[0] - A[0])

        return ccw(p1, p3, p4) != ccw(p2, p3, p4) and ccw(p1, p2,
                                                          p3) != ccw(p1,
                                                                     p2,
                                                                     p4)

    @staticmethod
    def merge_buildings_to_geojson(buildings: List,
                                   height_tolerance: float = HEIGHT_TOLERANCE) -> \
    Optional[GeoJsonBuilding]:
        """
        Merge a list of CitySketch buildings into a single GeoJSON building
        if they share walls or intersect and have similar heights.
        """
        if not buildings:
            return None

        if len(buildings) == 1:
            # Convert single building to GeoJSON
            b = buildings[0]
            corners = b.get_rotated_corners() if hasattr(b,
                                                         'get_rotated_corners') else b.get_corners()
            return GeoJsonBuilding(
                coordinates=list(corners),
                height=b.height,
                feature_id=b.id
            )

        # Check if buildings are connected and have similar heights
        # First, calculate area-weighted mean height
        total_area = 0
        weighted_height = 0

        for b in buildings:
            area = abs((b.x2 - b.x1) * (b.y2 - b.y1))
            total_area += area
            weighted_height += b.height * area

        if total_area == 0:
            return None

        mean_height = weighted_height / total_area

        # Check if all buildings have similar height
        for b in buildings:
            if abs(b.height - mean_height) > mean_height * height_tolerance:
                return None  # Heights too different

        # Check if buildings are connected
        # Create a graph of connections
        connected = set([buildings[0]])
        to_check = buildings[1:]

        while to_check:
            found_connection = False
            for b in to_check[:]:
                for connected_b in connected:
                    if (BuildingMerger.buildings_share_wall(b,
                                                            connected_b) or
                            BuildingMerger.buildings_intersect(b,
                                                               connected_b)):
                        connected.add(b)
                        to_check.remove(b)
                        found_connection = True
                        break

            if not found_connection:
                return None  # Not all buildings are connected

        # Create union of all building outlines
        # For simplicity, collect all corners and create convex hull
        all_points = []
        for b in buildings:
            corners = b.get_rotated_corners() if hasattr(b,
                                                         'get_rotated_corners') else b.get_corners()
            all_points.extend(corners)

        # Compute convex hull (simple implementation)
        hull_points = BuildingMerger._convex_hull(all_points)

        # Create GeoJSON building
        return GeoJsonBuilding(
            coordinates=hull_points,
            height=mean_height,
            feature_id=f"merged_{'_'.join(b.id for b in buildings[:3])}"
        )

    @staticmethod
    def _convex_hull(points):
        """Compute convex hull of points using Graham scan"""
        if len(points) < 3:
            return points

        # Remove duplicates
        points = list(set(points))

        # Find the bottom-most point (and left-most if tied)
        start = min(points, key=lambda p: (p[1], p[0]))

        # Sort points by polar angle with respect to start point
        def polar_angle(p):
            dx = p[0] - start[0]
            dy = p[1] - start[1]
            return math.atan2(dy, dx)

        sorted_points = sorted(points, key=polar_angle)

        # Build hull
        hull = []
        for p in sorted_points:
            while len(hull) > 1 and BuildingMerger._ccw(hull[-2], hull[-1],
                                                        p) <= 0:
                hull.pop()
            hull.append(p)

        return hull

    @staticmethod
    def _ccw(p1, p2, p3):
        """Counter-clockwise test"""
        return (p2[0] - p1[0]) * (p3[1] - p1[1]) - (p2[1] - p1[1]) * (
                    p3[0] - p1[0])

