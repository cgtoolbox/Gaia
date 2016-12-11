import hou
 
class DisplayMode(object):

    WIREFRAME = 0
    BBOX = 1
    GEOMETRY = 2
    POINTS = 3

class GaiaScatterInfos(object):

    __slots__ = ["node_path", "node"]

    def __init__(self):

        self.node_path = ""
        self.node = None

def get_painters(gaia_layer_node):

    p = gaia_layer_node.path() + "/PAINTERS"
    container = hou.node(p)
    return [n for n in container.children() \
            if n.name().startswith("painter_")]

def get_erasers(gaia_layer_node):

    p = gaia_layer_node.path() + "/ERASERS"
    container = hou.node(p)
    return [n for n in container.children() \
            if n.name().startswith("eraser_")]

def get_scale_painters(gaia_layer_node):

    p = gaia_layer_node.path() + "/SCALE_PAINTER"
    container = hou.node(p)
    return [n for n in container.children() \
            if n.name().startswith("scale_painter_")]

def get_viewer_fullpath():

    _desktop =  hou.ui.curDesktop()
    desktop = _desktop.name()
    _panetab =  _desktop.paneTabOfType(hou.paneTabType.SceneViewer)
    panetab = _panetab.name()
    persp = _panetab.curViewport().name()
    return desktop + "." + panetab + "." + "world" "." + persp