import json
import math
import urllib.request
from enum import Enum

from osgeo import osr
osr.UseExceptions()

# -------------------------------------------------------------------------

# WGS84 - World Geodetic System 1984, https://epsg.io/4326
LL = osr.SpatialReference()
LL.ImportFromEPSG(4326)
# DHDN / 3-degree Gauss-Kruger zone 3 (E-N), https://epsg.io/5677
GK = osr.SpatialReference()
GK.ImportFromEPSG(5677)
# ETRS89 / UTM zone 32N, https://epsg.io/25832
UT = osr.SpatialReference()
UT.ImportFromEPSG(25832)
# WGS 84 / Pseudo-Mercator, https://epsg.io/3857
WM =  osr.SpatialReference()
WM.ImportFromEPSG(3857)

# =========================================================================

class MapProvider(Enum):
    NONE = "None"
    OSM = "OpenStreetMap"
    SATELLITE = "Satellite"
    TERRAIN = "Terrain"
    HILLSHADE = "Hillshade"

# =========================================================================

def get_epsg2ll(epsg_id: int):
    crs = osr.SpatialReference()
    crs.ImportFromEPSG(int(epsg_id))
    return osr.CoordinateTransformation(crs, LL)

def gk2ll(rechts: float, hoch: float) -> tuple[float, float]:
    """
    Converts Gauss-Krüger rechts/hoch (east/north) coordinates
    (DHDN / 3-degree Gauss-Kruger zone 3 (E-N), https://epsg.io/5677)
    into Latitude/longitude  (WGS84, https://epsg.io/4326) position.

    :param rechts: "Rechtswert" (eastward coordinate) in m
    :type: float
    :param hoch: "Hochwert" (northward coordinate) in m
    :type: float
    :return: latitude in degrees, longitude in degrees, altitude in meters
    :rtype: float, float, float
    """
    transform = osr.CoordinateTransformation(GK, LL)
    lat, lon, zz = transform.TransformPoint(rechts, hoch)
    return lat, lon

# -------------------------------------------------------------------------

def ll2gk(lat: float, lon: float) -> tuple[float, float]:
    """
    Converts Latitude/longitude  (WGS84, https://epsg.io/4326) position
    into Gauss-Krüger rechts/hoch (east/north) coordinates
    (DHDN / 3-degree Gauss-Kruger zone 3 (E-N), https://epsg.io/5677).

    :param lat: latitude in degrees
    :type: float
    :param lon: longitude in degrees
    :type: float
    :return: "Rechtswert" (eastward coordinate) in m,
        "Hochwert" (northward coordinate) in m
    :rtype: float, float
    """
    transform = osr.CoordinateTransformation(LL, GK)
    x, y, z = transform.TransformPoint(lat, lon)
    return x, y

# -------------------------------------------------------------------------

def ut2ll(east: float, north:float) -> tuple[float, float]:
    """
    Converts UTM east/north coordinates
    (ETRS89 / UTM zone 32N, https://epsg.io/25832)
    into Latitude/longitude  (WGS84, https://epsg.io/4326) position.

    :param east: eastward UTM coordinate in m
    :type: float
    :param north: northward UTM coordinate in m
    :type: float
    :return: latitude in degrees, longitude in degrees, altitude in meters
    :rtype: float, float, float
    """
    transform = osr.CoordinateTransformation(UT, LL)
    lat, lon, zz = transform.TransformPoint(east, north)
    return lat, lon

# -------------------------------------------------------------------------

def ll2ut(lat: float, lon: float) -> tuple[float, float]:
    """
    Converts Latitude/longitude  (WGS84, https://epsg.io/4326) position
    into UTM east/north coordinates
    (ETRS89 / UTM zone 32N, https://epsg.io/25832)

    :param lat: latitude in degrees
    :type: float
    :param lon: longitude in degrees
    :type: float
    :return: "easting" (eastward coordinate) in m,
        "northing" (northward coordinate) in m
    :rtype: float, float
    """
    transform = osr.CoordinateTransformation(LL, UT)
    easting, nothing, zz = transform.TransformPoint(lat, lon)
    return easting, nothing

# -------------------------------------------------------------------------

def ll2wm(lat: float, lon: float) -> tuple[float, float]:
    """
    Converts Latitude/longitude  (WGS84, https://epsg.io/4326) position
    into Web Mercator (WGS 84 / Pseudo-Mercator, https://epsg.io/3857).

    :param lat: latitude in degrees
    :type: float
    :param lon: longitude in degrees
    :type: float
    :return: eastward coordinate in m,
        northward coordinate in m
    :rtype: float, float
    """
    transform = osr.CoordinateTransformation(LL, WM)
    x, y, z = transform.TransformPoint(lat, lon)
    return x, y

# -------------------------------------------------------------------------

def wm2ll(x, y):
    """
    Converts Web Mercator (WGS 84 / Pseudo-Mercator, https://epsg.io/3857)
    into Latitude/longitude  (WGS84, https://epsg.io/4326) position.

    :param x: eastward coordinate in m
    :type: float
    :param y: northward coordinate in m
    :type: float
    :return: latitude in degrees, longitude in degrees, altitude in meters
    :rtype: float, float, float
    """
    transform = osr.CoordinateTransformation(WM, LL)
    lat, lon, zz = transform.TransformPoint(x, y)
    return lat, lon

# -------------------------------------------------------------------------

def wm2ut(x: float, y: float) -> tuple[float, float]:
    """
    Converts Web Mercator (WGS 84 / Pseudo-Mercator, https://epsg.io/3857)
    into UTM east/north coordinates (ETRS89 / UTM zone 32N, https://epsg.io/25832).

    :param x: eastward Web Mercator coordinate in m
    :type x: float
    :param y: northward Web Mercator coordinate in m
    :type y: float
    :return: easting (eastward coordinate) in m,
        northing (northward coordinate) in m
    :rtype: tuple[float, float]
    """
    transform = osr.CoordinateTransformation(WM, UT)
    easting, northing, zz = transform.TransformPoint(x, y)
    return easting, northing

# -------------------------------------------------------------------------

def ut2wm(east: float, north: float) -> tuple[float, float]:
    """
    Converts UTM east/north coordinates (ETRS89 / UTM zone 32N, https://epsg.io/25832)
    into Web Mercator (WGS 84 / Pseudo-Mercator, https://epsg.io/3857).

    :param east: eastward UTM coordinate in m
    :type east: float
    :param north: northward UTM coordinate in m
    :type north: float
    :return: x (eastward coordinate) in m,
        y (northward coordinate) in m
    :rtype: tuple[float, float]
    """
    transform = osr.CoordinateTransformation(UT, WM)
    x, y, zz = transform.TransformPoint(east, north)
    return x, y

# -------------------------------------------------------------------------

def wm2gk(x: float, y: float) -> tuple[float, float]:
    """
    Converts Web Mercator (WGS 84 / Pseudo-Mercator, https://epsg.io/3857)
    into Gauss-Krüger rechts/hoch (east/north) coordinates
    (DHDN / 3-degree Gauss-Kruger zone 3 (E-N), https://epsg.io/5677).

    :param x: eastward Web Mercator coordinate in m
    :type x: float
    :param y: northward Web Mercator coordinate in m
    :type y: float
    :return: Rechtswert (eastward coordinate) in m,
        Hochwert (northward coordinate) in m
    :rtype: tuple[float, float]
    """
    transform = osr.CoordinateTransformation(WM, GK)
    rechts, hoch, zz = transform.TransformPoint(x, y)
    return rechts, hoch

# -------------------------------------------------------------------------

def gk2wm(rechts: float, hoch: float) -> tuple[float, float]:
    """
    Converts Gauss-Krüger rechts/hoch (east/north) coordinates
    (DHDN / 3-degree Gauss-Kruger zone 3 (E-N), https://epsg.io/5677)
    into Web Mercator (WGS 84 / Pseudo-Mercator, https://epsg.io/3857).

    :param rechts: Rechtswert (eastward coordinate) in m
    :type rechts: float
    :param hoch: Hochwert (northward coordinate) in m
    :type hoch: float
    :return: x (eastward coordinate) in m,
        y (northward coordinate) in m
    :rtype: tuple[float, float]
    """
    transform = osr.CoordinateTransformation(GK, WM)
    x, y, zz = transform.TransformPoint(rechts, hoch)
    return x, y

# -------------------------------------------------------------------------

def math2geo(rot):
    return rot * 180 / math.pi

# -------------------------------------------------------------------------

def geo2math(rot):
    return rot * math.pi / 180

# -------------------------------------------------------------------------

def get_location_from_ip():
    """
    Get estimated latitude and longitude based on user's IP address.
    Returns tuple of (latitude, longitude) or None if unable to determine.
    """
    try:
        # Try multiple free IP geolocation services
        services = [
            "http://ip-api.com/json/?fields=status,lat,lon",
            "https://ipapi.co/json/",
            "https://geolocation-db.com/json/"
        ]

        for service_url in services:
            try:
                req = urllib.request.Request(service_url, headers={
                    'User-Agent': 'CityJSON Creator/1.0'
                })

                with urllib.request.urlopen(req, timeout=3) as response:
                    data = json.loads(response.read().decode('utf-8'))

                # Parse response based on service
                if 'ip-api.com' in service_url:
                    if data.get('status') == 'success':
                        return data.get('lat'), data.get('lon')

                elif 'ipapi.co' in service_url:
                    lat = data.get('latitude')
                    lon = data.get('longitude')
                    if lat and lon:
                        return lat, lon

                elif 'geolocation-db.com' in service_url:
                    lat = data.get('latitude')
                    lon = data.get('longitude')
                    if lat and lon and lat != "Not found":
                        return lat, lon

            except Exception as e:
                print(f"Failed to get location from {service_url}: {e}")
                continue

        # If all services fail, return None
        return None


    # -------------------------------------------------------------------------

    except Exception as e:
        print(f"Error getting IP location: {e}")
        return None


def get_location_with_fallback():
    """
    Get user location from IP with fallback to default location.
    Returns (latitude, longitude) tuple.
    """
    location = get_location_from_ip()

    if location and location[0] and location[1]:
        print(f"Detected location: {location[0]:.4f}, {location[1]:.4f}")
        return location
    else:
        # Fallback to default location (Camous II, Uni Trier, Germany)
        print("Could not detect location, using default")
        return (49.74795,6.67412)
