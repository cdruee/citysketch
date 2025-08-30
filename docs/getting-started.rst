# Getting Started

================

This chapter will guide you through installing and setting up CitySketch for the first time.

Installation
=============

Prerequisites
--------------

CitySketch requires the following software components:

**Required Dependencies:**

* Python 3.7 or higher
* wxPython 4.0+
* NumPy

**Optional Dependencies:**

* **rasterio and GDAL**: For GeoTIFF overlay support
* **PyOpenGL and PyOpenGL_accelerate**: For 3D visualization
* **scipy**: For advanced image processing

Installing with pip
--------------------

.. code-block:: bash

   pip install citysketch

Installing from Source
-----------------------

1. Clone the repository:

   .. code-block:: bash

      git clone https://github.com/your-repo/citysketch.git
      cd citysketch

2. Install dependencies:

   .. code-block:: bash

      pip install -r requirements.txt

3. Install in development mode:

   .. code-block:: bash

      pip install -e .

Installing Optional Dependencies
--------------------------------

For full functionality, install optional dependencies:

.. code-block:: bash

   # For GeoTIFF support
   pip install rasterio gdal

   # For 3D visualization
   pip install PyOpenGL PyOpenGL_accelerate

   # For advanced image processing
   pip install scipy

First Launch
=============

Starting CitySketch
--------------------

After installation, start CitySketch by running:

.. code-block:: bash

   citysketch

Or from Python:

.. code-block:: python

   from citysketch.mainApp import main
   main()

Initial Setup
--------------

When CitySketch starts for the first time:

1. **Check Dependencies**: The application will display warnings if optional dependencies are missing
2. **Default Location**: The map will center on a default location (you can change this in settings)
3. **Interface Layout**: Familiarize yourself with the main interface components

Your First Project
===================

Creating Buildings
-------------------

Let's create your first building:

1. **Start Building Mode**:
   
   * Click the "Add Block Building" button in the toolbar
   * The status bar will show: "Click to place first corner of building"

2. **Place the Building**:
   
   * Click on the canvas to set the first corner
   * Move the mouse to see the building preview
   * Click again to complete the building

3. **Set Building Height**:
   
   * With the building selected, press a number key (1-9) to set stories
   * Or use the "Set Height" button for custom values

Setting Up a Basemap
---------------------

To work with real geographic data:

1. **Open Basemap Dialog**:
   
   * Go to Edit → Select Basemap
   * Or use the menu File → Basemap

2. **Choose Map Provider**:
   
   * **None**: Simple grid background (default)
   * **OpenStreetMap**: Street map data
   * **Satellite**: Aerial imagery
   * **Terrain**: Topographic map

3. **Set Location**:
   
   * Enter latitude and longitude coordinates
   * Or use quick location buttons for major cities
   * Click OK to apply

Basic Navigation
----------------

* **Pan**: Click and drag the background to move around
* **Zoom**: Use mouse wheel to zoom in/out
* **Zoom to Fit**: Click "Zoom Fit" button or press Ctrl+0

Saving Your Work
-----------------

1. **Save Project**: File → Save (Ctrl+S) saves as .csp format
2. **Export**: File → Export to AUSTAL for atmospheric modeling
3. **Auto-save**: CitySketch will prompt to save unsaved changes when closing

Understanding the Interface
===========================

Main Components
---------------

The CitySketch interface consists of:

* **Menu Bar**: File operations, editing tools, and settings
* **Toolbar**: Quick access to common tools
* **Canvas**: Main drawing area where you create and edit buildings
* **Status Bar**: Shows current mode, coordinates, and zoom level

Canvas Interaction Modes
-------------------------

CitySketch has several interaction modes:

* **Normal Mode**: Select, move, and edit existing buildings
* **Add Building Mode**: Create new rectangular buildings
* **Add Round Building Mode**: Create circular buildings  
* **Rectangle Select Mode**: Select multiple buildings with a rectangle

Building Selection
------------------

* **Single Select**: Click on a building to select it
* **Multi-Select**: Hold Ctrl and click buildings to add/remove from selection
* **Rectangle Select**: Hold Shift and drag to select multiple buildings
* **Select All**: Ctrl+A (when implemented)

Coordinate Systems
==================

CitySketch works with two coordinate systems:

World Coordinates
-----------------

* **Units**: Meters
* **Origin**: Configurable based on your project location
* Used for precise building placement and measurements

Geographic Coordinates  
----------------------

* **Format**: Latitude/Longitude (WGS84)
* **Usage**: For basemap integration and GeoTIFF overlays
* Automatically converted to/from world coordinates

Configuration Files
====================

CitySketch stores settings in several locations:

Project Files (.csp)
--------------------

Contains:

* Building geometry and properties
* Map settings (provider, center location, zoom)
* Color settings
* Editor preferences

Cache Directory
---------------

Map tiles are cached in:

* **Windows**: ``%TEMP%\cityjson_tiles``
* **macOS/Linux**: ``/tmp/cityjson_tiles``

The cache improves performance by storing downloaded map tiles locally.

Troubleshooting First Launch
=============================

Common Issues
-------------

**"OpenGL support not available"**
   Install PyOpenGL: ``pip install PyOpenGL PyOpenGL_accelerate``

**"GeoTIFF support not available"**
   Install rasterio: ``pip install rasterio``

**Application won't start**
   Check Python version (3.7+ required) and ensure wxPython is installed

**Map tiles won't load**
   * Check internet connection
   * Verify firewall settings allow HTTP/HTTPS access
   * Some corporate networks may block tile servers

Performance Tips
----------------

* **Large Projects**: Use "None" basemap for better performance with many buildings
* **Memory Usage**: Clear tile cache periodically if disk space is limited  
* **3D View**: Close 3D viewer when not needed to reduce GPU usage

Next Steps
==========

Now that you have CitySketch running:

1. Read the :doc:`user-interface` chapter to understand all interface elements
2. Learn :doc:`creating-buildings` for detailed building creation techniques
3. Explore :doc:`basemaps-geotiff` for working with geographic data
4. Check :doc:`keyboard-shortcuts` to improve your workflow efficiency

.. note::
   Keep CitySketch updated to get the latest features and bug fixes. Check the project repository for updates.