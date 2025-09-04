User Interface
================

This chapter provides a detailed overview of CitySketch's user interface, explaining each component and how to use it effectively.

Interface Overview
---------------------

The CitySketch interface is organized into several main areas:

.. image:: _static/citysketch_window.png
   :align: center
   :alt: CitySketch Interface Overview

1. **Menu Bar** - File operations and application settings
2. **Toolbar** - Quick access buttons for common operations  
3. **Canvas** - Main working area for building creation and editing
4. **Status Bar** - Information about current mode, coordinates, and zoom

Menu Bar
----------

File Menu
~~~~~~~~~~~

**New (Ctrl+N)**
   Creates a new empty project, clearing all existing buildings.

**Open (Ctrl+O)**
   Opens a saved CitySketch project file (.csp format).

**Save (Ctrl+S)**
   Saves the current project. If no filename is set, prompts for save location.

**Save As (Ctrl+Shift+S)**
   Saves the project with a new filename or location.

**Import from AUSTAL**
   Imports building data from an AUSTAL atmospheric modeling file (austal.txt).

**Export to AUSTAL**  
   Exports current buildings to AUSTAL format for atmospheric modeling.

**Exit (Ctrl+Q)**
   Closes CitySketch. Prompts to save unsaved changes.

Edit Menu
~~~~~~~~~~

**Select Basemap**
   Opens the basemap selection dialog to choose map provider and location.

**Zoom to Buildings (Ctrl+0)**
   Adjusts zoom and pan to fit all buildings in the view.

**Load GeoTIFF** *(when available)*
   Loads a GeoTIFF file as an overlay layer.

**GeoTIFF Settings** *(when GeoTIFF loaded)*
   Configures visibility and opacity of GeoTIFF overlay.

**Show 3D View (F3)** *(when OpenGL available)*
   Opens the 3D visualization window.

**Set Storey Height**
   Sets the default height per building storey (affects height calculations).

**Color Settings**
   Opens dialog to customize application colors and appearance.

Help Menu
~~~~~~~~~~

**About**
   Displays version information, credits, and library versions.

Toolbar
--------

The toolbar provides quick access to frequently used tools:

Building Tools
~~~~~~~~~~~~~~~~~

**Add Block Building**
   Switches to rectangular building creation mode. Click twice on canvas to create a building.

**Add Round Building**  
   Switches to circular building creation mode. Click center point, then drag to set radius.

View Controls
~~~~~~~~~~~~~~

**Snap: ON/OFF**
   Toggles snapping to building corners and edges for precise alignment.

**Set Height**
   Opens height dialog for selected buildings to set stories and exact height.

**Delete**
   Deletes currently selected buildings after confirmation.

**Zoom In**
   Increases zoom level, centered on current view.

**Zoom Out**
   Decreases zoom level, showing more area.

**Zoom Fit**
   Automatically adjusts zoom to show all buildings.

Canvas
--------

The canvas is the main working area where you create and edit buildings.
It supports multiple interaction modes and provides visual feedback for
all operations.

Coordinate Display
~~~~~~~~~~~~~~~~~~~

The canvas uses a coordinate system with:

* **Origin (0,0)**: Configurable based on your geographic location
* **Units**: Meters  
* **Axes**: X increases eastward, Y increases northward
* **Display**: World coordinates shown in status bar

Visual Elements
~~~~~~~~~~~~~~~~~~

**Grid**
   Background grid helps with alignment. Grid spacing adjusts with zoom level.

**Buildings**
   * **Unselected**: Light gray fill with dark border
   * **Selected**: Blue fill with blue border
   * **Preview**: Semi-transparent green during creation

**Basemap** *(when enabled)*
   Map tiles provide geographic context. Tiles load automatically as you navigate.

**GeoTIFF Overlay** *(when loaded)*
   Custom imagery displayed between basemap and buildings with adjustable opacity.

Selection Handles
~~~~~~~~~~~~~~~~~~~~

Selected buildings show corner handles for editing:

* **Square Handles**: Normal scaling mode - drag to resize
* **Circular Handles**: Rotation mode (when Ctrl is held) - drag to rotate

Mouse Interaction
-------------------

The canvas responds to various mouse actions depending on the current mode:

Normal Mode (Default)
~~~~~~~~~~~~~~~~~~~~~~~

**Single Click**
   * On empty space: Deselects all buildings
   * On building: Selects that building
   * With Ctrl: Adds/removes building from selection

**Click and Drag**  
   * On empty space: Pans the view
   * On building: Moves selected buildings
   * On corner handle: Resizes building (or rotates if Ctrl held)
   * With Shift: Starts rectangle selection

**Mouse Wheel**
   Zooms in/out centered on mouse cursor position

Add Building Mode
~~~~~~~~~~~~~~~~~~~

**First Click**
   Sets the first corner of the building (snapped if snap is enabled)

**Mouse Movement**
   Shows preview of building being created (mous must be above / right od the first-click position)

**Second Click**
   Completes building creation and returns to normal mode

**Ctrl Key**
   During building creation, switches between scale and rotation modes

Add Round Building Mode
~~~~~~~~~~~~~~~~~~~~~~~~

**First Click**
   Sets center point of circular building

**Mouse Movement**
   Shows circular preview with radius determined by distance from center

**Second Click**
   Completes circular building creation

Rectangle Selection Mode
~~~~~~~~~~~~~~~~~~~~~~~~~

**Click and Drag**
   Creates selection rectangle. All buildings completely within rectangle are selected when mouse is released.

Status Bar
-----------

The status bar displays important information:

Status Information
~~~~~~~~~~~~~~~~~~~~

**Left Section**: Current operation status
   * Operation messages and instructions
   * Error messages and warnings
   * Success confirmations

**Center Section**: Mouse coordinates and zoom info
   * Current mouse position in world coordinates
   * Current zoom factor

**Right Section**: Technical details
   * Map zoom level (for basemap tiles)
   * Pan offset values
   * Zoom factor

Keyboard Shortcuts
-------------------

The interface supports many keyboard shortcuts for efficient operation:

Building Operations
~~~~~~~~~~~~~~~~~~~~~~~

* **1-9**: Set selected buildings to 1-9 stories
* **Delete**: Delete selected buildings
* **Ctrl+A**: Select all buildings *(when implemented)*

View Control
~~~~~~~~~~~~

* **Ctrl+0**: Zoom to fit all buildings  
* **Ctrl++**: Zoom in
* **Ctrl+-**: Zoom out
* **F3**: Open 3D view (if OpenGL available)

File Operations
~~~~~~~~~~~~~~~~~

* **Ctrl+N**: New project
* **Ctrl+O**: Open project
* **Ctrl+S**: Save project
* **Ctrl+Shift+S**: Save As
* **Ctrl+Q**: Quit application

Selection Modes
~~~~~~~~~~~~~~~~~~

* **Ctrl+Click**: Multi-select buildings
* **Shift+Drag**: Rectangle selection mode
* **Ctrl+Drag**: Rotation mode (when dragging handles)

Context Sensitivity
--------------------

The interface adapts based on the current context:

Mode-Dependent Behavior
~~~~~~~~~~~~~~~~~~~~~~~~~~

* **Normal Mode**: Selection and editing operations available
* **Building Creation**: Instructions shown, other operations disabled
* **Multi-Selection**: Group operations available

Selection-Dependent Features
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

* **No Selection**: Building creation tools enabled
* **Single Selection**: Individual building editing available
* **Multi-Selection**: Group operations like simultaneous height setting

Map-Dependent Display
~~~~~~~~~~~~~~~~~~~~~~~

* **No Basemap**: Simple grid background, better performance
* **With Basemap**: Geographic context, tile loading indicators
* **With GeoTIFF**: Additional overlay controls available

Customization
----------------

Color Settings
~~~~~~~~~~~~~~~~~

Access through Edit → Color Settings to customize:

* **Building Colors**: Fill and border colors for normal and selected states
* **Interface Colors**: Grid, handles, preview colors
* **Basemap Colors**: Empty tile and border colors

The color dialog provides:

* **Predefined Colors**: Common color choices
* **Manual Input**: RGB/RGBA values and hex codes  
* **Opacity Control**: Alpha channel adjustment
* **Preview**: Real-time color preview

Application Preferences
~~~~~~~~~~~~~~~~~~~~~~~~

Various settings are automatically saved:

* **Window Size**: Application window dimensions
* **Last Location**: Map center coordinates
* **Zoom Level**: Current view zoom
* **Snap Setting**: Whether snapping is enabled
* **Storey Height**: Default height per storey
