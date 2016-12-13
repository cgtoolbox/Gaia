import os

from PySide import QtGui

def get_icon(name, size=32):
    """ Return a given QIcon object according to a icon name
        and icon size. Return an empty QIcon if name not found.
    """
    icons = os.path.dirname(__file__) + os.sep + str(size) + os.sep
    icon = icons + name + ".png"

    if not os.path.exists(icon):
        print("Warning: icon {}:{}px not found.".format(name, size))
        return QtGui.QIcon()

    return QtGui.QIcon(icon)