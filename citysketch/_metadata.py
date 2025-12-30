"""
Module to make the metadata from pyproject.toml available in the module
"""
from datetime import datetime
import os

__title__ = "citysketch"

year = datetime.now().year
__copyright__ = f'(C) 2022-{year} Clemens Drüe'

def get_metadata():
    """Get package metadata from pyproject.toml or use defaults"""
    try:
        from importlib.metadata import metadata, version
    except ImportError:
        # Python < 3.8
        from importlib_metadata import metadata, version

    try:
        meta = metadata(__title__)
        return {
            '__version__': version(__title__),
            '__author__': meta.get("Author", ""),
            '__author_email__': meta.get("Author-email", ""),
            '__description__': meta.get("Summary", ""),
            '__url__': meta.get("Home-page", ""),
            '__license__': meta.get("License", ""),
        }
    except Exception:
        # Package not installed, try to get version from _version.py if it exists
        version_str = "unknown"
        try:
            from ._version import version as scm_version
            version_str = scm_version
        except ImportError:
            # Try to read from _version.py file
            version_file = os.path.join(os.path.dirname(__file__), '_version.py')
            if os.path.exists(version_file):
                version_data = {}
                with open(version_file) as f:
                    exec(f.read(), version_data)
                version_str = version_data.get('version', 'unknown')

        # Return default values when package is not installed
        return {
            '__version__': version_str,
            '__author__': 'Clemens Drüe',
            '__author_email__': 'druee@uni-trier.de',
            '__description__': 'A visual building editor with interactive building placement, basemap overlays, and real-time 3D height editing.',
            '__url__': 'https://github.com/cdruee/citysketch',
            '__license__': 'EUPL-1.2',
        }

_meta = get_metadata()
__version__ = _meta.get('__version__', 'unknown')
__author__ = _meta.get('__author__', '')
__author_email__ = _meta.get('__author_email__', '')
__description__ = _meta.get('__description__', '')
__url__ = _meta.get('__url__', '')
__license__ = _meta.get('__license__', '')