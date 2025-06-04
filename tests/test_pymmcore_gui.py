from __future__ import annotations

from typing import TYPE_CHECKING

from pymmcore_gui import MicroManagerGUI

from pymmcore_openscan import augment_pymmcore_gui
from pymmcore_openscan._util import _get_action_infos

if TYPE_CHECKING:
    from pytestqt.qtbot import QtBot
    from qtpy.QtWidgets import QApplication


def test_augment_pymmcore_gui(qtbot: QtBot, qapp: QApplication) -> None:
    """Test that augment_pymmcore_gui installs the widgets."""
    # Create WidgetActionInfos
    augment_pymmcore_gui()
    # Create the GUI
    gui = MicroManagerGUI()
    qtbot.addWidget(gui)

    # Assert all widgets are registered
    for info in _get_action_infos():
        assert gui.get_action(info.key, create=False) is not None
