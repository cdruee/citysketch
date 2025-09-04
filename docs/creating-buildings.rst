Creating Buildings
===================

This chapter covers all aspects of creating buildings in CitySketch,
from basic rectangular structures to advanced rotated buildings with
precise dimensions.

Building Creation Modes
------------------------

CitySketch offers two primary building creation modes,
each optimized for different building types:

Block Building Mode
~~~~~~~~~~~~~~~~~~~~~

**Activation**:
Click "Add Block Building" button or use keyboard shortcut

**Best For**:
- Rectangular buildings
- Buildings aligned with streets or property lines  
- Structures requiring precise corner placement
- Buildings that need rotation after creation

**Creation Process**:
1. First click sets the anchor corner (lower left corner)
2. Mouse movement (up / right) shows building preview
3. Second click completes the building

Round Building Mode  
~~~~~~~~~~~~~~~~~~~~~

**Activation**: Click "Add Round Building" button

**Best For**:
- Circular or round buildings
- Towers, silos, and cylindrical structures
- Buildings where radius is the primary dimension
- Quick creation of symmetrical structures

**Creation Process**:
1. First click sets the center point
2. Mouse movement shows circular preview  
3. Second click sets the radius and completes the building

Using Snap-to-Grid
~~~~~~~~~~~~~~~~~~~~

**Enable Snapping**: Toggle the "Snap: ON/OFF" button in toolbar

**Snap Targets**:
- Corners of existing buildings
.. - Edges of existing buildings
.. - Grid intersections *(when no basemap is active)*

**Snap Threshold**: Approximately 15 pixels at current zoom level


Advanced Building Techniques
------------------------------

Creating Rotated Buildings
~~~~~~~~~~~~~~~~~~~~~~~~~~~~

**Method 1: Rotation During Creation**

1. Start building creation normally
2. After first click, hold Ctrl key
3. Move mouse to set both size and rotation
4. Click to complete

**Method 2: Rotation After Creation**  

1. Create building normally (rectangular)
2. Select the building
3. Hold Ctrl and drag corner handles to rotate

**Rotation Reference Point**:
- Block buildings rotate around first corner (anchor)
- Rotation angle displayed in status bar
- Angles measured from positive X-axis (eastward)

Creating Building Complexes
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

**Connected Buildings**:
1. Create first building
2. With snap enabled, start second building from first building's corner
3. Snap indicators will guide precise alignment

**Courtyard Buildings**:
1. Create outer perimeter buildings first
2. Use snap to align inner walls
3. Consider using Rectangle Select to modify multiple buildings

**Regular Patterns**:
1. Create one building as template
2. Use copy/paste operations *(via selection and movement)*
3. Leverage snap system for regular spacing

Building Properties
--------------------

Default Properties
~~~~~~~~~~~~~~~~~~~~~

New buildings are created with default properties:

* **Stories**: 3 floors
* **Height**: 9.9 meters (3 floors × 3.3m default storey height)
* **Rotation**: 0 degrees (aligned with coordinate axes)
* **Fill Color**: Light gray (configurable)
* **Border Color**: Dark gray (configurable)

Setting Initial Height
~~~~~~~~~~~~~~~~~~~~~~~~~

**Keyboard Shortcuts**: Press 1-9 immediately after creation to set stories

**Height Dialog**: 
1. Select the building
2. Click "Set Height" button  
3. Choose stories or enter exact height in meters

**Storey Height Configuration**:
- Set default through Edit → Set Storey Height
- Affects calculation: Total Height = Stories × Storey Height
- Global setting for all new buildings

Building Identification
~~~~~~~~~~~~~~~~~~~~~~~~~

**Automatic ID Assignment**:
- Each building gets a unique UUID identifier
- IDs are used for export formats and data consistency
- Invisible to user but important for file integrity

**Visual Representation**:
- Height shown as text label (e.g., "3F" for 3 floors)
- Label positioned at building center
- White text with shadow for readability


Troubleshooting Creation Issues
---------------------------------

Common Problems
~~~~~~~~~~~~~~~~~~

**Building Won't Complete**:
- Check if second click is in valid area
- Ensure minimum size requirements met
- Verify not clicking on interface elements

**Preview Not Showing**:
- Confirm you're in building creation mode
- Check zoom level (may be too far out)
- Verify mouse is over canvas area

**Snapping Not Working**:
- Check snap toggle is enabled
- Ensure you're within snap threshold
- Other buildings must exist for corner snapping

**Building Appears Wrong Size**:
- Check coordinate system and units
- Verify basemap scaling is correct
- Consider zoom level when judging size

**Rotation Issues**:
- Hold Ctrl key while moving mouse
- First click sets rotation anchor point
- Release Ctrl to return to scaling mode

Quality Control
-----------------

Validation During Creation
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

**Size Validation**:
- Minimum building size: 1m × 1m
- Maximum practical size: 1000m × 1000m
- Warning for unusually large or small buildings

**Position Validation**:
- Buildings can overlap (intentionally supported)
- No automatic collision detection
- Visual inspection recommended



Importing Reference Data
~~~~~~~~~~~~~~~~~~~~~~~~~~

**From AUSTAL Files**:
- Use File → Import from AUSTAL
- Provides building positions and heights
- Good starting point for atmospheric modeling

**From Geographic Data** *(with GeoTIFF)*:
- Load aerial imagery as reference
- Trace building outlines visually
- Match heights to shadow analysis or known data


Data Exchange Formats
~~~~~~~~~~~~~~~~~~~~~~~~~

**CitySketch Native (.csp)**:
- Preserves all editor settings
- Includes color and display preferences
- Best for continued editing

.. **CityJSON (.json)**:
    - International standard format
    - Compatible with other CityJSON tools
    - Good for data exchange

**AUSTAL (austal.txt)**:
- Atmospheric modeling format
- Contains building geometry and properties
- Used with AUSTAL simulation software
