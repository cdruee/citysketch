### CitySketch

![CitySketch logo](https://github.com/cdruee/citysketch/raw/main/logo/citysketch_logo.png)

A visual building editor for use with AUSTAL
with interactive building placement, 
basemap overlays, and real-time 3D height editing.

[![PyPi Version](https://img.shields.io/pypi/v/citysketch.svg?logo=python)](https://pypi.python.org/pypi/citysketch/)
[![GitHub Release](https://img.shields.io/github/v/release/cdruee/citysketch?logo=github&label=Github)](https://github.com/cdruee/citysketch/releases/latest)
<!--
[![DOI](https://zenodo.org/badge/968131323.svg)](https://doi.org/10.5281/zenodo.18404450)
-->

### Installation

#### Prerequisites

CitySketch requires the following software components:

**Required Dependencies:**

* Python 3.7 or higher
* wxPython 4.0+
* NumPy

**Optional Dependencies:**

* **rasterio and GDAL**: For GeoTIFF overlay support
* **PyOpenGL and PyOpenGL_accelerate**: For 3D visualization
* **scipy**: For advanced image processing

#### Installing with pip

```bash
pip install citysketch
```

#### Installing from PyPi

1. Clone the repository:

   ```bash
   pip install citysketch
   ```

2. Install all dependencies:

   ```bash
   pip install 'citysketch[full]'
   ```

#### Installing from Source

1. Clone the repository:

   ```bash
   git clone https://github.com/cdruee/citysketch.git
   cd citysketch
   ```

2. Install dependencies:

   ```bash
   pip install -r requirements.txt
   ```

3. Install optional Dependencies

For full functionality, install optional dependencies:

```bash
## For GeoTIFF support
pip install rasterio gdal

## For 3D visualization
pip install PyOpenGL PyOpenGL_accelerate

## For advanced image processing
pip install scipy
```

### First Launch

#### Starting CitySketch

After installation, start CitySketch by running:

```bash
citysketch
```

Or from Python:

```python
from citysketch.AppMain import main
main()
```
