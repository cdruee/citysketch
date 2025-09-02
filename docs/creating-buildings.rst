# Creating Buildings

===================

This chapter covers all aspects of creating buildings in CitySketch,
from basic rectangular structures to advanced rotated buildings with
precise dimensions.

Building Creation Modes
=========================

CitySketch offers two primary building creation modes,
each optimized for different building types:

Block Building Mode
--------------------

**Activation**:
Click "Add Block Building" button or use keyboard shortcut

**Best For**:
- Rectangular buildings
- Buildings aligned with streets or property lines  
- Structures requiring precise corner placement
- Buildings that need rotation after creation

**Creation Process**:
1. First click sets the anchor corner
2. Mouse movement shows building preview
3. Second click completes the building

Round Building Mode  
--------------------

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

Building Creation Workflow
===========================

Step-by-Step Creation
---------------------

1. **Select Creation Mode**
   
   Choose the appropriate building type from the toolbar.

2. **Position First Point**
   
   * **Block Building**: Click at the desired corner position
   * **Round Building**: Click at the center point
   * Use snapping (if enabled) for precise alignment

3. **Size the Building**
   
   * Move the mouse to adjust building size
   * **Block Building**: Diagonal from first corner to opposite corner
   * **Round Building**: Distance from center determines radius

4. **Apply Rotation** *(Block buildings only)*
   
   * Hold Ctrl during sizing to enable rotation mode
   * Building rotates around the first corner (anchor point)
   * Release Ctrl to return to scaling mode

5. **Complete Creation**
   
   * Click to finalize the building geometry
   * Building is automatically selected for further editing
   * Status bar confirms creation

Visual Feedback During Creation
-------------------------------

**Preview Display**:
- Semi-transparent green fill shows building outline
- Dotted border indicates the building is being created
- Real-time updates as you move the mouse

**Snap Indicators**:
- Cursor snaps to nearby corners and edges
- Visual highlighting of snap targets
- Distance threshold configurable in settings

Precision Building Creation
===========================

Using Snap-to-Grid
-------------------

**Enable Snapping**: Toggle the "Snap: ON/OFF" button in toolbar

**Snap Targets**:
- Corners of existing buildings
- Edges of existing buildings *(planned feature)*
- Grid intersections *(when no basemap is active)*

**Snap Threshold**: Approximately 15 pixels at current zoom level

**Benefits**:
- Ensures precise alignment between buildings
- Reduces measurement errors
- Speeds up creation of building complexes

Coordinate-Based Placement
--------------------------

For precise placement using coordinates:

1. **Plan Your Coordinates**: Determine exact positions in meters
2. **Use Status Bar**: Monitor mouse position in world coordinates  
3. **Position Carefully**: First click establishes the reference point
4. **Scale Precisely**: Use coordinate readout to achieve exact dimensions

.. tip::
   The status bar shows real-time coordinates as you move the mouse. Use this to achieve precise building dimensions.

Advanced Building Techniques
=============================

Creating Rotated Buildings
---------------------------

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
----------------------------

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
===================

Default Properties
-------------------

New buildings are created with default properties:

* **Stories**: 3 floors
* **Height**: 9.9 meters (3 floors × 3.3m default storey height)
* **Rotation**: 0 degrees (aligned with coordinate axes)
* **Fill Color**: Light gray (configurable)
* **Border Color**: Dark gray (configurable)

Setting Initial Height
----------------------

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
-----------------------

**Automatic ID Assignment**:
- Each building gets a unique UUID identifier
- IDs are used for export formats and data consistency
- Invisible to user but important for file integrity

**Visual Representation**:
- Height shown as text label (e.g., "3F" for 3 floors)
- Label positioned at building center
- White text with shadow for readability

Common Creation Patterns
=========================

Urban Building Types
---------------------

**Residential Buildings**:
- Typical size: 10m × 15m 
- Stories: 2-4 floors
- Height: 6.6m - 13.2m
- Often aligned with street grid

**Commercial Buildings**:
- Larger footprint: 20m × 30m or more
- Stories: 1-2 floors typically
- Height: 4-8m 
- May require custom height settings

**High-Rise Buildings**:
- Smaller footprint: 15m × 25m
- Stories: 10+ floors
- Height: 30m+
- Use custom height dialog for precision

**Industrial Buildings**:
- Large footprint: 40m × 60m or larger
- Stories: 1-2 floors typically
- Height: 8-15m (high ceilings)
- Often rectangular, aligned with property lines

Rural Building Types
--------------------

**Farm Buildings**:
- Barns: 20m × 40m, 1-2 stories, 8-12m height
- Silos: Use round building mode, 5-8m radius
- Houses: 8m × 12m, 1-2 stories, 3-7m height

**Storage Buildings**:
- Warehouses: Large rectangular, single story
- Grain storage: Round buildings work well
- Equipment sheds: Small rectangular buildings

Troubleshooting Creation Issues
===============================

Common Problems
---------------

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

Performance Considerations
--------------------------

**Large Number of Buildings**:
- Disable basemap for better performance
- Use "Zoom Fit" periodically to optimize view
- Consider working in sections for complex projects

**Complex Building Shapes**:
- CitySketch supports rectangles and circles only
- Complex shapes require multiple buildings
- Use building groups for related structures

Quality Control
================

Validation During Creation
--------------------------

**Size Validation**:
- Minimum building size: 1m × 1m
- Maximum practical size: 1000m × 1000m
- Warning for unusually large or small buildings

**Position Validation**:
- Buildings can overlap (intentionally supported)
- No automatic collision detection
- Visual inspection recommended

Best Practices
---------------

**Planning Your Model**:
1. Start with largest, most important buildings
2. Work from general to specific
3. Use consistent storey heights across project
4. Consider final export format requirements

**Accuracy Guidelines**:
- Real-world building dimensions preferred
- Use satellite imagery or maps for reference
- Measure from building footprints, not roof lines
- Consider building purpose when setting height

**Organization Tips**:
- Group related buildings by selecting together
- Use consistent naming/height conventions
- Save frequently during large modeling sessions
- Export backups in multiple formats

Working with Templates
======================

Creating Building Templates
---------------------------

While CitySketch doesn't have formal templates, you can create reusable patterns:

1. **Create Master Building**: Build one example with desired properties
2. **Duplicate Process**: 
   - Create new building near the template
   - Copy dimensions by visual reference
   - Set same height using number keys
3. **Modify as Needed**: Adjust size and rotation for each instance

**Template Categories**:
- Single-family homes
- Apartment blocks  
- Commercial buildings
- Industrial structures

Importing Reference Data
------------------------

**From AUSTAL Files**:
- Use File → Import from AUSTAL
- Provides building positions and heights
- Good starting point for atmospheric modeling

**From Geographic Data** *(with GeoTIFF)*:
- Load aerial imagery as reference
- Trace building outlines visually
- Match heights to shadow analysis or known data

Integration with External Tools
===============================

Workflow Integration
--------------------

**GIS Integration**:
- Export building data to CityJSON format
- Import into QGIS or ArcGIS for analysis
- Use coordinate reference system consistently

**3D Modeling**:
- CityJSON can be imported into Blender
- Building heights provide extrusion data
- Coordinates enable precise positioning

**Atmospheric Modeling**:
- AUSTAL export provides building data
- Heights and positions used for airflow simulation
- Building arrangement affects modeling results

Data Exchange Formats
----------------------

**CitySketch Native (.csp)**:
- Preserves all editor settings
- Includes color and display preferences
- Best for continued editing

**CityJSON (.json)**:
- International standard format
- Compatible with other CityJSON tools
- Good for data exchange

**AUSTAL (austal.txt)**:
- Atmospheric modeling format
- Contains building geometry and properties
- Used with AUSTAL simulation software

Next Steps
===========

After mastering building creation:

1. Learn :doc:`editing-buildings` for modifying existing structures
2. Explore :doc:`basemaps-geotiff` for geographic context
3. Try :doc:`3d-visualization` to see your buildings in 3D
4. Review :doc:`file-formats` for export options

.. note::
   Practice with simple buildings first before attempting complex urban models. The interface is designed to be intuitive, but precision comes with experience.