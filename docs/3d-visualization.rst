3D Visualization
==================

This chapter covers CitySketch's 3D visualization capabilities,
allowing you to view and export your building models in three dimensions using OpenGL rendering.

3D View Overview
------------------

3D Visualization Features
~~~~~~~~~~~~~~~~~~~~~~~~~~~~

CitySketch's 3D viewer provides:

- **Real-time 3D Rendering**: Interactive OpenGL-based visualization
- **Building Extrusion**: 2D footprints automatically converted to 3D volumes
- **Camera Controls**: Mouse-driven navigation around the 3D scene
- **Selective Display**: View all buildings or just selected ones
- **Ground Plane**: Grid reference for spatial orientation
- **Snapshot Export**: Save 3D views as image files

System Requirements
~~~~~~~~~~~~~~~~~~~~~

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
--------------------

Opening the 3D Viewer
~~~~~~~~~~~~~~~~~~~~~~~

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
------------------

Window Layout
~~~~~~~~~~~~~~~

**Main Components**:
- **3D Viewport**: Large OpenGL rendering area
- **Control Panel**: Instructions and buttons at bottom
- **Camera Position**: Calculated from building positions

**Window Controls**:
- **Save Snapshot**: Exports current 3D view as image
- **Close**: Returns to 2D editing interface

Display Elements
~~~~~~~~~~~~~~~~~

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
------------------------

Mouse Controls
~~~~~~~~~~~~~~~~

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
~~~~~~~~~~~~~~~

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


Rendering Modes
~~~~~~~~~~~~~~~~~~~

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
-----------------------

Rendering Quality
~~~~~~~~~~~~~~~~~~~~~

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
-----------------

Saving 3D Images
~~~~~~~~~~~~~~~~~~

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


Troubleshooting 3D Issues
---------------------------

Common 3D Problems
~~~~~~~~~~~~~~~~~~~~

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

