from __future__ import annotations

from typing import TYPE_CHECKING

from qtpy.QtCore import QObject, QThread, QTimer, Signal
from qtpy.QtGui import QIcon
from qtpy.QtWidgets import QPushButton, QWidget

if TYPE_CHECKING:
    from pymmcore_plus import CMMCorePlus

_DEVICE_NAME = "Spectra-Physics Laser"
_MAIN_SHUTTER_DEVICE = "Spectra-Physics Main Shutter"
_SHUTTER_1040_DEVICE = "Spectra-Physics Insight 1040nm Shutter"
_POLL_INTERVAL_MS = 500


class SafetyButton(QPushButton):
    """A QPushButton that toggles ON only after being held for a full countdown.

    Useful when you want to make sure that the user really intends to toggle the button.
    Press and hold to start the countdown; release early to cancel.
    """

    _OFF = "off"
    _COUNTING = "counting"
    _ON = "on"

    def __init__(
        self,
        parent: QWidget | None = None,
        on_text: str = "",
        off_text: str = "",
        on_icon: QIcon | None = None,
        counting_icon: QIcon | None = None,
        off_icon: QIcon | None = None,
        countdown_seconds: int = 3,
    ) -> None:
        super().__init__(parent)
        self._state = self._OFF
        self._source_state = self._OFF
        self._remaining = 0
        self.setCheckable(True)

        self._on_text = on_text
        self._off_text = off_text
        self._on_icon = on_icon or QIcon()
        self._counting_icon = counting_icon or QIcon()
        self._off_icon = off_icon or QIcon()

        self._countdown_seconds = countdown_seconds
        self.countdown_seconds = countdown_seconds  # sets tooltip

        self._countdown_timer = QTimer()
        self._countdown_timer.setInterval(1000)
        self._countdown_timer.timeout.connect(self._tick)

        self.pressed.connect(self._on_pressed)
        self.released.connect(self._on_released)
        self._refresh()

    def nextCheckState(self) -> None:
        """Suppress Qt's auto-toggle on click; state is managed entirely by us."""

    @property
    def on_text(self) -> str:
        return self._on_text

    @on_text.setter
    def on_text(self, value: str) -> None:
        self._on_text = value
        self._refresh()

    @property
    def off_text(self) -> str:
        return self._off_text

    @off_text.setter
    def off_text(self, value: str) -> None:
        self._off_text = value
        self._refresh()

    @property
    def on_icon(self) -> QIcon:
        return self._on_icon

    @on_icon.setter
    def on_icon(self, value: QIcon) -> None:
        self._on_icon = value
        self._refresh()

    @property
    def off_icon(self) -> QIcon:
        return self._off_icon

    @off_icon.setter
    def off_icon(self, value: QIcon) -> None:
        self._off_icon = value
        self._refresh()

    @property
    def counting_icon(self) -> QIcon:
        return self._counting_icon

    @counting_icon.setter
    def counting_icon(self, value: QIcon) -> None:
        self._counting_icon = value
        self._refresh()

    @property
    def countdown_seconds(self) -> int:
        return self._countdown_seconds

    @countdown_seconds.setter
    def countdown_seconds(self, value: int) -> None:
        self._countdown_seconds = value
        self.setToolTip(f"Hold for {self._countdown_seconds} seconds to toggle ON")
        self._refresh()

    def _on_pressed(self) -> None:
        if self._state == self._ON:
            self._state = self._OFF
        elif self._state == self._OFF:
            self._source_state = self._state
            self._state = self._COUNTING
            self._remaining = self._countdown_seconds
            self._countdown_timer.start()
            # Set a fixed size to prevent resizes during the countdown
            self.setFixedSize(self.size())
        self._refresh()

    def _on_released(self) -> None:
        if self._state == self._COUNTING:
            self._countdown_timer.stop()
            self._state = self._source_state
        # Undo the fixed size
        self.setMinimumSize(0, 0)
        # NOTE this number comes from the PyQt value for QWIDGETSIZE_MAX
        self.setMaximumSize(16777215, 16777215)
        self._refresh()

    def _tick(self) -> None:
        self._remaining -= 1
        if self._remaining == 0:
            self._countdown_timer.stop()
            self._state = self._ON if self._source_state == self._OFF else self._OFF
        self._refresh()

    def _refresh(self) -> None:
        super().setChecked(self._state == self._ON)
        text = {
            self._ON: self.on_text,
            self._OFF: self.off_text,
            self._COUNTING: str(self._remaining),
        }
        self.setText(text[self._state])
        icon = {
            self._ON: self.on_icon,
            self._OFF: self.off_icon,
            self._COUNTING: self.counting_icon,
        }
        self.setIcon(icon[self._state])

    def setChecked(self, checked: bool) -> None:
        """Override setChecked to update the state accordingly."""
        self._state = self._ON if checked else self._OFF
        self._refresh()


class _PollingWorker(QObject):
    """Polls a configurable list of (device, property) pairs at a regular interval.

    Emits ``updated(device_name, property_name, value)`` for each pair on every tick.
    Owns its own QThread; call ``start()`` / ``stop()`` to control polling.
    Must not be given a QObject parent (required by moveToThread).
    """

    updated = Signal(str, str, str)  # device_name, property_name, value
    _start_requested = Signal()
    _stop_requested = Signal()

    def __init__(
        self,
        mmcore: CMMCorePlus,
        props: list[tuple[str, str]],
        interval_ms: int = _POLL_INTERVAL_MS,
    ) -> None:
        super().__init__()
        self._mmcore = mmcore
        self._props = props
        self._timeout = interval_ms
        self._thread = QThread()
        self._timer: QTimer | None = None
        self._start_requested.connect(self._start)
        self._stop_requested.connect(self._stop_timer)
        self.moveToThread(self._thread)

    def start(self) -> None:
        if not self._thread.isRunning():
            self._thread.start()
        self._start_requested.emit()

    def _start(self) -> None:
        if self._timer is None:
            self._timer = QTimer()
        if self._timer.isActive():
            # Already going
            return
        self._timer.setInterval(self._timeout)
        self._timer.timeout.connect(self._poll)
        self._timer.start()

    def stop(self) -> None:
        self._stop_requested.emit()

    def _stop_timer(self) -> None:
        if self._timer:
            self._timer.stop()
        self._thread.quit()
        self._thread.wait()

    def _poll(self) -> None:
        for device, prop in self._props:
            if self._mmcore.hasProperty(device, prop):
                value = str(self._mmcore.getProperty(device, prop))
                self.updated.emit(device, prop, value)
