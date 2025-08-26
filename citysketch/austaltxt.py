import math
import shutil
from collections import OrderedDict
import logging
import os
import re
import shlex
import uuid

from osgeo import osr

from .Building import Building

logger = logging.getLogger(__name__)
osr.UseExceptions()

# -------------------------------------------------------------------------

MAX_CENTER_DISTANCE = 10.  # m

# WGS84 - World Geodetic System 1984, https://epsg.io/4326
LL = osr.SpatialReference()
LL.ImportFromEPSG(4326)
# DHDN / 3-degree Gauss-Kruger zone 3 (E-N), https://epsg.io/5677
GK = osr.SpatialReference()
GK.ImportFromEPSG(5677)
# ETRS89 / UTM zone 32N, https://epsg.io/25832
UT = osr.SpatialReference()
UT.ImportFromEPSG(25832)

# -------------------------------------------------------------------------

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

def math2geo(rot):
    return rot * 180 / math.pi

# -------------------------------------------------------------------------

def geo2math(rot):
    return rot * math.pi / 180

# -------------------------------------------------------------------------

def save_to_austaltxt(path, lat, lon, buildings, rs='ut'):
    """Write buildings to austaltxt file"""
    def transform(x,y):
        return x,y
    if os.path.exists(path):
        austxt = get_austxt()
    else:
        austxt = {}

    if "ux" in austxt and "uy" in austxt:
        app_ux, app_uy = ll2ut(lat, lon)
        d_ux = app_ux - austxt["ux"][0]
        d_uy = app_uy - austxt["uy"][0]
        dist = math.sqrt(d_ux ** 2 + d_uy ** 2)
    elif "gx" in austxt and "gy" in austxt:
        app_gx, app_gy = ll2ut(lat, lon)
        d_gx = app_gx - austxt["gx"][0]
        d_gy = app_gy - austxt["gy"][0]
        dist = math.sqrt(d_gx ** 2 + d_gy ** 2)
    else:
        # no preexisting center position definition
        dist = 0
        if rs == 'gk':
            app_gx, app_gy = ll2gk(lat, lon)
            austxt["gx"] = [app_gx]
            austxt["gy"] = [app_gy]
        elif rs == 'ut':
            app_ux, app_uy = ll2ut(lat, lon)
            austxt["ux"] = [app_ux]
            austxt["uy"] = [app_uy]
        else:
            raise ValueError(f"Not a valid reference system code {rs}")

    if dist > MAX_CENTER_DISTANCE:
        raise ValueError(f"Center position "
                         f"in file {os.path.basename(path)} "
                         f"does not match current center position.")

    xy_in = [(b.x1,b.y1) for b in buildings]
    xy_out = [transform(x,y) for x,y in xy_in]

    # empty building variables fields
    for x in ['x','y','a','b','c', 'w']:
        austxt[f'{x}b'] = []

    # convert buildings
    for i, building in enumerate(buildings):
        austxt['xb'].append(xy_out[i][0])
        austxt['yb'].append(xy_out[i][1])
        if building.a > 0:
            # block building
            austxt['ab'].append(building.a)
            austxt['bb'].append(building.b)
        else:
            # cylindical building
            austxt['ab'].append(0.)
            # austal: amount of (negative) bb is diameter
            austxt['bb'].append(-2 * building.b)
        austxt['cb'].append(building.height)
        austxt['wb'].append(math2geo(building.rotation))

    put_austxt(austxt, path)

# -------------------------------------------------------------------------

def load_from_austaltxt(path):
    """Write buildings to austaltxt file"""
    austxt = get_austxt(path)

    if "ux" in austxt and "uy" in austxt:
        lat, lon = ut2ll(austxt['ux'][0], austxt['uy'][0])
    elif "gx" in austxt and "gy" in austxt:
        lat, lon = gk2ll(austxt['gx'][0], austxt['gy'][0])
    else:
        raise ValueError(f"No valid reference position "
                         f"in {os.path.basename(path)}")

    buildings = []
    if 'xb' in austxt and 'yb' in austxt:
        # if there are building definitions
        xb = austxt['xb']
        yb = austxt['yb']
        if len(xb) != len(yb):
            raise ValueError(f"Inconsistent number of buildings "
                             f"in {os.path.basename(path)}")
        else:
            number_of_buildings = len(xb)
        zeroes = [0.] * number_of_buildings
        # load optional values 
        ba = austxt.get('ab', zeroes)
        bb = austxt.get('bb', zeroes)
        cb = austxt.get('cb', zeroes)
        wb = austxt.get('wb', zeroes)

        for i in range(number_of_buildings):
            if ba[i] <= 0.:
                # round building
                a = ba[i]
                b = - bb[i] / 2.  # diameeter -> radius
            else:
                # block building
                a = ba[i]
                b = bb[i]

            bldg = Building(
                id=str(uuid.uuid4()),
                x1=xb[i],
                y1=yb[i],
                a=a,
                b=b,
                height=cb[i],
                storeys=1,
                rotation=geo2math(wb[i])
            )
            buildings.append(bldg)
    return (lat, lon, buildings)

# -------------------------------------------------------------------------

def get_austxt(path=None):
    """
    Get AUSTAL configuration fron the file 'austal.txt' as dictionary,
    and do **not** fill in default values

    :param path: Configuration file. Defaults to
    :type: str, optional
    :return: configuration
    :rtype: OrderedDict
    """
    if path is None:
        path = "austal.txt"
    logger.info('reading: %s' % path)
    # return config as dict
    conf = OrderedDict()
    if not os.path.exists(path):
        raise FileNotFoundError('austal.txt not found')
    with open(path, 'r') as file:
        for line in file:
            # remove comments in each line
            text = re.sub("^ *-.*", "", line)
            text = re.sub("'.*", "", text).strip()
            # if empty line remains: skip
            if text == "":
                continue
            logger.debug('%s - %s' % (os.path.basename(path), text))
            # split line into key / value pair
            try:
                key, val = text.split(maxsplit=1)
            except ValueError:

                raise ValueError('no keyword/value pair ' +
                                 'in line "%s"' % text)
            # make numbers numeric
            try:
                values = [float(x) for x in val.split()]
            except ValueError:
                values = shlex.split(val)
            # in Liste abspeichern (Zahlen als Zahlen, Strings als Strings)
            conf[key] = values
    # liste zurückgeben
    return conf

# -------------------------------------------------------------------------

def put_austxt(data:dict|OrderedDict, path="austal.txt"):
    """
    Write AUSTAL configuration file 'austal.txt'.

    If the file exists, it will be rewritten.
    Configuration values in the file are kept unless
    data contains new values.

    A Backup file is created wit a tilde appended to the filename.

    :param data: Dictionary of configuration data.
        The keys are the AUSTAL configuration codes,
        the values are the configuration values as strings or
        space-separated lists
    :param path: File name. Defaults to 'austal.txt'
    :type: str, optional
    """
    # get config as text
    if os.path.exists(path):
        logger.debug('writing backup: %s' % path + '~')
        shutil.move(path, path + '~')
    # rewrite old file
    logger.info('rewriting file: %s' % path)
    with open(path, 'w') as file:
        for k, v in data.items():
            if isinstance(v, list):
                value = ' '.join([str(x) for x in v])
            else:
                value = str(v)
            line = "{:s}  {:s}\n".format(k, value)
            logger.debug(line.strip())
            file.write(line)

# -------------------------------------------------------------------------
