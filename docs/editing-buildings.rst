# Editing Buildings

=================

This chapter covers all aspects of modifying existing buildings in CitySketch, from basic selection and property changes to advanced transformation operations.

Building Selection
===================

Single Building Selection
--------------------------

**Mouse Click Selection**:
- Click on any part of a building to select it
- Selected buildings appear with blue fill and blue outline
- Selection handles (squares) appear at corners
- Building remains selected until you select something else

**Visual Indicators**:
- **Selected**: Blue fill with blue border
- **Unselected**: Gray fill with dark gray border
- **Corner Handles**: Blue squares at building corners

Multiple Building Selection
---------------------------

**Adding to Selection (Ctrl+Click)**:
1. Select first building with normal click
2. Hold Ctrl key and click additional buildings
3. Each clicked building toggles in/out of selection
4. All selected buildings show blue appearance

**Rectangle Selection (Shift+Drag)**:
1. Hold Shift key and start dragging on empty canvas
2. Drag to create selection rectangle
3. All buildings completely inside rectangle are selected
4. Partial overlap doesn't select buildings

**Selection Management**:
- Click on empty space to deselect all
- Ctrl+click on selected building to remove from selection
- Selection persists across mode changes

Building Properties
===================

Height and Stories
------------------

**Quick Height Setting**:
- Select building(s)
- Press number keys 1-9 to set story count
- Height automatically calculated: Stories × Storey Height
- Default storey height: 3.3 meters (configurable)

**Precise Height Setting**:
1. Select buildings
2. Click "Set Height" button in toolbar
3. Choose from dialog options:

   - **Stories**: Integer number of floors
   - **Height**: Exact height in meters

4. Changes apply to all selected buildings

**Height Dialog Features**:
- Live update between stories and height values
- Validation prevents negative values
- Remembers last used storey height setting

Building Geometry
=================

Moving Buildings
----------------

**Mouse Drag Movement**:
1. Select building(s) to move
2. Click and drag any selected building
3. All selected buildings move together
4. Snapping applies to movement (if enabled)

**Snap-Assisted Movement**:
- Enable snapping with toolbar toggle
- Buildings snap to corners of other buildings
- Snap threshold: approximately 15 pixels at current zoom
- Visual feedback shows snap targets

**Precision Movement**:
- Use status bar coordinates for exact positioning
- Move in small increments for fine adjustment
- Consider using snap points for alignment

Resizing Buildings
------------------

**Corner Handle Resizing**:
1. Select building (single selection only)
2. Click and drag corner handles (blue squares)
3. Different corners provide different resize behavior:

   - **Corner 0** (bottom-left): Anchor point, resize from here
   - **Other corners**: Resize relative to anchor point

**Resize Modes**:
- **Normal Mode**: Drag handles to scale building
- **Rotation Mode**: Hold Ctrl while dragging to rotate
- Handle appearance changes: squares (scale) vs circles (rotate)

**Aspect Ratio**:
- Free-form resizing - no locked aspect ratio
- Width and height can be adjusted independently
- Minimum size constraints prevent zero-dimension buildings

Rotating Buildings
------------------

**Rotation During Resize**:
1. Select single building
2. Hold Ctrl key
3. Corner handles become circles
4. Drag any handle to rotate building around anchor point
5. Release Ctrl to return to normal resize mode

**Rotation Properties**:
- Rotation always around first corner (anchor point)
- Angle displayed in status bar during rotation
- Buildings can be rotated to any angle
- Rotation preserved when saving/loading projects

**Rotation Limitations**:
- Only single buildings can be rotated (not groups)
- Rectangle selection mode doesn't support rotation
- AUSTAL export approximates rotated buildings

Advanced Editing Operations
============================

Working with Building Groups
-----------------------------

**Group Selection Benefits**:
- Simultaneous property changes (height, stories)
- Coordinated movement operations
- Consistent formatting across related buildings

**Group Operations**:
- **Height Setting**: Number keys affect all selected buildings
- **Movement**: Drag any selected building to move entire group  
- **Deletion**: Delete key removes all selected buildings
- **Property Dialogs**: Changes apply to entire selection

**Group Editing Limitations**:
- Rotation only works on single buildings
- Corner handles only appear for single selection
- Some operations require individual building selection

Building Duplication Workflow
------------------------------

While CitySketch doesn't have a built-in copy/paste function, you can duplicate buildings:

1. **Visual Reference Method**:
   - Select existing building to copy
   - Note dimensions and properties
   - Create new building nearby
   - Match size visually using handles
   - Set same height using number keys

2. **Template Building Approach**:
   - Create one "template" building with desired properties
   - Use it as reference for creating similar buildings
   - Maintain consistent proportions across project

Precision Editing
==================

Using Snap System
------------------

**Snap Targets**:
- Corners of existing buildings
- Building edges (planned feature)
- Grid intersections (when basemap disabled)

**Snap Configuration**:
- Toggle with "Snap: ON/OFF" toolbar button
- Snap threshold: ~15 pixels at current zoom level
- Visual feedback highlights snap points

**Snap Benefits**:
- Ensures precise building alignment
- Reduces measurement errors
- Speeds up complex building layouts
- Creates clean building arrangements

Coordinate-Based Editing
------------------------

**Status Bar Coordinates**:
- Real-time display of mouse position
- World coordinates in meters
- Reference for precise positioning

**Measurement Techniques**:
1. Note starting coordinates from status bar
2. Move building/handle to desired position
3. Use coordinate difference for exact measurements
4. Verify final position matches requirements

Visual Editing Aids
--------------------

**Zoom Controls**:
- Mouse wheel for detailed editing
- Zoom in for precision work
- Zoom out for overall context
- "Zoom Fit" to see all buildings

**Grid System**:
- Background grid for alignment reference
- Grid spacing adapts to zoom level
- More visible when basemap disabled
- Helps with regular building patterns

Error Prevention and Recovery
=============================

Common Editing Mistakes
------------------------

**Accidental Deletion**:
- **Prevention**: Careful selection before pressing Delete
- **Recovery**: Use Ctrl+Z undo (planned feature)
- **Workaround**: Recreate building using visual reference

**Unintended Movement**:
- **Cause**: Dragging building instead of empty space for panning
- **Prevention**: Click on empty areas for panning
- **Recovery**: Move building back to original position

**Wrong Building Selected**:
- **Prevention**: Check blue highlighting before operations
- **Recovery**: Click empty space to deselect, then reselect correct building

**Rotation Gone Wrong**:
- **Cause**: Accidentally holding Ctrl during resize
- **Recovery**: Continue rotation until building is properly aligned
- **Alternative**: Delete and recreate building

Validation and Quality Control
------------------------------

**Size Validation**:
- Check building dimensions make sense for intended use
- Compare with real-world references
- Verify heights are appropriate for building type

**Position Validation**:
- Ensure buildings are in correct geographic locations
- Use basemap or GeoTIFF overlay for reference
- Check alignment with streets and property boundaries

**Consistency Checks**:
- Verify similar buildings have similar heights
- Check building orientation matches site context
- Ensure regular patterns are maintained

Advanced Editing Techniques
============================

Creating Building Complexes
----------------------------

**Connected Buildings**:
1. Create first building
2. With snap enabled, position second building corner at first building's corner
3. Snap system ensures perfect alignment
4. Repeat for additional connected buildings

**Courtyard Layouts**:
1. Create perimeter buildings first
2. Use snap to align inner edges
3. Consider sight lines and access patterns
4. Maintain consistent building heights around courtyard

**Regular Grids**:
1. Create template building with desired properties
2. Use visual reference to create similar buildings
3. Maintain consistent spacing between buildings
4. Use snap system for alignment

Working with Different Building Types
-------------------------------------

**Residential Buildings**:
- Typical sizes: 8-15m × 10-25m
- Heights: 2-4 stories (6.6-13.2m)
- Regular patterns in subdivisions
- Alignment with property boundaries

**Commercial Buildings**:
- Larger footprints: 20-50m × 30-100m  
- Lower heights: 1-3 stories (4-10m)
- Alignment with streets and parking
- Consider loading dock access

**Industrial Buildings**:
- Very large footprints: 50-200m × 100-400m
- Single story with high ceilings: 8-15m
- Regular spacing for truck access
- Alignment with rail lines or highways

Editing Performance Optimization
=================================

Efficient Editing Workflows
----------------------------

**Start with Largest Buildings**:
- Create major structures first
- Add smaller buildings for detail
- Use major buildings as reference points

**Work in Sections**:
- Focus on one area at a time
- Complete sections before moving on
- Use zoom controls to work at appropriate detail level

**Use Consistent Methods**:
- Develop standard procedures for similar buildings
- Use same height settings for building types
- Maintain consistent orientation patterns

Managing Large Projects
-----------------------

**Performance Considerations**:
- Disable basemap during intensive editing
- Work at higher zoom levels for better performance
- Close 3D view when not needed
- Save frequently to prevent data loss

**Organization Strategies**:
- Group related buildings during selection
- Work on similar building types together
- Document building standards and conventions
- Export sections for backup

Integration with Reference Data
===============================

Using Basemap for Editing Context
----------------------------------

**Satellite Imagery**:
- Provides real building footprints
- Shows relationship to surrounding features
- Helps verify building positions and sizes
- Useful for tracing existing structures

**Street Maps**:
- Shows road network and property boundaries
- Helps align buildings with street grid
- Provides address and location context
- Useful for navigation and planning

Using GeoTIFF Overlays
----------------------

**Site Plans**:
- Architectural drawings as overlays
- Precise building positioning
- Detailed site context
- Property boundary information

**Aerial Photography**:
- High-resolution building details
- Shadow analysis for height estimation
- Vegetation and terrain context
- Current site conditions

Editing Workflow Best Practices
================================

Pre-Editing Planning
---------------------

1. **Gather Reference Data**:
   - Site plans, aerial imagery, maps
   - Building dimension data
   - Height information from various sources

2. **Set Up Environment**:
   - Configure geographic center
   - Load appropriate basemap
   - Set default storey height
   - Enable snapping

3. **Plan Building Order**:
   - Start with largest, most important buildings
   - Work from general to specific
   - Consider building relationships and dependencies

During Editing
--------------

1. **Save Frequently**: Use Ctrl+S every few minutes
2. **Check Work**: Periodically zoom out to see overall context
3. **Validate Properties**: Verify heights and dimensions are reasonable
4. **Use References**: Compare with basemap or GeoTIFF data
5. **Maintain Consistency**: Use standard procedures for similar buildings

Post-Editing Review
-------------------

1. **Overall Review**: Zoom to fit all buildings and check layout
2. **Detail Review**: Zoom in to check individual buildings
3. **Export Test**: Try exporting to target format
4. **3D View**: Check appearance in 3D visualization
5. **Documentation**: Record any assumptions or approximations made

Next Steps
===========

After mastering building editing:

1. Explore :doc:`basemaps-geotiff` for reference data integration
2. Learn :doc:`3d-visualization` to check your work in 3D
3. Review :doc:`file-formats` for export options
4. Check :doc:`keyboard-shortcuts` for editing efficiency tips

.. note::
   Advanced editing techniques become intuitive with practice. Start with simple projects and gradually work up to complex urban models.