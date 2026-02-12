from pymmcore_plus import CMMCorePlus, Device
from qtpy.QtCore import QPointF, Qt
from qtpy.QtGui import QColor, QPainter, QPalette, QPen, QPolygonF
from qtpy.QtWidgets import (
    QApplication,
    QComboBox,
    QFormLayout,
    QLabel,
    QPushButton,
    QSizePolicy,
    QWidget,
)
from superqt import QLabeledDoubleSlider
from superqt.utils import signals_blocked

MIN_PIXEL_SIZE = 1


class _FOVCanvas(QWidget):
    """Canvas that visualizes the field of view."""

    def __init__(
        self, parent: QWidget | None = None, mmcore: CMMCorePlus | None = None
    ) -> None:
        super().__init__(parent)
        self._mmcore = mmcore or CMMCorePlus.instance()
        self._resolution: int = 512
        self._pixel_size: float | None = self._mmcore.getPixelSizeUm()
        self._padding = 10  # Minimum number of pixels between FOV box and widget edge

        self.setMinimumSize(150, 150)
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)

        self._mmcore.events.pixelSizeChanged.connect(self._update_pixel_size)
        self._mmcore.events.systemConfigurationLoaded.connect(self._try_enable)
        self._try_enable()

    def _try_enable(self) -> None:
        dev_present = "OSc-LSM" in self._mmcore.getLoadedDevices()
        self.setEnabled(dev_present)

        self._mmcore.events.devicePropertyChanged("OSc-LSM", "LSM-Resolution").connect(
            self._update_resolution
        )

        if not dev_present:
            return

        self._mmcore.events.devicePropertyChanged("OSc-LSM", "LSM-Resolution").connect(
            self._update_resolution
        )

    def _update_pixel_size(self, new_size: float) -> None:
        self._pixel_size = new_size
        self.update()

    def _update_resolution(self, resolution: str) -> None:
        self._resolution = int(resolution)
        self.update()

    def paintEvent(self, a0: object) -> None:
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        # Determine the side length
        side = min(self.width(), self.height()) - 2 * self._padding

        self._paint_fov(painter, side)
        self._paint_dimensions(painter, side)

    def _paint_fov(self, painter: QPainter, side_length: int) -> None:
        painter.setPen(QPen(QColor(180, 180, 180), 2))
        painter.setBrush(QColor(40, 40, 40))
        painter.drawRect(self._padding, self._padding, side_length, side_length)

    def _paint_dimensions(self, painter: QPainter, side_length: int) -> None:
        # Set the font size
        font = painter.font()
        font.setPointSize(9)
        painter.setFont(font)
        fm = painter.fontMetrics()
        label_h = fm.height()

        if self._pixel_size:
            fov_um = self._resolution * self._pixel_size
            label = f"{fov_um:.1f} \u00b5m ({self._resolution} px)"
        else:
            label = f"{self._resolution} px"

        # Width dimension (along bottom edge)
        bot_y = self._padding + side_length - 4 - label_h
        self._paint_bot_y = bot_y
        painter.save()
        painter.translate(self._padding, bot_y)
        self._paint_dimension(painter, side_length, label)
        painter.restore()

        # Height dimension (along right edge, same thing but rotated)
        right_x = self._padding + side_length - 4 - label_h
        painter.save()
        painter.translate(right_x, self._padding + side_length)
        painter.rotate(-90)
        self._paint_dimension(painter, side_length, label)
        painter.restore()

        painter.end()

    def _paint_dimension(self, painter: QPainter, length: int, label: str) -> None:
        """Draw a horizontal dimension line in the painter's current coordinate system.

        Assumes the painter has been translated (and optionally rotated) so that
        the dimension runs along the x-axis from 0 to ``length``, with text
        centered vertically at y=0..text_h.
        """
        fm = painter.fontMetrics()
        text_h = fm.height()
        label_w = fm.horizontalAdvance(label)
        dim_color = QColor(180, 180, 180)
        dim_pen = QPen(dim_color, 1)
        arrow_size = 6
        inset = 14

        line_y = text_h // 2
        left_x = inset
        right_x = length - inset
        center_x = length // 2

        # Lines from arrows to label gap
        painter.setPen(dim_pen)
        painter.drawLine(left_x, line_y, center_x - label_w // 2 - 4, line_y)
        painter.drawLine(center_x + label_w // 2 + 4, line_y, right_x, line_y)

        # Left arrow
        painter.setBrush(dim_color)
        painter.drawPolygon(
            QPolygonF(
                [
                    QPointF(left_x, line_y),
                    QPointF(left_x + arrow_size, line_y - arrow_size / 2),
                    QPointF(left_x + arrow_size, line_y + arrow_size / 2),
                ]
            )
        )
        # Right arrow
        painter.drawPolygon(
            QPolygonF(
                [
                    QPointF(right_x, line_y),
                    QPointF(right_x - arrow_size, line_y - arrow_size / 2),
                    QPointF(right_x - arrow_size, line_y + arrow_size / 2),
                ]
            )
        )

        # Label text
        painter.setBrush(Qt.BrushStyle.NoBrush)
        painter.setPen(dim_color)
        painter.drawText(
            0,
            0,
            length,
            text_h,
            Qt.AlignmentFlag.AlignHCenter | Qt.AlignmentFlag.AlignVCenter,
            label,
        )


class _FOVCanvasZoomable(QWidget):
    """Canvas that visualizes the field of view."""

    def __init__(
        self, parent: QWidget | None = None, mmcore: CMMCorePlus | None = None
    ) -> None:
        super().__init__(parent)
        self._mmcore = mmcore or CMMCorePlus.instance()
        self._resolution: int = 512
        self._pixel_size: float | None = self._mmcore.getPixelSizeUm()
        self._zoom: float = 1.0
        self._padding = 10  # Minimum number of pixels between FOV box and widget edge
        self._pixel_side = 40

        self.setMinimumSize(150, 150)
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        self.setToolTip("Note: Not to scale")

        self._mmcore.events.pixelSizeChanged.connect(self._update_pixel_size)
        self._mmcore.events.systemConfigurationLoaded.connect(self._try_enable)
        self._try_enable()

    def _try_enable(self) -> None:
        dev_present = "OSc-LSM" in self._mmcore.getLoadedDevices()
        self.setEnabled(dev_present)

        if not dev_present:
            return

        self._mmcore.events.devicePropertyChanged("OSc-LSM", "LSM-Resolution").connect(
            self._update_resolution
        )
        self._mmcore.events.devicePropertyChanged("OSc-LSM", "LSM-ZoomFactor").connect(
            self._update_zoom
        )

    def _update_pixel_size(self, new_size: float) -> None:
        self._pixel_size = new_size
        self.update()

    def _update_resolution(self, resolution: str) -> None:
        self._resolution = int(resolution)
        self.update()

    def _update_zoom(self, zoom: str) -> None:
        self._zoom = float(zoom)
        self.update()

    def paintEvent(self, a0: object) -> None:
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        # Determine the side length
        side = min(self.width(), self.height()) - 2 * self._padding
        side = int(side / self._zoom)

        self._paint_fov(painter, side)
        self._paint_dimensions(painter, side)

    def _paint_fov(self, painter: QPainter, side_length: int) -> None:
        painter.setPen(
            QPen(QApplication.palette().color(QPalette.ColorRole.WindowText), 1)
        )
        painter.setBrush(QApplication.palette().mid())
        painter.drawRect(
            (self.width() - side_length) // 2,
            (self.height() - side_length) // 2,
            side_length,
            side_length,
        )

        painter.drawLine(
            self.width() // 2 - (self._pixel_side // 2),
            self.height() // 2 - self._pixel_side,
            self.width() // 2 - (self._pixel_side // 2),
            self.height() // 2 + self._pixel_side,
        )
        painter.drawLine(
            self.width() // 2 + (self._pixel_side // 2),
            self.height() // 2 - self._pixel_side,
            self.width() // 2 + (self._pixel_side // 2),
            self.height() // 2 + self._pixel_side,
        )
        painter.drawLine(
            self.width() // 2 - self._pixel_side,
            self.height() // 2 - (self._pixel_side // 2),
            self.width() // 2 + self._pixel_side,
            self.height() // 2 - (self._pixel_side // 2),
        )
        painter.drawLine(
            self.width() // 2 - self._pixel_side,
            self.height() // 2 + (self._pixel_side // 2),
            self.width() // 2 + self._pixel_side,
            self.height() // 2 + (self._pixel_side // 2),
        )
        painter.setPen(QPen(QApplication.palette().color(QPalette.ColorRole.Accent), 2))
        painter.setBrush(QApplication.palette().highlight())
        painter.drawRect(
            self.width() // 2 - (self._pixel_side // 2),
            self.height() // 2 - (self._pixel_side // 2),
            self._pixel_side,
            self._pixel_side,
        )

        # "FOV" label in top-left corner of FOV rectangle
        font = painter.font()
        font.setPointSize(9)
        painter.setFont(font)
        fm = painter.fontMetrics()
        fov_x = (self.width() - side_length) // 2
        fov_y = (self.height() - side_length) // 2
        text_margin = 4
        painter.setPen(QApplication.palette().color(QPalette.ColorRole.WindowText))
        painter.setBrush(Qt.BrushStyle.NoBrush)
        painter.drawText(fov_x + text_margin, fov_y + text_margin + fm.ascent(), "FOV")

        # "Pixel" label centered in the pixel square
        px_x = self.width() // 2 - (self._pixel_side // 2)
        px_y = self.height() // 2 - (self._pixel_side // 2)
        painter.setPen(QApplication.palette().color(QPalette.ColorRole.Accent))
        painter.drawText(
            px_x,
            px_y,
            self._pixel_side,
            self._pixel_side,
            Qt.AlignmentFlag.AlignHCenter | Qt.AlignmentFlag.AlignVCenter,
            "Pixel",
        )

    def _paint_dimensions(self, painter: QPainter, side_length: int) -> None:
        # Set the font size
        font = painter.font()
        font.setPointSize(9)
        painter.setFont(font)
        fm = painter.fontMetrics()
        label_h = fm.height()

        if pixel_size := self._mmcore.getPixelSizeUm():
            fov_um = self._resolution * pixel_size
            label = f"{fov_um:.1f} \u00b5m"
            # label = f"{fov_um:.1f} \u00b5m ({self._resolution} px)"
        else:
            label = f"{self._resolution} px"

        # FOV Width dimension (along bottom edge)
        left = (self.width() - side_length) // 2
        bottom = (self.height() + side_length) // 2 - 4 - label_h
        painter.save()
        painter.translate(left, bottom)
        self._paint_dimension(painter, side_length, label)
        painter.restore()

        # FOV Height dimension (along right edge, same thing but rotated)
        right = (self.width() + side_length) // 2 - 4 - label_h
        painter.save()
        painter.translate(right, self.height() // 2 + side_length // 2)
        painter.rotate(-90)
        self._paint_dimension(painter, side_length, label)
        painter.restore()

        if pixel_size := self._mmcore.getPixelSizeUm():
            label = f"{pixel_size:.2g} \u00b5m"
            # label = f"{pixel_size:.2g} \u00b5m ({self._resolution} px)"
        else:
            label = f"{self._resolution} px"

        # Pixel Width dimension (along bottom edge)
        left = (self.width() - self._pixel_side) // 2
        bottom = (self.height() + self._pixel_side) // 2 + 4
        painter.save()
        painter.translate(left, bottom)
        self._paint_dimension(painter, self._pixel_side, label, inward=True)
        painter.restore()

        painter.end()

    def _paint_dimension(
        self,
        painter: QPainter,
        length: int,
        label: str,
        inward: bool = False,
    ) -> None:
        """Draw a horizontal dimension line in the painter's current coordinate system.

        Assumes the painter has been translated (and optionally rotated) so that
        the dimension runs along the x-axis from 0 to ``length``, with text
        centered vertically at y=0..text_h.

        When *inward* is True, the arrows point towards each other and the
        lines extend outside the measured segment.
        """
        fm = painter.fontMetrics()
        text_h = fm.height()
        label_w = fm.horizontalAdvance(label)
        dim_color = QColor(180, 180, 180)
        dim_pen = QPen(dim_color, 1)
        arrow_size = 6
        inset = 14

        line_y = text_h // 2
        left_x = inset
        right_x = length - inset
        center_x = length // 2

        painter.setPen(dim_pen)

        if inward:
            # Lines extend outside the segment
            painter.drawLine(-inset, line_y, 0, line_y)
            painter.drawLine(length, line_y, length + inset, line_y)

            # Left arrow pointing right (inward), tip at 0
            painter.setBrush(dim_color)
            painter.drawPolygon(
                QPolygonF(
                    [
                        QPointF(0, line_y),
                        QPointF(-arrow_size, line_y - arrow_size / 2),
                        QPointF(-arrow_size, line_y + arrow_size / 2),
                    ]
                )
            )
            # Right arrow pointing left (inward), tip at length
            painter.drawPolygon(
                QPolygonF(
                    [
                        QPointF(length, line_y),
                        QPointF(length + arrow_size, line_y - arrow_size / 2),
                        QPointF(length + arrow_size, line_y + arrow_size / 2),
                    ]
                )
            )
        else:
            # Lines from arrows to label gap
            painter.drawLine(left_x, line_y, center_x - label_w // 2 - 4, line_y)
            painter.drawLine(center_x + label_w // 2 + 4, line_y, right_x, line_y)

            # Left arrow pointing left (outward)
            painter.setBrush(dim_color)
            painter.drawPolygon(
                QPolygonF(
                    [
                        QPointF(left_x, line_y),
                        QPointF(left_x + arrow_size, line_y - arrow_size / 2),
                        QPointF(left_x + arrow_size, line_y + arrow_size / 2),
                    ]
                )
            )
            # Right arrow pointing right (outward)
            painter.drawPolygon(
                QPolygonF(
                    [
                        QPointF(right_x, line_y),
                        QPointF(right_x - arrow_size, line_y - arrow_size / 2),
                        QPointF(right_x - arrow_size, line_y + arrow_size / 2),
                    ]
                )
            )

        # Label text
        painter.setBrush(Qt.BrushStyle.NoBrush)
        painter.setPen(dim_color)
        painter.drawText(
            0,
            0,
            length,
            text_h,
            Qt.AlignmentFlag.AlignHCenter | Qt.AlignmentFlag.AlignVCenter,
            label,
        )


class _FOVCanvasWithInset(_FOVCanvas):
    """FOV canvas with a zoomed inset showing pixel detail."""

    def paintEvent(self, a0: object) -> None:
        super().paintEvent(a0)

        side = min(self.width(), self.height()) - 2 * self._padding
        fov_x = self._padding
        fov_y = self._padding
        px_size = max(side / self._resolution, MIN_PIXEL_SIZE)

        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        font = painter.font()
        font.setPointSize(9)
        painter.setFont(font)
        fm = painter.fontMetrics()
        text_h = fm.height()
        arrow_size = 6
        dim_color = QColor(180, 180, 180)
        dim_pen = QPen(dim_color, 1)

        # Blue pixel rectangle in top-left of FOV
        painter.setPen(QPen(QColor(0, 180, 255), 2))
        painter.setBrush(QColor(0, 180, 255, 80))
        painter.drawRect(fov_x, fov_y, int(px_size), int(px_size))

        # Inset layout (centered in the FOV)
        inset_side = side // 3
        inset_x = fov_x + (side - inset_side) // 2
        inset_y = fov_y + (side - inset_side) // 2

        # Callout lines from actual pixel to inset
        painter.setPen(QPen(QColor(180, 180, 180, 100), 1, Qt.PenStyle.DashLine))
        painter.setBrush(Qt.BrushStyle.NoBrush)
        px_bottom = fov_y + int(px_size)
        px_right = fov_x + int(px_size)
        painter.drawLine(px_right, fov_y, inset_x + inset_side, inset_y)
        painter.drawLine(fov_x, px_bottom, inset_x, inset_y + inset_side)

        # Inset background
        painter.setPen(QPen(QColor(180, 180, 180), 1))
        painter.setBrush(QColor(30, 30, 30))
        painter.drawRect(inset_x, inset_y, inset_side, inset_side)

        # Enlarged pixel (centered in inset, ~40% of inset size)
        enlarged_px = inset_side * 2 // 5
        epx_x = inset_x + (inset_side - enlarged_px) // 2
        epx_y = inset_y + (inset_side - enlarged_px) // 2
        painter.setPen(QPen(QColor(0, 180, 255), 2))
        painter.setBrush(QColor(0, 180, 255, 80))
        painter.drawRect(epx_x, epx_y, enlarged_px, enlarged_px)

        # Pixel dimension arrows (below the enlarged pixel)
        if self._pixel_size:
            px_label = f"{self._pixel_size:.2f} \u00b5m"
        else:
            px_label = "1 px"
        px_label_w = fm.horizontalAdvance(px_label)
        dim_y = epx_y + enlarged_px + 4 + text_h // 2
        dim_left = epx_x
        dim_right = epx_x + enlarged_px
        dim_cx = (dim_left + dim_right) // 2

        painter.setPen(dim_pen)
        painter.drawLine(dim_left, dim_y, dim_cx - px_label_w // 2 - 4, dim_y)
        painter.drawLine(dim_cx + px_label_w // 2 + 4, dim_y, dim_right, dim_y)
        # Left arrow
        painter.setBrush(dim_color)
        painter.drawPolygon(
            QPolygonF(
                [
                    QPointF(dim_left, dim_y),
                    QPointF(dim_left + arrow_size, dim_y - arrow_size / 2),
                    QPointF(dim_left + arrow_size, dim_y + arrow_size / 2),
                ]
            )
        )
        # Right arrow
        painter.drawPolygon(
            QPolygonF(
                [
                    QPointF(dim_right, dim_y),
                    QPointF(dim_right - arrow_size, dim_y - arrow_size / 2),
                    QPointF(dim_right - arrow_size, dim_y + arrow_size / 2),
                ]
            )
        )
        # Label
        painter.setBrush(Qt.BrushStyle.NoBrush)
        painter.setPen(dim_color)
        painter.drawText(
            dim_left,
            dim_y - text_h // 2,
            enlarged_px,
            text_h,
            Qt.AlignmentFlag.AlignHCenter | Qt.AlignmentFlag.AlignVCenter,
            px_label,
        )

        painter.end()


class _PixelCanvas(_FOVCanvas):
    """Pixel-centric canvas showing a 3x3 grid with FOV dimension annotations."""

    def paintEvent(self, a0: object) -> None:
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        font = painter.font()
        font.setPointSize(9)
        painter.setFont(font)
        fm = painter.fontMetrics()
        text_h = fm.height()

        dim_color = QColor(180, 180, 180)
        dim_pen = QPen(dim_color, 1)
        arrow_size = 6
        tick_half = 5

        # Space for witness line annotations on top and left
        dim_margin = text_h + 16

        # Grid geometry
        available = min(self.width(), self.height()) - 2 * self._padding - dim_margin
        cell = available / 3
        gx = self._padding + dim_margin
        gy = self._padding + dim_margin
        grid_extent = 3 * cell

        # -- Grid lines (omit bottom and right closing borders) --
        painter.setPen(QPen(QColor(120, 120, 120), 1))
        painter.setBrush(Qt.BrushStyle.NoBrush)
        for i in range(3):
            y = int(gy + i * cell)
            painter.drawLine(int(gx), y, int(gx + grid_extent), y)
        for i in range(3):
            x = int(gx + i * cell)
            painter.drawLine(x, int(gy), x, int(gy + grid_extent))

        # -- Blue pixel (top-left cell) --
        painter.setPen(QPen(QColor(0, 180, 255), 2))
        painter.setBrush(QColor(0, 180, 255, 80))
        painter.drawRect(int(gx), int(gy), int(cell), int(cell))

        # -- Pixel size witness line (inside blue cell) --
        if self._pixel_size:
            px_label = f"{self._pixel_size:.2f} \u00b5m"
        else:
            px_label = "1 px"
        painter.save()
        painter.translate(int(gx), int(gy + cell - 4 - text_h))
        self._paint_dimension(painter, int(cell), px_label)
        painter.restore()

        # -- FOV dimension label --
        if self._pixel_size:
            fov_um = self._resolution * self._pixel_size
            fov_label = f"{fov_um:.1f} \u00b5m ({self._resolution} px)"
        else:
            fov_label = f"{self._resolution} px"
        fov_label_w = fm.horizontalAdvance(fov_label)

        # -- Top witness line: tick on left, arrow on right --
        top_y = int(gy - dim_margin // 2)
        left_end = int(gx)
        right_end = int(gx + grid_extent)
        h_center = int(gx + grid_extent / 2)

        painter.setPen(dim_pen)
        painter.drawLine(left_end, top_y, h_center - fov_label_w // 2 - 4, top_y)
        painter.drawLine(h_center + fov_label_w // 2 + 4, top_y, right_end, top_y)

        # Perpendicular tick (left end)
        painter.drawLine(left_end, top_y - tick_half, left_end, top_y + tick_half)

        # Arrow (right end)
        painter.setBrush(dim_color)
        painter.drawPolygon(
            QPolygonF(
                [
                    QPointF(right_end, top_y),
                    QPointF(right_end - arrow_size, top_y - arrow_size / 2),
                    QPointF(right_end - arrow_size, top_y + arrow_size / 2),
                ]
            )
        )

        # Label
        painter.setBrush(Qt.BrushStyle.NoBrush)
        painter.setPen(dim_color)
        painter.drawText(
            left_end,
            top_y - text_h // 2,
            int(grid_extent),
            text_h,
            Qt.AlignmentFlag.AlignHCenter | Qt.AlignmentFlag.AlignVCenter,
            fov_label,
        )

        # -- Left witness line: tick on top, arrow on bottom --
        left_x = int(gx - dim_margin // 2)
        top_end = int(gy)
        bottom_end = int(gy + grid_extent)
        v_center = int(gy + grid_extent / 2)

        painter.setPen(dim_pen)
        painter.drawLine(left_x, top_end, left_x, v_center - fov_label_w // 2 - 4)
        painter.drawLine(left_x, v_center + fov_label_w // 2 + 4, left_x, bottom_end)

        # Perpendicular tick (top end)
        painter.drawLine(left_x - tick_half, top_end, left_x + tick_half, top_end)

        # Arrow (bottom end)
        painter.setBrush(dim_color)
        painter.drawPolygon(
            QPolygonF(
                [
                    QPointF(left_x, bottom_end),
                    QPointF(left_x - arrow_size / 2, bottom_end - arrow_size),
                    QPointF(left_x + arrow_size / 2, bottom_end - arrow_size),
                ]
            )
        )

        # Label (rotated)
        painter.save()
        painter.translate(left_x, v_center)
        painter.rotate(-90)
        painter.setBrush(Qt.BrushStyle.NoBrush)
        painter.setPen(dim_color)
        painter.drawText(
            -int(grid_extent) // 2,
            -text_h // 2,
            int(grid_extent),
            text_h,
            Qt.AlignmentFlag.AlignHCenter | Qt.AlignmentFlag.AlignVCenter,
            fov_label,
        )
        painter.restore()

        painter.end()


class ImageCollectionParameters(QWidget):
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

        # -- Widgets --
        self._resolution = QComboBox()
        self._zoom = QLabeledDoubleSlider()
        self._px_time = QComboBox()
        self._px_rate = QComboBox()
        self._line_scan_time = QLabel()
        self._canvas = _FOVCanvasZoomable(mmcore=self._mmcore)
        self._show_canvas = QPushButton("Show")
        self._show_canvas.setCheckable(True)
        self._show_canvas.toggled.connect(self._toggle_canvas_visibility)
        self._toggle_canvas_visibility(False)

        # -- Layout --
        self._layout = QFormLayout(self)
        self._layout.addRow("Resolution: ", self._resolution)
        self._layout.addRow("Zoom Factor: ", self._zoom)
        self._layout.addRow("Pixel Time: ", self._px_time)
        self._layout.addRow("Pixel Rate: ", self._px_rate)
        self._layout.addRow("Line Scan Time: ", self._line_scan_time)
        self._layout.addRow("Visual: ", self._show_canvas)
        # FIXME: A QCollapsible might be nice here but looks off and
        # self._collapsible = QCollapsible("Visual")
        # self._collapsible.addWidget(self._canvas)
        # self._layout.addRow(self._collapsible)
        self._layout.addRow(self._canvas)

        # -- Signals --
        self._resolution.currentIndexChanged.connect(self._set_resolution_in_core)
        self._zoom.valueChanged.connect(self._set_zoom_in_core)
        self._px_time.currentIndexChanged.connect(self._set_px_time_in_core)
        self._px_rate.currentIndexChanged.connect(self._set_px_rate_in_core)

        self._mmcore.events.systemConfigurationLoaded.connect(self._try_enable)
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

        if self._dev is not None:
            # Disconnect signals from old device
            self._mmcore.events.devicePropertyChanged(
                "OSc-LSM", "LSM-Resolution"
            ).disconnect(self._sync_resolution_from_core)
            self._mmcore.events.devicePropertyChanged(
                "OSc-LSM", "LSM-ZoomFactor"
            ).disconnect(self._sync_zoom_from_core)
            self._mmcore.events.devicePropertyChanged(
                "OSc-LSM", "LSM-PixelRateHz"
            ).disconnect(self._sync_px_rate_from_core)

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
        # Connect signals
        events = self._mmcore.events
        events.devicePropertyChanged("OSc-LSM", "LSM-Resolution").connect(
            self._sync_resolution_from_core
        )
        events.devicePropertyChanged("OSc-LSM", "LSM-ZoomFactor").connect(
            self._sync_zoom_from_core
        )
        events.devicePropertyChanged("OSc-LSM", "LSM-PixelRateHz").connect(
            self._sync_px_rate_from_core
        )

    ## -- Update core from widget -- ##

    def _set_resolution_in_core(self, idx: int) -> None:
        if self._dev is not None and self._res_prop is not None:
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
            line_time_s = res / px_rate
            line_time_ms = line_time_s * 1e6
            self._line_scan_time.setText(f"{line_time_ms:.1f} μs")
