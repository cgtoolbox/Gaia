import os

from PySide2 import QtGui

def get_icon(name, file_type="svg", size=32):
    """ Return a given QIcon object according to a icon name
        and icon size. Return an empty QIcon if name not found.
    """
    icon = None
    if file_type == "png":
        icons = os.path.dirname(__file__) + os.sep + str(size) + os.sep
        icon = icons + name + ".png"

    elif file_type == "svg":
        icons = os.path.dirname(__file__) + "\\svg\\"
        icon = icons + name + ".svg"

    if not icon or not os.path.exists(icon):
        print("Warning: icon {}:{}(px) not found.".format(name, size))
        return QtGui.QIcon()

    return QtGui.QIcon(icon)
