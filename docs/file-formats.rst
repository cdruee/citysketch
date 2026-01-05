File Formats
==============

This chapter describes all file formats supported by CitySketch for import, export, and project storage.


CitySketch Project Format (.csp)
--------------------------------

The native CitySketch project format stores all project data in a single
JSON file with .csp extension.


File Structure
~~~~~~~~~~~~~~

.. code-block:: json

   {
     "type": "CitySketch",
     "version": "1.0",
     "buildings": [...],
     "editor_settings": {...},
     "color_settings": {...},
     "general_settings": {...}
   }

**Root Properties**:

- ``type``: Always "CitySketch" for format identification
- ``version``: Format version for compatibility checking
- ``buildings``: Array of building objects
- ``editor_settings``: Map configuration and display settings
- ``color_settings``: Custom color definitions
- ``general_settings``: Application preferences

Building Object Structure
~~~~~~~~~~~~~~~~~~~~~~~~~

Each building in the ``buildings`` array contains:

.. code-block:: json

   {
     "id": "550e8400-e29b-41d4-a716-446655440000",
     "x1": "100.5",
     "y1": "200.0",
     "a": "25.0",
     "b": "15.0",
     "height": "9.9",
     "storeys": "3",
     "rotation": "0.785398"
   }

**Building Properties**:

- ``id``: Unique identifier (UUID format)
- ``x1``, ``y1``: Anchor point coordinates (meters)
- ``a``, ``b``: Building dimensions along rotated axes (meters)
- ``height``: Total building height (meters)
- ``storeys``: Number of floors (integer)
- ``rotation``: Rotation angle in radians

Editor Settings Structure
~~~~~~~~~~~~~~~~~~~~~~~~~~~

.. code-block:: json

     "editor_settings": {
       "map_provider": "OpenStreetMap",
       "geo_center_lat": 49.4875,
       "geo_center_lon": 8.4660,
       "storey_height": 3.3
     }

**Settings Properties**:

- ``map_provider``: Basemap source ("None", "OpenStreetMap", "Satellite", "Terrain")
- ``geo_center_lat``, ``geo_center_lon``: Map center coordinates (WGS84)
- ``geo_zoom``: Map tile zoom level (1-18)
- ``storey_height``: Default height per floor (meters)


Simple example
~~~~~~~~~~~~~~

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



Usage Guidelines
~~~~~~~~~~~~~~~~

**When to Use**:
- Saving work for later editing
- Preserving all editor settings
- Creating project templates
- Version control of building models

**Advantages**:
- Complete data preservation
- Fast loading and saving
- Compact file size
- Human-readable format

**Limitations**:
- CitySketch-specific format
- Not directly usable by other applications
- Requires CitySketch for viewing

.. CityJSON Format (.json)
    -----------------------

    CityJSON is an international standard for 3D city models, based on CityGML but using JSON encoding.

    Format Specification
    ~~~~~~~~~~~~~~~~~~~~

    CitySketch exports CityJSON 1.1 compliant files with the following structure:

    .. code-block:: json

       {
         "type": "CityJSON",
         "version": "1.1",
         "metadata": {
           "geographicalExtent": [west, south, east, north, min_z, max_z],
           "referenceSystem": "https://www.opengis.net/def/crs/EPSG/0/4326"
         },
         "CityObjects": {...},
         "vertices": [...]
       }

    Building Representation
    ~~~~~~~~~~~~~~~~~~~~~~~~

    Buildings are exported as CityJSON Building objects:

    .. code-block:: json

       {
         "building_001": {
           "type": "Building",
           "attributes": {
             "height": 9.9,
             "stories": 3
           },
           "geometry": [{
             "type": "Solid",
             "lod": 1,
             "boundaries": [[[...]]]
           }]
         }
       }

    **Geometry Details**:

    - ``type``: Always "Solid" for 3D buildings
    - ``lod``: Level of detail (always 1 for CitySketch)
    - ``boundaries``: 3D face definitions using vertex indices

    Vertex Storage
    ~~~~~~~~~~~~~~~

    All 3D coordinates are stored in the global ``vertices`` array:

    .. code-block:: json

       "vertices": [
         [100.5, 200.0, 0.0],
         [125.5, 200.0, 0.0],
         [125.5, 215.0, 0.0],
         [100.5, 215.0, 0.0],
         [100.5, 200.0, 9.9],
         [125.5, 200.0, 9.9],
         [125.5, 215.0, 9.9],
         [100.5, 215.0, 9.9]
       ]

    **Coordinate System**:
    - Units: Meters
    - Format: [X, Y, Z] arrays
    - Reference: WGS84 (EPSG:4326)

    Usage Guidelines
    ~~~~~~~~~~~~~~~~~

    **When to Use**:
    - Data exchange with other applications
    - Integration with GIS systems
    - Compliance with international standards
    - Web-based 3D visualization

    **Compatible Applications**:
    - QGIS (with CityJSON plugin)
    - FME (Feature Manipulation Engine)
    - azul (CityJSON viewer)
    - Blender (with import plugins)

    **Advantages**:
    - International standard format
    - Wide software support
    - Detailed 3D geometry
    - Extensible attribute system

    **Limitations**:
    - Larger file size than .csp format
    - No editor-specific settings
    - Read-only (CitySketch doesn't import CityJSON)

GeoJSON Format (.geojson)
----------------------------

CitySketch can import building footprints from GeoJSON files, a widely-used
format for geographic data exchange.

Supported Structure
~~~~~~~~~~~~~~~~~~~~

CitySketch imports GeoJSON files with Polygon or MultiPolygon geometries:

.. code-block:: json

   {
     "type": "FeatureCollection",
     "features": [
       {
         "type": "Feature",
         "properties": {
           "height": 12.5,
           "building:levels": 4
         },
         "geometry": {
           "type": "Polygon",
           "coordinates": [[[lon1, lat1], [lon2, lat2], ...]]
         }
       }
     ]
   }

**Recognized Properties**:

* ``height``: Building height in meters
* ``building:levels`` or ``levels``: Number of stories (used to calculate height
  if height property is missing)
* ``id``: Feature identifier (preserved as building ID)

Coordinate Reference Systems
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

CitySketch supports various CRS definitions:

* **EPSG codes**: ``"EPSG:4326"``, ``"urn:ogc:def:crs:EPSG::4326"``
* **Default**: WGS84 (EPSG:4326) if no CRS is specified

Rectangle Fitting
~~~~~~~~~~~~~~~~~~

Since CitySketch works with rectangular buildings, imported polygons are
converted using intelligent fitting algorithms:

1. **Simple Rectangles**: Polygons with mostly right angles are simplified
   to single rectangles using PCA-based orientation detection.

2. **Complex Shapes**: L-shaped, T-shaped, and other complex footprints are
   decomposed into multiple rectangles using the Ferrari-Sankar-Sklansky
   partitioning algorithm.

3. **Quality Check**: Fitted rectangles must have at least 80% overlap with
   the original polygon (configurable via MAX_NON_OVERLAP_RATIO setting).

Import Tolerances
~~~~~~~~~~~~~~~~~~

The following settings (configurable in Edit → Settings → Import) control
the import behavior:

* **Angle Tolerance**: How close to 90° angles must be for rectangle detection
* **Distance Tolerance**: Simplification threshold for complex shapes
* **Max Non-Overlap Ratio**: Maximum acceptable fitting error

.. _gba-import:

Global Building Atlas Import
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

CitySketch supports bulk import from Global Building Atlas (GBA) tile sets.

**Setup**:

1. Download GBA tiles for your region of interest
2. Configure the GBA directory in Edit → Settings → Paths

**Tile Naming Convention**:

GBA tiles use a specific filename format encoding the tile bounds::

   {lon_left}_{lat_upper}_{lon_right}_{lat_lower}.geojson

Where coordinates use a special encoding:

* Longitude: 3 integer digits + optional decimals (e.g., ``e00675`` = 6.75°E)
* Latitude: 2 integer digits + optional decimals (e.g., ``n4987`` = 49.87°N)

**Import Process**:

1. Go to File → Import Global Building Atlas
2. CitySketch scans subdirectories for tiles overlapping the current view
3. Confirm the import when prompted with tile count
4. Buildings are imported and converted to CitySketch format

AUSTAL Format (austal.txt)
----------------------------

AUSTAL is a format used for atmospheric dispersion modeling.
CitySketch can import and export building data in AUSTAL format.

File Structure
~~~~~~~~~~~~~~

AUSTAL files are plain text with a specific structure:

.. code-block:: text

   ...

   - AUSTAL building configuration
   - Geographic center: 49.4875, 8.4660
   ux 461324.59
   uy 5481788.17

   - Buildings: #1 #2 #3
   xb  100.5  150.0 200.5
   yb  100.0  180.0 220.0
   ab   25.0   25.0  20.0
   bb   20.0   25.0  25.0
   wb    0.     0.    0.

   ...

Header Section
~~~~~~~~~~~~~~

**Geographic Reference**:
- ``ux``, ``uy```: Geographic anchor coordinate (UTM)
- Used to establish local coordinate system origin

- ``xb``, ``yb``: Building anchor coordinate in m (model coordinates)
- ``ab``, ``bb``: Building side-lengths in m (or 0. and diameter for round building)
- ``cb``: building height in m
- ``wb``: building rotation angle around anchor (0. if line is missing)

**Comment Lines**:
- Lines starting with ``-`` or ``'`` are comments

For full documentation see the AUSTAL user manual.


Import Process
~~~~~~~~~~~~~~

When importing AUSTAL files:

1. Parse geographic center (origin) position
2. Create buildings from the ``xb??, ??yb``, ... lines
3. Set default storey count based on height
4. Set map center to imported location

Export Process
~~~~~~~~~~~~~~

When exporting to AUSTAL:

1. If file exists: create backup file
2. If file exists: Check if geographic center (origin) position matches file
3. Leave file contents intact, delete all buildings in file.
4. Write buildings to file.


GeoTIFF Overlay Support
-----------------------

CitySketch can load GeoTIFF files as background overlays for geographic reference.

Supported Formats
~~~~~~~~~~~~~~~~~~

**File Extensions**:
- ``.tif``: Tagged Image File Format
- Must include geographic metadata

**Data Types**:
- 8-bit unsigned integer (0-255)
- 16-bit unsigned integer (auto-scaled)
- 32-bit floating point (normalized)

**Color Models**:
- RGB (3-band)
- RGBA (4-band with transparency)
- Grayscale (1-band, converted to RGB)


Loading Process
~~~~~~~~~~~~~~~

1. **File Validation**: Check for valid GeoTIFF format
2. **Metadata Reading**: Extract CRS, bounds, and transform
3. **Data Reading**: Load raster data as NumPy arrays
4. **Type Conversion**: Convert to 8-bit RGB
5. **Projection**: Reproject to WGS84 if necessary
6. **Display Integration**: Create overlay in map view


File Format Comparison
-----------------------

.. table:: Format Comparison Matrix
   :widths: auto

   =================  ========== ========  ===========  ========  ==============
   Feature            .csp       GeoJSON   AUSTAL       GeoTIFF   Usage
   =================  ========== ========  ===========  ========  ==============
   **Data Type**
   Project Storage    ✓          ✗         ✗            ✗         Native
   Building Import    ✗          ✓         ✓            ✗         Exchange
   Building Export    ✓          ✗         ✓            ✗         Exchange
   Background Data    ✗          ✗         ✗            ✓         Reference
   **Properties**
   Building Geom.     ✓          ✓         ✓            ✗         All
   Rotation           ✓          ✓         ✓            ✗         Advanced
   Editor Settings    ✓          ✗         ✗            ✗         Workflow
   Color Settings     ✓          ✗         ✗            ✗         Appearance
   3D Geometry        ✓          ✗         ✗            ✗         Visualization
   **Compatibility**
   CitySketch I/O     Read/Write Read      Read/Write   Read      Native
   External Tools     ✗          ✓         ✓            ✓         Integration
   Standard Format    ✗          ✓         ✗            ✓         Interchange
   =================  ========== ========  ===========  ========  ==============


Settings File Format (settings.ini)
------------------------------------

CitySketch stores application settings in an INI format configuration file.

File Location
~~~~~~~~~~~~~~

The settings file is stored in a platform-specific location:

* **Linux**: ``~/.config/citysketch/settings.ini``
* **Windows**: ``%APPDATA%\citysketch\settings.ini``
* **macOS**: ``~/Library/Application Support/citysketch/settings.ini``

File Structure
~~~~~~~~~~~~~~~

The settings file uses standard INI format with two sections:

.. code-block:: ini

   # CitySketch Settings
   # This file is auto-generated. Edit with care.

   [settings]
   zoom_step_percent = 20
   circle_corners = 12
   gba_directory = /path/to/gba/tiles
   height_tolerance = 0.1
   angle_tolerance = 15.0
   distance_tolerance = 2.0
   max_non_overlap_ratio = 0.2
   max_center_distance = 10.0

   [colors]
   col_tile_empty = 200, 200, 200, 255
   col_tile_edge = 240, 240, 240, 255
   col_grid = 220, 220, 220, 255
   col_float_in = 100, 255, 100, 100
   col_float_out = 0, 200, 0, 255
   col_bldg_in = 200, 200, 200, 180
   col_bldg_out = 100, 100, 100, 255
   col_bldg_lbl = 255, 255, 255, 255
   col_sel_bldg_in = 150, 180, 255, 180
   col_sel_bldg_out = 0, 0, 255, 255
   col_handle_in = 255, 255, 255, 255
   col_handle_out = 0, 0, 255, 255

Settings Section
~~~~~~~~~~~~~~~~~

**UI Settings**:

* ``zoom_step_percent``: Zoom increment per mouse wheel step (default: 20)
* ``circle_corners``: Number of vertices for circular buildings (default: 12)

**Paths**:

* ``gba_directory``: Path to Global Building Atlas tile directory

**Import Tolerances**:

* ``height_tolerance``: Height matching tolerance for merging (default: 0.1)
* ``angle_tolerance``: Rectangle detection angle tolerance in degrees (default: 15.0)
* ``distance_tolerance``: Shape simplification tolerance in meters (default: 2.0)
* ``max_non_overlap_ratio``: Maximum fitting error ratio (default: 0.2)
* ``max_center_distance``: AUSTAL center distance tolerance in meters (default: 10.0)

Colors Section
~~~~~~~~~~~~~~~

Colors are specified as comma-separated RGBA values (0-255):

* ``col_tile_empty``: Background color for empty map tiles
* ``col_tile_edge``: Border color for map tiles
* ``col_grid``: Grid line color
* ``col_float_in``: Building preview fill color
* ``col_float_out``: Building preview outline color
* ``col_bldg_in``: Building fill color
* ``col_bldg_out``: Building outline color
* ``col_bldg_lbl``: Building label text color
* ``col_sel_bldg_in``: Selected building fill color
* ``col_sel_bldg_out``: Selected building outline color
* ``col_handle_in``: Selection handle fill color
* ``col_handle_out``: Selection handle outline color

Manual Editing
~~~~~~~~~~~~~~~

The settings file can be edited manually while CitySketch is not running.
Changes take effect on the next application start. Invalid values are
silently replaced with defaults.

