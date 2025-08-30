# File Formats

==============

This chapter describes all file formats supported by CitySketch for import, export, and project storage.

CitySketch Project Format (.csp)
=================================

The native CitySketch project format stores all project data in a single JSON file with .csp extension.

File Structure
--------------

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
--------------------------

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
-------------------------

.. code-block:: json

   {
     "map_provider": "OpenStreetMap",
     "geo_center_lat": 49.4875,
     "geo_center_lon": 8.4660,
     "geo_zoom": 16,
     "storey_height": 3.3
   }

**Settings Properties**:

- ``map_provider``: Basemap source ("None", "OpenStreetMap", "Satellite", "Terrain")
- ``geo_center_lat``, ``geo_center_lon``: Map center coordinates (WGS84)
- ``geo_zoom``: Map tile zoom level (1-18)
- ``storey_height``: Default height per floor (meters)

Usage Guidelines
----------------

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

CityJSON Format (.json)
=======================

CityJSON is an international standard for 3D city models, based on CityGML but using JSON encoding.

Format Specification
---------------------

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
------------------------

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
--------------

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
----------------

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
==========================

AUSTAL is a format used for atmospheric dispersion modeling. CitySketch can import and export building data in AUSTAL format.

File Structure
--------------

AUSTAL files are plain text with a specific structure:

.. code-block:: text

   # AUSTAL building configuration
   # Geographic center: 49.4875, 8.4660
   
   gg 49.4875 8.4660
   
   # Buildings: x1 y1 x2 y2 height
   bld  100.5  200.0  125.5  215.0   9.9
   bld  150.0  180.0  175.0  195.0  13.2
   bld  200.5  220.0  220.5  240.0   6.6

Header Section
--------------

**Geographic Reference**:
- ``gg lat lon``: Geographic center coordinates (WGS84)
- Used to establish local coordinate system origin

**Comment Lines**:
- Lines starting with ``#`` are comments
- Provide human-readable documentation

Building Entries
----------------

Each building is defined by a single line:

``bld x1 y1 x2 y2 height``

**Parameters**:
- ``x1, y1``: Lower-left corner (meters from geographic center)
- ``x2, y2``: Upper-right corner (meters from geographic center)  
- ``height``: Building height (meters)

**Constraints**:
- Buildings must be axis-aligned rectangles
- No rotation support
- Height only (no storey count)

Import Process
--------------

When importing AUSTAL files:

1. Parse geographic center from ``gg`` line
2. Create buildings from each ``bld`` line
3. Convert coordinates relative to geographic center
4. Set default storey count based on height
5. Set map center to imported location

Export Process  
--------------

When exporting to AUSTAL:

1. Write geographic center as ``gg`` line
2. Convert building coordinates to AUSTAL format
3. Handle rotated buildings (approximate as axis-aligned)
4. Output only geometric properties (no colors/settings)

Usage Guidelines
----------------

**When to Use**:
- Atmospheric dispersion modeling with AUSTAL
- Data exchange with environmental simulation tools
- Simple building geometry export

**Advantages**:
- Simple, readable format
- Direct compatibility with AUSTAL software
- Compact file size
- Wide support in atmospheric modeling

**Limitations**:
- No rotation support (rotated buildings approximated)
- Limited building properties
- Axis-aligned rectangles only
- No 3D geometry details

GeoTIFF Overlay Support
=======================

CitySketch can load GeoTIFF files as background overlays for geographic reference.

Supported Formats
-----------------

**File Extensions**:
- ``.tif``, ``.tiff``: Tagged Image File Format
- Must include geographic metadata

**Data Types**:
- 8-bit unsigned integer (0-255)
- 16-bit unsigned integer (auto-scaled)
- 32-bit floating point (normalized)

**Color Models**:
- RGB (3-band)
- RGBA (4-band with transparency)
- Grayscale (1-band, converted to RGB)

Coordinate Reference Systems
----------------------------

**Preferred**:
- WGS84 (EPSG:4326): Direct compatibility
- Web Mercator (EPSG:3857): Good performance

**Supported with Reprojection**:
- Any CRS supported by GDAL
- UTM zones (various EPSG codes)
- National grid systems
- Custom projections

**Performance Notes**:
- WGS84 provides best performance
- Other CRS require reprojection (slower)
- Large files may take time to process

Loading Process
---------------

1. **File Validation**: Check for valid GeoTIFF format
2. **Metadata Reading**: Extract CRS, bounds, and transform
3. **Data Reading**: Load raster data as NumPy arrays
4. **Type Conversion**: Convert to 8-bit RGB
5. **Projection**: Reproject to WGS84 if necessary
6. **Display Integration**: Create overlay in map view

Display Options
---------------

**Opacity Control**:
- Adjustable from 0% (invisible) to 100% (opaque)
- Default: 70% for overlay effect

**Visibility Toggle**:
- Can be hidden/shown without reloading
- Useful for comparing with/without overlay

**Layer Order**:
- Displays between basemap and buildings
- Buildings always appear on top

Usage Guidelines
----------------

**Preparation Tips**:
1. **Optimize for Performance**:

   - Convert to WGS84 projection
   - Create pyramids/overviews
   - Compress with JPEG or LZW

2. **Size Considerations**:

   - Files over 100MB may be slow
   - Crop to area of interest
   - Reduce resolution if appropriate

**Common Use Cases**:
- Aerial photography for building tracing
- Satellite imagery for site context
- Site plans and architectural drawings
- Elevation models for terrain context

File Format Comparison
======================

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
   CitySketch I/O     Read/Write Write     Read/Write   Read      Native
   External Tools     ✗          ✓         ✓            ✓         Integration
   Standard Format    ✗          ✓         ✗            ✓         Interchange
   =================  ========== ========  ===========  ========  ==============

Format Selection Guidelines
============================

Choose the Right Format
------------------------

**For Ongoing Work**:
- Use .csp format to preserve all settings
- Save frequently during modeling sessions
- Create backup copies periodically

**For Data Exchange**:
- Use CityJSON for 3D applications and GIS
- Use AUSTAL for atmospheric modeling
- Consider target application requirements

**For Reference Data**:
- Use GeoTIFF for background imagery
- Optimize files for performance
- Match coordinate systems when possible

**For Collaboration**:
- CityJSON for technical partners
- AUSTAL for environmental consultants  
- .csp for other CitySketch users

Best Practices
==============

File Management
---------------

1. **Naming Conventions**:
   - Use descriptive names: ``downtown_buildings_v1.csp``
   - Include version numbers for iterations
   - Add date stamps for time-based projects

2. **Organization**:
   - Create project folders for related files
   - Store reference data (GeoTIFF) separately
   - Keep backup copies of important work

3. **Version Control**:
   - Export to CityJSON for milestone versions
   - Document changes in commit messages
   - Use branching for experimental modeling

Quality Assurance
-----------------

1. **Validate Exports**:
   - Open CityJSON in external viewers
   - Check AUSTAL files in text editor
   - Verify coordinates and dimensions

2. **Test Compatibility**:
   - Try importing in target applications
   - Check coordinate system alignment
   - Validate data integrity after round-trips

3. **Document Assumptions**:
   - Record coordinate system choices
   - Note data sources and dates
   - Explain modeling decisions

Troubleshooting File Issues
===========================

Common Export Problems
----------------------

**Empty Exports**:
- Check if buildings exist in project
- Verify selection if exporting selected only
- Confirm coordinate system is valid

**Wrong Coordinates**:
- Check geographic center settings
- Verify coordinate reference system
- Compare with reference data

**Missing Properties**:
- Some formats don't support all properties
- Check format limitations table
- Consider using multiple formats

Import Failures
----------------

**File Not Recognized**:
- Check file extension matches format
- Verify file isn't corrupted
- Try opening in text editor to inspect

**Coordinate Issues**:
- Buildings appear far from expected location
- Check coordinate system settings
- Verify geographic center in AUSTAL files

Performance Problems
--------------------

**Large File Sizes**:
- Use appropriate compression
- Remove unnecessary precision
- Split large projects into sections

**Slow Loading**:
- Optimize GeoTIFF files
- Check available memory
- Close other applications during processing

Next Steps
===========

After understanding file formats:

1. Practice with each format using sample data
2. Test compatibility with your target applications  
3. Develop naming conventions for your projects
4. Set up backup and version control procedures
5. Learn advanced GeoTIFF processing with GDAL tools