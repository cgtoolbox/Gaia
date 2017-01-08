import os
import hou

from PySide import QtGui
from PySide import QtCore

from . import strokes
reload(strokes)

from GaiaCollectionPy import ui as GC_ui
reload(GC_ui)

from GaiaCommon import nodeInfos
reload(nodeInfos)

from ...ui import widgets
reload(widgets)

from ...ui import col_widgets
reload(col_widgets)

from ...icons.icon import get_icon

from GaiaCollectionPy.ui.widgets import CreateNewEntryWidget

class LayersWidget(QtGui.QWidget):

    def __init__(self, top_asset, parent=None):
        super(LayersWidget, self).__init__(parent=parent)

        main_layout = QtGui.QVBoxLayout()

        self.top_asset = top_asset
        self.instance_node = hou.node(self.top_asset.path() + "/INSTANCES")

        # layer infos used to fetch gaia layer node
        self.scatter_infos = nodeInfos.GaiaScatterInfos()
        p = self.parentWidget().gaia_node_path.text()
        self.scatter_infos.node_path = p
        self.scatter_infos.node = hou.node(p)
        assert self.scatter_infos.node != None, "Invalid Gaia Node"

        # tab widget
        self.layers = []
        self.tabs = QtGui.QTabWidget()
        self.tabs.setStyleSheet("""
        QTabWidget::tab-bar {
            left: 5px;
        }
        QTabBar::tab {
            background: qlineargradient(x1: 0, y1: 0, x2: 0, y2: 1,
                                        stop: 0 #2b5327, stop: 0.4 #3b7536,
                                        stop: 0 #2b5327, stop: 1.0 #3b7536);
            border: 0px solid black;
            border-bottom-color: black;
            border-top-left-radius: 5px;
            border-top-right-radius: 5px;
            margin-right: 2px;
        }
        QTabBar::tab:!selected {
            margin-top: 2px;
            color:grey;
            background: qlineargradient(x1: 0, y1: 0, x2: 0, y2: 1,
                                        stop: 0 #2c2d35, stop: 0.4 #1c1c21,
                                        stop: 0 #2c2d35, stop: 1.0 #1c1c21);
            border: 0px solid black;
            border-bottom-color: black;
            border-top-left-radius: 3px;
            border-top-right-radius: 3px;
        }
        """)

        self.add_layer_btn = QtGui.QPushButton(self)
        self.add_layer_btn.setToolTip("Create a new layer")
        self.add_layer_btn.setFlat(True)
        self.add_layer_btn.setIcon(get_icon("add_plane"))
        self.add_layer_btn.clicked.connect(self.add_layer)
        self.tabs.setCornerWidget(self.add_layer_btn)

        self._init_layers()
        main_layout.addWidget(self.tabs)

        self.setLayout(main_layout)

    def add_layer(self):

        w = widgets.PickLayerTypeWidget(parent=hou.ui.mainQtWindow())
        w.exec_()

        if not w.layer_type:
            return

        name = w.layer_name
        
        name = name.replace(' ', '_')
        container = hou.node(self.scatter_infos.node_path + "/LAYERS")

        # create houdini node
        if w.layer_type == "paint":
            layer_node = container.createNode("Gaia_Paint_Scatter_Layer",
                                              node_name=name)
        else:
            layer_node = container.createNode("Gaia_Fill_Scatter_Layer",
                                              node_name=name)

        layer_node.setUserData("LATEST_STROKE_ID", "0")
        layer_node.allowEditingOfContents()
        layer_infos = nodeInfos.GaiaScatterInfos()
        p = layer_node.path()
        layer_infos.node_path = p
        layer_infos.node = layer_node

        # create UI widget
        if w.layer_type == "paint":
            layer = LayerTabWidget(layer_infos=layer_infos,
                                   tabs_widget=self,
                                   parent=self)
        else:
            layer = LayerFillTabWidget(layer_infos=layer_infos,
                                       tabs_widget=self,
                                       parent=self)
        layer.id = len(self.layers)
        self.layers.append(layer)
        self.tabs.addTab(layer, layer_node.name().replace('_', ' '))
        if w.layer_type == "paint":
            self.tabs.setTabIcon(layer.id, get_icon("brush"))
        else:
            self.tabs.setTabIcon(layer.id, get_icon("fill"))

        container.layoutChildren()

        self.tabs.setCurrentWidget(layer)

        self.instance_node.cook(True)

    def remove_layer(self, idx):

        w = self.layers[idx]
        tab_idx = self.tabs.indexOf(w)
        self.tabs.removeTab(tab_idx)
        self.layers.pop(idx)
        w.setParent(None)
        w.deleteLater()

        for i, w in enumerate(self.layers):
            w.id = i

    def _init_layers(self):
        """ Add layer tab widget if any gaia scatters found. If none of them found
            create a default one
        """

        container = hou.node(self.scatter_infos.node_path + "/LAYERS")
        childrens = [n for n in container.children() \
                     if n.type().name() in ["Gaia_Paint_Scatter_Layer",
                                            "Gaia_Fill_Scatter_Layer"]]

        if not childrens:
            n = container.createNode("Gaia_Paint_Scatter_Layer",
                                     node_name="Layer_1")
            n.setUserData("LATEST_STROKE_ID", "0")
            n.allowEditingOfContents()
            childrens = [n]

        for n in childrens:
            
            n.setUserData("LATEST_STROKE_ID", "0")
            layer_infos = nodeInfos.GaiaScatterInfos()
            p = n.path()
            layer_infos.node_path = p
            layer_infos.node = n

            if n.type().name() == "Gaia_Paint_Scatter_Layer":
                layer = LayerTabWidget(layer_infos=layer_infos,
                                       tabs_widget=self,
                                       parent=self)
            else:
                layer = LayerFillTabWidget(layer_infos=layer_infos,
                                           tabs_widget=self,
                                           parent=self)

            layer.id = len(self.layers)
            self.layers.append(layer)
            
            self.tabs.addTab(layer, layer_infos.node.name().replace('_', ' '))
            if n.type().name() == "Gaia_Paint_Scatter_Layer":
                self.tabs.setTabIcon(layer.id, get_icon("brush"))
            else:
                self.tabs.setTabIcon(layer.id, get_icon("fill"))

        self.instance_node.cook(True)

class LayerTabWidget(QtGui.QWidget):

    def __init__(self, layer_infos=None, tabs_widget=None, parent=None):
        super(LayerTabWidget, self).__init__(parent=parent)

        ############################################################
        # PLACEHOLDER CODE SET DEFAULT INSTANCE MODELS TO A, B, C
        n = layer_infos.node
        n.parm("instances").set(3)

        n.parm("influence_1").set(45)
        n.parm("path_1").set("/obj/object_A")

        n.parm("influence_2").set(20)
        n.parm("path_2").set("/obj/object_B")

        n.parm("influence_3").set(35)
        n.parm("path_3").set("/obj/object_C")
        #############################################################

        self.setObjectName("layer")
        self.layer_infos = layer_infos
        self.id = -1
        self.enabled = True
        self.tabs_widget = tabs_widget

        # layouts
        self.main_layout = QtGui.QVBoxLayout()
        self.main_layout.setSpacing(0)
        self.main_layout.setAlignment(QtCore.Qt.AlignTop|QtCore.Qt.AlignLeft)

        # top toolbar
        top_toolbar_layout = QtGui.QHBoxLayout()
        top_toolbar_layout.setSpacing(5)
        top_toolbar_layout.setAlignment(QtCore.Qt.AlignLeft)

        self.save_lay_btn = QtGui.QPushButton("")
        self.save_lay_btn.setIcon(get_icon("diskette"))
        self.save_lay_btn.setIconSize(QtCore.QSize(24,24))
        self.save_lay_btn.setToolTip("Save current layer to external geo file")
        self.save_lay_btn.clicked.connect(self.save)
        top_toolbar_layout.addWidget(self.save_lay_btn)

        self.infos_lay_btn = QtGui.QPushButton("")
        self.infos_lay_btn.setIcon(get_icon("white_list"))
        self.infos_lay_btn.setIconSize(QtCore.QSize(24,24))
        self.infos_lay_btn.setToolTip("Get informations about current layer")
        self.infos_lay_btn.clicked.connect(self.display_infos)
        top_toolbar_layout.addWidget(self.infos_lay_btn)

        self.hide_lay_btn = QtGui.QPushButton("")
        if self.layer_infos.node.parm("enable").eval():
            self.hide_lay_btn.setIcon(get_icon("eye_open"))
        else:
            self.hide_lay_btn.setIcon(get_icon("eye_close"))
            self.enabled = False
        self.hide_lay_btn.setIconSize(QtCore.QSize(24,24))
        self.hide_lay_btn.setToolTip("Hide / Show layer")
        self.hide_lay_btn.clicked.connect(self.switch_enable)
        top_toolbar_layout.addWidget(self.hide_lay_btn)

        self.delete_lay_btn = QtGui.QPushButton("")
        self.delete_lay_btn.setIcon(get_icon("close"))
        self.delete_lay_btn.setIconSize(QtCore.QSize(24,24))
        self.delete_lay_btn.setToolTip("Delete the Gaia layer")
        self.delete_lay_btn.clicked.connect(self.delete_layer)
        top_toolbar_layout.addWidget(self.delete_lay_btn)

        self.main_layout.addItem(top_toolbar_layout)

        # scroll layout part
        self.scroll = QtGui.QScrollArea()
        self.scroll.setStyleSheet("""QScrollArea{border:0px}""")
        self.scroll.setContentsMargins(0,0,0,0)
        self.scroll.setWidgetResizable(True)
        self.scroll_widget = QtGui.QWidget()
        self.scroll_layout = QtGui.QVBoxLayout()
        self.scroll_layout.setAlignment(QtCore.Qt.AlignTop)
        self.scroll_layout.setContentsMargins(3,3,3,3)

        # Instance models list widgets
        self.instances_list = InstancesListWidget(layer_infos=layer_infos)

        self.instances_list_w = widgets.CollapsableWidget(label="Instance Models",
                                                          widget=self.instances_list,
                                                          collapsed=True,
                                                          parent=self)
        self.scroll_layout.addWidget(self.instances_list_w)
        
        self.scroll_widget.setLayout(self.scroll_layout)
        self.scroll.setWidget(self.scroll_widget)
        self.main_layout.addWidget(self.scroll)

        self.init_tool_widgets()
        self.setLayout(self.main_layout)

    def init_tool_widgets(self):

        # global scatter options
        self.scatter_settings = ScatterOptionsWidget(gaia_node=self.layer_infos)
        self.scatter_settings_w = widgets.CollapsableWidget(label="Scattering Settings",
                                                           widget=self.scatter_settings,
                                                           collapsed=True,
                                                           parent=self)
        self.scroll_layout.addWidget(self.scatter_settings_w)

        # scattering rules
        self.scatter_rules = ScatterRulesWidget(self.layer_infos)
        self.scatter_rules_w = widgets.CollapsableWidget(label="Scattering Rules",
                                                         widget=self.scatter_rules,
                                                         collapsed=True,
                                                         parent=self)
        self.scroll_layout.addWidget(self.scatter_rules_w)

        # Strokes Groups
        self.strokes_groups = strokes.StrokesWidget(self.layer_infos)
        self.strokes_groups_w = widgets.CollapsableWidget(label="Paint",
                                                          widget=self.strokes_groups,
                                                          collapsed=True,
                                                          parent=self)
        self.scroll_layout.addWidget(self.strokes_groups_w)
    
    def delete_layer(self):

        r = hou.ui.displayMessage("Delete the layer?",
                                  help="This can't be undo !",
                                  title="Confirm",
                                  buttons=["Ok", "Cancel"],
                                  severity=hou.severityType.Warning)
        if r == 1: return

        self.layer_infos.node.destroy()
        self.tabs_widget.remove_layer(self.id)

    def switch_enable(self):

        if self.enabled:
            self.hide_lay_btn.setIcon(get_icon("eye_close"))
            self.enabled = False
            self.layer_infos.node.parm("enable").set(0)
        else:
            self.hide_lay_btn.setIcon(get_icon("eye_open"))
            self.enabled = True
            self.layer_infos.node.parm("enable").set(1)

    def save(self):

        cur_name = self.layer_infos.node.name()
        geo = hou.node(self.layer_infos.node.path() + "/OUT").geometry()
        f = hou.ui.selectFile()
        if not f: return
        if os.path.exists(f):
            r = hou.ui.displayMessage("File: " + f + " already exists, override ?", 
                                      buttons=["Yes", "Cancel"],
                                      severity=hou.severityType.Warning)
            if r == 1: return
        geo.saveToFile(f)
        hou.ui.displayMessage("File Saved !", help=f)

    def display_infos(self):

        cur_name = self.layer_infos.node.name()
        geo_out = hou.node(self.layer_infos.node.path() + "/OUT").geometry()
        geo_painters = hou.node(self.layer_infos.node.path() + "/PAINTERS").geometry()
        npts = len(geo_out.points())
        n_strokes = len([g for g in geo_painters.pointGroups() \
                         if g.name().startswith("stroke_")])
        n_grps = len(self.strokes_groups.strokes_list.strokes)

        msg = "Layer: {}, id: {}\n\n".format(cur_name, self.id + 1)
        msg += str(n_grps) + " painter stroke group(s)\n"
        msg += str(n_strokes) + " painter stroke(s)\n\n"
        msg += str(npts) + " point(s)\n"

        hou.ui.displayMessage(msg, title="layer infos")

class LayerFillTabWidget(LayerTabWidget):

    def __init__(self, layer_infos=None, tabs_widget=None, parent=None):
        super(LayerFillTabWidget, self).__init__(layer_infos, tabs_widget, parent)

    def init_tool_widgets(self):

        # scattering settings
        self.scatter_settings = FillScatterOptionsWidget(self.layer_infos)
        self.scatter_scatter_settings_w = widgets.CollapsableWidget(label="Scattering Settings",
                                                         widget=self.scatter_settings,
                                                         collapsed=True,
                                                         parent=self)
        self.scroll_layout.addWidget(self.scatter_scatter_settings_w)

        # scattering rules
        self.scatter_rules = ScatterRulesWidget(self.layer_infos, is_fill=True)
        self.scatter_rules_w = widgets.CollapsableWidget(label="Scattering Rules",
                                                         widget=self.scatter_rules,
                                                         collapsed=True,
                                                         parent=self)
        self.scroll_layout.addWidget(self.scatter_rules_w)

class ScatterOptionsWidget(QtGui.QWidget):

    def __init__(self, gaia_node=None, parent=None):
        super(ScatterOptionsWidget, self).__init__(parent=parent)

        main_layout = QtGui.QVBoxLayout()
        main_layout.setSpacing(5)
        main_layout.setAlignment(QtCore.Qt.AlignTop)

        self.gaia_node = gaia_node.node
        self.default = self.fetch_gaia_default_values()

        self.seed = widgets.HSlider("seed",
                                    default_value=self.default["seed"],
                                    hou_parm=self.gaia_node.parm("seed"))
        main_layout.addWidget(self.seed)

        self.density = widgets.HSlider("density",
                                       default_value=self.default["density"],
                                       hou_parm=self.gaia_node.parm("density"))
        main_layout.addWidget(self.density)

        self.min_distance = widgets.HSlider("min distance",
                                            default_value=self.default["min_distance"],
                                            max=1.0,
                                            hou_parm=self.gaia_node.parm("min_distance"))
        main_layout.addWidget(self.min_distance)

        self.max_points = widgets.HSlider(label="max points",
                                          _type="int",
                                          default_value=self.default["max_points"],
                                          enable=self.default["use_max_points"],
                                          min=1,
                                          max=1000000,
                                          enable_checkbox=True,
                                          hou_parm=self.gaia_node.parm("max_points"),
                                          hou_checkbox=self.gaia_node.parm("use_max_points"))
        main_layout.addWidget(self.max_points)
        
        self.resample_strokes = widgets.HSlider("resample strokes",
                                                default_value=self.default["resample_strokes"],
                                                max=5.0,
                                                hou_parm=self.gaia_node.parm("resample_strokes"))
        main_layout.addWidget(self.resample_strokes)
        
        self.up_vector = widgets.HVector("up_vector", size=3, min=-1.0, max=1.0,
                                         lock_min=True, lock_max=True,
                                         default_value=self.default["up_vector"],
                                         hou_parm=[self.gaia_node.parm("up_vector1"),
                                                   self.gaia_node.parm("up_vector2"),
                                                   self.gaia_node.parm("up_vector3")])
        main_layout.addWidget(self.up_vector)

        self.up_influence = widgets.HVector("min max up influence", max=1.0, min=0.0,
                                            lock_max=True, lock_min=True,
                                            default_value=self.default["up_influence"],
                                            hou_parm=[self.gaia_node.parm("up_influence1"),
                                                      self.gaia_node.parm("up_influence2")])
        main_layout.addWidget(self.up_influence)

        self.up_inf_seed = widgets.HSlider("up influence seed",
                                           default_value=self.default["up_influence_seed"],
                                           hou_parm=self.gaia_node.parm("up_influence_seed"))
        main_layout.addWidget(self.up_inf_seed)

        self.min_max_rot = widgets.HVector("min max rot",
                                           default_value=self.default["min_max_rot"],
                                           hou_parm=[self.gaia_node.parm("min_max_rot1"),
                                                     self.gaia_node.parm("min_max_rot2")])
        main_layout.addWidget(self.min_max_rot)

        self.rotation_seed = widgets.HSlider("rotation seed",
                                             default_value=self.default["rotation_seed"],
                                             hou_parm=self.gaia_node.parm("rotation_seed"))
        main_layout.addWidget(self.rotation_seed)

        self.radius_multiplier = widgets.HSlider("base scale",
                                                 default_value=self.default["base_scale"],
                                                 max=5.0,
                                                 hou_parm=self.gaia_node.parm("base_scale"))
        main_layout.addWidget(self.radius_multiplier)

        self.radius_affects_scale = QtGui.QCheckBox("radius affects scale")
        self.radius_affects_scale.setChecked(self.default["radius_affects_scale"])
        self.radius_affects_scale.clicked.connect(self.checkbox_radius_callback)
        main_layout.addWidget(self.radius_affects_scale)

        self.min_max_scale = widgets.HVector("min max scale", min=0.0, max=5.0, lock_min=True,
                                             default_value=self.default["min_max_scale"],
                                             hou_parm=[self.gaia_node.parm("min_max_scale1"),
                                                       self.gaia_node.parm("min_max_scale2")])
        main_layout.addWidget(self.min_max_scale)

        self.scale_seed = widgets.HSlider("scale seed",
                                          default_value=self.default["scale_seed"],
                                          hou_parm=self.gaia_node.parm("scale_seed"))
        main_layout.addWidget(self.scale_seed)

        self.setLayout(main_layout)

    def checkbox_radius_callback(self):

        p = self.gaia_node.parm("radius_affects_scale")
        p.set(self.radius_affects_scale.isChecked())

    def fetch_gaia_default_values(self):

        values = {}
        values["seed"] = self.gaia_node.parm("seed").eval()
        values["density"] = self.gaia_node.parm("density").eval()
        values["min_distance"] = self.gaia_node.parm("min_distance").eval()
        values["max_points"] = self.gaia_node.parm("max_points").eval()
        values["use_max_points"] = self.gaia_node.parm("use_max_points").eval()
        values["base_scale"] = self.gaia_node.parm("base_scale").eval()
        values["radius_affects_scale"] = self.gaia_node.parm("radius_affects_scale").eval()
        values["resample_strokes"] = self.gaia_node.parm("resample_strokes").eval()
        values["up_vector"] = [self.gaia_node.parm("up_vector1").eval(),
                               self.gaia_node.parm("up_vector2").eval(),
                               self.gaia_node.parm("up_vector3").eval()]
        values["up_influence"] = [self.gaia_node.parm("up_influence1").eval(),
                                  self.gaia_node.parm("up_influence2").eval()]
        values["up_influence_seed"] = self.gaia_node.parm("up_influence_seed").eval()
        values["min_max_rot"] = [self.gaia_node.parm("min_max_rot1").eval(),
                                 self.gaia_node.parm("min_max_rot2").eval()]
        values["rotation_seed"] = self.gaia_node.parm("rotation_seed").eval()
        values["min_max_scale"] = [self.gaia_node.parm("min_max_scale1").eval(),
                                   self.gaia_node.parm("min_max_scale1").eval()]
        values["scale_seed"] = self.gaia_node.parm("scale_seed").eval()

        return values

class FillScatterOptionsWidget(QtGui.QWidget):

    def __init__(self, gaia_node=None, parent=None):
        super(FillScatterOptionsWidget, self).__init__(parent=parent)

        main_layout = QtGui.QVBoxLayout()
        main_layout.setSpacing(5)
        main_layout.setAlignment(QtCore.Qt.AlignTop)

        self.gaia_node = gaia_node.node
        self.default = self.fetch_gaia_default_values()

        self.seed = widgets.HSlider("seed",
                                    default_value=self.default["seed"],
                                    hou_parm=self.gaia_node.parm("seed"))
        main_layout.addWidget(self.seed)

        self.seed = widgets.HSlider("density scale",
                                    default_value=self.default["density_scale"],
                                    hou_parm=self.gaia_node.parm("density_scale"))
        main_layout.addWidget(self.seed)

        self.max_points = widgets.HSlider(label="max points",
                                          _type="int",
                                          default_value=self.default["max_points"],
                                          enable=self.default["use_max_points"],
                                          min=1,
                                          max=1000000,
                                          enable_checkbox=True,
                                          hou_parm=self.gaia_node.parm("max_points"),
                                          hou_checkbox=self.gaia_node.parm("use_max_points"))
        main_layout.addWidget(self.max_points)

        self.relax_iters = widgets.HSlider(label="relax iterations",
                                           _type="int",
                                           default_value=self.default["relax_iterations"],
                                           enable=self.default["use_relax_iterations"],
                                           min=0,
                                           max=10,
                                           enable_checkbox=True,
                                           hou_parm=self.gaia_node.parm("relax_iterations"),
                                           hou_checkbox=self.gaia_node.parm("use_relax_points"))
        main_layout.addWidget(self.relax_iters)

        self.up_vector = widgets.HVector("up_vector", size=3, min=-1.0, max=1.0,
                                         lock_min=True, lock_max=True,
                                         default_value=self.default["up_vector"],
                                         hou_parm=[self.gaia_node.parm("up_vector1"),
                                                   self.gaia_node.parm("up_vector2"),
                                                   self.gaia_node.parm("up_vector3")])
        main_layout.addWidget(self.up_vector)

        self.up_influence = widgets.HVector("min max up influence", max=1.0, min=0.0,
                                            lock_max=True, lock_min=True,
                                            default_value=self.default["up_influence"],
                                            hou_parm=[self.gaia_node.parm("up_influence1"),
                                                      self.gaia_node.parm("up_influence2")])
        main_layout.addWidget(self.up_influence)

        self.up_inf_seed = widgets.HSlider("up influence seed",
                                           default_value=self.default["up_influence_seed"],
                                           hou_parm=self.gaia_node.parm("up_influence_seed"))
        main_layout.addWidget(self.up_inf_seed)

        self.min_max_rot = widgets.HVector("min max rot",
                                           default_value=self.default["min_max_rot"],
                                           hou_parm=[self.gaia_node.parm("min_max_rot1"),
                                                     self.gaia_node.parm("min_max_rot2")])
        main_layout.addWidget(self.min_max_rot)

        self.rotation_seed = widgets.HSlider("rotation seed",
                                             default_value=self.default["rotation_seed"],
                                             hou_parm=self.gaia_node.parm("rotation_seed"))
        main_layout.addWidget(self.rotation_seed)

        self.radius_multiplier = widgets.HSlider("base scale",
                                                 default_value=self.default["base_scale"],
                                                 max=5.0,
                                                 hou_parm=self.gaia_node.parm("base_scale"))
        main_layout.addWidget(self.radius_multiplier)

        self.min_max_scale = widgets.HVector("min max scale", min=0.0, max=5.0, lock_min=True,
                                             default_value=self.default["min_max_scale"],
                                             hou_parm=[self.gaia_node.parm("min_max_scalex"),
                                                       self.gaia_node.parm("min_max_scaley")])
        main_layout.addWidget(self.min_max_scale)

        self.scale_seed = widgets.HSlider("scale seed",
                                          default_value=self.default["scale_seed"],
                                          hou_parm=self.gaia_node.parm("scale_seed"))
        main_layout.addWidget(self.scale_seed)


        self.setLayout(main_layout)

    def fetch_gaia_default_values(self):

        values = {}
        values["seed"] = self.gaia_node.parm("seed").eval()
        values["density_attribute"] = self.gaia_node.parm("density_attribute").eval()
        values["use_density_attribute"] = self.gaia_node.parm("use_density_attribute").eval()
        values["density_scale"] = self.gaia_node.parm("density_scale").eval()
        values["use_max_points"] = self.gaia_node.parm("use_max_points").eval()
        values["max_points"] = self.gaia_node.parm("max_points").eval()
        values["use_relax_iterations"] = self.gaia_node.parm("use_relax_points").eval()
        values["relax_iterations"] = self.gaia_node.parm("relax_iterations").eval()
        values["scale_radii_by"] = self.gaia_node.parm("scale_radii_by").eval()
        values["use_max_relax_radius"] = self.gaia_node.parm("use_max_relax_radius").eval()
        values["up_vector"] = [self.gaia_node.parm("up_vectorx").eval(),
                               self.gaia_node.parm("up_vectory").eval(),
                               self.gaia_node.parm("up_vectorz").eval()]
        values["up_influence_seed"] = self.gaia_node.parm("seed").eval()
        values["up_influence"] = [self.gaia_node.parm("up_influence1").eval(),
                                  self.gaia_node.parm("up_influence2").eval()]
        values["min_max_rot"] = [self.gaia_node.parm("min_max_rotx").eval(),
                                 self.gaia_node.parm("min_max_roty").eval(),]
        values["rotation_seed"] = self.gaia_node.parm("seed").eval()
        values["base_scale"] = self.gaia_node.parm("base_scale").eval()
        values["min_max_scale"] = [self.gaia_node.parm("min_max_scalex").eval(),
                                   self.gaia_node.parm("min_max_scaley").eval()]
        values["scale_seed"] = self.gaia_node.parm("scale_seed").eval()

        return values

class ScatterRulesWidget(QtGui.QWidget):

    def __init__(self, gaia_node=None, is_fill=False, parent=None):
        super(ScatterRulesWidget, self).__init__(parent=parent)

        main_layout = QtGui.QVBoxLayout()
        main_layout.setSpacing(5)
        main_layout.setAlignment(QtCore.Qt.AlignTop)

        self.input_geo = hou.node(gaia_node.node_path + "/INPUT_GEO").geometry()
        self.scatter = hou.node(gaia_node.node_path + "/RAW_POINTS")
        fill_node = gaia_node.node

        if is_fill:
            self.group_choices = widgets.HStringValue(label="group",
                                                      pick_list_callback=self.pick_groups,
                                                      hou_parm=self.scatter.parm("group"))
            main_layout.addWidget(self.group_choices)

            self.density_attrib = widgets.HStringValue(label="density attribute",
                                                      pick_list_callback=self.pick_point_attribs,
                                                      default=fill_node.evalParm("density_attribute"),
                                                      enable_checkbox=True,
                                                      enable=fill_node.evalParm("use_density_attribute"),
                                                      hou_checkbox=fill_node.parm("use_density_attribute"),
                                                      hou_parm=fill_node.parm("density_attribute"))
            main_layout.addWidget(self.density_attrib)
        
        # OCCLUDER
        occluder_node = hou.node(gaia_node.node_path + "/IMPORT_OCCLUDER")
        occluder_switch = hou.node(gaia_node.node_path + "/switch_use_occluder")
        
        self.mesh_occluder = widgets.HStringValue(label="Mesh Occluder",
                                                  enable_checkbox=True,
                                                  pick_list_callback=True,
                                                  default=occluder_node.evalParm("objpath1"),
                                                  hou_checkbox=occluder_switch.parm("input"),
                                                  hou_parm=occluder_node.parm("objpath1"),
                                                  enable=occluder_switch.evalParm("input"))
        self.mesh_occluder.pick = self._pick_occl
        main_layout.addWidget(self.mesh_occluder)

        main_layout.addWidget(QtGui.QLabel("Min/Max normalized values:"))

        # ALTITUDE RULE
        alti_layout = QtGui.QHBoxLayout()
        alti_layout.setContentsMargins(0,0,0,0)
        alti_layout.setSpacing(3)
        alti_layout.setAlignment(QtCore.Qt.AlignLeft)

        alti_node = hou.node(gaia_node.node_path + "/altitude")
        alti_default = [alti_node.evalParm("min"), alti_node.evalParm("max")]
        self.altitude_rule = widgets.AttribRuleWidget(label="Altitude",
                                                      default=alti_default,
                                                      rule_node=alti_node)
        alti_layout.addWidget(self.altitude_rule)

        alti_default_noise = alti_node.evalParm("noise_freq")
        self.alti_noise = widgets.HSlider(label="Noise", max=1.0,
                                          lock_min=True,
                                          default_value=alti_default_noise,
                                          hou_parm=alti_node.parm("noise_freq"),
                                          tooltip="Apply a noise on the rule")
        alti_layout.addWidget(self.alti_noise)

        main_layout.addItem(alti_layout)

        # CURVATURE RULE
        curv_layout = QtGui.QHBoxLayout()
        curv_layout.setContentsMargins(0,0,0,0)
        curv_layout.setSpacing(3)
        curv_layout.setAlignment(QtCore.Qt.AlignLeft)

        curv_node = hou.node(gaia_node.node_path + "/curvature")
        curv_default = [curv_node.evalParm("min"), curv_node.evalParm("max")]
        self.curvature_rule = widgets.AttribRuleWidget(label="Curvature",
                                                       rule_node=curv_node)
        curv_layout.addWidget(self.curvature_rule)

        curv_default_noise = curv_node.evalParm("noise_freq")
        self.curv_noise = widgets.HSlider(label="Noise", max=1.0,
                                          lock_min=True,
                                          default_value=curv_default_noise,
                                          hou_parm=curv_node.parm("noise_freq"),
                                          tooltip="Apply a noise on the rule")
        curv_layout.addWidget(self.curv_noise)

        main_layout.addItem(curv_layout)

        # SLOPE RULE
        slope_layout = QtGui.QHBoxLayout()
        slope_layout.setContentsMargins(0,0,0,0)
        slope_layout.setSpacing(3)
        slope_layout.setAlignment(QtCore.Qt.AlignLeft)

        slope_node = hou.node(gaia_node.node_path + "/slope")
        slope_default = [slope_node.evalParm("min"), slope_node.evalParm("max")]
        self.slope_rule = widgets.AttribRuleWidget(label="Slope",
                                                   default=slope_default,
                                                   rule_node=slope_node)
        slope_layout.addWidget(self.slope_rule)

        slope_default_noise = slope_node.evalParm("noise_freq")
        self.slope_noise = widgets.HSlider(label="Noise", max=1.0,
                                           lock_min=True,
                                           default_value=slope_default_noise,
                                           hou_parm=slope_node.parm("noise_freq"),
                                           tooltip="Apply a noise on the rule")
        slope_layout.addWidget(self.slope_noise)

        main_layout.addItem(slope_layout)

        # OCCLUSION RULE
        occ_layout = QtGui.QHBoxLayout()
        occ_layout.setContentsMargins(0,0,0,0)
        occ_layout.setSpacing(3)
        occ_layout.setAlignment(QtCore.Qt.AlignLeft)

        occ_node = hou.node(gaia_node.node_path + "/occlusion")
        occ_default = [occ_node.evalParm("min"), occ_node.evalParm("max")]
        self.occ_rule = widgets.AttribRuleWidget(label="Occlusion",
                                                 default=occ_default,
                                                 rule_node=occ_node)
        occ_layout.addWidget(self.occ_rule)

        occ_default_noise = occ_node.evalParm("noise_freq")
        self.occ_noise = widgets.HSlider(label="Noise", max=1.0,
                                         lock_min=True,
                                         default_value=occ_default_noise,
                                         hou_parm=occ_node.parm("noise_freq"),
                                         tooltip="Apply a noise on the rule")
        occ_layout.addWidget(self.occ_noise)

        main_layout.addItem(occ_layout)

        # reset button
        reset_btn = QtGui.QPushButton("reset")
        reset_btn.clicked.connect(self.reset)
        main_layout.addWidget(reset_btn)

        # set the final layout
        self.setLayout(main_layout)

    def _pick_occl(self):

        r = hou.ui.selectNode(node_type_filter=hou.nodeTypeFilter.Obj)
        if not r: return
        self.mesh_occluder.set_value(r)

    def reset(self):

        self.altitude_rule.set_value([0.0, 1.0])
        self.curvature_rule.set_value([0.0, 1.0])
        self.slope_rule.set_value([0.0, 1.0])
        self.occ_rule.set_value([0.0, 1.0])

        self.alti_noise.set_value(0.0)
        self.curv_noise.set_value(0.0)
        self.slope_noise.set_value(0.0)
        self.occ_noise.set_value(0.0)

    def pick_groups(self):

        return [g.name() for g in self.input_geo.primGroups()]

    def pick_point_attribs(self):

        return [a.name() for a in self.input_geo.pointAttribs()\
                if a.name() not in ["P", "Pw", "Cd"]]

class InstancesListWidget(QtGui.QWidget):

    def __init__(self, layer_infos=None, parent=None):
        super(InstancesListWidget, self).__init__(parent=parent)

        self.gaia_wac = None

        main_layout = QtGui.QHBoxLayout()
        main_layout.setAlignment(QtCore.Qt.AlignLeft)
        main_layout.setSpacing(5)

        self.add_btn = QtGui.QPushButton("")
        self.add_btn.setFixedWidth(30)
        self.add_btn.setIcon(get_icon("add"))
        self.add_btn.setSizePolicy(QtGui.QSizePolicy.Maximum,
                                   QtGui.QSizePolicy.Minimum)
        self.add_btn.clicked.connect(self.add_item)
        main_layout.addWidget(self.add_btn)

        # list layout
        self.influence_widgets = []
        self.list_layout = QtGui.QHBoxLayout()
        self.list_layout.setSpacing(10)

        self.list_widget = QtGui.QWidget()
        self.list_widget.setSizePolicy(QtGui.QSizePolicy.Maximum,
                                   QtGui.QSizePolicy.Maximum)

        self.node = layer_infos.node
        instances = self.node.parm("instances").eval()
        for i in range(instances):

            i += 1
            w = col_widgets.CollectionInstanceWidget(self.node, i, self)
            self.influence_widgets.append(w)
            self.list_layout.addWidget(w)
        
        self.list_widget.setLayout(self.list_layout)

        main_layout.addWidget(self.list_widget)

        main_layout.setAlignment(QtCore.Qt.AlignLeft)
        self.setLayout(main_layout)

    def add_item(self):
        
        hou.session.GAIA_SCATTER_COLLECTION_W = GC_ui.widgets.CollectionWidget(from_gaia_scatter=True,
                                                parent=None)
        hou.session.GAIA_SCATTER_COLLECTION_W.setStyleSheet(hou.ui.qtStyleSheet())
        hou.session.GAIA_SCATTER_COLLECTION_W.show()