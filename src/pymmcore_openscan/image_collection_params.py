from pymmcore_plus import CMMCorePlus
from qtpy.QtWidgets import (
    QComboBox,
    QFormLayout,
    QWidget,
)
from superqt import QLabeledDoubleSlider


class ImageCollectionParameters(QWidget):
    """Widget controlling OpenScan Image Collection parameters."""

    def __init__(self, mmcore: CMMCorePlus) -> None:
        super().__init__()
        self._mmcore = mmcore
        self._dev = mmcore.getDeviceObject("OSc-LSM")

        # -- Widgets --
        self._res_prop = self._dev.getPropertyObject("LSM-Resolution")
        self._resolution = QComboBox()
        for val in self._res_prop.allowedValues():
            self._resolution.addItem(f"{val} x {val}")

        self._zoom_prop = self._dev.getPropertyObject("LSM-ZoomFactor")
        self._zoom = QLabeledDoubleSlider()
        self._zoom.setRange(self._zoom_prop.lowerLimit(), self._zoom_prop.upperLimit())
        self._zoom.setValue(self._zoom_prop.value)

        self._px_rate_prop = self._dev.getPropertyObject("LSM-PixelRateHz")
        self._rates_choices = sorted(
            ((f"{float(v) / 1e6} μs", v) for v in self._px_rate_prop.allowedValues()),
            key=lambda x: float(x[1]),
        )
        self._px_rate = QComboBox()
        for text, _ in self._rates_choices:
            self._px_rate.addItem(text)

        # -- Layout --
        self._layout = QFormLayout(self)
        self._layout.addRow("Resolution: ", self._resolution)
        self._layout.addRow("Zoom Factor: ", self._zoom)
        self._layout.addRow("Pixel Time: ", self._px_rate)

        # -- Signals --
        self._resolution.currentIndexChanged.connect(self._update_resolution)
        self._zoom.valueChanged.connect(self._update_zoom)
        self._px_rate.currentIndexChanged.connect(self._update_px_rate)

    def _update_resolution(self, idx: int) -> None:
        self._mmcore.setProperty(
            self._dev.label, "LSM-Resolution", self._res_prop.allowedValues()[idx]
        )

    def _update_zoom(self, value: float) -> None:
        self._mmcore.setProperty(self._dev.label, "LSM-ZoomFactor", value)

    def _update_px_rate(self, idx: int) -> None:
        self._mmcore.setProperty(
            self._dev.label, "LSM-PixelRateHz", self._rates_choices[idx][1]
        )
