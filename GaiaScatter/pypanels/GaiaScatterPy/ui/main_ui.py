import hou

from PySide import QtGui
from PySide import QtCore

from ..core import paint
reload(paint)
from ..core import cache
reload(cache)
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
        self.create_new_scatter_btn.clicked.connect(self.create_gaia_scatter)
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
        """ Create or update default layer widget
        """
        top_asset = hou.node(self.gaia_node_path.text())
        self.layers_w = layer_widget.LayersWidget(top_asset, parent=self)
        self.main_layout.addWidget(self.layers_w)

    def create_gaia_scatter(self):

        nodes = [n.path() for n in hou.node("/obj").children() if not \
                 n.path().startswith("/obj/ipr_camera")]

        if not nodes:
            hou.ui.displayMessage("The scene is empty")
            return

        v, name = hou.ui.readInput("Enter a name:", buttons=["OK", "Cancel"])
        if v == 1: return
        name = name.replace(' ', '_')

        terrain_node_id = hou.ui.selectFromList(nodes, title="Terrain Picker", exclusive=True,
                                                column_header="Terrain Geometry",
                                                message="Select the terrain geometry:")
        if not terrain_node_id: return
        terrain_node_id = terrain_node_id[0]

        gaia_node = hou.node("/obj").createNode("Gaia_Scatter", name)
        gaia_node.parm("target_geo").set(nodes[terrain_node_id])

        self.init_gaia_scatter_node(gaia_node.path())

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
        if not r: return

        node_path = paths[r[0]]
        self.init_gaia_scatter_node(node_path)

    def init_gaia_scatter_node(self, node_path):

        cache.set("CURRENT_GAIA_SCATTER", node_path)
        self.init_collection_node(node_path)

        self.gaia_node_path.setText(node_path)
        self.gaia_asset_lbl.setVisible(True)
        self.gaia_node_path.setVisible(True)
        self.create_gaia_node_btn.setVisible(True)
        self.select_gaia_node_btn.setVisible(True)
        self.create_new_scatter_btn.setVisible(False)
        self.open_scatter_btn.setVisible(False)
        self.update_layer_widget()

    def init_collection_node(self, gaia_scatter):
        """ Create the obj/collection subnet where the scatter assets
            will be stored.
        """

        col_name = gaia_scatter.split('/')[-1]
        n = hou.node("/obj/" + col_name + "_collection")
        if not n:
            n = hou.node("/obj").createNode("subnet", col_name + "_collection")
            gpos = hou.node(gaia_scatter).position()
            n.setPosition([gpos.x() + 3.0, gpos.y()])
            n.setComment("Collection assets for Gaia Scatter node: " + gaia_scatter)

        cache.set("CURRENT_GAIA_SCATTER_COLLECTION", n)

        