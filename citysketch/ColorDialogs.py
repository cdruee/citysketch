"""
Settings dialogs for CitySketch application.
Includes color configuration and application settings.
"""

import os
import wx

from .AppSettings import Settings, settings


class ColorSettingsDialog(wx.Dialog):
    """
    Dialog for configuring application settings.
    
    Includes:
    - Color settings for buildings, selection, etc.
    - Path settings (Global Building Atlas directory)
    """

    def __init__(self, parent, colorset: Settings):
        super().__init__(parent, title="Settings",
                         style=wx.DEFAULT_DIALOG_STYLE | wx.RESIZE_BORDER)

        self.colorset = colorset
        self.color_buttons = {}
        self.original_colors = {}

        # Store original colors for cancel
        for key in colorset.get_all_keys():
            self.original_colors[key] = colorset.get(key)

        # Main sizer
        main_sizer = wx.BoxSizer(wx.VERTICAL)

        # Create notebook for tabs
        notebook = wx.Notebook(self)

        # Paths panel
        paths_panel = self._create_paths_panel(notebook)
        notebook.AddPage(paths_panel, "Paths")

        # Colors panel
        colors_panel = self._create_colors_panel(notebook)
        notebook.AddPage(colors_panel, "Colors")

        main_sizer.Add(notebook, 1, wx.EXPAND | wx.ALL, 10)

        # Buttons
        btn_sizer = self.CreateStdDialogButtonSizer(wx.OK | wx.CANCEL)
        main_sizer.Add(btn_sizer, 0, wx.EXPAND | wx.ALL, 10)

        self.SetSizer(main_sizer)
        self.SetSize((500, 450))
        self.Centre()

        # Bind events
        self.Bind(wx.EVT_BUTTON, self.on_ok, id=wx.ID_OK)
        self.Bind(wx.EVT_BUTTON, self.on_cancel, id=wx.ID_CANCEL)

    def _create_paths_panel(self, parent):
        """Create the paths settings panel"""
        panel = wx.Panel(parent)
        sizer = wx.BoxSizer(wx.VERTICAL)

        # Global Building Atlas directory
        gba_box = wx.StaticBox(panel, label="Global Building Atlas")
        gba_sizer = wx.StaticBoxSizer(gba_box, wx.VERTICAL)

        # Description
        desc = wx.StaticText(
            panel,
            label="Set the directory containing Global Building Atlas GeoJSON tiles.\n"
                  "This enables the 'Import Global Building Atlas' feature."
        )
        desc.SetFont(desc.GetFont().MakeSmaller())
        gba_sizer.Add(desc, 0, wx.ALL, 5)

        # Directory path control
        path_sizer = wx.BoxSizer(wx.HORIZONTAL)
        
        self.gba_path_ctrl = wx.TextCtrl(
            panel, 
            value=settings.get('GBA_DIRECTORY'),
            size=(350, -1)
        )
        path_sizer.Add(self.gba_path_ctrl, 1, wx.EXPAND | wx.RIGHT, 5)

        browse_btn = wx.Button(panel, label="Browse...")
        browse_btn.Bind(wx.EVT_BUTTON, self.on_browse_gba)
        path_sizer.Add(browse_btn, 0)

        gba_sizer.Add(path_sizer, 0, wx.EXPAND | wx.ALL, 5)

        # Status indicator
        self.gba_status = wx.StaticText(panel, label="")
        self._update_gba_status()
        gba_sizer.Add(self.gba_status, 0, wx.ALL, 5)

        sizer.Add(gba_sizer, 0, wx.EXPAND | wx.ALL, 10)

        panel.SetSizer(sizer)
        return panel

    def _create_colors_panel(self, parent):
        """Create the colors settings panel"""
        panel = wx.ScrolledWindow(parent)
        panel.SetScrollRate(0, 20)
        
        sizer = wx.BoxSizer(wx.VERTICAL)

        # Group colors by category
        categories = {
            'Map Tiles': ['COL_TILE_EMPTY', 'COL_TILE_EDGE'],
            'Grid': ['COL_GRID'],
            'Building Preview': ['COL_FLOAT_IN', 'COL_FLOAT_OUT'],
            'Buildings': ['COL_BLDG_IN', 'COL_BLDG_OUT', 'COL_BLDG_LBL'],
            'Selected Buildings': ['COL_SEL_BLDG_IN', 'COL_SEL_BLDG_OUT'],
            'Handles': ['COL_HANDLE_IN', 'COL_HANDLE_OUT'],
        }

        for category, keys in categories.items():
            # Check if any keys exist in colorset
            valid_keys = [k for k in keys if k in self.colorset.get_all_keys()]
            if not valid_keys:
                continue

            box = wx.StaticBox(panel, label=category)
            box_sizer = wx.StaticBoxSizer(box, wx.VERTICAL)

            for key in valid_keys:
                row_sizer = wx.BoxSizer(wx.HORIZONTAL)

                # Description label
                desc = self.colorset.get_description(key)
                label = wx.StaticText(panel, label=desc, size=(200, -1))
                row_sizer.Add(label, 0, wx.ALIGN_CENTER_VERTICAL | wx.RIGHT, 10)

                # Color button
                color = self.colorset.get(key)
                btn = wx.Button(panel, label="", size=(60, 25))
                btn.SetBackgroundColour(color)
                btn.Bind(wx.EVT_BUTTON, 
                        lambda evt, k=key: self.on_color_click(k))
                self.color_buttons[key] = btn
                row_sizer.Add(btn, 0, wx.ALIGN_CENTER_VERTICAL | wx.RIGHT, 5)

                # Reset button
                reset_btn = wx.Button(panel, label="Reset", size=(50, 25))
                reset_btn.Bind(wx.EVT_BUTTON,
                              lambda evt, k=key: self.on_reset_color(k))
                row_sizer.Add(reset_btn, 0, wx.ALIGN_CENTER_VERTICAL)

                box_sizer.Add(row_sizer, 0, wx.EXPAND | wx.ALL, 3)

            sizer.Add(box_sizer, 0, wx.EXPAND | wx.ALL, 5)

        # Reset all button
        reset_all_btn = wx.Button(panel, label="Reset All Colors to Defaults")
        reset_all_btn.Bind(wx.EVT_BUTTON, self.on_reset_all)
        sizer.Add(reset_all_btn, 0, wx.ALIGN_CENTER | wx.ALL, 10)

        panel.SetSizer(sizer)
        return panel

    def _update_gba_status(self):
        """Update the GBA directory status indicator"""
        path = self.gba_path_ctrl.GetValue()
        if not path:
            self.gba_status.SetLabel("Status: No directory set")
            self.gba_status.SetForegroundColour(wx.Colour(128, 128, 128))
        elif os.path.isdir(path):
            # Count GeoJSON files
            try:
                geojson_files = [f for f in os.listdir(path) 
                                if f.endswith('.geojson')]
                self.gba_status.SetLabel(
                    f"Status: Valid directory ({len(geojson_files)} .geojson files found)")
                self.gba_status.SetForegroundColour(wx.Colour(0, 128, 0))
            except OSError as e:
                self.gba_status.SetLabel(f"Status: Error reading directory")
                self.gba_status.SetForegroundColour(wx.Colour(200, 0, 0))
        else:
            self.gba_status.SetLabel("Status: Directory not found")
            self.gba_status.SetForegroundColour(wx.Colour(200, 0, 0))

    def on_browse_gba(self, event):
        """Browse for GBA directory"""
        current = self.gba_path_ctrl.GetValue()
        dialog = wx.DirDialog(
            self,
            "Select Global Building Atlas Directory",
            defaultPath=current if os.path.isdir(current) else "",
            style=wx.DD_DEFAULT_STYLE | wx.DD_DIR_MUST_EXIST
        )

        if dialog.ShowModal() == wx.ID_OK:
            self.gba_path_ctrl.SetValue(dialog.GetPath())
            self._update_gba_status()

        dialog.Destroy()

    def on_color_click(self, key):
        """Handle color button click"""
        current_color = self.colorset.get(key)
        
        # Create color data with current color
        color_data = wx.ColourData()
        color_data.SetColour(current_color)
        
        dialog = wx.ColourDialog(self, color_data)
        if dialog.ShowModal() == wx.ID_OK:
            new_color = dialog.GetColourData().GetColour()
            # Preserve alpha from original color
            new_color = wx.Colour(new_color.Red(), new_color.Green(),
                                 new_color.Blue(), current_color.Alpha())
            self.colorset.set(key, new_color)
            self.color_buttons[key].SetBackgroundColour(new_color)
            self.color_buttons[key].Refresh()
        
        dialog.Destroy()

    def on_reset_color(self, key):
        """Reset a single color to default"""
        default_color = self.colorset.get_default(key)
        self.colorset.set(key, default_color)
        self.color_buttons[key].SetBackgroundColour(default_color)
        self.color_buttons[key].Refresh()

    def on_reset_all(self, event):
        """Reset all colors to defaults"""
        result = wx.MessageBox(
            "Reset all colors to their default values?",
            "Confirm Reset",
            wx.YES_NO | wx.ICON_QUESTION
        )
        if result == wx.YES:
            self.colorset.reset_to_defaults()
            for key, btn in self.color_buttons.items():
                btn.SetBackgroundColour(self.colorset.get(key))
                btn.Refresh()

    def on_ok(self, event):
        """Handle OK button - save settings"""
        # Save GBA directory
        settings.set('GBA_DIRECTORY', self.gba_path_ctrl.GetValue())
        self.EndModal(wx.ID_OK)

    def on_cancel(self, event):
        """Handle Cancel button - restore original colors"""
        for key, color in self.original_colors.items():
            self.colorset.set(key, color)
        self.EndModal(wx.ID_CANCEL)
