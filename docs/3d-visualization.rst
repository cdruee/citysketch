# 3D Visualization

==================

This chapter covers CitySketch's 3D visualization capabilities, allowing you to view and export your building models in three dimensions using OpenGL rendering.

3D View Overview
================

3D Visualization Features
-------------------------

CitySketch's 3D viewer provides:

- **Real-time 3D Rendering**: Interactive OpenGL-based visualization
- **Building Extrusion**: 2D footprints automatically converted to 3D volumes
- **Camera Controls**: Mouse-driven navigation around the 3D scene
- **Selective Display**: View all buildings or just selected ones
- **Ground Plane**: Grid reference for spatial orientation
- **Snapshot Export**: Save 3D views as image files

System Requirements
-------------------

**Required Dependencies**:
- PyOpenGL: `pip install PyOpenGL PyOpenGL_accelerate`
- Compatible graphics drivers with OpenGL support
- Hardware-accelerated graphics recommended

**Performance Requirements**:
- Modern graphics card (Intel HD Graphics 4000+ or equivalent)
- Updated graphics drivers
- At least 512MB graphics memory for complex scenes
- Windows DirectX 9.0c+ / Linux OpenGL 2.1+ / macOS OpenGL 2.1+

Accessing 3D View
=================

Opening the 3D Viewer
---------------------

**Methods to Open**:
1. **Keyboard Shortcut**: Press F3
2. **Menu**: Edit → Show 3D View
3. **Ensure Requirements**: OpenGL support must be available

**Prerequisites**:
- At least one building must exist in the project
- PyOpenGL libraries must be installed
- Graphics drivers must support OpenGL

**Dialog Behavior**:
- Opens as modal dialog window
- Blocks access to main interface while open
- Must be closed to continue 2D editing

3D View Interface
=================

Window Layout
-------------

**Main Components**:
- **3D Viewport**: Large OpenGL rendering area
- **Control Panel**: Instructions and buttons at bottom
- **Camera Position**: Calculated from building positions

**Window Controls**:
- **Save Snapshot**: Exports current 3D view as image
- **Close**: Returns to 2D editing interface

Display Elements
----------------

**Buildings**:
- **Selected Buildings**: Solid blue rendering with faces and edges
- **Unselected Buildings**: Wireframe outline only (if any exist)
- **Transparency**: Semi-transparent rendering for context buildings

**Ground Plane**:
- Grid lines for spatial reference
- Automatically sized based on building extents
- Helps with depth perception and orientation

**Lighting**:
- Ambient lighting for general visibility
- No shadows or complex lighting effects
- Optimized for clarity rather than realism

3D Navigation Controls
======================

Mouse Controls
--------------

**Camera Rotation**:
- **Left Click + Drag**: Rotate view around buildings
- **Horizontal Drag**: Change azimuth angle (rotate left/right)
- **Vertical Drag**: Change elevation angle (look up/down)
- **Elevation Range**: -89° to +89° (prevents flipping upside down)

**Camera Zoom**:
- **Mouse Wheel Up**: Zoom in (move camera closer)
- **Mouse Wheel Down**: Zoom out (move camera further away)
- **Zoom Range**: 10 to 5000 meters from center point
- **Center Point**: Automatically calculated from building positions

Camera System
-------------

**Spherical Coordinates**:
- Camera orbits around a center point using spherical coordinates
- **Distance**: How far camera is from center
- **Azimuth**: Horizontal rotation angle around center
- **Elevation**: Vertical angle (looking up/down)

**Automatic Positioning**:
- Center point calculated from all displayed buildings
- Initial distance set to show all buildings comfortably
- Initial angles: 45° azimuth, 30° elevation

**Navigation Limits**:
- Minimum distance prevents camera going inside buildings
- Maximum distance provides wide-area context
- Elevation limits prevent camera inversion

Building Rendering
==================

3D Geometry Generation
----------------------

**Extrusion Process**:
1. Take 2D building footprint (rotated rectangle)
2. Calculate corner positions in 3D space
3. Create bottom face at ground level (Z=0)
4. Create top face at building height
5. Connect corners with vertical side faces
6. Generate face triangulation for OpenGL

**Coordinate Conversion**:
- 2D world coordinates become X,Y in 3D
- Building height becomes Z coordinate
- Rotation preserved in 3D representation
- All measurements remain in meters

Rendering Modes
---------------

**Selected Buildings (Solid)**:
- Full 3D volume rendering with faces
- Blue color matching 2D interface
- Opaque rendering for main focus
- Edge outlines for definition

**Unselected Buildings (Wireframe)**:
- Edge-only rendering without faces
- Gray color for context only
- Semi-transparent for reduced visual weight
- Helps show relationship to selected buildings

**No Selection (All Solid)**:
- When no buildings selected, all render as solid
- All buildings receive focus treatment
- Useful for overall project visualization
- Same blue color scheme throughout

Visual Quality Settings
=======================

Rendering Quality
-----------------

**OpenGL Settings**:
- Depth testing enabled for proper occlusion
- Blending enabled for transparency effects
- Polygon offset to prevent Z-fighting
- Anti-aliasing depends on graphics driver settings

**Performance vs Quality**:
- Optimized for real-time interaction
- Simplified lighting model for speed
- No texture mapping or complex materials
- Focus on geometric accuracy over visual realism

**Color Scheme**:
- Matches 2D interface colors for consistency
- Blue for selected buildings (same as 2D)
- Gray for context buildings
- Light gray background for contrast

Snapshot Export
===============

Saving 3D Images
----------------

**Export Process**:
1. Position 3D view as desired using mouse controls
2. Click "Save Snapshot" button or press Ctrl+P
3. Choose file location and format in dialog
4. Image captures exactly what's visible in 3D window

**Supported Formats**:
- **PNG**: Lossless compression, best quality
- **JPEG**: Smaller file size, good for sharing
- **Automatic Extension**: .png added if no extension specified

**Image Properties**:
- Resolution matches 3D window size
- Full color depth (24-bit RGB)
- No compression artifacts with PNG format
- Suitable for presentations and documentation

Export Quality Considerations
-----------------------------

**Maximizing Image Quality**:
1. Resize 3D window to desired output resolution
2. Position camera for best viewing angle
3. Ensure all desired buildings are visible
4. Use PNG format for highest quality
5. Check image opens correctly after saving

**Typical Use Cases**:
- Project presentations and reports
- Documentation of building layouts
- Stakeholder communications
- Design review materials

3D View Limitations
===================

Current Limitations
-------------------

**Rendering Limitations**:
- Simple geometric shapes only (no architectural details)
- No texture mapping or material properties
- Simplified lighting (no shadows or reflections)
- No terrain or landscape features

**Interactive Limitations**:
- Read-only view (no editing in 3D)
- Cannot select or modify buildings in 3D
- No measurement tools in 3D space
- No cross-sections or cutaway views

**Export Limitations**:
- Image export only (no 3D model formats)
- Single viewpoint per export
- No animation or video export
- Resolution limited by window size

Performance Considerations
==========================

Optimizing 3D Performance
-------------------------

**For Better Performance**:
- Close unnecessary applications to free GPU memory
- Update graphics drivers to latest versions
- Work with smaller building selections when possible
- Reduce window size if frame rate is poor

**Performance Indicators**:
- Smooth rotation and zooming indicate good performance
- Stuttering or delays suggest performance issues
- Very slow opening indicates graphics compatibility problems

**Hardware Recommendations**:
- Dedicated graphics card preferred over integrated
- At least 1GB graphics memory for large projects
- Recent OpenGL driver support (last 5 years)

Troubleshooting 3D Issues
=========================

Common 3D Problems
------------------

**3D Window Won't Open**:
- Check PyOpenGL installation: `pip install PyOpenGL`
- Verify graphics drivers are current
- Test basic OpenGL support with other applications
- Try software rendering if hardware fails

**Display Problems**:
- Buildings appear as wireframes only: Check selection status
- Black or corrupted display: Graphics driver issue
- Very slow response: Performance/compatibility problem
- Window appears but is empty: OpenGL context creation failed

**Export Problems**:
- Snapshot button disabled: 3D rendering not properly initialized
- Save fails: Check file permissions and disk space
- Image appears black: OpenGL framebuffer read error
- Wrong resolution: Resize window before taking snapshot

Advanced 3D Features
====================

Camera Positioning Tips
-----------------------

**Effective Viewing Angles**:
- **45° elevation**: Good balance showing tops and sides of buildings
- **30° elevation**: More side detail, less roof area
- **60° elevation**: Emphasizes roof shapes and overall layout
- **Multiple angles**: Take snapshots from different viewpoints

**Composition Guidelines**:
- Position important buildings prominently in view
- Use ground plane grid for scale reference
- Consider background contrast for building visibility
- Frame view to show building relationships

Understanding Building Representation
-------------------------------------

**Height Accuracy**:
- 3D heights exactly match 2D height settings
- Story count visible through proportional height
- Useful for verifying height assumptions
- Helps identify unrealistic building proportions

**Geometric Accuracy**:
- Footprint shapes exactly match 2D drawings
- Rotation angles preserved in 3D space
- Building positions maintain precise relationships
- Scale reference helps verify real-world dimensions

Integration with 2D Workflow
============================

3D as Design Validation
-----------------------

**Design Review Process**:
1. Create buildings in 2D interface
2. Periodically check 3D view for overall appearance
3. Identify proportion or height issues
4. Return to 2D for corrections
5. Export 3D snapshots for documentation

**Quality Assurance**:
- 3D view reveals proportion problems not obvious in 2D
- Height relationships become clear in 3D context
- Building density and spacing easier to evaluate
- Overall project scale more apparent

3D for Communication
--------------------

**Stakeholder Presentations**:
- 3D images more intuitive than 2D plans
- Shows massing and overall development impact
- Helps non-technical audiences understand projects
- Supports zoning and planning discussions

**Technical Documentation**:
- 3D views complement 2D drawings in reports
- Multiple angles show different aspects
- Before/after comparisons for development projects
- Integration with other visualization tools

Future 3D Enhancements
======================

Planned Improvements
--------------------

While current 3D capabilities focus on core visualization needs, potential future enhancements could include:

- **Advanced Materials**: Texture mapping and material properties
- **Improved Lighting**: Shadow casting and realistic lighting
- **Animation Support**: Camera path animation and flythrough videos
- **Enhanced Export**: 3D model formats (OBJ, PLY, etc.)
- **Measurement Tools**: Distance and area measurement in 3D space

**Current Alternatives**:
For advanced 3D features, consider exporting to CityJSON format and importing into specialized 3D applications like Blender or professional GIS software.

Next Steps
==========

After mastering 3D visualization:

1. Practice taking effective snapshots for different purposes
2. Integrate 3D review into your building creation workflow  
3. Learn :doc:`file-formats` for exporting 3D-compatible data
4. Explore :doc:`technical/architecture` for understanding 3D rendering pipeline

.. note::
   The 3D view is designed as a visualization and validation tool rather than a full 3D modeling environment. It excels at showing spatial relationships and overall project context.