from __future__ import annotations

from typing import TYPE_CHECKING, cast

from pymmcore_plus import CMMCorePlus
from qtpy.QtCore import QPoint, QSize, Qt
from qtpy.QtGui import QCursor, QPalette
from qtpy.QtWidgets import (
    QApplication,
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

        # Get label from settings
        self._label = QLabel()

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


class _GainWidget(QWidget):
    """A single DCC/DCU connector providing PMT gain."""

    def __init__(self, mmcore: CMMCorePlus, device: Device, i: int) -> None:
        super().__init__()
        self._mmcore = mmcore
        self._dev: Device = device
        self._idx = i

        # Get label from settings
        self._label = QLabel()

        self._gain_lbl = QLabel("Gain/HV:")
        self._gain = QLabeledDoubleSlider(Qt.Orientation.Horizontal)
        self._gain.setRange(0, 100)
        self._gain.setValue(0)
        self._gain._label.setSuffix("%")

        # The Overload button serves two goals:
        # (a) notifies users of controller overload
        # (b) on DCUs, enables the user to clear the overload
        self._overload = QPushButton(text="Overloaded")
        self._overload.setToolTip("Overload indicator. Click to clear.")
        self._overload_icon = QIconifyIcon("si:error-line", color="red")
        self._overload_icon_hidden = QIconifyIcon("si:error-line", color="transparent")
        self._set_overload(False)
        if f"C{i}_ClearOverload" in self._dev.propertyNames():
            self._overload.clicked.connect(self._clear_connector_overload)
        elif "ClearOverloads" in self._dev.propertyNames():
            self._overload.clicked.connect(self._clear_all_overloads)

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

    def _clear_connector_overload(self) -> None:
        """Called when the device has one Clear Overloads signal per connector."""
        self._dev.setProperty(f"C{self._idx}_ClearOverload", "Clear")

    def _clear_all_overloads(self) -> None:
        """Called when the device has one Clear Overloads signal for all connectors."""
        self._dev.setProperty("ClearOverloads", "Clear")

    def _set_overload(self, overloaded: bool) -> None:
        # The goal here is to create an alert that (a) takes up needed space, but is not
        # distracting when not overloaded, and (b) is very noticeable when overloaded.
        icon = self._overload_icon if overloaded else self._overload_icon_hidden
        self._overload.setIcon(icon)
        color = (
            "transparent"
            if not overloaded
            else (
                QApplication.palette()
                .color(QPalette.ColorGroup.Active, QPalette.ColorRole.Text)
                .name()
            )
        )
        self._overload.setStyleSheet(f"QPushButton {{color: {color};}}")


class _LabelControls:
    """Label Controls for a particular index."""

    def __init__(self, mmcore: CMMCorePlus, dev: Device, idx: int) -> None:
        self._dev = dev
        self._idx = idx
        self.checkbox = QCheckBox()
        self.edit = QLineEdit()
        self.ctrl: _GainWidget | _DigitalOutWidget

        if f"C{self._idx}_GainHV" in self._dev.propertyNames():
            self.ctrl = _GainWidget(mmcore, self._dev, idx)
        elif f"C{self._idx}_DigitalOut" in self._dev.propertyNames():
            self.ctrl = _DigitalOutWidget(mmcore, self._dev, idx)
        else:
            raise Exception(f"Unexpected device on Connector {idx} of device {dev}")

        # Initialize settings
        lbl_map = Settings.instance().bh_dcc_dcu_connector_labels
        lbl_map.setdefault(self._dev.name(), {})
        lbl_map[self._dev.name()].setdefault(idx, f"Connector {idx}")

        vis_map = Settings.instance().bh_dcc_dcu_connector_visibility
        vis_map.setdefault(self._dev.name(), {})
        vis_map[self._dev.name()].setdefault(idx, True)

        # Signals
        self.checkbox.toggled.connect(self._update_visible)
        self.edit.editingFinished.connect(self._update_label)

        # Configure widget against settings
        self.edit.setText(lbl_map[self._dev.name()][self._idx])
        self.edit.editingFinished.emit()
        self.checkbox.setChecked(vis_map[self._dev.name()][self._idx])
        self.checkbox.toggled.emit(self.checkbox.isChecked())

    def _update_visible(self, toggled: bool) -> None:
        # Update visibility in ctrl
        self.ctrl.setVisible(toggled)

        # Update label in settings
        vis_map = Settings.instance().bh_dcc_dcu_connector_visibility
        vis_map[self._dev.name()][self._idx] = toggled
        Settings.instance().flush()

    def _update_label(self) -> None:
        # Update label in ctrl
        lbl = self.edit.text()
        self.ctrl._label.setText(lbl)

        # Update label in settings
        lbl_map = Settings.instance().bh_dcc_dcu_connector_labels
        lbl_map[self._dev.name()][self._idx] = lbl
        Settings.instance().flush()


class _PowerButton(QPushButton):
    """Buttons tailored to denote Device output power state."""

    def __init__(
        self,
        notify_icon: str,
        idle_icon: str,
        notify_text: str = "On",
        idle_text: str = "Off",
        *args: Any,
        **kwargs: Any,
    ) -> None:
        super().__init__(*args, **kwargs)

        self._on_color = (
            QApplication.palette()
            .color(QPalette.ColorGroup.Active, QPalette.ColorRole.Text)
            .name()
        )
        self._off_color = (
            QApplication.palette()
            .color(QPalette.ColorGroup.Disabled, QPalette.ColorRole.Text)
            .name()
        )

        self._on_icon: QIconifyIcon = QIconifyIcon(notify_icon)
        self._off_icon: QIconifyIcon = QIconifyIcon(idle_icon, color=self._off_color)

        self._on_text = notify_text
        self._off_text = idle_text

        # Init
        self._on_toggle(False)
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)

        # Signals
        self.setCheckable(True)
        self.toggled.connect(self._on_toggle)

    def set_height(self, height: int) -> None:
        icon_height = 24
        self.setIconSize(QSize(icon_height, icon_height))
        font = self.font()
        font.setPointSize(int(icon_height * 0.75))  # Works for most fonts
        self.setFont(font)

    def _on_toggle(self, toggled: bool) -> None:
        if toggled:
            self.setText(self._on_text)
            self.setIcon(self._on_icon)
            self.setStyleSheet(f"QPushButton {{color: {self._on_color}}}")
        else:
            self.setText(self._off_text)
            self.setIcon(self._off_icon)
            self.setStyleSheet(f"QPushButton {{color: {self._off_color}}}")


class _Module(QWidget):
    """Controls for a DCC/DCU Module."""

    def __init__(self, mmcore: CMMCorePlus, dev_name: str) -> None:
        super().__init__()
        self._mmcore = mmcore
        self._dev = mmcore.getDeviceObject(dev_name)
        self._connectors: list[_LabelControls] = []
        for i in range(1, 6):
            if (
                f"C{i}_GainHV" in self._dev.propertyNames()
                or f"C{i}_DigitalOut" in self._dev.propertyNames()
            ):
                self._connectors.append(_LabelControls(self._mmcore, self._dev, i))

        # Widgets for Power controls
        self._toggle_lbl = QLabel("Toggle Power: ")
        self._cooling = _PowerButton(
            notify_icon="fluent-color:weather-snowflake-48",
            idle_icon="fluent:weather-snowflake-48-regular",
            notify_text="Cooling",
            idle_text="Cooling",
        )
        self._outs_lbl = QLabel("Outputs: ")
        self._outs = _PowerButton(
            notify_icon="fluent-color:warning-48",
            idle_icon="fluent:warning-48-regular",
            notify_text="Outputs",
            idle_text="Outputs",
        )
        # Make these controls a little larger
        font = self._toggle_lbl.font()
        font.setPointSize(18)
        self._toggle_lbl.setFont(font)
        self._outs_lbl.setFont(font)
        self._cooling.set_height(24)
        self._outs.set_height(24)

        self._module_ctrls = QHBoxLayout()
        self._module_ctrls.addWidget(self._toggle_lbl)
        self._module_ctrls.addWidget(self._cooling)
        self._module_ctrls.addWidget(self._outs)

        self._layout = QVBoxLayout(self)
        for connector in self._connectors:
            self._layout.addWidget(connector.ctrl)
        self._layout.addLayout(self._module_ctrls)

        self._dev.propertyChanged.connect(self._on_property_changed)
        self._cooling.toggled.connect(self._on_enable_cooling)
        self._outs.toggled.connect(self._on_enable_outs)

        self.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.customContextMenuRequested.connect(self._show_popup)

        self._settings_popup = QtPopup()
        settings_layout = QFormLayout(self._settings_popup.frame)
        for con in self._connectors:
            settings_layout.addRow(f"Show Connector {con._idx}: ", con.checkbox)
            settings_layout.addRow(f"Connector {con._idx} Label: ", con.edit)

    def _show_popup(self) -> None:
        self._settings_popup.show_above_mouse()

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
                self._dev.setProperty(prop, value)

    def _on_enable_cooling(self, enabled: bool) -> None:
        value = "On" if enabled else "Off"
        for i in range(1, 6):
            # Some or all of these properties will be on the device
            prop = f"C{i}_Cooling"
            if prop in self._dev.propertyNames():
                self._dev.setProperty(prop, value)

    def _on_property_changed(self, prop: str, value: Any) -> None:
        if prop == "EnableOutputs":
            with signals_blocked(self._outs):
                self._outs.setChecked(value == "On")
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
