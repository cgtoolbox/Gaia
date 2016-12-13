import hou
import sys
import os
import tempfile

from PySide import QtGui
from PySide import QtCore
import toolutils

from ..icons.icon import get_icon

class CollectionWidget(QtGui.QWidget):

    def __init__(self, parent=None):
        super(CollectionWidget, self).__init__(parent=parent)

        self.collection_root = r"D:\WORK_3D\Gaia\GaiaCollection\collections"

        main_layout = QtGui.QVBoxLayout()
        main_layout.setAlignment(QtCore.Qt.AlignTop)
        main_layout.setContentsMargins(0,0,0,0)

        # top toolbar
        self.toolbar = CollectionToolbar(self)
        main_layout.addWidget(self.toolbar)

        middle_layout = QtGui.QHBoxLayout()
        middle_layout.setAlignment(QtCore.Qt.AlignLeft)
        middle_layout.setContentsMargins(0,0,0,0)

        # hierarchy menu
        self.collection_menu = CollectionMenu(self.collection_root, self)
        middle_layout.addWidget(self.collection_menu)


        main_layout.addItem(middle_layout)

        self.setLayout(main_layout)

class CollectionToolbar(QtGui.QWidget):
    """ Top toolbar of the collection widget
    """
    def __init__(self, parent=None):
        super(CollectionToolbar, self).__init__(parent=parent)

        layout = QtGui.QHBoxLayout()
        layout.setAlignment(QtCore.Qt.AlignLeft)

        self.add_asset_btn = QtGui.QPushButton("")
        self.add_asset_btn.setIcon(get_icon("add"))
        layout.addWidget(self.add_asset_btn)
        self.setLayout(layout)

class CollectionMenu(QtGui.QWidget):
    """ Left side menu to navigate throught the collection
    """
    def __init__(self, root="", parent=None):
        super(CollectionMenu, self).__init__(parent=parent)

        self.root = root

        self.setFixedWidth(105)
        self.main_layout = QtGui.QVBoxLayout()
        self.main_layout.setContentsMargins(5,0,0,0)
        self.main_layout.setSpacing(1)

        self.search = QtGui.QLineEdit()
        self.search.setContentsMargins(0,0,0,5)
        self.main_layout.addWidget(self.search)
        
        self.root_btn = CollectionMenuBtn("Root")
        self.main_layout.addWidget(self.root_btn)

        self.go_up_btn = CollectionMenuBtn("...")
        self.main_layout.addWidget(self.go_up_btn)

        self.setLayout(self.main_layout)

        self.sub_menu = []
        self.init_menu()

    def init_menu(self):

        for f in os.listdir(self.root):
            if not os.path.isdir(self.root + os.sep + f):
                continue

            w = CollectionMenuBtn(f)
            self.sub_menu.append(w)
            self.main_layout.addWidget(w)


class CollectionMenuBtn(QtGui.QPushButton):

    def __init__(self, label, icon=""):
        super(CollectionMenuBtn, self).__init__(label)

        self.setFlat(True)
        self.setContentsMargins(0,0,0,0)
        self.setStyleSheet("""QPushButton{border: 1px solid black;
                                          background-color: #2846b8}
                              QPushButton:hover{border: 1px solid black;
                                                background-color: #4e82e0}""")
        self.setFixedWidth(100)
        self.setFixedHeight(25)
        if icon:
            self.setIcon(get_icon(icon))

class CreateNewEntryWidget(QtGui.QMainWindow):

    def __init__(self, selected_node=None, parent=None):
        super(CreateNewEntryWidget, self).__init__(parent=parent)
        
        self.setWindowTitle("Create new asset")
        cw = QtGui.QWidget(self)
        cw.setAutoFillBackground(True)
        self.setObjectName("mw")
        
        self.setStyleSheet("""QWidget#mw{background-color: grey;}""")

        self.selected_node = selected_node
        main_layout = QtGui.QVBoxLayout()

        # Init view
        selected_node.setDisplayFlag(True)
        self.nodes_state = [n for n in hou.node("/obj").children() \
                            if n.isDisplayFlagSet() \
                            and n != selected_node]
        for n in self.nodes_state: n.setDisplayFlag(False)

        self.selected_node.setCurrent(True)
        self.selected_node.setSelected(True)

        viewer = toolutils.sceneViewer()
        viewport = viewer.curViewport()
        viewport.frameSelected()

        self.aspec = viewport.settings().viewAspectRatio()
        self.viewer_p = nodeInfos.get_viewer_fullpath()

        hou.hscript(("viewtransform " + self.viewer_p +
                     " flag ( +a ) aspect ( 1.0 )"))

        # thumbnail layout
        thumbnail_lay = QtGui.QHBoxLayout()
        thumbnail_lay.setSpacing(5)

        self.thumbnail = QtGui.QLabel("")
        self.thumbnail.setFixedWidth(90)
        self.thumbnail.setFixedHeight(90)
        self.thumbnail.setStyleSheet("""QLabel{border: 1px solid black}""")
        self.thumbnail_pix = get_icon("close", 32).pixmap(1,1)
        self.thumbnail.setPixmap(self.thumbnail_pix)
        thumbnail_lay.addWidget(self.thumbnail)

        thumbnail_opts_lay = QtGui.QVBoxLayout()
        self.name = widgets.HStringValue(self.selected_node.name(),
                                         "name:")
        thumbnail_opts_lay.addWidget(self.name)

        self.tags = widgets.HStringValue("",
                                         "tags:")
        thumbnail_opts_lay.addWidget(self.tags)

        self.capture_btn = QtGui.QPushButton("Snapshot")
        self.capture_btn.setIcon(get_icon("terrain"))
        self.capture_btn.clicked.connect(self.create_thumbnail)
        thumbnail_opts_lay.addWidget(self.capture_btn)
        thumbnail_lay.addItem(thumbnail_opts_lay)

        main_layout.addItem(thumbnail_lay)

        self.validate_btn = QtGui.QPushButton("Valid")
        self.validate_btn.setIcon(get_icon("checkmark"))
        main_layout.addWidget(self.validate_btn)
        
        cw.setLayout(main_layout)
        self.setCentralWidget(cw)

        self.create_thumbnail()

    def create_thumbnail(self):

        binary_data = createThumbnailBase(self.selected_node)
        self.thumbnail_pix.loadFromData(binary_data)
        self.thumbnail.update()

    def closeEvent(self, e):

        hou.hscript(("viewtransform " + self.viewer_p + 
                     " flag ( +a ) aspect ( " + 
                     str(self.aspec) + " )"))

        for n in self.nodes_state:
            
            try:
                n.setDisplayFlag(True)
            except hou.OperationFailed:
                continue

        super(CreateNewEntryWidget, self).closeEvent(e)


def createThumbnailBase(selected_obj, res=90, view_grid=False):
    """Create a thumbnail image from current scene viewer and selected object(s)
        return the binary data of the jpg file
    """
        
    viewer = toolutils.sceneViewer()
    viewport = viewer.curViewport()
    if not viewer:
        hou.ui.displayMessage("No scene viewer found.",
                                severity=hou.severityType.Error)
        return None
    
    cur_state = viewer.currentState()
    viewer.enterViewState()
        
    construct_plane = viewer.constructionPlane()
    construct_state = construct_plane.isVisible()
    construct_plane.setIsVisible(view_grid)
    
    _desktop =  hou.ui.curDesktop()
    desktop = _desktop.name()
    _panetab =  _desktop.paneTabOfType(hou.paneTabType.SceneViewer)
    panetab = _panetab.name()
    persp = _panetab.curViewport().name()
    camera_path = nodeInfos.get_viewer_fullpath()
    
    selected_obj.setCurrent(False)
    
    output = tempfile.gettempdir() + "\\" + selected_obj.name() + ".jpg"
    cmd = 'viewwrite -f $F $F -c -q 4 -r ' + \
          str(res) + ' ' + str(res) + ' ' + \
          camera_path + ' "' + output + '"'
    out, err = hou.hscript(cmd)
    
    if err:
        print err
    
    # clean temporary camera and set options back to initial values
    viewer.setCurrentState(cur_state)
    construct_plane.setIsVisible(construct_state)
    
    selected_obj.setCurrent(True)

    with open(output, 'rb') as f:
        return f.read()