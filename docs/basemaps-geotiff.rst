Basemaps and GeoTIFF
========================

This chapter explains how to work with geographic reference data in CitySketch, including basemap integration and GeoTIFF overlay functionality.

Understanding Basemaps
-----------------------

What are Basemaps?
~~~~~~~~~~~~~~~~~~~~~

Basemaps provide geographic context by displaying real-world imagery
or maps behind your building models. They help with:

- **Spatial Reference**: Understanding location in the real world
- **Building Placement**: Positioning buildings accurately  
- **Site Context**: Seeing surrounding features and terrain
- **Navigation**: Moving around large geographic areas

Supported Basemap Providers
~~~~~~~~~~~~~~~~~~~~~~~~~~~~

**None (Default)**
   Simple grid background with no geographic data.
   
   *Best for*: Performance-focused work, abstract modeling
   
   *Pros*: Fast rendering, no internet required, clean interface
   
   *Cons*: No geographic context, limited navigation aids

**OpenStreetMap**
   Collaborative street map with detailed road networks and labels.
   
   *Best for*: Urban planning, street-level context, navigation
   
   *Pros*: Detailed street data, worldwide coverage, regularly updated
   
   *Cons*: Limited building footprints, text-heavy display

**Satellite**
   High-resolution aerial imagery from Esri World Imagery service.
   
   *Best for*: Building tracing, site analysis, visual context
   
   *Pros*: Real building footprints, natural color, high detail
   
   *Cons*: May be outdated, cloud coverage, large file sizes

**Terrain**
   Topographic maps showing elevation, roads, and natural features.
   
   *Best for*: Mountainous areas, elevation context, outdoor sites
   
   *Pros*: Elevation information, natural features, clear symbology
   
   *Cons*: Limited urban detail, specialized use cases

**Hillshade**
   Shading that looks like the topograpy is all white and lightened from the top left.

   *Best for*: Complex tarrain, result presentation.

   *Pros*: Clean looks, elevation visualization

   *Cons*: No man-made references like streets or buildings, no place names


Configuring Basemaps
---------------------

Basemap Selection Dialog
~~~~~~~~~~~~~~~~~~~~~~~~~

Access through **Edit → Select Basemap** or the toolbar:

1. **Choose Map Provider**: Select from radio button options
2. **Set Geographic Center**: Enter latitude/longitude coordinates
3. **Use Quick Locations**: Click preset city buttons for common locations
4. **Apply Settings**: Click OK to load new basemap

Geographic Coordinates
~~~~~~~~~~~~~~~~~~~~~~

**Latitude and Longitude Format**:
- Use decimal degrees (e.g., 49.4875, not 49°29'15"N)
- Latitude: -90 to +90 (negative = South, positive = North)  
- Longitude: -180 to +180 (negative = West, positive = East)
- Precision: 6 decimal places provides ~0.1 meter accuracy

**Finding Coordinates**:
- Google Maps: Right-click location, copy coordinates
- OpenStreetMap: Click location, see coordinates in URL
- GPS devices: Export waypoint coordinates
- Survey data: Convert from local coordinate systems

Quick Location Presets
~~~~~~~~~~~~~~~~~~~~~~~

The basemap dialog includes preset locations:

- **Berlin**: 52.5200, 13.4050
- **Hannover**: 52.3747, 9.7385  
- **Trier**: 49.7523, 6.6370
- **Mannheim**: 49.4875, 8.4660

These provide starting points for common German locations. You can manually enter coordinates for any worldwide location.

Working with Map Tiles
-------------------------

Tile System Overview
~~~~~~~~~~~~~~~~~~~~~

Basemaps use a standard "slippy map" tile system:

- **Zoom Levels**: 0 (world view) to 18 (building detail)
- **Tile Size**: 256×256 pixels per tile
- **Coordinate System**: Web Mercator (EPSG:3857)
- **Tile Servers**: HTTP/HTTPS requests to map providers


Cache Management
~~~~~~~~~~~~~~~~~~~

**Cache Locations**:
- **Memory Cache**: Up to 100 tiles for immediate access
- **Disk Cache**: Unlimited storage in system temp directory

  - Windows: `%TEMP%\\cityjson_tiles\\`
  - macOS/Linux: `/tmp/cityjson_tiles/`

**Cache Behavior**:
- Tiles cached permanently until manually deleted
- Different providers use separate cache folders
- Cache survives application restarts
- No automatic cleanup (monitor disk space)

**Clearing Cache**:
1. Close CitySketch
2. Delete the cityjson_tiles folder
3. Restart CitySketch to recreate cache structure

Performance Considerations
---------------------------

Basemap Performance Factors
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

**Network Speed**: Tile download depends on internet connection
**Zoom Level**: Higher zoom = more tiles = slower loading
**Provider**: Satellite imagery loads slower than street maps
**Cache State**: First visit to area is slower than subsequent visits

Basemap vs. Performance Trade-offs
-----------------------------------

**With Basemap Enabled**:
- Geographic context and reference data
- Realistic building placement
- Professional-looking visualizations
- Slower rendering and higher memory usage

**With Basemap Disabled**:
- Maximum rendering performance
- Reduced memory and bandwidth usage
- Clean, distraction-free interface
- No geographic reference or context

GeoTIFF Overlay Support
-----------------------

Understanding GeoTIFF
~~~~~~~~~~~~~~~~~~~~~

GeoTIFF files are raster images with embedded geographic information:

- **Image Data**: RGB or grayscale pixel values
- **Geographic Metadata**: Coordinate system, bounds, resolution
- **Projection Information**: How to map pixels to real-world coordinates

**Common GeoTIFF Sources**:
- Aerial photography surveys
- Satellite imagery downloads
- Site plans and architectural drawings
- Digital elevation models
- Custom imagery from GIS systems

Loading GeoTIFF Files
---------------------

**Prerequisites**: Requires rasterio and GDAL libraries
```bash
pip install rasterio
```

**Loading Process**:
1. **File → Load GeoTIFF** (when rasterio available)
2. **Select File**: Choose .tif or .tiff file
3. **Processing**: CitySketch reads and processes the image
4. **Display**: Overlay appears between basemap and buildings

**Supported Formats**:
- Standard GeoTIFF (.tif, .tiff)
- Various bit depths (8-bit, 16-bit, 32-bit)
- RGB, RGBA, and grayscale images
- Most coordinate reference systems

GeoTIFF Display Options
--------------------------

Overlay Configuration
~~~~~~~~~~~~~~~~~~~~~~~

Access through **Edit → GeoTIFF Settings** after loading:

**Visibility Toggle**:
- Show/hide overlay without reloading file
- Useful for comparing with/without overlay
- Preserves all processing work

**Opacity Control**:
- Slider from 0% (invisible) to 100% (opaque)
- Default: 70% for overlay effect
- Real-time preview of changes

Layer Order
-----------

GeoTIFF overlays render in this order:

1. **Background**: Basemap tiles (bottom layer)
2. **Overlay**: GeoTIFF image (middle layer)  
3. **Foreground**: Buildings and interface (top layer)

This ensures buildings always appear above reference data while maintaining geographic context from the basemap.

Coordinate System Handling
----------------------------

Projection Support
~~~~~~~~~~~~~~~~~~

**Preferred Coordinate Systems**:
- **WGS84 (EPSG:4326)**: Direct compatibility, best performance
- **Web Mercator (EPSG:3857)**: Good performance, tile system compatibility

Coordinate System Warnings
---------------------------

**"Image is not projected to EPSG:4326" Warning**:
- Appears for non-WGS84 coordinate systems
- Indicates slower display performance
- Option to continue or cancel loading
- Consider reprojecting file externally for better performance

**Reprojection Solutions**:
```bash
# Convert to WGS84 using GDAL
gdalwarp -t_srs EPSG:4326 input.tif output_wgs84.tif
```

GeoTIFF Optimization
---------------------

Preparing GeoTIFF Files
~~~~~~~~~~~~~~~~~~~~~~~~

**Performance Optimization**:
1. **Convert to WGS84**: Use gdalwarp for coordinate system conversion
2. **Create Overviews**: Add pyramid levels for faster zooming

   ```bash
   gdaladdo input.tif 2 4 8 16 32
   ```

3. **Compress Images**: Reduce file size without losing quality

   ```bash
   gdal_translate -co COMPRESS=JPEG -co QUALITY=85 input.tif output.tif
   ```

4. **Crop to Area**: Remove unnecessary areas outside project bounds

**File Size Management**:
- Files over 100MB may cause performance issues
- Consider tiling large images into smaller sections
- Use appropriate compression for image type
- Balance file size vs. image quality

Data Type Handling
-------------------

**8-bit Images (0-255)**:
- Direct display compatibility
- RGB and grayscale supported
- Fastest processing and display

**16-bit Images**:
- Automatically scaled to 8-bit for display
- May lose some precision in conversion
- Consider external conversion for control

**Floating Point Images**:
- Normalized to 0-255 range
- May require manual scaling for optimal display
- Common with elevation models and analysis results

Troubleshooting GeoTIFF Issues
-------------------------------

Loading Problems
~~~~~~~~~~~~~~~~~

**"GeoTIFF support not available"**:
- Install rasterio: `pip install rasterio`
- May require GDAL system libraries
- Consider using conda for easier installation

**"Failed to load GeoTIFF"**:
- Check file isn't corrupted: try opening in other GIS software
- Verify file has valid geographic metadata
- Try converting to different format first

**"Very slow display"**:
- File likely uses complex coordinate system
- Convert to WGS84 externally for better performance
- Consider creating overview pyramids

Display Problems
----------------

**GeoTIFF appears in wrong location**:
- Verify coordinate system matches project area
- Check geographic center setting in basemap dialog
- Ensure coordinate system metadata is correct

**Image appears very dark or bright**:
- Original data may use unusual value ranges
- Try adjusting opacity to blend with basemap
- Consider preprocessing image contrast externally

**Partial or missing image display**:
- Check coordinate system compatibility
- Verify image bounds overlap with current view
- Try zooming to different areas to test coverage


Integration Strategies
-----------------------

Basemap-Driven Workflow
~~~~~~~~~~~~~~~~~~~~~~~~~

**Start with Basemap**:
1. Set geographic center to project location
2. Choose appropriate basemap provider
3. Navigate to precise working area
4. Create buildings using basemap as reference

GeoTIFF-Driven Workflow
~~~~~~~~~~~~~~~~~~~~~~~

**Start with GeoTIFF**:
1. Load site-specific GeoTIFF overlay
2. Set basemap to complement overlay (often None or minimal)
3. Adjust opacity for optimal visibility
4. Create buildings based on detailed overlay information

Combined Approach
~~~~~~~~~~~~~~~~~

**Layered Reference System**:
1. Basemap for general geographic context
2. GeoTIFF overlay for detailed site information
3. Buildings for final model representation
4. Toggle layers as needed during different work phases

