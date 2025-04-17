from math import log10
from typing import Any, cast

from pymmcore_plus import CMMCorePlus, DeviceProperty
from qtpy.QtCore import QLineF, Qt, QTimer
from qtpy.QtGui import QBrush, QColor, QPalette, QPen, QResizeEvent
from qtpy.QtWidgets import (
    QAbstractSpinBox,
    QApplication,
    QDoubleSpinBox,
    QFormLayout,
    QGraphicsRectItem,
    QGraphicsScene,
    QGraphicsSimpleTextItem,
    QGraphicsView,
    QHBoxLayout,
    QLineEdit,
    QSizePolicy,
    QWidget,
)

MAX_POWER = 8
BAR_WIDTH = 10
BAR_HEIGHT = 100

class _StandardFormSpinBox(QDoubleSpinBox):

    def __init__(self, parent: Any = None) -> None:
        super().__init__(parent)
        self.setRange(0, 1e8)
        self.setButtonSymbols(QAbstractSpinBox.ButtonSymbols.NoButtons)
        cast(QLineEdit, self.lineEdit()).setReadOnly(True)

    def textFromValue(self, value: float) -> str:
        # This is a bit of a hack, but it makes the spinbox look like a
        # standard form. The default implementation calls `str(value)` which
        # is not what we want.
        if value == 0:
            return "0.00E0"
        base = int(log10(value))
        prefix = value / 10**base
        return f"{prefix:.2f}E{base}"

class _RateCounter:

    bar_pen = QPen()
    # FIXME: This is just a nice background color, but it may not work well
    # everywhere. It would be nice if the QSlider groove color was exposed,
    # but it's OS dependent and does not correspond to any palette color.
    # Corresponds to the QSlider groove color (but adjusted to be fully opaque)on 
    # Windows 11, Dark mode.
    # (From https://github.com/qt/qtbase/blob/920a490d659836785f03d51edc11da1711ade965/src/plugins/styles/modernwindows/qwindows11style.cpp#L44)
    bar_brush = QBrush(QColor(0x99, 0x99, 0x99, 0xFF))

    def __init__(
            self,
            scene: QGraphicsScene,
            prop: DeviceProperty,
            lbl: str,
            color: QColor | Qt.GlobalColor,
            x: int
        ) -> None:
        self._scene = scene
        self._prop = prop
        self.lbl = lbl
        self._x = x

        self.spinbox = _StandardFormSpinBox()

        self._bar = self._scene.addRect(
            self._x,
            0,
            BAR_WIDTH,
            BAR_HEIGHT,
            self.bar_pen,
            self.bar_brush
        )

        self._brush = QBrush(color)
        self._rect = cast(QGraphicsRectItem, self._scene.addRect(
            self._x,
            BAR_HEIGHT,
            BAR_WIDTH,
            0,
            QPen(),
            self._brush
        ))

        self._lbl_item = cast(QGraphicsSimpleTextItem, self._scene.addSimpleText(lbl))
        # self._lbl_item.setBrush(self._brush)
        self._lbl_item.setPos(
            self._x + (BAR_WIDTH - self._lbl_item.boundingRect().width()) / 2,
            BAR_HEIGHT + self._lbl_item.boundingRect().height() / 2
        )

    def update(self) -> None:
        val = self._prop.value
        self.spinbox.setValue(val)
        # The below function linearly maps the logarithm of the value.
        # 10 -> 0
        # 1e8 -> 100
        new_height = BAR_HEIGHT / (MAX_POWER - 1) * (log10(val)-1)

        r = self._rect.rect()
        r.setY(BAR_HEIGHT - new_height)
        r.setHeight(new_height)
        self._rect.setRect(r)
        self._rect.update()


class _GraphicsFrame(QGraphicsView):

    def __init__(self, scene: QGraphicsScene) -> None:
        super().__init__(scene)
        self._scene = scene
        self.setSizePolicy(QSizePolicy.Policy.Minimum, QSizePolicy.Policy.Minimum)

    
    def resizeEvent(self, event: QResizeEvent | None) -> None:
        self.fitInView(
            self._scene.itemsBoundingRect(),
            Qt.AspectRatioMode.KeepAspectRatio
        )
        return super().resizeEvent(event)


class SPCRateCounters(QWidget):
    """Widget displaying SPC Rate Counters."""

    def __init__(self, mmcore: CMMCorePlus) -> None:
        super().__init__()
        self._mmcore = mmcore
        self._dev = mmcore.getDeviceObject("OSc-LSM")
        self._scene = QGraphicsScene()

        if "BH-TCSPC-RateCounter-Sync" not in self._dev.propertyNames():
            raise RuntimeError("SPC Rate Counters not available.")

        self._rate_counters = (
            _RateCounter(self._scene, self._dev.getPropertyObject("BH-TCSPC-RateCounter-Sync"), "Sync", Qt.GlobalColor.green, 10),
            _RateCounter(self._scene, self._dev.getPropertyObject("BH-TCSPC-RateCounter-CFD"), "CFD", Qt.GlobalColor.black, 40),
            _RateCounter(self._scene, self._dev.getPropertyObject("BH-TCSPC-RateCounter-TAC"), "TAC", Qt.GlobalColor.blue, 70),
            _RateCounter(self._scene, self._dev.getPropertyObject("BH-TCSPC-RateCounter-ADC"), "ADC", Qt.GlobalColor.red, 100),
        )

        bars_width = max([r._x for r in self._rate_counters]) + BAR_WIDTH

        tick_pen = QPen(QApplication.palette().color(QPalette.ColorRole.Text))
        tick_brush = QBrush(QApplication.palette().color(QPalette.ColorRole.Text))
        self._n_ticks = 8
        for i in range(self._n_ticks):
            # TODO: This could be a little hard on the eyes :)
            y = BAR_HEIGHT / (self._n_ticks - 1) * i
            self._scene.addLine(QLineF(0, y, bars_width, y), tick_pen)

            text = "10" if i == 0 else "100" if i == 1 else f"1e{i+1}"
            handle = cast(QGraphicsSimpleTextItem, self._scene.addSimpleText(text))
            handle.setBrush(tick_brush)
            handle.setPos(
                -10 - handle.boundingRect().width(),
                BAR_HEIGHT - y - handle.boundingRect().height() / 2
            )

        self._view = _GraphicsFrame(self._scene)

        self.spinboxes = QFormLayout()
        for counter in self._rate_counters:
            self.spinboxes.addRow(counter.lbl, counter.spinbox)


        self._layout = QHBoxLayout(self)
        self._layout.addWidget(self._view)
        self._layout.addLayout(self.spinboxes)

        t = QTimer(self)
        t.setInterval(100)
        t.timeout.connect(self._pollRates)
        t.start()

    def _pollRates(self) -> None:
        for counter in self._rate_counters:
            counter.update()
