import hou

INVALID_CACHE_KEY   = 0x00
CACHE_NOT_AVAILABLE = 0x01

def set(key, value):

    if not hasattr(hou.session, "MAIN_GAIA_SCATTER_CACHE"):
        hou.session.MAIN_GAIA_SCATTER_CACHE = {}
    
    hou.session.MAIN_GAIA_SCATTER_CACHE[key] = value

def get(key, default=INVALID_CACHE_KEY):

    if not hasattr(hou.session, "MAIN_GAIA_SCATTER_CACHE"):
        return CACHE_NOT_AVAILABLE

    return hou.session.MAIN_GAIA_SCATTER_CACHE.get(key,
                                                   default)