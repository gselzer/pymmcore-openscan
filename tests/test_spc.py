from __future__ import annotations

from typing import TYPE_CHECKING

from pymmcore_plus import CMMCorePlus

from pymmcore_openscan.widgets import SPCRateCounters

if TYPE_CHECKING:
    from pytestqt.qtbot import QtBot


def test_spc_disabled(qtbot: QtBot) -> None:
    """Tests how SPCRateCounters behaves when the device is unavailable."""
    mmcore = CMMCorePlus.instance()
    wdg = SPCRateCounters(mmcore=mmcore)
    qtbot.addWidget(wdg)

    for counter in wdg._rate_counters:
        assert not counter.spinbox.isEnabled()
        assert counter._rect.rect().height() == 0
