from __future__ import annotations

from typing import TYPE_CHECKING

from pymmcore_plus import CMMCorePlus

from pymmcore_openscan.widgets.spectra_physics import (
    LaserControlPanel,
    LaserDiagnosticsPanel,
)

if TYPE_CHECKING:
    from pytestqt.qtbot import QtBot


def test_controls_disabled(qtbot: QtBot) -> None:
    """Tests how the controls behave when the device is unavailable."""
    mmcore = CMMCorePlus.instance()
    wdg = LaserControlPanel(mmcore=mmcore)
    qtbot.addWidget(wdg)

    assert not wdg.isEnabled()


def test_diagnostics_disabled(qtbot: QtBot) -> None:
    """Tests how the diagnostics panel behaves when the device is unavailable."""
    mmcore = CMMCorePlus.instance()
    wdg = LaserDiagnosticsPanel(mmcore=mmcore)
    qtbot.addWidget(wdg)

    assert not wdg.isEnabled()
