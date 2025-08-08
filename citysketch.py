# !/usr/bin/env python3
"""
CityJSON Creator Application
A wxPython GUI application for creating and editing CityJSON files with building data.
"""

import wx
import wx.lib.scrolledpanel as scrolled
import json
import math
import sys
import numpy as np
from dataclasses import dataclass, field
from typing import List, Tuple, Optional, Set, Dict
from enum import Enum
import uuid
import urllib.request
import urllib.parse
import threading
import io
from collections import OrderedDict
import hashlib
import os
import tempfile

# Version info
APP_VERSION = "1.0.0"


class SelectionMode(Enum):
    NORMAL = "normal"
    ADD_BUILDING = "add_building"
    RECTANGLE_SELECT = "rectangle_select"


class MapProvider(Enum):
    NONE = "None"
    OSM = "OpenStreetMap"
    SATELLITE = "Satellite"
    TERRAIN = "Terrain"


class TileCache:
    """Simple tile cache for map tiles"""

    def __init__(self, cache_dir=None):
        if cache_dir is None:
            cache_dir = os.path.join(tempfile.gettempdir(),
                                     'cityjson_tiles')
        self.cache_dir = cache_dir
        os.makedirs(cache_dir, exist_ok=True)
        self.memory_cache = {}
        self.max_memory_tiles = 100

    def get_cache_path(self, provider, z, x, y):
        """Get the file path for a cached tile"""
        provider_dir = os.path.join(self.cache_dir, provider.value)
        os.makedirs(provider_dir, exist_ok=True)
        return os.path.join(provider_dir, f"{z}_{x}_{y}.png")

    def get_tile(self, provider, z, x, y):
        """Get a tile from cache"""
        key = (provider, z, x, y)

        # Check memory cache
        if key in self.memory_cache:
            return self.memory_cache[key]

        # Check disk cache
        cache_path = self.get_cache_path(provider, z, x, y)
        if os.path.exists(cache_path):
            try:
                with open(cache_path, 'rb') as f:
                    data = f.read()
                image = wx.Image(io.BytesIO(data))

                # Add to memory cache
                if len(self.memory_cache) >= self.max_memory_tiles:
                    # Remove oldest items
                    for _ in range(20):
                        self.memory_cache.pop(
                            next(iter(self.memory_cache)))
                self.memory_cache[key] = image

                return image
            except:
                pass

        return None

    def save_tile(self, provider, z, x, y, data):
        """Save a tile to cache"""
        cache_path = self.get_cache_path(provider, z, x, y)
        try:
            with open(cache_path, 'wb') as f:
                f.write(data)

            # Also add to memory cache
            image = wx.Image(io.BytesIO(data))
            key = (provider, z, x, y)
            if len(self.memory_cache) >= self.max_memory_tiles:
                for _ in range(20):
                    self.memory_cache.pop(next(iter(self.memory_cache)))
            self.memory_cache[key] = image

            return image
        except:
            return None


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
            [[2, 6, 7, 3]],  # back
            [[0, 3, 7, 4]],  # left
            [[1, 5, 6, 2]],  # right
        ]

        return vertices, boundaries


class MapCanvas(wx.Panel):
    """The main canvas for displaying and editing buildings"""

    def __init__(self, parent):
        super().__init__(parent)
        self.parent = parent

        # State
        self.buildings: List[Building] = []
        self.mode = SelectionMode.NORMAL
        self.snap_enabled = True
        self.zoom_level = 1.0
        self.pan_x = 0
        self.pan_y = 0
        self.storey_height = 3.3  # meters per storey

        # Map state
        self.map_provider = MapProvider.NONE
        self.map_enabled = True
        self.tile_cache = TileCache()
        self.tiles_loading = set()
        self.map_tiles = {}  # (z,x,y): wx.Image

        # Geographic coordinates (center of view)
        self.geo_center_lat = 49.4875  # Default: Ludwigshafen area
        self.geo_center_lon = 8.4660
        self.geo_zoom = 16  # Tile zoom level

        # Interaction state
        self.mouse_down = False
        self.drag_start = None
        self.drag_building = None
        self.drag_corner = None
        self.drag_corner_index = None
        self.first_corner = None
        self.selection_rect_start = None
        self.current_mouse_pos = None

        # Setup
        self.SetBackgroundStyle(wx.BG_STYLE_PAINT)
        self.Bind(wx.EVT_PAINT, self.on_paint)
        self.Bind(wx.EVT_LEFT_DOWN, self.on_mouse_down)
        self.Bind(wx.EVT_LEFT_UP, self.on_mouse_up)
        self.Bind(wx.EVT_MOTION, self.on_mouse_motion)
        self.Bind(wx.EVT_MOUSEWHEEL, self.on_mouse_wheel)
        self.Bind(wx.EVT_SIZE, self.on_size)

        self.SetMinSize((800, 600))

    def lat_lon_to_tile(self, lat, lon, zoom):
        """Convert lat/lon to tile coordinates"""
        lat_rad = math.radians(lat)
        n = 2.0 ** zoom
        x = (lon + 180.0) / 360.0 * n
        y = (1.0 - math.asinh(math.tan(lat_rad)) / math.pi) / 2.0 * n
        return x, y

    def tile_to_lat_lon(self, x, y, zoom):
        """Convert tile coordinates to lat/lon"""
        n = 2.0 ** zoom
        lon = x / n * 360.0 - 180.0
        lat_rad = math.atan(math.sinh(math.pi * (1 - 2 * y / n)))
        lat = math.degrees(lat_rad)
        return lat, lon

    def get_tile_url(self, provider, z, x, y):
        """Get the URL for a tile"""
        if provider == MapProvider.OSM:
            # Use OSM tile server
            servers = ['a', 'b', 'c']
            server = servers[abs(hash((x, y))) % len(servers)]
            return f"https://{server}.tile.openstreetmap.org/{z}/{x}/{y}.png"
        elif provider == MapProvider.SATELLITE:
            # Use ESRI World Imagery
            return f"https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{z}/{y}/{x}"
        elif provider == MapProvider.TERRAIN:
            # Use OpenTopoMap
            servers = ['a', 'b', 'c']
            server = servers[abs(hash((x, y))) % len(servers)]
            return f"https://{server}.tile.opentopomap.org/{z}/{x}/{y}.png"
        return None

    def load_tile_async(self, provider, z, x, y):
        """Load a tile asynchronously"""

        def load():
            try:
                # Check cache first
                image = self.tile_cache.get_tile(provider, z, x, y)
                if image:
                    wx.CallAfter(self.on_tile_loaded, provider, z, x, y,
                                 image)
                    return

                # Download tile
                url = self.get_tile_url(provider, z, x, y)
                if url:
                    req = urllib.request.Request(url, headers={
                        'User-Agent': 'CityJSON Creator/1.0'
                    })
                    with urllib.request.urlopen(req,
                                                timeout=5) as response:
                        data = response.read()

                    # Save to cache and convert to image
                    image = self.tile_cache.save_tile(provider, z, x, y,
                                                      data)
                    if image:
                        wx.CallAfter(self.on_tile_loaded, provider, z, x,
                                     y, image)
            except Exception as e:
                print(f"Failed to load tile {z}/{x}/{y}: {e}")
            finally:
                wx.CallAfter(self.on_tile_load_complete, z, x, y)

        thread = threading.Thread(target=load)
        thread.daemon = True
        thread.start()

    def on_tile_loaded(self, provider, z, x, y, image):
        """Called when a tile has been loaded"""
        if provider == self.map_provider:
            self.map_tiles[(z, x, y)] = image
            self.Refresh()

    def on_tile_load_complete(self, z, x, y):
        """Called when tile loading is complete"""
        self.tiles_loading.discard((z, x, y))

    def update_geo_center(self):
        """Update geographic center based on pan"""
        width, height = self.GetSize()
        center_x = width / 2
        center_y = height / 2

        # Calculate tile offset
        tile_x, tile_y = self.lat_lon_to_tile(self.geo_center_lat,
                                              self.geo_center_lon,
                                              self.geo_zoom)

        # Apply pan offset in tile coordinates
        tile_offset_x = -self.pan_x / 256.0
        tile_offset_y = -self.pan_y / 256.0

        new_tile_x = tile_x + tile_offset_x
        new_tile_y = tile_y + tile_offset_y

        # Convert back to lat/lon
        self.geo_center_lat, self.geo_center_lon = self.tile_to_lat_lon(
            new_tile_x, new_tile_y, self.geo_zoom)
        self.pan_x = 0
        self.pan_y = 0

    def screen_to_world(self, x: float, y: float) -> Tuple[float, float]:
        """Convert screen coordinates to world coordinates"""
        wx = (x - self.pan_x) / self.zoom_level
        wy = (y - self.pan_y) / self.zoom_level
        return wx, wy

    def world_to_screen(self, x: float, y: float) -> Tuple[float, float]:
        """Convert world coordinates to screen coordinates"""
        sx = x * self.zoom_level + self.pan_x
        sy = y * self.zoom_level + self.pan_y
        return sx, sy

    def snap_point(self, x: float, y: float,
                   exclude_building: Optional[Building] = None) -> Tuple[
        float, float]:
        """Snap a point to nearby building features"""
        if not self.snap_enabled:
            return x, y

        snap_threshold = 15 / self.zoom_level
        best_x, best_y = x, y
        best_dist = snap_threshold

        for building in self.buildings:
            if building == exclude_building:
                continue

            # Snap to corners
            for cx, cy in building.get_corners():
                dist = math.sqrt((x - cx) ** 2 + (y - cy) ** 2)
                if dist < best_dist:
                    best_x, best_y = cx, cy
                    best_dist = dist

            # Snap to edges
            if abs(x - building.x1) < best_dist:
                best_x = building.x1
                best_dist = abs(x - building.x1)
            if abs(x - building.x2) < best_dist:
                best_x = building.x2
                best_dist = abs(x - building.x2)
            if abs(y - building.y1) < best_dist:
                best_y = building.y1
                best_dist = abs(y - building.y1)
            if abs(y - building.y2) < best_dist:
                best_y = building.y2
                best_dist = abs(y - building.y2)

        return best_x, best_y

    def on_paint(self, event):
        """Handle paint events"""
        dc = wx.AutoBufferedPaintDC(self)
        dc.Clear()

        # Set up coordinate system
        gc = wx.GraphicsContext.Create(dc)

        # Draw map tiles if enabled
        if self.map_provider != MapProvider.NONE and self.map_enabled:
            self.draw_map_tiles(gc)

        # Draw grid
        self.draw_grid(gc)

        # Draw buildings
        for building in self.buildings:
            self.draw_building(gc, building)

        # Draw preview for new building
        if self.mode == SelectionMode.ADD_BUILDING and self.first_corner and self.current_mouse_pos:
            self.draw_building_preview(gc)

        # Draw selection rectangle
        if self.mode == SelectionMode.RECTANGLE_SELECT and self.selection_rect_start and self.current_mouse_pos:
            self.draw_selection_rectangle(gc)

    def draw_map_tiles(self, gc):
        """Draw map tiles as background"""
        width, height = self.GetSize()

        # Calculate which tiles we need
        tile_size = 256

        # Get center tile
        center_tile_x, center_tile_y = self.lat_lon_to_tile(
            self.geo_center_lat, self.geo_center_lon, self.geo_zoom
        )

        # Calculate visible tile range
        tiles_x = math.ceil(width / tile_size) + 2
        tiles_y = math.ceil(height / tile_size) + 2

        # Calculate offset for smooth panning
        frac_x = center_tile_x - math.floor(center_tile_x)
        frac_y = center_tile_y - math.floor(center_tile_y)
        offset_x = -frac_x * tile_size + width / 2 + self.pan_x
        offset_y = -frac_y * tile_size + height / 2 + self.pan_y

        # Draw tiles
        start_tile_x = int(center_tile_x) - tiles_x // 2
        start_tile_y = int(center_tile_y) - tiles_y // 2

        for dy in range(tiles_y):
            for dx in range(tiles_x):
                tile_x = start_tile_x + dx
                tile_y = start_tile_y + dy

                # Skip invalid tiles
                max_tile = 2 ** self.geo_zoom
                if tile_x < 0 or tile_x >= max_tile or tile_y < 0 or tile_y >= max_tile:
                    continue

                # Calculate screen position
                screen_x = offset_x + (dx - tiles_x // 2) * tile_size
                screen_y = offset_y + (dy - tiles_y // 2) * tile_size

                # Get or load tile
                tile_key = (self.geo_zoom, tile_x, tile_y)
                if tile_key in self.map_tiles:
                    # Draw tile
                    image = self.map_tiles[tile_key]
                    bitmap = wx.Bitmap(image)
                    gc.DrawBitmap(bitmap, screen_x, screen_y, tile_size,
                                  tile_size)
                else:
                    # Draw placeholder and load tile
                    gc.SetBrush(wx.Brush(wx.Colour(240, 240, 240)))
                    gc.SetPen(wx.Pen(wx.Colour(200, 200, 200), 1))
                    gc.DrawRectangle(screen_x, screen_y, tile_size,
                                     tile_size)

                    # Load tile if not already loading
                    if tile_key not in self.tiles_loading:
                        self.tiles_loading.add(tile_key)
                        self.load_tile_async(self.map_provider,
                                             self.geo_zoom, tile_x, tile_y)

    def draw_grid(self, gc):
        """Draw background grid"""
        # Only draw grid if no map or with transparency
        if self.map_provider == MapProvider.NONE:
            gc.SetPen(wx.Pen(wx.Colour(220, 220, 220), 1))
        else:
            gc.SetPen(wx.Pen(wx.Colour(100, 100, 100, 50), 1))

        width, height = self.GetSize()
        grid_size = 50 * self.zoom_level

        # Vertical lines
        x = self.pan_x % grid_size
        while x < width:
            gc.StrokeLine(x, 0, x, height)
            x += grid_size

        # Horizontal lines
        y = self.pan_y % grid_size
        while y < height:
            gc.StrokeLine(0, y, width, y)
            y += grid_size

    def draw_building(self, gc, building: Building):
        """Draw a single building"""
        x1, y1 = self.world_to_screen(building.x1, building.y1)
        x2, y2 = self.world_to_screen(building.x2, building.y2)

        # Set colors based on selection
        if building.selected:
            fill_color = wx.Colour(150, 180, 255, 180)
            border_color = wx.Colour(0, 0, 255)
        else:
            fill_color = wx.Colour(200, 200, 200, 180)
            border_color = wx.Colour(100, 100, 100)

        gc.SetBrush(wx.Brush(fill_color))
        gc.SetPen(wx.Pen(border_color, 2))

        # Draw rectangle
        gc.DrawRectangle(x1, y1, x2 - x1, y2 - y1)

        # Draw height text
        gc.SetFont(wx.Font(10, wx.FONTFAMILY_DEFAULT, wx.FONTSTYLE_NORMAL,
                           wx.FONTWEIGHT_NORMAL))
        text = f"{building.stories}F"
        tw, th = gc.GetTextExtent(text)
        gc.DrawText(text, (x1 + x2) / 2 - tw / 2, (y1 + y2) / 2 - th / 2)

        # Draw corner handles if selected
        if building.selected:
            gc.SetBrush(wx.Brush(wx.Colour(255, 255, 255)))
            gc.SetPen(wx.Pen(wx.Colour(0, 0, 255), 2))
            for cx, cy in building.get_corners():
                sx, sy = self.world_to_screen(cx, cy)
                gc.DrawEllipse(sx - 4, sy - 4, 8, 8)

    def draw_building_preview(self, gc):
        """Draw preview of building being created"""
        x1, y1 = self.first_corner
        x2, y2 = self.screen_to_world(*self.current_mouse_pos)
        x2, y2 = self.snap_point(x2, y2)

        sx1, sy1 = self.world_to_screen(x1, y1)
        sx2, sy2 = self.world_to_screen(x2, y2)

        gc.SetBrush(wx.Brush(wx.Colour(100, 255, 100, 100)))
        gc.SetPen(wx.Pen(wx.Colour(0, 200, 0), 2, wx.PENSTYLE_DOT))

        gc.DrawRectangle(min(sx1, sx2), min(sy1, sy2),
                         abs(sx2 - sx1), abs(sy2 - sy1))

    def draw_selection_rectangle(self, gc):
        """Draw selection rectangle"""
        x1, y1 = self.selection_rect_start
        x2, y2 = self.current_mouse_pos

        gc.SetBrush(wx.Brush(wx.Colour(0, 0, 255, 30)))
        gc.SetPen(wx.Pen(wx.Colour(0, 0, 255), 1, wx.PENSTYLE_DOT))

        gc.DrawRectangle(min(x1, x2), min(y1, y2),
                         abs(x2 - x1), abs(y2 - y1))

    def on_mouse_down(self, event):
        """Handle mouse down events"""
        self.mouse_down = True
        self.drag_start = event.GetPosition()
        wx, wy = self.screen_to_world(event.GetX(), event.GetY())

        if self.mode == SelectionMode.ADD_BUILDING:
            if self.first_corner is None:
                self.first_corner = self.snap_point(wx, wy)
            else:
                # Create building
                x2, y2 = self.snap_point(wx, wy)
                building = Building(
                    id=str(uuid.uuid4()),
                    x1=self.first_corner[0],
                    y1=self.first_corner[1],
                    x2=x2,
                    y2=y2,
                    height=self.storey_height * 3,
                    stories=3
                )
                self.buildings.append(building)
                self.first_corner = None
                self.mode = SelectionMode.NORMAL
                self.Refresh()

        elif self.mode == SelectionMode.NORMAL:
            if event.ShiftDown():
                # Start rectangle selection
                self.mode = SelectionMode.RECTANGLE_SELECT
                self.selection_rect_start = event.GetPosition()
            else:
                # Check for corner drag
                for building in self.buildings:
                    if building.selected:
                        corner_idx = building.get_corner_index(wx, wy,
                                                               10 / self.zoom_level)
                        if corner_idx is not None:
                            self.drag_corner = building
                            self.drag_corner_index = corner_idx
                            return

                # Check for building click
                clicked_building = None
                for building in reversed(self.buildings):
                    if building.contains_point(wx, wy):
                        clicked_building = building
                        break

                if clicked_building:
                    if not event.ControlDown():
                        # Clear selection unless Ctrl is held
                        for b in self.buildings:
                            b.selected = False
                    clicked_building.selected = not clicked_building.selected if event.ControlDown() else True
                    self.drag_building = clicked_building
                else:
                    # Click on empty space - clear selection
                    if not event.ControlDown():
                        for b in self.buildings:
                            b.selected = False

                self.Refresh()

    def on_mouse_up(self, event):
        """Handle mouse up events"""
        self.mouse_down = False

        if self.mode == SelectionMode.RECTANGLE_SELECT:
            # Select buildings in rectangle
            x1, y1 = self.screen_to_world(*self.selection_rect_start)
            x2, y2 = self.screen_to_world(event.GetX(), event.GetY())

            rx1, rx2 = min(x1, x2), max(x1, x2)
            ry1, ry2 = min(y1, y2), max(y1, y2)

            for building in self.buildings:
                if (building.x1 >= rx1 and building.x2 <= rx2 and
                        building.y1 >= ry1 and building.y2 <= ry2):
                    building.selected = True

            self.mode = SelectionMode.NORMAL
            self.selection_rect_start = None
            self.Refresh()

        self.drag_building = None
        self.drag_corner = None
        self.drag_corner_index = None
        self.drag_start = None

    def on_mouse_motion(self, event):
        """Handle mouse motion events"""
        self.current_mouse_pos = event.GetPosition()
        wx, wy = self.screen_to_world(event.GetX(), event.GetY())

        if self.mouse_down and self.drag_start:
            if self.drag_corner and self.drag_corner_index is not None:
                # Dragging a corner
                snapped_x, snapped_y = self.snap_point(wx, wy,
                                                       self.drag_corner)
                self.drag_corner.move_corner(self.drag_corner_index,
                                             snapped_x, snapped_y)
                self.Refresh()
            elif self.drag_building:
                # Dragging a building
                start_wx, start_wy = self.screen_to_world(*self.drag_start)
                dx = wx - start_wx
                dy = wy - start_wy

                # Apply snapping to the drag
                new_x1 = self.drag_building.x1 + dx
                new_y1 = self.drag_building.y1 + dy
                snapped_x, snapped_y = self.snap_point(new_x1, new_y1,
                                                       self.drag_building)

                actual_dx = snapped_x - self.drag_building.x1
                actual_dy = snapped_y - self.drag_building.y1

                self.drag_building.translate(actual_dx, actual_dy)
                self.drag_start = event.GetPosition()
                self.Refresh()
            elif event.MiddleIsDown() or (
                    event.RightIsDown() and not self.mode == SelectionMode.ADD_BUILDING):
                # Panning
                dx = event.GetX() - self.drag_start[0]
                dy = event.GetY() - self.drag_start[1]
                self.pan_x += dx
                self.pan_y += dy
                self.drag_start = event.GetPosition()
                self.Refresh()

        if self.mode == SelectionMode.ADD_BUILDING and self.first_corner:
            self.Refresh()

        if self.mode == SelectionMode.RECTANGLE_SELECT:
            self.Refresh()

    def on_mouse_wheel(self, event):
        """Handle mouse wheel events for zooming"""
        rotation = event.GetWheelRotation()
        mx, my = event.GetPosition()

        # Calculate zoom
        zoom_factor = 1.1 if rotation > 0 else 0.9
        new_zoom = self.zoom_level * zoom_factor
        new_zoom = max(0.1, min(10.0, new_zoom))

        # Adjust pan to zoom around mouse position
        wx, wy = self.screen_to_world(mx, my)
        self.zoom_level = new_zoom
        new_mx, new_my = self.world_to_screen(wx, wy)

        self.pan_x += mx - new_mx
        self.pan_y += my - new_my

        # Update map zoom level if needed
        if self.map_provider != MapProvider.NONE:
            # Adjust geo zoom based on canvas zoom
            if self.zoom_level > 2.0 and self.geo_zoom < 18:
                self.geo_zoom += 1
                self.map_tiles.clear()
                self.zoom_level /= 2
            elif self.zoom_level < 0.5 and self.geo_zoom > 10:
                self.geo_zoom -= 1
                self.map_tiles.clear()
                self.zoom_level *= 2

        self.Refresh()

    def on_size(self, event):
        """Handle resize events"""
        self.Refresh()
        event.Skip()

    def set_building_stories(self, stories: int):
        """Set stories for selected buildings"""
        for building in self.buildings:
            if building.selected:
                building.stories = stories
                building.height = stories * self.storey_height
        self.Refresh()

    def delete_selected_buildings(self):
        """Delete selected buildings"""
        self.buildings = [b for b in self.buildings if not b.selected]
        self.Refresh()

    def zoom_to_buildings(self):
        """Zoom to fit all buildings"""
        if not self.buildings:
            return

        # Find bounding box
        min_x = min(b.x1 for b in self.buildings)
        max_x = max(b.x2 for b in self.buildings)
        min_y = min(b.y1 for b in self.buildings)
        max_y = max(b.y2 for b in self.buildings)

        # Calculate zoom and pan
        width, height = self.GetSize()
        margin = 50

        zoom_x = (width - 2 * margin) / (
                    max_x - min_x) if max_x > min_x else 1.0
        zoom_y = (height - 2 * margin) / (
                    max_y - min_y) if max_y > min_y else 1.0

        self.zoom_level = min(zoom_x, zoom_y, 5.0)

        # Center the view
        center_x = (min_x + max_x) / 2
        center_y = (min_y + max_y) / 2

        self.pan_x = width / 2 - center_x * self.zoom_level
        self.pan_y = height / 2 - center_y * self.zoom_level

        self.Refresh()


class BasemapDialog(wx.Dialog):
    """Dialog for selecting and configuring basemap"""

    def __init__(self, parent, current_provider, map_enabled, lat, lon):
        super().__init__(parent, title="Select Basemap", size=(450, 420))

        self.provider = current_provider
        self.enabled = map_enabled
        self.lat = lat
        self.lon = lon

        panel = wx.Panel(self)
        sizer = wx.BoxSizer(wx.VERTICAL)

        # Map enabled checkbox
        self.enable_cb = wx.CheckBox(panel, label="Enable Basemap")
        self.enable_cb.SetValue(self.enabled)
        self.enable_cb.Bind(wx.EVT_CHECKBOX, self.on_enable_changed)
        sizer.Add(self.enable_cb, 0, wx.ALL, 10)

        # Map provider selection
        provider_box = wx.StaticBox(panel, label="Map Provider")
        provider_sizer = wx.StaticBoxSizer(provider_box, wx.VERTICAL)

        self.provider_radios = []
        for provider in MapProvider:
            if provider != MapProvider.NONE:
                radio = wx.RadioButton(panel, label=provider.value,
                                       style=wx.RB_SINGLE if provider == MapProvider.OSM else 0)
                radio.SetValue(provider == self.provider)
                radio.Bind(wx.EVT_RADIOBUTTON,
                           lambda e, p=provider: self.on_provider_changed(
                               p))
                provider_sizer.Add(radio, 0, wx.ALL, 5)
                self.provider_radios.append(radio)

        sizer.Add(provider_sizer, 0, wx.EXPAND | wx.LEFT | wx.RIGHT, 10)

        # Location settings
        location_box = wx.StaticBox(panel, label="Map Center Location")
        location_sizer = wx.StaticBoxSizer(location_box, wx.VERTICAL)

        # Latitude
        lat_box = wx.BoxSizer(wx.HORIZONTAL)
        lat_label = wx.StaticText(panel, label="Latitude:", size=(80, -1))
        lat_box.Add(lat_label, 0, wx.ALIGN_CENTER_VERTICAL | wx.RIGHT, 5)
        self.lat_ctrl = wx.TextCtrl(panel, value=f"{self.lat:.6f}")
        lat_box.Add(self.lat_ctrl, 1, wx.EXPAND)
        location_sizer.Add(lat_box, 0, wx.EXPAND | wx.ALL, 5)

        # Longitude
        lon_box = wx.BoxSizer(wx.HORIZONTAL)
        lon_label = wx.StaticText(panel, label="Longitude:", size=(80, -1))
        lon_box.Add(lon_label, 0, wx.ALIGN_CENTER_VERTICAL | wx.RIGHT, 5)
        self.lon_ctrl = wx.TextCtrl(panel, value=f"{self.lon:.6f}")
        lon_box.Add(self.lon_ctrl, 1, wx.EXPAND)
        location_sizer.Add(lon_box, 0, wx.EXPAND | wx.ALL, 5)

        # Quick location buttons - arranged in 2x2 grid
        quick_label = wx.StaticText(panel, label="Quick Locations:")
        location_sizer.Add(quick_label, 0, wx.LEFT | wx.TOP, 5)

        quick_grid = wx.GridSizer(2, 2, 5, 5)

        locations = [
            ("New York", 40.7128, -74.0060),
            ("London", 51.5074, -0.1278),
            ("Tokyo", 35.6762, 139.6503),
            ("Berlin", 52.5200, 13.4050),
        ]

        for name, lat, lon in locations:
            btn = wx.Button(panel, label=name, size=(90, 28))
            btn.Bind(wx.EVT_BUTTON,
                     lambda e, la=lat, lo=lon: self.set_location(la, lo))
            quick_grid.Add(btn, 0, wx.EXPAND)

        location_sizer.Add(quick_grid, 0, wx.ALL | wx.EXPAND, 5)
        sizer.Add(location_sizer, 0,
                  wx.EXPAND | wx.LEFT | wx.RIGHT | wx.BOTTOM, 10)

        # Add some spacing
        sizer.Add((-1, 10))

        # Update radio button states based on enable checkbox
        self.update_radio_states()

        # Buttons
        btn_sizer = wx.StdDialogButtonSizer()
        ok_btn = wx.Button(panel, wx.ID_OK)
        cancel_btn = wx.Button(panel, wx.ID_CANCEL)
        btn_sizer.AddButton(ok_btn)
        btn_sizer.AddButton(cancel_btn)
        btn_sizer.Realize()
        sizer.Add(btn_sizer, 0, wx.EXPAND | wx.ALL, 10)

        panel.SetSizer(sizer)

        # Center the dialog
        self.Centre()

    def on_enable_changed(self, event):
        """Handle enable checkbox change"""
        self.enabled = self.enable_cb.GetValue()
        self.update_radio_states()

    def update_radio_states(self):
        """Enable/disable radio buttons based on checkbox"""
        for radio in self.provider_radios:
            radio.Enable(self.enabled)

    def on_provider_changed(self, provider):
        """Handle provider selection change"""
        self.provider = provider

    def set_location(self, lat, lon):
        """Set location in text controls"""
        self.lat_ctrl.SetValue(f"{lat:.6f}")
        self.lon_ctrl.SetValue(f"{lon:.6f}")

    def get_values(self):
        """Get the current values"""
        try:
            lat = float(self.lat_ctrl.GetValue())
            lon = float(self.lon_ctrl.GetValue())
        except ValueError:
            lat = self.lat
            lon = self.lon

        return self.provider if self.enabled else MapProvider.NONE, self.enabled, lat, lon

class HeightDialog(wx.Dialog):
    """Dialog for setting building height"""

    def __init__(self, parent, stories=3, height=10.0, storey_height=3.3):
        super().__init__(parent, title="Set Building Height",
                         size=(300, 200))

        self.storey_height = storey_height

        panel = wx.Panel(self)
        sizer = wx.BoxSizer(wx.VERTICAL)

        # Stories control
        stories_box = wx.BoxSizer(wx.HORIZONTAL)
        stories_box.Add(wx.StaticText(panel, label="Stories:"), 0,
                        wx.ALIGN_CENTER_VERTICAL | wx.RIGHT, 5)
        self.stories_ctrl = wx.SpinCtrl(panel, value=str(stories), min=1,
                                        max=100)
        stories_box.Add(self.stories_ctrl, 1, wx.EXPAND)
        sizer.Add(stories_box, 0, wx.EXPAND | wx.ALL, 10)

        # Height control
        height_box = wx.BoxSizer(wx.HORIZONTAL)
        height_box.Add(wx.StaticText(panel, label="Height (m):"), 0,
                       wx.ALIGN_CENTER_VERTICAL | wx.RIGHT, 5)
        self.height_ctrl = wx.TextCtrl(panel, value=f"{height:.1f}")
        height_box.Add(self.height_ctrl, 1, wx.EXPAND)
        sizer.Add(height_box, 0, wx.EXPAND | wx.ALL, 10)

        # Buttons
        btn_sizer = wx.StdDialogButtonSizer()
        ok_btn = wx.Button(panel, wx.ID_OK)
        cancel_btn = wx.Button(panel, wx.ID_CANCEL)
        btn_sizer.AddButton(ok_btn)
        btn_sizer.AddButton(cancel_btn)
        btn_sizer.Realize()
        sizer.Add(btn_sizer, 0, wx.EXPAND | wx.ALL, 10)

        panel.SetSizer(sizer)

        # Bind events
        self.stories_ctrl.Bind(wx.EVT_SPINCTRL, self.on_stories_changed)
        self.height_ctrl.Bind(wx.EVT_TEXT, self.on_height_changed)

    def on_stories_changed(self, event):
        """Update height when stories change"""
        stories = self.stories_ctrl.GetValue()
        height = stories * self.storey_height
        self.height_ctrl.SetValue(f"{height:.1f}")
        self.height_ctrl.SetBackgroundColour(
            wx.SystemSettings.GetColour(wx.SYS_COLOUR_WINDOW))

    def on_height_changed(self, event):
        """Update stories when height changes and validate"""
        try:
            height = float(self.height_ctrl.GetValue())
            if height < 0:
                self.height_ctrl.SetBackgroundColour(
                    wx.Colour(255, 200, 200))
            else:
                self.height_ctrl.SetBackgroundColour(
                    wx.SystemSettings.GetColour(wx.SYS_COLOUR_WINDOW))
                stories = max(1, round(height / self.storey_height))
                self.stories_ctrl.SetValue(stories)
        except ValueError:
            self.height_ctrl.SetBackgroundColour(wx.Colour(255, 200, 200))

    def get_values(self):
        """Get the current values"""
        return self.stories_ctrl.GetValue(), float(
            self.height_ctrl.GetValue())


class MainFrame(wx.Frame):
    """Main application frame"""

    def __init__(self):
        super().__init__(None, title="CityJSON Creator", size=(1200, 800))

        self.current_file = None
        self.modified = False

        # Create UI
        self.create_menu_bar()
        self.create_toolbar()
        self.create_main_panel()

        # Bind keyboard events
        self.Bind(wx.EVT_CHAR_HOOK, self.on_key_press)

        self.Centre()
        self.Show()

    def create_menu_bar(self):
        """Create the menu bar"""
        menubar = wx.MenuBar()

        # File menu
        file_menu = wx.Menu()
        file_menu.Append(wx.ID_NEW, "&New\tCtrl+N", "Create a new project")
        file_menu.Append(wx.ID_OPEN, "&Open\tCtrl+O",
                         "Open a CityJSON file")
        file_menu.Append(wx.ID_SAVE, "&Save\tCtrl+S",
                         "Save the current project")
        file_menu.Append(wx.ID_SAVEAS, "Save &As...\tCtrl+Shift+S",
                         "Save with a new name")
        file_menu.AppendSeparator()
        file_menu.Append(wx.ID_EXIT, "E&xit\tCtrl+Q",
                         "Exit the application")

        # Edit menu
        edit_menu = wx.Menu()
        basemap_item = edit_menu.Append(wx.ID_ANY, "Select &Basemap",
                                        "Choose a basemap")
        zoom_item = edit_menu.Append(wx.ID_ANY,
                                     "&Zoom to Buildings\tCtrl+0",
                                     "Zoom to fit all buildings")
        storey_item = edit_menu.Append(wx.ID_ANY, "Set Storey &Height",
                                       "Set the height per storey")

        # Help menu
        help_menu = wx.Menu()
        help_menu.Append(wx.ID_ABOUT, "&About", "About this application")

        menubar.Append(file_menu, "&File")
        menubar.Append(edit_menu, "&Edit")
        menubar.Append(help_menu, "&Help")

        self.SetMenuBar(menubar)

        # Bind menu events
        self.Bind(wx.EVT_MENU, self.on_new, id=wx.ID_NEW)
        self.Bind(wx.EVT_MENU, self.on_open, id=wx.ID_OPEN)
        self.Bind(wx.EVT_MENU, self.on_save, id=wx.ID_SAVE)
        self.Bind(wx.EVT_MENU, self.on_save_as, id=wx.ID_SAVEAS)
        self.Bind(wx.EVT_MENU, self.on_exit, id=wx.ID_EXIT)
        self.Bind(wx.EVT_MENU, self.on_about, id=wx.ID_ABOUT)

        # Bind edit menu events
        self.Bind(wx.EVT_MENU, self.on_select_basemap,
                  id=basemap_item.GetId())
        self.Bind(wx.EVT_MENU, self.on_zoom_to_buildings,
                  id=zoom_item.GetId())
        self.Bind(wx.EVT_MENU, self.on_set_storey_height,
                  id=storey_item.GetId())

    def create_toolbar(self):
        """Create the toolbar"""
        toolbar = self.CreateToolBar(wx.TB_HORIZONTAL | wx.TB_FLAT)

        # Add Building button
        self.add_building_btn = wx.Button(toolbar, label="Add Building")
        self.add_building_btn.Bind(wx.EVT_BUTTON, self.on_add_building)
        toolbar.AddControl(self.add_building_btn)

        toolbar.AddSeparator()

        # Snap toggle
        self.snap_btn = wx.ToggleButton(toolbar, label="Snap: ON")
        self.snap_btn.SetValue(True)
        self.snap_btn.Bind(wx.EVT_TOGGLEBUTTON, self.on_toggle_snap)
        toolbar.AddControl(self.snap_btn)

        toolbar.AddSeparator()

        # Set Height button
        height_btn = wx.Button(toolbar, label="Set Height")
        height_btn.Bind(wx.EVT_BUTTON, self.on_set_height)
        toolbar.AddControl(height_btn)

        # Delete button
        delete_btn = wx.Button(toolbar, label="Delete")
        delete_btn.Bind(wx.EVT_BUTTON, self.on_delete)
        toolbar.AddControl(delete_btn)

        toolbar.AddSeparator()

        # Zoom controls
        zoom_in_btn = wx.Button(toolbar, label="Zoom In")
        zoom_in_btn.Bind(wx.EVT_BUTTON, self.on_zoom_in)
        toolbar.AddControl(zoom_in_btn)

        zoom_out_btn = wx.Button(toolbar, label="Zoom Out")
        zoom_out_btn.Bind(wx.EVT_BUTTON, self.on_zoom_out)
        toolbar.AddControl(zoom_out_btn)

        zoom_fit_btn = wx.Button(toolbar, label="Zoom Fit")
        zoom_fit_btn.Bind(wx.EVT_BUTTON, self.on_zoom_to_buildings)
        toolbar.AddControl(zoom_fit_btn)

        toolbar.Realize()

    def create_main_panel(self):
        """Create the main panel with canvas"""
        panel = wx.Panel(self)
        sizer = wx.BoxSizer(wx.VERTICAL)

        # Create canvas
        self.canvas = MapCanvas(panel)
        sizer.Add(self.canvas, 1, wx.EXPAND)

        # Status bar
        self.CreateStatusBar()
        self.SetStatusText("Ready")

        panel.SetSizer(sizer)

    def on_key_press(self, event):
        """Handle keyboard shortcuts"""
        key = event.GetKeyCode()

        # Number keys 1-9 for setting building stories
        if ord('1') <= key <= ord('9'):
            stories = key - ord('0')
            self.canvas.set_building_stories(stories)
            self.SetStatusText(
                f"Set selected buildings to {stories} stories")
        elif key == wx.WXK_DELETE:
            self.on_delete(None)
        else:
            event.Skip()

    def on_add_building(self, event):
        """Switch to add building mode"""
        self.canvas.mode = SelectionMode.ADD_BUILDING
        self.canvas.first_corner = None
        self.add_building_btn.SetLabel("Adding...")
        self.SetStatusText("Click to place first corner of building")

    def on_toggle_snap(self, event):
        """Toggle snapping"""
        self.canvas.snap_enabled = self.snap_btn.GetValue()
        self.snap_btn.SetLabel(
            f"Snap: {'ON' if self.canvas.snap_enabled else 'OFF'}")

    def on_set_height(self, event):
        """Open height setting dialog"""
        selected = [b for b in self.canvas.buildings if b.selected]
        if not selected:
            wx.MessageBox("Please select at least one building",
                          "No Selection",
                          wx.OK | wx.ICON_WARNING)
            return

        # Get current values from first selected building
        stories = selected[0].stories
        height = selected[0].height

        dialog = HeightDialog(self, stories, height,
                              self.canvas.storey_height)
        if dialog.ShowModal() == wx.ID_OK:
            new_stories, new_height = dialog.get_values()
            for building in selected:
                building.stories = new_stories
                building.height = new_height
            self.canvas.Refresh()
            self.SetStatusText(
                f"Set height to {new_stories} stories ({new_height:.1f}m)")
        dialog.Destroy()

    def on_delete(self, event):
        """Delete selected buildings"""
        selected = [b for b in self.canvas.buildings if b.selected]
        if not selected:
            return

        result = wx.MessageBox(
            f"Are you sure you want to delete {len(selected)} building(s)?",
            "Confirm Delete",
            wx.YES_NO | wx.ICON_QUESTION
        )

        if result == wx.YES:
            self.canvas.delete_selected_buildings()
            self.SetStatusText(f"Deleted {len(selected)} building(s)")

    def on_zoom_in(self, event):
        """Zoom in"""
        self.canvas.zoom_level *= 1.2
        self.canvas.zoom_level = min(10.0, self.canvas.zoom_level)
        self.canvas.Refresh()

    def on_zoom_out(self, event):
        """Zoom out"""
        self.canvas.zoom_level /= 1.2
        self.canvas.zoom_level = max(0.1, self.canvas.zoom_level)
        self.canvas.Refresh()

    def on_zoom_to_buildings(self, event):
        """Zoom to fit all buildings"""
        self.canvas.zoom_to_buildings()
        self.SetStatusText("Zoomed to fit all buildings")

    def on_select_basemap(self, event):
        """Open basemap selection dialog"""
        dialog = BasemapDialog(
            self,
            self.canvas.map_provider,
            self.canvas.map_enabled,
            self.canvas.geo_center_lat,
            self.canvas.geo_center_lon
        )

        if dialog.ShowModal() == wx.ID_OK:
            provider, enabled, lat, lon = dialog.get_values()

            # Update canvas settings
            self.canvas.map_provider = provider
            self.canvas.map_enabled = enabled
            self.canvas.geo_center_lat = lat
            self.canvas.geo_center_lon = lon

            # Clear tile cache if provider changed
            if provider != self.canvas.map_provider:
                self.canvas.map_tiles.clear()
                self.canvas.tiles_loading.clear()

            self.canvas.Refresh()

            if enabled and provider != MapProvider.NONE:
                self.SetStatusText(f"Basemap: {provider.value}")
            else:
                self.SetStatusText("Basemap disabled")

        dialog.Destroy()

    def on_set_storey_height(self, event):
        """Set the height per storey"""
        dialog = wx.TextEntryDialog(
            self,
            "Enter height per storey (meters):",
            "Set Storey Height",
            f"{self.canvas.storey_height:.1f}"
        )

        if dialog.ShowModal() == wx.ID_OK:
            try:
                height = float(dialog.GetValue())
                if height > 0:
                    self.canvas.storey_height = height
                    # Update all buildings
                    for building in self.canvas.buildings:
                        building.height = building.stories * height
                    self.canvas.Refresh()
                    self.SetStatusText(
                        f"Storey height set to {height:.1f}m")
                else:
                    wx.MessageBox("Height must be positive",
                                  "Invalid Input",
                                  wx.OK | wx.ICON_ERROR)
            except ValueError:
                wx.MessageBox("Invalid number", "Invalid Input",
                              wx.OK | wx.ICON_ERROR)
        dialog.Destroy()

    def on_new(self, event):
        """Create a new project"""
        if self.modified:
            result = wx.MessageBox(
                "Save current project?",
                "New Project",
                wx.YES_NO | wx.CANCEL | wx.ICON_QUESTION
            )
            if result == wx.YES:
                self.on_save(None)
            elif result == wx.CANCEL:
                return

        self.canvas.buildings.clear()
        self.canvas.Refresh()
        self.current_file = None
        self.modified = False
        self.SetTitle("CityJSON Creator - New Project")
        self.SetStatusText("New project created")

    def on_open(self, event):
        """Open a CityJSON file"""
        dialog = wx.FileDialog(
            self,
            "Open CityJSON file",
            wildcard="CityJSON files (*.json)|*.json|All files (*.*)|*.*",
            style=wx.FD_OPEN | wx.FD_FILE_MUST_EXIST
        )

        if dialog.ShowModal() == wx.ID_OK:
            filepath = dialog.GetPath()
            self.load_cityjson(filepath)
        dialog.Destroy()

    def on_save(self, event):
        """Save the current project"""
        if self.current_file:
            self.save_cityjson(self.current_file)
        else:
            self.on_save_as(event)

    def on_save_as(self, event):
        """Save with a new filename"""
        dialog = wx.FileDialog(
            self,
            "Save CityJSON file",
            wildcard="CityJSON files (*.json)|*.json",
            style=wx.FD_SAVE | wx.FD_OVERWRITE_PROMPT
        )

        if dialog.ShowModal() == wx.ID_OK:
            filepath = dialog.GetPath()
            if not filepath.endswith('.json'):
                filepath += '.json'
            self.save_cityjson(filepath)
        dialog.Destroy()

    def load_cityjson(self, filepath):
        """Load a CityJSON file"""
        try:
            with open(filepath, 'r') as f:
                data = json.load(f)

            if data.get('type') != 'CityJSON':
                wx.MessageBox("Not a valid CityJSON file", "Error",
                              wx.OK | wx.ICON_ERROR)
                return

            # Clear current buildings
            self.canvas.buildings.clear()

            # Load metadata if available
            metadata = data.get('metadata', {})
            creator_settings = metadata.get('cityjson_creator_settings',
                                            {})
            if creator_settings:
                # Restore map settings
                map_provider_str = creator_settings.get('map_provider',
                                                        'None')
                for provider in MapProvider:
                    if provider.value == map_provider_str:
                        self.canvas.map_provider = provider
                        break

                self.canvas.map_enabled = creator_settings.get(
                    'map_enabled', True)
                self.canvas.geo_center_lat = creator_settings.get(
                    'geo_center_lat', 49.4875)
                self.canvas.geo_center_lon = creator_settings.get(
                    'geo_center_lon', 8.4660)
                self.canvas.geo_zoom = creator_settings.get('geo_zoom', 16)
                self.canvas.storey_height = creator_settings.get(
                    'storey_height', 3.3)

                # Clear map tiles to reload with new settings
                self.canvas.map_tiles.clear()

            # Load vertices
            vertices = data.get('vertices', [])

            # Load city objects
            for obj_id, obj_data in data.get('CityObjects', {}).items():
                if obj_data.get('type') == 'Building':
                    # Extract building geometry
                    geom = obj_data.get('geometry', [])
                    if geom and geom[0].get('type') == 'Solid':
                        boundaries = geom[0].get('boundaries', [])
                        if boundaries:
                            # Get vertices of the bottom face
                            bottom_face = boundaries[0][
                                0] if boundaries else []
                            if len(bottom_face) >= 4:
                                # Get building bounds
                                v_indices = bottom_face
                                xs = [vertices[i][0] for i in v_indices]
                                ys = [vertices[i][1] for i in v_indices]
                                zs = [vertices[i][2] for i in v_indices]

                                # Get attributes
                                attrs = obj_data.get('attributes', {})
                                height = attrs.get('height', max(zs) - min(
                                    zs) if zs else 10.0)
                                stories = attrs.get('stories', max(1,
                                                                   round(
                                                                       height / self.canvas.storey_height)))

                                building = Building(
                                    id=obj_id,
                                    x1=min(xs),
                                    y1=min(ys),
                                    x2=max(xs),
                                    y2=max(ys),
                                    height=height,
                                    stories=stories
                                )
                                self.canvas.buildings.append(building)

            self.current_file = filepath
            self.modified = False
            self.SetTitle(f"CityJSON Creator - {filepath}")
            self.canvas.zoom_to_buildings()
            self.SetStatusText(
                f"Loaded {len(self.canvas.buildings)} buildings")

        except Exception as e:
            wx.MessageBox(f"Error loading file: {str(e)}", "Error",
                          wx.OK | wx.ICON_ERROR)

    def save_cityjson(self, filepath):
        """Save to a CityJSON file"""
        try:
            # Collect all vertices and create index mapping
            all_vertices = []
            vertex_map = {}

            city_objects = {}

            for building in self.canvas.buildings:
                vertices, boundaries = building.to_cityjson_geometry()

                # Map vertices to global index
                local_to_global = []
                for v in vertices:
                    v_tuple = tuple(v)
                    if v_tuple not in vertex_map:
                        vertex_map[v_tuple] = len(all_vertices)
                        all_vertices.append(list(v))
                    local_to_global.append(vertex_map[v_tuple])

                # Remap boundaries to global indices
                remapped_boundaries = []
                for face in boundaries:
                    remapped_face = [[local_to_global[i] for i in ring] for
                                     ring in face]
                    remapped_boundaries.append(remapped_face)

                # Create city object
                city_objects[building.id] = {
                    "type": "Building",
                    "attributes": {
                        "height": building.height,
                        "stories": building.stories
                    },
                    "geometry": [{
                        "type": "Solid",
                        "lod": 1,
                        "boundaries": [remapped_boundaries]
                    }]
                }

            # Create CityJSON structure with metadata
            cityjson = {
                "type": "CityJSON",
                "version": "1.1",
                "metadata": {
                    "geographicalExtent": [
                        min(v[0] for v in
                            all_vertices) if all_vertices else 0,
                        min(v[1] for v in
                            all_vertices) if all_vertices else 0,
                        min(v[2] for v in
                            all_vertices) if all_vertices else 0,
                        max(v[0] for v in
                            all_vertices) if all_vertices else 0,
                        max(v[1] for v in
                            all_vertices) if all_vertices else 0,
                        max(v[2] for v in
                            all_vertices) if all_vertices else 0,
                    ],
                    "referenceSystem": f"https://www.opengis.net/def/crs/EPSG/0/4326",
                    "cityjson_creator_settings": {
                        "map_provider": self.canvas.map_provider.value,
                        "map_enabled": self.canvas.map_enabled,
                        "geo_center_lat": self.canvas.geo_center_lat,
                        "geo_center_lon": self.canvas.geo_center_lon,
                        "geo_zoom": self.canvas.geo_zoom,
                        "storey_height": self.canvas.storey_height
                    }
                },
                "CityObjects": city_objects,
                "vertices": all_vertices
            }

            # Save to file
            with open(filepath, 'w') as f:
                json.dump(cityjson, f, indent=2)

            self.current_file = filepath
            self.modified = False
            self.SetTitle(f"CityJSON Creator - {filepath}")
            self.SetStatusText(
                f"Saved {len(self.canvas.buildings)} buildings to {filepath}")

        except Exception as e:
            wx.MessageBox(f"Error saving file: {str(e)}", "Error",
                          wx.OK | wx.ICON_ERROR)

    def on_exit(self, event):
        """Exit the application"""
        if self.modified:
            result = wx.MessageBox(
                "Save changes before exiting?",
                "Exit",
                wx.YES_NO | wx.CANCEL | wx.ICON_QUESTION
            )
            if result == wx.YES:
                self.on_save(None)
            elif result == wx.CANCEL:
                return

        self.Close()

    def on_about(self, event):
        """Show about dialog"""
        info = f"""CityJSON Creator
Version: {APP_VERSION}

A graphical tool for creating and editing CityJSON files.

Library Versions:
- wxPython: {wx.__version__}
- Python: {sys.version.split()[0]}
- NumPy: {np.__version__}

Map Data Sources:
- OpenStreetMap: © OpenStreetMap contributors
- Satellite: © Esri World Imagery
- Terrain: © OpenTopoMap (CC-BY-SA)

© 2024 - Created with Claude"""

        wx.MessageBox(info, "About CityJSON Creator",
                      wx.OK | wx.ICON_INFORMATION)


class CityJSONApp(wx.App):
    """Main application class"""

    def OnInit(self):
        self.frame = MainFrame()
        return True


if __name__ == '__main__':
    app = CityJSONApp()
    app.MainLoop()

    # # Edit menu
    # edit_menu = wx.Menu()
    # basemap_item = edit_menu.Append(wx.ID_ANY, "Select &Basemap",
    #                                 "Choose a basemap")
    # zoom_item = edit_menu.Append(wx.ID_ANY, "&Zoom to Buildings\tCtrl+0",
    #                              "Zoom to fit all buildings")
    # storey_item = edit_menu.Append(wx.ID_ANY, "Set Storey &Height",
    #                                "Set the height per storey")
    #
    # # Help menu
    # help_menu = wx.Menu()
    # help_menu.Append(wx.ID_ABOUT, "&About", "About this application")
    #
    # menubar.Append(file_menu, "&File")
    # menubar.Append(edit_menu, "&Edit")
    # menubar.Append(help_menu, "&Help")
    #
    # self.SetMenuBar(menubar)
    #
    # # Bind menu events
    # self.Bind(wx.EVT_MENU, self.on_new, id=wx.ID_NEW)
    # self.Bind(wx.EVT_MENU, self.on_open, id=wx.ID_OPEN)
    # self.Bind(wx.EVT_MENU, self.on_save, id=wx.ID_SAVE)
    # self.Bind(wx.EVT_MENU, self.on_save_as, id=wx.ID_SAVEAS)
    # self.Bind(wx.EVT_MENU, self.on_exit, id=wx.ID_EXIT)
    # self.Bind(wx.EVT_MENU, self.on_about, id=wx.ID_ABOUT)
    #
    # # Bind edit menu events
    # self.Bind(wx.EVT_MENU, self.on_select_basemap, id=basemap_item.GetId())
    # self.Bind(wx.EVT_MENU, self.on_zoom_to_buildings, id=zoom_item.GetId())
    # self.Bind(wx.EVT_MENU, self.on_set_storey_height,
    #           id=storey_item.GetId())