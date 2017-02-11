import hou

from PySide import QtGui
from PySide import QtCore

from GaiaCommon import h_widgets

from ...icons.icon import get_icon

from ...ui import widgets
reload(widgets)

from ...core import paint
reload(paint)

PAINTMODES = paint.PAINTMODES

class StrokesWidget(QtGui.QWidget):
    """ Bottom part
    """
    def __init__(self, layer_infos=None, paint=True, scale=True, eraser=True, parent=None):
        super(StrokesWidget, self).__init__(parent=parent)

        self.layer_infos = layer_infos

        main_layout = QtGui.QVBoxLayout()
        main_layout.setSpacing(5)
        main_layout.setAlignment(QtCore.Qt.AlignLeft)

        # buttons displayed
        self.paint_displayed = paint
        self.eraser_displayed = eraser
        self.scale_displayed = scale
        
        # toolbar (paint mode buttons)
        toolbar_layout = QtGui.QHBoxLayout()
        toolbar_layout.setSpacing(5)
        toolbar_layout.setAlignment(QtCore.Qt.AlignLeft)

        if self.paint_displayed:
            self.paint_stroke_btn = QtGui.QPushButton("")
            self.paint_stroke_btn.setCheckable(True)
            self.paint_stroke_btn.setIcon(get_icon("brush"))
            self.paint_stroke_btn.setToolTip("Paint instances")
            self.paint_stroke_btn.setIconSize(QtCore.QSize(20, 20))
            self.paint_stroke_btn.clicked.connect(self.paint_state)
            toolbar_layout.addWidget(self.paint_stroke_btn)

        if self.eraser_displayed :
            self.eraser_stroke_btn = QtGui.QPushButton("")
            self.eraser_stroke_btn.setCheckable(True)
            self.eraser_stroke_btn.setIcon(get_icon("eraser"))
            self.eraser_stroke_btn.setToolTip("Erase instances")
            self.eraser_stroke_btn.setIconSize(QtCore.QSize(20, 20))
            self.eraser_stroke_btn.clicked.connect(self.eraser_state)
            toolbar_layout.addWidget(self.eraser_stroke_btn)

        if self.scale_displayed:
            self.scale_stroke_btn = QtGui.QPushButton("")
            self.scale_stroke_btn.setCheckable(True)
            self.scale_stroke_btn.setIcon(get_icon("paint_scale"))
            self.scale_stroke_btn.setToolTip("Pain instances scale")
            self.scale_stroke_btn.setIconSize(QtCore.QSize(20, 20))
            self.scale_stroke_btn.clicked.connect(self.scale_state)
            toolbar_layout.addWidget(self.scale_stroke_btn)

            # scale value widget
            self.painted_scale_value = h_widgets.HSlider(label="Scale Value:", default_value=0.5,
                                                         tooltip="Painted scale multiplier applied")
            self.painted_scale_value.setVisible(False)
            toolbar_layout.addWidget(self.painted_scale_value)

        main_layout.addItem(toolbar_layout)

        # strokes list
        self.strokes_list = StrokesList(self.layer_infos.node, self)
        main_layout.addWidget(self.strokes_list)

        self.setLayout(main_layout)

    def paint_state(self):
        
        if self.paint_stroke_btn.isChecked():

            if self.eraser_displayed:
                self.eraser_stroke_btn.setEnabled(False)

            if self.scale_displayed:
                self.scale_stroke_btn.setEnabled(False)
                self.painted_scale_value.setVisible(False)

            node = paint.enter_paint_mode(PAINTMODES.PAINT,
                                          self.layer_infos.node)
            self.strokes_list.add_stroke("painter", node)

        else:
            if self.eraser_displayed:
                self.eraser_stroke_btn.setEnabled(True)

            if self.scale_displayed:
                self.scale_stroke_btn.setEnabled(True)
                self.painted_scale_value.setVisible(False)

            paint.exit_paint_mode()

    def eraser_state(self):

        if self.eraser_stroke_btn.isChecked():

            if self.paint_displayed:
                self.paint_stroke_btn.setEnabled(False)

            if self.scale_displayed:
                self.scale_stroke_btn.setEnabled(False)
                self.painted_scale_value.setVisible(False)

            node = paint.enter_paint_mode(PAINTMODES.ERASE,
                                          self.layer_infos.node)

            self.strokes_list.add_stroke("eraser", node)

        else:
            if self.paint_displayed:
                self.paint_stroke_btn.setEnabled(True)

            if self.scale_displayed:
                self.scale_stroke_btn.setEnabled(True)
                self.painted_scale_value.setVisible(False)

            paint.exit_paint_mode()

    def scale_state(self):

        if self.scale_stroke_btn.isChecked():

            self.painted_scale_value.setVisible(True)

            if self.paint_displayed:
                self.paint_stroke_btn.setEnabled(False)

            if self.eraser_displayed:
                self.eraser_stroke_btn.setEnabled(False)

            node = paint.enter_paint_mode(PAINTMODES.SCALE,
                                          self.layer_infos.node)
            self.painted_scale_value.hou_parm = node.parm("scale")
            self.strokes_list.add_stroke("scale", node)

        else:

            self.painted_scale_value.setVisible(False)

            if self.paint_displayed:
                self.paint_stroke_btn.setEnabled(True)

            if self.eraser_displayed:
                self.eraser_stroke_btn.setEnabled(True)

            self.painted_scale_value.hou_parm = None
            paint.exit_paint_mode()


class StrokesList(QtGui.QWidget):
    """ Widget which will store strokes group widget (created when the user enter
        in a paint mode).
    """
    def __init__(self, gaia_layer_node=None, parent=None):
        super(StrokesList, self).__init__(parent=parent)

        main_layout = QtGui.QVBoxLayout()

        self.strokes = []
        self.gaia_layer_node = gaia_layer_node

        scroll = QtGui.QScrollArea()
        scroll.setStyleSheet("""QScrollArea{border:0px}""")
        scroll.setContentsMargins(0,0,0,0)
        scroll.setWidgetResizable(True)
        scroll_widget = QtGui.QWidget()
        self.scroll_layout = QtGui.QVBoxLayout()
        self.scroll_layout.setAlignment(QtCore.Qt.AlignTop)
        self.scroll_layout.setContentsMargins(3,3,3,3)

        scroll_widget.setLayout(self.scroll_layout)
        scroll.setWidget(scroll_widget)

        self._init_list()

        main_layout.addWidget(scroll)
        self.setLayout(main_layout)

    def _init_list(self):
        """ Init stroke group list according to given Gaia layer nodes subnodes
        """
        
        painters_container = self.gaia_layer_node.path() + "/PAINTERS"
        painters_container = hou.node(painters_container)
        if painters_container:
            painters = [n for n in painters_container.children() \
                        if n.name().startswith("painter_")]
        else:
            painters = []

        erasers_container = self.gaia_layer_node.path() + "/ERASERS"
        erasers_container = hou.node(erasers_container)
        if erasers_container:
            erasers = [n for n in erasers_container.children() \
                       if n.name().startswith("eraser_")]
        else:
            erasers = []

        scales_container = self.gaia_layer_node.path() + "/SCALE_PAINTER"
        scales_container = hou.node(scales_container)
        if scales_container:
            scales = [n for n in scales_container.children() \
                      if n.name().startswith("scale_")]
        else:
            scales = []

        nodes = painters + erasers + scales

        nodes = sorted(nodes, key=lambda n: float(n.userData("time_stamp")))
        for n in nodes:
            self.add_stroke(n.name().split('_')[0], n)

    def add_stroke(self, stroke_type="painter",
                   stroke_node=None):
        
        if stroke_type == "painter":
            w = PaintStroke(strokes_list=self)

        if stroke_type == "eraser":
            w = EraserStroke(strokes_list=self)

        if stroke_type == "scale":
            w = ScaleStroke(strokes_list=self)
        
        w.stroke_grp_node = stroke_node
        w.id = len(self.strokes)
        self.scroll_layout.insertWidget(0, w)
        self.strokes.append(w)

    def remove_stroke(self, stroke_id):

        w = self.strokes.pop(stroke_id)
        for i, s in enumerate(self.strokes):
            s.id = i

        for i, s in enumerate(self.strokes):
            try:
                s.stroke_grp_node.setName(s.type + "_" + str(i+1))
            except hou.OperationFailed:
                pass

        w.setParent(None)
        w.deleteLater()

class _BaseStroke(QtGui.QWidget):

    def __init__(self, strokes_list=None, parent=None):
        super(_BaseStroke, self).__init__(parent=parent)

        self.strokes_list = strokes_list
        self.stroke_grp_node = None
        self.enabled = True
        self.id = -1

        self.set_type()

        self.setObjectName("paint_stroke")
        main_layout = QtGui.QHBoxLayout()
        main_layout.setSpacing(10)
        main_layout.setAlignment(QtCore.Qt.AlignTop)
        self.setFixedHeight(40)

        self.setAutoFillBackground(True)
        
        p = self.palette()
        p.setColor(self.backgroundRole(), self.bg_color)
        self.setPalette(p)

        self.lbl_ico = QtGui.QLabel("")
        self.lbl_ico.setFixedHeight(22)
        self.lbl_ico.setFixedWidth(22)
        self.lbl_ico.setPixmap(get_icon(self.icon_name).pixmap(22, 22))
        self.lbl_ico.setStyleSheet("QLabel{background:transparent;}")
        main_layout.addWidget(self.lbl_ico)

        lbl = QtGui.QLabel(self.lbl_value)
        lbl.setStyleSheet("QLabel{background:transparent;}")
        main_layout.addWidget(lbl)
        
        self.hide_stroke_btn = QtGui.QPushButton("")
        self.hide_stroke_btn.setIcon(get_icon("eye_open"))
        self.hide_stroke_btn.setToolTip("Hide / Show strokes group")
        self.hide_stroke_btn.setIconSize(QtCore.QSize(18, 18))
        self.hide_stroke_btn.setFixedWidth(22)
        self.hide_stroke_btn.setFixedHeight(22)
        self.hide_stroke_btn.clicked.connect(self.switch_enable)
        main_layout.addWidget(self.hide_stroke_btn)

        self.delete_stroke_btn = QtGui.QPushButton("")
        self.delete_stroke_btn.setIcon(get_icon("trash_can"))
        self.delete_stroke_btn.setToolTip("Delete strokes group")
        self.delete_stroke_btn.setIconSize(QtCore.QSize(18, 18))
        self.delete_stroke_btn.setFixedWidth(22)
        self.delete_stroke_btn.setFixedHeight(22)
        self.delete_stroke_btn.clicked.connect(self.remove_node)
        main_layout.addWidget(self.delete_stroke_btn)

        self.setLayout(main_layout)

    def set_type(self):

        self.lbl_value = "Paint Strokes Group"
        self.icon_name = "brush"
        self.type = "painter"
        self.bg_color = QtGui.QColor(20, 125, 20, 128)

    def switch_enable(self):

        if self.enabled:
            self.hide_stroke_btn.setIcon(get_icon("eye_close"))
            self.enabled = False
            self.stroke_grp_node.parm("enable").set(0)
            self.lbl_ico.setEnabled(False)
            p = self.palette()
            p.setColor(self.backgroundRole(), QtGui.QColor(80, 80, 80, 128))
            self.setPalette(p)
        else:
            self.hide_stroke_btn.setIcon(get_icon("eye_open"))
            self.enabled = True
            self.stroke_grp_node.parm("enable").set(1)
            self.lbl_ico.setEnabled(True)
            p = self.palette()
            p.setColor(self.backgroundRole(), self.bg_color)
            self.setPalette(p)

    def remove_node(self):

        r = hou.ui.displayMessage("Delete the stroke group ? ({})".format(self.type),
                                  help="This can't be undo !",
                                  title="Confirm",
                                  buttons=["Ok", "Cancel"],
                                  severity=hou.severityType.Warning)
        if r == 1: return

        c = self.stroke_grp_node.outputConnections()[0]
        output_node = self.stroke_grp_node.outputs()[0]
        idx = c.inputIndex()
        output_node.setInput(idx, None)
        self.stroke_grp_node.destroy()

        self.strokes_list.remove_stroke(self.id)

class PaintStroke(_BaseStroke):

    def __init__(self, strokes_list=None, parent=None):

        super(PaintStroke, self).__init__(strokes_list=strokes_list,
                                          parent=parent)

class EraserStroke(_BaseStroke):

    def __init__(self, strokes_list=None, parent=None):
        super(EraserStroke, self).__init__(strokes_list=strokes_list,
                                           parent=parent)
        
    def set_type(self):

        self.lbl_value = "Eraser Strokes Group"
        self.icon_name = "eraser"
        self.type = "eraser"
        self.bg_color = QtGui.QColor(125, 20, 20, 128)

class ScaleStroke(_BaseStroke):

    def __init__(self, strokes_list=None, parent=None):
        super(ScaleStroke, self).__init__(strokes_list=strokes_list,
                                          parent=parent)

        self.setObjectName("scale_stroke")

    def set_type(self):

        self.lbl_value = "Scale Strokes Group"
        self.icon_name = "paint_scale"
        self.type = "scale"
        self.bg_color = QtGui.QColor(20, 20, 125, 128)