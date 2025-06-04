from pymmcore_plus import CMMCorePlus, Device, DeviceProperty
from qtpy.QtWidgets import (
    QComboBox,
    QFormLayout,
    QWidget,
)
from superqt import QLabeledDoubleSlider
from superqt.utils import signals_blocked


class ImageCollectionParameters(QWidget):
    """Widget controlling OpenScan Image Collection parameters."""

    def __init__(
        self, *, parent: QWidget | None = None, mmcore: CMMCorePlus | None = None
    ) -> None:
        super().__init__(parent)
        self._mmcore = mmcore or CMMCorePlus.instance()
        self._dev: Device | None = None
        self._res_prop: DeviceProperty | None = None

        # -- Widgets --
        self._resolution = QComboBox()
        self._zoom = QLabeledDoubleSlider()
        self._px_rate = QComboBox()

        # -- Layout --
        self._layout = QFormLayout(self)
        self._layout.addRow("Resolution: ", self._resolution)
        self._layout.addRow("Zoom Factor: ", self._zoom)
        self._layout.addRow("Pixel Time: ", self._px_rate)

        # -- Signals --
        self._resolution.currentIndexChanged.connect(self._update_resolution)
        self._zoom.valueChanged.connect(self._update_zoom)
        self._px_rate.currentIndexChanged.connect(self._update_px_rate)

        self._mmcore.events.systemConfigurationLoaded.connect(self._try_enable)
        self._try_enable()

    def _try_enable(self) -> None:
        dev_present = "OSc-LSM" in self._mmcore.getLoadedDevices()

        # Reset the component widgets
        self._resolution.setEnabled(dev_present)
        self._zoom.setEnabled(dev_present)
        self._px_rate.setEnabled(dev_present)

        with signals_blocked(self._resolution):
            self._resolution.clear()
        with signals_blocked(self._zoom):
            self._zoom.setValue(1.0)
        with signals_blocked(self._px_rate):
            self._px_rate.clear()

        # Done if device isn't present
        if not dev_present:
            self._dev = None
            return

        # Grab ref to device
        self._dev = self._mmcore.getDeviceObject("OSc-LSM")
        # Init resolution combo box
        self._res_prop = self._dev.getPropertyObject("LSM-Resolution")
        with signals_blocked(self._resolution):
            for val in self._res_prop.allowedValues():
                self._resolution.addItem(f"{val} x {val}")
            starting_value = self._res_prop.value
            self._resolution.setCurrentText(f"{starting_value} x {starting_value}")
        # Init zoom slider
        with signals_blocked(self._zoom):
            zoom_prop = self._dev.getPropertyObject("LSM-ZoomFactor")
            self._zoom.setRange(
                int(zoom_prop.lowerLimit()), int(zoom_prop.upperLimit())
            )
            self._zoom.setValue(zoom_prop.value)
        # Init pixel rate combo box
        with signals_blocked(self._px_rate):
            px_rate_prop = self._dev.getPropertyObject("LSM-PixelRateHz")
            self._rates = sorted(px_rate_prop.allowedValues(), key=lambda x: float(x))
            for rate in self._rates:
                rate_us = (1 / float(rate)) * 1e6
                self._px_rate.addItem(f"{round(rate_us, 1)} μs", rate)
            current_rate_us = (1 / float(px_rate_prop.value)) * 1e6
            self._px_rate.setCurrentText(f"{round(current_rate_us, 1)} μs")

    def _update_resolution(self, idx: int) -> None:
        if self._dev is not None and self._res_prop is not None:
            self._mmcore.setProperty(
                self._dev.label, "LSM-Resolution", self._res_prop.allowedValues()[idx]
            )

    def _update_zoom(self, value: float) -> None:
        if self._dev is not None:
            self._mmcore.setProperty(self._dev.label, "LSM-ZoomFactor", value)

    def _update_px_rate(self, idx: int) -> None:
        if self._dev is not None:
            self._mmcore.setProperty(
                self._dev.label, "LSM-PixelRateHz", self._px_rate.itemData(idx)
            )
