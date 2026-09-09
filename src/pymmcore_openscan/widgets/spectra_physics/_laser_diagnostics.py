from __future__ import annotations

from pymmcore_plus import CMMCorePlus
from qtpy.QtGui import QPalette
from qtpy.QtWidgets import (
    QApplication,
    QFormLayout,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QProgressBar,
    QVBoxLayout,
    QWidget,
)
from superqt import QIconifyIcon

from ._diode_widget import DiodeWidget
from ._history_buffer import HistoryBufferPanel
from ._power_graph import LaserPowerGraph
from ._utils import _DEVICE_NAME, _PollingWorker

_HUMIDITY_WARNING_THRESHOLD = 5

_PROPS = [
    (_DEVICE_NAME, "Warmup Percentage (%)"),
    (_DEVICE_NAME, "Relative Humidity (%)"),
]


class LaserDiagnosticsPanel(QGroupBox):
    """Displays laser diagnostics."""

    def __init__(
        self,
        parent: QWidget | None = None,
        mmcore: CMMCorePlus | None = None,
    ) -> None:
        super().__init__("Laser Diagnostics", parent)
        self._mmcore = mmcore or CMMCorePlus.instance()

        ## -- WIDGETS -- ##
        self._warmup = QProgressBar()
        self._warmup.setRange(0, 100)
        self._warmup.setFormat("%v%")

        self._humidity = QLabel()
        self._humidity.setText("N/A")
        self._humidity_warning = QLabel()
        accent = (
            QApplication.palette()
            .color(QPalette.ColorGroup.Active, QPalette.ColorRole.Highlight)
            .name()
        )
        self._humidity_warning.setPixmap(
            QIconifyIcon("mdi:warning-outline", color=accent).pixmap(24, 24)
        )
        self._humidity_warning.setToolTip("Humidity above 5% - check the purge unit!")
        self._humidity_warning.setVisible(False)

        self._history = HistoryBufferPanel(mmcore=mmcore)
        self._diodes = DiodeWidget(mmcore=mmcore)
        self._laser_power = LaserPowerGraph(mmcore=mmcore)

        ## -- LAYOUT -- ##
        humidity_row = QHBoxLayout()
        humidity_row.addWidget(self._humidity)
        humidity_row.addWidget(self._humidity_warning)
        humidity_row.addStretch()

        form = QFormLayout()
        form.addRow("System Warmup:", self._warmup)
        form.addRow("Humidity:", humidity_row)

        left_col = QVBoxLayout()
        left_col.addLayout(form)
        left_col.addWidget(self._diodes)
        left_col.addWidget(self._laser_power)
        left_col.addStretch()

        columns = QHBoxLayout()
        columns.addLayout(left_col, stretch=2)
        columns.addWidget(self._history, stretch=1)

        layout = QVBoxLayout(self)
        layout.addLayout(columns)

        ## -- POLLING -- ##
        self._worker = _PollingWorker(self._mmcore, _PROPS)
        self._worker.updated.connect(self._on_updated)

        ## -- INIT -- ##
        self._mmcore.events.systemConfigurationLoaded.connect(self._try_enable)
        self._try_enable()

    def _try_enable(self) -> None:
        enabled = _DEVICE_NAME in self._mmcore.getLoadedDevices()
        self.setEnabled(enabled)
        if enabled:
            self._worker.start()
        else:
            self._worker.stop()

    def _on_updated(self, _: str, prop: str, value: str) -> None:
        if prop == "Warmup Percentage (%)":
            self._warmup.setValue(int(value))
        elif prop == "Relative Humidity (%)":
            humidity = float(value)
            self._humidity.setText(f"{humidity:.1f} %")
            self._humidity_warning.setVisible(humidity > _HUMIDITY_WARNING_THRESHOLD)
