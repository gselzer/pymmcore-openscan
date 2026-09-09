from __future__ import annotations

from typing import TYPE_CHECKING

from pymmcore_plus import CMMCorePlus
from qtpy.QtGui import QPalette
from qtpy.QtWidgets import QApplication
from superqt import QIconifyIcon
from superqt.utils import signals_blocked

if TYPE_CHECKING:
    from qtpy.QtWidgets import QWidget

from pymmcore_plus.core import ShutterDevice

from ._utils import SafetyButton


class ShutterButton(SafetyButton):
    """Shutter open/close button with a safety countdown."""

    def __init__(
        self,
        device_name: str,
        parent: QWidget | None = None,
        mmcore: CMMCorePlus | None = None,
    ) -> None:
        super().__init__(parent=parent)
        self._mmcore = mmcore or CMMCorePlus.instance()
        self._device_name = device_name
        self._dev: ShutterDevice | None = None

        text_color = (
            QApplication.palette()
            .color(QPalette.ColorGroup.Active, QPalette.ColorRole.Text)
            .name()
        )
        self.off_icon = QIconifyIcon("mdi:hexagon-slice-6", color=text_color)
        self.on_icon = QIconifyIcon("mdi:hexagon-outline")

        self.toggled.connect(self._on_toggled)
        self._mmcore.events.systemConfigurationLoaded.connect(self._try_enable)
        self._mmcore.events.shutterOpenChanged.connect(self._on_property_change)
        self._try_enable()

    def _try_enable(self) -> None:
        enabled = self._device_name in self._mmcore.getLoadedDevices()
        self.setEnabled(enabled)
        if enabled:
            self._dev = self._mmcore.getDeviceObject(self._device_name, ShutterDevice)
        else:
            self._dev = None

    def _on_property_change(self, device_name: str, open: bool) -> None:
        if device_name != self._device_name:
            return
        with signals_blocked(self):
            self.setChecked(open)

    def _on_toggled(self, checked: bool) -> None:
        if self.isEnabled() and self._dev:
            if checked:
                try:
                    self._dev.open()
                except RuntimeError as e:
                    # The device adapter prevents opening the shutter before turning on
                    # the laser
                    with signals_blocked(self):
                        self.setChecked(False)
                    raise e
            else:
                self._dev.close()
