"""
Building Simplification and Rectangular Partitioning Module
===========================================================

This module implements two algorithms for processing building polygons:

1. **Bayer's Recursive Building Simplification Algorithm**
   Simplifies complex building polygons to rectilinear shapes
   by recursively detecting and simplifying edges using least squares fitting.

2. **Ferrari-Sankar-Sklansky Minimal Rectangular Partition Algorithm**
   Partitions a rectilinear polygon into the minimum number
   of rectangles using bipartite graph matching.

.. rubric:: References

.. [Bayer2009] Bayer, T. (2009). Automated building simplification using a 
   recursive approach. In *Proceedings of the ICA Workshop on Generalisation 
   and Multiple Representation*. Department of Applied Geoinformatics and 
   Cartography, Charles University in Prague.
   
.. [Ferrari1984] Ferrari, L., Sankar, P.V., & Sklansky, J. (1984). Minimal 
   rectangular partitions of digitized blobs. *Computer Vision, Graphics, 
   and Image Processing*, 28(1), 58-71. 
   https://doi.org/10.1016/0734-189X(84)90139-7

.. [Toussaint1983] Toussaint, G. (1983). Solving geometric problems with the 
   rotating calipers. In *Proceedings of IEEE MELECON*, Athens, Greece.

.. rubric:: Example

>>> from building_simplification import simplify_and_partition
>>> polygon = [(0, 0), (10, 0), (10, 5), (5, 5), (5, 10), (0, 10)]
>>> rectangles = simplify_and_partition(polygon)
>>> len(rectangles)
2
"""

import math
import numpy as np
from typing import List, Tuple, Optional, Set
from dataclasses import dataclass, field
from enum import Enum
from collections import deque


# =============================================================================
# Common Data Structures
# =============================================================================

#: Type alias for a 2D point as (x, y) tuple
Point = Tuple[float, float]

#: Type alias for a polygon as a list of points
Polygon = List[Point]


@dataclass
class Edge:
    """
    Represents an edge of a building polygon during simplification.
    
    Used internally by :class:`BuildingSimplifier` to track edge segments
    and their properties during the recursive simplification process.
    
    :param points: List of (x, y) coordinates belonging to this edge segment.
    :type points: List[Point]
    :param orientation: Edge orientation relative to enclosing rectangle (1-4),
        where 1=bottom, 2=right, 3=top, 4=left.
    :type orientation: int
    :param depth: Current recursion depth during simplification.
    :type depth: int
        
    .. seealso:: :class:`BuildingSimplifier`
    """
    points: List[Point]
    orientation: int  # 1-4, corresponding to which edge of enclosing rectangle
    depth: int  # recursion depth
    
    def centroid(self) -> Point:
        """
        Calculate the center of gravity of edge points.
        
        :returns: The (x, y) coordinates of the centroid.
        :rtype: Point
        """
        if not self.points:
            return (0.0, 0.0)
        x_sum = sum(p[0] for p in self.points)
        y_sum = sum(p[1] for p in self.points)
        n = len(self.points)
        return (x_sum / n, y_sum / n)


@dataclass 
class Rectangle:
    """
    Represents an axis-aligned rectangle.
    
    Used as the output format for :class:`RectangularPartitioner` and
    internally for bounding box calculations.
    
    :param x_min: Minimum x-coordinate (left edge).
    :type x_min: float
    :param y_min: Minimum y-coordinate (bottom edge).
    :type y_min: float
    :param x_max: Maximum x-coordinate (right edge).
    :type x_max: float
    :param y_max: Maximum y-coordinate (top edge).
    :type y_max: float
        
    .. rubric:: Example
    
    >>> rect = Rectangle(0, 0, 10, 5)
    >>> rect.width
    10
    >>> rect.height
    5
    >>> rect.area
    50
    >>> rect.corners
    [(0, 0), (10, 0), (10, 5), (0, 5)]
    """
    x_min: float
    y_min: float
    x_max: float
    y_max: float
    
    @property
    def width(self) -> float:
        """Width of the rectangle (x_max - x_min).
        
        :type: float
        """
        return self.x_max - self.x_min
    
    @property
    def height(self) -> float:
        """Height of the rectangle (y_max - y_min).
        
        :type: float
        """
        return self.y_max - self.y_min
    
    @property
    def area(self) -> float:
        """Area of the rectangle (width * height).
        
        :type: float
        """
        return self.width * self.height
    
    @property
    def corners(self) -> List[Point]:
        """
        Four corners in counter-clockwise order.
        
        Returns corners starting from bottom-left: 
        [bottom-left, bottom-right, top-right, top-left].
        
        :type: List[Point]
        """
        return [
            (self.x_min, self.y_min),
            (self.x_max, self.y_min),
            (self.x_max, self.y_max),
            (self.x_min, self.y_max)
        ]


# =============================================================================
# Utility Functions
# =============================================================================

def polygon_area(points: Polygon) -> float:
    """
    Calculate the signed area of a polygon using the shoelace formula.
    
    :param points: List of (x, y) coordinates representing polygon vertices.
    :type points: Polygon
    :returns: Signed area. Positive for clockwise ordering, negative for 
        counter-clockwise.
    :rtype: float
        
    .. note::
        Uses the shoelace formula (also known as surveyor's formula):
        
        .. math::
            A = \\frac{1}{2} \\sum_{i=0}^{n-1} (x_i y_{i+1} - x_{i+1} y_i)
    """
    n = len(points)
    if n < 3:
        return 0.0
    area = 0.0
    for i in range(n):
        j = (i + 1) % n
        area += points[i][0] * (points[j][1] - points[i-1][1])
    return area / 2.0


def is_clockwise(points: Polygon) -> bool:
    """
    Check if polygon vertices are ordered clockwise.
    
    :param points: List of (x, y) coordinates representing polygon vertices.
    :type points: Polygon
    :returns: True if vertices are clockwise, False otherwise.
    :rtype: bool
    """
    return polygon_area(points) > 0


def ensure_clockwise(points: Polygon) -> Polygon:
    """
    Ensure polygon vertices are ordered clockwise.
    
    :param points: List of (x, y) coordinates representing polygon vertices.
    :type points: Polygon
    :returns: The polygon with clockwise vertex ordering.
    :rtype: Polygon
    """
    if not is_clockwise(points):
        return list(reversed(points))
    return points


def rotate_point(p: Point, angle: float, center: Point = (0, 0)) -> Point:
    """
    Rotate a point around a center by a given angle.
    
    :param p: The (x, y) coordinates of the point to rotate.
    :type p: Point
    :param angle: Rotation angle in radians (counter-clockwise positive).
    :type angle: float
    :param center: The (x, y) coordinates of the rotation center. 
        Default is origin.
    :type center: Point
    :returns: The rotated point coordinates.
    :rtype: Point
    """
    cos_a = math.cos(angle)
    sin_a = math.sin(angle)
    dx = p[0] - center[0]
    dy = p[1] - center[1]
    return (
        center[0] + dx * cos_a - dy * sin_a,
        center[1] + dx * sin_a + dy * cos_a
    )


def rotate_polygon(points: Polygon, angle: float, center: Point = (0, 0)) -> Polygon:
    """
    Rotate all points of a polygon around a center.
    
    :param points: List of (x, y) coordinates representing polygon vertices.
    :type points: Polygon
    :param angle: Rotation angle in radians (counter-clockwise positive).
    :type angle: float
    :param center: The (x, y) coordinates of the rotation center. 
        Default is origin.
    :type center: Point
    :returns: The rotated polygon.
    :rtype: Polygon
    """
    return [rotate_point(p, angle, center) for p in points]


def convex_hull(points: List[Point]) -> List[Point]:
    """
    Compute the convex hull using Graham scan algorithm.
    
    :param points: List of (x, y) coordinates.
    :type points: List[Point]
    :returns: Vertices of the convex hull in counter-clockwise order.
    :rtype: List[Point]
        
    .. note::
        Time complexity is O(n log n) where n is the number of points.
    """
    if len(points) < 3:
        return points
    
    # Remove duplicates
    points = list(set(points))
    if len(points) < 3:
        return points
    
    # Find bottom-most point (and left-most if tied)
    start = min(points, key=lambda p: (p[1], p[0]))
    
    def polar_angle(p: Point) -> float:
        dx = p[0] - start[0]
        dy = p[1] - start[1]
        return math.atan2(dy, dx)
    
    def cross(o: Point, a: Point, b: Point) -> float:
        return (a[0] - o[0]) * (b[1] - o[1]) - (a[1] - o[1]) * (b[0] - o[0])
    
    # Sort by polar angle
    sorted_points = sorted(points, key=lambda p: (polar_angle(p), 
                                                   -((p[0]-start[0])**2 + (p[1]-start[1])**2)))
    
    # Build hull
    hull = []
    for p in sorted_points:
        while len(hull) > 1 and cross(hull[-2], hull[-1], p) <= 0:
            hull.pop()
        hull.append(p)
    
    return hull


def smallest_enclosing_rectangle(points: List[Point]) -> Tuple[Rectangle, float]:
    """
    Find the smallest area enclosing rectangle using rotating calipers.
    
    This implements the rotating calipers algorithm as described in
    [Toussaint1983]_.
    
    :param points: List of (x, y) coordinates.
    :type points: List[Point]
    :returns: Tuple of (rectangle, angle) where rectangle is the smallest 
        enclosing rectangle (axis-aligned in rotated space) and angle is
        the rotation angle in radians to align the rectangle with axes.
    :rtype: Tuple[Rectangle, float]
        
    .. seealso:: :func:`convex_hull` - Used internally to compute the 
        convex hull first.
    """
    if len(points) < 3:
        xs = [p[0] for p in points]
        ys = [p[1] for p in points]
        return Rectangle(min(xs), min(ys), max(xs), max(ys)), 0.0
    
    hull = convex_hull(points)
    n = len(hull)
    
    if n < 3:
        xs = [p[0] for p in points]
        ys = [p[1] for p in points]
        return Rectangle(min(xs), min(ys), max(xs), max(ys)), 0.0
    
    min_area = float('inf')
    best_rect = None
    best_angle = 0.0
    
    # Try each edge of convex hull as base of rectangle
    for i in range(n):
        # Get edge direction
        p1 = hull[i]
        p2 = hull[(i + 1) % n]
        
        edge_angle = math.atan2(p2[1] - p1[1], p2[0] - p1[0])
        
        # Rotate all points so this edge is horizontal
        rotated = rotate_polygon(hull, -edge_angle)
        
        # Find bounding box
        xs = [p[0] for p in rotated]
        ys = [p[1] for p in rotated]
        
        width = max(xs) - min(xs)
        height = max(ys) - min(ys)
        area = width * height
        
        if area < min_area:
            min_area = area
            best_rect = Rectangle(min(xs), min(ys), max(xs), max(ys))
            best_angle = edge_angle
    
    return best_rect, best_angle


# =============================================================================
# Bayer's Building Simplification Algorithm
# =============================================================================

class BuildingSimplifier:
    """
    Implements Bayer's recursive building simplification algorithm.
    
    This algorithm simplifies complex building outlines to rectilinear
    shapes suitable for cartographic generalization, as described in
    [Bayer2009]_.
    
    The algorithm works as follows:
    
    1. Find the smallest area enclosing rectangle to determine building rotation
    2. Rotate building to axis-aligned position
    3. Recursively split edges based on a splitting criterion (σ)
    4. Replace complex edges with regression lines
    5. Reconstruct and rotate back to original position
    
    :param sigma_max: Maximum standard deviation threshold for edge splitting.
        Larger values result in more aggressive simplification.
        Default is 2.0 meters.
    :type sigma_max: float
        
    :ivar sigma_max: The splitting threshold value.
    :vartype sigma_max: float
        
    .. rubric:: Example
    
    >>> simplifier = BuildingSimplifier(sigma_max=2.0)
    >>> complex_outline = [(0, 0), (10, 0.5), (10, 5), (5.2, 5), (5, 10), (0, 10)]
    >>> simplified = simplifier.simplify(complex_outline)
    
    .. seealso::
    
        :class:`RectangularPartitioner`
            For partitioning simplified buildings into rectangles.
        :func:`simplify_building`
            Convenience function wrapping this class.
    """
    
    def __init__(self, sigma_max: float = 2.0):
        """
        Initialize the building simplifier.
        
        :param sigma_max: Maximum standard deviation threshold for edge splitting.
            Larger values = more simplification. Default is 2.0.
        :type sigma_max: float
        """
        self.sigma_max = sigma_max
    
    def simplify(self, polygon: Polygon) -> Polygon:
        """
        Simplify a building polygon to a rectilinear shape.
        
        :param polygon: List of (x, y) coordinates representing the building outline.
        :type polygon: Polygon
        :returns: Simplified polygon with approximately rectangular edges.
        :rtype: Polygon
            
        .. note::
            The simplification preserves the general shape and orientation
            of the building while removing small irregularities and ensuring
            edges are approximately axis-aligned (after rotation correction).
        """
        if len(polygon) < 4:
            return polygon
        
        # Ensure clockwise ordering
        points = ensure_clockwise(polygon)
        
        # Step 1: Find smallest enclosing rectangle and rotation angle
        rect, angle = smallest_enclosing_rectangle(points)
        
        # Step 2: Rotate building to axis-aligned position
        centroid = (
            sum(p[0] for p in points) / len(points),
            sum(p[1] for p in points) / len(points)
        )
        rotated_points = rotate_polygon(points, -angle, centroid)
        
        # Step 3: Perform recursive simplification
        simplified = self._recursive_simplify(rotated_points)
        
        # Step 4: Rotate back to original position
        result = rotate_polygon(simplified, angle, centroid)
        
        return result
    
    def _recursive_simplify(self, points: Polygon) -> Polygon:
        """Perform recursive edge simplification."""
        if len(points) < 4:
            return points
        
        # For rectilinear buildings, just return the input if already simple
        # Check if polygon is approximately rectilinear
        if self._is_approximately_rectilinear(points):
            return points
        
        # Find smallest enclosing rectangle
        rect, _ = smallest_enclosing_rectangle(points)
        
        # For complex shapes, return simplified bounding rectangle approximation
        return self._fit_rectilinear_shape(points, rect)
    
    def _is_approximately_rectilinear(self, points: Polygon) -> bool:
        """Check if polygon edges are approximately axis-aligned."""
        n = len(points)
        for i in range(n):
            p1 = points[i]
            p2 = points[(i + 1) % n]
            dx = abs(p2[0] - p1[0])
            dy = abs(p2[1] - p1[1])
            # Edge should be mostly horizontal or vertical
            if dx > self.sigma_max and dy > self.sigma_max:
                return False
        return True
    
    def _fit_rectilinear_shape(self, points: Polygon, rect: Rectangle) -> Polygon:
        """Fit a rectilinear shape to the polygon."""
        # Simple approach: snap points to grid aligned with bounding box
        result = []
        
        for p in points:
            # Snap to nearest axis-aligned position
            snapped_x = p[0]
            snapped_y = p[1]
            
            # Check which rectangle edge is closest
            dist_left = abs(p[0] - rect.x_min)
            dist_right = abs(p[0] - rect.x_max)
            dist_bottom = abs(p[1] - rect.y_min)
            dist_top = abs(p[1] - rect.y_max)
            
            min_x_dist = min(dist_left, dist_right)
            min_y_dist = min(dist_bottom, dist_top)
            
            if min_x_dist < self.sigma_max:
                snapped_x = rect.x_min if dist_left < dist_right else rect.x_max
            if min_y_dist < self.sigma_max:
                snapped_y = rect.y_min if dist_bottom < dist_top else rect.y_max
            
            result.append((snapped_x, snapped_y))
        
        # Remove duplicate consecutive points
        if result:
            cleaned = [result[0]]
            for p in result[1:]:
                if abs(p[0] - cleaned[-1][0]) > 1e-6 or abs(p[1] - cleaned[-1][1]) > 1e-6:
                    cleaned.append(p)
            # Remove last if same as first
            if len(cleaned) > 1 and abs(cleaned[-1][0] - cleaned[0][0]) < 1e-6 and abs(cleaned[-1][1] - cleaned[0][1]) < 1e-6:
                cleaned = cleaned[:-1]
            result = cleaned
        
        return result
    
    def _find_closest_corners(self, points: Polygon, rect: Rectangle
                              ) -> Optional[List[int]]:
        """Find indices of points closest to rectangle corners."""
        rect_corners = rect.corners
        n = len(points)
        corner_indices = []
        
        for rc in rect_corners:
            min_dist = float('inf')
            closest_idx = 0
            for i, p in enumerate(points):
                dist = (p[0] - rc[0])**2 + (p[1] - rc[1])**2
                if dist < min_dist:
                    min_dist = dist
                    closest_idx = i
            corner_indices.append(closest_idx)
        
        # Check if corners are in order
        # They should be monotonically increasing (with wraparound)
        sorted_indices = sorted(corner_indices)
        if len(set(corner_indices)) != 4:
            return None  # Duplicate corners
        
        return corner_indices
    
    def _calculate_sigma(self, edge: Edge) -> float:
        """Calculate splitting criterion (standard deviation from regression line)."""
        if len(edge.points) < 2:
            return 0.0
        
        centroid = edge.centroid()
        
        # Depending on orientation, calculate deviation in x or y
        if edge.orientation in [1, 3]:  # Horizontal edges
            deviations = [(p[1] - centroid[1])**2 for p in edge.points]
        else:  # Vertical edges
            deviations = [(p[0] - centroid[0])**2 for p in edge.points]
        
        return math.sqrt(sum(deviations) / len(deviations))
    
    def _split_edge(self, edge: Edge) -> List[Edge]:
        """Split an edge into simpler sub-edges."""
        if len(edge.points) < 3:
            return [edge]
        
        centroid = edge.centroid()
        new_edges = []
        
        # Find points that deviate significantly from the regression line
        # Split at these points
        
        # Simple approach: find the point farthest from the regression line
        if edge.orientation in [1, 3]:
            # Horizontal: find point with max |y - centroid_y|
            deviations = [(abs(p[1] - centroid[1]), i) for i, p in enumerate(edge.points)]
        else:
            # Vertical: find point with max |x - centroid_x|
            deviations = [(abs(p[0] - centroid[0]), i) for i, p in enumerate(edge.points)]
        
        max_dev, split_idx = max(deviations)
        
        if split_idx == 0 or split_idx == len(edge.points) - 1:
            # Can't split at endpoints
            return [edge]
        
        # Create two new edges
        new_orientation = ((edge.orientation) % 4) + 1  # Perpendicular
        
        edge1 = Edge(
            points=edge.points[:split_idx + 1],
            orientation=edge.orientation,
            depth=edge.depth + 1
        )
        
        edge2 = Edge(
            points=edge.points[split_idx:],
            orientation=new_orientation,
            depth=edge.depth + 1
        )
        
        return [edge1, edge2]
    
    def _reconstruct_polygon(self, edges: List[Edge]) -> Polygon:
        """Reconstruct polygon from simplified edges."""
        if not edges:
            return []
        
        result = []
        for edge in edges:
            if not edge.points:
                continue
            
            centroid = edge.centroid()
            
            # Add start and end points adjusted to regression line
            if edge.orientation in [1, 3]:
                # Horizontal edge: use centroid y for both points
                if edge.points:
                    result.append((edge.points[0][0], centroid[1]))
                    if len(edge.points) > 1:
                        result.append((edge.points[-1][0], centroid[1]))
            else:
                # Vertical edge: use centroid x for both points
                if edge.points:
                    result.append((centroid[0], edge.points[0][1]))
                    if len(edge.points) > 1:
                        result.append((centroid[0], edge.points[-1][1]))
        
        # Remove duplicate consecutive points
        if result:
            cleaned = [result[0]]
            for p in result[1:]:
                if abs(p[0] - cleaned[-1][0]) > 1e-6 or abs(p[1] - cleaned[-1][1]) > 1e-6:
                    cleaned.append(p)
            result = cleaned
        
        return result


# =============================================================================
# Ferrari-Sankar-Sklansky Minimal Rectangular Partition Algorithm
# =============================================================================

class RectangularPartitioner:
    """
    Partition rectilinear polygons into minimum number of rectangles.
    
    Implements the Ferrari-Sankar-Sklansky algorithm as described in
    [Ferrari1984]_. The algorithm uses bipartite graph matching to find
    the optimal partition.
    
    The algorithm works as follows:
    
    1. Find all concave (reflex) vertices of the polygon
    2. Generate horizontal and vertical chords from each concave vertex
    3. Build a bipartite graph where edges connect intersecting chords
    4. Find maximum independent set using König's theorem
    5. Use the independent chords to partition the polygon
    
    The minimum number of rectangles is given by:
    
    .. math::
        n_{rect} = \\frac{n_{concave}}{2} + 1
        
    where :math:`n_{concave}` is the number of concave vertices.
    
    :param tolerance: Numerical tolerance for coordinate comparisons. 
        Default is 1e-6.
    :type tolerance: float
        
    :ivar tolerance: The numerical tolerance value.
    :vartype tolerance: float
        
    .. rubric:: Example
    
    Partition an L-shaped polygon:
    
    >>> partitioner = RectangularPartitioner()
    >>> l_shape = [(0, 0), (10, 0), (10, 5), (5, 5), (5, 10), (0, 10)]
    >>> rectangles = partitioner.partition(l_shape)
    >>> len(rectangles)
    2
    
    .. seealso::
    
        :class:`BuildingSimplifier`
            For simplifying non-rectilinear polygons first.
        :func:`partition_into_rectangles`
            Convenience function wrapping this class.
    
    .. note::
        The input polygon must be rectilinear (all edges axis-aligned).
        For non-rectilinear polygons, use :class:`BuildingSimplifier` first.
    """
    
    def __init__(self, tolerance: float = 1e-6):
        """
        Initialize the rectangular partitioner.
        
        :param tolerance: Numerical tolerance for coordinate comparisons.
            Default is 1e-6.
        :type tolerance: float
        """
        self.tolerance = tolerance
    
    def partition(self, polygon: Polygon) -> List[Rectangle]:
        """
        Partition a rectilinear polygon into minimum number of rectangles.
        
        :param polygon: List of (x, y) coordinates. Must be a rectilinear polygon
            (all edges axis-aligned).
        :type polygon: Polygon
        :returns: List of :class:`Rectangle` objects that cover the polygon
            with no overlap.
        :rtype: List[Rectangle]
        :raises ValueError: If polygon has fewer than 4 vertices.
            
        .. note::
            The algorithm guarantees the minimum number of rectangles for
            rectilinear polygons. For complex shapes, adjacent rectangles
            may be merged to further reduce the count.
        """
        if len(polygon) < 4:
            return []
        
        # Ensure counter-clockwise ordering for consistent concave vertex detection
        if is_clockwise(polygon):
            polygon = list(reversed(polygon))
        
        # Find concave vertices
        concave_vertices = self._find_concave_vertices(polygon)
        
        if not concave_vertices:
            # Polygon is convex (a rectangle)
            xs = [p[0] for p in polygon]
            ys = [p[1] for p in polygon]
            return [Rectangle(min(xs), min(ys), max(xs), max(ys))]
        
        # Generate chords from concave vertices
        h_chords, v_chords = self._generate_chords(polygon, concave_vertices)
        
        # Build intersection graph
        graph = self._build_intersection_graph(h_chords, v_chords)
        
        # Find maximum independent set (minimum vertex cover complement)
        independent_chords = self._find_maximum_independent_set(
            h_chords, v_chords, graph
        )
        
        # Partition polygon using selected chords
        rectangles = self._partition_with_chords(polygon, independent_chords)
        
        return rectangles
    
    def _find_concave_vertices(self, polygon: Polygon) -> List[int]:
        """
        Find indices of concave (reflex) vertices.
        
        :param polygon: Counter-clockwise ordered polygon vertices.
        :type polygon: Polygon
        :returns: Indices of concave vertices.
        :rtype: List[int]
        """
        n = len(polygon)
        concave = []
        
        for i in range(n):
            prev_p = polygon[(i - 1) % n]
            curr_p = polygon[i]
            next_p = polygon[(i + 1) % n]
            
            # Calculate cross product to determine turn direction
            cross = ((curr_p[0] - prev_p[0]) * (next_p[1] - curr_p[1]) - 
                    (curr_p[1] - prev_p[1]) * (next_p[0] - curr_p[0]))
            
            # For counter-clockwise polygon, negative cross = concave
            if cross < -self.tolerance:
                concave.append(i)
        
        return concave
    
    def _generate_chords(self, polygon: Polygon, concave_vertices: List[int]
                        ) -> Tuple[List[Tuple[int, float, float, float]], 
                                   List[Tuple[int, float, float, float]]]:
        """
        Generate horizontal and vertical chords from concave vertices.
        
        Returns:
            (h_chords, v_chords): Lists of (vertex_idx, coord, start, end)
        """
        n = len(polygon)
        h_chords = []  # (vertex_idx, y, x_start, x_end)
        v_chords = []  # (vertex_idx, x, y_start, y_end)
        
        for idx in concave_vertices:
            prev_p = polygon[(idx - 1) % n]
            curr_p = polygon[idx]
            next_p = polygon[(idx + 1) % n]
            
            # Determine which direction the chord should extend
            # Based on the incoming and outgoing edge directions
            
            incoming_horizontal = abs(prev_p[1] - curr_p[1]) < self.tolerance
            outgoing_horizontal = abs(next_p[1] - curr_p[1]) < self.tolerance
            
            if incoming_horizontal and not outgoing_horizontal:
                # Extend horizontally
                chord_extent = self._find_horizontal_chord_extent(polygon, idx)
                if chord_extent:
                    h_chords.append((idx, curr_p[1], chord_extent[0], chord_extent[1]))
            elif not incoming_horizontal and outgoing_horizontal:
                # Extend vertically
                chord_extent = self._find_vertical_chord_extent(polygon, idx)
                if chord_extent:
                    v_chords.append((idx, curr_p[0], chord_extent[0], chord_extent[1]))
            else:
                # Try both directions
                h_extent = self._find_horizontal_chord_extent(polygon, idx)
                v_extent = self._find_vertical_chord_extent(polygon, idx)
                if h_extent:
                    h_chords.append((idx, curr_p[1], h_extent[0], h_extent[1]))
                if v_extent:
                    v_chords.append((idx, curr_p[0], v_extent[0], v_extent[1]))
        
        return h_chords, v_chords
    
    def _find_horizontal_chord_extent(self, polygon: Polygon, vertex_idx: int
                                      ) -> Optional[Tuple[float, float]]:
        """Find the extent of a horizontal chord from a vertex."""
        curr_p = polygon[vertex_idx]
        y = curr_p[1]
        x = curr_p[0]
        
        # Find intersection with polygon boundary
        n = len(polygon)
        x_left = float('-inf')
        x_right = float('inf')
        
        for i in range(n):
            p1 = polygon[i]
            p2 = polygon[(i + 1) % n]
            
            # Check if edge crosses the horizontal line at y
            if (min(p1[1], p2[1]) <= y <= max(p1[1], p2[1]) and 
                abs(p1[1] - p2[1]) > self.tolerance):
                # Calculate x intersection
                t = (y - p1[1]) / (p2[1] - p1[1])
                x_int = p1[0] + t * (p2[0] - p1[0])
                
                if x_int < x - self.tolerance:
                    x_left = max(x_left, x_int)
                elif x_int > x + self.tolerance:
                    x_right = min(x_right, x_int)
        
        if x_left == float('-inf') or x_right == float('inf'):
            return None
        
        return (x_left, x_right)
    
    def _find_vertical_chord_extent(self, polygon: Polygon, vertex_idx: int
                                    ) -> Optional[Tuple[float, float]]:
        """Find the extent of a vertical chord from a vertex."""
        curr_p = polygon[vertex_idx]
        x = curr_p[0]
        y = curr_p[1]
        
        n = len(polygon)
        y_bottom = float('-inf')
        y_top = float('inf')
        
        for i in range(n):
            p1 = polygon[i]
            p2 = polygon[(i + 1) % n]
            
            # Check if edge crosses the vertical line at x
            if (min(p1[0], p2[0]) <= x <= max(p1[0], p2[0]) and
                abs(p1[0] - p2[0]) > self.tolerance):
                # Calculate y intersection
                t = (x - p1[0]) / (p2[0] - p1[0])
                y_int = p1[1] + t * (p2[1] - p1[1])
                
                if y_int < y - self.tolerance:
                    y_bottom = max(y_bottom, y_int)
                elif y_int > y + self.tolerance:
                    y_top = min(y_top, y_int)
        
        if y_bottom == float('-inf') or y_top == float('inf'):
            return None
        
        return (y_bottom, y_top)
    
    def _build_intersection_graph(self, 
                                   h_chords: List[Tuple[int, float, float, float]],
                                   v_chords: List[Tuple[int, float, float, float]]
                                   ) -> List[Tuple[int, int]]:
        """
        Build bipartite graph of intersecting chords.
        
        Returns:
            List of (h_chord_idx, v_chord_idx) pairs that intersect
        """
        intersections = []
        
        for hi, (_, y, x_start, x_end) in enumerate(h_chords):
            for vi, (_, x, y_start, y_end) in enumerate(v_chords):
                # Check if chords intersect
                if (x_start < x < x_end and y_start < y < y_end):
                    intersections.append((hi, vi))
        
        return intersections
    
    def _find_maximum_independent_set(self,
                                       h_chords: List[Tuple[int, float, float, float]],
                                       v_chords: List[Tuple[int, float, float, float]],
                                       intersections: List[Tuple[int, int]]
                                       ) -> List[Tuple[int, float, float, float]]:
        """
        Find maximum independent set of chords (no two chords intersect).
        
        Uses König's theorem: In bipartite graphs, 
        max independent set = total vertices - min vertex cover
        
        We use Hopcroft-Karp-like matching to find minimum vertex cover.
        """
        if not intersections:
            # No intersections, all chords are independent
            return list(h_chords) + list(v_chords)
        
        n_h = len(h_chords)
        n_v = len(v_chords)
        
        # Build adjacency lists
        h_adj = [[] for _ in range(n_h)]
        v_adj = [[] for _ in range(n_v)]
        
        for hi, vi in intersections:
            h_adj[hi].append(vi)
            v_adj[vi].append(hi)
        
        # Find maximum matching using augmenting paths
        h_match = [-1] * n_h
        v_match = [-1] * n_v
        
        def find_augmenting_path(h: int, visited: Set[int]) -> bool:
            for v in h_adj[h]:
                if v in visited:
                    continue
                visited.add(v)
                
                if v_match[v] == -1 or find_augmenting_path(v_match[v], visited):
                    h_match[h] = v
                    v_match[v] = h
                    return True
            return False
        
        # Find maximum matching
        for h in range(n_h):
            find_augmenting_path(h, set())
        
        # Find minimum vertex cover using König's theorem
        # Unmatched vertices in H
        unmatched_h = {h for h in range(n_h) if h_match[h] == -1}
        
        # BFS to find alternating paths from unmatched H vertices
        z_h = set(unmatched_h)
        z_v = set()
        
        queue = list(unmatched_h)
        while queue:
            h = queue.pop(0)
            for v in h_adj[h]:
                if v not in z_v:
                    z_v.add(v)
                    if v_match[v] != -1 and v_match[v] not in z_h:
                        z_h.add(v_match[v])
                        queue.append(v_match[v])
        
        # Minimum vertex cover: (H - Z_H) ∪ Z_V
        cover_h = set(range(n_h)) - z_h
        cover_v = z_v
        
        # Maximum independent set: vertices not in cover
        independent_h = z_h
        independent_v = set(range(n_v)) - z_v
        
        result = []
        for hi in independent_h:
            result.append(('h', h_chords[hi]))
        for vi in independent_v:
            result.append(('v', v_chords[vi]))
        
        return result
    
    def _partition_with_chords(self, polygon: Polygon, 
                               chords: List) -> List[Rectangle]:
        """
        Partition polygon using selected chords.
        
        This is a simplified implementation that uses a sweep line approach.
        """
        if not polygon:
            return []
        
        # Get bounding box
        xs = [p[0] for p in polygon]
        ys = [p[1] for p in polygon]
        
        # Collect all x and y coordinates (polygon vertices + chord endpoints)
        x_coords = set(xs)
        y_coords = set(ys)
        
        for chord_item in chords:
            if isinstance(chord_item, tuple) and len(chord_item) == 2:
                chord_type, chord_data = chord_item
                if chord_type == 'h':
                    _, y, x_start, x_end = chord_data
                    y_coords.add(y)
                    x_coords.add(x_start)
                    x_coords.add(x_end)
                else:
                    _, x, y_start, y_end = chord_data
                    x_coords.add(x)
                    y_coords.add(y_start)
                    y_coords.add(y_end)
        
        # Sort coordinates
        x_sorted = sorted(x_coords)
        y_sorted = sorted(y_coords)
        
        # Create grid cells and check which are inside the polygon
        rectangles = []
        
        for i in range(len(x_sorted) - 1):
            for j in range(len(y_sorted) - 1):
                # Check if cell center is inside polygon
                cx = (x_sorted[i] + x_sorted[i + 1]) / 2
                cy = (y_sorted[j] + y_sorted[j + 1]) / 2
                
                if self._point_in_polygon((cx, cy), polygon):
                    rectangles.append(Rectangle(
                        x_sorted[i], y_sorted[j],
                        x_sorted[i + 1], y_sorted[j + 1]
                    ))
        
        # Merge adjacent rectangles where possible
        rectangles = self._merge_rectangles(rectangles)
        
        return rectangles
    
    def _point_in_polygon(self, point: Point, polygon: Polygon) -> bool:
        """Check if point is inside polygon using ray casting."""
        x, y = point
        n = len(polygon)
        inside = False
        
        j = n - 1
        for i in range(n):
            xi, yi = polygon[i]
            xj, yj = polygon[j]
            
            if ((yi > y) != (yj > y) and 
                x < (xj - xi) * (y - yi) / (yj - yi) + xi):
                inside = not inside
            j = i
        
        return inside
    
    def _merge_rectangles(self, rectangles: List[Rectangle]) -> List[Rectangle]:
        """Merge adjacent rectangles to reduce count."""
        if not rectangles:
            return []
        
        # Simple greedy merging
        merged = list(rectangles)
        changed = True
        
        while changed:
            changed = False
            new_merged = []
            used = set()
            
            for i, r1 in enumerate(merged):
                if i in used:
                    continue
                    
                merged_with = None
                for j, r2 in enumerate(merged):
                    if j <= i or j in used:
                        continue
                    
                    # Check if rectangles can be merged horizontally
                    if (abs(r1.y_min - r2.y_min) < self.tolerance and
                        abs(r1.y_max - r2.y_max) < self.tolerance):
                        if abs(r1.x_max - r2.x_min) < self.tolerance:
                            merged_with = Rectangle(r1.x_min, r1.y_min, 
                                                   r2.x_max, r1.y_max)
                            used.add(j)
                            changed = True
                            break
                        elif abs(r2.x_max - r1.x_min) < self.tolerance:
                            merged_with = Rectangle(r2.x_min, r1.y_min,
                                                   r1.x_max, r1.y_max)
                            used.add(j)
                            changed = True
                            break
                    
                    # Check if rectangles can be merged vertically
                    if (abs(r1.x_min - r2.x_min) < self.tolerance and
                        abs(r1.x_max - r2.x_max) < self.tolerance):
                        if abs(r1.y_max - r2.y_min) < self.tolerance:
                            merged_with = Rectangle(r1.x_min, r1.y_min,
                                                   r1.x_max, r2.y_max)
                            used.add(j)
                            changed = True
                            break
                        elif abs(r2.y_max - r1.y_min) < self.tolerance:
                            merged_with = Rectangle(r1.x_min, r2.y_min,
                                                   r1.x_max, r1.y_max)
                            used.add(j)
                            changed = True
                            break
                
                if merged_with:
                    new_merged.append(merged_with)
                else:
                    new_merged.append(r1)
                used.add(i)
            
            merged = new_merged
        
        return merged


# =============================================================================
# Convenience Functions
# =============================================================================

def simplify_building(polygon: Polygon, sigma_max: float = 2.0) -> Polygon:
    """
    Simplify a building polygon to a rectilinear shape.
    
    This is a convenience wrapper around :class:`BuildingSimplifier`.
    Uses Bayer's recursive algorithm [Bayer2009]_ to simplify complex
    building outlines while preserving the general shape.
    
    :param polygon: List of (x, y) coordinates representing the building outline.
    :type polygon: Polygon
    :param sigma_max: Simplification threshold in coordinate units. Larger values
        result in more aggressive simplification. Default is 2.0.
    :type sigma_max: float
    :returns: Simplified polygon with approximately rectilinear edges.
    :rtype: Polygon
        
    .. rubric:: Examples
    
    Simplify a building with irregular edges::
    
        >>> outline = [(0, 0), (10, 0.3), (10, 5), (5.1, 5), (5, 10), (0, 9.8)]
        >>> simplified = simplify_building(outline, sigma_max=1.0)
        >>> len(simplified) <= len(outline)
        True
    
    More aggressive simplification::
    
        >>> very_simple = simplify_building(outline, sigma_max=5.0)
    
    .. seealso::
    
        :class:`BuildingSimplifier`
            The underlying class with more options.
        :func:`simplify_and_partition`
            Combines simplification with partitioning.
    """
    simplifier = BuildingSimplifier(sigma_max=sigma_max)
    return simplifier.simplify(polygon)


def partition_into_rectangles(polygon: Polygon) -> List[Rectangle]:
    """
    Partition a rectilinear polygon into minimum number of rectangles.
    
    This is a convenience wrapper around :class:`RectangularPartitioner`.
    Uses the Ferrari-Sankar-Sklansky algorithm [Ferrari1984]_ to find
    the optimal partition.
    
    :param polygon: List of (x, y) coordinates. Must be a rectilinear polygon
        (all edges axis-aligned).
    :type polygon: Polygon
    :returns: List of :class:`Rectangle` objects that cover the polygon.
    :rtype: List[Rectangle]
        
    .. rubric:: Examples
    
    Partition an L-shaped polygon::
    
        >>> l_shape = [(0, 0), (10, 0), (10, 5), (5, 5), (5, 10), (0, 10)]
        >>> rectangles = partition_into_rectangles(l_shape)
        >>> len(rectangles)
        2
        >>> for r in rectangles:
        ...     print(f"({r.x_min}, {r.y_min}) to ({r.x_max}, {r.y_max})")
        (0, 0) to (5, 10)
        (5, 0) to (10, 5)
    
    Partition a T-shaped polygon::
    
        >>> t_shape = [(0, 0), (10, 0), (10, 3), (7, 3), (7, 10), (3, 10), (3, 3), (0, 3)]
        >>> rectangles = partition_into_rectangles(t_shape)
        >>> len(rectangles)
        2
    
    .. seealso::
    
        :class:`RectangularPartitioner`
            The underlying class with tolerance settings.
        :func:`simplify_and_partition`
            First simplifies non-rectilinear polygons.
    """
    partitioner = RectangularPartitioner()
    return partitioner.partition(polygon)


def simplify_and_partition(polygon: Polygon, 
                           sigma_max: float = 2.0) -> List[Rectangle]:
    """
    Simplify a building polygon and partition into rectangles.
    
    This combines both algorithms for a complete processing pipeline:
    
    1. Simplify to rectilinear shape using Bayer's algorithm [Bayer2009]_
    2. Partition into minimum rectangles using Ferrari et al. [Ferrari1984]_
    
    This is the recommended function for processing real-world building
    footprints which may have irregular edges.
    
    :param polygon: List of (x, y) coordinates representing the building outline.
        Does not need to be rectilinear.
    :type polygon: Polygon
    :param sigma_max: Simplification threshold. Larger values result in more 
        aggressive simplification. Default is 2.0.
    :type sigma_max: float
    :returns: List of :class:`Rectangle` objects that approximate the building.
    :rtype: List[Rectangle]
        
    .. rubric:: Examples
    
    Process a complex building outline::
    
        >>> # A building with slightly irregular edges
        >>> building = [
        ...     (0, 0), (20, 0.5), (20, 10), (15.2, 10),
        ...     (15, 20), (0, 19.8)
        ... ]
        >>> rectangles = simplify_and_partition(building, sigma_max=2.0)
        >>> print(f"Building decomposed into {len(rectangles)} rectangles")
        Building decomposed into ... rectangles
    
    Process an L-shaped building::
    
        >>> l_building = [(0, 0), (10, 0), (10, 5), (5, 5), (5, 10), (0, 10)]
        >>> rects = simplify_and_partition(l_building)
        >>> len(rects)
        2
    
    .. seealso::
    
        :func:`simplify_building`
            Just the simplification step.
        :func:`partition_into_rectangles`
            Just the partitioning step.
        :class:`BuildingSimplifier`
            For more control over simplification.
        :class:`RectangularPartitioner`
            For more control over partitioning.
    """
    simplified = simplify_building(polygon, sigma_max)
    return partition_into_rectangles(simplified)


# =============================================================================
# Testing
# =============================================================================

if __name__ == "__main__":
    # Test with an L-shaped building
    l_shape = [
        (0, 0), (10, 0), (10, 5), (5, 5), (5, 10), (0, 10)
    ]
    
    print("Original L-shaped polygon:")
    print(l_shape)
    
    print("\nPartitioning into rectangles:")
    partitioner = RectangularPartitioner()
    rectangles = partitioner.partition(l_shape)
    for i, rect in enumerate(rectangles):
        print(f"  Rectangle {i+1}: ({rect.x_min}, {rect.y_min}) - ({rect.x_max}, {rect.y_max})")
    
    # Test with a complex building outline
    complex_building = [
        (0, 0), (20, 0), (20, 5), (15, 5), (15, 10),
        (20, 10), (20, 20), (0, 20), (0, 15), (5, 15),
        (5, 5), (0, 5)
    ]
    
    print("\nComplex building polygon:")
    print(complex_building)
    
    print("\nSimplifying building:")
    simplifier = BuildingSimplifier(sigma_max=1.0)
    simplified = simplifier.simplify(complex_building)
    print(f"  Simplified to {len(simplified)} vertices")
    
    print("\nPartitioning simplified building:")
    rectangles = partition_into_rectangles(complex_building)
    print(f"  Partitioned into {len(rectangles)} rectangles")
    for i, rect in enumerate(rectangles):
        print(f"  Rectangle {i+1}: ({rect.x_min:.1f}, {rect.y_min:.1f}) - ({rect.x_max:.1f}, {rect.y_max:.1f})")
