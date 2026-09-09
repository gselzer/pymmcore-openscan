from __future__ import annotations

from pymmcore_plus import CMMCorePlus
from qtpy.QtGui import QPalette
from qtpy.QtWidgets import QGroupBox, QVBoxLayout, QWidget

from pymmcore_openscan.widgets._scrolling_plot import _ScrollingPlotWidget

from ._utils import _DEVICE_NAME, _PollingWorker

_POWER_PROP = "Laser Power (W)"


class LaserPowerGraph(QGroupBox):
    """Time-series of laser output power."""

    def __init__(
        self,
        parent: QWidget | None = None,
        mmcore: CMMCorePlus | None = None,
    ) -> None:
        super().__init__("Laser Power", parent)
        self._mmcore = mmcore or CMMCorePlus.instance()

        # TODO: We will likely want to be able to track power over longer time intervals
        self._graph = _ScrollingPlotWidget(
            y_label="Power",
            y_units="W",
            y_range=(0, 3),
            max_points=7200,
            default_window_s=10,
        )
        self._graph.add_curve("power", QPalette.ColorRole.Highlight)

        layout = QVBoxLayout(self)
        layout.addWidget(self._graph)

        self._worker = _PollingWorker(self._mmcore, [(_DEVICE_NAME, _POWER_PROP)])
        self._worker.updated.connect(self._on_updated)

        self._mmcore.events.systemConfigurationLoaded.connect(self._try_enable)
        self._try_enable()

    def _try_enable(self) -> None:
        enabled = _DEVICE_NAME in self._mmcore.getLoadedDevices()
        self.setEnabled(enabled)
        self._graph.clear()
        if enabled:
            self._worker.start()
        else:
            self._worker.stop()

    def _on_updated(self, _: str, prop: str, value: str) -> None:
        if prop != _POWER_PROP:
            return
        try:
            power = float(value)
        except ValueError:
            return
        self._graph.append("power", power)
