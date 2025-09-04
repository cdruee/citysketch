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
   Feature            .csp       CityJSON  AUSTAL       GeoTIFF   Usage
   =================  ========== ========  ===========  ========  ==============
   **Data Type**
   Project Storage    ✓          ✗         ✗            ✗         Native
   Building Export    ✓          ✓         ✓            ✗         Exchange
   Background Data    ✗          ✗         ✗            ✓         Reference
   **Properties**
   Building Geom.     ✓          ✓         ✓            ✗         All
   Rotation           ✓          ✓         ✗            ✗         Advanced
   Editor Settings    ✓          ✗         ✗            ✗         Workflow
   Color Settings     ✓          ✗         ✗            ✗         Appearance
   3D Geometry        ✓          ✓         ✗            ✗         Visualization
   **Compatibility**
   CitySketch I/O     Read/Write planned   Read/Write   Read       Native
   External Tools     ✗          ✓         ✓            ✓         Integration
   Standard Format    ✗          ✓         ✗            ✓         Interchange
   =================  ========== ========  ===========  ========  ==============

