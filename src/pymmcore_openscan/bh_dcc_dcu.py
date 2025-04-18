from __future__ import annotations

from typing import TYPE_CHECKING, cast

from qtpy.QtCore import Qt
from qtpy.QtWidgets import (
    QCheckBox,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QStyle,
    QStyleOptionButton,
    QVBoxLayout,
    QWidget,
)
from superqt import QIconifyIcon, QLabeledDoubleSlider
from superqt.utils import signals_blocked

if TYPE_CHECKING:
    from typing import Any

    from pymmcore_plus import CMMCorePlus, Device


# TODO: In the future, we likely want to add the ability to rename these buttons.
# This is why the setText method is overridden already. The reason we don't do it now is
# because we'd want a mechanism for saving the button names.
class _BitButton(QPushButton):
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
            cast(QStyle, self.style()).sizeFromContents(
                QStyle.ContentsType.CT_PushButton, opt, textSize, self
            )
        )

    def _on_toggled(self, checked: bool) -> None:
        if checked:
            self._prop.value |= self.value
        else:
            self._prop.value = (self._prop.value & ~self.value) % 256
        return


class _DCC_DigitalOutWidget(QWidget):
    """A single DCC connector providing digital output."""

    def __init__(self, mmcore: CMMCorePlus, device: Device, i: int) -> None:
        super().__init__()
        self._mmcore = mmcore
        self._dev = device
        self._idx = i

        self._label = QLabel(f"Connector {i}:")

        self._bit_btns = [_BitButton(device=device, idx=i, bit=b) for b in range(8)]

        self._layout = QHBoxLayout(self)
        self._layout.addWidget(self._label)
        for btn in self._bit_btns:
            self._layout.addWidget(btn)

        self._dev.propertyChanged.connect(self._on_property_changed)

    def _set_property(self, suffix: str, value: Any) -> None:
        self._mmcore.setProperty(self._dev.label, f"C{self._idx}_{suffix}", value)

    def _on_property_changed(self, prop: str, value: Any) -> None:
        if prop == f"C{self._idx}_DigitalOut":
            value = int(value)
            for btn in self._bit_btns:
                with signals_blocked(btn):
                    btn.setChecked(bool(btn.value & value))


class _DCC_GainWidget(QWidget):
    """A single DCC connector providing PMT gain."""

    def __init__(self, mmcore: CMMCorePlus, device: Device, i: int) -> None:
        super().__init__()
        self._mmcore = mmcore
        self._dev = device
        self._idx = i

        self._label = QLabel(f"Connector {i}:")

        self._overload = QPushButton(text="Overloaded")
        self._overload_icon = QIconifyIcon("si:error-line", color="red")
        self._overload_icon_hidden = QIconifyIcon("si:error-line", color="transparent")
        self._set_overload(False)

        self._gain = QLabeledDoubleSlider(Qt.Orientation.Horizontal)
        self._gain.setRange(0, 100)
        self._gain.setValue(0)
        self._gain._label.setSuffix("%")

        self._layout = QHBoxLayout(self)
        self._layout.addWidget(self._label)
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

    def _set_overload(self, overloaded: bool) -> None:
        icon = self._overload_icon if overloaded else self._overload_icon_hidden
        self._overload.setIcon(icon)
        color = "black" if overloaded else "transparent"
        self._overload.setStyleSheet(f"QPushButton {{color: {color};}}")


class _DCC_ModuleWidget(QWidget):
    """Controls for a DCC Module."""

    def __init__(self, mmcore: CMMCorePlus, i: int) -> None:
        super().__init__()
        self._mmcore = mmcore
        self._dev = mmcore.getDeviceObject(f"DCCModule{i}")
        self._connectors: dict[int, QWidget] = {}
        for i in range(1, 4):
            if f"C{i}_GainHV" in self._dev.propertyNames():
                self._connectors[i] = _DCC_GainWidget(mmcore, self._dev, i)
            elif f"C{i}_DigitalOut" in self._dev.propertyNames():
                self._connectors[i] = _DCC_DigitalOutWidget(mmcore, self._dev, i)

        self._cooling = QCheckBox("Enable Cooling")
        self._enable_outs = QCheckBox("Enable Outputs")
        self._clr_overloads = QPushButton("Clear Overloads")

        self._module_ctrls = QHBoxLayout()
        self._module_ctrls.addWidget(self._cooling)
        self._module_ctrls.addWidget(self._enable_outs)
        self._module_ctrls.addWidget(self._clr_overloads)

        self._layout = QVBoxLayout(self)
        for i in range(1, 4):
            self._layout.addWidget(self._connectors[i])
        self._layout.addLayout(self._module_ctrls)

        self._dev.propertyChanged.connect(self._on_property_changed)
        self._cooling.toggled.connect(self._on_enable_cooling)
        self._enable_outs.toggled.connect(self._on_enable_outs)
        self._clr_overloads.clicked.connect(self._on_clr_overloads)

    def _on_clr_overloads(self) -> None:
        prop = "ClearOverloads"
        self._mmcore.setProperty(self._dev.label, prop, "Clear")

    def _on_enable_outs(self, enabled: bool) -> None:
        prop = "EnableOutputs"
        value = "On" if enabled else "Off"
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


class DCCWidget(QWidget):
    """Widget controlling a Becker-Hickl Detector Control Card (DCC)."""

    def __init__(self, mmcore: CMMCorePlus):
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
