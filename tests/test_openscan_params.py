from __future__ import annotations

from typing import TYPE_CHECKING

from pymmcore_plus import CMMCorePlus

from pymmcore_openscan.widgets import OpenScanParameters

if TYPE_CHECKING:
    from pytestqt.qtbot import QtBot


def test_openscan_params_disabled(qtbot: QtBot) -> None:
    """Tests how OpenScanParameters behaves when the device is unavailable."""
    mmcore = CMMCorePlus.instance()
    wdg = OpenScanParameters(mmcore=mmcore)
    qtbot.addWidget(wdg)

    assert not wdg._resolution.isEnabled()
    assert wdg._resolution.count() == 0

    assert not wdg._zoom.isEnabled()
    assert wdg._zoom.value() == 1.0

    assert not wdg._px_time.isEnabled()
    assert wdg._px_time.count() == 0

    assert not wdg._px_rate.isEnabled()
    assert wdg._px_rate.count() == 0

    assert not wdg._line_scan_time.isEnabled()
    assert wdg._line_scan_time.text() == ""

    assert not wdg._show_canvas.isEnabled()
    assert not wdg._show_canvas.isChecked()

    assert not wdg._canvas.isEnabled()
    assert not wdg._canvas.isVisible()
