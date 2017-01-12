import hou
import toolutils

from functools import partial

from PySide import QtGui
from PySide import QtCore

from ..icons.icon import get_icon

class HSlider(QtGui.QWidget):
    """ Custom widget which emulates the houdini float and int slider parameter.
        Can be either a float or an int slider. Has slider and numeric text fields.
        
        label:            the label displayed on the left of the widget (str)
        _type:            either "int" or "float" (str)
        default_value:    the default slider and numeric field value (float or int )
        min:              the min value of the slider (float or int)
        max:              the max value of the slider (float or int)
        lock_min:         clamp the entered value to the min slider value (bool)
        lock_max:         clamp the entered value to the max slider value (bool)
        enable_checkbox:  add a enable toggle checkbox (bool)
        enable:           enable / disable widget (bool)
        tooltip:          the tooltip of the slider (str)
        hou_parm:         the houdini parameter affected by the slider, must be same type.

        call value() to get the current value of the slider (return int or float).
    """
    def __init__(self, label="", _type="float", default_value=0.0,
                 min=0.0, max=10.0, lock_min=True, lock_max=False,
                 enable_checkbox=False, enable=True,
                 tooltip="", hou_parm=None, hou_checkbox=None, parent=None):
        super(HSlider, self).__init__(parent=parent)
        
        self.hou_parm = hou_parm
        self.hou_checkbox = hou_checkbox
        
        if default_value > max and lock_max:
            default_value = max
        if default_value < min and lock_min:
            default_value = min

        if _type == "int":
            default_value = int(default_value)
        else:
            default_value = float(default_value)

        self._type = _type
        self._numeric_val = default_value

        self.lock_min = lock_min
        self.lock_max = lock_max

        layout = QtGui.QHBoxLayout()
        layout.setSpacing(5)
        layout.setAlignment(QtCore.Qt.AlignLeft)

        if enable_checkbox:
            self.enable_checkbox = QtGui.QCheckBox(self)
            self.enable_checkbox.setChecked(enable)
            self.enable_checkbox.clicked.connect(self._checkbox_sgn)
            layout.addWidget(self.enable_checkbox)

        self.lbl = QtGui.QLabel(label + "  ")
        self.lbl.setAlignment(QtCore.Qt.AlignRight|QtCore.Qt.AlignVCenter)
        self.lbl.setEnabled(enable)
        layout.addWidget(self.lbl)
        
        self.numeric = QtGui.QLineEdit(self)
        self.numeric.setEnabled(enable)
        self.numeric.setText(str(default_value))
        self.numeric.returnPressed.connect(self._validate_numeric)
        self.numeric.setFixedWidth(50)
        layout.addWidget(self.numeric)

        self.slider = QtGui.QSlider(self)
        self.slider.wheelEvent = self._wheel
        self.slider.setEnabled(enable)
        self.slider.setOrientation(QtCore.Qt.Horizontal)
        if self._type == "int":
            self.numeric.setValidator(QtGui.QIntValidator())
            self.slider.setRange(min, max)
            self.slider.setValue(default_value)
        else:
            self.numeric.setValidator(QtGui.QDoubleValidator())
            self.slider.setRange(min * 100.0, max * 100.0)
            self.slider.setValue(default_value * 100.0)

        self.slider.valueChanged.connect(self._update_from_slider)
        layout.addWidget(self.slider)

        self.setToolTip(tooltip)
        self.setSizePolicy(QtGui.QSizePolicy.Minimum,
                           QtGui.QSizePolicy.Maximum)
        layout.setContentsMargins(0,0,0,0)
        self.setLayout(layout)
        self.setContentsMargins(0,0,0,0)

    def _wheel(self, e):

        return

    def _validate_numeric(self):
        
        val = self.numeric.text()
        validator_result = self.numeric.validator().validate(val, 0)
        if validator_result[0] != QtGui.QValidator.State.Acceptable:
            val = self._numeric_val
            self.numeric.setText(str(self._numeric_val))
            return

        if self._type == "int":
            val = int(val)
        else:
            val = float(val)
            
        self._numeric_val = val
        slider_val = val

        if val * 100 < self.slider.minimum():
            
            if self.lock_min:
                if self._type == "int":
                    val = self.slider.minimum()
                else:
                    val = self.slider.minimum() * 0.01
                    slider_val = val * 100.0
            else:
                if self._type == "int":
                    self.slider.setMinimum(val)
                else:
                    self.slider.setMinimum(val * 100.0)
                    slider_val = val * 100.0

        if val * 100 > self.slider.maximum():
            
            if self.lock_max:
                if self._type == "int":
                    val = self.slider.maximum()
                else:
                    val = self.slider.maximum() * 0.01
                    slider_val = val * 100.0
            else:
                if self._type == "int":
                    self.slider.setMaximum(val)
                else:
                    self.slider.setMaximum(val * 100.0)
                    slider_val = val * 100.0
        
        if self._type == "float":
            self.slider.setValue(slider_val * 100)
        else:
            self.slider.setValue(slider_val)
        self.numeric.setText(str(val))

    def _update_from_slider(self):

        val = self.slider.value()
        if self._type == "int":
            val = int(val)
        else:
            val = float(val) * 0.01
        
        self.numeric.setText(str(val))
        self._value = val

        if self.hou_parm:
            self.hou_parm.set(val)
    
    def _checkbox_sgn(self):

        toggle = self.enable_checkbox.isChecked()
        self.lbl.setEnabled(toggle)
        self.numeric.setEnabled(toggle)
        self.slider.setEnabled(toggle)

        if self.hou_checkbox:
            self.hou_checkbox.set(self.enable_checkbox.isChecked())

    def set_value(self, value):
        
        self.numeric.setText(str(value))
        self._validate_numeric()

        if self.hou_parm:
            self.hou_parm.set(value)

    def value(self):
        
        val = self.numeric.text()
        if self._type == "float":
            return float(val)
        return int(val)

class HVector(QtGui.QWidget):

    def __init__(self, label="", size=2, _type="float",
                       min=0.0, max=10.0, lock_min=True, lock_max=False,
                       enable_checkbox=False, enable=True,
                       default_value=[-180.0, 180.0],
                       tooltip="", hou_parm=None, hou_checkbox=None, parent=None):
        super(HVector, self).__init__(parent=parent)

        self.hou_parm = hou_parm
        self.hou_checkbox = hou_checkbox

        main_layout = QtGui.QHBoxLayout()
        main_layout.setSpacing(5)
        main_layout.setContentsMargins(0,0,0,0)

        self.setToolTip(tooltip)

        self._type = _type
        self.default_value = default_value

        if enable_checkbox:
            self.enable_checkbox = QtGui.QCheckBox(self)
            self.enable_checkbox.setChecked(enable)
            self.enable_checkbox.clicked.connect(self._checkbox_sgn)
            main_layout.addWidget(self.enable_checkbox)

        self.lbl = QtGui.QLabel(label)
        self.lbl.setEnabled(enable)
        main_layout.addWidget(self.lbl)

        self.vector_widgets = []
        for i in range(size):

            if i < len(default_value):
                dval = default_value[i]
            else:
                dval = 0.0

            if _type == "int":
                dval = int(dval)
            else:
                dval = float(dval)

            w = QtGui.QLineEdit(self)
            if _type == "int":
                w.setValidator(QtGui.QIntValidator())
            else:
                w.setValidator(QtGui.QDoubleValidator())
            w.setObjectName("vid_" + str(i))
            w.returnPressed.connect(partial(self._validate_numeric, i))
            w.setEnabled(enable)
            w.setText(str(dval))
            self.vector_widgets.append(w)
            main_layout.addWidget(w)

        self.setLayout(main_layout)

    def _validate_numeric(self, idx):

        val = self.vector_widgets[idx].text()
        try:
            if self._type == "int":
                val = int(val)
            else:
                val = float(val)
        except ValueError:
            self.vector_widgets[idx].setText(str(self.default_value[idx]))

        val = self.value()
        for i, p in enumerate(self.hou_parm):
            p.set(val[i])

    def _checkbox_sgn(self):

        for w in self.vector_widgets:
            w.setEnabled(self.enable_checkbox.isChecked())

        if self.hou_checkbox:
            self.hou_checkbox.set(self.enable_checkbox.isChecked())

    def value(self):

        if self._type == "int":
            return [int(i.text()) for i in self.vector_widgets]
        return [float(i.text()) for i in self.vector_widgets]

class InstanceModelWidget(QtGui.QWidget):

    def __init__(self, path="", influence=50.0, idx=0, gaia_node=None,
                 parent=None):
        super(InstanceModelWidget, self).__init__(parent=parent)

        main_layout = QtGui.QVBoxLayout()
        main_layout.setSpacing(5)

        self.gaia_node = gaia_node
        self.idx = idx
        name = path.split('/')[-1]  # placeholder, should be a parameter
        model_ix = 0  # placeholder, will be a unique ID in the collection

        self.name = QtGui.QLabel(name)
        main_layout.addWidget(self.name)

        self.influence = InfluenceBarWidget(value=influence, idx=idx,
                                            callback=self.set_hou_parm)
        main_layout.addWidget(self.influence)

        main_layout.setAlignment(QtCore.Qt.AlignTop|QtCore.Qt.AlignLeft)
        self.setLayout(main_layout)

    def set_hou_parm(self, idx, value):
        
        self.gaia_node.parm("influence_" + str(idx)).set(value)

class HStringValue(QtGui.QWidget):

    def __init__(self, default="", label="",
                 pick_list_callback=None, multiple_values=False,
                 enable_checkbox=False, enable=True,
                 hou_parm=None, hou_checkbox=None,
                 parent=None):
        super(HStringValue, self).__init__(parent=parent)
        
        main_layout = QtGui.QHBoxLayout()
        main_layout.setAlignment(QtCore.Qt.AlignLeft)
        main_layout.setSpacing(5)

        self.enable_checkbox = None
        self.lbl = None
        self.pick_btn = None
        self.pick_list_callback = pick_list_callback
        self.hou_parm = hou_parm
        self.hou_checkbox = hou_checkbox
        self.multiple_values = multiple_values

        if enable_checkbox:
            self.enable_checkbox = QtGui.QCheckBox()
            self.enable_checkbox.setChecked(enable)
            self.enable_checkbox.clicked.connect(self.toggle_enable)
            main_layout.addWidget(self.enable_checkbox)

        if label:
            self.lbl = QtGui.QLabel(label)
            self.lbl.setEnabled(enable)
            main_layout.addWidget(self.lbl)

        self.string_input = QtGui.QLineEdit()
        self.string_input.returnPressed.connect(self.valid)
        self.string_input.setText(default)
        self.string_input.setEnabled(enable)
        main_layout.addWidget(self.string_input)

        if self.pick_list_callback and self.hou_parm:
            self.pick_btn = QtGui.QPushButton("")
            self.pick_btn.setIcon(get_icon("convert_to_solid"))
            self.pick_btn.clicked.connect(self.pick)
            self.pick_btn.setIconSize(QtCore.QSize(24, 24))
            self.pick_btn.setFixedWidth(28)
            self.pick_btn.setFixedHeight(28)
            self.pick_btn.setEnabled(enable)
            main_layout.addWidget(self.pick_btn)

        main_layout.setContentsMargins(0,0,0,0)
        self.setLayout(main_layout)
        self.setContentsMargins(0,0,0,0)

    def set_value(self, value):

        self.hou_parm.set(str(value))
        self.string_input.setText(str(value))

    def toggle_enable(self):

        t = self.enable_checkbox.isChecked()
        self.lbl.setEnabled(t)
        self.string_input.setEnabled(t)
        if self.pick_btn:
            self.pick_btn.setEnabled(t)
        self.hou_checkbox.set(t)

    def valid(self):

        if self.hou_parm:
            value = str(self.string_input.text())
            self.hou_parm.set(value)

    def pick(self):

        choices = self.pick_list_callback()
        r = hou.ui.selectFromList(choices,
                                  title="Pick an item")
        if not r: return

        value = ' '.join([choices[i] for i in r])
        
        if self.multiple_values:
            cur_val = str(self.string_input.text())
            if not cur_val.endswith(' '):
                cur_val += ' '

            value = cur_val + value

        self.string_input.setText(value)
        self.hou_parm.set(value)

class CollapsableWidget(QtGui.QWidget):
    """ Custom widget which makes a given widget "collapsable" (hidden/shown)
        using a simple custom push button.
    """
    def __init__(self, widget=None, label="",
                 color="", collapsed=False, parent=None):

        super(CollapsableWidget, self).__init__(parent=parent)

        self.collapsed = collapsed

        main_layout = QtGui.QVBoxLayout()
        self.setContentsMargins(0,0,0,0)
        self.collapse_btn = QtGui.QPushButton(label)
        self.collapse_btn.setContentsMargins(0,0,0,0)
        self.collapse_btn.clicked.connect(self.collapse)
        self.collapse_btn.setFixedHeight(20)
        self.collapse_btn.setSizePolicy(QtGui.QSizePolicy.MinimumExpanding,
                                        QtGui.QSizePolicy.Maximum)

        if color == "red":
            color = "rgb(120, 60, 60)"
            color_hoover = "rgb(220, 75, 75)"

        elif color == "green":
            color = "rgb(60, 120, 60)"
            color_hoover = "rgb(75, 220, 75)"

        elif color == "blue":
            color = "rgb(60, 60, 120)"
            color_hoover = "rgb(75, 75, 220)"

        else:
            color = "rgb(80, 80, 80)"
            color_hoover = "rgb(100, 100, 100)"

        self.collapse_btn.setStyleSheet("""
        QPushButton{background-color:""" + color + """;
                    border: 0px;}
        QPushButton:hover{background-color:""" + color_hoover + """;
                           border: 0px;}
        """)
        if collapsed:
            self.collapse_btn.setIcon(get_icon("collapse_up"))
        else:
            self.collapse_btn.setIcon(get_icon("collapse_down"))
        main_layout.addWidget(self.collapse_btn)

        self.widget = widget
        self.widget.setParent(self)
        self.widget.setContentsMargins(0,0,0,0)
        self.widget.setVisible(not collapsed)
        main_layout.setContentsMargins(0,1,0,1)
        main_layout.addWidget(self.widget)

        self.setLayout(main_layout)
        
    def collapse(self):

        if self.collapsed:
            self.widget.setVisible(True)
            self.collapsed = False
            self.collapse_btn.setIcon(get_icon("collapse_down"))
        else:
            self.widget.setVisible(False)
            self.collapsed = True
            self.collapse_btn.setIcon(get_icon("collapse_up"))

class PickLayerTypeWidget(QtGui.QDialog):

    def __init__(self, parent=None):
        super(PickLayerTypeWidget, self).__init__(parent=parent)

        self.setWindowTitle("Create a new layer")

        self.layer_type = None
        self.layer_name = ""

        main_layout = QtGui.QVBoxLayout()
        main_layout.setSpacing(5)

        name_layout = QtGui.QHBoxLayout()
        name_layout.addWidget(QtGui.QLabel("Layer Name:"))
        self.name_input = QtGui.QLineEdit()
        name_layout.addWidget(self.name_input)
        main_layout.addItem(name_layout)

        self.paint_btn = QtGui.QPushButton("Create Paint Layer")
        self.paint_btn.setIcon(get_icon("brush"))
        self.paint_btn.clicked.connect(lambda: self.create_layer("paint"))
        main_layout.addWidget(self.paint_btn)

        self.fill_btn = QtGui.QPushButton("Create Fill Layer")
        self.fill_btn.setIcon(get_icon("fill"))
        self.fill_btn.clicked.connect(lambda: self.create_layer("fill"))
        main_layout.addWidget(self.fill_btn)

        main_layout.addWidget(QtGui.QLabel(""))

        self.cancel_btn = QtGui.QPushButton("Cancel")
        self.cancel_btn.clicked.connect(self.close)
        main_layout.addWidget(self.cancel_btn)

        self.setLayout(main_layout)

    def create_layer(self, _type):

        n = str(self.name_input.text())
        if n.replace(' ', '') == "":
            hou.ui.displayMessage("Invalid name",
                                  severity=hou.severityType.Error)
            return

        self.layer_type = _type
        self.layer_name = n
        self.close()

class AttribRuleWidget(QtGui.QWidget):
    """ Define a min-max rule widget from a given normalized attributes
        Must be link to a given Gaia_Apply_Rule node in order to delete the points.
    """
    def __init__(self, rule_node=None, default=[0.0, 1.0],
                 label="", tooltip="", parent=None):
        super(AttribRuleWidget, self).__init__(parent=parent)

        assert (type(rule_node) == hou.SopNode or \
                rule_node.type().name() == "rule_node"), \
                "Invalud arg type: rule_node"

        main_layout = QtGui.QHBoxLayout()
        main_layout.setSpacing(5)

        self.enable = rule_node.evalParm("enable")
        self.rule_node = rule_node  # vex wrangle node wrapped in an hda

        self.enable_checkbox = QtGui.QCheckBox()
        self.enable_checkbox.setChecked(self.enable)
        self.enable_checkbox.clicked.connect(self.toggle_enable)
        main_layout.addWidget(self.enable_checkbox)

        self.label = QtGui.QLabel(label)
        self.label.setEnabled(self.enable)
        main_layout.addWidget(self.label)

        self.min = QtGui.QLineEdit("")
        self.min.setEnabled(self.enable)
        self.min.setText(str(default[0]))
        self.min.setValidator(QtGui.QDoubleValidator(0.0, 1.0, 10))
        self.min.returnPressed.connect(self.update_node)
        main_layout.addWidget(self.min)

        self.max = QtGui.QLineEdit("")
        self.max.setEnabled(self.enable)
        self.max.setText(str(default[1]))
        self.max.setValidator(QtGui.QDoubleValidator(0.0, 1.0, 10))
        self.max.returnPressed.connect(self.update_node)
        main_layout.addWidget(self.max)

        main_layout.setContentsMargins(0,0,0,0)
        self.setLayout(main_layout)
        self.setContentsMargins(0,0,0,0)

        self.min.setText(str(rule_node.evalParm("min")))
        self.max.setText(str(rule_node.evalParm("max")))

    def update_node(self):

        value = self.get_value()
        self.rule_node.parm("min").set(value[0])
        self.rule_node.parm("max").set(value[1])

    def toggle_enable(self):

        if self.enable:
            self.label.setEnabled(False)
            self.min.setEnabled(False)
            self.max.setEnabled(False)
            self.enable = False
            self.rule_node.parm("enable").set(False)
        else:
            self.label.setEnabled(True)
            self.min.setEnabled(True)
            self.max.setEnabled(True)
            self.enable = True
            self.rule_node.parm("enable").set(True)

    def get_value(self):

        return [float(self.min.text()),
                float(self.max.text())]

    def set_value(self, value):

        self.min.setText(str(value[0]))
        self.max.setText(str(value[1]))

        self.rule_node.parm("min").set(value[0])
        self.rule_node.parm("max").set(value[1])