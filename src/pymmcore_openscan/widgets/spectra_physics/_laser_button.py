from __future__ import annotations

from typing import TYPE_CHECKING

from pymmcore_plus import CMMCorePlus, Device
from qtpy.QtGui import QPalette
from qtpy.QtWidgets import QApplication
from superqt import QIconifyIcon
from superqt.utils import signals_blocked

if TYPE_CHECKING:
    from qtpy.QtWidgets import QWidget

from ._utils import _DEVICE_NAME, SafetyButton

_PROP_NAME = "Pump Laser"


class LaserButton(SafetyButton):
    """Laser enable/disable button with a safety countdown."""

    def __init__(
        self,
        parent: QWidget | None = None,
        mmcore: CMMCorePlus | None = None,
    ) -> None:
        super().__init__(parent=parent)
        self._mmcore = mmcore or CMMCorePlus.instance()
        self._dev: Device | None = None

        text_color = (
            QApplication.palette()
            .color(QPalette.ColorGroup.Active, QPalette.ColorRole.Text)
            .name()
        )
        self.off_icon = QIconifyIcon("mdi:power", color=text_color)
        self.on_icon = QIconifyIcon("mdi:power", color=text_color)

        self.toggled.connect(self._on_toggled)
        self._mmcore.events.systemConfigurationLoaded.connect(self._try_enable)
        self._mmcore.events.devicePropertyChanged(_DEVICE_NAME, _PROP_NAME).connect(
            self._on_property_change
        )
        self._try_enable()

    def _try_enable(self) -> None:
        enabled = _DEVICE_NAME in self._mmcore.getLoadedDevices()
        self.setEnabled(enabled)

        self._dev = None
        if enabled:
            self._dev = self._mmcore.getDeviceObject(_DEVICE_NAME)
            self.setChecked(self._dev.getProperty(_PROP_NAME) == "On")

    def _on_property_change(self, new_value: str) -> None:
        with signals_blocked(self):
            self.setChecked(new_value == "On")

    def _on_toggled(self, checked: bool) -> None:
        if self._dev:
            try:
                self._dev.setProperty(_PROP_NAME, "On" if checked else "Off")
            except RuntimeError as e:
                # The device adapter prevents turning the laser prematurely
                with signals_blocked(self):
                    self.setChecked(False)
                raise e
