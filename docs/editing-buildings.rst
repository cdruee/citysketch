Editing Buildings
=================

This chapter covers all aspects of modifying existing buildings in CitySketch.

Building Selection
------------------

Single Building Selection
~~~~~~~~~~~~~~~~~~~~~~~~~

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
~~~~~~~~~~~~~~~~~~~~~~~~~~~

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
---------------------

Height and Stories
~~~~~~~~~~~~~~~~~~

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
-------------------

Moving Buildings
~~~~~~~~~~~~~~~~~~

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
~~~~~~~~~~~~~~~~~~~

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
~~~~~~~~~~~~~~~~~~

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
---------------------------

Working with Building Groups
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

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




During Editing
~~~~~~~~~~~~~~~~

1. **Save Frequently**: Use Ctrl+S every few minutes
2. **Check Work**: Periodically zoom out to see overall context
3. **Validate Properties**: Verify heights and dimensions are reasonable
4. **Use References**: Compare with basemap or GeoTIFF data
5. **Maintain Consistency**: Use standard procedures for similar buildings

