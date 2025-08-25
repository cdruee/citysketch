import math
from turtle import color
from typing import Tuple, Optional

import wx
import wx.glcanvas

try:
    from OpenGL.GL import *
    from OpenGL.GLU import *
    import numpy as np

    OPENGL_SUPPORT = True
except ImportError:
    OPENGL_SUPPORT = False
    print("Warning: OpenGL support not available. "
          "Install PyOpenGL for 3D view.")

from .AppSettings import colorset

# =========================================================================

class Building3DViewer(wx.Dialog):
    """3D viewer for buildings using OpenGL"""

    def __init__(self, parent, buildings, selected_buildings):
        super().__init__(parent, title="3D Building View",
                         size=(800, 600),
                         style=wx.DEFAULT_DIALOG_STYLE | wx.RESIZE_BORDER)

        if not OPENGL_SUPPORT:
            wx.MessageBox("OpenGL support not available.\n\n"
                          "Please install PyOpenGL:\n"
                          "pip install PyOpenGL PyOpenGL_accelerate",
                          "OpenGL Missing",
                          wx.OK | wx.ICON_WARNING)
            self.EndModal(wx.ID_CANCEL)
            return

        self.buildings = buildings
        self.selected_buildings = selected_buildings

        # If no buildings selected, treat all as selected
        if len(selected_buildings) == 0:
            self.display_buildings = buildings
            self.wireframe_buildings = []
        else:
            self.display_buildings = selected_buildings.buildings if hasattr(
                selected_buildings, 'buildings') else list(
                selected_buildings)
            self.wireframe_buildings = [b for b in buildings if
                                        b not in self.display_buildings]

        # Calculate center point
        self.calculate_center()

        # Camera parameters
        self.camera_distance = self.calculate_initial_distance()
        self.camera_elevation = 30.0  # degrees
        self.camera_azimuth = 45.0  # degrees

        # Mouse interaction
        self.last_mouse_pos = None
        self.rotating = False

        # OpenGL initialization flag - ADD THIS
        self.opengl_initialized = False
        self.context = None

        self.create_ui()

        # Center on parent
        self.CenterOnParent()

        # Initialize OpenGL after showing the dialog - ADD THIS
        wx.CallAfter(self.delayed_opengl_setup)

    def calculate_center(self):
        """Calculate the center point of buildings to display"""
        if not self.display_buildings:
            self.center_x = self.center_y = 0
            return

        all_corners = []
        for building in self.display_buildings:
            all_corners.extend(building.get_corners())

        if all_corners:
            self.center_x = sum(
                corner[0] for corner in all_corners) / len(all_corners)
            self.center_y = sum(
                corner[1] for corner in all_corners) / len(all_corners)
        else:
            self.center_x = self.center_y = 0

    def calculate_initial_distance(self):
        """Calculate appropriate camera distance to fit all buildings"""
        if not self.display_buildings:
            return 100.0

        # Find bounding box
        all_corners = []
        for building in self.display_buildings:
            all_corners.extend(building.get_corners())

        if not all_corners:
            return 100.0

        min_x = min(corner[0] for corner in all_corners)
        max_x = max(corner[0] for corner in all_corners)
        min_y = min(corner[1] for corner in all_corners)
        max_y = max(corner[1] for corner in all_corners)

        # Calculate diagonal distance and add some margin
        diagonal = math.sqrt(
            (max_x - min_x) ** 2 + (max_y - min_y) ** 2)
        return max(100.0, diagonal * 1.5)

    def create_ui(self):
        """Create the user interface"""
        panel = wx.Panel(self)
        sizer = wx.BoxSizer(wx.VERTICAL)

        # Create OpenGL canvas
        attribList = [wx.glcanvas.WX_GL_RGBA,
                      wx.glcanvas.WX_GL_DOUBLEBUFFER,
                      wx.glcanvas.WX_GL_DEPTH_SIZE, 16]

        try:
            self.canvas = wx.glcanvas.GLCanvas(panel,
                                               attribList=attribList)
        except Exception as e:
            wx.MessageBox(f"Failed to create OpenGL canvas: {str(e)}",
                          "OpenGL Error", wx.OK | wx.ICON_ERROR)
            self.EndModal(wx.ID_CANCEL)
            return

        sizer.Add(self.canvas, 1, wx.EXPAND | wx.ALL, 5)

        # Control panel
        control_panel = wx.Panel(panel)
        control_sizer = wx.BoxSizer(wx.HORIZONTAL)

        # Instructions
        instructions = wx.StaticText(control_panel,
                                     label="Mouse: Drag to rotate view | Wheel: Zoom")
        control_sizer.Add(instructions, 1,
                          wx.ALIGN_CENTER_VERTICAL | wx.LEFT, 5)

        # Snapshot button
        snapshot_btn = wx.Button(control_panel,
                                 label="Save Snapshot (Ctrl+P)")
        snapshot_btn.Bind(wx.EVT_BUTTON, self.on_save_snapshot)
        control_sizer.Add(snapshot_btn, 0, wx.ALL, 5)

        # Close button
        close_btn = wx.Button(control_panel, wx.ID_CLOSE, "Close")
        close_btn.Bind(wx.EVT_BUTTON, self.on_close)
        control_sizer.Add(close_btn, 0, wx.ALL, 5)

        control_panel.SetSizer(control_sizer)
        sizer.Add(control_panel, 0, wx.EXPAND | wx.ALL, 5)

        panel.SetSizer(sizer)

        # Bind events
        self.canvas.Bind(wx.EVT_PAINT, self.on_paint)
        self.canvas.Bind(wx.EVT_SIZE, self.on_size)
        self.canvas.Bind(wx.EVT_LEFT_DOWN, self.on_mouse_down)
        self.canvas.Bind(wx.EVT_LEFT_UP, self.on_mouse_up)
        self.canvas.Bind(wx.EVT_MOTION, self.on_mouse_motion)
        self.canvas.Bind(wx.EVT_MOUSEWHEEL, self.on_mouse_wheel)
        self.Bind(wx.EVT_CHAR_HOOK, self.on_key_down)

    def delayed_opengl_setup(self):
        """Initialize OpenGL after the window is shown - ADD THIS METHOD"""
        try:
            # Create OpenGL context
            self.context = wx.glcanvas.GLContext(self.canvas)
            self.setup_opengl()
            self.opengl_initialized = True

            # Force a refresh to draw the scene
            self.Refresh()

        except Exception as e:
            wx.MessageBox(f"Failed to initialize OpenGL: {str(e)}",
                          "OpenGL Error", wx.OK | wx.ICON_ERROR)

    def setup_opengl(self):
        """Initialize OpenGL settings"""
        if not self.context:
            return

        self.canvas.SetCurrent(self.context)

        # Enable depth testing
        glEnable(GL_DEPTH_TEST)
        glDepthFunc(GL_LEQUAL)

        # Enable blending for transparency
        glEnable(GL_BLEND)
        glBlendFunc(GL_SRC_ALPHA, GL_ONE_MINUS_SRC_ALPHA)

        # Set background color
        glClearColor(0.9, 0.9, 0.9, 1.0)  # Light gray background

        # Enable polygon offset to avoid z-fighting
        glEnable(GL_POLYGON_OFFSET_FILL)
        glPolygonOffset(1.0, 1.0)

        # Setup initial projection
        self.setup_projection()

    def on_paint(self, event):
        """Handle paint events"""
        if not OPENGL_SUPPORT or not self.opengl_initialized:
            return

        try:
            self.canvas.SetCurrent(self.context)
            self.render()
            self.canvas.SwapBuffers()
        except Exception as e:
            print(f"Error in on_paint: {e}")

    def on_size(self, event):
        """Handle resize events"""
        if not OPENGL_SUPPORT or not self.opengl_initialized:
            event.Skip()
            return

        try:
            self.canvas.SetCurrent(self.context)
            size = self.canvas.GetSize()
            glViewport(0, 0, size.width, size.height)
            self.setup_projection()
            self.Refresh()
        except Exception as e:
            print(f"Error in on_size: {e}")

        event.Skip()

    def setup_projection(self):
        """Set up the projection matrix"""
        size = self.canvas.GetSize()
        if size.height == 0:
            return

        glMatrixMode(GL_PROJECTION)
        glLoadIdentity()

        aspect_ratio = float(size.width) / float(size.height)
        gluPerspective(45.0, aspect_ratio, 1.0, 10000.0)

    def render(self):
        """Render the 3D scene"""
        if not self.opengl_initialized:
            return

        try:
            glClear(GL_COLOR_BUFFER_BIT | GL_DEPTH_BUFFER_BIT)

            glMatrixMode(GL_MODELVIEW)
            glLoadIdentity()

            # Set up camera
            camera_x = self.center_x + self.camera_distance * math.cos(
                math.radians(self.camera_elevation)) * math.cos(
                math.radians(self.camera_azimuth))
            camera_y = self.center_y + self.camera_distance * math.cos(
                math.radians(self.camera_elevation)) * math.sin(
                math.radians(self.camera_azimuth))
            camera_z = self.camera_distance * math.sin(
                math.radians(self.camera_elevation))

            gluLookAt(camera_x, camera_y, camera_z,  # Camera position
                      self.center_x, self.center_y, 0,  # Look at point
                      0, 0, 1)  # Up vector

            # Draw ground plane
            self.draw_ground_plane()

            # Draw wireframe buildings (non-selected)
            for building in self.wireframe_buildings:
                self.draw_building_transparent(building)

            # Draw solid buildings (selected)
            for building in self.display_buildings:
                self.draw_building_solid(building)

        except Exception as e:
            print(f"Error in render: {e}")

    def draw_ground_plane(self):
        """Draw a simple ground plane"""
        if not self.display_buildings:
            return

        # Calculate ground plane size based on buildings
        all_corners = []
        for building in self.buildings:
            all_corners.extend(building.get_corners())

        if not all_corners:
            return

        min_x = min(corner[0] for corner in all_corners)
        max_x = max(corner[0] for corner in all_corners)
        min_y = min(corner[1] for corner in all_corners)
        max_y = max(corner[1] for corner in all_corners)

        # Expand a bit
        margin = (max_x - min_x + max_y - min_y) * 0.1
        min_x -= margin
        max_x += margin
        min_y -= margin
        max_y += margin

        # Draw ground grid
        glColor4f(0.8, 0.8, 0.8, 0.5)
        glBegin(GL_LINES)

        # Grid lines in X direction
        step = (max_x - min_x) / 20
        x = min_x
        while x <= max_x:
            glVertex3f(x, min_y, 0)
            glVertex3f(x, max_y, 0)
            x += step

        # Grid lines in Y direction
        step = (max_y - min_y) / 20
        y = min_y
        while y <= max_y:
            glVertex3f(min_x, y, 0)
            glVertex3f(max_x, y, 0)
            y += step

        glEnd()

    def draw_building(self, building,
                      color: Optional[int|float|Tuple|wx.Colour] = None,
                      solid: Optional[float|bool] = None,
                      faces: bool = True):
        """Draw a building as a solid with transparency"""
        corners = building.get_corners()
        height = building.height

        if solid is not None:
            solid = 0.7
        elif isinstance(solid, bool):
            solid = 1. if solid is True else 0.
        else:
            solid = 1.

        if isinstance(color, int):
            color = float(color) / 255.
        if isinstance(color, float):
            if color < 0.:
                rgb = (0.,) * 3
            elif color <= 1.:
                rgb = (color,) * 3
            else:
                rgb = (1.,) * 3
            alpha = solid
        elif isinstance(color, wx.Colour):
            rgb = (color.GetRed()/255.,
                   color.GetGreen()/255.,
                   color.GetBlue()/255.)
            alpha = color.GetAlpha()/255. * solid
        elif isinstance(color, tuple) and len(color) == 3:
                rgb = color
                alpha = solid
        elif isinstance(color, tuple) and len(color) == 4:
                rgb = color[0:3]
                alpha = color[3] * solid
        else:
            print(f"illegal color tuple {str(color)}")
            rgb = (0.5,) * 3
            alpha = 1.

        if faces:
            # Use semi-transparent blue for selected buildings (matching map colors)
            glColor4f(*rgb, alpha)  # Semi-transparent blue

            # Draw building faces
            glBegin(GL_POLYGON)
            # Bottom face (ground)
            for c in corners:
                glVertex3f(c[0], c[1], 0)
            glEnd()

            # Top face
            glBegin(GL_POLYGON)
            for c in corners:
                glVertex3f(c[0], c[1], height)
            glEnd()

            # Side faces
            for i in range(len(corners)):
                j = (i + 1) % len(corners)
                glBegin(GL_QUADS)
                # Bottom to top
                glVertex3f(corners[i][0], corners[i][1], 0)
                glVertex3f(corners[j][0], corners[j][1], 0)
                glVertex3f(corners[j][0], corners[j][1], height)
                glVertex3f(corners[i][0], corners[i][1], height)
                glEnd()

        # Draw edges
        glColor4f(*rgb, max(1., alpha * 1.25))  # Solid blue edges
        glBegin(GL_LINES)

        # Bottom edges
        for i in range(len(corners)):
            j = (i + 1) % len(corners)
            glVertex3f(corners[i][0], corners[i][1], 0)
            glVertex3f(corners[j][0], corners[j][1], 0)

        # Top edges
        for i in range(len(corners)):
            j = (i + 1) % len(corners)
            glVertex3f(corners[i][0], corners[i][1], height)
            glVertex3f(corners[j][0], corners[j][1], height)

        # Vertical edges
        for i in range(len(corners)):
            glVertex3f(corners[i][0], corners[i][1], 0)
            glVertex3f(corners[i][0], corners[i][1], height)

        glEnd()

    def draw_building_solid(self, building):
        return self.draw_building(
            building, color=colorset.get('COL_SEL_BLDG_IN')
        )

    def draw_building_transparent(self, building):
        return self.draw_building(
            building, color=colorset.get('COL_BLDG_IN'),
            solid=0.25,
            faces=False
        )

    def on_mouse_down(self, event):
        """Handle mouse down for rotation"""
        if not self.opengl_initialized:
            return
        self.last_mouse_pos = event.GetPosition()
        self.rotating = True
        self.canvas.CaptureMouse()

    def on_mouse_up(self, event):
        """Handle mouse up"""
        if self.rotating:
            self.rotating = False
            if self.canvas.HasCapture():
                self.canvas.ReleaseMouse()

    def on_mouse_motion(self, event):
        """Handle mouse motion for rotation"""
        if not self.opengl_initialized:
            return

        if self.rotating and self.last_mouse_pos:
            current_pos = event.GetPosition()
            dx = current_pos.x - self.last_mouse_pos.x
            dy = current_pos.y - self.last_mouse_pos.y

            # Update camera angles
            self.camera_azimuth += dx * 0.5
            self.camera_elevation = max(-89, min(89,
                                                 self.camera_elevation + dy * 0.5))

            self.last_mouse_pos = current_pos
            self.Refresh()

    def on_mouse_wheel(self, event):
        """Handle mouse wheel for zooming"""
        if not self.opengl_initialized:
            return

        rotation = event.GetWheelRotation()
        zoom_factor = 0.9 if rotation > 0 else 1.1

        self.camera_distance *= zoom_factor
        self.camera_distance = max(10.0, min(5000.0, self.camera_distance))

        self.Refresh()

    def on_key_down(self, event):
        """Handle keyboard events"""
        if event.ControlDown() and event.GetKeyCode() == ord('P'):
            self.on_save_snapshot(None)
        else:
            event.Skip()

    def on_save_snapshot(self, event):
        """Save a snapshot of the 3D view"""
        if not OPENGL_SUPPORT or not self.opengl_initialized:
            wx.MessageBox("3D view not properly initialized", "Error",
                          wx.OK | wx.ICON_ERROR)
            return

        # Get save location
        dialog = wx.FileDialog(
            self,
            "Save 3D View Snapshot",
            wildcard="PNG files (*.png)|*.png|JPEG files (*.jpg)|*.jpg",
            style=wx.FD_SAVE | wx.FD_OVERWRITE_PROMPT
        )

        if dialog.ShowModal() == wx.ID_OK:
            filepath = dialog.GetPath()

            try:
                # Make sure we're current
                self.canvas.SetCurrent(self.context)

                # Get viewport size
                size = self.canvas.GetSize()
                width, height = size.width, size.height

                # Read pixels from OpenGL
                glPixelStorei(GL_PACK_ALIGNMENT, 1)
                pixels = glReadPixels(0, 0, width, height, GL_RGB,
                                      GL_UNSIGNED_BYTE)

                # Convert to numpy array and flip vertically (OpenGL origin is bottom-left)
                image_array = np.frombuffer(pixels, dtype=np.uint8)
                image_array = image_array.reshape(height, width, 3)
                image_array = np.flipud(image_array)

                # Convert to wx.Image
                wx_image = wx.Image(width, height, image_array.tobytes())

                # Save to file
                if filepath.lower().endswith('.png'):
                    wx_image.SaveFile(filepath, wx.BITMAP_TYPE_PNG)
                elif filepath.lower().endswith(
                        '.jpg') or filepath.lower().endswith('.jpeg'):
                    wx_image.SaveFile(filepath, wx.BITMAP_TYPE_JPEG)
                else:
                    # Default to PNG
                    if not filepath.lower().endswith('.png'):
                        filepath += '.png'
                    wx_image.SaveFile(filepath, wx.BITMAP_TYPE_PNG)

                wx.MessageBox(f"Snapshot saved to:\n{filepath}",
                              "Snapshot Saved",
                              wx.OK | wx.ICON_INFORMATION)

            except Exception as e:
                wx.MessageBox(f"Failed to save snapshot:\n{str(e)}",
                              "Error",
                              wx.OK | wx.ICON_ERROR)

        dialog.Destroy()

    def on_close(self, event):
        """Handle close button"""
        self.EndModal(wx.ID_OK)

# =========================================================================