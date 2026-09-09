from __future__ import annotations

import re
from pathlib import Path
from typing import TYPE_CHECKING, ClassVar

from pymmcore_plus import CMMCorePlus, Device
from qtpy.QtCore import QByteArray, QRectF, QSize, Qt
from qtpy.QtGui import QPainter, QPalette, QPixmap
from qtpy.QtSvg import QSvgRenderer
from qtpy.QtWidgets import (
    QFormLayout,
    QGridLayout,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QMenu,
    QPushButton,
    QSizePolicy,
    QSpinBox,
    QVBoxLayout,
    QWidget,
)
from superqt import QElidingLabel, QFlowLayout
from superqt.utils import signals_blocked

from pymmcore_openscan._settings import Settings

from ._laser_button import LaserButton
from ._power_bar import PowerBarWidget
from ._shutter_button import ShutterButton
from ._utils import (
    _DEVICE_NAME,
    _MAIN_SHUTTER_DEVICE,
    _SHUTTER_1040_DEVICE,
    _PollingWorker,
)

if TYPE_CHECKING:
    from qtpy.QtCore import QPoint

_ASSETS = Path(__file__).parent / "_assets"
_ICON_ACTIVE_PATH = _ASSETS / "laser-symbol.svg"
_ICON_INACTIVE_PATH = _ASSETS / "laser-symbol-inactive.svg"
_ICON_SIZE = QSize(128, 128)


def _render_svg(data: bytes) -> QPixmap:
    pixmap = QPixmap(_ICON_SIZE)
    pixmap.fill(Qt.GlobalColor.transparent)
    renderer = QSvgRenderer(QByteArray(data))
    scaled = renderer.defaultSize().scaled(
        _ICON_SIZE, Qt.AspectRatioMode.KeepAspectRatio
    )
    x = (_ICON_SIZE.width() - scaled.width()) / 2
    y = (_ICON_SIZE.height() - scaled.height()) / 2
    painter = QPainter(pixmap)
    renderer.render(painter, QRectF(x, y, scaled.width(), scaled.height()))
    painter.end()
    return pixmap


class _LaserGroupBox(QGroupBox):
    """Controls for laser power."""

    _STATE_PROP = "Laser State"
    _PULSING_PROP = "Pulsing"
    _POWER_PROP = "Laser Power (W)"
    _POLL_PROPS: ClassVar[list[tuple[str, str]]] = [
        (_DEVICE_NAME, _STATE_PROP),
        (_DEVICE_NAME, _PULSING_PROP),
        (_DEVICE_NAME, _POWER_PROP),
    ]

    def __init__(
        self,
        mmcore: CMMCorePlus,
        parent: QWidget | None = None,
    ) -> None:
        super().__init__("Laser", parent)
        self.setSizePolicy(QSizePolicy.Policy.Preferred, QSizePolicy.Policy.Fixed)

        self._mmcore = mmcore
        self._worker = _PollingWorker(self._mmcore, self._POLL_PROPS)
        self._worker.updated.connect(self._on_updated)

        ## -- WIDGETS -- ##
        self.laser_button = LaserButton(mmcore=mmcore)

        self._pulsing_indicator = QLabel("Pulsing")
        self._pulsing_indicator.setAlignment(Qt.AlignmentFlag.AlignCenter)

        self._laser_state = QElidingLabel("N/A")
        self._laser_power = QLabel("N/A")

        ## -- LAYOUT -- ##
        top_row = QHBoxLayout()
        top_row.addWidget(self.laser_button, stretch=0)
        top_row.addWidget(self._pulsing_indicator, stretch=1)

        self._laser_form = QFormLayout()
        self._laser_form.addRow("State:", self._laser_state)
        self._laser_form.addRow("Power:", self._laser_power)

        layout = QVBoxLayout(self)
        layout.addLayout(top_row)
        layout.addLayout(self._laser_form)
        layout.addWidget(PowerBarWidget(mmcore=mmcore))

        ## -- INITIAL STATE -- ##
        self._set_pulsing(False)

        self._mmcore.events.systemConfigurationLoaded.connect(self._try_enable)
        self._try_enable()

    def _on_updated(self, _: str, prop: str, value: str) -> None:
        if prop == self._STATE_PROP:
            display = re.sub(r"\s*\(\d+\)$", "", value)
            self._laser_state.setText(display)
            self._laser_state.setToolTip(value)
            self.laser_button.setEnabled(not value.startswith("Initializing"))
        elif prop == self._PULSING_PROP:
            self._set_pulsing(value == "1")
        elif prop == self._POWER_PROP:
            try:
                float_value = float(value)
            except ValueError:
                self._laser_power.setText("N/A")
            else:
                self._laser_power.setText(f"{float_value:.2f} W")

    def _set_pulsing(self, pulsing: bool) -> None:
        p = self._pulsing_indicator.palette()
        if pulsing:
            text = p.color(QPalette.ColorRole.HighlightedText).name()
            bg = p.color(QPalette.ColorRole.Highlight).name()
            self._pulsing_indicator.setStyleSheet(
                f"color: {text}; background-color: {bg}; border-radius: 4px;"
            )
        else:
            text = p.color(QPalette.ColorRole.Mid).name()
            border = p.color(QPalette.ColorRole.Mid).name()
            self._pulsing_indicator.setStyleSheet(
                f"color: {text}; border: 1px solid {border}; border-radius: 4px;"
            )

    def _try_enable(self) -> None:
        enabled = _DEVICE_NAME in self._mmcore.getLoadedDevices()
        # The laser state is nice to show if available
        self._laser_form.setRowVisible(
            self._laser_state,
            enabled and self._mmcore.hasProperty(_DEVICE_NAME, self._STATE_PROP),
        )
        if enabled:
            self._worker.start()
        else:
            self._laser_state.setText("N/A")
            self._laser_power.setText("N/A")
            self._set_pulsing(False)
            self._worker.stop()


class _ShutterGroupBox(QGroupBox):
    """Controls for laser shutters."""

    def __init__(
        self,
        mmcore: CMMCorePlus,
        parent: QWidget | None = None,
    ) -> None:
        super().__init__("Shutters", parent)
        self._mmcore = mmcore

        ## -- WIDGETS -- ##
        self.shutter_main_button = ShutterButton(_MAIN_SHUTTER_DEVICE, mmcore=mmcore)
        self.shutter_main_button.on_text = "Main"
        self.shutter_main_button.off_text = "Main"

        self.shutter_1040_button = ShutterButton(_SHUTTER_1040_DEVICE, mmcore=mmcore)
        self.shutter_1040_button.on_text = "1040nm"
        self.shutter_1040_button.off_text = "1040nm"

        self._shutter_icon = QLabel()
        self._shutter_icon.setPixmap(self._inactive_laser_pixmap())

        ## -- LAYOUT -- ##
        self._layout = QGridLayout(self)
        self._layout.addWidget(
            self.shutter_main_button, 0, 0, Qt.AlignmentFlag.AlignHCenter
        )
        self._layout.addWidget(
            self.shutter_1040_button, 0, 1, Qt.AlignmentFlag.AlignHCenter
        )

        ## -- SIGNALS -- ##
        self.shutter_main_button.toggled.connect(self._update_shutter_icon)
        self.shutter_1040_button.toggled.connect(self._update_shutter_icon)
        mmcore.events.systemConfigurationLoaded.connect(self._try_enable)
        self._try_enable()

    def _try_enable(self) -> None:
        loaded = self._mmcore.getLoadedDevices()
        is_1040_unavailable = (
            _DEVICE_NAME in loaded and _SHUTTER_1040_DEVICE not in loaded
        )
        # TODO: Simulated device unloading is vulnerable to hangs when the 1040nm
        # shutter button is currently hidden. If the real devices are also vulnerable to
        # hangs, we may need to defer showing the button to the next event-loop tick via
        # QTimer.singleShot(0, self.shutter_1040_button.show)
        self.shutter_1040_button.setVisible(not is_1040_unavailable)
        colspan = 1 if is_1040_unavailable else 2
        self._layout.addWidget(
            self._shutter_icon, 1, 0, 1, colspan, Qt.AlignmentFlag.AlignHCenter
        )

    def _inactive_laser_pixmap(self) -> QPixmap:
        color = self.palette().color(QPalette.ColorRole.Mid).name()
        data = _ICON_INACTIVE_PATH.read_bytes().replace(b"currentColor", color.encode())
        return _render_svg(data)

    def _update_shutter_icon(self) -> None:
        if self.shutter_main_button.isChecked():
            self._shutter_icon.setPixmap(_render_svg(_ICON_ACTIVE_PATH.read_bytes()))
        elif (btn := self.shutter_1040_button) and btn.isChecked():
            self._shutter_icon.setPixmap(_render_svg(_ICON_ACTIVE_PATH.read_bytes()))
        else:
            self._shutter_icon.setPixmap(self._inactive_laser_pixmap())


class _WavelengthGroupBox(QGroupBox):
    """Controls for tunable output wavelength."""

    _TARGET_PROP = "Target Wavelength (nm)"
    _ACTUAL_PROP = "Actual Wavelength (nm)"
    _POLL_PROPS: ClassVar[list[tuple[str, str]]] = [
        (_MAIN_SHUTTER_DEVICE, _ACTUAL_PROP),
    ]

    def __init__(
        self,
        mmcore: CMMCorePlus,
        parent: QWidget | None = None,
    ) -> None:
        super().__init__("Wavelength", parent)
        self._mmcore = mmcore
        self._dev: Device | None = None
        self._preset_btns: list[QPushButton] = []

        ## -- WIDGETS -- ##
        self._target = QSpinBox()
        self._target.setRange(680, 1300)
        self._target.setSuffix(" nm")
        self._target.editingFinished.connect(self._on_target_widget_changed)

        self._actual = QLabel("N/A")

        self._presets_group = QGroupBox("Presets")
        self._add_btn = QPushButton("+ Add")
        self._add_btn.setToolTip("Save current target as a preset")

        ## -- LAYOUT -- ##
        form = QFormLayout()
        form.addRow("Target:", self._target)
        form.addRow("Actual:", self._actual)

        self._presets_layout = QFlowLayout(self._presets_group)
        self._presets_layout.addWidget(self._add_btn)

        layout = QVBoxLayout(self)
        layout.addLayout(form)
        layout.addWidget(self._presets_group)

        ## -- POLLING -- ##
        self._worker = _PollingWorker(self._mmcore, self._POLL_PROPS)
        self._worker.updated.connect(self._on_updated)

        ## -- SIGNALS -- ##
        self._mmcore.events.systemConfigurationLoaded.connect(self._try_enable)
        self._mmcore.events.devicePropertyChanged(
            _MAIN_SHUTTER_DEVICE, self._TARGET_PROP
        ).connect(self._on_target_property_change)
        self._add_btn.clicked.connect(self._add_preset)

        ## -- INITIALIZATION -- ##
        self._try_enable()
        for wl in Settings.instance().spectra_physics_wavelength_presets:
            self._insert_preset_button(wl)

    def _try_enable(self) -> None:
        self._dev = None
        if _MAIN_SHUTTER_DEVICE in self._mmcore.getLoadedDevices():
            self._dev = self._mmcore.getDeviceObject(_MAIN_SHUTTER_DEVICE)

        if self._dev:
            self._target.setValue(int(self._dev.getProperty(self._TARGET_PROP)))
            self._worker.start()
        else:
            self._target.setValue(0)
            self._worker.stop()

    def _on_target_property_change(self, new_value: str) -> None:
        if self._dev is None:
            return
        with signals_blocked(self._target):
            self._target.setValue(int(new_value))

    def _on_target_widget_changed(self) -> None:
        if self._dev is None:
            return
        self._dev.setProperty(self._TARGET_PROP, str(self._target.value()))

    def _on_updated(self, _: str, prop: str, value: str) -> None:
        if prop == self._ACTUAL_PROP:
            self._actual.setText(f"{float(value):g} nm")

    def _add_preset(self) -> None:
        wl = self._target.value()
        existing = [int(b.text().removesuffix(" nm")) for b in self._preset_btns]
        if wl in existing:
            return
        self._insert_preset_button(wl)
        self._save_presets()

    def _insert_preset_button(self, wl: int) -> None:
        btn = QPushButton(f"{wl} nm")
        btn.setToolTip("Click to apply; right-click to delete")
        btn.clicked.connect(lambda: self._apply_preset(wl))
        btn.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        btn.customContextMenuRequested.connect(
            lambda pos, b=btn: self._show_remove_menu(b, pos)
        )
        self._presets_layout.addWidget(btn)
        self._preset_btns.append(btn)

    def _save_presets(self) -> None:
        Settings.instance().spectra_physics_wavelength_presets = [
            int(b.text().removesuffix(" nm")) for b in self._preset_btns
        ]
        Settings.instance().flush()

    def _apply_preset(self, wl: int) -> None:
        self._target.setValue(wl)
        self._on_target_widget_changed()

    def _show_remove_menu(self, btn: QPushButton, pos: QPoint) -> None:
        menu = QMenu(self)
        remove = menu.addAction("Delete")
        if remove is not None:
            remove.triggered.connect(lambda: self._remove_preset(btn))
        menu.popup(btn.mapToGlobal(pos))

    def _remove_preset(self, btn: QPushButton) -> None:
        idx = self._preset_btns.index(btn)
        self._presets_layout.removeWidget(btn)
        btn.deleteLater()
        self._preset_btns.pop(idx)
        self._save_presets()


class LaserControlPanel(QWidget):
    """Combined panel with laser power, main shutter, and 1040nm shutter controls."""

    def __init__(
        self,
        parent: QWidget | None = None,
        mmcore: CMMCorePlus | None = None,
    ) -> None:
        super().__init__(parent)
        self._mmcore = mmcore or CMMCorePlus.instance()

        self._laser_group = _LaserGroupBox(self._mmcore)
        self._shutter_group = _ShutterGroupBox(self._mmcore)
        self._wavelength_group = _WavelengthGroupBox(self._mmcore)

        main_layout = QVBoxLayout(self)
        main_layout.addWidget(self._laser_group, stretch=0)
        main_layout.addWidget(self._shutter_group)
        main_layout.addWidget(self._wavelength_group)

        self._mmcore.events.systemConfigurationLoaded.connect(self._try_enable)
        self._try_enable()

    def _try_enable(self) -> None:
        enabled = _DEVICE_NAME in self._mmcore.getLoadedDevices()
        self.setEnabled(enabled)
