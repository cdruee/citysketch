import re
import wx
from typing import Optional, Tuple


class ColorPickerDialog(wx.Dialog):
    """Advanced color picker dialog with multiple input methods"""

    def __init__(self, parent, title="Select Color",
                 initial_color=wx.Colour(255, 255, 255),
                 default_color=wx.Colour(255, 255, 255)):
        super().__init__(parent, title=title, size=(500, 600))

        self.color = wx.Colour(initial_color)
        self.default = wx.Colour(default_color)
        self.updating = False  # Flag to prevent recursive updates

        self.create_ui()
        self.update_all_from_color()
        self.CenterOnParent()

    def create_ui(self):
        """Create the user interface"""
        panel = wx.Panel(self)
        main_sizer = wx.BoxSizer(wx.VERTICAL)

        # Color preview
        self.create_color_preview(panel, main_sizer)

        # Predefined colors from wx.ColourDatabase
        self.create_predefined_colors(panel, main_sizer)

        # Manual color input methods
        self.create_manual_inputs(panel, main_sizer)

        # Buttons
        self.create_buttons(panel, main_sizer)

        panel.SetSizer(main_sizer)

    def create_color_preview(self, parent, sizer):
        """Create color preview section"""
        preview_box = wx.StaticBox(parent, label="Color Preview")
        preview_sizer = wx.StaticBoxSizer(preview_box, wx.VERTICAL)

        self.color_preview = wx.Panel(parent, size=(100, 50))
        self.color_preview.SetBackgroundColour(self.color)
        preview_sizer.Add(self.color_preview, 0, wx.EXPAND | wx.ALL, 5)

        sizer.Add(preview_sizer, 0, wx.EXPAND | wx.ALL, 10)

    def create_predefined_colors(self, parent, sizer):
        """Create predefined colors section"""
        pred_box = wx.StaticBox(parent, label="Predefined Colors")
        pred_sizer = wx.StaticBoxSizer(pred_box, wx.VERTICAL)

        # Get color database
        color_db = wx.ColourDatabase()
        color_names = [
            # Common colors
            'BLACK', 'WHITE', 'RED', 'GREEN', 'BLUE', 'YELLOW', 'CYAN',
            'MAGENTA',
            'GREY', 'LIGHT GREY', 'DARK GREY',
            # Additional useful colors
            'ORANGE', 'PURPLE', 'BROWN', 'PINK', 'LIME', 'NAVY', 'MAROON',
            'OLIVE', 'TEAL', 'SILVER', 'GOLD', 'CORAL', 'SALMON', 'KHAKI',
            'TURQUOISE', 'VIOLET', 'PLUM', 'ORCHID', 'TAN', 'WHEAT'
        ]

        # Create color grid
        colors_per_row = 8
        grid_sizer = wx.GridSizer(cols=colors_per_row, hgap=2, vgap=2)

        self.color_buttons = {}
        for name in color_names:
            color = color_db.Find(name)
            if color.IsOk():
                btn = wx.Button(parent, size=(25, 25),
                                style=wx.BORDER_NONE)
                btn.SetBackgroundColour(color)
                btn.SetToolTip(name)
                btn.Bind(wx.EVT_BUTTON, lambda evt, c=color,
                                               n=name: self.on_predefined_color(
                    c, n))
                grid_sizer.Add(btn, 0, wx.EXPAND)
                self.color_buttons[name] = btn

        pred_sizer.Add(grid_sizer, 0, wx.EXPAND | wx.ALL, 5)

        # Selected predefined color label
        self.predefined_label = wx.StaticText(parent, label="")
        pred_sizer.Add(self.predefined_label, 0, wx.EXPAND | wx.ALL, 5)

        sizer.Add(pred_sizer, 0, wx.EXPAND | wx.ALL, 10)

    def create_manual_inputs(self, parent, sizer):
        """Create manual input methods section"""
        manual_box = wx.StaticBox(parent, label="Manual Input")
        manual_sizer = wx.StaticBoxSizer(manual_box, wx.VERTICAL)

        # HTTP color code input
        http_sizer = wx.BoxSizer(wx.HORIZONTAL)
        http_sizer.Add(wx.StaticText(parent, label="HTTP Color:"), 0,
                       wx.ALIGN_CENTER_VERTICAL | wx.RIGHT, 5)
        self.http_ctrl = wx.TextCtrl(parent, size=(100, -1))
        self.http_ctrl.Bind(wx.EVT_TEXT, self.on_http_text_changed)
        self.http_ctrl.Bind(wx.EVT_KILL_FOCUS, self.on_http_focus_lost)
        http_sizer.Add(self.http_ctrl, 1, wx.EXPAND)
        manual_sizer.Add(http_sizer, 0, wx.EXPAND | wx.ALL, 5)

        # RGBA input
        rgba_sizer = wx.FlexGridSizer(2, 4, 5, 5)
        rgba_sizer.AddGrowableCol(1)
        rgba_sizer.AddGrowableCol(3)

        # R, G, B, A labels and controls
        self.rgba_ctrls = {}
        self.rgba_labels = ['R', 'G', 'B', 'A']

        for i, label in enumerate(self.rgba_labels):
            rgba_sizer.Add(wx.StaticText(parent, label=f"{label}:"), 0,
                           wx.ALIGN_CENTER_VERTICAL)
            ctrl = wx.TextCtrl(parent, size=(60, -1))
            ctrl.Bind(wx.EVT_TEXT,
                      lambda evt, comp=label: self.on_rgba_text_changed(
                          evt, comp))
            ctrl.Bind(wx.EVT_KILL_FOCUS,
                      lambda evt, comp=label: self.on_rgba_focus_lost(evt,
                                                                      comp))
            self.rgba_ctrls[label] = ctrl
            rgba_sizer.Add(ctrl, 1, wx.EXPAND)

        manual_sizer.Add(rgba_sizer, 0, wx.EXPAND | wx.ALL, 5)

        # Alpha/Opacity slider
        alpha_sizer = wx.BoxSizer(wx.HORIZONTAL)
        alpha_sizer.Add(wx.StaticText(parent, label="Opacity:"), 0,
                        wx.ALIGN_CENTER_VERTICAL | wx.RIGHT, 5)
        self.alpha_slider = wx.Slider(parent, value=255, minValue=0,
                                      maxValue=255,
                                      style=wx.SL_HORIZONTAL | wx.SL_LABELS)
        self.alpha_slider.Bind(wx.EVT_SLIDER, self.on_alpha_slider_changed)
        alpha_sizer.Add(self.alpha_slider, 1, wx.EXPAND)
        manual_sizer.Add(alpha_sizer, 0, wx.EXPAND | wx.ALL, 5)

        sizer.Add(manual_sizer, 0, wx.EXPAND | wx.ALL, 10)

    def create_buttons(self, parent, sizer):
        """Create dialog buttons"""
        btn_sizer = wx.StdDialogButtonSizer()

        ok_btn = wx.Button(parent, wx.ID_OK)
        cancel_btn = wx.Button(parent, wx.ID_CANCEL)
        reset_btn = wx.Button(parent, label="Reset")

        btn_sizer.AddButton(ok_btn)
        btn_sizer.AddButton(cancel_btn)
        btn_sizer.Add(reset_btn, 0, wx.LEFT, 10)
        btn_sizer.Realize()

        reset_btn.Bind(wx.EVT_BUTTON, self.on_reset)

        sizer.Add(btn_sizer, 0, wx.EXPAND | wx.ALL, 10)

    def on_predefined_color(self, color, name):
        """Handle predefined color selection"""
        # Keep the alpha from current color
        new_color = wx.Colour(color.Red(), color.Green(), color.Blue(),
                              self.color.Alpha())
        self.color = new_color
        self.update_all_from_color()

    def on_http_text_changed(self, event):
        """Handle HTTP color code text change"""
        if self.updating:
            return

        text = self.http_ctrl.GetValue().strip()

        # Validate and parse HTTP color code
        if self.validate_http_color(text):
            try:
                color = self.parse_http_color(text)
                if color:
                    self.color = color
                    self.updating = True
                    self.update_preview()
                    self.update_rgba_inputs()
                    self.update_alpha_slider()
                    self.update_predefined_selection()
                    self.updating = False
                    self.http_ctrl.SetBackgroundColour(wx.NullColour)
            except:
                self.http_ctrl.SetBackgroundColour(
                    wx.Colour(255, 200, 200))
        else:
            if text:  # Only show error for non-empty text
                self.http_ctrl.SetBackgroundColour(
                    wx.Colour(255, 200, 200))
            else:
                self.http_ctrl.SetBackgroundColour(wx.NullColour)

        self.http_ctrl.Refresh()

    def on_http_focus_lost(self, event):
        """Handle HTTP input losing focus"""
        text = self.http_ctrl.GetValue().strip()
        if text and not self.validate_http_color(text):
            # Reset to current color if invalid
            self.update_http_input()
        event.Skip()

    def on_rgba_text_changed(self, event, component):
        """Handle RGBA text change"""
        if self.updating:
            return

        ctrl = self.rgba_ctrls[component]
        text = ctrl.GetValue().strip()

        # Validate RGBA value
        if self.validate_rgba_component(text):
            try:
                value = int(text)
                if 0 <= value <= 255:
                    # Update color
                    r, g, b, a = self.color.Red(), self.color.Green(), self.color.Blue(), self.color.Alpha()

                    if component == 'R':
                        r = value
                    elif component == 'G':
                        g = value
                    elif component == 'B':
                        b = value
                    elif component == 'A':
                        a = value

                    self.color = wx.Colour(r, g, b, a)

                    self.updating = True
                    self.update_preview()
                    self.update_http_input()
                    if component == 'A':
                        self.update_alpha_slider()
                    self.update_predefined_selection()
                    self.updating = False

                    ctrl.SetBackgroundColour(wx.NullColour)
                else:
                    ctrl.SetBackgroundColour(wx.Colour(255, 200, 200))
            except:
                ctrl.SetBackgroundColour(wx.Colour(255, 200, 200))
        else:
            if text:  # Only show error for non-empty text
                ctrl.SetBackgroundColour(wx.Colour(255, 200, 200))
            else:
                ctrl.SetBackgroundColour(wx.NullColour)

        ctrl.Refresh()

    def on_rgba_focus_lost(self, event, component):
        """Handle RGBA input losing focus"""
        ctrl = self.rgba_ctrls[component]
        text = ctrl.GetValue().strip()
        if text and not self.validate_rgba_component(text):
            # Reset to current color component if invalid
            self.update_rgba_inputs()
        event.Skip()

    def on_alpha_slider_changed(self, event):
        """Handle alpha slider change"""
        if self.updating:
            return

        alpha = self.alpha_slider.GetValue()
        self.color = wx.Colour(self.color.Red(), self.color.Green(),
                               self.color.Blue(), alpha)

        self.updating = True
        self.update_preview()
        self.update_http_input()
        self.update_rgba_inputs()
        self.updating = False

    def on_reset(self, event):
        """Reset to white color"""
        self.color = self.default
        self.update_all_from_color()

    def validate_http_color(self, text: str) -> bool:
        """Validate HTTP color code format"""
        if not text:
            return True  # Empty is valid

        # Pattern for #RRGGBB or #RRGGBBAA
        pattern = r'^#[0-9A-Fa-f]{6}([0-9A-Fa-f]{2})?$'
        return bool(re.match(pattern, text))

    def validate_rgba_component(self, text: str) -> bool:
        """Validate RGBA component value"""
        if not text:
            return True  # Empty is valid

        try:
            value = int(text)
            return 0 <= value <= 255
        except ValueError:
            return False

    def parse_http_color(self, text: str) -> Optional[wx.Colour]:
        """Parse HTTP color code to wx.Colour"""
        if not text or not text.startswith('#'):
            return None

        hex_color = text[1:]

        try:
            if len(hex_color) == 6:
                # #RRGGBB
                r = int(hex_color[0:2], 16)
                g = int(hex_color[2:4], 16)
                b = int(hex_color[4:6], 16)
                return wx.Colour(r, g, b, self.color.Alpha())
            elif len(hex_color) == 8:
                # #RRGGBBAA
                r = int(hex_color[0:2], 16)
                g = int(hex_color[2:4], 16)
                b = int(hex_color[4:6], 16)
                a = int(hex_color[6:8], 16)
                return wx.Colour(r, g, b, a)
        except ValueError:
            pass

        return None

    def color_to_http(self, color: wx.Colour) -> str:
        """Convert wx.Colour to HTTP color code"""
        if color.Alpha() == 255:
            return f"#{color.Red():02X}{color.Green():02X}{color.Blue():02X}"
        else:
            return f"#{color.Red():02X}{color.Green():02X}{color.Blue():02X}{color.Alpha():02X}"

    def update_all_from_color(self):
        """Update all UI elements from current color"""
        self.updating = True
        self.update_preview()
        self.update_http_input()
        self.update_rgba_inputs()
        self.update_alpha_slider()
        self.update_predefined_selection()
        self.updating = False

    def update_preview(self):
        """Update color preview"""
        self.color_preview.SetBackgroundColour(self.color)
        self.color_preview.Refresh()

    def update_http_input(self):
        """Update HTTP color input"""
        self.http_ctrl.SetValue(self.color_to_http(self.color))
        self.http_ctrl.SetBackgroundColour(wx.NullColour)
        self.http_ctrl.Refresh()

    def update_rgba_inputs(self):
        """Update RGBA input controls"""
        values = {
            'R': self.color.Red(),
            'G': self.color.Green(),
            'B': self.color.Blue(),
            'A': self.color.Alpha()
        }

        for component, value in values.items():
            ctrl = self.rgba_ctrls[component]
            ctrl.SetValue(str(value))
            ctrl.SetBackgroundColour(wx.NullColour)
            ctrl.Refresh()

    def update_alpha_slider(self):
        """Update alpha slider"""
        self.alpha_slider.SetValue(self.color.Alpha())

    def update_predefined_selection(self):
        """Update predefined color selection indicator"""
        color_db = wx.ColourDatabase()

        # Check if current RGB matches any predefined color
        current_rgb = (self.color.Red(), self.color.Green(),
                       self.color.Blue())

        for name, btn in self.color_buttons.items():
            color = color_db.Find(name)
            if color.IsOk():
                color_rgb = (color.Red(), color.Green(), color.Blue())
                if color_rgb == current_rgb:
                    self.predefined_label.SetLabel(f"Selected: {name}")
                    return

        self.predefined_label.SetLabel("")

    def get_color(self) -> wx.Colour:
        """Get the selected color"""
        return self.color


class ColorSettingsDialog(wx.Dialog):
    """Dialog for managing application color settings"""

    def __init__(self, parent, color_settings):
        super().__init__(parent, title="Color Settings", size=(600, 500))

        self.color_settings = color_settings
        self.color_buttons = []  # Initialize color buttons list
        self.create_ui()
        self.populate_colors()
        self.CenterOnParent()

    def create_ui(self):
        """Create the user interface"""
        panel = wx.Panel(self)
        main_sizer = wx.BoxSizer(wx.VERTICAL)

        # Instructions
        instructions = wx.StaticText(panel,
                                     label="Click on a color to change it. "
                                           "Changes are applied immediately.")
        main_sizer.Add(instructions, 0, wx.ALL, 10)

        # Color list
        self.create_color_list(panel, main_sizer)

        # Buttons
        self.create_buttons(panel, main_sizer)

        panel.SetSizer(main_sizer)

    def create_color_list(self, parent, sizer):
        """Create the color list control"""
        list_box = wx.StaticBox(parent, label="Application Colors")
        list_sizer = wx.StaticBoxSizer(list_box, wx.VERTICAL)

        # Create scrolled panel for the color list
        self.scroll_panel = wx.ScrolledWindow(parent, style=wx.VSCROLL)
        self.scroll_panel.SetScrollRate(0,
                                        20)  # Only vertical scrolling, 20 pixels per step

        # Create sizer for the scrolled content
        scroll_sizer = wx.BoxSizer(wx.VERTICAL)

        # Create header within the scrolled panel
        header_sizer = wx.BoxSizer(wx.HORIZONTAL)
        header_color = wx.StaticText(self.scroll_panel, label="Color",
                                     size=(80, -1))
        header_color.SetFont(header_color.GetFont().MakeBold())
        header_desc = wx.StaticText(self.scroll_panel, label="Description",
                                    size=(400, -1))
        header_desc.SetFont(header_desc.GetFont().MakeBold())

        header_sizer.Add(header_color, 0,
                         wx.ALL | wx.ALIGN_CENTER_VERTICAL, 5)
        header_sizer.Add(header_desc, 1, wx.ALL | wx.ALIGN_CENTER_VERTICAL,
                         5)
        scroll_sizer.Add(header_sizer, 0, wx.EXPAND | wx.ALL, 5)

        # Add separator line
        line = wx.StaticLine(self.scroll_panel)
        scroll_sizer.Add(line, 0, wx.EXPAND | wx.LEFT | wx.RIGHT, 5)

        # Store references for adding color rows
        self.color_rows_sizer = scroll_sizer
        self.color_parent = self.scroll_panel

        # Set the sizer for the scrolled panel
        self.scroll_panel.SetSizer(scroll_sizer)

        # Add scrolled panel to the main sizer
        list_sizer.Add(self.scroll_panel, 1, wx.EXPAND | wx.ALL, 5)
        sizer.Add(list_sizer, 1, wx.EXPAND | wx.ALL, 10)

    def create_buttons(self, parent, sizer):
        """Create dialog buttons"""
        btn_sizer = wx.BoxSizer(wx.HORIZONTAL)

        reset_all_btn = wx.Button(parent, label="Reset All to Defaults")
        reset_all_btn.Bind(wx.EVT_BUTTON, self.on_reset_all)
        btn_sizer.Add(reset_all_btn, 0, wx.RIGHT, 10)

        btn_sizer.AddStretchSpacer()

        close_btn = wx.Button(parent, wx.ID_CLOSE, "Close")
        close_btn.Bind(wx.EVT_BUTTON, self.on_close)
        btn_sizer.Add(close_btn, 0)

        sizer.Add(btn_sizer, 0, wx.EXPAND | wx.ALL, 10)

    def populate_colors(self):
        """Populate the color list"""
        # Clear existing color rows (keep header and separator)
        if hasattr(self, 'color_buttons'):
            for btn, label in self.color_buttons:
                btn.Destroy()
                label.Destroy()

        self.color_buttons = []

        for key in self.color_settings.get_all_keys():
            description = self.color_settings.get_description(key)
            color = self.color_settings.get(key)

            # Create horizontal sizer for this color row
            row_sizer = wx.BoxSizer(wx.HORIZONTAL)

            # Create color button with border
            color_btn = wx.Button(self.color_parent, size=(80, 30))
            color_btn.SetBackgroundColour(color)

            # Create HTTP color code for tooltip
            color_text = f"#{color.Red():02X}{color.Green():02X}{color.Blue():02X}"
            if color.Alpha() < 255:
                color_text += f"{color.Alpha():02X}"
            color_btn.SetToolTip(color_text)

            # Bind button click event
            color_btn.Bind(wx.EVT_BUTTON,
                           lambda evt, k=key: self.on_color_button_clicked(
                               evt, k))

            # Create description label
            desc_label = wx.StaticText(self.color_parent,
                                       label=description,
                                       size=(400, -1))
            desc_label.SetToolTip(f"Internal name: {key}")

            # Add to row sizer
            row_sizer.Add(color_btn, 0, wx.ALL | wx.ALIGN_CENTER_VERTICAL,
                          5)
            row_sizer.Add(desc_label, 1, wx.ALL | wx.ALIGN_CENTER_VERTICAL,
                          5)

            # Add row to main sizer
            self.color_rows_sizer.Add(row_sizer, 0, wx.EXPAND)

            # Store button and label references
            self.color_buttons.append((color_btn, desc_label))

        # Refresh layout and update scroll panel
        self.scroll_panel.SetSizer(self.color_rows_sizer)
        self.scroll_panel.FitInside()  # Update virtual size for scrolling
        self.Layout()

    def on_color_button_clicked(self, event, key):
        """Handle color button click"""
        description = self.color_settings.get_description(key)
        current_color = self.color_settings.get(key)
        default_color = self.color_settings.get_default(key)

        # Open color picker dialog
        dialog = ColorPickerDialog(self,
                                   f"Select {description}",
                                   current_color, default_color)
        if dialog.ShowModal() == wx.ID_OK:
            new_color = dialog.get_color()
            self.color_settings.set(key, new_color)

            # Refresh the display
            self.populate_colors()  # Repopulate to update colors

        dialog.Destroy()

    def on_reset_all(self, event):
        """Reset all colors to defaults"""
        result = wx.MessageBox(
            "Reset all colors to their default values?",
            "Reset Colors",
            wx.YES_NO | wx.ICON_QUESTION
        )

        if result == wx.YES:
            self.color_settings.reset_to_defaults()
            self.populate_colors()  # Repopulate to update colors

    def on_close(self, event):
        """Close the dialog"""
        self.EndModal(wx.ID_OK)
