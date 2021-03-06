import hou
import toolutils

from functools import partial

from PySide2 import QtGui
from PySide2 import QtWidgets
from PySide2 import QtCore

from .icons.icon import get_icon

class HSlider(QtWidgets.QWidget):
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
        self.setProperty("houdiniStyle", True)

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

        layout = QtWidgets.QHBoxLayout()
        layout.setSpacing(5)
        layout.setAlignment(QtCore.Qt.AlignLeft)

        if enable_checkbox:
            self.enable_checkbox = QtWidgets.QCheckBox(self)
            self.enable_checkbox.setChecked(enable)
            self.enable_checkbox.clicked.connect(self._checkbox_sgn)
            layout.addWidget(self.enable_checkbox)

        self.lbl = QtWidgets.QLabel(label + "  ")
        self.lbl.setAlignment(QtCore.Qt.AlignRight|QtCore.Qt.AlignVCenter)
        self.lbl.setEnabled(enable)
        layout.addWidget(self.lbl)
        
        self.numeric = QtWidgets.QLineEdit(self)
        self.numeric.setEnabled(enable)
        self.numeric.setText(str(default_value))
        self.numeric.returnPressed.connect(self._validate_numeric)
        self.numeric.setFixedWidth(50)
        layout.addWidget(self.numeric)

        self.slider = QtWidgets.QSlider(self)
        self.slider.wheelEvent = self._wheel
        self.slider.setEnabled(enable)
        self.slider.setOrientation(QtCore.Qt.Horizontal)
        if self._type == "int":
            self.slider.setRange(min, max)
            self.slider.setValue(default_value)
        else:
            self.slider.setRange(min * 100.0, max * 100.0)
            self.slider.setValue(default_value * 100.0)

        self.slider.valueChanged.connect(self._update_from_slider)
        layout.addWidget(self.slider)

        self.setToolTip(tooltip)
        self.setSizePolicy(QtWidgets.QSizePolicy.Minimum,
                           QtWidgets.QSizePolicy.Maximum)
        layout.setContentsMargins(0,0,0,0)
        self.setLayout(layout)
        self.setContentsMargins(0,0,0,0)

    def _wheel(self, e):

        return

    def _validate_numeric(self):
        
        val = self.numeric.text()
        try:
            if self._type == "int":
                val = int(val)
            else:
                val = float(val)
        except ValueError:
            val = self._numeric_val
            self.numeric.setText(str(self._numeric_val))
            return
            
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

class HVector(QtWidgets.QWidget):

    def __init__(self, label="", size=2, _type="float",
                       min=0.0, max=10.0, lock_min=True, lock_max=False,
                       enable_checkbox=False, enable=True,
                       default_value=[-180.0, 180.0],
                       tooltip="", hou_parm=None, hou_checkbox=None, parent=None):
        super(HVector, self).__init__(parent=parent)
        self.setProperty("houdiniStyle", True)

        self.hou_parm = hou_parm
        self.hou_checkbox = hou_checkbox

        main_layout = QtWidgets.QHBoxLayout()
        main_layout.setSpacing(5)
        main_layout.setContentsMargins(0,0,0,0)

        self.setToolTip(tooltip)

        self._type = _type
        self.default_value = default_value

        if enable_checkbox:
            self.enable_checkbox = QtWidgets.QCheckBox(self)
            self.enable_checkbox.setChecked(enable)
            self.enable_checkbox.clicked.connect(self._checkbox_sgn)
            main_layout.addWidget(self.enable_checkbox)

        self.lbl = QtWidgets.QLabel(label)
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

            w = QtWidgets.QLineEdit(self)
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

class HStringValue(QtWidgets.QWidget):

    def __init__(self, default="", label="",
                 pick_list_callback=None, multiple_values=False,
                 enable_checkbox=False, enable=True,
                 hou_parm=None, hou_checkbox=None,
                 parent=None):
        super(HStringValue, self).__init__(parent=parent)
        self.setProperty("houdiniStyle", True)

        main_layout = QtWidgets.QHBoxLayout()
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
            self.enable_checkbox = QtWidgets.QCheckBox()
            self.enable_checkbox.setChecked(enable)
            self.enable_checkbox.clicked.connect(self.toggle_enable)
            main_layout.addWidget(self.enable_checkbox)

        if label:
            self.lbl = QtWidgets.QLabel(label)
            self.lbl.setEnabled(enable)
            main_layout.addWidget(self.lbl)

        self.string_input = QtWidgets.QLineEdit()
        self.string_input.returnPressed.connect(self.valid)
        self.string_input.setText(default)
        self.string_input.setEnabled(enable)
        main_layout.addWidget(self.string_input)

        if self.pick_list_callback and self.hou_parm:
            self.pick_btn = QtWidgets.QPushButton("")
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

    def text(self):

        return self.string_input.text()

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

class HSeparator(QtWidgets.QFrame):

    def __init__(self, mode="horizontal", parent=None):
        super(HSeparator, self).__init__(parent=parent)
        self.setProperty("houdiniStyle", True)

        if mode == "horizontal":
            self.setFrameShape(QtWidgets.QFrame.HLine)
        else:
            self.setFrameShape(QtWidgets.QFrame.VLine)

        self.setFrameShadow(QtWidgets.QFrame.Sunken)
