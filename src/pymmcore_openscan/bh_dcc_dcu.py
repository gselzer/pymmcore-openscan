from __future__ import annotations

from typing import TYPE_CHECKING, cast

from pymmcore_plus import CMMCorePlus
from qtpy.QtCore import QPoint, Qt
from qtpy.QtGui import QCursor
from qtpy.QtWidgets import (
    QCheckBox,
    QDialog,
    QFormLayout,
    QFrame,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPushButton,
    QSizePolicy,
    QStyle,
    QStyleOptionButton,
    QVBoxLayout,
    QWidget,
)
from superqt import QIconifyIcon, QLabeledDoubleSlider
from superqt.utils import signals_blocked

from pymmcore_openscan._settings import Settings

if TYPE_CHECKING:
    from typing import Any

    from pymmcore_plus import Device


class QtPopup(QDialog):
    """A generic popup window."""

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setModal(False)  # if False, then clicking anywhere else closes it
        self.setWindowFlags(Qt.WindowType.Popup | Qt.WindowType.FramelessWindowHint)

        self.frame = QFrame(self)
        layout = QVBoxLayout(self)
        layout.addWidget(self.frame)
        layout.setContentsMargins(0, 0, 0, 0)

    def show_above_mouse(self, *args: Any) -> None:
        """Show popup dialog above the mouse cursor position."""
        pos = QCursor().pos()  # mouse position
        szhint = self.sizeHint()
        pos -= QPoint(szhint.width() // 2, szhint.height() + 14)
        self.move(pos)
        self.resize(self.sizeHint())
        self.show()


# TODO: In the future, we likely want to add the ability to rename these buttons.
# This is why the setText method is overridden already. The reason we don't do it now is
# because we'd want a mechanism for saving the button names.
class _BitButton(QPushButton):
    """Button toggling one bit of a DCC/DCU Digital Output."""

    def __init__(self, device: Device, idx: int, bit: int) -> None:
        super().__init__()
        self._device = device
        self._idx = idx
        self.value = 2**bit
        self._prop = self._device.getPropertyObject(f"C{self._idx}_DigitalOut")

        self.setText(f"b{bit}")
        self.setCheckable(True)
        self.toggled.connect(self._on_toggled)

    def setText(self, text: str | None) -> None:
        # Set the text
        super().setText(text)
        # Reset the minimum size around the new text
        textSize = self.fontMetrics().size(Qt.TextFlag.TextShowMnemonic, self.text())
        opt = QStyleOptionButton()
        opt.initFrom(self)
        opt.rect.setSize(textSize)
        self.setMinimumSize(
            cast("QStyle", self.style()).sizeFromContents(
                QStyle.ContentsType.CT_PushButton, opt, textSize, self
            )
        )
        self.setSizePolicy(QSizePolicy.Policy.Minimum, QSizePolicy.Policy.Minimum)

    def _on_toggled(self, checked: bool) -> None:
        if checked:
            self._prop.value |= self.value
        else:
            self._prop.value = (self._prop.value & ~self.value) % 256
        return


class _DigitalOutWidget(QWidget):
    """A single DCC connector providing digital output."""

    def __init__(self, mmcore: CMMCorePlus, device: Device, i: int) -> None:
        super().__init__()
        self._mmcore = mmcore
        self._dev = device
        self._idx = i

        # Ensure this device has a label
        lbl_map = Settings.instance().bh_dcc_dcu_connector_labels
        lbl_map.setdefault(self._dev.name(), {})
        lbl_map[self._dev.name()].setdefault(self._idx, f"Connector {self._idx}")
        # Get label from settings
        self._label = QLabel(lbl_map[self._dev.name()][self._idx])
        self._label.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self._label.customContextMenuRequested.connect(self._edit_label)

        self._label_popup = QtPopup()
        self._label_edit = QLineEdit(self._label.text())
        self._label_edit.editingFinished.connect(self._update_label)

        layout = QFormLayout(self._label_popup.frame)
        layout.addRow("Label", self._label_edit)

        self._bit_btns = [_BitButton(device=device, idx=i, bit=b) for b in range(8)]

        self._layout = QHBoxLayout(self)
        self._layout.addWidget(self._label)
        for btn in self._bit_btns:
            self._layout.addWidget(btn)

        self._dev.propertyChanged.connect(self._on_property_changed)

    def _edit_label(self) -> None:
        self._label_popup.show_above_mouse()

    def _update_label(self) -> None:
        lbl = self._label_edit.text()
        self._label.setText(lbl)

        lbl_map = Settings.instance().bh_dcc_dcu_connector_labels
        lbl_map[self._dev.name()][self._idx] = lbl
        Settings.instance().flush()

    def _set_property(self, suffix: str, value: Any) -> None:
        self._mmcore.setProperty(self._dev.label, f"C{self._idx}_{suffix}", value)

    def _on_property_changed(self, prop: str, value: Any) -> None:
        if prop == f"C{self._idx}_DigitalOut":
            value = int(value)
            for btn in self._bit_btns:
                with signals_blocked(btn):
                    btn.setChecked(bool(btn.value & value))


class _GainWidget(QWidget):
    """A single DCC/DCU connector providing PMT gain."""

    def __init__(self, mmcore: CMMCorePlus, device: Device, i: int) -> None:
        super().__init__()
        self._mmcore = mmcore
        self._dev = device
        self._idx = i

        # Ensure this device has a label
        lbl_map = Settings.instance().bh_dcc_dcu_connector_labels
        lbl_map.setdefault(device.name(), {})
        lbl_map[device.name()].setdefault(i, f"Connector {i}")
        # Get label from settings
        self._label = QLabel(lbl_map[device.name()][i])
        self._label.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self._label.customContextMenuRequested.connect(self._edit_label)

        self._label_popup = QtPopup()
        self._label_edit = QLineEdit(self._label.text())
        self._label_edit.editingFinished.connect(self._update_label)

        layout = QFormLayout(self._label_popup.frame)
        layout.addRow("Label", self._label_edit)

        self._gain_lbl = QLabel("Gain/HV:")
        self._gain = QLabeledDoubleSlider(Qt.Orientation.Horizontal)
        self._gain.setRange(0, 100)
        self._gain.setValue(0)
        self._gain._label.setSuffix("%")

        # The Overload button serves two goals:
        # (a) notifies users of controller overload
        # (b) on DCUs, enables the user to clear the overload
        self._overload = QPushButton(text="Overloaded")
        self._overload.setToolTip("Overload indicator")
        self._overload_icon = QIconifyIcon("si:error-line", color="red")
        self._overload_icon_hidden = QIconifyIcon("si:error-line", color="transparent")
        self._set_overload(False)
        if f"C{i}_ClearOverload" in self._dev.propertyNames():
            self._overload.clicked.connect(self._clear_overload)

        self._layout = QHBoxLayout(self)
        self._layout.addWidget(self._label)
        self._layout.addWidget(self._gain_lbl)
        self._layout.addWidget(self._gain)
        self._layout.addWidget(self._overload)

        self._gain.valueChanged.connect(self._on_gain_changed)
        self._dev.propertyChanged.connect(self._on_property_changed)

    def _on_gain_changed(self, value: float) -> None:
        self._set_property("GainHV", value)

    def _set_property(self, suffix: str, value: Any) -> None:
        self._mmcore.setProperty(self._dev.label, f"C{self._idx}_{suffix}", value)

    def _on_property_changed(self, prop: str, value: Any) -> None:
        if prop == f"C{self._idx}_GainHV":
            with signals_blocked(self._gain):
                self._gain.setValue(float(value))
        elif prop == f"C{self._idx}_Overloaded":
            self._set_overload(value == "Yes")

    def _clear_overload(self) -> None:
        self._set_property("ClearOverload", "Clear")

    def _set_overload(self, overloaded: bool) -> None:
        icon = self._overload_icon if overloaded else self._overload_icon_hidden
        self._overload.setIcon(icon)
        color = "black" if overloaded else "transparent"
        self._overload.setStyleSheet(f"QPushButton {{color: {color};}}")

    def _edit_label(self) -> None:
        self._label_popup.show_above_mouse()

    def _update_label(self) -> None:
        lbl = self._label_edit.text()
        self._label.setText(lbl)

        lbl_map = Settings.instance().bh_dcc_dcu_connector_labels
        lbl_map[self._dev.name()][self._idx] = lbl
        Settings.instance().flush()


class _Module(QWidget):
    """Controls for a DCC/DCU Module."""

    def __init__(self, mmcore: CMMCorePlus, dev_name: str) -> None:
        super().__init__()
        self._mmcore = mmcore
        self._dev = mmcore.getDeviceObject(dev_name)
        self._connectors: list[QWidget] = []
        for i in range(1, 6):
            if f"C{i}_GainHV" in self._dev.propertyNames():
                self._connectors.append(_GainWidget(mmcore, self._dev, i))
            elif f"C{i}_DigitalOut" in self._dev.propertyNames():
                self._connectors.append(_DigitalOutWidget(mmcore, self._dev, i))

        self._cooling = QCheckBox("Enable Cooling")
        self._enable_outs = QCheckBox("Enable Outputs")
        self._clr_overloads = QPushButton("Clear Overloads")

        self._module_ctrls = QHBoxLayout()
        self._module_ctrls.addWidget(self._cooling)
        self._module_ctrls.addWidget(self._enable_outs)
        self._module_ctrls.addWidget(self._clr_overloads)

        self._layout = QVBoxLayout(self)
        for connector in self._connectors:
            self._layout.addWidget(connector)
        self._layout.addLayout(self._module_ctrls)

        self._dev.propertyChanged.connect(self._on_property_changed)
        self._cooling.toggled.connect(self._on_enable_cooling)
        self._enable_outs.toggled.connect(self._on_enable_outs)
        self._clr_overloads.clicked.connect(self._on_clr_overloads)

    def _on_clr_overloads(self) -> None:
        prop = "ClearOverloads"
        self._mmcore.setProperty(self._dev.label, prop, "Clear")

    def _on_enable_outs(self, enabled: bool) -> None:
        # Some or all of these properties will be on the device
        enable_properties = [
            "EnableOutputs",
            "C1_EnableOutputs",
            "C2_EnableOutputs",
            "C3_EnableOutputs",
            "C4_EnableOutputs",
            "C5_EnableOutputs",
        ]
        value = "On" if enabled else "Off"
        for prop in enable_properties:
            if prop in self._dev.propertyNames():
                self._mmcore.setProperty(self._dev.label, prop, value)

    def _on_enable_cooling(self, enabled: bool) -> None:
        prop = "C3_Cooling"
        value = "On" if enabled else "Off"
        self._mmcore.setProperty(self._dev.label, prop, value)

    def _on_property_changed(self, prop: str, value: Any) -> None:
        if prop == "EnableOutputs":
            with signals_blocked(self._enable_outs):
                self._enable_outs.setChecked(value == "On")
        elif prop == "C3_Cooling":
            with signals_blocked(self._cooling):
                self._cooling.setChecked(value == "On")


class _DetectorWidget(QWidget):
    def __init__(
        self,
        prefix: str,
        numModules: int,
        parent: QWidget | None = None,
        mmcore: CMMCorePlus | None = None,
    ) -> None:
        super().__init__(parent=parent)
        self._layout = QVBoxLayout(self)
        self._prefix = prefix
        self._numModules = numModules
        self._mmcore = mmcore or CMMCorePlus.instance()
        # Each Detector Widget has a number of modules
        self._modules: dict[int, QWidget] = {}

        self._mmcore.events.systemConfigurationLoaded.connect(self.try_enable)
        self.try_enable()

    def try_enable(self) -> None:
        # Clear old Widgets
        for module in self._modules.values():
            self._layout.removeWidget(module)
        self._modules.clear()
        if f"{self._prefix}Hub" not in self._mmcore.getLoadedDevices():
            # Detector not loaded - nothing to do.
            return

        # Make new widgets
        self._dev = self._mmcore.getDeviceObject(f"{self._prefix}Hub")
        for i in range(1, self._numModules + 1):
            if self._mmcore.getProperty(self._dev.label, f"UseModule{i}") == "Yes":
                dev_name = f"{self._prefix}Module{i}"
                module_wdg = _Module(self._mmcore, dev_name)
                self._modules[i] = module_wdg
                self._layout.addWidget(module_wdg)


class DCUWidget(_DetectorWidget):
    """Widget controlling a Becker-Hickl Detector Control Unit (DCU)."""

    def __init__(
        self, parent: QWidget | None = None, mmcore: CMMCorePlus | None = None
    ):
        super().__init__("DCU", 3, parent=parent, mmcore=mmcore)


class DCCWidget(_DetectorWidget):
    """Widget controlling a Becker-Hickl Detector Control Card (DCC)."""

    def __init__(
        self, parent: QWidget | None = None, mmcore: CMMCorePlus | None = None
    ):
        super().__init__("DCC", 8, parent=parent, mmcore=mmcore)
