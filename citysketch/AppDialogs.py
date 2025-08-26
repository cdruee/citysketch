import re
import sys

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

        version = re.sub('\+.*', '', __version__)
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

        szrTop.Add(szrRight, 0, wx.ALL | wx.ALIGN_CENTER_VERTICAL, 5)

        szrMain.Add(szrTop, 0, wx.ALL, 5)

        btnSzr = self.CreateSeparatedButtonSizer(wx.CLOSE)
        szrMain.Add(btnSzr, 0, wx.ALL | wx.EXPAND, 5)

        #self.SetSizer(szrMain)
        self.SetSizerAndFit(szrMain)

        szrMain.SetSizeHints(self)


# =========================================================================

class BasemapDialog(wx.Dialog):
    """Dialog for selecting and configuring basemap"""

    def __init__(self, parent, current_provider, lat, lon):
        super().__init__(parent, title="Select Basemap", size=(450, 500))

        self.provider = current_provider
        self.lat = lat
        self.lon = lon

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

        #panel.SetSizer(sizer)
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

    def set_location(self, lat, lon):
        """Set location in text controls"""
        self.lat_ctrl.SetValue(f"{lat:.6f}")
        self.lon_ctrl.SetValue(f"{lon:.6f}")

    def get_values(self):
        """Get the current values"""
        try:
            lat = float(self.lat_ctrl.GetValue())
            lon = float(self.lon_ctrl.GetValue())
        except ValueError:
            lat = self.lat
            lon = self.lon

        return self.provider, lat, lon


# =========================================================================

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

        # panel.SetSizer(sizer)
        panel.SetSizerAndFit(sizer)


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
