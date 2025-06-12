from __future__ import annotations

from typing import TYPE_CHECKING

from pymmcore_plus import CMMCorePlus

from pymmcore_openscan.widgets import ImageCollectionParameters

if TYPE_CHECKING:
    from pytestqt.qtbot import QtBot


def test_image_collection_params_disabled(qtbot: QtBot) -> None:
    """Tests how DCCWidget behaves when the device is unavailable."""
    mmcore = CMMCorePlus.instance()
    wdg = ImageCollectionParameters(mmcore=mmcore)
    qtbot.addWidget(wdg)

    assert not wdg._resolution.isEnabled()
    assert wdg._resolution.count() == 0
    assert not wdg._zoom.isEnabled()
    assert wdg._zoom.value() == 1.0
    assert not wdg._px_rate.isEnabled()
    assert wdg._resolution.count() == 0
