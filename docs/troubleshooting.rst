# Troubleshooting

================

This chapter addresses common issues, error messages, and performance problems you may encounter while using CitySketch.

Installation Issues
====================

Python Version Problems
------------------------

**Error**: "Python 3.7+ required"

**Symptoms**:
- Application won't start
- Import errors during installation
- Missing language features

**Solutions**:
1. Check Python version: ``python --version``
2. Install Python 3.7 or later from python.org
3. Use virtual environment with correct version:
   
   .. code-block:: bash
   
      python3.9 -m venv citysketch-env
      source citysketch-env/bin/activate  # Linux/macOS
      # or
      citysketch-env\Scripts\activate.bat  # Windows

Missing wxPython
-----------------

**Error**: "No module named 'wx'"

**Symptoms**:
- Import error when starting CitySketch
- GUI components fail to load

**Solutions**:
1. Install wxPython: ``pip install wxpython``
2. For Linux, install system dependencies first:
   
   .. code-block:: bash
   
      # Ubuntu/Debian
      sudo apt-get install python3-wxgtk4.0-dev
      
      # CentOS/RHEL
      sudo yum install wxGTK3-devel

3. Try alternative installation method:
   
   .. code-block:: bash
   
      pip install -U -f https://extras.wxpython.org/wxPython4/extras/linux/gtk3/ubuntu-20.04 wxPython

Optional Dependencies Missing
------------------------------

**Warning**: "GeoTIFF support not available"

**Impact**: Cannot load .tif/.tiff overlay files

**Solutions**:
1. Install rasterio: ``pip install rasterio``
2. Install GDAL system library:
   
   .. code-block:: bash
   
      # Ubuntu/Debian
      sudo apt-get install gdal-bin libgdal-dev
      
      # macOS with Homebrew
      brew install gdal
      
      # Windows
      # Use conda: conda install gdal

**Warning**: "3D view requires OpenGL support"

**Impact**: F3 key and 3D menu items disabled

**Solutions**:
1. Install PyOpenGL: ``pip install PyOpenGL PyOpenGL_accelerate``
2. Update graphics drivers
3. Check OpenGL support: ``glxinfo | grep OpenGL`` (Linux)

Application Startup Issues
===========================

Application Won't Start
------------------------

**Symptoms**:
- Command line shows no output
- Window doesn't appear
- Process starts but exits immediately

**Diagnostic Steps**:
1. Run from command line to see error messages
2. Check Python path and module installation
3. Verify all dependencies are installed
4. Test with minimal wxPython example

**Common Causes**:
- Missing wxPython installation
- Incompatible Python version
- Corrupted installation files
- System graphics issues

Display Issues
---------------

**Problem**: Black or blank window

**Causes**:
- Graphics driver issues
- OpenGL context problems
- Display scaling issues

**Solutions**:
1. Update graphics drivers
2. Try different display scaling settings
3. Run with software rendering: ``export LIBGL_ALWAYS_SOFTWARE=1``
4. Check system compatibility with wxPython

**Problem**: Interface appears corrupted

**Causes**:
- DPI scaling issues
- Theme compatibility problems
- Font rendering issues

**Solutions**:
1. Adjust system DPI settings
2. Try different system themes
3. Reset application preferences (delete config files)

File Operation Issues
=====================

Can't Open Project Files
-------------------------

**Error**: "Not a valid CitySketch file"

**Causes**:
- File corruption
- Incompatible file version
- JSON syntax errors

**Solutions**:
1. Check file extension (.csp required)
2. Verify file isn't empty or corrupted
3. Open file in text editor to check JSON syntax
4. Try opening backup files if available

**Error**: "Permission denied"

**Causes**:
- File permissions issues
- File locked by another application
- Antivirus software interference

**Solutions**:
1. Check file permissions
2. Close other applications using the file
3. Run CitySketch as administrator (Windows)
4. Add CitySketch to antivirus exclusions

Can't Save Project Files
-------------------------

**Error**: "Failed to save file"

**Causes**:
- Insufficient disk space
- Write permissions issues
- Path too long (Windows)

**Solutions**:
1. Check available disk space
2. Save to different location
3. Shorten file path
4. Check folder permissions

Export Issues
-------------

**Problem**: AUSTAL export contains no buildings

**Causes**:
- No buildings created in project
- Geographic center not set
- Coordinate system issues

**Solutions**:
1. Verify buildings exist in project
2. Set geographic center via basemap dialog
3. Check coordinate values are reasonable

**Problem**: CityJSON export fails

**Causes**:
- Invalid building geometry
- Memory issues with large projects
- Missing building properties

**Solutions**:
1. Validate building geometry
2. Export smaller subsets of buildings
3. Check building height and dimension values

Performance Issues
==================

Slow Application Response
-------------------------

**Symptoms**:
- Delayed response to mouse clicks
- Jerky animation during pan/zoom
- High CPU usage

**Causes**:
- Too many buildings in view
- Complex basemap rendering
- Insufficient system resources

**Solutions**:
1. Disable basemap (set to "None")
2. Zoom to smaller areas
3. Close unnecessary applications
4. Increase system RAM if possible

Map Tiles Won't Load
--------------------

**Symptoms**:
- Gray squares instead of map imagery
- "Failed to load tile" messages in status bar
- Incomplete map coverage

**Causes**:
- Internet connection issues
- Tile server problems
- Firewall blocking requests
- Corporate network restrictions

**Solutions**:
1. Check internet connection
2. Try different map provider
3. Configure firewall exceptions
4. Clear tile cache: delete temp/cityjson_tiles folder
5. Restart application

3D View Problems
================

3D Window Won't Open
---------------------

**Error**: "OpenGL support not available"

**Causes**:
- Missing PyOpenGL installation
- Incompatible graphics hardware
- Driver issues

**Solutions**:
1. Install PyOpenGL: ``pip install PyOpenGL PyOpenGL_accelerate``
2. Update graphics drivers
3. Check hardware OpenGL support
4. Try software rendering

3D View Performance Issues
--------------------------

**Symptoms**:
- Very low frame rates
- Stuttering during rotation
- Long delays when opening 3D view

**Causes**:
- Software rendering instead of hardware
- Too many buildings to render
- Insufficient GPU memory

**Solutions**:
1. Update graphics drivers
2. Reduce number of selected buildings
3. Close other GPU-intensive applications
4. Lower display resolution

3D View Display Problems
------------------------

**Problem**: Buildings appear as wireframes only

**Cause**: OpenGL context issues or rendering settings

**Solutions**:
1. Restart 3D view
2. Update graphics drivers
3. Try different OpenGL settings

**Problem**: Camera controls don't work

**Solutions**:
1. Click in 3D window to ensure focus
2. Use mouse drag for rotation
3. Use mouse wheel for zoom
4. Check for conflicting system shortcuts

GeoTIFF Issues
==============

Can't Load GeoTIFF Files
-------------------------

**Error**: "GeoTIFF support not available"

**Cause**: Missing rasterio/GDAL installation

**Solutions**:
1. Install rasterio: ``pip install rasterio``
2. Install GDAL system library
3. Use conda for easier GDAL installation: ``conda install rasterio``

**Error**: "Failed to load GeoTIFF"

**Causes**:
- Unsupported file format
- Corrupted GeoTIFF file
- Projection issues
- File size too large

**Solutions**:
1. Verify file is valid GeoTIFF
2. Check file isn't corrupted
3. Try converting to WGS84 projection
4. Reduce file size using GIS tools

GeoTIFF Display Issues
----------------------

**Problem**: GeoTIFF appears in wrong location

**Causes**:
- Coordinate reference system mismatch
- Incorrect geographic center
- Projection transformation errors

**Solutions**:
1. Verify GeoTIFF coordinate system
2. Set correct geographic center in basemap
3. Convert GeoTIFF to WGS84 using GDAL:
   
   .. code-block:: bash
   
      gdalwarp -t_srs EPSG:4326 input.tif output_wgs84.tif

**Problem**: GeoTIFF appears very slow to display

**Causes**:
- Large file size
- Complex projection transformations
- Insufficient memory

**Solutions**:
1. Create pyramids/overviews: ``gdaladdo input.tif 2 4 8 16``
2. Compress GeoTIFF: ``gdal_translate -co COMPRESS=JPEG input.tif output.tif``
3. Crop to area of interest before loading

User Interface Issues
=====================

Toolbar Buttons Disabled
-------------------------

**Problem**: Some toolbar buttons appear grayed out

**Causes**:
- No buildings selected (for building-specific operations)
- Wrong application mode
- Missing optional dependencies

**Solutions**:
1. Select buildings before using building-specific tools
2. Exit building creation mode
3. Install missing dependencies (OpenGL, rasterio)

Keyboard Shortcuts Don't Work
------------------------------

**Problem**: Ctrl+S, Ctrl+O, etc. don't respond

**Causes**:
- System shortcuts override application shortcuts
- Keyboard focus issues
- Regional keyboard differences

**Solutions**:
1. Click in main window to ensure focus
2. Use menu items instead of shortcuts
3. Check for conflicting system shortcuts
4. Try alternative key combinations

Color Display Issues
--------------------

**Problem**: Buildings appear in wrong colors

**Causes**:
- Custom color settings
- Display calibration issues
- Graphics driver problems

**Solutions**:
1. Reset colors via Edit → Color Settings → Reset All
2. Adjust display color calibration
3. Update graphics drivers

Memory and Resource Issues
==========================

Out of Memory Errors
---------------------

**Symptoms**:
- Application crashes during large operations
- Error messages about memory allocation
- System becomes unresponsive

**Causes**:
- Large number of buildings
- High-resolution GeoTIFF files
- Map tile cache growth
- Memory leaks (rare)

**Solutions**:
1. Work with smaller datasets
2. Clear map tile cache
3. Restart application periodically
4. Increase system RAM
5. Process GeoTIFF files in external tools first

Disk Space Issues
-----------------

**Problem**: Tile cache consumes too much disk space

**Location**:
- Windows: ``%TEMP%\cityjson_tiles``
- Linux/macOS: ``/tmp/cityjson_tiles``

**Solutions**:
1. Delete cache folder manually
2. Restart CitySketch to recreate cache
3. Use "None" basemap to avoid tile caching
4. Monitor disk space regularly

Data Integrity Issues
=====================

Building Data Corruption
-------------------------

**Symptoms**:
- Buildings appear at wrong coordinates
- Unexpected building dimensions
- Missing building properties

**Causes**:
- File corruption during save/load
- Coordinate system issues
- Import errors from external formats

**Solutions**:
1. Load backup files
2. Check building properties in dialogs
3. Verify coordinate system settings
4. Re-import from original data sources

Geographic Coordinate Problems
------------------------------

**Problem**: Buildings appear far from expected location

**Causes**:
- Wrong geographic center setting
- Coordinate system confusion
- Import coordinate errors

**Solutions**:
1. Verify geographic center in basemap dialog
2. Check original data coordinate system
3. Use known reference points for verification
4. Convert coordinates using external tools

Getting Additional Help
=======================

Log File Information
--------------------

CitySketch outputs diagnostic information to the console. To capture this:

**Windows**:
.. code-block:: batch

   citysketch.exe > log.txt 2>&1

**Linux/macOS**:
.. code-block:: bash

   citysketch > log.txt 2>&1

System Information
------------------

When reporting issues, include:

- Operating system version
- Python version
- CitySketch version
- Installed dependencies (``pip list``)
- Graphics hardware information
- Error messages and stack traces

Common Error Message Reference
==============================

**"Warning: GeoTIFF support not available"**
   Install rasterio: ``pip install rasterio``

**"Warning: OpenGL support not available"**
   Install PyOpenGL: ``pip install PyOpenGL PyOpenGL_accelerate``

**"Failed to load tile Z/X/Y"**
   Check internet connection and tile server availability

**"Not a valid CitySketch file"**
   File may be corrupted or wrong format

**"Permission denied"**
   Check file permissions or run as administrator

**"The loaded image is not projected to EPSG:4326"**
   GeoTIFF needs coordinate system conversion

**"Failed to load GeoTIFF: [error]"**
   Check file format, size, and GDAL installation

Preventive Measures
===================

Regular Maintenance
-------------------

1. **Save Frequently**: Use Ctrl+S often to avoid data loss
2. **Clear Cache**: Delete tile cache monthly
3. **Update Dependencies**: Keep libraries current
4. **Backup Projects**: Save multiple versions of important work
5. **Monitor Resources**: Check disk space and memory usage

Best Practices
---------------

1. **Start Simple**: Begin with small projects to test functionality
2. **Validate Data**: Check building dimensions and coordinates
3. **Use Stable Versions**: Avoid bleeding-edge dependency versions
4. **Document Issues**: Record steps that lead to problems
5. **Test Exports**: Verify exported data in target applications

When All Else Fails
====================

Recovery Options
----------------

1. **Restart Application**: Close and reopen CitySketch
2. **Restart System**: Reboot computer to clear memory issues
3. **Reinstall Application**: Remove and reinstall CitySketch
4. **Reset Settings**: Delete configuration files
5. **Check Hardware**: Test graphics drivers and OpenGL support

Reporting Bugs
--------------

If you encounter persistent issues:

1. Document exact steps to reproduce
2. Collect error messages and log output
3. Note system configuration details
4. Create minimal test case if possible
5. Check existing issue reports first
6. Provide sample files that demonstrate the problem