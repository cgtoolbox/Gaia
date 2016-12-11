import hou

from PySide import QtGui
from PySide import QtCore

from core import paint
reload(paint)
from core.paint import PAINTMODES

from icons.icon import get_icon

from ui.layer import layer_widget
reload(layer_widget)

class MainUI(QtGui.QWidget):

    def __init__(self, parent=None):
        
        super(MainUI, self).__init__(parent=parent)

        self.main_layout = QtGui.QVBoxLayout()
        self.main_layout.setSpacing(0)
        self.main_layout.setAlignment(QtCore.Qt.AlignTop)

        # the gaia scattering digital asset
        gaia_path_layout = QtGui.QHBoxLayout()
        gaia_path_layout.setSpacing(5)

        gaia_path_layout.addWidget(QtGui.QLabel("Scatter Asset:"))

        self.gaia_node_path = QtGui.QLineEdit("")
        gaia_path_layout.addWidget(self.gaia_node_path)

        self.create_gaia_node_btn = QtGui.QPushButton("")
        self.create_gaia_node_btn.setIcon(get_icon("add"))
        self.create_gaia_node_btn.setIconSize(QtCore.QSize(24, 24))
        self.create_gaia_node_btn.setToolTip("Create a new Gaia Scatter asset on selected geo")
        gaia_path_layout.addWidget(self.create_gaia_node_btn)

        self.select_gaia_node_btn = QtGui.QPushButton("")
        self.select_gaia_node_btn.setIcon(get_icon("folder_open"))
        self.select_gaia_node_btn.setIconSize(QtCore.QSize(24, 24))
        self.select_gaia_node_btn.setToolTip("Pick a gaia asset")
        self.select_gaia_node_btn.clicked.connect(self.open_scatter_asset)
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
        self.update_layer_widget()


        