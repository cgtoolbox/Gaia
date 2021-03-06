import os
import hou
import base64
import json

from PySide2 import QtWidgets
from PySide2 import QtGui
from PySide2 import QtCore

from . import strokes
reload(strokes)

from GaiaCollectionPy import ui as GC_ui
reload(GC_ui)

from GaiaCommon import nodeInfos
reload(nodeInfos)

from ...ui import widgets
reload(widgets)

from ...core import cache
reload(cache)

from ...ui import col_widgets
reload(col_widgets)

from ...icons.icon import get_icon

from GaiaCollectionPy.ui.widgets import CreateNewEntryWidget

class LayersWidget(QtWidgets.QWidget):

    def __init__(self, top_asset, parent=None):
        super(LayersWidget, self).__init__(parent=parent)

        main_layout = QtWidgets.QVBoxLayout()
        self.setProperty("houdiniStyle", True)

        self.top_asset = top_asset
        self.instance_node = hou.node(self.top_asset.path() + "/PACKED_COPIES")

        # layer infos used to fetch gaia layer node
        self.scatter_infos = nodeInfos.GaiaScatterInfos()
        p = self.parentWidget().gaia_node_path.text()
        self.scatter_infos.node_path = p
        self.scatter_infos.node = hou.node(p)
        assert self.scatter_infos.node != None, "Invalid Gaia Node"

        # tab widget
        self.layers = []
        self.tabs = QtWidgets.QTabWidget()
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

        self.add_layer_btn = QtWidgets.QPushButton(self)
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

class LayerTabWidget(QtWidgets.QWidget):

    def __init__(self, layer_infos=None, tabs_widget=None, parent=None):
        super(LayerTabWidget, self).__init__(parent=parent)
        self.setProperty("houdiniStyle", True)

        self.setObjectName("layer")
        self.layer_infos = layer_infos
        self.id = -1
        self.enabled = True
        self.tabs_widget = tabs_widget


        # layouts
        self.main_layout = QtWidgets.QVBoxLayout()
        self.main_layout.setSpacing(0)
        self.main_layout.setAlignment(QtCore.Qt.AlignTop|QtCore.Qt.AlignLeft)

        # top toolbar
        top_toolbar_layout = QtWidgets.QHBoxLayout()
        top_toolbar_layout.setSpacing(5)
        top_toolbar_layout.setAlignment(QtCore.Qt.AlignLeft)

        self.save_lay_btn = QtWidgets.QPushButton("")
        self.save_lay_btn.setIcon(get_icon("diskette"))
        self.save_lay_btn.setIconSize(QtCore.QSize(24,24))
        self.save_lay_btn.setToolTip("Save current layer to external geo file")
        self.save_lay_btn.clicked.connect(self.save)
        top_toolbar_layout.addWidget(self.save_lay_btn)

        self.infos_lay_btn = QtWidgets.QPushButton("")
        self.infos_lay_btn.setIcon(get_icon("white_list"))
        self.infos_lay_btn.setIconSize(QtCore.QSize(24,24))
        self.infos_lay_btn.setToolTip("Get informations about current layer")
        self.infos_lay_btn.clicked.connect(self.display_infos)
        top_toolbar_layout.addWidget(self.infos_lay_btn)

        self.hide_lay_btn = QtWidgets.QPushButton("")
        if self.layer_infos.node.parm("enable").eval():
            self.hide_lay_btn.setIcon(get_icon("eye_open"))
        else:
            self.hide_lay_btn.setIcon(get_icon("eye_close"))
            self.enabled = False
        self.hide_lay_btn.setIconSize(QtCore.QSize(24,24))
        self.hide_lay_btn.setToolTip("Hide / Show layer")
        self.hide_lay_btn.clicked.connect(self.switch_enable)
        top_toolbar_layout.addWidget(self.hide_lay_btn)

        self.delete_lay_btn = QtWidgets.QPushButton("")
        self.delete_lay_btn.setIcon(get_icon("close"))
        self.delete_lay_btn.setIconSize(QtCore.QSize(24,24))
        self.delete_lay_btn.setToolTip("Delete the Gaia layer")
        self.delete_lay_btn.clicked.connect(self.delete_layer)
        top_toolbar_layout.addWidget(self.delete_lay_btn)

        self.refresh_scatter_btn = QtWidgets.QPushButton("")
        self.refresh_scatter_btn.setIcon(get_icon("refresh"))
        self.refresh_scatter_btn.setIconSize(QtCore.QSize(24,24))
        self.refresh_scatter_btn.setToolTip("Refresh Gaia Scatter state")
        self.refresh_scatter_btn.clicked.connect(self.refresh_gaia_scatter)
        top_toolbar_layout.addWidget(self.refresh_scatter_btn)

        self.main_layout.addItem(top_toolbar_layout)

        # scroll layout part
        self.scroll = QtWidgets.QScrollArea()
        self.scroll.setStyleSheet("""QScrollArea{border:0px;
                                                 background-color: transparent}""")
        self.scroll.setContentsMargins(0,0,0,0)
        self.scroll.setWidgetResizable(True)
        self.scroll_widget = QtWidgets.QWidget()
        self.scroll_layout = QtWidgets.QVBoxLayout()
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
    
    def refresh_gaia_scatter(self):

        gaia_top = hou.session.MAIN_GAIA_SCATTER_CACHE.get("CURRENT_GAIA_SCATTER")
        if not gaia_top: return
        gaia_top = hou.node(gaia_top)

        data_node = gaia_top.node("PACKED_COPIES").node("DATA")
        data_node.bypass(True)
        data_node.bypass(False)
        data_node.cook(force=True)

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

        # Strokes Groups
        self.strokes_groups = strokes.StrokesWidget(self.layer_infos, paint=False,)
        self.strokes_groups_w = widgets.CollapsableWidget(label="Paint",
                                                          widget=self.strokes_groups,
                                                          collapsed=True,
                                                          parent=self)
        self.scroll_layout.addWidget(self.strokes_groups_w)

class ScatterOptionsWidget(QtWidgets.QWidget):

    def __init__(self, gaia_node=None, parent=None):
        super(ScatterOptionsWidget, self).__init__(parent=parent)
        self.setProperty("houdiniStyle", True)

        main_layout = QtWidgets.QVBoxLayout()
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

        self.radius_affects_scale = QtWidgets.QCheckBox("radius affects scale")
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

class FillScatterOptionsWidget(QtWidgets.QWidget):

    def __init__(self, gaia_node=None, parent=None):
        super(FillScatterOptionsWidget, self).__init__(parent=parent)
        self.setProperty("houdiniStyle", True)

        main_layout = QtWidgets.QVBoxLayout()
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

class ScatterRulesWidget(QtWidgets.QWidget):

    def __init__(self, gaia_node=None, is_fill=False, parent=None):
        super(ScatterRulesWidget, self).__init__(parent=parent)
        self.setProperty("houdiniStyle", True)

        main_layout = QtWidgets.QVBoxLayout()
        main_layout.setSpacing(5)
        main_layout.setAlignment(QtCore.Qt.AlignTop)

        self.gaia_node = gaia_node
        self.input_geo = gaia_node.node.node("INPUT_GEO").geometry()
        self.scatter = gaia_node.node.node("RAW_POINTS")
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
        occluder_node = gaia_node.node.node("IMPORT_OCCLUDER")
        occluder_switch = gaia_node.node.node("switch_use_occluder")
        
        self.mesh_occluder = widgets.HStringValue(label="Mesh Occluder",
                                                  enable_checkbox=True,
                                                  pick_list_callback=True,
                                                  default=occluder_node.evalParm("objpath1"),
                                                  hou_checkbox=occluder_switch.parm("input"),
                                                  hou_parm=occluder_node.parm("objpath1"),
                                                  enable=occluder_switch.evalParm("input"))
        self.mesh_occluder.pick = self._pick_occl
        main_layout.addWidget(self.mesh_occluder)

        # EXCLUDE LAYER
        exclude_layer_node = gaia_node.node.node("EXCLUDE_LAYERS")
        self.exclude_layer = LayerExcludeWidget(exclude_layer_node, self)
        main_layout.addWidget(self.exclude_layer)

        # BASIC RULES
        main_layout.addWidget(QtWidgets.QLabel("Min/Max normalized values:"))

        # Attributes remap
        self.attr_remap_node = gaia_node.node.node("attr_remap_sub").node("attributes_remap")

        attr_remap_layout = QtWidgets.QHBoxLayout()
        attr_remap_layout.setSpacing(5)
        attr_remap_layout.setAlignment(QtCore.Qt.AlignLeft)
        attr_remap_check = widgets.HLabeledCheckbox("Attribute remap",
                                                    default_state=self.attr_remap_node.evalParm("enable"))
        attr_remap_check.clicked.connect(lambda: self.attr_remap_node.parm("enable").set(attr_remap_check.isChecked()))
        attr_remap_layout.addWidget(attr_remap_check)

        self.switch_attr_remap_btn = QtWidgets.QPushButton("")
        self.switch_attr_remap_btn.setCheckable(True)
        self.switch_attr_remap_btn.setChecked(False)
        self.switch_attr_remap_btn.setIcon(get_icon("wave_amplify_amplitude"))
        self.switch_attr_remap_btn.setToolTip("Go to remap attribute node")
        self.switch_attr_remap_btn.clicked.connect(self.swtich_attrib_remap)
        attr_remap_layout.addWidget(self.switch_attr_remap_btn)

        main_layout.addItem(attr_remap_layout)

        # ALTITUDE RULE
        alti_layout = QtWidgets.QHBoxLayout()
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
        curv_layout = QtWidgets.QHBoxLayout()
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
        slope_layout = QtWidgets.QHBoxLayout()
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
        occ_layout = QtWidgets.QHBoxLayout()
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
        reset_btn = QtWidgets.QPushButton("reset")
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

    def swtich_attrib_remap(self):

        if self.switch_attr_remap_btn.isChecked():
            self.attr_remap_node.setCurrent(True, True)
            self.attr_remap_node.setDisplayFlag(True)
            self.attr_remap_node.setRenderFlag(True)
            self.attr_remap_node.setSelected(True)

        else:
            self.gaia_node.node.node("OUT").setDisplayFlag(True)
            self.gaia_node.node.node("OUT").setRenderFlag(True)
            self.gaia_node.node.parent().parent().setCurrent(True, True)
            self.gaia_node.node.parent().parent().setSelected(True)

class LayerExcludeWidget(QtWidgets.QWidget):
    """ Exclude given layer(s) from current layer according to a radius
    """
    def __init__(self, exclude_layer_node=None, parent=None):
        super(LayerExcludeWidget, self).__init__(parent=parent)
        self.setProperty("houdiniStyle", True)

        self.setContentsMargins(0,0,0,0)

        self.top_w = parent

        self.exclude_layer_node = exclude_layer_node
        self.cur_layer = self.exclude_layer_node.parent()
        self.LAYERS = self.cur_layer.parent()

        self.widgets = []
        self.layer_widgets = []

        main_layout = QtWidgets.QVBoxLayout()
        main_layout.setAlignment(QtCore.Qt.AlignTop)

        d = self.exclude_layer_node.parm("enable").eval()
        self.enable_exclude = widgets.HLabeledCheckbox("Layers Exclusion", d)
        self.enable_exclude.clicked.connect(self.enable_widget)
        main_layout.addWidget(self.enable_exclude)

        toolbar_layout = QtWidgets.QHBoxLayout()
        self.add_layer_btn = QtWidgets.QPushButton("Add Layer")
        self.add_layer_btn.setIcon(get_icon("add"))
        self.add_layer_btn.clicked.connect(self.add_layer)
        self.widgets.append(self.add_layer_btn)
        toolbar_layout.addWidget(self.add_layer_btn)

        self.clear_layers_btn = QtWidgets.QPushButton("Clear All Layers")
        self.clear_layers_btn.setIcon(get_icon("close"))
        self.clear_layers_btn.clicked.connect(self.clear_layers)
        self.widgets.append(self.clear_layers_btn)
        toolbar_layout.addWidget(self.clear_layers_btn)
        
        main_layout.addLayout(toolbar_layout)

        self.scroll_layout = QtWidgets.QVBoxLayout()
        self.scroll_w = QtWidgets.QWidget()
        self.scroll_w.setLayout(self.scroll_layout)
        self.scroll_area = QtWidgets.QScrollArea()
        self.scroll_area.setStyleSheet("""QScrollArea{background-color:#2d3c5f}""")
        self.scroll_area.setWidgetResizable(True)
        self.scroll_area.setWidget(self.scroll_w)
        self.scroll_area.setSizePolicy(QtWidgets.QSizePolicy.Minimum, QtWidgets.QSizePolicy.Minimum)
        main_layout.addWidget(self.scroll_area)

        main_layout.setContentsMargins(0,0,0,0)
        self.setLayout(main_layout)

        self.setSizePolicy(QtWidgets.QSizePolicy.Minimum, QtWidgets.QSizePolicy.Minimum)

        self.init_widgets()

    def add_layer(self):

        w = _LayerExcludeElement(parent=self)
        self.scroll_layout.addWidget(w)
        self.widgets.append(w)
        self.layer_widgets.append(w)
        layers = [ v for v in self.exclude_layer_node.evalParm("layer_list").split(' ') if v]
        self.refresh_layer_imports(layers)

    def init_widgets(self):

        layers = [ v for v in self.exclude_layer_node.evalParm("layer_list").split(' ') if v]

        for layer in layers:

            if not layer: continue
            if not self.LAYERS.node(layer): continue

            w = _LayerExcludeElement(layer, parent=self)
            p = self.exclude_layer_node.node("import_layer_" + layer).parm("radius")
            w.radius_w.hou_parm = p
            w.radius_w.set_value(p.eval())
            self.scroll_layout.addWidget(w)
            self.widgets.append(w)
            self.layer_widgets.append(w)

        self.refresh_layer_imports(layers)
        self.enable_widget()

    def refresh_layer_imports(self, layer_names):
        
        checked_names = []
        invalid_names = []

        for s in layer_names:

            if not s: continue

            node = self.LAYERS.node(s)
            if not node:
                invalid_names.append(s)
                continue

            # create the object merge to import layer, if it doesn't exists
            import_layer = self.exclude_layer_node.node("import_layer_" + s)
            merge_layers = self.exclude_layer_node.node("MERGE_LAYERS")
            if not import_layer:
                n = "import_layer_" + s
                import_layer = self.exclude_layer_node.createNode("Gaia_Import_Exclude_Layer", n)
                import_layer.parm("path").set(self.LAYERS.node(s).path() + "/OUT")
                
                merge_layers.setInput(len(merge_layers.inputs()), import_layer)

            checked_names.append(s)

        self.exclude_layer_node.parm("layer_list").set(' '.join(checked_names))

        # delete missing layers
        for s in invalid_names:
            n_todel = self.LAYERS.node("import_layer_" + s)
            if n_todel:
                n_todel.destroy()

        # delete left over nodes if any
        for n in [n for n in self.exclude_layer_node.children() if \
                  n.type().name() == "Gaia_Import_Exclude_Layer"]:
            n_name = n.name()
            if n_name.replace("import_layer_", '') not in layer_names:
                n.destroy()

        self.exclude_layer_node.layoutChildren()

    def delete_w(self, w):

        w.setParent(None)
        self.scroll_layout.removeWidget(w)
        w.deleteLater()

        if w in self.widgets:
            self.widgets.remove(w)

        if w in self.layer_widgets:
            self.layer_widgets.remove(w)

    def clear_layers(self):

        if not self.layer_widgets: return

        r = hou.ui.displayMessage("Delete all layer exclusion ?",
                                    buttons=["Ok", "Cancel"], help="This can't be undo !")
        if r == 1: return

        for w in self.layer_widgets[::-1]:
            w.delete(show_ui=False)

    def fetch_layers(self):

        layers = [layer for layer in self.LAYERS.children() if \
                  layer.name() not in ["Layer_dummy", self.cur_layer.name()]]

        return [layer.name() for layer in layers]

    def enable_widget(self):

        state = self.enable_exclude.isChecked()
        for w in self.widgets:
            w.setEnabled(state)

        self.exclude_layer_node.parm("enable").set(state)

        if state:
            self.scroll_area.setStyleSheet("""QScrollArea{background-color:#2d3c5f}""")
        else:
            self.scroll_area.setStyleSheet("""QScrollArea{background-color:#505562}""")
        
class _LayerExcludeElement(QtWidgets.QWidget):

    def __init__(self, default="", visible=True, parent=None):
        super(_LayerExcludeElement, self).__init__(parent=parent)
        self.setProperty("houdiniStyle", True)

        self.top_w = parent
        self.visible = visible

        main_layout = QtWidgets.QHBoxLayout()
        main_layout.setAlignment(QtCore.Qt.AlignLeft)
        hou_parm = self.top_w.exclude_layer_node.parm("layer_list")

        self.layer_to_exclude = widgets.HStringValue(label="Layer",
                                                     default=default, append_value=True,
                                                     hou_parm=hou_parm, read_only=True,
                                                     pick_list_callback=self.top_w.fetch_layers)
        self.layer_to_exclude.setToolTip("Layer you want to exclude from current scattering layer. (Use button to change the value)")
        self.layer_to_exclude.lbl.setStyleSheet("QLabel{background: transparent}")
        self.layer_to_exclude.value_changed.connect(self.refresh_layer_imports)
        main_layout.addWidget(self.layer_to_exclude)

        self.radius_w = widgets.HSlider(label="Radius", default_value=2.0)
        self.radius_w.lbl.setStyleSheet("QLabel{background: transparent}")
        main_layout.addWidget(self.radius_w)

        self.hide_btn = QtWidgets.QPushButton("")
        self.hide_btn.setFixedSize(QtCore.QSize(28, 28))
        self.hide_btn.setIconSize(QtCore.QSize(24, 24))
        self.hide_btn.clicked.connect(self.switch_visible)
        if self.visible:
            self.hide_btn.setIcon(get_icon("eye_open"))
        else:
            self.hide_btn.setIcon(get_icon("eye_close"))
        main_layout.addWidget(self.hide_btn)

        self.delete_btn = QtWidgets.QPushButton()
        self.delete_btn.setFixedSize(QtCore.QSize(28, 28))
        self.delete_btn.setIconSize(QtCore.QSize(24, 24))
        self.delete_btn.setIcon(get_icon("close"))
        self.delete_btn.clicked.connect(self.delete)
        main_layout.addWidget(self.delete_btn)

        main_layout.setContentsMargins(1,1,1,1)
        self.setLayout(main_layout)

    def update_hou_parm(self, layer):

        hou_parm = self.top_w.exclude_layer_node.node("import_layer_" + layer).parm("radius")
        self.radius_w.hou_parm = hou_parm

    def delete(self, show_ui=True):

        if show_ui:
            r = hou.ui.displayMessage("Delete layer exclusion: " + self.layer_to_exclude.text() + " ?",
                                      buttons=["Ok", "Cancel"], help="This can't be undo !")
            if r == 1: return

        _node_name = self.layer_to_exclude.text()
        node_name = "import_layer_" + _node_name
        imp_node = self.top_w.exclude_layer_node.node(node_name)
        if imp_node:
            imp_node.destroy()

        cur_layers = self.top_w.exclude_layer_node.evalParm("layer_list").split(' ')
        if _node_name in cur_layers:
            cur_layers.remove(_node_name)

        self.top_w.exclude_layer_node.parm("layer_list").set(' '.join(cur_layers))

        self.top_w.delete_w(self)

    def switch_visible(self):

        node_name = "import_layer_" + self.layer_to_exclude.text()
        imp_node = self.top_w.exclude_layer_node.node(node_name)
        if not imp_node: return

        if self.visible:
            self.hide_btn.setIcon(get_icon("eye_close"))
            imp_node.parm("enable").set(False)
            self.layer_to_exclude.setEnabled(False)
            self.radius_w.setEnabled(False)
            self.visible = False
        else:
            self.hide_btn.setIcon(get_icon("eye_open"))
            imp_node.parm("enable").set(True)
            self.layer_to_exclude.setEnabled(True)
            self.radius_w.setEnabled(True)
            self.visible = True

    def refresh_layer_imports(self, value):

        layer_names = self.top_w.exclude_layer_node.evalParm("layer_list").split(' ')
        layer_names = list(set(layer_names))
        self.top_w.refresh_layer_imports(layer_names)

        #TODO: clean
        v = value.split(' ')[-1].replace(' ', '')
        self.update_hou_parm(v)

class InstancesListWidget(QtWidgets.QWidget):

    def __init__(self, layer_infos=None, parent=None):
        super(InstancesListWidget, self).__init__(parent=parent)
        self.setProperty("houdiniStyle", True)

        self.gaia_wac = None

        main_layout = QtWidgets.QVBoxLayout()
        main_layout.setAlignment(QtCore.Qt.AlignLeft)
        main_layout.setSpacing(5)

        self.add_btn = QtWidgets.QPushButton("")
        self.add_btn.setIcon(get_icon("add"))
        self.add_btn.clicked.connect(self.add_item)
        main_layout.addWidget(self.add_btn)

        # list layout
        self.node = hou.node(layer_infos.node.path())
        self.list_widget = InstanceItemsContainer(node=self.node,
                                                  parent=self)
        main_layout.addWidget(self.list_widget)

        # read instances
        instances = self.node.parm("instances").eval()
        instances_metadata = []
        for i in range(instances):
            try:
                i = str(i + 1)
                uid = self.node.evalParm("asset_uid_" + i)
                asset_category = self.node.evalParm("category_" + i)
                asset_path = self.node.evalParm("path_" + i)
                root = self.node.evalParm("collection_root_" + i).replace('\\', '/')
                metadata_name = asset_path.split('/')[-1].replace('_' + uid, "") + ".json"
                metadata_path = root + asset_category + '/' + metadata_name
                with open(metadata_path, 'r') as f:
                    metadata = json.load(f)

                metadata["collection_root"] = root
                instances_metadata.append(metadata)
                
            except hou.OperationFailed:
                print("Error reading instance data {}: {}".format(self.node.path(), i))
            except IOError:
                print("Error can't read instance data {}: {}".format(self.node.path(), i))

        if instances_metadata:
            self.init_collection_grid_items(instances_metadata)
            
        main_layout.setAlignment(QtCore.Qt.AlignLeft)
        self.setLayout(main_layout)

    def add_item(self):
        
        hou.session.GAIA_SCATTER_COLLECTION_W = GC_ui.widgets.CollectionWidget(from_gaia_scatter=True,
                                                parent=None)
        hou.session.GAIA_SCATTER_COLLECTION_W.setStyleSheet(hou.ui.qtStyleSheet())
        hou.session.GAIA_SCATTER_COLLECTION_W.show()

    def init_collection_grid_items(self, metadata_list):

        self.list_widget.init_grid_items(metadata_list)

    def append_item(self, metadata):

        self.list_widget.append_item(metadata)

class InstanceItemsContainer(QtWidgets.QFrame):

    def __init__(self, node=None, parent=None):
        super(InstanceItemsContainer, self).__init__(parent=parent)
        self.setProperty("houdiniStyle", True)

        self.influence_widgets = []
        self.assets_uids = []
        self.n_items = 0
        self.node = node

        self.top_w = parent
        self.setAcceptDrops(True)
        self.setMinimumHeight(85)
        self.setSizePolicy(QtWidgets.QSizePolicy.Minimum,
                           QtWidgets.QSizePolicy.Minimum)

        main_layout = QtWidgets.QVBoxLayout()
        main_layout.setAlignment(QtCore.Qt.AlignTop)
        self.nitems_lbl = QtWidgets.QLabel("0 Item(s)")
        main_layout.addWidget(self.nitems_lbl)

        self.scroll_w = QtWidgets.QWidget()
        self.grid_layout = QtWidgets.QGridLayout()
        self.scroll_w.setLayout(self.grid_layout)
        self.scroll_area = QtWidgets.QScrollArea()
        self.scroll_area.setWidgetResizable(True)
        self.scroll_area.setWidget(self.scroll_w)

        main_layout.addWidget(self.scroll_area)
        self.setLayout(main_layout)

    def init_grid_items(self, metadata_list):

        for i, metadata in enumerate(metadata_list):
            i += 1

            w = self.create_collection_grid_item(metadata, i, set_instances_parm=False)
            self.place_collection_item(w)

    def append_item(self, metadata):
        """ Append item to grif of items, when the grid is init and existing items are
            read, set_instance_parm must be set to False as the instances parms is already set
        """

        uid = metadata["uid"]
        _name = metadata["name"]
        if uid in self.assets_uids:
            hou.ui.displayMessage("Asset: {} already used in this layer".format(_name))
            return None

        new_idx = self.node.evalParm("instances") + 1
        self.node.parm("instances").set(new_idx)

        w = self.create_collection_grid_item(metadata, new_idx)
        if not w: return

        self.place_collection_item(w)

    def place_collection_item(self, collection_item):
        """ Place a collection grid item into the grid
        """
        if not collection_item: return
        idx = collection_item.idx - 1
        col = idx % 4
        row = idx / 4

        self.grid_layout.addWidget(collection_item, row, col)
        self.influence_widgets.append(collection_item)
        self.assets_uids.append(collection_item.uid)
        self.grid_layout.update()
        self.nitems_lbl.setText("{} Item(s)".format(self.node.evalParm("instances")))


    def create_collection_grid_item(self, metadata, idx, set_instances_parm=True):
        """ set_instances_parm set to False when items are added from grid init
            as parms are just read and not created.
        """
        
        item_inf = nodeInfos.CollectionItemInfos()

        uid = metadata["uid"]
        _name = metadata["name"]
        comment = metadata["comment"]
        category = metadata["category"]
        format = metadata["format"]
        _path = metadata["path"].replace('\\', '/')
        _path = _path.replace("%ROOT%", metadata["collection_root"])
        _path = _path.replace('\\', '/') + '/'
        _path += _name + '.' + format

        # append item to collection subnet
        collection_sub = cache.get("CURRENT_GAIA_SCATTER_COLLECTION")
        col_item = collection_sub.node(_name + '_' + uid)
        if not col_item:
            col_item = collection_sub.createNode("geo", _name + '_' + uid)
            col_item.setComment("Collection item, file: " + _path)
            _file = col_item.node("file1")
            _file.setName("import_file")
            _file.parm("file").set(_path)
            _file.parm("loadtype").set(4)
            _file.parm("viewportlod").set(0)
            output = col_item.createNode("output", "OUT_" + _name)

            null = col_item.createNode("null", "NONE")  # used to hide the object

            switch = col_item.createNode("switch", "show_object")
            switch.setInput(0, null)
            switch.setInput(1, _file)
            switch.parm("input").set(1)

            output.setInput(0, switch)
            output.setDisplayFlag(True)
            output.setRenderFlag(True)
            col_item.layoutChildren()

        # display state of collection item
        item_inf.visible = col_item.node("show_object").evalParm("input")
        item_inf.display_mode = col_item.node("import_file").evalParm("viewportlod")

        collection_sub.layoutChildren()

        thumbnail_binary = base64.decodestring(metadata["thumbnail"])
        tooltip = ("Asset name: {}\n"
                   "Category: {}\n"
                   "Format: {}\n"
                   "Path: {}\n"
                   "Comment: {}".format(_name, category, format, _path, comment))

        item_inf.asset_path = col_item.path()
        item_inf.category = category
        item_inf.comment = comment
        item_inf.uid = uid
        item_inf.tooltip = tooltip
        item_inf.idx = idx
        item_inf.collection_root = metadata["collection_root"]
        item_inf.thumbnail_binary = thumbnail_binary

        w = col_widgets.CollectionInstanceWidget(layer_node=self.node, item_infos=item_inf,
                                                 set_parms=set_instances_parm,
                                                 parent=self)

        return w
        

    def remove_item(self, w):
        """ Remove item from the grid, called from items
        """

        if w.uid in self.assets_uids:
            self.assets_uids.pop(self.assets_uids.index(w.uid))

        if w in self.influence_widgets:
            self.influence_widgets.pop(self.influence_widgets.index(w))

        self.grid_layout.removeWidget(w)
        w.setParent(None)
        w.deleteLater()

        # update idx
        for i, w in enumerate(self.influence_widgets):
            w.idx = i + 1

        # reorder widgets
        for w in self.influence_widgets:
            self.grid_layout.removeWidget(w)

        for i, w in enumerate(self.influence_widgets):
                
                col = i % 4
                row = i / 4
                self.grid_layout.addWidget(w, row, col)



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