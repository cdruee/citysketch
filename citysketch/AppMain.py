# !/usr/bin/env python3
"""
CityJSON Creator Application
A wxPython GUI application for creating and editing CityJSON files with building data.
"""

import io
import json
import math
import os
import sys
import tempfile
import threading
import urllib.parse
import urllib.request
import uuid
from typing import List, Tuple, Optional

import numpy as np
import wx

from AppDialogs import AboutDialog, BasemapDialog, HeightDialog
from Building import Building
from utils import SelectionMode, MapProvider, get_location_with_fallback
from _version import __version__ as APP_VERSION

# =========================================================================

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

# =========================================================================

class MapCanvas(wx.Panel):
    """The main canvas for displaying and editing buildings"""

    BASE_TILE_SIZE = 256
    BASE_GEO_ZOOM = 16

    def __init__(self, parent):
        super().__init__(parent)
        self.parent = parent
        self.statusbar = None

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
        self.tile_cache = TileCache()
        self.tiles_loading = set()
        self.map_tiles = {}  # (z,x,y): wx.Image

        # Geographic coordinates (center of view)
        lat, lon = get_location_with_fallback()  # user IP location
        self.geo_center_lat = lat
        self.geo_center_lon = lon
        self.geo_zoom = self.BASE_GEO_ZOOM  # Tile zoom level

        # Interaction state
        self.mouse_down = False
        self.drag_start = None
        self.drag_building = None
        self.drag_corner = None
        self.drag_corner_index = None
        self.floating_rect = None
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
        self.SetBackgroundColour(wx.WHITE)

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
            # FIXME
            # if abs(x - building.x1) < best_dist:
            #     best_x = building.x1
            #     best_dist = abs(x - building.x1)
            # if abs(x - building.x2) < best_dist:
            #     best_x = building.x2
            #     best_dist = abs(x - building.x2)
            # if abs(y - building.y1) < best_dist:
            #     best_y = building.y1
            #     best_dist = abs(y - building.y1)
            # if abs(y - building.y2) < best_dist:
            #     best_y = building.y2
            #     best_dist = abs(y - building.y2)

        return best_x, best_y

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
            servers = ['a', 'b', 'c']
            server = servers[abs(hash((x, y))) % len(servers)]
            return f"https://{server}.tile.openstreetmap.org/{z}/{x}/{y}.png"
        elif provider == MapProvider.SATELLITE:
            return f"https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{z}/{y}/{x}"
        elif provider == MapProvider.TERRAIN:
            servers = ['a', 'b', 'c']
            server = servers[abs(hash((x, y))) % len(servers)]
            return f"https://{server}.tile.opentopomap.org/{z}/{x}/{y}.png"
        return None

    def load_tile_async(self, provider, z, x, y):
        """Load a tile asynchronously"""

        def load():
            try:
                image = self.tile_cache.get_tile(provider, z, x, y)
                if image:
                    wx.CallAfter(self.on_tile_loaded, provider, z, x, y,
                                 image)
                    return

                url = self.get_tile_url(provider, z, x, y)
                if url:
                    req = urllib.request.Request(url, headers={
                        'User-Agent': 'CityJSON Creator/1.0'
                    })
                    with urllib.request.urlopen(req,
                                                timeout=5) as response:
                        data = response.read()

                    image = self.tile_cache.save_tile(provider, z, x, y,
                                                      data)
                    if image:
                        wx.CallAfter(self.on_tile_loaded, provider, z, x,
                                     y, image)
            except Exception as e:
                self.statusbar.SetStatusText(
                    f"Failed to load tile {z}/{x}/{y}: {e}")
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
        wx.EndBusyCursor()

    def on_paint(self, event):
        """Handle paint events"""
        dc = wx.AutoBufferedPaintDC(self)
        dc.SetBackground(wx.Brush(wx.WHITE))
        dc.Clear()

        # Draw map tiles if enabled
        if self.map_provider != MapProvider.NONE:
            self.draw_map_tiles(dc)

        # Set up graphics context for other drawing
        gc = wx.GraphicsContext.Create(dc)

        # Draw grid
        self.draw_grid(gc)

        self.geo_zoom = 11
        while (self.zoom_level > 2.**self.geo_zoom / 2.**self.BASE_GEO_ZOOM
                and self.geo_zoom < 18):
            self.geo_zoom += 1

        if self.statusbar is not None:
            self.statusbar.SetStatusText(
                f"Zoom level {self.geo_zoom:2d}  "
                f"factor {self.zoom_level:3.2f} "
                f"Pan: {self.pan_x:7.1f} {self.pan_y:7.1f}",  i=2)

        # Draw buildings
        for building in self.buildings:
            self.draw_building(gc, building)

        # Draw preview for new building
        if self.mode == SelectionMode.ADD_BUILDING and self.floating_rect and self.current_mouse_pos:
            self.draw_building_preview(gc)
            print (self.floating_rect)

        # Draw selection rectangle
        if self.mode == SelectionMode.RECTANGLE_SELECT and self.selection_rect_start and self.current_mouse_pos:
            self.draw_selection_rectangle(gc)

    def draw_map_tiles(self, dc):
        """Draw map tiles as background"""
        width, height = self.GetSize()
        tile_size = self.BASE_TILE_SIZE * self.zoom_level * 2**16/( 2**self.geo_zoom)

        center_tile_x, center_tile_y = self.lat_lon_to_tile(
            self.geo_center_lat, self.geo_center_lon, self.geo_zoom
        )

        floor_x = math.floor(center_tile_x)
        floor_y = math.floor(center_tile_y)
        frac_x = center_tile_x - floor_x
        frac_y = center_tile_y - floor_y

        center_x, center_y = self.world_to_screen(0,0 )

        offset_x = -frac_x * tile_size + center_x
        offset_y = -frac_y * tile_size + center_y

        tiles_x = math.ceil(width / tile_size) + 1
        tiles_y = math.ceil(height / tile_size) + 1

        #start_tile_x = floor_x - 1 # tiles_x // 2
        #start_tile_y = floor_y - 1 # tiles_y // 2
        start_tile_x = floor_x - math.ceil( offset_x / tile_size)
        start_tile_y = floor_y - math.ceil( offset_y / tile_size)


        for tile_y in range(start_tile_y, start_tile_y + tiles_y):
            for tile_x in range(start_tile_x, start_tile_x + tiles_x):

                max_tile = 2 ** self.geo_zoom
                if tile_x < 0 or tile_x >= max_tile or tile_y < 0 or tile_y >= max_tile:
                    continue

                screen_x = offset_x + (tile_x - floor_x) * tile_size
                screen_y = offset_y + (tile_y - floor_y) * tile_size

                tile_key = (self.geo_zoom, tile_x, tile_y)
                if tile_key in self.map_tiles:
                    image = self.map_tiles[tile_key]
                    scaled = image.Scale(int(tile_size), int(tile_size),
                                        wx.IMAGE_QUALITY_HIGH)
                    bitmap = wx.Bitmap(scaled)
                    dc.DrawBitmap(bitmap, int(screen_x), int(screen_y))
                else:
                    dc.SetBrush(wx.Brush(wx.Colour(240, 240, 240)))
                    dc.SetPen(wx.Pen(wx.Colour(200, 200, 200), 1))
                    dc.DrawRectangle(int(screen_x), int(screen_y),
                                     int(tile_size), int(tile_size))

                    if tile_key not in self.tiles_loading:
                        wx.BeginBusyCursor()
                        self.tiles_loading.add(tile_key)
                        self.load_tile_async(self.map_provider,
                                             self.geo_zoom, tile_x, tile_y)

    def draw_grid(self, gc):
        """Draw background grid"""
        if self.map_provider == MapProvider.NONE:
            gc.SetPen(wx.Pen(wx.Colour(220, 220, 220), 1))
        else:
            gc.SetPen(wx.Pen(wx.Colour(100, 100, 100, 50), 1))

        width, height = self.GetSize()
        grid_size = 50 * self.zoom_level

        x = self.pan_x % grid_size
        while x < width:
            gc.StrokeLine(x, 0, x, height)
            x += grid_size

        y = self.pan_y % grid_size
        while y < height:
            gc.StrokeLine(0, y, width, y)
            y += grid_size

    def draw_building(self, gc, building: Building):
        """Draw a single building with rotation support"""
        # Get rotated corners
        corners = building.get_corners()

        # Create path for rotated rectangle
        path = gc.CreatePath()
        path.MoveToPoint(*self.world_to_screen(*corners[0]))
        for corner in corners[1:]:
            path.AddLineToPoint(*self.world_to_screen(*corner))
        path.CloseSubpath()

        # Set colors based on selection
        if building.selected:
            fill_color = wx.Colour(150, 180, 255, 180)
            border_color = wx.Colour(0, 0, 255)
        else:
            fill_color = wx.Colour(200, 200, 200, 180)
            border_color = wx.Colour(100, 100, 100)

        gc.SetBrush(wx.Brush(fill_color))
        gc.SetPen(wx.Pen(border_color, 2))
        gc.DrawPath(path)

        # Draw height text at center
        cx = sum(c[0] for c in corners) / 4
        cy = sum(c[1] for c in corners) / 4
        scx, scy = self.world_to_screen(cx, cy)

        gc.SetFont(wx.Font(10, wx.FONTFAMILY_DEFAULT, wx.FONTSTYLE_NORMAL,
                           wx.FONTWEIGHT_NORMAL),
                   wx.Colour(255, 255, 255))
        text = f"{building.storeys}F"
        tw, th = gc.GetTextExtent(text)
        gc.DrawText(text, scx - tw / 2, scy - th / 2)

        # Draw corner handles if selected
        if building.selected:
            # Check if Ctrl is pressed (use rotation mode)
            ctrl_pressed = wx.GetKeyState(wx.WXK_CONTROL)

            for i, (cx, cy) in enumerate(corners):
                sx, sy = self.world_to_screen(cx, cy)

                if ctrl_pressed:
                    # Draw circles in rotation mode
                    if i == 0:
                        # Filled circle for rotation center
                        gc.SetBrush(wx.Brush(wx.Colour(0, 0, 255)))
                    else:
                        # Open circle for other corners
                        gc.SetBrush(wx.Brush(wx.Colour(255, 255, 255)))
                    gc.SetPen(wx.Pen(wx.Colour(0, 0, 255), 2))
                    gc.DrawEllipse(sx - 5, sy - 5, 10, 10)
                else:
                    # Draw squares in normal mode
                    gc.SetBrush(wx.Brush(wx.Colour(255, 255, 255)))
                    gc.SetPen(wx.Pen(wx.Colour(0, 0, 255), 2))
                    gc.DrawRectangle(sx - 4, sy - 4, 8, 8)

    def draw_building_preview(self, gc):
        """Draw preview of building being created with rotation support"""
        x1, y1 = self.floating_rect['anchor']
        x2, y2 = self.screen_to_world(*self.current_mouse_pos)

        ctrl_pressed = wx.GetKeyState(wx.WXK_CONTROL)

        if ctrl_pressed and self.floating_rect:
            # Calculate distance for fixed size
            dist = math.sqrt((x2 - x1) ** 2 + (y2 - y1) ** 2)
            # Calculate angle
            angle = math.atan2(y2 - y1, x2 - x1)

            # Create a rectangle with constant aspect ratio
            old_dist = math.sqrt(self.floating_rect['b']**2. +
                                 self.floating_rect['a']**2.)
            new_a = self.floating_rect['a']
            new_b = self.floating_rect['b']
            # new_a = self.floating_rect['a'] * dist/old_dist
            # new_b = self.floating_rect['b'] * dist/old_dist
            new_r = angle - math.atan2(new_b, new_a)
        
        else:
            # Scaling mode during creation
            dx = x2 - x1
            dy = y2 - y1
            new_r = self.floating_rect['r']
            new_a = + math.cos(new_r) * dx + math.sin(new_r) * dy
            new_b = - math.sin(new_r) * dx + math.cos(new_r) * dy
            
        corners = [
            (0., 0.),
            (new_a, 0.),
            (new_a, new_b),
            (0., new_b)
        ]

        # Draw rotated preview
        path = gc.CreatePath()
        sx, sy = self.world_to_screen(x1, y1)
        path.MoveToPoint(sx, sy)
        for ca, cb in corners[1:]:
            x = x1 + math.cos(new_r) * ca - math.sin(new_r) * cb
            y = y1 + math.sin(new_r) * ca + math.cos(new_r) * cb
            sx, sy = self.world_to_screen(x, y)
            path.AddLineToPoint(sx, sy)
        path.CloseSubpath()

        gc.SetBrush(wx.Brush(wx.Colour(100, 255, 100, 100)))
        gc.SetPen(wx.Pen(wx.Colour(0, 200, 0), 2, wx.PENSTYLE_DOT))
        gc.DrawPath(path)

        self.floating_rect['a'] = new_a
        self.floating_rect['b'] = new_b
        self.floating_rect['r'] = new_r

    def draw_selection_rectangle(self, gc):
        """Draw preview of building being created with rotation support"""

        # Draw rectangle
        sx, sy = self.selection_rect_start
        cx, cy = self.current_mouse_pos
        corners = [
            (sx, sy),
            (cx, sy),
            (cx, cy),
            (sx, cy)
        ]
        path = gc.CreatePath()
        path.MoveToPoint(sx, sy)
        for xx, yy in corners[1:]:
            path.AddLineToPoint(xx, yy)
        path.CloseSubpath()

        gc.SetBrush(wx.NullBrush)
        gc.SetPen(wx.Pen(wx.Colour(32, 32, 32), 2, wx.PENSTYLE_SHORT_DASH))
        gc.DrawPath(path)

    def on_mouse_down(self, event):
        """Handle mouse down events with rotation support"""
        self.mouse_down = True
        self.drag_start = event.GetPosition()
        wx, wy = self.screen_to_world(event.GetX(), event.GetY())
        ctrl_pressed = event.ControlDown()

        if self.mode == SelectionMode.ADD_BUILDING:
            if self.floating_rect is None:
                self.floating_rect = {'anchor': self.snap_point(wx, wy),
                                      'a': 0., 'b': 0., 'r': 0.}
                self.statusbar.SetStatusText(
                    "Move to draw, press Ctrl to rotate, click to finish")
            else:
                x1, y1 = self.floating_rect['anchor']
                building = Building(
                    id=str(uuid.uuid4()),
                    x1=x1,
                    y1=y1,
                    a=self.floating_rect['a'],
                    b=self.floating_rect['b'],
                    height=self.storey_height * 3,
                    storeys=3,
                    rotation=self.floating_rect['r']
                )

                self.buildings.append(building)
                self.floating_rect = None
                self.mode = SelectionMode.NORMAL
                self.statusbar.SetStatusText(
                    f"Added building #{len(self.buildings)}")
                self.Refresh()

        elif self.mode == SelectionMode.NORMAL:
            if event.ShiftDown():
                self.mode = SelectionMode.RECTANGLE_SELECT
                self.selection_rect_start = event.GetPosition()
            else:
                # Check for corner drag
                for building in self.buildings:
                    if building.selected:
                        corner_idx = building.get_corner_index(wx, wy,
                                                               10 / self.zoom_level)
                        if corner_idx is not None:
                            if ctrl_pressed:
                                # Rotation mode
                                self.drag_corner = building
                                self.drag_corner_index = corner_idx
                                self.drag_mode = 'rotate'
                                return
                            else:
                                # Normal scaling mode
                                self.drag_corner = building
                                self.drag_corner_index = corner_idx
                                self.drag_mode = 'scale'
                                return

                # Check for building click
                clicked_building = None
                for building in reversed(self.buildings):
                    if building.contains_point(wx, wy):
                        clicked_building = building
                        break

                if clicked_building:
                    if not event.ControlDown():
                        for b in self.buildings:
                            b.selected = False
                    clicked_building.selected = not clicked_building.selected if event.ControlDown() else True
                    self.drag_building = clicked_building
                else:
                    if not event.ControlDown():
                        for b in self.buildings:
                            b.selected = False

                self.Refresh()

    def on_mouse_up(self, event):
        """Handle mouse up events"""
        self.mouse_down = False

        if self.mode == SelectionMode.RECTANGLE_SELECT:
            x1, y1 = self.screen_to_world(*self.selection_rect_start)
            x2, y2 = self.screen_to_world(event.GetX(), event.GetY())

            rx1, rx2 = min(x1, x2), max(x1, x2)
            ry1, ry2 = min(y1, y2), max(y1, y2)

            for building in self.buildings:
                le, lo, ri, up = building.get_llur()
                if (le >= rx1 and ri <= rx2 and
                        lo >= ry1 and up <= ry2):
                    building.selected = True

            self.mode = SelectionMode.NORMAL
            self.selection_rect_start = None
            self.Refresh()

        self.drag_building = None
        self.drag_corner = None
        self.drag_corner_index = None
        self.drag_mode = None
        self.drag_start = None

    def on_mouse_motion(self, event):
        """Handle mouse motion events with rotation support"""
        self.current_mouse_pos = event.GetPosition()
        wx, wy = self.screen_to_world(event.GetX(), event.GetY())

        if self.mouse_down and self.drag_start:
            if self.drag_corner and self.drag_corner_index is not None:
                snapped_x, snapped_y = self.snap_point(wx, wy,
                                                           self.drag_corner)
                if self.drag_mode == 'scale':
                    self.drag_corner.scale_to_corner(
                        self.drag_corner_index, snapped_x, snapped_y)
                elif self.drag_mode == 'rotate':
                    self.drag_corner.rotate_to_corner(
                        self.drag_corner_index, snapped_x, snapped_y)
                self.Refresh()
            elif self.drag_building:
                # Moving building
                start_wx, start_wy = self.screen_to_world(*self.drag_start)
                dx = wx - start_wx
                dy = wy - start_wy

                new_x1 = self.drag_building.x1 + dx
                new_y1 = self.drag_building.y1 + dy
                snapped_x, snapped_y = self.snap_point(new_x1, new_y1,
                                                       self.drag_building)

                actual_dx = snapped_x - self.drag_building.x1
                actual_dy = snapped_y - self.drag_building.y1

                self.drag_building.shift(actual_dx, actual_dy)
                self.drag_start = event.GetPosition()
                self.Refresh()
            elif not event.ShiftDown():
                # Panning
                dx = event.GetX() - self.drag_start[0]
                dy = event.GetY() - self.drag_start[1]
                self.pan_x += dx
                self.pan_y += dy
                self.drag_start = event.GetPosition()
                self.Refresh()

        # Update preview
        if self.mode == SelectionMode.ADD_BUILDING and self.floating_rect:
            self.Refresh()

        if self.mode == SelectionMode.RECTANGLE_SELECT:
            self.Refresh()

        # Update corner appearance when Ctrl is pressed/released
        if any(b.selected for b in self.buildings):
            self.Refresh()

    def on_mouse_wheel(self, event):
        """Handle mouse wheel events for zooming"""
        rotation = event.GetWheelRotation()
        mx, my = event.GetPosition()

        zoom_factor = 1.1 if rotation > 0 else 0.9
        new_zoom = self.zoom_level * zoom_factor
        new_zoom = max(0.1, min(10.0, new_zoom))

        wx, wy = self.screen_to_world(mx, my)
        self.zoom_level = new_zoom
        new_mx, new_my = self.world_to_screen(wx, wy)

        self.pan_x += mx - new_mx
        self.pan_y += my - new_my

        self.Refresh()

    def on_size(self, event):
        """Handle resize events"""
        self.Refresh()
        event.Skip()

    def set_building_stories(self, stories: int):
        """Set stories for selected buildings"""
        for building in self.buildings:
            if building.selected:
                building.storeys = stories
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

        min_x = min(b.get_llur()[0] for b in self.buildings)
        max_x = min(b.get_llur()[2] for b in self.buildings)
        min_y = min(b.get_llur()[1] for b in self.buildings)
        max_y = min(b.get_llur()[3] for b in self.buildings)

        width, height = self.GetSize()
        margin = 50

        zoom_x = (width - 2 * margin) / (
                    max_x - min_x) if max_x > min_x else 1.0
        zoom_y = (height - 2 * margin) / (
                    max_y - min_y) if max_y > min_y else 1.0

        self.zoom_level = min(zoom_x, zoom_y, 5.0)

        center_x = (min_x + max_x) / 2
        center_y = (min_y + max_y) / 2

        self.pan_x = width / 2 - center_x * self.zoom_level
        self.pan_y = height / 2 - center_y * self.zoom_level

        self.Refresh()

# =========================================================================

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
        statusbar = self.CreateStatusBar()
        statusbar.SetFieldsCount(3)
        statusbar.SetStatusWidths([-3,-2,-2])
        self.SetStatusText("Ready")
        self.canvas.statusbar = statusbar

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
        self.canvas.floating_rect = None
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
        stories = selected[0].storeys
        height = selected[0].height

        dialog = HeightDialog(self, stories, height,
                              self.canvas.storey_height)
        if dialog.ShowModal() == wx.ID_OK:
            new_stories, new_height = dialog.get_values()
            for building in selected:
                building.storeys = new_stories
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
            self.canvas.geo_center_lat,
            self.canvas.geo_center_lon
        )

        if dialog.ShowModal() == wx.ID_OK:
            provider, lat, lon = dialog.get_values()

            # Clear tile cache if provider changed
            if provider != self.canvas.map_provider:
                self.canvas.map_tiles.clear()
                self.canvas.tiles_loading.clear()

            # Update canvas settings
            self.canvas.map_provider = provider
            self.canvas.geo_center_lat = lat
            self.canvas.geo_center_lon = lon

            self.canvas.Refresh()

            if provider != MapProvider.NONE:
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
                        building.height = building.storeys * height
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
                                    storeys=stories
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
                        "stories": building.storeys
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
        about = (AboutDialog(self))
        about.ShowModal()
        about.Destroy()

# =========================================================================

class CityJSONApp(wx.App):
    """Main application class"""

    def OnInit(self):
        self.frame = MainFrame()
        return True

# =========================================================================

def main():
    app = CityJSONApp()
    app.MainLoop()

if __name__ == '__main__':
    main()