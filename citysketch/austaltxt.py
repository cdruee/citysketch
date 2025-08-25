import math
import shutil
from collections import OrderedDict
import logging
import os
import re
import shlex

logger = logging.getLogger(__name__)

def math2geo(rot):
    return (- rot) * 180 / math.pi

def geo2math(rot):
    return (- rot) * math.pi / 180

def save_to_austaltxt(path, buildings):
    """Write buildings to austaltxt file"""
    def transform(x,y):
        return x,y
    austxt = get_austxt()
    xy_in = [(b.x,b.y) for b in buildings]
    xy_out = [transform(x,y) for x,y in xy_in]

    for i, building in enumerate(buildings):
        austxt['ab'].append(xy_out[i][0])
        austxt['yb'].append(xy_out[i][1])
        if building.a > 0:
            # block building
            austxt['ab'].append(building.a)
            austxt['bb'].append(building.b)
        else:
            # cylindical building
            austxt['ab'].append(0.)
            austxt['bb'].append(-building.b)
        austxt['cb'].append(building.height)
        austxt['wb'].append(math2geo(building.rotation))

    put_austxt(austxt, path)


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

def put_austxt(data:OrderedDict|dict, path="austal.txt"):
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
