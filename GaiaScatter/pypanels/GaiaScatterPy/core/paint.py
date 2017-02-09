import time
import random
import hou
import toolutils

from . import cache
reload(cache)

from GaiaCommon import nodeInfos
reload(nodeInfos)

class PAINTMODES:

    NONE = -1
    PAINT = 0
    ERASE = 1
    SCALE = 2

def enter_paint_mode(mode=PAINTMODES.NONE, gaia_layer=None):
    """ 
        Create a new gaia scatter internal tool accroding to the mode.

        Set the painting desktop as current and select the good
        stroke node according to paint mode and id (if needed).
        Saves also current selected node and desktop in cache
        in order to revert the view back when exit_paint_mode()
        is called.
    """
    global CUR_PAINTER_STROKES

    if not gaia_layer or mode == PAINTMODES.NONE:
        return False

    sv = toolutils.sceneViewer()
    if not sv:
        return False

    selected_node = hou.selectedNodes()
    if selected_node:
        cache.set("SELECTED_NODE", selected_node)
    else:
        cache.set("SELECTED_NODE", [sv.currentNode(),])
        
    gaia_layer_path = gaia_layer.path() + "/"
    cur_node = None

    if mode == PAINTMODES.PAINT:

        idx = len(nodeInfos.get_painters(gaia_layer)) + 1
        container = hou.node(gaia_layer_path + "PAINTERS")
        out = hou.node(container.path() + "/merge_painters")
        input = hou.node(gaia_layer_path + "PAINTERS/INPUT")
        painter = container.createNode("Gaia_Scatter_Painter",
                                       node_name="painter_" + str(idx))

        # user data used to fetch on what painters the erasers
        # should be applied
        cur_id = gaia_layer.userData("LATEST_STROKE_ID")
        if cur_id:
            cur_id = int(cur_id)
        else:
            cur_id = 0
        gaia_layer.setUserData("LATEST_STROKE_ID", str(cur_id + 1))

        painter.parm("id").set(cur_id)
        painter.setUserData("time_stamp", str(time.time()))
        #painter.allowEditingOfContents()
        painter.setInput(0, input)
        out.setNextInput(painter)
        cur_node = hou.node(painter.path() + "/STROKES")
        container.layoutChildren()

    elif mode == PAINTMODES.ERASE:

        idx = len(nodeInfos.get_erasers(gaia_layer)) + 1
        container = hou.node(gaia_layer_path + "ERASERS")
        out = hou.node(container.path() + "/merge_erasers")
        input = hou.node(gaia_layer_path + "ERASERS/INPUT")
        eraser = container.createNode("Gaia_Scatter_Eraser",
                                       node_name="eraser_" + str(idx))
        
        cur_id = gaia_layer.userData("LATEST_STROKE_ID")
        if cur_id:
            cur_id = int(cur_id)
        else:
            cur_id = 0
        eraser.parm("apply_on").set(str(cur_id))

        eraser.setUserData("time_stamp", str(time.time()))
        #eraser.allowEditingOfContents()
        eraser.setInput(0, input)
        out.setNextInput(eraser)
        cur_node = hou.node(eraser.path() + "/STROKE_ERASER")
        container.layoutChildren()

    elif mode == PAINTMODES.SCALE:

        idx = len(nodeInfos.get_scale_painters(gaia_layer)) + 1
        container = hou.node(gaia_layer_path + "SCALE_PAINTER")
        out = hou.node(container.path() + "/merge_scale_painters")
        input = hou.node(gaia_layer_path + "PAINTERS/INPUT")
        scale_painter = container.createNode("Gaia_Scale_painter",
                                             node_name="scale_painter_" + str(idx))
        scale_painter.setUserData("time_stamp", str(time.time()))
        #scale_painter.allowEditingOfContents()
        scale_painter.setInput(0, input)
        out.setNextInput(scale_painter)
        cur_node = hou.node(scale_painter.path() + "/STROKES_SCALE_PAINTER")
        container.layoutChildren()

    if not cur_node:
        return False

    cur_node.setCurrent(True)
    sv.enterCurrentNodeState()

    cur_desk = hou.ui.curDesktop()
    
    hou.hscript("vieweroption -a 1 " + cur_desk.name() + '.' + \
                sv.name() + ".world")

    return cur_node.parent()

def exit_paint_mode():
    """ Revert the viewport option to the previous state (before
        enter_paint_mode() was called).
    """
    sel = cache.get("SELECTED_NODE")
    if sel:
        sel[0].setSelected(True, clear_all_selected=True)
        sel[0].setCurrent(True)
    
    return True