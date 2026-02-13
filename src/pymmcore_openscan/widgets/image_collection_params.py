from typing import Any

from pymmcore_plus import CMMCorePlus, Device
from qtpy.QtCore import QPointF, Qt
from qtpy.QtGui import QPainter, QPalette, QPen, QPolygonF
from qtpy.QtWidgets import (
    QApplication,
    QComboBox,
    QDoubleSpinBox,
    QFormLayout,
    QLabel,
    QPushButton,
    QSizePolicy,
    QWidget,
)
from superqt.utils import signals_blocked


class _ScaledFOVCanvas(QWidget):
    """Canvas that visualizes the field of view with pixel scaled to FOV."""

    def __init__(
        self, parent: QWidget | None = None, mmcore: CMMCorePlus | None = None
    ) -> None:
        super().__init__(parent)
        self._mmcore = mmcore or CMMCorePlus.instance()

        # Magic numbers
        self._fov_padding = 15  # Default padding between FOV and canvas edge
        self._arrow_length = 6
        self._pixel_base_side_length = 40  #  Side length of pixel for default params

        # The default pixel size (before it is modified by OpenScan Zoom/Resolution)
        # set in self._try_enable
        self._base_pixel_size: float = -1

        self.setMinimumSize(150, 150)
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)

        # FIXME: There's probably something to be done here but I don't know what yet :)
        # For example, we PROBABLY want to reset self._base_pixel_size, but I'm not sure
        # when this would get called.
        # self._mmcore.events.pixelSizeChanged.connect(something)

        # Listen to relevant signals
        events = self._mmcore.events
        events.devicePropertyChanged("OSc-LSM", "LSM-Resolution").connect(self._update)
        events.devicePropertyChanged("OSc-LSM", "LSM-ZoomFactor").connect(self._update)

        # Enable iff OpenScan is present
        self._mmcore.events.systemConfigurationLoaded.connect(self._try_enable)
        self._try_enable()

    def paintEvent(self, a0: object) -> None:
        # ...apparently it's best practice to create one of these each event...
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        font = painter.font()
        font.setPointSize(9)
        painter.setFont(font)

        # First paint FOV visual...
        self._paint_fov(painter)
        # ...and then paint the pixel visual
        self._paint_pixel(painter)
        painter.end()

    def _try_enable(self) -> None:
        self.setEnabled("OSc-LSM" in self._mmcore.getLoadedDevices())
        self._base_pixel_size = self._mmcore.getPixelSizeUm()

    def _update(self, *args: Any, **kwargs: Any) -> None:
        # self.update() doesn't take any of the params that will be passed listening to
        # the core events
        self.update()

    @property
    def _resolution(self) -> int:
        return int(self._mmcore.getProperty("OSc-LSM", "LSM-Resolution"))

    @property
    def _zoom(self) -> float:
        return float(self._mmcore.getProperty("OSc-LSM", "LSM-ZoomFactor"))

    @staticmethod
    def _draw_arrowhead(
        painter: QPainter,
        tip: tuple[float, float],
        base: tuple[float, float],
    ) -> None:
        """Draw a triangular arrowhead.

        Parameters
        ----------
        painter: QPainter
            The painter drawing the arrow.
        tip: tuple[float, float]
            The (x, y) coordinate of the tip of the arrow.
        base: tuple[float, float]
            The (x, y) center of the base edge.
        """
        dx = base[0] - tip[0]
        dy = base[1] - tip[1]
        length = (dx**2 + dy**2) ** 0.5
        half_w = length / 2
        # Perpendicular to tip→base, scaled to half-width
        px, py = -dy / length * half_w, dx / length * half_w
        painter.drawPolygon(
            QPolygonF(
                [
                    QPointF(tip[0], tip[1]),
                    QPointF(base[0] + px, base[1] + py),
                    QPointF(base[0] - px, base[1] - py),
                ]
            )
        )

    def _paint_fov(self, painter: QPainter) -> None:
        """Visualizes FOV information on the canvas."""
        fm = painter.fontMetrics()
        edge_color = QApplication.palette().color(QPalette.ColorRole.WindowText)
        # FOV size: most of the canvas by default, scales with zoom
        fov_side = min(self.width(), self.height()) - 2 * self._fov_padding
        fov_side = int(fov_side / self._zoom)

        # STEP 1: Draw the rectangle
        painter.setPen(QPen(edge_color, 2))
        painter.setBrush(QApplication.palette().mid())
        painter.drawRect(
            (self.width() - fov_side) // 2,
            (self.height() - fov_side) // 2,
            fov_side,
            fov_side,
        )

        # STEP 2: Draw the label
        pixel_size = self._mmcore.getPixelSizeUm()
        if pixel_size := self._mmcore.getPixelSizeUm():
            fov_um = self._resolution * pixel_size
            label = f"FOV: {fov_um:.1f} \u00b5m"
        else:
            label = f"FOV: {self._resolution} px"
        painter.setPen(QPen(edge_color, 1))
        painter.setBrush(Qt.BrushStyle.NoBrush)
        painter.drawText(0, self.height() - fm.descent(), label)

        # STEP 3.1: Witness lines
        # Only drawn if the witness arrow can fit between the text label and the FOV
        fov_left = int((self.width() - fov_side) / 2)
        text_right = fm.horizontalAdvance(label) + 4
        if fov_left < text_right + self._arrow_length:
            return
        witness_y = self.height() - fm.descent() - fm.height() // 2
        # Left witness line
        painter.setPen(QPen(edge_color, 1))
        painter.setBrush(edge_color)
        painter.drawLine(text_right, witness_y, fov_left, witness_y)
        self._draw_arrowhead(
            painter,
            (fov_left, witness_y),  # tip
            (fov_left - self._arrow_length, witness_y),  # base
        )
        # Right witness line
        fov_right = int((self.width() + fov_side) / 2)
        painter.drawLine(fov_right, witness_y, fov_right + 10, witness_y)
        painter.setBrush(edge_color)
        self._draw_arrowhead(
            painter,
            (fov_right, witness_y),
            (fov_right + self._arrow_length, witness_y),
        )

        # STEP 3.2: Dashed lines to pixel
        midlight = QApplication.palette().color(QPalette.ColorRole.Midlight)
        dash_pen = QPen(midlight, 1, Qt.PenStyle.DashLine)
        painter.setPen(dash_pen)
        fov_bottom = int((self.height() + fov_side) / 2)
        painter.drawLine(int(fov_left), int(fov_bottom), int(fov_left), witness_y)
        painter.drawLine(int(fov_right), int(fov_bottom), int(fov_right), witness_y)

    def _paint_pixel(self, painter: QPainter) -> None:
        """Visualizes pixel information on the canvas."""
        fm = painter.fontMetrics()
        accent_color = QApplication.palette().color(QPalette.ColorRole.Accent)
        # Pixel size: scales with pixel size(zoom & resolution)
        zoom_factor = self._base_pixel_size / self._mmcore.getPixelSizeUm()
        pixel_side = self._pixel_base_side_length // zoom_factor

        # STEP 1: Draw the rectangle
        painter.setPen(QPen(accent_color, 2))
        painter.setBrush(QApplication.palette().highlight())
        painter.drawRect(
            int((self.width() - pixel_side) // 2),  # x
            int((self.height() - pixel_side) // 2),  # y
            int(pixel_side),  # w
            int(pixel_side),  # h
        )

        # STEP 2: Draw the label
        pixel_size = self._mmcore.getPixelSizeUm()
        if pixel_size == 0:
            # FIXME: Log a warning?
            return
        label = f"Pixel: {pixel_size:.2g} \u00b5m"
        painter.setPen(QPen(accent_color, 1))
        painter.setBrush(Qt.BrushStyle.NoBrush)
        painter.drawText(0, fm.ascent(), label)

        # STEP 3.1: Witness lines
        # Only drawn if the witness arrow can fit between the text label and the pixel
        px_left = int((self.width() - pixel_side) / 2)
        text_right = fm.horizontalAdvance(label) + 4
        if px_left < text_right + self._arrow_length:
            return
        witness_y = fm.height() // 2
        # Left witness line
        painter.setPen(QPen(accent_color, 1))
        painter.setBrush(accent_color)
        painter.drawLine(text_right, witness_y, px_left, witness_y)
        self._draw_arrowhead(
            painter,
            (px_left, witness_y),  # tip
            (px_left - self._arrow_length, witness_y),  # base
        )
        # Right witness line
        px_right = int((self.width() + pixel_side) / 2)
        painter.drawLine(px_right, witness_y, px_right + 10, witness_y)
        painter.setBrush(accent_color)
        self._draw_arrowhead(
            painter,
            (px_right, witness_y),
            (px_right + self._arrow_length, witness_y),
        )

        # STEP 3.2: Dashed lines to pixel
        midlight = QApplication.palette().color(QPalette.ColorRole.Midlight)
        dash_pen = QPen(midlight, 1, Qt.PenStyle.DashLine)
        painter.setPen(dash_pen)
        px_top = int((self.height() - pixel_side) / 2)
        painter.drawLine(int(px_left), int(px_top), int(px_left), witness_y)
        painter.drawLine(int(px_right), int(px_top), int(px_right), witness_y)


class OpenScanParameters(QWidget):
    """Widget controlling OpenScan Image Collection parameters.

    TODO: Add
        * ROI
            - optional, kinda orthogonal to the others
        * Frame Scan time?
            - Trickier because depends on retrace time
    """

    def __init__(
        self, *, parent: QWidget | None = None, mmcore: CMMCorePlus | None = None
    ) -> None:
        super().__init__(parent)
        self._mmcore = mmcore or CMMCorePlus.instance()
        self._dev: Device | None = None

        # -- Widgets -- #
        self._layout = QFormLayout(self)

        self._resolution = QComboBox()
        self._resolution.currentIndexChanged.connect(self._set_resolution_in_core)
        self._layout.addRow("Resolution: ", self._resolution)

        self._zoom = QDoubleSpinBox()
        self._zoom.setSingleStep(0.25)
        self._zoom.valueChanged.connect(self._set_zoom_in_core)
        self._layout.addRow("Zoom Factor: ", self._zoom)

        self._px_time = QComboBox()
        self._px_time.currentIndexChanged.connect(self._set_px_time_in_core)
        self._layout.addRow("Pixel Time: ", self._px_time)

        self._px_rate = QComboBox()
        self._px_rate.currentIndexChanged.connect(self._set_px_rate_in_core)
        self._layout.addRow("Pixel Rate: ", self._px_rate)

        self._line_scan_time = QLabel()
        self._layout.addRow("Line Scan Time: ", self._line_scan_time)

        self._show_canvas = QPushButton("Show")
        self._show_canvas.setCheckable(True)
        self._show_canvas.toggled.connect(self._toggle_canvas_visibility)
        self._layout.addRow("Visual: ", self._show_canvas)

        self._canvas = _ScaledFOVCanvas(mmcore=self._mmcore)
        self._toggle_canvas_visibility(False)
        self._layout.addRow(self._canvas)

        # -- Initialization & Signals -- #
        events = self._mmcore.events
        events.systemConfigurationLoaded.connect(self._try_enable)
        events.devicePropertyChanged("OSc-LSM", "LSM-Resolution").connect(
            self._sync_resolution_from_core
        )
        events.devicePropertyChanged("OSc-LSM", "LSM-ZoomFactor").connect(
            self._sync_zoom_from_core
        )
        events.devicePropertyChanged("OSc-LSM", "LSM-PixelRateHz").connect(
            self._sync_px_rate_from_core
        )
        self._try_enable()

    def _toggle_canvas_visibility(self, toggled: bool) -> None:
        self._show_canvas.setChecked(toggled)
        self._show_canvas.setText("Hide" if toggled else "Show")
        self._canvas.setVisible(toggled)

    def _try_enable(self) -> None:
        dev_present = "OSc-LSM" in self._mmcore.getLoadedDevices()

        # Reset the component widgets
        self._resolution.setEnabled(dev_present)
        with signals_blocked(self._resolution):
            self._resolution.clear()

        self._zoom.setEnabled(dev_present)
        with signals_blocked(self._zoom):
            self._zoom.setValue(1.0)

        self._px_time.setEnabled(dev_present)
        with signals_blocked(self._px_time):
            self._px_time.clear()

        self._px_rate.setEnabled(dev_present)
        with signals_blocked(self._px_rate):
            self._px_rate.clear()

        self._line_scan_time.setEnabled(dev_present)
        self._line_scan_time.clear()

        self._show_canvas.setEnabled(dev_present)
        # Hide the canvas if shown and no OpenScan
        if self._show_canvas.isChecked() and not dev_present:
            self._show_canvas.setChecked(False)

        # Done if device isn't present
        if not dev_present:
            self._dev = None
            return

        # Grab ref to device
        self._dev = self._mmcore.getDeviceObject("OSc-LSM")
        # Init resolution combo box
        self._res_prop = self._dev.getPropertyObject("LSM-Resolution")
        resolutions = sorted(self._res_prop.allowedValues(), key=lambda x: float(x))
        with signals_blocked(self._resolution):
            for res in resolutions:
                self._resolution.addItem(f"{res} x {res}", res)
            self._sync_resolution_from_core(self._res_prop.value)
        # Init zoom slider
        with signals_blocked(self._zoom):
            zoom_prop = self._dev.getPropertyObject("LSM-ZoomFactor")
            self._zoom.setRange(zoom_prop.lowerLimit(), zoom_prop.upperLimit())
            self._zoom.setValue(zoom_prop.value)
            self._sync_zoom_from_core(zoom_prop.value)
        # Init pixel rate combo box
        px_rate_prop = self._dev.getPropertyObject("LSM-PixelRateHz")
        rates = sorted(px_rate_prop.allowedValues(), key=lambda x: float(x))
        with signals_blocked(self._px_time):
            with signals_blocked(self._px_rate):
                # Add rates to pixel time
                for rate in rates:
                    rate_us = 1e6 / float(rate)
                    self._px_time.addItem(f"{round(rate_us, 1)} μs", rate)
                    self._px_rate.addItem(f"{float(rate)} Hz", rate)
                self._sync_px_rate_from_core(px_rate_prop.value)

    ## -- Update core from widget -- ##

    def _set_resolution_in_core(self, idx: int) -> None:
        if self._dev is not None:
            self._mmcore.setProperty(
                self._dev.label, "LSM-Resolution", self._resolution.itemData(idx)
            )

    def _set_zoom_in_core(self, value: float) -> None:
        if self._dev is not None:
            self._mmcore.setProperty(self._dev.label, "LSM-ZoomFactor", value)

    def _set_px_time_in_core(self, idx: int) -> None:
        if self._dev is not None:
            self._mmcore.setProperty(
                self._dev.label, "LSM-PixelRateHz", self._px_time.itemData(idx)
            )

    def _set_px_rate_in_core(self, idx: int) -> None:
        if self._dev is not None:
            self._mmcore.setProperty(
                self._dev.label, "LSM-PixelRateHz", self._px_rate.itemData(idx)
            )

    ## -- Update widget from core -- ##

    def _sync_resolution_from_core(self, value: str) -> None:
        with signals_blocked(self._resolution):
            if (idx := self._resolution.findData(value)) > -1:
                self._resolution.setCurrentIndex(idx)
        self._update_line_scan_time()

    def _sync_zoom_from_core(self, zoom: str) -> None:
        with signals_blocked(self._zoom):
            self._zoom.setValue(float(zoom))

    def _sync_px_rate_from_core(self, px_rate: str) -> None:
        with signals_blocked(self._px_time):
            if (idx := self._px_time.findData(px_rate)) > -1:
                self._px_time.setCurrentIndex(idx)
        with signals_blocked(self._px_rate):
            if (idx := self._px_rate.findData(px_rate)) > -1:
                self._px_rate.setCurrentIndex(idx)
        self._update_line_scan_time()

    def _update_line_scan_time(self) -> None:
        if self._dev is not None:
            px_rate = float(self._dev.getProperty("LSM-PixelRateHz"))
            res = int(self._dev.getProperty("LSM-Resolution"))
            line_time = res / px_rate * 1e6
            self._line_scan_time.setText(f"{line_time:.1f} μs")
