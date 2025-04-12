from __future__ import annotations

from typing import TYPE_CHECKING

from qtpy.QtCore import Qt
from qtpy.QtWidgets import (
    QCheckBox,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QVBoxLayout,
    QWidget,
)
from superqt import QIconifyIcon, QLabeledDoubleSlider
from superqt.utils import signals_blocked

if TYPE_CHECKING:
    from typing import Any

    from pymmcore_plus import CMMCorePlus, Device

class _DCC_ConnectorWidget(QWidget):
    """Controls for a single DCC connector."""

    def __init__(self, mmcore:CMMCorePlus, device: Device, i: int) -> None:
        super().__init__()
        self._mmcore = mmcore
        self._dev = device
        self._idx = i

        self._label = QLabel(f"Connector {i}:")

        self._pos12v = QCheckBox("+12V")
        self._pos5v = QCheckBox("+5V")
        self._neg5v = QCheckBox("-5V")
        # TODO: Consider an icon here
        self._overload = QPushButton()
        self._overload_icon = QIconifyIcon("si:error-line", color="red")
        self._overload_icon_hidden = QIconifyIcon("si:error-line", color="transparent")
        self._overload.setCheckable(True)
        self._overload.toggled.connect(self._on_overload)
        self._on_overload(False)

        # TODO: Gain percentage suffix
        self._gain = QLabeledDoubleSlider(Qt.Orientation.Horizontal)
        self._gain.setRange(0, 100)
        self._gain.setValue(0)

        self._layout = QHBoxLayout(self)
        self._layout.addWidget(self._label)
        self._layout.addWidget(self._pos12v)
        self._layout.addWidget(self._pos5v)
        self._layout.addWidget(self._neg5v)
        self._layout.addWidget(self._gain)
        self._layout.addWidget(self._overload)

        self._pos12v.toggled.connect(self._on_12v_toggled)
        self._pos5v.toggled.connect(self._on_pos5v_toggled)
        self._neg5v.toggled.connect(self._on_neg5v_toggled)
        self._gain.valueChanged.connect(self._on_gain_changed)
        self._dev.propertyChanged.connect(self._on_property_changed)

    def _on_12v_toggled(self, toggled: bool) -> None:
        self._set_property("Plus12V", "On" if toggled else "Off")

    def _on_pos5v_toggled(self, toggled: bool) -> None:
        self._set_property("Plus5V", "On" if toggled else "Off")

    def _on_neg5v_toggled(self, toggled: bool) -> None:
        self._set_property("Minus5V", "On" if toggled else "Off")

    def _on_gain_changed(self, value: float) -> None:
        self._set_property("GainHV", value)

    def _set_property(self, suffix: str, value: Any) -> None:
        self._mmcore.setProperty( self._dev.label, f"C{self._idx}_{suffix}", value)

    def _on_property_changed(self, prop: str, value: Any) -> None:
        if prop == f"C{self._idx}_Plus12V":
            with signals_blocked(self._pos12v):
                self._pos12v.setChecked(value == "On")
        elif prop == f"C{self._idx}_Plus5V":
            with signals_blocked(self._pos5v):
                self._pos5v.setChecked(value == "On")
        elif prop == f"C{self._idx}_Minus5V":
            with signals_blocked(self._neg5v):
                self._neg5v.setChecked(value == "On")
        elif prop == f"C{self._idx}_GainHV":
            with signals_blocked(self._gain):
                self._gain.setValue(value)
        elif prop == f"C{self._idx}_Overloaded":
            self._on_overload(True)

    def _on_overload(self, overloaded: bool) -> None:
        self._overload.setEnabled(overloaded)
        self._overload.setText("Overloaded" if overloaded else "")
        self._overload.setIcon(self._overload_icon if overloaded else self._overload_icon_hidden)


class _DCC_CoolingWidget(QWidget):
    """Controls for DCC cooling."""

    def __init__(self, mmcore:CMMCorePlus, device: Device) -> None:
        super().__init__()
        self._mmcore = mmcore
        self._dev = device
        self._dev.propertyChanged.connect(self._on_property_changed)

        self._label = QLabel("Cooling")

        self._enabled = QCheckBox("On")
        self._enabled.toggled.connect(self._on_enabled)

        # TODO: Current limit
        self._current_lbl = QLabel("Amps:")
        self._current = QLabeledDoubleSlider(Qt.Orientation.Horizontal)
        self._current.setEnabled(False)
        self._current.setRange(0, 2)
        self._current.setValue(0)
        self._current.valueChanged.connect(self._on_current_changed)

        self._voltage_lbl = QLabel("Volts:")
        self._voltage = QLabeledDoubleSlider(Qt.Orientation.Horizontal)
        self._voltage.setEnabled(False)
        self._voltage.setRange(0, 5)
        self._voltage.setValue(0)
        self._voltage.valueChanged.connect(self._on_voltage_changed)

        self._layout = QHBoxLayout(self)
        self._layout.addWidget(self._label)
        self._layout.addWidget(self._enabled)
        self._layout.addWidget(self._current_lbl)
        self._layout.addWidget(self._current)
        self._layout.addWidget(self._voltage_lbl)
        self._layout.addWidget(self._voltage)

    def _on_enabled(self, toggled: bool) -> None:
        self._set_property("Cooling", "On" if toggled else "Off")
        self._current.setEnabled(toggled)
        self._voltage.setEnabled(toggled)

    def _on_current_changed(self, value: float) -> None:
        self._set_property("CoolerCurrentLimit", value)

    def _on_voltage_changed(self, value: float) -> None:
        self._set_property("CoolerVoltage", value)

    def _set_property(self, suffix: str, value: Any) -> None:
        self._mmcore.setProperty( self._dev.label, f"C3_{suffix}", value)

    def _on_property_changed(self, prop: str, value: Any) -> None:
        if prop == "C3_Cooling":
            self._enabled.setChecked(value == "On")
        elif prop == "C3_CoolerCurrentLimit":
            self._current.setValue(value)
        elif prop == "C3_CoolerVoltage":
            self._voltage.setValue(value)

class _DCC_ModuleWidget(QWidget):
    """Controls for a DCC Module."""

    def __init__(self, mmcore:CMMCorePlus, i: int) -> None:
        super().__init__()
        self._mmcore = mmcore
        self._dev = mmcore.getDeviceObject(f"DCCModule{i}")
        self._connectors = {i: _DCC_ConnectorWidget(mmcore, self._dev, i+1) for i in range(3)}
        self._cooling = _DCC_CoolingWidget(mmcore, self._dev)

        self._clr_overloads = QPushButton("Clear Overloads")
        self._enable_outs = QPushButton("Enable Outputs")
        self._enable_outs.setCheckable(True)

        self._module_ctrls = QHBoxLayout()
        self._module_ctrls.addWidget(self._clr_overloads)
        self._module_ctrls.addWidget(self._enable_outs)

        self._layout = QVBoxLayout(self)
        for i in range(3):
            self._layout.addWidget(self._connectors[i])
        self._layout.addWidget(self._cooling)
        self._layout.addLayout(self._module_ctrls)

        self._dev.propertyChanged.connect(self._on_property_changed)
        self._clr_overloads.clicked.connect(self._on_clr_overloads)
        self._enable_outs.toggled.connect(self._on_enable_outs)

        self._toggle_overloads = QPushButton("Toggle Overloads")
        self._toggle_overloads.clicked.connect(self._on_toggle_overloads)
        self._layout.addWidget(self._toggle_overloads)

    def _on_clr_overloads(self) -> None:
        prop = "ClearOverloads"
        self._mmcore.setProperty(self._dev.label, prop, "Clear")
        # for connector in self._connectors.values():
        #     connector._overload.toggle()

    def _on_enable_outs(self, enabled: bool) -> None:
        prop = "EnableOutputs"
        value = "On" if enabled else "Off"
        self._mmcore.setProperty(self._dev.label, prop, value)

    def _on_toggle_overloads(self) -> None:
        for connector in self._connectors.values():
            connector._overload.toggle()

    def _on_property_changed(self, prop: str, value: Any) -> None:
        if prop == "EnableOutputs":
            self._enable_outs.setChecked(value == "On")


class DCCWidget(QWidget):
    """Widget controlling a Becker-Hickl Detector Control Card (DCC)."""

    def __init__(self, mmcore:CMMCorePlus):
        super().__init__()
        self._layout = QVBoxLayout(self)
        for dev in mmcore.getLoadedDevices():
            if mmcore.getDeviceName(dev) == "DCCHub":
                self._hub = mmcore.getDeviceObject(dev)
                break
        if self._hub is None:
            raise RuntimeError("No DCC device found")

        self._modules = {}
        for i in range(1, 9):
            if mmcore.getProperty(self._hub.label, f"UseModule{i}") == "Yes":
                self._modules[i] = module_wdg = _DCC_ModuleWidget(mmcore, i)
                self._layout.addWidget(module_wdg)


