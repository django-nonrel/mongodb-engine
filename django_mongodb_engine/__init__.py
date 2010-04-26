__author__ = 'Flavio Percoco Premoli - Alberto Paro'

VERSION = (0, 0, 1)

def get_version():
    version = '%s.%s' % (VERSION[0], VERSION[1])
    if VERSION[2]:
        version = '%s.%s' % (version, VERSION[2])
    return version

__version__ = get_version()

