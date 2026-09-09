"""Shared pyqtgraph-based widget for live, scrolling time-series graphs."""

from __future__ import annotations

from collections import deque
from time import time
from typing import Literal, NamedTuple

import pyqtgraph as pg
from qtpy.QtCore import QEvent, Qt
from qtpy.QtGui import QColor, QPalette
from qtpy.QtWidgets import (
    QHBoxLayout,
    QPushButton,
    QSpinBox,
    QVBoxLayout,
    QWidget,
)


class _Curve(NamedTuple):
    item: pg.PlotDataItem
    xs: deque[float]
    ys: deque[float]
    width: int
    color: QColor | QPalette.ColorRole


class _ScrollingPlotWidget(QWidget):
    """A live, scrolling time-series plot with "Fit All" / "Last N seconds" controls.

    Provides pan/zoom and axis behavior for widgets that need a rolling graph.
    Add one or more named curves with `add_curve`, then push new samples with `append`.
    """

    def __init__(
        self,
        *,
        parent: QWidget | None = None,
        y_label: str = "",
        y_units: str | None = None,
        y_range: tuple[float, float] | None = None,
        y_si_prefix: bool = True,
        y_axis_side: Literal["left", "right"] | None = "left",
        log_y: bool = False,
        legend: bool = False,
        max_points: int = 7200,
        default_window_s: int = 10,
    ) -> None:
        super().__init__(parent=parent)
        self._max_points = max_points
        self._setting_range = False
        self._curves: dict[str, _Curve] = {}
        self._y_axis_side = y_axis_side

        self._plot = pg.PlotWidget(axisItems={"bottom": pg.DateAxisItem()})
        self._plot.hideAxis("left")
        self._plot.hideAxis("right")
        if y_axis_side == "right":
            self._plot.showAxis("right")
        elif y_axis_side == "left":
            self._plot.showAxis("left")

        y_axis = self._plot.getAxis(y_axis_side)
        if y_label or y_units:
            y_axis.setLabel(y_label, units=y_units)
        if not y_si_prefix:
            y_axis.enableAutoSIPrefix(False)
        if legend:
            # Curves added after this via `add_curve(..., name=...)` are
            # automatically shown in the legend. An opaque background (matching
            # the plot background) keeps curves from showing through the legend.
            self._plot.addLegend(
                pen=pg.mkPen(150, 150, 150),
                brush=pg.mkBrush(pg.getConfigOption("background")),
            )
        self._plot.showGrid(x=True, y=True, alpha=0.3)
        if log_y:
            self._plot.setLogMode(y=True)
        if y_range is not None:
            self._plot.setYRange(*y_range, padding=0)
        self._plot.hideButtons()
        self._plot.setMenuEnabled(False)
        vb = self._plot.getViewBox()
        vb.setMouseMode(pg.ViewBox.PanMode)
        vb.setMouseEnabled(x=True, y=False)
        # Disable "Last" mode when the user manually pans/zooms
        vb.sigRangeChangedManually.connect(self._on_manual_range_change)

        self._last_btn = QPushButton("Last")
        self._last_btn.setCheckable(True)
        self._last_btn.setChecked(True)
        self._last_btn.toggled.connect(self._on_last_toggled)

        self._last_spin = QSpinBox()
        self._last_spin.setRange(1, 3600)
        self._last_spin.setValue(default_window_s)
        self._last_spin.setSuffix(" s")
        self._last_spin.valueChanged.connect(self._on_last_spin_changed)

        controls = QHBoxLayout()
        controls.setContentsMargins(0, 0, 0, 0)
        controls.addStretch()
        controls.addWidget(self._last_btn)
        controls.addWidget(self._last_spin)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addWidget(self._plot)
        layout.addLayout(controls)

    def add_curve(
        self,
        key: str,
        color: QColor | Qt.GlobalColor | QPalette.ColorRole,
        *,
        width: int = 2,
        name: str | None = None,
    ) -> None:
        """Add a named curve.

        `color` may be a fixed color, or a `QPalette.ColorRole` that is
        re-resolved automatically whenever the widget's palette changes (e.g.
        a light/dark theme switch). `name` is the label shown in the legend
        (only meaningful if `legend=True` was passed to the constructor).
        """
        stored_color = color if isinstance(color, QPalette.ColorRole) else QColor(color)
        resolved_color = (
            self.palette().color(stored_color)
            if isinstance(stored_color, QPalette.ColorRole)
            else stored_color
        )
        item = self._plot.plot(pen=pg.mkPen(resolved_color, width=width), name=name)
        xs: deque[float] = deque(maxlen=self._max_points)
        ys: deque[float] = deque(maxlen=self._max_points)
        self._curves[key] = _Curve(item, xs, ys, width, stored_color)

    def append(self, key: str, y: float, x: float | None = None) -> None:
        """Append a sample to the named curve and refresh the plot."""
        curve = self._curves[key]
        curve.xs.append(time() if x is None else x)
        curve.ys.append(y)
        curve.item.setData(curve.xs, curve.ys)
        if self._last_btn.isChecked():
            self._scroll_to_last()

    def clear_curve(self, key: str) -> None:
        """Clear the data for a single named curve."""
        curve = self._curves[key]
        curve.xs.clear()
        curve.ys.clear()
        curve.item.setData(curve.xs, curve.ys)

    def clear(self) -> None:
        """Clear the data for all curves."""
        for key in self._curves:
            self.clear_curve(key)

    def _scroll_to_last(self) -> None:
        n = self._last_spin.value()
        self._setting_range = True
        self._plot.setXRange(time() - n, time(), padding=0)
        self._setting_range = False

    def _on_last_toggled(self, checked: bool) -> None:
        if checked:
            self._scroll_to_last()

    def _on_last_spin_changed(self) -> None:
        if self._last_btn.isChecked():
            self._scroll_to_last()

    def _on_manual_range_change(self) -> None:
        if not self._setting_range:
            self._last_btn.setChecked(False)

    def changeEvent(self, a0: QEvent | None) -> None:
        super().changeEvent(a0)
        if a0 is not None and a0.type() == QEvent.Type.PaletteChange:
            for curve in self._curves.values():
                if isinstance(curve.color, QPalette.ColorRole):
                    color = self.palette().color(curve.color)
                    curve.item.setPen(pg.mkPen(color, width=curve.width))
