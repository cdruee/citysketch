Troubleshooting
================

This chapter addresses common issues, error messages, and performance problems you may encounter while using CitySketch.

Installation Issues
--------------------

Python Version Problems
~~~~~~~~~~~~~~~~~~~~~~~~

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
~~~~~~~~~~~~~~~~~

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
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

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



GeoTIFF Issues
--------------

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


Getting Additional Help
-----------------------

Log File Information
~~~~~~~~~~~~~~~~~~--

CitySketch outputs diagnostic information to the console. To capture this:

**Windows**:
.. code-block:: batch

   citysketch.exe > log.txt 2>&1

**Linux/macOS**:
.. code-block:: bash

   citysketch > log.txt 2>&1

System Information
~~~~~~~~~~~~~~~~~~

When reporting issues, include:

- Operating system version
- Python version
- CitySketch version
- Installed dependencies (``pip list``)
- Graphics hardware information
- Error messages and stack traces


Reporting Bugs
~~~~~~~~~~~~~~

If you encounter persistent issues:

1. Document exact steps to reproduce
2. Collect error messages and log output
3. Note system configuration details
4. Create minimal test case if possible
5. Check existing issue reports first
6. Provide sample files that demonstrate the problem


Common Error Message Reference
------------------------------

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

