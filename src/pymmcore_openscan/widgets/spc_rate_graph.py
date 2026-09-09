from pymmcore_plus import CMMCorePlus, Device, DeviceProperty
from qtpy.QtCore import QTimer
from qtpy.QtGui import QColor
from qtpy.QtWidgets import QVBoxLayout, QWidget

from pymmcore_openscan.widgets._scrolling_plot import _ScrollingPlotWidget

MAX_POWER = 8

RATES = [
    "Sync",
    "CFD",
    "TAC",
    "ADC",
]

# Rate colors chosen for:
# 1) Good contrast with both light and dark themes
# 2) Colorblind accessibility (tested against protanopia, deuteranopia, tritanopia)
#    https://davidmathlogic.com/colorblind/#%23D81B60-%23FFC107-%231E88E5-%2376AB10
COLORS = [
    QColor(216, 27, 96),  # Red
    QColor(255, 193, 7),  # Yellow
    QColor(30, 136, 229),  # Blue
    QColor(118, 171, 16),  # Green
]


class SPCRateGraph(QWidget):
    """Widget displaying SPC Rate Graph with controls."""

    def __init__(
        self, *, parent: QWidget | None = None, mmcore: CMMCorePlus | None = None
    ) -> None:
        super().__init__(parent=parent)
        self._mmcore = mmcore or CMMCorePlus.instance()
        self.setMinimumWidth(300)
        self.setMinimumHeight(300)

        self._dev: Device | None = None
        self._values: dict[str, DeviceProperty] = {}

        self._graph = _ScrollingPlotWidget(
            y_label="Rate",
            y_units="Hz",
            y_si_prefix=False,
            y_axis_side="right",
            y_range=(1, MAX_POWER),
            log_y=True,
            legend=True,
            default_window_s=10,
        )
        for rate, color in zip(RATES, COLORS, strict=True):
            self._graph.add_curve(rate, color, name=rate)

        layout = QVBoxLayout(self)
        layout.addWidget(self._graph)

        t = QTimer(self)
        t.setInterval(100)
        t.timeout.connect(self._on_rates)
        t.start()

        self._mmcore.events.systemConfigurationLoaded.connect(self._on_conf_loaded)
        self._on_conf_loaded()

    def _on_conf_loaded(self) -> None:
        """Handle configuration loaded event."""
        self._dev = None
        self._values.clear()
        self._graph.clear()

        if "OSc-LSM" in self._mmcore.getLoadedDevices():
            dev = self._mmcore.getDeviceObject("OSc-LSM")
            self._dev = dev
            for rate in RATES:
                name = f"BH-TCSPC-RateCounter-{rate}"
                if name in dev.propertyNames():
                    self._values[rate] = dev.getPropertyObject(name)

    def _on_rates(self) -> None:
        """Poll rates and update the graph."""
        for rate, prop in self._values.items():
            value = prop.value
            # Clamp to the log-scale floor.
            self._graph.append(rate, max(value, 10))
