import hou
from PySide import QtGui


from ui import main_ui
reload(main_ui)

def main():
    return main_ui.MainUI(parent=hou.ui.mainQtWindow())
