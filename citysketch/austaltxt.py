import math
import shutil
from collections import OrderedDict
import logging
import os
import re
import shlex
import uuid

from osgeo import osr
osr.UseExceptions()

from utils import (LL, GK, UT, WM, 
                   gk2ll, ll2gk, ut2ll, ll2ut, 
                   ll2wm, wm2ll, wm2ut, ut2wm, wm2gk, gk2wm,
                   math2geo, geo2math)
from .Building import Building

logger = logging.getLogger(__name__)
osr.UseExceptions()

# -------------------------------------------------------------------------

MAX_CENTER_DISTANCE = 10.  # m

# -------------------------------------------------------------------------

def save_to_austaltxt(path, lat, lon, buildings, rs='ut'):
    """
    Write buildings to austaltxt file.
    
    Building coordinates are in Web Mercator (EPSG:3857) relative to center.
    They are converted to the appropriate reference system (UT or GK) for storage.
    
    :param path: Path to the austaltxt file
    :param lat: Center latitude (WGS84)
    :param lon: Center longitude (WGS84)
    :param buildings: List of Building objects with Web Mercator coordinates
    :param rs: Reference system for file ('ut' or 'gk')
    """

    FMT = '{:.2f}'
    
    # Get center in Web Mercator
    center_wm_x, center_wm_y = ll2wm(lat, lon)
    
    # Define transform from Web Mercator world coords to file coords
    if rs == 'ut':
        def transform(wx, wy):
            # World coords are relative to center in Web Mercator
            wm_x = wx + center_wm_x
            wm_y = wy + center_wm_y
            # Convert to UTM
            ux, uy = wm2ut(wm_x, wm_y)
            # Make relative to center in UTM
            center_ux, center_uy = ll2ut(lat, lon)
            return ux - center_ux, uy - center_uy
    elif rs == 'gk':
        def transform(wx, wy):
            # World coords are relative to center in Web Mercator
            wm_x = wx + center_wm_x
            wm_y = wy + center_wm_y
            # Convert to GK
            gx, gy = wm2gk(wm_x, wm_y)
            # Make relative to center in GK
            center_gx, center_gy = ll2gk(lat, lon)
            return gx - center_gx, gy - center_gy
    else:
        raise ValueError(f"Not a valid reference system code {rs}")
    
    if os.path.exists(path):
        austxt = get_austxt(path)
    else:
        austxt = {}

    if "ux" in austxt and "uy" in austxt:
        app_ux, app_uy = ll2ut(lat, lon)
        d_ux = app_ux - austxt["ux"][0]
        d_uy = app_uy - austxt["uy"][0]
        dist = math.sqrt(d_ux ** 2 + d_uy ** 2)
    elif "gx" in austxt and "gy" in austxt:
        app_gx, app_gy = ll2gk(lat, lon)
        d_gx = app_gx - austxt["gx"][0]
        d_gy = app_gy - austxt["gy"][0]
        dist = math.sqrt(d_gx ** 2 + d_gy ** 2)
    else:
        # no preexisting center position definition
        dist = 0.
        if rs == 'gk':
            app_gx, app_gy = ll2gk(lat, lon)
            austxt["gx"] = [app_gx]
            austxt["gy"] = [app_gy]
        elif rs == 'ut':
            app_ux, app_uy = ll2ut(lat, lon)
            austxt["ux"] = [app_ux]
            austxt["uy"] = [app_uy]

    if dist > MAX_CENTER_DISTANCE:
        raise ValueError(f"Center position "
                         f"in file {os.path.basename(path)} "
                         f"does not match current center position. "
                         f"(dist = {dist})")

    xy_in = [(b.x1,b.y1) for b in buildings]
    xy_out = [transform(x,y) for x,y in xy_in]

    # empty building variables fields
    for x in ['x','y','a','b','c', 'w']:
        austxt[f'{x}b'] = []

    # convert buildings
    for i, building in enumerate(buildings):
        austxt['xb'].append(FMT.format(xy_out[i][0]))
        austxt['yb'].append(FMT.format(xy_out[i][1]))
        if building.a > 0:
            # block building
            austxt['ab'].append(FMT.format(building.a))
            austxt['bb'].append(FMT.format(building.b))
        else:
            # cylindical building
            austxt['ab'].append(FMT.format(0.))
            # austal: amount of (negative) bb is diameter
            austxt['bb'].append(-2 * building.b)
        austxt['cb'].append(FMT.format(building.height))
        austxt['wb'].append(FMT.format(math2geo(building.rotation)))

    put_austxt(austxt, path)

# -------------------------------------------------------------------------

def load_from_austaltxt(path):
    """
    Load buildings from austaltxt file.
    
    File coordinates are in UTM (ux/uy) or Gauss-Krüger (gx/gy).
    Building coordinates are converted to Web Mercator (EPSG:3857)
    relative to the center position.
    
    :param path: Path to the austaltxt file
    :return: Tuple of (lat, lon, buildings) where buildings have 
        Web Mercator coordinates relative to center
    """
    austxt = get_austxt(path)

    if "ux" in austxt and "uy" in austxt:
        lat, lon = ut2ll(austxt['ux'][0], austxt['uy'][0])
        center_ux, center_uy = austxt['ux'][0], austxt['uy'][0]
        def transform(x, y):
            # x, y are relative to center in UTM
            ux = x + center_ux
            uy = y + center_uy
            # Convert to Web Mercator
            wm_x, wm_y = ut2wm(ux, uy)
            # Make relative to center in Web Mercator
            center_wm_x, center_wm_y = ll2wm(lat, lon)
            return wm_x - center_wm_x, wm_y - center_wm_y
    elif "gx" in austxt and "gy" in austxt:
        lat, lon = gk2ll(austxt['gx'][0], austxt['gy'][0])
        center_gx, center_gy = austxt['gx'][0], austxt['gy'][0]
        def transform(x, y):
            # x, y are relative to center in GK
            gx = x + center_gx
            gy = y + center_gy
            # Convert to Web Mercator
            wm_x, wm_y = gk2wm(gx, gy)
            # Make relative to center in Web Mercator
            center_wm_x, center_wm_y = ll2wm(lat, lon)
            return wm_x - center_wm_x, wm_y - center_wm_y
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
                b = - bb[i] / 2.  # diameter -> radius
            else:
                # block building
                a = ba[i]
                b = bb[i]

            # Transform coordinates from file system to Web Mercator
            wm_x, wm_y = transform(xb[i], yb[i])
            
            bldg = Building(
                id=str(uuid.uuid4()),
                x1=wm_x,
                y1=wm_y,
                a=a,
                b=b,
                height=cb[i],
                storeys=None,
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
