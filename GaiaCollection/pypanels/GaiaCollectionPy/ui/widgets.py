import hou
import sys
import os
import tempfile
import math
import json
import base64
import datetime
import getpass

from PySide import QtGui
from PySide import QtCore
import toolutils

from ..icons.icon import get_icon
from GaiaCommon import nodeInfos
from GaiaCommon import h_widgets
reload(h_widgets)

class CollectionWidget(QtGui.QFrame):

    def __init__(self, parent=None):
        super(CollectionWidget, self).__init__(parent, QtCore.Qt.WindowStaysOnTopHint)

        self.collection_root = r"D:\WORK_3D\Gaia\GaiaCollection\collections"
        hou.session.GAIA_COLLECTION_ROOT = self.collection_root
        hou.session.GAIA_COLLECTION_CATEGORIES_INDEX = {}
        self.categories = []
        self.init_collection_folders()

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

    def init_collection_folders(self):

        for f in os.listdir(self.collection_root):
            if not os.path.isdir(self.collection_root + os.sep + f):
                continue

            self.categories.append(f)
            p = self.collection_root + os.sep + f
            hou.session.GAIA_COLLECTION_CATEGORIES_INDEX[f] = p
        

class CollectionToolbar(QtGui.QWidget):
    """ Top toolbar of the collection widget
    """
    def __init__(self, parent=None):
        super(CollectionToolbar, self).__init__(parent=parent)

        layout = QtGui.QHBoxLayout()
        layout.setAlignment(QtCore.Qt.AlignLeft)

        self.add_asset_btn = QtGui.QPushButton("")
        self.add_asset_btn.setIcon(get_icon("add"))
        self.add_asset_btn.clicked.connect(self.add_entry)
        layout.addWidget(self.add_asset_btn)
        self.setLayout(layout)

    def add_entry(self):
        """ Add the selected object to the collection and create
            metadata accordingly.
        """
        selected_node = hou.selectedNodes()
        if not selected_node:
            hou.ui.displayMessage("Nothing is selected",
                                  severity=hou.severityType.Error)
            return

        selected_node = selected_node[0]
        child_geo = [n.geometry() for n in selected_node.children() if \
                     n.isDisplayFlagSet()][0]
        if not child_geo.prims():
            hou.ui.displayMessage("Invalid node: no geometry found",
                                  severity=hou.severityType.Error)
            return

        self.w = CreateNewEntryWidget(selected_node=selected_node,
                                      parent=None)
        self.w.setStyleSheet(hou.ui.qtStyleSheet())
        self.w.show()

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

class CreateNewEntryWidget(QtGui.QFrame):

    def __init__(self, selected_node=None, create_light=True,
                 parent=None):
        super(CreateNewEntryWidget, self).__init__(parent,
                                                   QtCore.Qt.WindowStaysOnTopHint)
        
        self.setWindowTitle("Create new asset")
        self.setWindowIcon(get_icon("populate_database"))
        self.setAutoFillBackground(True)

        self.selected_node = selected_node
        self.nprims = -1
        self.npoints = -1
        self.bounds = []
        self.obj_center = []
        self.light_scale = 1
        self.obj_geo = None
        self.get_object_infos()

        main_layout = QtGui.QVBoxLayout()

        # create light node if needed
        self.light_node = None
        if create_light:
            self.light_node = hou.node("obj/Gaia_3pts_light")
            if not self.light_node:
                self.light_node = hou.node("/obj").createNode("three_point_light",
                                                              "Gaia_3pts_light")
                self.light_node.setDisplayFlag(False)
                self.light_node.parm("scale").set(self.light_scale)

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

        snap_lay = QtGui.QVBoxLayout()
        snap_lay.setAlignment(QtCore.Qt.AlignTop)
        snap_lay.setSpacing(5)

        self.thumbnail = QtGui.QLabel("")
        self.thumbnail.setFixedWidth(150)
        self.thumbnail.setFixedHeight(150)
        self.thumbnail.setStyleSheet("""QLabel{border: 1px solid black}""")
        self.thumbnail_pix = get_icon("close", 32).pixmap(1,1)
        self.thumbnail.setPixmap(self.thumbnail_pix)
        snap_lay.addWidget(self.thumbnail)

        # basic geo infos
        snap_lay.addWidget(h_widgets.HSeparator())
        snap_lay.addWidget(QtGui.QLabel("Points: {}".format(self.npoints)))
        snap_lay.addWidget(QtGui.QLabel("Prims: {}".format(self.nprims)))
        binfos = "Bounds:\t {0:.2f} ".format(self.bounds[1])
        binfos += "{0:.2f} ".format(self.bounds[3])
        binfos += "{0:.2f} ".format(self.bounds[5])
        snap_lay.addWidget(QtGui.QLabel(binfos))
        binfos = "\t {0:.2f} ".format(self.bounds[0])
        binfos += "{0:.2f} ".format(self.bounds[2])
        binfos += "{0:.2f}".format(self.bounds[4])
        snap_lay.addWidget(QtGui.QLabel(binfos))

        center = "Center: {0:.2f} ".format(self.obj_center[0])
        center += "{0:.2f} ".format(self.obj_center[1])
        center += "{0:.2f}".format(self.obj_center[2])
        snap_lay.addWidget(QtGui.QLabel(center))

        thumbnail_lay.addItem(snap_lay)

        thumbnail_lay.addWidget(h_widgets.HSeparator(mode="vertical"))

        thumbnail_opts_lay = QtGui.QVBoxLayout()
        thumbnail_opts_lay.setSpacing(5)
        thumbnail_opts_lay.setAlignment(QtCore.Qt.AlignTop)

        if self.light_node:
            self.light_orient = h_widgets.HSlider("light orientation", min=0.0, max=360,
                                                  lock_min=True, lock_max=True,
                                                  hou_parm=self.light_node.parm("ry"))
            thumbnail_opts_lay.addWidget(self.light_orient)

        self.capture_btn = QtGui.QPushButton("Update Snapshot")
        self.capture_btn.setIcon(get_icon("terrain"))
        self.capture_btn.clicked.connect(self.create_thumbnail)
        thumbnail_opts_lay.addWidget(self.capture_btn)

        thumbnail_opts_lay.addWidget(h_widgets.HSeparator())

        self.name = h_widgets.HStringValue(self.selected_node.name(),
                                           "name:")
        thumbnail_opts_lay.addWidget(self.name)

        self.tags = h_widgets.HStringValue("",
                                         "tags:")
        thumbnail_opts_lay.addWidget(self.tags)

        category_lay = QtGui.QHBoxLayout()
        category_lay.setSpacing(5)
        category_lay.setAlignment(QtCore.Qt.AlignLeft)
        category_lay.addWidget(QtGui.QLabel("Category:"))
        
        self.category = QtGui.QComboBox()
        self.category.addItems(hou.session.GAIA_COLLECTION_CATEGORIES_INDEX.keys())
        category_lay.addWidget(self.category)

        thumbnail_opts_lay.addLayout(category_lay)

        format_lay = QtGui.QHBoxLayout()
        format_lay.setSpacing(5)
        format_lay.setAlignment(QtCore.Qt.AlignLeft)
        format_lay.addWidget(QtGui.QLabel("Format:"))
        
        self.format = QtGui.QComboBox()
        self.format.addItems(["bgeo.gz", "obj", "abc", "hda"])
        format_lay.addWidget(self.format)

        thumbnail_opts_lay.addLayout(format_lay)

        type_lay = QtGui.QHBoxLayout()
        type_lay.setSpacing(5)
        type_lay.setAlignment(QtCore.Qt.AlignLeft)
        type_lay.addWidget(QtGui.QLabel("Type:"))
        
        self.obj_type = QtGui.QComboBox()
        self.obj_type.addItems(["static", "dynamic", "animated"])
        type_lay.addWidget(self.obj_type)

        thumbnail_opts_lay.addLayout(type_lay)

        thumbnail_opts_lay.addWidget(QtGui.QLabel("Infos:"))
        self.info_text = QtGui.QTextEdit()
        self.info_text.setMaximumHeight(75)
        thumbnail_opts_lay.addWidget(self.info_text)

        thumbnail_lay.addItem(thumbnail_opts_lay)
        main_layout.addItem(thumbnail_lay)

        # footer
        buttons_layout = QtGui.QHBoxLayout()
        buttons_layout.setSpacing(5)

        self.validate_btn = QtGui.QPushButton("Create Asset")
        self.validate_btn.clicked.connect(self.create_asset)
        self.validate_btn.setIcon(get_icon("checkmark"))
        buttons_layout.addWidget(self.validate_btn)

        self.cancel_btn = QtGui.QPushButton("Cancel")
        self.cancel_btn.clicked.connect(self.close)
        self.cancel_btn.setIcon(get_icon("close"))
        buttons_layout.addWidget(self.cancel_btn)

        main_layout.addLayout(buttons_layout)
        
        self.setLayout(main_layout)

        self.thumbnail_data = ""
        self.create_thumbnail()

    def get_object_infos(self):
        """ Get basic object's geometry infos, if object doesn't have any geo
            return false
        """
        geo = [n.geometry() for n in self.selected_node.children() if \
               n.isDisplayFlagSet()]
        if not geo:
            return False
        geo = geo[0]
        self.obj_geo = geo

        self.nprims = geo.intrinsicValue("primitivecount")
        self.npoints = geo.intrinsicValue("pointcount")
        self.bounds = geo.intrinsicValue("bounds")

        self.obj_center = [(self.bounds[1] + self.bounds[0]) * 0.5,
                           (self.bounds[3] + self.bounds[2]) * 0.5,
                           (self.bounds[5] + self.bounds[4]) * 0.5]

        bb = [math.fabs(self.bounds[1]) + math.fabs(self.bounds[0]),
              math.fabs(self.bounds[3]) + math.fabs(self.bounds[2]),
              math.fabs(self.bounds[5]) + math.fabs(self.bounds[4])]

        self.light_scale = max(bb) * 0.75

        return True

    def create_thumbnail(self):

        self.thumbnail_data = createThumbnailBase(self.selected_node)
        self.thumbnail_pix.loadFromData(self.thumbnail_data)
        self.thumbnail.update()

    def closeEvent(self, e):
        """ Switch camera state back after closing the view
            If the windows is called because of invalid node selected
            the script is ignored.
        """
        try:
            hou.hscript(("viewtransform " + self.viewer_p + 
                         " flag ( +a ) aspect ( " + 
                         str(self.aspec) + " )"))

            for n in self.nodes_state:
            
                try:
                    n.setDisplayFlag(True)
                except hou.OperationFailed:
                    continue

            if self.light_node:
                self.light_node.destroy()
        except AttributeError:
            pass

        super(CreateNewEntryWidget, self).closeEvent(e)

    def validate_data(self):
        """ Validate data such as tags, comment, name etc.
            before saving out the geo and metadata
        """
        self.validate_msg = ""
        return True

    def create_asset(self):
        """ Save the geo file and create metadata in the right folder
        """

        if not validate_data:
            hou.ui.displayMessage("Can't create asset",
                                  help = self.validate_msg,
                                  severity=hou.severityType.Error)
            return

        metadata = {}

        metadata["creation_time"] = str(datetime.datetime.now())
        metadata["created_by"] = getpass.getuser()

        category = self.category.currentText()
        metadata["category"] = category

        obj_type = self.obj_type.currentText()
        metadata["type"] = obj_type

        format = self.format.currentText()
        metadata["format"] = format

        name = self.name.text()
        metadata["name"] = name

        comment = self.info_text.toPlainText()
        metadata["comment"] = comment

        tags = [s.replace(' ', '') for s in self.tags.text().split(';')]
        metadata["tags"] = tags

        geo_infos = {}
        geo_infos["npoints"] = self.npoints
        geo_infos["nprims"] = self.nprims
        geo_infos["bounds"] = self.bounds
        geo_infos["center"] = self.obj_center
        metadata["geo_infos"] = geo_infos

        _path = hou.session.GAIA_COLLECTION_CATEGORIES_INDEX[category]
        metadata["path"] = _path.replace(hou.session.GAIA_COLLECTION_ROOT, "%ROOT%")

        metadata["thumbnail"] = base64.b64encode(self.thumbnail_data)

        # save geometry
        self.obj_geo.saveToFile(_path + os.sep + name + "." + format)

        # save metadata
        with open(_path + os.sep + name + ".json", 'wb') as f:
            json.dump(metadata, f, indent=4)

        hou.ui.displayMessage("Asset created: " + name)

        self.close()

def createThumbnailBase(selected_obj, res=150, view_grid=False):
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