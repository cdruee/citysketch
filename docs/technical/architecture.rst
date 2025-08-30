# Technical Architecture

=====================

This chapter provides technical details about CitySketch's architecture, data structures, and implementation for developers and advanced users.

System Architecture
====================

Application Structure
---------------------

CitySketch follows a modular architecture built on wxPython:

.. code-block:: text

   CitySketch Application
   ├── User Interface Layer (wxPython)
   │   ├── MainFrame (Application window)
   │   ├── MapCanvas (Drawing surface)  
   │   ├── Dialogs (Configuration windows)
   │   └── Toolbar (Quick actions)
   ├── Data Layer
   │   ├── Building (Core building class)
   │   ├── BuildingGroup (Selection management)
   │   └── Settings (Configuration management)
   ├── Visualization Layer  
   │   ├── 2D Rendering (Canvas drawing)
   │   ├── 3D Rendering (OpenGL)
   │   └── Map Integration (Tile system)
   └── I/O Layer
       ├── CityJSON Import/Export
       ├── AUSTAL Integration
       └── GeoTIFF Processing

Core Components
================

MainFrame Class
----------------

The main application window managing the overall application state:

**Responsibilities**:
- Menu bar and toolbar management
- File operations (New, Open, Save)
- Dialog coordination
- Status bar updates

**Key Methods**:
- ``create_menu_bar()``: Builds application menus
- ``create_toolbar()``: Initializes toolbar buttons
- ``on_key_press()``: Global keyboard shortcut handling

MapCanvas Class
---------------

The primary drawing surface where buildings are displayed and edited:

**Coordinate Systems**:
- Screen coordinates: Pixel positions in window
- World coordinates: Meter-based engineering coordinates
- Geographic coordinates: WGS84 latitude/longitude

**Rendering Pipeline**:
1. Clear background
2. Draw map tiles (if basemap enabled)
3. Draw GeoTIFF overlay (if loaded)
4. Draw grid system
5. Draw buildings (unselected, then selected)
6. Draw selection handles and previews

**Event Handling**:
- Mouse events for interaction
- Paint events for rendering
- Resize events for viewport changes

Building Class
--------------

Core data structure representing individual buildings:

.. code-block:: python

   @dataclass
   class Building:
       id: str              # Unique identifier
       x1: float           # Anchor X coordinate (meters)
       y1: float           # Anchor Y coordinate (meters)
       a: float            # Width along rotated X axis (meters)
       b: float            # Height along rotated Y axis (meters)
       height: float       # Building height (meters)
       storeys: int        # Number of floors
       rotation: float     # Rotation angle (radians)

**Key Methods**:
- ``get_corners()``: Calculate rotated corner positions
- ``contains_point()``: Point-in-polygon testing
- ``to_cityjson_geometry()``: Export geometry

Data Management
================

Coordinate Transformations
--------------------------

CitySketch uses multiple coordinate systems requiring frequent transformations:

**Screen ↔ World Transformation**:

.. code-block:: python

   # Screen to World
   wx = (screen_x - pan_x) / zoom_level  
   wy = (size_y - screen_y + pan_y) / zoom_level
   
   # World to Screen  
   screen_x = world_x * zoom_level + pan_x
   screen_y = size_y - (world_y * zoom_level - pan_y)

**World ↔ Geographic Transformation**:

Uses Web Mercator projection for compatibility with tile systems:

.. code-block:: python

   # Geographic to World (simplified)
   x = (lon - center_lon) * 20037508.34 / 180.0
   y = log(tan((90 + lat) * π / 360)) * 20037508.34 / π - center_y

Building Storage Format
-----------------------

**Internal Representation**:
Buildings are stored as dataclass objects with geometric and semantic properties.

**File Serialization**:
Projects are saved as JSON with the following structure:

.. code-block:: json

   {
     "type": "CitySketch",
     "version": "1.0",
     "buildings": [
       {
         "id": "uuid-string",
         "x1": "float",
         "y1": "float", 
         "a": "float",
         "b": "float",
         "height": "float",
         "storeys": "int",
         "rotation": "float"
       }
     ],
     "editor_settings": {
       "map_provider": "OpenStreetMap",
       "geo_center_lat": 49.4875,
       "geo_center_lon": 8.4660,
       "storey_height": 3.3
     }
   }

Rendering System
================

2D Graphics Pipeline
--------------------

Uses wxPython's graphics context for high-quality 2D rendering:

**Building Rendering**:
1. Calculate rotated corner positions
2. Create graphics path from corners  
3. Set fill and stroke colors based on selection state
4. Draw filled path with border
5. Add text label at center

**Performance Optimizations**:
- Viewport culling (only draw visible buildings)
- Level-of-detail rendering at high zoom levels
- Efficient path reuse for similar buildings

3D Visualization (OpenGL)
--------------------------

**Requirements**:
- PyOpenGL and PyOpenGL_accelerate
- Compatible OpenGL drivers
- Hardware-accelerated graphics recommended

**3D Rendering Pipeline**:
1. Initialize OpenGL context with depth testing
2. Set up perspective projection matrix
3. Position camera using spherical coordinates  
4. Draw ground plane grid
5. Extrude building footprints to 3D volumes
6. Apply lighting and materials

Map Tile System
================

Tile Management
---------------

**Tile Coordinate System**:
Standard slippy map tiles (z/x/y format) compatible with OpenStreetMap and other providers.

**Caching Strategy**:
- Memory cache: Up to 100 tiles for immediate access
- Disk cache: Unlimited tiles in system temp directory
- Cache key: (provider, zoom_level, tile_x, tile_y)

**Loading Process**:
1. Check memory cache
2. Check disk cache  
3. Download from tile server (threaded)
4. Save to both caches
5. Trigger display refresh

**Supported Providers**:
- OpenStreetMap: ``https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png``
- Satellite: ArcGIS World Imagery service
- Terrain: OpenTopoMap service

GeoTIFF Integration
===================

Raster Data Processing
----------------------

**Dependencies**:
- rasterio: Geospatial raster I/O
- GDAL: Coordinate reference system transformations
- NumPy: Array processing

**Processing Pipeline**:
1. Load GeoTIFF with metadata (CRS, bounds, transform)
2. Read raster data as NumPy array
3. Handle different data types (uint8, uint16, float32)
4. Normalize to 8-bit RGB for display
5. Reproject to WGS84 if necessary
6. Create wx.Image for display

**Display Integration**:
- Reproject to current view bounds
- Scale to appropriate resolution
- Apply opacity blending
- Insert in rendering pipeline between basemap and buildings

File Format Support
====================

CitySketch Native Format (.csp)
-------------------------------

**Design Goals**:
- Preserve all editing state
- Include color and preference settings
- Support version migration

**JSON Structure**:
- Root object with type identifier
- Buildings array with all properties
- Editor settings for map and display
- Color settings for customization

CityJSON Export
---------------

**Compliance**:
- CityJSON 1.1 specification
- Building geometry as Solid objects
- Metadata preservation

**Geometry Generation**:
1. Calculate 3D vertices from 2D footprint + height
2. Generate face boundaries (bottom, top, sides)
3. Create vertex index mapping
4. Build CityJSON geometry structure

AUSTAL Integration  
------------------

**File Format**:
- Plain text with specific line format
- Geographic center coordinates
- Building list with position and height

**Import Process**:
1. Parse header for geographic reference
2. Read building records
3. Convert coordinates to internal system
4. Create Building objects

Performance Considerations
==========================

Memory Management
-----------------

**Building Storage**:
- Lightweight dataclass objects
- Minimal memory per building (~200 bytes)
- Efficient for projects with thousands of buildings

**Tile Caching**:
- Configurable memory limits
- Automatic cleanup of old tiles
- Disk cache size monitoring

**3D Rendering**:
- On-demand vertex generation
- GPU memory management through OpenGL
- Automatic resource cleanup

Rendering Performance
---------------------

**Optimization Strategies**:
- Viewport culling for large datasets  
- Simplified rendering at high zoom levels
- Efficient graphics context usage
- Minimal redraws (damage regions)

**Scaling Characteristics**:
- Linear performance with building count
- Logarithmic performance with tile count
- Constant performance for view operations

Threading Model
---------------

**Main Thread**:
- UI operations and rendering
- User input processing
- File I/O operations

**Background Threads**:
- Map tile downloading
- GeoTIFF processing (large files)
- Export operations (future enhancement)

Extension Points
================

Plugin Architecture *(Future)*
-------------------------------

**Planned Extension Points**:
- Custom building types
- Additional file format support
- Analysis and measurement tools
- Integration with external databases

**API Design Goals**:
- Minimal core dependencies
- Clear plugin interfaces
- Robust error handling
- Configuration management

Custom Rendering *(Advanced)*
------------------------------

**Customization Options**:
- Building appearance through color settings
- Custom background rendering
- Additional overlay layers
- Export format extensions

Development Environment
=======================

Build System
-------------

**Requirements**:
- Python 3.7+
- setuptools for packaging
- setuptools_scm for version management

**Development Dependencies**:
- pytest for testing
- sphinx for documentation
- black for code formatting

**Build Process**:
1. Version detection from git tags
2. Package building with setuptools
3. Entry point generation for GUI scripts
4. Resource file inclusion

Testing Framework *(Future)*
-----------------------------

**Planned Testing Strategy**:
- Unit tests for core data structures
- Integration tests for file I/O
- UI automation tests for critical workflows
- Performance benchmarks

Next Steps
===========

For developers interested in contributing:

1. Review the source code structure
2. Set up development environment
3. Read :doc:`development` for contribution guidelines
4. Check issue tracker for enhancement opportunities

For advanced users:

1. Understand file format specifications
2. Explore customization options
3. Consider integration with external tools
4. Provide feedback on architectural decisions