#!/usr/bin/env python3
"""
CityJSON Creator Application
A wxPython GUI application for creating and editing CityJSON files with building data.
"""

import wx
import wx.lib.scrolledpanel as scrolled
import json
import math
import sys
import numpy as np
from dataclasses import dataclass, field
from typing import List, Tuple, Optional, Set
from enum import Enum
import uuid

# Version info
APP_VERSION = "1.0.0"


class SelectionMode(Enum):
    NORMAL = "normal"
    ADD_BUILDING = "add_building"
    RECTANGLE_SELECT = "rectangle_select"


@dataclass
class Building:
    """Represents a building with its properties"""
    id: str
    x1: float
    y1: float
    x2: float
    y2: float
    height: float = 10.0  # meters
    stories: int = 3
    selected: bool = False

    def __post_init__(self):
        # Ensure x1,y1 is bottom-left and x2,y2 is top-right
        if self.x1 > self.x2:
            self.x1, self.x2 = self.x2, self.x1
        if self.y1 > self.y2:
            self.y1, self.y2 = self.y2, self.y1

    def contains_point(self, x: float, y: float) -> bool:
        """Check if a point is inside the building"""
        return self.x1 <= x <= self.x2 and self.y1 <= y <= self.y2

    def get_corner_index(self, x: float, y: float,
                         threshold: float = 10) -> Optional[int]:
        """Get which corner is near the point (0-3), None if no corner"""
        corners = self.get_corners()
        for i, (cx, cy) in enumerate(corners):
            if math.sqrt((x - cx) ** 2 + (y - cy) ** 2) < threshold:
                return i
        return None

    def get_corners(self) -> List[Tuple[float, float]]:
        """Get all four corners"""
        return [
            (self.x1, self.y1),  # 0: bottom-left
            (self.x2, self.y1),  # 1: bottom-right
            (self.x2, self.y2),  # 2: top-right
            (self.x1, self.y2),  # 3: top-left
        ]

    def move_corner(self, corner_index: int, new_x: float, new_y: float):
        """Move a specific corner"""
        if corner_index == 0:  # bottom-left
            self.x1, self.y1 = new_x, new_y
        elif corner_index == 1:  # bottom-right
            self.x2, self.y1 = new_x, new_y
        elif corner_index == 2:  # top-right
            self.x2, self.y2 = new_x, new_y
        elif corner_index == 3:  # top-left
            self.x1, self.y2 = new_x, new_y
        self.__post_init__()  # Normalize coordinates

    def translate(self, dx: float, dy: float):
        """Move the entire building"""
        self.x1 += dx
        self.x2 += dx
        self.y1 += dy
        self.y2 += dy

    def to_cityjson_geometry(self) -> dict:
        """Convert to CityJSON geometry format"""
        # Create vertices for the building (8 points for a box)
        vertices = [
            [self.x1, self.y1, 0.0],
            [self.x2, self.y1, 0.0],
            [self.x2, self.y2, 0.0],
            [self.x1, self.y2, 0.0],
            [self.x1, self.y1, self.height],
            [self.x2, self.y1, self.height],
            [self.x2, self.y2, self.height],
            [self.x1, self.y2, self.height],
        ]

        # Define faces (indices into vertices array)
        boundaries = [
            [[0, 1, 2, 3]],  # bottom
            [[4, 7, 6, 5]],  # top
            [[0, 4, 5, 1]],  # front
            [[2, 6, 7, 3]],  # back
            [[0, 3, 7, 4]],  # left
            [[1, 5, 6, 2]],  # right
        ]

        return vertices, boundaries


class MapCanvas(wx.Panel):
    """The main canvas for displaying and editing buildings"""

    def __init__(self, parent):
        super().__init__(parent)
        self.parent = parent

        # State
        self.buildings: List[Building] = []
        self.mode = SelectionMode.NORMAL
        self.snap_enabled = True
        self.zoom_level = 1.0
        self.pan_x = 0
        self.pan_y = 0
        self.storey_height = 3.3  # meters per storey

        # Interaction state
        self.mouse_down = False
        self.drag_start = None
        self.drag_building = None
        self.drag_corner = None
        self.drag_corner_index = None
        self.first_corner = None
        self.selection_rect_start = None
        self.current_mouse_pos = None

        # Setup
        self.SetBackgroundStyle(wx.BG_STYLE_PAINT)
        self.Bind(wx.EVT_PAINT, self.on_paint)
        self.Bind(wx.EVT_LEFT_DOWN, self.on_mouse_down)
        self.Bind(wx.EVT_LEFT_UP, self.on_mouse_up)
        self.Bind(wx.EVT_MOTION, self.on_mouse_motion)
        self.Bind(wx.EVT_MOUSEWHEEL, self.on_mouse_wheel)
        self.Bind(wx.EVT_SIZE, self.on_size)

        self.SetMinSize((800, 600))

    def screen_to_world(self, x: float, y: float) -> Tuple[float, float]:
        """Convert screen coordinates to world coordinates"""
        wx = (x - self.pan_x) / self.zoom_level
        wy = (y - self.pan_y) / self.zoom_level
        return wx, wy

    def world_to_screen(self, x: float, y: float) -> Tuple[float, float]:
        """Convert world coordinates to screen coordinates"""
        sx = x * self.zoom_level + self.pan_x
        sy = y * self.zoom_level + self.pan_y
        return sx, sy

    def snap_point(self, x: float, y: float,
                   exclude_building: Optional[Building] = None) -> Tuple[
        float, float]:
        """Snap a point to nearby building features"""
        if not self.snap_enabled:
            return x, y

        snap_threshold = 15 / self.zoom_level
        best_x, best_y = x, y
        best_dist = snap_threshold

        for building in self.buildings:
            if building == exclude_building:
                continue

            # Snap to corners
            for cx, cy in building.get_corners():
                dist = math.sqrt((x - cx) ** 2 + (y - cy) ** 2)
                if dist < best_dist:
                    best_x, best_y = cx, cy
                    best_dist = dist

            # Snap to edges
            if abs(x - building.x1) < best_dist:
                best_x = building.x1
                best_dist = abs(x - building.x1)
            if abs(x - building.x2) < best_dist:
                best_x = building.x2
                best_dist = abs(x - building.x2)
            if abs(y - building.y1) < best_dist:
                best_y = building.y1
                best_dist = abs(y - building.y1)
            if abs(y - building.y2) < best_dist:
                best_y = building.y2
                best_dist = abs(y - building.y2)

        return best_x, best_y

    def on_paint(self, event):
        """Handle paint events"""
        dc = wx.AutoBufferedPaintDC(self)
        dc.Clear()

        # Set up coordinate system
        gc = wx.GraphicsContext.Create(dc)

        # Draw grid
        self.draw_grid(gc)

        # Draw buildings
        for building in self.buildings:
            self.draw_building(gc, building)

        # Draw preview for new building
        if self.mode == SelectionMode.ADD_BUILDING and self.first_corner and self.current_mouse_pos:
            self.draw_building_preview(gc)

        # Draw selection rectangle
        if self.mode == SelectionMode.RECTANGLE_SELECT and self.selection_rect_start and self.current_mouse_pos:
            self.draw_selection_rectangle(gc)

    def draw_grid(self, gc):
        """Draw background grid"""
        gc.SetPen(wx.Pen(wx.Colour(220, 220, 220), 1))

        width, height = self.GetSize()
        grid_size = 50 * self.zoom_level

        # Vertical lines
        x = self.pan_x % grid_size
        while x < width:
            gc.StrokeLine(x, 0, x, height)
            x += grid_size

        # Horizontal lines
        y = self.pan_y % grid_size
        while y < height:
            gc.StrokeLine(0, y, width, y)
            y += grid_size

    def draw_building(self, gc, building: Building):
        """Draw a single building"""
        x1, y1 = self.world_to_screen(building.x1, building.y1)
        x2, y2 = self.world_to_screen(building.x2, building.y2)

        # Set colors based on selection
        if building.selected:
            fill_color = wx.Colour(150, 180, 255, 180)
            border_color = wx.Colour(0, 0, 255)
        else:
            fill_color = wx.Colour(200, 200, 200, 180)
            border_color = wx.Colour(100, 100, 100)

        gc.SetBrush(wx.Brush(fill_color))
        gc.SetPen(wx.Pen(border_color, 2))

        # Draw rectangle
        gc.DrawRectangle(x1, y1, x2 - x1, y2 - y1)

        # Draw height text
        gc.SetFont(wx.Font(10, wx.FONTFAMILY_DEFAULT, wx.FONTSTYLE_NORMAL,
                           wx.FONTWEIGHT_NORMAL))
        text = f"{building.stories}F"
        tw, th = gc.GetTextExtent(text)
        gc.DrawText(text, (x1 + x2) / 2 - tw / 2, (y1 + y2) / 2 - th / 2)

        # Draw corner handles if selected
        if building.selected:
            gc.SetBrush(wx.Brush(wx.Colour(255, 255, 255)))
            gc.SetPen(wx.Pen(wx.Colour(0, 0, 255), 2))
            for cx, cy in building.get_corners():
                sx, sy = self.world_to_screen(cx, cy)
                gc.DrawEllipse(sx - 4, sy - 4, 8, 8)

    def draw_building_preview(self, gc):
        """Draw preview of building being created"""
        x1, y1 = self.first_corner
        x2, y2 = self.screen_to_world(*self.current_mouse_pos)
        x2, y2 = self.snap_point(x2, y2)

        sx1, sy1 = self.world_to_screen(x1, y1)
        sx2, sy2 = self.world_to_screen(x2, y2)

        gc.SetBrush(wx.Brush(wx.Colour(100, 255, 100, 100)))
        gc.SetPen(wx.Pen(wx.Colour(0, 200, 0), 2, wx.PENSTYLE_DOT))

        gc.DrawRectangle(min(sx1, sx2), min(sy1, sy2),
                         abs(sx2 - sx1), abs(sy2 - sy1))

    def draw_selection_rectangle(self, gc):
        """Draw selection rectangle"""
        x1, y1 = self.selection_rect_start
        x2, y2 = self.current_mouse_pos

        gc.SetBrush(wx.Brush(wx.Colour(0, 0, 255, 30)))
        gc.SetPen(wx.Pen(wx.Colour(0, 0, 255), 1, wx.PENSTYLE_DOT))

        gc.DrawRectangle(min(x1, x2), min(y1, y2),
                         abs(x2 - x1), abs(y2 - y1))

    def on_mouse_down(self, event):
        """Handle mouse down events"""
        self.mouse_down = True
        self.drag_start = event.GetPosition()
        wx, wy = self.screen_to_world(event.GetX(), event.GetY())

        if self.mode == SelectionMode.ADD_BUILDING:
            if self.first_corner is None:
                self.first_corner = self.snap_point(wx, wy)
            else:
                # Create building
                x2, y2 = self.snap_point(wx, wy)
                building = Building(
                    id=str(uuid.uuid4()),
                    x1=self.first_corner[0],
                    y1=self.first_corner[1],
                    x2=x2,
                    y2=y2,
                    height=self.storey_height * 3,
                    stories=3
                )
                self.buildings.append(building)
                self.first_corner = None
                self.mode = SelectionMode.NORMAL
                self.Refresh()

        elif self.mode == SelectionMode.NORMAL:
            if event.ShiftDown():
                # Start rectangle selection
                self.mode = SelectionMode.RECTANGLE_SELECT
                self.selection_rect_start = event.GetPosition()
            else:
                # Check for corner drag
                for building in self.buildings:
                    if building.selected:
                        corner_idx = building.get_corner_index(wx, wy,
                                                               10 / self.zoom_level)
                        if corner_idx is not None:
                            self.drag_corner = building
                            self.drag_corner_index = corner_idx
                            return

                # Check for building click
                clicked_building = None
                for building in reversed(self.buildings):
                    if building.contains_point(wx, wy):
                        clicked_building = building
                        break

                if clicked_building:
                    if not event.ControlDown():
                        # Clear selection unless Ctrl is held
                        for b in self.buildings:
                            b.selected = False
                    clicked_building.selected = not clicked_building.selected if event.ControlDown() else True
                    self.drag_building = clicked_building
                else:
                    # Click on empty space - clear selection
                    if not event.ControlDown():
                        for b in self.buildings:
                            b.selected = False

                self.Refresh()

    def on_mouse_up(self, event):
        """Handle mouse up events"""
        self.mouse_down = False

        if self.mode == SelectionMode.RECTANGLE_SELECT:
            # Select buildings in rectangle
            x1, y1 = self.screen_to_world(*self.selection_rect_start)
            x2, y2 = self.screen_to_world(event.GetX(), event.GetY())

            rx1, rx2 = min(x1, x2), max(x1, x2)
            ry1, ry2 = min(y1, y2), max(y1, y2)

            for building in self.buildings:
                if (building.x1 >= rx1 and building.x2 <= rx2 and
                        building.y1 >= ry1 and building.y2 <= ry2):
                    building.selected = True

            self.mode = SelectionMode.NORMAL
            self.selection_rect_start = None
            self.Refresh()

        self.drag_building = None
        self.drag_corner = None
        self.drag_corner_index = None
        self.drag_start = None

    def on_mouse_motion(self, event):
        """Handle mouse motion events"""
        self.current_mouse_pos = event.GetPosition()
        wx, wy = self.screen_to_world(event.GetX(), event.GetY())

        if self.mouse_down and self.drag_start:
            if self.drag_corner and self.drag_corner_index is not None:
                # Dragging a corner
                snapped_x, snapped_y = self.snap_point(wx, wy,
                                                       self.drag_corner)
                self.drag_corner.move_corner(self.drag_corner_index,
                                             snapped_x, snapped_y)
                self.Refresh()
            elif self.drag_building:
                # Dragging a building
                start_wx, start_wy = self.screen_to_world(*self.drag_start)
                dx = wx - start_wx
                dy = wy - start_wy

                # Apply snapping to the drag
                new_x1 = self.drag_building.x1 + dx
                new_y1 = self.drag_building.y1 + dy
                snapped_x, snapped_y = self.snap_point(new_x1, new_y1,
                                                       self.drag_building)

                actual_dx = snapped_x - self.drag_building.x1
                actual_dy = snapped_y - self.drag_building.y1

                self.drag_building.translate(actual_dx, actual_dy)
                self.drag_start = event.GetPosition()
                self.Refresh()
            elif event.MiddleIsDown() or (
                    event.RightIsDown() and not self.mode == SelectionMode.ADD_BUILDING):
                # Panning
                dx = event.GetX() - self.drag_start[0]
                dy = event.GetY() - self.drag_start[1]
                self.pan_x += dx
                self.pan_y += dy
                self.drag_start = event.GetPosition()
                self.Refresh()

        if self.mode == SelectionMode.ADD_BUILDING and self.first_corner:
            self.Refresh()

        if self.mode == SelectionMode.RECTANGLE_SELECT:
            self.Refresh()

    def on_mouse_wheel(self, event):
        """Handle mouse wheel events for zooming"""
        rotation = event.GetWheelRotation()
        mx, my = event.GetPosition()

        # Calculate zoom
        zoom_factor = 1.1 if rotation > 0 else 0.9
        new_zoom = self.zoom_level * zoom_factor
        new_zoom = max(0.1, min(10.0, new_zoom))

        # Adjust pan to zoom around mouse position
        wx, wy = self.screen_to_world(mx, my)
        self.zoom_level = new_zoom
        new_mx, new_my = self.world_to_screen(wx, wy)

        self.pan_x += mx - new_mx
        self.pan_y += my - new_my

        self.Refresh()

    def on_size(self, event):
        """Handle resize events"""
        self.Refresh()
        event.Skip()

    def set_building_stories(self, stories: int):
        """Set stories for selected buildings"""
        for building in self.buildings:
            if building.selected:
                building.stories = stories
                building.height = stories * self.storey_height
        self.Refresh()

    def delete_selected_buildings(self):
        """Delete selected buildings"""
        self.buildings = [b for b in self.buildings if not b.selected]
        self.Refresh()

    def zoom_to_buildings(self):
        """Zoom to fit all buildings"""
        if not self.buildings:
            return

        # Find bounding box
        min_x = min(b.x1 for b in self.buildings)
        max_x = max(b.x2 for b in self.buildings)
        min_y = min(b.y1 for b in self.buildings)
        max_y = max(b.y2 for b in self.buildings)

        # Calculate zoom and pan
        width, height = self.GetSize()
        margin = 50

        zoom_x = (width - 2 * margin) / (
                    max_x - min_x) if max_x > min_x else 1.0
        zoom_y = (height - 2 * margin) / (
                    max_y - min_y) if max_y > min_y else 1.0

        self.zoom_level = min(zoom_x, zoom_y, 5.0)

        # Center the view
        center_x = (min_x + max_x) / 2
        center_y = (min_y + max_y) / 2

        self.pan_x = width / 2 - center_x * self.zoom_level
        self.pan_y = height / 2 - center_y * self.zoom_level

        self.Refresh()


class HeightDialog(wx.Dialog):
    """Dialog for setting building height"""

    def __init__(self, parent, stories=3, height=10.0, storey_height=3.3):
        super().__init__(parent, title="Set Building Height",
                         size=(300, 200))

        self.storey_height = storey_height

        panel = wx.Panel(self)
        sizer = wx.BoxSizer(wx.VERTICAL)

        # Stories control
        stories_box = wx.BoxSizer(wx.HORIZONTAL)
        stories_box.Add(wx.StaticText(panel, label="Stories:"), 0,
                        wx.ALIGN_CENTER_VERTICAL | wx.RIGHT, 5)
        self.stories_ctrl = wx.SpinCtrl(panel, value=str(stories), min=1,
                                        max=100)
        stories_box.Add(self.stories_ctrl, 1, wx.EXPAND)
        sizer.Add(stories_box, 0, wx.EXPAND | wx.ALL, 10)

        # Height control
        height_box = wx.BoxSizer(wx.HORIZONTAL)
        height_box.Add(wx.StaticText(panel, label="Height (m):"), 0,
                       wx.ALIGN_CENTER_VERTICAL | wx.RIGHT, 5)
        self.height_ctrl = wx.TextCtrl(panel, value=f"{height:.1f}")
        height_box.Add(self.height_ctrl, 1, wx.EXPAND)
        sizer.Add(height_box, 0, wx.EXPAND | wx.ALL, 10)

        # Buttons
        btn_sizer = wx.StdDialogButtonSizer()
        ok_btn = wx.Button(panel, wx.ID_OK)
        cancel_btn = wx.Button(panel, wx.ID_CANCEL)
        btn_sizer.AddButton(ok_btn)
        btn_sizer.AddButton(cancel_btn)
        btn_sizer.Realize()
        sizer.Add(btn_sizer, 0, wx.EXPAND | wx.ALL, 10)

        panel.SetSizer(sizer)

        # Bind events
        self.stories_ctrl.Bind(wx.EVT_SPINCTRL, self.on_stories_changed)
        self.height_ctrl.Bind(wx.EVT_TEXT, self.on_height_changed)

    def on_stories_changed(self, event):
        """Update height when stories change"""
        stories = self.stories_ctrl.GetValue()
        height = stories * self.storey_height
        self.height_ctrl.SetValue(f"{height:.1f}")
        self.height_ctrl.SetBackgroundColour(
            wx.SystemSettings.GetColour(wx.SYS_COLOUR_WINDOW))

    def on_height_changed(self, event):
        """Update stories when height changes and validate"""
        try:
            height = float(self.height_ctrl.GetValue())
            if height < 0:
                self.height_ctrl.SetBackgroundColour(
                    wx.Colour(255, 200, 200))
            else:
                self.height_ctrl.SetBackgroundColour(
                    wx.SystemSettings.GetColour(wx.SYS_COLOUR_WINDOW))
                stories = max(1, round(height / self.storey_height))
                self.stories_ctrl.SetValue(stories)
        except ValueError:
            self.height_ctrl.SetBackgroundColour(wx.Colour(255, 200, 200))

    def get_values(self):
        """Get the current values"""
        return self.stories_ctrl.GetValue(), float(
            self.height_ctrl.GetValue())


class MainFrame(wx.Frame):
    """Main application frame"""

    def __init__(self):
        super().__init__(None, title="CityJSON Creator", size=(1200, 800))

        self.current_file = None
        self.modified = False

        # Create UI
        self.create_menu_bar()
        self.create_toolbar()
        self.create_main_panel()

        # Bind keyboard events
        self.Bind(wx.EVT_CHAR_HOOK, self.on_key_press)

        self.Centre()
        self.Show()

    def create_menu_bar(self):
        """Create the menu bar"""
        menubar = wx.MenuBar()

        # File menu
        file_menu = wx.Menu()
        file_menu.Append(wx.ID_NEW, "&New\tCtrl+N", "Create a new project")
        file_menu.Append(wx.ID_OPEN, "&Open\tCtrl+O",
                         "Open a CityJSON file")
        file_menu.Append(wx.ID_SAVE, "&Save\tCtrl+S",
                         "Save the current project")
        file_menu.Append(wx.ID_SAVEAS, "Save &As...\tCtrl+Shift+S",
                         "Save with a new name")
        file_menu.AppendSeparator()
        file_menu.Append(wx.ID_EXIT, "E&xit\tCtrl+Q",
                         "Exit the application")

        # Edit menu
        edit_menu = wx.Menu()
        edit_menu.Append(wx.ID_ANY, "Select &Basemap", "Choose a basemap")
        edit_menu.Append(wx.ID_ANY, "&Zoom to Buildings\tCtrl+0",
                         "Zoom to fit all buildings")
        edit_menu.Append(wx.ID_ANY, "Set Storey &Height",
                         "Set the height per storey")

        # Help menu
        help_menu = wx.Menu()
        help_menu.Append(wx.ID_ABOUT, "&About", "About this application")

        menubar.Append(file_menu, "&File")
        menubar.Append(edit_menu, "&Edit")
        menubar.Append(help_menu, "&Help")

        self.SetMenuBar(menubar)

        # Bind menu events
        self.Bind(wx.EVT_MENU, self.on_new, id=wx.ID_NEW)
        self.Bind(wx.EVT_MENU, self.on_open, id=wx.ID_OPEN)
        self.Bind(wx.EVT_MENU, self.on_save, id=wx.ID_SAVE)
        self.Bind(wx.EVT_MENU, self.on_save_as, id=wx.ID_SAVEAS)
        self.Bind(wx.EVT_MENU, self.on_exit, id=wx.ID_EXIT)
        self.Bind(wx.EVT_MENU, self.on_about, id=wx.ID_ABOUT)

        # Bind edit menu events
        self.Bind(wx.EVT_MENU, self.on_zoom_to_buildings,
                  id=edit_menu.FindItem("&Zoom to Buildings\tCtrl+0"))
        self.Bind(wx.EVT_MENU, self.on_set_storey_height,
                  id=edit_menu.FindItem("Set Storey &Height"))

    def create_toolbar(self):
        """Create the toolbar"""
        toolbar = self.CreateToolBar(wx.TB_HORIZONTAL | wx.TB_FLAT)

        # Add Building button
        self.add_building_btn = wx.Button(toolbar, label="Add Building")
        self.add_building_btn.Bind(wx.EVT_BUTTON, self.on_add_building)
        toolbar.AddControl(self.add_building_btn)

        toolbar.AddSeparator()

        # Snap toggle
        self.snap_btn = wx.ToggleButton(toolbar, label="Snap: ON")
        self.snap_btn.SetValue(True)
        self.snap_btn.Bind(wx.EVT_TOGGLEBUTTON, self.on_toggle_snap)
        toolbar.AddControl(self.snap_btn)

        toolbar.AddSeparator()

        # Set Height button
        height_btn = wx.Button(toolbar, label="Set Height")
        height_btn.Bind(wx.EVT_BUTTON, self.on_set_height)
        toolbar.AddControl(height_btn)

        # Delete button
        delete_btn = wx.Button(toolbar, label="Delete")
        delete_btn.Bind(wx.EVT_BUTTON, self.on_delete)
        toolbar.AddControl(delete_btn)

        toolbar.AddSeparator()

        # Zoom controls
        zoom_in_btn = wx.Button(toolbar, label="Zoom In")
        zoom_in_btn.Bind(wx.EVT_BUTTON, self.on_zoom_in)
        toolbar.AddControl(zoom_in_btn)

        zoom_out_btn = wx.Button(toolbar, label="Zoom Out")
        zoom_out_btn.Bind(wx.EVT_BUTTON, self.on_zoom_out)
        toolbar.AddControl(zoom_out_btn)

        zoom_fit_btn = wx.Button(toolbar, label="Zoom Fit")
        zoom_fit_btn.Bind(wx.EVT_BUTTON, self.on_zoom_to_buildings)
        toolbar.AddControl(zoom_fit_btn)

        toolbar.Realize()

    def create_main_panel(self):
        """Create the main panel with canvas"""
        panel = wx.Panel(self)
        sizer = wx.BoxSizer(wx.VERTICAL)

        # Create canvas
        self.canvas = MapCanvas(panel)
        sizer.Add(self.canvas, 1, wx.EXPAND)

        # Status bar
        self.CreateStatusBar()
        self.SetStatusText("Ready")

        panel.SetSizer(sizer)

    def on_key_press(self, event):
        """Handle keyboard shortcuts"""
        key = event.GetKeyCode()

        # Number keys 1-9 for setting building stories
        if ord('1') <= key <= ord('9'):
            stories = key - ord('0')
            self.canvas.set_building_stories(stories)
            self.SetStatusText(
                f"Set selected buildings to {stories} stories")
        elif key == wx.WXK_DELETE:
            self.on_delete(None)
        else:
            event.Skip()

    def on_add_building(self, event):
        """Switch to add building mode"""
        self.canvas.mode = SelectionMode.ADD_BUILDING
        self.canvas.first_corner = None
        self.add_building_btn.SetLabel("Adding...")
        self.SetStatusText("Click to place first corner of building")

    def on_toggle_snap(self, event):
        """Toggle snapping"""
        self.canvas.snap_enabled = self.snap_btn.GetValue()
        self.snap_btn.SetLabel(
            f"Snap: {'ON' if self.canvas.snap_enabled else 'OFF'}")

    def on_set_height(self, event):
        """Open height setting dialog"""
        selected = [b for b in self.canvas.buildings if b.selected]
        if not selected:
            wx.MessageBox("Please select at least one building",
                          "No Selection",
                          wx.OK | wx.ICON_WARNING)
            return

        # Get current values from first selected building
        stories = selected[0].stories
        height = selected[0].height

        dialog = HeightDialog(self, stories, height,
                              self.canvas.storey_height)
        if dialog.ShowModal() == wx.ID_OK:
            new_stories, new_height = dialog.get_values()
            for building in selected:
                building.stories = new_stories
                building.height = new_height
            self.canvas.Refresh()
            self.SetStatusText(
                f"Set height to {new_stories} stories ({new_height:.1f}m)")
        dialog.Destroy()

    def on_delete(self, event):
        """Delete selected buildings"""
        selected = [b for b in self.canvas.buildings if b.selected]
        if not selected:
            return

        result = wx.MessageBox(
            f"Are you sure you want to delete {len(selected)} building(s)?",
            "Confirm Delete",
            wx.YES_NO | wx.ICON_QUESTION
        )

        if result == wx.YES:
            self.canvas.delete_selected_buildings()
            self.SetStatusText(f"Deleted {len(selected)} building(s)")

    def on_zoom_in(self, event):
        """Zoom in"""
        self.canvas.zoom_level *= 1.2
        self.canvas.zoom_level = min(10.0, self.canvas.zoom_level)
        self.canvas.Refresh()

    def on_zoom_out(self, event):
        """Zoom out"""
        self.canvas.zoom_level /= 1.2
        self.canvas.zoom_level = max(0.1, self.canvas.zoom_level)
        self.canvas.Refresh()

    def on_zoom_to_buildings(self, event):
        """Zoom to fit all buildings"""
        self.canvas.zoom_to_buildings()
        self.SetStatusText("Zoomed to fit all buildings")

    def on_set_storey_height(self, event):
        """Set the height per storey"""
        dialog = wx.TextEntryDialog(
            self,
            "Enter height per storey (meters):",
            "Set Storey Height",
            f"{self.canvas.storey_height:.1f}"
        )

        if dialog.ShowModal() == wx.ID_OK:
            try:
                height = float(dialog.GetValue())
                if height > 0:
                    self.canvas.storey_height = height
                    # Update all buildings
                    for building in self.canvas.buildings:
                        building.height = building.stories * height
                    self.canvas.Refresh()
                    self.SetStatusText(
                        f"Storey height set to {height:.1f}m")
                else:
                    wx.MessageBox("Height must be positive",
                                  "Invalid Input",
                                  wx.OK | wx.ICON_ERROR)
            except ValueError:
                wx.MessageBox("Invalid number", "Invalid Input",
                              wx.OK | wx.ICON_ERROR)
        dialog.Destroy()

    def on_new(self, event):
        """Create a new project"""
        if self.modified:
            result = wx.MessageBox(
                "Save current project?",
                "New Project",
                wx.YES_NO | wx.CANCEL | wx.ICON_QUESTION
            )
            if result == wx.YES:
                self.on_save(None)
            elif result == wx.CANCEL:
                return

        self.canvas.buildings.clear()
        self.canvas.Refresh()
        self.current_file = None
        self.modified = False
        self.SetTitle("CityJSON Creator - New Project")
        self.SetStatusText("New project created")

    def on_open(self, event):
        """Open a CityJSON file"""
        dialog = wx.FileDialog(
            self,
            "Open CityJSON file",
            wildcard="CityJSON files (*.json)|*.json|All files (*.*)|*.*",
            style=wx.FD_OPEN | wx.FD_FILE_MUST_EXIST
        )

        if dialog.ShowModal() == wx.ID_OK:
            filepath = dialog.GetPath()
            self.load_cityjson(filepath)
        dialog.Destroy()

    def on_save(self, event):
        """Save the current project"""
        if self.current_file:
            self.save_cityjson(self.current_file)
        else:
            self.on_save_as(event)

    def on_save_as(self, event):
        """Save with a new filename"""
        dialog = wx.FileDialog(
            self,
            "Save CityJSON file",
            wildcard="CityJSON files (*.json)|*.json",
            style=wx.FD_SAVE | wx.FD_OVERWRITE_PROMPT
        )

        if dialog.ShowModal() == wx.ID_OK:
            filepath = dialog.GetPath()
            if not filepath.endswith('.json'):
                filepath += '.json'
            self.save_cityjson(filepath)
        dialog.Destroy()

    def load_cityjson(self, filepath):
        """Load a CityJSON file"""
        try:
            with open(filepath, 'r') as f:
                data = json.load(f)

            if data.get('type') != 'CityJSON':
                wx.MessageBox("Not a valid CityJSON file", "Error",
                              wx.OK | wx.ICON_ERROR)
                return

            # Clear current buildings
            self.canvas.buildings.clear()

            # Load vertices
            vertices = data.get('vertices', [])

            # Load city objects
            for obj_id, obj_data in data.get('CityObjects', {}).items():
                if obj_data.get('type') == 'Building':
                    # Extract building geometry
                    geom = obj_data.get('geometry', [])
                    if geom and geom[0].get('type') == 'Solid':
                        boundaries = geom[0].get('boundaries', [])
                        if boundaries:
                            # Get vertices of the bottom face
                            bottom_face = boundaries[0][
                                0] if boundaries else []
                            if len(bottom_face) >= 4:
                                # Get building bounds
                                v_indices = bottom_face
                                xs = [vertices[i][0] for i in v_indices]
                                ys = [vertices[i][1] for i in v_indices]
                                zs = [vertices[i][2] for i in v_indices]

                                building = Building(
                                    id=obj_id,
                                    x1=min(xs),
                                    y1=min(ys),
                                    x2=max(xs),
                                    y2=max(ys),
                                    height=max(zs) - min(
                                        zs) if zs else 10.0,
                                    stories=max(1, round((max(zs) - min(
                                        zs)) / self.canvas.storey_height))
                                )
                                self.canvas.buildings.append(building)

            self.current_file = filepath
            self.modified = False
            self.SetTitle(f"CityJSON Creator - {filepath}")
            self.canvas.zoom_to_buildings()
            self.SetStatusText(
                f"Loaded {len(self.canvas.buildings)} buildings")

        except Exception as e:
            wx.MessageBox(f"Error loading file: {str(e)}", "Error",
                          wx.OK | wx.ICON_ERROR)

    def save_cityjson(self, filepath):
        """Save to a CityJSON file"""
        try:
            # Collect all vertices and create index mapping
            all_vertices = []
            vertex_map = {}

            city_objects = {}

            for building in self.canvas.buildings:
                vertices, boundaries = building.to_cityjson_geometry()

                # Map vertices to global index
                local_to_global = []
                for v in vertices:
                    v_tuple = tuple(v)
                    if v_tuple not in vertex_map:
                        vertex_map[v_tuple] = len(all_vertices)
                        all_vertices.append(list(v))
                    local_to_global.append(vertex_map[v_tuple])

                # Remap boundaries to global indices
                remapped_boundaries = []
                for face in boundaries:
                    remapped_face = [[local_to_global[i] for i in ring] for
                                     ring in face]
                    remapped_boundaries.append(remapped_face)

                # Create city object
                city_objects[building.id] = {
                    "type": "Building",
                    "attributes": {
                        "height": building.height,
                        "stories": building.stories
                    },
                    "geometry": [{
                        "type": "Solid",
                        "lod": 1,
                        "boundaries": [remapped_boundaries]
                    }]
                }

            # Create CityJSON structure
            cityjson = {
                "type": "CityJSON",
                "version": "1.1",
                "CityObjects": city_objects,
                "vertices": all_vertices
            }

            # Save to file
            with open(filepath, 'w') as f:
                json.dump(cityjson, f, indent=2)

            self.current_file = filepath
            self.modified = False
            self.SetTitle(f"CityJSON Creator - {filepath}")
            self.SetStatusText(
                f"Saved {len(self.canvas.buildings)} buildings to {filepath}")

        except Exception as e:
            wx.MessageBox(f"Error saving file: {str(e)}", "Error",
                          wx.OK | wx.ICON_ERROR)

    def on_exit(self, event):
        """Exit the application"""
        if self.modified:
            result = wx.MessageBox(
                "Save changes before exiting?",
                "Exit",
                wx.YES_NO | wx.CANCEL | wx.ICON_QUESTION
            )
            if result == wx.YES:
                self.on_save(None)
            elif result == wx.CANCEL:
                return

        self.Close()

    def on_about(self, event):
        """Show about dialog"""
        info = f"""CityJSON Creator
Version: {APP_VERSION}

A graphical tool for creating and editing CityJSON files.

Library Versions:
- wxPython: {wx.__version__}
- Python: {sys.version.split()[0]}
- NumPy: {np.__version__}

© 2024 - Created with Claude"""

        wx.MessageBox(info, "About CityJSON Creator",
                      wx.OK | wx.ICON_INFORMATION)


class CityJSONApp(wx.App):
    """Main application class"""

    def OnInit(self):
        self.frame = MainFrame()
        return True


if __name__ == '__main__':
    app = CityJSONApp()
    app.MainLoop()