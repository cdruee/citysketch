# !/usr/bin/env python3
"""
CitySketch Application
A wxPython GUI application for creating and editing CityJSON files with building data.
"""

from dataclasses import dataclass
from enum import Enum
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

try:
    import rasterio
    from rasterio.warp import transform_bounds, reproject, Resampling
    from rasterio.transform import from_bounds
    GEOTIFF_SUPPORT = True
except ImportError:
    GEOTIFF_SUPPORT = False
    print("Warning: GeoTIFF support not available. "
          "Install rasterio for full functionality.")

from .AppDialogs import (AboutDialog, HeightDialog,
                        BasemapDialog, GeoTiffDialog)
from .App3dview import OPENGL_SUPPORT, Building3DViewer
from .Building import Building, BuildingGroup
from .AppSettings import colorset, settings
from .ColorDialogs import ColorSettingsDialog
from .austaltxt import load_from_austaltxt, save_to_austaltxt
from .utils import MapProvider, get_location_with_fallback
from ._version import __version__, __version_tuple__

APP_NAME = "CitySketch"
APP_VERSION = __version__
APP_MINOR = '.'.join(str(x) for x in __version_tuple__[0:2])

FEXT = '.csp'

print(f"Starting {APP_NAME} {APP_MINOR} (v{APP_VERSION})")

# =========================================================================

@dataclass
class Preview:
    anchor: Tuple[float, float]
    a: float
    b: float
    r: float

# =========================================================================

class SelectMode(Enum):
    NORMAL = "normal"
    ADD_BUILDING = "add_building"
    ADD_ROTUNDA = "add_rotunda"
    RECTANGLE_SELECT = "rectangle_select"

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

class GeoTiffLayer:
    """Manages a GeoTIFF overlay layer"""

    def __init__(self):
        self.filepath = None
        self.visible = True
        self.opacity = 0.7
        self.data = None
        self.transform = None
        self.crs = None
        self.bounds = None  # (west, south, east, north) in WGS84
        self.wx_image = None
        self.reprojected_data = None
        self.reprojected_transform = None

    def load_file(self, filepath):
        """Load a GeoTIFF file"""
        if not GEOTIFF_SUPPORT:
            raise RuntimeError("GeoTIFF support not available. "
                               "Please install gdal and rasterio.")

        try:
            with rasterio.open(filepath) as src:
                print(f"Loading GeoTIFF: {filepath}")

                epsg = src.crs.to_epsg()

                if epsg != 4326:
                    result = wx.MessageBox(
                        f"The loaded image is not projected "
                        f"to EPSG:4326 (WGS84), but to EPSG:{epsg}. "
                        f"This will result in a very slow display. "
                        f"Are you sure you want to use it?",
                        "Confirm Delete",
                        wx.YES_NO | wx.ICON_QUESTION
                    )

                    if result == wx.NO:
                        self.data = None
                        return False

                print(f"Shape: {src.shape}, "
                      f"Bands: {src.count}, CRS: {src.crs}")
                print(f"Data type: {src.dtypes}, Bounds: {src.bounds}")

                # Read the data with better handling
                if src.count >= 3:
                    # RGB or RGBA - read first 3 bands
                    self.data = src.read([1, 2, 3])
                elif src.count == 1:
                    # Grayscale - duplicate to RGB
                    band = src.read(1)
                    self.data = np.stack([band, band, band], axis=0)
                else:
                    # Read first band and duplicate
                    band = src.read(1)
                    self.data = np.stack([band, band, band], axis=0)

                self.transform = src.transform
                self.crs = src.crs

                # Get bounds in WGS84
                if self.crs and epsg != 4326:
                    self.bounds = transform_bounds(src.crs, 'EPSG:4326',
                                                   *src.bounds)
                else:
                    self.bounds = src.bounds
                print(f"Bounds in WGS84: {self.bounds}")

                self.filepath = filepath

                # Handle different data types and ranges
                if self.data.dtype == np.uint8:
                    # Already 8-bit, just ensure it's in 0-255 range
                    pass
                elif self.data.dtype == np.uint16:
                    # 16-bit data, scale down to 8-bit
                    self.data = (self.data / 256).astype(np.uint8)
                elif np.issubdtype(self.data.dtype, np.floating):
                    # Floating point data
                    data_min = np.nanmin(self.data)
                    data_max = np.nanmax(self.data)
                    print(f"Float data range: {data_min} to {data_max}")

                    # Handle common float ranges
                    if data_max <= 1.0 and data_min >= 0.0:
                        # Normalized float (0-1), scale to 0-255
                        self.data = (self.data * 255).astype(np.uint8)
                    else:
                        # General float, normalize then scale
                        if data_max > data_min:
                            self.data = ((self.data - data_min) / (
                                        data_max - data_min) * 255).astype(
                                np.uint8)
                        else:
                            self.data = np.full_like(self.data, 128,
                                                     dtype=np.uint8)
                else:
                    # Other integer types, normalize to 0-255
                    data_min = np.min(self.data)
                    data_max = np.max(self.data)
                    if data_max > data_min:
                        self.data = ((self.data - data_min) / (
                                    data_max - data_min) * 255).astype(
                            np.uint8)
                    else:
                        self.data = np.full_like(self.data, 128,
                                                 dtype=np.uint8)

                # Handle NoData values
                if hasattr(src, 'nodata') and src.nodata is not None:
                    nodata_mask = self.data == src.nodata
                    self.data[nodata_mask] = 0

                return True

        except Exception as e:
            print(f"Error in load_file: {e}")
            raise RuntimeError(f"Failed to load GeoTIFF: {str(e)}")

    def reproject_for_display(self, target_bounds, target_size):
        """Reproject the GeoTIFF data for display at current view"""
        if not GEOTIFF_SUPPORT or self.data is None:
            return False

        try:
            print(f"Reprojecting for display:")
            print(f"Target bounds: {target_bounds}")
            print(f"Target size: {target_size}")
            print(f"Source CRS: {self.crs}")

            # Create target transform
            target_transform = from_bounds(*target_bounds, target_size[0],
                                           target_size[1])
            print(f"Target transform: {target_transform}")

            # Prepare output array
            reprojected = np.zeros((3, target_size[1], target_size[0]),
                                   dtype=np.uint8)

            # Check if we need reprojection at all
            if self.crs and self.crs.to_epsg() == 4326:
                print("Source is already WGS84, "
                      "using direct transformation")
                # Direct pixel mapping without CRS transformation
                src_bounds = self.bounds

                # Calculate scaling factors
                scale_x = self.data.shape[2] / (
                            src_bounds[2] - src_bounds[0])
                scale_y = self.data.shape[1] / (
                            src_bounds[3] - src_bounds[1])

                # Calculate source pixel coordinates for target bounds
                src_x_min = int(
                    (target_bounds[0] - src_bounds[0]) * scale_x)
                src_x_max = int(
                    (target_bounds[2] - src_bounds[0]) * scale_x)
                src_y_min = int((src_bounds[3] - target_bounds[
                    3]) * scale_y)  # Note: y is flipped
                src_y_max = int(
                    (src_bounds[3] - target_bounds[1]) * scale_y)

                # Clamp to valid ranges
                src_x_min = max(0, min(self.data.shape[2] - 1, src_x_min))
                src_x_max = max(0, min(self.data.shape[2], src_x_max))
                src_y_min = max(0, min(self.data.shape[1] - 1, src_y_min))
                src_y_max = max(0, min(self.data.shape[1], src_y_max))

                print(f"Source pixel bounds: x({src_x_min}:{src_x_max}), "
                      f"y({src_y_min}:{src_y_max})")

                if src_x_max > src_x_min and src_y_max > src_y_min:
                    # Extract the relevant portion
                    cropped_data = self.data[
                        :, src_y_min:src_y_max, src_x_min:src_x_max]
                    print(f"Cropped data shape: {cropped_data.shape}")

                    # Resize to target size
                    from scipy.ndimage import zoom
                    if cropped_data.shape[1] > 0 and cropped_data.shape[
                        2] > 0:
                        zoom_y = target_size[1] / cropped_data.shape[1]
                        zoom_x = target_size[0] / cropped_data.shape[2]

                        for i in range(3):
                            reprojected[i] = zoom(cropped_data[i],
                                                  (zoom_y, zoom_x),
                                                  order=1)

            else:
                # Use rasterio reprojection for different CRS
                print("Using rasterio reprojection for non-WGS84 data")

                # Try rasterio first (if future Version works)
                try:
                    for i in range(3):
                        reprojected[i], _ = reproject(
                            source=self.data[i],
                            destination=reprojected[i],
                            src_transform=self.transform,
                            src_crs=self.crs,
                            dst_transform=target_transform,
                            dst_crs='EPSG:4326',
                            resampling=Resampling.bilinear,
                            src_nodata=None,
                            dst_nodata=0
                        )

                    total_nonzero = np.count_nonzero(reprojected)
                    print(
                        f"Rasterio reprojection produced {total_nonzero} non-zero pixels")

                except Exception as e:
                    print(f"Rasterio reprojection failed: {e}")
                    total_nonzero = 0

                # If rasterio failed or produced no data, use improved manual approach
                if np.count_nonzero(reprojected) == 0:
                    print("Using manual transformation...")

                    try:
                        from rasterio.warp import \
                            transform as warp_transform

                        height, width = self.data.shape[1], \
                        self.data.shape[2]

                        # Create coordinate arrays for the entire source image
                        print("Creating coordinate grids...")

                        # Create meshgrid of all pixel coordinates
                        px_coords, py_coords = np.meshgrid(
                            np.arange(width, dtype=np.float64),
                            np.arange(height, dtype=np.float64)
                        )

                        # Transform pixel coordinates to source CRS coordinates using the affine transform
                        src_x_coords = (self.transform.c +
                                        self.transform.a * px_coords +
                                        self.transform.b * py_coords)
                        src_y_coords = (self.transform.f +
                                        self.transform.d * px_coords +
                                        self.transform.e * py_coords)

                        print(f"Source coordinate ranges: "
                              f"X({np.min(src_x_coords):.2f} "
                              f"to {np.max(src_x_coords):.2f}), "
                              f"Y({np.min(src_y_coords):.2f} "
                              f"to {np.max(src_y_coords):.2f})")

                        # Transform to WGS84 in chunks to manage memory
                        chunk_size = 10000  # Process 10k points at a time
                        total_pixels = width * height
                        processed_pixels = 0

                        print("Transforming coordinates to WGS84...")

                        # Flatten arrays for processing
                        src_x_flat = src_x_coords.flatten()
                        src_y_flat = src_y_coords.flatten()

                        # Process in chunks
                        for start_idx in range(0, total_pixels,
                                               chunk_size):
                            end_idx = min(start_idx + chunk_size,
                                          total_pixels)

                            # Transform this chunk
                            chunk_x = src_x_flat[start_idx:end_idx]
                            chunk_y = src_y_flat[start_idx:end_idx]

                            try:
                                wgs84_x_chunk, wgs84_y_chunk = \
                                    warp_transform(
                                        self.crs, 'EPSG:4326',
                                        chunk_x, chunk_y
                                    )

                                # Filter points within target bounds
                                mask = ((np.array(wgs84_x_chunk) >=
                                         target_bounds[0]) &
                                        (np.array(wgs84_x_chunk) <=
                                         target_bounds[2]) &
                                        (np.array(wgs84_y_chunk) >=
                                         target_bounds[1]) &
                                        (np.array(wgs84_y_chunk) <=
                                         target_bounds[3]))

                                if np.any(mask):
                                    # Get valid points
                                    valid_wgs84_x = \
                                    np.array(wgs84_x_chunk)[mask]
                                    valid_wgs84_y = \
                                    np.array(wgs84_y_chunk)[mask]

                                    # Calculate corresponding source pixel indices
                                    valid_indices = \
                                    np.arange(start_idx, end_idx)[mask]
                                    src_py_indices = valid_indices // width
                                    src_px_indices = valid_indices % width

                                    # Calculate target pixel coordinates
                                    target_x = ((valid_wgs84_x -
                                                 target_bounds[0]) /
                                                (target_bounds[2] -
                                                 target_bounds[0]) *
                                                target_size[0]).astype(int)
                                    target_y = ((target_bounds[
                                                     3] - valid_wgs84_y) /
                                                (target_bounds[3] -
                                                 target_bounds[1]) *
                                                target_size[1]).astype(int)

                                    # Clamp to valid ranges
                                    valid_target = ((target_x >= 0) & (
                                                target_x < target_size[
                                            0]) &
                                                    (target_y >= 0) & (
                                                                target_y <
                                                                target_size[
                                                                    1]))

                                    if np.any(valid_target):
                                        # Copy pixel values
                                        final_src_px = src_px_indices[
                                            valid_target]
                                        final_src_py = src_py_indices[
                                            valid_target]
                                        final_tgt_x = target_x[
                                            valid_target]
                                        final_tgt_y = target_y[
                                            valid_target]

                                        for i in range(3):
                                            # Get source pixel values
                                            src_values = self.data[
                                                i, final_src_py, final_src_px]
                                            # Only copy non-zero values
                                            nonzero_mask = src_values > 0
                                            if np.any(nonzero_mask):
                                                reprojected[i, final_tgt_y[
                                                    nonzero_mask],
                                                final_tgt_x[
                                                    nonzero_mask]] = \
                                                src_values[nonzero_mask]

                            except Exception as chunk_error:
                                print(f"Error processing chunk "
                                      f"{start_idx}-{end_idx}: "
                                      f"{chunk_error}")
                                continue

                            processed_pixels += (end_idx - start_idx)
                            if processed_pixels % 50000 == 0:
                                print(f"Processed {processed_pixels}/"
                                      f"{total_pixels} pixels "
                                      f"({100 * processed_pixels / total_pixels:.1f}%)")

                        manual_nonzero = np.count_nonzero(reprojected)
                        print(f"Manual transformation produced "
                              f"{manual_nonzero} non-zero pixels")

                        # If still very sparse, try nearest neighbor interpolation
                        if manual_nonzero < target_size[0] * target_size[
                            1] * 0.01:  # Less than 1% coverage
                            print("Applying nearest neighbor "
                                  "interpolation to fill gaps...")

                            from scipy.ndimage import binary_dilation

                            for i in range(3):
                                # Create a mask of valid pixels
                                valid_mask = reprojected[i] > 0
                                if np.any(valid_mask):
                                    # Dilate the valid pixels to fill small gaps
                                    dilated_mask = binary_dilation(
                                        valid_mask, iterations=2)
                                    # Use the dilated area but keep original values where available
                                    dilated_data = np.where(
                                        dilated_mask & ~valid_mask,
                                        np.median(
                                            reprojected[i][valid_mask]),
                                        # Fill with median value
                                        reprojected[i])
                                    reprojected[i] = dilated_data

                            final_nonzero = np.count_nonzero(reprojected)
                            print(f"After interpolation: "
                                  f"{final_nonzero} non-zero pixels")

                    except Exception as manual_error:
                        print(f"Manual transformation failed: "
                              f"{manual_error}")
                        import traceback
                        traceback.print_exc()

            self.reprojected_data = reprojected
            self.reprojected_transform = target_transform

            print(f"Final reprojected data shape: {reprojected.shape}")
            print(f"Final reprojected data range: "
                  f"{np.min(reprojected)} to {np.max(reprojected)}")
            print(f"Final non-zero pixels: "
                  f"{np.count_nonzero(reprojected)}")

            # Create wx.Image
            rgb_data = np.transpose(reprojected, (1, 2, 0))
            height, width = rgb_data.shape[:2]

            if not rgb_data.flags['C_CONTIGUOUS']:
                rgb_data = np.ascontiguousarray(rgb_data)

            self.wx_image = wx.Image(width, height)
            self.wx_image.SetData(rgb_data.tobytes())

            print(f"Created wx.Image: {width}x{height}")
            return True

        except Exception as e:
            print(f"Failed to reproject GeoTIFF: {e}")
            import traceback
            traceback.print_exc()
            return False

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
        self.mode = SelectMode.NORMAL
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

        # GeoTIFF layer - ADD THIS
        self.geotiff_layer = GeoTiffLayer()

        # Geographic coordinates (center of view)
        lat, lon = get_location_with_fallback()  # user IP location
        self.geo_center_lat = lat
        self.geo_center_lon = lon
        self.geo_zoom = self.BASE_GEO_ZOOM  # Tile zoom level

        # Interaction state
        self.mouse_down = False
        self.drag_start = None
        self.drag_mode = None
        self.drag_corner_index = None
        self.selected_buildings = BuildingGroup([])
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
        size_x, size_y = self.GetSize()
        plot_x = x
        plot_y = size_y - y
        wx = (plot_x - self.pan_x) / self.zoom_level
        wy = (plot_y + self.pan_y) / self.zoom_level
        return wx, wy

    def world_to_screen(self, x: float, y: float) -> Tuple[float, float]:
        """Convert world coordinates to screen coordinates"""
        plot_x = x * self.zoom_level + self.pan_x
        plot_y = y * self.zoom_level - self.pan_y
        size_x, size_y = self.GetSize()
        sx = plot_x
        sy = size_y - plot_y
        return sx, sy

    def snap_point(self, x: float, y: float,
                   exclude: Optional[Building | BuildingGroup] = None
                   ) -> Tuple[float, float]:
        """Snap a point to nearby building features"""
        if not self.snap_enabled:
            return x, y

        # make `in` work for single buidling
        if exclude is None:
            exclude = []
        elif isinstance(exclude, Building):
            exclude = [exclude]

        snap_threshold = 15 / self.zoom_level
        best_x, best_y = x, y
        best_dist = snap_threshold

        for building in self.buildings:
            if building in exclude:
                continue

            # Snap to corners
            for cx, cy in building.get_corners():
                dist = math.sqrt((x - cx) ** 2 + (y - cy) ** 2)
                if dist < best_dist:
                    best_x, best_y = cx, cy
                    best_dist = dist

            # TODO Snap to edges
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
                        'User-Agent': f'{APP_NAME}/{APP_MINOR}'
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

    def geo_to_world(self, lat, lon):
        """Convert geographic coordinates to world coordinates - FIXED VERSION"""
        # Use proper Web Mercator projection instead of simple linear scaling
        # This matches how the map tiles are projected

        # Web Mercator transformation
        x = (lon - self.geo_center_lon) * 20037508.34 / 180.0
        lat_rad = math.radians(lat)
        y = math.log(
            math.tan((90 + lat) * math.pi / 360.0)) * 20037508.34 / math.pi

        # Center coordinates
        center_lat_rad = math.radians(self.geo_center_lat)
        center_y = math.log(math.tan((
                                                 90 + self.geo_center_lat) * math.pi / 360.0)) * 20037508.34 / math.pi

        # Relative to center
        y = y - center_y

        return x, y

    def world_to_geo(self, x, y):
        """Convert world coordinates to geographic coordinates - FIXED VERSION"""
        # Inverse Web Mercator transformation

        # Add center offset back
        center_lat_rad = math.radians(self.geo_center_lat)
        center_y = math.log(math.tan((
                                             90 + self.geo_center_lat) * math.pi / 360.0)) * 20037508.34 / math.pi
        y_abs = y + center_y

        # Convert back to lat/lon
        lon = (x * 180.0 / 20037508.34) + self.geo_center_lon
        lat = (math.atan(math.exp(
            y_abs * math.pi / 20037508.34)) * 360.0 / math.pi) - 90

        return lat, lon

    def on_paint(self, event):
        """Handle paint events"""
        dc = wx.AutoBufferedPaintDC(self)
        dc.SetBackground(wx.Brush(wx.WHITE))
        dc.Clear()

        # Draw map tiles if enabled
        if self.map_provider != MapProvider.NONE:
            self.draw_map_tiles(dc)

        # Draw GeoTIFF layer if loaded - ADD THIS
        if self.geotiff_layer.visible and self.geotiff_layer.data is not None:
            self.draw_geotiff_layer(dc)

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

        if len(self.selected_buildings) > 0:
            if len(self.selected_buildings) > 1:
                self.draw_selected_rectangle(gc)
            self.draw_selected_handles(gc)

        # Draw preview for new building
        if (self.mode in [SelectMode.ADD_BUILDING, SelectMode.ADD_ROTUNDA]
                and self.floating_rect and self.current_mouse_pos):
            if self.mode == SelectMode.ADD_BUILDING:
                self.draw_building_preview(gc, mode='corner')
            elif self.mode == SelectMode.ADD_ROTUNDA:
                self.draw_building_preview(gc, mode='center')
            else:
                pass

        # Draw selection rectangle
        if (self.mode == SelectMode.RECTANGLE_SELECT
                and self.selection_rect_start and self.current_mouse_pos):
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
                    dc.SetBrush(wx.Brush(
                        colorset.get('COL_TILE_EMPTY')))
                    dc.SetPen(
                        wx.Pen(
                            colorset.get('COL_TILE_EDGE'), 1))
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
            gc.SetPen(wx.Pen(colorset.get('COL_GRID'), 1))
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
        corners = building.get_corners()

        # Create path for rotated rectangle
        path = gc.CreatePath()
        path.MoveToPoint(*self.world_to_screen(*corners[0]))
        for corner in corners[1:]:
            path.AddLineToPoint(*self.world_to_screen(*corner))
        path.CloseSubpath()

        # Set colors based on selection
        if building in self.selected_buildings:
            fill_color = colorset.get('COL_SEL_BLDG_IN')
            border_color = colorset.get('COL_SEL_BLDG_OUT')
        else:
            fill_color = colorset.get('COL_BLDG_IN')
            border_color = colorset.get('COL_BLDG_OUT')

        gc.SetBrush(wx.Brush(fill_color))
        gc.SetPen(wx.Pen(border_color, 2))
        gc.DrawPath(path)

        # Draw height text at center
        cx = sum(c[0] for c in corners) / len(corners)
        cy = sum(c[1] for c in corners) / len(corners)
        scx, scy = self.world_to_screen(cx, cy)

        gc.SetFont(wx.Font(10, wx.FONTFAMILY_DEFAULT, wx.FONTSTYLE_NORMAL,
                           wx.FONTWEIGHT_NORMAL),
                   colorset.get('COL_BLDG_LBL'))
        text = f"{building.storeys}F"
        tw, th = gc.GetTextExtent(text)
        gc.DrawText(text, scx - tw / 2, scy - th / 2)

    def draw_selected_rectangle(self, gc):
        """Draw preview of building being created with rotation support"""

        # Draw rectangle
        corners = self.selected_buildings.get_corners()
        if len(corners) == 0:
            return
        path = gc.CreatePath()
        path.MoveToPoint(self.world_to_screen(*corners[0]))
        for xx, yy in corners[1:]:
            path.AddLineToPoint(self.world_to_screen(xx, yy))
        path.CloseSubpath()

        gc.SetBrush(wx.NullBrush)
        gc.SetPen(wx.Pen(colorset.get('COL_SEL_BLDG_OUT'), 1, wx.PENSTYLE_DOT))
        gc.DrawPath(path)

    def draw_selected_handles(self, gc):
        """ Draw corner handles of selection"""
        corners = self.selected_buildings.get_corners()

        # Check if Ctrl is pressed (use rotation mode)
        ctrl_pressed = wx.GetKeyState(wx.WXK_CONTROL)

        for i, (cx, cy) in enumerate(corners):
            sx, sy = self.world_to_screen(cx, cy)

            if i == 0:
                gc.SetBrush(
                    wx.Brush(colorset.get('COL_HANDLE_OUT')))
            else:
                gc.SetBrush(
                    wx.Brush(colorset.get('COL_HANDLE_IN')))
            gc.SetPen(
                wx.Pen(colorset.get('COL_HANDLE_OUT'), 2))
            if ctrl_pressed:
                # Draw circles in rotation mode
                gc.DrawEllipse(sx - 5, sy - 5, 10, 10)
            else:
                # Draw squares in normal mode
                gc.DrawRectangle(sx - 4, sy - 4, 8, 8)

    def draw_building_preview(self, gc, mode:str='corner'):
        """Draw preview of building being created with rotation support"""
        x1, y1 = self.floating_rect.anchor
        x2, y2 = self.screen_to_world(*self.current_mouse_pos)
        dist = math.sqrt((x2 - x1) ** 2 + (y2 - y1) ** 2)
        angle = math.atan2(y2 - y1, x2 - x1)

        ctrl_pressed = wx.GetKeyState(wx.WXK_CONTROL)

        if mode == 'corner':
            if ctrl_pressed and self.floating_rect:
                # # Create a rectangle with constant aspect ratio
                # old_dist = math.sqrt(self.floating_rect.b**2. +
                #                      self.floating_rect.a**2.)
                new_a = self.floating_rect.a
                new_b = self.floating_rect.b
                new_r = angle - math.atan2(new_b, new_a)

            else:
                # Scaling mode during creation
                dx = x2 - x1
                dy = y2 - y1
                new_r = self.floating_rect.r
                new_a = + math.cos(new_r) * dx + math.sin(new_r) * dy
                new_b = - math.sin(new_r) * dx + math.cos(new_r) * dy

            if new_a <= 0 or new_b <= 0:
                # do no accept negtaive values, do not draw
                return

            corners = [
                (0., 0.),
                (new_a, 0.),
                (new_a, new_b),
                (0., new_b)
            ]


        elif mode == 'center':
            new_r = 0.
            new_a = 0.
            new_b = math.sqrt((x2 - x1) ** 2 + (y2 - y1)**2)

            corners = [
                (-new_b, -new_b),
                (new_b, -new_b),
                (new_b, new_b),
                (-new_b, new_b)
            ]

            # new b cannot be < 0

        else:
            print(f"Unknown preview mode {mode}")

        # Draw rotated preview
        path = gc.CreatePath()
        path_start = True
        for ca, cb in corners:
            x = x1 + math.cos(new_r) * ca - math.sin(new_r) * cb
            y = y1 + math.sin(new_r) * ca + math.cos(new_r) * cb
            sx, sy = self.world_to_screen(x, y)
            if path_start:
                path.MoveToPoint(sx, sy)
                path_start = False
            else:
                path.AddLineToPoint(sx, sy)
        path.CloseSubpath()

        gc.SetBrush(wx.Brush(colorset.get('COL_FLOAT_IN')))
        gc.SetPen(wx.Pen(colorset.get('COL_FLOAT_OUT'),
                         2, wx.PENSTYLE_DOT))
        gc.DrawPath(path)

        self.floating_rect.a = new_a
        self.floating_rect.b = new_b
        self.floating_rect.r = new_r

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


    def test_simple_overlay(self, dc):
        """Test overlay with a simple colored rectangle"""
        if self.geotiff_layer.data is None:
            return

        try:
            width, height = self.GetSize()

            # Create a simple test image
            test_image = wx.Image(100, 100)
            test_image.SetRGB(wx.Rect(0, 0, 100, 100), 255, 0, 0)  # Red rectangle

            bitmap = wx.Bitmap(test_image)
            dc.DrawBitmap(bitmap, 50, 50)  # Draw at fixed position

            print("Drew test red rectangle")

        except Exception as e:
            print(f"Error in test overlay: {e}")

    def draw_geotiff_layer(self, dc):
        """Draw the GeoTIFF overlay - FIXED VERSION"""
        if self.geotiff_layer.data is None:
            return

        try:
            # Use the existing tile coordinate system for consistency
            width, height = self.GetSize()

            # Get the bounds from the tile system (same as used for map tiles)
            center_tile_x, center_tile_y = self.lat_lon_to_tile(
                self.geo_center_lat, self.geo_center_lon, self.geo_zoom
            )

            # Calculate view bounds in tile coordinates
            tile_size = self.BASE_TILE_SIZE * self.zoom_level * 2 ** 16 / (
                        2 ** self.geo_zoom)
            center_x, center_y = self.world_to_screen(0, 0)

            # Convert screen corners to tile coordinates
            nw_tile_x = center_tile_x + (0 - center_x) / tile_size
            nw_tile_y = center_tile_y + (0 - center_y) / tile_size
            se_tile_x = center_tile_x + (width - center_x) / tile_size
            se_tile_y = center_tile_y + (height - center_y) / tile_size

            # Convert tile coordinates to lat/lon
            nw_lat, nw_lon = self.tile_to_lat_lon(nw_tile_x, nw_tile_y,
                                                  self.geo_zoom)
            se_lat, se_lon = self.tile_to_lat_lon(se_tile_x, se_tile_y,
                                                  self.geo_zoom)

            # View bounds (west, south, east, north)
            view_bounds = (nw_lon, se_lat, se_lon, nw_lat)

            print(f"View bounds (tile-based): {view_bounds}")
            print(f"GeoTIFF bounds: {self.geotiff_layer.bounds}")

            # Check intersection
            geotiff_bounds = self.geotiff_layer.bounds
            if not (view_bounds[2] >= geotiff_bounds[0] and
                    view_bounds[0] <= geotiff_bounds[2] and
                    view_bounds[3] >= geotiff_bounds[1] and
                    view_bounds[1] <= geotiff_bounds[3]):
                print("No intersection between view and GeoTIFF bounds")
                return

            # Calculate intersection bounds
            intersect_bounds = (
                max(view_bounds[0], geotiff_bounds[0]),  # west
                max(view_bounds[1], geotiff_bounds[1]),  # south
                min(view_bounds[2], geotiff_bounds[2]),  # east
                min(view_bounds[3], geotiff_bounds[3])  # north
            )

            print(f"Intersection bounds: {intersect_bounds}")

            # Target size
            target_width = min(width, 1024)
            target_height = min(height, 1024)


            # Reproject
            if self.geotiff_layer.reproject_for_display(intersect_bounds,
                                                        (target_width,
                                                         target_height)):
                if self.geotiff_layer.wx_image and self.geotiff_layer.wx_image.IsOk():
                    print("Drawing GeoTIFF image...")

                    # Convert intersection bounds to tile coordinates for screen positioning
                    nw_tile_x_img, nw_tile_y_img = self.lat_lon_to_tile(
                        intersect_bounds[3], intersect_bounds[0],
                        self.geo_zoom)  # north, west
                    se_tile_x_img, se_tile_y_img = self.lat_lon_to_tile(
                        intersect_bounds[1], intersect_bounds[2],
                        self.geo_zoom)  # south, east

                    # Convert to screen coordinates
                    nw_screen_x = center_x + (
                                nw_tile_x_img - center_tile_x) * tile_size
                    nw_screen_y = center_y + (
                                nw_tile_y_img - center_tile_y) * tile_size
                    se_screen_x = center_x + (
                                se_tile_x_img - center_tile_x) * tile_size
                    se_screen_y = center_y + (
                                se_tile_y_img - center_tile_y) * tile_size

                    print(f"Screen positions: "
                          f"NW=({nw_screen_x}, {nw_screen_y}), "
                          f"SE=({se_screen_x}, {se_screen_y})")

                    # Calculate size
                    img_width = abs(se_screen_x - nw_screen_x)
                    img_height = abs(se_screen_y - nw_screen_y)

                    print(f"Image screen size: {img_width} x {img_height}")

                    if img_width > 1 and img_height > 1:
                        # Scale the image
                        scaled_image = self.geotiff_layer.wx_image.Scale(
                            int(img_width), int(img_height),
                            wx.IMAGE_QUALITY_HIGH)

                        # Apply opacity
                        if self.geotiff_layer.opacity < 1.0:
                            alpha_value = int(
                                255 * self.geotiff_layer.opacity)
                            if not scaled_image.HasAlpha():
                                scaled_image.InitAlpha()
                            width_img = scaled_image.GetWidth()
                            height_img = scaled_image.GetHeight()
                            alpha_data = bytes(
                                [alpha_value] * (width_img * height_img))
                            scaled_image.SetAlpha(alpha_data)

                        # Draw
                        bitmap = wx.Bitmap(scaled_image)
                        draw_x = int(min(nw_screen_x, se_screen_x))
                        draw_y = int(min(nw_screen_y, se_screen_y))

                        print(f"Drawing at position: ({draw_x}, {draw_y})")
                        dc.DrawBitmap(bitmap, draw_x, draw_y)

                    else:
                        print(
                            f"Image too small to draw: {img_width} x {img_height}")
                else:
                    print("wx.Image is not valid")
            else:
                print("Reprojection failed")

        except Exception as e:
            print(f"Error drawing GeoTIFF: {e}")
            import traceback
            traceback.print_exc()

    def load_geotiff(self, filepath):
        """Load a GeoTIFF file"""
        try:
            success = self.geotiff_layer.load_file(filepath)
            if success:
                self.Refresh()
                return True
        except Exception as e:
            wx.MessageBox(f"Failed to load GeoTIFF: {str(e)}", "Error",
                          wx.OK | wx.ICON_ERROR)
        return False

    def set_geotiff_opacity(self, opacity):
        """Set GeoTIFF layer opacity (0.0 to 1.0)"""
        self.geotiff_layer.opacity = max(0.0, min(1.0, opacity))
        self.Refresh()

    def toggle_geotiff_visibility(self):
        """Toggle GeoTIFF layer visibility"""
        self.geotiff_layer.visible = not self.geotiff_layer.visible
        self.Refresh()
        return self.geotiff_layer.visible

    def on_mouse_down(self, event):
        """Handle mouse down events with rotation support"""
        self.mouse_down = True
        self.drag_start = event.GetPosition()
        wx, wy = self.screen_to_world(event.GetX(), event.GetY())
        ctrl_pressed = event.ControlDown()

        if self.mode in [SelectMode.ADD_BUILDING, SelectMode.ADD_ROTUNDA]:
            if self.floating_rect is None:
                # 1st click defines first corner (lower left)
                self.floating_rect = Preview(
                    anchor=self.snap_point(wx, wy),
                    a=0., b=0., r=0.)
                self.statusbar.SetStatusText(
                    "Move to draw, press Ctrl to rotate, click to finish")
            else:
                # 2nd click defines 2n corner (upper right) and adds bldg.
                x1, y1 = self.floating_rect.anchor
                building = Building(
                    id=str(uuid.uuid4()),
                    x1=x1,
                    y1=y1,
                    a=self.floating_rect.a,
                    b=self.floating_rect.b,
                    height=self.storey_height * 3,
                    storeys=3,
                    rotation=self.floating_rect.r
                )

                self.buildings.append(building)
                self.floating_rect = None
                self.mode = SelectMode.NORMAL
                self.statusbar.SetStatusText(
                    f"Added building #{len(self.buildings)}")
                self.Refresh()

        elif self.mode == SelectMode.NORMAL:
            if event.ShiftDown():
                # shift-click on map: start spanning rectangle selection
                self.mode = SelectMode.RECTANGLE_SELECT
                self.selection_rect_start = event.GetPosition()
            else:
                # check for corner drag
                corner_idx = self.selected_buildings.get_corner_index(
                    wx, wy, 10 / self.zoom_level)
                if corner_idx is not None:
                    if ctrl_pressed:
                        # Rotation mode
                        self.drag_corner_index = corner_idx
                        self.drag_mode = 'rotate'
                        return
                    else:
                        # Normal scaling mode
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
                    # a building was clicked
                    if ctrl_pressed:
                        # Ctrl held down
                        if clicked_building in self.selected_buildings:
                            # remove building from selecetion
                            self.selected_buildings.remove(clicked_building)
                        else:
                            # add unselected building to selection
                            self.selected_buildings.add(clicked_building)
                    else:
                        # Not Key held down
                        if clicked_building in self.selected_buildings:
                            # do nothing
                            pass
                        else:
                            # select solely this building
                            self.selected_buildings = BuildingGroup([clicked_building])
                    self.drag_mode = 'translate'
                else:
                    # no building was clicked
                    # unselect all
                    self.selected_buildings = BuildingGroup([])

                self.Refresh()

    def on_mouse_up(self, event):
        """Handle mouse up events"""
        self.mouse_down = False

        if self.mode == SelectMode.RECTANGLE_SELECT:
            x1, y1 = self.screen_to_world(*self.selection_rect_start)
            x2, y2 = self.screen_to_world(event.GetX(), event.GetY())

            rx1, rx2 = min(x1, x2), max(x1, x2)
            ry1, ry2 = min(y1, y2), max(y1, y2)

            for building in self.buildings:
                le, lo, ri, up = building.get_llur()
                if (le >= rx1 and ri <= rx2 and
                        lo >= ry1 and up <= ry2):
                    self.selected_buildings.add(building)

            self.mode = SelectMode.NORMAL
            self.selection_rect_start = None
            self.Refresh()

        self.drag_corner_index = None
        self.drag_mode = None
        self.drag_start = None

    def on_mouse_motion(self, event):
        """Handle mouse motion events with rotation support"""
        self.current_mouse_pos = event.GetPosition()
        wx, wy = self.screen_to_world(event.GetX(), event.GetY())

        if self.mouse_down and self.drag_start:
            # mouse id being dragged
            snapped_x, snapped_y = self.snap_point(
                wx, wy, exclude=self.selected_buildings)

            if self.drag_mode == 'scale':
                self.selected_buildings.scale_to_corner(
                    self.drag_corner_index, snapped_x, snapped_y)
            elif self.drag_mode == 'rotate':
                self.selected_buildings.rotate_to_corner(
                    self.drag_corner_index, snapped_x, snapped_y)
            elif self.drag_mode == 'translate':
                # Moving building
                start_wx, start_wy = self.screen_to_world(*self.drag_start)
                dx = wx - start_wx
                dy = wy - start_wy

                new_x1 = self.selected_buildings.x1 + dx
                new_y1 = self.selected_buildings.y1 + dy
                snapped_x, snapped_y = self.snap_point(
                    new_x1, new_y1, exclude=self.selected_buildings)

                actual_dx = snapped_x - self.selected_buildings.x1
                actual_dy = snapped_y - self.selected_buildings.y1

                self.selected_buildings.shift(actual_dx, actual_dy)
                self.drag_start = event.GetPosition()
            elif not event.ShiftDown():
                # Panning
                dx = event.GetX() - self.drag_start[0]
                dy = event.GetY() - self.drag_start[1]
                self.pan_x += dx
                self.pan_y += dy
                self.drag_start = event.GetPosition()
            self.Refresh()

        # Update preview
        if (self.mode in [SelectMode.ADD_BUILDING, SelectMode.ADD_ROTUNDA]
                and self.floating_rect):
            self.Refresh()

        if self.mode == SelectMode.RECTANGLE_SELECT:
            self.Refresh()

        # Update corner appearance when Ctrl is pressed/released
        if len(self.selected_buildings) > 0:
            self.Refresh()

    def on_mouse_wheel(self, event):
        """Handle mouse wheel events for zooming"""
        rotation = event.GetWheelRotation()
        mx, my = event.GetPosition()

        zoom_factor = 1.1 if rotation > 0 else 0.9
        self.zoom_view(zoom_factor, mx, my)

    def on_size(self, event):
        """Handle resize events"""
        self.Refresh()
        event.Skip()

    def set_building_stories(self, stories: int):
        """Set stories for selected buildings"""
        for building in self.selected_buildings:
            building.storeys = stories
            building.height = stories * self.storey_height
        self.Refresh()

    def delete_selected_buildings(self):
        """Delete selected buildings"""
        for b in self.selected_buildings.buildings.copy():
            self.selected_buildings.remove(b)
            self.buildings = [x for x in self.buildings if x != b]
        self.Refresh()

    def zoom_view(self, factor, apex_x=None, apex_y=None):

        if apex_x is None or apex_y is None:
            width, height = self.GetSize()
            apex_x = width / 2.
            apex_y = height / 2.

        new_zoom = self.zoom_level * factor
        new_zoom = max(0.1, min(10.0, new_zoom))

        wx, wy = self.screen_to_world(apex_x, apex_y)
        self.zoom_level = new_zoom
        new_mx, new_my = self.world_to_screen(wx, wy)

        self.pan_x += apex_x - new_mx
        self.pan_y += apex_y - new_my

        self.Refresh()

    def zoom_to_buildings(self):
        """Zoom to fit all buildings"""
        if not self.buildings:
            return

        xw_min = min(b.get_llur()[0] for b in self.buildings)
        yw_min = min(b.get_llur()[1] for b in self.buildings)
        xw_max = max(b.get_llur()[2] for b in self.buildings)
        yw_max = max(b.get_llur()[3] for b in self.buildings)

        width, height = self.GetSize()
        margin = 50

        xs_center = width / 2
        ys_center = height / 2

        zoom_x = (width - 2 * margin) / (
                    xw_max - xw_min) if xw_max > xw_min else 1.0
        zoom_y = (height - 2 * margin) / (
                    yw_max - yw_min) if yw_max > yw_min else 1.0

        self.zoom_level = min(zoom_x, zoom_y, 5.0)

        xw_focus = (xw_min + xw_max) / 2
        yw_focus = (yw_min + yw_max) / 2

        xs_focus, ys_focus  = self.world_to_screen(xw_focus, yw_focus)

        dxs = xs_center - xs_focus
        dys = ys_center - ys_focus

        # self.pan_x = width / 2 - xw_focus * self.zoom_level
        # self.pan_y = height / 2 - yw_focus * self.zoom_level
        self.pan_x += dxs
        self.pan_y += dys

        self.Refresh()

# =========================================================================

class MainFrame(wx.Frame):
    """Main application frame"""

    def __init__(self):
        super().__init__(None, title=f"{APP_NAME} {APP_VERSION}",
                         size=(1200, 800))

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
        import_austal = file_menu.Append(
            wx.ID_ANY, "&Import from AUSTAL",
            "Import Buildings from austal.txt")
        export_austal = file_menu.Append(
            wx.ID_ANY, "&Export to AUSTAL",
            "Export Buildings to austal.txt")
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

        if GEOTIFF_SUPPORT:
            edit_menu.AppendSeparator()
            geotiff_item = edit_menu.Append(wx.ID_ANY,
                                            "Load &GeoTIFF...",
                                            "Load a GeoTIFF overlay")
            geotiff_set_item = edit_menu.Append(wx.ID_ANY,
                                                "GeoTIFF &Settings",
                                                "Configure GeoTIFF overlay")
        if OPENGL_SUPPORT:
            edit_menu.AppendSeparator()
            view_3d_item = edit_menu.Append(wx.ID_ANY,
                                            "Show &3D View\tF3",
                                            "Show buildings in 3D view")
        edit_menu.AppendSeparator()
        storey_item = edit_menu.Append(wx.ID_ANY,
                                       "Set Storey &Height",
                                       "Set the height per storey")

        # Add color settings menu item
        edit_menu.AppendSeparator()
        color_settings_item = edit_menu.Append(wx.ID_ANY,
                                               "&Color Settings...",
                                               "Configure application colors")


        # Help menu
        help_menu = wx.Menu()
        help_menu.Append(wx.ID_ABOUT,
                         "&About",
                         "About this application")

        menubar.Append(file_menu, "&File")
        menubar.Append(edit_menu, "&Edit")
        menubar.Append(help_menu, "&Help")

        self.SetMenuBar(menubar)

        # Bind menu events
        self.Bind(wx.EVT_MENU, self.on_new, id=wx.ID_NEW)
        self.Bind(wx.EVT_MENU, self.on_open, id=wx.ID_OPEN)
        self.Bind(wx.EVT_MENU, self.on_save, id=wx.ID_SAVE)
        self.Bind(wx.EVT_MENU, self.on_save_as, id=wx.ID_SAVEAS)
        self.Bind(wx.EVT_MENU, self.on_open_austal,
                  id=import_austal.GetId())
        self.Bind(wx.EVT_MENU, self.on_save_austal,
                  id=export_austal.GetId())
        self.Bind(wx.EVT_MENU, self.on_exit, id=wx.ID_EXIT)
        self.Bind(wx.EVT_MENU, self.on_about, id=wx.ID_ABOUT)
        self.Bind(wx.EVT_MENU, self.on_color_settings,
                  id=color_settings_item.GetId())
        # optionals
        if GEOTIFF_SUPPORT:
            self.Bind(wx.EVT_MENU, self.on_load_geotiff,
                      id=geotiff_item.GetId())

        # Bind edit menu events
        self.Bind(wx.EVT_MENU, self.on_select_basemap,
                  id=basemap_item.GetId())
        self.Bind(wx.EVT_MENU, self.on_zoom_to_buildings,
                  id=zoom_item.GetId())
        self.Bind(wx.EVT_MENU, self.on_set_storey_height,
                  id=storey_item.GetId())
        # optionals
        if GEOTIFF_SUPPORT:
            self.Bind(wx.EVT_MENU, self.on_geotiff_settings,
                      id=geotiff_set_item.GetId())
        if OPENGL_SUPPORT:
            self.Bind(wx.EVT_MENU, self.on_show_3d_view,
                      id=view_3d_item.GetId())

    def create_toolbar(self):
        """Create the toolbar"""
        toolbar = self.CreateToolBar(wx.TB_HORIZONTAL | wx.TB_FLAT)

        # Add Building button
        self.add_building_btn = wx.Button(toolbar,
                                          label="Add Block Building")
        self.add_building_btn.Bind(wx.EVT_BUTTON, self.on_add_building)
        toolbar.AddControl(self.add_building_btn)

        self.add_rotunda_btn = wx.Button(toolbar,
                                          label="Add Round Building")
        self.add_rotunda_btn.Bind(wx.EVT_BUTTON, self.on_add_rotunda)
        toolbar.AddControl(self.add_rotunda_btn)

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
        # zoom conrol
        elif event.ControlDown() and key in [ord('0'), wx.WXK_NUMPAD0]:
            # Check for Ctrl+0
            self.on_zoom_to_buildings(None)
        elif event.ControlDown() and key in [ord('+'), wx.WXK_NUMPAD_ADD]:
            # Handle either Ctrl++
            self.on_zoom_in(None)
        elif event.ControlDown() and key in [ord('-'), wx.WXK_NUMPAD_SUBTRACT]:
            # Handle either Ctrl+-
            self.on_zoom_out(None)
        # file control
        elif key == wx.WXK_CONTROL_O:
            self.on_open(None)
        elif key == wx.WXK_CONTROL_S:
            self.on_save()

        elif key == wx.WXK_DELETE:
            self.on_delete(None)
        elif key == wx.WXK_F3:
            self.on_show_3d_view(None)
        else:
            event.Skip()

    def on_add_building(self, event):
        """Switch to add building mode"""
        self.canvas.mode = SelectMode.ADD_BUILDING
        self.canvas.floating_rect = None
        self.SetStatusText("Click to place first corner of building")

    def on_add_rotunda(self, event):
        """Switch to add building mode"""
        self.canvas.mode = SelectMode.ADD_ROTUNDA
        self.canvas.floating_rect = None
        self.SetStatusText("Click to place first center of building")

    def on_toggle_snap(self, event):
        """Toggle snapping"""
        self.canvas.snap_enabled = self.snap_btn.GetValue()
        self.snap_btn.SetLabel(
            f"Snap: {'ON' if self.canvas.snap_enabled else 'OFF'}")

    def on_set_height(self, event):
        """Open height setting dialog"""
        if len(self.canvas.selected_buildings) > 0:
            wx.MessageBox("Please select at least one building",
                          "No Selection",
                          wx.OK | wx.ICON_WARNING)
            return

        # Get current values from first selected building
        stories = self.canvas.selected_buildings[0].storeys
        height = self.canvas.selected_buildings[0].height

        dialog = HeightDialog(self, stories, height,
                              self.canvas.storey_height)
        if dialog.ShowModal() == wx.ID_OK:
            new_stories, new_height = dialog.get_values()
            for building in self.canvas.selected_buildings:
                building.storeys = new_stories
                building.height = new_height
            self.canvas.Refresh()
            self.SetStatusText(
                f"Set height to {new_stories} stories ({new_height:.1f}m)")
        dialog.Destroy()

    def on_delete(self, event):
        """Delete selected buildings"""

        result = wx.MessageBox(
            f"Are you sure you want to delete "
            f"{len(self.canvas.selected_buildings)} building(s)?",
            "Confirm Delete",
            wx.YES_NO | wx.ICON_QUESTION
        )

        if result == wx.YES:
            self.canvas.delete_selected_buildings()
            self.SetStatusText(f"Deleted "
            f"{len(self.canvas.selected_buildings)} building(s).")

    def on_zoom_in(self, event):
        """Zoom in"""
        factor = (100. + float(settings.get('ZOOM_STEP_PERCENT'))) / 100.
        return self.canvas.zoom_view(factor)

    def on_zoom_out(self, event):
        """Zoom out"""
        factor = 100. / (100. + float(settings.get('ZOOM_STEP_PERCENT')))
        return self.canvas.zoom_view(factor)

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

    def on_color_settings(self, event):
        """Open color settings dialog"""
        dialog = ColorSettingsDialog(self, colorset)
        dialog.ShowModal()
        dialog.Destroy()

        # Refresh the canvas to show color changes
        self.canvas.Refresh()


    def on_show_3d_view(self, event):
        """Show 3D view of buildings"""
        if not OPENGL_SUPPORT:
            wx.MessageBox("3D view requires OpenGL support.\n\n"
                         "Please install PyOpenGL:\n"
                         "pip install PyOpenGL PyOpenGL_accelerate",
                         "OpenGL Missing",
                         wx.OK | wx.ICON_WARNING)
            return

        if not self.canvas.buildings:
            wx.MessageBox("No buildings to display in 3D view.", "No Buildings",
                         wx.OK | wx.ICON_INFORMATION)
            return

        # Create and show 3D viewer
        viewer = Building3DViewer(self, self.canvas.buildings, self.canvas.selected_buildings)
        viewer.ShowModal()
        viewer.Destroy()


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
        self.SetTitle(f"{APP_NAME} - New Project")
        self.SetStatusText("New project created")

    def on_open(self, event):
        """Open a CityJSON file"""
        dialog = wx.FileDialog(
            self,
            "Open CitySketch project",
            wildcard=f"CitySketch files (*{FEXT})|*{FEXT}|All files (*.*)|*.*",
            style=wx.FD_OPEN | wx.FD_FILE_MUST_EXIST
        )

        if dialog.ShowModal() == wx.ID_OK:
            filepath = dialog.GetPath()
            self.load_project(filepath)
        dialog.Destroy()

    def on_save(self, event):
        """Save the current project"""
        if self.current_file:
            self.save_project(self.current_file)
        else:
            self.on_save_as(event)

    def on_open_austal(self, event):
        """Open a CityJSON file"""
        dialog = wx.FileDialog(
            self,
            "Open AUSTAL settings file",
            defaultFile="austal.txt",
            wildcard=f"AUSTAL files (austal.txt)|austal.txt",
            style=wx.FD_OPEN | wx.FD_FILE_MUST_EXIST
        )

        if dialog.ShowModal() == wx.ID_OK:
            filepath = dialog.GetPath()
            self.load_austal(filepath)
        dialog.Destroy()

    def on_save_austal(self, event):
        """Save with a new filename"""
        dialog = wx.FileDialog(
            self,
            "Export to AUSTAL settings file",
            defaultFile="austal.txt",
            wildcard=f"AUSTAL files (austal.txt)|austal.txt",
            style=wx.FD_SAVE | wx.FD_OVERWRITE_PROMPT
        )

        if dialog.ShowModal() == wx.ID_OK:
            filepath = dialog.GetPath()
            self.save_austal(filepath)
        dialog.Destroy()

    def on_open_cityjson(self, event):
        """Open a CityJSON file"""
        dialog = wx.FileDialog(
            self,
            "Open CityJSON file",
            wildcard=f"CityJSON files (*{FEXT})|*{FEXT}"
                     f"|All files (*.*)|*.*",
            style=wx.FD_OPEN | wx.FD_FILE_MUST_EXIST
        )

        if dialog.ShowModal() == wx.ID_OK:
            filepath = dialog.GetPath()
            self.load_cityjson(filepath)
        dialog.Destroy()

    def on_save_cityjson(self, event):
        """Save the current project"""
        if self.current_file:
            self.save_cityjson(self.current_file)
        else:
            self.on_save_as(event)

    def on_save_as(self, event):
        """Save with a new filename"""
        dialog = wx.FileDialog(
            self,
            "Save CitySketch file",
            wildcard=f"CitySketch files (*{FEXT})|*{FEXT}",
            style=wx.FD_SAVE | wx.FD_OVERWRITE_PROMPT
        )

        if dialog.ShowModal() == wx.ID_OK:
            filepath = dialog.GetPath()
            if not filepath.endswith(FEXT):
                filepath += FEXT
            self.save_project(filepath)
        dialog.Destroy()

    def load_project(self, filepath):
        """Load a CityJSON file"""
        try:
            with open(filepath, 'r') as f:
                data = json.load(f)

            if data.get('type') != 'CitySketch':
                wx.MessageBox("Not a valid CitySketch file", "Error",
                              wx.OK | wx.ICON_ERROR)
                return

            # Clear current buildings
            self.canvas.buildings.clear()

            # Load Buildings
            buildings_data = data.get('buildings', [])
            if buildings_data:
                batts = Building.__annotations__
                for bldg in buildings_data:
                    bs = [v(bldg[k]) for k,v in batts.items()]
                    self.canvas.buildings.append(Building(*bs))

            # Load editor settings
            editor_settings = data.get('editor_settings', {})
            if editor_settings:
                # Restore map settings
                map_provider_str = editor_settings.get('map_provider',
                                                        'None')
                for provider in MapProvider:
                    if provider.value == map_provider_str:
                        self.canvas.map_provider = provider
                        break

                self.canvas.geo_center_lat = float(editor_settings.get(
                    'geo_center_lat', 49.4875))
                self.canvas.geo_center_lon = float(editor_settings.get(
                    'geo_center_lon', 8.4660))
                self.canvas.geo_zoom = int(editor_settings.get('geo_zoom', 16))
                self.canvas.storey_height = float(editor_settings.get(
                    'storey_height', 3.3))

                # Clear map tiles to reload with new settings
                self.canvas.map_tiles.clear()

            color_settings = data.get('color_settings', None)
            if color_settings:
                colorset.from_dict(color_settings)

            general_settings = data.get('general_settings', None)
            if general_settings:
                settings.from_dict(general_settings)

            self.current_file = filepath
            self.modified = False
            self.SetTitle(f"{APP_NAME} - {filepath}")
            self.canvas.zoom_to_buildings()
            self.SetStatusText(
                f"Loaded {len(self.canvas.buildings)} buildings")

        except Exception as e:
            wx.MessageBox(f"Error loading file: {str(e)}", "Error",
                          wx.OK | wx.ICON_ERROR)

    def save_project(self, filepath):
        """Save to a CityJSON file"""
        try:
            # Create structure with metadata
            data = {
                "type": "CitySketch",
                "version": "1.0",
            }

            buildings_data = []
            for bldg in self.canvas.buildings:
                batt = {}
                for att in list(bldg.__dict__.keys()):
                    batt[att] = str(bldg.__getattribute__(att))
                buildings_data.append(batt)
            data['buildings'] = buildings_data

            editor_settings = {
                "map_provider": self.canvas.map_provider.value,
                "geo_center_lat": self.canvas.geo_center_lat,
                "geo_center_lon": self.canvas.geo_center_lon,
                "geo_zoom": self.canvas.geo_zoom,
                "storey_height": self.canvas.storey_height
            }
            data["editor_settings"] = editor_settings

            color_settings = colorset.to_dict()
            data['color_settings'] = color_settings

            general_settings = settings.to_dict()
            data['general_settings'] = general_settings

            # Save to file
            with open(filepath, 'w') as f:
                json.dump(data, f, indent=2)

            self.current_file = filepath
            self.modified = False
            self.SetTitle(f"{APP_NAME} - {filepath}")
            self.SetStatusText(
                f"Saved {len(self.canvas.buildings)} buildings to {filepath}")

        except Exception as e:
            wx.MessageBox(f"Error saving file: {str(e)}", "Error",
                          wx.OK | wx.ICON_ERROR)


    def load_austal(self, filepath):
        """Load a CityJSON file"""
        try:
            lat, lon, buildings = load_from_austaltxt(filepath)

            self.canvas.geo_center_lat = lat
            self.canvas.geo_center_lon = lon
            self.canvas.buildings.clear()
            self.canvas.buildings = buildings
            self.modified = False
            self.SetTitle(f"{APP_NAME} - {filepath}")
            self.canvas.zoom_to_buildings()
            self.SetStatusText(
                f"Loaded {len(self.canvas.buildings)} buildings")

        except Exception as e:
            wx.MessageBox(f"Error loading file: {str(e)}", "Error",
                          wx.OK | wx.ICON_ERROR)


    def save_austal(self, filepath):
        """Save to a CityJSON file"""
        try:
            lat = self.canvas.geo_center_lat
            lon = self.canvas.geo_center_lon
            buildings = self.canvas.buildings

            save_to_austaltxt(filepath, lat, lon, buildings)
            self.modified = False
            self.SetTitle(f"{APP_NAME} - {filepath}")
            self.SetStatusText(
                f"Saved {len(self.canvas.buildings)} buildings to {filepath}")

        except Exception as e:
            wx.MessageBox(f"Error saving file: {str(e)}", "Error",
                          wx.OK | wx.ICON_ERROR)


    def on_load_geotiff(self, event):
        """Load a GeoTIFF file"""
        if not GEOTIFF_SUPPORT:
            wx.MessageBox("GeoTIFF support not available.\n\n"
                          "Please install the following packages:\n"
                          "- gdal (conda install gdal or pip install gdal)\n"
                          "- rasterio (pip install rasterio)",
                          "GeoTIFF Support Missing",
                          wx.OK | wx.ICON_WARNING)
            return

        dialog = wx.FileDialog(
            self,
            "Load GeoTIFF file",
            wildcard="GeoTIFF files (*.tif;*.tiff)|*.tif;*.tiff|All files (*.*)|*.*",
            style=wx.FD_OPEN | wx.FD_FILE_MUST_EXIST
        )

        if dialog.ShowModal() == wx.ID_OK:
            filepath = dialog.GetPath()

            # Show progress dialog for large files
            progress = wx.ProgressDialog("Loading GeoTIFF",
                                         "Loading and processing GeoTIFF file...",
                                         maximum=100, parent=self,
                                         style=wx.PD_AUTO_HIDE | wx.PD_APP_MODAL)
            progress.Pulse()

            try:
                success = self.canvas.load_geotiff(filepath)
                progress.Destroy()

                if success:
                    self.SetStatusText(
                        f"Loaded GeoTIFF: {os.path.basename(filepath)}")

                    # Optionally show settings dialog
                    result = wx.MessageBox(
                        "GeoTIFF loaded successfully!\n\n"
                        "Would you like to adjust the overlay settings?",
                        "GeoTIFF Loaded",
                        wx.YES_NO | wx.ICON_QUESTION
                    )
                    if result == wx.YES:
                        self.on_geotiff_settings(None)
                else:
                    self.SetStatusText("Failed to load GeoTIFF")

            except Exception as e:
                progress.Destroy()
                wx.MessageBox(f"Error loading GeoTIFF: {str(e)}", "Error",
                              wx.OK | wx.ICON_ERROR)

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
            editor_settings = metadata.get('cityjson_editor_settings',
                                            {})
            if editor_settings:
                # Restore map settings
                map_provider_str = editor_settings.get('map_provider',
                                                        'None')
                for provider in MapProvider:
                    if provider.value == map_provider_str:
                        self.canvas.map_provider = provider
                        break

                self.canvas.geo_center_lat = editor_settings.get(
                    'geo_center_lat', 49.4875)
                self.canvas.geo_center_lon = editor_settings.get(
                    'geo_center_lon', 8.4660)
                self.canvas.geo_zoom = editor_settings.get('geo_zoom', 16)
                self.canvas.storey_height = editor_settings.get(
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
            self.SetTitle(f"{APP_NAME} - {filepath}")
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
                    "cityjson_editor_settings": {
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
            self.SetTitle(f"{APP_NAME} - {filepath}")
            self.SetStatusText(
                f"Saved {len(self.canvas.buildings)} buildings to {filepath}")

        except Exception as e:
            wx.MessageBox(f"Error saving file: {str(e)}", "Error",
                          wx.OK | wx.ICON_ERROR)

    def on_load_geotiff(self, event):
        """Load a GeoTIFF file"""
        if not GEOTIFF_SUPPORT:
            wx.MessageBox("GeoTIFF support not available.\n\n"
                          "Please install the following packages:\n"
                          "- gdal (conda install gdal or pip install gdal)\n"
                          "- rasterio (pip install rasterio)",
                          "GeoTIFF Support Missing",
                          wx.OK | wx.ICON_WARNING)
            return

        dialog = wx.FileDialog(
            self,
            "Load GeoTIFF file",
            wildcard="GeoTIFF files (*.tif;*.tiff)|*.tif;*.tiff|All files (*.*)|*.*",
            style=wx.FD_OPEN | wx.FD_FILE_MUST_EXIST
        )

        if dialog.ShowModal() == wx.ID_OK:
            filepath = dialog.GetPath()

            # Show progress dialog for large files
            progress = wx.ProgressDialog("Loading GeoTIFF",
                                         "Loading and processing GeoTIFF file...",
                                         maximum=100, parent=self,
                                         style=wx.PD_AUTO_HIDE | wx.PD_APP_MODAL)
            progress.Pulse()

            try:
                success = self.canvas.load_geotiff(filepath)
                progress.Destroy()

                if success:
                    self.SetStatusText(
                        f"Loaded GeoTIFF: {os.path.basename(filepath)}")

                    # Optionally show settings dialog
                    result = wx.MessageBox(
                        "GeoTIFF loaded successfully!\n\n"
                        "Would you like to adjust the overlay settings?",
                        "GeoTIFF Loaded",
                        wx.YES_NO | wx.ICON_QUESTION
                    )
                    if result == wx.YES:
                        self.on_geotiff_settings(None)
                else:
                    self.SetStatusText("Failed to load GeoTIFF")

            except Exception as e:
                progress.Destroy()
                wx.MessageBox(f"Error loading GeoTIFF: {str(e)}", "Error",
                              wx.OK | wx.ICON_ERROR)

        dialog.Destroy()

    def on_geotiff_settings(self, event):
        """Show GeoTIFF settings dialog"""
        if not GEOTIFF_SUPPORT:
            return

        if self.canvas.geotiff_layer.data is None:
            wx.MessageBox("No GeoTIFF file loaded.", "No GeoTIFF",
                          wx.OK | wx.ICON_WARNING)
            return

        dialog = GeoTiffDialog(self,
                               self.canvas.geotiff_layer.visible,
                               self.canvas.geotiff_layer.opacity)

        if dialog.ShowModal() == wx.ID_OK:
            visible, opacity = dialog.get_values()
            self.canvas.geotiff_layer.visible = visible
            self.canvas.set_geotiff_opacity(opacity)
            self.SetStatusText(
                f"GeoTIFF: {'Visible' if visible else 'Hidden'}, "
                f"Opacity: {opacity:.0%}")

        dialog.Destroy()

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