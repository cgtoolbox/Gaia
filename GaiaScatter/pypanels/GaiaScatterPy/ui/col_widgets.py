import hou
import sys
import os
import tempfile

from PySide import QtGui
from PySide import QtCore
import toolutils

from ..icons.icon import get_icon
from GaiaCommon import nodeInfos

from . import widgets
reload(widgets)

class CollectionInstanceWidget(QtGui.QWidget):
    """ Widget used in the layer widget, when object are dropped from the collection
        to the scatter tool.
    """
    def __init__(self, layer_node=None, item_infos=None, 
                 set_parms=True, parent=None):

        super(CollectionInstanceWidget, self).__init__(parent=parent)

        self.setToolTip(unicode(item_infos.tooltip))
        self.setAcceptDrops(True)
        self.top_w = parent

        self._name = item_infos.name
        self.asset_category = item_infos.category
        self.asset_path = item_infos.asset_path
        self.uid = item_infos.uid
        self.collection_root = item_infos.collection_root.replace('\\', '/')

        self.idx = item_infos.idx
        self.layer_node = layer_node
        
        # When added from collection, parm are set to new values
        if set_parms:
            self.layer_node.parm("path_" + str(self.idx)).set(self.asset_path)
            self.layer_node.parm("category_" + str(self.idx)).set(self.asset_category)
            self.layer_node.parm("asset_uid_" + str(self.idx)).set(self.uid)
            self.layer_node.parm("collection_root_" + str(self.idx)).set(self.collection_root)

        self.influence = self.layer_node.evalParm("influence_" + str(self.idx))
        self.thumbnail_binary = item_infos.thumbnail_binary

        # states
        self.displayed = item_infos.visible
        self.display_mode = item_infos.display_mode

        self.main_layout = QtGui.QVBoxLayout()
        self.main_layout.setAlignment(QtCore.Qt.AlignTop)
        self.main_layout.setContentsMargins(0,0,0,0)
        self.main_layout.setSpacing(0)

        self.btn_layout = QtGui.QHBoxLayout()
        self.btn_layout.setContentsMargins(0,0,0,0)
        self.btn_layout.setSpacing(10)
        self.btn_layout.setAlignment(QtCore.Qt.AlignLeft)

        self.show_toggle_btn = QtGui.QPushButton("")
        self.show_toggle_btn.setToolTip("Hide / Show object")
        if self.displayed:
            self.show_toggle_btn.setIcon(get_icon("eye_open"))
        else:
            self.show_toggle_btn.setIcon(get_icon("eye_close"))
        self.show_toggle_btn.setFixedWidth(22)
        self.show_toggle_btn.setFixedHeight(22)
        self.show_toggle_btn.setFlat(True)
        self.show_toggle_btn.clicked.connect(self.show_object)
        self.btn_layout.addWidget(self.show_toggle_btn)

        self.display_mode_btn = QtGui.QPushButton("")
        if self.display_mode == 0:
            self.display_mode_btn.setIcon(get_icon("tree"))
        elif self.display_mode == 1:
            self.display_mode_btn.setIcon(get_icon("diffusion"))
        else:
            self.display_mode_btn.setIcon(get_icon("cube"))
        self.display_mode_btn.setFixedWidth(22)
        self.display_mode_btn.setFixedHeight(22)
        self.display_mode_btn.setFlat(True)
        self.display_mode_btn.clicked.connect(self.change_display_mode)
        self.btn_layout.addWidget(self.display_mode_btn)

        self.displayModeMenu = QtGui.QMenu(self)

        full_geo = QtGui.QAction(get_icon("tree"), " Full Geometry", self)
        full_geo.triggered.connect(lambda: self.set_display_mode(0))
        self.displayModeMenu.addAction(full_geo)
        boudning_box = QtGui.QAction(get_icon("cube"), " Bounding Box", self)
        boudning_box.triggered.connect(lambda: self.set_display_mode(2))
        self.displayModeMenu.addAction(boudning_box)
        pt_cloud = QtGui.QAction(get_icon("diffusion"), " Points Coud", self)
        pt_cloud.triggered.connect(lambda: self.set_display_mode(1))
        self.displayModeMenu.addAction(pt_cloud)

        self.delete_btn = QtGui.QPushButton("")
        self.delete_btn.setIcon(get_icon("close"))
        self.delete_btn.setFixedWidth(22)
        self.delete_btn.setFixedHeight(22)
        self.delete_btn.setFlat(True)
        self.delete_btn.clicked.connect(self.remove_item)
        self.btn_layout.addWidget(self.delete_btn)
        
        self.main_layout.addItem(self.btn_layout)

        self.thumbnail = QtGui.QLabel()
        self.thumbnail.setFixedWidth(90)
        self.thumbnail.setFixedHeight(90)
        self.pixmap = QtGui.QPixmap()
        self.pixmap.loadFromData(self.thumbnail_binary)
        self.pixmap = self.pixmap.scaledToHeight(90, QtCore.Qt.TransformationMode.SmoothTransformation)
        self.thumbnail.setPixmap(self.pixmap)
        self.thumbnail.setStyleSheet("""QLabel{border: 1px solid black}""")
        self.main_layout.addWidget(self.thumbnail)

        self.influence_base = InfluenceBarWidget(value=self.influence,
                                                 idx=self.idx,
                                                 callback=self.change_influence)
        self.main_layout.addWidget(self.influence_base)

        self.setLayout(self.main_layout)

    def change_influence(self, value):

        self.layer_node.parm("influence_" + str(self.idx)).set(value)

    def remove_item(self):
        """ Remove item from list, the actual asset node will not be removed
        """

        instances = self.layer_node.parm("instances")
        instances.removeMultiParmInstance(self.idx - 1)

        self.top_w.remove_item(self)

    def show_object(self):
        """ Hide / show current collection item
        """
        asset_node = hou.node(self.asset_path)
        assert asset_node is not None, "Asset node not found"

        switch = asset_node.node("show_object")
        assert switch is not None, "Asset switch node not found"

        if self.displayed:
            # hide it
            self.displayed = False
            switch.parm("input").set(0)
            self.show_toggle_btn.setIcon(get_icon("eye_close"))
            self.layer_node.parm("visible_" + str(self.idx)).set(0)
        else:
            # show it
            self.displayed = True
            switch.parm("input").set(1)
            self.show_toggle_btn.setIcon(get_icon("eye_open"))
            self.layer_node.parm("visible_" + str(self.idx)).set(1)

    def change_display_mode(self):
        """ Change the display mode of the current collection item
            ( Bounding box, pt clouds, centroid or full geo )
        """
        
        p = self.display_mode_btn.pos()
        p = self.mapToGlobal(p)
        self.displayModeMenu.popup(p)

    def set_display_mode(self, mode):

        asset_node = hou.node(self.asset_path)
        assert asset_node is not None, "Asset node not found"

        _file = asset_node.node("import_file")
        assert _file is not None, "_file node not found"

        _file.parm("viewportlod").set(mode)
        if mode == 0:
            self.display_mode_btn.setIcon(get_icon("tree"))
        elif mode == 1:
            self.display_mode_btn.setIcon(get_icon("diffusion"))
        elif mode == 2:
            self.display_mode_btn.setIcon(get_icon("cube"))

        self.layer_node.parm("display_mode_" + str(self.idx)).set(mode)

    def dragEnterEvent(self, event):

        return

    def dragMoveEvent(self, event):
        
        return

    def dropEvent(self, event):
        
        try:
            data = event.mimeData().text()
            data = eval(data)
            self.top_w.append_item(data)
        except SyntaxError:
            print("Error: bad formating metadata")

class InfluenceBarWidget(QtGui.QWidget):
    """ Special custom slider used in the collection thumbnail widget
        to set the influence of the given props in the instance scattering
    """
    def __init__(self, value=50.0, w=91, h=15, idx=0, callback=None, parent=None):
        
        super(InfluenceBarWidget, self).__init__(parent=parent)
        
        self.main_layout = QtGui.QHBoxLayout()

        self.callback = callback
        self.idx = idx
        self._value = value
        self._w = w
        self._h = h
        self.setContentsMargins(0, 0, 0, 0)

        self.main_layout.setSpacing(0)
        self.main_layout.setContentsMargins(0, 0, 0, 0)
        self.main_layout.setAlignment(QtCore.Qt.AlignLeft)
        
        self.setFixedWidth(w)
        self.setFixedHeight(h)
        
        self.slider = QtGui.QSlider()
        self.slider.setMinimum(0)
        self.slider.setMaximum(100)
        self.slider.setValue(value)
        self.slider.setFixedWidth(w-25)
        self.slider.setFixedHeight(h)
        self.slider.setStyleSheet(self._slider_styleSheet())
        self.slider.setOrientation(QtCore.Qt.Horizontal)
        self.slider.valueChanged.connect(self._update_from_slider)
        self.slider.setContentsMargins(0, 0, 0, 0)
        self.main_layout.addWidget(self.slider)

        self.numeric_input = QtGui.QSpinBox()
        self.numeric_input.setFixedWidth(25)
        self.numeric_input.setFixedHeight(h)
        self.numeric_input.setMinimum(0)
        self.numeric_input.setMaximum(100)
        self.numeric_input.setValue(value)
        self.numeric_input.setStyleSheet(self._numeric_input_stylesheet())
        nb = QtGui.QAbstractSpinBox.ButtonSymbols.NoButtons
        self.numeric_input.setButtonSymbols(nb)
        self.numeric_input.setContentsMargins(0, 0, 0, 0)
        self.numeric_input.valueChanged.connect(self._update_from_numeric)
        self.main_layout.addWidget(self.numeric_input)

        self.setLayout(self.main_layout)

    def _update_from_numeric(self):

        self._value = self.numeric_input.value()
        self.slider.setValue(self._value)

    def _update_from_slider(self):

        self._value = self.slider.value()
        self.numeric_input.setValue(self._value)

        if self.callback:
            self.callback(self._value)

    def _numeric_input_stylesheet(self):
        
        return ''' QSpinBox{background-color: #474b5e;
                            border: 0px;}'''

    def _slider_styleSheet(self):

        return '''
                QSlider::handle{
                    margin-top: -9px;
                    margin-bottom: -9px;
                    background-color: #002bcb;
                    height ''' + str(self._h) + ''';
                    width: 6px;
                    border: 1px solid #001f92;
                }

                QSlider::sub-page:horizontal {
                    margin-top: -9px;
                    margin-bottom: -9px;
                    background: qlineargradient(x1: 0, y1: 0,
                                                x2: 0, y2: 1,
                        stop: 0 #3a60f1, stop: 1 #002bcb);
                    background: qlineargradient(x1: 0, y1: 0.2,
                                                x2: 1, y2: 1,
                        stop: 0 #3a60f1, stop: 1 #002bcb);
                    height: ''' + str(self._h) + '''px;
                }

                QSlider::add-page:horizontal {
                    margin-top: -9px;
                    margin-bottom: -9px;
                    background: #585e76;
                    height: ''' + str(self._h) + '''px;
                }'''
        
    def get_value(self):

        return self._value

    def set_value(self, value):

        if value > 100:
            value = 100

        elif value < 0:
            value = 0

        self._value = value
        self.slider.setValue(value)
        self.numeric_input.setValue(value)