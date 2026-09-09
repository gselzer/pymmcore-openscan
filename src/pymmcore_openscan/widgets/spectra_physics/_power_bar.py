from __future__ import annotations

from typing import TYPE_CHECKING

import numpy as np
from pymmcore_plus import CMMCorePlus
from qtpy.QtCore import Qt
from qtpy.QtGui import QPainter
from qtpy.QtWidgets import QWidget

from ._utils import _DEVICE_NAME, _PollingWorker

if TYPE_CHECKING:
    from qtpy.QtGui import QPaintEvent

_POWER_PROP = "Laser Power (W)"
_BAR_MAX = 3.0
_TICK_INTERVAL = 0.5
# Gap between the bar and the label text below it
_LABEL_GAP = 2


class PowerBarWidget(QWidget):
    """Laser output power bar (0-3), polled from the device."""

    def __init__(
        self,
        parent: QWidget | None = None,
        mmcore: CMMCorePlus | None = None,
    ) -> None:
        super().__init__(parent)
        self._mmcore = mmcore or CMMCorePlus.instance()
        self._value = 0.0
        self.setFixedHeight(30)
        self.setMinimumWidth(100)

        self._worker = _PollingWorker(self._mmcore, [(_DEVICE_NAME, _POWER_PROP)])
        self._worker.updated.connect(self._on_updated)

        self._mmcore.events.systemConfigurationLoaded.connect(self._try_enable)
        self._try_enable()

    def _try_enable(self) -> None:
        enabled = _DEVICE_NAME in self._mmcore.getLoadedDevices()
        self.setEnabled(enabled)
        if enabled:
            self._worker.start()
        else:
            self._worker.stop()
            self._set_value(0.0)

    def _on_updated(self, _: str, prop: str, value: str) -> None:
        if prop == _POWER_PROP:
            try:
                self._set_value(float(value))
            except ValueError:
                pass

    def _set_value(self, value: float) -> None:
        if value == self._value:
            return
        self._value = value
        self.update()

    def paintEvent(self, a0: QPaintEvent | None) -> None:
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        font = painter.font()
        font.setPointSize(7)
        painter.setFont(font)

        w = self.width()
        h = self.height()
        fm = painter.fontMetrics()
        pal = self.palette()

        bar_h = h - _LABEL_GAP - fm.height()

        # Background track
        painter.setPen(Qt.PenStyle.NoPen)
        painter.setBrush(pal.color(pal.ColorRole.Mid))
        painter.drawRect(0, 0, w, bar_h)

        # Fill in the bar according to the current value
        if 0 <= self._value <= _BAR_MAX:
            painter.setBrush(pal.color(pal.ColorRole.Highlight))
            fill_width = round(self._value / _BAR_MAX * w)
            painter.drawRect(0, 0, fill_width, bar_h)

        painter.setPen(pal.color(pal.ColorRole.PlaceholderText))
        label_baseline = bar_h + _LABEL_GAP + fm.ascent()

        # Ticks at every half-integer; integer ticks are full-height
        for i in np.arange(0, _BAR_MAX + _TICK_INTERVAL, _TICK_INTERVAL):
            x = min(round(i / _BAR_MAX * w), w - 1)
            top = 0 if i % 1 == 0 else (3 * bar_h // 4)
            painter.drawLine(x, top, x, bar_h)

        # Labels at the endpoints
        for val in (0.0, _BAR_MAX):
            x = min(round(val / _BAR_MAX * w), w - 1)
            label = f"{val:g}"
            lw = fm.horizontalAdvance(label)
            lx = max(0, min(x - lw // 2, w - lw))
            painter.drawText(lx, label_baseline, label)

        # "Output Power (W)" title centered under the bar
        title = "Output Power (W)"
        tw = fm.horizontalAdvance(title)
        painter.drawText(max(0, (w - tw) // 2), label_baseline, title)
