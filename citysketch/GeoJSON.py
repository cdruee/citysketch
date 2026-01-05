"""
GeoJSON Module for CitySketch
=============================

Handles import/export and conversion between GeoJSON and CitySketch buildings.

This module provides functionality for:

- Loading building footprints from GeoJSON files
- Converting GeoJSON polygons to CitySketch Building objects
- Fitting rectangles to irregular polygon shapes
- Merging adjacent buildings into single footprints
- Exporting CitySketch buildings back to GeoJSON format

.. rubric:: Module Constants

.. data:: HEIGHT_TOLERANCE
   :value: 0.10

   Tolerance (10%) for height matching when merging buildings.

.. data:: ANGLE_TOLERANCE
   :value: 15.0

   Tolerance in degrees for rectangle detection.

.. data:: DISTANCE_TOLERANCE
   :value: 2.0

   Tolerance in meters for shape simplification.

.. data:: MAX_NON_OVERLAP_RATIO
   :value: 0.20

   Maximum allowed ratio (20%) of non-overlapping area between original
   polygon and fitted rectangle for simple rectangle fitting to be accepted.
"""

import json
import math
import re
import uuid
from typing import List, Tuple, Optional
from pathlib import Path
from dataclasses import dataclass


import numpy as np
from osgeo import osr

from .Building import Building
from .utils import get_epsg2ll
from .building_simplification import (
    BuildingSimplifier,
    RectangularPartitioner,
    smallest_enclosing_rectangle,
    rotate_polygon,
    Rectangle
)

# Module constants - these provide defaults, but actual values come from settings
# Import settings for dynamic values
from .AppSettings import settings as app_settings

def get_height_tolerance():
    """Get height tolerance from settings."""
    return app_settings.get('HEIGHT_TOLERANCE')

def get_angle_tolerance():
    """Get angle tolerance from settings."""
    return app_settings.get('ANGLE_TOLERANCE')

def get_distance_tolerance():
    """Get distance tolerance from settings."""
    return app_settings.get('DISTANCE_TOLERANCE')

def get_max_non_overlap_ratio():
    """Get max non-overlap ratio from settings."""
    return app_settings.get('MAX_NON_OVERLAP_RATIO')

# Legacy constants for backward compatibility (use getter functions instead)
HEIGHT_TOLERANCE = 0.10  # Default: 10% tolerance for height matching
ANGLE_TOLERANCE = 15.0  # Default: degrees for rectangle detection
DISTANCE_TOLERANCE = 2.0  # Default: meters for shape simplification
MAX_NON_OVERLAP_RATIO = 0.20  # Default: Maximum allowed non-overlapping area ratio (20%)


def extract_epsg(crs_object):
    """
    Extract EPSG code from various CRS string formats.
    
    Handles formats like:
    
    - ``"EPSG::3857"``
    - ``"EPSG:3857"``
    - ``"urn:ogc:def:crs:EPSG:6.3:26986"``
    - ``"urn:ogc:def:crs:EPSG::4326"``
    - ``"https://www.opengis.net/def/crs/EPSG/0/4326"``
    
    :param crs_object: CRS object from GeoJSON containing 'type' and 'properties' keys.
    :type crs_object: dict
    :returns: The EPSG code, or None if not found.
    :rtype: int or None
    
    .. rubric:: Example
    
    >>> crs = {'type': 'name', 'properties': {'name': 'EPSG:4326'}}
    >>> extract_epsg(crs)
    4326
    """
    type = crs_object['type']
    props = crs_object['properties']
    if type != 'name':
        print('Linked CRS are not implemented')

    crs_string = props.get('name', "")
    match = re.search(r'EPSG[:/]+(?:[\d.]+[:/]+)?(\d+)',
                      crs_string, re.IGNORECASE)
    return int(match.group(1)) if match else None


@dataclass
class GeoJsonBuildingCache(list):
    """
    Cache for storing and managing GeoJSON building data.
    
    Extends list to provide additional functionality for loading GeoJSON files
    and tracking the bounds of loaded building data.
    
    :ivar count: Number of buildings in the cache.
    :vartype count: int
    :ivar bounds: Bounding box as (min_lat, min_lon, max_lat, max_lon).
    :vartype bounds: Tuple[float, float, float, float]
    """
    count = int
    bounds = Tuple[float, float, float, float]

    def __init__(self):
        """Initialize an empty building cache."""
        self._update_props()

    def _update_props(self):
        """Update count and bounds properties based on current contents."""
        # Track bounds of loaded data
        min_lat, min_lon = float('inf'), float('inf')
        max_lat, max_lon = float('-inf'), float('-inf')
        for building in self:
            for lat, lon in building.coordinates:
                min_lat = min(min_lat, lat)
                max_lat = max(max_lat, lat)
                min_lon = min(min_lon, lon)
                max_lon = max(max_lon, lon)
        self.bounds = min_lat, min_lon, max_lat, max_lon
        self.count = len(self)

    def load(self, filepaths: List[str|Path],
             area: Tuple[float, float, float,float]|None = None):
        """
        Load buildings from one or more GeoJSON files.
        
        :param filepaths: List of paths to GeoJSON files to load.
        :type filepaths: List[str or Path]
        :param area: Optional bounding box to filter buildings.
            Format: (lat1, lon1, lat2, lon2). If None, all buildings are loaded.
        :type area: Tuple[float, float, float, float] or None
        :returns: Tuple of (loaded_count, skipped_count).
        :rtype: Tuple[int, int]
        :raises ValueError: If EPSG code cannot be extracted from a file.
        
        .. rubric:: Example
        
        >>> cache = GeoJsonBuildingCache()
        >>> loaded, skipped = cache.load(['buildings.geojson'])
        >>> print(f"Loaded {loaded} buildings, skipped {skipped}")
        """

        if area is None:
            view_lat1, view_lon1 = float('inf'), float('inf')
            view_lat2, view_lon2 = float('-inf'), float('-inf')
        else:
            view_lat1, view_lon1, view_lat2, view_lon2 = area

        loaded_count = 0
        skipped_count = 0

        for filepath in filepaths:
            with open(filepath, 'r', encoding='utf-8') as f:
                data = json.load(f)

            if data.get('type') != 'FeatureCollection':
                print(f"Skipping {filepath}: Not a FeatureCollection")
                continue

            # Check CRS - handle EPSG:3857 (Web Mercator)
            epsg_id = extract_epsg(data.get('crs', {}))
            if epsg_id is None:
                raise ValueError(f"Could not extract EPSG "
                                 f"code from {filepath}")
            transformation = get_epsg2ll(epsg_id)


            for feature in data.get('features', []):
                if feature.get('type') != 'Feature':
                    continue

                props = feature.get('properties', {})
                geom = feature.get('geometry', {})

                if geom.get('type') not in ['Polygon', 'MultiPolygon']:
                    continue

                # Handle both Polygon and MultiPolygon
                if geom.get('type') == 'Polygon':
                    polygon_coords_list = [
                        geom.get('coordinates', [[]])[0]]
                else:  # MultiPolygon
                    polygon_coords_list = [poly[0] for poly in
                                           geom.get('coordinates', [])]

                for polygon_coords in polygon_coords_list:
                    if len(polygon_coords) < 3:
                        continue

                    # Convert coordinates
                    building_coords = []
                    for coord in polygon_coords[
                        :-1]:  # Skip last (duplicate of first)
                        if len(coord) < 2:
                            continue
                        lat, lon, _ = transformation.TransformPoint(coord[0],
                                                           coord[1])
                        building_coords.append((lat, lon))

                    # Skip if not enough coordinates
                    if len(building_coords) < 3:
                        continue

                    feature_id = str(
                        props.get(
                            'id',
                            props.get('osm_id', str(uuid.uuid4()))))

                    # Check if building intersects view
                    if self.polygon_intersects_view(building_coords,
                                                    view_lat1, view_lon1,
                                                    view_lat2, view_lon2):
                        # Check if identical to existing building
                        height = float(props.get('height', 10.0))

                        if id not in [x.feature_id for x in self]:
                            # Get building ID from properties
                            geojson_building = GeoJsonBuilding(
                                coordinates=building_coords,
                                height=height,
                                feature_id=feature_id
                            )

                            # Add additional properties if needed
                            if 'var' in props:
                                geojson_building.height_variance = float(
                                    props['var'])
                            if 'region' in props:
                                geojson_building.region = props[
                                    'region']
                            if 'source' in props:
                                geojson_building.source = props[
                                    'source']

                            self.append(
                                geojson_building)
                            loaded_count += 1
                        else:
                            skipped_count += 1
        self._update_props()
        return loaded_count, skipped_count

    def polygon_intersects_view(self, coords, lat1, lon1, lat2, lon2):
        """
        Check if a polygon intersects with a view rectangle.
        
        :param coords: List of (lat, lon) coordinates defining the polygon.
        :type coords: List[Tuple[float, float]]
        :param lat1: Minimum latitude of view rectangle.
        :type lat1: float
        :param lon1: Minimum longitude of view rectangle.
        :type lon1: float
        :param lat2: Maximum latitude of view rectangle.
        :type lat2: float
        :param lon2: Maximum longitude of view rectangle.
        :type lon2: float
        :returns: True if polygon intersects the view rectangle.
        :rtype: bool
        """
        # Check if any vertex is in view
        for x, y in coords:
            if lat1 <= x <= lat2 and lon1 <= y <= lon2:
                return True

        # Check if polygon bounding box intersects view
        if coords:
            poly_x_min = min(c[0] for c in coords)
            poly_x_max = max(c[0] for c in coords)
            poly_y_min = min(c[1] for c in coords)
            poly_y_max = max(c[1] for c in coords)

            # Check for intersection
            if not (poly_x_max < lat1 or poly_x_min > lat2 or
                    poly_y_max < lon1 or poly_y_min > lon2):
                return True

        # Check if view center is in polygon
        cx, cy = (lat1 + lat2) / 2, (lon1 + lon2) / 2
        inside = False
        n = len(coords)
        j = n - 1
        for i in range(n):
            xi, yi = coords[i]
            xj, yj = coords[j]
            if ((yi > cy) != (yj > cy)) and (
                    cx < (xj - xi) * (cy - yi) / (yj - yi) + xi):
                inside = not inside
            j = i

        return inside



@dataclass
class GeoJsonBuilding:
    """
    Represents a building loaded from GeoJSON for preview and import.
    
    This class stores the polygon coordinates and metadata for a building
    footprint loaded from a GeoJSON file. Buildings can be selected for
    import and converted to CitySketch :class:`Building` objects.
    
    :param coordinates: List of (lat, lon) tuples defining the polygon outline.
    :type coordinates: List[Tuple[float, float]]
    :param height: Building height in meters.
    :type height: float
    :param feature_id: Unique identifier from the GeoJSON feature.
    :type feature_id: str
    :param selected: Whether the building is selected for import. 
        Selected buildings are displayed in green, unselected in red.
    :type selected: bool
    :param imported: Whether the building has been imported.
    :type imported: bool
    :param height_variance: Optional variance in height estimation.
    :type height_variance: float or None
    :param region: Optional region identifier.
    :type region: str or None
    :param source: Optional data source identifier.
    :type source: str or None
    
    .. seealso:: :meth:`to_building`, :meth:`to_buildings`
    """
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
        """
        Check if a point is inside the polygon using ray casting algorithm.
        
        :param x: X-coordinate (latitude) of the point.
        :type x: float
        :param y: Y-coordinate (longitude) of the point.
        :type y: float
        :returns: True if the point is inside the polygon.
        :rtype: bool
        """
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

    def intersects_rect(self, lat1, lon1, lat2, lon2):
        """
        Check if the polygon intersects with a rectangle.
        
        :param lat1: Minimum latitude of rectangle.
        :type lat1: float
        :param lon1: Minimum longitude of rectangle.
        :type lon1: float
        :param lat2: Maximum latitude of rectangle.
        :type lat2: float
        :param lon2: Maximum longitude of rectangle.
        :type lon2: float
        :returns: True if polygon intersects the rectangle.
        :rtype: bool
        """
        # Check if any vertex is inside rect
        for x, y in self.coordinates:
            if lat1 <= x <= lat2 and lon1 <= y <= lon2:
                return True
        # Check if rect center is inside polygon
        cx, cy = (lat1 + lat2) / 2, (lon1 + lon2) / 2
        return self.contains_point(cx, cy)

    def to_buildings(self, storey_height: float = 3.3, geo_to_world=None):
        """
        Convert to one or more CitySketch Building objects by fitting rectangles.
        
        For complex polygon shapes (L-shaped, T-shaped, etc.), multiple
        rectangles may be fitted using the Ferrari-Sankar-Sklansky algorithm.
        
        :param storey_height: Height per storey in meters for calculating
            storey count. Default is 3.3m.
        :type storey_height: float
        :param geo_to_world: Optional function to convert (lat, lon) to 
            world coordinates (x, y). If None, coordinates are used as-is.
        :type geo_to_world: callable or None
        :returns: List of Building objects fitted to the polygon.
        :rtype: List[Building]
        
        .. seealso::
        
            :meth:`to_building`
                Convenience method returning only the first building.
            :class:`RectangleFitter`
                Used internally for rectangle fitting.
        """
        buildings = []
        
        # Convert to world coordinates BEFORE rectangle fitting
        if geo_to_world:
            world_coords = [geo_to_world(lat, lon) for lat, lon in self.coordinates]
        else:
            world_coords = self.coordinates
        
        rectangles = RectangleFitter.fit_multiple_rectangles(world_coords)

        for i, rect_coords in enumerate(rectangles):
            # rect_coords are already in world coordinates now

            # Calculate rotation from first edge
            dx = rect_coords[1][0] - rect_coords[0][0]
            dy = rect_coords[1][1] - rect_coords[0][1]
            rotation = math.atan2(dy, dx)

            # Calculate dimensions
            a = math.sqrt(dx ** 2 + dy ** 2)  # width along first edge
            side2_dx = rect_coords[3][0] - rect_coords[0][0]
            side2_dy = rect_coords[3][1] - rect_coords[0][1]
            b = math.sqrt(
                side2_dx ** 2 + side2_dy ** 2)  # height along second edge

            # x1, y1 is the anchor point (first corner)
            x1, y1 = rect_coords[0]

            building = Building(
                id=f"geojson_{self.feature_id}_{i}" if i > 0 else f"geojson_{self.feature_id}",
                x1=x1,
                y1=y1,
                a=a,
                b=b,
                height=self.height,
                storeys=max(1, round(self.height / storey_height)),
                rotation=rotation
            )

            if i == 0:
                building.polygon_coords = self.coordinates

            buildings.append(building)

        return buildings

    def to_building(self, storey_height: float = 3.3, geo_to_world=None):
        """
        Convert to a single CitySketch Building object.
        
        This is a convenience method that returns only the first (and usually
        largest) fitted rectangle. For complex polygons that decompose into
        multiple buildings, use :meth:`to_buildings` instead.
        
        :param storey_height: Height per storey in meters. Default is 3.3m.
        :type storey_height: float
        :param geo_to_world: Optional coordinate transformation function.
        :type geo_to_world: callable or None
        :returns: The first fitted Building, or None if fitting fails.
        :rtype: Building or None
        
        .. seealso:: :meth:`to_buildings`
        """
        buildings = self.to_buildings(storey_height, geo_to_world=geo_to_world)
        return buildings[0] if buildings else None


class RectangleFitter:
    """
    Fit irregular polygons with one or more rectangles.
    
    Provides static methods for fitting rectangles to building footprint
    polygons. Uses PCA for simple shapes and the Ferrari-Sankar-Sklansky
    algorithm [Ferrari1984]_ for complex L-shaped or T-shaped buildings.
    
    .. seealso::
    
        :mod:`building_simplification`
            Module containing the underlying algorithms.
    """

    @staticmethod
    def _polygon_area(coordinates: List[Tuple[float, float]]) -> float:
        """
        Calculate the area of a polygon using the shoelace formula.
        
        :param coordinates: List of (x, y) polygon vertices.
        :type coordinates: List[Tuple[float, float]]
        :returns: Absolute area of the polygon.
        :rtype: float
        """
        n = len(coordinates)
        if n < 3:
            return 0.0
        
        area = 0.0
        for i in range(n):
            j = (i + 1) % n
            area += coordinates[i][0] * coordinates[j][1]
            area -= coordinates[j][0] * coordinates[i][1]
        return abs(area) / 2.0

    @staticmethod
    def _polygon_intersection_area(poly1: List[Tuple[float, float]], 
                                   poly2: List[Tuple[float, float]]) -> float:
        """
        Calculate the intersection area of two convex polygons using
        Sutherland-Hodgman clipping algorithm.
        
        :param poly1: First polygon vertices.
        :type poly1: List[Tuple[float, float]]
        :param poly2: Second polygon vertices (used as clipping polygon).
        :type poly2: List[Tuple[float, float]]
        :returns: Area of intersection.
        :rtype: float
        """
        def line_intersection(p1, p2, p3, p4):
            """Find intersection point of two line segments."""
            x1, y1 = p1
            x2, y2 = p2
            x3, y3 = p3
            x4, y4 = p4
            
            denom = (x1 - x2) * (y3 - y4) - (y1 - y2) * (x3 - x4)
            if abs(denom) < 1e-10:
                return None
            
            t = ((x1 - x3) * (y3 - y4) - (y1 - y3) * (x3 - x4)) / denom
            x = x1 + t * (x2 - x1)
            y = y1 + t * (y2 - y1)
            return (x, y)
        
        def is_inside(point, edge_start, edge_end):
            """Check if point is on the left side of the edge."""
            return ((edge_end[0] - edge_start[0]) * (point[1] - edge_start[1]) - 
                    (edge_end[1] - edge_start[1]) * (point[0] - edge_start[0])) >= 0
        
        output = list(poly1)
        
        for i in range(len(poly2)):
            if len(output) == 0:
                return 0.0
            
            input_poly = output
            output = []
            
            edge_start = poly2[i]
            edge_end = poly2[(i + 1) % len(poly2)]
            
            for j in range(len(input_poly)):
                current = input_poly[j]
                next_pt = input_poly[(j + 1) % len(input_poly)]
                
                if is_inside(current, edge_start, edge_end):
                    if is_inside(next_pt, edge_start, edge_end):
                        output.append(next_pt)
                    else:
                        intersection = line_intersection(current, next_pt, edge_start, edge_end)
                        if intersection:
                            output.append(intersection)
                elif is_inside(next_pt, edge_start, edge_end):
                    intersection = line_intersection(current, next_pt, edge_start, edge_end)
                    if intersection:
                        output.append(intersection)
                    output.append(next_pt)
        
        return RectangleFitter._polygon_area(output)

    @staticmethod
    def _calculate_fit_quality(original_coords: List[Tuple[float, float]],
                               fitted_rect_coords: List[Tuple[float, float]]) -> float:
        """
        Calculate how well a fitted rectangle matches the original polygon.
        
        Returns the ratio of non-overlapping area to total area. A value of 0
        means perfect fit, a value of 1 means no overlap at all.
        
        :param original_coords: Original polygon vertices.
        :type original_coords: List[Tuple[float, float]]
        :param fitted_rect_coords: Fitted rectangle vertices (4 corners).
        :type fitted_rect_coords: List[Tuple[float, float]]
        :returns: Non-overlap ratio (0.0 = perfect fit, 1.0 = no overlap).
        :rtype: float
        """
        original_area = RectangleFitter._polygon_area(original_coords)
        rect_area = RectangleFitter._polygon_area(fitted_rect_coords)
        
        if original_area < 1e-10 or rect_area < 1e-10:
            return 1.0
        
        # Calculate intersection area
        intersection_area = RectangleFitter._polygon_intersection_area(
            original_coords, fitted_rect_coords)
        
        # Non-overlapping area = (original - intersection) + (rect - intersection)
        # This is the symmetric difference
        non_overlap_area = (original_area - intersection_area) + (rect_area - intersection_area)
        total_area = original_area + rect_area - intersection_area  # Union area
        
        if total_area < 1e-10:
            return 1.0
        
        return non_overlap_area / total_area

    @staticmethod
    def fit_single_rectangle(coordinates: List[Tuple[float, float]]) -> \
    Tuple[float, float, float, float, float]:
        """
        Fit a single rectangle to a polygon using PCA for orientation.
        
        Uses Principal Component Analysis to find the optimal orientation
        and then computes the bounding box in that orientation.
        
        :param coordinates: List of (x, y) polygon vertices.
        :type coordinates: List[Tuple[float, float]]
        :returns: Tuple of (cx, cy, width, height, angle) where cx, cy is the
            center, width and height are dimensions, and angle is rotation
            in radians.
        :rtype: Tuple[float, float, float, float, float]
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
            coordinates: List[Tuple[float, float]], 
            check_fit_quality: bool = True) -> bool:
        """
        Check if a polygon is approximately rectangular.
        
        Analyzes the interior angles to determine if the polygon has
        mostly right angles (within :data:`ANGLE_TOLERANCE`). Optionally
        also verifies that a fitted rectangle has good overlap with the
        original polygon (within :data:`MAX_NON_OVERLAP_RATIO`).
        
        :param coordinates: List of (x, y) polygon vertices.
        :type coordinates: List[Tuple[float, float]]
        :param check_fit_quality: If True, also verify the fitted rectangle
            has acceptable overlap with the original polygon.
        :type check_fit_quality: bool
        :returns: True if the polygon is approximately rectangular and
            (if check_fit_quality is True) the fit is acceptable.
        :rtype: bool
        """
        if len(coordinates) < 4:
            return False
        
        # For very simple polygons, accept them
        if len(coordinates) == 4:
            # Still check fit quality for 4-vertex polygons
            if check_fit_quality:
                fitted_corners = RectangleFitter.simplify_to_rectangle(coordinates)
                non_overlap = RectangleFitter._calculate_fit_quality(
                    coordinates, fitted_corners)
                return non_overlap <= get_max_non_overlap_ratio()
            return True
        
        if len(coordinates) > 8:
            return False

        # Check angles
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
            1 for a in angles if abs(a - 90) < get_angle_tolerance())
        has_rectangular_angles = right_angles >= len(coordinates) - 2
        
        if not has_rectangular_angles:
            return False
        
        # Check fit quality if requested
        if check_fit_quality:
            fitted_corners = RectangleFitter.simplify_to_rectangle(coordinates)
            non_overlap = RectangleFitter._calculate_fit_quality(
                coordinates, fitted_corners)
            return non_overlap <= get_max_non_overlap_ratio()
        
        return True

    @staticmethod
    def simplify_to_rectangle(coordinates: List[Tuple[float, float]]) -> \
    List[Tuple[float, float]]:
        """
        Simplify an approximately rectangular polygon to exactly 4 corners.
        
        :param coordinates: List of (x, y) polygon vertices.
        :type coordinates: List[Tuple[float, float]]
        :returns: List of 4 corner points in order.
        :rtype: List[Tuple[float, float]]
        """
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
                                max_rectangles: int = 5) -> List[
        List[Tuple[float, float]]]:
        """
        Fit a polygon with multiple rectangles for complex shapes.
        
        For L-shaped, T-shaped, and other complex building footprints,
        this method decomposes the polygon into multiple rectangles using
        the Ferrari-Sankar-Sklansky algorithm [Ferrari1984]_ combined with
        Bayer's building simplification [Bayer2009]_.
        
        :param coordinates: List of (x, y) polygon vertices.
        :type coordinates: List[Tuple[float, float]]
        :param max_rectangles: Maximum number of rectangles to return.
            If more rectangles are produced, only the largest by area
            are kept. Default is 5.
        :type max_rectangles: int
        :returns: List of rectangle corner lists, each with 4 corners.
        :rtype: List[List[Tuple[float, float]]]
        
        .. rubric:: Algorithm
        
        1. Find the building's principal orientation using smallest 
           enclosing rectangle
        2. Rotate to axis-aligned position
        3. Simplify to rectilinear shape using :class:`BuildingSimplifier`
        4. Partition into minimal rectangles using :class:`RectangularPartitioner`
        5. Rotate resulting rectangles back to original orientation
        """
        if len(coordinates) < 4:
            return [RectangleFitter.simplify_to_rectangle(coordinates)]
        
        # Check if already approximately rectangular
        if RectangleFitter.is_approximately_rectangular(coordinates):
            return [RectangleFitter.simplify_to_rectangle(coordinates)]
        
        # Step 1: Find the building's principal orientation
        rect, angle = smallest_enclosing_rectangle(coordinates)
        
        # Step 2: Rotate to axis-aligned position
        centroid = (
            sum(p[0] for p in coordinates) / len(coordinates),
            sum(p[1] for p in coordinates) / len(coordinates)
        )
        rotated_coords = rotate_polygon(coordinates, -angle, centroid)
        
        # Step 3: Simplify to rectilinear shape
        simplifier = BuildingSimplifier(sigma_max=get_distance_tolerance())
        simplified = simplifier.simplify(rotated_coords)
        
        # Step 4: Partition into minimal rectangles
        partitioner = RectangularPartitioner(tolerance=0.1)
        rectangles = partitioner.partition(simplified)
        
        if not rectangles:
            # Fallback to single rectangle
            return [RectangleFitter.simplify_to_rectangle(coordinates)]
        
        # Limit number of rectangles
        if len(rectangles) > max_rectangles:
            # Sort by area and keep largest ones
            rectangles = sorted(rectangles, key=lambda r: r.area, reverse=True)
            rectangles = rectangles[:max_rectangles]
        
        # Step 5: Convert rectangles back to corner lists and rotate back
        result = []
        for rect in rectangles:
            # Get corners of axis-aligned rectangle
            corners = [
                (rect.x_min, rect.y_min),
                (rect.x_max, rect.y_min),
                (rect.x_max, rect.y_max),
                (rect.x_min, rect.y_max)
            ]
            # Rotate back to original orientation
            rotated_corners = rotate_polygon(corners, angle, centroid)
            result.append(rotated_corners)
        
        return result if result else [RectangleFitter.simplify_to_rectangle(coordinates)]


class BuildingMerger:
    """
    Merge CitySketch buildings into unified GeoJSON building footprints.
    
    Provides static methods for detecting shared walls, checking intersections,
    and merging adjacent buildings with similar heights into single polygons.
    """

    @staticmethod
    def buildings_share_wall(b1, b2, tolerance: float = 0.5) -> bool:
        """
        Check if two buildings share at least one wall.
        
        :param b1: First building object.
        :param b2: Second building object.
        :param tolerance: Distance tolerance in coordinate units for 
            determining if edges are shared. Default is 0.5.
        :type tolerance: float
        :returns: True if buildings share a wall.
        :rtype: bool
        """
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
        """
        Check if two edges form a shared wall.
        
        :param e1_start: Start point of first edge.
        :param e1_end: End point of first edge.
        :param e2_start: Start point of second edge.
        :param e2_end: End point of second edge.
        :param tolerance: Distance tolerance.
        :type tolerance: float
        :returns: True if edges form a shared wall.
        :rtype: bool
        """
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
        """
        Calculate distance from a point to a line segment.
        
        :param point: The point as (x, y).
        :param line_start: Start point of line segment.
        :param line_end: End point of line segment.
        :returns: Distance from point to line segment.
        :rtype: float
        """
        x0, y0 = point
        lat1, lon1 = line_start
        lat2, lon2 = line_end

        dx = lat2 - lat1
        dy = lon2 - lon1

        if dx == 0 and dy == 0:
            return math.sqrt((x0 - lat1) ** 2 + (y0 - lon1) ** 2)

        t = ((x0 - lat1) * dx + (y0 - lon1) * dy) / (dx ** 2 + dy ** 2)
        t = max(0, min(1, t))

        closest_x = lat1 + t * dx
        closest_y = lon1 + t * dy

        return math.sqrt((x0 - closest_x) ** 2 + (y0 - closest_y) ** 2)

    @staticmethod
    def _project_point_on_line(point, line_start, line_end):
        """
        Project a point onto a line and return the parameter t.
        
        :param point: The point as (x, y).
        :param line_start: Start point of line.
        :param line_end: End point of line.
        :returns: Parameter t where 0 <= t <= 1 means point projects onto segment.
        :rtype: float
        """
        x0, y0 = point
        lat1, lon1 = line_start
        lat2, lon2 = line_end

        dx = lat2 - lat1
        dy = lon2 - lon1

        if dx == 0 and dy == 0:
            return 0

        return ((x0 - lat1) * dx + (y0 - lon1) * dy) / (dx ** 2 + dy ** 2)

    @staticmethod
    def buildings_intersect(b1, b2) -> bool:
        """
        Check if two buildings' outlines intersect.
        
        :param b1: First building object.
        :param b2: Second building object.
        :returns: True if building outlines intersect.
        :rtype: bool
        """
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
        """
        Check if a point is inside a polygon using ray casting.
        
        :param point: The point as (x, y).
        :param polygon: List of polygon vertices.
        :returns: True if point is inside polygon.
        :rtype: bool
        """
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
        """
        Check if line segments p1-p2 and p3-p4 intersect.
        
        :param p1: First point of first segment.
        :param p2: Second point of first segment.
        :param p3: First point of second segment.
        :param p4: Second point of second segment.
        :returns: True if segments intersect.
        :rtype: bool
        """

        def ccw(A, B, C):
            return (C[1] - A[1]) * (B[0] - A[0]) > (B[1] - A[1]) * (
                        C[0] - A[0])

        return ccw(p1, p3, p4) != ccw(p2, p3, p4) and ccw(p1, p2,
                                                          p3) != ccw(p1,
                                                                     p2,
                                                                     p4)

    @staticmethod
    def merge_buildings_to_geojson(buildings: List,
                                   height_tolerance: float = None) -> \
    Optional[GeoJsonBuilding]:
        """
        Merge a list of CitySketch buildings into a single GeoJSON building.
        
        Buildings are merged if they share walls or intersect and have
        similar heights (within the specified tolerance).
        
        :param buildings: List of Building objects to merge.
        :type buildings: List[Building]
        :param height_tolerance: Maximum relative height difference allowed
            for merging. Default is from settings (HEIGHT_TOLERANCE, typically 10%).
        :type height_tolerance: float
        :returns: Merged GeoJsonBuilding, or None if buildings cannot be merged.
        :rtype: GeoJsonBuilding or None
        
        .. note::
        
            The merged building uses the convex hull of all input building
            corners, which may not perfectly represent complex merged shapes.
        """
        # Use settings default if not specified
        if height_tolerance is None:
            height_tolerance = get_height_tolerance()
            
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
            area = abs((b.lat2 - b.lat1) * (b.lon2 - b.lon1))
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
        """
        Compute convex hull of points using Graham scan algorithm.
        
        :param points: List of (x, y) points.
        :type points: List[Tuple[float, float]]
        :returns: List of points forming the convex hull.
        :rtype: List[Tuple[float, float]]
        """
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
        """
        Counter-clockwise test for three points.
        
        :param p1: First point.
        :param p2: Second point.
        :param p3: Third point.
        :returns: Positive if counter-clockwise, negative if clockwise, 
            zero if collinear.
        :rtype: float
        """
        return (p2[0] - p1[0]) * (p3[1] - p1[1]) - (p2[1] - p1[1]) * (
                    p3[0] - p1[0])


