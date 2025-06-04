from __future__ import annotations

from typing import TYPE_CHECKING

from pymmcore_plus import CMMCorePlus

from pymmcore_openscan.widgets import DCCWidget, DCUWidget

if TYPE_CHECKING:
    from pytestqt.qtbot import QtBot


def test_dcc_disabled(qtbot: QtBot) -> None:
    """Tests how DCCWidget behaves when the device is unavailable."""
    mmcore = CMMCorePlus.instance()
    wdg = DCCWidget(mmcore=mmcore)
    qtbot.addWidget(wdg)

    assert len(wdg._modules) == 0


def test_dcu_disabled(qtbot: QtBot) -> None:
    """Tests how DCUWidget behaves when the device is unavailable."""
    mmcore = CMMCorePlus.instance()
    wdg = DCUWidget(mmcore=mmcore)
    qtbot.addWidget(wdg)

    assert len(wdg._modules) == 0
