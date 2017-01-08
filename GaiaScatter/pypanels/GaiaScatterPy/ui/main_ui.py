import hou

from PySide import QtGui
from PySide import QtCore

from ..core import paint
reload(paint)
from ..core.paint import PAINTMODES

from ..icons.icon import get_icon

from layer import layer_widget
reload(layer_widget)

class MainUI(QtGui.QWidget):

    def __init__(self, parent=None):
        
        super(MainUI, self).__init__(parent=parent)

        self.main_layout = QtGui.QVBoxLayout()
        self.main_layout.setSpacing(5)
        self.main_layout.setAlignment(QtCore.Qt.AlignTop)

        # First buttons
        self.create_new_scatter_btn = QtGui.QPushButton("Create New Gaia Scatter")
        self.create_new_scatter_btn.setIcon(get_icon("gaia_add"))
        self.create_new_scatter_btn.setIconSize(QtCore.QSize(50, 50))
        self.main_layout.addWidget(self.create_new_scatter_btn)

        self.open_scatter_btn = QtGui.QPushButton("Open Gaia Scatter")
        self.open_scatter_btn.setIcon(get_icon("gaia_open"))
        self.open_scatter_btn.setIconSize(QtCore.QSize(50, 50))
        self.open_scatter_btn.clicked.connect(self.open_scatter_asset)
        self.main_layout.addWidget(self.open_scatter_btn)

        # the gaia scattering digital asset
        gaia_path_layout = QtGui.QHBoxLayout()
        gaia_path_layout.setSpacing(5)
        gaia_path_layout.addWidget(QtGui.QLabel(""))

        self.gaia_asset_lbl = QtGui.QLabel("Scatter Asset:")
        self.gaia_asset_lbl.setVisible(False)
        gaia_path_layout.addWidget(self.gaia_asset_lbl)

        self.gaia_node_path = QtGui.QLineEdit("")
        self.gaia_node_path.setVisible(False)
        gaia_path_layout.addWidget(self.gaia_node_path)

        self.create_gaia_node_btn = QtGui.QPushButton("")
        self.create_gaia_node_btn.setIcon(get_icon("gaia_add"))
        self.create_gaia_node_btn.setIconSize(QtCore.QSize(24, 24))
        self.create_gaia_node_btn.setToolTip("Create a new Gaia Scatter asset on selected geo")
        self.create_gaia_node_btn.setVisible(False)
        gaia_path_layout.addWidget(self.create_gaia_node_btn)

        self.select_gaia_node_btn = QtGui.QPushButton("")
        self.select_gaia_node_btn.setIcon(get_icon("gaia_open"))
        self.select_gaia_node_btn.setIconSize(QtCore.QSize(24, 24))
        self.select_gaia_node_btn.setToolTip("Pick a gaia asset")
        self.select_gaia_node_btn.clicked.connect(self.open_scatter_asset)
        self.select_gaia_node_btn.setVisible(False)
        gaia_path_layout.addWidget(self.select_gaia_node_btn)

        self.main_layout.addItem(gaia_path_layout)

        if self.gaia_node_path.text():
            top_asset = hou.node(self.gaia_node_path.text())
            self.layers_w = layer_widget.LayersWidget(top_asset, parent=self)
            self.main_layout.addWidget(self.layers_w)

        self.setLayout(self.main_layout)

    def update_layer_widget(self):

        top_asset = hou.node(self.gaia_node_path.text())
        self.layers_w = layer_widget.LayersWidget(top_asset, parent=self)
        self.main_layout.addWidget(self.layers_w)

    def open_scatter_asset(self):

        nodes = [n for n in hou.node("/obj").children() \
                 if n.type().name() == "Gaia_Scatter"]
        if not nodes:
            hou.ui.displayMessage("No Gaia Scatter asset found")
            return

        names = [n.name() for n in nodes]
        paths = [n.path() for n in nodes]

        r = hou.ui.selectFromList(names, title="Selection", exclusive=True,
                                  column_header="Scatter Assets",
                                  message="Select a Gaia Scatter asset to load:")
        hou.ui.selectFromList
        if not r: return

        self.gaia_node_path.setText(paths[r[0]])
        self.gaia_asset_lbl.setVisible(True)
        self.gaia_node_path.setVisible(True)
        self.create_gaia_node_btn.setVisible(True)
        self.select_gaia_node_btn.setVisible(True)
        self.create_new_scatter_btn.setVisible(False)
        self.open_scatter_btn.setVisible(False)
        self.update_layer_widget()


        