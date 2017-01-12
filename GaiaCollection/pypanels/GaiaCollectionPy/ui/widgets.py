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
from . import ui_workers
reload(ui_workers)
from GaiaCommon import nodeInfos
from GaiaCommon import h_widgets
reload(h_widgets)

global FROM_GAIA_SCATTER
FROM_GAIA_SCATTER = False

class CollectionWidget(QtGui.QFrame):

    def __init__(self, from_gaia_scatter=False, parent=None):
        super(CollectionWidget, self).__init__(parent, QtCore.Qt.WindowStaysOnTopHint)

        self.setWindowTitle("Gaia Collection")

        global FROM_GAIA_SCATTER
        FROM_GAIA_SCATTER = from_gaia_scatter

        self.collection_root = r"D:\WORK_3D\Gaia\GaiaCollection\collections"
        hou.session.GAIA_COLLECTION_ROOT = self.collection_root
        hou.session.GAIA_COLLECTION_CATEGORIES_INDEX = {}
        self.categories = []
        self.init_collection_folders()

        main_layout = QtGui.QVBoxLayout()
        main_layout.setAlignment(QtCore.Qt.AlignTop)
        main_layout.setContentsMargins(0,0,0,0)

        # middle layout
        middle_layout = QtGui.QHBoxLayout()
        middle_layout.setSpacing(5)
        middle_layout.setAlignment(QtCore.Qt.AlignLeft)
        middle_layout.setContentsMargins(5,5,5,5)

        # hierarchy menu
        self.collection_menu = CollectionMenu(self.collection_root,
                                              parent=self)
        middle_layout.addWidget(self.collection_menu)

        # asset grid and properties
        self.asset_properties = CollectionItemProperties(self.collection_root)
        self.assets_grid = CollectionGrid(self.collection_root, parent=self)
        self.toolbar = CollectionToolbar(self)
        main_layout.addWidget(self.toolbar)
        middle_layout.addWidget(self.assets_grid)
        middle_layout.addWidget(self.asset_properties)
        self.toolbar.asset_grid = self.assets_grid

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
        self.assets_grid = parent.assets_grid

        self.add_asset_btn = QtGui.QPushButton("")
        self.add_asset_btn.setFixedHeight(32)
        self.add_asset_btn.setFixedWidth(32)
        self.add_asset_btn.setIcon(get_icon("add"))
        self.add_asset_btn.setIconSize(QtCore.QSize(25, 25))
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
                                      assets_grid=self.assets_grid,
                                      parent=None)
        self.w.setStyleSheet(hou.ui.qtStyleSheet())
        self.w.show()

class CollectionIconProvider(QtGui.QFileIconProvider):

    def __init__(self):
        super(CollectionIconProvider, self).__init__(self)
   

    def icon(self, info):

        return get_icon("database")

class CollectionGrid(QtGui.QFrame):

    def __init__(self, collection_root, parent=None):
        super(CollectionGrid, self).__init__(parent=parent)

        self.collection_items = []
        self.selected_item = None
        self.item_properties = parent.asset_properties
        self.collection_root = collection_root

        # worker thread used by item parsing
        self.worker = QtCore.QThread()
        self.getCollectionItems = ui_workers.GetCollectionItems()
        self.getCollectionItems.add_entry.connect(self.add_entry)
        self.getCollectionItems.start_process.connect(self.start_process)
        self.getCollectionItems.end_process.connect(self.end_process)
        self.getCollectionItems.moveToThread(self.worker)
        self.worker.start()

        self.setObjectName("grid")
        self.setFixedWidth(415)
        main_layout = QtGui.QVBoxLayout()
        main_layout.setAlignment(QtCore.Qt.AlignTop)
        self.setSizePolicy(QtGui.QSizePolicy.Minimum,
                           QtGui.QSizePolicy.Minimum)

        self.items_loading_progress = QtGui.QProgressBar()
        self.items_loading_progress.setFixedHeight(5)
        self.items_loading_progress.setTextVisible(False)
        main_layout.addWidget(self.items_loading_progress)

        self.setStyleSheet("""QFrame#grid{border: 1px solid black}""")

        self.scrollarea = QtGui.QScrollArea()
        self.scrollarea.setVerticalScrollBarPolicy(QtCore.Qt.ScrollBarAlwaysOn)
        self.scroll_widget = QtGui.QWidget()
        self.asset_grid_layout = QtGui.QGridLayout()
        self.asset_grid_layout.setAlignment(QtCore.Qt.AlignTop)
        self.scroll_widget.setLayout(self.asset_grid_layout)
        self.scrollarea.setWidgetResizable(True)
        self.scrollarea.setWidget(self.scroll_widget)
        main_layout.addWidget(self.scrollarea)

        self.setLayout(main_layout)

    def __del__(self):
        
        if self.worker.isRunning():
            self.worker.quit()
            self.worker.terminate()
    
    def display_items(self, collection_folder):

        self.clear_entries()
        self.getCollectionItems.cancel = True
        self.getCollectionItems.init_run.emit(collection_folder)

    @QtCore.Slot(int)
    def start_process(self, val):
        
        self.items_loading_progress.setMinimum(0)
        self.items_loading_progress.setMaximum(val)
        self.items_loading_progress.setValue(0)

    @QtCore.Slot()
    def end_process(self):
        
        self.items_loading_progress.setValue(0)

    @QtCore.Slot()
    def cancel_process(self):

        self.clear_entries()

    @QtCore.Slot(dict)
    def add_entry(self, metadata):
        
        w = CollectionItem(metadata=metadata, collection_root=self.collection_root,
                           parent=self)
        nitems = len(self.collection_items)

        col = 0
        row = 0
        if nitems > 0: 
            
            col = nitems % 4
            row = nitems / 4

        self.asset_grid_layout.addWidget(w, row, col)
        self.collection_items.append(w)

        val = self.items_loading_progress.value()
        self.items_loading_progress.setValue(val + 1)

    def clear_entries(self):

        for i in range(self.asset_grid_layout.count())[::-1]:
            
            it = self.asset_grid_layout.itemAt(i)
            if it:
                w = it.widget()
                self.asset_grid_layout.removeWidget(w)
                w.setParent(None)
                w.deleteLater()

        self.collection_items = []
        self.selected_item = None
        self.item_properties.reset()

class CollectionMenu(QtGui.QTreeView):
    """ Left side menu to navigate throught the collection
    """
    def __init__(self, collection_root="", parent=None):
        super(CollectionMenu, self).__init__(parent=parent)

        self.collection = parent
        self.setFixedWidth(150)
        self.setStyleSheet( """QTreeView::branch {border-image: url(none.png);}
                               QTreeView{outline: 0}
                               QTreeView::item:selected{border: None;
                                                        background-color: rgba(20,20,120,128);}
                            """ );

        self.collection_dict = {}
        self.collection_root = collection_root

        self.filemodel = QtGui.QFileSystemModel(self)
        self.filemodel.setIconProvider(CollectionIconProvider())
        
        self.filemodel.setFilter(QtCore.QDir.AllDirs|QtCore.QDir.NoDotAndDotDot)

        r = self.filemodel.setRootPath(collection_root)
        self.filemodel.setHeaderData(0, QtCore.Qt.Horizontal, "Folders");
        self.setModel(self.filemodel)
        self.setRootIndex(r)
        
        for i in range(self.header().count()):

            if i == 0: continue
            self.hideColumn(i)

        self.header().close()

    def selectionChanged(self, selected, deselected):
        
        items_path_root = self.filemodel.filePath(self.currentIndex())
        self.collection.assets_grid.display_items(items_path_root)
        super(CollectionMenu, self).selectionChanged(selected, deselected)
        
class CollectionItemProperties(QtGui.QWidget):

    def __init__(self, collection_root, parent=None):
        super(CollectionItemProperties, self).__init__(parent=parent)

        global FROM_GAIA_SCATTER

        self.item_path = ""
        self.collection_root = collection_root
        self.metadata = None
        self.setProperty("houdiniStyle", True)

        main_layout = QtGui.QVBoxLayout()
        main_layout.setAlignment(QtCore.Qt.AlignTop)
        main_layout.setSpacing(5)

        main_layout.addWidget(QtGui.QLabel("Properties:"))
        main_layout.addWidget(h_widgets.HSeparator())

        self.item_name_w = QtGui.QLabel("Name: -")
        main_layout.addWidget(self.item_name_w)

        self.item_path_w = QtGui.QLabel("Path: -")
        main_layout.addWidget(self.item_path_w)

        self.check_geo_btn = QtGui.QPushButton("Preview geo")
        self.check_geo_btn.setEnabled(False)
        main_layout.addWidget(self.check_geo_btn)

        main_layout.addWidget(h_widgets.HSeparator())

        self.item_format = QtGui.QLabel("Format: - ")
        main_layout.addWidget(self.item_format)

        self.item_type = QtGui.QLabel("Type: - ")
        main_layout.addWidget(self.item_type)

        self.item_npoints = QtGui.QLabel("Points: - ")
        main_layout.addWidget(self.item_npoints)

        self.item_nprims = QtGui.QLabel("Prims: -")
        main_layout.addWidget(self.item_nprims)

        main_layout.addWidget(h_widgets.HSeparator())

        main_layout.addWidget(QtGui.QLabel("Infos:"))
        self.item_infos = QtGui.QTextEdit()
        self.item_infos.setReadOnly(True)
        main_layout.addWidget(self.item_infos)

        self.tags_w = QtGui.QLabel("Tags: -")
        main_layout.addWidget(self.tags_w)

        self.edit_tags_btn = None
        self.import_3d_btn = None
        if not FROM_GAIA_SCATTER:

            self.edit_tags_btn = QtGui.QPushButton("Edit Properties")
            self.edit_tags_btn.setEnabled(False)
            main_layout.addWidget(self.edit_tags_btn)

            main_layout.addWidget(h_widgets.HSeparator())

            self.import_3d_btn = QtGui.QPushButton("Import Asset To Scene")
            self.import_3d_btn.setFixedHeight(36)
            self.import_3d_btn.setIcon(get_icon("3d_file_import"))
            self.import_3d_btn.setIconSize(QtCore.QSize(32, 32))
            self.import_3d_btn.clicked.connect(self.import_obj)
            self.import_3d_btn.setEnabled(False)
            main_layout.addWidget(self.import_3d_btn)

        self.setLayout(main_layout)

    def update_entry(self, metadata):
        
        self.metadata = metadata
        try:
            name = metadata["name"]
            _format = metadata["format"]
            _path = metadata["path"].replace('\\', '/') + '/' + name + '.' + _format
            comment = metadata["comment"]
            tags = metadata["tags"]
            _type = metadata["type"]

            geo_infos = metadata["geo_infos"]
            npoints = geo_infos["npoints"]
            nprims = geo_infos["nprims"]

            self.item_name_w.setText("Name: " + name)
            self.item_format.setText("Format: " + _format)
            self.item_path_w.setText("Path: " + _path)
            self.item_path = _path.replace("%ROOT%", self.collection_root.replace('\\', '/'))
            self.item_infos.setText(comment)
            self.tags_w.setText("Tags: " + ', '.join(tags))
            self.item_npoints.setText("Points: " + str(npoints))
            self.item_nprims.setText("Prims: " + str(nprims))
            self.item_type.setText("Type: " + _type)

            self.check_geo_btn.setEnabled(True)
            if self.edit_tags_btn:
                self.edit_tags_btn.setEnabled(True)
            if self.import_3d_btn:
                self.import_3d_btn.setEnabled(True)

        except KeyError:
            hou.ui.displayMessage("Invalid metadata",
                                  severity=hou.severityType.Error)
            return False

        return True

    def reset(self):

        self.item_name_w.setText("Name: -")
        self.item_format.setText("Format: -")
        self.item_path_w.setText("Path: -")
        self.item_path = ""
        self.item_infos.setText("")
        self.tags_w.setText("Tags: -")
        self.item_npoints.setText("Points: -")
        self.item_nprims.setText("Prims: -")
        self.item_type.setText("Type: -")

        self.metadata = None

        self.check_geo_btn.setEnabled(False)
        if self.edit_tags_btn:
            self.edit_tags_btn.setEnabled(False)
        if self.import_3d_btn:
            self.import_3d_btn.setEnabled(False)

    def preview_geo(self):

        pass

    def import_obj(self):

        if not os.path.exists(self.item_path):
            hou.ui.displayMessage("Data not found",
                                  severity=hou.severityType.Error)
            return

        if not self.metadata:
            hou.ui.displayMessage("Metadata not found",
                                  severity=hou.severityType.Error)
            return

        geo = hou.node("/obj").createNode("geo", self.metadata["name"])
        f = hou.node(geo.path() + "/file1")
        f.setName("import_" + self.metadata["name"])
        f.parm("file").set(self.item_path)

class CollectionItem(QtGui.QLabel):

    def __init__(self, metadata=None, collection_root="", parent=None):
        super(CollectionItem, self).__init__(parent=parent)

        global FROM_GAIA_SCATTER
        self.from_gaia_scatter = FROM_GAIA_SCATTER

        self.is_selected = False
        self.metadata = metadata
        self.collection_grid = parent
        self.metadata["collection_root"] = collection_root
        self.setMouseTracking(True)

        self.setFixedSize(QtCore.QSize(85, 85))

        pixdata = self.metadata["thumbnail"]
        pixmap = QtGui.QPixmap()
        pixmap.loadFromData(base64.decodestring(pixdata))
        pixmap = pixmap.scaledToHeight(85, QtCore.Qt.TransformationMode.SmoothTransformation)

        self.setPixmap(pixmap)

        self.setStyleSheet("""QLabel{border: 1px solid black;}""")

    def mousePressEvent(self, event):

        self.collection_grid.item_properties.update_entry(self.metadata)

        cur_item = self.collection_grid.selected_item
        if cur_item:
            cur_item.setStyleSheet("""QLabel{border: 1px solid black}""")
            cur_item.is_selected = False

        if self.is_selected:
            self.is_selected = False
            self.setStyleSheet("""QLabel{border: 1px solid black}""")
        else:
            self.is_selected = True
            self.setStyleSheet("""QLabel{border: 1px solid blue}""")

        self.collection_grid.selected_item = self

        if self.from_gaia_scatter:
            mimeData = QtCore.QMimeData()
            mimeData.setText(str(self.metadata))
            drag = QtGui.QDrag(self)
            drag.setPixmap(self.pixmap())
            drag.setMimeData(mimeData)
            drag.setHotSpot(event.pos() - self.rect().topLeft())
            drag.start(QtCore.Qt.MoveAction)
        
        super(CollectionItem, self).mousePressEvent(event)

class CreateNewEntryWidget(QtGui.QFrame):

    def __init__(self, selected_node=None, create_light=True, assets_grid=None,
                 parent=None):
        super(CreateNewEntryWidget, self).__init__(parent,
                                                   QtCore.Qt.WindowStaysOnTopHint)
        
        self.setWindowTitle("Create new asset")
        self.setWindowIcon(get_icon("populate_database"))
        self.setAutoFillBackground(True)
        
        self.assets_grid = assets_grid

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
        self.thumbnail_pix = get_icon("close").pixmap(1,1)
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

        if not self.validate_data():
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

        self.assets_grid.add_entry(metadata)
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