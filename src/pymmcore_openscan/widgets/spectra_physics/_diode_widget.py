"""Widgets displaying diode info."""

from __future__ import annotations

from pymmcore_plus import CMMCorePlus
from qtpy.QtWidgets import (
    QFormLayout,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QWidget,
)

from ._utils import _DEVICE_NAME, _PollingWorker


class _DiodePanel(QGroupBox):
    def __init__(
        self, diode_num: int, mmcore: CMMCorePlus, parent: QWidget | None = None
    ) -> None:
        super().__init__(f"Diode {diode_num}", parent)
        self._mmcore = mmcore
        self._diode_num = diode_num

        self._current = QLabel()
        self._temperature = QLabel()
        self._hours = QLabel()

        self._layout = QFormLayout(self)
        self._layout.addRow("Current: ", self._current)
        self._layout.addRow("Temperature: ", self._temperature)
        self._layout.addRow("Accumulated Hours: ", self._hours)

        props = [
            (_DEVICE_NAME, f"Diode {diode_num} Current (A)"),
            (_DEVICE_NAME, f"Diode {diode_num} Temperature (C)"),
            (_DEVICE_NAME, f"Diode {diode_num} Accumulated Hours"),
        ]
        self._worker = _PollingWorker(mmcore, props)
        self._worker.updated.connect(self._on_updated)

        mmcore.events.systemConfigurationLoaded.connect(self._on_system_config_loaded)
        self._on_system_config_loaded()

    def _on_system_config_loaded(self) -> None:
        if _DEVICE_NAME in self._mmcore.getLoadedDevices():
            # NOTE if we ever support Qt<6.4 we'll need an alternative to setRowVisible
            has_current = self._mmcore.hasProperty(
                _DEVICE_NAME, f"Diode {self._diode_num} Current (A)"
            )
            self._layout.setRowVisible(self._current, has_current)
            has_temperature = self._mmcore.hasProperty(
                _DEVICE_NAME, f"Diode {self._diode_num} Temperature (C)"
            )
            self._layout.setRowVisible(self._temperature, has_temperature)
            has_hours = self._mmcore.hasProperty(
                _DEVICE_NAME, f"Diode {self._diode_num} Accumulated Hours"
            )
            self._layout.setRowVisible(self._hours, has_hours)

            self.setVisible(has_current or has_temperature or has_hours)
            self._worker.start()
        else:
            self.setVisible(True)

            self._current.setText("N/A")
            self._temperature.setText("N/A")
            self._hours.setText("N/A")

            self._worker.stop()

    def _on_updated(self, _: str, prop: str, value: str) -> None:
        if "Current" in prop:
            self._current.setText(f"{float(value):.3f} A")
        elif "Temperature" in prop:
            self._temperature.setText(f"{float(value):.1f} °C")
        elif "Accumulated Hours" in prop:
            self._hours.setText(f"{float(value):.1f} h")


class DiodeWidget(QWidget):
    def __init__(
        self,
        parent: QWidget | None = None,
        mmcore: CMMCorePlus | None = None,
    ) -> None:
        super().__init__(parent=parent)
        mmcore = mmcore or CMMCorePlus.instance()

        layout = QHBoxLayout(self)
        layout.addWidget(_DiodePanel(1, mmcore))
        layout.addWidget(_DiodePanel(2, mmcore))
