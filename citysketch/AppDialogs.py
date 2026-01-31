import json
import re
import sys
import threading
import urllib.request
import urllib.parse

import wx
from numpy import __version__ as numpy_ver

try:
    from rasterio import __version__ as rasterio_ver
except ImportError:
    rasterio_ver = None
try:
    from osgeo import __version__ as gdal_ver
except ImportError:
    gdal_ver = None


from ._version import __version__
from .utils import MapProvider


# =========================================================================

class AboutDialog(wx.Dialog):
    def __init__(self, parent):
        wx.Dialog.__init__(self, parent, title="About")
        self._create()
        self.CenterOnParent()

    def _create(self):
        szrMain = wx.BoxSizer(wx.VERTICAL)
        szrTop = wx.BoxSizer(wx.HORIZONTAL)

        # left
        bmpCtrl = wx.StaticBitmap(self, wx.ID_ANY, wx.Bitmap(
            'citysketch_logo.png', wx.BITMAP_TYPE_PNG))
        szrTop.Add(bmpCtrl, 0, wx.ALL | wx.ALIGN_CENTER_VERTICAL, 5)

        # right
        szrRight = wx.BoxSizer(wx.VERTICAL)

        version = re.sub(r'\+.*', '', __version__)
        sTitle = f'CitySketch ({version})'
        label = wx.StaticText(self, wx.ID_STATIC, sTitle)
        fntTitle = label.GetFont()
        fntTitle.MakeLarger()
        fntTitle.MakeBold()
        label.SetFont(fntTitle)
        szrRight.Add(label, 0, wx.ALL | wx.ALIGN_CENTER, 5)

        label = wx.StaticText(self, wx.ID_STATIC,
                              'Copyright (c) 2025 Clemens Drüe')
        szrRight.Add(label, 0, wx.BOTTOM | wx.ALIGN_CENTER, 5)

        label = wx.StaticText(self, wx.ID_STATIC,
                              f'Library Versions:\n'
                              f'- wxPython: {wx.__version__}\n'
                              f'- Python: {sys.version.split()[0]}\n'
                              f'- NumPy: {numpy_ver}\n'
                              f'- rasterio: {rasterio_ver}\n'
                              f'- gdal: {gdal_ver}')
        szrRight.Add(label, 0, wx.LEFT | wx.TOP | wx.ALIGN_CENTER, 5)

        label = wx.StaticText(self, wx.ID_STATIC,
                              'Map Data Sources:\n'
                              '- OpenStreetMap: © OpenStreetMap contributors\n'
                              '- Satellite: © Esri World Imagery\n'
                              '- Terrain: © OpenTopoMap (CC-BY-SA)')
        szrRight.Add(label, 0,
                     wx.LEFT | wx.RIGHT | wx.TOP | wx.ALIGN_CENTER, 5)

        label = wx.StaticText(self, wx.ID_STATIC,
                              'UI code developed with assistance from '
                              'Claude (Anthropic)')
        szrRight.Add(label, 0,
                     wx.LEFT | wx.RIGHT | wx.TOP | wx.ALIGN_CENTER, 5)

        szrTop.Add(szrRight, 0, wx.ALL | wx.ALIGN_CENTER_VERTICAL, 5)

        szrMain.Add(szrTop, 0, wx.ALL, 5)

        btnSzr = self.CreateSeparatedButtonSizer(wx.CLOSE)
        szrMain.Add(btnSzr, 0, wx.ALL | wx.EXPAND, 5)

        #self.SetSizer(szrMain)
        self.SetSizerAndFit(szrMain)

        szrMain.SetSizeHints(self)


# =========================================================================

class BasemapDialog(wx.Dialog):
    """Dialog for selecting basemap provider"""

    def __init__(self, parent, current_provider):
        super().__init__(parent, title="Select Basemap", size=(300, 250))

        self.provider = current_provider

        panel = wx.Panel(self)
        sizer = wx.BoxSizer(wx.VERTICAL)

        # Map provider selection
        lblList = [p.value for p in MapProvider]
        self.provider_box = wx.RadioBox(panel, label="Map Provider",
                                        choices=lblList,
                                        majorDimension=1,
                                        style=wx.RA_SPECIFY_COLS)
        self.provider_box.SetStringSelection(current_provider.value)
        sizer.Add(self.provider_box, 0, wx.EXPAND | wx.ALL, 10)
        self.provider_box.Bind(wx.EVT_RADIOBOX, self.on_provider_changed)

        # Add some spacing
        sizer.Add((-1, 10))

        # Buttons
        btn_sizer = wx.StdDialogButtonSizer()
        ok_btn = wx.Button(panel, wx.ID_OK)
        cancel_btn = wx.Button(panel, wx.ID_CANCEL)
        btn_sizer.AddButton(ok_btn)
        btn_sizer.AddButton(cancel_btn)
        btn_sizer.Realize()
        sizer.Add(btn_sizer, 0, wx.EXPAND | wx.ALL, 10)

        panel.SetSizerAndFit(sizer)

        # Center the dialog
        self.Centre()

    def on_provider_changed(self, event):
        """Handle provider selection change"""
        rb = event.GetEventObject()
        label = rb.GetStringSelection()
        for p in MapProvider:
            if p.value == label:
                provider = p
                break
        else:
            return
        self.provider = provider

    def get_values(self):
        """Get the current values"""
        return self.provider


# =========================================================================

class CenterLocationDialog(wx.Dialog):
    """Dialog for setting and configuring map center location"""

    def __init__(self, parent, lat, lon, show_marker=False):
        super().__init__(parent, title="Center Location", size=(450, 620))

        self.lat = lat
        self.lon = lon
        self.show_marker = show_marker

        panel = wx.Panel(self)
        sizer = wx.BoxSizer(wx.VERTICAL)

        # Location settings
        location_box = wx.StaticBox(panel, label="Map Center Location")
        location_sizer = wx.StaticBoxSizer(location_box, wx.VERTICAL)

        # Latitude
        lat_box = wx.BoxSizer(wx.HORIZONTAL)
        lat_label = wx.StaticText(panel, label="Latitude:", size=(80, -1))
        lat_box.Add(lat_label, 0, wx.ALIGN_CENTER_VERTICAL | wx.RIGHT, 5)
        self.lat_ctrl = wx.TextCtrl(panel, value=f"{self.lat:.6f}")
        lat_box.Add(self.lat_ctrl, 1, wx.EXPAND)
        location_sizer.Add(lat_box, 0, wx.EXPAND | wx.ALL, 5)

        # Longitude
        lon_box = wx.BoxSizer(wx.HORIZONTAL)
        lon_label = wx.StaticText(panel, label="Longitude:", size=(80, -1))
        lon_box.Add(lon_label, 0, wx.ALIGN_CENTER_VERTICAL | wx.RIGHT, 5)
        self.lon_ctrl = wx.TextCtrl(panel, value=f"{self.lon:.6f}")
        lon_box.Add(self.lon_ctrl, 1, wx.EXPAND)
        location_sizer.Add(lon_box, 0, wx.EXPAND | wx.ALL, 5)

        # Look up coordinates section
        lookup_label = wx.StaticText(panel, label="Look up coordinates")
        lookup_label.SetFont(lookup_label.GetFont().MakeBold())
        location_sizer.Add(lookup_label, 0, wx.LEFT | wx.TOP, 5)

        # Place name input
        place_box = wx.BoxSizer(wx.HORIZONTAL)
        place_label = wx.StaticText(panel, label="Place:", size=(80, -1))
        place_box.Add(place_label, 0, wx.ALIGN_CENTER_VERTICAL | wx.RIGHT, 5)
        self.place_ctrl = wx.TextCtrl(panel, value="",
                                      style=wx.TE_PROCESS_ENTER)
        self.place_ctrl.SetHint("Enter place name...")
        place_box.Add(self.place_ctrl, 1, wx.EXPAND | wx.RIGHT, 5)
        self.lookup_btn = wx.Button(panel, label="Search")
        place_box.Add(self.lookup_btn, 0)
        location_sizer.Add(place_box, 0, wx.EXPAND | wx.ALL, 5)

        # Results list
        self.results_list = wx.ListBox(panel, size=(-1, 110),
                                       style=wx.LB_SINGLE)
        location_sizer.Add(self.results_list, 0, wx.EXPAND | wx.LEFT | wx.RIGHT, 5)

        # Use button and status
        result_action_box = wx.BoxSizer(wx.HORIZONTAL)
        self.lookup_status = wx.StaticText(panel, label="")
        self.lookup_status.SetFont(self.lookup_status.GetFont().MakeSmaller())
        result_action_box.Add(self.lookup_status, 1, wx.ALIGN_CENTER_VERTICAL)
        self.use_btn = wx.Button(panel, label="Apply")
        self.use_btn.Enable(False)
        result_action_box.Add(self.use_btn, 0)
        location_sizer.Add(result_action_box, 0, wx.EXPAND | wx.ALL, 5)

        # Store lookup results data
        self._lookup_results = []

        # Bind lookup events
        self.lookup_btn.Bind(wx.EVT_BUTTON, self.on_lookup)
        self.place_ctrl.Bind(wx.EVT_TEXT_ENTER, self.on_lookup)
        self.results_list.Bind(wx.EVT_LISTBOX, self.on_result_selected)
        self.results_list.Bind(wx.EVT_LISTBOX_DCLICK, self.on_result_dclick)
        self.use_btn.Bind(wx.EVT_BUTTON, self.on_use_result)

        # Quick location buttons - arranged in 2x2 grid
        quick_label = wx.StaticText(panel, label="Quick Locations:")
        location_sizer.Add(quick_label, 0, wx.LEFT | wx.TOP, 5)

        quick_grid = wx.GridSizer(2, 2, 5, 5)

        locations = [
            ("Berlin", 52.5200, 13.4050),
            ("Hannover", 52.3747, 9.7385),
            ("Trier", 49.7523, 6.6370),
            ("Mannheim", 49.4875, 8.4660),
        ]

        for name, lat, lon in locations:
            btn = wx.Button(panel, label=name, size=(90, 28))
            btn.Bind(wx.EVT_BUTTON,
                     lambda e, la=lat, lo=lon: self.set_location(la, lo))
            quick_grid.Add(btn, 0, wx.EXPAND)

        location_sizer.Add(quick_grid, 0, wx.ALL | wx.EXPAND, 5)
        sizer.Add(location_sizer, 0,
                  wx.EXPAND | wx.LEFT | wx.RIGHT | wx.BOTTOM, 10)

        # Marker settings
        marker_box = wx.StaticBox(panel, label="Center Marker")
        marker_sizer = wx.StaticBoxSizer(marker_box, wx.VERTICAL)

        self.marker_cb = wx.CheckBox(panel, label="Show center location marker")
        self.marker_cb.SetValue(show_marker)
        marker_sizer.Add(self.marker_cb, 0, wx.ALL, 5)

        # Marker description
        marker_desc = wx.StaticText(
            panel, 
            label="Displays a pin marker at the center location\n"
                  "to help identify the reference point."
        )
        marker_desc.SetFont(marker_desc.GetFont().MakeSmaller())
        marker_sizer.Add(marker_desc, 0, wx.LEFT | wx.BOTTOM, 5)

        sizer.Add(marker_sizer, 0,
                  wx.EXPAND | wx.LEFT | wx.RIGHT | wx.BOTTOM, 10)

        # Buttons
        btn_sizer = wx.StdDialogButtonSizer()
        ok_btn = wx.Button(panel, wx.ID_OK)
        ok_btn.SetDefault()
        cancel_btn = wx.Button(panel, wx.ID_CANCEL)
        btn_sizer.AddButton(ok_btn)
        btn_sizer.AddButton(cancel_btn)
        btn_sizer.Realize()
        sizer.Add(btn_sizer, 0, wx.EXPAND | wx.ALL, 10)

        panel.SetSizer(sizer)
        
        # Make panel fill the dialog
        dialog_sizer = wx.BoxSizer(wx.VERTICAL)
        dialog_sizer.Add(panel, 1, wx.EXPAND)
        self.SetSizer(dialog_sizer)

        # Center the dialog
        self.Centre()

    def set_location(self, lat, lon):
        """Set location in text controls"""
        self.lat_ctrl.SetValue(f"{lat:.6f}")
        self.lon_ctrl.SetValue(f"{lon:.6f}")

    def on_lookup(self, event):
        """Handle place name lookup using Nominatim"""
        place_name = self.place_ctrl.GetValue().strip()
        if not place_name:
            self.lookup_status.SetLabel("Please enter a place name.")
            return

        # Clear previous results
        self.results_list.Clear()
        self._lookup_results = []
        self.use_btn.Enable(False)

        # Disable button and show searching status
        self.lookup_btn.Enable(False)
        self.lookup_status.SetLabel("Searching...")

        # Run lookup in background thread to keep UI responsive
        thread = threading.Thread(target=self._do_lookup, args=(place_name,))
        thread.daemon = True
        thread.start()

    def _do_lookup(self, place_name):
        """Perform the actual Nominatim lookup in a background thread"""
        try:
            # Build Nominatim API URL
            params = urllib.parse.urlencode({
                'q': place_name,
                'format': 'json',
                'limit': 5
            })
            url = f"https://nominatim.openstreetmap.org/search?{params}"

            # Create request with User-Agent (required by Nominatim)
            request = urllib.request.Request(
                url,
                headers={'User-Agent': 'CitySketch/1.0'}
            )

            # Perform the request
            with urllib.request.urlopen(request, timeout=10) as response:
                data = json.loads(response.read().decode('utf-8'))

            # Process result on main thread
            wx.CallAfter(self._handle_lookup_result, data, place_name)

        except urllib.error.URLError as e:
            wx.CallAfter(self._handle_lookup_error, f"Network error: {e.reason}")
        except json.JSONDecodeError:
            wx.CallAfter(self._handle_lookup_error, "Invalid response from server")
        except Exception as e:
            wx.CallAfter(self._handle_lookup_error, str(e))

    def _handle_lookup_result(self, data, place_name):
        """Handle successful lookup result (called on main thread)"""
        self.lookup_btn.Enable(True)
        self.results_list.Clear()
        self._lookup_results = []

        if not data:
            self.lookup_status.SetLabel(f"No results for '{place_name}'")
            return

        # Store results and populate list
        for result in data:
            try:
                lat = float(result['lat'])
                lon = float(result['lon'])
                display_name = result.get('display_name', 'Unknown')

                # Truncate long display names
                if len(display_name) > 60:
                    display_name = display_name[:57] + "..."

                self._lookup_results.append((lat, lon, display_name))
                self.results_list.Append(display_name)

            except (KeyError, ValueError):
                continue

        if self._lookup_results:
            self.lookup_status.SetLabel(f"{len(self._lookup_results)} result(s) found")
            # Select first result by default
            self.results_list.SetSelection(0)
            self.use_btn.Enable(True)
        else:
            self.lookup_status.SetLabel("No valid results")

    def _handle_lookup_error(self, error_msg):
        """Handle lookup error (called on main thread)"""
        self.lookup_btn.Enable(True)
        self.lookup_status.SetLabel(f"Error: {error_msg}")

    def on_result_selected(self, event):
        """Handle selection change in results list"""
        selection = self.results_list.GetSelection()
        self.use_btn.Enable(selection != wx.NOT_FOUND)

    def on_result_dclick(self, event):
        """Handle double-click on a result - apply it immediately"""
        self.on_use_result(event)

    def on_use_result(self, event):
        """Apply the selected result to the coordinate fields"""
        selection = self.results_list.GetSelection()
        if selection == wx.NOT_FOUND or selection >= len(self._lookup_results):
            return

        lat, lon, display_name = self._lookup_results[selection]
        self.set_location(lat, lon)

    def get_values(self):
        """Get the current values"""
        try:
            lat = float(self.lat_ctrl.GetValue())
            lon = float(self.lon_ctrl.GetValue())
        except ValueError:
            lat = self.lat
            lon = self.lon

        show_marker = self.marker_cb.GetValue()
        return lat, lon, show_marker


# =========================================================================

class HeightDialog(wx.Dialog):
    """Dialog for setting building height by stories or direct height input"""

    def __init__(self, parent, stories=3, height=10.0, storey_height=3.3):
        super().__init__(parent, title="Set Building Height")

        self.storey_height = storey_height
        self._updating = False  # Flag to prevent recursive updates

        sizer = wx.BoxSizer(wx.VERTICAL)

        # Mode selection radio buttons
        mode_box = wx.StaticBox(self, label="Input Mode")
        mode_sizer = wx.StaticBoxSizer(mode_box, wx.VERTICAL)
        
        self.stories_radio = wx.RadioButton(self, label="By number of stories",
                                            style=wx.RB_GROUP)
        self.height_radio = wx.RadioButton(self, label="By height (meters)")
        
        mode_sizer.Add(self.stories_radio, 0, wx.ALL, 5)
        mode_sizer.Add(self.height_radio, 0, wx.LEFT | wx.RIGHT | wx.BOTTOM, 5)
        sizer.Add(mode_sizer, 0, wx.EXPAND | wx.ALL, 10)

        # Stories control
        stories_box = wx.BoxSizer(wx.HORIZONTAL)
        self.stories_label = wx.StaticText(self, label="Stories:", size=(80, -1))
        stories_box.Add(self.stories_label, 0,
                        wx.ALIGN_CENTER_VERTICAL | wx.RIGHT, 5)
        self.stories_ctrl = wx.SpinCtrl(self, value=str(stories), min=1,
                                        max=100, size=(100, -1))
        stories_box.Add(self.stories_ctrl, 1, wx.EXPAND)
        sizer.Add(stories_box, 0, wx.EXPAND | wx.LEFT | wx.RIGHT, 10)

        # Height control
        height_box = wx.BoxSizer(wx.HORIZONTAL)
        self.height_label = wx.StaticText(self, label="Height (m):", size=(80, -1))
        height_box.Add(self.height_label, 0,
                       wx.ALIGN_CENTER_VERTICAL | wx.RIGHT, 5)
        self.height_ctrl = wx.TextCtrl(self, value=f"{height:.1f}", size=(100, -1))
        height_box.Add(self.height_ctrl, 1, wx.EXPAND)
        sizer.Add(height_box, 0, wx.EXPAND | wx.ALL, 10)

        # Info text
        self.info_text = wx.StaticText(
            self, 
            label=f"(Storey height: {storey_height:.1f} m)"
        )
        self.info_text.SetFont(self.info_text.GetFont().MakeSmaller())
        sizer.Add(self.info_text, 0, wx.LEFT | wx.BOTTOM, 10)

        # Buttons
        btn_sizer = self.CreateStdDialogButtonSizer(wx.OK | wx.CANCEL)
        sizer.Add(btn_sizer, 0, wx.EXPAND | wx.ALL, 10)

        self.SetSizerAndFit(sizer)

        # Bind events
        self.stories_radio.Bind(wx.EVT_RADIOBUTTON, self.on_mode_changed)
        self.height_radio.Bind(wx.EVT_RADIOBUTTON, self.on_mode_changed)
        self.stories_ctrl.Bind(wx.EVT_SPINCTRL, self.on_stories_changed)
        self.height_ctrl.Bind(wx.EVT_TEXT, self.on_height_changed)

        # Initialize in stories mode
        self.stories_radio.SetValue(True)
        self._update_controls_state()

        # Center the dialog
        self.Centre()

    def on_mode_changed(self, event):
        """Handle mode radio button change"""
        if self.height_radio.GetValue():
            # Switching from stories to height mode
            # Keep current height value, disable stories
            pass
        else:
            # Switching from height to stories mode
            # Calculate stories from current height
            try:
                height = float(self.height_ctrl.GetValue())
                stories = max(1, round(height / self.storey_height))
                self._updating = True
                self.stories_ctrl.SetValue(stories)
                # Update height to match exact stories
                new_height = stories * self.storey_height
                self.height_ctrl.SetValue(f"{new_height:.1f}")
                self._updating = False
            except ValueError:
                pass
        
        self._update_controls_state()

    def _update_controls_state(self):
        """Update enabled/disabled state of controls based on mode"""
        stories_mode = self.stories_radio.GetValue()
        
        # In stories mode: stories enabled, height disabled (shows calculated value)
        # In height mode: stories disabled, height editable
        self.stories_ctrl.Enable(stories_mode)
        self.stories_label.Enable(stories_mode)
        
        self.height_ctrl.Enable(not stories_mode)
        self.height_label.Enable(not stories_mode)
        
        # Update visual appearance
        if stories_mode:
            self.height_ctrl.SetBackgroundColour(
                wx.SystemSettings.GetColour(wx.SYS_COLOUR_BTNFACE))
        else:
            self.height_ctrl.SetBackgroundColour(
                wx.SystemSettings.GetColour(wx.SYS_COLOUR_WINDOW))

    def on_stories_changed(self, event):
        """Update height when stories change (only in stories mode)"""
        if self._updating:
            return
        if not self.stories_radio.GetValue():
            return
            
        stories = self.stories_ctrl.GetValue()
        height = stories * self.storey_height
        self._updating = True
        self.height_ctrl.SetValue(f"{height:.1f}")
        self._updating = False

    def on_height_changed(self, event):
        """Validate height input (only active in height mode)"""
        if self._updating:
            return
        
        # In stories mode, height field is disabled so this shouldn't trigger
        if self.stories_radio.GetValue():
            return
            
        try:
            height = float(self.height_ctrl.GetValue())
            if height < 0:
                self.height_ctrl.SetBackgroundColour(
                    wx.Colour(255, 200, 200))
            else:
                self.height_ctrl.SetBackgroundColour(
                    wx.SystemSettings.GetColour(wx.SYS_COLOUR_WINDOW))
        except ValueError:
            self.height_ctrl.SetBackgroundColour(wx.Colour(255, 200, 200))

    def get_values(self):
        """
        Get the current values.
        
        Returns:
            tuple: (stories, height) where stories is None if in height-only mode
        """
        try:
            height = float(self.height_ctrl.GetValue())
        except ValueError:
            height = self.storey_height  # Default fallback
            
        if self.stories_radio.GetValue():
            # Stories mode: return both
            stories = self.stories_ctrl.GetValue()
        else:
            # Height mode: stories is None
            stories = None
            
        return stories, height


# =========================================================================

class GeoTiffDialog(wx.Dialog):
    """Dialog for configuring GeoTIFF overlay settings"""

    def __init__(self, parent, visible=True, opacity=0.7):
        super().__init__(parent, title="GeoTIFF Settings", size=(350, 250))

        self.visible = visible
        self.opacity = opacity

        panel = wx.Panel(self)
        sizer = wx.BoxSizer(wx.VERTICAL)

        # Visibility checkbox
        self.visible_cb = wx.CheckBox(panel, label="Show GeoTIFF overlay")
        self.visible_cb.SetValue(visible)
        sizer.Add(self.visible_cb, 0, wx.ALL, 10)

        # Opacity slider
        opacity_box = wx.StaticBox(panel, label="Opacity")
        opacity_sizer = wx.StaticBoxSizer(opacity_box, wx.VERTICAL)

        # Create horizontal sizer for slider and value
        slider_sizer = wx.BoxSizer(wx.HORIZONTAL)

        self.opacity_slider = wx.Slider(
            panel, value=int(opacity * 100),
            minValue=0, maxValue=100,
            style=wx.SL_HORIZONTAL | wx.SL_LABELS)
        slider_sizer.Add(self.opacity_slider, 1,
                         wx.EXPAND | wx.RIGHT, 5)

        self.opacity_text = wx.StaticText(panel, label=f"{opacity:.0%}")
        slider_sizer.Add(self.opacity_text, 0,
                         wx.ALIGN_CENTER_VERTICAL)

        opacity_sizer.Add(slider_sizer, 0, wx.EXPAND | wx.ALL, 5)
        sizer.Add(opacity_sizer, 0,
                  wx.EXPAND | wx.LEFT | wx.RIGHT | wx.BOTTOM, 10)

        # # Info text
        # info_text = wx.StaticText(panel,
        #                           label="The GeoTIFF overlay will be displayed between\n"
        #                                 "the basemap and building layers.")
        # info_text.SetFont(info_text.GetFont().MakeSmaller())
        # sizer.Add(info_text, 0, wx.ALL | wx.ALIGN_CENTER, 10)

        # Buttons
        btn_sizer = wx.StdDialogButtonSizer()
        ok_btn = wx.Button(panel, wx.ID_OK)
        cancel_btn = wx.Button(panel, wx.ID_CANCEL)
        btn_sizer.AddButton(ok_btn)
        btn_sizer.AddButton(cancel_btn)
        btn_sizer.Realize()
        sizer.Add(btn_sizer, 0, wx.EXPAND | wx.ALL, 10)

        #panel.SetSizer(sizer)
        panel.SetSizerAndFit(sizer)

        # Bind events
        self.opacity_slider.Bind(wx.EVT_SLIDER, self.on_opacity_changed)

        # Center the dialog
        self.Centre()

    def on_opacity_changed(self, event):
        """Handle opacity slider change"""
        value = self.opacity_slider.GetValue() / 100.0
        self.opacity_text.SetLabel(f"{value:.0%}")

    def get_values(self):
        """Get the current values"""
        visible = self.visible_cb.GetValue()
        opacity = self.opacity_slider.GetValue() / 100.0
        return visible, opacity

# =========================================================================
